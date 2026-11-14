"""The one guarded fetch of the confirmatory packages file (scripts/fetch_confirmatory.py). No test contacts the network."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture()
def fc():
    path = Path(__file__).resolve().parents[1] / "scripts" / "fetch_confirmatory.py"
    spec = importlib.util.spec_from_file_location("fetch_confirmatory", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LISTING = [{"name": "upworthy-archive-exploratory-packages.csv", "size": 5, "url": "https://osf.io/download/a/"},
           {"name": "upworthy-archive-confirmatory-packages.csv", "size": 4, "url": "https://osf.io/download/b/"},
           {"name": "upworthy-archive-holdout-packages.csv", "size": 4, "url": "https://osf.io/download/c/"},
           {"name": "upworthy-archive-undeployed-packages.csv", "size": 4, "url": "https://osf.io/download/d/"}]


def _stub(fc, monkeypatch, listing=LISTING):
    calls = []

    def fake_fetch(url, dest, expected):
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"data")
        return "abc123", 4

    monkeypatch.setattr(fc.dd, "list_files", lambda base, node: list(listing))
    monkeypatch.setattr(fc.dd, "fetch", fake_fetch)
    return calls


def test_without_the_recorded_decision_nothing_is_listed_or_fetched(fc, monkeypatch, tmp_path):
    calls = _stub(fc, monkeypatch)
    with pytest.raises(PermissionError):
        fc.fetch_once(tmp_path, decision=None)
    with pytest.raises(PermissionError):
        fc.fetch_once(tmp_path, decision="2026-11-13")
    assert calls == [] and not any(tmp_path.iterdir())


def test_only_the_confirmatory_file_is_fetched_and_its_checksum_is_recorded(fc, monkeypatch, tmp_path):
    calls = _stub(fc, monkeypatch)
    doc = fc.fetch_once(tmp_path, decision="2026-11-14")
    assert calls == ["https://osf.io/download/b/"]
    assert (tmp_path / "upworthy-archive-confirmatory-packages.csv").read_bytes() == b"data"
    record = json.loads((tmp_path / "confirmatory-fetch-record.json").read_text())
    assert record == doc and doc["sha256"] == "abc123" and doc["bytes"] == 4 and doc["decision"] == "2026-11-14"
    assert doc["file"] == "upworthy-archive-confirmatory-packages.csv" and doc["node"] == "jd64p"


def test_a_second_fetch_is_refused(fc, monkeypatch, tmp_path):
    _stub(fc, monkeypatch)
    fc.fetch_once(tmp_path, decision="2026-11-14")
    with pytest.raises(FileExistsError):
        fc.fetch_once(tmp_path, decision="2026-11-14")


def test_no_match_or_more_than_one_match_fetches_nothing(fc, monkeypatch, tmp_path):
    calls = _stub(fc, monkeypatch, [f for f in LISTING if "confirmatory" not in f["name"]])
    with pytest.raises(LookupError):
        fc.fetch_once(tmp_path, decision="2026-11-14")
    two = LISTING + [{"name": "confirmatory-notes.csv", "size": 1, "url": "https://osf.io/download/e/"}]
    calls2 = _stub(fc, monkeypatch, two)
    with pytest.raises(LookupError):
        fc.fetch_once(tmp_path, decision="2026-11-14")
    assert calls == [] and calls2 == []


def test_a_name_that_also_says_holdout_or_undeployed_is_not_the_confirmatory_file(fc, monkeypatch, tmp_path):
    calls = _stub(fc, monkeypatch, [{"name": "confirmatory-holdout.csv", "size": 1, "url": "https://osf.io/download/f/"}])
    with pytest.raises(LookupError):
        fc.fetch_once(tmp_path, decision="2026-11-14")
    assert calls == []
