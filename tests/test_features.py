"""T-004 contracts: features, kernel, retrieval index."""
import json
import subprocess
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd
import pytest


def _text_rows(make_synth, n_tests=400):
    ledger, _ = make_synth(seed=21, n_tests=n_tests, variants_per_test=2)
    return ledger


def test_structured_feature_names_start_with_the_six(imp):
    names = list(imp("mootcourt.features").STRUCTURED_FEATURES)
    assert names[:6] == ["n_words", "has_question", "has_number", "has_quote", "starts_pronoun", "image_changed"]


def test_structured_features_values(imp):
    f = imp("mootcourt.features")
    v = f.structured_features("You will not believe these 3 \"facts\"?", image_changed=True)
    got = dict(zip(f.STRUCTURED_FEATURES, v))
    assert got["n_words"] == 7 and got["has_question"] == 1 and got["has_number"] == 1
    assert got["has_quote"] == 1 and got["starts_pronoun"] == 1 and got["image_changed"] == 1
    plain = dict(zip(f.STRUCTURED_FEATURES, f.structured_features("Cats nap", image_changed=False)))
    assert plain["n_words"] == 2 and plain["has_question"] == 0 and plain["has_number"] == 0
    assert plain["has_quote"] == 0 and plain["starts_pronoun"] == 0 and plain["image_changed"] == 0


def test_fit_is_deterministic_and_dims_are_capped(imp, make_synth):
    f = imp("mootcourt.features")
    rows = _text_rows(make_synth)
    a = f.FeatureSpace.fit(rows)
    b = f.FeatureSpace.fit(rows)
    xa, xb = a.transform(rows), b.transform(rows)
    np.testing.assert_allclose(xa, xb, atol=1e-12)
    assert a.svd_dims <= 64 and xa.shape == (len(rows), a.dim)
    assert f.feature_hash(a) == f.feature_hash(b)


def _tiny_vocab_rows(ledger_builder, n=12):
    df = ledger_builder(n=n)
    words = ["cats nap", "dogs run", "cats run", "dogs nap"]
    df["features_json"] = [json.dumps({"headline": words[i % 4] + " today", "image_changed": False}) for i in range(n)]
    return df


def test_svd_cap_is_logged_when_vocabulary_is_small(imp, ledger_builder, caplog):
    f = imp("mootcourt.features")
    rows = _tiny_vocab_rows(ledger_builder, n=40)
    with caplog.at_level("INFO"):
        space = f.FeatureSpace.fit(rows, min_df=1)
    assert space.svd_dims < 64
    assert any("cap" in r.getMessage().lower() for r in caplog.records)


def test_transform_handles_unseen_and_oov_headlines(imp, make_synth):
    f = imp("mootcourt.features")
    space = f.FeatureSpace.fit(_text_rows(make_synth))
    x = space.transform_text(["zzzxq qqqwv xylophonic", "", "totally unseen words only"], image_changed=False)
    assert x.shape == (3, space.dim)
    assert np.isfinite(x).all()


def test_median_bandwidth_is_the_median_pairwise_distance(imp):
    f = imp("mootcourt.features")
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 5))
    d = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    expected = np.median(d[np.triu_indices(40, k=1)])
    assert f.median_bandwidth(X) == pytest.approx(expected, rel=1e-9)


def test_kernel_weights_match_dense_reference(imp):
    f = imp("mootcourt.features")
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 4))
    x = rng.normal(size=4)
    h = 1.7
    ref = np.exp(-((X - x) ** 2).sum(1) / (2 * h * h))
    np.testing.assert_allclose(f.kernel_weights(x, X, h), ref, atol=1e-9, rtol=0)


def test_top_m_neighbors_equal_brute_force(imp):
    f = imp("mootcourt.features")
    rng = np.random.default_rng(2)
    X = rng.normal(size=(3000, 8))
    index = f.build_index(X)
    x = rng.normal(size=8)
    idx, w = f.top_m_neighbors(x, index, m=100)
    full = f.kernel_weights(x, X, index.h)
    order = np.argsort(-full)[:100]
    np.testing.assert_allclose(np.sort(w)[::-1], full[order], atol=1e-12)
    assert set(idx.tolist()) == set(order.tolist())


def test_top_m_with_m_larger_than_n_returns_all(imp):
    f = imp("mootcourt.features")
    X = np.random.default_rng(3).normal(size=(20, 3))
    idx, w = f.top_m_neighbors(X[0], f.build_index(X), m=1000)
    assert len(idx) == 20 and len(w) == 20


def test_loo_density_matches_dense_and_stays_chunked(imp):
    f = imp("mootcourt.features")
    rng = np.random.default_rng(4)
    X = rng.normal(size=(60, 4))
    index = f.build_index(X)
    K = np.exp(-((X[:, None, :] - X[None, :, :]) ** 2).sum(-1) / (2 * index.h ** 2))
    np.fill_diagonal(K, 0.0)
    np.testing.assert_allclose(f.loo_density(index), K.sum(1) / (len(X) - 1), atol=1e-12)
    thr = f.novelty_threshold(index, pct=5)
    assert thr == pytest.approx(np.percentile(f.loo_density(index), 5))
    # memory: 20000 rows must never allocate anything close to n x n floats (3.2 GB)
    big = f.build_index(np.random.default_rng(5).normal(size=(20000, 8)).astype("float32"))
    tracemalloc.start()
    f.loo_density(big, chunk=256)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 256 * 20000 * 8 * 6, f"peak {peak} bytes exceeds a small multiple of chunk x n"


def test_feature_hash_stable_across_processes_and_sensitive(imp, make_synth, tmp_path):
    f = imp("mootcourt.features")
    rows = _text_rows(make_synth)
    h1 = f.feature_hash(f.FeatureSpace.fit(rows))
    assert len(h1) == 12 and all(c in "0123456789abcdef" for c in h1)
    # the child rebuilds the frame from a fixed seed through the same generator
    child = (
        "from mootcourt.sources import synthetic as s\n"
        "from mootcourt import features as f\n"
        "ledger, _ = s.generate(s.SyntheticConfig(seed=21, n_tests=400, variants_per_test=2))\n"
        "print(f.feature_hash(f.FeatureSpace.fit(ledger)))\n")
    out = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, check=True).stdout.strip()
    assert out == h1
    assert f.feature_hash(f.FeatureSpace.fit(rows, svd_dims=16)) != h1
    other = rows.copy()
    other["features_json"] = other["features_json"].map(
        lambda j: json.dumps({**json.loads(j), "headline": json.loads(j)["headline"] + " extraterm"}))
    assert f.feature_hash(f.FeatureSpace.fit(other)) != h1


def test_cell_only_space_degenerates(imp, ledger_builder):
    f = imp("mootcourt.features")
    rows = pd.concat([ledger_builder(n=30, cell="m1", id_prefix="a"), ledger_builder(n=30, cell="m2", id_prefix="b")],
                     ignore_index=True)
    space = f.FeatureSpace.fit(rows, cell_only=True)
    assert space.cell_only is True


def test_embeddings_backend_raises_clear_error_by_default(imp, make_synth):
    f = imp("mootcourt.features")
    with pytest.raises(RuntimeError, match="--embeddings"):
        f.FeatureSpace.fit(_text_rows(make_synth), backend="embeddings")


@pytest.mark.slow
def test_single_row_query_latency_on_20000_by_70(imp):
    f = imp("mootcourt.features")
    rng = np.random.default_rng(6)
    index = f.build_index(rng.normal(size=(20000, 70)).astype("float32"))
    x = rng.normal(size=70).astype("float32")
    f.top_m_neighbors(x, index, m=1000)
    best = min(_timed(lambda: f.top_m_neighbors(x, index, m=1000)) for _ in range(5))
    assert best < 0.25, f"query took {best:.3f}s; target 50 ms with a 5x margin"


def _timed(fn):
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t
