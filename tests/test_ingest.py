"""Builder additions (T-022): `moot ingest` builds the shared ledger from data/raw, idempotently."""
import csv
import re
import shutil
from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "asos_mini"
HEAD = ["", "created_at", "updated_at", "clickability_test_id", "excerpt", "headline", "lede", "slug", "eyecatcher_id", "impressions",
        "clicks", "significance", "first_place", "winner", "share_text", "square", "test_week"]


def _raw(tmp_path):
    up = tmp_path / "raw" / "upworthy"
    up.mkdir(parents=True)
    with (up / "upworthy-archive-exploratory-packages-03.12.2020.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        w.writerow([0, "2014-09-28 10:00:00.5", "2099", "T1", "x", "H0", "l", "s", "e1", 5000, 100, 1.0, True, True, "", "", 201440])
        w.writerow([1, "2014-09-28 11:00:00", "2099", "T1", "x", "H1", "l", "s", "e1", 5000, 150, 1.0, True, True, "", "", 201440])
    shutil.copytree(FIX, tmp_path / "raw" / "asos")
    return tmp_path / "raw"


def _run(imp, tmp_path, *extra):
    app = imp("mootcourt.cli").app
    return CliRunner().invoke(app, ["ingest", "--raw-dir", str(_raw_dir(tmp_path)), "--ledger", str(tmp_path / "ledger" / "ledger.parquet"), *extra])


def _raw_dir(tmp_path):
    return tmp_path / "raw" if (tmp_path / "raw").exists() else _raw(tmp_path)


def test_ingest_builds_one_ledger_for_both_sources_and_is_idempotent(imp, tmp_path):
    ledger = imp("mootcourt.ledger")
    res = _run(imp, tmp_path, "--source", "upworthy")
    assert res.exit_code == 0, res.output
    res = _run(imp, tmp_path, "--source", "asos")
    assert res.exit_code == 0, res.output
    df = ledger.read_ledger(tmp_path / "ledger" / "ledger.parquet")
    assert set(df["source"]) == {"upworthy", "asos"} and (df["source"] == "upworthy").sum() == 1 and (df["source"] == "asos").sum() == 11
    before = len(df)
    again = _run(imp, tmp_path, "--source", "all", "--no-synthetic")
    assert again.exit_code == 0, again.output
    assert len(ledger.read_ledger(tmp_path / "ledger" / "ledger.parquet")) == before


def test_ingest_synthetic_rows_and_missing_raw_file(imp, tmp_path):
    ledger = imp("mootcourt.ledger")
    res = _run(imp, tmp_path, "--source", "synthetic", "--n-tests", "40")
    assert res.exit_code == 0, res.output
    assert set(ledger.read_ledger(tmp_path / "ledger" / "ledger.parquet")["source"]) == {"synthetic"}
    empty = CliRunner().invoke(imp("mootcourt.cli").app, ["ingest", "--source", "upworthy", "--raw-dir", str(tmp_path / "nothing"),
                                                          "--ledger", str(tmp_path / "l2" / "ledger.parquet")])
    flat = re.sub(r"[│╭╰╮╯─\s]+", " ", empty.output)
    assert empty.exit_code != 0 and "make data" in flat


def test_makefile_data_target_downloads_then_ingests():
    make = (ROOT / "Makefile").read_text()
    block = make.split("\ndata:", 1)[1].split("\n\n", 1)[0]
    assert "scripts/download_data.py" in block and "ingest" in block
