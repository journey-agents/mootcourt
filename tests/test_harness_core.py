"""T-013 contracts: rolling origin, leakage guard, per-row scores."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

UTC = dt.timezone.utc
SCORE_COLUMNS = ["row_id", "test_id", "cell", "period", "origin", "rung", "y", "s", "logscore", "crps", "p_sig",
                 "p_win", "brier_event", "event", "direction_correct", "lo80", "hi80", "lo90", "hi90",
                 "abstain", "abstain_reasons", "p_theta_posterior", "fallback_global"]


def _ledger(make_synth, **kw):
    base = dict(seed=91, n_tests=240, variants_per_test=2, cell_params={"headline_only": (1.0, 2.0)}, s_scale=2.0)
    base.update(kw)
    return make_synth(**base)[0]


class _SpyFactory:
    """Records every frame handed to fit, returns a real P0 fitted on it."""

    def __init__(self, imp):
        self.imp, self.calls = imp, []

    def __call__(self, rows, origin):
        self.calls.append((origin, rows.copy()))
        return self.imp("mootcourt.predictors.p0").P0Predictor().fit(rows)


def test_quarterly_origins_are_quarter_starts_covering_the_data(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth)
    origins = harness.quarterly_origins(ledger)
    assert all(o.day == 1 and o.month in (1, 4, 7, 10) and o.hour == 0 for o in origins)
    assert str(origins[0].tz) == "UTC"
    assert origins[0] <= ledger["started_at"].min() and origins[-1] <= ledger["started_at"].max()
    assert origins == sorted(origins)


def test_fit_sees_only_visible_rows_and_scored_rows_are_unseen(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth)
    spy = _SpyFactory(imp)
    scores = harness.rolling_origin(ledger, {"P0": spy}, harness.quarterly_origins(ledger))
    assert spy.calls
    for origin, rows in spy.calls:
        assert (rows["usable_after"] <= origin).all(), "a row with usable_after > origin reached fit"
        assert (rows["status"] == "admitted").all()
        scored_ids = set(scores.loc[scores["origin"] == origin, "row_id"])
        assert scored_ids.isdisjoint(set(rows["row_id"])), "a scored row was in the fit set"


def test_scored_rows_have_started_at_inside_the_origin_quarter(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth)
    origins = harness.quarterly_origins(ledger)
    scores = harness.rolling_origin(ledger, {"P0": _SpyFactory(imp)}, origins)
    started = ledger.set_index("row_id")["started_at"]
    for o in origins[:-1]:
        nxt = origins[origins.index(o) + 1]
        got = scores.loc[scores["origin"] == o, "row_id"]
        assert ((started[got] >= o) & (started[got] < nxt)).all()


def test_leaky_factory_is_caught_by_the_audit(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth)

    def leaky(rows, origin):
        return imp("mootcourt.predictors.p0").P0Predictor().fit(ledger)   # ignores visibility

    with pytest.raises(harness.LeakageError):
        harness.rolling_origin(ledger, {"P0": leaky}, harness.quarterly_origins(ledger), audit_fit_rows=True)


def test_assert_no_leakage_both_directions(imp, ledger_builder, origin):
    harness = imp("mootcourt.harness")
    fit = ledger_builder(n=5, seed=1)
    scored = ledger_builder(n=3, seed=2, id_prefix="s")
    fit["usable_after"] = origin - pd.Timedelta(days=1)
    scored["usable_after"] = origin + pd.Timedelta(days=3)
    harness.assert_no_leakage(fit, scored, origin)
    bad_fit = fit.copy()
    bad_fit.loc[bad_fit.index[0], "usable_after"] = origin + pd.Timedelta(microseconds=1)
    with pytest.raises(harness.LeakageError):
        harness.assert_no_leakage(bad_fit, scored, origin)
    bad_scored = scored.copy()
    bad_scored.loc[bad_scored.index[0], "usable_after"] = origin                     # at the origin: already visible
    with pytest.raises(harness.LeakageError):
        harness.assert_no_leakage(fit, bad_scored, origin)
    overlap = scored.copy()
    overlap["row_id"] = fit["row_id"].iloc[: len(scored)].to_numpy()
    with pytest.raises(harness.LeakageError):
        harness.assert_no_leakage(fit, overlap, origin)


def test_rolling_origin_raises_when_a_scored_row_was_already_usable(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth).copy()
    origins = harness.quarterly_origins(ledger)
    idx = ledger.index[(ledger["started_at"] >= origins[2]) & (ledger["started_at"] < origins[3])][0]
    ledger.loc[idx, "usable_after"] = origins[2]       # corrupt: usable at the origin that scores it
    with pytest.raises(harness.LeakageError):
        harness.rolling_origin(ledger, {"P0": _SpyFactory(imp)}, origins)


def test_score_table_columns_and_value_checks(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth)
    scores = harness.rolling_origin(ledger, {"P0": _SpyFactory(imp)}, harness.quarterly_origins(ledger))
    assert set(SCORE_COLUMNS) <= set(scores.columns)
    assert np.isfinite(scores["logscore"]).all() and (scores["crps"] >= 0).all()
    assert scores["p_sig"].between(0, 1).all() and scores["p_win"].between(0, 1).all()
    expected_event = scores["y"] > 1.96 * scores["s"]
    assert (scores["event"].astype(bool) == expected_event).all()
    np.testing.assert_allclose(scores["brier_event"], (scores["p_sig"] - scores["event"].astype(float)) ** 2, atol=1e-12)
    assert ((scores["lo90"] <= scores["lo80"]) & (scores["hi80"] <= scores["hi90"])).all()


def test_first_origin_abstains_for_missing_reliability_report(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth)
    scores = harness.rolling_origin(ledger, {"P0": _SpyFactory(imp)}, harness.quarterly_origins(ledger))
    first = scores[scores["origin"] == scores["origin"].min()]
    assert first["abstain"].all()
    assert first["abstain_reasons"].str.contains("reliability").all()
    assert getattr(harness, "BURN_IN_NOTE", "") and "burn-in" in harness.BURN_IN_NOTE.lower()


def test_small_visible_cell_falls_back_to_global_and_is_flagged(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = _ledger(make_synth, cell_params={"headline_only": (1.0, 2.0), "image_only": (0.0, 2.0)}).copy()
    # make image_only appear for the first time in a late origin so it has < 2 visible rows
    origins = harness.quarterly_origins(ledger)
    late = origins[-2]
    ledger.loc[ledger["cell"] == "image_only", "started_at"] = late + pd.Timedelta(days=5)
    ledger.loc[ledger["cell"] == "image_only", "usable_after"] = late + pd.Timedelta(days=12)
    ledger.loc[ledger["cell"] == "image_only", "final_read_at"] = late + pd.Timedelta(days=12)
    scores = harness.rolling_origin(ledger, {"P0": _SpyFactory(imp)}, origins)
    img = scores[scores["cell"] == "image_only"]
    assert len(img) == (ledger["cell"] == "image_only").sum(), "no row may be dropped silently"
    assert img["fallback_global"].all()


@pytest.mark.slow
def test_ladder_orders_on_known_truth(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=92, n_tests=900, variants_per_test=2, text_effect_strength=3.0,
                        cell_params={"headline_only": (1.0, 1.0)}, s_scale=2.5)[0]
    scores = harness.rolling_origin(ledger, harness.default_rungs("synthetic"), harness.quarterly_origins(ledger))
    mean = scores.groupby("rung")["logscore"].mean()
    assert mean["P1"] > mean["P0"], mean
    assert mean["P2"] > mean["P1"], mean


@pytest.mark.slow
def test_p3_rung_present_only_when_team_forecasts_exist(imp, make_synth):
    harness = imp("mootcourt.harness")
    with_team = make_synth(seed=93, n_tests=300, variants_per_test=2, team_forecaster_sd=1.0)[0]
    without = make_synth(seed=93, n_tests=300, variants_per_test=2)[0]
    s1 = harness.rolling_origin(with_team, harness.default_rungs("synthetic", ledger=with_team), harness.quarterly_origins(with_team))
    s2 = harness.rolling_origin(without, harness.default_rungs("synthetic", ledger=without), harness.quarterly_origins(without))
    assert "P3" in set(s1["rung"]) and "P3" not in set(s2["rung"])


@pytest.mark.slow
def test_gbm_challenger_adds_a_rung_with_out_of_origin_residual_sd(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=94, n_tests=300, variants_per_test=2)[0]
    rungs = harness.default_rungs("synthetic", ledger=ledger, challenger="gbm")
    scores = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger))
    gbm = scores[scores["rung"] == "GBM"]
    assert len(gbm) > 0 and np.isfinite(gbm["logscore"]).all()
