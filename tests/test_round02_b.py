"""Round 02, Tier B code rows (task R02-B): each test is the reviewer's reproduction or the check the triage names."""
from __future__ import annotations

import datetime as dt
import json

import pytest
from typer.testing import CliRunner

UTC = dt.timezone.utc
REVENUE_ROW = "sample:exp-105:treatment::revenue_per_user"


def _sample_world(tmp_path, as_of=dt.datetime(2025, 7, 9, tzinfo=UTC)):
    """R2's scratch project: the sample ledger of ``moot init`` with a champion fit on the rows usable at ``as_of``."""
    from mootcourt.bundle import fit_bundle, save_bundle
    from mootcourt.importers.ingest import import_file
    from mootcourt.importers.sample import sample_exchange
    from mootcourt.ledger import ensure_snapshot, write_ledger
    from mootcourt.registry import Registry
    from mootcourt.storage import storage_paths

    layout = storage_paths(root=tmp_path / "mootcourt-data")
    for folder in layout.named().values():
        folder.mkdir(parents=True, exist_ok=True)
    csv = tmp_path / "sample.csv"
    sample_exchange().to_csv(csv, index=False)
    ledger, _ = import_file("generic", csv, "sample")
    write_ledger(ledger, layout.ledger_path)
    sid = ensure_snapshot(ledger, layout.ledger_path.parent)
    bundle = fit_bundle(ledger, "sample", sid, as_of=as_of)
    save_bundle(bundle, layout.models)
    Registry(layout.models).register_model("sample", bundle.model_id)
    return layout, ledger, bundle


# ------------------------------------------------------------------ R2-F1: the join matches the row id and the cell
def _mismatched_card(layout, bundle):
    """R2's card 1a2101fb2c118442: a checkout_conversion card for the revenue_per_user row, built past the refusal at issue."""
    from mootcourt import card as card_mod

    now = dt.datetime(2025, 7, 10, tzinfo=UTC)
    req = card_mod.CardRequest(source="sample", headline="", image_changed=False, impressions=20000, origin=now, row_id=REVENUE_ROW,
                               cell="checkout_conversion")
    card = card_mod.build_card(bundle, req, reliability=None, now=now)
    card_mod.freeze_card(card, layout.cards)
    return card


def test_r2_the_join_records_a_card_scored_against_a_row_of_another_cell_as_a_mismatch_and_scores_nothing(tmp_path):
    from mootcourt import loop

    layout, ledger, bundle = _sample_world(tmp_path)
    assert ledger.set_index("row_id").loc[REVENUE_ROW, "cell"] == "revenue_per_user"
    card = _mismatched_card(layout, bundle)
    assert card.cell == "checkout_conversion"
    res = loop.join_command("sample", layout.ledger_path.parent, layout.cards, layout.reports, now=dt.datetime(2025, 12, 30, tzinfo=UTC))
    outcome = json.loads((layout.cards / "outcomes" / f"{card.card_id}.json").read_text())
    assert outcome["scored"] is False and outcome["cell_mismatch"] is True
    assert "revenue_per_user" in outcome["cell_mismatch_reason"] and "checkout_conversion" in outcome["cell_mismatch_reason"]
    assert outcome["logscore"] is None and outcome["brier"] is None and outcome["y"] is None and outcome["miss_type"] is None
    assert loop.reliability_row(outcome) is None
    assert res.n_outcomes == 0 and res.n_cell_mismatch == 1
    assert json.loads((layout.reports / "reliability-sample.json").read_text())["cells"] == {}, "no cell's window is fed by the mismatch"


def test_r2_a_card_of_the_rows_own_cell_is_still_scored(tmp_path):
    from mootcourt import card as card_mod
    from mootcourt import loop

    layout, ledger, bundle = _sample_world(tmp_path)
    now = dt.datetime(2025, 7, 10, tzinfo=UTC)
    req = card_mod.CardRequest(source="sample", headline="", image_changed=False, impressions=20000, origin=now, row_id=REVENUE_ROW,
                               cell="revenue_per_user")
    card = card_mod.build_card(bundle, req, reliability=None, now=now)
    card_mod.freeze_card(card, layout.cards)
    res = loop.join_command("sample", layout.ledger_path.parent, layout.cards, layout.reports, now=dt.datetime(2025, 12, 30, tzinfo=UTC))
    assert res.n_outcomes == 1 and res.n_cell_mismatch == 0


def test_r2_moot_join_and_the_doctor_count_the_cell_mismatch(tmp_path, monkeypatch):
    from mootcourt import onboarding
    from mootcourt.cli import app

    layout, ledger, bundle = _sample_world(tmp_path)
    _mismatched_card(layout, bundle)
    res = CliRunner().invoke(app, ["join", "--source", "sample", "--ledger", str(layout.ledger_path), "--cards-dir", str(layout.cards),
                                   "--reports-dir", str(layout.reports), "--now", "2025-12-30T00:00:00+00:00"])
    assert res.exit_code == 0, res.output
    assert "attached 0 outcomes" in res.output and "1 card for a row of another cell" in res.output, res.output
    (tmp_path / "mootcourt.toml").write_text(onboarding.config_text(data_root=layout.root, cells=["checkout_conversion"], name="r2"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    doc = onboarding.run_doctor(now=dt.datetime(2025, 12, 31, tzinfo=UTC), write=False)
    check = next(c for c in doc["checks"] if c["name"] == "cards sample")
    assert check["status"] == "warn" and "cards for a row of another cell: 1" in check["detail"], check


def test_r2_moot_card_refuses_a_row_id_whose_ledger_row_has_another_cell_and_freezes_nothing(tmp_path):
    from mootcourt.cli import app

    layout, ledger, bundle = _sample_world(tmp_path)
    common = ["--models-dir", str(layout.models), "--cards-dir", str(layout.cards), "--reports-dir", str(layout.reports)]
    args = ["card", "--source", "sample", "--impressions", "20000", "--row-id", REVENUE_ROW, "--now", "2025-07-10T00:00:00+00:00", *common]
    res = CliRunner().invoke(app, [*args, "--cell", "checkout_conversion"], env={"MOOTCOURT_DATA_ROOT": str(layout.root)})
    assert res.exit_code != 0
    assert "revenue_per_user" in res.output and "checkout_conversion" in res.output and "cell" in res.output, res.output
    assert list(layout.cards.glob("*.json")) == []
    ok = CliRunner().invoke(app, [*args, "--cell", "revenue_per_user"], env={"MOOTCOURT_DATA_ROOT": str(layout.root)})
    assert ok.exit_code == 0, ok.output


def test_r2_post_card_refuses_a_row_id_whose_ledger_row_has_another_cell(tmp_path):
    from fastapi.testclient import TestClient

    from mootcourt.service import create_app

    layout, ledger, bundle = _sample_world(tmp_path)
    now = dt.datetime(2025, 7, 10, tzinfo=UTC)
    client = TestClient(create_app(layout.models, layout.cards, reports_dir=layout.reports, now=lambda: now, ledger_path=layout.ledger_path))
    payload = {"source": "sample", "impressions": 20000, "row_id": REVENUE_ROW, "cell": "checkout_conversion"}
    res = client.post("/card", json=payload)
    assert res.status_code == 422 and "revenue_per_user" in res.json()["error"], res.text
    assert list(layout.cards.glob("*.json")) == []
    assert client.post("/card", json={**payload, "cell": "revenue_per_user"}).status_code == 200


# ------------------------------------------------------------------ R2-F2: the card's cell verdict is the cell's own-dependence verdict
def _both_cell_doc():
    """The headline bundle's both cell: decidable at skill 0.20 at the pooled archive's dependence, undecidable at the cell's own."""
    from test_round01_r2 import _report_doc

    doc = _report_doc()
    both = next(r for r in doc["tables"]["aggregate"] if r["cell"] == "both" and r["rung"] == "P2")
    both.update({"decidable_by_tests": "decidable at skill 0.20 only", "decidable_by_tests_cell": "undecidable at this n",
                 "gate_cell_n_200": 318, "gate_cell_n_400": 454, "n_tests": 225})
    head = next(r for r in doc["tables"]["aggregate"] if r["cell"] == "headline_only" and r["rung"] == "P2")
    head.update({"decidable_by_tests_cell": "decidable at skill 0.20 and 0.10", "gate_cell_n_200": 90, "gate_cell_n_400": 130})
    return doc


def test_r2_the_backtest_summary_copies_the_cells_own_verdict_and_its_two_gate_sizes():
    from mootcourt.registry import backtest_summary

    s = backtest_summary(_both_cell_doc(), "backtest-upworthy-20261103-aaaaaaaaaaaa.json")
    both = s["cells"]["both"]
    assert both["decidable_by_tests_cell"] == "undecidable at this n" and both["decidable_by_tests"] == "decidable at skill 0.20 only"
    assert both["gate_cell_n_200"] == 318 and both["gate_cell_n_400"] == 454


def test_r2_a_both_cell_card_prints_the_cells_own_undecidable_verdict_not_the_pooled_dependence_one():
    import dataclasses

    from test_round01_r2 import _card, _split

    from mootcourt import card as card_mod
    from mootcourt.registry import backtest_summary

    old, new, bundle, origin, now0, rows = _split()
    summary = backtest_summary(_both_cell_doc(), "backtest-upworthy-20261103-aaaaaaaaaaaa.json")
    view = card_mod.backtest_view(summary, "both")
    assert view["scope"] == "pooled" and view["decidable"] == "undecidable at this n"
    assert "318" in view["reason"] and "454" in view["reason"], "the cell's gate sizes say how far it is from decidable"
    assert card_mod.backtest_view(summary, "headline_only")["scope"] == "cell"
    legacy = json.loads(json.dumps(summary))
    for cell in legacy["cells"].values():
        cell.pop("decidable_by_tests_cell"), cell.pop("gate_cell_n_200"), cell.pop("gate_cell_n_400")
    assert card_mod.backtest_view(legacy, "both")["scope"] == "cell", "a summary stored before the field existed reads the old verdict"
    card = _card(dataclasses.replace(bundle, backtest_summary=summary), rows.iloc[0], now0, now0)
    assert "decidable at skill 0.20 only" not in card_mod.to_markdown(card)


def test_r2_the_backtest_line_comes_before_the_window_line_and_the_window_line_says_it_is_descriptive():
    import dataclasses

    from test_round01_r2 import _card, _report_doc, _split

    from mootcourt import card as card_mod
    from mootcourt.registry import backtest_summary

    old, new, bundle, origin, now0, rows = _split()
    summary = backtest_summary(_report_doc(), "backtest-synthetic-20261103-aaaaaaaaaaaa.json")
    card = _card(dataclasses.replace(bundle, backtest_summary=summary), rows.iloc[0], now0, now0)
    sec = card_mod.to_markdown(card).split("## Skill at this n")[1].split("## Abstention")[0]
    lines = [ln for ln in sec.splitlines() if ln.startswith("- ")]
    assert lines[0].startswith("- Latest gated backtest"), lines
    window = next(i for i, ln in enumerate(lines) if "Brier skill against the cell base rate" in ln)
    assert window == 1 and lines[window].endswith("descriptive, one window of many"), lines[window]
    assert lines[window + 1].startswith("- Gate at this n"), "the window's gate line stays beside the window line"


# ------------------------------------------------------------------ R6-F1: the first table of the backtest report
def _sample_doc():
    from pathlib import Path

    return json.loads((Path(__file__).parent / "fixtures" / "quick-check" / "backtest-sample.json").read_text())


def _first_table(md: str) -> tuple[str, str]:
    block = md.split("### Rows, tests, gates and abstention")[1].split("\n###")[0]
    heading = block.splitlines()[0]
    header_row = next(ln for ln in block.splitlines() if ln.startswith("| cell"))
    return heading, header_row


def test_r6_the_first_table_drops_the_repeated_and_the_fixed_rate_columns_when_the_gates_count_tests():
    from mootcourt.report import render_markdown

    doc = _sample_doc()
    assert doc["header"]["gate_interval"]["by"] == "test"
    md = render_markdown(doc)
    heading, header_row = _first_table(md)
    cols = [c.strip() for c in header_row.strip("|").split("|")]
    assert "decidable_by_tests" in cols and "decidable_research_by_tests" in cols
    assert not {"decidable", "decidable_research", "decidable_by_tests_base_0.3"} & set(cols), cols
    assert "by-row columns are beside it" not in heading and "by tests" in heading
    assert "### Other columns" not in md or "decidable_research |" not in md.split("### Other columns")[1], "dropped columns do not reappear"


def test_r6_the_first_table_keeps_the_by_row_columns_for_a_per_row_gates_file():
    from mootcourt.report import render_markdown

    doc = _sample_doc()
    doc["header"]["gate_interval"] = {"by": "row", "level": 0.95}
    for r in doc["tables"]["aggregate"]:
        r["decidable"], r["decidable_research"] = "undecidable at this n", "undecidable at this n"
    heading, header_row = _first_table(render_markdown(doc))
    assert "| decidable |" in header_row + " " and "decidable_research" in header_row
    assert "by-row columns" in heading


# ------------------------------------------------------------------ R6-F3: the report card says which base rate its gates were simulated at
def test_r6_the_report_card_names_the_simulated_base_rate_and_the_ledgers_own(tmp_path, imp, make_synth):
    from test_benchmark_card import GATES, _cli

    ledger, _ = make_synth(seed=57, n_tests=260, variants_per_test=2)
    path = tmp_path / "acme-tests.parquet"
    imp("mootcourt.ledger").write_ledger(ledger, path)
    (tmp_path / "reports").mkdir()
    far_targets = {"0.80": {"n_200": 90, "n_400": 190}, "0.90": {"n_200": 99, "n_400": 199}}
    far = {**GATES, "n_200": 99, "n_400": 199, "base_rate": 0.09, "by_target": far_targets}
    near = {**GATES, "base_rate": 0.25}
    gates = {**far, "by_base_rate": {"0.09": {**far}, "0.25": {**near}}}      # the top level is the first rate, as gate-power writes it
    (tmp_path / "reports" / "gates.json").write_text(json.dumps(gates))
    res = _cli(imp, ["benchmark", "--ledger", str(path), "--bootstrap", "60"], tmp_path)
    assert res.exit_code == 0, res.output
    md = next((tmp_path / "reports" / "benchmark").glob("acme-tests-*.md")).read_text()
    doc = json.loads(next((tmp_path / "reports" / "benchmark").glob("acme-tests-*.json")).read_text())
    rate = doc["ledger"]["base_rate"]
    assert 0.2 < rate < 0.3, "the fixture's ledger is nearer to 0.25 than to 0.09"
    assert doc["gates_base_rate"] == pytest.approx(0.25)
    assert doc["gates"]["0.90"] == {"n_200": 20, "n_400": 30}, "the sizes printed are those of the nearest simulated rate"
    line = f"Simulated at base rate 0.25, the nearest simulated rate to this ledger's {rate:.3f}."
    assert line in md
    assert len(md.splitlines()) <= 70


# ------------------------------------------------------------------ R6-F4: the backtest's fallback gates are the quick simulation `moot init` runs
def test_r6_the_quick_gates_are_by_test_at_the_simulated_rate_nearest_the_ledgers_and_level_090(tmp_path, monkeypatch):
    from mootcourt import onboarding, simulate

    monkeypatch.setattr(onboarding, "QUICK_GATE", {"reps": 8, "B": 20})
    path = tmp_path / "gates.json"
    doc = onboarding.write_quick_gates(path, 0.12, 0.9)
    assert sorted(doc["by_base_rate"]) == ["0.14"], "0.12 is nearer to 0.14 than to 0.09"
    assert doc["interval"]["by"] == "test" and doc["interval"]["level"] == simulate.DEFAULT_LEVEL == 0.90
    assert doc["interval"]["rows_per_test"] == simulate.SOURCE_DEPENDENCE[0.14][0] and doc["reps"] == 8 and "table" not in doc


def test_r6_moot_backtest_without_a_gates_file_runs_the_same_quick_simulation_as_init(tmp_path, monkeypatch):
    import typer

    from mootcourt import onboarding
    from mootcourt.cli import app

    layout, ledger, bundle = _sample_world(tmp_path)
    layout.gates_path.unlink(missing_ok=True)
    seen = {}

    def spy(path, base_rate, target, progress=None):
        seen.update(path=path, base_rate=base_rate, target=target)
        raise typer.Exit(code=7)

    monkeypatch.setattr(onboarding, "write_quick_gates", spy)
    res = CliRunner().invoke(app, ["backtest", "--source", "sample", "--ledger", str(layout.ledger_path), "--reports-dir", str(layout.reports)],
                             env={"MOOTCOURT_DATA_ROOT": str(layout.root)})
    assert res.exit_code == 7, res.output
    from mootcourt.simulate import ledger_dependence

    assert seen["base_rate"] == pytest.approx(ledger_dependence(ledger)["base_rate"])
    assert "quick gate simulation" in res.output and "moot simulate gate-power" in res.output, res.output


# ------------------------------------------------------------------ R6-F5 and R6-s2: help text a newcomer can read
def _help(*args) -> str:
    from mootcourt.cli import app

    res = CliRunner().invoke(app, [*args, "--help"], env={"COLUMNS": "200", "NO_COLOR": "1"})
    assert res.exit_code == 0, res.output
    return " ".join(res.output.split())


def test_r6_the_impressions_variant_help_says_planned_units_like_its_sibling():
    text = _help("card")
    assert "Planned units of the variant arm" in text and "Planned exposures" not in text


def test_r6_the_reliability_help_names_no_design_call():
    import re

    assert not re.search(r"\(call \d+\)", _help("reliability"))


# ------------------------------------------------------------------ R6-F6: a join error names the problem and the cure
def test_r6_join_with_a_missing_new_rows_file_names_the_file_and_the_ingest_step(tmp_path):
    from mootcourt.cli import app

    layout, ledger, bundle = _sample_world(tmp_path)
    missing = tmp_path / "nonexistent.parquet"
    res = CliRunner().invoke(app, ["join", "--source", "sample", "--ledger", str(layout.ledger_path), "--cards-dir", str(layout.cards),
                                   "--reports-dir", str(layout.reports), "--new-rows", str(missing)], env={"MOOTCOURT_DATA_ROOT": str(layout.root)})
    assert res.exit_code == 2
    assert f"error: new rows file not found: {missing}" in res.output
    assert "moot ingest --ledger incoming/ledger.parquet" in res.output


def test_r6_join_without_a_ledger_names_the_ledger_and_the_ingest_step(tmp_path):
    from mootcourt.cli import app

    missing = tmp_path / "nowhere" / "ledger.parquet"
    res = CliRunner().invoke(app, ["join", "--source", "sample", "--ledger", str(missing), "--cards-dir", str(tmp_path / "c"),
                                   "--reports-dir", str(tmp_path / "r")], env={"MOOTCOURT_DATA_ROOT": str(tmp_path / "root")})
    assert res.exit_code == 2
    assert f"error: ledger not found: {missing}" in res.output and "moot ingest" in res.output


def test_r2_attaching_a_report_with_the_cell_verdict_refreshes_the_stored_summary_and_the_card_reads_it(tmp_path):
    """Decision 10: the released bundle's stored summary is regenerated from its report, and the card then reads the cell's own verdict."""
    from test_round01_r2 import _split

    from mootcourt import card as card_mod
    from mootcourt.bundle import load_bundle, save_bundle
    from mootcourt.registry import Registry, attach_backtest, backtest_summary

    old, new, bundle, origin, now0, rows = _split()
    stale = backtest_summary(_both_cell_doc(), "backtest-synthetic-20261103-aaaaaaaaaaaa.json")
    for cell in stale["cells"].values():                      # the summary as the released bundle stores it: no cell verdict, no gate sizes
        for key in ("decidable_by_tests_cell", "gate_cell_n_200", "gate_cell_n_400"):
            cell.pop(key, None)
    models = tmp_path / "models"
    models.mkdir()
    import dataclasses

    bundle = dataclasses.replace(bundle, backtest_summary=stale)
    save_bundle(bundle, models)
    Registry(models).register_model("synthetic", bundle.model_id, stale)
    assert card_mod.backtest_view(load_bundle(bundle.model_id, models).backtest_summary, "both")["decidable"] == "decidable at skill 0.20 only"
    updated = attach_backtest(models, "synthetic", bundle.snapshot_id, {**_both_cell_doc(), "header": {"snapshot_id": bundle.snapshot_id}},
                              "backtest-synthetic-20261103-aaaaaaaaaaaa.json")
    assert updated == [bundle.model_id]
    fresh = load_bundle(bundle.model_id, models).backtest_summary
    assert fresh["cells"]["both"]["decidable_by_tests_cell"] == "undecidable at this n"
    assert card_mod.backtest_view(fresh, "both")["decidable"] == "undecidable at this n"


# ------------------------------------------------------------------ R3.9: the report header records the P2 selection rule
def test_r3_the_backtest_header_records_the_p2_selection_rule_in_force():
    import numpy as np
    import pandas as pd

    from mootcourt import report

    for rule in ("forward", "loto"):
        scores = pd.DataFrame({"x": np.arange(2)})
        scores.attrs["selections"] = [{"rung": "P2", "cell": "a", "selection": rule, "lambda": 0.1}]
        assert report.selection_setting(scores) == rule
    assert report.selection_setting(pd.DataFrame({"x": [1]})) is None
