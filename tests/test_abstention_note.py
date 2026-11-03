"""Builder additions (T-022): the report states which abstention triggers never fired."""
import pandas as pd


def _scores(reasons_by_origin):
    rows = []
    for origin, reasons in reasons_by_origin:
        for r in reasons:
            rows.append({"origin": pd.Timestamp(origin, tz="UTC"), "rung": "P2", "cell": "a", "abstain": bool(r), "abstain_reasons": r})
    return pd.DataFrame(rows)


def test_note_names_triggers_that_never_fired_and_burn_in_only_reliability(imp):
    hs = imp("mootcourt.harness_stats")
    df = _scores([("2014-01-01", ["reliability", "reliability", "reliability"]), ("2014-04-01", ["support", "", "novelty,support", ""])])
    note = hs.abstention_trigger_note(df)
    assert "Never fired in this backtest: instability." in note
    assert "After the burn-in origin the reliability trigger fired on 0 rows" in note
    assert "no cell was marked drifted" in note


def test_note_when_everything_fired(imp):
    hs = imp("mootcourt.harness_stats")
    df = _scores([("2014-01-01", ["reliability"]), ("2014-04-01", ["support", "novelty", "reliability", "instability"])])
    note = hs.abstention_trigger_note(df)
    assert "All four triggers fired at least once." in note
    assert "the reliability trigger fired on 1 rows" in note and "no cell was marked drifted" not in note


def test_note_reaches_the_report_json_and_markdown(imp, make_synth, tmp_path):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=95, n_tests=120, variants_per_test=2, cell_params={"headline_only": (1.0, 2.0)}, s_scale=2.0)[0]
    p0 = imp("mootcourt.predictors.p0").P0Predictor
    scores = harness.rolling_origin(ledger, {"P0": lambda r, o: p0().fit(r)}, harness.quarterly_origins(ledger))
    import json

    paths = imp("mootcourt.report").write_report(
        scores, ledger=ledger, source="synthetic", snapshot_id="20261102-eeeeeeeeeeee", model_id="m1", feature_hash="f1", command="c", seed=0,
        gates={"n_200": 200, "n_400": 400}, out_dir=tmp_path, B=30)
    data = json.loads(paths.json.read_text())
    assert "fired" in data["notes"]["abstention_triggers"]
    assert data["notes"]["abstention_triggers"] in paths.md.read_text()
