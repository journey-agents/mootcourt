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
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import special

from mootcourt.config import Z
from mootcourt.ledger import ADMITTED, series_ns, timestamp_ns
from mootcourt.predictors.base import Predictive, build_grid

_MIN_ROWS = 2
_SD_FLOOR = 1e-6


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
        self.cum_pos = np.cumsum((self.y_raw > 0.0).astype(np.float64))
        y = df["y"].to_numpy(dtype=np.float64) - center
        self.cum_n = np.arange(1, len(y) + 1, dtype=np.float64)
        self.cum_y = np.cumsum(y)
        self.cum_y2 = np.cumsum(y * y)
        self.cum_sig = np.cumsum((df["y"].to_numpy() > z * df["s"].to_numpy()).astype(np.float64))
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

    def __init__(self, z: float = Z):
        self.z = z
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
        series, k, _ = self._pick(cell, origin)
        return float(series.cum_sig[k - 1] / k)

    def forecast(self, cell: str, origin) -> P0Forecast:
        """The empirical forecast of the cell's visible rows at the origin (global rows when the cell has fewer than 2)."""
        series, k, fallback = self._pick(cell, origin)
        key = (id(series), k)
        got = self._cache.get(key)
        if got is None:
            mean, var = series.stats(k, self._center)
            lo80, hi80, lo90, hi90 = (float(v) for v in np.quantile(series.y_raw[:k], [0.1, 0.9, 0.05, 0.95]))
            got = P0Forecast(k, mean, var, float(series.cum_sig[k - 1] / k), float(series.cum_pos[k - 1] / k), lo80, hi80, lo90, hi90, fallback)
            self._cache[key] = got
        return got

    def logscore(self, y, cell: str, origin):
        """Log density of ``y`` under Normal(visible mean, visible variance); scalar or array in, same shape out."""
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
