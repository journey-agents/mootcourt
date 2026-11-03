"""Extra checks for the harness internals added by the builder (not stubs from the planner)."""
import datetime as dt

import numpy as np
import pytest

UTC = dt.timezone.utc


def test_ystar_intervals_agree_with_predictive_interval(imp):
    harness = imp("mootcourt.harness")
    base = imp("mootcourt.predictors.base")
    grid = base.build_grid(1.0, 2.0)
    for pred in (base.Predictive.from_normal(grid, 1.0, 2.0), base.Predictive.from_normal(grid, -3.0, 0.7)):
        s = np.array([0.4, 1.5, 3.0])
        iv = harness.ystar_intervals(pred, s)
        for j, sv in enumerate(s):
            for level in (0.8, 0.9):
                lo, hi = pred.interval(level, float(sv))
                spread = hi - lo
                assert abs(iv[level][0][j] - lo) < 0.01 * spread and abs(iv[level][1][j] - hi) < 0.01 * spread


def test_posterior_floor_is_a_valid_brier_floor_and_direction_ceiling(imp, make_synth):
    harness, p1m = imp("mootcourt.harness"), imp("mootcourt.predictors.p1")
    ledger = make_synth(seed=131, n_tests=200, variants_per_test=2)[0]
    p1 = p1m.P1Predictor().fit(ledger)
    out = harness.posterior_floor(ledger.head(100), p1, ledger["usable_after"].max())
    assert ((out["brier_floor_row"] >= 0) & (out["brier_floor_row"] <= 0.25 + 1e-12)).all()
    assert ((out["dir_ceiling_row"] >= 0.5) & (out["dir_ceiling_row"] <= 1.0)).all()
    assert out["p_theta_posterior"].min() >= 0 and out["p_theta_posterior"].max() <= 1


def test_audit_restores_fit_methods(imp, make_synth):
    harness, p0m = imp("mootcourt.harness"), imp("mootcourt.predictors.p0")
    before = p0m.P0Predictor.__dict__["fit"]
    ledger = make_synth(seed=132, n_tests=60, variants_per_test=1)[0]
    with pytest.raises(harness.LeakageError):
        harness.rolling_origin(ledger, {"P0": lambda rows, o: p0m.P0Predictor().fit(ledger)}, harness.quarterly_origins(ledger))
    assert p0m.P0Predictor.__dict__["fit"] is before


def test_reliability_window_drops_old_outcomes_and_keeps_every_recent_one(imp):
    rel = imp("mootcourt.reliability")
    now = dt.datetime(2014, 7, 15, tzinfo=UTC)

    def rows(days_ago, n):
        return [{"cell": "a", "at": (now - dt.timedelta(days=days_ago, hours=i)).isoformat(), "logscore": -2.0, "p0_logscore": -2.0,
                 "brier": 0.2, "p0_brier": 0.2} for i in range(n)]

    rep = rel.build_reliability(None, rows(70, 30) + rows(3, 12), now, advance=True, source="synthetic")
    assert rep["cells"]["a"]["n"] == 12 and rep["source"] == "synthetic"


def test_reliability_needs_enough_outcomes_before_counting_a_drift(imp):
    rel = imp("mootcourt.reliability")
    now = dt.datetime(2014, 7, 15, tzinfo=UTC)
    few = [{"cell": "a", "at": (now - dt.timedelta(days=1)).isoformat(), "logscore": -5.0, "p0_logscore": -1.0,
            "brier": 0.5, "p0_brier": 0.2}] * 3
    rep = rel.build_reliability(None, few, now, advance=True)
    assert rep["cells"]["a"]["n"] == 3 and rep["cells"]["a"]["consecutive_below"] == 0
