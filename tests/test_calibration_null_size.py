"""The rejection rate of the calibration procedure on calibrated outcomes (scripts/calibration_null_size.py)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def cns():
    path = Path(__file__).resolve().parents[1] / "scripts" / "calibration_null_size.py"
    spec = importlib.util.spec_from_file_location("calibration_null_size", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def tmp_scores():
    rng = np.random.default_rng(5)
    rows = []
    for rung in ("P0", "P1"):
        for i in range(300):
            p = float(rng.uniform(0.05, 0.4))
            rows.append({"rung": rung, "cell": "headline_only" if i % 2 else "image_only", "test_id": f"t{i // 2}", "p_sig": p,
                         "event": float(rng.random() < p)})
    return pd.DataFrame(rows)


def test_draws_keep_the_marginals(cns):
    rng = np.random.default_rng(0)
    p = np.full(20000, 0.2)
    t = np.repeat(np.arange(5000), 4)
    e = cns.draw_events(p, t, 0.5, rng)
    assert abs(e.mean() - 0.2) < 0.01
    by_test = pd.Series(e).groupby(t).mean()
    assert by_test.var() > 0.2 * 0.8 / 4 * 1.2          # outcomes of a test move together


def test_independent_calibrated_forecasts_reject_near_five_percent(cns):
    rng = np.random.default_rng(1)
    p = rng.uniform(0.02, 0.4, 3000)
    t = np.arange(3000)          # one row per test
    row = cns.size_row(p, t, 0.0, reps=200, seed=3)
    assert row["reject_95_lo"] <= 0.05 <= row["reject_95_hi"]
    assert 90.0 <= row["critical_95"] <= 99.9


def test_constant_forecast_is_flagged_and_still_scored(cns):
    p = np.full(800, 0.1)
    t = np.repeat(np.arange(200), 4)
    row = cns.size_row(p, t, 0.3, reps=20, seed=0)
    assert row["constant_forecast"] is True and 0.0 <= row["reject_95"] <= 1.0


def test_summary_has_one_row_per_rung_stratum_binning_and_truth(cns, tmp_scores):
    doc = cns.summarize(tmp_scores, rungs=("P0", "P1"), strata=("ALL",), reps=5, seed=0)
    assert len(doc["rows"]) == 2 * 1 * 2 * 3
    assert {r["truth"] for r in doc["rows"]} == {"zero", "observed", "double"}
    assert {r["binning"] for r in doc["rows"]} == {"equal_width", "equal_mass"}
