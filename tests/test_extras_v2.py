"""Paper v2 plan, X1 and X4 to X9: the analyses of ``mootcourt.extras_v2`` on small controlled inputs and on a small synthetic backtest."""

import json

import numpy as np
import pandas as pd
import pytest

from mootcourt import extras_v2 as ex
from mootcourt import harness_stats as hs


@pytest.fixture(scope="module")
def backtest_scores():
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.sources import synthetic as synth

    ledger = synth.generate(synth.SyntheticConfig(seed=11, n_tests=320, variants_per_test=3))[0]
    rungs = default_rungs("synthetic", ledger, ["text_lr"], baselines=False)
    return rolling_origin(ledger, rungs, quarterly_origins(ledger), source="synthetic")


# ------------------------------------------------------------------------------------------------------------------------------- X1
def test_compare_reports_ignores_model_ids_and_flags_a_changed_leaf():
    a = {"header": {"model_id": "m1", "created_at": "t1", "n": 5}, "tables": {"aggregate": [{"x": 1.0, "y": [0.5, 0.25]}]}}
    b = json.loads(json.dumps(a))
    b["header"]["model_id"], b["header"]["created_at"] = "m2", "t2"
    r = ex.compare_reports(a, b)
    assert r["leaves_different"] == 0 and r["leaves_compared"] == 4
    b["tables"]["aggregate"][0]["y"][1] = 0.26
    r = ex.compare_reports(a, b)
    assert r["leaves_different"] == 1 and r["first_differences"][0]["leaf"].endswith("y[1]")
    b["tables"]["aggregate"][0]["z"] = 1.0
    assert ex.compare_reports(a, b)["leaves_only_in_second"] == 1
    assert ex.compare_reports(a, {"header": a["header"], "tables": {"aggregate": [{"x": 1.0 + 1e-12, "y": [0.5, 0.25]}]}})["leaves_different"] == 0


def _report(rung_rows):
    return {"header": {"variant": None}, "tables": {"aggregate": [{"cell": "ALL", "rung": r, **v} for r, v in rung_rows.items()]}}


def test_randomization_window_summary_counts_the_rule_and_the_ablation(tmp_path):
    from mootcourt.ledger import write_ledger
    from mootcourt.sources import synthetic as synth

    led = synth.generate(synth.SyntheticConfig(seed=3, n_tests=40, variants_per_test=2))[0].copy()
    led["source"] = "upworthy"
    led["row_id"] = led["row_id"].str.replace("synthetic", "upworthy")
    abl = led.copy()
    flagged = led["test_id"].isin(sorted(led["test_id"].unique())[:4])
    led.loc[flagged, "status"] = "imbalance_flag"
    reports = tmp_path / "reports"
    reports.mkdir()
    abl_dir = tmp_path / "abl"
    write_ledger(abl, abl_dir / "data" / "ledger" / "ledger.parquet")
    row = {"brier_skill": 0.1, "logscore": -1.0, "n": 10}
    (reports / "backtest-upworthy-S.json").write_text(json.dumps(_report({"P1": row})))
    (abl_dir / "backtest-upworthy-T.json").write_text(json.dumps(_report({"P1": row})))
    r7 = tmp_path / "run7.json"
    r7.write_text(json.dumps(_report({"P1": row})))
    out = ex.randomization_window_summary(reports, "upworthy", "S", led, ablation_dir=abl_dir, run7_report=r7)
    assert out["rows_changed_by_the_rule"] == int(flagged.sum()) and out["tests_with_a_changed_row"] == 4
    assert out["rows_changed_from_admitted"] == out["rows_changed_by_the_rule"]
    assert out["admitted_rows"]["ablation"] - out["admitted_rows"]["main"] == int(flagged.sum())
    assert out["ablation_vs_run7"]["report_leaves"]["leaves_different"] == 0
    assert out["headline"]["main"]["P1"]["brier_skill"] == 0.1
    assert ex.randomization_window_summary(reports, "asos", "S", led) is None


# ------------------------------------------------------------------------------------------------------------------------- X2 and X3
def test_effect_scale_choices_names_the_runs_where_p1_reverses(tmp_path):
    ab = tmp_path / "ablations"
    ab.mkdir()
    good = {
        "P1": {
            "auc_event": 0.55,
            "auc_event_lo": 0.53,
            "auc_event_hi": 0.57,
            "auc_event_within": 0.53,
            "auc_event_within_lo": 0.51,
            "auc_event_within_hi": 0.55,
            "brier_skill": 0.002,
            "brier_skill_lo": -0.001,
            "brier_skill_hi": 0.005,
            "event_rate": 0.09,
        }
    }
    bad = {
        "P1": {
            "auc_event": 0.26,
            "auc_event_lo": 0.25,
            "auc_event_hi": 0.28,
            "auc_event_within": 0.16,
            "auc_event_within_lo": 0.15,
            "auc_event_within_hi": 0.17,
            "brier_skill": -0.1,
            "brier_skill_lo": -0.11,
            "brier_skill_hi": -0.09,
            "event_rate": 0.05,
        }
    }
    (tmp_path / "backtest-upworthy-S.json").write_text(json.dumps(_report(good)))
    (ab / "backtest-upworthy-S--effect-scale-relative+s-star-realized.json").write_text(json.dumps(_report(bad)))
    (ab / "backtest-upworthy-S--effect-scale-relative.json").write_text(json.dumps(_report(good)))
    (ab / "backtest-upworthy-S--s-star-realized.json").write_text(json.dumps(_report(bad)))
    out = ex.effect_scale_choices(tmp_path, "upworthy", "S")
    assert out["runs_where_p1_auc_interval_is_below_half"] == ["cautionary", "absolute_realized"]
    assert out["runs"]["main"]["p1_ranking"]["auc_event_below_half"] is False
    assert ex.effect_scale_choices(tmp_path / "nowhere", "upworthy", "S") is None and ex.effect_scale_choices(tmp_path, "asos", "S") is None


def test_exposure_fixed_reports_the_change_and_the_constant_forecasts(tmp_path):
    ab = tmp_path / "ablations"
    ab.mkdir()
    main = _report({"P1": {"auc_event_within": 0.53, "brier_skill": 0.002}})
    fixed = _report({"P1": {"auc_event_within": 0.50, "brier_skill": 0.001}})
    (tmp_path / "backtest-upworthy-S.json").write_text(json.dumps(main))
    (ab / "backtest-upworthy-S--exposure-cell-median.json").write_text(json.dumps(fixed))
    rows = lambda p: pd.DataFrame({"origin": ["o"] * 4, "cell": ["a", "a", "b", "b"], "rung": ["P1"] * 4, "p_sig": p, "exposure": [1, 2, 3, 3]})  # noqa: E731
    rows([0.1, 0.2, 0.3, 0.3]).to_parquet(tmp_path / "scores-upworthy-S.parquet")
    rows([0.1, 0.1, 0.3, 0.3]).to_parquet(ab / "scores-upworthy-S--exposure-cell-median.parquet")
    out = ex.exposure_fixed(tmp_path, "upworthy", "S")
    assert out["by_cell"]["ALL"]["fixed_minus_main"]["P1"]["auc_event_within"] == pytest.approx(-0.03)
    c = out["p_sig_constant_within_origin_and_cell"]
    assert c["main"]["P1"]["strata_with_one_value"] == 1 and c["fixed"]["P1"]["strata_with_one_value"] == 2
    assert out["auc_event_within_ties_exact"] == {}  # this toy table has no event column


# ------------------------------------------------------------------------------------------------------------------------------- X4
def _ctr_ledger(rng, scale_mixture: bool, n=1500):
    ctr = rng.choice([0.01, 0.04], size=n)
    s_pp = 100 * np.sqrt(2 * ctr * (1 - ctr) / 8000)
    theta_rel = rng.normal(0, 0.15, n) if scale_mixture else rng.standard_t(3, n) * 0.07
    y = 100 * ctr * theta_rel + rng.normal(0, s_pp)
    feats = [json.dumps({"post_launch": {"ctr_ref": float(c)}}) for c in ctr]
    return pd.DataFrame({"status": "admitted", "cell": "headline_only", "y": y, "s": s_pp, "features_json": feats})


def test_prior_family_scale_separates_a_level_mixture_from_heavy_tails():
    mix = ex.prior_family_scale(_ctr_ledger(np.random.default_rng(1), True), "upworthy")["by_cell"]["ALL"]
    assert mix["pp"]["gain_total"] > 3.0  # in percentage points the t prior wins ...
    assert mix["relative"]["gain_total"] < 0.3 * mix["pp"]["gain_total"]  # ... and on the standardized effect the gain is mostly gone
    assert mix["level_bins"]["share_of_t_gain_reached_by_normal_by_level"] > 0.6
    tail = ex.prior_family_scale(_ctr_ledger(np.random.default_rng(2), False), "upworthy")["by_cell"]["ALL"]
    assert tail["relative"]["gain_total"] > 20.0  # genuinely heavy-tailed effects keep their gain on the standardized scale
    assert tail["relative"]["gain_total"] / tail["pp"]["gain_total"] > 3 * mix["relative"]["gain_total"] / mix["pp"]["gain_total"]
    assert tail["level_bins"]["gain_t_within_level_bins_over_normal_within_level_bins"] > 20.0  # heavy tails remain inside a level
    assert mix["level_bins"]["gain_t_within_level_bins_over_normal_within_level_bins"] < 0.2 * mix["pp"]["gain_total"]
    assert ex.prior_family_scale(_ctr_ledger(np.random.default_rng(1), True), "asos") is None


# ------------------------------------------------------------------------------------------------------------------------------- X5
def _rank_scores(rng, n_tests=60, origins=3):
    rows = []
    for o in range(origins):
        for t in range(n_tests):
            arms = int(rng.integers(1, 4))
            value = float(rng.exponential(0.4))
            for a in range(arms):
                y = value if a == 0 else -abs(rng.normal(0, 0.1))
                rid = f"r{o}-{t}-{a}"
                for rung, p in (("A", value + rng.normal(0, 0.01)), ("B", rng.random()), ("P1", rng.random())):
                    rows.append(
                        {
                            "origin": pd.Timestamp("2014-01-01", tz="UTC") + pd.Timedelta(days=90 * o),
                            "test_id": f"{o}-{t}",
                            "row_id": rid,
                            "rung": rung,
                            "y": y,
                            "p_win": min(max(p, 0.0), 1.0),
                            "s_star": 0.5 + 0.1 * arms,
                        }
                    )
    return pd.DataFrame(rows)


def test_ranking_paired_orders_policies_and_adjusts_the_listed_comparisons():
    sc = _rank_scores(np.random.default_rng(4))
    out = ex.ranking_paired(sc, rungs=("A", "B", "P1"), comparisons=(("A", "P1"), ("B", "P1")), B=100, budgets=(0.25, 0.10))
    row = out["budgets"]["0.25"]
    pol = row["policies"]
    assert pol["A"]["estimate"] > pol["B"]["estimate"] and pol["oracle"]["estimate"] >= pol["A"]["estimate"] > pol["random"]["estimate"]
    d = row["differences"]["A_minus_P1"]
    assert d["lo"] > 0 and d["adjusted_lo"] < d["lo"] and d["family_size"] == 2  # the adjusted bound is wider than the percentile one
    assert row["differences"]["A_minus_P1"]["estimate"] == pytest.approx(pol["A"]["estimate"] - pol["P1"]["estimate"])
    assert (
        "s_star_minus_arm_count" in row["differences"]
        and "s_star_desc_minus_arm_count" in row["differences"]
        and "A_minus_s_star" in row["differences"]
    )
    assert set(out["budgets"]) == {"0.25", "0.10"}
    # the same input and seed give the same intervals
    assert (
        ex.ranking_paired(sc, rungs=("A", "B", "P1"), comparisons=(("A", "P1"),), B=100, budgets=(0.25,))["budgets"]["0.25"]["policies"]["A"]
        == ex.ranking_paired(sc, rungs=("A", "B", "P1"), comparisons=(("A", "P1"),), B=100, budgets=(0.25,))["budgets"]["0.25"]["policies"]["A"]
    )
    assert ex.ranking_paired(sc.drop(columns="s_star")) is None


def test_ranking_paired_on_a_backtest_agrees_with_the_decision_table(backtest_scores):
    from mootcourt import decision_value as dv

    out = ex.ranking_paired(backtest_scores, comparisons=(("P2", "P1"), ("text_lr", "P1")), B=50, budgets=(0.25,))
    table = dv.decision_value(backtest_scores, B=20, fractions=(0.25,))
    pooled = table[(table["origin"].astype(str) == "ALL") & (table["policy"] == "p_win")].set_index("rung")["captured_fraction"]
    for r in ("P1", "P2", "text_lr"):
        assert out["budgets"]["0.25"]["policies"][r]["estimate"] == pytest.approx(float(pooled[r]))


# ------------------------------------------------------------------------------------------------------------------------------- X6
def _abstain_scores(rng, effect_within: float):
    rows = []
    for o in range(3):
        for cell, p_base, abst_rate in (("a", 0.30, 0.1), ("b", 0.05, 0.7)):
            for t in range(120):
                abst = rng.random() < abst_rate
                ev = float(rng.random() < p_base)
                # in cell b the forecast of the rung is better on issued rows by `effect_within`
                p = p_base + (0.0 if abst else effect_within * (ev - p_base))
                rows.append(
                    {
                        "origin": pd.Timestamp("2014-01-01", tz="UTC") + pd.Timedelta(days=90 * o),
                        "cell": cell,
                        "test_id": f"{o}{cell}{t}",
                        "rung": "P1",
                        "abstain": abst,
                        "brier_event": (p - ev) ** 2,
                        "brier_base": (p_base - ev) ** 2,
                    }
                )
    return pd.DataFrame(rows)


def test_abstention_composition_removes_the_burn_in_and_the_composition_effect():
    sc = _abstain_scores(np.random.default_rng(5), 0.0)
    out = ex.abstention_composition(sc, rungs=("P1",), B=200)
    r = out["P1"]
    assert r["rows"] == int((sc["origin"] > sc["origin"].min()).sum())  # the first origin is out
    # no difference within strata: the stratified difference is near zero, and the interval holds zero
    s = r["stratified_issued_minus_abstained_skill"]
    assert abs(s["estimate"]) < 1e-9 and s["lo"] <= 0 <= s["hi"] and s["strata_with_both_groups"] == s["strata_total"]
    sc2 = _abstain_scores(np.random.default_rng(6), 0.8)
    s2 = ex.abstention_composition(sc2, rungs=("P1",), B=200)["P1"]["stratified_issued_minus_abstained_skill"]
    assert s2["estimate"] > 0.05 and s2["lo"] > 0
    assert ex.abstention_composition(sc.drop(columns="abstain")) is None


# ------------------------------------------------------------------------------------------------------------------------------- X7
def test_gates_by_stratum_uses_each_strata_own_gate_and_one_rule(backtest_scores):
    scores = backtest_scores.copy()
    cells = sorted(scores["cell"].unique())
    gates = {
        "reps": 1,
        "strata": {"ALL": {"n_200": 10, "n_400": 20, "by_target": {"0.80": {"n_200": 8, "n_400": 15}, "0.90": {"n_200": 10, "n_400": 20}}}},
    }
    for c in cells:
        gates["strata"][c] = {
            "n_200": 10**6,
            "n_400": 10**7,
            "by_target": {"0.80": {"n_200": 10**5, "n_400": 10**6}, "0.90": {"n_200": 10**6, "n_400": 10**7}},
        }
    out = ex.gates_by_stratum(scores, gates, B=50)
    assert out["strata"]["ALL"]["verdict"] == "decidable at skill 0.20 and 0.10"
    for c in cells:
        assert out["strata"][c]["verdict"] == "undecidable at this n"
        for v in out["strata"][c]["rungs"].values():
            assert v["family_size"] == len(out["strata"][c]["rungs"]) and v["verdict"] == "undecidable at this n"
            assert v["adjusted_lo"] <= v["lo"] + 1e-12 and v["adjusted_hi"] >= v["hi"] - 1e-12
    assert ex.gates_by_stratum(scores, None) is None


def test_stratum_dependence_matches_the_ledger_measure():
    rng = np.random.default_rng(8)
    g = pd.DataFrame({"test_id": np.repeat(np.arange(200), 3), "event": (rng.random(600) < 0.1).astype(float)})
    d = ex.stratum_dependence(g)
    assert d["rows_per_test"] == 3.0 and d["n_tests"] == 200 and d["base_rate"] == pytest.approx(g["event"].mean()) and 0 <= d["icc"] < 1


# ------------------------------------------------------------------------------------------------------------------------------- X8
def test_drift_null_with_q_equal_p_is_the_current_null_and_a_shifted_world_raises_the_ece():
    rng = np.random.default_rng(9)
    p = rng.uniform(0.02, 0.4, 600)
    t = np.repeat(np.arange(200), 3)
    same = ex.ece_null_drift(p, p, draws=200, seed=3, test_ids=t, icc=0.2)
    assert np.allclose(same, hs.ece_null(p, 200, 3, test_ids=t, icc=0.2))
    shifted = ex.ece_null_drift(p, np.clip(p * 0.5, 0, 1), draws=200, seed=3, test_ids=t, icc=0.2)
    assert shifted.mean() > same.mean() + 0.02
    with pytest.raises(ValueError):
        ex.ece_null_drift(p, p[:-1])


def test_drift_matched_null_reproduces_the_current_null_percentile_and_adds_the_second(backtest_scores):
    out = ex.drift_matched_null(backtest_scores, draws=200)
    r = out["rungs"]["P1"]["pooled"]
    g = backtest_scores[backtest_scores["rung"] == "P1"]
    p, e, t = g["p_sig"].to_numpy(float), g["event"].to_numpy(float), g["test_id"].to_numpy()
    de = hs.design_effect(p, e, t)
    rho = hs.latent_rho_for_design_effect(p, t, de["design_effect"], seed=0)
    assert r["current_null"]["percentile"] == pytest.approx(hs.ece_percentile(p, e, draws=200, seed=0, test_ids=t, icc=rho))
    assert 0 <= r["drift_matched_null"]["percentile"] <= 100 and r["ece"] == pytest.approx(hs.ece(p, e))
    assert set(out["rungs"]) == {"P0", "P1", "P2"}
    assert ex.drift_matched_null(backtest_scores.drop(columns="p_base")) is None


# ------------------------------------------------------------------------------------------------------------------------------- X9
def test_within_origin_auc_is_one_half_for_a_forecast_that_only_moves_with_the_origin():
    rng = np.random.default_rng(10)
    rows = []
    for o in range(3):
        for t in range(150):
            rows.append(
                {
                    "origin": pd.Timestamp("2014-01-01", tz="UTC") + pd.Timedelta(days=90 * o),
                    "cell": "a",
                    "test_id": f"{o}-{t}",
                    "rung": "R",
                    "p_sig": 0.1 + 0.1 * o,
                    "event": float(rng.random() < 0.1 + 0.1 * o),
                }
            )
    sc = pd.DataFrame(rows)
    out = ex.within_origin_auc_by_year(sc, rungs=("R",), B=100)
    row = out["years"]["ALL"]["R"]
    assert row["auc_within_origin"]["estimate"] == pytest.approx(0.5) and row["auc_pooled"]["estimate"] > 0.55
    assert "2014" in out["years"]


def test_lowest_reliability_bin_reads_the_first_populated_bin():
    rng = np.random.default_rng(12)
    n = 800
    p = np.where(np.arange(n) < 200, 0.03, 0.4)
    ev = (rng.random(n) < np.where(np.arange(n) < 200, 0.10, 0.4)).astype(float)
    sc = pd.DataFrame({"rung": "R", "p_sig": p, "event": ev, "test_id": np.arange(n) // 2, "origin": pd.Timestamp("2014-01-01", tz="UTC")})
    r = ex.lowest_reliability_bin(sc, rungs=("R",), B=100)["rungs"]["R"]
    assert r["bin"] == 0 and r["rows"] == 200 and r["mean_forecast"] == pytest.approx(0.03)
    assert r["gap_observed_minus_forecast"] > 0.03 and r["gap_lo"] is not None


def test_learning_curve_pairs_each_rung_with_p1_on_the_same_rows():
    from mootcourt.harness import default_rungs
    from mootcourt.learning_curve import final_origin, run_learning_curve
    from mootcourt.sources import synthetic as synth

    ledger = synth.generate(synth.SyntheticConfig(seed=13, n_tests=300, variants_per_test=2))[0]
    gates = {"n_200": 20, "n_400": 30}
    doc = run_learning_curve(ledger, "synthetic", lambda frame: default_rungs("synthetic", frame, None, baselines=False), [0.5, 1.0], 2, gates, B=50)
    rows = {(r["fraction"], r["rung"]): r for r in doc["paired_vs_p1"]}
    assert {(0.5, "P2"), (1.0, "P2"), (0.5, "P0"), (1.0, "P0")} <= set(rows) and not any(k[1] == "P1" for k in rows)
    full = rows[(1.0, "P2")]
    assert full["n_seeds"] == 1 and full["logscore_lo"] <= full["logscore_minus_p1"] <= full["logscore_hi"]
    assert rows[(0.5, "P2")]["n_seeds"] == 2 and rows[(0.5, "P2")]["n_paired"] == full["n_paired"]
    assert np.isfinite(rows[(1.0, "P0")]["logscore_minus_p1"]) and np.isfinite(rows[(1.0, "P0")]["brier_gain_over_p1"])
    assert final_origin(ledger) is not None


def test_learning_curve_pairs_each_rung_with_itself_at_the_full_history():
    """The history-amount comparison (docs/superpowers/plans/2026-11-10-history-amount-comparison.md): each rung on a subsample
    against the same rung on the full history, on the same held-out rows, with an interval by test."""
    from mootcourt.harness import default_rungs
    from mootcourt.learning_curve import run_learning_curve
    from mootcourt.sources import synthetic as synth

    ledger = synth.generate(synth.SyntheticConfig(seed=13, n_tests=300, variants_per_test=2))[0]
    gates = {"n_200": 20, "n_400": 30}
    doc = run_learning_curve(ledger, "synthetic", lambda frame: default_rungs("synthetic", frame, None, baselines=False), [0.5, 1.0], 2, gates, B=50)
    rows = {(r["fraction"], r["rung"]): r for r in doc["paired_vs_full"]}
    assert {(0.5, "P0"), (0.5, "P1"), (0.5, "P2")} <= set(rows) and not any(k[0] >= 1.0 for k in rows)   # the full history has no pair
    r = rows[(0.5, "P1")]
    assert r["n_seeds"] == 2 and r["n_paired"] == doc["heldout_rows"]
    assert r["logscore_lo"] <= r["logscore_minus_full"] <= r["logscore_hi"] and np.isfinite(r["brier_gain_over_full"])
    by = {(x["fraction"], x["rung"]): x["logscore"] for x in doc["rows"]}
    assert r["logscore_minus_full"] == pytest.approx(by[(0.5, "P1")] - by[(1.0, "P1")], abs=1e-9)      # mean of pairs = difference of means
    assert "full history" in doc["paired_vs_full_note"]
    assert {(x["fraction"], x["rung"]) for x in doc["paired_vs_p1"]} >= {(0.5, "P0"), (1.0, "P0")}            # the existing key is unchanged


def test_gates_by_stratum_script_simulates_each_strata_with_its_own_dependence(backtest_scores):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("gates_by_stratum", Path(__file__).resolve().parents[1] / "scripts" / "gates_by_stratum.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = mod.compute(backtest_scores, reps=6, B=20, seed=1, grid=[25, 50, 100, 200])
    assert "ALL" in doc["strata"] and doc["label"] == "synthetic" and doc["interval"]["by"] == "test"
    for cell, e in doc["strata"].items():
        dep = e["dependence"]
        assert dep["rows_per_test"] >= 1 and 0 <= dep["icc"] < 1 and e["n_200"] <= e["n_400"]
        assert set(e["by_target"]) == {"0.80", "0.90"}
    out = ex.gates_by_stratum(backtest_scores, doc, B=30)
    assert out["strata"]["ALL"]["verdict"] in {
        "undecidable at this n",
        "decidable at skill 0.20 only",
        "decidable at skill 0.10 only",
        "decidable at skill 0.20 and 0.10",
    }


def _paper_extras():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("paper_extras_v2", Path(__file__).resolve().parents[1] / "scripts" / "paper_extras.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_version2_keys_fill_from_a_score_table_and_name_what_is_missing(backtest_scores, tmp_path):
    pe = _paper_extras()
    backtest_scores.to_parquet(tmp_path / "scores-synthetic-S.parquet")
    out = pe.version2_keys("synthetic", pd.DataFrame(), tmp_path, "S")
    for key in ("ranking_paired", "abstention_composition", "drift_matched_null", "within_origin_auc_by_year", "lowest_reliability_bin"):
        assert out[key] is not None, key
    for key in (
        "randomization_window",
        "effect_scale_choices",
        "exposure_fixed",
        "exposure_fixed_visible",
        "prior_family_scale",
        "gates_by_stratum",
        "positive_control_decision_value",
    ):
        assert out[key] is None, key
    assert out["version2_errors"] == {}
    # a score table that lacks a column an analysis needs gives None and a recorded error, not a crash
    backtest_scores.drop(columns=["origin"]).to_parquet(tmp_path / "scores-synthetic-T.parquet")
    broken = pe.version2_keys("synthetic", pd.DataFrame(), tmp_path, "T")
    assert (
        broken["ranking_paired"] is None
        and "ranking_paired" in broken["version2_errors"]
        and "KeyError" in broken["version2_errors"]["ranking_paired"]
    )
    json.dumps(pe.clean(out), allow_nan=False)


def test_the_run_folder_collects_the_window_ablation_and_the_stratum_gates(tmp_path):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("assemble_v2", Path(__file__).resolve().parents[1] / "scripts" / "assemble_run_folder.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rep = tmp_path / "reports"
    (rep / "include-randomization-window").mkdir(parents=True)
    (rep / "include-randomization-window" / "backtest-upworthy-S.json").write_text("{}")
    (rep / "gates-by-stratum-upworthy-S.json").write_text("{}")
    (rep / "backtest-upworthy-S.json").write_text("{}")
    got = mod.collect(rep)
    assert {"include-randomization-window/backtest-upworthy-S.json", "gates-by-stratum-upworthy-S.json", "backtest-upworthy-S.json"} <= set(got)
    assert (
        mod._relative_name(rep / "include-randomization-window" / "backtest-upworthy-S.json")
        == "include-randomization-window/backtest-upworthy-S.json"
    )


def test_exposure_fixed_reads_forecasts_equal_to_rounding_noise_as_ties(tmp_path):
    ab = tmp_path / "ablations"
    ab.mkdir()
    (tmp_path / "backtest-upworthy-S.json").write_text(json.dumps(_report({"P1": {"auc_event_within": 0.53}})))
    (ab / "backtest-upworthy-S--exposure-cell-median.json").write_text(json.dumps(_report({"P1": {"auc_event_within": 0.49}})))
    rng = np.random.default_rng(3)
    n = 400
    base = pd.DataFrame(
        {"origin": ["o"] * n, "cell": ["a"] * n, "rung": "P1", "test_id": np.arange(n), "exposure": 5.0, "event": (rng.random(n) < 0.2).astype(float)}
    )
    base.assign(p_sig=0.1 + rng.normal(0, 1e-15, n)).to_parquet(ab / "scores-upworthy-S--exposure-cell-median.parquet")
    base.assign(p_sig=rng.uniform(0.05, 0.3, n), exposure=rng.uniform(1, 9, n)).to_parquet(tmp_path / "scores-upworthy-S.parquet")
    out = ex.exposure_fixed(tmp_path, "upworthy", "S")
    assert out["auc_event_within_ties_exact"]["fixed"]["P1"] == pytest.approx(0.5)  # noise in the last place is a tie
    assert out["auc_event_within_ties_exact"]["main"]["P1"] != pytest.approx(0.5, abs=1e-6)


def test_calibration_within_period_removes_a_level_error_but_not_a_shape_error():
    rng = np.random.default_rng(31)
    rows = []
    for o in range(4):
        level = 0.05 + 0.04 * o  # the event rate moves between origins
        for t in range(300):
            p = float(np.clip(0.1 + rng.normal(0, 0.03), 0.02, 0.4))  # the forecast does not follow it
            rows.append(
                {
                    "origin": pd.Timestamp("2014-01-01", tz="UTC") + pd.Timedelta(days=90 * o),
                    "cell": "a",
                    "test_id": f"{o}-{t}",
                    "rung": "R",
                    "p_sig": p,
                    "event": float(rng.random() < level),
                }
            )
    sc = pd.DataFrame(rows)
    out = ex.calibration_within_period(sc, rungs=("R",), draws=100)["rungs"]["R"]
    a = out["by_stratum_group"]["ALL"]
    assert a["ece_after"] < a["ece_before"] and a["share_of_ece_removed"] > 0.2 and out["strata_shifted"] == 4
    # shifted forecasts have the realized mean in every stratum
    p_s, shift = ex.logit_shift_to_mean(np.array([0.1, 0.2, 0.3]), 0.4)
    assert p_s.mean() == pytest.approx(0.4, abs=1e-6) and shift > 0
    # a stratum with too few rows is listed and left as it is
    small = sc[sc["origin"] == sc["origin"].min()].head(10)
    out2 = ex.calibration_within_period(pd.concat([sc, small.assign(origin=pd.Timestamp("2016-01-01", tz="UTC"))]), rungs=("R",), draws=50)["rungs"][
        "R"
    ]
    assert len(out2["unshifted_strata"]) == 1
    assert ex.calibration_within_period(sc.drop(columns="event")) is None


# ---------------------------------------------------------------- the learning curve at a named origin (reviewer runs, Part D)
def _curve_inputs():
    from mootcourt.harness import default_rungs
    from mootcourt.sources import synthetic as synth

    ledger = synth.generate(synth.SyntheticConfig(seed=13, n_tests=300, variants_per_test=2))[0]
    return ledger, (lambda frame: default_rungs("synthetic", frame, None, baselines=False)), {"n_200": 20, "n_400": 30}


def test_the_learning_curve_at_its_default_origin_is_unchanged_by_naming_that_origin():
    from mootcourt.learning_curve import final_origin, run_learning_curve

    ledger, factory, gates = _curve_inputs()
    a = run_learning_curve(ledger, "synthetic", factory, [0.5, 1.0], 2, gates, B=20)
    b = run_learning_curve(ledger, "synthetic", factory, [0.5, 1.0], 2, gates, B=20, origin=final_origin(ledger))
    assert a["final_origin"] == b["final_origin"] and a["rows"] == b["rows"] and a["paired_vs_full"] == b["paired_vs_full"]
    assert a["origin_rule"] == "final" and b["origin_rule"] == "given"


def test_the_learning_curve_at_another_origin_scores_that_quarter():
    from mootcourt.learning_curve import final_origin, run_learning_curve

    ledger, factory, gates = _curve_inputs()
    other = pd.Timestamp("2014-07-01", tz="UTC")
    assert other != final_origin(ledger)
    doc = run_learning_curve(ledger, "synthetic", factory, [0.5, 1.0], 2, gates, B=20, origin=other)
    adm = ledger[ledger["status"] == "admitted"]
    in_quarter = adm[(adm["started_at"] >= other) & (adm["started_at"] < other + pd.DateOffset(months=3))]
    assert doc["final_origin"] == other.isoformat() and 0 < doc["heldout_rows"] <= len(in_quarter)
    assert {(r["fraction"], r["rung"]) for r in doc["paired_vs_full"]} >= {(0.5, "P1")}


def test_a_fraction_too_small_to_fit_is_counted_and_does_not_stop_the_curve():
    from mootcourt.learning_curve import run_learning_curve

    ledger, factory, gates = _curve_inputs()
    doc = run_learning_curve(ledger, "synthetic", factory, [0.001, 1.0], 2, gates, B=20, origin=pd.Timestamp("2014-07-01", tz="UTC"))
    assert doc["skipped_runs"] == {"0.001": 2} and not any(r["fraction"] == 0.001 for r in doc["paired_vs_full"])


def test_a_curve_at_a_named_origin_is_written_beside_the_default_one(tmp_path):
    from mootcourt.learning_curve import run_learning_curve, write_learning_curve

    ledger, factory, gates = _curve_inputs()
    doc = run_learning_curve(ledger, "synthetic", factory, [1.0], 1, gates, B=20, origin=pd.Timestamp("2014-07-01", tz="UTC"))
    plain = write_learning_curve(doc, tmp_path, "sid")
    named = write_learning_curve(doc, tmp_path, "sid", suffix="origin-2014-07-01")
    assert plain["json"].name == "learning-curve-synthetic-sid.json"
    assert named["json"].name == "learning-curve-synthetic-sid--origin-2014-07-01.json" and named["json"].exists()
    assert named["figure"] != plain["figure"] and named["md"] != plain["md"]


# ---------------------------------------------------------------- exposure fixed on visible rows (reviewer runs, Part E)
def _two_fixings(tmp_path, visible=True):
    ab = tmp_path / "ablations"
    ab.mkdir()
    (tmp_path / "backtest-upworthy-S.json").write_text(json.dumps(_report({"P1": {"auc_event_within": 0.53, "brier_skill": 0.002}})))
    rows = lambda p: pd.DataFrame({"origin": ["o"] * 4, "cell": ["a", "a", "b", "b"], "rung": ["P1"] * 4, "p_sig": p, "exposure": [1, 2, 3, 3]})  # noqa: E731
    rows([0.1, 0.2, 0.3, 0.3]).to_parquet(tmp_path / "scores-upworthy-S.parquet")
    for suffix, skill, on in (("exposure-cell-median", 0.001, True), ("exposure-cell-median-visible", 0.004, visible)):
        if on:
            (ab / f"backtest-upworthy-S--{suffix}.json").write_text(json.dumps(_report({"P1": {"auc_event_within": 0.50, "brier_skill": skill}})))
            rows([0.1, 0.1, 0.3, 0.3]).to_parquet(ab / f"scores-upworthy-S--{suffix}.parquet")


def test_exposure_fixed_default_variant_is_the_whole_ledger_run(tmp_path):
    _two_fixings(tmp_path)
    assert ex.exposure_fixed(tmp_path, "upworthy", "S") == ex.exposure_fixed(tmp_path, "upworthy", "S", variant="exposure-cell-median")
    assert ex.exposure_fixed(tmp_path, "upworthy", "S")["report"].endswith("--exposure-cell-median.json")


def test_exposure_fixed_on_visible_rows_reads_its_own_report(tmp_path):
    _two_fixings(tmp_path)
    doc = ex.exposure_fixed(tmp_path, "upworthy", "S", variant="exposure-cell-median-visible")
    assert doc["report"].endswith("--exposure-cell-median-visible.json")
    assert "start of the row's calendar quarter" in doc["definition"]
    assert doc["by_cell"]["ALL"]["fixed_minus_main"]["P1"]["brier_skill"] == pytest.approx(0.002)
    assert doc["p_sig_constant_within_origin_and_cell"]["fixed"]["P1"]["strata_with_one_value"] == 2


def test_exposure_fixed_on_visible_rows_is_none_without_its_report(tmp_path):
    _two_fixings(tmp_path, visible=False)
    assert ex.exposure_fixed(tmp_path, "upworthy", "S", variant="exposure-cell-median-visible") is None
    assert ex.exposure_fixed(tmp_path, "upworthy", "S") is not None


def test_exposure_fixed_refuses_an_unknown_variant(tmp_path):
    _two_fixings(tmp_path)
    with pytest.raises(ValueError):
        ex.exposure_fixed(tmp_path, "upworthy", "S", variant="exposure-other")
