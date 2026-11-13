"""The learning curve summarized over origins (scripts/learning_curve_origins.py)."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def lco():
    path = Path(__file__).resolve().parents[1] / "scripts" / "learning_curve_origins.py"
    spec = importlib.util.spec_from_file_location("learning_curve_origins", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fake_curve(origin, quarter, half, rung="P1"):
    """The smallest curve document ``origin_row`` reads; ``quarter`` and ``half`` are (difference, lo, hi) or None for a fraction not fitted."""
    rows, skipped = [], {}
    for fraction, got in ((0.25, quarter), (0.5, half)):
        if got is None:
            skipped[str(fraction)] = 20
            continue
        d, lo, hi = got
        rows.append({"fraction": fraction, "rung": rung, "n_seeds": 20, "n_paired": 100, "logscore_minus_full": d, "logscore_lo": lo,
                     "logscore_hi": hi, "brier_gain_over_full": d / 10, "brier_lo": lo / 10, "brier_hi": hi / 10})
    return {"source": "upworthy", "final_origin": f"{origin}T00:00:00+00:00", "heldout_rows": 100, "heldout_tests": 50, "seeds": 20,
            "paired_vs_full": rows, "skipped_runs": skipped}


def test_counts_only_intervals_that_exclude_zero(lco):
    docs = [fake_curve("2014-01-01", quarter=(-0.010, -0.015, -0.005), half=(-0.002, -0.006, 0.002)),
            fake_curve("2014-04-01", quarter=(-0.001, -0.004, 0.002), half=(0.001, -0.002, 0.004)),
            fake_curve("2014-07-01", quarter=None, half=(-0.004, -0.007, -0.001))]          # quarter not fitted
    doc = lco.summarize(docs)
    assert doc["origins"] == 3 and doc["worse_at_quarter"] == 1 and doc["worse_at_half"] == 1 and doc["not_fitted"] == 1
    assert [r["origin"] for r in doc["rows"]] == ["2014-01-01", "2014-04-01", "2014-07-01"]


def test_a_row_carries_both_scores_and_says_when_a_fraction_was_not_fitted(lco):
    row = lco.origin_row(fake_curve("2014-07-01", quarter=None, half=(-0.004, -0.007, -0.001)))
    assert row["quarter"] == {"fitted": False} and row["half"]["fitted"] is True
    assert row["half"]["log_diff"] == pytest.approx(-0.004) and row["half"]["brier_hi"] == pytest.approx(-0.0001)
    assert row["heldout_rows"] == 100


def test_the_same_origin_twice_is_an_error(lco):
    with pytest.raises(ValueError):
        lco.summarize([fake_curve("2014-01-01", None, None), fake_curve("2014-01-01", None, None)])
