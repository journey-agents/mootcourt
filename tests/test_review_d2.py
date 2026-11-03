"""T-043 contracts: the findings of the chunk D2 code review (REV-001 to REV-019), one test each."""
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_simulators import _info, _req, _script, _Server
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=dt.timezone.utc)
GATES = {"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9,
         "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}
EARLY_CUTOFF = "2000-01-01"


def _cli(imp, args, root=None):
    env = {"MOOTCOURT_DATA_ROOT": str(root)} if root is not None else None
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env=env)


# ------------------------------------------------------------------ REV-001 proxy
def test_http_loopback_call_ignores_a_configured_proxy(imp, monkeypatch):
    httpmod = imp("mootcourt.simulators.http")
    for k in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(k, "http://127.0.0.1:9")                # a dead address: any request sent through it fails
    for k in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(k, raising=False)
    srv = _Server()
    try:
        sim = httpmod.HttpSimulator(srv.url, _info(imp), time_cap_s=10)
        res = sim.simulate(_req(imp))
        assert res is not None and res.p_win_ai == 0.6 and srv.calls == 1, sim.last_note
    finally:
        srv.close()


def test_http_opener_has_no_proxy_handler_even_when_the_environment_names_one(imp, monkeypatch):
    """The adapter talks to the named host directly: with a proxy in the environment the request still reaches a loopback server.

    (Chunk G: the adapter uses http.client, which never reads proxy variables; the test used to inspect a urllib opener and now checks
    the behaviour that the opener's empty proxy table was there to give.)
    """
    import http.server
    import threading

    from test_simulators import _req

    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(self.rfile.read(int(self.headers["Content-Length"])))
            body = b"null"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
            monkeypatch.setenv(name, "http://127.0.0.1:9")                  # a closed port: any use of it would fail the request
        monkeypatch.delenv("NO_PROXY", raising=False)
        monkeypatch.delenv("no_proxy", raising=False)
        sim = imp("mootcourt.simulators.http").HttpSimulator(f"http://127.0.0.1:{srv.server_address[1]}/x", _info(imp))
        assert sim.simulate(_req(imp)) is None and sim.last_failure is None and sim.last_note == "the agent declined"
        assert len(seen) == 1
    finally:
        srv.shutdown()
        srv.server_close()


# ------------------------------------------------------------------ REV-002 and REV-016 versioned, champion-bound weight
def _registry(imp, tmp_path, champion="m1"):
    reg = imp("mootcourt.registry").Registry(tmp_path / "models")
    reg.register_model("synthetic", champion)
    return reg


def test_earned_weight_belongs_to_one_version(imp, tmp_path):
    reg = _registry(imp, tmp_path)
    reg.set_second_opinion_weight("synthetic", "agent", "1", 0.3, {"why": "test"})
    assert reg.get_second_opinion_weight("synthetic", "agent", "1") == 0.3
    assert reg.get_second_opinion_weight("synthetic", "agent", "2") == 0.0
    assert reg.get_second_opinion("synthetic", "agent", "2") is None
    reg.set_second_opinion_weight("synthetic", "agent", "2", 0.1, {"why": "its own"})
    assert reg.get_second_opinion_weight("synthetic", "agent", "2") == 0.1 and reg.get_second_opinion_weight("synthetic", "agent", "1") == 0.0


def test_earned_weight_lapses_when_the_champion_changes(imp, tmp_path):
    reg = _registry(imp, tmp_path)
    reg.set_second_opinion_weight("synthetic", "agent", "1", 0.3, {})
    reg.register_model("synthetic", "m2")                          # a challenger: the champion is the same
    assert reg.get_second_opinion_weight("synthetic", "agent", "1") == 0.3
    doc = reg._read()
    doc["synthetic"]["champion"] = "m2"                            # what promotion does
    reg._write(doc)
    assert reg.get_second_opinion_weight("synthetic", "agent", "1") == 0.0
    assert reg.second_opinion("synthetic")["agent"]["weight"] == 0.3        # the record is kept for the audit trail


def test_the_contaminated_flag_is_stored_and_returned(imp, tmp_path):
    reg = _registry(imp, tmp_path)
    reg.set_second_opinion_weight("synthetic", "agent", "1", 0.2, {}, contaminated=True)
    assert reg.get_second_opinion("synthetic", "agent", "1")["contaminated"] is True
    reg.set_second_opinion_weight("synthetic", "agent", "1", 0.2, {})
    assert reg.get_second_opinion("synthetic", "agent", "1")["contaminated"] is False


def test_card_and_backtest_pass_the_version(imp, tmp_path, make_synth, reliability_factory):
    ledger, _ = make_synth(seed=101, n_tests=300, variants_per_test=2)
    bm, regm = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-111111111111", as_of=NOW)
    bm.save_bundle(bundle, models)
    reg = regm.Registry(models)
    reg.register_model("synthetic", bundle.model_id)
    (reports / "reliability-synthetic.json").write_text(json.dumps(reliability_factory(as_of=NOW - dt.timedelta(days=1), n=500)))
    reg.set_second_opinion_weight("synthetic", "heuristic", "0-older", 0.3, {})            # earned by another version
    args = ["card", "--source", "synthetic", "--headline", "you will not believe what happened next", "--image-changed", "false",
            "--impressions", "20000", "--models-dir", str(models), "--cards-dir", str(cards), "--reports-dir", str(reports),
            "--now", NOW.isoformat(), "--simulator", "heuristic", "--json"]
    res = _cli(imp, args, tmp_path / "root")
    assert res.exit_code == 0, res.output
    assert json.loads(res.output)["second_opinion"]["weight"] == 0.0
    reg.set_second_opinion_weight("synthetic", "heuristic", "1", 0.3, {})
    res = _cli(imp, args[:args.index("--cards-dir") + 1] + [str(tmp_path / "c2")] + args[args.index("--cards-dir") + 2:], tmp_path / "root")
    assert json.loads(res.output)["second_opinion"]["weight"] == 0.3


# ------------------------------------------------------------------ REV-003 and REV-004 failures, declines and the cache
class _Flaky:
    """Fails with a stated kind on the first pass and answers on the second."""

    def __init__(self, imp, kind="timeout"):
        self.calls, self.kind, self.last_note, self.last_failure, self.imp = 0, kind, "", None, imp

    def describe(self):
        return _info(self.imp, provider_id="flaky")

    def simulate(self, request):
        self.calls += 1
        if self.calls <= 1:
            self.last_note, self.last_failure = "connection refused", self.kind
            return None
        self.last_note, self.last_failure = "", None
        return self.imp("mootcourt.simulators").SimulationResult(p_win_ai=0.4)


def _items(imp, n=1):
    runner = imp("mootcourt.simulators.runner")
    return [runner.RequestItem(f"r{i}", "2014-07-01T00:00:00+00:00", _req(imp, variant_headline=f"Headline {i}")) for i in range(n)]


def test_a_transient_failure_is_recorded_but_never_cached(imp, tmp_path):
    runner, cache_mod = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.cache")
    cache = cache_mod.SimulationCache(tmp_path / "cache")
    sim = _Flaky(imp)
    first = runner.run(sim, _items(imp), tmp_path / "a.jsonl", cache)
    rec = json.loads((tmp_path / "a.jsonl").read_text().splitlines()[0])
    assert rec["declined"] is True and rec["failure"] == "timeout" and "connection refused" in rec["note"]
    assert first.n_failed == 1 and not list((tmp_path / "cache").rglob("*.json"))
    again = runner.run(sim, _items(imp), tmp_path / "b.jsonl", cache)             # the agent is called again and now answers
    assert sim.calls == 2 and again.n_called == 1 and again.n_failed == 0
    assert list((tmp_path / "cache").rglob("*.json"))
    assert json.loads((tmp_path / "b.jsonl").read_text().splitlines()[0]).get("failure") is None


def test_an_explicit_decline_is_cached(imp, tmp_path):
    runner, cache_mod, stdio = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.cache"), imp("mootcourt.simulators.stdio")
    sim = stdio.StdioSimulator(_script(tmp_path, "import sys\nsys.stdin.readline()\nprint('null')\n"), _info(imp), time_cap_s=20)
    cache = cache_mod.SimulationCache(tmp_path / "cache")
    out = runner.run(sim, _items(imp), tmp_path / "a.jsonl", cache)
    assert out.n_declined == 1 and out.n_failed == 0 and len(list((tmp_path / "cache").rglob("*.json"))) == 1


@pytest.mark.parametrize("body,kind", [
    ("import sys\nsys.exit(3)\n", "exit"),
    ("print('not json')\n", "invalid"),
    ("print('0.3')\n", "invalid"),                                  # a bare number
    ("print('[0.3]')\n", "invalid"),                                # a list
    ("print('{\"p_win_ai\": 0.3, \"interval_ai\": [0.0, 0.1, 0.2]}')\n", "invalid"),      # wrong interval length
    ("print('{\"p_win_ai\": 0.3, \"interval_ai\": 5}')\n", "invalid"),
    ("print('\"text\"')\n", "invalid"),
])
def test_stdio_bad_outputs_are_failures_with_a_reason_not_crashes(imp, tmp_path, body, kind):
    stdio = imp("mootcourt.simulators.stdio")
    sim = stdio.StdioSimulator(_script(tmp_path, body), _info(imp), time_cap_s=20)
    assert sim.simulate(_req(imp)) is None
    assert sim.last_failure == kind and sim.last_note


def test_stdio_failure_kinds(imp, tmp_path):
    stdio = imp("mootcourt.simulators.stdio")
    slow = stdio.StdioSimulator(_script(tmp_path, "import time\ntime.sleep(30)\n"), _info(imp), time_cap_s=0.5)
    assert slow.simulate(_req(imp)) is None and slow.last_failure == "timeout"
    gone = stdio.StdioSimulator(["/no/such/binary"], _info(imp))
    assert gone.simulate(_req(imp)) is None and gone.last_failure == "start"
    decl = stdio.StdioSimulator(_script(tmp_path, "print('null')\n"), _info(imp), time_cap_s=20)
    assert decl.simulate(_req(imp)) is None and decl.last_failure is None


def test_http_failure_kinds_and_malformed_replies(imp):
    httpmod = imp("mootcourt.simulators.http")
    for reply in (0.3, [0.3], {"p_win_ai": 0.3, "interval_ai": [0, 1, 2]}):
        srv = _Server(reply=reply)
        try:
            sim = httpmod.HttpSimulator(srv.url, _info(imp), time_cap_s=10)
            assert sim.simulate(_req(imp)) is None and sim.last_failure == "invalid" and "invalid output" in sim.last_note
        finally:
            srv.close()
    srv = _Server()
    url = srv.url
    srv.close()                                                     # nothing listens there any more
    sim = httpmod.HttpSimulator(url, _info(imp), time_cap_s=5)
    assert sim.simulate(_req(imp)) is None and sim.last_failure == "transport"


def test_a_simulator_that_raises_becomes_a_recorded_failure_and_the_file_is_written(imp, tmp_path):
    runner = imp("mootcourt.simulators.runner")

    class Boom:
        def describe(self):
            return _info(imp, provider_id="boom")

        def simulate(self, request):
            raise RuntimeError("kaboom")

    out = runner.run(Boom(), _items(imp, 3), tmp_path / "a.jsonl", None)
    recs = [json.loads(ln) for ln in (tmp_path / "a.jsonl").read_text().splitlines()]
    assert len(recs) == 3 and out.n_failed == 3 and all(r["failure"] == "error" and "kaboom" in r["note"] for r in recs)


def test_http_and_stdio_outputs_are_bounded(imp, tmp_path):
    stdio = imp("mootcourt.simulators.stdio")
    sim = stdio.StdioSimulator(_script(tmp_path, "import sys\nsys.stdin.readline()\nsys.stdout.write('x' * 3_000_000)\n"), _info(imp), time_cap_s=20)
    assert sim.simulate(_req(imp)) is None and sim.last_failure == "invalid" and "too large" in sim.last_note
    httpmod = imp("mootcourt.simulators.http")
    srv = _Server(reply={"p_win_ai": 0.3, "notes": "y" * 3_000_000})
    try:
        h = httpmod.HttpSimulator(srv.url, _info(imp), time_cap_s=10)
        assert h.simulate(_req(imp)) is None and h.last_failure == "invalid" and "too large" in h.last_note
    finally:
        srv.close()


# ------------------------------------------------------------------ REV-005 validation when read back
def _write_records(path, p_win, extra=None):
    rec = {"request_hash": "abc123", "provider_id": "agent", "version": "1", "knowledge_cutoff": EARLY_CUTOFF, "declined": False,
           "result": {"p_win_ai": p_win, **(extra or {})}, "latency_s": 0.0, "cost_usd": 0.0, "row_id": "row-77",
           "origin": "2014-07-01T00:00:00+00:00"}
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")


@pytest.mark.parametrize("value,extra", [(1.7, None), (float("nan"), None), ("high", None), (0.5, {"interval_ai": [0.0, 1.0, 2.0]}), (None, None)])
def test_a_hand_edited_record_is_refused_with_its_name(imp, tmp_path, value, extra):
    sc, base = imp("mootcourt.simulators.scoring"), imp("mootcourt.simulators")
    _write_records(tmp_path / "r.jsonl", value, extra)
    with pytest.raises(base.SimulatorError) as exc:
        sc.load_second_opinion(tmp_path / "r.jsonl")
    assert "abc123" in str(exc.value) or "row-77" in str(exc.value)


def test_a_valid_record_loads(imp, tmp_path):
    sc = imp("mootcourt.simulators.scoring")
    _write_records(tmp_path / "r.jsonl", 0.4, {"interval_ai": [0.0, 1.0]})
    assert sc.load_second_opinion(tmp_path / "r.jsonl").provider_id == "agent"


# ------------------------------------------------------------------ REV-006 knowledge cutoff
def test_a_missing_cutoff_means_every_origin_is_possibly_contaminated(imp, tmp_path):
    sc = imp("mootcourt.simulators.scoring")
    origins = pd.Series(pd.to_datetime(["2013-01-01", "2014-01-01"], utc=True))
    assert sc.clean_mask(origins, None, unknown_is_contaminated=True).tolist() == [False, False]
    assert sc.clean_mask(origins, None).tolist() == [True, True]                                     # the old default stays for built-ins
    assert sc.is_contaminated(origins[0], None, unknown_is_contaminated=True) and not sc.is_contaminated(origins[0], None)
    p = tmp_path / "r.jsonl"
    _write_records(p, 0.4)
    rec = json.loads(p.read_text())
    rec["knowledge_cutoff"] = None
    p.write_text(json.dumps(rec) + "\n")
    assert sc.load_second_opinion(p).cutoff_unknown is True
    rec["provider_id"] = "heuristic"
    p.write_text(json.dumps(rec) + "\n")
    assert sc.load_second_opinion(p).cutoff_unknown is False                                         # a built-in has no training data


def test_a_provider_table_without_a_cutoff_is_refused(imp, tmp_path):
    loader, base = imp("mootcourt.simulators.loader"), imp("mootcourt.simulators")
    cfg = tmp_path / "mootcourt.toml"
    cfg.write_text('[simulators.mine]\nadapter = "stdio"\ncommand = ["python3", "agent.py"]\n', encoding="utf-8")
    with pytest.raises(base.SimulatorError, match="knowledge_cutoff"):
        loader.get_simulator("mine", cfg)
    cfg.write_text('[simulators.mine]\nadapter = "stdio"\ncommand = ["python3", "agent.py"]\nknowledge_cutoff = "2025-06-01"\n', encoding="utf-8")
    assert loader.get_simulator("mine", cfg).describe().knowledge_cutoff == "2025-06-01"
    assert loader.get_simulator("heuristic", cfg).describe().provider_id == "heuristic"


def test_the_simulator_docs_require_the_cutoff():
    text = (ROOT / "docs" / "simulators.md").read_text(encoding="utf-8")
    assert "knowledge_cutoff" in text and "possibly contaminated" in text and "or leave it out" not in text


# ------------------------------------------------------------------ REV-007 flag on the weight
def test_the_card_and_the_report_state_a_contaminated_weight(imp):
    card_mod, sc = imp("mootcourt.card"), imp("mootcourt.simulators.scoring")
    assert "contaminated" in sc.CONTAMINATION_SENTENCE.lower()
    sentence = sc.CONTAMINATION_SENTENCE
    assert "unless the run was told to include contaminated ones" in sentence and "marked as contaminated" in sentence
    import dataclasses

    names = [f.name for f in dataclasses.fields(card_mod.SecondOpinionView)]
    assert names[-1] == "contaminated"


def test_a_contaminated_weight_is_marked_on_the_card(imp, tmp_path, make_synth, reliability_factory):
    ledger, _ = make_synth(seed=101, n_tests=300, variants_per_test=2)
    bm, regm = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-111111111111", as_of=NOW)
    bm.save_bundle(bundle, models)
    reg = regm.Registry(models)
    reg.register_model("synthetic", bundle.model_id)
    (reports / "reliability-synthetic.json").write_text(json.dumps(reliability_factory(as_of=NOW - dt.timedelta(days=1), n=500)))
    reg.set_second_opinion_weight("synthetic", "heuristic", "1", 0.3, {}, contaminated=True)
    args = ["card", "--source", "synthetic", "--headline", "you will not believe what happened next", "--image-changed", "false",
            "--impressions", "20000", "--models-dir", str(models), "--cards-dir", str(cards), "--reports-dir", str(reports),
            "--now", NOW.isoformat(), "--simulator", "heuristic"]
    md = _cli(imp, args, tmp_path / "root").output
    assert "contaminated origins" in md
    js = json.loads(_cli(imp, args[:args.index("--cards-dir") + 1] + [str(tmp_path / "c2")] + args[args.index("--cards-dir") + 2:] + ["--json"],
                        tmp_path / "root").output)
    assert js["second_opinion"]["contaminated"] is True


# ------------------------------------------------------------------ REV-012 choose in time, judge later
class _Probs:
    def __init__(self, table):
        self.table = table

    def p_ai(self, row):
        return self.table[row["row_id"]]


def _two_period_frame(informative_late: bool, n_each=200, seed=5):
    rng = np.random.default_rng(seed)
    n = 2 * n_each
    event = rng.random(n) < 0.3
    origin = pd.to_datetime(["2014-01-01"] * n_each + ["2014-04-01"] * n_each, utc=True)
    rows = pd.DataFrame({"row_id": [f"r{i}" for i in range(n)], "origin": origin, "p_sig": np.full(n, 0.3), "event": event})
    ai = np.where(event, 0.9, 0.1)
    if not informative_late:
        ai[n_each:] = 0.5 + 0.0 * ai[n_each:]                      # useless in the later period
    return rows, dict(zip(rows["row_id"], ai))


def test_weight_is_chosen_on_early_origins_and_judged_on_later_ones(imp):
    so = imp("mootcourt.predictors.second_opinion")
    rows, table = _two_period_frame(informative_late=True)
    res = so.earn_weight(_Probs(table), rows, n_gate=100, margin=0.01)
    assert res.weight > 0 and res.n == 200 and res.n_chosen == 200
    assert "chosen on origins before" in res.message and "judged on" in res.message
    rows, table = _two_period_frame(informative_late=False)
    res = so.earn_weight(_Probs(table), rows, n_gate=100, margin=0.01)
    assert res.weight == 0.0                                       # a weight chosen on the early rows fails on the later ones


def test_the_gate_counts_the_judged_rows_and_one_origin_cannot_be_split(imp):
    so = imp("mootcourt.predictors.second_opinion")
    rows, table = _two_period_frame(informative_late=True)
    res = so.earn_weight(_Probs(table), rows, n_gate=250, margin=0.01)
    assert res.weight == 0.0 and "gate" in res.message
    one = rows.assign(origin=rows["origin"].iloc[0])
    res = so.earn_weight(_Probs(table), one, n_gate=10, margin=0.01)
    assert res.weight == 0.0 and "two origins" in res.message


def test_method_and_simulator_docs_state_the_time_split():
    for name in ("method.md", "simulators.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        assert "before an inner cut" in text and "judged" in text, name


# ------------------------------------------------------------------ REV-009 and the scores lookup by snapshot id
def test_find_scores_uses_the_snapshot_id_not_the_modification_time(imp, tmp_path):
    reg = imp("mootcourt.registry")
    old, new = tmp_path / "scores-synthetic-20260101-aaaaaaaaaaaa.parquet", tmp_path / "scores-synthetic-20260102-bbbbbbbbbbbb.parquet"
    other = tmp_path / "scores-synthetic-20260101-aaaaaaaaaaaa--second-opinion.parquet"
    for p in (old, new, other):
        p.write_bytes(b"x")
    os.utime(old, (time.time() + 100, time.time() + 100))          # the stale one is the newest on disk
    assert reg.find_scores(tmp_path, "synthetic", "20260102-bbbbbbbbbbbb") == new
    assert reg.find_scores(tmp_path, "synthetic", "20260101-aaaaaaaaaaaa") == old
    assert reg.find_scores(tmp_path, "synthetic", "20260103-cccccccccccc") is None


def test_earn_weight_reads_the_current_snapshots_scores(imp, tmp_path, make_synth):
    ledger, _ = make_synth(seed=57, n_tests=260, variants_per_test=2)
    root = tmp_path / "root"
    imp("mootcourt.ledger").write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    assert _cli(imp, ["fit", "--source", "synthetic"], root).exit_code == 0
    assert _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40"], root).exit_code == 0
    good = next((root / "reports").glob("scores-synthetic-*.parquet"))
    stale = root / "reports" / "scores-synthetic-19990101-ffffffffffff.parquet"
    stale.write_bytes(b"not a parquet file")
    os.utime(stale, (time.time() + 500, time.time() + 500))
    rec = tmp_path / "heur.jsonl"
    assert _cli(imp, ["simulators", "run", "--provider", "heuristic", "--source", "synthetic", "--out", str(rec)], root).exit_code == 0
    res = _cli(imp, ["earn-weight", "--source", "synthetic", "--second-opinion", str(rec)], root)
    assert res.exit_code == 0, res.output
    assert f"scores {good.name}" in res.output and "19990101" not in res.output


def test_list_precedents_enforces_the_fit_cutoff(imp, tmp_path, make_synth, reliability_factory):
    ledger, _ = make_synth(seed=102, n_tests=300, variants_per_test=2)
    bm, regm, mcp = imp("mootcourt.bundle"), imp("mootcourt.registry"), imp("mootcourt.mcp_server")
    models, reports = tmp_path / "models", tmp_path / "reports"
    models.mkdir()
    reports.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-222222222222", as_of=NOW)
    bm.save_bundle(bundle, models)
    regm.Registry(models).register_model("synthetic", bundle.model_id)
    state = imp("mootcourt.service").ServingState(models, reports, lambda: NOW)
    early = (bundle.fit_cutoff - pd.Timedelta(days=100)).isoformat()
    with pytest.raises(ValueError, match="cutoff"):
        mcp.tool_list_precedents(state, "synthetic", "a plain headline", False, 3, origin=early)
    assert len(json.loads(mcp.tool_list_precedents(state, "synthetic", "a plain headline", False, 3, origin=bundle.fit_cutoff.isoformat()))) == 3


# ------------------------------------------------------------------ REV-008 Makefile
def _make_root(tmp_path, env):
    (tmp_path / ".env").write_text("MOOTCOURT_DATA_ROOT=/from/dotenv\n", encoding="utf-8")
    show = "\nshow:\n\t@echo ROOT=$(MOOTCOURT_DATA_ROOT)\n"
    (tmp_path / "Makefile").write_text((ROOT / "Makefile").read_text(encoding="utf-8") + show, encoding="utf-8")
    e = {k: v for k, v in os.environ.items() if k != "MOOTCOURT_DATA_ROOT"}
    e.update(env)
    return subprocess.run(["make", "-s", "show"], cwd=tmp_path, env=e, capture_output=True, text=True).stdout.strip()


def test_the_shell_variable_beats_the_env_file(tmp_path):
    assert _make_root(tmp_path, {"MOOTCOURT_DATA_ROOT": "/from/shell"}) == "ROOT=/from/shell"
    assert _make_root(tmp_path, {}) == "ROOT=/from/dotenv"


# ------------------------------------------------------------------ REV-010 and REV-011 stdio process group and data root
def test_the_time_cap_kills_the_whole_process_group(imp, tmp_path):
    stdio = imp("mootcourt.simulators.stdio")
    pidfile = tmp_path / "grandchild.pid"
    sim = stdio.StdioSimulator(["sh", "-c", f"sleep 40 & echo $! > {pidfile}; wait"], _info(imp), time_cap_s=1.0)
    pid = None
    try:
        assert sim.simulate(_req(imp)) is None and sim.last_failure == "timeout"
        pid = int(pidfile.read_text().strip())
        gone = False
        for _ in range(40):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                gone = True
                break
            time.sleep(0.1)
        assert gone, f"the grandchild {pid} survived the time cap"
    finally:
        if pid is None and pidfile.exists():
            pid = int(pidfile.read_text().strip())
        if pid:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass


def test_a_command_inside_the_data_root_is_refused(imp, tmp_path, monkeypatch):
    stdio, base = imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators")
    root = tmp_path / "dataroot"
    (root / "data").mkdir(parents=True)
    script = root / "data" / "agent.py"
    script.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    with pytest.raises(base.SimulatorError, match="data root"):
        stdio.StdioSimulator([sys.executable, str(script)], _info(imp))
    with pytest.raises(base.SimulatorError, match="data root"):
        stdio.StdioSimulator([str(script)], _info(imp))
    monkeypatch.chdir(root / "data")
    with pytest.raises(base.SimulatorError, match="data root"):
        stdio.StdioSimulator([sys.executable, "agent.py"], _info(imp))
    outside = tmp_path / "ok.py"
    outside.write_text("print('null')\n")
    monkeypatch.chdir(tmp_path)                       # the working directory is checked too since REV-003 of the chunk E review
    stdio.StdioSimulator([sys.executable, str(outside)], _info(imp))              # outside the root: allowed


def test_config_pins_the_working_directory_to_the_config_file(imp, tmp_path):
    loader = imp("mootcourt.simulators.loader")
    (tmp_path / "proj").mkdir()
    cfg = tmp_path / "proj" / "mootcourt.toml"
    cfg.write_text('[simulators.mine]\nadapter = "stdio"\ncommand = ["python3", "agent.py"]\nknowledge_cutoff = "2025-06-01"\n', encoding="utf-8")
    assert Path(loader.get_simulator("mine", cfg).cwd).resolve() == (tmp_path / "proj").resolve()


# ------------------------------------------------------------------ low and nit findings
def test_ids_that_climb_out_of_the_cache_are_refused(imp):
    base, cache = imp("mootcourt.simulators"), imp("mootcourt.simulators.cache")
    for bad in ("..", ".", "../x", "a/b", ""):
        with pytest.raises(base.SimulatorError):
            base.SimulatorInfo(provider_id=bad or "", version="1", knowledge_cutoff=None, cost_model="free", description="x")
        with pytest.raises(base.SimulatorError):
            base.SimulatorInfo(provider_id="ok", version=bad or "", knowledge_cutoff=None, cost_model="free", description="x")
    assert cache._safe("..") != ".." and cache._safe(".") != "."
    base.SimulatorInfo(provider_id="my-agent_2.1", version="0.3-rc1", knowledge_cutoff=None, cost_model="free", description="x")


def test_the_agent_rung_is_compared_with_the_base_rung_on_the_same_rows(imp, make_synth, tmp_path):
    ledger, _ = make_synth(seed=57, n_tests=260, variants_per_test=2)
    harness, sc, report = imp("mootcourt.harness"), imp("mootcourt.simulators.scoring"), imp("mootcourt.report")
    runner, rec = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.recorded")
    rungs = {k: v for k, v in harness.default_rungs("synthetic", ledger).items() if k in ("P0", "P1", "P2")}
    scores = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger), source="synthetic")
    items = runner.build_requests(ledger)
    out = [{"request_hash": it.request.request_hash(), "provider_id": "agent", "version": "1", "knowledge_cutoff": EARLY_CUTOFF,
            "declined": i % 3 == 0, "result": None if i % 3 == 0 else {"p_win_ai": 0.3}, "latency_s": 0.0, "cost_usd": 0.0,
            "row_id": it.row_id, "origin": it.origin, "budget": it.request.to_wire()["budget"]} for i, it in enumerate(items)]
    rec.write_records(tmp_path / "r.jsonl", out)
    data = sc.load_second_opinion(tmp_path / "r.jsonl")
    table, meta = sc.add_agent_rungs(scores, ledger, data, 0.0)
    tab = report._second_opinion_table(table, meta, GATES, 30, 1)
    on_rows = [r for r in tab if r["origins"] == "all" and r["rung"] == "P2 on agent rows"]
    agent = [r for r in tab if r["origins"] == "all" and r["rung"] == "agent"]
    assert on_rows and agent and on_rows[0]["n"] == agent[0]["n"]


def test_the_manifest_temp_file_is_dot_prefixed(imp, tmp_path, make_synth, monkeypatch):
    bundle_mod, reg_mod = imp("mootcourt.bundle"), imp("mootcourt.registry")
    ledger = make_synth(seed=151, n_tests=120, variants_per_test=2)[0]
    b = bundle_mod.fit_bundle(ledger, "synthetic", "20261102-333333333333")
    bundle_mod.save_bundle(b, tmp_path)
    reg_mod.Registry(tmp_path).register_model("synthetic", b.model_id)
    report = {"header": {"snapshot_id": "20261102-333333333333"},
              "tables": {"aggregate": [{"cell": "ALL", "rung": "P2", "brier_skill": 0.05, "brier_skill_lo": 0.01, "brier_skill_hi": 0.09,
                                        "n": 321, "logscore": -2.0}]}}

    def boom(*a, **k):
        raise OSError("crash between write and replace")

    with monkeypatch.context() as m:
        m.setattr(reg_mod.os, "replace", boom)
        with pytest.raises(OSError):
            reg_mod.attach_backtest(tmp_path, "synthetic", "20261102-333333333333", report, "backtest-x.json")
    leftovers = [p.name for p in (tmp_path / b.model_id).iterdir() if p.name.endswith(".tmp")]
    assert leftovers and all(n.startswith(".") for n in leftovers)
    assert bundle_mod.load_bundle(b.model_id, tmp_path).model_id == b.model_id


def test_the_environment_scrub_covers_common_credential_names(imp):
    stdio = imp("mootcourt.simulators.stdio")
    env = {"PGPASSWORD": "1", "DB_PASSWORD": "1", "AWS_CREDENTIALS": "1", "SERVICE_AUTH": "1", "GH_PAT": "1", "GH_PASS": "1",
           "PATH": "/usr/bin", "PYTHONPATH": "x", "AUTHOR": "me", "HOME": "/h", "PASSTHROUGH": "1", "API_KEY": "1"}
    kept = stdio.scrub_env(env)
    assert set(kept) == {"PATH", "PYTHONPATH", "AUTHOR", "HOME", "PASSTHROUGH"}


def test_the_test_session_ignores_the_repository_toml(imp, monkeypatch):
    import tomllib

    storage = imp("mootcourt.storage")
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(tomllib, "loads", lambda text: {"storage": {"data_root": "/would/write/here"}})
    assert storage.data_root() is None


def test_scoring_counts_failed_calls_separately(imp, tmp_path):
    sc = imp("mootcourt.simulators.scoring")
    rec = [{"request_hash": "h1", "provider_id": "agent", "version": "1", "knowledge_cutoff": EARLY_CUTOFF, "declined": True, "result": None,
            "failure": "timeout", "note": "slow", "latency_s": 0.0, "cost_usd": 0.0}]
    p = tmp_path / "r.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rec))
    data = sc.load_second_opinion(p)
    assert data.by_hash["h1"]["failure"] == "timeout"
