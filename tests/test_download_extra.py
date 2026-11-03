"""Extra checks for the download script (builder additions): deny list, preferred files, offline verify, ignore rules."""
import json
import subprocess
import sys
from pathlib import Path

from test_download import SCRIPT, _run, _Stub  # noqa: F401  (pytest puts tests/ on sys.path, so bare pytest collects this file)

ROOT = Path(__file__).resolve().parents[1]


def _stub(files):
    return _Stub(files)


def test_denied_files_are_never_fetched_and_preferred_files_win(tmp_path):
    files = {"jd64p": {"upworthy-archive-exploratory-packages.csv": b"e\n", "upworthy-archive-holdout-packages.csv": b"h\n",
                       "upworthy-archive-confirmatory-packages.csv": b"c\n", "upworthy-archive-undeployed-packages.csv": b"u\n",
                       "notes.txt": b"n\n"}, "64jsb": {}}
    s = _stub(files)
    try:
        r = _run(tmp_path, s)
    finally:
        s.close()
    assert r.returncode == 0, r.stderr
    got = sorted(p.name for p in (tmp_path / "data" / "raw" / "upworthy").iterdir())
    assert got == ["upworthy-archive-exploratory-packages.csv"]
    assert "deliberately not used" in r.stdout
    rec = json.loads((tmp_path / "data" / "CHECKSUMS.json").read_text())
    assert list(rec) == ["raw/upworthy/upworthy-archive-exploratory-packages.csv"]


def test_asos_fetches_only_the_parquet_and_the_datasheet(tmp_path):
    files = {"jd64p": {}, "64jsb": {"asos_digital_experiments_dataset.csv": b"c\n", "asos_digital_experiments_dataset.parquet": b"p\n",
                                    "Datasheet_ASOS.pdf": b"d\n", "metadata.html": b"m\n"}}
    s = _stub(files)
    try:
        r = _run(tmp_path, s, source="asos")
    finally:
        s.close()
    assert r.returncode == 0, r.stderr
    got = sorted(p.name for p in (tmp_path / "data" / "raw" / "asos").iterdir())
    assert got == ["Datasheet_ASOS.pdf", "asos_digital_experiments_dataset.parquet"]


def test_verify_only_needs_no_network_and_names_a_changed_file(tmp_path):
    s = _stub({"jd64p": {"exploratory-u.csv": b"a\n"}, "64jsb": {}})
    try:
        assert _run(tmp_path, s).returncode == 0
    finally:
        s.close()
    cmd = [sys.executable, str(SCRIPT), "--source", "upworthy", "--verify-only", "--base-url", "http://127.0.0.1:9",
           "--data-dir", str(tmp_path / "data")]
    assert subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path).returncode == 0
    (tmp_path / "data" / "raw" / "upworthy" / "exploratory-u.csv").write_bytes(b"b\n")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2 and "exploratory-u.csv" in r.stderr


def test_oversized_file_is_refused(tmp_path):
    s = _stub({"jd64p": {"exploratory-big.csv": b"0" * 5000}, "64jsb": {}})
    try:
        r = _run(tmp_path, s, "--max-file-bytes", "100")
    finally:
        s.close()
    assert r.returncode != 0 and "exploratory-big.csv" in r.stderr
    assert not list((tmp_path / "data" / "raw").rglob("exploratory-big.csv*"))


def test_raw_downloads_are_gitignored_and_checksums_are_not():
    def ignored(path):
        return subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0

    assert ignored("data/raw/upworthy/anything.csv") and ignored("data/raw/asos/x.parquet")
    assert not ignored("data/CHECKSUMS.json")
