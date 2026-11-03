"""Chunk F: fixes for the findings of the chunk E review and the final tester's bugs."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from test_loop_extra import _world


# ------------------------------------------------------------ BUG-001 (T-045): AppleDouble sidecars on exFAT
def test_hidden_files_helper_skips_dot_files(tmp_path):
    from mootcourt.storage import is_hidden, visible_glob

    for name in ("a.json", ".hidden.json", "._a.json", ".DS_Store"):
        (tmp_path / name).write_bytes(b"\x00\x05\x16\x07")
    assert [p.name for p in visible_glob(tmp_path, "*.json")] == ["a.json"]
    assert is_hidden("._x") and is_hidden(".y") and not is_hidden("x._y")
    assert visible_glob(tmp_path / "missing", "*.json") == []


def test_join_skips_binary_sidecars_in_cards_and_outcomes(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    (dirs["cards"] / "outcomes").mkdir(exist_ok=True)
    sidecar = b"\x00\x05\x16\x07\xb0binary-sidecar"
    (dirs["cards"] / "._card.json").write_bytes(sidecar)
    (dirs["cards"] / "outcomes" / "._outcome.json").write_bytes(sidecar)
    later = new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1)
    res = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                             source="synthetic", now=later)
    assert res.n_outcomes == 6
    again = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                               source="synthetic", now=later)       # outcomes now hold a sidecar too: load_outcomes must skip it
    assert again.n_outcomes == 0
    assert loop.load_outcomes(dirs["cards"], "synthetic")


def test_no_unfiltered_glob_over_the_data_root_remains():
    """Every glob or directory walk in the package goes through the storage helpers or filters dot files itself."""
    import re
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "mootcourt"
    bad = []
    for p in src.rglob("*.py"):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.glob\(|\.rglob\(|\.iterdir\(|os\.listdir|glob\.glob", line) and "is_hidden" not in line \
                    and "startswith(\".\")" not in line and "visible_" not in line and p.name != "storage.py":
                bad.append(f"{p.name}:{n}: {line.strip()}")
    assert not bad, "\n".join(bad)


# ------------------------------------------------------------ REV-026 (T-044): the Upworthy horizon is test level
def test_upworthy_horizon_is_the_same_for_every_contrast_of_a_test(imp):
    from pathlib import Path

    import pandas as pd

    up = imp("mootcourt.sources.upworthy")
    fixture = Path(__file__).parent / "fixtures" / "upworthy_late_variants.csv"
    led = up.load_upworthy(fixture)
    raw = pd.read_csv(fixture, dtype=str)
    raw["created"] = pd.to_datetime(raw["created_at"], utc=True, format="ISO8601")
    last = raw.groupby("clickability_test_id")["created"].max()
    horizon = pd.Timedelta(days=7)
    multi = led[led["status"] != "single_arm"]
    assert len(multi) > 100
    for test_id, g in multi.groupby("test_id"):
        assert (g["usable_after"] == last[test_id] + horizon).all(), test_id
        assert (g["final_read_at"] == g["usable_after"]).all()
        assert (g["started_at"] + horizon <= g["usable_after"]).all()      # started_at stays per contrast
    assert (multi["period"] == multi["final_read_at"].map(imp("mootcourt.ledger").quarter_of)).all()
    # a test whose arms were created at different times has contrasts with different started_at but one usable_after
    assert (multi.groupby("test_id")["started_at"].nunique() > 1).any()


# ------------------------------------------------------------ REV-007 (T-044): gates count tests, not rows
def _frame_with_tests(rows_per_test: int):

    from test_review_d2 import _two_period_frame

    rows, table = _two_period_frame(informative_late=True)
    rows = rows.assign(test_id=[f"t{i // rows_per_test}" for i in range(len(rows))])
    return rows, table


def test_earn_gate_counts_judged_tests_not_rows(imp):
    from test_review_d2 import _Probs

    so = imp("mootcourt.predictors.second_opinion")
    rows, table = _frame_with_tests(rows_per_test=1)
    res = so.earn_weight(_Probs(table), rows, n_gate=150, margin=0.01)
    assert res.weight > 0 and res.n_tests == 200                     # 200 judged rows from 200 tests clear a gate of 150
    rows, table = _frame_with_tests(rows_per_test=4)
    res = so.earn_weight(_Probs(table), rows, n_gate=150, margin=0.01)
    assert res.weight == 0.0 and res.n == 200 and res.n_tests == 50  # the same 200 judged rows from 50 tests do not
    assert "tests" in res.message and "gate of 150" in res.message


def test_promotion_gate_compares_tests_with_the_gate(imp, tmp_path):
    regm = imp("mootcourt.registry")
    reg = regm.Registry(tmp_path)
    reg.register_model("s", "champ", {"brier_skill": 0.05, "n": 5000, "n_tests": 5000})
    reg.register_model("s", "chall", {"brier_skill": 0.20, "n": 5000, "n_tests": 100})
    res = reg.promote("s", {"n_200": 300, "n_400": 800})
    assert not res.promoted and "tests" in res.reason
    reg2 = regm.Registry(tmp_path / "ok")
    reg2.register_model("s", "champ", {"brier_skill": 0.05, "n": 5000, "n_tests": 5000})
    reg2.register_model("s", "chall", {"brier_skill": 0.20, "n": 5000, "n_tests": 900})
    assert reg2.promote("s", {"n_200": 300, "n_400": 800}).promoted


def test_backtest_summary_carries_the_test_count(imp):
    regm = imp("mootcourt.registry")
    report = {"header": {"snapshot_id": "x"}, "tables": {"aggregate": [
        {"cell": "ALL", "rung": "P2", "brier_skill": 0.1, "brier_skill_lo": 0.0, "brier_skill_hi": 0.2, "n": 900, "n_tests": 300, "logscore": -1.0}]}}
    assert regm.backtest_summary(report, "r.json")["n_tests"] == 300


# ------------------------------------------------------------ REV-019, 022, 024 (T-044): the report card
def _benchmark(imp, make_synth, tmp_path, gates=None, seed=57):
    import json as _json

    from typer.testing import CliRunner

    ledger, _ = make_synth(seed=seed, n_tests=200, variants_per_test=2)
    path = tmp_path / "acme.parquet"
    imp("mootcourt.ledger").write_ledger(ledger, path)
    (tmp_path / "reports").mkdir(exist_ok=True)
    if gates is not None:
        (tmp_path / "reports" / "gates.json").write_text(_json.dumps(gates))
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["benchmark", "--ledger", str(path), "--bootstrap", "40"],
                             env={"MOOTCOURT_DATA_ROOT": str(tmp_path)})
    assert res.exit_code == 0, res.output
    md = next((tmp_path / "reports" / "benchmark").glob("acme-*.md"))
    js = next((tmp_path / "reports" / "benchmark").glob("acme-*.json"))
    return md.read_text(encoding="utf-8"), json.loads(js.read_text(encoding="utf-8"))


def test_report_card_states_the_interval_level_the_code_computes(imp, make_synth, tmp_path):
    from mootcourt.harness_stats import LEVEL

    md, card = _benchmark(imp, make_synth, tmp_path, gates={"n_200": 20, "n_400": 30})
    assert f"Intervals are {round(LEVEL * 100)} percent" in md
    assert "95 percent" not in md
    bench = (Path(__file__).resolve().parents[1] / "docs" / "benchmark.md").read_text(encoding="utf-8")
    assert f"{round(LEVEL * 100)} percent" in bench and "95 percent" not in bench


def test_decidable_columns_follow_the_targets_in_the_gates_file(imp, make_synth, tmp_path):
    gates = {"n_200": 20, "n_400": 30, "decision_target": 0.95, "target_power": 0.95,
             "by_target": {"0.70": {"n_200": 10, "n_400": 20}, "0.95": {"n_200": 20, "n_400": 30}}}
    md, card = _benchmark(imp, make_synth, tmp_path, gates=gates)
    header = next(line for line in md.splitlines() if line.startswith("| rung"))
    assert "decidable at 0.95" in header and "decidable at 0.70" in header
    assert "decidable at 0.90" not in header and "decidable at 0.80" not in header
    assert card["research_target"] == 0.70 and card["decision_target"] == 0.95


def test_a_single_target_gates_file_gives_one_decidable_column(imp, make_synth, tmp_path):
    gates = {"n_200": 20, "n_400": 30, "decision_target": 0.9, "by_target": {"0.90": {"n_200": 20, "n_400": 30}}}
    md, card = _benchmark(imp, make_synth, tmp_path, gates=gates)
    header = next(line for line in md.splitlines() if line.startswith("| rung"))
    assert header.count("decidable at") == 1


def test_quick_gates_never_touch_the_shared_gates_file(imp, make_synth, tmp_path, monkeypatch):
    from mootcourt import benchmark

    monkeypatch.setitem(benchmark.QUICK_GATES, "reps", 40)
    monkeypatch.setitem(benchmark.QUICK_GATES, "B", 40)
    md, card = _benchmark(imp, make_synth, tmp_path, gates=None)
    assert not (tmp_path / "reports" / "gates.json").exists()
    quick = tmp_path / "reports" / "benchmark" / "gates-quick.json"
    assert quick.is_file()
    assert "gates-quick.json" in md and "quick power simulation" in card["gates_source"]
    md2, card2 = _benchmark(imp, make_synth, tmp_path / "other", gates={"n_200": 20, "n_400": 30})
    assert "gates.json" in card2["gates_source"] and "gates-quick" not in card2["gates_source"]


# ------------------------------------------------------------ REV-020, 021, 023, 031 (T-044): doctor and init
def _reliability_file(reports, report_as_of, cells):
    reports.mkdir(parents=True, exist_ok=True)
    doc = {"source": "s", "as_of": report_as_of.isoformat(), "cells": {c: {"as_of": a.isoformat()} for c, a in cells.items()}}
    (reports / "reliability-s.json").write_text(json.dumps(doc))


def test_doctor_checks_every_cell_as_of_with_the_cards_exact_rule(imp, tmp_path):
    ob, storage = imp("mootcourt.onboarding"), imp("mootcourt.storage")
    now = dt.datetime(2026, 1, 20, tzinfo=dt.timezone.utc)
    paths = storage.storage_paths(root=tmp_path)
    _reliability_file(paths.reports, now - dt.timedelta(days=1), {
        "old_cell": now - dt.timedelta(days=30), "edge_cell": now - dt.timedelta(days=14, hours=1),
        "fresh_cell": now - dt.timedelta(days=2)})
    out = ob.check_reliability(paths, now)
    assert len(out) == 1 and out[0]["status"] == "warn"
    detail = out[0]["detail"]
    assert "old_cell" in detail and "edge_cell" in detail and "fresh_cell" not in detail
    assert "moot join refreshes" not in detail and "until new outcomes" in detail
    _reliability_file(paths.reports, now - dt.timedelta(days=1), {"fresh_cell": now - dt.timedelta(days=2)})
    assert ob.check_reliability(paths, now)[0]["status"] == "ok"


def test_doctor_and_the_card_agree_on_staleness(imp):
    ab = imp("mootcourt.abstain")
    now = dt.datetime(2026, 1, 20, tzinfo=dt.timezone.utc)
    for age in (dt.timedelta(days=13, hours=23), dt.timedelta(days=14), dt.timedelta(days=14, seconds=1), dt.timedelta(days=30)):
        as_of = (now - age).isoformat()
        report = {"as_of": as_of, "cells": {"c": {"as_of": as_of}}}
        card_says_stale = (ab.reliability_reason(report, "c", now) or "").startswith("reliability report is older")
        assert (ab.staleness_reason(as_of, now) is not None) == card_says_stale


def _uncomment_example(text: str) -> dict:
    import tomllib

    lines, keep = text.splitlines(), []
    on = False
    for line in lines:
        if line.startswith("# [simulators."):
            on = True
        elif on and not line.startswith("# "):
            on = False
        if on:
            keep.append(line[2:])
    return tomllib.loads("\n".join(keep))["simulators"]["my_agent"]


def test_the_simulator_example_that_init_writes_loads_when_uncommented(imp, tmp_path):
    ob, loader = imp("mootcourt.onboarding"), imp("mootcourt.simulators.loader")
    table = _uncomment_example(ob.config_text(tmp_path, ["a"], "demo"))
    assert "knowledge_cutoff" in table
    sim = loader.from_table("my_agent", table, base_dir=tmp_path)
    assert sim.describe().knowledge_cutoff == table["knowledge_cutoff"]


def test_init_writes_valid_toml_for_names_with_quotes_spaces_and_backslashes(imp, tmp_path, monkeypatch):
    import tomllib

    ob = imp("mootcourt.onboarding")
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    weird_root = tmp_path / 'data "root" with space' / "back\\slash"
    ob.init_project(tmp_path / "proj", data_root=weird_root, cells=['pay "now"', "back\\slash", "plain"], name='My "pilot" \\ project')
    cfg = tomllib.loads((tmp_path / "proj" / "mootcourt.toml").read_text(encoding="utf-8"))
    assert cfg["project"]["name"] == 'My "pilot" \\ project'
    assert cfg["storage"]["data_root"] == str(weird_root.resolve())
    assert cfg["cells"]["names"] == ['pay "now"', "back\\slash", "plain"]


def test_init_refuses_control_characters_in_names(imp, tmp_path):
    import pytest

    ob = imp("mootcourt.onboarding")
    with pytest.raises(ValueError, match="control"):
        ob.init_project(tmp_path / "p2", data_root=tmp_path / "r", name="bad\nname")


def test_doctor_contacts_only_loopback_http_services(imp):
    ob = imp("mootcourt.onboarding")
    for url in ("http://example.com:8000", "ftp://127.0.0.1/x", "file:///etc/passwd"):
        got = ob.check_service(url)
        assert got[0]["status"] == "warn" and "not contacted" in got[0]["detail"], url


# ------------------------------------------------------------ REV-001, 003, 004 (T-044): the simulator adapters
def _pid_alive(pid: int) -> bool:
    import os

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_stdio_kills_the_whole_group_when_the_wait_is_interrupted(imp, tmp_path, monkeypatch):
    import subprocess
    import sys
    import time

    import pytest
    from test_simulators import _info, _req

    stdio = imp("mootcourt.simulators.stdio")
    pidfile = tmp_path / "grandchild.pid"
    sh = f"sleep 300 & echo $! > {pidfile}; wait"

    class Interrupted(subprocess.Popen):
        def wait(self, timeout=None):
            if timeout is not None and not getattr(self, "_raised", False):
                self._raised = True
                for _ in range(100):
                    if pidfile.exists() and pidfile.read_text().strip():
                        break
                    time.sleep(0.05)
                raise KeyboardInterrupt
            return super().wait(timeout)

    monkeypatch.setattr(stdio.subprocess, "Popen", Interrupted)
    sim = stdio.StdioSimulator(["sh", "-c", sh], _info(imp), time_cap_s=60)
    with pytest.raises(KeyboardInterrupt):
        sim.simulate(_req(imp))
    pid = int(pidfile.read_text())
    for _ in range(50):
        if not _pid_alive(pid):
            break
        time.sleep(0.1)
    assert not _pid_alive(pid), "the grandchild survived the interrupt"
    del sys


def test_the_data_root_refusal_covers_cwd_module_paths_option_values_and_case(imp, tmp_path, monkeypatch):
    import sys

    import pytest
    from test_simulators import _info

    stdio, base = imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators")
    root = tmp_path / "dataroot"
    (root / "lib").mkdir(parents=True)
    (root / "lib" / "evilmod.py").write_text("print('null')\n")
    (root / "agent.py").write_text("print('null')\n")
    outside = tmp_path / "ok.py"
    outside.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    # the working directory itself is inside the data root
    with pytest.raises(base.SimulatorError, match="data root"):
        stdio.StdioSimulator([sys.executable, str(outside)], _info(imp), cwd=str(root))
    # a module run with -m that lives inside the root
    monkeypatch.syspath_prepend(str(root / "lib"))
    with pytest.raises(base.SimulatorError, match="data root"):
        stdio.StdioSimulator([sys.executable, "-m", "evilmod"], _info(imp))
    # an option value: --opt=path
    with pytest.raises(base.SimulatorError, match="data root"):
        stdio.StdioSimulator([sys.executable, str(outside), f"--config={root / 'agent.py'}"], _info(imp))
    stdio.StdioSimulator([sys.executable, str(outside)], _info(imp))                       # outside the root: allowed
    # a path spelled with other letter case on a case-insensitive volume
    probe = tmp_path / "CaseProbe"
    probe.mkdir()
    if (tmp_path / "caseprobe").exists():
        shouted = str(root / "agent.py").replace("dataroot", "DATAROOT")
        with pytest.raises(base.SimulatorError, match="data root"):
            stdio.StdioSimulator([sys.executable, shouted], _info(imp))


def test_http_deadline_is_a_wall_clock_for_a_dripping_server(imp):
    import http.server
    import threading
    import time

    from test_simulators import _info, _req

    class Drip(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "100000")
            self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b" ")
                    self.wfile.flush()
                    time.sleep(0.2)
            except OSError:
                pass

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Drip)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        httpmod = imp("mootcourt.simulators.http")
        sim = httpmod.HttpSimulator(f"http://127.0.0.1:{srv.server_address[1]}/x", _info(imp), time_cap_s=1.0)
        t0 = time.monotonic()
        res = sim.simulate(_req(imp))
        elapsed = time.monotonic() - t0
        assert res is None and sim.last_failure == "timeout"
        assert elapsed < 2.0, f"the exchange took {elapsed:.1f} s against a cap of 1 s"
    finally:
        srv.shutdown()
        srv.server_close()


# ------------------------------------------------------------ REV-002, 005, 006, 037 (T-044): records, cache, cutoffs
def test_replaying_a_records_file_does_not_cache_failures_or_missing_hashes(imp, tmp_path):
    from test_simulators import _req

    runner, cache_mod, rec_mod = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.cache"), imp("mootcourt.simulators.recorded")
    items = [runner.RequestItem(f"r{i}", "2014-07-01T00:00:00+00:00", _req(imp, variant_headline=f"Headline {i}")) for i in range(4)]
    h = [it.request.request_hash() for it in items]
    base = {"provider_id": "agent", "version": "1", "knowledge_cutoff": "2000-01-01", "latency_s": 0.0, "cost_usd": 0.0}
    rec_mod.write_records(tmp_path / "live.jsonl", [
        {**base, "request_hash": h[0], "declined": False, "result": {"p_win_ai": 0.4}},
        {**base, "request_hash": h[1], "declined": True, "result": None, "failure": "timeout", "note": "time cap"},
        {**base, "request_hash": h[2], "declined": True, "result": None, "note": "the agent declined"}])
    sim = rec_mod.RecordedSimulator(tmp_path / "live.jsonl")
    cache = cache_mod.SimulationCache(tmp_path / "cache")
    summary = runner.run(sim, items, tmp_path / "replay.jsonl", cache)
    out = {r["request_hash"]: r for r in rec_mod.read_records(tmp_path / "replay.jsonl")}
    assert out[h[1]].get("failure") and out[h[3]].get("failure") == "missing"        # the failure and the absent hash stay failures
    assert out[h[2]].get("failure") is None and out[h[2]]["declined"] is True         # a recorded decline is still a decline
    assert summary.n_failed == 2 and summary.n_declined == 1
    assert not list((tmp_path / "cache").rglob("*.json")), "a replay must not write the live agent's cache"


def _records_with(path, result=None, budget=None, cutoffs=("2000-01-01",)):
    lines = []
    for i, cutoff in enumerate(cutoffs):
        rec = {"request_hash": f"h{i}", "provider_id": "agent", "version": "1", "knowledge_cutoff": cutoff, "declined": False,
               "result": result or {"p_win_ai": 0.4}, "latency_s": 0.0, "cost_usd": 0.0, "row_id": f"row-{i}", "origin": "2014-07-01T00:00:00+00:00"}
        if budget is not None:
            rec["budget"] = budget
        lines.append(json.dumps(rec))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_infinity_and_out_of_range_values_in_a_records_file_name_the_record(imp, tmp_path):
    import pytest

    sc, base = imp("mootcourt.simulators.scoring"), imp("mootcourt.simulators")
    for result, budget in (({"p_win_ai": 0.4, "n_simulated": float("inf")}, None), ({"p_win_ai": 0.4, "n_simulated": 1e400}, None),
                           ({"p_win_ai": 0.4, "cost_usd": float("inf")}, None), ({"p_win_ai": 0.4, "n_simulated": -3}, None),
                           (None, {"max_respondents": float("inf"), "max_seconds": 30}), (None, {"max_respondents": 5, "max_seconds": float("nan")}),
                           (None, {"max_respondents": 5, "bogus": 1})):
        p = tmp_path / "r.jsonl"
        _records_with(p, result, budget)
        with pytest.raises(base.SimulatorError):
            sc.load_second_opinion(p)
    p = tmp_path / "ok.jsonl"
    _records_with(p, None, {"max_respondents": 50, "max_seconds": 20})
    assert sc.load_second_opinion(p).budget.max_respondents == 50


def test_mixed_knowledge_cutoffs_in_one_records_file_are_refused(imp, tmp_path):
    import pytest

    sc, base = imp("mootcourt.simulators.scoring"), imp("mootcourt.simulators")
    p = tmp_path / "mixed.jsonl"
    _records_with(p, cutoffs=("2000-01-01", "2020-01-01"))
    with pytest.raises(base.SimulatorError, match="cutoff"):
        sc.load_second_opinion(p)


def test_adapters_turn_infinity_in_an_agent_reply_into_an_invalid_failure(imp, tmp_path):
    from test_simulators import _info, _req, _script

    stdio = imp("mootcourt.simulators.stdio")
    cmd = _script(tmp_path, "import sys\nsys.stdin.readline()\nprint('{\"p_win_ai\": 0.4, \"n_simulated\": Infinity}')\n")
    sim = stdio.StdioSimulator(cmd, _info(imp), time_cap_s=20)
    assert sim.simulate(_req(imp)) is None and sim.last_failure == "invalid"


def test_a_cache_hit_rereads_the_cutoff_from_the_current_provider(imp, tmp_path):
    from test_simulators import _info, _req

    runner, cache_mod = imp("mootcourt.simulators.runner"), imp("mootcourt.simulators.cache")
    sc, base = imp("mootcourt.simulators.scoring"), imp("mootcourt.simulators")

    class Agent:
        def __init__(self, cutoff):
            self.cutoff = cutoff
            self.calls = 0

        def describe(self):
            return _info(imp, provider_id="agent", knowledge_cutoff=self.cutoff)

        def simulate(self, request):
            self.calls += 1
            return base.SimulationResult(p_win_ai=0.4)

    items = [runner.RequestItem("r0", "2014-07-01T00:00:00+00:00", _req(imp))]
    cache = cache_mod.SimulationCache(tmp_path / "cache")
    first = Agent("2014-01-01")
    runner.run(first, items, tmp_path / "a.jsonl", cache)
    origins = __import__("pandas").Series(__import__("pandas").to_datetime(["2014-07-01"], utc=True))
    data_a = sc.load_second_opinion(tmp_path / "a.jsonl")
    assert data_a.knowledge_cutoff == "2014-01-01" and sc.clean_mask(origins, data_a.knowledge_cutoff).tolist() == [True]
    second = Agent("2015-01-01")                                    # the provider's cutoff was corrected after the cache was filled
    out = runner.run(second, items, tmp_path / "b.jsonl", cache)
    assert second.calls == 0 and out.n_cached == 1                  # still a hit
    data_b = sc.load_second_opinion(tmp_path / "b.jsonl")
    assert data_b.knowledge_cutoff == "2015-01-01" and sc.clean_mask(origins, data_b.knowledge_cutoff).tolist() == [False]


def test_an_invalid_or_unreadable_cache_entry_is_a_miss(imp, tmp_path):
    from test_simulators import _req

    cache_mod = imp("mootcourt.simulators.cache")
    cache = cache_mod.SimulationCache(tmp_path / "cache")
    h = _req(imp).request_hash()
    cache.put("agent", "1", h, {"request_hash": h, "declined": False, "result": {"p_win_ai": 7.0}})
    assert cache.get("agent", "1", h) is None
    cache.put("agent", "1", h, {"request_hash": h, "declined": False, "result": {"p_win_ai": float("inf")}})
    assert cache.get("agent", "1", h) is None
    cache.path("agent", "1", h).write_text("{not json", encoding="utf-8")
    assert cache.get("agent", "1", h) is None
    cache.put("agent", "1", h, {"request_hash": h, "declined": False, "result": {"p_win_ai": 0.3}})
    assert cache.get("agent", "1", h)["result"]["p_win_ai"] == 0.3
    cache.put("agent", "1", h, {"request_hash": h, "declined": True, "result": None})
    assert cache.get("agent", "1", h)["declined"] is True


# ------------------------------------------------------------ importers (T-044 REV-008 to 013, 033, 042, 043; T-046 BUG-002; T-047 BUG-003)
FIX = Path(__file__).resolve().parent / "fixtures" / "importers"


def _cli_in(imp, args, cwd, monkeypatch):
    from typer.testing import CliRunner

    monkeypatch.chdir(cwd)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    return CliRunner().invoke(imp("mootcourt.cli").app, args)


def test_growthbook_bulk_snapshot_imports_from_the_command_line_with_started_at(imp, tmp_path, monkeypatch):      # BUG-002
    base = ["ingest", "--format", "growthbook", "--input", str(FIX / "growthbook_bulk.json"), "--source-name", "gb"]
    without = _cli_in(imp, [*base, "--dry-run"], tmp_path, monkeypatch)
    assert without.exit_code == 1 and "--started-at" in without.output                    # the error says what to pass
    dry = _cli_in(imp, [*base, "--started-at", "2024-06-01T00:00:00Z", "--dry-run"], tmp_path, monkeypatch)
    assert dry.exit_code == 0, dry.output
    real = _cli_in(imp, [*base, "--started-at", "2024-06-01T00:00:00Z"], tmp_path, monkeypatch)
    assert real.exit_code == 0, real.output
    led = imp("mootcourt.ledger").read_ledger(tmp_path / "data" / "ledger" / "ledger.parquet")
    assert len(led) == 1 and led["started_at"].iloc[0].isoformat().startswith("2024-06-01")
    own = _cli_in(imp, ["ingest", "--format", "growthbook", "--input", str(FIX / "growthbook_result.json"), "--source-name", "gb2", "--dry-run"],
                  tmp_path, monkeypatch)
    assert own.exit_code == 0                                                           # a result file that carries dateStart needs no option


def test_growthbook_records_which_path_gave_the_standard_error(imp, tmp_path):                                         # REV-010
    import copy

    doc = json.loads((FIX / "growthbook_result.json").read_text())
    dumped = copy.deepcopy(doc)

    def strip_se(o):
        if isinstance(o, dict):
            o.pop("effectStandardError", None)
            for v in o.values():
                strip_se(v)
        elif isinstance(o, list):
            for v in o:
                strip_se(v)

    strip_se(dumped)
    p = tmp_path / "no_se.json"
    p.write_text(json.dumps(dumped))
    v = imp("mootcourt.importers").read_format("growthbook", p, ci_level=0.90).iloc[0]
    assert "ciLow" in v["variance_method"] and "0.90" in v["variance_method"] and "assumed" in v["variance_method"]
    assert "symmetric bounds" in v["variance_method"]
    plain = imp("mootcourt.importers").read_format("growthbook", FIX / "growthbook_result.json").iloc[0]
    assert "effectStandardError" in plain["variance_method"] and "assumed" not in plain["variance_method"]


def test_harness_variance_method_names_the_assumed_level_when_the_threshold_is_missing(imp, tmp_path):             # REV-009
    import pandas as pd

    with_thr = imp("mootcourt.importers").read_format("harness", FIX / "harness.csv", experiment_id="x").iloc[0]
    assert "exported significance threshold" in with_thr["variance_method"] and "0.95" in with_thr["variance_method"]
    raw = pd.read_csv(FIX / "harness.csv").drop(columns=["Experiment significance threshold"])
    p = tmp_path / "h.csv"
    raw.to_csv(p, index=False)
    got = imp("mootcourt.importers").read_format("harness", p, experiment_id="x")
    assert all("0.95" in m and "assumed" in m for m in got["variance_method"])
    doc = json.loads((FIX / "harness.json").read_text())

    def drop_thr(o):
        if isinstance(o, dict):
            o.pop("significanceThreshold", None)
            for v in o.values():
                drop_thr(v)
        elif isinstance(o, list):
            for v in o:
                drop_thr(v)

    drop_thr(doc)
    pj = tmp_path / "h.json"
    pj.write_text(json.dumps(doc))
    gj = imp("mootcourt.importers").read_format("harness", pj)
    assert all("0.95" in m and "assumed" in m for m in gj["variance_method"])
    full = imp("mootcourt.importers").read_format("harness", FIX / "harness.json")
    assert all("assumed" not in m for m in full["variance_method"])


def test_jetstream_filters_on_analysis_basis_with_a_stated_default(imp, tmp_path):                                  # REV-008
    import pandas as pd
    import pytest

    raw = pd.read_csv(FIX / "jetstream.csv")
    twin = raw.assign(analysis_basis="exposures", point=raw["point"] + 0.5)
    p = tmp_path / "both.csv"
    pd.concat([raw, twin]).to_csv(p, index=False)
    kw = dict(experiment_id="n1", started_at="2024-04-01T00:00:00Z", ended_at="2024-04-30T00:00:00Z", n_baseline=10, n_variant=10)
    mod = imp("mootcourt.importers")
    default = mod.read_format("jetstream", p, **kw)
    assert len(default) == 1 and default.iloc[0]["effect"] == pytest.approx(0.05) and "enrollments" in default.iloc[0]["variance_method"]
    exposures = mod.read_format("jetstream", p, analysis_basis="exposures", **kw)
    assert exposures.iloc[0]["effect"] == pytest.approx(0.55) and "exposures" in exposures.iloc[0]["variance_method"]
    with pytest.raises(mod.MappingError, match="analysis_basis"):
        mod.read_format("jetstream", p, analysis_basis="nonsense", **kw)
    assert mod.check_exchange(default.assign(), None) is not None


def test_parquet_null_status_is_missing_not_the_text_none(imp, tmp_path):                                           # REV-011
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    rows = pd.DataFrame([{"experiment_id": "e1", "variant_id": "v", "metric_id": "m", "effect": 0.1, "se": 0.05, "n_baseline": 1000,
                          "n_variant": 1000, "started_at": "2024-01-01T00:00:00Z", "ended_at": "2024-01-15T00:00:00Z", "status": None,
                          "source_system": "t", "variance_method": "n"}])
    p = tmp_path / "x.parquet"
    rows.to_parquet(p)
    df = ex.read_table(p)
    assert not [v for v in ex.check_exchange(df, dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)) if v.column == "status"]
    led = ex.to_ledger(df, "t", now=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    assert led["status"].iloc[0] == "admitted"


def _exch(**over):
    row = {"experiment_id": "e1", "variant_id": "v", "metric_id": "m", "effect": "0.1", "se": "0.05", "n_baseline": "1000", "n_variant": "1000",
           "started_at": "2024-01-01T00:00:00Z", "ended_at": "2024-01-15T00:00:00Z", "source_system": "t", "variance_method": "n"}
    row.update(over)
    return row


NOW_2026 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)


def test_effect_unit_must_be_in_the_documented_set_and_agree_within_a_cell(imp):                                  # REV-012, BUG-003
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    banana = pd.DataFrame([_exch(effect_unit="banana")], dtype=str)
    got = ex.check_exchange(banana, NOW_2026)
    assert [v for v in got if v.column == "effect_unit" and v.severity == "error" and v.row == 1 and "banana" in v.message]
    mixed = pd.DataFrame([_exch(variant_id="a", effect_unit="relative"), _exch(variant_id="b", effect_unit="standardized"),
                          _exch(variant_id="c", effect_unit="relative"), _exch(variant_id="d", metric_id="other", effect_unit="absolute")], dtype=str)
    got = [v for v in ex.check_exchange(mixed, NOW_2026) if v.column == "effect_unit"]
    assert [v.row for v in got] == [2] and "standardized" in got[0].message and "relative" in got[0].message and "row 1" in got[0].message
    ok = pd.DataFrame([_exch(variant_id="a"), _exch(variant_id="b", effect_unit="absolute"), _exch(variant_id="c", effect_unit="")], dtype=str)
    assert not [v for v in ex.check_exchange(ok, NOW_2026) if v.column == "effect_unit"]
    explicit_cells = pd.DataFrame([_exch(variant_id="a", cell="k", effect_unit="relative"), _exch(variant_id="b", metric_id="m2", cell="k",
                                                                                                 effect_unit="absolute")], dtype=str)
    assert [v.row for v in ex.check_exchange(explicit_cells, NOW_2026) if v.column == "effect_unit"] == [2]        # the cell column decides the pool


def test_ledger_check_exits_1_for_a_bad_or_mixed_unit(imp, tmp_path, monkeypatch):                               # BUG-003 repro as a test
    import csv

    rows = list(csv.DictReader((Path(__file__).resolve().parents[1] / "examples" / "ledgers" / "sample.csv").open()))
    first_metric = rows[0]["metric_id"]
    for i, r in enumerate(rows):
        r["effect_unit"] = "standardized" if (i % 2 == 0 and r["metric_id"] == first_metric) else r.get("effect_unit") or "relative"
    for name, mutate in (("mixed.csv", lambda r: None), ("banana.csv", lambda r: r.__setitem__("effect_unit", "banana"))):
        for r in rows:
            mutate(r)
        with (tmp_path / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        res = _cli_in(imp, ["ledger", "check", str(tmp_path / name)], tmp_path, monkeypatch)
        assert res.exit_code == 1 and "effect_unit" in res.output, (name, res.output)


def test_a_cell_cannot_gain_a_second_unit_across_imports(imp, tmp_path, monkeypatch):                              # REV-012 ingest path
    import pandas as pd

    a = tmp_path / "a.csv"
    pd.DataFrame([_exch(variant_id="a", effect_unit="relative")]).to_csv(a, index=False)
    b = tmp_path / "b.csv"
    pd.DataFrame([_exch(experiment_id="e2", variant_id="a", effect_unit="standardized")]).to_csv(b, index=False)
    base = ["ingest", "--format", "generic", "--source-name", "units"]
    assert _cli_in(imp, [*base, "--input", str(a)], tmp_path, monkeypatch).exit_code == 0
    res = _cli_in(imp, [*base, "--input", str(b)], tmp_path, monkeypatch)
    assert res.exit_code == 1 and "standardized" in res.output and "relative" in res.output


def test_documented_units_match_the_importers(imp):                                                               # BUG-003
    import re

    ex = imp("mootcourt.importers.exchange")
    src = (Path(__file__).resolve().parents[1] / "src" / "mootcourt" / "importers").glob("*.py")
    used = set()
    for p in src:
        used |= set(re.findall(r'effect_unit="([a-z_]+)"', p.read_text(encoding="utf-8")))
        used |= set(re.findall(r'"effect_unit": "([a-z_]+)"', p.read_text(encoding="utf-8")))
    assert used and used <= set(ex.UNITS), used
    doc = (Path(__file__).resolve().parents[1] / "docs" / "ledger-format.md").read_text(encoding="utf-8")
    assert all(f"`{u}`" in doc for u in ex.UNITS)


def test_counts_above_two_to_the_53_or_non_finite_are_rejected_with_row_and_column(imp, tmp_path, monkeypatch):    # REV-013
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    df = pd.DataFrame([_exch(variant_id="a", n_baseline=str(2 ** 60)), _exch(variant_id="b", n_variant="inf"),
                       _exch(variant_id="c", n_baseline="nan"), _exch(variant_id="d")], dtype=str)
    got = {(v.row, v.column): v for v in ex.check_exchange(df, NOW_2026) if v.severity == "error"}
    assert (1, "n_baseline") in got and "too large" in got[(1, "n_baseline")].message
    assert (2, "n_variant") in got and (3, "n_baseline") in got and (4, "n_baseline") not in got
    p = tmp_path / "big.csv"
    df.iloc[[0]].to_csv(p, index=False)
    res = _cli_in(imp, ["ingest", "--format", "generic", "--input", str(p), "--source-name", "big"], tmp_path, monkeypatch)
    assert res.exit_code == 1 and "n_baseline" in res.output and "Traceback" not in res.output and "OverflowError" not in res.output


def test_a_given_admitted_status_cannot_override_a_derived_exclusion(imp):                                        # REV-033
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    df = pd.DataFrame([_exch(variant_id="a", status="admitted", srm_flag="true"), _exch(variant_id="b", status="admitted", n_baseline="5"),
                       _exch(variant_id="c", status="low_clicks"), _exch(variant_id="d", status="admitted")], dtype=str)
    led = ex.to_ledger(df, "t", now=NOW_2026)
    assert led["status"].tolist() == ["imbalance_flag", "low_exposure", "low_clicks", "admitted"]


def test_the_composed_row_key_cannot_collide(imp):                                                                # REV-042
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    df = pd.DataFrame([_exch(variant_id="a::b", metric_id="c"), _exch(variant_id="a", metric_id="b::c")], dtype=str)
    got = [v for v in ex.check_exchange(df, NOW_2026) if v.severity == "error"]
    assert {(v.row, v.column) for v in got} == {(1, "variant_id"), (2, "metric_id")} and all("::" in v.message for v in got)


def test_a_derived_standard_error_is_written_into_variance_method(imp):                                           # REV-043
    import pandas as pd

    vend = imp("mootcourt.importers.vendors")
    raw = pd.DataFrame({"e": ["x"], "v": ["a"], "m": ["k"], "eff": [0.1], "lo": [0.0], "hi": [0.2], "nb": [100], "nv": [100],
                        "s": ["2024-01-01T00:00:00Z"], "t": ["2024-01-09T00:00:00Z"]})
    mapping = {"columns": {"experiment_id": "e", "variant_id": "v", "metric_id": "m", "effect": "eff", "ci_low": "lo", "ci_high": "hi",
                           "n_baseline": "nb", "n_variant": "nv", "started_at": "s", "ended_at": "t"},
               "constants": {"source_system": "map", "variance_method": "vendor says normal"}, "options": {"ci_level": 0.9}}
    out = vend.apply_mapping(raw, mapping).iloc[0]
    assert "0.90" in out["variance_method"] and "ci_low" in out["variance_method"] and "vendor says normal" in out["variance_method"]
    plain = vend.apply_mapping(raw.assign(se=0.05), {**mapping, "columns": {**mapping["columns"], "se": "se"}}).iloc[0]
    assert "ci_low" not in plain["variance_method"]


# ------------------------------------------------------------ REV-014 (T-044) and BUG-004 (T-048): service and MCP cards
SAMPLE_NOW = "2025-12-30T00:00:00+00:00"


def _sample_project(imp, tmp_path, monkeypatch, threshold=None):
    from typer.testing import CliRunner

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    app = imp("mootcourt.cli").app
    for args in (["init"], ["ingest", "--format", "generic", "--input", "mootcourt-data/data/sample-ledger.csv", "--source-name", "sample"],
                 ["fit", "--source", "sample"], ["backtest", "--source", "sample"]):
        res = CliRunner().invoke(app, args)
        assert res.exit_code == 0, (args, res.output)
    if threshold is not None:
        cfg = (tmp_path / "mootcourt.toml").read_text(encoding="utf-8").replace("action_threshold = 0.35", f"action_threshold = {threshold}")
        (tmp_path / "mootcourt.toml").write_text(cfg)
    return tmp_path / "mootcourt-data"


def _cli_card(imp, extra=()):
    from typer.testing import CliRunner

    res = CliRunner().invoke(imp("mootcourt.cli").app, ["card", "--source", "sample", "--cell", "checkout_conversion", "--impressions", "20000",
                                                         "--now", SAMPLE_NOW, "--json", *extra])
    assert res.exit_code == 0, res.output
    return json.loads(res.output)


def test_service_and_mcp_use_the_configured_action_threshold_like_the_cli(imp, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    root = _sample_project(imp, tmp_path, monkeypatch, threshold=0.6)
    expected = _cli_card(imp)
    assert expected["robustness"]["action_threshold"] == 0.6
    now = dt.datetime.fromisoformat(SAMPLE_NOW)
    app = imp("mootcourt.service").create_app(root / "models", root / "cards_service", reports_dir=root / "reports", now=lambda: now)
    body = {"source": "sample", "cell": "checkout_conversion", "impressions": 20000}
    served = TestClient(app).post("/card", json=body)
    assert served.status_code == 200, served.text
    assert served.json()["robustness"]["action_threshold"] == 0.6
    assert served.json()["card_id"] == expected["card_id"] and served.json()["abstention"] == expected["abstention"]
    mcp = imp("mootcourt.mcp_server")
    state = app.state.serving
    via_mcp = json.loads(mcp.tool_get_card(state, "sample", "", False, 20000, cell="checkout_conversion"))
    assert via_mcp["card_id"] == expected["card_id"] and via_mcp["robustness"]["action_threshold"] == 0.6


def test_a_metric_keyed_source_is_served_without_headline_or_image_flag(imp, tmp_path, monkeypatch):               # BUG-004
    from fastapi.testclient import TestClient

    root = _sample_project(imp, tmp_path, monkeypatch)
    expected = _cli_card(imp)
    now = dt.datetime.fromisoformat(SAMPLE_NOW)
    app = imp("mootcourt.service").create_app(root / "models", root / "cards_service", reports_dir=root / "reports", now=lambda: now)
    client = TestClient(app)
    r = client.post("/card", json={"source": "sample", "cell": "checkout_conversion", "impressions": 20000})
    assert r.status_code == 200, r.text
    assert r.json()["card_id"] == expected["card_id"]
    explicit = client.post("/card", json={"source": "sample", "cell": "checkout_conversion", "impressions": 20000, "headline": "",
                                          "image_changed": False})
    assert explicit.status_code == 200 and explicit.json()["card_id"] == expected["card_id"]
    too_long = client.post("/card", json={"source": "sample", "cell": "checkout_conversion", "impressions": 20000, "headline": "x" * 1001})
    assert too_long.status_code == 422                                                         # the length cap stays


def test_the_mcp_get_card_and_list_precedents_tools_accept_a_missing_headline(imp, tmp_path, monkeypatch):          # BUG-004
    import asyncio
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = _sample_project(imp, tmp_path, monkeypatch)
    expected = _cli_card(imp)
    params = StdioServerParameters(command=sys.executable, args=["-m", "mootcourt.mcp_server", "--models-dir", str(root / "models"),
                                                                  "--reports-dir", str(root / "reports"), "--now", SAMPLE_NOW], cwd=str(tmp_path))

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                card = await session.call_tool("get_card", {"source": "sample", "cell": "checkout_conversion", "impressions": 20000})
                prec = await session.call_tool("list_precedents", {"source": "sample", "cell": "checkout_conversion", "k": 3})
                return card, prec

    card, prec = asyncio.run(asyncio.wait_for(go(), timeout=120))
    for res in (card, prec):
        assert not (getattr(res, "isError", None) or getattr(res, "is_error", None)), res
    assert json.loads(card.content[0].text)["card_id"] == expected["card_id"]
    assert len(json.loads(prec.content[0].text)) == 3


# ------------------------------------------------------------ REV-039 (T-044): a card without s_star scores no log score
def test_a_card_without_s_star_gets_null_log_scores_and_stays_out_of_reliability(imp, tmp_path, make_synth, reliability_factory, caplog):
    import logging
    import os
    import stat

    loop = imp("mootcourt.loop")
    dirs, new, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    cards = sorted(p for p in dirs["cards"].glob("*.json"))
    victim = json.loads(cards[0].read_text())
    victim["request"].pop("s_star", None)
    os.chmod(cards[0], stat.S_IRUSR | stat.S_IWUSR)
    cards[0].write_text(json.dumps(victim, sort_keys=True))
    later = new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1)
    with caplog.at_level(logging.WARNING, logger="mootcourt.loop"):
        res = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                                 source="synthetic", now=later)
    assert res.n_outcomes == 6
    out = json.loads((dirs["cards"] / "outcomes" / f"{victim['card_id']}.json").read_text())
    assert out["logscore"] is None and out["p0_logscore"] is None
    assert any("s_star" in r.getMessage() and victim["card_id"] in r.getMessage() for r in caplog.records)
    every = [json.loads(p.read_text()) for p in (dirs["cards"] / "outcomes").glob("*.json")]
    scoreable = [o for o in every if None not in (o["logscore"], o["p0_logscore"], o["brier"], o["p0_brier"])]
    assert victim["card_id"] not in {o["card_id"] for o in scoreable}
    assert len(loop.load_outcomes(dirs["cards"], "synthetic")) == len(scoreable)          # the null-scored outcome is excluded


# ------------------------------------------------------------ REV-025, 029 (T-044): contaminated mark and version-keyed weight on every path
def test_simulators_list_marks_a_contaminated_weight_and_ignores_another_versions_weight(imp, tmp_path):
    from typer.testing import CliRunner

    regm = imp("mootcourt.registry")
    models = tmp_path / "models"
    reg = regm.Registry(models)
    reg.register_model("synthetic", "m1")
    app = imp("mootcourt.cli").app

    def listing():
        res = CliRunner().invoke(app, ["simulators", "list", "--models-dir", str(models), "--config", str(tmp_path / "none.toml")])
        assert res.exit_code == 0, res.output
        return next(line for line in res.output.splitlines() if line.startswith("heuristic"))

    assert "0 (not earned)" in listing()
    reg.set_second_opinion_weight("synthetic", "heuristic", "0-older", 0.3, {})            # earned by another version
    assert "0 (not earned)" in listing() and "synthetic=" not in listing()
    reg.set_second_opinion_weight("synthetic", "heuristic", "1", 0.3, {}, contaminated=False)
    assert "synthetic=0.3" in listing() and "contaminated" not in listing()
    reg.set_second_opinion_weight("synthetic", "heuristic", "1", 0.3, {}, contaminated=True)
    assert "synthetic=0.3" in listing() and "contaminated" in listing()


def test_backtest_second_opinion_uses_only_the_weight_of_the_same_version(imp, make_synth, tmp_path):
    from test_second_opinion_rungs import _cli, _records

    ledger, _ = make_synth(seed=57, n_tests=260, variants_per_test=2)
    root = tmp_path / "root"
    imp("mootcourt.ledger").write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "gates.json").write_text(json.dumps({"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9, "by_target": {
        "0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}))
    assert _cli(imp, ["fit", "--source", "synthetic"], root).exit_code == 0
    assert _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40"], root).exit_code == 0
    records = tmp_path / "oracle.jsonl"
    _records(imp, ledger, records, mode="oracle", provider="oracle")                 # version "1"
    reg = imp("mootcourt.registry").Registry(root / "models")
    reg.set_second_opinion_weight("synthetic", "oracle", "0-older", 0.4, {})
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40", "--second-opinion", str(records)], root)
    assert res.exit_code == 0, res.output
    assert "weight in force 0.0" in res.output
    reg.set_second_opinion_weight("synthetic", "oracle", "1", 0.4, {}, contaminated=True)
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "40", "--second-opinion", str(records)], root)
    assert "weight in force 0.4" in res.output
    doc = json.loads(next((root / "reports" / "second-opinion-oracle").glob("*.json")).read_text())
    assert doc["header"]["second_opinion"]["weight_contaminated"] is True
    md = next((root / "reports" / "second-opinion-oracle").glob("*.md")).read_text()
    assert "contaminated" in md.lower()


# ------------------------------------------------------------ REV-038, 040, 041 (T-044): the download script
def test_download_refuses_an_ambiguous_approved_pattern(tmp_path):
    from test_download import _run, _Stub

    s = _Stub({"jd64p": {"upworthy-exploratory-a.csv": b"a\n", "upworthy-exploratory-b.csv": b"b\n"}, "64jsb": {}})
    try:
        r = _run(tmp_path, s)
    finally:
        s.close()
    assert r.returncode == 4 and "more than one file" in r.stderr and "exploratory-a" in r.stderr
    raw = tmp_path / "data" / "raw"
    assert not raw.exists() or not any(p.is_file() for p in raw.rglob("*"))


def test_verify_only_fails_when_a_requested_source_has_no_recorded_file(tmp_path):
    import subprocess
    import sys

    from test_download import SCRIPT

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "CHECKSUMS.json").write_text("{}")
    r = subprocess.run([sys.executable, str(SCRIPT), "--verify-only", "--data-dir", str(tmp_path / "data")],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2 and "records no file" in r.stderr


def test_download_urls_must_name_an_osf_host_or_the_stub(tmp_path):
    import importlib.util
    import subprocess
    import sys

    from test_download import SCRIPT

    cmd = [sys.executable, str(SCRIPT), "--source", "upworthy", "--base-url", "http://evil.example", "--data-dir", str(tmp_path / "data"),
           "--verify-only"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2                                    # verify-only never opens a URL
    spec = importlib.util.spec_from_file_location("dl", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for url in ("https://evil.example/x", "http://169.254.169.254/latest", "https://osf.io.evil.example/x"):
        try:
            mod._open(url)
        except mod.DownloadError as exc:
            assert exc.code == 4 and "not an OSF host" in str(exc)
        else:
            raise AssertionError(url)


# ------------------------------------------------------------ REV-032, 034, 045, 046 and the other nits (T-044)
def test_the_credential_scrub_covers_dsn_cookie_session_proxy_and_url_logins(imp):
    stdio = imp("mootcourt.simulators.stdio")
    env = {"PATH": "/bin", "HOME": "/h", "LANG": "C", "SENTRY_DSN": "https://k@o.example/1", "AUTH_COOKIE": "c", "SESSION_ID": "s",
           "HTTPS_PROXY": "http://u:p@proxy:3128", "http_proxy": "http://proxy:3128", "DATABASE_URL": "postgres://user:secret@db/x",
           "PLAIN_URL": "https://example.org/x", "SSL_CERT_FILE": "/etc/ssl/cert.pem", "BEARER_TOKEN": "t", "MY_PRIVATE_THING": "x",
           "CLIENT_CERT": "c", "DECLARED_SESSION": "keep"}
    got = stdio.scrub_env(env, declared=["DECLARED_SESSION"])
    assert set(got) == {"PATH", "HOME", "LANG", "PLAIN_URL", "SSL_CERT_FILE", "DECLARED_SESSION"}


def test_a_config_table_cannot_grant_remote_access_on_its_own(imp, tmp_path):
    loader, base = imp("mootcourt.simulators.loader"), imp("mootcourt.simulators")
    table = {"adapter": "http", "url": "http://example.org/simulate", "knowledge_cutoff": "2025-06-01", "allow_remote": True}
    import pytest

    with pytest.raises(base.SimulatorError, match="allow-remote"):
        loader.from_table("far", table)
    assert loader.from_table("far", table, allow_remote=True) is not None


def test_the_configured_gate_power_reaches_every_write_of_the_gates_file(imp, make_synth, tmp_path, monkeypatch):    # REV-045
    from typer.testing import CliRunner

    simulate = imp("mootcourt.simulate")
    seen = []
    real = simulate.write_gates

    def spy(path=None, **kw):
        seen.append(kw.get("target"))
        return real(path, **{**kw, "reps": 30, "B": 30, "with_table": False})

    monkeypatch.setattr(simulate, "write_gates", spy)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mootcourt.toml").write_text('[storage]\ndata_root = "root"\n[gate]\ntarget_power = 0.8\n')
    ledger, _ = make_synth(seed=57, n_tests=200, variants_per_test=2)
    imp("mootcourt.ledger").write_ledger(ledger, tmp_path / "root" / "data" / "ledger" / "ledger.parquet")
    app = imp("mootcourt.cli").app
    assert CliRunner().invoke(app, ["fit", "--source", "synthetic"]).exit_code == 0
    res = CliRunner().invoke(app, ["backtest", "--source", "synthetic", "--bootstrap", "30"])
    assert res.exit_code == 0, res.output
    assert seen == [0.8]
    gates = json.loads((tmp_path / "root" / "reports" / "gates.json").read_text())
    assert gates["decision_target"] == 0.8


def test_trusted_hosts_refuse_a_rebound_host_name(imp, tmp_path, make_synth, reliability_factory):                 # REV-035
    from fastapi.testclient import TestClient

    ledger, _ = make_synth(seed=101, n_tests=200, variants_per_test=2)
    bm, regm = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-111111111111", as_of=dt.datetime(2014, 7, 15, 12, tzinfo=dt.timezone.utc))
    bm.save_bundle(bundle, models)
    regm.Registry(models).register_model("synthetic", bundle.model_id)
    app = imp("mootcourt.service").create_app(models, cards, reports_dir=reports, trusted_hosts=["127.0.0.1", "localhost"])
    assert TestClient(app, base_url="http://127.0.0.1:8000").get("/health").status_code == 200
    assert TestClient(app, base_url="http://localhost:8000").get("/health").status_code == 200
    assert TestClient(app, base_url="http://rebind.example:8000").get("/health").status_code == 400
    open_app = imp("mootcourt.service").create_app(models, cards, reports_dir=reports)
    assert TestClient(open_app, base_url="http://rebind.example").get("/health").status_code == 200       # no list, no check


def test_earning_a_weight_for_a_new_version_keeps_the_old_versions_record(imp, tmp_path):                           # REV-046
    reg = imp("mootcourt.registry").Registry(tmp_path)
    reg.register_model("synthetic", "m1")
    reg.set_second_opinion_weight("synthetic", "agent", "1", 0.3, {"why": "first"})
    reg.set_second_opinion_weight("synthetic", "agent", "2", 0.1, {"why": "second"})
    assert reg.get_second_opinion_weight("synthetic", "agent", "2") == 0.1 and reg.get_second_opinion_weight("synthetic", "agent", "1") == 0.0
    history = reg.second_opinion_history("synthetic")
    assert [(h["provider_id"], h["version"], h["weight"], h["evidence"]) for h in history] == [("agent", "1", 0.3, {"why": "first"})]
    reg.set_second_opinion_weight("synthetic", "agent", "2", 0.2, {"why": "again"})        # the same version again replaces it in place
    assert len(reg.second_opinion_history("synthetic")) == 1


# ------------------------------------------------------------ REV-028 (T-044): reproducible CI and image; the CI job that builds the image
def _ci_text():
    return (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def test_every_action_is_pinned_by_commit_sha_with_a_version_comment():
    import re

    uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)(.*)$", _ci_text(), re.M)
    assert uses
    for ref, rest in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), f"{ref} is not pinned by a full commit SHA"
        assert re.search(r"#\s*v\d+(\.\d+)*", rest), f"{ref} has no version comment"


def test_dependency_installs_in_ci_and_the_image_use_the_lock_file():
    import re

    text = _ci_text()
    syncs = re.findall(r"uv sync[^\n]*", text)
    assert syncs and all("--locked" in s for s in syncs), syncs
    docker = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")
    assert "uv.lock" in docker and re.search(r"uv sync[^\n]*--locked", docker) and "--no-dev" in docker
    assert re.search(r"pip install[^\n]*uv==\d+\.\d+\.\d+", docker), "the uv version in the image is pinned"
    assert (Path(__file__).resolve().parents[1] / ".github" / "dependabot.yml").is_file()
    dep = (Path(__file__).resolve().parents[1] / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    for eco in ("github-actions", "uv", "docker"):          # chunk G (REV-F-017): the uv ecosystem updates uv.lock, which a locked sync needs
        assert f"package-ecosystem: {eco}" in dep or f'package-ecosystem: "{eco}"' in dep, eco


def test_a_ci_job_builds_the_image_and_runs_doctor_inside_it():
    import re

    text = _ci_text()
    assert re.findall(r"^  ([a-z-]+):$", text.split("jobs:", 1)[1], re.M) == ["lint", "test", "writing-rules", "build", "docs", "docker"]
    job = text.split("\n  docker:", 1)[1]
    assert "docker build" in job and "moot doctor" in job and "check_doctor_output.sh" in job    # chunk G, REV-F-003: not the exit code alone
    release = (Path(__file__).resolve().parents[1] / "docs" / "release.md").read_text(encoding="utf-8")
    assert "verified by" in release and "hosted runner" in release


def test_doctor_survives_a_data_root_it_cannot_write(imp, tmp_path, monkeypatch):
    import os
    import stat

    from typer.testing import CliRunner

    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    monkeypatch.chdir(tmp_path)
    os.chmod(root, stat.S_IRUSR | stat.S_IXUSR)
    try:
        if os.access(root, os.W_OK):
            return                                   # running as a user to whom permissions do not apply
        res = CliRunner().invoke(imp("mootcourt.cli").app, ["doctor"])
    finally:
        os.chmod(root, stat.S_IRWXU)
    assert res.exit_code in (1, 2) and "Traceback" not in res.output and "report" in res.output.lower()


# ------------------------------------------------------------ BUG-005 and BUG-007 (T-044 last criterion)
def _run_log(tmp_path, data_log_text):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("run_log", Path(__file__).resolve().parents[1] / "scripts" / "run_log.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "stages.txt").write_text("setup 0 0.5\ndata 0 9.8\npower 0 40.0\n")
    (tmp_path / "data.log").write_text(data_log_text)
    out = tmp_path / "out"
    old = sys.argv
    sys.argv = ["run_log", "--stages", str(tmp_path / "stages.txt"), "--data-log", str(tmp_path / "data.log"), "--out-dir", str(out),
                "--meta", "run=clean copy"]
    try:
        assert mod.main() == 0
    finally:
        sys.argv = old
    return (out / "run-log.md").read_text(), json.loads((out / "run-log.json").read_text())


def test_the_run_log_says_downloaded_only_when_something_was_fetched(tmp_path):
    (tmp_path / "a").mkdir()
    md, doc = _run_log(tmp_path / "a", "")
    assert "verified checksums of existing archives" in md and "downloaded" not in md.replace("nothing was downloaded", "")
    assert doc["data_stage_kind"] == "checksum verification" and doc["meta"]["data"].startswith("verified checksums")
    (tmp_path / "b").mkdir()
    md, doc = _run_log(tmp_path / "b", "ok: 3 downloaded (15470807 bytes), 0 verified, 17.3 s\n")
    assert "downloaded 3 file(s)" in md and doc["data_stage_kind"] == "download"
    (tmp_path / "c").mkdir()
    md, doc = _run_log(tmp_path / "c", "ok: 0 downloaded (0 bytes), 3 verified, 0.1 s\n")
    assert "verified checksums of existing archives" in md and "downloaded 3" not in md


def test_timed_run_never_claims_a_download_on_its_own():
    text = (Path(__file__).resolve().parents[1] / "scripts" / "timed_run.sh").read_text(encoding="utf-8")
    assert "downloaded from OSF" not in text


def test_bad_inputs_end_in_one_line_errors_and_exit_2_not_tracebacks(imp, tmp_path, monkeypatch):                    # BUG-005
    from typer.testing import CliRunner

    _sample_project(imp, tmp_path, monkeypatch)
    app = imp("mootcourt.cli").app
    card = ["card", "--source", "sample", "--cell", "checkout_conversion"]
    cases = [
        ([*card, "--impressions", "0", "--now", SAMPLE_NOW], "impressions"),
        ([*card, "--impressions", "20000", "--now", "notadate"], "--now"),
        ([*card, "--impressions", "20000", "--now", "2020-01-01T00:00:00+00:00"], "fit cutoff"),
        (["join", "--source", "sample", "--new-rows", "/nonexistent.parquet"], "/nonexistent.parquet"),
        (["earn-weight", "--source", "sample", "--second-opinion", "/nonexistent.jsonl"], "/nonexistent.jsonl"),
        ([*card, "--impressions", "20000", "--now", "2025-12-30T00:00:00"], "offset"),
    ]
    for args, needle in cases:
        res = CliRunner().invoke(app, args)
        assert res.exit_code == 2, (args, res.exit_code, res.output)
        assert needle in res.output and "Traceback" not in res.output, (args, res.output)
        assert res.exception is None or isinstance(res.exception, SystemExit), (args, repr(res.exception))
        # a usage error prints its small box; none prints a traceback
        assert len([ln for ln in res.output.strip().splitlines() if ln.strip()]) <= 8, (args, res.output)
    monkeypatch.setenv("MOOTCOURT_DEBUG", "1")                      # a developer can still get the traceback
    res = CliRunner().invoke(app, [*card, "--impressions", "0", "--now", SAMPLE_NOW])
    assert isinstance(res.exception, ValueError)


def test_a_conflicting_join_names_the_conflict_in_one_line(imp, tmp_path, monkeypatch):                              # BUG-005
    import pandas as pd
    from typer.testing import CliRunner

    root = _sample_project(imp, tmp_path, monkeypatch)
    led = imp("mootcourt.ledger").read_ledger(root / "data" / "ledger" / "ledger.parquet")
    changed = led.head(3).assign(y=lambda d: d["y"] + 1.0)
    imp("mootcourt.ledger").write_ledger(pd.concat([changed]), tmp_path / "conflict.parquet")
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["join", "--source", "sample", "--new-rows", str(tmp_path / "conflict.parquet")])
    assert res.exit_code == 2 and "Traceback" not in res.output and "would change" in res.output


def test_data_md_and_readme_state_the_impressions_stand_in_and_what_it_can_leak():                                    # REV-030
    root = Path(__file__).resolve().parents[1]
    for rel in ("DATA.md", "README.md"):
        flat = " ".join((root / rel).read_text(encoding="utf-8").split()).lower()
        assert "stand in" in flat or "stand-in" in flat, rel
        assert "planned exposure" in flat and "+0.099" in flat and "leak" in flat, rel
        assert "planned exposure" in flat and "realized impressions" in flat, rel


# ------------------------------------------------------------ documentation nits (REV-036, 044, 051, 054)
def _page(rel):
    return " ".join((Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8").split())


def test_the_release_docs_say_the_wheel_check_needs_the_package_index():                                               # REV-036
    assert "package index" in _page("docs/release.md") and "package index" in _page("scripts/release_check.py")


def test_the_ratio_helper_is_documented_as_a_library_function_only():                                                   # REV-044
    assert "library helper" in _page("docs/ledger-format.md") and "library helper" in _page("src/mootcourt/importers/exchange.py")


def test_the_method_page_names_no_private_party_even_in_general_terms():                                                # REV-051
    text = _page("docs/method.md").lower()
    assert "built for" not in text
    for line in (Path(__file__).resolve().parents[1] / "docs" / "method.md").read_text(encoding="utf-8").splitlines():
        low = line.lower()
        assert not ("employer" in low and "team" in low and "person" in low), line


def test_the_faq_does_not_repeat_the_boundary_sentence_the_footer_carries():                                            # REV-054
    body = _page("docs/faq.md")
    assert "The live test decides" not in body
