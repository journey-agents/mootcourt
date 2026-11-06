"""X10 (paper v2 plan): the test-and-roll decision problem, the three sizing rules, the nonparametric world and the evaluation."""

import math

import numpy as np
import pandas as pd
import pytest
from scipy import special

from mootcourt import sizing as sz


def test_expected_gain_matches_a_simulation():
    rng = np.random.default_rng(0)
    c, N, n = 0.03, 40000.0, 3000
    theta_pp = np.array([-0.4, 0.0, 0.3, 0.8])
    w = np.array([0.3, 0.2, 0.3, 0.2])
    exact = sz.expected_gain(theta_pp, w, n, N, c)[0]
    draws = 400000
    th = rng.choice(theta_pp, size=draws, p=w) / 100.0
    hat = th + rng.normal(0, sz.se_of_difference(n, c), draws)
    sim = np.mean(n * th + (N - 2 * n) * th * (hat > 0))
    assert exact == pytest.approx(sim, abs=4 * 0.1 * N * 0.008 / math.sqrt(draws) + 0.05)


def test_numerical_optimum_matches_the_closed_form_for_a_normal_prior():
    c, N = 0.04, 2.0e6
    sigma_arm = 0.0015  # prior sd of one arm's mean rate
    s_unit = math.sqrt(c * (1 - c))
    theta, w = sz.t_prior_grid(0.0, math.sqrt(2) * sigma_arm * 100.0, math.inf)  # the difference of two arms: sd sqrt(2) sigma
    n_num = sz.optimal_size(theta, w, N, c)
    n_closed = sz.feige_mcdowell_size(N, s_unit / sigma_arm)
    assert n_num == pytest.approx(n_closed, rel=0.03)
    # and it really is the maximum of the expected gain on the grid
    grid = sz.size_grid(N)
    g = sz.expected_gain(theta, w, grid, N, c)
    assert sz.expected_gain(theta, w, n_num, N, c)[0] == pytest.approx(g.max())


def test_regret_anchors_and_the_oracle():
    theta = np.array([-0.5, 0.2, 0.6])
    w = np.array([0.4, 0.3, 0.3])
    N, c = 1e5, 0.02
    assert sz.oracle_gain(theta, w, N) == pytest.approx(N * (0.3 * 0.002 + 0.3 * 0.006))
    r_small, r_mid, r_all = (sz.regret(theta, w, n, N, c)[0] for n in (1, 5000, N / 2))
    assert r_mid < r_small and r_mid < r_all and min(r_small, r_mid, r_all) > 0  # some testing beats none and beats testing everything
    assert sz.regret(theta, w, N / 2, N, c)[0] == pytest.approx(sz.oracle_gain(theta, w, N) - (N / 2) * float(np.sum(w * theta / 100)))


def test_base_rate_prior_reproduces_the_base_rate():
    for base, s in ((0.09, 0.3), (0.2, 0.5), (0.05, 0.1)):
        tau = sz.base_rate_tau(base, s)
        assert tau > 0
        assert special.ndtr(-1.96 * s / math.sqrt(tau**2 + s**2)) == pytest.approx(base, abs=1e-9)
    assert sz.base_rate_tau(0.02, 0.3) == 0.0 and sz.base_rate_tau(0.6, 0.3) == 0.0 and sz.base_rate_tau(0.0, 0.3) == 0.0
    assert sz.base_rate_rule_size(0.02, 0.3, 1e5, 0.03) == 1


def test_power_rule_has_the_stated_power():
    c = 0.03
    n = sz.power_rule_size(c)
    se = float(sz.se_of_difference(n, c))
    delta = 0.10 * c
    power = special.ndtr(delta / se - 1.959964) + special.ndtr(-delta / se - 1.959964)
    assert power == pytest.approx(0.80, abs=0.005)


def test_npmle_recovers_a_two_point_world():
    rng = np.random.default_rng(1)
    n = 3000
    theta = rng.choice([0.0, 1.0], size=n, p=[0.7, 0.3])
    s = rng.uniform(0.2, 0.4, n)
    y = theta + rng.normal(0, s)
    g, w = sz.npmle(y, s)
    assert w.sum() == pytest.approx(1.0) and g.min() <= 0 <= g.max()
    mean = float(np.sum(g * w))
    assert mean == pytest.approx(0.3, abs=0.05)
    assert float(np.sum(w[g > 0.5])) == pytest.approx(0.3, abs=0.08)


def test_a_misspecified_prior_costs_more_than_the_matched_one():
    # the world is wide; a prior that is far too narrow picks a size that is too large, one that is far too wide too small
    c, N = 0.03, 4.0e5
    world, ww = sz.t_prior_grid(0.0, 0.6, math.inf)
    narrow, wn = sz.t_prior_grid(0.0, 0.06, math.inf)
    n_world = sz.optimal_size(world, ww, N, c)
    n_narrow = sz.optimal_size(narrow, wn, N, c)
    assert n_narrow > n_world
    assert sz.regret(world, ww, n_world, N, c)[0] < sz.regret(world, ww, n_narrow, N, c)[0]


def _small_run():
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.sources import synthetic as synth

    led = synth.generate(synth.SyntheticConfig(seed=21, n_tests=600, variants_per_test=3))[0].copy()
    led["source"] = "upworthy"
    import json

    rng = np.random.default_rng(3)
    feats = []
    for j in led["features_json"]:
        f = json.loads(j)
        f["post_launch"] = {"ctr_ref": float(rng.choice([0.02, 0.03]))}
        feats.append(json.dumps(f))
    led["features_json"] = feats
    led["n_ref"] = (3000 + rng.integers(0, 1500, len(led))).astype("int64")
    led["n_var"] = led["n_ref"]
    scores = rolling_origin(
        led, {"P0": default_rungs("synthetic", led)["P0"], "P1": default_rungs("synthetic", led)["P1"]}, quarterly_origins(led), source="synthetic"
    )
    return led, scores


def test_the_evaluation_has_the_structure_the_design_note_names():
    led, scores = _small_run()
    out = sz.evaluate_test_and_roll(led, scores, multiples=(5, 20), B=10, min_rows=40)
    assert out is not None and set(out["by_audience"]) == {"5", "20"}
    a = out["by_audience"]["20"]
    assert set(a["pooled_relative_regret"]) == {"x1", "x0.67", "x1.5"}
    for world in a["pooled_relative_regret"].values():
        assert set(world) == {"prior", "base_rate", "power", "never_test", "test_everything"}
        assert 0 <= world["prior"] <= 1.0 + 1e-9 and world["never_test"] == pytest.approx(1.0)  # never testing forgoes the whole oracle gain
    d = a["paired_differences"]
    assert set(d) == {"prior_minus_base_rate", "prior_minus_power", "base_rate_minus_power"} and d["prior_minus_power"]["family_size"] == 2
    c = out["claim"]
    assert set(c["feasibility_failures"]) == {
        "units_after_the_date_rule",
        "units_with_100_or_more_scored_rows",
        "fewer_than_half_of_units_have_100_rows",
        "sizes_within_10_percent_in_over_80_percent_of_units",
    }
    assert c["verdict"] in {
        "not evaluated",
        "evaluated; no measurable sizing advantage",
        "evaluated; the prior rule's regret differs from a simpler rule's",
    }
    assert (c["verdict"] == "not evaluated") == c["not_evaluated"] and "horizon_note" in out
    for u in a["units_table"]:
        assert 1 <= u["sizes"]["prior"] <= u["cap"] and u["N"] == pytest.approx(20 * 2 * u["median_exposure"])
    # the same seed gives the same figures
    again = sz.evaluate_test_and_roll(led, scores, multiples=(5, 20), B=10, min_rows=40)
    assert again["by_audience"]["20"]["relative_regret_with_interval"] == a["relative_regret_with_interval"]


def test_units_with_too_few_rows_are_listed_and_left_out():
    led, scores = _small_run()
    out = sz.evaluate_test_and_roll(led, scores, multiples=(20,), B=5, min_rows=10**6)
    assert out["by_audience"] == {} and len(out["units_skipped"]) > 0 and out["claim"]["verdict"] == "not evaluated"


def test_assurance_by_exposure_bins():
    rng = np.random.default_rng(5)
    n = 3000
    expo = rng.uniform(1000, 9000, n)
    p = np.full(n, 0.1)
    e = (rng.random(n) < 0.05 + 0.1 * (expo - 1000) / 8000).astype(float)  # the realized rate rises with exposure, the forecast does not
    sc = pd.DataFrame({"rung": "P1", "cell": "a", "test_id": np.arange(n) // 2, "exposure": expo, "p_sig": p, "event": e})
    out = sz.sizing_assurance(sc, rungs=("P1",), B=100)["rungs"]["P1"]["ALL"]
    gaps = [b["gap"] for b in out["bins"]]
    assert len(gaps) == 5 and gaps[0] < 0 < gaps[-1]
    s = out["slope_gap_on_standardized_log_exposure"]
    assert s["estimate"] > 0.02 and s["lo"] > 0
    assert sz.sizing_assurance(sc.drop(columns="exposure")) is None
