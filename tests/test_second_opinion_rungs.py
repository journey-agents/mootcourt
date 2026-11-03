"""T-030 contracts: the second opinion as a harness rung, the earned weight, the contamination split and the card display."""
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=dt.timezone.utc)
GATES = {"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9,
         "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}


def _cli(imp, args, root=None):
    env = {"MOOTCOURT_DATA_ROOT": str(root)} if root is not None else None
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env=env)


def _records(imp, ledger, path, mode="oracle", cutoff="2000-01-01", provider="oracle", decline_every=0):
    """Write a records file for the rolling-origin request set: an oracle that knows the event, or a constant."""
    runner, rec = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.recorded")
    ev = dict(zip(ledger["row_id"], ledger["y"] > 1.96 * ledger["s"]))
    out = []
    for i, it in enumerate(runner.build_requests(ledger)):
        declined = bool(decline_every) and i % decline_every == 0
        p = (0.97 if ev[it.row_id] else 0.02) if mode == "oracle" else 0.5
        out.append({"request_hash": it.request.request_hash(), "provider_id": provider, "version": "1", "knowledge_cutoff": cutoff,
                    "declined": declined, "result": None if declined else {"p_win_ai": p, "cost_usd": 0.01}, "latency_s": 0.1,
                    "cost_usd": 0.0 if declined else 0.01, "row_id": it.row_id, "origin": it.origin, "budget": it.request.to_wire()["budget"]})
    rec.write_records(path, out)
    return out


@pytest.fixture
def world(imp, make_synth):
    ledger, _ = make_synth(seed=57, n_tests=260, variants_per_test=2)
    harness = imp("mootcourt.harness")
    rungs = {k: v for k, v in harness.default_rungs("synthetic", ledger).items() if k in ("P0", "P1", "P2")}
    scores = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger), source="synthetic")
    return ledger, scores


def _data(imp, path):
    return imp("mootcourt.simulators.scoring").load_second_opinion(path)


# ------------------------------------------------------------------ registry
def test_registry_stores_and_resets_the_weight(imp, tmp_path):
    reg = imp("mootcourt.registry").Registry(tmp_path)
    assert reg.get_second_opinion_weight("synthetic", "agent") == 0.0
    with pytest.raises(KeyError):
        reg.set_second_opinion_weight("synthetic", "agent", "1", 0.2, {})
    reg.register_model("synthetic", "m1")
    reg.set_second_opinion_weight("synthetic", "agent", "2", 0.35, {"n": 99})
    assert reg.get_second_opinion_weight("synthetic", "agent") == 0.35 and reg.second_opinion("synthetic")["agent"]["version"] == "2"
    assert reg.get_second_opinion_weight("synthetic", "other") == 0.0
    with pytest.raises(ValueError):
        reg.set_second_opinion_weight("synthetic", "agent", "2", 1.5, {})
    assert reg.sources() == ["synthetic"] and reg.get_champion("synthetic") == "m1"
    reg.set_second_opinion_weight("synthetic", "agent", "2", 0.0, {"why": "no longer passes"})
    assert reg.get_second_opinion_weight("synthetic", "agent") == 0.0


# ------------------------------------------------------------------ rungs
def test_agent_and_stacked_rungs_cover_the_base_rows(imp, world, tmp_path):
    ledger, scores = world
    sc = imp("mootcourt.simulators.scoring")
    _records(imp, ledger, tmp_path / "a.jsonl", decline_every=5)
    out, meta = sc.add_agent_rungs(scores, ledger, _data(imp, tmp_path / "a.jsonl"), weight=0.0)
    base, agent, stack = (out[out["rung"] == r].reset_index(drop=True) for r in ("P2", "agent", "P2+agent"))
    assert len(stack) == len(base) and len(agent) == meta["n_with_opinion"]
    assert meta["n_declined"] > 0 and meta["n_missing"] == 0
    assert meta["n_with_opinion"] + meta["n_declined"] + meta["n_missing"] == meta["n_rows"] == len(base)
    assert np.allclose(stack["p_sig"], base["p_sig"])                    # weight 0: the stack is p_sig
    assert set(agent["row_id"]) <= set(base["row_id"])
    for r in (agent, stack):
        assert r[["logscore", "crps", "lo90", "hi90"]].isna().all().all()
    assert np.allclose(agent["brier_event"], (agent["p_sig"] - agent["event"].astype(float)) ** 2)
    assert (out[out["rung"] == "P2"].reset_index(drop=True)["p_sig"] == base["p_sig"]).all()      # the base rung is untouched
    heavy, _ = sc.add_agent_rungs(scores, ledger, _data(imp, tmp_path / "a.jsonl"), weight=0.4)
    st = heavy[heavy["rung"] == "P2+agent"].reset_index(drop=True)
    have = np.isin(base["row_id"], agent["row_id"])
    ai = agent.set_index("row_id")["p_sig"].reindex(base["row_id"]).to_numpy()
    assert np.allclose(st["p_sig"][have], 0.6 * base["p_sig"][have] + 0.4 * ai[have])
    assert np.allclose(st["p_sig"][~have], base["p_sig"][~have])         # declined rows keep p_sig
    with pytest.raises(imp("mootcourt.simulators").SimulatorError):
        sc.add_agent_rungs(scores, ledger, _data(imp, tmp_path / "a.jsonl"), weight=1.5)


def test_rows_absent_from_the_file_are_counted_as_missing(imp, world, tmp_path):
    ledger, scores = world
    sc, rec = imp("mootcourt.simulators.scoring"), imp("mootcourt.simulators.recorded")
    _records(imp, ledger, tmp_path / "full.jsonl")
    keep = rec.read_records(tmp_path / "full.jsonl")[::2]
    rec.write_records(tmp_path / "half.jsonl", keep)
    out, meta = sc.add_agent_rungs(scores, ledger, _data(imp, tmp_path / "half.jsonl"), 0.0)
    assert meta["n_missing"] > 0 and meta["n_with_opinion"] == len(keep) and len(out[out["rung"] == "agent"]) == len(keep)


def test_contamination_split_is_reported_separately(imp, world, tmp_path):
    ledger, scores = world
    sc, report, hs = imp("mootcourt.simulators.scoring"), imp("mootcourt.report"), imp("mootcourt.harness_stats")
    origins = sorted(scores["origin"].unique())
    cutoff = pd.Timestamp(origins[len(origins) // 2]).date().isoformat()
    _records(imp, ledger, tmp_path / "c.jsonl", cutoff=cutoff)
    data = _data(imp, tmp_path / "c.jsonl")
    assert sc.is_contaminated(origins[0], cutoff) and not sc.is_contaminated(origins[-1], cutoff) and not sc.is_contaminated(origins[0], None)
    out, meta = sc.add_agent_rungs(scores, ledger, data, 0.0)
    doc = report.build_document(out, ledger=ledger, source="synthetic", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0,
                                gates=GATES, B=50, second_opinion=meta)
    tab = pd.DataFrame(doc["tables"]["second_opinion"])
    n = tab[tab["rung"] == "agent"].set_index("origins")["n"]
    assert set(n.index) == {"all", "contaminated", "clean"} and n["contaminated"] + n["clean"] == n["all"] and n["contaminated"] > 0
    assert doc["notes"]["second_opinion"] == sc.CONTAMINATION_SENTENCE
    assert doc["header"]["second_opinion"]["knowledge_cutoff"] == cutoff
    mask = sc.clean_mask(out["origin"], cutoff)
    assert (pd.to_datetime(out["origin"][mask], utc=True) >= pd.Timestamp(cutoff, tz="UTC")).all()
    agg = hs.aggregate_scores(out, GATES, B=30)
    row = agg[(agg["cell"] == "ALL") & (agg["rung"] == "agent")].iloc[0]
    assert pd.isna(row["logscore"]) and pd.isna(row["coverage_90"]) and np.isfinite(row["brier_skill"])      # no density, no coverage, a Brier skill


def test_report_markdown_and_readme_carry_the_limitation_sentence(imp, world, tmp_path):
    ledger, scores = world
    sc, report = imp("mootcourt.simulators.scoring"), imp("mootcourt.report")
    _records(imp, ledger, tmp_path / "c.jsonl", cutoff="2020-01-01")
    out, meta = sc.add_agent_rungs(scores, ledger, _data(imp, tmp_path / "c.jsonl"), 0.0)
    paths = report.write_report(out, ledger=ledger, source="synthetic", snapshot_id="s1", model_id="m", feature_hash="f", command="c", seed=0,
                                gates=GATES, out_dir=tmp_path / "second-opinion-oracle", B=30, second_opinion=meta,
                                suffix="second-opinion", main=False)
    md = paths.md.read_text()
    assert sc.CONTAMINATION_SENTENCE in md and "## Second opinion" in md and "Weight in force" in md
    assert paths.json.name == "backtest-synthetic-s1--second-opinion.json" and not (tmp_path / "second-opinion-oracle" / "figures").exists()
    js = json.loads(paths.json.read_text())
    assert {"agent", "P2+agent"} <= set(js["header"]["rungs"])
    spec = __import__("importlib.util").util.spec_from_file_location("rr", ROOT / "scripts" / "render_readme_results.py")
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lines = "\n".join(mod.second_opinion_lines(tmp_path))
    assert sc.CONTAMINATION_SENTENCE in lines and "agent" in lines
    assert mod.second_opinion_lines(tmp_path / "nothing") == []


# ------------------------------------------------------------------ CLI: backtest and earn-weight
@pytest.fixture
def pipeline(imp, tmp_path, make_synth):
    ledger, _ = make_synth(seed=57, n_tests=260, variants_per_test=2)
    root = tmp_path / "root"
    imp("mootcourt.ledger").write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    assert _cli(imp, ["fit", "--source", "synthetic"], root).exit_code == 0
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40"], root)
    assert res.exit_code == 0, res.output
    return ledger, root


def test_earn_weight_accepts_an_informative_agent_and_refuses_a_useless_one(imp, pipeline, tmp_path):
    ledger, root = pipeline
    reg = imp("mootcourt.registry").Registry(root / "models")
    _records(imp, ledger, tmp_path / "oracle.jsonl", mode="oracle", provider="oracle")
    _records(imp, ledger, tmp_path / "noise.jsonl", mode="noise", provider="noise")
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "noise.jsonl")], root)
    assert res.exit_code == 0, res.output
    assert "weight stays 0" in res.output and reg.get_second_opinion_weight("synthetic", "noise") == 0.0
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "oracle.jsonl")], root)
    assert res.exit_code == 0, res.output
    w = reg.get_second_opinion_weight("synthetic", "oracle")
    assert w > 0 and "earned" in res.output
    ev = reg.second_opinion("synthetic")["oracle"]["evidence"]
    assert ev["brier_stacked"] < ev["brier_p_sig"] and ev["n_gate"] == GATES["n_400"]


def test_earn_weight_respects_the_gate_the_cutoff_and_resets(imp, pipeline, tmp_path):
    ledger, root = pipeline
    reg = imp("mootcourt.registry").Registry(root / "models")
    _records(imp, ledger, tmp_path / "o.jsonl", mode="oracle", provider="oracle")
    assert _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "o.jsonl")], root).exit_code == 0
    assert reg.get_second_opinion_weight("synthetic", "oracle") > 0
    (root / "reports" / "gates.json").write_text(json.dumps({**GATES, "n_400": 10**6}))
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "o.jsonl")], root)
    assert "below the gate" in res.output and reg.get_second_opinion_weight("synthetic", "oracle") == 0.0      # no longer passes: reset
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    _records(imp, ledger, tmp_path / "late.jsonl", mode="oracle", provider="late", cutoff="2030-01-01")
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "late.jsonl")], root)
    assert reg.get_second_opinion_weight("synthetic", "late") == 0.0 and "no opinion" in res.output       # every origin is contaminated
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "late.jsonl"), "--include-contaminated"], root)
    assert reg.get_second_opinion_weight("synthetic", "late") > 0


def test_backtest_with_a_second_opinion_adds_the_rungs_and_uses_the_weight_in_force(imp, pipeline, tmp_path):
    ledger, root = pipeline
    reg = imp("mootcourt.registry").Registry(root / "models")
    _records(imp, ledger, tmp_path / "o.jsonl", mode="oracle", provider="oracle", decline_every=6)
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40", "--second-opinion", str(tmp_path / "o.jsonl")], root)
    assert res.exit_code == 0, res.output
    js = json.loads(next((root / "reports" / "second-opinion-oracle").glob("backtest-synthetic-*--second-opinion.json")).read_text())
    assert {"agent", "P2+agent"} <= set(js["header"]["rungs"]) and js["header"]["second_opinion"]["weight"] == 0.0
    assert js["header"]["second_opinion"]["n_declined"] > 0 and "declined" in res.output
    main = sorted((root / "reports").glob("backtest-synthetic-*.json"))
    assert main and "agent" not in json.loads(main[-1].read_text())["header"]["rungs"]            # the main report is not replaced
    assert _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(tmp_path / "o.jsonl")], root).exit_code == 0
    w = reg.get_second_opinion_weight("synthetic", "oracle")
    _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40", "--second-opinion", str(tmp_path / "o.jsonl")], root)
    js = json.loads(next((root / "reports" / "second-opinion-oracle").glob("backtest-synthetic-*--second-opinion.json")).read_text())
    assert js["header"]["second_opinion"]["weight"] == w > 0
    bad = _cli(imp, ["backtest", "--source", "synthetic", "--second-opinion", str(tmp_path / "missing.jsonl")], root)
    assert bad.exit_code != 0


# ------------------------------------------------------------------ the card
@pytest.fixture
def served(imp, tmp_path, make_synth, reliability_factory):
    ledger, _ = make_synth(seed=101, n_tests=300, variants_per_test=2)
    bm, reg = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-111111111111", as_of=NOW)
    bm.save_bundle(bundle, models)
    reg.Registry(models).register_model("synthetic", bundle.model_id)
    (reports / "reliability-synthetic.json").write_text(json.dumps(reliability_factory(as_of=NOW - dt.timedelta(days=1), n=500)))
    return models, cards, reports, tmp_path / "root"


def _card_args(served, *extra, cards=None):
    models, cards_dir, reports, _ = served
    return ["card", "--source", "synthetic", "--headline", "you will not believe what happened next", "--image-changed", "false",
            "--impressions", "20000", "--models-dir", str(models), "--cards-dir", str(cards or cards_dir), "--reports-dir", str(reports),
            "--now", NOW.isoformat(), *extra]


def test_card_shows_the_second_opinion_beside_p_sig(imp, served):
    models, cards, reports, root = served
    plain = json.loads(_cli(imp, _card_args(served, "--json", cards=cards.parent / "c0"), root).output)
    assert "second_opinion" not in plain
    res = _cli(imp, _card_args(served, "--simulator", "heuristic"), root)
    assert res.exit_code == 0, res.output
    for needle in ("## Second opinion", "heuristic version 1", "Weight in force: 0.00", "the model's p_sig is the one that counts", "agent:"):
        assert needle in res.output, needle
    js = json.loads(_cli(imp, _card_args(served, "--simulator", "heuristic", "--json"), root).output)
    so = js["second_opinion"]
    assert so["provider_id"] == "heuristic" and so["version"] == "1" and so["weight"] == 0.0 and 0.0 < so["p_ai"] < 1.0
    assert so["p_stack"] == pytest.approx(js["prediction"]["p_sig"])             # weight 0: the stack is p_sig
    assert js["card_id"] != plain["card_id"]
    frozen = json.loads((cards / f"{js['card_id']}.json").read_text())
    assert frozen["second_opinion"] == so                                         # the frozen card carries the same fields


def test_card_uses_the_earned_weight_and_states_declines(imp, served):
    models, cards, reports, root = served
    imp("mootcourt.registry").Registry(models).set_second_opinion_weight("synthetic", "heuristic", "1", 0.3, {"why": "test"})
    js = json.loads(_cli(imp, _card_args(served, "--simulator", "heuristic", "--json"), root).output)
    so, p = js["second_opinion"], js["prediction"]["p_sig"]
    assert so["weight"] == 0.3 and so["p_stack"] == pytest.approx(0.7 * p + 0.3 * so["p_ai"])
    md = _cli(imp, _card_args(served, "--simulator", "heuristic"), root).output
    assert "Weight in force: 0.30" in md and "Stacked P(significant and positive)" in md and "weight is zero" not in md
    null = _cli(imp, _card_args(served, "--simulator", "null"), root).output
    assert "The second opinion abstained" in null


def test_an_abstained_card_shows_no_opinion(imp, served, tmp_path):
    models, cards, reports, root = served
    empty = tmp_path / "empty_reports"
    empty.mkdir()
    args = _card_args(served, "--simulator", "heuristic", "--json")
    args[args.index("--reports-dir") + 1] = str(empty)
    js = json.loads(_cli(imp, args, root).output)
    assert js["abstention"]["status"] == "abstain" and js["second_opinion"]["p_ai"] is None and js["second_opinion"]["p_stack"] is None


def test_unknown_simulator_is_an_error(imp, served):
    res = _cli(imp, _card_args(served, "--simulator", "nope"), served[3])
    assert res.exit_code == 1 and "unknown provider" in res.output


# ------------------------------------------------------------------ end to end
def test_end_to_end_on_the_synthetic_source_with_the_heuristic_provider(imp, pipeline, tmp_path):
    ledger, root = pipeline
    rec = tmp_path / "heur.jsonl"
    run = ["simulators", "run", "--provider", "heuristic", "--source", "synthetic", "--origins", "quarterly", "--out", str(rec)]
    assert _cli(imp, run, root).exit_code == 0
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(rec)], root)
    assert res.exit_code == 0 and "heuristic 1" in res.output
    weight = imp("mootcourt.registry").Registry(root / "models").get_second_opinion_weight("synthetic", "heuristic")
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40", "--second-opinion", str(rec)], root)
    assert res.exit_code == 0, res.output
    js = json.loads(next((root / "reports" / "second-opinion-heuristic").glob("*.json")).read_text())
    assert js["header"]["second_opinion"]["weight"] == weight
    tab = pd.DataFrame(js["tables"]["second_opinion"])
    assert {"P2", "agent", "P2+agent"} <= set(tab["rung"])
    last = pd.Timestamp(ledger["usable_after"].max()) + pd.Timedelta(days=1)
    when = last.isoformat()
    card = _cli(imp, ["card", "--source", "synthetic", "--headline", "a plain headline about nothing", "--image-changed", "false",
                      "--impressions", "20000", "--now", when, "--origin", when, "--simulator", "heuristic", "--json"], root)
    assert card.exit_code == 0, card.output
    so = json.loads(card.output)["second_opinion"]
    assert so["provider_id"] == "heuristic" and so["weight"] == weight
