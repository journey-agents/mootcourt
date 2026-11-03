"""Chunk H: fixes for the findings of the chunk G review (REV-G-001 to REV-G-006).

The scanner tests for REV-G-002 are in test_writing_rules.py, next to the scanner they exercise.
"""
from __future__ import annotations

import socket
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------ REV-G-001: the url port and the connection construction
@pytest.mark.parametrize("url", ["http://127.0.0.1:99999/x", "http://127.0.0.1:abc/x", "http://127.0.0.1:-1/x"])
def test_a_url_with_an_invalid_port_is_a_simulator_error(imp, url):                                      # REV-G-001
    from test_simulators import _info

    httpmod, base = imp("mootcourt.simulators.http"), imp("mootcourt.simulators.base")
    with pytest.raises(base.SimulatorError, match="port"):
        httpmod.HttpSimulator(url, _info(imp))


def test_a_connection_construction_error_reaches_the_caller_not_a_too_large_reply(imp, monkeypatch):    # REV-G-001
    from test_simulators import _info, _req

    httpmod = imp("mootcourt.simulators.http")

    def boom(*args, **kwargs):
        raise RuntimeError("construction failed")

    monkeypatch.setattr(httpmod.http.client, "HTTPConnection", boom)
    sim = httpmod.HttpSimulator("http://127.0.0.1:9/x", _info(imp), time_cap_s=2.0)
    with pytest.raises(RuntimeError, match="construction failed"):
        sim.simulate(_req(imp))
    assert sim.last_failure != "invalid", sim.last_note


# ------------------------------------------------------------ REV-G-003: colon lists and env wrappers
def test_the_data_root_refusal_reads_the_first_piece_of_a_colon_list_and_an_env_wrapper(imp, tmp_path, monkeypatch):    # REV-G-003
    from test_simulators import _info

    stdio, base = imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators")
    root = tmp_path / "dataroot"
    root.mkdir()
    (root / "agent.py").write_text("print('null')\n")
    ok = tmp_path / "ok.py"
    ok.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    for command in ([sys.executable, str(ok), f"{root}:/usr/lib"],
                    [sys.executable, str(ok), f"--path={root}:/usr/lib"],
                    ["env", "FOO=1", "sh", "-c", f"python3 {root / 'agent.py'}"],
                    ["env", "-i", "A=b", "bash", "-c", f"python3 {root / 'agent.py'}"],
                    ["env", "-u", "HOME", "sh", "-c", f"python3 {root / 'agent.py'}"],
                    ["/usr/bin/env", "sh", "-c", f"python3 {root / 'agent.py'}"]):
        with pytest.raises(base.SimulatorError, match="data root"):
            stdio.StdioSimulator(command, _info(imp))
    stdio.StdioSimulator(["env", "FOO=1", "sh", "-c", f"python3 {ok}"], _info(imp))
    stdio.StdioSimulator([sys.executable, str(ok), "/usr/lib:/usr/bin"], _info(imp))


# ------------------------------------------------------------ REV-G-004: the TLS handshake and the cap (limit stated, behaviour pinned)
def test_https_handshake_that_drips_is_closed_at_the_cap(imp):                                           # REV-G-004 (pins the stated limit)
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
            conn.recv(65536)                                       # the client hello
            # a TLS record header that promises 4000 bytes, then one byte every 100 ms: every read succeeds, so no read times out
            for ch in b"\x16\x03\x03\x0f\xa0" + b"a" * 4000:
                if stop.is_set():
                    return
                conn.sendall(bytes([ch]))
                time.sleep(0.1)
        except OSError:
            broken.set()                                           # the client closed its end

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    threading.Thread(target=serve, args=(listener,), daemon=True).start()
    try:
        httpmod = imp("mootcourt.simulators.http")
        sim = httpmod.HttpSimulator(f"https://127.0.0.1:{listener.getsockname()[1]}/x", _info(imp), time_cap_s=1.0)
        t0 = time.monotonic()
        assert sim.simulate(_req(imp)) is None and sim.last_failure == "timeout"
        assert time.monotonic() - t0 < 2.0
        assert broken.wait(3.0), "the socket was still open 3 s after the cap, in the middle of the handshake"
    finally:
        stop.set()
        listener.close()
        for c in accepted:
            c.close()
    assert ssl.OPENSSL_VERSION                                       # the stdlib ssl module is what the adapter uses


# ------------------------------------------------------------ REV-G-005: the module docstring
def test_the_http_adapter_docstring_describes_the_http_client_exchange(imp):                            # REV-G-005
    doc = imp("mootcourt.simulators.http").__doc__
    assert "urllib" not in doc and "opener" not in doc, doc
    for needle in ("http.client", "proxy", "redirect", "verif", "megabyte", "wall clock", "handshake", "resolution"):
        assert needle in doc, needle


# ------------------------------------------------------------ REV-G-006: make docker-check leaves nothing behind
def test_docker_check_writes_to_a_temporary_folder_and_mounts_a_temporary_data_root():                  # REV-G-006
    lines = (ROOT / "Makefile").read_text().splitlines()
    start = lines.index("docker-check:")
    recipe = []
    for line in lines[start + 1:]:
        if not line.startswith("\t"):
            break
        recipe.append(line)
    text = "\n".join(recipe)
    assert "mktemp" in text, text
    assert "doctor-output" not in text and "$$work/doctor.txt" in text, "the doctor output belongs in the temporary folder"
    assert "mootcourt-data" not in text and "MOOTCOURT_DATA_ROOT" not in text, "the mount is a temporary folder"
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    assert "mootcourt-data/" in ignored
    r = subprocess.run(["make", "-n", "docker-check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
