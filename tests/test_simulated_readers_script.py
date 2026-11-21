"""The script of the simulated readers, end to end. A stand-in program plays the model and a synthetic ledger the archive."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from mootcourt import harness
from mootcourt.simulators.readers.protocol import MODELS
from mootcourt.sources import synthetic

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "simulated_readers.py"
_spec = importlib.util.spec_from_file_location("fake_reader_tool", ROOT / "tests" / "fixtures" / "fake_reader_tool.py")
fake_reader_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_reader_tool)


def run_script(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *(str(a) for a in args)], capture_output=True, text=True, cwd=ROOT)


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    """A ledger and its saved row scores in the archive's shape, with a planted word that decides the direction."""
    folder = tmp_path_factory.mktemp("archive")
    ledger = synthetic.generate(synthetic.SyntheticConfig(seed=71, n_tests=70, variants_per_test=2,
                                                          cell_params={"headline_only": (0.0, 0.5)}, s_scale=1.0))[0]
    features = []
    for row in ledger.itertuples():
        words = json.loads(row.features_json)["headline"]
        planted = " amazing" if row.y > 0 else ""
        features.append(json.dumps({
            "headline": f"{words} story about people and places today {row.variant_id}{planted}",
            "reference_headline": f"a plain story about people and places today {row.test_id}",
            "post_launch": {"clicks_ref": 150, "clicks_var": 150 + (40 if row.y > 0 else -40)}}))
    # one reference arm serves every variant of a test, so its count is the same on each row of the test
    ledger = ledger.assign(features_json=features, n_ref=ledger.groupby("test_id")["n_ref"].transform("first"))
    rungs = harness.default_rungs("synthetic", ledger, "text_lr", baselines=True)
    scores = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger), source="synthetic")
    ledger_path, scores_path = folder / "ledger.parquet", folder / "scores-synthetic-20260101-0123456789ab.parquet"
    ledger.to_parquet(ledger_path)
    scores.to_parquet(scores_path)
    return ledger_path, scores_path


LEDGER = None


def plan_into(folder, archive):
    r = run_script("plan", "--ledger", archive[0], "--scores", archive[1], "--out", folder)
    assert r.returncode == 0, r.stderr
    return json.loads((Path(folder) / "plan.json").read_text())


@pytest.fixture(scope="module")
def planned(tmp_path_factory, archive):
    folder = tmp_path_factory.mktemp("plan")
    plan_into(folder, archive)
    return folder


def _fake(tmp_path_factory, **options):
    return fake_reader_tool.make_fake(tmp_path_factory.mktemp("fake"), **options)


def full_run(folder, planned, archive, program, models=MODELS):
    for m in models:
        r = run_script("run", "--model", m, "--plan", planned, "--transcripts", folder / "t", "--allow-model-calls", "--program", program,
                       "--workers", "8")
        assert r.returncode == 0, r.stderr
    r = run_script("score", "--plan", planned, "--transcripts", folder / "t", "--ledger", archive[0], "--out", folder / "o", "--commit", "aaaaaaa")
    assert r.returncode == 0, r.stderr
    return {m: json.loads(next((folder / "o").glob(f"simulated-readers-{m}-*.json")).read_text()) for m in models}


@pytest.fixture(scope="module")
def planted_run(tmp_path_factory, planned, archive):
    folder = tmp_path_factory.mktemp("planted")
    program = _fake(tmp_path_factory, mode="planted")
    return folder, program, full_run(folder, planned, archive, program)


def test_run_refuses_without_the_flag(tmp_path, planned, tmp_path_factory):
    program = _fake(tmp_path_factory, mode="planted")
    r = run_script("run", "--model", "claude-opus-5-5", "--plan", planned, "--transcripts", tmp_path, "--program", program)
    assert r.returncode == 2 and "model calls are not allowed" in r.stderr and not any(tmp_path.iterdir()) and program.calls() == 0


def test_run_refuses_a_model_outside_the_three(tmp_path, planned):
    r = run_script("run", "--model", "some-other-model", "--plan", planned, "--transcripts", tmp_path, "--allow-model-calls")
    assert r.returncode != 0 and not any(tmp_path.iterdir())


def test_score_refuses_while_calls_are_outstanding(tmp_path, planned, archive, tmp_path_factory):
    program = _fake(tmp_path_factory, mode="planted")
    one_model_done = tmp_path / "t"
    assert run_script("run", "--model", MODELS[0], "--plan", planned, "--transcripts", one_model_done, "--allow-model-calls",
                      "--program", program, "--workers", "8").returncode == 0
    r = run_script("score", "--plan", planned, "--transcripts", one_model_done, "--ledger", archive[0], "--out", tmp_path / "o",
                   "--commit", "aaaaaaa")
    assert r.returncode == 5 and "outstanding" in r.stderr and not list((tmp_path / "o").glob("*.json"))
    assert MODELS[1] in r.stderr and MODELS[0] + ":" not in r.stderr


def test_planted_effect_is_recovered_end_to_end(planted_run, planned):
    folder, _, reports = planted_run
    rep = reports["claude-opus-5-5"]
    assert rep["plain"]["accuracy"] > 0.8 and rep["readings"]["plain_minus_always_reference"]["verdict"] == "above"
    assert rep["counts"]["calls_ok"] == rep["counts"]["calls_planned"] > 0 and rep["commit"] == "aaaaaaa"
    plan = json.loads((planned / "plan.json").read_text())
    assert rep["counts"]["calls_planned"] == plan["calls"]["per_model"]
    assert rep["methods"]["text_with_panel"]["without_equals_saved_share"] == 1.0
    assert rep["readings"]["text_with_panel_minus_text"]["family_size"] == 3
    assert rep["probes"]["pairs"]["direction_accuracy"] > 0.8 and rep["probes"]["completion"]["n_pairs"] > 0
    assert rep["tool_versions"] == {"fake-1": rep["counts"]["calls_ok"]} and rep["reported_models"] == {"claude-opus-5-5": rep["counts"]["calls_ok"]}
    assert set(rep["methods"]["audience_brief"]["notes"]) == set(rep["by_origin"]) - {min(rep["by_origin"])}


def test_the_other_models_get_reports_without_a_verdict_and_an_agreement_report(planted_run):
    folder, _, reports = planted_run
    assert "verdict" not in reports["claude-haiku-5-5"]["readings"]["plain_minus_always_reference"]
    agreement = json.loads(next((folder / "o").glob("simulated-readers-agreement-*.json")).read_text())
    assert len(agreement["pairs"]) == 3 and all(p["agree_share"] == 1.0 for p in agreement["pairs"].values())
    assert sorted(p.name for p in (folder / "o").iterdir()) == sorted(
        [f"simulated-readers-{m}-20260101-0123456789ab.json" for m in MODELS] + ["simulated-readers-agreement-20260101-0123456789ab.json"])


def test_a_second_run_makes_no_call(planted_run, planned, archive):
    folder, program, _ = planted_run
    n = program.calls()
    full_run(folder, planned, archive, program)
    assert program.calls() == n > 0


def test_score_never_calls_a_model(planted_run, planned, archive, tmp_path):
    folder, program, reports = planted_run
    n = program.calls()
    r = run_script("score", "--plan", planned, "--transcripts", folder / "t", "--ledger", archive[0], "--out", tmp_path, "--commit", "bbbbbbb")
    assert r.returncode == 0 and program.calls() == n
    again = json.loads(next(tmp_path.glob("simulated-readers-claude-opus-5-5-*.json")).read_text())
    assert again["plain"] == reports["claude-opus-5-5"]["plain"] and again["commit"] == "bbbbbbb"


def test_a_reader_that_answers_at_random_is_not_shown_to_beat_the_baseline(tmp_path, planned, archive, tmp_path_factory):
    rep = full_run(tmp_path, planned, archive, _fake(tmp_path_factory, mode="random"), models=MODELS)["claude-opus-5-5"]
    assert rep["readings"]["plain_minus_always_reference"]["verdict"] in {"contains_zero", "below"}


def test_run_stops_after_five_transport_failures(tmp_path, planned, tmp_path_factory):
    fake_always_limit = _fake(tmp_path_factory, usage_limit_text_exit_zero=True)
    r = run_script("run", "--model", "claude-opus-5-5", "--plan", planned, "--transcripts", tmp_path, "--allow-model-calls",
                   "--program", fake_always_limit, "--workers", "1")
    assert r.returncode == 3 and fake_always_limit.calls() == 5 and "outstanding" in r.stderr


def test_plan_is_repeatable_and_makes_no_call(tmp_path, archive):
    a, b = plan_into(tmp_path / "a", archive), plan_into(tmp_path / "b", archive)
    assert a["sha256"] == b["sha256"] and a["calls"]["per_model"] == sum(a["calls"]["by_kind"].values())
    assert set(a["sha256"]) == {"arms.parquet", "contrasts.parquet", "feeds.parquet", "probes.json"}
    assert a["snapshot"] == "20260101-0123456789ab" and a["calls"]["all_models"] == 3 * a["calls"]["per_model"]
    assert a["calls"]["by_kind"]["brief"] == a["calls"]["by_kind"]["examples"] < a["calls"]["by_kind"]["plain"]
    feeds = pd.read_parquet(tmp_path / "a" / "feeds.parquet")
    assert a["calls"]["by_kind"]["plain"] == 10 * feeds.groupby("block_id").feed_index.nunique().sum() == 10 * a["counts"]["feeds"]


def test_plan_stops_when_the_archive_counts_are_expected_and_not_found(tmp_path, archive):
    r = run_script("plan", "--ledger", archive[0], "--scores", archive[1], "--out", tmp_path, "--expect-archive-counts")
    assert r.returncode == 2 and "1771" in r.stderr


def test_forbidden_file_names_are_refused(tmp_path):
    # the word may sit in the file's name or in any folder of its path
    for name in ("upworthy-confirmatory.parquet", "upworthy-holdout.parquet", "undeployed.parquet", "Holdout/ledger.parquet",
                 "data/upworthy-confirmatory/ledger.parquet"):
        r = run_script("plan", "--ledger", tmp_path / name, "--scores", "s", "--out", tmp_path / "out")
        assert r.returncode != 0 and "refused" in r.stderr and not (tmp_path / "out").exists()


def test_the_canary_stores_the_start_record_and_fails_on_a_listed_tool(tmp_path, tmp_path_factory):
    clean = _fake(tmp_path_factory, mode="planted")
    r = run_script("canary", "--model", "claude-opus-5-5", "--transcripts", tmp_path, "--allow-model-calls", "--program", clean)
    assert r.returncode == 0, r.stderr
    record = json.loads((tmp_path / "canary-claude-opus-5-5.json").read_text())
    assert record["tools"] == [] and record["servers"] == [] and record["start_record"]["subtype"] == "init"
    assert len(record["headlines"]) == 5 and len(json.loads(record["reply_text"])["clicks"]) == 5
    loaded = _fake(tmp_path_factory, mode="planted", start_tools=["Bash"])
    r = run_script("canary", "--model", "claude-sonnet-5-5", "--transcripts", tmp_path, "--allow-model-calls", "--program", loaded)
    assert r.returncode == 4 and "Bash" in r.stderr
    assert run_script("canary", "--model", "claude-opus-5-5", "--transcripts", tmp_path / "x").returncode == 2
    assert {"PATH", "HOME"} <= set(record["env_names"]) and record["tool_version"] == "fake-1"


def test_the_canary_fails_when_the_reply_cannot_be_read_or_the_tool_does_not_say_what_it_is(tmp_path, tmp_path_factory):
    for options, word in (({"refuse": True}, "reply"), ({"mode": "planted", "no_version": True}, "version")):
        r = run_script("canary", "--model", "claude-opus-5-5", "--transcripts", tmp_path, "--allow-model-calls", "--program",
                       _fake(tmp_path_factory, **options))
        assert r.returncode == 4 and word in r.stderr, r.stderr


def test_a_refused_note_is_reported_and_does_not_block_the_score(tmp_path, planned, archive, tmp_path_factory):
    reports = full_run(tmp_path, planned, archive, _fake(tmp_path_factory, mode="planted", refuse_some_notes=True))
    brief = reports["claude-opus-5-5"]["methods"]["audience_brief"]
    assert brief["notes_missing"] and set(brief["notes_missing"]).isdisjoint(brief["notes"])
    origins = set(reports["claude-opus-5-5"]["by_origin"])
    assert set(brief["notes_missing"]) | set(brief["notes"]) == origins - {min(origins)}
    assert brief["no_reader"] > 0 and reports["claude-opus-5-5"]["counts"]["calls_refusal"] == len(brief["notes_missing"])


def test_a_labelled_score_and_the_comparison_of_two_transports(planted_run, planned, archive, tmp_path):
    folder, program, reports = planted_run
    n, out, stamp = program.calls(), tmp_path / "o", "20260101-0123456789ab"
    score = ("score", "--plan", planned, "--transcripts", folder / "t", "--ledger", archive[0], "--out", out)
    assert run_script(*score, "--commit", "aaaaaaa").returncode == 0
    assert run_script(*score, "--commit", "bbbbbbb", "--label", "run12-api").returncode == 0
    labelled = json.loads((out / f"simulated-readers-claude-opus-5-5-run12-api-{stamp}.json").read_text())
    assert labelled["run_label"] == "run12-api" and labelled["plain"] == reports["claude-opus-5-5"]["plain"]
    assert "run_label" not in json.loads((out / f"simulated-readers-claude-opus-5-5-{stamp}.json").read_text())
    r = run_script("compare", "--plan", planned, "--tool", folder / "t", "--api", folder / "t", "--reports", out, "--label", "run12-api",
                   "--out", out, "--commit", "ccccccc")
    assert r.returncode == 0, r.stderr
    rep = json.loads((out / f"simulated-readers-transport-claude-opus-5-5-{stamp}.json").read_text())
    assert rep["plain"]["agree_share"] == 1.0 and rep["plain"]["accuracy_api_minus_tool"]["estimate"] == 0.0
    assert rep["readings"]["weights_minus_plain"]["api"] == labelled["readings"]["weights_minus_plain"]
    assert rep["commits"] == {"tool": "aaaaaaa", "api": "bbbbbbb"} and rep["commit"] == "ccccccc" and rep["run_label"] == "run12-api"
    assert program.calls() == n                                   # neither stage called a model


def test_compare_refuses_while_a_run_has_calls_outstanding(planted_run, planned, tmp_path):
    folder, _, _ = planted_run
    r = run_script("compare", "--plan", planned, "--tool", folder / "t", "--api", tmp_path / "empty", "--reports", folder / "o",
                   "--label", "run12-api", "--out", tmp_path / "o", "--commit", "ccccccc")
    assert r.returncode == 5 and "the api run has calls outstanding" in r.stderr and not (tmp_path / "o").exists()


def test_the_api_transport_also_refuses_without_the_flag(tmp_path):
    for stage in (("canary",), ("run", "--plan", tmp_path)):
        r = run_script(*stage, "--model", "claude-opus-5-5", "--transcripts", tmp_path / "t", "--transport", "api")
        assert r.returncode == 2 and "model calls are not allowed" in r.stderr and not (tmp_path / "t").exists()


def test_a_link_with_a_plain_name_to_a_forbidden_file_is_refused(tmp_path):
    target = tmp_path / "upworthy-holdout.parquet"
    target.write_bytes(b"")
    (tmp_path / "ledger.parquet").symlink_to(target)
    r = run_script("plan", "--ledger", tmp_path / "ledger.parquet", "--scores", "s", "--out", tmp_path / "out")
    assert r.returncode != 0 and "refused" in r.stderr and not (tmp_path / "out").exists()


@pytest.mark.parametrize("value", ["x", "HEAD", "abc12", "g123456", "a" * 41])
def test_a_commit_that_is_not_a_hash_is_refused(tmp_path, planned, value):
    for stage in (("score", "--plan", planned, "--transcripts", tmp_path, "--ledger", tmp_path / "l", "--out", tmp_path / "o"),
                  ("compare", "--plan", planned, "--tool", tmp_path, "--api", tmp_path, "--reports", tmp_path, "--label", "n",
                   "--out", tmp_path / "o")):
        r = run_script(*stage, "--commit", value)
        assert r.returncode == 2 and "commit" in r.stderr and not (tmp_path / "o").exists()
