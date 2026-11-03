"""T-026 contracts: gates at two power targets, release gate at 0.90."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GRID = [50, 100, 200, 400, 800, 1600, 3200]
BY_TARGET = {"0.80": {"n_200": 125, "n_400": 300}, "0.90": {"n_200": 300, "n_400": 700}}
GATES = {"n_200": 300, "n_400": 700, "decision_target": 0.90, "by_target": BY_TARGET}


def test_default_target_is_the_release_gate(imp):
    sim = imp("mootcourt.simulate")
    assert sim.DEFAULT_TARGET == 0.90
    assert sim.RESEARCH_TARGET == 0.80
    assert tuple(sim.TARGETS) == (0.80, 0.90)


def test_gates_json_carries_both_targets(imp, tmp_path):
    sim = imp("mootcourt.simulate")
    path = tmp_path / "gates.json"
    sim.write_gates(path, reps=60, B=50, seed=4, grid=GRID)
    data = json.loads(path.read_text())
    assert set(data["by_target"]) == {"0.80", "0.90"}
    for t in ("0.80", "0.90"):
        assert set(data["by_target"][t]) >= {"n_200", "n_400"}
        assert data["by_target"][t]["n_400"] >= data["by_target"][t]["n_200"]
    for key in ("n_200", "n_400"):
        assert data["by_target"]["0.90"][key] >= data["by_target"]["0.80"][key]
        assert data[key] == data["by_target"]["0.90"][key], "top-level n_200 and n_400 are the decision target"
    assert data["target_power"] == 0.90 and data["decision_target"] == 0.90 and data["research_target"] == 0.80
    assert "matches_expected" not in data


def test_load_gates_returns_decision_values_and_both_targets(imp, tmp_path):
    sim = imp("mootcourt.simulate")
    path = tmp_path / "gates.json"
    sim.write_gates(path, reps=60, B=50, seed=4, grid=GRID)
    data = json.loads(path.read_text())
    g = sim.load_gates(path)
    assert g["n_200"] == data["n_200"] and g["n_400"] == data["n_400"]
    assert g["by_target"] == data["by_target"] and g["decision_target"] == 0.90


def test_load_gates_reads_an_old_file_without_by_target(imp, tmp_path):
    path = tmp_path / "g.json"
    path.write_text(json.dumps({"n_200": 125, "n_400": 300, "target_power": 0.8}))
    g = imp("mootcourt.simulate").load_gates(path)
    assert g["n_200"] == 125 and g["n_400"] == 300


def test_gate_status_reports_the_research_screen_beside_the_release_gate(imp):
    hs = imp("mootcourt.harness_stats")
    st = hs.gate_status(200, GATES)
    assert st["label"] == "undecidable at this n"               # below 300 at the 0.90 gate
    assert st["label_research"] == "decidable at skill 0.20 only"   # 125 <= 200 < 300 at 0.80
    assert st["decidable_at_0.20"] is False
    st = hs.gate_status(800, GATES)
    assert st["label"] == st["label_research"] == "decidable at skill 0.20 and 0.10"


def test_gate_status_without_by_target_still_works(imp):
    st = imp("mootcourt.harness_stats").gate_status(250, {"n_200": 300, "n_400": 700})
    assert st["label"] == "undecidable at this n" and st.get("label_research") is None


def test_aggregate_rows_carry_both_labels(imp):
    import pandas as pd

    hs = imp("mootcourt.harness_stats")
    n = 200
    base = dict(test_id=[f"t{i}" for i in range(n)], cell="a", origin="o", y=1.0, s=1.0, direction_correct=1, lo80=-1, hi80=2, lo90=-2,
                hi90=3, abstain=False, abstain_reasons="", crps=0.5, p_win=0.5, event=[i % 2 for i in range(n)], rung="P1",
                logscore=-1.0, p_sig=0.5, brier_event=0.25)
    agg = hs.aggregate_scores(pd.DataFrame(base), GATES, B=30, seed=1)
    row = agg[(agg["cell"] == "a") & (agg["rung"] == "P1")].iloc[0]
    assert row["decidable"] == "undecidable at this n" and row["decidable_research"] == "decidable at skill 0.20 only"


@pytest.fixture
def report_doc(imp, make_synth, tmp_path):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=95, n_tests=120, variants_per_test=2, cell_params={"headline_only": (1.0, 2.0)}, s_scale=2.0)[0]
    scores = harness.rolling_origin(ledger, {"P0": lambda r, o: imp("mootcourt.predictors.p0").P0Predictor().fit(r)},
                                    harness.quarterly_origins(ledger))
    paths = imp("mootcourt.report").write_report(
        scores, ledger=ledger, source="synthetic", snapshot_id="20261102-eeeeeeeeeeee", model_id="m123456789ab", feature_hash="f123456789ab",
        command="moot backtest --source synthetic --origins quarterly", seed=0, gates=GATES, out_dir=tmp_path, B=40)
    return json.loads(paths.json.read_text()), paths.md.read_text()


def test_report_header_and_markdown_print_both_targets(report_doc):
    data, md = report_doc
    h = data["header"]
    assert h["gate_by_target"] == BY_TARGET and h["gate_decision_target"] == 0.90
    assert h["gate_n_200"] == 300 and h["gate_n_400"] == 700
    assert "0.90" in md and "0.80" in md and "125" in md and "700" in md
    assert all("decidable_research" in r for r in data["tables"]["aggregate"])


def test_no_gate_size_is_hardcoded_in_source():
    pat = re.compile(r"(?<![\w.])(125|200|300|400)(?![\w.])")
    offenders = []
    for rel in ("simulate.py", "harness_stats.py", "report.py", "registry.py", "cli.py", "harness.py"):
        for i, line in enumerate((ROOT / "src" / "mootcourt" / rel).read_text().splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, offenders


def test_method_doc_explains_the_two_targets():
    path = ROOT / "docs" / "method.md"
    assert path.exists(), "docs/method.md is written by T-023 and carries the call on the two power targets"
    text = path.read_text().lower()
    assert "0.90" in text and "0.80" in text and "same power curve" in text
