"""Chunk J (T-052): every paper number traces to a report JSON, and the chunk I review findings.

Covers the paper-extras script, the decision table of the paper, the replay's abstentions by trigger, the released rows of the
trigger-removal ablation, the snapshot check of the trigger table, REV-I-001 (env option parsing) and REV-I-003 (dead helper).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import AMBIENT_ROOT
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
TRIGGERS = ("support", "novelty", "reliability", "instability")
GATES = {"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9,
         "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _extras():
    return _load("paper_extras", ROOT / "scripts" / "paper_extras.py")


def _tables():
    return _load("build_tables", ROOT / "paper" / "build_tables.py")


def _cli(imp, args, root):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env={"MOOTCOURT_DATA_ROOT": str(root)})


@pytest.fixture(scope="module")
def synth():
    from mootcourt.sources import synthetic

    return synthetic.generate(synthetic.SyntheticConfig(seed=61, n_tests=260, variants_per_test=2))[0]


@pytest.fixture(scope="module")
def root(tmp_path_factory, synth):
    """A data root with the main synthetic backtest and the trigger-removal run of novelty and support."""
    import importlib

    r = tmp_path_factory.mktemp("rootj") / "root"
    importlib.import_module("mootcourt.ledger").write_ledger(synth, r / "data" / "ledger" / "ledger.parquet")
    (r / "reports").mkdir(parents=True)
    (r / "reports" / "gates.json").write_text(json.dumps(GATES))
    for extra in ([], ["--drop-trigger", "novelty"], ["--drop-trigger", "support"]):
        res = _cli(importlib.import_module, ["backtest", "--source", "synthetic", "--bootstrap", "30", *extra], r)
        assert res.exit_code == 0, res.output
    return r


def _main(root: Path) -> dict:
    return json.loads(next((root / "reports").glob("backtest-synthetic-*.json")).read_text())


# ------------------------------------------------------------------ paper_extras: the correlation of exposure with the effect
def test_the_exposure_correlation_is_computed_on_admitted_rows_from_the_ledger(synth):
    ex = _extras()
    out = ex.impressions_effect_correlation(synth, "synthetic")
    adm = synth[synth["status"] == "admitted"]
    x = np.log(0.5 * (adm["n_ref"].to_numpy(float) + adm["n_var"].to_numpy(float)))
    z = adm["y"].to_numpy(float) / adm["s"].to_numpy(float)
    assert out["n_rows"] == len(adm)
    assert out["corr_log_impressions_abs_z"] == pytest.approx(np.corrcoef(x, np.abs(z))[0, 1])
    assert out["corr_log_impressions_event"] == pytest.approx(np.corrcoef(x, (z > 1.96).astype(float))[0, 1])
    assert -1.0 <= out["corr_log_impressions_abs_z"] <= 1.0 and -1.0 <= out["corr_log_impressions_event"] <= 1.0
    assert "n_ref" in out["inputs"]["columns"] and out["inputs"]["rows"] == "status == admitted"


def test_the_exposure_correlation_refuses_a_ledger_without_admitted_rows(synth):
    ex = _extras()
    with pytest.raises(ValueError, match="no admitted rows"):
        ex.impressions_effect_correlation(synth.assign(status="low_exposure"), "synthetic")


# ------------------------------------------------------------------ paper_extras: guard admission on no-signal cells
def test_guard_admission_rates_count_positive_lambda_cells_for_each_multiplier():
    ex = _extras()
    out = ex.guard_admission_rates(seeds=range(2), n_tests=80, multipliers=(1.0, 1.5, 2.0))
    rows = {r["multiplier"]: r for r in out["by_multiplier"]}
    assert set(rows) == {1.0, 1.5, 2.0, "off"}
    for m, r in rows.items():
        assert r["cells"] >= 4 and 0 <= r["admitted"] <= r["cells"], m
        assert r["share_admitted"] == pytest.approx(r["admitted"] / r["cells"]) and 0.0 <= r["share_admitted"] <= 1.0
    assert rows[1.0]["admitted"] >= rows[1.5]["admitted"] >= rows[2.0]["admitted"]      # a higher multiplier admits a subset
    assert out["inputs"]["seeds"] == [0, 1] and out["inputs"]["n_tests"] == 80 and out["inputs"]["text_effect_strength"] == 0.0
    assert out["inputs"]["generator"].startswith("mootcourt.sources.synthetic.generate")


# ------------------------------------------------------------------ paper_extras: the tail of the kernel weights
def test_tail_shares_are_fractions_of_the_weight_beyond_the_top_m():
    ex = _extras()
    out = ex.top_m_tail_share(sizes=(300, 600), top_m=20, n_queries=4, seed=3)
    assert [r["contrasts"] for r in out["by_size"]] == [300, 600]
    for r in out["by_size"]:
        for key in ("share_p2_weight", "share_raw_kernel"):
            s = r[key]
            assert 0.0 <= s["p10"] <= s["p90"] <= 1.0 and 0.0 <= s["mean"] <= 1.0, (key, s)
        assert r["n_queries"] == 4 and r["ledger"] in ("generated", "experiments/scale")
    assert out["top_m"] == 20 and out["cell"] == "headline_only"
    all_listed = ex.top_m_tail_share(sizes=(300,), top_m=10**9, n_queries=3, seed=3)
    assert all_listed["by_size"][0]["share_p2_weight"]["mean"] == 0.0         # nothing is beyond a top M that lists every neighbor


def test_the_script_writes_one_report_with_every_value_and_the_inputs_it_came_from(root):
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "paper_extras.py"), "--source", "synthetic", "--guard-seeds", "2", "--guard-tests", "80",
         "--tail-sizes", "300,600", "--tail-top-m", "20", "--tail-queries", "4", "--sensitivity-seeds", "0"],
        env={**__import__("os").environ, "MOOTCOURT_DATA_ROOT": str(root)}, capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    sid = _main(root)["header"]["snapshot_id"]
    path = root / "reports" / f"paper-extras-synthetic-{sid}.json"
    assert path.exists() and f"wrote {path}" in out.stdout
    doc = json.loads(path.read_text())
    assert doc["header"]["source"] == "synthetic" and doc["header"]["snapshot_id"] == sid
    assert doc["header"]["main_report"].startswith("backtest-synthetic-")
    assert {"guard_admission_rates", "top_m_tail_share", "impressions_effect_correlation", "trigger_ablation_released_rows"} <= set(doc)
    assert 0 <= doc["guard_admission_rates"]["by_multiplier"][0]["share_admitted"] <= 1
    assert doc["impressions_effect_correlation"]["n_rows"] == _main(root)["header"]["admitted_rows"]
    runs = {r["dropped_trigger"]: r for r in doc["trigger_ablation_released_rows"]["runs"]}
    assert set(runs) == {"novelty", "support"}                               # the runs that exist on this root
    rel = json.loads(next((root / "reports" / "ablations").glob("backtest-synthetic-*--drop-trigger-novelty.json")).read_text())
    want = next(r for r in rel["tables"]["released_rows"] if r["cell"] == "ALL" and r["rung"] == "P2")
    assert runs["novelty"]["released"]["n"] == want["n"] and runs["novelty"]["released"]["logscore"] == want["logscore"]
    assert runs["novelty"]["report"].endswith("--drop-trigger-novelty.json")
    assert doc["header"]["created_by"] == "scripts/paper_extras.py" and doc["header"]["differences_from_docs"]


def test_the_script_computes_the_slow_values_only_for_the_synthetic_source(root, tmp_path, synth):
    ex = _extras()
    doc = ex.build_extras("upworthy", synth.assign(source="upworthy"), root / "reports", experiments_dir=tmp_path, snapshot_id="s1",
                          guard_seeds=range(1), guard_tests=60, tail_sizes=(200,), tail_top_m=10, tail_queries=2, tail_seed=1)
    assert doc["guard_admission_rates"] is None and doc["top_m_tail_share"] is None
    assert doc["impressions_effect_correlation"]["n_rows"] > 0
    assert "synthetic" in doc["header"]["not_computed_reason"]


# ------------------------------------------------------------------ released rows of the trigger-removal ablation
def _frame(rows):
    cols = ["row_id", "test_id", "cell", "rung", "origin", "abstain", "logscore", "brier_event", "brier_base", "event", "p_sig",
            "direction_correct", "crps", "lo80", "hi80", "lo90", "hi90", "y"]
    return pd.DataFrame([{c: r.get(c, 0.0) for c in cols} for r in rows])


def _row(i, abstain, logscore, hit, event=0.0, p_sig=0.1, rung="P2", cell="a"):
    return {"row_id": f"r{i}", "test_id": f"t{i // 2}", "cell": cell, "rung": rung, "origin": "2014-01-01", "abstain": abstain,
            "logscore": logscore, "brier_event": (p_sig - event) ** 2, "brier_base": 0.1, "event": event, "p_sig": p_sig,
            "direction_correct": hit}


def test_released_rows_are_those_abstained_in_the_main_run_and_issued_in_the_ablation():
    from mootcourt import harness_stats as hs

    main = _frame([_row(0, True, -1.0, 1.0), _row(1, True, -2.0, 0.0), _row(2, True, -3.0, 1.0), _row(3, False, -0.5, 1.0),
                   _row(4, True, -9.0, 1.0)])
    abl = main.copy()
    abl["abstain"] = [False, False, True, False, True]                    # rows 0 and 1 are released; 2 and 4 still abstain; 3 was issued before
    got = hs.released_rows(main, abl, GATES, B=20, seed=0, rung="P2")
    all_row = next(r for r in got if r["cell"] == "ALL")
    assert all_row["rung"] == "P2" and all_row["n"] == 2 and all_row["n_tests"] == 1
    assert all_row["logscore"] == pytest.approx(-1.5) and all_row["direction_accuracy"] == pytest.approx(0.5)
    assert all_row["brier"] == pytest.approx(0.01) and all_row["brier_skill"] == pytest.approx(1.0 - 0.01 / 0.1)
    assert all_row["n_abstained_main"] == 4 and all_row["n_abstained_ablation"] == 2
    for key in ("logscore", "brier_skill", "direction_accuracy"):
        assert {key + "_lo", key + "_hi"} <= set(all_row)


def test_released_rows_of_a_run_that_releases_nothing_is_an_empty_row_not_an_error():
    from mootcourt import harness_stats as hs

    main = _frame([_row(0, True, -1.0, 1.0), _row(1, False, -2.0, 0.0)])
    got = hs.released_rows(main, main.copy(), GATES, B=20, seed=0, rung="P2")
    r = next(x for x in got if x["cell"] == "ALL")
    assert r["n"] == 0 and r["logscore"] is None and r["brier_skill"] is None and r["direction_accuracy"] is None


def test_released_rows_refuse_a_main_run_that_scored_other_rows_or_other_values():
    from mootcourt import harness_stats as hs

    main = _frame([_row(0, True, -1.0, 1.0), _row(1, False, -2.0, 0.0)])
    other = _frame([_row(0, False, -1.0, 1.0), _row(7, False, -2.0, 0.0)])
    with pytest.raises(ValueError, match="same rows"):
        hs.released_rows(main, other, GATES, B=20, seed=0, rung="P2")
    changed = main.copy()
    changed["logscore"] = changed["logscore"] - 0.1
    with pytest.raises(ValueError, match="scored differently"):
        hs.released_rows(main, changed, GATES, B=20, seed=0, rung="P2")


def test_the_trigger_removal_report_prints_the_released_rows_and_the_main_tables_are_unchanged(root):
    main_doc = _main(root)
    assert "released_rows" not in main_doc["tables"]
    abl = next((root / "reports" / "ablations").glob("backtest-synthetic-*--drop-trigger-novelty.json"))
    doc = json.loads(abl.read_text())
    rr = doc["tables"]["released_rows"]
    main_s = pd.read_parquet(next((root / "reports").glob("scores-synthetic-*.parquet")))
    abl_s = pd.read_parquet(next((root / "reports" / "ablations").glob("scores-synthetic-*--drop-trigger-novelty.parquet")))
    p2m, p2a = (s[s["rung"] == "P2"].set_index("row_id").sort_index() for s in (main_s, abl_s))
    released = p2m.index[p2m["abstain"].to_numpy() & ~p2a["abstain"].to_numpy()]
    assert len(released) > 0
    row = next(r for r in rr if r["cell"] == "ALL" and r["rung"] == "P2")
    assert row["n"] == len(released)
    assert row["logscore"] == pytest.approx(p2a.loc[released, "logscore"].mean(), abs=1e-4)
    assert row["direction_accuracy"] == pytest.approx(p2a.loc[released, "direction_correct"].mean(), abs=1e-4)
    assert doc["header"]["released_rows_reference"]["main_report"] == next((root / "reports").glob("backtest-synthetic-*.json")).name
    assert "released_rows" in json.loads(json.dumps(doc["notes"])) or "released" in doc["notes"]["abstention_triggers"].lower()
    # the aggregate table of an ablation is what it was before this field existed: only additions
    keys_before = {"aggregate", "decision_value", "abstention", "origins", "score_by_origin", "score_by_year", "reliability_bins", "coverage"}
    assert keys_before <= set(doc["tables"])
    md = abl.with_suffix(".md").read_text()
    assert "Released rows" in md and f"{row['n']}" in md


def test_a_trigger_run_without_a_main_scores_file_says_so_and_prints_no_released_rows(imp, tmp_path, synth):
    r = tmp_path / "bare"
    imp("mootcourt.ledger").write_ledger(synth, r / "data" / "ledger" / "ledger.parquet")
    (r / "reports").mkdir(parents=True)
    (r / "reports" / "gates.json").write_text(json.dumps(GATES))
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--drop-trigger", "support"], r)
    assert res.exit_code == 0, res.output
    assert "no released rows" in res.output.lower() or "main run's scores" in res.output
    doc = json.loads(next((r / "reports" / "ablations").glob("backtest-synthetic-*--drop-trigger-support.json")).read_text())
    assert "released_rows" not in doc["tables"]


def test_a_changed_aggregate_cannot_hide_behind_the_new_field(imp, root, synth):
    """build_document with and without the reference scores gives the same aggregate, by construction."""
    rep = imp("mootcourt.report")
    abl_dir = root / "reports" / "ablations"
    scores = pd.read_parquet(next(abl_dir.glob("scores-synthetic-*--drop-trigger-novelty.parquet")))
    ref = pd.read_parquet(next((root / "reports").glob("scores-synthetic-*.parquet")))
    kw = dict(ledger=synth, source="synthetic", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=GATES, B=20)
    a = rep.build_document(scores, **kw)
    b = rep.build_document(scores, reference_scores=ref, **kw)
    assert a["tables"]["aggregate"] == b["tables"]["aggregate"]
    assert "released_rows" in b["tables"] and "released_rows" not in a["tables"]


# ------------------------------------------------------------------ the replay counts abstentions by trigger
@pytest.fixture(scope="module")
def replay_run(synth):
    mod = _load("replay_weekly", ROOT / "scripts" / "replay_weekly.py")
    sub = __import__("mootcourt.sources.synthetic", fromlist=["generate"]).generate(
        __import__("mootcourt.sources.synthetic", fromlist=["SyntheticConfig"]).SyntheticConfig(seed=71, n_tests=170, variants_per_test=2))[0]
    doc, records = mod.replay(sub, "synthetic", "snap-test", keep_records=True)
    return doc, records


def test_each_week_counts_its_abstained_cards_by_trigger(replay_run):
    doc, records = replay_run
    seen_reason = False
    for w in doc["weeks"]:
        by = w["abstained_by_trigger"]
        assert set(by) == set(TRIGGERS)
        assert all(0 <= v <= w["abstained"] for v in by.values())
        if w["abstained"]:
            assert w["abstained"] <= sum(by.values())                      # every abstained card carries at least one reason
        seen_reason |= sum(by.values()) > 0
    assert seen_reason
    tot = doc["totals"]["abstained_by_trigger"]
    assert tot == {t: sum(w["abstained_by_trigger"][t] for w in doc["weeks"]) for t in TRIGGERS}
    from_cards = {t: sum(1 for r in records if t in r["card"]["abstention"]["reasons"]) for t in TRIGGERS}
    assert tot == from_cards                                               # recomputed from the cards themselves
    by_week = {}
    for r in records:
        for t in r["card"]["abstention"]["reasons"]:
            by_week.setdefault((r["issue_week"], t), 0)
            by_week[(r["issue_week"], t)] += 1
    for w in doc["weeks"]:
        for t in TRIGGERS:
            assert w["abstained_by_trigger"][t] == by_week.get((w["week_start"], t), 0)


# ------------------------------------------------------------------ the paper's decision table
def _decision_rep(path="x/backtest-upworthy-s1.json"):
    rows = []
    for origin, caps in (("2014-01-01", (0.2, 0.3, 0.7)), ("2014-04-01", (0.4, 0.5, 0.9)), ("ALL", (0.9, 0.9, 0.9))):
        for (pol, rg), cap in zip((("random", "none"), ("p_win", "P2"), ("oracle", "none")), caps):
            rows.append({"origin": origin, "policy": pol, "rung": rg, "captured_fraction": cap, "regret": 10.0 * (1 - cap)})
    return {"_path": path, "header": {"snapshot_id": "s1"}, "tables": {"decision_value": rows}}


def test_the_decision_table_means_exclude_the_pooled_row_and_say_so(tmp_path):
    bt = _tables()
    bt.decision_table(_decision_rep(), "upworthy", str(tmp_path))
    text = (tmp_path / "decision-upworthy.tex").read_text()
    first = text.splitlines()[0]
    assert "excludes the pooled" in first and "2 per-origin rows" in first
    body = {ln.split("&")[0].strip() + "|" + ln.split("&")[1].strip(): ln for ln in text.splitlines() if "&" in ln and "policy" not in ln}
    assert "0.300" in body["random|none"] and "0.400" in body["p\\_win|P2"] and "0.800" in body["oracle|none"]   # means over the two origins
    assert "0.900" not in text


def test_a_decision_table_with_only_the_pooled_row_is_refused(tmp_path):
    bt = _tables()
    rep = _decision_rep()
    rep["tables"]["decision_value"] = [r for r in rep["tables"]["decision_value"] if r["origin"] == "ALL"]
    with pytest.raises(ValueError, match="per-origin"):
        bt.decision_table(rep, "upworthy", str(tmp_path))


def test_the_generated_decision_tables_match_the_reports_on_the_data_root():
    if AMBIENT_ROOT is None:
        pytest.skip("MOOTCOURT_DATA_ROOT was not exported")
    reports = Path(AMBIENT_ROOT) / "reports"
    checked = 0
    for source in ("upworthy", "asos", "synthetic"):
        files = sorted(reports.glob(f"backtest-{source}-*.json"))
        table = ROOT / "paper" / "tables" / f"decision-{source}.tex"
        if not files or not table.exists():
            continue
        doc = json.loads(files[-1].read_text())
        # round 00 (T-054): the table also holds the 10 and 50 percent budgets; the generated means are the 25 percent rows
        rows = [r for r in doc["tables"]["decision_value"] if r["origin"] != "ALL" and r.get("budget", 0.25) == 0.25]
        text = table.read_text()
        assert files[-1].name in text.splitlines()[0], "the table was built from another report"
        for pol, rg in {(r["policy"], r["rung"]) for r in rows}:
            mean = np.mean([r["captured_fraction"] for r in rows if r["policy"] == pol and r["rung"] == rg])
            line = next(ln for ln in text.splitlines() if ln.startswith(f"{pol.replace('_', chr(92) + '_')} & {rg.replace('_', chr(92) + '_')} &"))
            assert f"{mean:.3f}" in line, (source, pol, rg, mean, line)
            checked += 1
    if not checked:
        pytest.skip("no generated decision table next to a report on this data root")


# ------------------------------------------------------------------ REV-I-002: the trigger table checks the snapshot
def _agg(rate=0.1):
    return [{"cell": "ALL", "rung": "P2", "abstention_rate": rate, "n_nonabstained": 10, "logscore_nonabstained": -1.0,
             "logscore_nonabstained_lo": -1.1, "logscore_nonabstained_hi": -0.9, "brier_nonabstained": 0.1,
             "brier_nonabstained_lo": 0.09, "brier_nonabstained_hi": 0.11, "direction_accuracy_nonabstained": 0.5,
             "direction_accuracy_nonabstained_lo": 0.4, "direction_accuracy_nonabstained_hi": 0.6}]


def _trigger_dir(tmp_path, sid_main, sid_run):
    (tmp_path / "ablations").mkdir()
    main = {"_path": str(tmp_path / f"backtest-upworthy-{sid_main}.json"), "header": {"snapshot_id": sid_main}, "tables": {"aggregate": _agg()}}
    for name in TRIGGERS:
        doc = {"header": {"snapshot_id": sid_run}, "tables": {"aggregate": _agg(0.05)}}
        (tmp_path / "ablations" / f"backtest-upworthy-{sid_run}--drop-trigger-{name}.json").write_text(json.dumps(doc))
    return main


def test_the_trigger_table_fails_naming_both_ids_when_a_run_is_from_another_snapshot(tmp_path):
    bt = _tables()
    main = _trigger_dir(tmp_path, "20261103-aaaa", "20261104-bbbb")
    with pytest.raises(ValueError) as exc:
        bt.trigger_ablation_table(main, str(tmp_path), "upworthy", str(tmp_path))
    assert "20261103-aaaa" in str(exc.value) and "20261104-bbbb" in str(exc.value)


def test_the_trigger_table_is_written_when_the_snapshots_agree_and_prints_the_released_rows(tmp_path):
    bt = _tables()
    main = _trigger_dir(tmp_path, "s1", "s1")
    for name in TRIGGERS:
        p = next((tmp_path / "ablations").glob(f"*--drop-trigger-{name}.json"))
        doc = json.loads(p.read_text())
        doc["tables"]["released_rows"] = [{"cell": "ALL", "rung": "P2", "n": 7, "n_tests": 4, "logscore": -0.954, "logscore_lo": -1.2,
                                           "logscore_hi": -0.7, "brier_skill": -0.02, "brier_skill_lo": -0.1, "brier_skill_hi": 0.05,
                                           "direction_accuracy": 0.453, "direction_accuracy_lo": 0.3, "direction_accuracy_hi": 0.6}]
        p.write_text(json.dumps(doc))
    bt.trigger_ablation_table(main, str(tmp_path), "upworthy", str(tmp_path))
    assert (tmp_path / "trigger-ablation-upworthy.tex").exists()
    text = (tmp_path / "trigger-released-upworthy.tex").read_text()
    assert "released rows" in text and "-0.954" in text and "0.453" in text and "-0.020" in text and "drop reliability" in text


# ------------------------------------------------------------------ REV-I-003
def test_the_unused_model_logscore_helper_is_gone_and_the_forecast_helper_stays(imp):
    loop = imp("mootcourt.loop")
    assert not hasattr(loop, "_model_logscore")
    assert hasattr(loop, "_forecast_logscore")
    src = (ROOT / "src" / "mootcourt" / "loop.py").read_text()
    assert "_model_logscore" not in src


# ------------------------------------------------------------------ REV-I-001: env options with and without arguments
@pytest.fixture
def env_setup(imp, tmp_path, monkeypatch):
    from test_simulators import _info

    root = tmp_path / "dataroot"
    root.mkdir()
    (root / "agent.py").write_text("print('null')\n")
    ok = tmp_path / "ok.py"
    ok.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    return imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators"), _info(imp), f"python3 {root / 'agent.py'}", f"python3 {ok}"


def test_env_options_that_take_an_argument_consume_it_and_the_shell_string_is_still_read(env_setup):    # REV-I-001
    stdio, base, info, inside, _ok = env_setup
    bad = [
        ["env", "-uSHELL", "sh", "-c", inside],
        ["env", "-u", "SHELL", "sh", "-c", inside],
        ["env", "-CSomeDir", "sh", "-c", inside],
        ["env", "-C", "SomeDir", "sh", "-c", inside],
        ["env", "--unset=SHELL", "sh", "-c", inside],
        ["env", "--chdir=SomeDir", "sh", "-c", inside],
        ["env", "--unset", "SHELL", "sh", "-c", inside],
        ["env", "-iu", "SHELL", "sh", "-c", inside],                    # a cluster that ends in an option with an argument
        ["env", "-iuSHELL", "sh", "-c", inside],
        ["env", "-uS", "sh", "-c", inside],                             # the variable is named S, it is not -S
        ["env", "-u", "S", "sh", "-c", inside],
        ["env", "-S", inside],                                          # a bare -S still splits
        ["env", "--split-string", inside],
        ["env", "-iS", inside],
        ["env", "-uSHELL", "-S", inside],                               # both in one command
        ["env", "-a", "x", "-S", f"sh -c '{inside}'"],
    ]
    for command in bad:
        with pytest.raises(base.SimulatorError, match="data root"):
            stdio.StdioSimulator(command, info)


def test_env_options_do_not_turn_a_harmless_command_into_a_refusal(env_setup):
    stdio, _base, info, _inside, ok = env_setup
    for command in (["env", "-uSHELL", "sh", "-c", ok], ["env", "-u", "SHELL", "sh", "-c", ok], ["env", "-CSomeDir", "sh", "-c", ok],
                    ["env", "--unset=SHELL", "sh", "-c", ok], ["env", "-iS", ok], ["env", "-S", ok], ["env", "--split-string", ok]):
        stdio.StdioSimulator(command, info)
