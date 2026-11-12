"""P0, the empirical base-rate forecaster of the visible ledger, per cell and origin.

Round 00 redefined this rung (docs/method.md call 160). P0 forecasts the observed estimate from the visible history alone:

* ``p_sig`` is the visible share of rows whose estimate was significant and positive (``y > z s``), the same quantity the
  Brier skill denominator uses, so P0's Brier skill is zero by construction (the identity is tested, and the report says so);
* ``p_dir`` (also ``p_win``) is the visible share of rows with ``y > 0``;
* the 80 and 90 percent intervals are the empirical quantiles of the visible ``y`` (they already include measurement error);
* the log score and the CRPS are those of a Normal with the visible mean and variance of ``y``, a density family only for scoring
  (the intervals do not come from it); the point estimate is the visible mean.

P0 does not ignore measurement error by assumption, it never models it: ``y`` already contains it. The legacy ``predict`` (a Normal
of the visible ``y`` on a theta grid) is kept for callers that need a ``Predictive``; the backtest, the card and the loop score
with ``forecast``, ``logscore``, ``crps`` and ``score_block``.

Units: ``y`` and ``s`` are in the ledger's units (percentage points of click-through rate for Upworthy); frequencies are
unitless. Origin semantics: only rows with status admitted and ``usable_after <= origin`` are used;
this is applied at predict time, so one fitted P0 serves every origin. A cell with fewer than 2
visible rows falls back to the global fit over all cells.

``density="t"`` (an ablation, docs/superpowers/plans/2026-11-12-heavy-tailed-base-rate.md) scores the log score with a Student-t fitted
by maximum likelihood to the same visible ``y``: location, scale and the degrees of freedom from ``NU_GRID``. It is a harder baseline
for a rung whose own density has heavy tails. Nothing else changes: ``p_sig``, ``p_dir``, the quantile intervals and the CRPS are those
of the default, so the Brier skill of every rung is the same under both densities.

``recency`` (an ablation, docs/superpowers/plans/2026-11-12-base-rate-recency-and-origins.md) gives ``p_sig`` a period term, so the
Brier skill of the other rungs is measured against a base rate that follows the level of the last quarter as P1 does. ``quarter``
mirrors P1's rule: the cell's visible share plus half of (the share over all visible rows of the last complete quarter with at least
``MIN_PERIOD_ROWS`` visible rows, minus the share over all visible rows), clipped to the unit interval. ``cell-quarter`` is the cell's
own share in the last complete quarter that holds at least that many visible rows of the cell. Without such a quarter both leave the
share as it is. Nothing else changes: the density, the intervals and ``p_dir`` are those of the default.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from scipy import special, stats

from mootcourt.config import NU_GRID, Z
from mootcourt.ledger import ADMITTED, series_ns, timestamp_ns
from mootcourt.predictors.base import Predictive, build_grid
from mootcourt.predictors.p1 import MIN_PERIOD_ROWS, _period_end

_MIN_ROWS = 2
_SD_FLOOR = 1e-6
DENSITIES = ("normal", "t")
_MIN_ROWS_T = 5          # with fewer visible rows a tail cannot be fitted: the t density is then its normal limit
RECENCIES = ("none", "quarter", "cell-quarter")


def last_complete_period(periods: np.ndarray, origin) -> str | None:
    """The latest period label among ``periods`` that is complete at ``origin`` (P1's test: its last day is on or before the origin's
    day) and holds at least ``MIN_PERIOD_ROWS`` of the rows passed; None when there is none."""
    day = pd.Timestamp(origin)
    day = (day.tz_localize("UTC") if day.tzinfo is None else day.tz_convert("UTC")).date()
    labels, counts = np.unique(np.asarray(periods, dtype=object).astype(str), return_counts=True)
    ok = [p for p, n in zip(labels, counts) if n >= MIN_PERIOD_ROWS and (_period_end(p) - pd.Timedelta(days=1)).date() <= day]
    return max(ok) if ok else None


def recent_share(ev_cell: np.ndarray, per_cell: np.ndarray, ev_all: np.ndarray, per_all: np.ndarray, origin, rule: str) -> float:
    """The base probability of an event under a recency ``rule`` of ``RECENCIES``, from visible rows only.

    ``ev_cell`` and ``per_cell`` are the event indicator and the period label of the cell's visible rows (the caller passes all rows for a
    thin cell); ``ev_all`` and ``per_all`` are those of all visible rows. Unitless, in [0, 1]."""
    ev_cell, ev_all = np.asarray(ev_cell, dtype=np.float64), np.asarray(ev_all, dtype=np.float64)
    share = float(ev_cell.mean())
    if rule == "none":
        return share
    if rule == "quarter":
        p = last_complete_period(per_all, origin)
        if p is None:
            return share
        level = float(ev_all[np.asarray(per_all, dtype=object).astype(str) == p].mean())
        return float(np.clip(share + (level - float(ev_all.mean())) / 2.0, 0.0, 1.0))
    if rule == "cell-quarter":
        p = last_complete_period(per_cell, origin)
        return share if p is None else float(ev_cell[np.asarray(per_cell, dtype=object).astype(str) == p].mean())
    raise ValueError(f"recency must be one of {RECENCIES}; got {rule!r}")


@dataclass(frozen=True)
class P0Forecast:
    """The P0 forecast of one cell at one origin (units of y; probabilities unitless)."""

    n: int
    mean: float
    var: float
    p_sig: float
    p_dir: float
    lo80: float
    hi80: float
    lo90: float
    hi90: float
    used_global_fallback: bool = False


class _CellSeries:
    """Cumulative statistics of one cell's admitted rows ordered by usable_after."""

    def __init__(self, df: pd.DataFrame, center: float, z: float):
        df = df.sort_values("usable_after", kind="stable")
        self.t = series_ns(df["usable_after"])
        self.y_raw = df["y"].to_numpy(dtype=np.float64)
        self.s_raw = df["s"].to_numpy(dtype=np.float64)
        self.cum_pos = np.cumsum((self.y_raw > 0.0).astype(np.float64))
        y = df["y"].to_numpy(dtype=np.float64) - center
        self.cum_n = np.arange(1, len(y) + 1, dtype=np.float64)
        self.cum_y = np.cumsum(y)
        self.cum_y2 = np.cumsum(y * y)
        self.sig = (df["y"].to_numpy() > z * df["s"].to_numpy()).astype(np.float64)
        self.cum_sig = np.cumsum(self.sig)
        self.period = df["period"].to_numpy(dtype=object) if "period" in df.columns else None
        self.cum_min = np.minimum.accumulate(df["y"].to_numpy(dtype=np.float64))
        self.cum_max = np.maximum.accumulate(df["y"].to_numpy(dtype=np.float64))

    def upto(self, origin_ns: int) -> int:
        return int(np.searchsorted(self.t, origin_ns, side="right"))

    def stats(self, k: int, center: float) -> tuple[float, float]:
        """Mean and sample variance of the first ``k`` rows."""
        m = self.cum_y[k - 1] / k
        var = (self.cum_y2[k - 1] - k * m * m) / (k - 1) if k > 1 else 0.0
        return float(m + center), float(max(var, 0.0))


class P0Predictor:
    """Base-rate predictor. ``fit(rows)`` returns self; rows are filtered by origin at predict time."""

    def __init__(self, z: float = Z, density: str = "normal", recency: str = "none"):
        if density not in DENSITIES:
            raise ValueError(f"density must be one of {DENSITIES}; got {density!r}")
        if recency not in RECENCIES:
            raise ValueError(f"recency must be one of {RECENCIES}; got {recency!r}")
        self.z = z
        self.density = density
        self.recency = recency
        self._t_cache: dict[tuple[int, int], tuple[float, float, float]] = {}
        self._center = 0.0
        self._cells: dict[str, _CellSeries] = {}
        self._global: _CellSeries | None = None
        self._cache: dict[tuple[int, int], P0Forecast] = {}

    def fit(self, rows: pd.DataFrame) -> P0Predictor:
        """Store admitted rows by cell. Raises ValueError when there are no admitted rows."""
        adm = rows.loc[rows["status"] == ADMITTED]
        if len(adm) == 0:
            raise ValueError("P0 needs at least one admitted row")
        self._center = float(adm["y"].mean())
        self._cells = {c: _CellSeries(g, self._center, self.z) for c, g in adm.groupby("cell")}
        self._global = _CellSeries(adm, self._center, self.z)
        self._cache = {}
        self._t_cache = {}
        return self

    def _pick(self, cell: str, origin) -> tuple[_CellSeries, int, bool]:
        t = timestamp_ns(origin)
        series = self._cells.get(cell)
        if series is not None:
            k = series.upto(t)
            if k >= _MIN_ROWS:
                return series, k, False
        glob = self._global
        k = glob.upto(t)
        if k < 1:
            raise ValueError("no admitted rows are visible at this origin")
        return glob, k, True

    def used_global_fallback(self, cell: str, origin) -> bool:
        """True when the cell has fewer than 2 visible rows and the global fit is used."""
        return self._pick(cell, origin)[2]

    def n_visible(self, cell: str, origin) -> int:
        """Number of admitted rows in the cell visible at the origin."""
        series = self._cells.get(cell)
        return 0 if series is None else series.upto(timestamp_ns(origin))

    def sig_positive_frequency(self, cell: str, origin) -> float:
        """Share of visible rows in the cell with ``y > z s`` (unitless), global when the cell is thin."""
        return self.forecast(cell, origin).p_sig

    def forecast(self, cell: str, origin) -> P0Forecast:
        """The empirical forecast of the cell's visible rows at the origin (global rows when the cell has fewer than 2).

        With a ``recency`` rule ``p_sig`` carries its period term; every other field is the default's."""
        f = self._plain_forecast(cell, origin)
        if self.recency == "none":
            return f
        series, k, _ = self._pick(cell, origin)
        glob = self._global
        kg = glob.upto(timestamp_ns(origin))
        if series.period is None or glob.period is None:
            raise ValueError("a recency rule needs the ledger's period column")
        p_sig = recent_share(series.sig[:k], series.period[:k], glob.sig[:kg], glob.period[:kg], origin, self.recency)
        return replace(f, p_sig=p_sig)

    def _plain_forecast(self, cell: str, origin) -> P0Forecast:
        series, k, fallback = self._pick(cell, origin)
        key = (id(series), k)
        got = self._cache.get(key)
        if got is None:
            mean, var = series.stats(k, self._center)
            # a variance floor: y contains its measurement noise, so Var(y) is at least about the median s^2; two visible rows must not give a
            # near-zero spread and an unbounded log score (REV-L-022)
            var = max(var, float(np.median(series.s_raw[:k] ** 2)))
            lo80, hi80, lo90, hi90 = (float(v) for v in np.quantile(series.y_raw[:k], [0.1, 0.9, 0.05, 0.95]))
            got = P0Forecast(k, mean, var, float(series.cum_sig[k - 1] / k), float(series.cum_pos[k - 1] / k), lo80, hi80, lo90, hi90, fallback)
            self._cache[key] = got
        return got

    def density_params(self, cell: str, origin) -> tuple[float, float, float]:
        """``(nu, location, scale)`` of the density the log score uses, in the units of y; ``nu`` is infinite for the normal.

        The default is Normal(visible mean, visible variance). With ``density="t"`` each ``nu`` of ``NU_GRID`` is fitted by maximum
        likelihood to the visible ``y`` and the likeliest is kept; the scale has the floor of the default's standard deviation, the
        square root of the median squared standard error of the visible rows. Fewer than ``_MIN_ROWS_T`` visible rows give the normal.
        """
        f = self._plain_forecast(cell, origin)
        normal = (float("inf"), f.mean, max(float(np.sqrt(f.var)), _SD_FLOOR))
        if self.density == "normal":
            return normal
        series, k, _ = self._pick(cell, origin)
        key = (id(series), k)
        got = self._t_cache.get(key)
        if got is None:
            got = normal
            if k >= _MIN_ROWS_T:
                y = series.y_raw[:k]
                floor = max(float(np.sqrt(np.median(series.s_raw[:k] ** 2))), _SD_FLOOR)
                best = float(stats.norm.logpdf(y, normal[1], normal[2]).sum())
                for nu in NU_GRID:
                    if not np.isfinite(nu):
                        continue
                    _, loc, scale = stats.t.fit(y, fdf=nu, loc=normal[1], scale=normal[2])
                    scale = max(float(scale), floor)
                    ll = float(stats.t.logpdf(y, nu, loc, scale).sum())
                    if ll > best:
                        best, got = ll, (float(nu), float(loc), scale)
            self._t_cache[key] = got
        return got

    def logscore(self, y, cell: str, origin):
        """Log density of ``y`` under the density of ``density_params``; scalar or array in, same shape out."""
        if self.density == "t":
            nu, loc, scale = self.density_params(cell, origin)
            if np.isfinite(nu):
                return stats.t.logpdf(np.asarray(y, dtype=np.float64), nu, loc, scale)
        f = self.forecast(cell, origin)
        sd = max(float(np.sqrt(f.var)), _SD_FLOOR)
        z = (np.asarray(y, dtype=np.float64) - f.mean) / sd
        return -0.5 * z * z - np.log(sd * np.sqrt(2.0 * np.pi))

    def crps(self, y, cell: str, origin):
        """CRPS of ``y`` under Normal(visible mean, visible variance), in the units of y."""
        f = self.forecast(cell, origin)
        sd = max(float(np.sqrt(f.var)), _SD_FLOOR)
        z = (np.asarray(y, dtype=np.float64) - f.mean) / sd
        return sd * (z * (2.0 * special.ndtr(z) - 1.0) + 2.0 * np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi) - 1.0 / np.sqrt(np.pi))

    def score_block(self, scored: pd.DataFrame, y, s_star, origin, X_cache=None):
        """``(columns, keep)`` for the backtest: the rows are scored cell by cell with the empirical forecast, none dropped."""
        n = len(scored)
        y = np.asarray(y, dtype=np.float64)
        keys = ("logscore", "crps", "p_sig", "p_win", "point", "p_gt0", "lo80", "hi80", "lo90", "hi90")
        cols = {k: np.empty(n) for k in keys}
        cells = scored["cell"].to_numpy()
        for c in np.unique(cells):
            idx = np.flatnonzero(cells == c)
            f = self.forecast(str(c), origin)
            cols["logscore"][idx], cols["crps"][idx] = self.logscore(y[idx], str(c), origin), self.crps(y[idx], str(c), origin)
            cols["p_sig"][idx], cols["p_win"][idx], cols["p_gt0"][idx], cols["point"][idx] = f.p_sig, f.p_dir, f.p_dir, f.mean
            cols["lo80"][idx], cols["hi80"][idx], cols["lo90"][idx], cols["hi90"][idx] = f.lo80, f.hi80, f.lo90, f.hi90
        return cols, np.ones(n, bool)

    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:
        """Legacy view: Normal(mean, var) of the cell's visible y on a grid covering their observed range."""
        series, k, _ = self._pick(cell, origin)
        mean, var = series.stats(k, self._center)
        sd = max(float(np.sqrt(var)), _SD_FLOOR)
        grid = build_grid(mean, sd, y_min=float(series.cum_min[k - 1]), y_max=float(series.cum_max[k - 1]))
        return Predictive.from_normal(grid, mean, sd)
