"""T-007 contracts: P2 weighted precedents."""
import time

import numpy as np
import pytest

# Hand-computed 5-row example (spec section 8).
K = np.array([1.0, 0.5, 0.25, 0.8, 0.1])
Y = np.array([4.0, 2.0, 0.0, 3.0, 6.0])
S = np.array([1.0, 2.0, 1.0, 0.5, 2.0])
TAU, MU, LAM, TAU_RES2 = 1.0, 2.0, 0.6, 0.5
# w = K / (S^2 + TAU^2) = [0.5, 0.1, 0.125, 0.64, 0.02], sum w = 1.385
EXPECTED = {
    "m": 3.0613718411552346,
    "v_m": 0.5709705587196496,
    "n_eff": 2.7977757520510487,
    "theta_hat": 2.636823104693141,
    "v": 1.0425823352317898,
}


def test_moments_match_hand_computation(imp):
    p2 = imp("mootcourt.predictors.p2")
    got = p2.p2_moments(K, Y, S, tau=TAU, mu=MU, lam=LAM, tau_res2=TAU_RES2)
    for name, want in EXPECTED.items():
        assert getattr(got, name) == pytest.approx(want, rel=1e-9), name


def test_moments_lambda_zero_returns_the_prior(imp):
    got = imp("mootcourt.predictors.p2").p2_moments(K, Y, S, tau=TAU, mu=MU, lam=0.0, tau_res2=TAU_RES2)
    assert got.theta_hat == pytest.approx(MU) and got.v == pytest.approx(TAU ** 2)


def test_moments_reject_empty_or_negative_weights(imp):
    p2 = imp("mootcourt.predictors.p2")
    with pytest.raises(ValueError):
        p2.p2_moments(np.array([]), np.array([]), np.array([]), tau=1.0, mu=0.0, lam=0.5, tau_res2=0.0)
    with pytest.raises(ValueError):
        p2.p2_moments(-K, Y, S, tau=TAU, mu=MU, lam=LAM, tau_res2=TAU_RES2)


def _fit_pair(imp, ledger, **p2kw):
    p2kw.setdefault("guard", None)     # the selection rules are tested here; the admission guard (T-042) is tested in test_p2_guard.py
    features = imp("mootcourt.features")
    p1m = imp("mootcourt.predictors.p1")
    p2m = imp("mootcourt.predictors.p2")
    space = features.FeatureSpace.fit(ledger)
    p1 = p1m.P1Predictor().fit(ledger)
    p2 = p2m.P2Predictor().fit(ledger, space, p1, **p2kw)
    return space, p1, p2


def _x(space, ledger, i=0):
    return space.transform(ledger.iloc[[i]])[0]


def test_lambda_zero_equals_p1_grid(imp, make_synth, origin):
    ledger, _ = make_synth(seed=51, n_tests=250, variants_per_test=2, text_effect_strength=2.0)
    space, p1, p2 = _fit_pair(imp, ledger, lambda_override=0.0)
    x = _x(space, ledger)
    a = p1.predict(x, 1.5, "headline_only", origin)
    b = p2.predict(x, 1.5, "headline_only", origin)
    np.testing.assert_allclose(a.theta, b.theta, atol=1e-12, rtol=0)
    np.testing.assert_allclose(a.pmf, b.pmf, atol=1e-12, rtol=0)


def test_lambda_chosen_from_the_grid_and_tau_res_floored(imp, make_synth):
    ledger, _ = make_synth(seed=52, n_tests=250, variants_per_test=2)
    _, _, p2 = _fit_pair(imp, ledger)
    grid = [round(i / 10, 1) for i in range(11)]
    for cell, lam in p2.lambda_by_cell.items():
        assert round(lam, 1) in grid
        assert p2.tau_res2_by_cell[cell] >= 0.0


def test_text_signal_makes_p2_beat_p1_out_of_origin(imp, make_synth, origin):
    train, _ = make_synth(seed=53, n_tests=500, variants_per_test=1, text_effect_strength=4.0,
                          cell_params={"headline_only": (0.0, 1.0)}, s_scale=1.0)
    test, _ = make_synth(seed=54, n_tests=300, variants_per_test=1, text_effect_strength=4.0,
                         cell_params={"headline_only": (0.0, 1.0)}, s_scale=1.0)
    space, p1, p2 = _fit_pair(imp, train)
    X = space.transform(test)
    ls1 = np.mean([p1.predict(X[i], r.s, r.cell, origin).logscore(r.y, r.s) for i, r in enumerate(test.itertuples())])
    ls2 = np.mean([p2.predict(X[i], r.s, r.cell, origin).logscore(r.y, r.s) for i, r in enumerate(test.itertuples())])
    assert ls2 > ls1 + 0.02


def test_no_text_signal_keeps_lambda_small_and_p2_not_worse(imp, make_synth, origin):
    kw = dict(variants_per_test=1, text_effect_strength=0.0, cell_params={"headline_only": (0.0, 1.0)}, s_scale=1.0)
    train, _ = make_synth(seed=55, n_tests=500, **kw)
    test, _ = make_synth(seed=56, n_tests=300, **kw)
    space, p1, p2 = _fit_pair(imp, train)
    assert p2.lambda_by_cell["headline_only"] <= 0.3
    X = space.transform(test)
    ls1 = np.mean([p1.predict(X[i], r.s, r.cell, origin).logscore(r.y, r.s) for i, r in enumerate(test.itertuples())])
    ls2 = np.mean([p2.predict(X[i], r.s, r.cell, origin).logscore(r.y, r.s) for i, r in enumerate(test.itertuples())])
    assert ls2 > ls1 - 0.01


def test_leave_one_test_out_blocks_same_test_leakage(imp, make_synth):
    """Rows in one test share a test-level effect and similar text. Leaving out one row at a time
    (leaky) rewards lambda near 1; leaving out the whole test must not."""
    kw = dict(seed=57, n_tests=300, variants_per_test=4, test_effect_sd=2.0, text_effect_strength=0.0,
              cell_params={"headline_only": (0.0, 0.3)}, s_scale=0.5)
    ledger, _ = make_synth(**kw)
    _, _, honest = _fit_pair(imp, ledger, selection="loto")
    _, _, leaky = _fit_pair(imp, ledger, selection="loto", leave_out="row")
    assert leaky.lambda_by_cell["headline_only"] > honest.lambda_by_cell["headline_only"]


def test_top_precedents_and_p_sig_without(imp, make_synth, origin):
    ledger, _ = make_synth(seed=58, n_tests=250, variants_per_test=2, text_effect_strength=2.0)
    # stub edit (T-007): lambda_override=0.5. At this seed the cell's out-of-origin curve is flat or falling in
    # lambda (precedents add nothing), so the honest choice is lambda 0 and dismissing precedents changes nothing.
    space, _, p2 = _fit_pair(imp, ledger, lambda_override=0.5)
    x = _x(space, ledger, 3)
    top = p2.top_precedents(x, "headline_only", origin, k=5)
    assert {"row_id", "weight", "y", "s"} <= set(top.columns)
    assert len(top) == 5 and top["weight"].is_monotonic_decreasing
    full = p2.p_sig_without(x, "headline_only", origin, 1.5, dismissed_row_ids=())
    assert full == pytest.approx(p2.predict(x, 1.5, "headline_only", origin).p_sig(1.5), abs=1e-9)
    with_drop = p2.p_sig_without(x, "headline_only", origin, 1.5, dismissed_row_ids=tuple(top["row_id"]))
    assert 0.0 <= with_drop <= 1.0 and with_drop != full


def test_neighbor_state_fields(imp, make_synth, origin):
    ledger, _ = make_synth(seed=59, n_tests=200, variants_per_test=2)
    space, _, p2 = _fit_pair(imp, ledger)
    st = p2.neighbor_state(_x(space, ledger), "headline_only", origin)
    n = len(st.row_ids)
    assert 0 < n <= 1000
    for name in ("kernel", "y", "s", "test_ids"):
        assert len(getattr(st, name)) == n
    assert st.tau > 0 and 0.0 <= st.lam <= 1.0


def test_p_sig_from_state_matches_moments(imp):
    p2 = imp("mootcourt.predictors.p2")
    st = p2.NeighborState(row_ids=tuple(f"r{i}" for i in range(5)), kernel=K, y=Y, s=S,
                          test_ids=tuple(f"t{i}" for i in range(5)), mu=MU, tau=TAU, lam=LAM, tau_res2=TAU_RES2)
    from scipy import stats
    s_star = 1.0
    want = stats.norm.sf(1.96 * s_star, EXPECTED["theta_hat"], np.sqrt(EXPECTED["v"] + s_star ** 2))
    assert p2.p_sig_from_state(st, s_star) == pytest.approx(want, rel=1e-9)


def test_truncated_neighbors_agree_with_exact(imp, make_synth, origin):
    ledger, _ = make_synth(seed=60, n_tests=1000, variants_per_test=2, text_effect_strength=2.0)
    features = imp("mootcourt.features")
    p1m, p2m = imp("mootcourt.predictors.p1"), imp("mootcourt.predictors.p2")
    space = features.FeatureSpace.fit(ledger)
    p1 = p1m.P1Predictor().fit(ledger)
    trunc = p2m.P2Predictor().fit(ledger, space, p1, top_m=200)
    exact = p2m.P2Predictor().fit(ledger, space, p1, top_m=None)
    X = space.transform(ledger.iloc[:15])
    for x in X:
        a = trunc.predict(x, 1.5, "headline_only", origin).p_sig(1.5)
        b = exact.predict(x, 1.5, "headline_only", origin).p_sig(1.5)
        assert abs(a - b) < 0.01


@pytest.mark.slow
def test_fit_15000_rows_three_cells_under_90_seconds(imp, make_synth):
    ledger, _ = make_synth(seed=61, n_tests=7500, variants_per_test=2,
                           cell_params={"headline_only": (1.0, 2.0), "image_only": (0.0, 2.0), "both": (2.0, 2.0)})
    assert len(ledger) >= 15000
    t = time.perf_counter()
    _fit_pair(imp, ledger)
    assert time.perf_counter() - t < 90
