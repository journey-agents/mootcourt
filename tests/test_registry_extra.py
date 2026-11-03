"""Extra checks for the registry (builder additions)."""
import json

GATES = {"n_200": 200, "n_400": 400}


def test_attach_backtest_fills_manifest_and_registry_and_the_bundle_still_loads(imp, tmp_path, make_synth):
    bundle_mod, reg_mod = imp("mootcourt.bundle"), imp("mootcourt.registry")
    ledger = make_synth(seed=151, n_tests=120, variants_per_test=2)[0]
    b = bundle_mod.fit_bundle(ledger, "synthetic", "20261102-333333333333")
    bundle_mod.save_bundle(b, tmp_path)
    reg = reg_mod.Registry(tmp_path)
    reg.register_model("synthetic", b.model_id)
    report = {"header": {"snapshot_id": "20261102-333333333333"},
              "tables": {"aggregate": [{"cell": "ALL", "rung": "P2", "brier_skill": 0.05, "brier_skill_lo": 0.01, "brier_skill_hi": 0.09,
                                        "n": 321, "logscore": -2.0}]}}
    assert reg_mod.attach_backtest(tmp_path, "synthetic", "20261102-333333333333", report, "backtest-x.json") == [b.model_id]
    assert reg.summary("synthetic", b.model_id)["n"] == 321
    assert json.loads((tmp_path / b.model_id / "manifest.json").read_text())["backtest_summary"]["brier_skill"] == 0.05
    assert bundle_mod.load_bundle(b.model_id, tmp_path).backtest_summary["n"] == 321


def test_promotion_is_logged_and_clears_the_challenger(imp, tmp_path):
    reg = imp("mootcourt.registry").Registry(tmp_path)
    reg.register_model("s", "a", {"brier_skill": 0.05, "n": 900})
    reg.register_model("s", "b", {"brier_skill": 0.12, "n": 900})
    assert reg.promote("s", GATES).promoted
    doc = json.loads((tmp_path / "registry.json").read_text())["s"]
    assert doc["champion"] == "b" and doc["challenger"] is None
    assert [h["event"] for h in doc["history"]][-1] == "promoted"
    assert not reg.promote("s", GATES).promoted           # nothing left to promote


def test_exact_margin_is_accepted_despite_float_noise(imp, tmp_path):
    reg = imp("mootcourt.registry").Registry(tmp_path)
    reg.register_model("s", "a", {"brier_skill": 0.10, "n": 900})
    reg.register_model("s", "b", {"brier_skill": 0.12, "n": 900})
    assert reg.promote("s", GATES, margin=0.02).promoted
