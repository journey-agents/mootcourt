"""T-008 contracts: P3 team forecast field."""
import dataclasses
import datetime as dt

import pandas as pd
import pytest

UTC = dt.timezone.utc


def test_team_forecast_is_frozen_and_stamped_by_injected_clock(imp, frozen_clock):
    p3 = imp("mootcourt.predictors.p3")
    tf = p3.TeamForecast.create(p_win_team=0.6, point_team=1.5, clock=frozen_clock)
    assert tf.frozen_at == frozen_clock()
    assert tf.frozen_at.tzinfo is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        tf.p_win_team = 0.9
    with pytest.raises(dataclasses.FrozenInstanceError):
        tf.frozen_at = dt.datetime(2000, 1, 1, tzinfo=UTC)


def test_team_forecast_validates_probability(imp, frozen_clock):
    p3 = imp("mootcourt.predictors.p3")
    with pytest.raises(ValueError):
        p3.TeamForecast.create(p_win_team=1.2, point_team=0.0, clock=frozen_clock)


def test_score_team_hand_computed(imp):
    p3 = imp("mootcourt.predictors.p3")
    forecasts = pd.DataFrame({"row_id": list("abcd"), "p_win_team": [0.9, 0.2, 0.7, 0.4],
                              "point_team": [2.0, -2.0, -1.0, 1.0]})
    outcomes = pd.DataFrame({"row_id": list("abcd"), "y": [1.0, -1.0, -2.0, 3.0],
                             "p_gt0_rung": [0.8, 0.3, 0.5, 0.6], "source": "synthetic"})
    out = p3.score_team(forecasts, outcomes)
    # events y > 0: 1, 0, 0, 1
    assert out["brier_team"] == pytest.approx((0.01 + 0.04 + 0.49 + 0.36) / 4)
    assert out["brier_rung"] == pytest.approx((0.04 + 0.09 + 0.25 + 0.16) / 4)
    assert out["mae_point_team"] == pytest.approx((1.0 + 1.0 + 1.0 + 2.0) / 4)
    assert out["n"] == 4
    assert out["label"] == "synthetic"


def test_score_team_label_only_for_synthetic_and_rejects_unmatched(imp):
    p3 = imp("mootcourt.predictors.p3")
    f = pd.DataFrame({"row_id": ["a"], "p_win_team": [0.5], "point_team": [0.0]})
    o = pd.DataFrame({"row_id": ["a"], "y": [1.0], "p_gt0_rung": [0.5], "source": "upworthy"})
    assert p3.score_team(f, o).get("label") != "synthetic"
    with pytest.raises(ValueError):
        p3.score_team(f, o.assign(row_id="zzz"))
