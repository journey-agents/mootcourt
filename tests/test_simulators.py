"""T-029 contracts: the response-simulator protocol, adapters, registration, cache and CLI. No model calls, no network beyond loopback."""
import http.server
import json
import sys
import textwrap
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REQUEST_FIELDS = {"source", "cell", "origin", "reference_headline", "variant_headline", "image_changed", "headline_changed",
                           "planned_n_ref", "planned_n_var", "s_star", "action_threshold", "budget"}


def _req(imp, **kw):
    base = imp("mootcourt.simulators")
    d = dict(source="synthetic", cell="headline_only", origin="2014-07-01T00:00:00+00:00", reference_headline="old", variant_headline="Why 5 things?",
             image_changed=False, headline_changed=True, planned_n_ref=20000, planned_n_var=20000, s_star=0.4, action_threshold=0.35)
    d.update(kw)
    return base.SimulationRequest(**d)


def _info(imp, **kw):
    d = dict(provider_id="fake", version="1", knowledge_cutoff=None, cost_model="free", description="fake")
    d.update(kw)
    return imp("mootcourt.simulators").SimulatorInfo(**d)


# ------------------------------------------------------------------ protocol
def test_request_schema_has_no_user_level_fields(imp):
    import dataclasses

    names = {f.name for f in dataclasses.fields(imp("mootcourt.simulators").SimulationRequest)}
    assert names == EXPECTED_REQUEST_FIELDS
    assert not [n for n in names if any(w in n for w in ("user", "person", "email", "name", "id_", "respondent_"))]
    wire = _req(imp).to_wire()
    assert set(wire) == EXPECTED_REQUEST_FIELDS and set(wire["budget"]) == {"max_respondents", "max_seconds"}


def test_request_refuses_unknown_fields_and_bad_values(imp):
    base = imp("mootcourt.simulators")
    wire = _req(imp).to_wire()
    assert base.SimulationRequest.from_wire(wire) == _req(imp)
    with pytest.raises(base.SimulatorError):
        base.SimulationRequest.from_wire({**wire, "user_id": "u1"})
    with pytest.raises(base.SimulatorError):
        base.SimulationRequest.from_wire({**wire, "budget": {"max_respondents": 5, "max_seconds": 1, "email": "x"}})
    for bad in ({"s_star": 0.0}, {"planned_n_ref": 0}, {"source": ""}, {"s_star": float("nan")}):
        with pytest.raises(base.SimulatorError):
            _req(imp, **bad)


def test_result_validation(imp):
    base = imp("mootcourt.simulators")
    ok = base.SimulationResult(p_win_ai=0.4, point_ai=0.1, interval_ai=(-0.2, 0.5), n_simulated=10, raw_votes={"variant": 6, "reference": 4})
    assert ok.to_dict()["interval_ai"] == [-0.2, 0.5]
    for bad in ({"p_win_ai": 1.2}, {"p_win_ai": -0.1}, {"p_win_ai": float("nan")}, {"p_win_ai": 0.5, "interval_ai": (1.0, 0.0)},
                {"p_win_ai": 0.5, "n_simulated": -1}, {"p_win_ai": 0.5, "raw_votes": ["a"]}, {"p_win_ai": 0.5, "cost_usd": -1.0}):
        with pytest.raises(base.SimulatorError):
            base.SimulationResult(**bad)
    parsed = base.SimulationResult.from_dict({"p_win_ai": 0.3, "surplus": 1, "interval_ai": [0, 1]}, provider_id="x", version="2")
    assert parsed.provider_id == "x" and parsed.interval_ai == (0.0, 1.0)
    with pytest.raises(base.SimulatorError):
        base.SimulationResult.from_dict({"point_ai": 1.0})


def test_info_validation_and_request_hash(imp):
    base = imp("mootcourt.simulators")
    with pytest.raises(base.SimulatorError):
        _info(imp, cost_model="free_beer")
    with pytest.raises(base.SimulatorError):
        _info(imp, knowledge_cutoff="June 2025")
    assert _info(imp, knowledge_cutoff="2025-06-01").knowledge_cutoff == "2025-06-01"
    a, b = _req(imp), _req(imp, s_star=0.4 + 1e-12)
    assert a.request_hash() == b.request_hash() and len(a.request_hash()) == 16
    assert a.request_hash() != _req(imp, variant_headline="other").request_hash()
    assert a.request_hash() != _req(imp, s_star=0.5).request_hash()


def test_null_declines_and_heuristic_is_deterministic(imp):
    builtin = imp("mootcourt.simulators.builtin")
    assert builtin.NullSimulator().simulate(_req(imp)) is None
    h = builtin.HeuristicSimulator()
    r1, r2 = h.simulate(_req(imp)), h.simulate(_req(imp))
    assert r1 == r2 and 0.02 <= r1.p_win_ai <= 0.60
    assert h.simulate(_req(imp, variant_headline="Why 5 things?")).p_win_ai != h.simulate(_req(imp, variant_headline="plain")).p_win_ai
    assert h.describe().provider_id == "heuristic" and builtin.NullSimulator().describe().provider_id == "null"


# ------------------------------------------------------------------ adapters
def _script(tmp_path, body, name="agent.py"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return [sys.executable, str(p)]


ECHO = """
import json, os, sys
req = json.loads(sys.stdin.readline())
names = sorted(k for k in os.environ if k.startswith("MOOT_TEST_"))
print(json.dumps({"p_win_ai": 0.25, "point_ai": 0.1, "n_simulated": 7, "notes": ",".join(names) + "|" + req["variant_headline"]}))
"""


def test_stdio_roundtrip_and_env_scrubbing(imp, tmp_path, monkeypatch):
    stdio = imp("mootcourt.simulators.stdio")
    for k in ("MOOT_TEST_API_KEY", "MOOT_TEST_TOKEN", "MOOT_TEST_SECRET_X", "MOOT_TEST_PLAIN", "MOOT_TEST_NEEDED_KEY"):
        monkeypatch.setenv(k, "v")
    sim = stdio.StdioSimulator(_script(tmp_path, ECHO), _info(imp), time_cap_s=20)
    res = sim.simulate(_req(imp))
    assert res.p_win_ai == 0.25 and res.provider_id == "fake" and res.latency_s > 0
    assert res.notes == "MOOT_TEST_PLAIN|Why 5 things?"        # the three secret-looking names were stripped
    declared = stdio.StdioSimulator(_script(tmp_path, ECHO), _info(imp), time_cap_s=20, env=["MOOT_TEST_NEEDED_KEY"])
    assert declared.simulate(_req(imp)).notes == "MOOT_TEST_NEEDED_KEY,MOOT_TEST_PLAIN|Why 5 things?"
    assert stdio.scrub_env({"A_KEY": "1", "B": "2", "my_token": "3"}) == {"B": "2"}


def test_stdio_time_cap_kills_and_declines(imp, tmp_path):
    import time

    stdio = imp("mootcourt.simulators.stdio")
    cmd = _script(tmp_path, "import time\ntime.sleep(30)\n")
    sim = stdio.StdioSimulator(cmd, _info(imp), time_cap_s=0.5)
    t0 = time.perf_counter()
    assert sim.simulate(_req(imp)) is None
    assert time.perf_counter() - t0 < 10 and "time cap" in sim.last_note
    short = stdio.StdioSimulator(cmd, _info(imp), time_cap_s=60)          # the request budget caps it too
    t0 = time.perf_counter()
    assert short.simulate(_req(imp, budget=imp("mootcourt.simulators").Budget(10, 0.5))) is None
    assert time.perf_counter() - t0 < 10


def test_stdio_failures_are_declines_with_a_reason(imp, tmp_path):
    stdio = imp("mootcourt.simulators.stdio")
    for body, word in (("import sys\nsys.exit(3)\n", "exit code 3"), ("print('not json')\n", "invalid output"),
                       ("print('{\"p_win_ai\": 7}')\n", "invalid output"), ("print('null')\n", "declined")):
        sim = stdio.StdioSimulator(_script(tmp_path, body), _info(imp), time_cap_s=20)
        assert sim.simulate(_req(imp)) is None and word in sim.last_note
    assert stdio.StdioSimulator(["/no/such/binary"], _info(imp)).simulate(_req(imp)) is None


class _Server:
    """A loopback HTTP agent that counts its calls."""

    def __init__(self, reply=None, status=200):
        outer = self
        self.calls, self.seen = 0, []
        self.reply = reply if reply is not None else {"p_win_ai": 0.6, "point_ai": 0.2}

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                outer.calls += 1
                outer.seen.append(json.loads(body))
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(outer.reply).encode())

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/simulate"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


def test_http_roundtrip_on_loopback_and_remote_refusal(imp):
    base, httpmod = imp("mootcourt.simulators"), imp("mootcourt.simulators.http")
    srv = _Server()
    try:
        sim = httpmod.HttpSimulator(srv.url, _info(imp), time_cap_s=10)
        res = sim.simulate(_req(imp))
        assert res.p_win_ai == 0.6 and res.point_ai == 0.2 and srv.calls == 1
        assert set(srv.seen[0]) == EXPECTED_REQUEST_FIELDS                  # nothing but the schema is sent
    finally:
        srv.close()
    with pytest.raises(base.SimulatorError):
        httpmod.HttpSimulator("http://example.org/simulate", _info(imp))
    httpmod.HttpSimulator("http://example.org/simulate", _info(imp), allow_remote=True)      # explicit flag, nothing is sent
    with pytest.raises(base.SimulatorError):
        httpmod.HttpSimulator("ftp://127.0.0.1/x", _info(imp))
    assert httpmod.is_loopback_host("127.0.0.1") and httpmod.is_loopback_host("localhost") and httpmod.is_loopback_host("::1")
    assert not httpmod.is_loopback_host("10.0.0.5") and not httpmod.is_loopback_host("example.org") and not httpmod.is_loopback_host(None)


def test_http_bad_reply_and_dead_server_are_declines(imp):
    httpmod = imp("mootcourt.simulators.http")
    srv = _Server(reply={"p_win_ai": 9})
    try:
        sim = httpmod.HttpSimulator(srv.url, _info(imp), time_cap_s=10)
        assert sim.simulate(_req(imp)) is None and "invalid output" in sim.last_note
    finally:
        srv.close()
    assert sim.simulate(_req(imp)) is None and "request failed" in sim.last_note       # the server is gone


def test_recorded_adapter_replays_by_request_hash(imp, tmp_path):
    rec, base = imp("mootcourt.simulators.recorded"), imp("mootcourt.simulators")
    r1, r2 = _req(imp), _req(imp, variant_headline="other")
    rows = [{"request_hash": r1.request_hash(), "provider_id": "agent", "version": "3", "knowledge_cutoff": "2025-01-01", "declined": False,
             "result": {"p_win_ai": 0.7}},
            {"request_hash": r2.request_hash(), "provider_id": "agent", "version": "3", "knowledge_cutoff": "2025-01-01", "declined": True,
             "result": None}]
    path = tmp_path / "a.jsonl"
    rec.write_records(path, rows)
    sim = rec.RecordedSimulator(path)
    assert sim.simulate(r1).p_win_ai == 0.7 and sim.simulate(r2) is None
    assert sim.simulate(_req(imp, variant_headline="never seen")) is None
    info = sim.describe()
    assert (info.provider_id, info.version, info.knowledge_cutoff) == ("agent", "3", "2025-01-01")
    rec.write_records(tmp_path / "mixed.jsonl", [rows[0], {**rows[1], "version": "4"}])
    with pytest.raises(base.SimulatorError):
        rec.RecordedSimulator(tmp_path / "mixed.jsonl")
    (tmp_path / "bad.jsonl").write_text("{not json}\n")
    with pytest.raises(base.SimulatorError):
        rec.read_records(tmp_path / "bad.jsonl")


# ------------------------------------------------------------------ cache and runner
class _Counting:
    def __init__(self):
        self.calls = 0
        self.last_note = ""

    def describe(self):
        return imp_info("counting", "1")

    def simulate(self, request):
        self.calls += 1
        return None if "decline" in request.variant_headline else imp_result(0.3)


def imp_info(pid, version):
    from mootcourt.simulators import SimulatorInfo

    return SimulatorInfo(pid, version, None, "per_call", "counts calls")


def imp_result(p):
    from mootcourt.simulators import SimulationResult

    return SimulationResult(p_win_ai=p, cost_usd=0.01, latency_s=0.2)


def test_cache_hit_never_calls_the_agent_again(imp, tmp_path):
    runner, cache_mod = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.cache")
    heads = ["h0", "h1", "decline me", "h3"]
    items = [runner.RequestItem(f"r{i}", "2014-07-01T00:00:00+00:00", _req(imp, variant_headline=h)) for i, h in enumerate(heads)]
    cache = cache_mod.SimulationCache(tmp_path / "cache" / "simulators")
    sim = _Counting()
    first = runner.run(sim, items, tmp_path / "a.jsonl", cache)
    assert (sim.calls, first.n_called, first.n_cached, first.n_declined) == (4, 4, 0, 1)
    assert abs(first.cost_usd - 0.03) < 1e-9
    again = runner.run(sim, items, tmp_path / "b.jsonl", cache)
    assert sim.calls == 4 and (again.n_called, again.n_cached, again.n_declined) == (0, 4, 1)      # declines are cached too
    assert again.cost_usd == 0.0
    h = items[0].request.request_hash()
    assert (tmp_path / "cache" / "simulators" / "counting" / "1" / f"{h}.json").is_file()
    runner.run(_Counting(), items, tmp_path / "c.jsonl", cache_mod.SimulationCache(tmp_path / "other"))      # another root: no hits
    sim2 = _Counting()
    sim2.describe = lambda: imp_info("counting", "2")                      # a new version has its own folder
    assert runner.run(sim2, items, tmp_path / "d.jsonl", cache).n_cached == 0
    recs = [json.loads(line) for line in (tmp_path / "a.jsonl").read_text().splitlines()]
    need = {"request_hash", "provider_id", "version", "knowledge_cutoff", "declined", "result", "latency_s", "cost_usd", "row_id", "origin"}
    assert need <= set(recs[0])
    assert [r["declined"] for r in recs] == [False, False, True, False]


def test_stdio_agent_is_not_reinvoked_on_a_cache_hit(imp, tmp_path):
    runner, cache_mod, stdio = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.cache"), imp("mootcourt.simulators.stdio")
    counter = tmp_path / "count.txt"
    cmd = _script(tmp_path, f"""
        import json, sys
        sys.stdin.readline()
        open({str(counter)!r}, "a").write("x")
        print(json.dumps({{"p_win_ai": 0.1}}))
    """)
    sim = stdio.StdioSimulator(cmd, _info(imp), time_cap_s=20)
    items = [runner.RequestItem("r0", "2014-07-01T00:00:00+00:00", _req(imp))]
    cache = cache_mod.SimulationCache(tmp_path / "c")
    runner.run(sim, items, tmp_path / "1.jsonl", cache)
    runner.run(sim, items, tmp_path / "2.jsonl", cache)
    assert counter.read_text() == "x"


def test_request_set_is_the_set_the_backtest_scores(imp, make_synth):
    runner, harness = imp("mootcourt.simulators.runner"), imp("mootcourt.harness")
    ledger, _ = make_synth(seed=21, n_tests=150, variants_per_test=1)
    items = runner.build_requests(ledger)
    scores = harness.rolling_origin(ledger, {"P0": harness.default_rungs("synthetic", ledger)["P0"]}, harness.quarterly_origins(ledger))
    assert sorted(i.row_id for i in items) == sorted(scores["row_id"])
    by_row = {i.row_id: i for i in items}
    for r in scores.head(5).itertuples():
        assert abs(by_row[r.row_id].request.s_star - r.s_star) < 1e-9
        assert by_row[r.row_id].request.origin == r.origin.isoformat()
    assert len(runner.build_requests(ledger, limit=3)) == 3
    for it in items[:20]:
        assert set(it.request.to_wire()) == EXPECTED_REQUEST_FIELDS


# ------------------------------------------------------------------ registration and CLI
def test_toml_registration_and_entry_points(imp, tmp_path, monkeypatch):
    loader, base = imp("mootcourt.simulators.loader"), imp("mootcourt.simulators")
    cmd = json.dumps(_script(tmp_path, ECHO))
    conf = tmp_path / "mootcourt.toml"
    conf.write_text(f"""
[simulators.my_agent]
adapter = "stdio"
command = {cmd}
version = "0.3"
knowledge_cutoff = "2025-06-01"
cost_model = "per_call"
description = "echo agent"
time_cap_s = 20

[simulators.off]
adapter = "stdio"
command = {cmd}
enabled = false

[simulators.replay]
adapter = "recorded"
path = "{tmp_path / 'none.jsonl'}"
""", encoding="utf-8")
    names = loader.provider_names(conf)
    assert "my_agent" in names and "off" not in names and {"null", "heuristic"} <= set(names)
    sim = loader.get_simulator("my_agent", conf)
    info = sim.describe()
    assert (info.provider_id, info.version, info.knowledge_cutoff, info.cost_model) == ("my_agent", "0.3", "2025-06-01", "per_call")
    assert sim.simulate(_req(imp)).p_win_ai == 0.25
    with pytest.raises(base.SimulatorError, match="known:"):
        loader.get_simulator("nope", conf)
    rows = {r["name"]: r for r in loader.describe_all(conf)}
    assert rows["my_agent"]["adapter"] == "stdio" and rows["heuristic"]["adapter"] == "builtin"
    assert "unavailable" in rows["replay"]["description"]                   # a broken table does not hide the others

    class Fake:
        def describe(self):
            return _info(imp, provider_id="ep_agent", knowledge_cutoff="2025-01-01")

        def simulate(self, request):
            return None

    class EP:
        name = "ep_agent"

        def load(self):
            return Fake

    monkeypatch.setattr(loader.metadata, "entry_points", lambda group=None: [EP()] if group == "mootcourt.simulators" else [])
    assert "ep_agent" in loader.provider_names(conf) and loader.get_simulator("ep_agent", conf).describe().provider_id == "ep_agent"
    assert loader.ENTRY_POINT_GROUP == "mootcourt.simulators"


def test_toml_may_not_shadow_a_builtin(imp, tmp_path):
    loader, base = imp("mootcourt.simulators.loader"), imp("mootcourt.simulators")
    conf = tmp_path / "mootcourt.toml"
    conf.write_text('[simulators.null]\nadapter = "stdio"\ncommand = ["true"]\n', encoding="utf-8")
    with pytest.raises(base.SimulatorError, match="shadow"):
        loader.get_simulator("null", conf)


def test_repo_config_lists_the_example_provider(imp):
    loader = imp("mootcourt.simulators.loader")
    assert (ROOT / "mootcourt.toml").is_file()
    assert "example_stdio" in loader.provider_names(ROOT / "mootcourt.toml")


def _cli(imp, args, env=None):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env=env)


def test_cli_simulators_run_and_list(imp, tmp_path, make_synth):
    ledger_mod, registry = imp("mootcourt.ledger"), imp("mootcourt.registry")
    ledger, _ = make_synth(seed=33, n_tests=120, variants_per_test=1)
    root = tmp_path / "root"
    ledger_mod.write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    env = {"MOOTCOURT_DATA_ROOT": str(root)}
    out = tmp_path / "heur.jsonl"
    res = _cli(imp, ["simulators", "run", "--provider", "heuristic", "--source", "synthetic", "--origins", "quarterly", "--out", str(out)], env)
    assert res.exit_code == 0, res.output
    recs = [json.loads(line) for line in out.read_text().splitlines()]
    assert recs and all(r["provider_id"] == "heuristic" and r["version"] == "1" and r["request_hash"] and not r["declined"] for r in recs)
    assert all({"latency_s", "cost_usd", "knowledge_cutoff"} <= set(r) for r in recs)
    assert list((root / "cache" / "simulators" / "heuristic" / "1").glob("*.json"))
    again = _cli(imp, ["simulators", "run", "--provider", "heuristic", "--source", "synthetic", "--out", str(tmp_path / "h2.jsonl")], env)
    assert "0 called" in again.output and f"{len(recs)} from the cache" in again.output
    bad = _cli(imp, ["simulators", "run", "--provider", "nope", "--source", "synthetic", "--out", str(tmp_path / "x.jsonl")], env)
    assert bad.exit_code != 0
    reg = registry.Registry(root / "models")
    reg.register_model("synthetic", "m1")
    reg.set_second_opinion_weight("synthetic", "heuristic", "1", 0.25, {"why": "test"})
    listed = _cli(imp, ["simulators", "list"], env)
    assert listed.exit_code == 0
    line = next(ln for ln in listed.output.splitlines() if ln.startswith("heuristic"))
    assert "synthetic=0.25" in line and "builtin" in line
    assert "0 (not earned)" in next(ln for ln in listed.output.splitlines() if ln.startswith("null"))


# ------------------------------------------------------------------ docs and examples
def _code_blocks(text):
    out, cur, lang = [], None, None
    for line in text.splitlines():
        if line.startswith("```"):
            if cur is None:
                cur, lang = [], line[3:].strip()
            else:
                out.append((lang, cur))
                cur = None
        elif cur is not None:
            cur.append(line)
    return out


def test_docs_have_two_examples_under_thirty_lines(imp):
    text = (ROOT / "docs" / "simulators.md").read_text(encoding="utf-8")
    blocks = _code_blocks(text)
    python_blocks = [b for lang, b in blocks if lang == "python"]
    http_blocks = [b for lang, b in blocks if lang == "python" and any("http" in ln.lower() for ln in b)]
    assert python_blocks and http_blocks and any("stdin" in "\n".join(b) for b in python_blocks)
    assert all(len(b) < 30 for lang, b in blocks if lang in ("python", "toml", "json"))
    for word in ("moot simulators run", "--second-opinion", "earn-weight", "knowledge cutoff", "mootcourt.simulators", "zero"):
        assert word.lower() in text.lower(), word


def test_stdio_example_works_and_persona_template_is_a_marked_stub(imp):
    stdio = imp("mootcourt.simulators.stdio")
    ex = ROOT / "examples" / "simulators"
    sim = stdio.StdioSimulator([sys.executable, str(ex / "stdio_agent.py")], _info(imp, provider_id="example_stdio"), time_cap_s=20)
    res = sim.simulate(_req(imp))
    assert res is not None and 0.0 <= res.p_win_ai <= 1.0 and res.n_simulated >= 1
    tpl = (ex / "persona_pool_template.py").read_text(encoding="utf-8")
    assert "STUB" in tpl and "ask_persona" in tpl
    import ast

    tree = ast.parse(tpl)
    mods = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | \
           {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= {"hashlib", "json", "math", "sys"}                      # the stub needs no client library of any kind
    proc = __import__("subprocess").run([sys.executable, str(ex / "persona_pool_template.py")], input=json.dumps(_req(imp).to_wire()) + "\n",
                                        capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0 and 0.0 <= json.loads(proc.stdout)["p_win_ai"] <= 1.0
    assert "readme" in "".join(p.name.lower() for p in ex.iterdir())


def test_importing_the_package_loads_no_model_client(imp):
    import subprocess

    code = ("import sys, mootcourt.simulators.loader, mootcourt.simulators.scoring\n"
            "bad = {'requests', 'httpx', 'urllib3', 'aiohttp', 'grpc'}\nprint(bad & set(sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    assert out == "set()"
