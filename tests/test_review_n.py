"""Chunk N (T-056): the fixes for the review of chunk L (REV-L-001 to REV-L-028).

One group per finding. The fixtures are the small Upworthy-shaped ledgers of tests/test_review_l.py.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_review_l import GATES, fresh_report, upworthy_like
from typer.testing import CliRunner

UTC = dt.timezone.utc


# ============================================================================ REV-L-002: the log score is the analytic t marginal
def test_the_scored_log_score_is_the_analytic_t_marginal_on_random_rows_including_rows_beyond_the_grid_edge():
    from mootcourt.predictors.base import Predictive, build_grid
    from mootcourt.predictors.p1 import marginal_logpdf_rows

    rng = np.random.default_rng(0)
    loc, scale, nu = 0.05, 0.27, 3.0
    pred = Predictive.from_t(build_grid(loc, scale, y_min=-1.0, y_max=1.0), loc, scale, nu)
    y = np.concatenate([rng.normal(loc, 0.6, 40), [-5.6, 4.0, loc + 60 * scale]])  # the last three are far beyond the grid
    s = rng.uniform(0.1, 0.5, y.size)
    got = pred.logscore(y, s)
    want = marginal_logpdf_rows(y, s * s, loc, scale, nu)
    assert np.allclose(got, want, atol=1e-12)
    assert got[-3] > -12.0  # on the grid this row scored about -43 (the Gaussian decay of the edge)
    # a Predictive without a spec (a hand-built grid) keeps its exact grid mixture
    grid = Predictive(pred.theta, pred.pmf)
    assert np.isfinite(grid.logscore(0.1, 0.2)) and grid.spec is None


def test_p1_p2_card_and_join_score_the_same_analytic_quantity():
    from mootcourt.predictors.base import Predictive
    from mootcourt.predictors.p1 import P1Predictor, marginal_logpdf_rows

    ledger = upworthy_like(260, seed=9, signal=0.9, heavy=True)
    adm = ledger[ledger["status"] == "admitted"]
    p1 = P1Predictor(nu_grid=(3,)).fit(adm)
    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    pred = p1.predict(None, 0.2, "headline_only", origin)
    par = p1.cell_params("headline_only", "2015Q1")
    rebuilt = Predictive.from_spec(pred.spec)
    for y in (-3.0, 0.0, 0.4, 7.0):
        a = pred.logscore(y, 0.25)
        assert a == pytest.approx(float(marginal_logpdf_rows(y, 0.25**2, pred.spec["location"], pred.spec["scale"], 3.0)), abs=1e-12)
        assert rebuilt.logscore(y, 0.25) == pytest.approx(a, abs=1e-12)
    assert par["nu"] == 3.0


def test_p0_log_score_is_unchanged_by_the_analytic_route():
    from mootcourt.predictors.p0 import P0Predictor

    ledger = upworthy_like(100, seed=3)
    adm = ledger[ledger["status"] == "admitted"]
    p0 = P0Predictor().fit(adm)
    origin = pd.Timestamp("2014-04-01", tz="UTC")
    f = p0.forecast("headline_only", origin)
    y = 0.3
    assert p0.logscore(y, "headline_only", origin) == pytest.approx(-0.5 * (y - f.mean) ** 2 / f.var - 0.5 * math.log(2 * math.pi * f.var))


# ============================================================================ REV-L-001: outcomes without a test id
def test_the_skill_interval_leaves_out_outcomes_without_a_test_id_and_reports_none_when_none_remain():
    from mootcourt.reliability import skill_interval

    rng = np.random.default_rng(1)
    b0 = rng.uniform(0.05, 0.15, 60)
    b = b0 - 0.01
    ids = np.array([f"t{i // 2}" for i in range(60)], dtype=object)
    assert skill_interval(b, b0, ids)[2] == 30
    mixed = ids.copy()
    mixed[:20] = None
    lo, hi, n_tests = skill_interval(b, b0, mixed)
    assert n_tests == 20 and lo is not None and lo < hi
    assert skill_interval(b, b0, np.array([None] * 60, dtype=object)) == (None, None, None)
    assert skill_interval(b, b0, np.array(["t0"] * 60, dtype=object))[:2] == (None, None)  # one test cannot be resampled


def test_a_window_that_mixes_legacy_and_new_outcomes_is_rewritten_and_a_legacy_window_says_no_interval():
    from mootcourt import card as card_mod
    from mootcourt.reliability import build_reliability

    now = dt.datetime(2014, 8, 1, tzinfo=UTC)

    def outcome(i, test_id, key=True):
        o = {
            "cell": "headline_only",
            "at": (now - dt.timedelta(days=i)).isoformat(),
            "logscore": -1.0,
            "p0_logscore": -1.1,
            "brier": 0.08,
            "p0_brier": 0.09,
        }
        if key:
            o["test_id"] = test_id
        return o

    legacy = [outcome(i, None, key=(i % 2 == 0)) for i in range(1, 13)]
    rep = build_reliability(None, legacy, now, source="upworthy")["cells"]["headline_only"]
    assert rep["n"] == 12 and rep["n_tests"] is None and rep["brier_skill_lo"] is None
    mixed = legacy + [outcome(i, f"t{i}") for i in range(13, 25)]
    rep = build_reliability(None, mixed, now, source="upworthy")["cells"]["headline_only"]
    assert rep["n"] == 24 and rep["n_tests"] == 12 and rep["brier_skill_lo"] is not None
    ledger = upworthy_like(100, seed=2)
    row = ledger[(ledger["started_at"] >= "2014-04-01") & (ledger["cell"] == "headline_only")].iloc[0]
    from test_review_l import _issued_card

    bundle, req, origin = _issued_card(ledger, row)
    text = card_mod.to_markdown(
        card_mod.build_card(
            bundle,
            req,
            reliability=fresh_report(origin, n_tests=None, brier_skill_lo=None, brier_skill_hi=None),
            now=origin.to_pydatetime(),
            gates=GATES,
        )
    )
    assert "no interval is recorded" in text


# ============================================================================ REV-L-003, 017, 028: gates by test
def test_the_by_row_decidable_column_is_not_computed_against_gates_that_count_tests():
    from test_review_l import _bt

    from mootcourt import harness_stats as hs

    _, sc = _bt()
    by_test = {**GATES, "interval": {"by": "test", "level": 0.9}}
    row = hs.aggregate_scores(sc[sc["rung"] == "P1"], by_test, B=20).query("cell == 'ALL'").iloc[0]
    assert row["decidable"] == hs.BY_ROW_NOT_COMPUTED and row["decidable_research"] == hs.BY_ROW_NOT_COMPUTED
    assert row["decidable_by_tests"].startswith(("decidable", "undecidable"))
    flat = hs.aggregate_scores(sc[sc["rung"] == "P1"], GATES, B=20).query("cell == 'ALL'").iloc[0]
    assert flat["decidable"].startswith(("decidable", "undecidable"))  # a per-row gates file still has its per-row verdict


def test_the_second_opinion_table_and_the_verdict_label_the_unit_of_the_gates():
    from test_review_l import _bt

    from mootcourt.card import gate_verdict
    from mootcourt.report import build_document

    ledger, sc = _bt()
    assert "simulated per row" in gate_verdict(60, 0.0, 0.1, GATES, 0.09)
    assert "simulated per row" not in gate_verdict(60, 0.0, 0.1, {**GATES, "interval": {"by": "test"}}, 0.09)
    doc = build_document(
        sc, ledger=ledger, source="upworthy", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0, gates=GATES, B=20
    )
    assert doc["tables"]["aggregate"]


# ============================================================================ REV-L-004, 020: the clustered null reproduces the design effect
def test_the_clustered_null_draws_reproduce_the_observed_design_effect():
    from mootcourt import harness_stats as hs

    rng = np.random.default_rng(5)
    tests = np.repeat(np.arange(500), 4)
    p = np.full(tests.size, 0.09)
    z = rng.standard_normal(500)
    e = (np.sqrt(0.4) * z[tests] + np.sqrt(0.6) * rng.standard_normal(tests.size) < hs.special.ndtri(p)).astype(float)
    target = hs.design_effect(p, e, tests)["design_effect"]
    assert target > 1.3
    rho = hs.latent_rho_for_design_effect(p, tests, target)
    codes = pd.factorize(tests)[0]
    rng2 = np.random.default_rng(99)
    vals = []
    for _ in range(80):
        draw = (np.sqrt(rho) * rng2.standard_normal(500)[codes] + np.sqrt(1 - rho) * rng2.standard_normal(tests.size) < hs.special.ndtri(p)).astype(
            float
        )
        vals.append(hs.design_effect(p, draw, tests)["design_effect"])
    assert np.mean(vals) == pytest.approx(target, rel=0.08)
    old = hs.design_effect(p, e, tests)["icc"]  # the binary icc used as the latent one gave far less
    assert rho > old
    assert hs.latent_rho_for_design_effect(p, tests, 1.0) == 0.0


def test_the_aggregate_reports_the_latent_correlation_beside_the_binary_one():
    from test_review_l import _bt

    from mootcourt import harness_stats as hs

    _, sc = _bt()
    row = hs.aggregate_scores(sc[sc["rung"] == "P1"], GATES, B=20).query("cell == 'ALL'").iloc[0]
    assert row["latent_rho"] >= row["icc"] >= 0.0


# ============================================================================ REV-L-008: the gate simulation has dependence within a test
def test_the_gate_simulation_draws_dependent_rows_within_a_test_and_power_falls_with_the_correlation():
    from mootcourt import simulate as sim

    kw = dict(reps=150, B=150, seed=3, rows_per_test=3.5, level=0.90)
    independent = sim.gate_power(175, 0.10, base=0.09, icc=0.0, **kw)
    clustered = sim.gate_power(175, 0.10, base=0.09, icc=0.13, **kw)
    assert independent > clustered + 0.08
    rho = sim.latent_rho_for_icc(0.09, 0.13)
    from scipy import special

    rng = np.random.default_rng(0)
    g = rng.standard_normal(200000)
    a = (np.sqrt(rho) * g + np.sqrt(1 - rho) * rng.standard_normal(200000) < special.ndtri(0.09)).astype(float)
    b = (np.sqrt(rho) * g + np.sqrt(1 - rho) * rng.standard_normal(200000) < special.ndtri(0.09)).astype(float)
    assert np.corrcoef(a, b)[0, 1] == pytest.approx(0.13, abs=0.01)  # the latent correlation gives the stated binary one


def test_write_gates_records_the_dependence_it_used_per_base_rate(tmp_path):
    from mootcourt import simulate as sim

    doc = sim.write_gates(
        tmp_path / "g.json",
        base_rates=[0.09, 0.14],
        reps=30,
        B=30,
        seed=1,
        grid=[25, 100, 400, 1600],
        with_table=False,
        rows_per_test={b: v[0] for b, v in sim.SOURCE_DEPENDENCE.items()},
        icc={b: v[1] for b, v in sim.SOURCE_DEPENDENCE.items()},
    )
    e1, e2 = doc["by_base_rate"]["0.09"], doc["by_base_rate"]["0.14"]
    assert (e1["rows_per_test"], e1["icc"]) == (3.5, 0.13) and (e2["rows_per_test"], e2["icc"]) == (5.0, 0.67)
    assert 0 < e1["latent_rho"] < e2["latent_rho"] < 1 and doc["interval"]["by"] == "test"


# ============================================================================ REV-L-005: the leakage spies cover every challenger
@pytest.fixture(scope="module")
def visible_and_future():
    ledger = upworthy_like(120, seed=35, span_days=600)
    adm = ledger[ledger["status"] == "admitted"]
    t = pd.Timestamp("2014-04-01", tz="UTC")
    return ledger, adm, t


def test_a_challenger_built_from_rows_that_are_not_yet_usable_raises_in_the_audited_fit(visible_and_future):
    from mootcourt.features import FeatureSpace
    from mootcourt.harness import GBMChallenger, LeakageError, LocalEB, TextLR, _audit_fits

    ledger, adm, t = visible_and_future
    future = adm[adm["usable_after"] > t]
    assert len(future) > 20
    space = FeatureSpace.fit(adm[adm["usable_after"] <= t])
    with _audit_fits(t):
        for build in (lambda: TextLR(future), lambda: LocalEB(space, future), lambda: GBMChallenger(space, future)):
            with pytest.raises(LeakageError):
                build()
        TextLR(adm[adm["usable_after"] <= t])  # the visible rows are fine
    TextLR(future)  # and the wrapping is undone afterwards


def test_a_mutation_that_hands_a_challenger_every_admitted_row_fails_the_run(monkeypatch, visible_and_future):
    from mootcourt import harness
    from mootcourt.harness import LeakageError, default_rungs, quarterly_origins, rolling_origin

    ledger, adm, t = visible_and_future
    rungs = default_rungs("upworthy", ledger, ["text_lr"], baselines=False)
    rungs["text_lr"] = lambda rows, origin: harness.TextLR(adm)  # the mutation: the full ledger, whatever the origin
    with pytest.raises(LeakageError):
        rolling_origin(ledger, rungs, quarterly_origins(ledger)[:3], source="upworthy")


def test_the_recalibration_is_fit_on_visible_rows_for_all_three_challengers(monkeypatch, visible_and_future):
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.recalibration import Calibrator

    ledger, adm, t = visible_and_future
    fits = []
    real = Calibrator.fit
    monkeypatch.setattr(Calibrator, "fit", lambda self, p, e: (fits.append((len(p), float(np.mean(e)))), real(self, p, e))[1])
    sc = rolling_origin(
        ledger,
        default_rungs("upworthy", ledger, ["gbm", "local_eb", "text_lr"], baselines=False, recalibrate=True),
        quarterly_origins(ledger),
        source="upworthy",
    )
    origins = sorted(sc[sc["rung"] == "GBM+cal"]["origin"].unique())
    assert len(fits) == 3 * len(origins)
    for k, (n_fit, rate) in enumerate(fits):
        visible = adm[adm["usable_after"] <= origins[k // 3]]
        assert n_fit <= len(visible)
        if n_fit == len(visible):
            assert rate == pytest.approx(float((visible["y"] > 1.96 * visible["s"]).mean()))


def test_flipping_the_outcomes_of_later_rows_does_not_move_the_recalibrated_probabilities_of_earlier_origins(visible_and_future):
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin

    ledger, adm, t = visible_and_future
    origins = quarterly_origins(ledger)
    last = origins[-1]
    flipped = ledger.copy()
    late = flipped["started_at"] >= last
    flipped.loc[late, "y"] = -5.0 * flipped.loc[late, "y"] + 3.0
    kw = dict(source="upworthy")
    a = rolling_origin(ledger, default_rungs("upworthy", ledger, ["gbm", "local_eb", "text_lr"], baselines=False, recalibrate=True), origins, **kw)
    b = rolling_origin(flipped, default_rungs("upworthy", flipped, ["gbm", "local_eb", "text_lr"], baselines=False, recalibrate=True), origins, **kw)
    for rung in ("GBM+cal", "local_eb+cal", "text_lr+cal"):
        pa = a[a["rung"] == rung].set_index("row_id")["p_sig"]
        pb = b[b["rung"] == rung].set_index("row_id")["p_sig"].reindex(pa.index)
        assert np.allclose(pa, pb)  # visible-only fits: the probabilities cannot depend on later outcomes


# ============================================================================ REV-L-006, 007, 011: champion refresh
def _summary(skill, lo, hi):
    return {"brier_skill": skill, "brier_skill_lo": lo, "brier_skill_hi": hi, "n": 100, "n_tests": 100}


def test_a_refit_of_older_data_with_a_newer_fit_time_does_not_take_the_champion_back(tmp_path):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    reg.register_model(
        "s", "a", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-01T00:00:00+00:00", data_through="2014-01-01T00:00:00+00:00"
    )
    assert (
        reg.register_model(
            "s", "b", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-02T00:00:00+00:00", data_through="2014-06-01T00:00:00+00:00"
        )
        == "champion"
    )  # strictly newer data: a refresh
    assert (
        reg.register_model(
            "s", "c", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-03T00:00:00+00:00", data_through="2014-02-01T00:00:00+00:00"
        )
        == "challenger"
    )  # older data, later fit time
    assert reg.get_champion("s") == "b"
    last = reg._read()["s"]["history"][-1]
    assert last["event"] == "challenger_set" and "older data" in last["reason"]
    assert (
        reg.register_model("s", "d", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-04T00:00:00+00:00") == "challenger"
    )  # recency unknown


def test_the_fit_time_only_breaks_a_tie_between_equal_data(tmp_path):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    same = "2014-06-01T00:00:00+00:00"
    reg.register_model("s", "a", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-02T00:00:00+00:00", data_through=same)
    assert (
        reg.register_model("s", "b", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-01T00:00:00+00:00", data_through=same)
        == "challenger"
    )
    assert (
        reg.register_model("s", "c", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-03T00:00:00+00:00", data_through=same)
        == "champion"
    )


def test_a_same_method_refit_without_a_backtest_is_pending_until_the_summary_is_attached(tmp_path):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    reg.register_model(
        "s", "a", _summary(0.10, 0.08, 0.12), method_id="A", fitted_at="2026-11-01T00:00:00+00:00", data_through="2014-01-01T00:00:00+00:00"
    )
    role = reg.register_model("s", "b", None, method_id="A", fitted_at="2026-11-02T00:00:00+00:00", data_through="2014-06-01T00:00:00+00:00")
    assert role == "challenger" and reg.get_champion("s") == "a" and reg._read()["s"]["pending_refresh"] == "b"
    reg.attach_summary("s", "b", _summary(0.11, 0.09, 0.13))  # fine: the refresh goes through
    assert reg.get_champion("s") == "b" and reg._read()["s"]["history"][-1]["event"] == "champion_refreshed"
    reg.register_model("s", "c", None, method_id="A", fitted_at="2026-11-03T00:00:00+00:00", data_through="2014-09-01T00:00:00+00:00")
    reg.attach_summary("s", "c", _summary(-0.20, -0.25, -0.15))  # clearly worse: refused, and the history says why
    last = reg._read()["s"]["history"][-1]
    assert reg.get_champion("s") == "b" and last["event"] == "refresh_refused" and "entirely below" in last["reason"]


def test_a_different_method_is_a_challenger_with_the_reason_in_the_history(tmp_path):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    reg.register_model(
        "s", "a", _summary(0.0, -0.01, 0.01), method_id="A", fitted_at="2026-11-01T00:00:00+00:00", data_through="2014-01-01T00:00:00+00:00"
    )
    reg.register_model(
        "s", "b", _summary(0.5, 0.4, 0.6), method_id="B", fitted_at="2026-11-02T00:00:00+00:00", data_through="2014-06-01T00:00:00+00:00"
    )
    assert "different method" in reg._read()["s"]["history"][-1]["reason"]


# ============================================================================ the lows
def test_a_huge_exposure_is_one_line_error_not_an_overflow(tmp_path):
    from fastapi.testclient import TestClient

    from mootcourt.bundle import MAX_EXPOSURE
    from mootcourt.service import CardPayload

    with pytest.raises(Exception, match="less than or equal"):
        CardPayload(source="upworthy", impressions=10**13)
    ledger = upworthy_like(60, seed=4)
    from test_review_l import _bundle

    bundle = _bundle(ledger, pd.Timestamp("2014-07-01", tz="UTC"))
    with pytest.raises(ValueError, match="at most"):
        bundle.s_star("headline_only", 2 * MAX_EXPOSURE)
    assert TestClient is not None


def test_mcp_refusals_reach_the_client_as_their_one_line_message(tmp_path):
    import asyncio

    from test_review_l import _bundle

    from mootcourt.bundle import save_bundle
    from mootcourt.mcp_server import build_server
    from mootcourt.registry import Registry

    ledger = upworthy_like(120, seed=4)
    bundle = _bundle(ledger, pd.Timestamp("2014-07-01", tz="UTC"))
    save_bundle(bundle, tmp_path / "models")
    Registry(tmp_path / "models").register_model("upworthy", bundle.model_id)
    (tmp_path / "reports").mkdir()
    server = build_server(tmp_path / "models", tmp_path / "reports", lambda: dt.datetime(2014, 7, 2, tzinfo=UTC))
    with pytest.raises(Exception) as exc:
        asyncio.run(server.call_tool("get_card", {"source": "upworthy", "impressions": 1000, "row_id": "x", "test_id": "t"}))
    assert "not both" in str(exc.value) and type(exc.value).__name__ == "ToolError"  # the message reaches the client, not an opaque error


def test_the_simulator_request_carries_the_variant_exposure():
    import inspect

    from mootcourt import cli

    assert "planned_n_var=r.impressions_variant or r.impressions" in inspect.getsource(cli._attach_simulator)


def test_without_a_reference_headline_the_pair_features_are_neutral_too():
    from mootcourt.features import FeatureSpace

    adm = upworthy_like(150, seed=32)
    sp = FeatureSpace.fit(adm)
    x = sp.transform_text(["amazing dog story about the city"], False, exposure=20000)[0]
    n_pair = 3
    assert np.allclose(x[-n_pair:], 0.0, atol=1e-9)  # the fit-set means, a standardized zero
    with_ref = sp.transform_text(["amazing dog story about the city"], False, exposure=20000, reference="why the river")[0]
    assert not np.allclose(with_ref[-n_pair:], 0.0)


def test_the_learning_curve_runs_on_the_admission_it_records(tmp_path):
    from mootcourt.cli import app
    from mootcourt.ledger import write_ledger

    ledger = upworthy_like(150, seed=8, span_days=700)
    ledger.loc[ledger.index[:30], "status"] = "low_clicks"
    root = tmp_path / "root"
    write_ledger(ledger, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    res = CliRunner().invoke(
        app,
        ["backtest", "--source", "upworthy", "--admission", "prelaunch", "--learning-curve", "0.5,1", "--seeds", "1", "--bootstrap", "20"],
        env={"MOOTCOURT_DATA_ROOT": str(root)},
    )
    assert res.exit_code == 0, res.output
    assert "admission on exposure only: 30 contrasts admitted" in res.output
    doc = json.loads(next((root / "reports").glob("learning-curve-upworthy-*.json")).read_text())
    assert "--admission prelaunch" in doc["command"]


def test_a_row_id_must_belong_to_the_cards_source_and_carry_no_control_character():
    from mootcourt.ledger import resolve_row_id

    assert resolve_row_id("upworthy", "upworthy:t1:v1") == "upworthy:t1:v1"
    for bad in ("asos:t1:v1", "upworthy:a\rb", "upworthy:a\x00b", "upworthy:a\tb"):
        with pytest.raises(ValueError):
            resolve_row_id("upworthy", bad)
    with pytest.raises(ValueError, match="source"):
        resolve_row_id("upworthy", "t1:v1")


def test_the_bonferroni_family_counts_the_intervals_the_table_reports():
    from test_review_l import _bt

    from mootcourt import harness_stats as hs

    _, sc = _bt()
    agg = hs.aggregate_scores(sc, GATES, B=40)
    has_skill = agg["brier_skill_lo"].notna() & ((agg["brier_skill_hi"] - agg["brier_skill_lo"]) > 0)
    has_log = agg["logscore_lo"].notna()
    assert agg["family_size"].iloc[0] == int(has_skill.sum() + has_log.sum())
    p0 = agg[(agg["rung"] == "P0") & (agg["cell"] == "ALL")].iloc[0]
    assert pd.isna(p0["adjusted_lo"])  # P0's skill interval has zero width: nothing to adjust
    assert not agg.columns.str.startswith("_se").any()


def test_the_baseline_log_score_of_the_join_is_the_cards_own_p0():
    from test_review_l import _issued_card

    from mootcourt import card as card_mod
    from mootcourt import loop
    from mootcourt.predictors.p0 import P0Predictor

    ledger = upworthy_like(170, seed=5)
    adm = ledger[ledger["status"] == "admitted"]
    row = adm[(adm["started_at"] >= "2014-04-01") & (adm["cell"] == "headline_only")].iloc[0]
    bundle, req, origin = _issued_card(ledger, row)
    card = card_mod.to_json(card_mod.build_card(bundle, req, reliability=fresh_report(origin), now=origin.to_pydatetime()))
    p0c = card["prediction"]["p0"]
    assert p0c["var"] is not None
    later = P0Predictor().fit(adm)  # a P0 that has seen rows the bundle had not
    out = loop.outcome_from_card(card, row, later, row["usable_after"].to_pydatetime() + dt.timedelta(days=1))
    expect = -0.5 * (row["y"] - p0c["mean"]) ** 2 / p0c["var"] - 0.5 * math.log(2 * math.pi * p0c["var"])
    assert out["p0_logscore"] == pytest.approx(expect)


def test_a_far_query_gets_p1s_predictive_and_an_empty_state():
    from test_review_l import _p2_fit

    from mootcourt.predictors.p2 import P2Predictor

    adm, space, p1, _ = _p2_fit()
    p2 = P2Predictor().fit(adm, space, p1, lambda_override=0.5, bandwidth_override=0.002)
    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    x = space.transform_text(["zzz qqq xxx nothing like it"], False, reference="www", exposure=20000)[0] + 50.0
    st = p2.neighbor_state(x, "headline_only", origin)
    assert st.lam == 0.0 and len(st.row_ids) == 0
    assert np.array_equal(p2.predictive_from_state(st, x, 0.2, "headline_only", origin).pmf, p1.predict(x, 0.2, "headline_only", origin).pmf)


def test_p0_variance_has_a_floor_at_the_median_squared_standard_error():
    from mootcourt.predictors.p0 import P0Predictor

    ledger = upworthy_like(60, seed=6)
    adm = ledger[(ledger["status"] == "admitted") & (ledger["cell"] == "headline_only")].head(2).copy()
    adm["y"] = [0.10, 0.11]
    adm["s"] = [0.3, 0.3]
    f = P0Predictor().fit(adm).forecast("headline_only", adm["usable_after"].max())
    assert f.var >= 0.3**2 - 1e-12
    assert P0Predictor().fit(adm).logscore(0.5, "headline_only", adm["usable_after"].max()) > -20


def test_method_id_changes_with_the_kind_of_feature_space():
    from mootcourt.bundle import method_id
    from mootcourt.features import FeatureSpace

    adm = upworthy_like(100, seed=7)
    assert method_id(FeatureSpace.fit(adm)) != method_id(FeatureSpace.fit(adm, pairwise=False))
    assert method_id(FeatureSpace.fit(adm, feature_set="text")) != method_id(FeatureSpace.fit(adm))
    cell_only = FeatureSpace.fit(adm, cell_only=True)
    assert method_id(cell_only) != method_id(FeatureSpace.fit(adm))


def test_the_gbm_calibration_set_is_the_same_fixed_subsample_as_the_other_challengers():
    from mootcourt.features import FeatureSpace
    from mootcourt.harness import CALIBRATION_MAX_ROWS, GBMChallenger

    adm = upworthy_like(160, seed=11)
    adm = adm[adm["status"] == "admitted"]
    g = GBMChallenger(FeatureSpace.fit(adm), adm)
    p, e = g.oof_probabilities()
    assert len(p) == min(len(adm), CALIBRATION_MAX_ROWS) == len(e)


def test_the_robustness_count_does_not_depend_on_the_kernel_scale():
    from mootcourt.card import robustness_dismissals
    from mootcourt.predictors.p2 import NeighborState

    rng = np.random.default_rng(0)
    n = 40
    kern = rng.uniform(0.2, 1.0, n)
    base = dict(
        row_ids=tuple(f"r{i}" for i in range(n)),
        y=rng.normal(0.2, 0.5, n),
        s=np.full(n, 0.2),
        test_ids=tuple(f"t{i}" for i in range(n)),
        mu=0.0,
        tau=0.3,
        lam=1.0,
        tau_res2=0.0,
        nu=math.inf,
    )
    a = robustness_dismissals(NeighborState(kernel=kern, **base), 0.2, 0.35)
    b = robustness_dismissals(NeighborState(kernel=kern * 1e-30, **base), 0.2, 0.35)
    c = robustness_dismissals(NeighborState(kernel=kern * 1e-60, **base), 0.2, 0.35)
    assert a == b == c


def test_an_infinite_guardrail_delta_is_refused_by_the_command_and_the_service():
    import typer

    from mootcourt.cli import _parse_guardrail
    from mootcourt.service import GuardrailPayload

    with pytest.raises(typer.BadParameter):
        _parse_guardrail("cell:inf")
    with pytest.raises(ValueError):
        GuardrailPayload(cell="c", delta=float("inf"))
    assert _parse_guardrail("cell:0.5").delta == 0.5


# ============================================================================ criteria 11 to 14: discrimination, event, guard pairs
def test_auc_by_test_matches_the_rank_formula_with_ties_and_is_none_for_one_class():
    from sklearn.metrics import roc_auc_score

    from mootcourt import harness_stats as hs

    rng = np.random.default_rng(3)
    n = 400
    p = np.round(rng.uniform(0, 1, n), 1)  # many ties
    e = (rng.uniform(0, 1, n) < 0.2 + 0.5 * p).astype(float)
    tests = rng.integers(0, 60, n)
    ts = hs._TestSums(pd.DataFrame({"test_id": tests}), {"a": np.zeros(n)})
    counts = ts.resample_counts(80, np.random.default_rng(0))
    est, lo, hi = hs.auc_by_test(p, e, ts.codes, counts)
    assert est == pytest.approx(roc_auc_score(e, p), abs=1e-12)
    assert lo < est < hi
    assert hs.auc_by_test(p, np.zeros(n), ts.codes, counts) == (None, None, None)
    assert hs.auc_by_test(p, np.ones(n), ts.codes, counts) == (None, None, None)


def test_the_aggregate_reports_auc_and_the_murphy_resolution_apart_from_skill():
    from test_review_l import _bt

    from mootcourt import harness_stats as hs

    _, sc = _bt()
    agg = hs.aggregate_scores(sc, GATES, B=40)
    for col in (
        "auc_event",
        "auc_event_lo",
        "auc_event_hi",
        "resolution_event",
        "resolution_direction",
        "resolution_direction_lo",
        "resolution_direction_hi",
    ):
        assert col in agg.columns
    g = sc[sc["rung"] == "P1"]
    row = agg[(agg["cell"] == "ALL") & (agg["rung"] == "P1")].iloc[0]
    want = hs.murphy_resolution(g["p_sig"], g["event"].astype(float))[0]
    assert row["resolution_event"] == pytest.approx(want, abs=1e-12)
    assert hs.murphy_resolution(g["p_gt0"], g["event_pos"].astype(float))[0] == pytest.approx(row["resolution_direction"], abs=1e-12)
    assert 0.0 <= row["auc_event"] <= 1.0 and row["auc_event_lo"] <= row["auc_event"] <= row["auc_event_hi"]
    assert row["resolution_event_lo"] <= row["resolution_event"] <= row["resolution_event_hi"]
    assert row["resolution_direction_lo"] <= row["resolution_direction_hi"]  # the estimate is biased up, so it may sit below its interval


def test_murphy_resolution_is_near_zero_for_a_noise_forecast_and_large_for_an_informative_one_whatever_the_spread():
    from mootcourt import harness_stats as hs

    rng = np.random.default_rng(0)
    n = 20000
    tests = rng.integers(0, 4000, n)
    ts = hs._TestSums(pd.DataFrame({"test_id": tests}), {"a": np.zeros(n)})
    counts = ts.resample_counts(60, np.random.default_rng(1))
    e = (rng.uniform(0, 1, n) < 0.2).astype(float)
    noise = rng.uniform(0.0, 0.9, n)  # very spread, unrelated to the outcome
    informative = np.where(e == 1, 0.5, 0.05) + rng.normal(0, 0.01, n)
    r_noise, lo, hi = hs.murphy_resolution(noise, e, ts.codes, counts)
    r_inf = hs.murphy_resolution(informative, e)[0]
    spread = float(((noise - e.mean()) ** 2).mean())
    assert spread > 0.1 and r_noise < 5e-4 and lo <= r_noise <= hi  # the old quantity (spread) was 200 times larger
    assert r_inf > 0.03
    assert hs.murphy_resolution(np.full(n, 0.2), e)[0] == pytest.approx(0.0, abs=1e-12)


def test_the_event_on_the_planned_standard_error_is_scored_for_every_rung_and_p0_has_zero_skill_on_it():
    from test_review_l import _bt

    from mootcourt import harness_stats as hs
    from mootcourt.config import Z

    _, sc = _bt()
    assert (sc["event_planned"].to_numpy() == (sc["y"].to_numpy() > Z * sc["s_star"].to_numpy())).all()
    p1 = sc[sc["rung"] == "P1"]
    assert np.allclose(p1["brier_planned"], (p1["p_sig"] - p1["event_planned"].astype(float)) ** 2)
    p0 = sc[sc["rung"] == "P0"]
    assert np.allclose(p0["brier_planned"], p0["brier_base_planned"])  # P0 forecasts the visible rate of the event being scored
    agg = hs.aggregate_scores(sc, GATES, B=40).query("cell == 'ALL'").set_index("rung")
    assert agg.loc["P0", "brier_skill_planned"] == pytest.approx(0.0, abs=1e-12)
    for rung in ("P1", "P2"):
        r = agg.loc[rung]
        assert r["brier_skill_planned"] == pytest.approx(1.0 - r["brier_planned"] / r["brier_base_planned"], abs=1e-12)
        assert r["brier_skill_planned_lo"] <= r["brier_skill_planned"] <= r["brier_skill_planned_hi"]
        assert 0.0 <= r["event_rate_planned"] <= 1.0 and 0.0 <= r["p_sig_mean"] <= 1.0


def test_the_report_markdown_has_the_discrimination_and_the_planned_event_tables():
    from mootcourt import report

    columns = {c for _, cols in report._AGG_GROUPS for c in cols}
    assert {"auc_event", "resolution_event", "auc_direction", "brier_skill_planned", "event_rate_planned"} <= columns


def _load_paper_extras():
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "paper_extras.py"
    spec = importlib.util.spec_from_file_location("paper_extras_n", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_guard_pair_table_lists_each_admitted_pair_with_its_realized_out_of_time_difference(tmp_path):
    pe = _load_paper_extras()
    origins = [pd.Timestamp("2013-04-01", tz="UTC"), pd.Timestamp("2013-07-01", tz="UTC")]
    rows = []
    for oi, o in enumerate(origins):
        for t in range(6):
            for rung, ls in (("P1", -1.0), ("P2", -1.0 - (0.1 if oi == 0 else -0.05))):
                rows.append({"row_id": f"r{oi}{t}", "test_id": f"t{oi}{t}", "cell": "headline_only", "origin": o, "rung": rung, "logscore": ls})
    pd.DataFrame(rows).to_parquet(tmp_path / "scores-upworthy-SID.parquet")
    sel = [
        {
            "origin": origins[0].isoformat(),
            "rung": "P2",
            "cell": "headline_only",
            "lambda": 0.5,
            "lambda_unguarded": 0.7,
            "gain": 0.01,
            "gain_se": 0.004,
            "n_rows": 100,
        },
        {
            "origin": origins[1].isoformat(),
            "rung": "P2",
            "cell": "headline_only",
            "lambda": 0.1,
            "lambda_unguarded": 0.1,
            "gain": 0.002,
            "gain_se": 0.001,
            "n_rows": 120,
        },
        {
            "origin": origins[1].isoformat(),
            "rung": "P2",
            "cell": "image_only",
            "lambda": 0.0,
            "lambda_unguarded": 0.3,
            "gain": -0.01,
            "gain_se": 0.01,
            "n_rows": 50,
        },
    ]
    (tmp_path / "backtest-upworthy-SID.json").write_text(json.dumps({"tables": {"p2_selection": sel}}))
    got = pe.guard_pairs(tmp_path, "upworthy", "SID", B=50)
    assert got["summary"]["pairs_in_selection"] == 3 and got["summary"]["pairs_admitted"] == 2
    assert [r["realized_p2_minus_p1"] for r in got["rows"]] == [pytest.approx(-0.1), pytest.approx(0.05)]
    assert got["summary"]["pairs_with_negative_realized"] == 1
    assert got["summary"]["pooled_rows"] == 12 and got["summary"]["pooled_tests"] == 12
    assert pe.guard_pairs(tmp_path, "upworthy", "MISSING") is None


def test_the_positive_control_sensitivity_has_a_point_at_the_per_cell_size_of_the_headline_only_cell():
    from mootcourt.sources.synthetic import SyntheticConfig, generate

    pe = _load_paper_extras()
    assert 11100 in pe.SENSITIVITY_SIZES  # 11,100 tests of two variants over three cells = about 7,400 rows in each cell the guard works in
    ledger, _ = generate(SyntheticConfig(seed=0, n_tests=11100))
    per_cell = ledger[ledger["status"] == "admitted"].groupby("cell").size()
    assert per_cell.min() > 7000 and per_cell.max() < 7800


def test_build_tables_writes_the_discrimination_event_definition_and_guard_pair_tables(tmp_path):
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / "paper" / "build_tables.py"
    spec = importlib.util.spec_from_file_location("build_tables_n", path)
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    row = {
        "cell": "ALL",
        "rung": "P1",
        "kind": "ladder",
        "auc_event": 0.55,
        "auc_event_lo": 0.5,
        "auc_event_hi": 0.6,
        "resolution_event": 0.0013,
        "auc_direction": 0.5,
        "auc_direction_lo": 0.49,
        "auc_direction_hi": 0.51,
        "resolution_direction": 0.0015,
        "p_sig_mean": 0.12,
        "brier_skill": 0.0015,
        "brier_skill_lo": -0.002,
        "brier_skill_hi": 0.005,
        "brier_skill_planned": 0.002,
        "brier_skill_planned_lo": -0.001,
        "brier_skill_planned_hi": 0.005,
        "event_rate_planned": 0.14,
    }
    rep = {"_path": "rep.json", "tables": {"aggregate": [row, {**row, "rung": "always_variant", "kind": "baseline"}]}}
    bt.discrimination_table(rep, "upworthy", str(tmp_path))
    bt.event_definition_table(rep, "upworthy", str(tmp_path))
    d = (tmp_path / "discrimination-upworthy.tex").read_text()
    e = (tmp_path / "event-definition-upworthy.tex").read_text()
    assert "0.550 (0.500, 0.600)" in d and "always" not in d
    assert "0.0020 (-0.0010, 0.0050)" in e and "planned event rate 0.1400" in e
    (tmp_path / "paper-extras-upworthy-SID.json").write_text(
        json.dumps(
            {
                "guard_pairs": {
                    "rows": [
                        {
                            "origin": "2013-10-01T00:00:00+00:00",
                            "cell": "headline_only",
                            "lambda": 0.5,
                            "in_selection_gain": 0.011,
                            "in_selection_gain_se": 0.005,
                            "n_scored_rows": 649,
                            "n_scored_tests": 220,
                            "realized_p2_minus_p1": 0.0109,
                        }
                    ],
                    "summary": {
                        "pairs_admitted": 1,
                        "pairs_in_selection": 3,
                        "mean_in_selection_gain": 0.011,
                        "pooled_rows": 649,
                        "pooled_tests": 220,
                        "pooled_realized_p2_minus_p1": 0.0109,
                        "pooled_lo": 0.0,
                        "pooled_hi": 0.02,
                        "bootstrap_resamples": 1000,
                    },
                }
            }
        )
    )
    bt.guard_pairs_table(str(tmp_path), "upworthy", str(tmp_path))
    g = (tmp_path / "guard-pairs-upworthy.tex").read_text()
    assert "2013-10-01" in g and "pooled (1 of 3 pairs)" in g


def test_a_refit_on_newer_data_through_fit_command_refreshes_the_champion_and_without_a_backtest_waits_for_the_summary(tmp_path):
    """The tutorial 4 sequence at the library level: fit, ingest more rows, fit again."""
    from mootcourt.registry import Registry, fit_command

    ledger = upworthy_like(170, seed=5)
    ledger = ledger[ledger["status"] == "admitted"].sort_values("usable_after").reset_index(drop=True)
    first = ledger.iloc[: int(len(ledger) * 0.85)].reset_index(drop=True)
    ldir, mdir, rdir = tmp_path / "ledger", tmp_path / "models", tmp_path / "reports"
    for d in (ldir, mdir, rdir):
        d.mkdir()
    m1, _, role1, _ = fit_command("upworthy", first, ldir, mdir, rdir)
    assert role1 == "champion"
    m2, _, role2, summary = fit_command("upworthy", ledger, ldir, mdir, rdir)
    assert m2 != m1 and summary is None
    doc = Registry(mdir)._read()["upworthy"]
    assert doc["data_through"][m1] < doc["data_through"][m2]  # the fit path records how far the data reaches
    assert role2 == "challenger" and doc["pending_refresh"] == m2  # same method, newer data, no backtest yet: pending, not a plain challenger
    assert "recency" not in doc["history"][-1].get("reason", "")
    Registry(mdir).attach_summary("upworthy", m2, {"brier_skill": 0.01, "brier_skill_lo": -0.01, "brier_skill_hi": 0.03, "n": 100})
    assert Registry(mdir).get_champion("upworthy") == m2


def test_simulators_list_names_a_missing_config_and_init_quotes_the_sample_path(tmp_path, monkeypatch):
    from mootcourt.cli import app

    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(tmp_path / "root"))
    res = CliRunner().invoke(app, ["simulators", "list", "--config", str(tmp_path / "missing.toml")])
    assert res.exit_code == 2 and "does not exist" in res.output
    from mootcourt.onboarding import init_project

    out = init_project(tmp_path / "a folder", None, None, None, False)
    assert "--input '" in out["commands"][0] and "a folder" in out["commands"][0]
    assert "reports/challengers" not in (Path(__file__).resolve().parents[1] / "Makefile").read_text()


def test_the_released_gates_carry_the_base_rate_014():
    import json

    from conftest import AMBIENT_ROOT

    path = Path(AMBIENT_ROOT or "/nonexistent") / "reports" / "gates.json"
    if not path.is_file():
        pytest.skip("no gates.json on the data root (export MOOTCOURT_DATA_ROOT)")
    by = json.loads(path.read_text())["by_base_rate"]
    assert set(by) == {"0.09", "0.14", "0.30"} and by["0.14"]["n_200"] > 0 and by["0.14"]["n_400"] >= by["0.14"]["n_200"]


def test_build_tables_writes_the_walltime_table_from_the_run_log_and_states_the_data_stage(tmp_path):
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "paper" / "build_tables.py"
    spec = importlib.util.spec_from_file_location("build_tables_w", path)
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    log = {
        "data_stage_kind": "checksum verification",
        "download_seconds": 5.2,
        "main_pipeline_seconds": 10.0,
        "total_seconds": 12.5,
        "stages": [{"stage": "setup", "seconds": 1.0, "exit_code": 0}, {"stage": "data", "seconds": 6.0, "exit_code": 0}],
    }
    (tmp_path / "run-log.json").write_text(json.dumps(log))
    bt.walltime_table(str(tmp_path), str(tmp_path))
    text = (tmp_path / "walltime.tex").read_text()
    assert "checksum verification (5.2 s), nothing downloaded" in text and "data & 6.0" in text and "total & 12.5" in text


# ============================================================================ the review of chunk N (T-057)
def test_a_champion_from_a_registry_written_before_data_through_is_refreshed_by_a_same_method_refit(tmp_path):
    from mootcourt.registry import Registry, fit_command

    ledger = upworthy_like(170, seed=5)
    ledger = ledger[ledger["status"] == "admitted"].sort_values("usable_after").reset_index(drop=True)
    first = ledger.iloc[: int(len(ledger) * 0.85)].reset_index(drop=True)
    ldir, mdir, rdir = tmp_path / "ledger", tmp_path / "models", tmp_path / "reports"
    for d in (ldir, mdir, rdir):
        d.mkdir()
    m1, _, _, _ = fit_command("upworthy", first, ldir, mdir, rdir)
    doc = json.loads((mdir / "registry.json").read_text())  # the registry as chunk L wrote it: no data_through anywhere
    doc["upworthy"].pop("data_through")
    (mdir / "registry.json").write_text(json.dumps(doc))
    m2, _, role, _ = fit_command("upworthy", ledger, ldir, mdir, rdir)
    assert role == "challenger" and Registry(mdir).pending_refresh("upworthy") == m2
    Registry(mdir).attach_summary("upworthy", m2, {"brier_skill": 0.01, "brier_skill_lo": -0.01, "brier_skill_hi": 0.03, "n": 100})
    after = Registry(mdir)._read()["upworthy"]
    assert after["champion"] == m2
    derived = [h for h in after["history"] if h["event"] == "data_through_derived"]
    assert derived and derived[0]["model_id"] == m1 and "predates the field" in derived[0]["reason"]
    assert after["data_through"][m1] < after["data_through"][m2]


def test_moot_fit_says_a_refresh_is_pending_and_that_the_backtest_decides_it(tmp_path, monkeypatch):
    from mootcourt import registry as reg
    from mootcourt.cli import app

    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(tmp_path / "root"))
    monkeypatch.setattr("mootcourt.cli._load_source_ledger", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(reg, "fit_command", lambda *a, **k: ("m2", "snap", "challenger", None))
    monkeypatch.setattr(reg.Registry, "pending_refresh", lambda self, source: "m2")
    res = CliRunner().invoke(app, ["fit", "--source", "upworthy"])
    assert res.exit_code == 0, res.output
    assert "refresh of the champion is pending" in res.output and "`moot backtest` decides it" in res.output
    assert "then `moot fit`" not in res.output


def test_a_query_between_the_float32_and_float64_underflow_gets_p1s_predictive():
    from test_review_l import _p2_fit

    from mootcourt.features import sq_dists
    from mootcourt.ledger import timestamp_ns
    from mootcourt.predictors.p2 import P2Predictor

    adm, space, p1, _ = _p2_fit()
    p2 = P2Predictor().fit(adm, space, p1, lambda_override=0.5)
    origin = adm["usable_after"].max() + pd.Timedelta(days=1)
    base = space.transform_text(["a plain headline about dogs"], False, reference="www", exposure=20000)[0]
    data = p2._cells["headline_only"]
    k = data.prefix(timestamp_ns(origin))
    band = None
    for off in np.arange(1.0, 40.0, 0.5):
        x = base + off
        peak = float(
            np.exp(sq_dists(np.asarray(x, dtype=data.X.dtype), data.X[:k], data.sq[:k]).astype(np.float64) * (-1.0 / (2.0 * data.h**2))).max()
        )
        if 1e-300 < peak < 1e-46:
            band = x
            break
    assert band is not None, "no offset lands in the band between the float32 and the float64 underflow"
    st = p2.neighbor_state(band, "headline_only", origin)
    assert st.lam == 0.0 and len(st.row_ids) == 0


def test_a_missing_exposure_is_filled_with_the_exposure_column_mean_in_a_pairwise_space_and_list_precedents_takes_one():
    import inspect

    from mootcourt.features import FeatureSpace
    from mootcourt.mcp_server import tool_list_precedents

    adm = upworthy_like(120, seed=8)
    adm = adm[adm["status"] == "admitted"]
    space = FeatureSpace.fit(adm, pairwise=True) if "pairwise" in inspect.signature(FeatureSpace.fit).parameters else FeatureSpace.fit(adm)
    if not space.pairwise:
        pytest.skip("this fixture builds no pairwise space")
    exp_col = len(space.mean) - 1 - 3
    with_none = space.transform_text(["a headline"], False, reference="another headline")[0]
    assert abs(with_none[exp_col]) < 1e-9  # the fit mean standardizes to zero in the exposure column
    assert "exposure" in inspect.signature(tool_list_precedents).parameters


def test_init_writes_quick_gates_by_test_and_gate_verdict_compares_rows_with_a_per_row_file(tmp_path):
    from mootcourt.card import gate_verdict
    from mootcourt.onboarding import init_project

    out = init_project(tmp_path / "proj", None, None, None, False)
    from mootcourt.simulate import load_gates

    gates = load_gates(Path(out["gates"]))
    assert gates["interval"]["by"] == "test" and gates["interval"]["level"] == 0.9
    assert gates["interval"]["rows_per_test"] == 3.5 and gates["interval"]["icc"] == 0.13
    per_row = {"base_rate": 0.3, "n_200": 175, "n_400": 400, "interval": {"by": "row", "level": 0.95}, "target_power": 0.9}
    text = gate_verdict(7, None, None, per_row, 0.3, n_rows=500)
    assert text.startswith("500 rows:") and "decidable" in text and "numbers of rows" in text
    assert gate_verdict(7, None, None, per_row, 0.3, n_rows=100).startswith("100 rows: undecidable")
    by_test = gate_verdict(7, None, None, gates, 0.3, n_rows=500)
    assert by_test.startswith("7 tests:") and "overstates" not in by_test


def test_skill_interval_keeps_a_test_named_none_and_the_planned_table_reports_the_scored_forecast_mean():
    from test_review_l import _bt

    from mootcourt import harness_stats as hs
    from mootcourt.reliability import skill_interval

    b = np.array([0.1, 0.2, 0.15, 0.3, 0.25, 0.05] * 5)
    ids = np.array(["None", "a", "b", "c", "d", "e"] * 5, dtype=object)
    assert skill_interval(b, np.full(len(b), 0.2), ids, B=50)[2] == 6  # the literal id "None" is a test, not a missing id
    _, sc = _bt()
    agg = hs.aggregate_scores(sc, GATES, B=30).query("cell == 'ALL'").set_index("rung")
    p0 = sc[sc["rung"] == "P0"]
    assert agg.loc["P0", "p_sig_mean"] == pytest.approx(float(p0["p_base_planned"].mean()), abs=1e-12)
    p1 = sc[sc["rung"] == "P1"]
    assert agg.loc["P1", "p_sig_mean"] == pytest.approx(float(p1["p_sig"].mean()), abs=1e-12)


def test_the_guard_gain_diagnostic_reports_gain_standard_error_ratio_and_share_admitted_per_size_and_has_a_table(tmp_path):
    import importlib.util

    pe = _load_paper_extras()
    got = pe.guard_gain_diagnostic(sizes=(120,), seeds=range(2))
    row = got["rows"][0]
    assert row["n_tests"] == 120 and row["cells"] > 0 and row["mean_gain_se"] > 0
    assert 0.0 <= row["share_admitted"] <= 1.0 and 0.0 <= row["share_gain_positive"] <= 1.0
    assert row["ratio_of_means"] == pytest.approx(row["mean_gain"] / row["mean_gain_se"])
    spec = importlib.util.spec_from_file_location("build_tables_g", Path(__file__).resolve().parents[1] / "paper" / "build_tables.py")
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    (tmp_path / "paper-extras-synthetic-SID.json").write_text(json.dumps({"guard_gain_diagnostic": got}))
    bt.guard_gain_table(str(tmp_path), str(tmp_path))
    assert "120 &" in (tmp_path / "guard-gain-diagnostic.tex").read_text()


def test_the_held_out_gain_and_fit_fraction_diagnostics_hold_out_tests_and_have_tables(tmp_path):
    import importlib.util

    pe = _load_paper_extras()
    ho = pe.guard_held_out_gain(sizes=(120,), seeds=range(2))
    row = ho["rows"][0]
    assert row["n_tests"] == 120 and row["cells"] > 0
    assert row["mean_difference"] == pytest.approx(row["mean_in_selection_gain"] - row["mean_held_out_gain"])
    assert row["admitted_cells"] <= row["cells"] and ho["held_out_share_of_tests"] == 0.15
    fs = pe.guard_fit_fraction_stability(n_tests=120, seeds=range(2))
    assert [r["fit"] for r in fs["rows"]] == ["first_85_percent", "first_90_percent", "first_95_percent", "first_100_percent", "random_85_percent"]
    assert all(r["cells"] > 0 and 0.0 <= r["share_admitted"] <= 1.0 for r in fs["rows"])
    spec = importlib.util.spec_from_file_location("build_tables_h", Path(__file__).resolve().parents[1] / "paper" / "build_tables.py")
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    (tmp_path / "paper-extras-synthetic-SID.json").write_text(json.dumps({"guard_held_out_gain": ho, "guard_fit_fraction_stability": fs}))
    bt.guard_held_out_table(str(tmp_path), str(tmp_path))
    assert (
        "120 &" in (tmp_path / "guard-gain-held-out.tex").read_text() and "random\\_85\\_percent" in (tmp_path / "guard-fit-fraction.tex").read_text()
    )
