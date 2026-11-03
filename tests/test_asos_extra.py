"""Builder additions for the ASOS loader: hand-computed effect, final-checkpoint values, nominal placement."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FIX = Path(__file__).parent / "fixtures" / "asos_mini"


def _frame(rows):
    cols = ["experiment_id", "variant_id", "metric_id", "time_since_start", "count_c", "count_t", "mean_c", "mean_t", "variance_c", "variance_t"]
    return pd.DataFrame(rows, columns=cols)


def test_standardised_effect_matches_a_hand_calculation(imp, tmp_path):
    rows = [["e1", 1, 1, 1.0, 5000, 5000, 0.10, 0.20, 0.09, 0.09], ["e1", 1, 1, 2.0, 10000, 10000, 0.10, 0.11, 0.09, 0.09]]
    p = tmp_path / "asos_digital_experiments_dataset.csv"
    _frame(rows).to_csv(p, index=False)
    out = imp("mootcourt.sources.asos").load_asos(tmp_path)
    assert len(out) == 1
    d = 0.01 / 0.3
    assert out["y"].iloc[0] == pytest.approx(d, rel=1e-12)
    assert out["s"].iloc[0] == pytest.approx(np.sqrt(2 / 10000 + d * d / 40000), rel=1e-12)
    feats = json.loads(out["features_json"].iloc[0])["post_launch"]
    assert feats["original_effect"] == pytest.approx(0.01) and feats["original_se"] == pytest.approx(np.sqrt(0.09 / 10000 * 2))
    assert out["n_ref"].iloc[0] == 10000 and out["cell"].iloc[0] == "metric_1"


def test_final_checkpoint_values_are_used_not_earlier_ones(imp):
    out = imp("mootcourt.sources.asos").load_asos(FIX)
    raw = pd.read_csv(FIX / "asos_digital_experiments_dataset.csv", dtype={"experiment_id": str})
    last = raw[raw["time_since_start"] == 5.0].set_index(["experiment_id", "variant_id", "metric_id"])
    for r in out[out["status"] == "admitted"].itertuples():
        e, rest = r.row_id.split(":")[1], r.variant_id
        v, m = (int(x) for x in rest.replace("v", "").replace("m", "").split("_"))
        row = last.loc[(e, v, m)]
        assert r.n_ref == int(row["count_c"]) and r.n_var == int(row["count_t"])
        assert json.loads(r.features_json)["post_launch"]["original_effect"] == pytest.approx(row["mean_t"] - row["mean_c"])


def test_missing_variance_is_excluded_with_a_reason_and_keeps_its_row(imp):
    out = imp("mootcourt.sources.asos").load_asos(FIX)
    bad = out[out["status"] != "admitted"]
    assert len(bad) == 1 and json.loads(bad["features_json"].iloc[0])["exclusion_detail"] == "missing_variance"
    assert bad["y"].isna().all()


def test_nominal_calendar_is_deterministic_and_data_independent(imp):
    asos = imp("mootcourt.sources.asos")
    a = asos.nominal_starts(["x1", "x2", "x3", "x4"])
    b = asos.nominal_starts(["x4", "x3", "x2", "x1"])
    assert a == b and len(set(a.values())) == 4
    assert min(a.values()) == asos.NOMINAL_EPOCH and max(a.values()) < asos.NOMINAL_EPOCH + pd.Timedelta(days=asos.NOMINAL_SPAN_DAYS)


def test_loader_accepts_a_file_path_too(imp):
    asos = imp("mootcourt.sources.asos")
    assert len(asos.load_asos(FIX / "asos_digital_experiments_dataset.csv")) == len(asos.load_asos(FIX))
