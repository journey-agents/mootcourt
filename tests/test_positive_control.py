"""T-066: the positive control reports gain, not only admission (round 01, R3 major 4 and R1 minor).

The sensitivity rows carry the realized held-out P2 minus P1 log-score gain with a by-test interval, the gain of the oracle that knows the
planted effect, both Brier skills and the recovered fraction; the rung comparison on the planted ledger reads a backtest folder; the add-only
flag of ``scripts/paper_extras.py`` merges only the positive-control keys; ``paper/build_tables.py`` prints both tables.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extras():
    return _load("paper_extras_pc", "scripts/paper_extras.py")


def _tables():
    return _load("build_tables_pc", "paper/build_tables.py")


NEW_KEYS = (
    "realized_gain", "realized_gain_lo", "realized_gain_hi", "realized_gain_se", "oracle_gain", "oracle_gain_lo", "oracle_gain_hi",
    "recovered_fraction", "brier_skill_p1", "brier_skill_p2", "brier_skill_oracle", "held_out_rows", "held_out_tests", "share_admitted_fit_split",
    "by_cell",
)


def test_the_sensitivity_rows_carry_the_realized_and_oracle_gains_and_the_old_admission_share_to_the_last_digit():
    pe = _extras()
    got = pe.positive_control_sensitivity(strengths=(0.0, 4.0), sizes=(300,), seeds=range(2))
    rows = got["rows"]
    assert [r["text_effect_strength"] for r in rows] == [0.0, 4.0]
    for r in rows:
        for k in NEW_KEYS:
            assert k in r, k
        assert r["held_out_rows"] > 0 and r["held_out_tests"] > 0 and r["cells"] == 6
        assert r["realized_gain_lo"] <= r["realized_gain"] <= r["realized_gain_hi"]
        assert {c["cell"] for c in r["by_cell"]} == {"both", "headline_only", "image_only"}
    # the admission share is the fit on the whole ledger, as before, so the published numbers do not move
    old = pe.guard_admission_rates(range(2), 300, multipliers=(2.0,), text_effect_strength=4.0)["by_multiplier"][0]
    assert rows[1]["share_admitted"] == old["share_admitted"] and rows[1]["admitted"] == old["admitted"]
    # with nothing planted the oracle is P1 itself: its gain is exactly zero and the recovered fraction is undefined
    assert rows[0]["oracle_gain"] == 0.0 and rows[0]["recovered_fraction"] is None
    assert got["inputs"]["held_out_share_of_tests"] == 0.15 and got["inputs"]["bootstrap_resamples"] > 0


def test_the_recovered_fraction_is_between_zero_and_about_one_on_a_tiny_planted_ledger():
    pe = _extras()
    got = pe.positive_control_sensitivity(strengths=(4.0,), sizes=(300,), seeds=range(2))
    r = got["rows"][0]
    assert r["oracle_gain"] > 0.0 and r["oracle_gain_lo"] > 0.0
    assert 0.0 <= r["recovered_fraction"] <= 1.1
    assert r["recovered_fraction"] == pytest.approx(r["realized_gain"] / r["oracle_gain"])
    assert r["brier_skill_oracle"] >= r["brier_skill_p1"]
    for c in r["by_cell"]:
        assert c["oracle_gain"] > 0.0 and c["rows"] > 0


def test_the_planted_shift_is_the_generators_own_text_term_and_the_oracle_refit_removes_it():
    from mootcourt.sources.synthetic import SIGNAL_WORDS, SyntheticConfig, generate

    pe = _extras()
    ledger, _ = generate(SyntheticConfig(seed=3, n_tests=200, text_effect_strength=2.0))
    shift = pe.planted_shift(ledger, 2.0)
    heads = [json.loads(j)["headline"] for j in ledger["features_json"]]
    flagged = np.array([any(w in SIGNAL_WORDS for w in h.split()) for h in heads])
    assert set(np.unique(shift)) == {-1.0, 1.0} and np.array_equal(shift > 0, flagged)
    assert np.all(pe.planted_shift(ledger, 0.0) == 0.0)
    plain = pe.oracle_p1(ledger, 0.0).fit_cell_params("headline_only")
    known = pe.oracle_p1(ledger, 2.0).fit_cell_params("headline_only")
    assert known["tau"] < plain["tau"]  # the planted spread, strength squared over four, is no longer in the prior


def _fake_run(tmp_path: Path, n_tests: int = 160, strength: float = 4.0):
    """A run folder: the planted ledger, a score table for P1 (its real scores at one origin), P2, GBM and text_lr at fixed offsets from it,
    and a report with the aggregate rows."""
    from mootcourt.ledger import ensure_snapshot, write_ledger
    from mootcourt.predictors.p1 import P1Predictor
    from mootcourt.sources.synthetic import SyntheticConfig, generate
    from mootcourt.storage import storage_paths

    run = tmp_path / "n160"
    ledger, _ = generate(SyntheticConfig(seed=5, n_tests=n_tests, text_effect_strength=strength))
    ledger_path = storage_paths(run).ledger_path  # the run folder is a data root: its ledger sits under the standard layout
    write_ledger(ledger, ledger_path)
    sid = ensure_snapshot(ledger, ledger_path.parent)
    origin = pd.Timestamp("2014-07-01", tz="UTC")
    scored = ledger[(ledger["started_at"] >= origin) & (ledger["started_at"] < pd.Timestamp("2014-10-01", tz="UTC"))]
    p1 = P1Predictor().fit(ledger[ledger["usable_after"] <= origin], data_end=origin)
    y, s, cells = scored["y"].to_numpy(float), scored["s"].to_numpy(float), scored["cell"].to_numpy()
    base, p_base = np.empty(len(scored)), np.empty(len(scored))
    for cell in np.unique(cells):
        idx = np.flatnonzero(cells == cell)
        pred = p1.predict(None, s[idx[0]], str(cell), origin)
        base[idx], p_base[idx] = pred.logscore(y[idx], s[idx]), pred.p_sig(s[idx])
    frames = []
    for rung, dls, dp in (("P1", 0.0, 0.0), ("P2", 0.02, -0.01), ("GBM", 0.05, -0.03), ("text_lr", None, -0.02)):
        f = scored[["row_id", "test_id", "cell", "y", "s"]].copy()
        f["origin"], f["rung"], f["s_star"] = origin, rung, f["s"]
        f["event"] = f["y"] > 1.96 * f["s"]
        f["logscore"] = np.nan if dls is None else base + dls
        f["p_sig"] = np.clip(p_base + dp, 0.01, 0.99)
        f["brier_event"] = (f["p_sig"] - f["event"].astype(float)) ** 2
        frames.append(f)
    pd.concat(frames).to_parquet(run / f"scores-synthetic-{sid}.parquet")
    agg = []
    for cell in ("ALL", "both", "headline_only", "image_only"):
        for rung, ls, sk in (("P0", -2.6, 0.0), ("P1", -2.5, 0.02), ("P2", -2.48, 0.03), ("GBM", -2.45, 0.05), ("text_lr", None, 0.04)):
            agg.append({"cell": cell, "rung": rung, "n": 10, "n_tests": 5, "logscore": ls, "brier_skill": sk, "brier_skill_lo": sk - 0.01,
                        "brier_skill_hi": sk + 0.01, "auc_event": 0.55})
    rep = {
        "header": {"snapshot_id": sid, "model_id": "m", "command": "moot backtest --source synthetic --challenger text_lr",
                   "tests_in_ledger": n_tests, "ledger_rows": len(ledger), "scored_rows": int(len(scored)),
                   "tests_scored": int(scored["test_id"].nunique()), "seed": 0, "bootstrap_resamples": 500},
        "tables": {"aggregate": agg, "p2_selection": [{"rung": "P2", "cell": "headline_only", "lambda": 0.3, "origin": origin.isoformat()},
                                                      {"rung": "P2", "cell": "both", "lambda": 0.0, "origin": origin.isoformat()}]},
    }
    (run / f"backtest-synthetic-{sid}.json").write_text(json.dumps(rep))
    return run, sid


def test_the_rung_comparison_reads_a_run_folder_and_reports_every_rung_against_p1_beside_the_oracle(tmp_path):
    pe = _extras()
    run, sid = _fake_run(tmp_path)
    got = pe.positive_control_rungs([run], strength=4.0, B=50)
    assert len(got["runs"]) == 1
    r = got["runs"][0]
    assert r["n_tests"] == 160 and r["snapshot_id"] == sid and r["planted_text_effect"] == 4.0 and "text_lr" in r["command"]
    allc = r["by_cell"]["ALL"]
    by = {x["rung"]: x for x in allc["rungs"]}
    assert set(by) >= {"P1", "P2", "GBM", "text_lr"}
    assert by["P2"]["diff_logscore_vs_p1"] == pytest.approx(0.02) and by["GBM"]["diff_logscore_vs_p1"] == pytest.approx(0.05)
    # a constant difference has a degenerate interval
    assert by["P2"]["diff_logscore_vs_p1_lo"] == pytest.approx(0.02) and by["P2"]["diff_logscore_vs_p1_hi"] == pytest.approx(0.02)
    assert by["GBM"]["diff_brier_vs_p1_lo"] <= by["GBM"]["diff_brier_vs_p1"] <= by["GBM"]["diff_brier_vs_p1_hi"]
    assert by["text_lr"]["diff_logscore_vs_p1"] is None and by["text_lr"]["diff_brier_vs_p1"] is not None
    assert by["P1"]["diff_logscore_vs_p1"] == 0.0 and by["P1"]["brier_skill"] == 0.02
    assert allc["oracle"]["gain_logscore_vs_p1"] > 0.0 and allc["oracle"]["rows"] == by["P1"]["rows"]  # P1's scores are its real ones
    assert by["P2"]["recovered_fraction_logscore"] == pytest.approx(0.02 / allc["oracle"]["gain_logscore_vs_p1"])
    assert set(r["by_cell"]) == {"ALL", "both", "headline_only", "image_only"}
    assert r["share_pairs_admitted"] == pytest.approx(0.5)


def test_the_positive_control_only_flag_merges_the_positive_control_keys_and_leaves_every_other_key_unchanged(tmp_path, monkeypatch):
    from mootcourt.ledger import ensure_snapshot, write_ledger
    from mootcourt.sources.synthetic import SyntheticConfig, generate

    pe = _extras()
    ledger, _ = generate(SyntheticConfig(seed=0, n_tests=150))
    ledger_path = tmp_path / "data" / "ledger" / "ledger.parquet"
    ledger_path.parent.mkdir(parents=True)
    write_ledger(ledger, ledger_path)
    sid = ensure_snapshot(ledger, ledger_path.parent)
    reports = tmp_path / "reports"
    reports.mkdir()
    before = {
        "header": {"source": "synthetic", "snapshot_id": sid, "created_at": "2026-11-04T00:00:00+00:00"},
        "guard_admission_rates": {"by_multiplier": [{"multiplier": 2.0, "share_admitted": 0.08333333333333333}]},
        "guard_period_control": {"rows": [{"n_tests": 3700, "mean_gain": 0.0027412345678901234}]},
        "top_m_tail_share": {"by_size": [{"contrasts": 10000, "share_p2_weight": {"mean": 0.12345678901234567}}]},
        "positive_control_sensitivity": {"rows": [{"n_tests": 300, "share_admitted": 0.5, "stale": True}]},
        "guard_pairs": None,
        "nested": {"a": [1, 2.5, None, {"b": "c"}]},
    }
    out = reports / f"paper-extras-synthetic-{sid}.json"
    out.write_text(json.dumps(before, indent=1, sort_keys=True) + "\n")
    run, _ = _fake_run(tmp_path / "runs", n_tests=160)
    monkeypatch.setattr(
        sys,
        "argv",
        ["paper_extras.py", "--source", "synthetic", "--ledger", str(ledger_path), "--reports-dir", str(reports), "--positive-control-only",
         "--sensitivity-seeds", "1", "--sensitivity-sizes", "150", "--sensitivity-strengths", "0,4", "--positive-control-runs", str(run),
         "--positive-control-lift", "4", "--positive-control-bootstrap", "50"],
    )
    assert pe.main() == 0
    after = json.loads(out.read_text())
    for k, v in before.items():
        if k != "positive_control_sensitivity":
            assert after[k] == v, k
    rows = after["positive_control_sensitivity"]["rows"]
    assert [r["text_effect_strength"] for r in rows] == [0.0, 4.0] and all("stale" not in r and "realized_gain" in r for r in rows)
    assert [r["n_tests"] for r in after["positive_control_rungs"]["runs"]] == [160]
    # without run folders the rungs key is left as it was, not blanked
    monkeypatch.setattr(
        sys,
        "argv",
        ["paper_extras.py", "--source", "synthetic", "--ledger", str(ledger_path), "--reports-dir", str(reports), "--positive-control-only",
         "--sensitivity-seeds", "1", "--sensitivity-sizes", "150", "--sensitivity-strengths", "0"],
    )
    assert pe.main() == 0
    again = json.loads(out.read_text())
    assert again["positive_control_rungs"] == after["positive_control_rungs"] and again["guard_period_control"] == before["guard_period_control"]


def test_build_tables_writes_the_positive_control_gain_and_rung_tables(tmp_path):
    bt = _tables()
    row = {
        "n_tests": 11100, "rows_per_cell": 7400, "text_effect_strength": 1.0, "cells": 36, "admitted": 32, "share_admitted": 0.8888888888888888,
        "realized_gain": 0.0012, "realized_gain_lo": 0.0008, "realized_gain_hi": 0.0016, "oracle_gain": 0.0186, "oracle_gain_lo": 0.017,
        "oracle_gain_hi": 0.02, "recovered_fraction": 0.0645, "recovered_fraction_lo": 0.04, "recovered_fraction_hi": 0.09,
        "brier_skill_p1": 0.0251, "brier_skill_p2": 0.0265, "brier_skill_oracle": 0.05, "held_out_rows": 39960, "held_out_tests": 19980,
    }
    stale = {"n_tests": 300, "rows_per_cell": 200, "text_effect_strength": 0.0, "cells": 36, "admitted": 1, "share_admitted": 0.0278}
    rungs = {
        "runs": [{
            "n_tests": 2000, "rows_per_cell": 1333, "snapshot_id": "S", "command": "moot backtest", "planted_text_effect": 1.0, "scored_rows": 3576,
            "by_cell": {
                "ALL": {
                    "oracle": {"rows": 3576, "gain_logscore_vs_p1": 0.019, "gain_logscore_vs_p1_lo": 0.017, "gain_logscore_vs_p1_hi": 0.021,
                               "gain_brier_vs_p1": -0.004, "gain_brier_vs_p1_lo": -0.005, "gain_brier_vs_p1_hi": -0.003, "brier_skill": 0.06},
                    "rungs": [
                        {"rung": "P1", "rows": 3576, "logscore": -2.4268, "brier_skill": 0.0239, "brier_skill_lo": 0.01, "brier_skill_hi": 0.04,
                         "diff_logscore_vs_p1": 0.0, "diff_logscore_vs_p1_lo": 0.0, "diff_logscore_vs_p1_hi": 0.0, "diff_brier_vs_p1": 0.0,
                         "diff_brier_vs_p1_lo": 0.0, "diff_brier_vs_p1_hi": 0.0, "recovered_fraction_logscore": 0.0, "recovered_fraction_brier": 0.0},
                        {"rung": "text_lr+cal", "rows": 3576, "logscore": None, "brier_skill": 0.041, "brier_skill_lo": 0.02, "brier_skill_hi": 0.06,
                         "diff_logscore_vs_p1": None, "diff_logscore_vs_p1_lo": None, "diff_logscore_vs_p1_hi": None, "diff_brier_vs_p1": -0.0031,
                         "diff_brier_vs_p1_lo": -0.004, "diff_brier_vs_p1_hi": -0.002, "recovered_fraction_logscore": None,
                         "recovered_fraction_brier": 0.775},
                    ],
                }
            },
        }]
    }
    (tmp_path / "paper-extras-synthetic-SID.json").write_text(
        json.dumps(
            {"positive_control_sensitivity": {"rows": [stale, row], "multiplier": 2.0, "inputs": {"seeds": [0]}}, "positive_control_rungs": rungs}
        )
    )
    bt.positive_control_gain_table(str(tmp_path), str(tmp_path))
    bt.positive_control_rungs_table(str(tmp_path), str(tmp_path))
    gain = (tmp_path / "positive-control-gain.tex").read_text()
    assert "11,100" in gain and "0.0012 (0.0008, 0.0016)" in gain and "0.0186" in gain and "0.06 (0.04, 0.09)" in gain
    assert "300 &" not in gain  # a row without the realized gain (an older file) prints nothing
    rt = (tmp_path / "positive-control-rungs.tex").read_text()
    assert "text\\_lr+cal" in rt and "-0.0031 (-0.0040, -0.0020)" in rt and "oracle" in rt and "0.78" in rt
