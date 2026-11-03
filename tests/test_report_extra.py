"""Extra checks for the report writer and snapshot reuse (builder additions)."""
import json

import pandas as pd


def _scores(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=141, n_tests=200, variants_per_test=2, cell_params={"headline_only": (1.0, 2.0)}, s_scale=2.0)[0]
    rungs = {k: v for k, v in harness.default_rungs("synthetic").items() if k in ("P0", "P1")}
    return ledger, harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger))


def test_markdown_is_regenerated_exactly_from_the_json(imp, make_synth, tmp_path):
    report = imp("mootcourt.report")
    ledger, sc = _scores(imp, make_synth)
    paths = report.write_report(sc, ledger=ledger, source="synthetic", snapshot_id="20261102-aaaaaaaaaaaa", model_id="m1", feature_hash="f1",
                                command="moot backtest --source synthetic --origins quarterly", seed=0, gates={"n_200": 200, "n_400": 400},
                                out_dir=tmp_path, B=50)
    doc = json.loads(paths.json.read_text(encoding="utf-8"))
    assert report.render_markdown(doc) == paths.md.read_text(encoding="utf-8")


def test_boundary_sentence_is_in_the_header_exactly(imp, make_synth, tmp_path, spec_boundary_sentence):
    report = imp("mootcourt.report")
    ledger, sc = _scores(imp, make_synth)
    paths = report.write_report(sc, ledger=ledger, source="synthetic", snapshot_id="20261102-aaaaaaaaaaaa", model_id="m1", feature_hash="f1",
                                command="c", seed=0, gates={"n_200": 200, "n_400": 400}, out_dir=tmp_path, B=50)
    assert spec_boundary_sentence in paths.md.read_text(encoding="utf-8")
    assert json.loads(paths.json.read_text(encoding="utf-8"))["header"]["boundary"] == spec_boundary_sentence


def test_reliability_seed_does_not_overwrite_a_newer_report(imp, make_synth, tmp_path):
    report = imp("mootcourt.report")
    _, sc = _scores(imp, make_synth)
    newer = {"source": "synthetic", "as_of": "2099-01-01T00:00:00+00:00", "cells": {"x": {"as_of": "2099-01-01T00:00:00+00:00"}}}
    (tmp_path / "reliability-synthetic.json").write_text(json.dumps(newer))
    report.write_reliability(sc, "synthetic", tmp_path)
    assert json.loads((tmp_path / "reliability-synthetic.json").read_text()) == newer
    report.write_reliability(sc, "synthetic", tmp_path, overwrite=True)
    assert "headline_only" in json.loads((tmp_path / "reliability-synthetic.json").read_text())["cells"]


def test_ensure_snapshot_reuses_an_existing_one(imp, make_synth, tmp_path):
    ledger_mod = imp("mootcourt.ledger")
    ledger, _ = make_synth(seed=142, n_tests=30, variants_per_test=1)
    a = ledger_mod.ensure_snapshot(ledger, tmp_path)
    b = ledger_mod.ensure_snapshot(ledger, tmp_path)
    assert a == b and len(list((tmp_path / "snapshots").iterdir())) == 1
    c = ledger_mod.ensure_snapshot(pd.concat([ledger.iloc[:-1]]), tmp_path)
    assert c != a
