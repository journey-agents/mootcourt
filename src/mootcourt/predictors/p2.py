"""P2 weighted precedents with an out-of-origin lambda.

For a query ``x`` in a cell, with kernel ``k_i = k(x, x_i)`` over the cell's rows visible at the origin
(status admitted and ``usable_after <= origin``) and the P1 cell prior ``(mu_c, tau_c)``:

    w_i     = k_i / (s_i^2 + tau_c^2)
    m       = sum w_i y_i / sum w_i
    v_m     = sum w_i^2 (s_i^2 + tau_c^2) / (sum w_i)^2
    n_eff   = (sum w_i)^2 / sum w_i^2
    theta^  = lam m + (1 - lam) mu_c
    v       = lam (v_m + tau_res^2) + (1 - lam) tau_c^2

and the working predictive is ``theta ~ t(theta^, scale, nu)`` placed on the grid, the SAME family as P1 with the cell's fitted
degrees of freedom ``nu`` (round 00, docs/method.md call 161), moment matched: ``scale = sqrt(v (nu - 2) / nu)``, so the theta variance
is ``v`` as before and ``lam = 0`` gives ``scale = tau`` of P1 exactly. At every lam the lambda ablation therefore varies the
precedent weighting only, not the distribution family; the earlier Normal mixture is gone. With ``lam = 0`` the predictive is exactly
P1's grid, so ``predict`` returns P1's prediction.
Units: ``y``, ``s``, ``tau``, ``mu`` and ``theta^`` are in the units of y; ``v`` and ``tau_res^2`` are
squared. ``tau_c`` is P1's cell prior expressed as a standard deviation (for a Student-t prior,
``tau sqrt(nu / (nu - 2))``), so that ``tau_c^2`` is a variance.

Choosing lam and tau_res^2 (documented builder calls; the log score of a candidate is that of the t predictive it would issue, the
marginal density of y given theta ~ t(theta^_i, scale_i, nu) and y | theta ~ Normal(theta, s_i^2), so the lam = 0 baseline is
P1's actual predictive and not a Normal stand-in)
* Leave-one-TEST-out. Contrasts of one test share a reference arm and similar text, so a row is scored
  with every row of its own test removed. ``leave_out="row"`` removes only the row itself and is kept
  to show that it leaks (it rewards lam near 1).
* ``m_{-i}``, ``v_m,i`` do not depend on lam. ``tau_res^2 = max(0, mean(r^2) - mean(s^2) - mean(v_m))``
  with ``r_i = y_i - m_{-i}``. lam is the smallest value in {0, 0.1, ..., 1} whose mean log score of
  ``Normal(theta^_i, v_i + s_i^2)`` at ``y_i`` is within 0.001 nats of the best (a flat curve means the
  precedents add nothing, so the smaller lam wins). P1 parameters are those of the
  most recent period, because the quarter being predicted never has history.

Admission guard (builder call 86, the ladder's admission rule made operational). The out-of-sample selection scores
roughly forty candidates (eleven lambdas times the bandwidths) on the same validation rows, and the best of many noisy
gains is biased upward: at two origins checked by hand the in-selection gain over lam 0 was 0.002 to 0.027 nats while
the loss on the next origin was 0.025 to 0.11 nats. A candidate with lam above zero is therefore admissible only when
its mean per-row log-score gain over lam 0 exceeds the tie tolerance and minus ``guard`` standard errors is above zero, the standard error being
cluster-robust over tests (rows of one test share a reference arm and are not independent). Among admissible
candidates the best gain wins (gains within the tie tolerance resolve to the smaller lam). With none admissible lam is 0
for that cell and origin and P2 equals P1. A rung is used only when it beats the rung below out of sample by more than
noise. The multiplier is ``config.P2_GUARD_MULT`` (2.0; one standard error admitted 39 percent of cells on data with no
precedent signal, see the comment there). ``guard=None`` switches the guard off and restores the earlier rule; ``lambda_override`` also bypasses it.

Bandwidth (documented builder call). The kernel bandwidth is the median heuristic ``h0`` times a multiplier
``c`` in {1, 1/2, 1/4, 1/8} chosen per cell, jointly with lam, by the same out-of-origin log score. In 72
standardized dimensions the median distance is nearly the typical distance, so ``c = 1`` gives a nearly flat
kernel that cannot tell neighbors from strangers; ``c = 1`` is the plain median heuristic and stays in the grid.
The leave-one-test-out statistics use at most 3000 query rows per cell (a fixed subsample), each against all
rows, which bounds the cost at 3000 by n distances.

Performance (documented builder call). A query lists only its top ``M = 1000`` neighbors by kernel weight (for
the card and the bootstrap), and the sums of the unlisted visible rows are kept as a tail, so the moments are
those of all visible precedents and truncation does not bias ``p_sig``.
The leave-one-test-out step never forms an n by n matrix: it works on a chunk of query rows by n at a time and
one distance pass serves the whole lambda and bandwidth grid. ``top_m=None`` lists all neighbors; a test
compares truncated and exact prediction on 2000 rows.

Origin semantics: rows are stored sorted by ``usable_after`` and a query at ``origin`` searches the
prefix of rows with ``usable_after <= origin``. The retrieval index is rebuilt at every fit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

from mootcourt.config import (
    BANDWIDTH_MULTIPLIERS,
    CV_MAX_QUERIES,
    FORWARD_CUT_QUANTILES,
    HALF_LIFE_DAYS,
    LAMBDA_GRID,
    NOVELTY_PERCENTILE,
    P2_GUARD_MULT,
    P2_SELECTION_DEFAULT,
    P2_SELECTIONS,
    TOP_M_NEIGHBORS,
    Z,
)
from mootcourt.features import FeatureSpace, Index, density, median_bandwidth, sq_dists
from mootcourt.ledger import ADMITTED, quarter_of, series_ns, timestamp_ns
from mootcourt.predictors.base import Predictive, build_grid
from mootcourt.predictors.p1 import P1Predictor, marginal_logpdf_rows, p_sig_t, scale_from_sd, sd_equivalent

_CHUNK = 256
_F32_SMALLEST = float(np.finfo(np.float32).smallest_subnormal)   # below this the float32 kernel of the fit-time validation is exactly zero
_SD_FLOOR = 1e-9
_MIN_CV_ROWS = 5
_LAMBDA_TIE = 1e-3  # nats of mean log score below which two lambdas are treated as tied


@dataclass(frozen=True)
class Moments:
    """P2 moments for one query (all in units of y or y squared)."""

    m: float
    v_m: float
    n_eff: float
    theta_hat: float
    v: float


def p2_moments(kernel, y, s, tau: float, mu: float, lam: float, tau_res2: float, tail=(0.0, 0.0, 0.0, 0.0)) -> Moments:
    """Weights and moments of spec section 8 for the given neighbors.

    ``kernel`` are kernel weights in (0, 1]; ``y`` and ``s`` the precedents' effects and standard
    errors; ``tau`` and ``mu`` the cell prior; ``lam`` in [0, 1]. ``tail`` holds the sums
    ``(sum w, sum w y, sum w^2 (s^2 + tau^2), sum w^2)`` of precedents that are not listed (the part of
    the visible rows beyond the top M), so the moments are those of all visible precedents.
    Raises ValueError for no precedents, negative weights or a zero total weight.
    """
    k = np.asarray(kernel, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    s = np.asarray(s, dtype=np.float64)
    if k.size == 0 and tail[0] == 0.0:
        raise ValueError("P2 needs at least one precedent")
    if np.any(k < 0):
        raise ValueError("kernel weights must be nonnegative")
    var = s * s + tau * tau
    w = k / var
    sw = w.sum() + tail[0]
    if not sw > 0:
        raise ValueError("total precedent weight is zero")
    m = float(((w * y).sum() + tail[1]) / sw)
    v_m = float(((w * w * var).sum() + tail[2]) / (sw * sw))
    n_eff = float(sw * sw / ((w * w).sum() + tail[3]))
    return Moments(m, v_m, n_eff, lam * m + (1.0 - lam) * mu, lam * (v_m + tau_res2) + (1.0 - lam) * tau * tau)


@dataclass
class NeighborState:
    """Top-M neighbors of one query plus the cell parameters, for the card and the bootstrap."""

    row_ids: tuple
    kernel: np.ndarray
    y: np.ndarray
    s: np.ndarray
    test_ids: tuple
    mu: float
    tau: float
    lam: float
    tau_res2: float
    tail: tuple = (0.0, 0.0, 0.0, 0.0)
    nu: float = math.inf                  # degrees of freedom of the cell's P1 prior (infinite is the Normal)

    def moments(self) -> Moments:
        """P2 moments of this state, including the unlisted tail."""
        return p2_moments(self.kernel, self.y, self.s, self.tau, self.mu, self.lam, self.tau_res2, self.tail)

    def without(self, dismissed) -> NeighborState:
        """A copy with the named precedents removed."""
        drop = set(dismissed)
        keep = np.array([r not in drop for r in self.row_ids], dtype=bool)
        return replace(
            self,
            row_ids=tuple(r for r, k in zip(self.row_ids, keep) if k),
            kernel=self.kernel[keep], y=self.y[keep], s=self.s[keep],
            test_ids=tuple(t for t, k in zip(self.test_ids, keep) if k),
        )


def p_sig_from_state(st: NeighborState, s_star: float, z: float = Z) -> float:
    """P(y* > z s*) for the working t predictive of a state, by the scale-mixture form (no grid involved).

    ``theta ~ t(theta^, scale, nu)`` with variance ``v``; for an infinite ``nu`` this is the Normal closed form
    ``y* ~ Normal(theta^, v + s*^2)``. ``s_star`` is in the units of y.
    """
    mo = st.moments()
    return float(p_sig_t(mo.theta_hat, mo.v, st.nu, s_star, z))


class _CellData:
    """Retrieval data of one cell, sorted by usable_after."""

    def __init__(self, X, y, s, row_ids, test_ids, usable_ns, h, start_ns=None):
        self.X, self.y, self.s = X, y, s
        self.sq = np.einsum("ij,ij->i", X, X)
        self.row_ids, self.test_ids, self.usable_ns, self.h = row_ids, test_ids, usable_ns, h
        self.start_ns = start_ns          # start times, needed only while choosing hyperparameters (not stored in the bundle)
        self.novelty = float("-inf")

    def prefix(self, origin_ns: int) -> int:
        return int(np.searchsorted(self.usable_ns, origin_ns, side="right"))


_NS_PER_DAY = 86_400e9


def _half_life_factor(age_days: np.ndarray, half_life: float) -> np.ndarray | float:
    """Recency weight ``2 ** (-age / half_life)``; a half-life of infinity is no decay."""
    return 1.0 if math.isinf(half_life) else np.exp2(-age_days / half_life)


def _cv_cell(data: _CellData, codes: np.ndarray, tau: float, mults, leave_out: str, queries: np.ndarray,
             half_lives=(math.inf,), forward=None):
    """Hyperparameter statistics for query rows, for every bandwidth multiplier and half-life.

    Returns ``(stats, dens)``: ``stats[(c, hl)] = (m_{-i}, v_m,i, valid)`` and ``dens[c]`` the leave-one-out kernel
    density of each query row. All allowed neighbors enter the weights (the hyperparameters are chosen on exact
    weights; truncation to the top M applies to the neighbors stored for prediction), and only a chunk by n block of
    distances is alive at a time.

    Which neighbors are allowed depends on the rule. Leave-one-test-out (``forward=None``): every row except the
    query's own test; the recency age is measured from the query's start time. Forward chaining (``forward`` is a
    pair ``(block, cut_ns)``): a query in block ``b`` may use only rows with ``usable_after <= cut_ns[b]``, the
    precedents a fit at that inner cut would have had, and the age is measured from the cut, as at a real origin.
    """
    X, sq, y, s2 = data.X, data.sq, data.y, data.s ** 2
    n, nq = len(y), len(queries)
    h0 = data.h
    inv = {c: -1.0 / (2.0 * (c * h0) ** 2) for c in mults}
    keys = [(c, hl) for c in mults for hl in half_lives]
    stats = {k: (np.zeros(nq), np.zeros(nq), np.zeros(nq, dtype=bool)) for k in keys}
    dens = {c: np.zeros(nq) for c in mults}
    var_all = s2 + tau * tau
    use_age = any(not math.isinf(hl) for hl in half_lives)
    for a in range(0, nq, _CHUNK):
        q = queries[a:a + _CHUNK]
        rows = np.arange(len(q))
        d2 = X[q] @ X.T
        d2 *= -2.0
        d2 += sq[q, None]
        d2 += sq[None, :]
        np.maximum(d2, 0.0, out=d2)
        for c in mults:
            K = np.exp(d2 * np.float32(inv[c]))
            dens[c][a:a + len(q)] = (K.sum(axis=1, dtype=np.float64) - K[rows, q]) / max(n - 1, 1)
        d2[rows, q] = np.inf
        if leave_out == "test":
            d2[codes[q][:, None] == codes[None, :]] = np.inf
        if forward is not None:
            block, cut_ns = forward
            ref = cut_ns[block[a:a + len(q)]]
            d2[data.usable_ns[None, :] > ref[:, None]] = np.inf
        else:
            ref = data.start_ns[q] if (use_age and data.start_ns is not None) else None
        age = None
        if use_age:
            age = np.maximum((ref[:, None] - data.usable_ns[None, :]) / _NS_PER_DAY, 0.0)
        tw = {hl: _half_life_factor(age, hl) if age is not None else 1.0 for hl in half_lives}
        finite = np.isfinite(d2)
        dz = np.where(finite, d2, 0.0)
        vv, yy = var_all[None, :], y[None, :]
        for c in mults:
            with np.errstate(over="ignore", invalid="ignore"):
                Kt = np.exp(dz * np.float32(inv[c])).astype(np.float64)
            Kt[~finite] = 0.0
            for hl in half_lives:
                w = Kt * tw[hl] / vv
                sw = w.sum(axis=1)
                ok = sw > 0
                safe = np.where(ok, sw, 1.0)
                m_, vm_, valid_ = stats[(c, hl)]
                m_[a:a + len(q)] = (w * yy).sum(axis=1) / safe
                vm_[a:a + len(q)] = (w * w * vv).sum(axis=1) / (safe * safe)
                valid_[a:a + len(q)] = ok
    return stats, dens


def gain_and_se(gain: np.ndarray, codes: np.ndarray) -> tuple[float, float]:
    """Mean of per-row ``gain`` and its standard error clustered by test ``codes`` (infinite with fewer than two tests).

    The ratio-mean estimator: the variance is ``T / (T - 1) * sum_t (G_t - gbar n_t)^2 / n^2`` with ``G_t`` the sum of the
    gains of test ``t`` and ``n_t`` its rows.
    """
    n = len(gain)
    if n == 0:
        return 0.0, math.inf
    gbar = float(np.mean(gain))
    _, inv = np.unique(codes, return_inverse=True)
    t = int(inv.max()) + 1
    if t < 2:
        return gbar, math.inf
    g_t = np.bincount(inv, weights=gain, minlength=t)
    n_t = np.bincount(inv, minlength=t)
    return gbar, float(math.sqrt(t / (t - 1.0) * float(np.sum((g_t - gbar * n_t) ** 2))) / n)


def _forward_blocks(start_ns: np.ndarray, quantiles=FORWARD_CUT_QUANTILES):
    """Inner cuts at quantiles of the start times and the block of each row (-1 before the first cut)."""
    cut_ns = np.quantile(start_ns.astype(np.float64), quantiles).astype(np.int64)
    block = np.searchsorted(cut_ns, start_ns, side="right") - 1
    return block, cut_ns


class P2Predictor:
    """Weighted-precedent predictor. ``fit(rows, space, p1, ...)`` returns self."""

    def __init__(self):
        self.space: FeatureSpace | None = None
        self.p1: P1Predictor | None = None
        self.lambda_by_cell: dict[str, float] = {}
        self.bandwidth_mult_by_cell: dict[str, float] = {}
        self.tau_res2_by_cell: dict[str, float] = {}
        self.half_life_by_cell: dict[str, float] = {}
        self.score_by_cell: dict[str, float] = {}
        self.lambda_override: float | None = None
        self.top_m: int | None = TOP_M_NEIGHBORS
        self.leave_out = "test"
        self.selection = P2_SELECTION_DEFAULT
        self.recency: str | float | None = None
        self.bandwidth_override: float | None = None
        self.guard: float | None = P2_GUARD_MULT
        self.guard_by_cell: dict[str, dict] = {}
        self._cells: dict[str, _CellData] = {}

    # ------------------------------------------------------------------ fit
    def fit(
        self,
        rows: pd.DataFrame,
        space: FeatureSpace,
        p1: P1Predictor,
        lambda_override: float | None = None,
        leave_out: str = "test",
        top_m: int | None = TOP_M_NEIGHBORS,
        selection: str | None = None,
        recency: str | float | None = None,
        bandwidth_override: float | None = None,
        guard: float | None = P2_GUARD_MULT,
    ) -> P2Predictor:
        """Build the per-cell retrieval index and choose lam and tau_res^2 per cell.

        ``rows`` are the admitted rows the model may use (the caller passes rows visible at the origin);
        ``lambda_override`` forces lam for every cell (0 reproduces P1). ``leave_out`` is ``"test"`` or
        ``"row"``; ``top_m`` is the neighbor truncation, or None for all neighbors.

        ``selection`` picks how lam, the bandwidth multiplier and the half-life are chosen: ``"loto"`` (leave one
        test out, time order ignored; the default of ``config.P2_SELECTION_DEFAULT``) or ``"forward"`` (forward
        chaining at inner cuts, see ``_cv_cell``). ``recency`` is None (no time kernel), a half-life in days, or
        ``"select"`` (the half-life is chosen with lam and the bandwidth from ``config.HALF_LIFE_DAYS``).
        ``bandwidth_override`` fixes the bandwidth multiplier for every cell. ``guard`` is the admission guard multiplier
        (module docstring); None switches it off, and ``lambda_override`` bypasses it.
        """
        if leave_out not in ("test", "row"):
            raise ValueError("leave_out must be 'test' or 'row'")
        selection = selection or P2_SELECTION_DEFAULT
        if selection not in P2_SELECTIONS:
            raise ValueError(f"selection must be one of {P2_SELECTIONS}")
        if recency not in (None, "select") and not (isinstance(recency, (int, float)) and recency > 0):
            raise ValueError("recency must be None, 'select' or a half-life in days")
        if bandwidth_override is not None and bandwidth_override <= 0:
            raise ValueError("bandwidth_override must be positive")
        self.space, self.p1 = space, p1
        self.lambda_override, self.top_m, self.leave_out = lambda_override, top_m, leave_out
        if guard is not None and guard < 0:
            raise ValueError("guard must be nonnegative or None")
        self.selection, self.recency, self.bandwidth_override = selection, recency, bandwidth_override
        self.guard, self.guard_by_cell, self.top_candidate_by_cell = guard, {}, {}
        self.lambda_by_cell, self.tau_res2_by_cell, self._cells = {}, {}, {}
        self.bandwidth_mult_by_cell, self.half_life_by_cell, self.score_by_cell = {}, {}, {}
        mults = BANDWIDTH_MULTIPLIERS if bandwidth_override is None else (float(bandwidth_override),)
        half_lives = (math.inf,) if recency is None else HALF_LIFE_DAYS if recency == "select" else (float(recency),)
        adm = rows.loc[rows["status"] == ADMITTED]
        last = p1.last_period()
        for cell, g in adm.groupby("cell"):
            g = g.sort_values("usable_after", kind="stable")
            X = space.transform(g).astype(np.float32)
            data = _CellData(
                X, g["y"].to_numpy(float), g["s"].to_numpy(float), tuple(g["row_id"]), tuple(g["test_id"]),
                series_ns(g["usable_after"]), median_bandwidth(X), series_ns(g["started_at"]),
            )
            par = p1.cell_params(cell, last)
            tau = sd_equivalent(par["tau"], par["nu"])
            codes = pd.factorize(g["test_id"])[0]
            n = len(data.y)
            forward = None
            if selection == "forward":
                block, cut_ns = _forward_blocks(data.start_ns)
                pool = np.flatnonzero(block >= 0)
            else:
                pool = np.arange(n)
            queries = pool if len(pool) <= CV_MAX_QUERIES else np.sort(np.random.default_rng(0).choice(pool, CV_MAX_QUERIES, replace=False))
            if selection == "forward":
                forward = (block[queries], cut_ns)
            stats, dens = _cv_cell(data, codes, tau, mults, leave_out, queries, half_lives, forward)
            picks = []
            for c in mults:
                for hl in half_lives:
                    m, v_m, valid = stats[(c, hl)]
                    pick = self._choose(data, queries, m, v_m, valid, tau, par["mu"], codes[queries], par["nu"])
                    picks.append((c, hl, pick))
            c, hl, pick, diag = self._select(picks)
            data.h *= c
            dd = dens[c]
            data.novelty = float(np.percentile(dd, NOVELTY_PERCENTILE)) if len(dd) > 1 else float("-inf")
            self._cells[cell] = data
            self.bandwidth_mult_by_cell[cell], self.half_life_by_cell[cell], self.score_by_cell[cell] = c, hl, diag["score"]
            self.tau_res2_by_cell[cell], self.lambda_by_cell[cell] = pick["tau_res2"], diag["lambda"]
            self.guard_by_cell[cell] = {k: diag[k] for k in ("lambda_unguarded", "gain", "gain_se", "guard_held")}
            self.top_candidate_by_cell[cell] = self._top_pending
        return self

    def _select(self, picks):
        """Choose ``(c, hl, pick, diagnostics)`` from the per-bandwidth picks by the guarded rule or the earlier one.

        The earlier rule takes the best mean log score over bandwidths and, inside it, the smallest lam within the tie
        tolerance of the best. The guarded rule (module docstring) restricts the candidates with lam above zero to the
        admissible ones and takes the best gain among them; with none admissible lam is 0 and the bandwidth is the one
        the earlier rule would have used (it only sets the novelty threshold when lam is 0).
        """
        best = None
        for c, hl, pick in picks:
            if best is None or pick["score"] > best[2]["score"] + 1e-12:
                best = (c, hl, pick)
        c0, hl0, p0 = best
        unguarded = {"c": c0, "hl": hl0, "pick": p0, "lambda": p0["lam"], "score": p0["score"]}
        # largest-gain candidate with lam above zero, admissible or not, for the record
        top = None
        for c, hl, pick in picks:
            for lam, gain, se in pick["cand"]:
                if top is None or gain > top[2] + 1e-12:
                    top = (c, hl, gain, se, lam, pick)
        gain0, se0 = (top[2], top[3]) if top else (0.0, math.inf)
        self._top_pending = None if top is None else {"lambda": top[4], "bandwidth_mult": top[0], "half_life_days": top[1]}
        if self.guard is None or self.lambda_override is not None or top is None:
            sel_gain, sel_se = gain0, se0
            if unguarded["lambda"] > 0:
                hit = [(g, s_) for lam, g, s_ in p0["cand"] if lam == unguarded["lambda"]]
                sel_gain, sel_se = hit[0] if hit else (gain0, se0)
            return c0, hl0, p0, {**unguarded, "lambda_unguarded": unguarded["lambda"], "gain": sel_gain, "gain_se": sel_se, "guard_held": False}
        adm = [(c, hl, pick, lam, gain, se) for c, hl, pick in picks for lam, gain, se in pick["cand"]
               if gain > _LAMBDA_TIE and gain - self.guard * se > 0]
        if not adm:
            base = p0["base_mean"]
            return c0, hl0, p0, {"lambda": 0.0, "score": base, "lambda_unguarded": unguarded["lambda"], "gain": gain0, "gain_se": se0,
                                 "guard_held": bool(unguarded["lambda"] > 0)}
        best_gain = max(a[4] for a in adm)
        near = [a for a in adm if a[4] >= best_gain - _LAMBDA_TIE]
        c, hl, pick, lam, gain, se = min(near, key=lambda a: a[3])          # ties resolve to the smaller lam
        return c, hl, pick, {"lambda": lam, "score": pick["base_mean"] + gain, "lambda_unguarded": unguarded["lambda"], "gain": gain,
                             "gain_se": se, "guard_held": False}

    def _choose(self, data, queries, m, v_m, valid, tau, mu, codes_q, nu=math.inf) -> dict:
        """Statistics for one bandwidth and half-life.

        Returns ``tau_res2``, ``lam`` and ``score`` (the earlier rule: the smallest lam within the tie tolerance of the best mean
        log score), ``base_mean`` (the mean log score at lam 0) and ``cand``, a list ``(lam, gain, se)`` for every lam above zero
        where the gain is the mean per-row log-score gain over lam 0 and ``se`` its standard error clustered by test. ``cand`` is
        empty when ``lambda_override`` is set (no lam-0 baseline is scored).
        """
        if valid.sum() < _MIN_CV_ROWS:
            return {"tau_res2": 0.0, "lam": 0.0, "score": -math.inf, "base_mean": -math.inf, "cand": []}
        y, s2 = data.y[queries][valid], data.s[queries][valid] ** 2
        m, v_m = m[valid], v_m[valid]
        r2 = float(np.mean((y - m) ** 2))
        tau_res2 = max(0.0, r2 - float(np.mean(s2)) - float(np.mean(v_m)))
        lams = LAMBDA_GRID if self.lambda_override is None else (self.lambda_override,)
        rows = []
        for lam in lams:
            theta = lam * m + (1.0 - lam) * mu
            v = lam * (v_m + tau_res2) + (1.0 - lam) * tau * tau
            scale = np.sqrt(v) if math.isinf(nu) else scale_from_sd(np.sqrt(v), nu)
            rows.append(marginal_logpdf_rows(y, s2, theta, scale, nu))
        means = np.array([float(r.mean()) for r in rows])
        top = int(np.argmax(means))
        # smallest lam within the tie tolerance of the best: a flat curve means the precedents add nothing
        pick = next(i for i, mv in enumerate(means) if mv >= means[top] - _LAMBDA_TIE)
        cand = []
        if self.lambda_override is None and lams[0] == 0.0:
            codes_v = codes_q[valid]
            for i, lam in enumerate(lams):
                if lam > 0:
                    g, se = gain_and_se(rows[i] - rows[0], codes_v)
                    cand.append((float(lam), g, se))
        return {"tau_res2": tau_res2, "lam": float(lams[pick]), "score": float(means[top]), "base_mean": float(means[0]), "cand": cand}

    # ------------------------------------------------------------- queries
    def _lam(self, cell: str) -> float:
        return self.lambda_override if self.lambda_override is not None else self.lambda_by_cell.get(cell, 0.0)

    def neighbor_state(self, x, cell: str, origin) -> NeighborState:
        """Top-M visible neighbors of ``x`` in ``cell`` at ``origin`` with the cell parameters.

        Only rows with ``usable_after <= origin`` are searched. An unknown cell, or one with no visible
        rows, gives an empty state with ``lam = 0``.
        """
        par = self.p1.cell_params(cell, quarter_of(origin))
        tau = sd_equivalent(par["tau"], par["nu"])
        data = self._cells.get(cell)
        k = 0 if data is None else data.prefix(timestamp_ns(origin))
        if k == 0:
            return NeighborState((), np.zeros(0), np.zeros(0), np.zeros(0), (), par["mu"], tau, 0.0, 0.0, nu=par["nu"])
        d2 = sq_dists(np.asarray(x, dtype=data.X.dtype), data.X[:k], data.sq[:k]).astype(np.float64)
        inv = -1.0 / (2.0 * data.h * data.h)
        recency = 1.0
        hl = self.half_life_by_cell.get(cell, math.inf)
        if not math.isinf(hl):          # recency: older precedents count less, with age measured from the origin
            age = np.maximum((timestamp_ns(origin) - data.usable_ns[:k]) / _NS_PER_DAY, 0.0)
            recency = np.exp2(-age / hl)
        kern_all = np.exp(d2 * inv) * recency
        peak = float(kern_all.max())
        if peak < _F32_SMALLEST:
            # The kernel is below the float32 range the validation used (or is exactly zero) for every precedent: the query is far from all of
            # them and the fit-time validation never saw
            # such a query (it drops them), and a weight chosen on in-support queries applied to one dissimilar precedent would be an
            # unvalidated forecast. The state is empty with a weight of zero, so the predictive is P1's (REV-L-021).
            return NeighborState((), np.zeros(0), np.zeros(0), np.zeros(0), (), par["mu"], tau, 0.0, 0.0, nu=par["nu"])
        m = k if self.top_m is None else min(self.top_m, k)
        if m < k:
            top = np.argpartition(-kern_all, m - 1)[:m]
            rest = np.ones(k, dtype=bool)
            rest[top] = False
            w_rest = kern_all[rest] / (data.s[:k][rest] ** 2 + tau * tau)
            tail = (
                float(w_rest.sum()), float((w_rest * data.y[:k][rest]).sum()),
                float((w_rest ** 2 * (data.s[:k][rest] ** 2 + tau * tau)).sum()), float((w_rest ** 2).sum()),
            )
        else:
            top, tail = np.arange(k), (0.0, 0.0, 0.0, 0.0)
        idx = top[np.argsort(-kern_all[top], kind="stable")]
        return NeighborState(
            tuple(data.row_ids[i] for i in idx), kern_all[idx], data.y[idx], data.s[idx],
            tuple(data.test_ids[i] for i in idx), par["mu"], tau, self._lam(cell),
            self.tau_res2_by_cell.get(cell, 0.0), tail, par["nu"],
        )

    def predictive_from_state(self, st: NeighborState, x, s_star: float, cell: str, origin) -> Predictive:
        if st.lam == 0.0 or (len(st.row_ids) == 0 and st.tail[0] == 0.0) or not (st.kernel.sum() + st.tail[0]) > 0:
            return self.p1.predict(x, s_star, cell, origin)
        mo = st.moments()
        sd = max(math.sqrt(mo.v), _SD_FLOOR)
        scale = sd if math.isinf(st.nu) else max(float(scale_from_sd(sd, st.nu)), _SD_FLOOR)
        lo, hi = self.p1.y_range(cell)
        grid = build_grid(mo.theta_hat, scale, y_min=lo, y_max=hi)
        return Predictive.from_t(grid, mo.theta_hat, scale, st.nu)

    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:
        """Working predictive ``t(theta^, scale, nu)`` (variance ``v``) on the grid; P1's grid when lam is 0 or there are no precedents."""
        return self.predictive_from_state(self.neighbor_state(x, cell, origin), x, s_star, cell, origin)

    def top_precedents(self, x, cell: str, origin, k: int) -> pd.DataFrame:
        """The ``k`` highest-weight precedents, sorted by weight descending.

        Columns: ``row_id``, ``weight`` (share of the total P2 weight ``w_i``, the unlisted tail beyond the top M included), ``kernel``, ``y``, ``s``
        (units of y), ``test_id``.
        """
        st = self.neighbor_state(x, cell, origin)
        if len(st.row_ids) == 0:
            return pd.DataFrame(columns=["row_id", "weight", "kernel", "y", "s", "test_id"])
        w = st.kernel / (st.s ** 2 + st.tau ** 2)
        order = np.argsort(-w, kind="stable")[:k]
        return pd.DataFrame(
            {
                "row_id": [st.row_ids[i] for i in order], "weight": w[order] / (w.sum() + st.tail[0]), "kernel": st.kernel[order],
                "y": st.y[order], "s": st.s[order], "test_id": [st.test_ids[i] for i in order],
            }
        )

    def p_sig_without(self, x, cell: str, origin, s_star: float, dismissed_row_ids=()) -> float:
        """P(y* > z s*) on the grid after removing the named precedents from the top-M neighbors."""
        st = self.neighbor_state(x, cell, origin).without(dismissed_row_ids)
        return self.predictive_from_state(st, x, s_star, cell, origin).p_sig(s_star)

    def density(self, x, cell: str, origin) -> float:
        """Kernel density of ``x`` among the cell's rows visible at the origin (0 when there are none)."""
        data = self._cells.get(cell)
        k = 0 if data is None else data.prefix(timestamp_ns(origin))
        return 0.0 if k == 0 else density(np.asarray(x), Index(data.X[:k], data.sq[:k], data.h))

    def novelty_threshold(self, cell: str) -> float:
        """5th percentile of the leave-one-out density of the cell's fit rows, stored at fit."""
        data = self._cells.get(cell)
        return float("-inf") if data is None else data.novelty

    def selection_summary(self) -> list[dict]:
        """One record per cell: the selected lam, bandwidth multiplier and half-life (None for no decay) and the selection score."""
        out = []
        for cell, d in self._cells.items():
            hl = self.half_life_by_cell.get(cell, math.inf)
            sc = self.score_by_cell.get(cell)
            out.append({"cell": cell, "lambda": self._lam(cell), "bandwidth_mult": self.bandwidth_mult_by_cell.get(cell),
                        "half_life_days": None if math.isinf(hl) else float(hl), "tau_res2": self.tau_res2_by_cell.get(cell),
                        "selection_score": None if sc is None or not math.isfinite(sc) else float(sc), "n_rows": int(len(d.y)),
                        "selection": self.selection, "guard": self.guard, **self._guard_record(cell)})
        return out

    def _guard_record(self, cell: str) -> dict:
        g = self.guard_by_cell.get(cell)
        if g is None:
            return {"lambda_unguarded": None, "gain": None, "gain_se": None, "guard_held": None}
        def fin(x):
            return None if x is None or not math.isfinite(x) else float(x)

        return {"lambda_unguarded": float(g["lambda_unguarded"]), "gain": fin(g["gain"]), "gain_se": fin(g["gain_se"]),
                "guard_held": bool(g["guard_held"])}

    def n_visible(self, cell: str, origin) -> int:
        """Number of rows of the cell visible at the origin."""
        data = self._cells.get(cell)
        return 0 if data is None else data.prefix(timestamp_ns(origin))

    # ---------------------------------------------------------------- state
    def to_state(self) -> dict[str, Any]:
        """Split into ``arrays`` (npz-safe), ``meta`` (JSON). Row and test ids are stored as unicode arrays."""
        arrays: dict[str, np.ndarray] = {}
        meta: dict[str, Any] = {
            "lambda_by_cell": self.lambda_by_cell, "bandwidth_mult_by_cell": self.bandwidth_mult_by_cell, "tau_res2_by_cell": self.tau_res2_by_cell,
            "lambda_override": self.lambda_override, "top_m": self.top_m, "leave_out": self.leave_out,
            "half_life_by_cell": {c: (None if math.isinf(v) else v) for c, v in self.half_life_by_cell.items()},
            "selection": self.selection, "recency": self.recency, "bandwidth_override": self.bandwidth_override,
            "guard": self.guard, "guard_by_cell": {c: self._guard_record(c) for c in self._cells},
            "cells": {},
        }
        for i, (cell, d) in enumerate(self._cells.items()):
            meta["cells"][cell] = {"key": i, "h": d.h, "novelty": None if math.isinf(d.novelty) else d.novelty}
            arrays[f"c{i}_X"], arrays[f"c{i}_y"], arrays[f"c{i}_s"] = d.X, d.y, d.s
            arrays[f"c{i}_usable"] = d.usable_ns
            arrays[f"c{i}_row_ids"] = np.array(d.row_ids, dtype="U")
            arrays[f"c{i}_test_ids"] = np.array(d.test_ids, dtype="U")
        return {"arrays": arrays, "meta": meta}

    @classmethod
    def from_state(cls, state: dict[str, Any], space: FeatureSpace, p1: P1Predictor) -> P2Predictor:
        """Inverse of ``to_state``; ``space`` and ``p1`` are the already-loaded companions."""
        meta, arr = state["meta"], state["arrays"]
        p = cls()
        p.space, p.p1 = space, p1
        p.lambda_by_cell, p.tau_res2_by_cell = dict(meta["lambda_by_cell"]), dict(meta["tau_res2_by_cell"])
        p.bandwidth_mult_by_cell = dict(meta["bandwidth_mult_by_cell"])
        p.lambda_override, p.top_m, p.leave_out = meta["lambda_override"], meta["top_m"], meta["leave_out"]
        p.half_life_by_cell = {c: (math.inf if v is None else float(v)) for c, v in meta.get("half_life_by_cell", {}).items()}
        p.selection = meta.get("selection", P2_SELECTION_DEFAULT)
        p.recency, p.bandwidth_override = meta.get("recency"), meta.get("bandwidth_override")
        p.guard = meta.get("guard")
        p.guard_by_cell = {c: {"lambda_unguarded": r["lambda_unguarded"], "gain": r["gain"], "gain_se": r["gain_se"], "guard_held": r["guard_held"]}
                           for c, r in (meta.get("guard_by_cell") or {}).items() if r.get("lambda_unguarded") is not None}
        for cell, info in meta["cells"].items():
            i = info["key"]
            d = _CellData(
                arr[f"c{i}_X"], arr[f"c{i}_y"], arr[f"c{i}_s"], tuple(arr[f"c{i}_row_ids"].tolist()),
                tuple(arr[f"c{i}_test_ids"].tolist()), arr[f"c{i}_usable"], info["h"],
            )
            d.novelty = float("-inf") if info["novelty"] is None else info["novelty"]
            p._cells[cell] = d
        return p
