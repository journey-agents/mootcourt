"""Rolling-origin backtest core: leakage guard, per-row scores and the rungs that are scored.

For each calendar quarter start ``t_k`` the harness fits every rung on the rows visible at ``t_k``
(status admitted and ``usable_after <= t_k``), then predicts every admitted row whose ``started_at`` lies in
``[t_k, t_{k+1})`` using that row's planned-exposure standard error as ``s_star``, and scores it against its
realized ``y``. Nothing is scored by a model that saw it, and two guards enforce that:

* ``assert_no_leakage`` checks the frames handed over (fit rows usable, scored rows not yet usable, no
  shared row id) and raises ``LeakageError``.
* While fitting, the ``fit`` methods of the known model classes are wrapped so a frame containing a row
  that is not yet usable raises ``LeakageError`` even if a factory ignores the rows it was given.

The wrapped classes are P0, P1, P2 and the feature space. ``TeamModel`` and ``GBMChallenger`` read the rows
the factory hands them and are not wrapped, so the factory is the one place that decides what they see.

Row-level output only; aggregation, intervals and calibration are in ``harness_stats``.

Units: ``y``, ``s``, intervals and point estimates are in the ledger's units (percentage points of click-through rate for Upworthy);
probabilities are unitless; log scores are per unit of y. A prediction is for the observed estimate
``y* = theta + Normal(0, s^2)``, so scores are against the observed estimate with known standard error.

Builder calls recorded for docs/method.md: 1 (Brier baseline is P0's significant-positive frequency),
2 (all predicted rows for every rung, abstention reported beside), 3 (reliability from earlier origins
only, burn-in at the first scored origin), 5, 10 (P3 scored beside each rung against the event y > 0),
26 to 31 (see plan-notes.md).
"""
from __future__ import annotations

import contextlib
import dataclasses
import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import special

from mootcourt import scale
from mootcourt.abstain import AbstainConfig, check_support, decide, reliability_reason
from mootcourt.config import (
    GBM_CONFIGS,
    GBM_FOLDS,
    GBM_ITER_MAX,
    GBM_VALIDATION_FRACTION,
    KAPPA,
    LOCAL_EB_K,
    NU_GRID,
    P2_GUARD_MULT,
    P2_SELECTIONS,
    Z,
)
from mootcourt.features import FEATURE_SETS, FeatureSpace, _parse_rows, has_reference, parse_references, sq_dists, use_cell_only
from mootcourt.ledger import ADMITTED, metric_of, quarter_of, to_utc, visible_rows
from mootcourt.predictors.base import Predictive, build_grid
from mootcourt.predictors.p0 import P0Predictor
from mootcourt.predictors.p1 import P1Predictor, sd_equivalent
from mootcourt.predictors.p2 import P2Predictor
from mootcourt.recalibration import METHODS as RECAL_METHODS
from mootcourt.recalibration import Calibrator, time_folds
from mootcourt.reliability import build_reliability

BURN_IN_NOTE = (
    "Burn-in: the first scored origin has no earlier origin to build a reliability report from, so every row "
    "there abstains for 'reliability report is missing'. Abstention-adjusted figures for that origin are not "
    "comparable with later origins."
)
MIN_FIT_ROWS = 20
INTERVAL_POINTS = 201
CALIBRATION_MAX_ROWS = 3000                      # visible rows used to fit a recalibration map (a fixed subsample above this)
_GH_NODES, _GH_WEIGHTS = np.polynomial.hermite.hermgauss(24)

SCORE_COLUMNS = [
    "row_id", "test_id", "cell", "period", "origin", "rung", "y", "s", "logscore", "crps", "p_sig", "p_win",
    "brier_event", "event", "direction_correct", "lo80", "hi80", "lo90", "hi90", "abstain", "abstain_reasons",
    "p_theta_posterior", "fallback_global",
]
EXTRA_COLUMNS = [
    "usable_after", "point", "p_gt0", "event_pos", "brier_pos", "p_base", "brier_base", "brier_floor_row",
    "dir_ceiling_row", "n_visible_cell", "s_star", "exposure", "event_planned", "brier_planned", "p_base_planned", "brier_base_planned",
]


class LeakageError(RuntimeError):
    """A model saw a row it may not have seen, or a scored row was already usable at its origin."""


# ------------------------------------------------------------------ origins
def _quarter_start(ts: pd.Timestamp) -> pd.Timestamp:
    ts = ts.tz_convert("UTC")
    return pd.Timestamp(year=ts.year, month=3 * ((ts.month - 1) // 3) + 1, day=1, tz="UTC")


def quarterly_origins(ledger: pd.DataFrame) -> list[pd.Timestamp]:
    """Calendar quarter starts (UTC) from the quarter of the first admitted start to the quarter of the last."""
    adm = ledger.loc[ledger["status"] == ADMITTED] if (ledger["status"] == ADMITTED).any() else ledger
    if len(adm) == 0:
        raise ValueError("the ledger has no rows")
    lo, hi = adm["started_at"].min(), adm["started_at"].max()
    out, cur = [], _quarter_start(lo)
    while cur <= hi:
        out.append(cur)
        cur = cur + pd.DateOffset(months=3)
    return out


# ----------------------------------------------------------------- leakage
def assert_no_leakage(fit_rows: pd.DataFrame, scored_rows: pd.DataFrame, origin) -> None:
    """Raise LeakageError unless every fit row is usable at ``origin``, no scored row is, and no row is in both."""
    t = to_utc(origin)
    late = fit_rows["usable_after"] > t
    if late.any():
        raise LeakageError(f"{int(late.sum())} fit rows are not usable at {t} (first: {fit_rows.loc[late, 'row_id'].iloc[0]})")
    seen = scored_rows["usable_after"] <= t
    if seen.any():
        raise LeakageError(f"{int(seen.sum())} scored rows were already usable at {t} (first: {scored_rows.loc[seen, 'row_id'].iloc[0]})")
    both = set(fit_rows["row_id"]) & set(scored_rows["row_id"])
    if both:
        raise LeakageError(f"{len(both)} rows are in both the fit set and the scored set (first: {sorted(both)[0]})")


@contextlib.contextmanager
def _audit_fits(origin):
    """Wrap the known ``fit`` methods so any frame with a not-yet-usable row raises LeakageError."""
    t = to_utc(origin)
    targets = [(P0Predictor, False), (P1Predictor, False), (P2Predictor, False), (FeatureSpace, True)]
    saved = []

    def check(frame):
        if isinstance(frame, pd.DataFrame) and "usable_after" in frame.columns:
            late = frame["usable_after"] > t
            if late.any():
                raise LeakageError(f"{int(late.sum())} rows with usable_after after the origin {t} reached fit")

    for cls, is_cls in targets:
        raw = cls.__dict__["fit"]
        fn = raw.__func__ if is_cls else raw

        def make(fn=fn, is_cls=is_cls):
            if is_cls:
                def wrapped(klass, rows, *a, **k):
                    check(rows)
                    return fn(klass, rows, *a, **k)
                return classmethod(wrapped)

            def wrapped(self, rows, *a, **k):
                check(rows)
                return fn(self, rows, *a, **k)
            return wrapped

        saved.append((cls, "fit", raw))
        cls.fit = make()
    # The challengers are built from the rows the factory hands them, in __init__: wrapped the same way (review L, REV-L-005), so a factory
    # that gives GBMChallenger, LocalEB or TextLR a row that is not yet usable raises LeakageError.
    for cls in (GBMChallenger, LocalEB, TextLR):
        raw_init = cls.__dict__["__init__"]

        def make_init(raw_init=raw_init):
            def wrapped(self, *args, **kwargs):
                for a in list(args) + list(kwargs.values()):
                    check(a)
                return raw_init(self, *args, **kwargs)
            return wrapped

        saved.append((cls, "__init__", raw_init))
        cls.__init__ = make_init()
    try:
        yield
    finally:
        for cls, name, raw in saved:
            setattr(cls, name, raw)


# -------------------------------------------------------------- rung models
class _Shared:
    """Per-origin cache so P1, P2 and the challenger share one P1 fit and one feature space."""

    def __init__(self):
        self._store: dict = {}

    def get(self, kind, rows: pd.DataFrame, origin, build):
        key = (kind, pd.Timestamp(origin).value, len(rows), round(float(rows["y"].sum()), 9))
        if key not in self._store:
            if len(self._store) > 12:
                self._store.clear()
            self._store[key] = build()
        return self._store[key]


def _team_arrays(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """``(p_win_team, point_team)`` from features_json, NaN where a row has no team forecast."""
    p, pt = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
    for i, j in enumerate(rows["features_json"].tolist()):
        if "p_win_team" in j:
            f = json.loads(j)
            if "p_win_team" in f and "point_team" in f:
                p[i], pt[i] = float(f["p_win_team"]), float(f["point_team"])
    return p, pt


def has_team_forecasts(ledger: pd.DataFrame) -> bool:
    """True when any ledger row carries a team forecast in its features."""
    return bool(ledger["features_json"].str.contains("p_win_team", regex=False).any())


class TeamModel:
    """P3: the team's own forecast as a rung. Row-aware, so it exposes ``predict_row`` instead of ``predict``.

    The predictive for theta is Normal(point_team, sd_err^2) where ``sd_err^2`` is the variance of
    ``y - point_team`` over visible rows with forecasts minus their mean ``s^2`` (floored). ``p_gt0`` is the
    team's own ``p_win_team``, scored against the event y > 0 beside each rung's P(y* > 0) (call 10).
    """

    def __init__(self, rows: pd.DataFrame):
        p, pt = _team_arrays(rows)
        ok = np.isfinite(pt)
        y, s = rows["y"].to_numpy(float), rows["s"].to_numpy(float)
        if ok.sum() >= 5:
            v = float(np.var(y[ok] - pt[ok], ddof=1) - np.mean(s[ok] ** 2))
        else:
            v = float(np.var(y, ddof=1)) if len(y) > 1 else 1.0
        self.sd = float(np.sqrt(max(v, 1e-4)))
        self.n_forecasts = int(ok.sum())

    def predict_row(self, row, s_star: float, origin):
        """``(Predictive, {"p_gt0": p_win_team})`` for a scored row, or None when the row has no forecast."""
        f = json.loads(row.features_json)
        if "p_win_team" not in f or "point_team" not in f:
            return None
        grid = build_grid(f["point_team"], self.sd)
        return Predictive.from_normal(grid, f["point_team"], self.sd), {"p_gt0": float(f["p_win_team"])}


class GBMChallenger:
    """Gradient-boosted regression of y on the same features, as a predictive Normal for theta.

    Fairness (round 00, docs/method.md call 169). The model is weighted by ``1 / (s^2 + tau^2)`` (``tau`` the DerSimonian-Laird
    between-test spread of the visible rows), so a noisy estimate counts less, as it does in the ladder. A small time-ordered
    search picks the learning rate, the leaf count and the number of rounds: the earliest 80 percent of the visible rows (in
    start-time order) fit each configuration and the latest 20 percent score it by weighted squared error at every boosting
    round, so the stopping point never looks at a later row than a validation row. The chosen configuration is refit on all
    visible rows. ``tuned=False`` restores the earlier untuned, unweighted model (100 rounds, 0.1, 15 leaves).

    Calibration of the spread. The spread of the predictive comes from out-of-fold residuals: the visible rows are put in time
    order and cut into ``GBM_FOLDS`` contiguous folds, each fold is predicted by a model fit on the other folds, and the variance
    of those residuals minus the mean ``s^2`` (floored) is the spread of theta around the prediction. Below ``min_rows`` rows
    it is a constant (the weighted mean of y). Its ``p_sig`` goes through the same reliability bins as every other rung; the
    recalibrated rung (``oof_probabilities``) is fit on the out-of-fold predictions.
    """

    min_rows = 40

    def __init__(self, space: FeatureSpace, rows: pd.DataFrame, seed: int = 0, n_folds: int = GBM_FOLDS, tuned: bool = True):
        from threadpoolctl import threadpool_limits

        # one thread is faster than eight on these row counts (thread start-up dominates) and lets runs share the machine
        with threadpool_limits(limits=1):
            self._fit(space, rows, seed, n_folds, tuned)

    def _fit(self, space: FeatureSpace, rows: pd.DataFrame, seed: int, n_folds: int, tuned: bool) -> None:
        from sklearn.ensemble import HistGradientBoostingRegressor

        self.space, self.n_folds = space, n_folds
        order = rows.sort_values("started_at", kind="stable")
        # the cell is a feature: the ladder fits each cell apart, so a model of all cells must see which one
        self.cells = tuple(sorted(order["cell"].unique()))
        X, y, s = self._raw(order), order["y"].to_numpy(float), order["s"].to_numpy(float)
        # Quantize each column once (at most 63 levels, from the visible rows). With a sample weight scikit-learn finds its histogram bins by a
        # weighted percentile on every fit, which cost seven seconds a fit here; a column with fewer levels than bins skips that search.
        self._edges = [np.unique(np.quantile(X[:, j], np.linspace(0.0, 1.0, 64)[1:-1])) for j in range(X.shape[1])]
        X = self._bin(X)
        self.sorted_rows = order
        n = len(y)
        w = np.ones(n)
        if tuned and n > 1:
            _, tau = dersimonian_laird(y, s)
            w = 1.0 / (s ** 2 + tau ** 2)
            w = w / w.mean()

        def new(lr: float, leaves: int, iters: int):
            return HistGradientBoostingRegressor(max_iter=iters, learning_rate=lr, max_leaf_nodes=leaves, min_samples_leaf=10,
                                                 random_state=seed, early_stopping=False)

        self.oof_mean = np.full(n, np.nan)
        self.config: dict = {"tuned": bool(tuned)}
        if n < self.min_rows:
            self.model, self._const = None, float(np.average(y, weights=w))
            self.oof_mean = np.full(n, self._const)
        else:
            lr, leaves, iters = 0.1, 15, 100
            if tuned:
                cut = max(int(n * (1.0 - GBM_VALIDATION_FRACTION)), 10)
                best = None
                for lr_c, leaves_c in GBM_CONFIGS:
                    m = new(lr_c, leaves_c, GBM_ITER_MAX).fit(X[:cut], y[:cut], sample_weight=w[:cut])
                    errs = [float(np.average((yp - y[cut:]) ** 2, weights=w[cut:])) for yp in m.staged_predict(X[cut:])]
                    k = int(np.argmin(errs))
                    if best is None or errs[k] < best[0]:
                        best = (errs[k], lr_c, leaves_c, k + 1)
                _, lr, leaves, iters = best
                self.config.update({"learning_rate": lr, "max_leaf_nodes": leaves, "rounds": int(iters)})
            for a, b in time_folds(n, n_folds):
                self.oof_mean[b] = new(lr, leaves, iters).fit(X[a], y[a], sample_weight=w[a]).predict(X[b])
            self.model, self._const = new(lr, leaves, iters).fit(X, y, sample_weight=w), 0.0
        self.oof_residuals = y - self.oof_mean
        v = float(np.mean(self.oof_residuals ** 2) - np.mean(s ** 2))
        self.sd = float(np.sqrt(max(v, 1e-4)))
        self.range = (float(y.min()), float(y.max()))

    def _raw(self, rows: pd.DataFrame) -> np.ndarray:
        """The feature space of the rows with one 0/1 column per cell seen at fit appended."""
        onehot = (rows["cell"].to_numpy()[:, None] == np.asarray(self.cells, dtype=object)[None, :]).astype(np.float64)
        return np.hstack([self.space.transform(rows), onehot])

    def _bin(self, X: np.ndarray) -> np.ndarray:
        """The columns of ``X`` as ordinal quantile levels (0 to 63) by the edges found at fit."""
        X = np.asarray(X, dtype=np.float64)
        return np.column_stack([np.searchsorted(e, X[:, j], side="right") for j, e in enumerate(self._edges)]).astype(np.float64)

    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:
        """Normal(prediction, sd^2) for theta on a grid covering the observed range of y; ``x`` is a feature-space row, ``cell`` its cell."""
        onehot = np.array([[1.0 if c == cell else 0.0 for c in self.cells]])
        mean = self._const if self.model is None else float(self.model.predict(self._bin(np.hstack([np.asarray(x).reshape(1, -1), onehot])))[0])
        grid = build_grid(mean, self.sd, y_min=self.range[0], y_max=self.range[1])
        return Predictive.from_normal(grid, mean, self.sd)

    def _p_sig(self, mean, s_star) -> np.ndarray:
        return special.ndtr((np.asarray(mean) - Z * s_star) / np.sqrt(self.sd ** 2 + s_star ** 2))

    def raw_p_sig(self, scored: pd.DataFrame, s_star, X_cache=None) -> np.ndarray:
        """Closed-form ``p_sig`` of every scored row (what the recalibration map is applied to)."""
        key = id(self.space)
        X = (X_cache or {}).get(key)
        onehot = (scored["cell"].to_numpy()[:, None] == np.asarray(self.cells, dtype=object)[None, :]).astype(np.float64)
        X = np.hstack([self.space.transform(scored) if X is None else X, onehot])
        mean = np.full(len(scored), self._const) if self.model is None else self.model.predict(self._bin(X))
        return self._p_sig(mean, np.asarray(s_star, dtype=float))

    def oof_probabilities(self) -> tuple[np.ndarray, np.ndarray]:
        """``(p_sig, event)`` of the visible rows from their out-of-fold predictions, at their own pre-launch ``s_star``."""
        rows = self.sorted_rows
        s_star = scale.s_star_rows(rows, rows)
        p, e = self._p_sig(self.oof_mean, s_star), (rows["y"].to_numpy(float) > Z * rows["s"].to_numpy(float)).astype(float)
        if len(p) > CALIBRATION_MAX_ROWS:         # the same fixed subsample as the other challengers (REV-L-026)
            pick = np.sort(np.random.default_rng(0).choice(len(p), CALIBRATION_MAX_ROWS, replace=False))
            p, e = p[pick], e[pick]
        return p, e


def dersimonian_laird(y, s) -> tuple[float, float]:
    """Normal-Normal empirical Bayes for effects ``y`` with standard errors ``s``: ``(mu, tau)`` of the prior on theta.

    The between-test variance is the DerSimonian-Laird moment estimate ``max(0, (Q - (k - 1)) / C)`` with
    ``Q = sum w (y - y_w)^2``, ``C = sum w - sum w^2 / sum w`` and ``w = 1 / s^2``; the mean is then re-weighted by
    ``1 / (s^2 + tau^2)``. No shrinkage toward any other prior is applied.
    """
    y, s = np.asarray(y, float), np.asarray(s, float)
    k = len(y)
    if k == 0:
        raise ValueError("no effects to fit")
    if k == 1:
        return float(y[0]), 0.0
    w = 1.0 / s ** 2
    y_w = float((w * y).sum() / w.sum())
    q = float((w * (y - y_w) ** 2).sum())
    c = float(w.sum() - (w ** 2).sum() / w.sum())
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    w2 = 1.0 / (s ** 2 + tau2)
    return float((w2 * y).sum() / w2.sum()), math.sqrt(tau2)


class LocalEB:
    """Comparison-set empirical Bayes: the prior for a query is fit on its ``k`` nearest visible rows in feature space.

    Neighbors are searched among the visible rows of the query's cell (all visible rows when the cell has fewer
    than two). The prior is Normal(mu, tau^2) from ``dersimonian_laird`` on those neighbors alone: nothing is shrunk
    toward the cell prior, which is what makes it a baseline for the ladder and not another rung of it. The
    predictive for theta is that prior; its spread is floored at a thousandth of the range of y so the grid is defined.
    The feature space reads the reference headline where the rows carry one, so the neighbors are contrasts that changed
    the way the query does.
    """

    def __init__(self, space: FeatureSpace, rows: pd.DataFrame, k: int = LOCAL_EB_K):
        if k < 2:
            raise ValueError("k must be at least 2")
        self.space, self.k = space, int(k)
        X = space.transform(rows).astype(np.float32)
        y, s = rows["y"].to_numpy(float), rows["s"].to_numpy(float)
        self.rows = rows
        self._X, self._y, self._s, self._cells = X, y, s, rows["cell"].to_numpy()
        self._tables = self._build(np.ones(len(y), bool))
        self._floor = 1e-3 * float(y.max() - y.min() or 1.0)
        self.range = (float(y.min()), float(y.max()))

    def _build(self, mask: np.ndarray):
        """Search tables of the rows in ``mask``: ``(all, {cell: table})`` with a table ``(X, squared norms, y, s)``."""
        X, y, s, cells = self._X[mask], self._y[mask], self._s[mask], self._cells[mask]
        full = (X, np.einsum("ij,ij->i", X, X), y, s)
        by_cell = {}
        for c in np.unique(cells):
            idx = np.flatnonzero(cells == c)
            by_cell[c] = (X[idx], np.einsum("ij,ij->i", X[idx], X[idx]), y[idx], s[idx])
        return full, by_cell

    @staticmethod
    def _neighbors(tables, k: int, x, cell: str):
        full, by_cell = tables
        X, sq, y, s = by_cell.get(cell, full)
        if len(y) < 2:
            X, sq, y, s = full
        d2 = sq_dists(np.asarray(x, dtype=X.dtype), X, sq)
        kk = min(k, len(y))
        idx = np.argpartition(d2, kk - 1)[:kk] if kk < len(y) else np.arange(len(y))
        return y[idx], s[idx]

    def neighbors(self, x, cell: str):
        """``(y, s)`` of the ``k`` nearest visible rows of the cell."""
        return self._neighbors(self._tables, self.k, x, cell)

    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:
        ny, ns = self.neighbors(x, cell)
        mu, tau = dersimonian_laird(ny, ns)
        sd = max(tau, self._floor)
        return Predictive.from_normal(build_grid(mu, sd, y_min=self.range[0], y_max=self.range[1]), mu, sd)

    def _p_sig(self, tables, x, cell: str, s_star: float) -> float:
        ny, ns = self._neighbors(tables, self.k, x, cell)
        mu, tau = dersimonian_laird(ny, ns)
        sd = max(tau, self._floor)
        return float(special.ndtr((mu - Z * s_star) / math.sqrt(sd * sd + s_star * s_star)))

    def raw_p_sig(self, scored: pd.DataFrame, s_star, X_cache=None) -> np.ndarray:
        """Closed-form ``p_sig`` of every scored row (what the recalibration map is applied to)."""
        key = id(self.space)
        X = (X_cache or {}).get(key)
        if X is None:
            X = self.space.transform(scored)
        cells = scored["cell"].to_numpy()
        return np.array([self._p_sig(self._tables, X[i], cells[i], float(s_star[i])) for i in range(len(scored))])

    def oof_probabilities(self, max_rows: int = CALIBRATION_MAX_ROWS, n_folds: int = GBM_FOLDS, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """``(p_sig, event)`` of a subsample of the visible rows, each predicted from the rows of the other time folds.

        The visible rows are put in start-time order and cut into contiguous folds; a row's neighbors come from the other
        folds only, so it never neighbors itself or its own test's siblings that share its fold.
        """
        rows = self.rows
        order = np.argsort(rows["started_at"].to_numpy(), kind="stable")
        fold = np.empty(len(rows), int)
        for f, (_, test) in enumerate(time_folds(len(rows), n_folds)):
            fold[order[test]] = f
        pick = np.arange(len(rows))
        if len(pick) > max_rows:
            pick = np.sort(np.random.default_rng(seed).choice(len(pick), max_rows, replace=False))
        s_star = scale.s_star_rows(rows.iloc[pick], rows)
        p = np.empty(len(pick))
        for f in np.unique(fold):
            tables = self._build(fold != f)
            for j in np.flatnonzero(fold[pick] == f):
                i = pick[j]
                p[j] = self._p_sig(tables, self._X[i], str(self._cells[i]), float(s_star[j]))
        return p, (self._y[pick] > Z * self._s[pick]).astype(float)


class TextLR:
    """Text-only winner classifier: TF-IDF of the variant headline and logistic regression, probabilities used directly.

    Two models share one vectorizer. The first predicts the direction event ``y > 0``; the second is refit on the
    significant-positive event ``y > Z s`` (the realized ``s`` of past rows, which is history). There is no density,
    no interval and no Platt scaling, so the rung is scored with Brier and direction accuracy only. It ignores the
    precision of the future test, which is part of what the comparison shows.

    Pairwise (round 00, call 167). Where the rows carry a reference headline the design is the difference of the two headlines'
    TF-IDF vectors beside the variant's own, so the classifier sees what changed; without one it is the variant's TF-IDF.
    """

    def __init__(self, rows: pd.DataFrame, seed: int = 0, pairwise: bool | None = None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        heads = _parse_rows(rows)[0]
        self.cells = tuple(sorted(rows["cell"].unique()))           # one 0/1 column per cell, as for the GBM
        self.pairwise = has_reference(rows) if pairwise is None else (bool(pairwise) and has_reference(rows))
        refs = parse_references(rows) if self.pairwise else []
        self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, dtype=np.float64)
        self.vec.fit(list(dict.fromkeys(heads + refs)))
        Xt = self._design(heads, refs, rows["cell"].to_numpy())
        y, s = rows["y"].to_numpy(float), rows["s"].to_numpy(float)
        self._seed = seed
        self._rows = rows
        self._X, self._labels = Xt, (y > 0, y > Z * s)
        self._models = []
        for label in self._labels:
            if label.all() or not label.any():
                self._models.append(float(label.mean()))
            else:
                self._models.append(LogisticRegression(C=1.0, max_iter=500, random_state=seed).fit(Xt, label))

    def _design(self, heads, refs, cells):
        from scipy import sparse

        Xv = self.vec.transform(heads)
        onehot = sparse.csr_matrix((np.asarray(cells, dtype=object)[:, None] == np.asarray(self.cells, dtype=object)[None, :]).astype(np.float64))
        if not self.pairwise:
            return sparse.hstack([Xv, onehot], format="csr")
        return sparse.hstack([Xv - self.vec.transform(refs), Xv, onehot], format="csr")

    def _proba(self, model, Xt) -> np.ndarray:
        if isinstance(model, float):
            return np.full(Xt.shape[0], model)
        return model.predict_proba(Xt)[:, 1]

    def _scored_design(self, scored: pd.DataFrame):
        return self._design(_parse_rows(scored)[0], parse_references(scored) if self.pairwise else [], scored["cell"].to_numpy())

    def raw_p_sig(self, scored: pd.DataFrame, s_star, X_cache=None) -> np.ndarray:
        """``p_sig`` of every scored row (what the recalibration map is applied to)."""
        return self._proba(self._models[1], self._scored_design(scored))

    def oof_probabilities(self, max_rows: int = CALIBRATION_MAX_ROWS, n_folds: int = GBM_FOLDS, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
        """``(p_sig, event)`` of a subsample of the visible rows, each predicted by a classifier fit on the other time folds."""
        from sklearn.linear_model import LogisticRegression

        label = self._labels[1]
        n = len(label)
        order = np.argsort(self._rows["started_at"].to_numpy(), kind="stable")
        p = np.full(n, np.nan)
        for train, test in time_folds(n, n_folds):
            tr, te = order[train], order[test]
            if label[tr].all() or not label[tr].any():
                p[te] = float(label[tr].mean())
            else:
                p[te] = LogisticRegression(C=1.0, max_iter=500, random_state=self._seed).fit(self._X[tr], label[tr]).predict_proba(self._X[te])[:, 1]
        pick = np.arange(n)
        if n > max_rows:
            pick = np.sort(np.random.default_rng(seed).choice(n, max_rows, replace=False))
        return p[pick], label[pick].astype(float)

    def score_block(self, scored: pd.DataFrame, y, s_star, origin, X_cache=None):
        """``(columns, keep)``: ``p_sig`` and ``p_win`` (the direction probability) with NaN where a rung has nothing to say."""
        n = len(scored)
        Xt = self._scored_design(scored)
        p_dir, p_sig = self._proba(self._models[0], Xt), self._proba(self._models[1], Xt)
        nan = np.full(n, np.nan)
        cols = {k: nan.copy() for k in ("logscore", "crps", "lo80", "hi80", "lo90", "hi90")}
        cols.update(p_sig=p_sig, p_win=p_dir, p_gt0=p_dir, point=p_dir - 0.5)           # only the sign of the point is used
        return cols, np.ones(n, bool)


class Recalibrated:
    """A challenger's significant-positive probability through a monotone map fit on the visible rows only (``recalibration.py``).

    The map is fit on the inner model's out-of-fold predictions for the rows visible at the origin against their events, so
    nothing from the scored rows reaches it. Only ``p_sig`` is reported: the density columns, the direction and the win
    probability are left empty, because the raw rung already carries them and a monotone map does not change a ranking.
    """

    def __init__(self, inner, method: str = "platt"):
        p, event = inner.oof_probabilities()
        self.inner = inner
        self.calibrator = Calibrator(method).fit(p, event)
        self.n_fit = self.calibrator.n_fit

    def score_block(self, scored: pd.DataFrame, y, s_star, origin, X_cache=None):
        n = len(scored)
        nan = np.full(n, np.nan)
        cols = {k: nan.copy() for k in ("logscore", "crps", "lo80", "hi80", "lo90", "hi90", "p_win", "p_gt0", "point")}
        cols["p_sig"] = self.calibrator.transform(self.inner.raw_p_sig(scored, np.asarray(s_star, dtype=float), X_cache))
        return cols, np.ones(n, bool)


class DirectionBaseline:
    """Predict that the reference arm always wins, or that the variant always does. Direction accuracy only.

    The earliest-created arm is the reference, so ``always_reference`` measures the creation-order effect the archive
    carries: how often the arm that was created first ends up ahead. ``always_variant`` is its complement.
    """

    def __init__(self, reference_wins: bool):
        self.reference_wins = reference_wins

    def score_block(self, scored: pd.DataFrame, y, s_star, origin, X_cache=None):
        n = len(scored)
        nan = np.full(n, np.nan)
        cols = {k: nan.copy() for k in ("logscore", "crps", "lo80", "hi80", "lo90", "hi90", "p_sig", "p_win", "p_gt0")}
        cols["point"] = np.full(n, -1.0 if self.reference_wins else 1.0)
        return cols, np.ones(n, bool)


CHALLENGERS = ("gbm", "local_eb", "text_lr")
RECAL_SUFFIX = "+cal"
PRIOR_KINDS = ("t", "normal")


def parse_challengers(challenger) -> list[str]:
    """Challenger names from None, one name, a comma-separated string or a list of those; unknown names raise ValueError."""
    if challenger is None:
        return []
    items = [challenger] if isinstance(challenger, str) else list(challenger)
    names = [n.strip() for it in items for n in str(it).split(",") if n.strip()]
    bad = [n for n in names if n not in CHALLENGERS]
    if bad:
        raise ValueError(f"unknown challenger {bad}; the challengers are {', '.join(CHALLENGERS)}")
    return list(dict.fromkeys(names))


def default_rungs(source: str, ledger: pd.DataFrame | None = None, challenger=None, *, features: str = "both",
                  bandwidth_mult: float | None = None, lam: float | None = None, kappa: float = KAPPA, prior: str = "t",
                  p2_selection: str | None = None, recency: str | float | None = None, local_k: int = LOCAL_EB_K,
                  baselines: bool = False, p2_guard: float | None = P2_GUARD_MULT, recalibrate: bool = False,
                  recalibration: str = "platt", gbm_tuned: bool = True, pairwise: bool | None = None) -> dict[str, Callable]:
    """Rung factories ``factory(rows, origin)``: P0, P1, P2, P3 when the ledger has team forecasts, then challengers.

    ``challenger`` is a name, a comma-separated string or a list from ``CHALLENGERS`` (gbm, local_eb, text_lr).
    ``baselines`` adds the two direction baselines. The keyword arguments are the ablation switches: ``features``
    (``text``, ``structured`` or ``both``), a fixed ``bandwidth_mult`` and ``lam`` for P2, the P1 pooling strength
    ``kappa``, the P1 ``prior`` (``t`` or ``normal``), and P2's ``p2_selection``, ``recency`` and ``p2_guard`` (the admission
    guard multiplier, None for no guard). With ``recalibrate`` every challenger also gets a recalibrated rung (``GBM+cal`` and so on; the
    ``moot backtest`` command turns it on by default); ``recalibration`` is ``platt`` or ``isotonic`` and ``gbm_tuned`` False restores
    the untuned GBM.
    ``pairwise`` None reads the reference headline where the rows carry one (the default), ``False`` is the single-headline space of earlier versions.
    """
    names = parse_challengers(challenger)
    if features not in FEATURE_SETS:
        raise ValueError(f"features must be one of {FEATURE_SETS}")
    if prior not in PRIOR_KINDS:
        raise ValueError(f"prior must be one of {PRIOR_KINDS}")
    if p2_selection is not None and p2_selection not in P2_SELECTIONS:
        raise ValueError(f"p2_selection must be one of {P2_SELECTIONS}")
    cell_only = use_cell_only(source, ledger[ledger["source"] == source] if ledger is not None and "source" in ledger else ledger)
    if "text_lr" in names and cell_only:
        raise ValueError("text_lr needs headline text and this source has none")
    nu_grid = (math.inf,) if prior == "normal" else NU_GRID
    shared = _Shared()

    def p1_of(rows, origin):
        return shared.get("p1", rows, origin, lambda: P1Predictor(kappa=kappa, nu_grid=nu_grid).fit(rows, data_end=origin))

    def space_of(rows, origin):
        return shared.get("space", rows, origin, lambda: FeatureSpace.fit(rows, cell_only=cell_only, feature_set=features, pairwise=pairwise))

    def p0(rows, origin):
        return P0Predictor().fit(rows)

    def p2(rows, origin):
        return P2Predictor().fit(rows, space_of(rows, origin), p1_of(rows, origin), lambda_override=lam, selection=p2_selection,
                                 recency=recency, bandwidth_override=bandwidth_mult, guard=p2_guard)

    rungs: dict[str, Callable] = {"P0": p0, "P1": lambda rows, origin: p1_of(rows, origin), "P2": p2}
    if ledger is not None and has_team_forecasts(ledger):
        rungs["P3"] = lambda rows, origin: TeamModel(rows)
    if recalibration not in RECAL_METHODS:
        raise ValueError(f"recalibration must be one of {RECAL_METHODS}")

    def gbm_of(rows, origin):
        return shared.get("gbm", rows, origin, lambda: GBMChallenger(space_of(rows, origin), rows, tuned=gbm_tuned))

    def local_of(rows, origin):
        return shared.get("local_eb", rows, origin, lambda: LocalEB(space_of(rows, origin), rows, k=local_k))

    def text_of(rows, origin):
        return shared.get("text_lr", rows, origin, lambda: TextLR(rows, pairwise=pairwise))

    if "gbm" in names:
        rungs["GBM"] = gbm_of
        if recalibrate:
            rungs["GBM" + RECAL_SUFFIX] = lambda rows, origin: Recalibrated(gbm_of(rows, origin), recalibration)
    if "local_eb" in names:
        rungs["local_eb"] = local_of
        if recalibrate:
            rungs["local_eb" + RECAL_SUFFIX] = lambda rows, origin: Recalibrated(local_of(rows, origin), recalibration)
    if "text_lr" in names:
        rungs["text_lr"] = text_of
        if recalibrate:
            rungs["text_lr" + RECAL_SUFFIX] = lambda rows, origin: Recalibrated(text_of(rows, origin), recalibration)
    if baselines:
        rungs["always_reference"] = lambda rows, origin: DirectionBaseline(reference_wins=True)
        rungs["always_variant"] = lambda rows, origin: DirectionBaseline(reference_wins=False)
    return rungs


# ------------------------------------------------------------------ scoring
def _chunks(n: int, size: int):
    for a in range(0, n, size):
        yield slice(a, min(a + size, n))


def ystar_intervals(pred: Predictive, s, levels=(0.8, 0.9), points: int = INTERVAL_POINTS) -> dict[float, tuple[np.ndarray, np.ndarray]]:
    """Central intervals of y* = theta + Normal(0, s^2) for each ``s``, from one cdf evaluation per row.

    The cdf of y* is evaluated on ``points`` points spanning the theta support widened by four ``s`` each way,
    on the grid columns that carry mass, and inverted by linear interpolation. This replaces one 2G-point
    cdf per quantile and agrees with ``Predictive.interval(level, s)`` to well under 1 percent of the
    spread (checked in the tests).
    """
    s = np.atleast_1d(np.asarray(s, dtype=np.float64))
    keep = pred.pmf > 1e-12
    th, w = pred.theta[keep], pred.pmf[keep]
    w = w / w.sum()
    q_lo, q_hi = pred.quantile(1e-3), pred.quantile(1.0 - 1e-3)
    qs = sorted({q for lv in levels for q in ((1 - lv) / 2, 1 - (1 - lv) / 2)})
    out = np.empty((len(qs), len(s)))
    for sl in _chunks(len(s), 16):
        sc = s[sl]
        t = np.linspace(q_lo - 4.0 * sc, q_hi + 4.0 * sc, points, axis=-1)          # (c, points)
        cdf = special.ndtr((t[:, :, None] - th[None, None, :]) / sc[:, None, None]) @ w
        for r in range(len(sc)):
            out[:, sl.start + r] = np.interp(qs, np.maximum.accumulate(cdf[r]), t[r])
    pos = {q: i for i, q in enumerate(qs)}
    return {lv: (out[pos[(1 - lv) / 2]], out[pos[1 - (1 - lv) / 2]]) for lv in levels}


def score_rows(pred: Predictive, y, s, p_gt0=None) -> dict[str, np.ndarray]:
    """Row scores of one predictive against realized ``y`` (array) with standard errors ``s`` (array).

    Returns logscore, crps, p_sig, p_win, point, p_gt0, interval limits and the event ``y > Z s``.
    """
    y, s = np.atleast_1d(np.asarray(y, float)), np.atleast_1d(np.asarray(s, float))
    n = len(y)
    ls, cr = np.empty(n), np.empty(n)
    p_sig, gt0 = np.empty(n), np.empty(n)
    for sl in _chunks(n, 512):
        ls[sl], cr[sl] = pred.logscore(y[sl], s[sl]), pred.crps(y[sl], s[sl])
        p_sig[sl], gt0[sl] = pred.p_sig(s[sl]), pred.p_sig(s[sl], z=0.0)
    iv = ystar_intervals(pred, s)
    if p_gt0 is not None:
        gt0 = np.full(n, float(p_gt0))
    return {
        "logscore": ls, "crps": cr, "p_sig": p_sig, "p_win": np.full(n, pred.p_win(0.0)), "point": np.full(n, pred.mean()),
        "p_gt0": gt0, "lo80": iv[0.8][0], "hi80": iv[0.8][1], "lo90": iv[0.9][0], "hi90": iv[0.9][1],
    }


def posterior_floor(rows: pd.DataFrame, p1: P1Predictor, origin) -> dict[str, np.ndarray]:
    """Per-row floor ingredients from the shrunken posterior of theta given the row's own ``y`` and ``s``.

    Prior: Normal(mu, sd) with the pooled P1 parameters of the row's cell at the origin (the t prior is
    replaced by its standard-deviation equivalent). Posterior Normal(m, v) by conjugacy. By Gauss-Hermite
    quadrature over the posterior: ``p_theta_posterior = E[Phi(theta/s - Z)]`` (the chance an estimate of
    this row would be significant and positive), ``brier_floor_row = E[p_theta (1 - p_theta)]`` (the Brier
    score no forecaster can beat on this row) and ``dir_ceiling_row = E[Phi(|theta| / s)]`` (the best
    expected direction accuracy).
    """
    qlabel = quarter_of(origin)
    y, s = rows["y"].to_numpy(float), rows["s"].to_numpy(float)
    mu, sd = np.empty(len(rows)), np.empty(len(rows))
    cache: dict[str, tuple[float, float]] = {}
    for i, c in enumerate(rows["cell"].tolist()):
        if c not in cache:
            par = p1.cell_params(c, qlabel)
            cache[c] = (par["mu"], sd_equivalent(par["tau"], par["nu"]))
        mu[i], sd[i] = cache[c]
    prec = 1.0 / sd ** 2 + 1.0 / s ** 2
    v = 1.0 / prec
    m = (mu / sd ** 2 + y / s ** 2) * v
    theta = m[:, None] + np.sqrt(2.0 * v)[:, None] * _GH_NODES[None, :]
    w = _GH_WEIGHTS / np.sqrt(np.pi)
    p_theta = special.ndtr(theta / s[:, None] - Z)
    return {
        "p_theta_posterior": p_theta @ w,
        "brier_floor_row": (p_theta * (1.0 - p_theta)) @ w,
        "dir_ceiling_row": special.ndtr(np.abs(theta) / s[:, None]) @ w,
    }


def _outcomes_for_reliability(blocks: list[pd.DataFrame], rel_rung: str, t) -> pd.DataFrame:
    """Outcomes known at ``t`` (``usable_after <= t``) from earlier origins, in the reliability schema."""
    cols = ["cell", "at", "logscore", "p0_logscore", "brier", "p0_brier", "test_id"]
    if not blocks:
        return pd.DataFrame({c: [] for c in cols})
    allr = pd.concat(blocks, ignore_index=True)
    main = allr[allr["rung"] == rel_rung]
    base = allr[allr["rung"] == "P0"].set_index("row_id")["logscore"] if (allr["rung"] == "P0").any() else None
    main = main[main["usable_after"] <= t]
    p0_ls = main["logscore"].to_numpy() if base is None else base.reindex(main["row_id"]).to_numpy()
    return pd.DataFrame({"cell": main["cell"].to_numpy(), "at": main["usable_after"].to_numpy(), "logscore": main["logscore"].to_numpy(),
                         "p0_logscore": p0_ls, "brier": main["brier_event"].to_numpy(), "p0_brier": main["brier_base"].to_numpy(),
                         "test_id": main["test_id"].to_numpy()})


@dataclass
class _Abstain:
    flags: np.ndarray
    reasons: list[str]


def rolling_origin(
    ledger: pd.DataFrame,
    predictors: dict[str, Callable],
    origins,
    *,
    audit_fit_rows: bool = True,
    min_fit_rows: int = MIN_FIT_ROWS,
    reliability_rung: str | None = None,
    abstain_config: AbstainConfig | None = None,
    source: str | None = None,
    verbose: bool = False,
    s_star_mode: str = "prelaunch",
    drop_triggers=(),
    progress: Callable[[str], None] | None = None,
) -> pd.DataFrame:
    """Score every admitted row once per rung, at the origin whose quarter it starts in.

    ``progress`` (a callable taking one line) is told of each origin as it is fitted, whatever ``verbose`` says (call 207).

    ``predictors`` maps a rung name to ``factory(rows, origin)`` returning a fitted model with
    ``predict(x, s_star, cell, origin)`` (and a ``space`` attribute when it needs features), or
    ``predict_row`` for row-aware models. Returns the per-row score table (``SCORE_COLUMNS`` plus
    ``EXTRA_COLUMNS``); ``frame.attrs`` carries ``skipped_origins`` (origins with fewer than
    ``min_fit_rows`` visible rows, where nothing could be fitted).

    ``audit_fit_rows`` wraps the model ``fit`` methods during factory calls (see module docstring).

    ``drop_triggers`` names abstention triggers to switch off for the run (the trigger-removal ablation): a dropped trigger is
    never evaluated, adds no reason and cannot flag a row, while the others are computed exactly as before. Predictions, scores and
    the reliability report do not depend on abstention, so only the abstention columns change. ``frame.attrs["dropped_triggers"]``
    lists them.
    """
    if s_star_mode not in ("prelaunch", "realized"):
        raise ValueError("s_star_mode must be prelaunch or realized")
    cfg = abstain_config or AbstainConfig()
    if drop_triggers:
        cfg = dataclasses.replace(cfg, disabled=frozenset(cfg.disabled) | frozenset(drop_triggers))
    adm = ledger.loc[ledger["status"] == ADMITTED]
    origins = sorted(to_utc(o) for o in origins)
    if not origins:
        raise ValueError("no origins")
    ends = origins[1:] + [origins[-1] + pd.DateOffset(months=3)]
    rel_rung = reliability_rung or ("P2" if "P2" in predictors else list(predictors)[-1])
    src = source or (str(ledger["source"].iloc[0]) if len(ledger) else "")
    blocks: list[pd.DataFrame] = []
    skipped, prev_report, selections = [], None, []
    for t, t_next in zip(origins, ends):
        scored = adm[(adm["started_at"] >= t) & (adm["started_at"] < t_next)].reset_index(drop=True)
        if scored.empty:
            continue
        visible = visible_rows(adm, t)
        if len(visible) < min_fit_rows:
            skipped.append(t)
            continue
        assert_no_leakage(visible, scored, t)
        spying = _audit_fits(t) if audit_fit_rows else contextlib.nullcontext()
        with spying:
            models = {name: factory(visible, t) for name, factory in predictors.items()}
        line = f"origin {t.date()}: fitted {list(models)} on {len(visible)} rows, scoring {len(scored)}"
        if verbose:
            print(line, file=sys.stderr)
        if progress is not None:
            progress(line)
        for name, m in models.items():
            if hasattr(m, "selection_summary"):
                selections += [{"origin": t.isoformat(), "rung": name, **rec} for rec in m.selection_summary()]

        n_cell = visible.groupby("cell").size()
        n_vis = scored["cell"].map(n_cell).fillna(0).astype(int).to_numpy()
        y, s = scored["y"].to_numpy(float), scored["s"].to_numpy(float)
        event = y > Z * s                                   # the realized s defines the event and nothing else
        # What is known before launch drives every predictor. "realized" feeds the realized standard error instead, which is
        # in-test information; it exists only to reproduce the cautionary first run (--s-star realized).
        s_star = np.array(s, copy=True) if s_star_mode == "realized" else scale.s_star_rows(scored, visible)
        expo = scale.planned_exposure(scored)
        metric_ids = np.array([metric_of(j) for j in scored["features_json"]], dtype=object)

        p1 = next((m for m in models.values() if isinstance(m, P1Predictor)), None) or P1Predictor().fit(visible, data_end=t)
        p0m = next((m for m in models.values() if isinstance(m, P0Predictor)), None) or P0Predictor().fit(visible)
        floor = posterior_floor(scored, p1, t)
        base_by_cell = {c: p0m.sig_positive_frequency(c, t) for c in scored["cell"].unique()}
        p_base = scored["cell"].map(base_by_cell).to_numpy(float)
        # The sensitivity event of review R5: significant on the PLANNED standard error (y > z s_star) instead of the realized one. The
        # forecast p_sig is the same number; P0's forecast for this event is the visible rate of the same event (its own definition), so its
        # skill is zero here too. The visible rows' planned standard errors are the pre-launch ones computed from the visible set.
        event_planned = y > Z * s_star
        p_base_planned = _planned_event_base(visible, scored, s_star_mode)

        outcomes = _outcomes_for_reliability(blocks, rel_rung, t)
        if prev_report is not None or len(outcomes):
            prev_report = build_reliability(prev_report, outcomes, t.to_pydatetime(), advance=True, source=src)
        report = prev_report

        card_model = models.get("P2") if hasattr(models.get("P2"), "neighbor_state") else next(
            (m for m in models.values() if hasattr(m, "neighbor_state")), None)
        X_by_model: dict[int, np.ndarray] = {}
        abstain: _Abstain | None = None
        per_rung: dict[str, dict[str, np.ndarray]] = {}
        keep_rows: dict[str, np.ndarray] = {}
        for name, m in models.items():
            cols, keep, ab = _score_rung(m, name, scored, y, s_star, t, X_by_model, card_model, report, n_vis, cfg)
            per_rung[name], keep_rows[name] = cols, keep
            if ab is not None:
                abstain = ab
        if abstain is None:
            abstain = _basic_abstain(scored, n_vis, report, t, cfg)

        for name, cols in per_rung.items():
            keep = keep_rows[name]
            idx = np.flatnonzero(keep)
            frame = pd.DataFrame({
                "row_id": scored["row_id"].to_numpy()[idx], "test_id": scored["test_id"].to_numpy()[idx],
                "cell": scored["cell"].to_numpy()[idx], "period": scored["period"].to_numpy()[idx],
                "origin": t, "rung": name, "y": y[idx], "s": s[idx], "s_star": s_star[idx], "exposure": expo[idx],
                "logscore": cols["logscore"], "crps": cols["crps"], "p_sig": cols["p_sig"], "p_win": cols["p_win"],
                "brier_event": (cols["p_sig"] - event[idx]) ** 2, "event": event[idx],
                "direction_correct": _direction_correct(cols["point"], y[idx]),
                "lo80": cols["lo80"], "hi80": cols["hi80"], "lo90": cols["lo90"], "hi90": cols["hi90"],
                "abstain": abstain.flags[idx], "abstain_reasons": [abstain.reasons[i] for i in idx],
                "p_theta_posterior": floor["p_theta_posterior"][idx], "fallback_global": n_vis[idx] < 2,
                "usable_after": scored["usable_after"].to_numpy()[idx], "point": cols["point"], "p_gt0": cols["p_gt0"],
                "event_pos": y[idx] > 0, "brier_pos": (cols["p_gt0"] - (y[idx] > 0)) ** 2, "p_base": p_base[idx],
                "brier_base": (p_base[idx] - event[idx]) ** 2, "brier_floor_row": floor["brier_floor_row"][idx],
                "dir_ceiling_row": floor["dir_ceiling_row"][idx], "n_visible_cell": n_vis[idx],
            })
            p_plan = p_base_planned[idx] if isinstance(models[name], P0Predictor) else cols["p_sig"]
            frame["event_planned"] = event_planned[idx]
            frame["brier_planned"] = (p_plan - event_planned[idx]) ** 2
            frame["p_base_planned"] = p_base_planned[idx]
            frame["brier_base_planned"] = (p_base_planned[idx] - event_planned[idx]) ** 2
            if metric_ids.any():                      # the column exists only for multi-metric ledgers: the single-metric table is unchanged
                frame["metric"] = metric_ids[idx]
            blocks.append(frame)
    out = pd.concat(blocks, ignore_index=True) if blocks else pd.DataFrame(columns=SCORE_COLUMNS + EXTRA_COLUMNS)
    if out["direction_correct"].dtype == object:        # rungs without a point estimate leave NaN beside the booleans
        out["direction_correct"] = out["direction_correct"].astype(float)
    out["usable_after"] = pd.to_datetime(out["usable_after"], utc=True)
    out.attrs["skipped_origins"] = [t.isoformat() for t in skipped]
    out.attrs["dropped_triggers"] = sorted(cfg.disabled)
    out.attrs["selections"] = selections
    return out


def _planned_event_base(visible: pd.DataFrame, scored: pd.DataFrame, s_star_mode: str) -> np.ndarray:
    """Per scored row, the share of the visible rows of its cell with ``y > z s_star`` (the planned-standard-error event), the share over all
    visible rows where the cell has fewer than two. The visible rows' ``s_star`` is the pre-launch one computed from the visible set."""
    s_vis = np.array(visible["s"].to_numpy(float), copy=True) if s_star_mode == "realized" else scale.s_star_rows(visible, visible)
    ev = pd.Series(visible["y"].to_numpy(float) > Z * s_vis, index=visible.index).astype(float)
    cells = visible["cell"].to_numpy()
    glob = float(ev.mean()) if len(ev) else float("nan")
    by_cell = {c: (float(ev[cells == c].mean()) if (cells == c).sum() >= 2 else glob) for c in np.unique(cells)}
    return scored["cell"].map(lambda c: by_cell.get(c, glob)).to_numpy(float)


def _direction_correct(point, y) -> np.ndarray:
    """Whether the sign of the point estimate matches the sign of ``y``; NaN where a rung has no point estimate."""
    point = np.asarray(point, float)
    ok = (point > 0) == (np.asarray(y) > 0)
    finite = np.isfinite(point)
    return ok if finite.all() else np.where(finite, ok, np.nan)


def _basic_abstain(scored, n_vis, report, t, cfg) -> _Abstain:
    """Support and reliability only, for runs without a retrieval rung (novelty and instability need P2)."""
    flags, reasons = np.zeros(len(scored), bool), []
    now = t.to_pydatetime()
    for i, c in enumerate(scored["cell"].tolist()):
        r = []
        if cfg.enabled("support") and check_support(int(n_vis[i]), cfg):
            r.append("support")
        if cfg.enabled("reliability") and reliability_reason(report, c, now, cfg) is not None:
            r.append("reliability")
        flags[i] = bool(r)
        reasons.append(",".join(r))
    return _Abstain(flags, reasons)


def _score_rung(m, name, scored, y, s, t, X_cache, card_model, report, n_vis, cfg):
    """Scores of one fitted rung on the scored rows. Returns (columns, keep mask, abstention or None).

    Models with a ``space`` get a feature matrix and are scored row by row; models with ``predict_row`` get
    each row; everything else is x-independent and scored once per cell in a vectorized block. The model
    carrying ``neighbor_state`` (P2) also produces the abstention decision, so its neighbor search is reused.
    """
    n = len(scored)
    names = ["logscore", "crps", "p_sig", "p_win", "point", "p_gt0", "lo80", "hi80", "lo90", "hi90"]
    if hasattr(m, "score_block"):
        cols, keep = m.score_block(scored, y, s, t, X_cache)
        return cols, keep, None
    if hasattr(m, "predict_row"):
        parts, keep = [], np.zeros(n, bool)
        for i, row in enumerate(scored.itertuples(index=False)):
            got = m.predict_row(row, s[i], t)
            if got is None:
                continue
            pred, extra = got
            parts.append(score_rows(pred, y[i:i + 1], s[i:i + 1], p_gt0=extra.get("p_gt0")))
            keep[i] = True
        cols = {k: (np.concatenate([p[k] for p in parts]) if parts else np.zeros(0)) for k in names}
        return cols, keep, None
    space = getattr(m, "space", None)
    keep = np.ones(n, bool)
    if space is None:
        cols = {k: np.empty(n) for k in names}
        cells = scored["cell"].to_numpy()
        for c in np.unique(cells):
            idx = np.flatnonzero(cells == c)
            pred = m.predict(None, float(np.median(s[idx])), c, t)
            sc = score_rows(pred, y[idx], s[idx])
            for k in names:
                cols[k][idx] = sc[k]
        return cols, keep, None
    key = id(space)
    if key not in X_cache:
        X_cache[key] = space.transform(scored)
    X = X_cache[key]
    cols = {k: np.empty(n) for k in names}
    is_card = m is card_model
    flags, reasons = np.zeros(n, bool), [""] * n
    now = t.to_pydatetime()
    for i in range(n):
        c = scored["cell"].iat[i]
        if hasattr(m, "neighbor_state") and hasattr(m, "predictive_from_state"):
            state = m.neighbor_state(X[i], c, t)
            pred = m.predictive_from_state(state, X[i], s[i], c, t)
        else:
            state, pred = None, m.predict(X[i], s[i], c, t)
        sc = score_rows(pred, y[i:i + 1], s[i:i + 1])
        for k in names:
            cols[k][i] = sc[k][0]
        if is_card:
            d = decide(n_support=int(n_vis[i]), density=m.density(X[i], c, t), density_threshold=m.novelty_threshold(c),
                       reliability_report=report, cell=c, now=now, neighbor_state=state if (state is not None and len(state.row_ids)) else None,
                       s_star=float(s[i]), config=cfg)
            flags[i], reasons[i] = d.status == "abstain", ",".join(d.reasons)
    return cols, keep, (_Abstain(flags, reasons) if is_card else None)
