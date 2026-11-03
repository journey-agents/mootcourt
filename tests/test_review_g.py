"""Chunk G: fixes for the findings of the chunk F review (REV-F-001 to REV-F-027)."""
from __future__ import annotations

import datetime as dt
import json
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from test_review_f import FIX, NOW_2026, _cli_in, _exch

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------ REV-F-001, REV-F-016: the download script
def test_a_required_file_with_no_match_fails_even_when_the_datasheet_matches(tmp_path):            # REV-F-001
    from test_download import _run, _Stub

    s = _Stub({"jd64p": {"upworthy-exploratory.csv": b"a\n"},
               "64jsb": {"asos_digital_experiments_dataset_v2.parquet": b"x", "datasheet.pdf": b"d", "datasheet-notes.md": b"n"}})
    try:
        r = _run(tmp_path, s, source="asos")
    finally:
        s.close()
    assert r.returncode == 4 and "asos_digital_experiments_dataset.parquet" in r.stderr, r.stderr
    raw = tmp_path / "data" / "raw"
    assert not raw.exists() or not any(p.is_file() for p in raw.rglob("*"))


def _dl_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("dl_g", ROOT / "scripts" / "download_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_plain_http_is_refused_for_the_osf_hosts_and_allowed_for_a_base_url_host():                # REV-F-016
    mod = _dl_module()
    for url in ("http://files.osf.io/x", "http://api.osf.io/v2/", "http://osf.io/x"):
        with pytest.raises(mod.DownloadError, match="https") as exc:
            mod._open(url)
        assert exc.value.code == 4
    mod._extra_hosts.add("127.0.0.1")
    try:
        with pytest.raises(mod.DownloadError) as exc:
            mod._open("http://127.0.0.1:1/x")                      # allowed by scheme: refused by the connection, not by the rule
        assert exc.value.code == 3
    finally:
        mod._extra_hosts.discard("127.0.0.1")


def test_a_base_url_on_plain_http_to_an_osf_host_is_refused(tmp_path):                               # REV-F-016
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "download_data.py"), "--source", "upworthy", "--base-url",
                        "http://api.osf.io", "--data-dir", str(tmp_path / "data")], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 4 and "https" in r.stderr and "Traceback" not in r.stderr, r.stderr


# ------------------------------------------------------------ REV-F-002, 005, 022: exchange file checks
def test_a_parquet_null_in_a_nullable_integer_count_names_row_and_column(imp, tmp_path, monkeypatch):    # REV-F-002
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    df = pd.DataFrame([_exch(variant_id="a"), _exch(variant_id="b"), _exch(variant_id="c")])
    df["n_baseline"] = pd.array([None, 1000, 1000], dtype="Int64")
    df["n_variant"] = pd.array([1000, 1000, None], dtype="Int64")
    p = tmp_path / "nullable.parquet"
    df.to_parquet(p)
    got = {(v.row, v.column): v for v in ex.check_exchange(ex.read_table(p), NOW_2026) if v.severity == "error"}
    assert (1, "n_baseline") in got and "missing" in got[(1, "n_baseline")].message and (3, "n_variant") in got
    res = _cli_in(imp, ["ledger", "check", str(p)], tmp_path, monkeypatch)
    assert res.exit_code == 1 and "n_baseline" in res.output and "Traceback" not in res.output, res.output
    with pytest.raises(ex.ExchangeError):
        ex.to_ledger(ex.read_table(p), "t", now=NOW_2026)


def test_a_count_of_two_to_the_53_plus_one_is_rejected_not_rounded(imp):                             # REV-F-022
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    over = pd.DataFrame([_exch(variant_id="a", n_baseline=str(2 ** 53 + 1)), _exch(variant_id="b", n_baseline=str(2 ** 53)),
                         _exch(variant_id="c", n_baseline="9007199254740993.0"), _exch(variant_id="d", n_variant="9.007199254740993e15")], dtype=str)
    errs = {(v.row, v.column) for v in ex.check_exchange(over, NOW_2026) if v.severity == "error"}
    assert errs == {(1, "n_baseline"), (3, "n_baseline"), (4, "n_variant")}, errs     # 2**53 itself is the largest exact count and stays
    ints = pd.DataFrame([_exch(variant_id="a")])
    ints["n_baseline"] = pd.array([2 ** 53 + 1], dtype="Int64")
    assert {(v.row, v.column) for v in ex.check_exchange(ints, NOW_2026) if v.severity == "error"} == {(1, "n_baseline")}


def test_a_composed_row_key_collision_without_double_colons_names_both_rows(imp):                    # REV-F-005
    import pandas as pd

    ex = imp("mootcourt.importers.exchange")
    pairs = [(dict(variant_id="x:", metric_id="y"), dict(variant_id="x", metric_id=":y")),
             (dict(experiment_id="e:x", variant_id="v"), dict(experiment_id="e", variant_id="x:v"))]
    for first, second in pairs:
        df = pd.DataFrame([_exch(**first), _exch(**second)], dtype=str)
        errs = [v for v in ex.check_exchange(df, NOW_2026) if v.severity == "error"]
        assert len(errs) == 1 and errs[0].row == 2 and "row 1" in errs[0].message, errs
        with pytest.raises(ex.ExchangeError):                       # an error of the check, not a LedgerSchemaError from the conversion
            ex.to_ledger(df, "t", now=NOW_2026)
    ok = pd.DataFrame([_exch(variant_id="x", metric_id="y"), _exch(variant_id="x", metric_id="z")], dtype=str)
    assert not [v for v in ex.check_exchange(ok, NOW_2026) if v.severity == "error"]


# ------------------------------------------------------------ REV-F-006, REV-F-018: units in a ledger file and across vendors
def _unit_ledger(ex, unit: str, exp: str, system: str = "t"):
    import pandas as pd

    return ex.to_ledger(pd.DataFrame([_exch(experiment_id=exp, effect_unit=unit, source_system=system)], dtype=str), "s", now=NOW_2026)


def test_ledger_check_reads_units_from_a_ledger_file(imp, tmp_path):                                  # REV-F-006
    import pandas as pd

    ex, ledger, ingest = imp("mootcourt.importers.exchange"), imp("mootcourt.ledger"), imp("mootcourt.importers.ingest")
    mixed = pd.concat([_unit_ledger(ex, "relative", "e1"), _unit_ledger(ex, "standardized", "e2")], ignore_index=True)
    p = tmp_path / "mixed.parquet"
    ledger.write_ledger(mixed, p)
    got = [v for v in ingest.check_file(p, NOW_2026) if v.severity == "error"]
    assert got and got[0].column == "effect_unit" and got[0].row == 2 and "differs" in got[0].message, got
    bad = _unit_ledger(ex, "relative", "e3")
    bad["features_json"] = bad["features_json"].str.replace('"effect_unit": "relative"', '"effect_unit": "banana"')
    q = tmp_path / "bad.parquet"
    ledger.write_ledger(bad, q)
    assert [v for v in ingest.check_file(q, NOW_2026) if v.column == "effect_unit" and "banana" in v.message]
    fine = pd.concat([_unit_ledger(ex, "relative", "e1"), _unit_ledger(ex, "relative", "e2")], ignore_index=True)
    r = tmp_path / "fine.parquet"
    ledger.write_ledger(fine, r)
    assert not [v for v in ingest.check_file(r, NOW_2026) if v.severity == "error"]


def test_as_exported_does_not_pool_across_vendors(imp, tmp_path):                                     # REV-F-018
    import pandas as pd

    ex, ledger, ingest = imp("mootcourt.importers.exchange"), imp("mootcourt.ledger"), imp("mootcourt.importers.ingest")
    a, b = _unit_ledger(ex, "as_exported", "e1", "optimizely_csv"), _unit_ledger(ex, "as_exported", "e2", "harness_csv")
    assert ex.unit_conflicts(a, b), "two vendors' as_exported rows are not one unit"
    assert not ex.unit_conflicts(a, _unit_ledger(ex, "as_exported", "e2", "optimizely_csv"))
    p = tmp_path / "vendors.parquet"
    ledger.write_ledger(pd.concat([a, b], ignore_index=True), p)
    assert [v for v in ingest.check_file(p, NOW_2026) if v.severity == "error" and v.column == "effect_unit"]
    one_file = pd.DataFrame([_exch(variant_id="a", effect_unit="as_exported", source_system="optimizely_csv"),
                             _exch(variant_id="b", effect_unit="as_exported", source_system="harness_csv")], dtype=str)
    assert [v for v in ex.check_exchange(one_file, NOW_2026) if v.column == "effect_unit" and v.severity == "error"]
    doc = (ROOT / "docs" / "ledger-format.md").read_text(encoding="utf-8")
    assert "as_exported" in doc and "source_system" in doc.split("as_exported", 1)[1][:900]


# ------------------------------------------------------------ REV-F-007: the Jetstream reader names the real cause
def test_jetstream_reports_an_unmatched_statistic_before_the_basis(imp, tmp_path):                    # REV-F-007
    mod = imp("mootcourt.importers")
    kw = dict(experiment_id="n1", started_at="2024-04-01T00:00:00Z", ended_at="2024-04-30T00:00:00Z", n_baseline=10, n_variant=10)
    with pytest.raises(mod.MappingError) as exc:
        mod.read_format("jetstream", FIX / "jetstream.csv", statistic="median", **kw)
    assert "statistic 'median'" in str(exc.value) and "analysis_basis" not in str(exc.value)
    with pytest.raises(mod.MappingError) as exc:
        mod.read_format("jetstream", FIX / "jetstream.csv", comparison="ratio", **kw)
    assert "comparison 'ratio'" in str(exc.value) and "analysis_basis" not in str(exc.value)
    with pytest.raises(mod.MappingError, match="analysis_basis"):
        mod.read_format("jetstream", FIX / "jetstream.csv", analysis_basis="nonsense", **kw)


# ------------------------------------------------------------ REV-F-004: the simulator cache
def test_a_cache_entry_must_state_declined_as_a_bool_and_match_its_result(imp, tmp_path):             # REV-F-004
    from test_simulators import _req

    cache = imp("mootcourt.simulators.cache").SimulationCache(tmp_path / "cache")
    h = _req(imp).request_hash()
    good = {"p_win_ai": 0.3}
    for rec in ({"request_hash": h, "declined": False, "result": None},          # an answer without a result
                {"request_hash": h, "result": good},                              # no declined key
                {"request_hash": h, "result": None},
                {"request_hash": h, "declined": "no", "result": good},            # not a bool
                {"request_hash": h, "declined": 0, "result": good},
                {"request_hash": h, "declined": True, "result": good},            # a decline that carries a result
                {"request_hash": h, "declined": None, "result": None}):
        cache.put("agent", "1", h, rec)
        assert cache.get("agent", "1", h) is None, rec
    cache.put("agent", "1", h, {"request_hash": h, "declined": False, "result": good})
    assert cache.get("agent", "1", h) is not None
    cache.put("agent", "1", h, {"request_hash": h, "declined": True, "result": None})
    assert cache.get("agent", "1", h) is not None


# ------------------------------------------------------------ REV-F-008, REV-F-009, REV-F-020, REV-F-021
def test_http_closes_the_connection_when_the_server_drips_the_header(imp):                             # REV-F-008
    from test_simulators import _info, _req

    stop, broken, accepted = threading.Event(), threading.Event(), []

    def serve(listener):
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            accepted.append(conn)
            threading.Thread(target=drip, args=(conn,), daemon=True).start()

    def drip(conn):
        try:
            conn.recv(65536)
            for ch in b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nX-Slow: " + b"a" * 400:
                if stop.is_set():
                    return
                conn.sendall(bytes([ch]))
                time.sleep(0.1)
        except OSError:
            broken.set()                                    # the client closed its end

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    threading.Thread(target=serve, args=(listener,), daemon=True).start()
    try:
        httpmod = imp("mootcourt.simulators.http")
        sim = httpmod.HttpSimulator(f"http://127.0.0.1:{listener.getsockname()[1]}/x", _info(imp), time_cap_s=1.0)
        t0 = time.monotonic()
        assert sim.simulate(_req(imp)) is None and sim.last_failure == "timeout"
        assert time.monotonic() - t0 < 2.0
        assert broken.wait(3.0), "the connection was still open 3 s after the cap"
    finally:
        stop.set()
        listener.close()
        for c in accepted:
            c.close()


def test_the_data_root_refusal_reads_attached_module_names_and_shell_strings(imp, tmp_path, monkeypatch):    # REV-F-009
    from test_simulators import _info

    stdio, base = imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators")
    root = tmp_path / "dataroot"
    (root / "lib").mkdir(parents=True)
    (root / "lib" / "evilmod.py").write_text("print('null')\n")
    (root / "agent.py").write_text("print('null')\n")
    ok = tmp_path / "ok.py"
    ok.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    monkeypatch.syspath_prepend(str(root / "lib"))
    for command in ([sys.executable, "-mevilmod"],
                    ["sh", "-c", f"python3 {root / 'agent.py'}"],
                    ["bash", "-c", f"cd /tmp && python3 '{root / 'agent.py'}' --x"],
                    ["zsh", "-c", "python3 -mevilmod"],
                    [sys.executable, str(ok), f"--search-path=/usr/lib:{root}"]):
        with pytest.raises(base.SimulatorError, match="data root"):
            stdio.StdioSimulator(command, _info(imp))
    stdio.StdioSimulator([sys.executable, str(ok)], _info(imp))
    stdio.StdioSimulator(["sh", "-c", f"python3 {ok}"], _info(imp))
    stdio.StdioSimulator(["sh", "-c", "unbalanced 'quote"], _info(imp))             # a string shlex cannot read is not an error here


def test_finite_rejects_huge_integers_and_non_numbers(imp):                                           # REV-F-020
    base = imp("mootcourt.simulators.base")
    for bad in (10 ** 400, "5", True, None, [1], float("nan")):
        with pytest.raises(base.SimulatorError):
            base._finite(bad, "x")
    assert base._finite(5, "x") == 5.0 and base._finite(0.5, "x") == 0.5
    with pytest.raises(base.SimulatorError):
        base.Budget(max_respondents="5")


def test_the_scrub_keeps_a_certificate_bundle_path_and_the_no_proxy_list(imp):                         # REV-F-021
    stdio = imp("mootcourt.simulators.stdio")
    env = {"PATH": "/bin", "PIP_CERT": "/etc/ssl/corp.pem", "NO_PROXY": "localhost,127.0.0.1", "no_proxy": "localhost", "HTTPS_PROXY": "http://p:1",
           "CLIENT_CERT": "c", "SSL_CERT_FILE": "/etc/ssl/cert.pem"}
    assert set(stdio.scrub_env(env)) == {"PATH", "PIP_CERT", "NO_PROXY", "no_proxy", "SSL_CERT_FILE"}
    assert "HTTPS_PROXY" in stdio.scrub_env(env, declared=["HTTPS_PROXY"])
    doc = (ROOT / "docs" / "simulators.md").read_text(encoding="utf-8")
    assert "NO_PROXY" in doc and "declare" in doc.lower()


def test_second_opinion_history_is_listed_by_the_simulators_command(imp, tmp_path, monkeypatch):      # REV-F-023
    from typer.testing import CliRunner

    reg = imp("mootcourt.registry").Registry(tmp_path / "models")
    reg.register_model("synthetic", "m1")
    reg.set_second_opinion_weight("synthetic", "agent", "1", 0.3, {"why": "first"})
    reg.set_second_opinion_weight("synthetic", "agent", "2", 0.1, {"why": "second"})
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["simulators", "list", "--models-dir", str(tmp_path / "models")])
    assert res.exit_code == 0, res.output
    assert "displaced" in res.output and "synthetic" in res.output and "agent" in res.output and "0.3" in res.output, res.output
    assert "audit record" in (ROOT / "docs" / "simulators.md").read_text(encoding="utf-8")


# ------------------------------------------------------------ REV-F-010: moot serve on another loopback address
def test_serve_trusts_its_own_bind_host(imp, tmp_path, monkeypatch):                                    # REV-F-010
    from fastapi.testclient import TestClient
    from typer.testing import CliRunner

    captured = {}
    uvicorn = pytest.importorskip("uvicorn")
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: captured.update(app=app, **kw))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    for d in ("m", "c", "r"):
        (tmp_path / d).mkdir()
    base = ["serve", "--models-dir", "m", "--cards-dir", "c", "--reports-dir", "r"]
    for host, header in (("127.0.0.2", "127.0.0.2:8000"), ("::1", "[::1]:8000"), ("127.0.0.1", "127.0.0.1:8000"), ("localhost", "localhost:8000")):
        res = CliRunner().invoke(imp("mootcourt.cli").app, [*base, "--host", host, "--port", "8000"])
        assert res.exit_code == 0, res.output
        client = TestClient(captured["app"], base_url=f"http://{header}")
        assert client.get("/health").status_code == 200, host
        assert TestClient(captured["app"], base_url="http://rebind.example:8000").get("/health").status_code == 400, host
    res = CliRunner().invoke(imp("mootcourt.cli").app, [*base, "--host", "0.0.0.0"])           # a wide bind keeps its documented behaviour
    assert res.exit_code == 0 and TestClient(captured["app"], base_url="http://rebind.example").get("/health").status_code == 200


# ------------------------------------------------------------ REV-F-003: the docker CI job and the doctor output check
CHECK_SCRIPT = ROOT / "scripts" / "check_doctor_output.sh"


def _check_doctor(tmp_path, code: int, text: str):
    out = tmp_path / "doctor.txt"
    out.write_text(text, encoding="utf-8")
    return subprocess.run(["bash", str(CHECK_SCRIPT), str(code), str(out)], capture_output=True, text=True)


def test_the_doctor_output_check_fails_on_a_crash_and_passes_a_warning(tmp_path):                      # REV-F-003
    healthy = "OK    python: 3.12\nstatus: ok\n"
    warned = "WARN  ledger: no ledger\nstatus: warn\n"
    assert _check_doctor(tmp_path, 0, healthy).returncode == 0
    assert _check_doctor(tmp_path, 1, warned).returncode == 0                 # an empty data root warns
    assert _check_doctor(tmp_path, 2, "FAIL python: 3.9\nstatus: fail\n").returncode != 0
    crash = "Traceback (most recent call last):\n  File \"x\", line 1\nImportError: no module named pandas\n"
    r = _check_doctor(tmp_path, 1, crash)                                       # Python exits 1 on an uncaught exception
    assert r.returncode != 0 and "Traceback" in (r.stdout + r.stderr)
    assert _check_doctor(tmp_path, 1, warned + crash).returncode != 0          # a traceback after good lines is still a crash
    assert _check_doctor(tmp_path, 1, "something else entirely\n").returncode != 0        # no parseable status line
    assert _check_doctor(tmp_path, 0, "").returncode != 0


def test_the_docker_job_runs_version_then_doctor_and_checks_the_output():                              # REV-F-003
    job = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").split("\n  docker:", 1)[1]
    steps = re.split(r"\n      - ", job)
    version = [s for s in steps if "moot --version" in s]
    doctor = [s for s in steps if "moot doctor" in s]
    assert len(version) == 1 and len(doctor) == 1 and version[0] is not doctor[0], "moot --version is its own step"
    assert steps.index(version[0]) < steps.index(doctor[0])
    assert "check_doctor_output.sh" in doctor[0] and "-le 1" not in doctor[0]
    assert "check_doctor_output.sh" in (ROOT / "Makefile").read_text(encoding="utf-8")


# ------------------------------------------------------------ REV-F-017: dependabot updates uv.lock
def test_dependabot_uses_the_uv_ecosystem_so_its_pull_requests_pass_a_locked_sync():                      # REV-F-017
    dep = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    ecosystems = re.findall(r"package-ecosystem:\s*\"?([\w-]+)", dep)
    assert "uv" in ecosystems and "pip" not in ecosystems and {"github-actions", "docker"} <= set(ecosystems), ecosystems
    assert (ROOT / "uv.lock").is_file() and not (ROOT / "requirements.txt").exists()


# ------------------------------------------------------------ REV-F-019: the FAQ and the footer
def test_the_faq_does_not_repeat_the_opening_clause_of_the_footer():                                      # REV-F-019
    footer = re.search(r"^copyright:\s*(.+)$", (ROOT / "mkdocs.yml").read_text(encoding="utf-8"), re.M).group(1)
    clause = " ".join(footer.split(",")[0].split())
    faq = " ".join((ROOT / "docs" / "faq.md").read_text(encoding="utf-8").split())
    assert len(clause) > 30 and clause.lower() not in faq.lower(), clause
    assert "Does it replace running the experiment?" in faq


# ------------------------------------------------------------ REV-F-024, REV-F-025: init and doctor
def test_init_refuses_a_data_root_with_a_control_character_before_creating_anything(imp, tmp_path):        # REV-F-024
    ob = imp("mootcourt.onboarding")
    proj = tmp_path / "proj"
    proj.mkdir()
    with pytest.raises(ValueError, match="control character"):
        ob.init_project(proj, data_root=proj / ("a" + chr(127) + "b"))
    assert list(proj.iterdir()) == [], "no folder or file is created for an invalid configuration"
    with pytest.raises(ValueError, match="control character"):
        ob.init_project(proj, name="bad" + chr(127))
    assert list(proj.iterdir()) == []
    ob.init_project(proj, data_root=proj / "ok")
    assert (proj / "mootcourt.toml").is_file()


def test_doctor_reports_a_malformed_reliability_file_instead_of_aborting(imp, tmp_path, monkeypatch):    # REV-F-025
    ob, storage = imp("mootcourt.onboarding"), imp("mootcourt.storage")
    now = dt.datetime(2026, 1, 20, tzinfo=dt.timezone.utc)
    paths = storage.storage_paths(root=tmp_path)
    _good = {"source": "good", "as_of": (now - dt.timedelta(days=1)).isoformat(), "cells": {"c": {"as_of": (now - dt.timedelta(days=1)).isoformat()}}}
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / "reliability-good.json").write_text(json.dumps(_good))
    (paths.reports / "reliability-naive.json").write_text(json.dumps({"source": "naive", "as_of": "2026-01-19T00:00:00", "cells": {}}))
    (paths.reports / "reliability-noasof.json").write_text(json.dumps({"source": "noasof", "cells": {}}))
    (paths.reports / "reliability-garbage.json").write_text("{not json")
    (paths.reports / "reliability-list.json").write_text("[1, 2]")
    out = ob.check_reliability(paths, now)
    by_name = {c["name"]: c for c in out}
    assert by_name["reliability good"]["status"] == "ok"
    failed = [c for c in out if c["status"] == "fail"]
    assert len(failed) == 4, out
    text = " ".join(c["name"] + c["detail"] for c in failed)
    for stem in ("naive", "noasof", "garbage", "list"):
        assert f"reliability-{stem}.json" in text, stem
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    report = ob.run_doctor(now=now)
    assert report["status"] == "fail" and ob.exit_code(report) == 2 and (paths.reports / "doctor.json").is_file()


# ------------------------------------------------------------ the writing-rules scanner (REV-F-011 to 015, 026, 027)
import test_writing_rules as wr  # noqa: E402

_T = {wr._digest("zebrafoo"), wr._digest("zebra foo"), wr._digest("capex"), wr._digest("pixie")}
_ROLE_WORD, _ROLE_PLURAL = sorted(wr.ROLE_WORDS, key=len)


def _kinds(text, rules=("dash", "role", "tokens"), digests=_T, restricted=None):
    return {w for _n, w in wr.scan_text(text, set(rules), digests, restricted)}


@pytest.mark.parametrize("url", ["https://example.org/search?q=zebra%20foo", "https://example.org/people/Zebra%20Foo/", "https://example.org/a/zebra%2Dfoo",
                                 "https://example.org/a/zebra%2520foo", "https://example.org/a/zebra%252Dfoo", "https://example.org/a?q=zebra%2bfoo",
                                 "https://example.org/a?q=zebra+foo", "https://example.org/a/ZEBRA%5FFOO"])
def test_a_percent_encoded_separator_does_not_hide_a_name_in_a_url(url):                             # REV-F-011
    assert wr.url_hits(f"see {url} now\n", _T) == [1], url
    assert "forbidden term in a URL" in _kinds(f"see {url} now")


def test_a_percent_encoded_url_without_a_term_still_passes():                                        # REV-F-011
    assert wr.url_hits("see https://example.org/a%20b/c%2Dd?q=x+y now\n", _T) == []


@pytest.mark.parametrize("text,what", [("the two ZEBRAFOOs met", "forbidden term"), ("many ZEBRA_FOOs", "forbidden term"),
                                       (f"the two {_ROLE_WORD.upper()}s met", "role noun"), (f"all {_ROLE_WORD.upper()}s agree", "role noun"),
                                       ("two CAPEXs", "forbidden term")])
def test_an_all_caps_run_with_a_lower_case_plural_s_is_found(text, what):                          # REV-F-012
    assert what in _kinds(text), text


def test_all_caps_acronyms_with_a_plural_s_do_not_trip_the_scan():                                    # REV-F-012
    assert _kinds("the URLs and IDs and CPUs of the APIs") == set()


@pytest.mark.parametrize("code", [0xFE58, 0xFE31, 0xFE32, 0x2015, 0x2E3A, 0x2E3B, 0x2010, 0x2011, 0x2012, 0xFF0D, 0xFE63, 0x058A])
def test_every_dash_look_alike_is_a_dash_hit(code):                                                   # REV-F-013
    assert "dash character" in _kinds(f"a {chr(code)} b"), hex(code)


def test_ordinary_hyphens_and_minus_signs_are_not_dashes():                                           # REV-F-013
    assert "dash character" not in _kinds("a - b, a-b, 3 " + chr(0x2212) + " 1, x_y")
    assert "dash character" in _kinds(f"a {chr(0x2014)} b") and "dash character" in _kinds(f"a {chr(0x2013)} b")


def _lookalike(word: str, table: dict[str, int]) -> str:
    return "".join(chr(table[c]) if c in table else c for c in word)


CYR = {"c": 0x0441, "a": 0x0430, "p": 0x0440, "e": 0x0435, "x": 0x0445, "i": 0x0456}


@pytest.mark.parametrize("injected,what", [
    (f"then zebraf{chr(0x0585)}o appears", "mixed-script word"),                    # an Armenian letter inside a Latin word
    (f"then zebraf{chr(0x03BF)}{chr(0x043E)} appears", "mixed-script word"),         # Greek and Cyrillic o in one word
    (f"then {_lookalike('capex', CYR)} appears", "forbidden term"),                  # a word wholly in Cyrillic look-alikes
    (f"then p{chr(0x0131)}x{chr(0x0131)}e appears", "forbidden term"),               # Latin dotless i
    (f"then {_lookalike('pixie', CYR)} appears", "forbidden term"),
    (f"then zebrafo{chr(0x0585)} appears", "mixed-script word"),
])
def test_look_alike_letters_outside_latin_greek_and_cyrillic_pairs_are_found(injected, what):    # REV-F-015
    assert what in _kinds(injected), injected


@pytest.mark.parametrize("text", [
    "a latency of 5 " + chr(0xB5) + "s per call", "a 3 " + chr(0x3BC) + "m film", "10 " + chr(0xB5) + "mol and 2 " + chr(0xB5) + "A",
    "Greek alpha and the Latin beta are separate words", "pi, " + chr(0x3C0) + ", and sigma " + chr(0x3C3) + " alone are fine",
    "caf" + chr(0xE9) + " and na" + chr(0xEF) + "ve and Z" + chr(0xFC) + "rich"])
def test_the_micro_sign_before_an_si_unit_and_single_script_words_pass(text):                         # REV-F-026
    assert _kinds(text) == set(), text


def test_a_greek_mu_before_a_non_unit_is_still_mixed_script():                                        # REV-F-026
    assert "mixed-script word" in _kinds("the " + chr(0x3BC) + "zebra word")


def test_the_tier_two_exemption_covers_the_importer_commands_and_not_a_look_alike_path():             # REV-F-027
    for path in (("moot", "ingest"), ("moot", "ledger"), ("moot", "ledger", "check"), ("moot", "ledger", "formats")):
        assert wr.importer_command(path), path
    for path in (("moot",), ("moot", "simulate", "ledger"), ("moot", "simulate"), ("moot", "card"), ("moot", "simulators", "list"),
                 ("moot", "benchmark")):
        assert not wr.importer_command(path), path
    restricted = {wr._digest("yakcorp")}
    assert wr.tier2_set_for_help(("moot", "ingest"), restricted) is None
    assert wr.tier2_set_for_help(("moot", "simulate", "ledger"), restricted) == restricted


# ------------------------------------------------------------ binary files (REV-F-014)
def _png(*chunks: tuple[bytes, bytes]) -> bytes:
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + b"".join(chunk(k, d) for k, d in chunks) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _scan_bytes(tmp_path, name: str, data: bytes, restricted=None):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return wr.scan_file(p, _T, root=tmp_path, restricted=restricted)


def test_a_clean_picture_passes_and_a_text_chunk_with_a_blocked_term_fails(tmp_path):                   # REV-F-014
    import zlib

    assert _scan_bytes(tmp_path, "docs/ok.png", _png()) == []
    assert _scan_bytes(tmp_path, "docs/ok2.png", _png((b"tEXt", b"Title\x00a plain caption"))) == []
    hits = _scan_bytes(tmp_path, "docs/a.png", _png((b"tEXt", b"Author\x00Zebra Foo")))
    assert any(w == "forbidden term" for _f, _n, w in hits), hits
    z = _png((b"zTXt", b"Author\x00\x00" + zlib.compress(b"by zebra foo")))                               # compressed text chunk
    assert any(w == "forbidden term" for _f, _n, w in _scan_bytes(tmp_path, "docs/b.png", z))
    i = _png((b"iTXt", b"Author\x00\x01\x00\x00\x00" + zlib.compress("zebrafoo".encode())))
    assert any(w == "forbidden term" for _f, _n, w in _scan_bytes(tmp_path, "docs/c.png", i))


def test_a_binary_suffix_needs_the_matching_magic_bytes(tmp_path):                                      # REV-F-014
    blob = b"\xff\xfe\x00\x01\x80binary"
    for name in ("a.png", "a.jpg", "a.jpeg", "a.gif", "a.ico", "a.parquet"):
        hits = _scan_bytes(tmp_path, f"docs/{name}", blob)
        assert hits and "does not match" in hits[0][2], (name, hits)
    assert _scan_bytes(tmp_path, "docs/text.png", b"just text renamed to a picture\n")                 # a text file named as a picture
    assert _scan_bytes(tmp_path, "docs/ok.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20) == []
    assert _scan_bytes(tmp_path, "docs/ok.gif", b"GIF89a" + b"\x00" * 20) == []
    assert _scan_bytes(tmp_path, "docs/ok.ico", b"\x00\x00\x01\x00" + b"\xff" * 20) == []


def test_parquet_metadata_columns_and_strings_are_scanned(tmp_path):                                    # REV-F-014
    import io

    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    def blob(table):
        buf = io.BytesIO()
        pq.write_table(table, buf)
        return buf.getvalue()

    clean = pa.table({"a": [1, 2], "b": ["x", "y"]})
    assert _scan_bytes(tmp_path, "data/clean.parquet", blob(clean)) == []
    meta = clean.replace_schema_metadata({"note": "made by Zebra Foo"})
    assert any(w == "forbidden term" for _f, _n, w in _scan_bytes(tmp_path, "data/meta.parquet", blob(meta)))
    col = pa.table({"zebra_foo": [1, 2]})
    assert any(w == "forbidden term" for _f, _n, w in _scan_bytes(tmp_path, "data/col.parquet", blob(col)))
    cells = pa.table({"b": ["fine", "met Zebra Foo today"]})                                              # a string value, compressed by the writer
    sink = io.BytesIO()
    pq.write_table(cells, sink, compression="gzip")
    assert any(w == "forbidden term" for _f, _n, w in _scan_bytes(tmp_path, "data/cells.parquet", sink.getvalue()))
    assert isinstance(pd.__version__, str)


def test_a_restricted_term_in_a_picture_is_allowed_only_where_tier_two_is_allowed(tmp_path):            # REV-F-014
    data = _png((b"tEXt", b"Title\x00YakCorp"))
    r = {wr._digest("yakcorp")}
    assert any(w == "restricted term" for _f, _n, w in _scan_bytes(tmp_path, "docs/x.png", data, restricted=r))
    assert _scan_bytes(tmp_path, "docs/landscape-fig.png", data, restricted=r)         # not a listed file
    assert _scan_bytes(tmp_path, "tests/fixtures/importers/x.png", data, restricted=r) == []
