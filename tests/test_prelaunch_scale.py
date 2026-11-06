"""T-032 contracts: pre-launch scale (absolute CTR difference, planned-exposure standard error), the
pre-launch feature allow-list, low_clicks admission, calibration by precision."""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ loader
def _packages(rows):
    cols = ["created_at", "test_week", "clickability_test_id", "impressions", "clicks", "headline", "eyecatcher_id",
            "excerpt", "lede", "slug", "share_text"]
    return pd.DataFrame(rows, columns=cols)


def _row(test, t, imp, clk, head, eye):
    return [t, "2014W1", test, imp, clk, head, eye, "e", "l", "s", "t"]


def test_upworthy_y_is_the_absolute_ctr_difference_in_points_with_binomial_se(imp, tmp_path):
    up = imp("mootcourt.sources.upworthy")
    df = _packages([_row("t1", "2014-01-01T00:00:00Z", 10000, 200, "ref head", "a"),
                    _row("t1", "2014-01-01T00:00:01Z", 12000, 300, "new head", "a")])
    path = tmp_path / "up.csv"
    df.to_csv(path)
    out = up.load_upworthy(path, exclude_randomization_window=False)       
    r = out.iloc[0]
    cr, cv = 200 / 10000, 300 / 12000
    assert r["status"] == "admitted"
    assert r["y"] == pytest.approx(100 * (cv - cr))
    assert r["s"] == pytest.approx(100 * math.sqrt(cv * (1 - cv) / 12000 + cr * (1 - cr) / 10000))
    feats = json.loads(r["features_json"])
    assert feats["post_launch"]["relative_lift"] == pytest.approx((cv - cr) / cr * 100)
    assert "ctr_ref" not in feats and "relative_lift" not in feats          # nothing post-launch at the top level
    assert {"headline", "reference_headline", "headline_changed", "image_changed", "n_variants"} <= set(feats)


def test_low_clicks_status_when_either_arm_has_fewer_than_ten_clicks(imp, tmp_path):
    up = imp("mootcourt.sources.upworthy")
    df = _packages([_row("t1", "2014-01-01T00:00:00Z", 10000, 9, "ref head", "a"),
                    _row("t1", "2014-01-01T00:00:01Z", 10000, 300, "new head", "a"),
                    _row("t2", "2014-01-01T00:00:00Z", 10000, 200, "ref two", "a"),
                    _row("t2", "2014-01-01T00:00:01Z", 10000, 0, "new two", "a"),
                    _row("t3", "2014-01-01T00:00:00Z", 500, 3, "ref three", "a"),
                    _row("t3", "2014-01-01T00:00:01Z", 10000, 300, "new three", "a")])
    path = tmp_path / "up.csv"
    df.to_csv(path)
    out = up.load_upworthy(path, exclude_randomization_window=False).set_index("test_id")       
    assert out.loc["t1", "status"] == "low_clicks" and out.loc["t2", "status"] == "low_clicks"
    assert out.loc["t3", "status"] == "low_exposure", "fewer than 1000 impressions takes precedence"
    assert imp("mootcourt.ledger").exclusion_reason("low_clicks")


# ------------------------------------------------------------------ allow-list
def _upworthy_like(make_synth, n_tests=160, seed=33):
    """A synthetic ledger relabeled as Upworthy rows with planned exposures and a post-launch block."""
    ledger = make_synth(seed=seed, n_tests=n_tests, variants_per_test=2)[0].copy()
    rng = np.random.default_rng(seed)
    n = len(ledger)
    ctr = rng.uniform(0.01, 0.05, n)
    expo = rng.integers(3000, 60000, n)
    ledger["source"] = "upworthy"
    ledger["n_ref"], ledger["n_var"] = expo.astype("int64"), expo.astype("int64")
    ledger["features_json"] = [
        json.dumps({**json.loads(j), "n_variants": 2, "post_launch": {"ctr_ref": float(c)}})
        for j, c in zip(ledger["features_json"], ctr)]
    return ledger


def test_feature_builder_rejects_post_launch_fields(imp, make_synth):
    scale, feats = imp("mootcourt.scale"), imp("mootcourt.features")
    ledger = _upworthy_like(make_synth)
    adm = ledger[ledger["status"] == "admitted"]
    feats.FeatureSpace.fit(adm)                                    # the clean ledger is accepted
    for bad in ("ctr_ref", "clicks", "s", "realized_s"):
        dirty = adm.copy()
        dirty["features_json"] = [json.dumps({**json.loads(j), bad: 0.5}) for j in dirty["features_json"]]
        with pytest.raises(scale.PostLaunchFieldError):
            feats.FeatureSpace.fit(dirty)
    assert set(scale.PRELAUNCH_FEATURES) == {"headline", "reference_headline", "headline_changed", "image_changed",
                                             "n_variants", "planned_exposures", "cell", "period"}


def test_planned_exposure_is_a_feature_and_text_requests_need_it(imp, make_synth):
    feats = imp("mootcourt.features")
    ledger = _upworthy_like(make_synth)
    adm = ledger[ledger["status"] == "admitted"]
    space = feats.FeatureSpace.fit(adm)
    assert "log_exposure" in feats.EXPOSURE_FEATURES
    X = space.transform(adm.iloc[:3])
    a = space.transform_text(["x y z"], False, exposure=5000.0)
    b = space.transform_text(["x y z"], False, exposure=50000.0)
    assert X.shape[1] == a.shape[1] == space.dim and not np.allclose(a, b)


def test_leakage_audit_reports_post_launch_fields_as_violations(imp, make_synth, tmp_path):
    harness = imp("mootcourt.harness")
    ledger = _upworthy_like(make_synth, n_tests=120)
    p0 = imp("mootcourt.predictors.p0").P0Predictor
    scores = harness.rolling_origin(ledger, {"P0": lambda r, o: p0().fit(r)}, harness.quarterly_origins(ledger))
    script = ROOT / "scripts" / "leakage_audit.py"

    def run(led):
        imp("mootcourt.ledger").write_ledger(led, tmp_path / "ledger.parquet")
        scores.to_parquet(tmp_path / "scores.parquet")
        return subprocess.run([sys.executable, str(script), "--ledger", str(tmp_path / "ledger.parquet"),
                               "--scores", str(tmp_path / "scores.parquet")], capture_output=True, text=True)

    clean = run(ledger)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "post-launch fields in features 0" in clean.stdout
    dirty = ledger.copy()
    dirty["features_json"] = [json.dumps({**json.loads(j), "ctr_ref": 0.02}) for j in dirty["features_json"]]
    bad = run(dirty)
    assert bad.returncode == 1 and "FAIL" in bad.stdout and "post-launch fields in features" in bad.stdout


# ------------------------------------------------------------------ s_star
def test_s_star_uses_planned_exposure_and_the_visible_cell_median_rate(imp, make_synth):
    scale = imp("mootcourt.scale")
    ledger = _upworthy_like(make_synth)
    adm = ledger[ledger["status"] == "admitted"]
    origin = adm["usable_after"].quantile(0.5)
    visible = adm[adm["usable_after"] <= origin]
    scored = adm[adm["usable_after"] > origin].head(20)
    got = scale.s_star_rows(scored, visible)
    for cell, g in scored.groupby("cell"):
        c = np.median([json.loads(j)["post_launch"]["ctr_ref"] for j in visible[visible["cell"] == cell]["features_json"]])
        n = g["n_ref"].to_numpy(float)
        np.testing.assert_allclose(got[scored.index.get_indexer(g.index)], 100 * np.sqrt(2 * c * (1 - c) / n))
    assert not np.allclose(got, scored["s"].to_numpy())


def test_card_s_star_formula_is_the_absolute_one(imp):
    f = imp("mootcourt.card").s_star_from_exposure
    assert f(20000, 0.02) == pytest.approx(100 * math.sqrt(2 * 0.02 * 0.98 / 20000))


def test_realized_s_never_reaches_a_predictor(imp, make_synth):
    harness, scale, ledger_mod = imp("mootcourt.harness"), imp("mootcourt.scale"), imp("mootcourt.ledger")
    from mootcourt.predictors.base import Predictive, build_grid

    ledger = _upworthy_like(make_synth, n_tests=200)
    seen = {}

    class Recorder:
        """Row-aware rung that records the s_star it is handed and answers with a fixed predictive."""

        def predict_row(self, row, s_star, origin):
            seen[row.row_id] = (float(s_star), float(row.s), origin)
            return Predictive.from_normal(build_grid(0.0, 1.0), 0.0, 1.0), {}

    scores = harness.rolling_origin(ledger, {"R": lambda rows, origin: Recorder()}, harness.quarterly_origins(ledger),
                                    min_fit_rows=20)
    assert len(seen) == len(scores) > 50
    adm = ledger[ledger["status"] == "admitted"].set_index("row_id")
    for rid, (s_star, s_real, origin) in list(seen.items())[:200]:
        row = adm.loc[[rid]]
        expect = scale.s_star_rows(row.reset_index(), ledger_mod.visible_rows(adm.reset_index(), origin))[0]
        assert s_star == pytest.approx(expect)
    assert not np.allclose([v[0] for v in seen.values()], [v[1] for v in seen.values()])
    assert {"s_star", "exposure"} <= set(scores.columns)
    np.testing.assert_allclose(scores.set_index("row_id").loc[list(seen), "s_star"].to_numpy(), [v[0] for v in seen.values()])


# ------------------------------------------------------------------ calibration by precision
def test_calibration_by_precision_table(imp, make_synth):
    hs, harness = imp("mootcourt.harness_stats"), imp("mootcourt.harness")
    ledger = _upworthy_like(make_synth, n_tests=300)
    scores = harness.rolling_origin(ledger, harness.default_rungs("upworthy", ledger), harness.quarterly_origins(ledger))
    tab = hs.calibration_by_precision(scores)
    assert {"rung", "decile", "exposure_lo", "exposure_hi", "n", "mean_p_sig", "event_rate", "coverage_90"} <= set(tab.columns)
    for rung, g in tab.groupby("rung"):
        n_rows = scores[scores["rung"] == rung].shape[0]
        assert g["n"].sum() == n_rows and 2 <= len(g) <= 10
        assert g["exposure_lo"].is_monotonic_increasing
        sub = scores[scores["rung"] == rung]
        lo, hi = g.iloc[0]["exposure_lo"], g.iloc[0]["exposure_hi"]
        first = sub[(sub["exposure"] >= lo) & (sub["exposure"] <= hi)]
        assert g.iloc[0]["mean_p_sig"] == pytest.approx(first["p_sig"].mean(), abs=0.05)
    one = hs.calibration_by_precision(scores.assign(exposure=10000.0))
    assert one.groupby("rung").size().max() == 1, "tied exposures give a single bin"


def test_report_carries_and_renders_the_calibration_by_precision_table(imp, make_synth, tmp_path):
    rp, harness, hs = imp("mootcourt.report"), imp("mootcourt.harness"), imp("mootcourt.harness_stats")
    ledger = _upworthy_like(make_synth, n_tests=300)
    scores = harness.rolling_origin(ledger, harness.default_rungs("upworthy", ledger), harness.quarterly_origins(ledger))
    gates = {"n_200": 175, "n_400": 375, "target_power": 0.9, "decision_target": 0.9, "by_target": {}}
    doc = rp.build_document(scores, ledger=ledger, source="upworthy", snapshot_id="20261102-aaaaaaaaaaaa", model_id="m",
                            feature_hash="f", command="moot backtest", gates=gates, B=50, seed=1)
    assert doc["tables"]["calibration_by_precision"], "the JSON carries the table"
    md = rp.render_markdown(doc)
    assert "Calibration by precision" in md
    assert hs.calibration_by_precision(scores).shape[0] == len(doc["tables"]["calibration_by_precision"])


# ------------------------------------------------------------------ docs
def test_method_md_records_the_finding_in_plain_words():
    text = (ROOT / "docs" / "method.md").read_text(encoding="utf-8")
    low = text.lower()
    for needle in ("relative lift", "noisy reference", "-41", "+104", "pre-launch", "planned exposure", "precision"):
        assert needle in low, f"method.md lacks {needle}"


def test_the_two_run_length_fields_of_the_asos_rows_reach_no_pre_launch_view(imp):
    """T6-plan row 2 (R2 nit 1, call 249): ``n_checkpoints`` and ``final_offset_days`` stay at the top level of the ASOS features, which
    keeps every snapshot id of the released ledgers; the guard is that the pre-launch view, the only reader of the features, drops both."""
    scale = imp("mootcourt.scale")
    features = {"metric_id": 3, "n_variants": 2, "n_checkpoints": 41, "final_offset_days": 43.5, "calendar": "nominal",
                "post_launch": {"original_effect": 0.1, "original_se": 0.2}}
    assert {"n_checkpoints", "final_offset_days"}.isdisjoint(scale.prelaunch_view(features))
    assert set(scale.PRELAUNCH_FEATURES).isdisjoint({"n_checkpoints", "final_offset_days"})
