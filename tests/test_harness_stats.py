"""T-014 contracts: bootstrap, calibration null, coverage, split-half, gates."""
import json
import time

import numpy as np
import pandas as pd
import pytest


def _clustered(n_tests=100, per=10, test_sd=1.0, row_sd=0.1, seed=0):
    rng = np.random.default_rng(seed)
    eff = rng.normal(0, test_sd, n_tests)
    rows = [(f"t{i}", eff[i] + rng.normal(0, row_sd)) for i in range(n_tests) for _ in range(per)]
    return pd.DataFrame(rows, columns=["test_id", "logscore"])


def test_bootstrap_by_test_interval_is_wider_than_by_row(imp):
    hs = imp("mootcourt.harness_stats")
    df = _clustered()
    res = hs.bootstrap_by_test(df, "logscore", B=500, seed=1)
    assert res.lo < df["logscore"].mean() < res.hi
    rng = np.random.default_rng(1)
    by_row = [df["logscore"].to_numpy()[rng.integers(0, len(df), len(df))].mean() for _ in range(500)]
    row_w = np.percentile(by_row, 95) - np.percentile(by_row, 5)
    assert (res.hi - res.lo) > 2.0 * row_w


def test_bootstrap_by_test_is_seeded_and_level_is_ninety(imp):
    hs = imp("mootcourt.harness_stats")
    df = _clustered(seed=3)
    a, b = hs.bootstrap_by_test(df, "logscore", B=200, seed=9), hs.bootstrap_by_test(df, "logscore", B=200, seed=9)
    assert (a.lo, a.hi) == (b.lo, b.hi)
    wide = hs.bootstrap_by_test(df, "logscore", B=200, seed=9, level=0.99)
    assert wide.hi - wide.lo > a.hi - a.lo


def test_bootstrap_by_test_validates_input(imp):
    hs = imp("mootcourt.harness_stats")
    with pytest.raises(KeyError):
        hs.bootstrap_by_test(_clustered(), "nope")
    with pytest.raises(ValueError):
        hs.bootstrap_by_test(pd.DataFrame({"test_id": [], "logscore": []}), "logscore")


def test_reliability_bins_and_ece_hand_example(imp):
    hs = imp("mootcourt.harness_stats")
    p = np.array([0.1, 0.1, 0.9, 0.9])
    e = np.array([0, 0, 1, 0])
    bins = hs.reliability_bins(p, e, n_bins=10)
    assert bins["n"].sum() == 4
    # bin 0.1: freq 0 vs p 0.1 (gap 0.1, weight 0.5); bin 0.9: freq 0.5 vs p 0.9 (gap 0.4, weight 0.5)
    assert hs.ece(p, e, n_bins=10) == pytest.approx(0.5 * 0.1 + 0.5 * 0.4)


def test_calibrated_predictor_lands_inside_the_central_90_percent_at_least_85_percent(imp):
    hs = imp("mootcourt.harness_stats")
    inside = 0
    for seed in range(40):
        rng = np.random.default_rng(seed)
        p = rng.beta(2, 5, 600)
        event = rng.random(600) < p
        pct = hs.ece_percentile(p, event, draws=300, seed=seed)
        inside += 5.0 <= pct <= 95.0
    assert inside / 40 >= 0.85, f"{inside}/40 inside the central 90 percent"


def test_miscalibrated_predictor_lands_above_the_99th_percentile(imp):
    hs = imp("mootcourt.harness_stats")
    rng = np.random.default_rng(0)
    p = rng.beta(2, 5, 1500)
    event = rng.random(1500) < np.clip(p + 0.2, 0, 1)         # systematically under-confident
    assert hs.ece_percentile(p, event, draws=500, seed=0) > 99.0


def test_ece_null_has_requested_size_and_is_nonnegative(imp):
    hs = imp("mootcourt.harness_stats")
    p = np.random.default_rng(1).beta(2, 5, 300)
    null = hs.ece_null(p, draws=500, seed=1)
    assert null.shape == (500,) and (null >= 0).all()
    with pytest.raises(ValueError):
        hs.ece_null(np.array([1.2]), draws=10)


def test_interval_coverage_binomial_tolerance_overall_and_per_cell(imp):
    hs = imp("mootcourt.harness_stats")
    rng = np.random.default_rng(2)
    n = 6000
    y = rng.normal(0, 1, n)
    cell = np.where(np.arange(n) % 2 == 0, "a", "b")
    z80, z90 = 1.2815515655, 1.6448536269
    df = pd.DataFrame({"cell": cell, "y": y, "lo80": -z80, "hi80": z80, "lo90": -z90, "hi90": z90})
    tab = hs.coverage_by_cell(df)
    def tol(p, m):
        return 3 * np.sqrt(p * (1 - p) / m)

    overall = tab[tab["cell"] == "ALL"].iloc[0]
    assert abs(overall["coverage_80"] - 0.80) < tol(0.8, n) and abs(overall["coverage_90"] - 0.90) < tol(0.9, n)
    for c in ("a", "b"):
        row = tab[tab["cell"] == c].iloc[0]
        assert abs(row["coverage_80"] - 0.80) < tol(0.8, n // 2)
    assert hs.interval_coverage(np.array([0.0, 5.0]), np.array([-1.0, -1.0]), np.array([1.0, 1.0])) == 0.5


def test_split_half_reports_gaps_per_cell(imp, tiny_ledger):
    hs = imp("mootcourt.harness_stats")
    ledger = tiny_ledger.copy()
    ledger["test_id"] = [f"t{i // 2}" for i in range(len(ledger))]
    out = hs.split_half(ledger)
    row = out["headline_only"]
    for k in ("mu_odd", "mu_even", "tau_odd", "tau_even", "mu_gap", "tau_gap"):
        assert k in row
    assert row["mu_gap"] == pytest.approx(abs(row["mu_odd"] - row["mu_even"]))
    assert row["mu_gap"] < 0.3 * 3.0 and row["tau_gap"] < 0.25 * 3.0


@pytest.mark.parametrize("n,d20,d10", [(199, False, False), (200, True, False), (399, True, False), (400, True, True)])
def test_gate_status_arithmetic_on_both_sides_of_n(imp, tmp_path, n, d20, d10):
    hs = imp("mootcourt.harness_stats")
    path = tmp_path / "gates.json"
    path.write_text(json.dumps({"n_200": 200, "n_400": 400, "label": "synthetic"}))
    gates = imp("mootcourt.simulate").load_gates(path)
    st = hs.gate_status(n, gates)
    assert st["n"] == n and st["decidable_at_0.20"] is d20 and st["decidable_at_0.10"] is d10
    if not d20:
        assert st["label"] == "undecidable at this n"
    else:
        assert "decidable" in st["label"] and "undecidable" not in st["label"]


def test_gate_status_never_hardcodes_200_or_400(imp):
    hs = imp("mootcourt.harness_stats")
    st = hs.gate_status(250, {"n_200": 300, "n_400": 700})
    assert st["decidable_at_0.20"] is False and st["label"] == "undecidable at this n"


def _scores(rows):
    return pd.DataFrame(rows)


def test_aggregate_scores_hand_example(imp):
    hs = imp("mootcourt.harness_stats")
    n = 4
    base = dict(test_id=[f"t{i}" for i in range(n)], cell="a", origin="o", y=1.0, s=1.0, direction_correct=[1, 1, 0, 1],
                lo80=-1, hi80=2, lo90=-2, hi90=3, abstain=[True, False, False, False], abstain_reasons=["support", "", "", ""],
                crps=0.5, p_win=0.5, event=[1, 0, 0, 1])
    p0 = _scores({**base, "rung": "P0", "logscore": [-1.0, -2.0, -3.0, -2.0], "p_sig": 0.5,
                  "brier_event": [0.25] * 4})
    p1 = _scores({**base, "rung": "P1", "logscore": [-1.0, -1.0, -1.0, -1.0], "p_sig": [0.9, 0.1, 0.1, 0.9],
                  "brier_event": [0.01, 0.01, 0.01, 0.01]})
    agg = hs.aggregate_scores(pd.concat([p0, p1]), gates={"n_200": 200, "n_400": 400})
    r1 = agg[(agg["cell"] == "a") & (agg["rung"] == "P1")].iloc[0]
    assert r1["n"] == 4 and r1["logscore"] == pytest.approx(-1.0)
    assert r1["brier_skill"] == pytest.approx(1 - 0.01 / 0.25)
    assert r1["direction_accuracy"] == pytest.approx(0.75)
    assert r1["abstention_rate"] == pytest.approx(0.25)
    assert r1["decidable"] == "undecidable at this n"
    assert {"logscore_lo", "logscore_hi", "coverage_80", "coverage_90", "crps"} <= set(agg.columns)
    assert r1["logscore_lo"] <= r1["logscore"] <= r1["logscore_hi"]


def test_abstention_summary_by_trigger(imp):
    hs = imp("mootcourt.harness_stats")
    df = _scores({"cell": ["a"] * 4, "rung": "P1", "abstain": [True, True, False, True],
                  "abstain_reasons": ["support", "support,novelty", "", "instability"]})
    tab = hs.abstention_summary(df).set_index("cell")
    row = tab.loc["a"]
    assert row["rate"] == pytest.approx(0.75)
    assert (row["support"], row["novelty"], row["reliability"], row["instability"]) == (2, 1, 0, 1)


def test_circularity_note_is_stated(imp):
    note = imp("mootcourt.harness_stats").CIRCULARITY_NOTE
    assert "observed estimate with known standard error" in note
    assert "not against the unknown true effect" in note


@pytest.mark.slow
def test_aggregation_of_20000_rows_with_B500_under_30_seconds(imp):
    rng = np.random.default_rng(0)
    n = 20000
    df = pd.DataFrame({"test_id": [f"t{i // 4}" for i in range(n)], "cell": "a", "rung": "P1",
                       "origin": "o", "logscore": rng.normal(-2, 1, n), "crps": rng.random(n), "p_sig": rng.random(n),
                       "p_win": rng.random(n), "brier_event": rng.random(n), "event": rng.random(n) < 0.3,
                       "direction_correct": rng.random(n) < 0.6, "y": rng.normal(0, 1, n), "s": 1.0,
                       "lo80": -1.3, "hi80": 1.3, "lo90": -1.7, "hi90": 1.7, "abstain": False, "abstain_reasons": ""})
    t = time.perf_counter()
    imp("mootcourt.harness_stats").aggregate_scores(df, gates={"n_200": 200, "n_400": 400}, B=500)
    assert time.perf_counter() - t < 30
