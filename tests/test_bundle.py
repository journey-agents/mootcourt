"""T-010 contracts: model bundle fit, save, load with checksums."""
import hashlib
import json

import numpy as np
import pytest


@pytest.fixture
def small_ledger(make_synth):
    ledger, _ = make_synth(seed=71, n_tests=300, variants_per_test=2, text_effect_strength=2.0)
    return ledger


def _fit(imp, ledger, sid="20261102-aaaaaaaaaaaa"):
    return imp("mootcourt.bundle").fit_bundle(ledger, "synthetic", sid)


def test_fit_bundle_carries_version_ids(imp, small_ledger):
    b = _fit(imp, small_ledger)
    assert b.snapshot_id == "20261102-aaaaaaaaaaaa"
    assert len(b.feature_hash) == 12 and b.model_id
    preds = b.predict_all(b.transform_text("cats and dogs", image_changed=False), 1.5, "headline_only",
                          small_ledger["usable_after"].max())
    assert set(preds) >= {"P0", "P1", "P2"}


def test_model_id_deterministic_and_fit_reproducible(imp, small_ledger, origin):
    a, b = _fit(imp, small_ledger), _fit(imp, small_ledger)
    assert a.model_id == b.model_id
    x = a.transform_text("you will not believe this", image_changed=False)
    for rung in ("P0", "P1", "P2"):
        pa = a.predict_all(x, 1.5, "headline_only", small_ledger["usable_after"].max())[rung]
        pb = b.predict_all(x, 1.5, "headline_only", small_ledger["usable_after"].max())[rung]
        np.testing.assert_allclose(pa.pmf, pb.pmf, atol=1e-15)
    assert _fit(imp, small_ledger, sid="20261102-bbbbbbbbbbbb").model_id != a.model_id


def test_save_writes_manifest_and_checksums(imp, small_ledger, tmp_path):
    bm = imp("mootcourt.bundle")
    b = _fit(imp, small_ledger)
    d = bm.save_bundle(b, tmp_path)
    assert d == tmp_path / b.model_id
    man = json.loads((d / "manifest.json").read_text())
    for key in ("snapshot_id", "feature_hash", "parameters", "fit_time", "backtest_summary", "artifacts"):
        assert key in man
    assert man["backtest_summary"] is None
    assert any(p.suffix == ".npz" for p in d.iterdir())
    for rel, digest in man["artifacts"].items():
        assert hashlib.sha256((d / rel).read_bytes()).hexdigest() == digest


def test_round_trip_predictions_equal(imp, small_ledger, tmp_path):
    bm = imp("mootcourt.bundle")
    b = _fit(imp, small_ledger)
    bm.save_bundle(b, tmp_path)
    loaded = bm.load_bundle(b.model_id, tmp_path)
    origin = small_ledger["usable_after"].max()
    x = b.transform_text("surprising science fact", image_changed=True)
    for rung in ("P0", "P1", "P2"):
        a = b.predict_all(x, 1.5, "headline_only", origin)[rung]
        c = loaded.predict_all(x, 1.5, "headline_only", origin)[rung]
        np.testing.assert_allclose(a.pmf, c.pmf, atol=1e-12, rtol=0)
    assert loaded.feature_hash == b.feature_hash and loaded.snapshot_id == b.snapshot_id


def test_one_flipped_byte_raises_integrity_error(imp, small_ledger, tmp_path):
    bm = imp("mootcourt.bundle")
    b = _fit(imp, small_ledger)
    d = bm.save_bundle(b, tmp_path)
    victim = sorted(p for p in d.iterdir() if p.name != "manifest.json")[0]
    raw = bytearray(victim.read_bytes())
    raw[len(raw) // 2] ^= 0x01
    victim.write_bytes(bytes(raw))
    with pytest.raises(bm.BundleIntegrityError):
        bm.load_bundle(b.model_id, tmp_path)


def test_load_never_leaves_models_dir(imp, small_ledger, tmp_path):
    bm = imp("mootcourt.bundle")
    models = tmp_path / "models"
    models.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "manifest.json").write_text("{}")
    for bad in ("../outside", str(outside), "a/../../outside"):
        with pytest.raises(ValueError):
            bm.load_bundle(bad, models)


def test_index_is_rebuilt_not_incrementally_updated(imp, make_synth):
    full, _ = make_synth(seed=72, n_tests=300, variants_per_test=2)
    part = full.iloc[: len(full) // 2]
    bm = imp("mootcourt.bundle")
    bm.fit_bundle(part, "synthetic", "20261102-aaaaaaaaaaaa")
    grown = bm.fit_bundle(full, "synthetic", "20261102-aaaaaaaaaaaa")
    direct = bm.fit_bundle(full, "synthetic", "20261102-aaaaaaaaaaaa")
    assert grown.model_id == direct.model_id
    x = grown.transform_text("number one reason", image_changed=False)
    o = full["usable_after"].max()
    np.testing.assert_allclose(grown.predict_all(x, 1.5, "headline_only", o)["P2"].pmf,
                               direct.predict_all(x, 1.5, "headline_only", o)["P2"].pmf, atol=1e-15)
