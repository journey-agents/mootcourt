"""T-042: the guarded against unguarded comparison (paired by test, same rows)."""
import json

import pytest

GATES = {"n_200": 200, "n_400": 400}


def _run(imp, ledger, guard):
    harness, report = imp("mootcourt.harness"), imp("mootcourt.report")
    rungs = {k: v for k, v in harness.default_rungs("synthetic", p2_guard=guard).items() if k in ("P0", "P1", "P2")}
    sc = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger))
    doc = report.build_document(sc, ledger=ledger, source="synthetic", snapshot_id="20261103-aaaaaaaaaaaa", model_id="m", feature_hash="f",
                                command="c", seed=0, gates=GATES, B=40)
    return sc, json.loads(json.dumps(doc))


@pytest.fixture(scope="module")
def runs():
    import importlib

    synth = importlib.import_module("mootcourt.sources.synthetic")
    ledger, _ = synth.generate(synth.SyntheticConfig(seed=5, n_tests=260, variants_per_test=2))
    return _run(importlib.import_module, ledger, 2.0), _run(importlib.import_module, ledger, None)


def test_paired_differences_and_shares(imp, runs):
    (gs, gd), (us, ud) = runs
    out = imp("mootcourt.guard_compare").compare_guard(gs, us, gd, ud, B=60, seed=1)
    assert out["rung"] == "P2" and out["guarded"]["n"] == out["unguarded"]["n"] == out["difference"]["logscore"]["n"]
    for k in ("logscore", "crps", "brier_skill"):
        d = out["difference"][k]
        assert d["lo"] <= d["estimate"] <= d["hi"]
        assert {"estimate", "lo", "hi", "n"} <= set(d)
    # the guard can only move lambda toward zero
    assert out["guarded"]["share_lambda_zero"] >= out["unguarded"]["share_lambda_zero"]
    assert out["guarded"]["guard"] == 2.0 and out["unguarded"]["guard"] is None
    assert out["unguarded"]["share_guard_held"] == 0.0
    # the paired log-score difference is the difference of the two runs' own all-rows means up to the common rows
    own = out["guarded"]["logscore"] - out["unguarded"]["logscore"]
    assert out["difference"]["logscore"]["estimate"] == pytest.approx(own, abs=1e-9)


def test_refuses_runs_on_different_snapshots(imp, runs):
    (gs, gd), (us, ud) = runs
    other = json.loads(json.dumps(ud))
    other["header"]["snapshot_id"] = "20261103-bbbbbbbbbbbb"
    with pytest.raises(ValueError, match="same source and snapshot"):
        imp("mootcourt.guard_compare").compare_guard(gs, us, gd, other)
