"""Chunk L (T-054): the code fixes of the round 00 red-team review.

One group of tests per criterion. The findings are named by reviewer and number (R1 statistician, R2 platform engineer, R3 ML reviewer,
R5 area chair) as in ``paper/reviews/round-00``. The fixtures are small ledgers shaped like the Upworthy archive (a reference headline,
unequal contrasts per test, a post-launch block), so every path the archive takes is taken here in seconds.
"""
from __future__ import annotations

import datetime as dt
import functools
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
WORDS = ("dog", "teacher", "city", "river", "money", "truth", "story", "future", "garden", "lesson", "dream", "idea", "nobody", "why", "how")
SIGNAL = ("amazing", "secret", "shocking")


def upworthy_like(n_tests: int = 170, seed: int = 5, signal: float = 0.0, source: str = "upworthy", start=dt.datetime(2013, 1, 1, tzinfo=UTC),
                  span_days: int = 780, heavy: bool = False):
    """A ledger with the columns, the reference headline and the post-launch block of the Upworthy loader, from a known generator."""
    from mootcourt.ledger import LEDGER_COLUMNS, make_row_id, quarter_of

    rng = np.random.default_rng(seed)
    rows = []
    offs = np.sort(rng.uniform(0, span_days, n_tests))
    for i in range(n_tests):
        started = start + dt.timedelta(days=float(offs[i]))
        final = started + dt.timedelta(days=7)
        ref_head = " ".join(rng.choice(WORDS, size=int(rng.integers(3, 7))))
        n_ref = int(rng.integers(8000, 30000))
        ctr = float(rng.uniform(0.012, 0.03))
        for j in range(int(rng.integers(1, 4))):
            has = rng.random() < 0.5
            words = list(rng.choice(WORDS, size=int(rng.integers(3, 7))))
            if has:
                words.insert(1, str(rng.choice(SIGNAL)))
            head = " ".join(words)
            n_var = int(rng.integers(8000, 30000))
            s = 100.0 * math.sqrt(ctr * (1 - ctr) * (1 / n_ref + 1 / n_var))
            theta = 0.02 + (0.12 * rng.standard_t(3) / math.sqrt(3.0) if heavy else rng.normal(0.0, 0.12)) + signal * (has - 0.5)
            y = theta + rng.normal(0.0, s)
            cell = "headline_only" if rng.random() < 0.8 else "both"
            rows.append(
                {
                    "row_id": make_row_id(source, f"t{i:05d}", f"v{j}"),
                    "source": source,
                    "test_id": f"t{i:05d}",
                    "variant_id": f"v{j}",
                    "cell": cell,
                    "period": quarter_of(final),
                    "started_at": pd.Timestamp(started),
                    "final_read_at": pd.Timestamp(final),
                    "usable_after": pd.Timestamp(final),
                    "y": y,
                    "s": s,
                    "n_ref": n_ref,
                    "n_var": n_var,
                    "status": "admitted",
                    "schema_version": 1,
                    "features_json": json.dumps(
                        {
                            "headline": head,
                            "reference_headline": ref_head,
                            "image_changed": cell == "both",
                            "headline_changed": True,
                            "n_variants": 2,
                            "post_launch": {"ctr_ref": ctr, "ctr_var": ctr},
                        },
                        sort_keys=True,
                    ),
                }
            )
    df = pd.DataFrame(rows)[LEDGER_COLUMNS]
    for c in ("started_at", "final_read_at", "usable_after"):
        df[c] = pd.to_datetime(df[c], utc=True)
    df["n_ref"], df["n_var"], df["schema_version"] = df["n_ref"].astype("int64"), df["n_var"].astype("int64"), df["schema_version"].astype("int64")
    return df


GATES = {"n_200": 40, "n_400": 90, "decision_target": 0.9, "by_target": {"0.80": {"n_200": 30, "n_400": 70}, "0.90": {"n_200": 40, "n_400": 90}}}


@functools.lru_cache(maxsize=1)
def _bt():
    """One small backtest of P0, P1, P2 and two challengers with their recalibrated rungs, shared by the tests below."""
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin

    ledger = upworthy_like()
    rungs = default_rungs("upworthy", ledger, ["gbm", "local_eb"], baselines=False, recalibrate=True)
    scores = rolling_origin(ledger, rungs, quarterly_origins(ledger), source="upworthy")
    return ledger, scores


def _bundle(ledger, as_of):
    from mootcourt.bundle import fit_bundle

    return fit_bundle(ledger, "upworthy", "20261103-lllllllllllllll"[:21], as_of=as_of)


# ============================================================================ P0 (R5 blocking, R3 major)
def test_p0_p_sig_is_the_visible_event_rate_and_equals_the_brier_skill_baseline_row_by_row():
    _, sc = _bt()
    p0 = sc[sc["rung"] == "P0"]
    assert len(p0) > 100
    assert np.array_equal(p0["p_sig"].to_numpy(), p0["p_base"].to_numpy())             # the identity: P0's p_sig is brier_base's probability
    assert np.array_equal(p0["brier_event"].to_numpy(), p0["brier_base"].to_numpy())


def test_p0_brier_skill_is_zero_by_construction_in_the_aggregate_and_the_report_says_so():
    from mootcourt import harness_stats as hs
    from mootcourt.report import build_document, render_markdown

    ledger, sc = _bt()
    agg = hs.aggregate_scores(sc[sc["rung"] == "P0"], GATES, B=50)
    assert (agg["brier_skill"].abs() < 1e-12).all()
    doc = build_document(
        sc, ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=GATES, B=40
    )
    assert "zero by construction" in doc["notes"]["p0_skill"] and "zero by construction" in doc["notes"]["rungs"]["P0"]
    assert "zero by construction" in render_markdown(doc)


def test_p0_forecast_is_the_visible_rate_sign_share_and_empirical_quantiles():
    from mootcourt.predictors.p0 import P0Predictor

    ledger, _ = _bt()
    adm = ledger[ledger["status"] == "admitted"]
    origin = pd.Timestamp("2014-04-01", tz="UTC")
    vis = adm[(adm["usable_after"] <= origin) & (adm["cell"] == "headline_only")]
    f = P0Predictor().fit(adm).forecast("headline_only", origin)
    assert f.n == len(vis)
    assert f.p_sig == pytest.approx(float((vis["y"] > 1.96 * vis["s"]).mean()))
    assert f.p_dir == pytest.approx(float((vis["y"] > 0).mean()))
    assert (f.lo90, f.hi90) == pytest.approx(tuple(np.quantile(vis["y"], [0.05, 0.95])))
    assert (f.lo80, f.hi80) == pytest.approx(tuple(np.quantile(vis["y"], [0.1, 0.9])))
    assert f.mean == pytest.approx(float(vis["y"].mean())) and f.var == pytest.approx(float(vis["y"].var(ddof=1)))


def test_p0_scores_y_without_adding_the_measurement_noise_a_second_time():
    from mootcourt.predictors.p0 import P0Predictor

    ledger, _ = _bt()
    adm = ledger[ledger["status"] == "admitted"]
    origin = pd.Timestamp("2014-04-01", tz="UTC")
    p0 = P0Predictor().fit(adm)
    f = p0.forecast("headline_only", origin)
    y = np.array([-0.2, 0.0, 0.4])
    expected = -0.5 * ((y - f.mean) ** 2 / f.var) - 0.5 * math.log(2 * math.pi * f.var)
    assert np.allclose(p0.logscore(y, "headline_only", origin), expected)         # a Normal of y itself, not of theta convolved with s_star
    assert p0.crps(y, "headline_only", origin).min() > 0


def test_the_documented_ladder_states_what_each_rung_adds_and_drops_strict_nesting():
    text = " ".join((ROOT / "docs" / "method.md").read_text(encoding="utf-8").split())
    assert "generalizes the one below it" not in text                                  # the chain of strict nesting is gone from the method notes
    assert "P1 adds a fitted partially pooled Student-t prior that accounts for measurement error" in text
    assert "P2 adds kernel-weighted precedents under an admission guard" in text
    assert "P2 nests P1 exactly at lambda zero" in text


# ============================================================================ P2 family (R1 blocking)
@functools.lru_cache(maxsize=1)
def _p2_fit():
    from mootcourt.features import FeatureSpace
    from mootcourt.predictors.p1 import P1Predictor
    from mootcourt.predictors.p2 import P2Predictor

    ledger = upworthy_like(260, seed=9, signal=0.9, heavy=True)
    adm = ledger[ledger["status"] == "admitted"]
    space = FeatureSpace.fit(adm)
    # a Student-t prior with finite degrees of freedom, so the family is visible
    p1 = P1Predictor(nu_grid=(3,)).fit(adm)
    return adm, space, p1, P2Predictor().fit(adm, space, p1, guard=None)


def test_p2_at_lambda_zero_reproduces_p1_exactly_and_above_zero_keeps_the_family_and_the_degrees_of_freedom():
    adm, space, p1, _ = _p2_fit()
    from mootcourt.predictors.p2 import P2Predictor

    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    x = space.transform_text(["amazing dog story"], False, reference="why the city", exposure=20000)[0]
    zero = P2Predictor().fit(adm, space, p1, lambda_override=0.0)
    p1_pred = p1.predict(x, 0.2, "headline_only", origin)
    assert np.array_equal(zero.predict(x, 0.2, "headline_only", origin).pmf, p1_pred.pmf)       # exact, not to the fourth decimal
    half = P2Predictor().fit(adm, space, p1, lambda_override=0.5).predict(x, 0.2, "headline_only", origin)
    assert half.spec["family"] == p1_pred.spec["family"] == "student_t"
    assert half.spec["df"] == p1_pred.spec["df"]
    assert (half.spec["location"], half.spec["scale"]) != (p1_pred.spec["location"], p1_pred.spec["scale"])     # the precedents move both


def test_p2_variance_at_every_lambda_is_the_moment_matched_mixture_variance_of_the_t():
    adm, space, p1, p2 = _p2_fit()
    from mootcourt.predictors.p2 import P2Predictor

    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    x = space.transform_text(["secret river lesson"], False, reference="a b c", exposure=20000)[0]
    for lam in (0.2, 0.7, 1.0):
        m = P2Predictor().fit(adm, space, p1, lambda_override=lam)
        st = m.neighbor_state(x, "headline_only", origin)
        mo = st.moments()
        pred = m.predictive_from_state(st, x, 0.2, "headline_only", origin)
        nu = pred.spec["df"]
        assert nu is not None and nu > 2
        assert pred.spec["scale"] ** 2 * nu / (nu - 2) == pytest.approx(mo.v, rel=1e-9)         # the t's theta variance is exactly v
        assert pred.spec["location"] == pytest.approx(mo.theta_hat)


def test_the_selection_scores_lambda_zero_with_p1s_own_t_predictive_not_a_normal_stand_in():
    from mootcourt.predictors.p1 import marginal_logpdf_rows, scale_from_sd

    adm, space, p1, p2 = _p2_fit()
    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    par = p1.cell_params("headline_only", p1.last_period())
    g = adm[adm["cell"] == "headline_only"].head(120)
    pred = p1.predict(None, 0.2, "headline_only", origin)
    from_grid = pred.logscore(g["y"].to_numpy(), g["s"].to_numpy())
    from_rows = marginal_logpdf_rows(g["y"].to_numpy(), g["s"].to_numpy() ** 2, par["mu"], par["tau"], par["nu"])
    assert from_rows.mean() == pytest.approx(from_grid.mean(), abs=0.01)                          # the selection's quantity is the predictive's score
    assert scale_from_sd(1.0, 3.0) == pytest.approx(math.sqrt(1 / 3))


def test_the_old_normal_mixture_is_gone_from_the_p2_predictive():
    src = (ROOT / "src" / "mootcourt" / "predictors" / "p2.py").read_text(encoding="utf-8")
    assert "from_normal" not in src
    assert "special.ndtr" not in src


# ============================================================================ coverage by precision, card and loop (R1 blocking, R2 major)
def test_coverage_by_se_ratio_has_ten_deciles_per_rung_and_the_ratio_is_realized_over_planned():
    from mootcourt import harness_stats as hs

    _, sc = _bt()
    tab = hs.coverage_by_se_ratio(sc)
    assert set(tab.columns) >= {"rung", "decile", "ratio_lo", "ratio_hi", "n", "coverage_80", "coverage_90", "event_rate", "mean_p_sig"}
    p1 = tab[tab["rung"] == "P1"]
    assert list(p1["decile"]) == list(range(1, len(p1) + 1)) and 8 <= len(p1) <= 10
    assert (p1["ratio_lo"].to_numpy()[1:] >= p1["ratio_hi"].to_numpy()[:-1] - 1e-12).all()          # deciles are ordered and do not overlap
    assert p1["n"].sum() == (sc["rung"] == "P1").sum()
    row = sc[sc["rung"] == "P1"].iloc[0]
    assert tab["ratio_lo"].min() <= row["s"] / row["s_star"] <= tab["ratio_hi"].max()
    assert ((p1["coverage_90"] >= 0) & (p1["coverage_90"] <= 1)).all()


def test_the_report_carries_the_coverage_by_se_ratio_table_for_every_rung_and_prints_it():
    from mootcourt.report import build_document, render_markdown

    ledger, sc = _bt()
    doc = build_document(
        sc, ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=GATES, B=40
    )
    tab = pd.DataFrame(doc["tables"]["coverage_by_se_ratio"])
    assert {"P0", "P1", "P2", "GBM", "local_eb"} <= set(tab["rung"])
    assert "Coverage by realized over planned standard error" in render_markdown(doc)


def fresh_report(now, cells=("headline_only", "both", "image_only"), **over):
    """A reliability report dated at ``now`` for ``cells``, in the schema of abstain.py."""
    entry = {"as_of": now.isoformat(), "rolling_logscore": 0.0, "p0_rolling_logscore": 0.0, "brier_skill": 0.0, "n": 100, "drifted": False,
             "consecutive_below": 0, "n_tests": 40, "brier_skill_lo": -0.05, "brier_skill_hi": 0.05, "window_weeks": 8, **over}
    return {"source": "upworthy", "as_of": now.isoformat(), "cells": {c: dict(entry) for c in cells}}


def _issued_card(ledger, row, with_abstain_stale=False):
    from mootcourt import card as card_mod

    origin = pd.Timestamp(year=row["started_at"].year, month=3 * ((row["started_at"].month - 1) // 3) + 1, day=1, tz="UTC")
    bundle = _bundle(ledger, origin)
    f = json.loads(row["features_json"])
    req = card_mod.CardRequest(source="upworthy", headline=f["headline"], image_changed=f["image_changed"], impressions=int(row["n_ref"]),
                               impressions_variant=int(row["n_var"]), origin=origin.to_pydatetime(), row_id=row["row_id"], cell=row["cell"],
                               reference_headline=f["reference_headline"])
    return bundle, req, origin


def test_a_card_carries_the_theta_interval_the_y_interval_and_the_predictive_it_will_be_scored_with():
    from mootcourt import card as card_mod
    from mootcourt.predictors.base import Predictive

    ledger, _ = _bt()
    row = ledger[(ledger["started_at"] >= "2014-04-01") & (ledger["cell"] == "headline_only")].iloc[0]
    bundle, req, origin = _issued_card(ledger, row)
    card = card_mod.build_card(bundle, req, reliability=fresh_report(origin), now=origin.to_pydatetime())
    assert card.abstention.status == "issue", card.abstention.details
    p = card.prediction
    assert p.predictive["family"] in ("student_t", "normal") and (p.predictive["family"] == "normal") == (p.predictive["df"] is None)
    assert {"location", "scale", "s_star", "grid_lo", "grid_hi", "grid_n"} <= set(p.predictive)
    assert p.predictive["s_star"] == pytest.approx(card.request.s_star)
    assert p.interval_90_y[0] < p.interval_90[0] and p.interval_90_y[1] > p.interval_90[1]           # the result is wider than the effect
    rebuilt = Predictive.from_spec(p.predictive)
    assert rebuilt.p_sig(card.request.s_star) == pytest.approx(p.p_sig)
    doc = card_mod.to_json(card)
    assert doc["schema_version"] == 2 and doc["prediction"]["interval_90_y"] == list(p.interval_90_y)
    assert "result of the test at the planned standard error" in card_mod.to_markdown(card)


def test_the_weekly_join_scores_a_card_with_its_own_predictive_and_matches_the_backtest_score_of_the_same_row():
    from mootcourt import card as card_mod
    from mootcourt import loop
    from mootcourt.predictors.p0 import P0Predictor

    ledger, sc = _bt()
    adm = ledger[ledger["status"] == "admitted"]
    checked = 0
    for _, row in adm[(adm["started_at"] >= "2014-04-01") & (adm["cell"] == "headline_only")].head(40).iterrows():
        bundle, req, origin = _issued_card(ledger, row)
        card = card_mod.to_json(card_mod.build_card(bundle, req, reliability=fresh_report(origin), now=origin.to_pydatetime()))
        out = loop.outcome_from_card(card, row, P0Predictor().fit(adm), row["usable_after"].to_pydatetime() + dt.timedelta(days=1))
        bt = sc[(sc["rung"] == "P2") & (sc["row_id"] == row["row_id"])]
        if len(bt) != 1 or bt["origin"].iloc[0] != origin:
            continue
        checked += 1
        # the backtest's score, not a Normal rebuilt from an interval
        assert out["logscore"] == pytest.approx(bt["logscore"].iloc[0], abs=1e-9)
        assert out["covered_90"] == bool(bt["lo90"].iloc[0] <= row["y"] <= bt["hi90"].iloc[0])
        assert out["brier"] == pytest.approx(bt["brier_event"].iloc[0], abs=1e-9)
        assert not out["legacy_normal"]
        if checked >= 3:
            break
    assert checked >= 1


def test_a_card_of_schema_one_is_scored_by_the_normal_its_interval_implies_and_says_so():
    from mootcourt import card as card_mod
    from mootcourt import loop
    from mootcourt.predictors.p0 import P0Predictor

    ledger, _ = _bt()
    adm = ledger[ledger["status"] == "admitted"]
    row = adm[(adm["started_at"] >= "2014-04-01") & (adm["cell"] == "headline_only")].iloc[0]
    bundle, req, origin = _issued_card(ledger, row)
    card = card_mod.to_json(card_mod.build_card(bundle, req, reliability=fresh_report(origin), now=origin.to_pydatetime()))
    card["prediction"].pop("predictive")
    card["prediction"].pop("interval_90_y")
    out = loop.outcome_from_card(card, row, P0Predictor().fit(adm), row["usable_after"].to_pydatetime() + dt.timedelta(days=1))
    assert out["legacy_normal"] is True and out["logscore"] is not None and out["covered_90"] is None


# ============================================================================ the live loop recovers (R2 blocking)
def _freeze_cards(ledger, rows, bundle, origin, reliability, cards_dir, now=None):
    from mootcourt import card as card_mod

    cards = []
    for _, row in rows.iterrows():
        f = json.loads(row["features_json"])
        req = card_mod.CardRequest(source="upworthy", headline=f["headline"], image_changed=f["image_changed"], impressions=int(row["n_ref"]),
                                   impressions_variant=int(row["n_var"]), origin=origin.to_pydatetime(), row_id=row["row_id"], cell=row["cell"],
                                   reference_headline=f["reference_headline"])
        card = card_mod.build_card(bundle, req, reliability=reliability, now=(now or origin).to_pydatetime())
        card_mod.freeze_or_load(card, cards_dir)
        cards.append(card)
    return cards


def test_abstained_cards_are_scored_by_the_join_flagged_and_a_stale_cell_recovers(tmp_path):
    from mootcourt import loop
    from mootcourt.abstain import reliability_reason
    from mootcourt.ledger import write_ledger

    ledger = upworthy_like()
    adm = ledger[(ledger["status"] == "admitted") & (ledger["cell"] == "headline_only")]
    origin = pd.Timestamp("2014-07-02", tz="UTC")
    bundle = _bundle(ledger, pd.Timestamp("2014-07-01", tz="UTC"))
    rows = adm[(adm["started_at"] >= origin) & (adm["started_at"] < origin + pd.Timedelta(days=50))].head(16)
    assert len(rows) >= 12
    stale = fresh_report(origin - pd.Timedelta(days=30), cells=("headline_only",))              # the cell's entry is a month old: every card abstains
    cards_dir, reports_dir, ledger_dir = tmp_path / "cards", tmp_path / "reports", tmp_path / "ledger"
    cards = _freeze_cards(ledger, rows, bundle, origin, stale, cards_dir)
    assert all(c.abstention.status == "abstain" and "reliability" in c.abstention.reasons for c in cards)
    assert all(c.withheld is not None and c.withheld["predictive"] for c in cards)              # the withheld forecast is sealed in the card
    reports_dir.mkdir()
    (reports_dir / "reliability-upworthy.json").write_text(json.dumps(stale))
    ledger_dir.mkdir()
    write_ledger(ledger, ledger_dir / "ledger.parquet")
    now = (rows["usable_after"].max() + pd.Timedelta(days=1)).to_pydatetime()
    res = loop.join_new_rows(
        lambda: ledger.iloc[0:0], ledger_dir=ledger_dir, cards_dir=cards_dir, reports_dir=reports_dir, source="upworthy", now=now
    )
    assert res.n_outcomes == len(rows)
    outs = [json.loads(p.read_text()) for p in (cards_dir / "outcomes").glob("*.json")]
    assert all(o["abstained"] and o["logscore"] is not None and o["scored_forecast"] == "withheld" for o in outs)      # flagged, not dropped
    report = json.loads((reports_dir / "reliability-upworthy.json").read_text())
    entry = report["cells"]["headline_only"]
    assert entry["n"] == len(rows) and entry["as_of"] == now.isoformat()                         # the entry refreshed: the cell is no longer stale
    assert entry["n_tests"] is not None and entry["brier_skill_lo"] is not None
    assert reliability_reason(report, "headline_only", now + dt.timedelta(days=1)) is None


def test_a_drift_mark_is_cleared_by_later_outcomes_of_abstained_cards(tmp_path):
    from mootcourt import loop
    from mootcourt.ledger import write_ledger

    ledger = upworthy_like()
    adm = ledger[(ledger["status"] == "admitted") & (ledger["cell"] == "headline_only")]
    origin = pd.Timestamp("2014-07-02", tz="UTC")
    bundle = _bundle(ledger, pd.Timestamp("2014-07-01", tz="UTC"))
    rows = adm[(adm["started_at"] >= origin) & (adm["started_at"] < origin + pd.Timedelta(days=50))].head(16)
    drifted = fresh_report(origin, cells=("headline_only",), drifted=True, consecutive_below=2)
    cards_dir, reports_dir, ledger_dir = tmp_path / "cards", tmp_path / "reports", tmp_path / "ledger"
    cards = _freeze_cards(ledger, rows, bundle, origin, drifted, cards_dir)
    assert all("reliability" in c.abstention.reasons for c in cards)                              # a marked cell abstains on every card
    reports_dir.mkdir()
    (reports_dir / "reliability-upworthy.json").write_text(json.dumps(drifted))
    ledger_dir.mkdir()
    write_ledger(ledger, ledger_dir / "ledger.parquet")
    now = (rows["usable_after"].max() + pd.Timedelta(days=1)).to_pydatetime()
    loop.join_new_rows(lambda: ledger.iloc[0:0], ledger_dir=ledger_dir, cards_dir=cards_dir, reports_dir=reports_dir, source="upworthy", now=now)
    entry = json.loads((reports_dir / "reliability-upworthy.json").read_text())["cells"]["headline_only"]
    assert entry["n"] >= 10 and entry["consecutive_below"] == 0 and entry["drifted"] is False


def test_the_withheld_forecast_never_reaches_a_rendering_a_response_or_a_tool():
    from mootcourt import card as card_mod

    ledger, _ = _bt()
    row = ledger[(ledger["started_at"] >= "2014-04-01") & (ledger["cell"] == "headline_only")].iloc[0]
    bundle, req, origin = _issued_card(ledger, row)
    card = card_mod.build_card(bundle, req, reliability=None, now=origin.to_pydatetime())            # no report: the card abstains
    assert card.abstention.status == "abstain" and card.withheld
    frozen = card_mod.to_json(card)
    assert "withheld" in frozen and "withheld" not in card_mod.public_json(frozen)
    assert "interval_90_y" not in frozen["prediction"] and frozen["prediction"]["rung"] == "P0"
    text = card_mod.to_markdown(card)
    assert "the base rate the card declined to improve on" in text
    assert frozen["robustness"]["applicable"] is False                                           # no robustness numbers on an abstained card


def test_replay_and_join_share_one_code_path_and_the_replay_passes_no_forecast_of_its_own():
    import inspect

    from mootcourt import loop

    assert "forecast" not in inspect.signature(loop.outcome_from_card).parameters
    script = (ROOT / "scripts" / "replay_weekly.py").read_text(encoding="utf-8")
    assert "forecast=" not in script and "loop.reliability_row" in script and "loop.outcome_from_card" in script
    ops = " ".join((ROOT / "docs" / "operations.md").read_text(encoding="utf-8").split())
    assert "abstained card is scored on the forecast it withheld" in ops


def test_the_replay_scores_with_the_stored_predictive_and_covers_against_the_y_interval():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("replay_weekly_l", ROOT / "scripts" / "replay_weekly.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["replay_weekly_l"] = mod
    spec.loader.exec_module(mod)
    ledger = upworthy_like(150, seed=12, span_days=500)
    doc, records = mod.replay(ledger, "upworthy", "snap-l", keep_records=True)
    joined = [r for r in records if r["outcome"] is not None]
    assert joined
    issued = [r for r in joined if not r["outcome"]["abstained"]]
    assert issued and all(r["outcome"]["interval_90_y"] and r["outcome"]["covered_90"] in (True, False) for r in issued)
    assert all(r["outcome"]["logscore"] is not None for r in joined if r["card"]["abstention"]["status"] == "abstain" and r["card"].get("withheld"))
    assert all(not r["outcome"]["legacy_normal"] for r in joined)
    assert doc["totals"]["coverage_90_all_n"] == len(issued)


# ============================================================================ released interfaces close the loop (R2 major)
@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """A saved and registered bundle on a scratch models folder, with the reports and cards folders beside it."""
    from mootcourt.bundle import save_bundle
    from mootcourt.registry import Registry

    root = tmp_path_factory.mktemp("served")
    ledger = upworthy_like()
    now = pd.Timestamp("2014-07-02 12:00", tz="UTC")
    bundle = _bundle(ledger, pd.Timestamp("2014-07-01", tz="UTC"))
    save_bundle(bundle, root / "models")
    Registry(root / "models").register_model("upworthy", bundle.model_id)
    (root / "reports").mkdir()
    (root / "reports" / "reliability-upworthy.json").write_text(json.dumps(fresh_report(now)))
    (root / "cards").mkdir()
    return root, ledger, now, bundle


def test_resolve_row_id_accepts_a_row_id_or_the_ledger_row_key_and_refuses_ambiguity():
    from mootcourt.ledger import resolve_row_id

    assert resolve_row_id("upworthy", None, None, None) is None
    assert resolve_row_id("upworthy", "upworthy:t1:v0") == "upworthy:t1:v0"
    assert resolve_row_id("upworthy", None, "t1", "v0") == "upworthy:t1:v0"
    for bad in (("upworthy", "a", "t1", "v0"), ("upworthy", None, "t1", None), ("upworthy", " ", None, None), ("upworthy", "a\nb", None, None)):
        with pytest.raises(ValueError):
            resolve_row_id(*bad)


def test_moot_card_accepts_a_row_id_and_a_ledger_row_key_and_the_frozen_card_carries_it(served):
    from mootcourt.cli import app

    root, ledger, now, bundle = served
    common = ["card", "--source", "upworthy", "--headline", "amazing dog story", "--impressions", "20000", "--models-dir", str(root / "models"),
              "--cards-dir", str(root / "cards"), "--reports-dir", str(root / "reports"), "--now", now.isoformat(), "--origin", now.isoformat(),
              "--json", "--reference-headline", "why the city"]
    out = CliRunner().invoke(app, common + ["--row-id", "upworthy:t99999:v0"])
    assert out.exit_code == 0, out.output
    doc = json.loads(out.output)
    assert doc["request"]["row_id"] == "upworthy:t99999:v0" and "withheld" not in doc
    on_disk = json.loads((root / "cards" / f"{doc['card_id']}.json").read_text())
    assert on_disk["request"]["row_id"] == "upworthy:t99999:v0" and on_disk["schema_version"] == 2
    out2 = CliRunner().invoke(app, common + ["--test-id", "t88888", "--variant-id", "v1"])
    assert out2.exit_code == 0, out2.output
    assert json.loads(out2.output)["request"]["row_id"] == "upworthy:t88888:v1"
    both = CliRunner().invoke(app, common + ["--row-id", "x", "--test-id", "t", "--variant-id", "v"])
    assert both.exit_code != 0


def test_post_card_and_the_mcp_tool_accept_the_row_id_and_the_tool_still_writes_nothing(served):
    from fastapi.testclient import TestClient

    from mootcourt import mcp_server
    from mootcourt.service import ServingState, create_app

    root, ledger, now, bundle = served
    clock = lambda: now.to_pydatetime()  # noqa: E731
    client = TestClient(create_app(root / "models", root / "cards", root / "reports", now=clock))
    payload = {
        "source": "upworthy",
        "headline": "secret river lesson",
        "impressions": 20000,
        "origin": now.isoformat(),
        "row_id": "upworthy:t77777:v0",
        "reference_headline": "a b c",
        "impressions_variant": 18000,
    }
    r = client.post("/card", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["request"]["row_id"] == "upworthy:t77777:v0" and r.json()["request"]["impressions_variant"] == 18000
    assert (
        client.post("/card", json={**payload, "row_id": None, "test_id": "t66666", "variant_id": "v2"}).json()["request"]["row_id"]
        == "upworthy:t66666:v2"
    )
    state = ServingState(root / "models", root / "reports", clock)
    before = sorted(p.name for p in (root / "cards").glob("*.json"))
    got = json.loads(
        mcp_server.tool_get_card(state, "upworthy", "secret river lesson", False, 20000, now.isoformat(), None, True, "upworthy:t55555:v0")
    )
    assert got["request"]["row_id"] == "upworthy:t55555:v0" and "withheld" not in got
    assert sorted(p.name for p in (root / "cards").glob("*.json")) == before


def test_a_card_frozen_through_an_interface_is_joined_to_its_outcome_by_the_weekly_join(served, tmp_path):
    from fastapi.testclient import TestClient

    from mootcourt import loop
    from mootcourt.ledger import write_ledger
    from mootcourt.service import create_app

    root, ledger, now, _ = served
    row = ledger[(ledger["started_at"] >= now) & (ledger["cell"] == "headline_only")].iloc[0]
    f = json.loads(row["features_json"])
    cards = tmp_path / "cards"
    client = TestClient(create_app(root / "models", cards, root / "reports", now=lambda: now.to_pydatetime()))
    r = client.post(
        "/card",
        json={
            "source": "upworthy",
            "headline": f["headline"],
            "impressions": int(row["n_ref"]),
            "impressions_variant": int(row["n_var"]),
            "origin": now.isoformat(),
            "test_id": row["test_id"],
            "variant_id": row["variant_id"],
            "cell": row["cell"],
            "reference_headline": f["reference_headline"],
        },
    )
    assert r.status_code == 200 and r.json()["request"]["row_id"] == row["row_id"]
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()
    write_ledger(ledger, ledger_dir / "ledger.parquet")
    res = loop.join_new_rows(lambda: ledger.iloc[0:0], ledger_dir=ledger_dir, cards_dir=cards, reports_dir=tmp_path / "reports", source="upworthy",
                             now=(row["usable_after"] + pd.Timedelta(days=1)).to_pydatetime())
    assert res.n_outcomes == 1 and next((cards / "outcomes").glob("*.json")).exists()


# ---- champion refresh
def test_a_refit_of_the_same_method_on_a_newer_fit_replaces_the_champion_without_the_margin_and_a_different_method_still_needs_it(tmp_path):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    t0, t1, t2 = (f"2026-11-0{d}T12:00:00+00:00" for d in (1, 2, 3))
    skill = lambda s: {"brier_skill": s, "brier_skill_lo": s - 0.01, "brier_skill_hi": s + 0.01, "n": 100, "n_tests": 100}  # noqa: E731
    # round 00 review L: a refresh needs strictly newer DATA, not a later fit time
    d0, d1, d2 = (f"2014-0{d}-01T00:00:00+00:00" for d in (1, 2, 3))
    assert reg.register_model("s", "m1", skill(0.001), method_id="A", fitted_at=t0, data_through=d0) == "champion"
    # same method, newer data: a refresh
    assert reg.register_model("s", "m2", skill(0.002), method_id="A", fitted_at=t1, data_through=d1) == "champion"
    assert reg.get_champion("s") == "m2" and reg.get_challenger("s") is None
    assert [e["event"] for e in reg._read()["s"]["history"]][-1] == "champion_refreshed"
    # another method needs the margin
    assert reg.register_model("s", "m3", skill(0.50), method_id="B", fitted_at=t2, data_through=d2) == "challenger"
    assert reg.get_champion("s") == "m2" and reg.get_challenger("s") == "m3"
    res = reg.promote("s", {"n_200": 10, "n_400": 20}, margin=0.02)
    assert res.promoted and reg.get_champion("s") == "m3"


def test_a_refresh_that_is_clearly_worse_or_older_is_a_challenger_not_a_refresh(tmp_path):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    good = {"brier_skill": 0.10, "brier_skill_lo": 0.08, "brier_skill_hi": 0.12, "n": 100, "n_tests": 100}
    worse = {"brier_skill": 0.01, "brier_skill_lo": -0.01, "brier_skill_hi": 0.03, "n": 100, "n_tests": 100}
    reg.register_model("s", "m1", good, method_id="A", fitted_at="2026-11-02T00:00:00+00:00", data_through="2014-02-01T00:00:00+00:00")
    assert (
        reg.register_model("s", "m2", worse, method_id="A", fitted_at="2026-11-03T00:00:00+00:00", data_through="2014-03-01T00:00:00+00:00")
        == "challenger"
    )
    assert (
        reg.register_model("s", "m3", good, method_id="A", fitted_at="2026-11-04T00:00:00+00:00", data_through="2014-01-01T00:00:00+00:00")
        == "challenger"
    )  # older data
    assert reg.get_champion("s") == "m1"


def test_fit_records_the_method_id_in_the_bundle_and_two_fits_of_the_same_method_share_it(served):
    from mootcourt.bundle import load_bundle, method_id

    root, ledger, now, bundle = served
    assert bundle.method_id and bundle.method_id == method_id(bundle.space)
    assert load_bundle(bundle.model_id, root / "models").method_id == bundle.method_id
    assert bundle.method_id != method_id(None)                      # a pairwise space is another method than a single-headline one


# ---- the skill line
def test_the_skill_line_prints_the_interval_the_test_count_and_the_gate_verdict_never_a_bare_number():
    from mootcourt import card as card_mod

    ledger, _ = _bt()
    row = ledger[(ledger["started_at"] >= "2014-04-01") & (ledger["cell"] == "headline_only")].iloc[0]
    bundle, req, origin = _issued_card(ledger, row)
    rel = fresh_report(origin, brier_skill=0.075, n=265, n_tests=60, brier_skill_lo=-0.04, brier_skill_hi=0.19)
    bundle.backtest_summary = {
        "rung": "P2",
        "brier_skill": -0.0043,
        "brier_skill_lo": -0.0085,
        "brier_skill_hi": -0.0006,
        "n_tests": 3797,
        "n": 13247,
    }
    text = card_mod.to_markdown(card_mod.build_card(bundle, req, reliability=rel, now=origin.to_pydatetime(), gates=GATES))
    sec = text.split("## Skill at this n")[1].split("## Abstention")[0]
    assert "0.075" in sec and "90 percent interval -0.040 to 0.190" in sec and "from 60 tests" in sec and "265 rows" in sec
    # GATES is a per-row file: the 265 rows of the window are compared with it, not the 60 tests (review N, REV-N-007)
    assert "Gate at this n: 265 rows:" in sec and "interval includes zero" in sec
    assert "Latest gated backtest, rung P2: Brier skill -0.004" in sec and "3797 tests" in sec
    no_gates = card_mod.to_markdown(card_mod.build_card(bundle, req, reliability=rel, now=origin.to_pydatetime()))
    assert "gate sizes are not available" in no_gates
    old = card_mod.to_markdown(
        card_mod.build_card(
            bundle,
            req,
            reliability=fresh_report(origin, brier_skill_lo=None, brier_skill_hi=None, n_tests=None),
            now=origin.to_pydatetime(),
            gates=GATES,
        )
    )
    assert "no interval is recorded" in old


def test_the_robustness_lines_say_not_applicable_where_the_weight_on_precedents_is_zero():
    from mootcourt import card as card_mod

    ledger, _ = _bt()
    row = ledger[(ledger["started_at"] >= "2014-04-01") & (ledger["cell"] == "headline_only")].iloc[0]
    bundle, req, origin = _issued_card(ledger, row)
    card = card_mod.build_card(bundle, req, reliability=fresh_report(origin), now=origin.to_pydatetime())
    assert card.prediction.lam == 0.0 and card.robustness.applicable is False
    text = card_mod.to_markdown(card)
    assert "Not applicable: the weight on precedents is zero" in text and "more than" not in text.split("## Robustness")[1].split("## Skill")[0]


# ============================================================================ gates at the archive base rate (R1, R5 major)
def test_gate_power_by_test_depends_on_the_base_rate_and_a_lower_base_rate_needs_more_tests():
    from mootcourt import simulate as sim

    kw = dict(reps=200, B=150, seed=3, rows_per_test=3.5, level=0.90)
    high = sim.gate_power(80, 0.10, base=0.30, **kw)
    low = sim.gate_power(80, 0.10, base=0.09, **kw)
    assert high > low + 0.15                                              # a skill of 0.10 is a smaller Brier gap at a base rate of 0.09
    # no skill, no pass (one-sided 5 percent)
    assert sim.gate_power(300, 0.0, base=0.09, reps=250, B=120, seed=4, rows_per_test=3.5, level=0.90) <= 0.12
    assert sim.gate_power(50, 0.20, base=0.09, **kw) < sim.gate_power(400, 0.20, base=0.09, **kw)


def test_write_gates_records_every_base_rate_and_the_by_test_interval_and_load_gates_reads_them(tmp_path):
    from mootcourt import simulate as sim

    path = tmp_path / "gates.json"
    doc = sim.write_gates(
        path, base_rates=[0.09, 0.30], reps=50, B=50, seed=4, grid=[25, 50, 100, 200, 400, 800, 1600, 3200], rows_per_test=3.5, level=0.90
    )
    assert set(doc["by_base_rate"]) == {"0.09", "0.30"} and doc["base_rate"] == 0.09
    assert doc["by_base_rate"]["0.09"]["n_400"] >= doc["by_base_rate"]["0.30"]["n_400"]
    assert {k: doc["interval"][k] for k in ("level", "by", "rows_per_test")} == {"level": 0.9, "by": "test", "rows_per_test": 3.5}
    g = sim.load_gates(path)
    assert sorted(g["by_base_rate"]) == [0.09, 0.30] and g["n_200"] == doc["n_200"]
    assert sim.select_gates(g, 0.085)["base_rate"] == 0.09 and sim.select_gates(g, 0.25)["base_rate"] == 0.30
    assert sim.select_gates(g, 0.30, exact=True)["base_rate"] == 0.30 and sim.select_gates(g, 0.2, exact=True) is None
    flat = {"n_200": 10, "n_400": 20}
    assert sim.select_gates(flat, 0.09) is flat and sim.select_gates(flat, 0.3, exact=True) is None


def test_the_cli_gate_power_command_takes_base_rates_and_writes_the_layout(tmp_path):
    from mootcourt.cli import app

    out = tmp_path / "gates.json"
    res = CliRunner().invoke(
        app, ["simulate", "gate-power", "--out", str(out), "--reps", "30", "--bootstrap", "30", "--base-rate", "0.09", "--base-rate", "0.30"]
    )
    assert res.exit_code == 0, res.output
    doc = json.loads(out.read_text())
    assert set(doc["by_base_rate"]) == {"0.09", "0.30"} and doc["interval"]["by"] == "test" and "base rate 0.09" in res.output


def test_the_harness_reads_decidability_at_the_base_rate_of_the_group_and_keeps_the_old_column():
    from mootcourt import harness_stats as hs

    _, sc = _bt()
    p1 = sc[sc["rung"] == "P1"]
    rate = float(p1["event"].astype(float).mean())
    n_tests = p1["test_id"].nunique()
    gates = {**GATES, "base_rate": 0.09, "by_base_rate": {
        0.09: {"n_200": n_tests - 1, "n_400": n_tests - 1, "base_rate": 0.09, "by_target": {"0.80": {"n_200": 5, "n_400": 9}}},
        0.30: {"n_200": n_tests + 100, "n_400": n_tests + 100, "base_rate": 0.30, "by_target": {"0.80": {"n_200": 5, "n_400": 9}}}}}
    assert rate < 0.2
    row = hs.aggregate_scores(p1, gates, B=40).query("cell == 'ALL'").iloc[0]
    # read at the group's own base rate
    assert row["gate_base_rate"] == 0.09 and row["decidable_by_tests"] == "decidable at skill 0.20 and 0.10"
    assert row["decidable_by_tests_base_0.3"] == "undecidable at this n"                                                # the labelled earlier column


def test_the_report_header_lists_the_gate_sizes_at_each_base_rate():
    from mootcourt.report import build_document

    ledger, sc = _bt()
    gates = {**GATES, "base_rate": 0.09, "interval": {"level": 0.9, "by": "test", "rows_per_test": 3.5},
             "by_base_rate": {0.09: {"n_200": 100, "n_400": 300, "base_rate": 0.09}, 0.30: {"n_200": 40, "n_400": 90, "base_rate": 0.30}}}
    doc = build_document(
        sc, ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=gates, B=30
    )
    assert doc["header"]["gate_base_rates"] == [0.09, 0.30] and doc["header"]["gate_by_base_rate"]["0.09"] == {"n_200": 100, "n_400": 300}


# ============================================================================ decision value (R1, R3, R5)
def test_decision_value_has_a_bootstrap_interval_for_every_fraction_and_regret_three_budgets_and_a_note():
    from mootcourt.decision_value import decision_value

    _, sc = _bt()
    tab = decision_value(sc, B=60)
    assert set(tab["budget"]) == {0.1, 0.25, 0.5} and tab["budget"].iloc[0] == 0.25
    for col in (
        "captured_fraction_lo",
        "captured_fraction_hi",
        "regret_lo",
        "regret_hi",
        "diff_random_lo",
        "diff_random_hi",
        "random_fraction",
        "note",
    ):
        assert col in tab.columns
    allrows = tab[(tab["origin"] == "ALL") & (tab["budget"] == 0.25)]
    assert {"GBM", "local_eb"} <= set(allrows["rung"])                                  # every challenger of the run, not only the ladder
    ok = allrows[allrows["captured_fraction_lo"].notna()]
    assert ((ok["captured_fraction_lo"] <= ok["captured_fraction"] + 0.05) & (ok["captured_fraction"] - 0.05 <= ok["captured_fraction_hi"])).all()
    assert (ok["captured_fraction_hi"] > ok["captured_fraction_lo"]).all()


def test_random_order_captures_k_over_n_exactly_and_a_constant_within_cell_rung_is_flagged_with_the_note():
    from mootcourt.decision_value import NOTE_CELL, NOTE_RANDOM, decision_value

    _, sc = _bt()
    tab = decision_value(sc, B=40)
    rnd = tab[(tab["policy"] == "random") & (tab["budget"] == 0.25) & (tab["origin"] != "ALL")]
    assert np.allclose(rnd["captured_fraction"], rnd["K"] / rnd["n_tests"]) and (rnd["note"] == NOTE_RANDOM).all()
    p1 = tab[(tab["policy"] == "p_win") & (tab["rung"] == "P1") & (tab["origin"] == "ALL") & (tab["budget"] == 0.25)].iloc[0]
    assert bool(p1["constant_within_cell"]) and p1["note"] == NOTE_CELL                  # P1's p_win is one number per cell and origin
    gbm = tab[(tab["policy"] == "p_win") & (tab["rung"] == "GBM") & (tab["origin"] == "ALL") & (tab["budget"] == 0.25)].iloc[0]
    assert not bool(gbm["constant_within_cell"]) and gbm["note"] == ""


def test_the_decision_value_interval_narrows_with_more_tests_and_is_seeded():
    from mootcourt.decision_value import decision_value

    rng = np.random.default_rng(1)

    def make(n):
        v = rng.exponential(1.0, n)
        return pd.DataFrame({"test_id": [f"t{i}" for i in range(n)], "row_id": [f"r{i}" for i in range(n)], "origin": "o", "rung": "P2", "cell": "c",
                             "y": v - 0.5, "p_win": rng.random(n)})

    w = lambda d: (lambda r: r["captured_fraction_hi"] - r["captured_fraction_lo"])(  # noqa: E731
        d[(d["policy"] == "p_win") & (d["budget"] == 0.25)].iloc[0])
    small, big = decision_value(make(40), B=200, seed=1), decision_value(make(800), B=200, seed=1)
    assert w(big) < w(small)
    same = make(40)
    a, b = decision_value(same, B=50, seed=7), decision_value(same, B=50, seed=7)
    assert a.equals(b)                                                                    # the intervals are a function of the seed


def test_paper_tables_print_the_decision_value_columns():
    src = (ROOT / "paper" / "build_tables.py").read_text(encoding="utf-8")
    for col in ("captured_fraction_lo", "diff_random", "regret_lo", "constant_within_cell", "decision-intervals-"):
        assert col in src


# ============================================================================ clustered calibration null (R1 major)
def test_the_clustered_null_is_wider_than_the_independent_null_when_outcomes_move_together_and_has_the_right_marginals():
    from mootcourt import harness_stats as hs

    rng = np.random.default_rng(2)
    tests = np.repeat(np.arange(400), 4)
    p = np.clip(rng.beta(2, 14, tests.size), 0.01, 0.99)
    ind = hs.ece_null(p, draws=300, seed=1)
    clu = hs.ece_null(p, draws=300, seed=1, test_ids=tests, icc=0.6)
    assert clu.mean() > ind.mean() and clu.std() > ind.std()                           # contrasts of one test move together
    same = hs.ece_null(p, draws=300, seed=1, test_ids=tests, icc=0.0)
    assert np.allclose(same, ind)                                                      # no correlation, the independent null
    # a clustered world is a null the observed ECE can sit inside: the percentile falls
    z = rng.standard_normal(400)
    thr = hs.special.ndtri(p)
    e = (np.sqrt(0.6) * z[tests] + np.sqrt(0.4) * rng.standard_normal(tests.size) < thr).astype(float)
    assert hs.ece_percentile(p, e, draws=300, seed=1, test_ids=tests, icc=0.6) <= hs.ece_percentile(p, e, draws=300, seed=1)


def test_the_design_effect_is_near_one_for_independent_outcomes_and_large_for_clustered_ones():
    from mootcourt import harness_stats as hs

    rng = np.random.default_rng(3)
    tests = np.repeat(np.arange(500), 4)
    p = np.full(tests.size, 0.2)
    indep = (rng.random(tests.size) < p).astype(float)
    shared = (rng.random(500) < 0.2).astype(float)[tests]
    d1, d2 = hs.design_effect(p, indep, tests), hs.design_effect(p, shared, tests)
    assert 0.8 < d1["design_effect"] < 1.25 and d1["icc"] < 0.15
    assert d2["design_effect"] > 2.5 and d2["icc"] > 0.5 and d2["mean_test_size"] == 4.0


def test_the_aggregate_reports_the_design_effect_the_clustered_percentile_and_the_equal_mass_ece():
    from mootcourt import harness_stats as hs

    _, sc = _bt()
    row = hs.aggregate_scores(sc[sc["rung"] == "P1"], GATES, B=30).query("cell == 'ALL'").iloc[0]
    for col in ("design_effect", "icc", "ece", "ece_percentile", "ece_percentile_independent", "ece_equal_mass", "ece_equal_mass_percentile"):
        assert np.isfinite(row[col]), col
    assert row["design_effect"] > 0 and 0 <= row["ece_percentile"] <= 100


def test_the_equal_mass_bins_share_a_bin_for_equal_probabilities_and_the_percentile_resolution_is_stated():
    from mootcourt import harness_stats as hs
    from mootcourt.report import INTERVAL_NOTE

    p = np.array([0.1] * 6 + [0.2] * 4 + [0.9] * 10)
    idx = hs._quantile_bin_index(p, 10)
    assert len(set(idx[:6])) == 1 and len(set(idx[6:10])) == 1
    assert "100 means above every draw" in INTERVAL_NOTE and "99.8" in INTERVAL_NOTE


# ============================================================================ ablations off the guard (R3 major)
def test_the_ablation_script_runs_every_guarded_ablation_a_second_time_with_the_guard_off():
    text = (ROOT / "scripts" / "run_ablations.sh").read_text(encoding="utf-8")
    block = re.search(r"GUARDED=\((.*?)\n    \)", text, re.S).group(1)
    guarded = re.findall(r'"([^"]+)"', block)
    for flag in (
        "--features text",
        "--features structured",
        "--bandwidth-mult 1",
        "--bandwidth-mult 0.5",
        "--bandwidth-mult 0.25",
        "--bandwidth-mult 0.125",
        "--p2-selection forward",
        "--recency select",
        "--p2-selection forward --recency select",
        "--pairwise off",
    ):
        assert flag in guarded
    assert 'SETTINGS+=("$g --p2-guard off")' in text and '"--admission prelaunch"' in text


def test_a_guard_off_variant_is_named_after_its_ablation_and_the_header_records_the_guard_setting():
    from mootcourt.cli import _variant_name, _variant_settings
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.report import guard_setting

    v = _variant_settings("text", None, None, None, "t", None, None, p2_guard=None)
    assert _variant_name(v) == "features-text+p2-guard-off" and v["p2_guard"] == "off"
    both = _variant_settings("both", 0.5, None, None, "t", None, None, p2_guard=None)
    assert _variant_name(both) == "bandwidth-mult-0.5+p2-guard-off"
    ledger = upworthy_like(90, seed=21, span_days=500)
    on = rolling_origin(ledger, default_rungs("upworthy", ledger), quarterly_origins(ledger)[:3], source="upworthy")
    off = rolling_origin(ledger, default_rungs("upworthy", ledger, p2_guard=None), quarterly_origins(ledger)[:3], source="upworthy")
    assert guard_setting(on) == 2.0 and guard_setting(off) == "off"


# ============================================================================ reference headline and fair challengers (R3 major)
def test_the_feature_space_reads_the_reference_headline_both_arms_and_their_difference_and_the_hash_changes():
    from mootcourt.features import FeatureSpace, feature_hash, has_reference

    ledger = upworthy_like(120, seed=31)
    adm = ledger[ledger["status"] == "admitted"]
    assert has_reference(adm)
    pair, single = FeatureSpace.fit(adm), FeatureSpace.fit(adm, pairwise=False)
    assert pair.pairwise and not single.pairwise and pair.dim > single.dim
    assert feature_hash(pair) != feature_hash(single)
    d = pair.svd_dims
    X = pair.transform(adm.head(6))
    # variant, reference, difference blocks, structured, pair features
    assert X.shape[1] == 3 * d + 9 + 1 + 3 - 1 or X.shape[1] == pair.dim
    changed = adm.head(6).copy()
    changed["features_json"] = [
        json.dumps({**json.loads(j), "reference_headline": "completely different words nobody"}) for j in changed["features_json"]
    ]
    X2 = pair.transform(changed)
    assert not np.allclose(X, X2)                                                                # the reference headline is an input
    assert np.allclose(single.transform(adm.head(6)), single.transform(changed))                 # the single-headline space never read it
    only_text, only_struct = FeatureSpace.fit(adm, feature_set="text"), FeatureSpace.fit(adm, feature_set="structured")
    assert only_text.dim == 3 * d and only_struct.dim == pair.dim - 3 * d


def test_a_card_request_without_a_reference_headline_gets_the_fit_mean_reference_and_never_fails():
    from mootcourt.features import FeatureSpace

    adm = upworthy_like(100, seed=32)
    sp = FeatureSpace.fit(adm)
    a = sp.transform_text(["amazing dog"], False, exposure=20000)
    b = sp.transform_text(["amazing dog"], False, exposure=20000, reference="why the city is a story")
    assert a.shape == b.shape == (1, sp.dim) and not np.allclose(a, b)
    again = FeatureSpace.from_state(sp.to_state())
    assert again.pairwise and np.allclose(again.transform_text(["amazing dog"], False, exposure=20000), a)


def test_the_text_classifier_reads_both_headlines_where_the_ledger_has_them():
    from mootcourt.harness import TextLR

    adm = upworthy_like(150, seed=33)
    pair, single = TextLR(adm), TextLR(adm, pairwise=False)
    assert pair.pairwise and not single.pairwise
    n_cells = len(pair.cells)
    assert pair._X.shape[1] == 2 * len(pair.vec.vocabulary_) + n_cells and single._X.shape[1] == len(single.vec.vocabulary_) + n_cells


def test_the_gbm_is_precision_weighted_and_picks_its_rounds_on_the_latest_visible_rows_only(monkeypatch):
    from sklearn.ensemble import HistGradientBoostingRegressor as H

    from mootcourt.config import GBM_CONFIGS, GBM_ITER_MAX
    from mootcourt.features import FeatureSpace
    from mootcourt.harness import GBMChallenger

    adm = upworthy_like(200, seed=34)
    adm = adm[adm["status"] == "admitted"]
    space = FeatureSpace.fit(adm)
    seen = []
    real = H.fit

    def spy(self, X, y, sample_weight=None, **kw):
        seen.append((len(X), None if sample_weight is None else float(np.std(sample_weight))))
        return real(self, X, y, sample_weight=sample_weight, **kw)

    monkeypatch.setattr(H, "fit", spy)
    g = GBMChallenger(space, adm)
    n = len(adm)
    search = seen[:len(GBM_CONFIGS)]
    assert all(m == max(int(n * 0.8), 10) for m, _ in search)                                      # the search fits the earliest 80 percent only
    assert all(w is not None and w > 0 for _, w in search)                                         # precision weights that differ by row
    assert 1 <= g.config["rounds"] <= GBM_ITER_MAX and g.config["tuned"]
    monkeypatch.setattr(H, "fit", real)
    plain = GBMChallenger(space, adm, tuned=False)
    assert plain.config == {"tuned": False}


def test_every_challenger_has_a_raw_row_and_a_recalibrated_row_and_the_recalibrated_rows_carry_only_a_probability():
    from mootcourt import harness_stats as hs
    from mootcourt.report import rung_kind

    _, sc = _bt()
    assert {"GBM", "GBM+cal", "local_eb", "local_eb+cal"} <= set(sc["rung"])
    cal = sc[sc["rung"] == "GBM+cal"]
    assert cal["p_sig"].notna().all() and cal["logscore"].isna().all() and cal["p_win"].isna().all() and rung_kind("GBM+cal") == "challenger"
    agg = hs.aggregate_scores(sc, GATES, B=30).query("cell == 'ALL'").set_index("rung")
    assert np.isfinite(agg.loc["GBM+cal", "brier_skill"]) and np.isfinite(agg.loc["GBM", "brier_skill"])
    assert (sc[sc["rung"] == "GBM+cal"].groupby("origin")["p_sig"].nunique() > 1).any()


def test_the_recalibration_is_fit_on_rows_visible_at_the_origin_only_and_never_on_the_scored_rows(monkeypatch):
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.recalibration import Calibrator

    ledger = upworthy_like(120, seed=35, span_days=600)
    fits = []
    real = Calibrator.fit

    def spy(self, p, event):
        fits.append((len(p), float(np.mean(event))))
        return real(self, p, event)

    monkeypatch.setattr(Calibrator, "fit", spy)
    origins = quarterly_origins(ledger)
    sc = rolling_origin(ledger, default_rungs("upworthy", ledger, ["gbm"], baselines=False, recalibrate=True), origins, source="upworthy")
    adm = ledger[ledger["status"] == "admitted"]
    cal_origins = sorted(sc[sc["rung"] == "GBM+cal"]["origin"].unique())
    assert len(fits) == len(cal_origins) >= 3
    for (n_fit, event_rate), t in zip(fits, cal_origins):
        visible = adm[adm["usable_after"] <= t]
        assert n_fit == len(visible)                                                              # exactly the visible rows, one prediction each
        assert event_rate == pytest.approx(float((visible["y"] > 1.96 * visible["s"]).mean()))
    # changing the outcomes of the scored rows changes nothing about the map
    from mootcourt.features import FeatureSpace
    from mootcourt.harness import GBMChallenger, Recalibrated

    vis = adm[adm["usable_after"] <= cal_origins[-1]]
    inner = GBMChallenger(FeatureSpace.fit(vis), vis)
    rec = Recalibrated(inner)
    scored = adm[adm["started_at"] >= cal_origins[-1]].head(30)
    s_star = np.full(len(scored), 0.2)
    a = rec.score_block(scored, scored["y"].to_numpy(), s_star, cal_origins[-1])[0]["p_sig"]
    flipped = scored.assign(y=-scored["y"] * 5)
    b = rec.score_block(flipped, flipped["y"].to_numpy(), s_star, cal_origins[-1])[0]["p_sig"]
    assert np.allclose(a, b)


def test_a_calibrator_with_too_few_events_returns_the_visible_base_rate_and_the_isotonic_map_is_monotone():
    from mootcourt.recalibration import Calibrator

    p = np.linspace(0.01, 0.9, 200)
    none = Calibrator("platt").fit(p, np.zeros(200))
    assert np.allclose(none.transform(p), 0.0)
    rng = np.random.default_rng(0)
    e = (rng.random(200) < p).astype(float)
    for method in ("platt", "isotonic"):
        out = Calibrator(method).fit(p, e).transform(np.linspace(0, 1, 50))
        assert (np.diff(out) >= -1e-12).all() and ((out > 0) & (out < 1)).all()
    with pytest.raises(ValueError):
        Calibrator("nope")


# ============================================================================ positive control (R3 major)
@functools.lru_cache(maxsize=2)
def _planted(strength: float):
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.sources import synthetic

    ledger, _ = synthetic.generate(synthetic.SyntheticConfig(seed=3, n_tests=700, variants_per_test=2, text_effect_strength=strength))
    sc = rolling_origin(ledger, default_rungs("synthetic", ledger), quarterly_origins(ledger), source="synthetic")
    return ledger, sc


def test_a_planted_text_signal_is_admitted_by_the_guard_and_p2_beats_p1_where_it_is_planted():
    _, sc = _planted(4.0)
    sel = pd.DataFrame(sc.attrs["selections"])
    p2 = sel[sel["rung"] == "P2"]
    # the guard admits the precedents where there is something to learn
    assert (p2["lambda"] > 0).any() and p2["guard_held"].notna().all()
    g = sc.pivot_table(index="row_id", columns="rung", values="logscore")
    late = sc[sc["rung"] == "P2"].set_index("row_id")
    gain = (g["P2"] - g["P1"]).reindex(late.index)
    assert gain.mean() > 0.01                                                              # P2 beats P1 out of time, with the family held fixed


def test_without_a_planted_signal_the_guard_holds_lambda_at_zero_nearly_everywhere():
    _, sc = _planted(0.0)
    p2 = pd.DataFrame(sc.attrs["selections"]).query("rung == 'P2'")
    assert (p2["lambda"] == 0).mean() >= 0.8


def test_the_simulate_ledger_command_plants_the_text_signal(tmp_path):
    from mootcourt.cli import app
    from mootcourt.ledger import read_ledger

    quiet, loud = tmp_path / "q.parquet", tmp_path / "l.parquet"
    assert CliRunner().invoke(app, ["simulate", "ledger", "--out", str(quiet), "--n-tests", "200", "--seed", "4"]).exit_code == 0
    res = CliRunner().invoke(app, ["simulate", "ledger", "--out", str(loud), "--n-tests", "200", "--seed", "4", "--text-effect", "3"])
    assert res.exit_code == 0 and "planted text effect 3" in res.output
    a, b = read_ledger(quiet), read_ledger(loud)
    has = b["features_json"].map(lambda j: any(w in json.loads(j)["headline"] for w in ("amazing", "secret", "shocking", "unbelievable",
                                                                                         "heartbreaking", "genius", "incredible", "powerful")))
    assert abs(b.loc[has, "y"].mean() - b.loc[~has, "y"].mean()) > abs(a["y"].mean() - a["y"].mean()) + 1.0


# ============================================================================ admission and proxy sensitivity (R2 major)
def test_admission_on_exposure_only_readmits_low_click_rows_with_a_finite_estimate_and_nothing_else():
    from mootcourt.scale import prelaunch_admission_ledger

    ledger = upworthy_like(40, seed=41)
    ledger.loc[ledger.index[:6], "status"] = "low_clicks"
    ledger.loc[ledger.index[6:9], "status"] = "low_exposure"
    ledger.loc[ledger.index[2], "s"] = np.nan                                         # no standard error: it cannot be scored
    out = prelaunch_admission_ledger(ledger)
    assert (out.loc[ledger.index[[0, 1, 3, 4, 5]], "status"] == "admitted").all()
    assert out.loc[ledger.index[2], "status"] == "low_clicks" and (out.loc[ledger.index[6:9], "status"] == "low_exposure").all()
    assert (ledger["status"] == "low_clicks").sum() == 6                              # the input is left as it was


def test_the_backtest_takes_an_admission_option_and_names_the_ablation():
    from mootcourt.cli import _variant_name, _variant_settings, app

    assert _variant_name(_variant_settings("both", None, None, None, "t", None, None, admission="prelaunch")) == "admission-prelaunch"
    assert _variant_settings("both", None, None, None, "t", None, None) == {}
    res = CliRunner().invoke(app, ["backtest", "--source", "upworthy", "--admission", "sometimes"])
    assert res.exit_code != 0 and "--admission" in res.output


def test_the_exposure_proxy_correlation_is_computed_for_asos_and_adds_the_run_length_where_the_rows_have_one():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("paper_extras_l", ROOT / "scripts" / "paper_extras.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["paper_extras_l"] = mod
    spec.loader.exec_module(mod)
    ledger = upworthy_like(80, seed=42, source="asos")
    ledger["features_json"] = [json.dumps({"metric_id": 1, "final_offset_days": 10.0 + i % 40}) for i in range(len(ledger))]
    out = mod.impressions_effect_correlation(ledger, "asos")
    assert out["n_rows"] == len(ledger) and np.isfinite(out["corr_log_impressions_abs_z"]) and np.isfinite(out["corr_log_run_length_abs_z"])
    assert out["n_rows_with_run_length"] == len(ledger)
    up = mod.impressions_effect_correlation(upworthy_like(80, seed=43), "upworthy")
    assert "corr_log_run_length_abs_z" not in up and np.isfinite(up["corr_log_impressions_abs_z"])


# ============================================================================ adjusted intervals and counts (R1 major, R5 minor)
def test_the_aggregate_carries_bonferroni_adjusted_bounds_wider_than_the_unadjusted_ones():
    from mootcourt import harness_stats as hs

    _, sc = _bt()
    agg = hs.aggregate_scores(sc, GATES, B=100)
    fam = agg["family_size"].iloc[0]
    # round 00 review L (REV-L-018): the family is the intervals the table reports, not its rows
    has_skill = agg["brier_skill_lo"].notna() & ((agg["brier_skill_hi"] - agg["brier_skill_lo"]) > 0)
    assert fam == int(has_skill.sum() + agg["logscore_lo"].notna().sum())
    ok = agg[agg["brier_skill_lo"].notna() & agg["adjusted_lo"].notna()]
    assert len(ok) > 10
    assert (ok["adjusted_lo"] < ok["brier_skill_lo"] + 1e-9).all() and (ok["adjusted_hi"] > ok["brier_skill_hi"] - 1e-9).all()
    p1 = agg[(agg["rung"] == "P1") & (agg["cell"] == "ALL")].iloc[0]
    assert p1["adjusted_lo"] < p1["brier_skill"] < p1["adjusted_hi"] and p1["logscore_adjusted_lo"] < p1["logscore"] < p1["logscore_adjusted_hi"]


def test_the_year_table_adjusts_for_the_family_of_all_its_rows():
    from mootcourt import harness_stats as hs
    from mootcourt.report import row_years

    ledger, sc = _bt()
    yr = hs.by_year(sc, row_years(sc, ledger), GATES, B=40)
    assert {"adjusted_lo", "adjusted_hi", "family_size"} <= set(yr.columns)
    assert yr["family_size"].nunique() == 1 and yr["family_size"].iloc[0] >= len(yr) / 2
    ok = yr[yr["brier_skill_lo"].notna() & yr["adjusted_lo"].notna()]
    assert (ok["adjusted_lo"] < ok["brier_skill_lo"] + 1e-9).all()


def test_the_header_states_tests_admitted_scored_and_why_they_differ():
    from mootcourt.report import build_document

    ledger, sc = _bt()
    doc = build_document(
        sc, ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=GATES, B=30
    )
    h = doc["header"]
    adm = ledger[ledger["status"] == "admitted"]
    assert h["tests_in_ledger"] == ledger["test_id"].nunique() and h["tests_admitted"] == adm["test_id"].nunique()
    assert h["tests_scored"] == sc[sc["rung"] == "P2"]["test_id"].nunique() <= h["tests_admitted"]
    assert "before the first origin with enough visible rows" in h["test_count_definition"]


def test_the_report_header_renders_the_counts_the_guard_and_the_adjusted_columns():
    from mootcourt.report import build_document, render_markdown

    ledger, sc = _bt()
    doc = build_document(
        sc, ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=GATES, B=30
    )
    md = render_markdown(doc)
    assert "- Tests:" in md and "- P2 admission guard: 2.0" in md and "Bonferroni-adjusted bounds" in md and "design_effect" in md


def test_the_changelog_and_the_method_notes_record_the_round_00_changes():
    log = " ".join((ROOT / "CHANGELOG.md").read_text(encoding="utf-8").split())
    method = " ".join((ROOT / "docs" / "method.md").read_text(encoding="utf-8").split())
    for needle in ("P0", "Student-t", "coverage_by_se_ratio", "gate-power", "champion refresh", "recalibrat"):
        assert needle.lower() in log.lower(), needle
    assert "Call 160" in method and "Call 179" in method


# ============================================================================ a far query still gets a forecast (found by the learning curve)
def test_a_query_whose_kernel_underflows_to_zero_for_every_precedent_still_gets_weights():
    """The 0.01 fraction of the learning curve left a few hundred rows and a query so far from all of them (pairwise features, small bandwidth)
    that exp(-d2 / 2h2) was exactly zero for every precedent, and the moments raised 'total precedent weight is zero'."""
    from mootcourt.predictors.p2 import P2Predictor

    adm, space, p1, _ = _p2_fit()
    p2 = P2Predictor().fit(adm, space, p1, lambda_override=0.5, bandwidth_override=0.002)
    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    x = space.transform_text(["zzz qqq xxx nothing like it"], False, reference="www", exposure=20000)[0] + 50.0
    st = p2.neighbor_state(x, "headline_only", origin)
    # round 00 review L (REV-L-021): such a query gets P1's predictive (an empty state, weight zero), never a weight chosen elsewhere on one precedent
    assert len(st.row_ids) == 0 and st.lam == 0.0
    pred = p2.predictive_from_state(st, x, 0.2, "headline_only", origin)
    assert 0.0 < pred.p_sig(0.2) < 1.0 and np.array_equal(pred.pmf, p1.predict(x, 0.2, "headline_only", origin).pmf)


def test_the_challengers_see_the_cell_because_the_ladder_fits_each_cell_apart():
    """On the synthetic archive the three cells have means 2.0, minus 1.0 and 0.5: a model that cannot see the cell is handicapped against the ladder
    by construction (the first rerun showed recalibrated challengers at minus 0.10 Brier skill for that reason)."""
    from mootcourt.features import FeatureSpace
    from mootcourt.harness import GBMChallenger, TextLR
    from mootcourt.sources import synthetic

    ledger, _ = synthetic.generate(synthetic.SyntheticConfig(seed=11, n_tests=600))
    adm = ledger[ledger["status"] == "admitted"]
    space = FeatureSpace.fit(adm)
    g = GBMChallenger(space, adm)
    assert set(g.cells) == {"headline_only", "image_only", "both"}
    x = space.transform_text(["a secret dog story"], False, exposure=20000)[0]
    origin = adm["usable_after"].max()
    means = {c: g.predict(x, 1.5, c, origin).mean() for c in g.cells}
    assert means["headline_only"] > means["image_only"] + 0.3                       # the same headline, forecast by the cell it is tested in
    t = TextLR(adm)
    assert set(t.cells) == set(g.cells) and t._X.shape[1] == len(t.vec.vocabulary_) + 3
    scored = adm.head(40)
    p = t.raw_p_sig(scored, np.full(40, 1.5))
    by_cell = pd.Series(p, index=scored["cell"].to_numpy()).groupby(level=0).mean()
    assert by_cell["headline_only"] > by_cell["image_only"]


# ============================================================================ review J notes and the walkthrough's CLI defects (16, 17)
def _scratch_root(tmp_path, ledger, gates=GATES):
    from mootcourt.ledger import write_ledger

    root = tmp_path / "root"
    write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "reports" / "gates.json").write_text(json.dumps(gates))
    return root


def test_a_trigger_run_combined_with_another_ablation_scores_and_says_released_rows_are_not_computed(tmp_path):
    """REV-J-001: --drop-trigger with --features text used to exit 2 after scoring because the base run differs."""
    from mootcourt.cli import app
    from mootcourt.sources import synthetic

    ledger, _ = synthetic.generate(synthetic.SyntheticConfig(seed=2, n_tests=150))
    root = _scratch_root(tmp_path, ledger)
    env = {"MOOTCOURT_DATA_ROOT": str(root)}
    main = CliRunner().invoke(app, ["backtest", "--source", "synthetic", "--bootstrap", "20"], env=env)
    assert main.exit_code == 0, main.output
    flags = ["backtest", "--source", "synthetic", "--bootstrap", "20", "--drop-trigger", "support"]
    both = CliRunner().invoke(app, [*flags, "--features", "text"], env=env)
    assert both.exit_code == 0, both.output
    doc = json.loads(next((root / "reports" / "ablations").glob("*drop-trigger-support*features-text*.json")).read_text()
                     if list((root / "reports" / "ablations").glob("*drop-trigger-support*features-text*.json"))
                     else next((root / "reports" / "ablations").glob("*features-text*drop-trigger-support*.json")).read_text())
    assert "released_rows" not in doc["tables"] and "not computed" in doc["notes"]["released_rows_skipped"]
    alone = CliRunner().invoke(app, flags, env=env)
    only = next((root / "reports" / "ablations").glob("*--drop-trigger-support.json"))
    assert alone.exit_code == 0 and "released_rows" in json.loads(only.read_text())["tables"]


def test_env_long_options_are_resolved_by_unique_prefix_as_gnu_env_reads_them(env_setup_l):
    stdio, base, info, inside, ok = env_setup_l
    for command in (["env", "--spl", inside], ["env", "--s=" + inside], ["env", "--uns", "SHELL", "sh", "-c", inside],
                    ["env", "--ch", "/tmp", "sh", "-c", inside], ["env", "--unset", "SHELL", "sh", "-c", inside]):
        with pytest.raises(base.SimulatorError, match="data root"):
            stdio.StdioSimulator(command, info)
    assert stdio._env_long("--spl") == "--split-string" and stdio._env_long("--d") is None and stdio._env_long("--zzz") is None
    stdio.StdioSimulator(["env", "--ignore-environment", "python3", ok.split()[-1]], info)         # a harmless command is still accepted


@pytest.fixture
def env_setup_l(imp, tmp_path, monkeypatch):
    from test_simulators import _info

    root = tmp_path / "dataroot"
    root.mkdir()
    (root / "agent.py").write_text("print('null')\n")
    ok = tmp_path / "ok.py"
    ok.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    return imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators"), _info(imp), f"python3 {root / 'agent.py'}", f"python3 {ok}"


def test_the_paper_extras_import_the_benchmark_word_list_and_report_the_range_over_query_seeds():
    import importlib.util
    import sys

    from mootcourt.benchmark import HEADLINE_WORDS

    spec = importlib.util.spec_from_file_location("paper_extras_l2", ROOT / "scripts" / "paper_extras.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["paper_extras_l2"] = mod
    spec.loader.exec_module(mod)
    assert mod.TAIL_WORDS is HEADLINE_WORDS
    out = mod.top_m_tail_share(sizes=(300,), top_m=10, n_queries=3, seed=3, n_seeds=4)
    row = out["by_size"][0]
    lo, hi = row["mean_range_over_seeds"]["share_p2_weight"]
    assert row["n_query_seeds"] == 4 and lo <= row["share_p2_weight"]["mean"] <= hi and out["inputs"]["seeds"] == [3, 4, 5, 6]


def test_the_decision_table_prints_small_regrets_with_three_decimals():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("build_tables_l", ROOT / "paper" / "build_tables.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_tables_l"] = mod
    spec.loader.exec_module(mod)
    assert mod.fr(0.06) == "0.060" and mod.fr(586.07) == "586.1" and mod.fr(None) == ""


def test_a_backtest_on_a_ledger_too_small_to_fit_ends_in_a_one_line_error_naming_the_minimum(tmp_path):
    from mootcourt.cli import app
    from mootcourt.harness import MIN_FIT_ROWS
    from mootcourt.sources import synthetic

    ledger, _ = synthetic.generate(synthetic.SyntheticConfig(seed=5, n_tests=8, variants_per_test=1))
    assert (ledger["status"] == "admitted").sum() < MIN_FIT_ROWS
    root = _scratch_root(tmp_path, ledger)
    res = CliRunner().invoke(app, ["backtest", "--source", "synthetic", "--bootstrap", "20"], env={"MOOTCOURT_DATA_ROOT": str(root)})
    assert res.exit_code == 2 and "KeyError" not in res.output and "too small" in res.output and str(MIN_FIT_ROWS) in res.output


def test_a_card_without_a_cell_on_a_ledger_keyed_by_metric_fails_and_lists_the_cells():
    from mootcourt import card as card_mod
    from mootcourt.bundle import fit_bundle
    from mootcourt.sources import synthetic

    ledger, _ = synthetic.generate(synthetic.SyntheticConfig(seed=6, n_tests=120))
    ledger = ledger.assign(cell=ledger["cell"].map({"headline_only": "metric_1", "image_only": "metric_2", "both": "metric_2"}))
    now = ledger["usable_after"].max().to_pydatetime() + dt.timedelta(days=1)
    bundle = fit_bundle(ledger, "synthetic", "20261103-xxxxxxxxxxxx")
    req = card_mod.CardRequest(source="synthetic", headline="a b", image_changed=False, impressions=1000, origin=now)
    with pytest.raises(ValueError, match="metric_1, metric_2.*--cell"):
        card_mod.build_card(bundle, req, reliability=None, now=now)
    named = card_mod.build_card(bundle, card_mod.CardRequest(source="synthetic", headline="a b", image_changed=False, impressions=1000, origin=now,
                                                              cell="metric_1"), reliability=None, now=now)
    assert named.cell == "metric_1"
