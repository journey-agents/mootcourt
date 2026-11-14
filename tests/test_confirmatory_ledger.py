"""The one guarded door to the Upworthy confirmatory file (scripts/confirmatory_ledger.py; run 9 plan, Part C). No real file is read here."""
import importlib.util
import shutil
from pathlib import Path

import pandas as pd
import pytest
from test_randomization_window import BOUNDARIES, _pair, _write


@pytest.fixture(scope="module")
def cl():
    path = Path(__file__).resolve().parents[1] / "scripts" / "confirmatory_ledger.py"
    spec = importlib.util.spec_from_file_location("confirmatory_ledger", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def stand_in(tmp_path):
    """A small file of made-up packages under a name like the real one's."""
    rows = []
    for name, (at, _) in BOUNDARIES.items():
        rows += _pair(name, at, at)
    p = tmp_path / "upworthy-archive-confirmatory-packages-stand-in.csv"
    _write(p, rows)
    return p


def test_it_refuses_without_the_recorded_decision(cl, stand_in, tmp_path):
    for bad in (None, "", "2026-11-13", "yes"):
        with pytest.raises(PermissionError):
            cl.build(stand_in, tmp_path / "out" / "ledger.parquet", decision=bad)
    assert not (tmp_path / "out").exists()


def test_it_refuses_any_file_that_is_not_the_confirmatory_one(cl, stand_in, tmp_path):
    for name in ("upworthy-archive-holdout-packages.csv", "upworthy-archive-undeployed-packages.csv", "upworthy-archive-exploratory-packages.csv"):
        other = tmp_path / name
        shutil.copy(stand_in, other)
        with pytest.raises(PermissionError):
            cl.build(other, tmp_path / "out" / "ledger.parquet", decision=cl.DECISION)


def test_with_the_decision_it_writes_a_ledger_of_its_own_and_a_record(cl, stand_in, tmp_path):
    out = tmp_path / "confirmatory" / "data" / "ledger" / "ledger.parquet"
    doc = cl.build(stand_in, out, decision=cl.DECISION)
    led = pd.read_parquet(out)
    assert set(led["source"]) == {"upworthy"} and len(led) == doc["rows"] > 0
    assert doc["decision"] == "2026-11-14" and doc["file"] == stand_in.name and len(doc["sha256"]) == 64
    assert (out.parent / "confirmatory-record.json").is_file()
    with pytest.raises(FileExistsError):                                  # opened once: a second build is refused
        cl.build(stand_in, out, decision=cl.DECISION)
