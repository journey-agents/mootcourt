"""T-003 contracts: synthetic source with known truth."""
import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

UTC = dt.timezone.utc


def _gen(imp, **kw):
    syn = imp("mootcourt.sources.synthetic")
    return syn.generate(syn.SyntheticConfig(**kw))


def test_generate_returns_valid_ledger_and_truth(imp):
    ledger_mod = imp("mootcourt.ledger")
    ledger, truth = _gen(imp, seed=1, n_tests=200)
    ledger_mod.validate_ledger(ledger)
    assert {"row_id", "theta_true"} <= set(truth.columns)
    assert set(truth["row_id"]) == set(ledger["row_id"])
    assert "theta_true" not in ledger.columns, "truth never lives in the ledger"
    assert "theta_true" not in ledger["features_json"].iloc[0]


def test_same_seed_identical_different_seed_differs(imp):
    a, _ = _gen(imp, seed=3, n_tests=100)
    b, _ = _gen(imp, seed=3, n_tests=100)
    c, _ = _gen(imp, seed=4, n_tests=100)
    pd.testing.assert_frame_equal(a, b)
    assert not a["y"].equals(c["y"])


def test_cell_moments_match_configuration(imp):
    ledger, truth = _gen(imp, seed=5, n_tests=2500, variants_per_test=1,
                         cell_params={"headline_only": (2.0, 3.0)})
    th = truth.set_index("row_id").loc[ledger["row_id"], "theta_true"].to_numpy()
    n = len(th)
    assert n >= 2000
    assert abs(th.mean() - 2.0) < 3 * 3.0 / np.sqrt(n)
    assert abs(th.std(ddof=1) - 3.0) < 3 * 3.0 / np.sqrt(2 * (n - 1))


def test_standardized_residual_sd_is_one(imp):
    ledger, truth = _gen(imp, seed=6, n_tests=5200, variants_per_test=1)
    th = truth.set_index("row_id").loc[ledger["row_id"], "theta_true"].to_numpy()
    z = (ledger["y"].to_numpy() - th) / ledger["s"].to_numpy()
    assert len(z) >= 5000
    assert 0.95 <= z.std() <= 1.05


def test_usable_after_is_final_read_plus_seven_days(imp):
    ledger, _ = _gen(imp, seed=7, n_tests=50)
    assert ((ledger["usable_after"] - ledger["final_read_at"]) == pd.Timedelta(days=7)).all()
    assert (ledger["source"] == "synthetic").all()


def test_text_signal_shifts_theta_for_signal_words(imp):
    syn = imp("mootcourt.sources.synthetic")
    ledger, truth = _gen(imp, seed=8, n_tests=3000, variants_per_test=1, text_effect_strength=4.0)
    heads = ledger["features_json"].map(lambda j: json.loads(j)["headline"].lower())
    has = heads.map(lambda h: any(w in h.split() for w in syn.SIGNAL_WORDS)).to_numpy()
    th = truth.set_index("row_id").loc[ledger["row_id"], "theta_true"].to_numpy()
    assert 0.2 < has.mean() < 0.8, "signal words must appear in a non-trivial share of headlines"
    assert th[has].mean() - th[~has].mean() > 3.0


def test_zero_text_strength_has_no_shift(imp):
    syn = imp("mootcourt.sources.synthetic")
    ledger, truth = _gen(imp, seed=9, n_tests=3000, variants_per_test=1, text_effect_strength=0.0)
    heads = ledger["features_json"].map(lambda j: json.loads(j)["headline"].lower())
    has = heads.map(lambda h: any(w in h.split() for w in syn.SIGNAL_WORDS)).to_numpy()
    th = truth.set_index("row_id").loc[ledger["row_id"], "theta_true"].to_numpy()
    assert abs(th[has].mean() - th[~has].mean()) < 0.5


def test_low_exposure_fraction_option(imp):
    ledger, _ = _gen(imp, seed=10, n_tests=2000, variants_per_test=1, low_exposure_frac=0.2)
    frac = (ledger["status"] == "low_exposure").mean()
    assert 0.17 < frac < 0.23


@pytest.mark.parametrize("k", [1, 2, 4])
def test_variants_per_test(imp, k):
    ledger, _ = _gen(imp, seed=11, n_tests=60, variants_per_test=k)
    assert (ledger.groupby("test_id").size() == k).all()


def test_variants_in_a_test_share_a_test_level_effect(imp):
    ledger, truth = _gen(imp, seed=12, n_tests=800, variants_per_test=3, test_effect_sd=2.0,
                         cell_params={"headline_only": (0.0, 0.5)})
    df = ledger[["row_id", "test_id"]].merge(truth, on="row_id")
    between = df.groupby("test_id")["theta_true"].mean().var()
    assert between > 2.0, "test-level random effect should dominate the spread of test means"


def test_regime_shift_moves_mu(imp):
    shift_at = dt.datetime(2014, 1, 1, tzinfo=UTC)
    ledger, truth = _gen(imp, seed=13, n_tests=3000, variants_per_test=1, shift_at=shift_at, shift_delta=-4.0,
                         cell_params={"headline_only": (2.0, 1.0)})
    th = truth.set_index("row_id").loc[ledger["row_id"], "theta_true"].to_numpy()
    after = (ledger["started_at"] >= pd.Timestamp(shift_at)).to_numpy()
    assert after.any() and (~after).any()
    assert abs((th[~after].mean() - th[after].mean()) - 4.0) < 0.3


def test_team_forecaster_stored_in_features_json(imp):
    ledger, truth = _gen(imp, seed=14, n_tests=300, variants_per_test=1, team_forecaster_sd=1.0)
    feats = ledger["features_json"].map(json.loads)
    assert all("p_win_team" in f and "point_team" in f for f in feats)
    assert all(0.0 <= f["p_win_team"] <= 1.0 for f in feats)
    pt = np.array([f["point_team"] for f in feats])
    th = truth.set_index("row_id").loc[ledger["row_id"], "theta_true"].to_numpy()
    assert abs((pt - th).std() - 1.0) < 0.2


def test_synthetic_label_constant(imp):
    assert imp("mootcourt.sources.synthetic").SYNTHETIC_LABEL == "synthetic"


def test_bad_config_raises(imp):
    syn = imp("mootcourt.sources.synthetic")
    with pytest.raises(ValueError):
        syn.generate(syn.SyntheticConfig(seed=1, n_tests=10, variants_per_test=5))
    with pytest.raises(ValueError):
        syn.generate(syn.SyntheticConfig(seed=1, n_tests=0))


def test_variants_in_a_test_share_a_topic_word(imp):
    """Retrieval can only leak same-test rows (and the leave-one-test-out rule only matters) if variants of one
    test are close in text, as real packages of one test are."""
    ledger, _ = _gen(imp, seed=15, n_tests=100, variants_per_test=3)
    heads = ledger["features_json"].map(lambda j: set(json.loads(j)["headline"].lower().split()))
    for _, idx in ledger.groupby("test_id").groups.items():
        common = set.intersection(*[heads[i] for i in idx])
        assert common, "variants of one test must share at least one headline word"
