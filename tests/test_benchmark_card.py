"""T-038 contracts: `moot benchmark --ledger FILE` and its one-page report card."""
import json
import re

import pytest
from typer.testing import CliRunner

GATES = {"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9,
         "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}
HEADINGS = ["Ledger", "Gates", "Ladder", "Decision value", "Calibration by precision", "Limitations"]
LIMITS = ["The forecast is only as good as the ledger it was fit on.",
          "The gates say whether a skill difference is decidable at this n, not whether the tool is useful.",
          "A precedent forecast never replaces running the experiment."]


def _cli(imp, args, root):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env={"MOOTCOURT_DATA_ROOT": str(root)})


def _run(imp, make_synth, tmp_path, seed=57, name="acme-tests", extra=()):
    ledger, _ = make_synth(seed=seed, n_tests=260, variants_per_test=2)
    path = tmp_path / f"{name}.parquet"
    imp("mootcourt.ledger").write_ledger(ledger, path)
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "gates.json").write_text(json.dumps(GATES))
    res = _cli(imp, ["benchmark", "--ledger", str(path), "--bootstrap", "60", *extra], tmp_path)
    return ledger, reports, res


@pytest.fixture(scope="module")
def card_files(tmp_path_factory):
    import importlib

    root = tmp_path_factory.mktemp("card")
    syn = importlib.import_module("mootcourt.sources.synthetic")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=57, n_tests=260, variants_per_test=2))
    path = root / "acme-tests.parquet"
    importlib.import_module("mootcourt.ledger").write_ledger(ledger, path)
    (root / "reports").mkdir()
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    res = CliRunner().invoke(importlib.import_module("mootcourt.cli").app, ["benchmark", "--ledger", str(path), "--bootstrap", "60"],
                             env={"MOOTCOURT_DATA_ROOT": str(root)})
    assert res.exit_code == 0, res.output
    md = next((root / "reports" / "benchmark").glob("acme-tests-*.md"))
    js = next((root / "reports" / "benchmark").glob("acme-tests-*.json"))
    return ledger, md, js, res.output


def test_files_are_named_by_ledger_stem_and_snapshot(card_files):
    _ledger, md, js, out = card_files
    assert re.fullmatch(r"acme-tests-\d{8}-[0-9a-f]{12}\.md", md.name) and js.name == md.name[:-3] + ".json"
    assert str(md) in out and str(js) in out


def test_markdown_has_the_fixed_layout_on_one_page(card_files):
    _l, md, _j, _o = card_files
    text = md.read_text(encoding="utf-8")
    assert re.findall(r"^## (.+)$", text, re.M) == HEADINGS
    assert text.startswith("# Benchmark report card: acme-tests")
    assert len(text.splitlines()) <= 70, "the card must fit one page"
    for sentence in LIMITS:
        assert sentence in text
    assert text.index(LIMITS[0]) < text.index(LIMITS[1]) < text.index(LIMITS[2])
    assert "synthetic" in text.lower()                                          # the ledger is synthetic and the card says so


def test_the_card_states_every_required_number(card_files):
    ledger, _m, js, _o = card_files
    doc = json.loads(js.read_text(encoding="utf-8"))
    assert doc["report_card_schema_version"] == 2 and doc["kind"] == "benchmark_report_card"
    led = doc["ledger"]
    assert led["n_admitted"] == int((ledger["status"] == "admitted").sum()) and led["n_scored"] > 0 and 0 < led["base_rate"] < 1
    assert led["synthetic"] is True and led["n_cells"] == ledger["cell"].nunique() and led["origins_scored"] >= 2
    assert set(doc["gates"]) == {"0.80", "0.90"} and doc["gates"]["0.90"] == {"n_200": 20, "n_400": 30}
    rungs = {r["rung"]: r for r in doc["ladder"]}
    assert {"P0", "P1", "P2"} <= set(rungs)
    for r in rungs.values():
        for key in ("n", "n_tests", "brier_skill", "brier_skill_lo", "brier_skill_hi", "coverage_80", "coverage_90", "abstention_rate",
                    "decidable", "decidable_research"):
            assert key in r, key
        assert r["decidable"] and r["decidable_research"]                        # a label, never empty
    assert rungs["P0"]["brier_skill_lo"] <= rungs["P0"]["brier_skill"] <= rungs["P0"]["brier_skill_hi"]
    dv = {(r["policy"], r["rung"]): r for r in doc["decision_value"]}
    assert ("random", "all") in dv and ("oracle", "all") in dv and ("p_win", doc["ladder_primary"]) in dv
    assert 0 <= dv[("random", "all")]["captured_fraction"] <= dv[("oracle", "all")]["captured_fraction"] <= 1
    assert len(doc["calibration_by_precision"]) == 10
    assert all({"decile", "n", "mean_p_sig", "event_rate"} <= set(r) for r in doc["calibration_by_precision"])
    assert doc["limitations"] == LIMITS and "abstention" in doc and doc["abstention"]["rate"] == rungs[doc["ladder_primary"]]["abstention_rate"]


def test_nothing_that_identifies_a_row_or_a_cell_is_published(card_files):
    ledger, md, js, _o = card_files
    blob = md.read_text(encoding="utf-8") + js.read_text(encoding="utf-8")
    for token in (ledger["row_id"].iloc[0], ledger["test_id"].iloc[0], json.loads(ledger["features_json"].iloc[0])["headline"]):
        assert token not in blob
    for cell in ledger["cell"].unique():
        assert f'"{cell}"' not in blob


def test_two_ledgers_give_cards_with_identical_layout(imp, make_synth, tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _l, ra, res_a = _run(imp, make_synth, a, seed=57, name="org-a")
    _l, rb, res_b = _run(imp, make_synth, b, seed=58, name="org-b")
    assert res_a.exit_code == 0 and res_b.exit_code == 0, res_a.output + res_b.output
    ta = next((ra / "benchmark").glob("org-a-*.md")).read_text()
    tb = next((rb / "benchmark").glob("org-b-*.md")).read_text()

    def skeleton(t):
        return [ln for ln in t.splitlines() if ln.startswith("#") or ln.startswith("|") and set(ln) <= set("|- :")] \
            + [ln for ln in t.splitlines() if ln.startswith("| rung") or ln.startswith("| decile") or ln.startswith("| policy")]

    assert skeleton(ta)[1:] == skeleton(tb)[1:]
    ja = json.loads(next((ra / "benchmark").glob("org-a-*.json")).read_text())
    jb = json.loads(next((rb / "benchmark").glob("org-b-*.json")).read_text())
    assert list(ja) == list(jb) and list(ja["ladder"][0]) == list(jb["ladder"][0])


def test_a_missing_or_nonconformant_ledger_is_a_clear_error(imp, tmp_path):
    res = _cli(imp, ["benchmark", "--ledger", str(tmp_path / "nope.parquet")], tmp_path)
    assert res.exit_code != 0 and "nope.parquet" in res.output
    import pandas as pd

    bad = tmp_path / "bad.parquet"
    pd.DataFrame({"a": [1]}).to_parquet(bad)
    res = _cli(imp, ["benchmark", "--ledger", str(bad)], tmp_path)
    assert res.exit_code != 0 and res.exception is not None and "Traceback" not in res.output


def test_a_ledger_with_several_sources_needs_a_choice(imp, make_synth, tmp_path):
    ledger, _ = make_synth(seed=57, n_tests=120, variants_per_test=2)
    other = ledger.copy()
    other["source"] = "other"
    other["row_id"] = other["row_id"].str.replace("synthetic", "other")
    other["test_id"] = "o" + other["test_id"]
    import pandas as pd

    path = tmp_path / "two.parquet"
    imp("mootcourt.ledger").write_ledger(pd.concat([ledger, other], ignore_index=True), path)
    res = _cli(imp, ["benchmark", "--ledger", str(path)], tmp_path)
    assert res.exit_code != 0 and "--source" in res.output


def test_the_card_obeys_the_writing_rules(card_files):
    _l, md, js, _o = card_files
    text = md.read_text(encoding="utf-8") + js.read_text(encoding="utf-8")
    assert chr(0x2014) not in text and chr(0x2013) not in text


def test_the_docs_page_exists_and_names_every_section():
    from pathlib import Path

    page = Path(__file__).resolve().parents[1] / "docs" / "benchmark.md"
    text = page.read_text(encoding="utf-8")
    for h in HEADINGS:
        assert h in text
    for needle in ("moot benchmark --ledger", "publish", "private", "report_card_schema_version"):
        assert needle in text
