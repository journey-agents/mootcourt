"""Extra checks for the aggregate table (builder additions): every table number is re-derivable."""
import numpy as np
import pandas as pd
import pytest

GATES = {"n_200": 200, "n_400": 400}


def _table(n_tests=60, per=3, seed=0):
    rng = np.random.default_rng(seed)
    n = n_tests * per
    p = rng.beta(2, 5, n)
    event = rng.random(n) < p
    y = rng.normal(0, 1, n)
    df = pd.DataFrame({
        "test_id": [f"t{i // per}" for i in range(n)], "row_id": [f"r{i}" for i in range(n)], "cell": np.where(np.arange(n) % 2, "a", "b"),
        "origin": "o", "rung": "P1", "y": y, "s": 1.0, "logscore": rng.normal(-2, 0.5, n), "crps": rng.random(n), "p_sig": p,
        "p_win": 0.5, "brier_event": (p - event) ** 2, "event": event, "direction_correct": rng.random(n) < 0.6,
        "lo80": -1.28, "hi80": 1.28, "lo90": -1.64, "hi90": 1.64, "abstain": rng.random(n) < 0.3, "abstain_reasons": "",
        "brier_base": (0.25 - event) ** 2, "brier_floor_row": 0.1, "dir_ceiling_row": 0.8})
    return df


def test_table_interval_equals_the_standalone_by_test_bootstrap(imp):
    hs = imp("mootcourt.harness_stats")
    df = _table()
    agg = hs.aggregate_scores(df, GATES, B=300, seed=4)
    row = agg[(agg["cell"] == "ALL") & (agg["rung"] == "P1")].iloc[0]
    iv = hs.bootstrap_by_test(df, "logscore", B=300, seed=4)
    assert (row["logscore"], row["logscore_lo"], row["logscore_hi"]) == pytest.approx((iv.estimate, iv.lo, iv.hi))


def test_brier_skill_uses_the_base_rate_column_and_nonabstained_rows_are_separate(imp):
    hs = imp("mootcourt.harness_stats")
    df = _table(seed=1)
    row = hs.aggregate_scores(df, GATES, B=100).query("cell == 'ALL'").iloc[0]
    assert row["brier_skill"] == pytest.approx(1 - df["brier_event"].mean() / df["brier_base"].mean())
    na = df[~df["abstain"]]
    assert row["n_nonabstained"] == len(na)
    assert row["logscore_nonabstained"] == pytest.approx(na["logscore"].mean())
    assert row["brier_floor"] == pytest.approx(0.1) and row["direction_ceiling"] == pytest.approx(0.8)
    assert row["abstention_rate"] == pytest.approx(df["abstain"].mean())


def test_ece_null_formula_matches_ece_of_the_same_outcomes(imp):
    hs = imp("mootcourt.harness_stats")
    p = np.random.default_rng(3).beta(2, 5, 400)
    rng = np.random.default_rng(9)
    e = (rng.random((100, p.size)) < p[None, :]).astype(float)
    ref = np.array([hs.ece(p, row) for row in e])
    null = hs.ece_null(p, draws=100, seed=9)
    np.testing.assert_allclose(null, ref, atol=1e-12)


def test_by_origin_gives_one_row_per_origin_and_rung(imp):
    hs = imp("mootcourt.harness_stats")
    df = pd.concat([_table(seed=2).assign(origin="o1"), _table(seed=3).assign(origin="o2")])
    out = hs.by_origin(df, "logscore", B=50)
    assert len(out) == 2 and set(out["origin"]) == {"o1", "o2"}
    assert (out["logscore_lo"] <= out["logscore"]).all() and (out["logscore"] <= out["logscore_hi"]).all()


def test_p0_rung_is_the_fallback_baseline_when_no_base_column(imp):
    hs = imp("mootcourt.harness_stats")
    df = _table(seed=5).drop(columns=["brier_base"])
    p0 = df.assign(rung="P0", brier_event=0.25)
    row = hs.aggregate_scores(pd.concat([p0, df]), GATES, B=50).query("cell == 'ALL' and rung == 'P1'").iloc[0]
    assert row["brier_skill"] == pytest.approx(1 - df["brier_event"].mean() / 0.25)
