"""T-019 contracts: download script, stdlib only, tested against a loopback OSF stub."""
import hashlib
import http.server
import io
import json
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "download_data.py"
NODES = {"upworthy": "jd64p", "asos": "64jsb"}


def _zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


class _Stub:
    """Minimal OSF API v2 stand-in: /v2/nodes/<id>/files/osfstorage/ and /download/<name>."""

    def __init__(self, files_by_node, status=200, truncate=None):
        self.files_by_node, self.status, self.truncate = files_by_node, status, truncate
        stub = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if stub.status != 200:
                    self.send_response(stub.status)
                    self.end_headers()
                    return
                for node, files in stub.files_by_node.items():
                    if self.path.rstrip("/") == f"/v2/nodes/{node}/files/osfstorage":
                        data = [{"id": n, "type": "files", "attributes": {"kind": "file", "name": n, "size": len(b)},
                                 "links": {"download": f"{stub.base}/download/{node}/{n}"}} for n, b in files.items()]
                        body = json.dumps({"data": data, "links": {"next": None}}).encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    prefix = f"/download/{node}/"
                    if self.path.startswith(prefix):
                        blob = files[self.path[len(prefix):]]
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(blob)))
                        self.end_headers()
                        self.wfile.write(blob[: stub.truncate] if stub.truncate else blob)
                        return
                self.send_response(404)
                self.end_headers()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def stub():
    made = []

    def make(**kw):
        files = kw.pop("files", {"jd64p": {"upworthy-exploratory.csv": b"a,b\n1,2\n"},
                                 "64jsb": {"asos_digital_experiments_dataset.parquet": b"x\n9\n"}})
        s = _Stub(files, **kw)
        made.append(s)
        return s

    yield make
    for s in made:
        s.close()


def _run(tmp_path, stub_obj, *extra, source="upworthy"):
    assert SCRIPT.exists(), "scripts/download_data.py must exist"
    return subprocess.run([sys.executable, str(SCRIPT), "--source", source, "--base-url", stub_obj.base,
                           "--data-dir", str(tmp_path / "data"), *extra], capture_output=True, text=True, cwd=tmp_path)


def test_script_exists_and_is_stdlib_only():
    assert SCRIPT.exists()
    text = SCRIPT.read_text(encoding="utf-8")
    for banned in ("import requests", "import numpy", "import pandas", "import httpx", "from mootcourt"):
        assert banned not in text


def test_download_records_checksums_and_size(stub, tmp_path):
    s = stub()
    r = _run(tmp_path, s)
    assert r.returncode == 0, r.stderr
    raw = tmp_path / "data" / "raw" / "upworthy" / "upworthy-exploratory.csv"
    assert raw.read_bytes() == b"a,b\n1,2\n"
    rec = json.loads((tmp_path / "data" / "CHECKSUMS.json").read_text())
    entry = next(v for k, v in rec.items() if k.endswith("upworthy-exploratory.csv"))
    assert entry["sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest() and entry["size"] == 8


def test_listing_is_done_at_run_time_not_hardcoded(stub, tmp_path):
    s = stub(files={"jd64p": {"exploratory_brand_new_name.csv": b"z\n"}, "64jsb": {}})
    assert _run(tmp_path, s).returncode == 0
    assert (tmp_path / "data" / "raw" / "upworthy" / "exploratory_brand_new_name.csv").exists()


def test_second_run_verifies_and_one_changed_byte_fails_with_file_name(stub, tmp_path):
    s = stub()
    assert _run(tmp_path, s).returncode == 0
    assert _run(tmp_path, s).returncode == 0
    raw = tmp_path / "data" / "raw" / "upworthy" / "upworthy-exploratory.csv"
    raw.write_bytes(b"a,b\n1,3\n")
    r = _run(tmp_path, s)
    assert r.returncode != 0 and "upworthy-exploratory.csv" in (r.stderr + r.stdout)


def test_refresh_is_the_only_way_to_rerecord(stub, tmp_path):
    s = stub()
    _run(tmp_path, s)
    raw = tmp_path / "data" / "raw" / "upworthy" / "upworthy-exploratory.csv"
    raw.write_bytes(b"changed\n")
    assert _run(tmp_path, s).returncode != 0
    assert _run(tmp_path, s, "--refresh").returncode == 0


def test_zip_slip_member_is_rejected_and_nothing_escapes(stub, tmp_path):
    bad = _zip({"../evil.txt": b"pwn", "ok.txt": b"fine"})
    s = stub(files={"jd64p": {"exploratory-bundle.zip": bad}, "64jsb": {}})
    r = _run(tmp_path, s)
    assert r.returncode != 0
    assert not (tmp_path / "data" / "raw" / "evil.txt").exists() and not (tmp_path / "data" / "evil.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_absolute_member_names_are_rejected(stub, tmp_path):
    victim = tmp_path / "abs_target.txt"
    bad = _zip({str(victim): b"pwn"})
    s = stub(files={"jd64p": {"exploratory-bundle.zip": bad}, "64jsb": {}})
    assert _run(tmp_path, s).returncode != 0
    assert not victim.exists()


def test_extraction_size_limit(stub, tmp_path):
    big = _zip({"big.txt": b"0" * 1_000_000})
    s = stub(files={"jd64p": {"exploratory-bundle.zip": big}, "64jsb": {}})
    r = _run(tmp_path, s, "--max-extract-bytes", "1000")
    assert r.returncode != 0
    assert not list((tmp_path / "data" / "raw").rglob("big.txt"))


def test_good_zip_is_extracted_inside_raw_dir(stub, tmp_path):
    s = stub(files={"jd64p": {"exploratory-bundle.zip": _zip({"inner/data.csv": b"1,2\n"})}, "64jsb": {}})
    assert _run(tmp_path, s).returncode == 0
    assert (tmp_path / "data" / "raw" / "upworthy").rglob("data.csv")
    assert list((tmp_path / "data" / "raw" / "upworthy").rglob("data.csv"))


def test_interrupted_download_leaves_no_verifying_file(stub, tmp_path):
    s = stub(truncate=3)
    r = _run(tmp_path, s)
    assert r.returncode != 0
    raw = tmp_path / "data" / "raw" / "upworthy" / "upworthy-exploratory.csv"
    assert not raw.exists(), "a partial download must only ever exist under a .part name"
    checks = tmp_path / "data" / "CHECKSUMS.json"
    assert not checks.exists() or "upworthy-exploratory.csv" not in checks.read_text()


def test_maintenance_503_is_a_clear_nonzero_exit_without_partial_checksums(stub, tmp_path):
    s = stub(status=503)
    r = _run(tmp_path, s)
    assert r.returncode != 0
    assert "503" in (r.stderr + r.stdout) or "maintenance" in (r.stderr + r.stdout).lower()
    checks = tmp_path / "data" / "CHECKSUMS.json"
    assert not checks.exists() or json.loads(checks.read_text()) == {}


def test_downloaded_content_is_never_executed(stub, tmp_path):
    marker = tmp_path / "executed.txt"
    payload = f"open({str(marker)!r}, 'w').write('x')\n".encode()
    s = stub(files={"jd64p": {"exploratory-evil.py": payload}, "64jsb": {}})
    assert _run(tmp_path, s).returncode == 0
    assert not marker.exists()


def test_makefile_data_target_calls_the_script():
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "scripts/download_data.py" in make
