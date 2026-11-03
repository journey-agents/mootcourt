"""T-021 contracts: ASOS loader.

The real file layout is unknown until the OSF archive is reachable, so T-021 writes
tests/fixtures/asos_mini/ to mirror the real layout and records the expected counts in
tests/fixtures/asos_mini/EXPECTED.json with these keys:
  n_contrasts          one per treatment variant per metric at the final checkpoint
  n_checkpoints        checkpoints per experiment in the fixture (at least 5)
  last_checkpoint      ISO date of the final checkpoint of the fixture experiments
  metrics              list of metric ids
These tests are layout independent and fail until that fixture and the loader exist.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FIX = Path(__file__).parent / "fixtures" / "asos_mini"


@pytest.fixture
def expected():
    path = FIX / "EXPECTED.json"
    assert path.exists(), "T-021 must create tests/fixtures/asos_mini/EXPECTED.json"
    return json.loads(path.read_text())


@pytest.fixture
def ledger(imp, expected):
    return imp("mootcourt.sources.asos").load_asos(FIX)


def test_ledger_is_valid_and_labelled_asos(imp, ledger):
    imp("mootcourt.ledger").validate_ledger(ledger)
    assert set(ledger["source"]) == {"asos"}


def test_only_the_final_checkpoint_is_an_outcome(ledger, expected):
    assert expected["n_checkpoints"] >= 5
    assert len(ledger) == expected["n_contrasts"], "earlier checkpoints must never become rows"
    assert not ledger["row_id"].duplicated().any()


def test_usable_after_is_the_final_checkpoint_date(ledger, expected):
    last = pd.Timestamp(expected["last_checkpoint"], tz="UTC")
    assert (ledger["usable_after"] == last).all() or (ledger["usable_after"] >= last).all()
    assert (ledger["usable_after"] >= ledger["final_read_at"]).all()


def test_cell_is_the_metric_id_and_effects_are_standardised(ledger, expected):
    assert set(ledger["cell"]) <= set(expected["metrics"]) and set(ledger["cell"])
    adm = ledger[ledger["status"] == "admitted"]
    assert np.isfinite(adm["y"]).all() and (adm["s"] > 0).all()
    assert (adm["y"].abs() < 10).all(), "standardised effects are O(1), not raw units"
    feats = json.loads(adm.iloc[0]["features_json"])
    assert any("original" in k or "raw" in k or "unit" in k for k in feats), "original-unit effect is kept in features_json"


def test_p2_degenerates_note_in_module_docstring(imp):
    doc = (imp("mootcourt.sources.asos").__doc__ or "").lower()
    assert "p2" in doc and "p1" in doc and "metric" in doc


def test_loader_takes_path_and_fails_clearly_on_missing_input(imp, tmp_path):
    with pytest.raises(FileNotFoundError):
        imp("mootcourt.sources.asos").load_asos(tmp_path / "missing")
