"""Round 02, R1-F3 and decision 9: the issued-row Brier skill in the paper extras and the guard-pairs resample count."""

from __future__ import annotations

import importlib.util
import inspect
import json
import pathlib

import numpy as np
import pandas as pd
import pytest


def _load():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "paper_extras.py"
    spec = importlib.util.spec_from_file_location("paper_extras_r02", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _scores(n_tests=40, rows_per_test=4, seed=1):
    rng = np.random.default_rng(seed)
    out = []
    for t in range(n_tests):
        for r in range(rows_per_test):
            ev = float(rng.random() < 0.12)
            abstain = bool(r == 0 or rng.random() < 0.1)
            for rung in ("P1", "P2"):
                p = float(np.clip(0.12 + 0.2 * (ev - 0.12) * rng.random(), 0.01, 0.99))
                out.append(
                    {
                        "row_id": f"t{t}r{r}", "test_id": f"t{t}", "cell": "headline_only" if t % 2 else "image_only",
                        "origin": pd.Timestamp("2014-01-01", tz="UTC"), "rung": rung, "event": ev, "abstain": abstain,
                        "brier_event": (p - ev) ** 2, "brier_base": (0.12 - ev) ** 2, "logscore": -0.9, "crps": 0.1, "direction_correct": 1.0,
                        "y": 0.0, "lo80": -1.0, "hi80": 1.0, "lo90": -1.5, "hi90": 1.5, "p_sig": p,
                    }
                )
    return pd.DataFrame(out)


def test_the_extras_hold_the_issued_and_abstained_row_brier_skill_with_the_issued_base(tmp_path):
    pe = _load()
    sc = _scores()
    sc.to_parquet(tmp_path / "scores-upworthy-SID.parquet")
    (tmp_path / "backtest-upworthy-SID.json").write_text(json.dumps({"header": {"bootstrap_resamples": 50, "seed": 0}, "tables": {}}))
    got = pe.issued_row_brier_skill(tmp_path, "upworthy", "SID")
    p2 = got["rungs"]["P2"]
    issued, aband, full = p2["issued"], p2["abstained"], p2["all"]
    p2s = sc[sc["rung"] == "P2"]
    iss = p2s[~p2s["abstain"]]
    assert issued["n"] == len(iss) and aband["n"] == int(p2s["abstain"].sum()) and full["n"] == len(p2s)
    assert issued["brier_base"] == pytest.approx(iss["brier_base"].mean())
    assert issued["brier_skill"] == pytest.approx(1 - iss["brier_event"].mean() / iss["brier_base"].mean())
    for part in (issued, aband, full):
        assert part["brier_skill_lo"] <= part["brier_skill"] <= part["brier_skill_hi"] or np.isnan(part["brier_skill"])
    assert got["bootstrap_resamples"] == 50
    assert pe.issued_row_brier_skill(tmp_path, "upworthy", "MISSING") is None


def test_the_guard_pairs_bootstrap_defaults_to_the_count_every_other_interval_uses():
    pe = _load()
    assert inspect.signature(pe.guard_pairs).parameters["B"].default == pe.SENSITIVITY_BOOTSTRAP == 500


def _rows(rule_shift, n_tests=30, origins=("2014-01-01", "2014-04-01")):
    rows = []
    for t in range(n_tests):
        for o in origins:
            for k in range(2):
                rows.append({"row_id": f"r{t}{o}{k}", "test_id": f"t{t}", "cell": "headline_only", "origin": pd.Timestamp(o, tz="UTC"), "rung": "P2",
                             "logscore": -1.0 + rule_shift + 0.001 * (t % 3)})
                rows.append({**rows[-1], "rung": "P1", "logscore": -1.0})
    return pd.DataFrame(rows)


def test_the_extras_hold_the_paired_forward_minus_loto_comparison_pooled_and_by_origin(tmp_path):
    pe = _load()
    ab = tmp_path / "ablations"
    ab.mkdir()
    _rows(0.0).to_parquet(tmp_path / "scores-upworthy-SID.parquet")
    _rows(-0.004).to_parquet(ab / "scores-upworthy-SID--p2-selection-loto.parquet")
    _rows(-0.01).to_parquet(ab / "scores-upworthy-SID--p2-guard-off.parquet")
    _rows(-0.012).to_parquet(ab / "scores-upworthy-SID--p2-selection-loto+p2-guard-off.parquet")
    (tmp_path / "backtest-upworthy-SID.json").write_text(json.dumps({"header": {"bootstrap_resamples": 50, "seed": 0}, "tables": {}}))
    got = pe.p2_selection_comparison(tmp_path, "upworthy", "SID")
    on = got["guard_on"]
    assert on["pooled"]["difference"] == pytest.approx(0.004) and on["pooled"]["lo"] <= 0.004 + 1e-9 and on["pooled"]["hi"] >= 0.004 - 1e-9
    assert [r["origin"][:10] for r in on["by_origin"]] == ["2014-01-01", "2014-04-01"]
    assert all(r["difference"] == pytest.approx(0.004) for r in on["by_origin"])
    assert got["guard_off"]["pooled"]["difference"] == pytest.approx(0.002) and got["bootstrap_resamples"] == 500
    assert pe.p2_selection_comparison(tmp_path, "upworthy", "MISSING") is None
