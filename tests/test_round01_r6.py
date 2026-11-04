"""Round 01, reviewer R6 (practitioner), T-068: the code-side findings and the three items of builder-m's documentation pass.

One group per item: the sidecar check of the doctor and the one-line backtest failure, the gate line's base rate, non-text cards, the
report card's "Tests needed", the gate-power assumptions and the progress lines, ``moot reliability``, the signed zero, the planned units
and the decidable columns of the report document.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

UTC = dt.timezone.utc


# ============================================================================ 1. sidecar files
def test_the_doctor_detects_sidecar_files_in_the_environment_and_names_the_cure(tmp_path):
    from mootcourt.onboarding import check_environment

    site = tmp_path / "venv" / "lib" / "python3.11" / "site-packages"
    style = site / "matplotlib" / "mpl-data" / "stylelib"
    style.mkdir(parents=True)
    (style / "classic.mplstyle").write_text("lines.linewidth: 1.0\n")
    (ok,) = check_environment(site_packages=site, prefix=tmp_path / "venv")
    assert ok["name"] == "environment" and ok["status"] == "ok"
    (style / ".__classic_test_patch.mplstyle").write_bytes(b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X")
    (bad,) = check_environment(site_packages=site, prefix=tmp_path / "venv")
    assert bad["status"] == "fail" and "1 sidecar" in bad["detail"] and "._" in bad["detail"]
    assert "moot backtest" in bad["detail"] and "internal disk" in bad["detail"] and "find " in bad["detail"]
    (site / "._numpy").write_bytes(b"\x00")
    (bad2,) = check_environment(site_packages=site, prefix=tmp_path / "venv")
    assert "2 sidecar" in bad2["detail"]
    # an environment on an external volume is a warning before any sidecar appears
    clean = tmp_path / "other" / "site-packages"
    clean.mkdir(parents=True)
    (warn,) = check_environment(site_packages=clean, prefix=Path("/Volumes/External/clone/.venv"))
    assert warn["status"] == "warn" and "external volume" in warn["detail"] and "internal disk" in warn["detail"]


def test_the_doctor_runs_the_environment_check(tmp_path, monkeypatch):
    from mootcourt import onboarding

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    names = [c["name"] for c in onboarding.run_doctor(now=dt.datetime(2025, 12, 30, tzinfo=UTC), write=False)["checks"]]
    assert "environment" in names


def test_a_sidecar_in_the_plotting_library_fails_the_backtest_with_one_line_not_a_traceback():
    from mootcourt.cli import _user_error_types
    from mootcourt.report import _pyplot
    from mootcourt.storage import SidecarEnvironmentError, sidecar_message

    assert SidecarEnvironmentError in _user_error_types()
    text = ("Cannot decode configuration file PosixPath('/Volumes/x/.venv/lib/python3.11/site-packages/matplotlib/mpl-data/stylelib/"
            ".__classic_test_patch.mplstyle') as utf-8")
    msg = sidecar_message(text)
    assert "._" in msg and "internal disk" in msg and "moot doctor" in msg and ".__classic_test_patch.mplstyle" in msg

    def broken(name):
        raise UnicodeDecodeError("utf-8", b"\xb0", 0, 1, text)

    with pytest.raises(SidecarEnvironmentError, match="internal disk"):
        _pyplot(importer=broken)


# ============================================================================ 2. the gate line's base rate
def test_the_gate_line_names_the_nearest_simulated_base_rate_and_the_cell_own_rate():
    from mootcourt.card import gate_verdict

    gates = {"n_200": 75, "n_400": 150, "base_rate": 0.30, "interval": {"by": "test", "level": 0.9}}
    text = gate_verdict(20, -0.1, 0.2, gates, 0.117)
    assert "nearest simulated base rate, 0.30" in text and "this cell's own rate is 0.117" in text and " at base rate 0.30" not in text
    multi = {**gates, "by_base_rate": {0.09: {"n_200": 175, "n_400": 250, "base_rate": 0.09}, 0.30: {"n_200": 75, "n_400": 150, "base_rate": 0.30}}}
    assert "nearest simulated base rate, 0.09" in gate_verdict(20, -0.1, 0.2, multi, 0.117)
    assert "own rate" not in gate_verdict(20, -0.1, 0.2, gates, None)


# ============================================================================ 3. non-text cards and 8. planned units
def test_a_card_without_text_skips_the_text_fields_and_stores_headline_changed_false():
    from test_round01_r2 import _card, _split

    from mootcourt import card as card_mod

    old, new, bundle, origin, now0, rows = _split()
    row = rows.iloc[0]
    plain = _card(bundle, row, now0, now0, headline="", cell="headline_only")
    doc = card_mod.to_json(plain)
    assert doc["request"]["headline"] == "" and doc["request"]["headline_changed"] is False
    line = next(ln for ln in card_mod.to_markdown(plain).splitlines() if ln.startswith("- Request:"))
    assert "headline" not in line and "image changed" not in line and "planned units per arm: 20000" in line
    text = _card(bundle, row, now0, now0)
    tline = next(ln for ln in card_mod.to_markdown(text).splitlines() if ln.startswith("- Request:"))
    assert "headline \"" in tline and "image changed: no" in tline and "planned units per arm: 20000" in tline and "exposures" not in tline
    assert card_mod.to_json(text)["request"]["headline_changed"] is True
    unequal = _card(bundle, row, now0, now0, impressions_variant=30000)
    uline = next(ln for ln in card_mod.to_markdown(unequal).splitlines() if ln.startswith("- Request:"))
    assert "planned units: 20000 reference, 30000 variant" in uline


def test_the_card_help_and_module_note_say_planned_units():
    from mootcourt import card as card_mod
    from mootcourt.cli import app

    res = CliRunner().invoke(app, ["card", "--help"])
    assert res.exit_code == 0 and "planned units per arm" in res.output.lower()
    assert "headline_changed" in card_mod.__doc__ and "planned units" in card_mod.__doc__


# ============================================================================ 4. tests needed
def test_the_report_card_says_tests_needed_when_the_gates_count_tests():
    from mootcourt.benchmark import gates_heading

    assert gates_heading({"gates_unit": "test", "gates_source": "from gates.json"}).startswith("Tests needed")
    assert gates_heading({"gates_unit": "row", "gates_source": "from gates.json"}).startswith("Rows needed")
    assert gates_heading({"gates_source": "x"}).startswith("Tests needed"), "a card from before the field counts tests, as every gates file does now"


def test_the_report_card_records_the_unit_of_its_gates(make_synth, tmp_path):
    from mootcourt.benchmark import card_markdown, run_report_card
    from mootcourt.ledger import write_ledger

    ledger, _ = make_synth(seed=131, n_tests=160, variants_per_test=2)
    write_ledger(ledger, tmp_path / "led.parquet")
    (tmp_path / "reports").mkdir()
    gates = {"n_200": 75, "n_400": 150, "base_rate": 0.3, "decision_target": 0.9, "reps": 400,
             "by_target": {"0.80": {"n_200": 50, "n_400": 100}, "0.90": {"n_200": 75, "n_400": 150}}, "interval": {"by": "test", "level": 0.9}}
    (tmp_path / "reports" / "gates.json").write_text(json.dumps(gates))       # the gates `moot init` writes count tests (R6's case)
    card = run_report_card(tmp_path / "led.parquet", tmp_path / "reports", bootstrap=20)
    assert card["gates_unit"] == "test"
    assert "Tests needed before a skill difference is decidable" in card_markdown(card) and "Rows needed" not in card_markdown(card)
    card2 = run_report_card(tmp_path / "led.parquet", tmp_path / "reports2", bootstrap=20)      # the report card's own quick gates count rows
    assert card2["gates_unit"] == "row" and "Rows needed" in card_markdown(card2)


# ============================================================================ 5. gate-power assumptions and progress
def test_ledger_dependence_measures_rows_per_test_base_rate_and_icc(make_synth):
    from mootcourt.simulate import ledger_dependence

    ledger, _ = make_synth(seed=132, n_tests=200, variants_per_test=3)
    dep = ledger_dependence(ledger)
    assert dep["rows_per_test"] == pytest.approx(3.0) and dep["n_tests"] == 200
    assert 0.0 < dep["base_rate"] < 1.0 and 0.0 <= dep["icc"] <= 0.99


def test_gate_power_prints_its_assumptions_their_source_and_progress(tmp_path, monkeypatch, make_synth):
    from mootcourt.cli import app
    from mootcourt.ledger import write_ledger

    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    res = CliRunner().invoke(app, ["simulate", "gate-power", "--reps", "20", "--bootstrap", "20", "--base-rate", "0.2", "--no-table",
                                   "--progress-after", "0"])
    assert res.exit_code == 0, res.output
    out = res.output
    assert "assumptions" in out and "rows per test 5.0" in out and "within-test correlation 0.67" in out
    assert "public archive" in out and "nearest" in out and "--source" in out
    assert "still running" in out or "progress:" in out
    (tmp_path / "data" / "ledger").mkdir(parents=True)
    ledger, _ = make_synth(seed=133, n_tests=120, variants_per_test=3)
    write_ledger(ledger, tmp_path / "data" / "ledger" / "ledger.parquet")
    res = CliRunner().invoke(app, ["simulate", "gate-power", "--reps", "20", "--bootstrap", "20", "--source", "synthetic", "--no-table"])
    assert res.exit_code == 0, res.output
    assert "measured on the synthetic ledger" in res.output and "rows per test 3.0" in res.output
    doc = json.loads((tmp_path / "reports" / "gates.json").read_text())
    assert doc["rows_per_test"] == pytest.approx(3.0) and doc["dependence_source"].startswith("measured on the synthetic ledger")
    res = CliRunner().invoke(app, ["simulate", "gate-power", "--reps", "20", "--bootstrap", "20", "--base-rate", "0.2", "--rows-per-test", "2",
                                   "--icc", "0.1", "--no-table"])
    assert res.exit_code == 0 and "given on the command line" in res.output


def test_the_heartbeat_prints_a_progress_line_after_the_delay():
    from mootcourt.cli import Heartbeat

    lines: list[str] = []
    with Heartbeat("the quick gates", delay=0.05, every=0.05, echo=lines.append):
        time.sleep(0.4)
    assert lines and "the quick gates" in lines[0] and "still running" in lines[0] and "s elapsed" in lines[0]
    quiet: list[str] = []
    with Heartbeat("fast", delay=5.0, every=5.0, echo=quiet.append):
        pass
    assert quiet == []


def test_init_and_backtest_take_a_progress_delay(tmp_path, monkeypatch):
    from mootcourt.cli import app

    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(app, ["init", "--dir", str(tmp_path), "--progress-after", "0"])
    assert res.exit_code == 0, res.output
    assert "still running" in res.output and "quick gates" in res.output
    assert CliRunner().invoke(app, ["backtest", "--help"]).output.count("--progress-after") == 1


# ============================================================================ 6. moot reliability
def test_moot_reliability_prints_the_weekly_report(tmp_path):
    from mootcourt.cli import app

    rdir = tmp_path / "reports"
    rdir.mkdir()
    report = {"source": "sample", "as_of": "2025-12-30T00:00:00+00:00", "cells": {
        "checkout_conversion": {"as_of": "2025-12-01T00:00:00+00:00", "n": 5, "n_tests": 5, "brier_skill": -0.062, "brier_skill_lo": -0.2,
                                "brier_skill_hi": 0.1, "rolling_logscore": 1.956, "p0_rolling_logscore": 1.978, "consecutive_below": 0,
                                "drifted": False, "window_weeks": 8},
        "revenue_per_user": {"as_of": "2025-07-02T00:00:00+00:00", "n": 7, "brier_skill": 0.033, "rolling_logscore": 1.921,
                             "p0_rolling_logscore": 1.910, "consecutive_below": 1, "drifted": True}}}
    (rdir / "reliability-sample.json").write_text(json.dumps(report))
    res = CliRunner().invoke(app, ["reliability", "--source", "sample", "--reports-dir", str(rdir)])
    assert res.exit_code == 0, res.output
    assert "report as of 2025-12-30" in res.output
    rows = [ln for ln in res.output.splitlines() if ln.startswith(("checkout_conversion", "revenue_per_user"))]
    assert len(rows) == 2 and "2025-12-01" in rows[0] and "-0.062" in rows[0] and "1.956" in rows[0] and "True" in rows[1]
    as_json = CliRunner().invoke(app, ["reliability", "--source", "sample", "--reports-dir", str(rdir), "--json"])
    assert as_json.exit_code == 0 and json.loads(as_json.output)["cells"]["revenue_per_user"]["drifted"] is True
    missing = CliRunner().invoke(app, ["reliability", "--source", "nope", "--reports-dir", str(rdir)])
    assert missing.exit_code != 0 and "moot join" in missing.output


# ============================================================================ 7. signed zero
def test_a_value_that_rounds_to_zero_prints_without_a_sign():
    from mootcourt import benchmark, card, report

    assert card._num(-0.0004, 2) == "0.00" and card._num(-0.0, 3) == "0.000" and card._num(-0.004, 2) == "0.00" and card._num(-0.006, 2) == "-0.01"
    assert benchmark._num(-0.0) == "0.000" and benchmark._num(-0.0002) == "0.000" and benchmark._num(-0.0006) == "-0.001"
    assert report._fmt(-0.00001) == "0.0000" and report._fmt(-0.00006) == "-0.0001" and report._fmt(-1) == "-1"


# ============================================================================ 9. the decidable columns of the report document
def test_the_report_document_gives_the_decidable_verdict_in_the_unit_of_the_gates():
    from test_review_l import GATES, _bt

    from mootcourt import harness_stats as hs
    from mootcourt.report import build_document, render_markdown

    ledger, sc = _bt()
    by_test = {**GATES, "interval": {"by": "test", "level": 0.9}}
    doc = build_document(sc[sc["rung"].isin(["P0", "P1"])], ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f",
                         command="c", seed=0, gates=by_test, B=20)
    rows = doc["tables"]["aggregate"]
    assert rows and all(r["decidable"] == r["decidable_by_tests"] for r in rows)
    assert all(r["decidable"].startswith(("decidable", "undecidable")) for r in rows)
    assert all(r["decidable_research"] == r["decidable_research_by_tests"] for r in rows)
    assert "tests" in doc["notes"]["decidable_unit"]
    assert hs.BY_ROW_NOT_COMPUTED not in render_markdown(doc)
    # the stats function itself keeps its contract (review N): the by-row verdict is not computed against gates that count tests
    agg = hs.aggregate_scores(sc[sc["rung"] == "P1"], by_test, B=20)
    assert (agg["decidable"] == hs.BY_ROW_NOT_COMPUTED).all()
    with_rows = build_document(sc[sc["rung"].isin(["P0", "P1"])], ledger=ledger, source="upworthy", snapshot_id="s", model_id="m",
                               feature_hash="f", command="c", seed=0, gates=GATES, B=20)
    assert all(r["decidable"].startswith(("decidable", "undecidable")) for r in with_rows["tables"]["aggregate"])
    assert "rows" in with_rows["notes"]["decidable_unit"]
