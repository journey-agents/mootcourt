"""P0 base rate: Normal(mean(y), var(y)) per cell over visible admitted rows.

Deliberately ignores measurement error (spec section 8): the spread of y already includes it. Also
exposes the empirical frequency of significant-positive outcomes (``y > z s``) in the cell, which is
the base rate used for Brier skill (a documented builder call).

Units: ``y`` and ``s`` are in the ledger's units (percentage points of click-through rate for Upworthy); frequencies are
unitless. Origin semantics: only rows with status admitted and ``usable_after <= origin`` are used;
this is applied at predict time, so one fitted P0 serves every origin. A cell with fewer than 2
visible rows falls back to the global fit over all cells.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mootcourt.config import Z
from mootcourt.ledger import ADMITTED, series_ns, timestamp_ns
from mootcourt.predictors.base import Predictive, build_grid

_MIN_ROWS = 2
_SD_FLOOR = 1e-6


class _CellSeries:
    """Cumulative statistics of one cell's admitted rows ordered by usable_after."""

    def __init__(self, df: pd.DataFrame, center: float, z: float):
        df = df.sort_values("usable_after", kind="stable")
        self.t = series_ns(df["usable_after"])
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

    def fit(self, rows: pd.DataFrame) -> P0Predictor:
        """Store admitted rows by cell. Raises ValueError when there are no admitted rows."""
        adm = rows.loc[rows["status"] == ADMITTED]
        if len(adm) == 0:
            raise ValueError("P0 needs at least one admitted row")
        self._center = float(adm["y"].mean())
        self._cells = {c: _CellSeries(g, self._center, self.z) for c, g in adm.groupby("cell")}
        self._global = _CellSeries(adm, self._center, self.z)
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

    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:
        """Normal(mean, var) of the cell's visible y on a grid covering their observed range."""
        series, k, _ = self._pick(cell, origin)
        mean, var = series.stats(k, self._center)
        sd = max(float(np.sqrt(var)), _SD_FLOOR)
        grid = build_grid(mean, sd, y_min=float(series.cum_min[k - 1]), y_max=float(series.cum_max[k - 1]))
        return Predictive.from_normal(grid, mean, sd)
