"""scripts/paper_figures.py: every figure is written from the committed run folder, identical twice, with every plotted number in its JSON."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "paper" / "data" / "run5-period-rule"
CAUTIONARY = ROOT / "paper" / "data" / "run1-relative-lift"
EXPECTED = (
    [
        f"{kind}-{src}.pdf"
        for src in ("upworthy", "asos", "synthetic")
        for kind in ("coverage-se", "coverage-exposure", "decision-value", "reliability")
    ]
    + ["learning-curve-upworthy.pdf", "learning-curve-asos.pdf", "cautionary-upworthy.pdf"]
)


@pytest.fixture(scope="module")
def pf():
    spec = importlib.util.spec_from_file_location("paper_figures", ROOT / "scripts" / "paper_figures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def two_runs(pf, tmp_path_factory):
    a, b = tmp_path_factory.mktemp("figs-a"), tmp_path_factory.mktemp("figs-b")
    assert pf.main(["--run", str(RUN), "--out", str(a)]) == 0
    assert pf.main(["--run", str(RUN), "--out", str(b)]) == 0
    return a, b


def test_every_expected_file_is_written_and_is_a_pdf(two_runs):
    a, _ = two_runs
    for name in EXPECTED + ["figures.json"]:
        assert (a / name).is_file(), name
    for name in EXPECTED:
        assert (a / name).read_bytes().startswith(b"%PDF")


def test_two_runs_are_byte_identical(two_runs):
    a, b = two_runs
    assert sorted(p.name for p in a.iterdir()) == sorted(p.name for p in b.iterdir())
    for p in a.iterdir():
        assert p.read_bytes() == (b / p.name).read_bytes(), p.name


def test_fonts_are_embedded_and_no_date_is_written(two_runs):
    a, _ = two_runs
    for name in EXPECTED:
        raw = (a / name).read_bytes()
        assert b"/CreationDate" not in raw and b"/ModDate" not in raw, name
        assert b"/FontFile2" in raw and b"/Type3" not in raw, name


def test_text_has_no_dashes(two_runs):
    a, _ = two_runs
    dashes = [chr(0x2013), chr(0x2014), chr(0x2212)]
    text = (a / "figures.json").read_text(encoding="utf-8")
    assert not any(d in text for d in dashes)
    for name in EXPECTED:
        raw = (a / name).read_bytes()
        assert not any(d.encode() in raw for d in dashes), name



def _resolve(doc, path):
    for part in path.split("."):
        doc = doc[part]
    return doc


def _json_for(entry):
    """The JSON files a figure reads: one path, or two joined by ' and ' (the cautionary figure)."""
    return {p: json.loads((ROOT / p).read_text()) for p in entry["json"].split(" and ")}


def test_every_plotted_number_is_in_its_named_json(two_runs):
    a, _ = two_runs
    index = json.loads((a / "figures.json").read_text())
    assert [f["file"] for f in index["figures"]] == sorted(EXPECTED)
    for entry in index["figures"]:
        docs = _json_for(entry)
        assert entry["values"], entry["file"]
        for item in entry["values"]:
            doc = docs[item.get("json", entry["json"])]
            rows = [r for r in _resolve(doc, item["table"]) if all(r.get(k) == v for k, v in item["where"].items())]
            assert len(rows) == 1, (entry["file"], item)
            assert rows[0][item["field"]] == item["value"], (entry["file"], item)
        assert entry["keys"] == sorted({f"{i['table']}.{i['field']}" for i in entry["values"]})


def test_reliability_bars_follow_the_bin_counts(two_runs):
    a, _ = two_runs
    index = json.loads((a / "figures.json").read_text())
    entry = next(f for f in index["figures"] if f["file"] == "reliability-upworthy.pdf")
    by_bin = {}
    for item in entry["values"]:
        by_bin.setdefault((item["where"]["rung"], item["where"]["bin"]), {})[item["field"]] = item["value"]
    assert entry["derived"] and len(entry["derived"]) == len(by_bin)
    for d in entry["derived"]:
        v = by_bin[(d["rung"], d["bin"])]
        assert d["lo"] == binom.ppf(0.05, v["n"], v["mean_p"]) / v["n"]
        assert d["hi"] == binom.ppf(0.95, v["n"], v["mean_p"]) / v["n"]
        assert d["lo"] <= v["mean_p"] <= d["hi"]


def test_cautionary_figure_uses_both_runs_and_a_missing_file_is_skipped(pf, tmp_path):
    out = tmp_path / "out"
    pf.main(["--run", str(RUN), "--out", str(out), "--cautionary", str(tmp_path / "nowhere")])
    doc = json.loads((out / "figures.json").read_text())
    assert not (out / "cautionary-upworthy.pdf").exists()
    assert [s["file"] for s in doc["skipped"] if s["file"].startswith("cautionary")] == ["cautionary-upworthy.pdf"]
    assert CAUTIONARY.is_dir()
