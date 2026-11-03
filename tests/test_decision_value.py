"""T-015 contracts: decision value."""
import numpy as np
import pandas as pd
import pytest


def _scores(values, p_win, origin="2014-01-01", tests_per_contrast=1):
    rows = []
    for i, (v, p) in enumerate(zip(values, p_win)):
        for j in range(tests_per_contrast):
            rows.append({"test_id": f"t{i}", "row_id": f"t{i}:{j}", "origin": origin, "rung": "P2", "y": v, "p_win": p})
    return pd.DataFrame(rows)


def _row(tab, policy, origin="2014-01-01"):
    return tab[(tab["policy"] == policy) & (tab["origin"] == origin)].iloc[0]


def test_k_is_a_quarter_of_tests_rounded_half_up_with_floor_of_one(imp):
    dv = imp("mootcourt.decision_value")
    assert [dv.budget_k(n) for n in (1, 2, 3, 4, 10, 12)] == [1, 1, 1, 1, 3, 3]


def test_hand_example_oracle_and_p_win_policies(imp):
    dv = imp("mootcourt.decision_value")
    # 8 tests, K = 2. Values (best positive lift): 8,7,6,5,4,3,2,1; p_win ranks the top two correctly
    values = [8, 7, 6, 5, 4, 3, 2, 1]
    tab = dv.decision_value(_scores(values, p_win=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]))
    total = sum(values)
    assert _row(tab, "oracle")["captured_fraction"] == pytest.approx(15 / total)
    assert _row(tab, "p_win")["captured_fraction"] == pytest.approx(15 / total)
    assert _row(tab, "p_win")["regret"] == pytest.approx(0.0)
    assert _row(tab, "random")["captured_fraction"] < _row(tab, "oracle")["captured_fraction"]
    assert _row(tab, "oracle")["K"] == 2


def test_wrong_ranking_has_positive_regret_and_oracle_is_best(imp):
    dv = imp("mootcourt.decision_value")
    values = [8, 7, 6, 5, 4, 3, 2, 1]
    tab = dv.decision_value(_scores(values, p_win=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]))
    assert _row(tab, "p_win")["captured_fraction"] == pytest.approx((2 + 1) / sum(values))
    assert _row(tab, "p_win")["regret"] == pytest.approx(15 - 3)
    best = max(tab["captured_fraction"])
    assert _row(tab, "oracle")["captured_fraction"] == pytest.approx(best)


def test_test_value_is_best_positive_lift_among_contrasts_and_policy_is_max_p_win(imp):
    dv = imp("mootcourt.decision_value")
    df = pd.DataFrame({
        "test_id": ["a", "a", "b", "b", "c", "d"], "row_id": list("123456"), "origin": "o", "rung": "P2",
        "y": [-5.0, 2.0, 10.0, 9.0, -3.0, 4.0], "p_win": [0.1, 0.9, 0.2, 0.3, 0.5, 0.4]})
    tab = dv.decision_value(df)
    # values: a=2, b=10, c=0 (no positive lift), d=4 ; total 16 ; K=1
    assert _row(tab, "oracle", "o")["captured_fraction"] == pytest.approx(10 / 16)
    assert _row(tab, "p_win", "o")["captured_fraction"] == pytest.approx(2 / 16)   # test a has the max p_win 0.9


def test_perfect_sign_knowledge_ties_the_oracle(imp):
    dv = imp("mootcourt.decision_value")
    values = [5, 4, 3, 2, 1, 0.5, 0.25, 0.1]
    tab = dv.decision_value(_scores(values, p_win=list(np.linspace(0.99, 0.5, 8))))
    assert _row(tab, "p_win")["captured_fraction"] == pytest.approx(_row(tab, "oracle")["captured_fraction"])


def test_random_policy_is_near_k_over_n_tests(imp):
    dv = imp("mootcourt.decision_value")
    rng = np.random.default_rng(0)
    values = rng.uniform(0.5, 5.0, 40)
    tab = dv.decision_value(_scores(values, p_win=rng.random(40)), draws=200, seed=0)
    assert abs(_row(tab, "random")["captured_fraction"] - 10 / 40) < 0.06


def test_zero_lift_period_and_ties_do_not_divide_by_zero(imp):
    dv = imp("mootcourt.decision_value")
    tab = dv.decision_value(_scores([-1, -2, -3, -4], p_win=[0.5, 0.5, 0.5, 0.5]))
    for policy in ("random", "p_win", "oracle"):
        r = _row(tab, policy)
        assert r["captured_fraction"] == 0.0 and r["regret"] == 0.0
    tie = dv.decision_value(_scores([3, 3, 3, 3], p_win=[0.5] * 4))
    assert np.isfinite(tie["captured_fraction"]).all()


def test_periods_are_separate_and_an_overall_row_is_given(imp):
    dv = imp("mootcourt.decision_value")
    a = _scores([8, 7, 6, 5], [0.9, 0.8, 0.7, 0.6], origin="o1")
    b = _scores([1, 2, 3, 4], [0.9, 0.8, 0.7, 0.6], origin="o2").assign(test_id=lambda d: "u" + d["test_id"],
                                                                         row_id=lambda d: "u" + d["row_id"])
    tab = dv.decision_value(pd.concat([a, b]))
    assert set(tab["origin"]) == {"o1", "o2", "ALL"}


def test_decision_value_is_not_folded_into_calibration_columns(imp):
    tab = imp("mootcourt.decision_value").decision_value(_scores([1, 2, 3, 4], [0.4, 0.3, 0.2, 0.1]))
    assert not ({"logscore", "brier_skill", "ece"} & set(tab.columns))
