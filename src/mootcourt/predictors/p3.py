"""P3 team forecast: a field on the setup card, frozen at issue and never edited.

``p_win_team`` is the team's probability that the true effect is above zero (unitless) and
``point_team`` its point forecast of the effect (units of y, percentage points for Upworthy). No archive has
historical forecasts, so the only populated P3 appears in the synthetic cell with a labeled synthetic
forecaster.

``score_team`` scores the forecast next to each rung. Documented call: the team's ``p_win_team``, a
probability that theta > 0, is scored with Brier against the realized event ``y > 0`` (the sign of the
observed effect), beside each rung's ``P(y* > 0)``. This is an approximation of the target the forecast
describes, because the true theta is unknown; it is labeled synthetic whenever the source is synthetic.
"""
from __future__ import annotations

import datetime as dt
import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mootcourt.sources.synthetic import SYNTHETIC_LABEL


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


@dataclass(frozen=True)
class TeamForecast:
    """A frozen team forecast. Build with ``TeamForecast.create`` so ``frozen_at`` comes from the clock."""

    p_win_team: float
    point_team: float
    frozen_at: dt.datetime

    @classmethod
    def create(cls, p_win_team: float, point_team: float, clock: Callable[[], dt.datetime] | None = None) -> TeamForecast:
        """Validate and stamp a forecast; ``clock`` returns a timezone-aware datetime (injectable for tests)."""
        if not (isinstance(p_win_team, (int, float)) and 0.0 <= p_win_team <= 1.0):
            raise ValueError("p_win_team must be a probability in [0, 1]")
        if not math.isfinite(point_team):
            raise ValueError("point_team must be finite")
        now = (clock or _utc_now)()
        if now.tzinfo is None:
            raise ValueError("the clock must return a timezone-aware datetime")
        return cls(float(p_win_team), float(point_team), now)

    def to_dict(self) -> dict:
        """JSON-safe form with an ISO-8601 timestamp."""
        return {"p_win_team": self.p_win_team, "point_team": self.point_team, "frozen_at": self.frozen_at.isoformat()}


def score_team(forecasts: pd.DataFrame, outcomes: pd.DataFrame) -> dict:
    """Score team forecasts beside a rung.

    ``forecasts`` has ``row_id``, ``p_win_team``, ``point_team``. ``outcomes`` has ``row_id``, ``y``,
    ``p_gt0_rung`` (the rung's ``P(y* > 0)``) and ``source``. Returns ``n``, ``brier_team``,
    ``brier_rung`` (both against the event ``y > 0``), ``mae_point_team`` (absolute error of the point
    forecast against the observed ``y``, units of y) and ``label`` equal to ``"synthetic"`` only when every
    outcome row has source synthetic. Raises ValueError when a forecast has no outcome.
    """
    merged = forecasts.merge(outcomes, on="row_id", how="left", validate="one_to_one")
    if merged["y"].isna().any():
        raise ValueError("every forecast needs a matching outcome row")
    event = (merged["y"].to_numpy(float) > 0).astype(float)
    out = {
        "n": int(len(merged)),
        "brier_team": float(np.mean((merged["p_win_team"].to_numpy(float) - event) ** 2)),
        "brier_rung": float(np.mean((merged["p_gt0_rung"].to_numpy(float) - event) ** 2)),
        "mae_point_team": float(np.mean(np.abs(merged["point_team"].to_numpy(float) - merged["y"].to_numpy(float)))),
    }
    if len(merged) and (merged["source"] == SYNTHETIC_LABEL).all():
        out["label"] = SYNTHETIC_LABEL
    return out
