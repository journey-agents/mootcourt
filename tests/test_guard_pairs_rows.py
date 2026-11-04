"""T-067: where the realized P2 minus P1 loss of the admitted guard pairs sits (round 01, R3 major 2).

``guard_pairs_rows`` reads the per-row score table of a run, keeps the rows of the (origin, cell) pairs where the guard admitted a weight, and
reports per pair and pooled the share of rows where P2 beats P1, the median and mean per-row log-score difference, the same split by decisive
rows (|y| above z s) against the rest and by the significant-positive event, and the difference decomposed into a location and a scale part
(refit predictives checked against the stored log scores). The add-only flag merges the key; ``build_tables.py`` prints ``guard-pairs-rows.tex``.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extras():
    return _load("paper_extras_gpr", "scripts/paper_extras.py")


def test_the_row_statistics_report_share_median_mean_the_splits_and_parts_that_sum_to_the_difference():
    pe = _extras()
    rng = np.random.default_rng(0)
    n = 400
    d = np.where(np.arange(n) % 4 == 0, 0.2, -0.05) + 0.001 * rng.standard_normal(n)      # P2 wins on a quarter of the rows, by a lot
    frame = pd.DataFrame(
        {
            "test_id": [f"t{i // 2}" for i in range(n)],
            "d": d,
            "decisive": np.arange(n) % 4 == 0,                                             # the winning rows are the decisive ones
            "event": np.arange(n) % 8 == 0,
            "loc_part": 0.75 * d,
            "scale_part": 0.25 * d,
        }
    )
    got = pe._rows_stats(frame, B=100, seed=0, level=0.9)
    assert got["rows"] == n and got["tests"] == n // 2
    assert got["share_p2_better"] == pytest.approx(0.25) and got["share_p2_better_lo"] <= 0.25 <= got["share_p2_better_hi"]
    assert got["median_diff"] == pytest.approx(-0.05, abs=0.01) and got["median_diff_lo"] <= got["median_diff"] <= got["median_diff_hi"]
    assert got["mean_diff"] == pytest.approx(d.mean()) and got["mean_diff_lo"] <= got["mean_diff"] <= got["mean_diff_hi"]
    dec, rest = got["decisive"], got["non_decisive"]
    assert dec["rows"] == 100 and rest["rows"] == 300 and dec["mean_diff"] > 0 > rest["mean_diff"]
    assert dec["share_p2_better"] == pytest.approx(1.0) and rest["share_p2_better"] == pytest.approx(0.0)
    assert got["event"]["rows"] == 50 and got["non_event"]["rows"] == 350
    assert got["location_part"] == pytest.approx(0.75 * d.mean()) and got["scale_part"] == pytest.approx(0.25 * d.mean())
    assert got["location_part"] + got["scale_part"] == pytest.approx(got["mean_diff"])
    assert dec["location_part"] + dec["scale_part"] == pytest.approx(dec["mean_diff"])


def _planted_run(tmp_path: Path, n_tests: int = 300, strength: float = 4.0):
    """A real backtest of P0, P1 and P2 on a planted ledger in a scratch data root: the guard admits weights at several origins."""
    from mootcourt.cli import app
    from mootcourt.ledger import write_ledger
    from mootcourt.sources.synthetic import SyntheticConfig, generate

    ledger, _ = generate(SyntheticConfig(seed=3, n_tests=n_tests, text_effect_strength=strength))
    root = tmp_path / "root"
    write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True, exist_ok=True)
    args = ["backtest", "--source", "synthetic", "--bootstrap", "20", "--no-baselines"]
    res = CliRunner().invoke(app, args, env={"MOOTCOURT_DATA_ROOT": str(root)})
    assert res.exit_code == 0, res.output
    rep = next((root / "reports").glob("backtest-synthetic-*.json"))
    sid = json.loads(rep.read_text())["header"]["snapshot_id"]
    return root, sid, ledger


@pytest.fixture(scope="module")
def planted_run(tmp_path_factory):
    return _planted_run(tmp_path_factory.mktemp("gpr"))


def test_the_admitted_pairs_rows_are_read_refit_checked_and_decomposed_on_a_planted_backtest(planted_run):
    pe = _extras()
    root, sid, ledger = planted_run
    got = pe.guard_pairs_rows(root / "reports", "synthetic", sid, ledger, B=50)
    rows = got["rows"]
    assert len(rows) >= 2 and all(r["lambda"] > 0 for r in rows)
    rep = json.loads(next((root / "reports").glob("backtest-synthetic-*.json")).read_text())
    admitted = [(r["origin"], r["cell"]) for r in rep["tables"]["p2_selection"] if r["rung"] == "P2" and r["lambda"] > 0]
    assert [(r["origin"], r["cell"]) for r in rows] == admitted
    scores = pd.read_parquet(root / "reports" / f"scores-synthetic-{sid}.parquet")
    for r in rows:
        assert r["recomputation_max_abs_error"] < 1e-6                               # the refit predictives are the backtest's own
        assert r["location_part"] + r["scale_part"] == pytest.approx(r["mean_diff"], abs=1e-9)
        assert r["decisive"]["rows"] + r["non_decisive"]["rows"] == r["rows"]
        assert 0.0 <= r["share_p2_better"] <= 1.0 and r["mean_diff_lo"] <= r["mean_diff"] <= r["mean_diff_hi"]
        part = scores[(scores["cell"] == r["cell"]) & (pd.to_datetime(scores["origin"], utc=True) == pd.Timestamp(r["origin"]))]
        p1 = part[part["rung"] == "P1"].set_index("row_id")["logscore"]
        p2 = part[part["rung"] == "P2"].set_index("row_id")["logscore"]
        assert r["rows"] == len(p1) and r["mean_diff"] == pytest.approx(float((p2 - p1.reindex(p2.index)).mean()))
        assert r["mean_scale_ratio_p2_over_p1"] > 0 and 0.0 <= r["share_scale_wider"] <= 1.0
    pooled = got["pooled"]
    assert pooled["rows"] == sum(r["rows"] for r in rows)
    assert pooled["location_part"] + pooled["scale_part"] == pytest.approx(pooled["mean_diff"], abs=1e-9)
    assert got["decomposition"]["defined"] is True and "location" in got["decomposition"]["definition"]
    assert pe.guard_pairs_rows(root / "reports", "synthetic", "MISSING", ledger) is None


def test_a_run_without_admitted_pairs_gives_empty_rows_and_no_pooled_block(tmp_path):
    from mootcourt.sources.synthetic import SyntheticConfig, generate

    pe = _extras()
    ledger, _ = generate(SyntheticConfig(seed=1, n_tests=60))
    sel = [{"rung": "P2", "cell": "m1", "lambda": 0.0, "origin": "2014-01-01T00:00:00+00:00"}]
    (tmp_path / "backtest-asos-SID.json").write_text(json.dumps({"header": {"snapshot_id": "SID", "p2_guard": 2.0}, "tables": {"p2_selection": sel}}))
    pd.DataFrame({"row_id": ["a"], "test_id": ["t"], "cell": ["m1"], "origin": ["2014-01-01T00:00:00+00:00"], "rung": ["P1"], "y": [0.1], "s": [0.1],
                  "s_star": [0.1], "logscore": [-1.0], "event": [False], "point": [0.0]}).to_parquet(tmp_path / "scores-asos-SID.parquet")
    got = pe.guard_pairs_rows(tmp_path, "asos", "SID", ledger)
    assert got["rows"] == [] and got["pooled"] is None and got["summary"]["pairs_admitted"] == 0 and got["summary"]["pairs_in_selection"] == 1


def test_the_guard_pairs_rows_only_flag_merges_the_key_and_leaves_every_other_key_unchanged(planted_run, monkeypatch):
    pe = _extras()
    root, sid, _ledger = planted_run
    out = root / "reports" / f"paper-extras-synthetic-{sid}.json"
    before = {"header": {"snapshot_id": sid}, "guard_pairs": {"rows": [{"origin": "x", "lambda": 0.123456789}]}, "top_m_tail_share": {"a": [1, 2.5]}}
    out.write_text(json.dumps(before, indent=1, sort_keys=True) + "\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["paper_extras.py", "--source", "synthetic", "--ledger", str(root / "data" / "ledger" / "ledger.parquet"), "--reports-dir",
         str(root / "reports"), "--guard-pairs-rows-only", "--positive-control-bootstrap", "30"],
    )
    assert pe.main() == 0
    after = json.loads(out.read_text())
    assert all(after[k] == v for k, v in before.items())
    assert len(after["guard_pairs_rows"]["rows"]) >= 2 and after["guard_pairs_rows"]["inputs"]["bootstrap_resamples"] == 30


def test_build_tables_writes_the_guard_pairs_rows_table(tmp_path):
    bt = _load("build_tables_gpr", "paper/build_tables.py")
    pair = {
        "origin": "2014-07-01T00:00:00+00:00", "cell": "headline_only", "lambda": 0.6, "rows": 1550, "tests": 439, "share_p2_better": 0.195,
        "share_p2_better_lo": 0.17, "share_p2_better_hi": 0.22, "median_diff": -0.0504, "median_diff_lo": -0.06, "median_diff_hi": -0.04,
        "mean_diff": -0.0267, "mean_diff_lo": -0.04, "mean_diff_hi": -0.01,
        "decisive": {"rows": 402, "share_p2_better": 0.7, "mean_diff": 0.0446, "mean_diff_lo": 0.02, "mean_diff_hi": 0.07, "median_diff": 0.03,
                     "location_part": 0.05, "scale_part": -0.005},
        "non_decisive": {"rows": 1148, "share_p2_better": 0.02, "mean_diff": -0.0517, "mean_diff_lo": -0.06, "mean_diff_hi": -0.04,
                         "median_diff": -0.055, "location_part": -0.01, "scale_part": -0.04},
        "location_part": 0.0057, "location_part_lo": -0.001, "location_part_hi": 0.012, "scale_part": -0.0324, "scale_part_lo": -0.04,
        "scale_part_hi": -0.025, "mean_scale_ratio_p2_over_p1": 1.12, "share_scale_wider": 0.9,
    }
    pooled = {**pair, "rows": 7773, "tests": 2000, "mean_diff": -0.0067, "mean_diff_lo": -0.009, "mean_diff_hi": -0.005}
    decomposition = {"defined": True, "definition": "x"}
    gpr = {"rows": [pair], "pooled": pooled, "decomposition": decomposition, "inputs": {"bootstrap_resamples": 500}}
    doc = {"guard_pairs_rows": gpr}
    (tmp_path / "paper-extras-upworthy-SID.json").write_text(json.dumps(doc))
    bt.guard_pairs_rows_table(str(tmp_path), str(tmp_path))
    t = (tmp_path / "guard-pairs-rows.tex").read_text()
    assert "2014-07-01" in t and "0.195 (0.170, 0.220)" in t and "-0.0504" in t and "402" in t and "0.0446" in t and "pooled" in t
    assert "-0.0324 (-0.0400, -0.0250)" in t
