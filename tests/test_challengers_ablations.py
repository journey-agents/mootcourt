"""T-031 contracts: challengers, direction baselines, ablation switches, P2 selection rules, recency, learning curve."""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
GATES = {"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9,
         "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}


def _synth(make_synth, seed=61, **kw):
    cfg = dict(seed=seed, n_tests=260, variants_per_test=2)
    cfg.update(kw)
    return make_synth(**cfg)[0]


def _run(imp, ledger, challenger=None, source="synthetic", **kw):
    h = imp("mootcourt.harness")
    rungs = h.default_rungs(source, ledger, challenger, **kw)
    return h.rolling_origin(ledger, rungs, h.quarterly_origins(ledger), source=source)


def _cli(imp, args, root):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env={"MOOTCOURT_DATA_ROOT": str(root)})


# ------------------------------------------------------------------ estimators
def test_dersimonian_laird_recovers_the_prior_and_returns_zero_on_pure_noise(imp):
    h = imp("mootcourt.harness")
    rng = np.random.default_rng(3)
    s = rng.uniform(0.5, 1.5, 3000)
    y = rng.normal(2.0, 3.0, 3000) + rng.normal(0, s)
    mu, tau = h.dersimonian_laird(y, s)
    assert abs(mu - 2.0) < 0.25 and abs(tau - 3.0) < 0.25
    mu0, tau0 = h.dersimonian_laird(rng.normal(0, s), s)
    assert tau0 < 0.2 and abs(mu0) < 0.1
    assert h.dersimonian_laird([1.5], [0.3]) == (1.5, 0.0)
    with pytest.raises(ValueError):
        h.dersimonian_laird([], [])


def test_parse_challengers_and_unknown_names(imp):
    h = imp("mootcourt.harness")
    assert h.parse_challengers(None) == [] and h.parse_challengers("gbm") == ["gbm"]
    assert h.parse_challengers(["gbm,local_eb", "text_lr", "gbm"]) == ["gbm", "local_eb", "text_lr"]
    with pytest.raises(ValueError, match="unknown challenger"):
        h.parse_challengers("xgboost")


def test_default_rungs_adds_challengers_and_baselines_in_order(imp, make_synth):
    ledger = _synth(make_synth)
    rungs = imp("mootcourt.harness").default_rungs("synthetic", ledger, ["gbm", "local_eb", "text_lr"], baselines=True)
    assert list(rungs) == ["P0", "P1", "P2", "GBM", "local_eb", "text_lr", "always_reference", "always_variant"]
    assert list(imp("mootcourt.harness").default_rungs("synthetic", ledger)) == ["P0", "P1", "P2"]
    with pytest.raises(ValueError, match="headline text"):
        imp("mootcourt.harness").default_rungs("asos", None, "text_lr")


def test_local_eb_finds_the_prior_of_its_neighbors_and_k_is_configurable(imp, tiny_ledger, origin):
    h, fs = imp("mootcourt.harness"), imp("mootcourt.features")
    space = fs.FeatureSpace.fit(tiny_ledger)
    wide = h.LocalEB(space, tiny_ledger, k=400)
    x = space.transform(tiny_ledger.head(1))[0]
    pred = wide.predict(x, 1.0, "headline_only", origin)
    assert abs(pred.mean() - 2.0) < 0.6 and 2.2 < math.sqrt(pred.var()) < 3.8          # the cell is Normal(2, 3^2)
    ny, ns = wide.neighbors(x, "headline_only")
    assert len(ny) == 400 and len(h.LocalEB(space, tiny_ledger, k=25).neighbors(x, "headline_only")[0]) == 25
    with pytest.raises(ValueError):
        h.LocalEB(space, tiny_ledger, k=1)
    assert wide.neighbors(x, "unknown_cell")[0].size == 400                                  # an unseen cell falls back to all rows


def test_text_lr_learns_a_headline_marker_and_is_scored_on_the_same_rows(imp, make_synth):
    ledger = _synth(make_synth, seed=62, n_tests=500, variants_per_test=1, text_effect_strength=12.0,
                    cell_params={"headline_only": (0.0, 0.5)}, s_scale=1.0)
    sc = _run(imp, ledger, "text_lr")
    lr, p2 = sc[sc["rung"] == "text_lr"], sc[sc["rung"] == "P2"]
    assert set(lr["row_id"]) == set(p2["row_id"]) and len(lr) == len(p2)                      # exactly the ladder's rows
    assert lr[["logscore", "crps", "lo90", "hi90"]].isna().all().all()                      # probabilities only
    assert lr["direction_correct"].astype(float).mean() > 0.8                                  # the marker word decides the sign
    assert lr["brier_event"].notna().all() and lr["p_sig"].between(0, 1).all()
    model = imp("mootcourt.harness").TextLR(ledger)
    cols, keep = model.score_block(ledger.head(40), ledger["y"].head(40).to_numpy(), None, None)
    words = imp("mootcourt.sources.synthetic").SIGNAL_WORDS
    pos = np.array([any(w in json.loads(j)["headline"] for w in words) for j in ledger.head(40)["features_json"]])
    assert cols["p_win"][pos].mean() > cols["p_win"][~pos].mean() + 0.4 and keep.all()


def test_text_lr_handles_a_single_class(imp, tiny_ledger):
    allpos = tiny_ledger.assign(y=np.abs(tiny_ledger["y"]) + 10.0, s=0.01)
    model = imp("mootcourt.harness").TextLR(allpos)
    cols, _ = model.score_block(allpos.head(5), None, None, None)
    assert np.allclose(cols["p_win"], 1.0) and np.allclose(cols["p_sig"], 1.0)


def test_direction_baselines_measure_the_creation_order_share(imp, make_synth):
    ledger = _synth(make_synth, seed=63, cell_params={"headline_only": (-1.5, 1.0), "image_only": (-1.5, 1.0), "both": (-1.5, 1.0)})
    sc = _run(imp, ledger, baselines=True)
    ref, var = sc[sc["rung"] == "always_reference"], sc[sc["rung"] == "always_variant"]
    p2 = sc[sc["rung"] == "P2"].set_index("row_id")
    assert set(ref["row_id"]) == set(p2.index)
    share_ref = float((p2.loc[ref["row_id"], "y"] <= 0).mean())
    assert ref["direction_correct"].astype(float).mean() == pytest.approx(share_ref)
    assert var["direction_correct"].astype(float).mean() == pytest.approx(float((p2["y"] > 0).mean()))
    assert share_ref > 0.6                                                                       # the reference arm wins here by construction
    assert ref[["p_sig", "logscore", "brier_event"]].isna().all().all()
    agg = imp("mootcourt.harness_stats").aggregate_scores(sc, GATES, B=30)
    row = agg[(agg["cell"] == "ALL") & (agg["rung"] == "always_reference")].iloc[0]
    assert row["direction_accuracy"] == pytest.approx(share_ref) and np.isfinite(row["direction_ceiling"])
    assert row["direction_ceiling"] > row["direction_accuracy"] - 0.2 and pd.isna(row["brier_skill"])


def test_gbm_residual_spread_comes_from_out_of_fold_predictions(imp, make_synth):
    ledger = _synth(make_synth, seed=64, n_tests=400, variants_per_test=1, text_effect_strength=4.0)
    h, fs = imp("mootcourt.harness"), imp("mootcourt.features")
    adm = ledger[ledger["status"] == "admitted"]
    g = h.GBMChallenger(fs.FeatureSpace.fit(adm), adm)
    n = len(adm)
    assert g.n_folds == imp("mootcourt.config").GBM_FOLDS and len(g.oof_residuals) == n and np.isfinite(g.oof_residuals).all()
    expected = math.sqrt(max(float(np.mean(g.oof_residuals ** 2) - adm["s"].pow(2).mean()), 1e-4))
    assert g.sd == pytest.approx(expected)
    # An in-sample fit would leave smaller residuals than the out-of-fold ones that set the spread.
    order = adm.sort_values("started_at", kind="stable")
    insample = order["y"].to_numpy() - g.model.predict(g._bin(g._raw(order)))          # round 00: the model reads quantized columns and the cell
    assert np.mean(insample ** 2) < np.mean(g.oof_residuals ** 2)


def test_every_rung_has_reliability_bins_and_a_kind(imp, make_synth):
    ledger = _synth(make_synth, seed=65, n_tests=300, text_effect_strength=3.0)
    sc = _run(imp, ledger, ["gbm", "local_eb", "text_lr"], baselines=True)
    report = imp("mootcourt.report")
    doc = report.build_document(sc, ledger=ledger, source="synthetic", snapshot_id="s", model_id="m", feature_hash="f", command="c", seed=0,
                                gates=GATES, B=30)
    bins = pd.DataFrame(doc["tables"]["reliability_bins"])
    assert {"P0", "P1", "P2", "GBM", "local_eb", "text_lr"} <= set(bins["rung"]) and not {"always_reference", "always_variant"} & set(bins["rung"])
    kinds = {r["rung"]: r["kind"] for r in doc["tables"]["aggregate"] if r["cell"] == "ALL"}
    assert kinds["GBM"] == kinds["text_lr"] == kinds["local_eb"] == "challenger" and kinds["P2"] == "ladder" and kinds["always_variant"] == "baseline"
    assert doc["header"]["challengers"] == ["GBM", "local_eb", "text_lr"]
    assert doc["header"]["direction_baselines"] == ["always_reference", "always_variant"]
    md = report.render_markdown(doc)
    assert "challenger: TF-IDF" in md and "direction baseline" in md and "| kind |" in md
    assert doc["tables"]["aggregate"][0]["cell"] == "ALL"


# ------------------------------------------------------------------ ablation switches
def test_feature_sets_select_the_text_or_the_structured_columns(imp, make_synth):
    ledger = _synth(make_synth, n_tests=120)
    fs = imp("mootcourt.features")
    both, text, struct = (fs.FeatureSpace.fit(ledger, feature_set=k) for k in ("both", "text", "structured"))
    n_struct = len(fs.STRUCTURED_FEATURES) + len(fs.EXPOSURE_FEATURES)
    assert text.dim == both.svd_dims and struct.dim == n_struct and both.dim == both.svd_dims + n_struct
    X, Xt, Xs = both.transform(ledger), text.transform(ledger), struct.transform(ledger)
    assert Xt.shape[1] == text.dim and Xs.shape[1] == struct.dim
    assert np.allclose(X[:, : both.svd_dims], Xt) and np.allclose(X[:, both.svd_dims:], Xs)
    assert fs.feature_hash(both) != fs.feature_hash(text) != fs.feature_hash(struct)
    assert fs.FeatureSpace.from_state(text.to_state()).feature_set == "text"
    with pytest.raises(ValueError):
        fs.FeatureSpace.fit(ledger, feature_set="images")


def test_ablation_switches_reach_the_models(imp, make_synth):
    ledger = _synth(make_synth, n_tests=200)
    h = imp("mootcourt.harness")
    vis = ledger.head(300)
    rungs = h.default_rungs("synthetic", ledger, kappa=5, prior="normal", lam=0.3, bandwidth_mult=0.25, features="text")
    origin = vis["usable_after"].max()
    p1, p2 = rungs["P1"](vis, origin), rungs["P2"](vis, origin)
    assert p1.kappa == 5 and all(math.isinf(v["nu"]) for v in (p1.cell_params(c, "2013Q4") for c in vis["cell"].unique()))
    assert set(p2.bandwidth_mult_by_cell.values()) == {0.25} and p2.lambda_override == 0.3 and p2.space.feature_set == "text"
    assert all(rec["lambda"] == 0.3 for rec in p2.selection_summary())
    base = h.default_rungs("synthetic", ledger)
    assert base["P1"](vis, origin).kappa == imp("mootcourt.config").KAPPA
    for bad in ({"features": "images"}, {"prior": "cauchy"}, {"p2_selection": "random"}):
        with pytest.raises(ValueError):
            h.default_rungs("synthetic", ledger, **bad)


# ------------------------------------------------------------------ P2 selection and recency
def _cell_data(imp, ledger):
    p2, fs = imp("mootcourt.predictors.p2"), imp("mootcourt.features")
    from mootcourt.ledger import series_ns

    g = ledger.sort_values("usable_after", kind="stable")
    X = fs.FeatureSpace.fit(g).transform(g).astype(np.float32)
    data = p2._CellData(X, g["y"].to_numpy(float), g["s"].to_numpy(float), tuple(g["row_id"]), tuple(g["test_id"]),
                        series_ns(g["usable_after"]), fs.median_bandwidth(X), series_ns(g["started_at"]))
    return p2, data, g


def test_forward_chaining_never_reads_rows_usable_after_the_inner_cut(imp, make_synth):
    ledger = _synth(make_synth, seed=66, n_tests=300, variants_per_test=1, text_effect_strength=4.0, cell_params={"headline_only": (0.0, 1.0)})
    p2, data, g = _cell_data(imp, ledger)
    block, cut_ns = p2._forward_blocks(data.start_ns)
    queries = np.flatnonzero(block >= 0)
    assert len(queries) < len(data.y) and (data.start_ns[queries] >= cut_ns[0]).all()
    codes = pd.factorize(g["test_id"])[0]
    base, _ = p2._cv_cell(data, codes, 1.0, (0.5,), "test", queries, (math.inf,), (block[queries], cut_ns))
    later = data.usable_ns > cut_ns[0]
    data2 = p2._CellData(data.X, np.where(later, data.y + 100.0, data.y), data.s, data.row_ids, data.test_ids, data.usable_ns, data.h, data.start_ns)
    moved, _ = p2._cv_cell(data2, codes, 1.0, (0.5,), "test", queries, (math.inf,), (block[queries], cut_ns))
    m0, m1 = base[(0.5, math.inf)][0], moved[(0.5, math.inf)][0]
    first = block[queries] == 0
    assert np.allclose(m0[first], m1[first])                      # block 0 saw only rows usable at the first cut
    assert not np.allclose(m0[~first], m1[~first])                # later blocks do see the shifted rows: the check can fail
    loto, _ = p2._cv_cell(data2, codes, 1.0, (0.5,), "test", queries, (math.inf,), None)
    assert not np.allclose(loto[(0.5, math.inf)][0][first], m0[first])      # leave-one-test-out ignores time order


def _drift(syn, json_mod, seed, flip, strength=6.0):
    led, _ = syn.generate(syn.SyntheticConfig(seed=seed, n_tests=900, variants_per_test=1, text_effect_strength=strength,
                                              cell_params={"headline_only": (0.0, 1.0)}, s_scale=1.0))
    sig = np.array([any(w in json_mod.loads(j)["headline"] for w in syn.SIGNAL_WORDS) for j in led.features_json])
    if flip:
        late = (led["started_at"] >= led["started_at"].quantile(0.5)).to_numpy()
        led.loc[late, "y"] = led.loc[late, "y"] - 2 * strength * (sig[late] - 0.5)
    return led


def _fit_p2(imp, led, **kw):
    fs, p1m = imp("mootcourt.features"), imp("mootcourt.predictors.p1")
    # these tests are about the selection rule and the time kernel; the admission guard (T-042) is tested in test_p2_guard.py
    kw.setdefault("guard", None)
    return imp("mootcourt.predictors.p2").P2Predictor().fit(led, fs.FeatureSpace.fit(led), p1m.P1Predictor().fit(led), **kw)


def test_forward_selection_distrusts_precedents_under_drift_and_recency_finds_a_half_life(imp):
    syn = imp("mootcourt.sources.synthetic")
    drifting, stable = _drift(syn, json, 5, True), _drift(syn, json, 5, False)
    loto, fwd = _fit_p2(imp, drifting), _fit_p2(imp, drifting, selection="forward")
    rec = _fit_p2(imp, drifting, selection="forward", recency="select")
    assert fwd.lambda_by_cell["headline_only"] < loto.lambda_by_cell["headline_only"]          # time order exposes the flip
    assert math.isfinite(rec.half_life_by_cell["headline_only"]) and rec.half_life_by_cell["headline_only"] <= 180
    assert rec.score_by_cell["headline_only"] > fwd.score_by_cell["headline_only"]
    calm = _fit_p2(imp, stable, selection="forward", recency="select")
    assert math.isinf(calm.half_life_by_cell["headline_only"]) and calm.lambda_by_cell["headline_only"] >= 0.5
    rec_row = rec.selection_summary()[0]
    assert rec_row["selection"] == "forward" and rec_row["half_life_days"] == rec.half_life_by_cell["headline_only"]
    assert _fit_p2(imp, stable).selection_summary()[0]["half_life_days"] is None


def test_recency_down_weights_old_precedents_at_prediction_time(imp):
    syn = imp("mootcourt.sources.synthetic")
    led = _drift(syn, json, 6, True)
    fs = imp("mootcourt.features")
    kw = dict(lambda_override=1.0, bandwidth_override=0.5)                      # same kernel, so only the decay differs
    plain, aged = _fit_p2(imp, led, **kw), _fit_p2(imp, led, recency=60.0, **kw)
    x = fs.FeatureSpace.fit(led).transform(led.head(1))[0]
    origin = led["usable_after"].max()
    k_plain = plain.neighbor_state(x, "headline_only", origin).kernel
    k_aged = aged.neighbor_state(x, "headline_only", origin).kernel
    assert k_aged.sum() < k_plain.sum() * 0.8 and np.all(k_aged <= k_plain + 1e-12)
    assert aged.half_life_by_cell["headline_only"] == 60.0
    restored = imp("mootcourt.predictors.p2").P2Predictor.from_state(aged.to_state(), aged.space, aged.p1)
    assert restored.half_life_by_cell == aged.half_life_by_cell and restored.selection == aged.selection
    with pytest.raises(ValueError):
        _fit_p2(imp, led, recency=-3.0)
    with pytest.raises(ValueError):
        _fit_p2(imp, led, selection="random")


def test_default_selection_is_unchanged_for_the_main_run(imp, make_synth):
    ledger = _synth(make_synth, seed=67, n_tests=200)
    a, b = _run(imp, ledger), _run(imp, ledger, p2_selection=imp("mootcourt.config").P2_SELECTION_DEFAULT)
    assert np.allclose(a["logscore"], b["logscore"])
    sel = pd.DataFrame(a.attrs["selections"])
    assert {"origin", "rung", "cell", "lambda", "bandwidth_mult", "half_life_days", "selection"} <= set(sel.columns) and set(sel["rung"]) == {"P2"}


def test_report_carries_the_per_cell_selection(imp, make_synth):
    ledger = _synth(make_synth, seed=68, n_tests=240, text_effect_strength=3.0)
    sc = _run(imp, ledger, p2_selection="forward")
    doc = imp("mootcourt.report").build_document(sc, ledger=ledger, source="synthetic", snapshot_id="s", model_id="m", feature_hash="f",
                                                 command="c", seed=0, gates=GATES, B=30, variant={"p2_selection": "forward"})
    by_cell = pd.DataFrame(doc["tables"]["p2_selection_by_cell"])
    assert set(by_cell["selection"]) == {"forward"} and by_cell["origins"].min() >= 1
    assert len(doc["tables"]["p2_selection"]) == by_cell["origins"].sum() and doc["header"]["variant"] == {"p2_selection": "forward"}
    md = imp("mootcourt.report").render_markdown(doc)
    assert "## P2 selection by cell" in md and "Variant (an ablation" in md


# ------------------------------------------------------------------ CLI
@pytest.fixture
def root(imp, tmp_path, make_synth):
    ledger = _synth(make_synth, seed=69, n_tests=200)
    r = tmp_path / "root"
    imp("mootcourt.ledger").write_ledger(ledger, r / "data" / "ledger" / "ledger.parquet")
    (r / "reports").mkdir(parents=True)
    (r / "reports" / "gates.json").write_text(json.dumps(GATES))
    return r


def test_each_ablation_flag_writes_its_own_named_report(imp, root):
    runs = {"features-text": ["--features", "text"], "features-structured": ["--features", "structured"],
            "bandwidth-mult-0.25": ["--bandwidth-mult", "0.25"], "lambda-0.0": ["--lambda", "0"], "kappa-5.0": ["--kappa", "5"],
            "prior-normal": ["--prior", "normal"], "p2-selection-forward": ["--p2-selection", "forward"], "recency-select": ["--recency", "select"],
            "p2-selection-forward+recency-90": ["--p2-selection", "forward", "--recency", "90"]}
    for name, flags in runs.items():
        res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", *flags], root)
        assert res.exit_code == 0, (name, res.output)
        files = list((root / "reports" / "ablations").glob(f"backtest-synthetic-*--{name}.json"))
        assert len(files) == 1, (name, [p.name for p in (root / "reports" / "ablations").iterdir()])
        assert json.loads(files[0].read_text())["header"]["variant"]
    assert not list((root / "reports").glob("backtest-synthetic-*.json"))                # an ablation never replaces the main report
    lam0 = json.loads(next((root / "reports" / "ablations").glob("*--lambda-0.0.json")).read_text())
    agg = {r["rung"]: r for r in lam0["tables"]["aggregate"] if r["cell"] == "ALL"}
    assert agg["P2"]["logscore"] == pytest.approx(agg["P1"]["logscore"], abs=1e-9)              # lambda 0 is P1
    main = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--p2-selection", "loto", "--kappa", "20"], root)
    assert main.exit_code == 0 and list((root / "reports").glob("backtest-synthetic-*.json")), "defaults give the main report"
    for bad in (["--features", "images"], ["--prior", "cauchy"], ["--recency", "never"], ["--challenger", "xgboost"], ["--p2-selection", "x"]):
        assert _cli(imp, ["backtest", "--source", "synthetic", *bad], root).exit_code != 0


def test_challenger_flags_in_the_cli_and_the_asos_guard(imp, root):
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--challenger", "gbm", "--challenger", "local_eb,text_lr"], root)
    assert res.exit_code == 0, res.output
    js = json.loads(next((root / "reports").glob("backtest-synthetic-*.json")).read_text())
    # round 00 (T-054): `moot backtest` adds a recalibrated rung (+cal) for every challenger unless --no-recalibrate is given
    assert js["header"]["challengers"] == ["GBM", "GBM+cal", "local_eb", "local_eb+cal", "text_lr", "text_lr+cal"]
    assert "always_reference" in js["header"]["rungs"]
    assert "--challenger gbm --challenger local_eb --challenger text_lr" in js["header"]["command"]
    off = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--no-baselines"], root)
    assert off.exit_code == 0
    assert "always_reference" not in json.loads(next((root / "reports").glob("backtest-synthetic-*.json")).read_text())["header"]["rungs"]


def test_learning_curve_command_and_document(imp, tmp_path, make_synth):
    root = tmp_path / "lcroot"
    imp("mootcourt.ledger").write_ledger(_synth(make_synth, seed=71, n_tests=700), root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    res = _cli(imp, ["backtest", "--source", "synthetic", "--learning-curve", "0.3,1", "--seeds", "2", "--bootstrap", "40",
                     "--challenger", "local_eb", "--no-baselines"], root)
    assert res.exit_code == 0, res.output
    js = json.loads(next((root / "reports").glob("learning-curve-synthetic-*.json")).read_text())
    assert (root / "reports" / "figures" / "learning_curve-synthetic.png").stat().st_size > 1000
    assert next((root / "reports").glob("learning-curve-synthetic-*.md")).read_text().startswith("# Learning curve")
    assert js["fractions"] == [0.3, 1.0] and js["seeds"] == 2 and set(js["gates"]["by_target"]) == {"0.80", "0.90"}
    rows = pd.DataFrame(js["rows"])
    assert {"P0", "P1", "P2", "local_eb"} <= set(rows["rung"])
    p2 = rows[rows["rung"] == "P2"].sort_values("fraction")
    assert list(p2["fraction"]) == [0.3, 1.0] and p2["n_fit_rows"].iloc[0] < 0.5 * p2["n_fit_rows"].iloc[1]
    assert (rows.groupby("fraction")["n_scored"].nunique() == 1).all() and rows["n_scored"].nunique() == 1       # same held-out rows throughout
    assert (p2["skill_lo"] <= p2["skill"]).all() and (p2["skill"] <= p2["skill_hi"]).all()
    assert rows[rows["fraction"] == 1.0]["n_seeds"].eq(1).all() and rows[rows["fraction"] == 0.3]["n_seeds"].eq(2).all()
    assert not list((root / "reports").glob("backtest-synthetic-*.json"))
    assert _cli(imp, ["backtest", "--source", "synthetic", "--learning-curve", "0,2"], root).exit_code != 0


def test_learning_curve_subsampling_keeps_whole_tests_and_the_held_out_rows(imp, make_synth):
    lc = imp("mootcourt.learning_curve")
    ledger = _synth(make_synth, seed=70, n_tests=300)
    T = lc.final_origin(ledger, heldout_min=20)
    sub = lc.subsample(ledger, T, 0.4, seed=3)
    again = lc.subsample(ledger, T, 0.4, seed=3)
    assert list(sub["row_id"]) == list(again["row_id"]) and len(lc.subsample(ledger, T, 1.0, 0)) == len(ledger)
    from mootcourt.ledger import visible_rows
    hist_all, hist_sub = visible_rows(ledger, T), visible_rows(sub, T)
    assert 0.3 < hist_sub["test_id"].nunique() / hist_all["test_id"].nunique() < 0.5
    kept = set(hist_sub["test_id"])
    assert set(hist_all[hist_all["test_id"].isin(kept)]["row_id"]) == set(hist_sub["row_id"])         # all rows of a kept test stay
    held = ledger[ledger["started_at"] >= T]
    assert set(held["row_id"]) <= set(sub["row_id"])
    assert lc.parse_fractions("0.5, 0.1,1") == [0.1, 0.5, 1.0]
    for bad in ("", "0", "1.5", "a"):
        with pytest.raises(ValueError):
            lc.parse_fractions(bad)


# ------------------------------------------------------------------ README blocks
def _renderer():
    spec = importlib.util.spec_from_file_location("rr", ROOT / "scripts" / "render_readme_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_readme_ablation_and_learning_curve_blocks_regenerate_from_report_json(imp, root):
    mod = _renderer()
    reports = root / "reports"
    assert mod.ablation_lines(reports) == [] and mod.learning_curve_lines(reports) == [] and mod.challenger_lines(reports) == []
    assert _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20"], root).exit_code == 0
    assert _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--p2-selection", "forward"], root).exit_code == 0
    assert _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--features", "text"], root).exit_code == 0
    assert _cli(imp, ["backtest", "--source", "synthetic", "--learning-curve", "0.5,1", "--seeds", "2", "--bootstrap", "20"], root).exit_code == 0
    lines = "\n".join(mod.ablation_lines(reports, "synthetic"))
    for name in ("p2-selection-forward", "features-text"):
        assert name in lines
    main = json.loads(next(p for p in reports.glob("backtest-synthetic-*.json")).read_text())
    p2 = next(r for r in main["tables"]["aggregate"] if r["cell"] == "ALL" and r["rung"] == "P2")
    assert f"{p2['logscore']:.4f}" in lines                                                      # the baseline row comes from the main JSON
    lc = "\n".join(mod.learning_curve_lines(reports, "synthetic"))
    js = json.loads(next(reports.glob("learning-curve-synthetic-*.json")).read_text())
    assert f"{js['rows'][0]['skill']:.4f}" in lc and "n_200" in lc
    assert mod.ablation_lines(reports, "upworthy") == []


def test_a_query_far_from_every_precedent_gives_finite_moments(imp, make_synth):
    """Regression: with a small bandwidth the kernel of a distant query underflowed and squared weights became 0, giving NaN."""
    ledger = _synth(make_synth, seed=72, n_tests=200, variants_per_test=1, text_effect_strength=3.0, cell_params={"headline_only": (0.0, 1.0)})
    fs = imp("mootcourt.features")
    space = fs.FeatureSpace.fit(ledger, feature_set="structured")
    p2 = imp("mootcourt.predictors.p2").P2Predictor().fit(ledger, space, imp("mootcourt.predictors.p1").P1Predictor().fit(ledger),
                                                          lambda_override=0.6, bandwidth_override=0.125)
    data = p2._cells["headline_only"]
    x = space.transform(ledger.head(1))[0].copy()
    x[0] = data.X[:, 0].max() + data.h * math.sqrt(130.0)                # the nearest precedent now has a kernel value near 1e-28
    origin = ledger["usable_after"].max()
    st = p2.neighbor_state(x, "headline_only", origin)
    assert 0 < st.kernel.max() <= 1.0 + 1e-12
    mo = st.moments()
    assert all(np.isfinite([mo.m, mo.v_m, mo.n_eff, mo.theta_hat, mo.v]))
    assert 0.0 <= p2.predict(x, 1.0, "headline_only", origin).p_sig(1.0) <= 1.0
    # review N (REV-N-005): a query beyond the float32 range of the validation (here near 1e-217) gets P1's predictive, an empty state
    x[0] = data.X[:, 0].max() + data.h * math.sqrt(1000.0)
    far = p2.neighbor_state(x, "headline_only", origin)
    assert len(far.row_ids) == 0 and far.lam == 0.0
    assert 0.0 <= p2.predict(x, 1.0, "headline_only", origin).p_sig(1.0) <= 1.0


def test_final_origin_prefers_the_latest_big_quarter_and_falls_back_to_the_biggest(imp, make_synth):
    lc = imp("mootcourt.learning_curve")
    ledger = _synth(make_synth, seed=73, n_tests=300)
    from mootcourt.harness import quarterly_origins
    adm = ledger[ledger["status"] == "admitted"]
    origins = quarterly_origins(ledger)
    counts = {t: int(((adm["started_at"] >= t) & (adm["started_at"] < t + pd.DateOffset(months=3))).sum()) for t in origins}
    assert counts[lc.final_origin(ledger, heldout_min=1)] > 0
    big = [t for t, n in counts.items() if n >= 60 and len(adm[adm["usable_after"] <= t]) >= 20]
    assert lc.final_origin(ledger, heldout_min=60) == big[-1]
    eligible = {t: n for t, n in counts.items() if n > 0 and len(adm[adm["usable_after"] <= t]) >= 20}
    best = max(eligible.values())
    assert eligible[lc.final_origin(ledger, heldout_min=10**6)] == best               # nothing reaches the minimum: the biggest quarter


def test_relative_lift_ledger_rebuilds_the_first_runs_y_and_s(imp, make_synth):
    scale = imp("mootcourt.scale")
    ledger = _synth(make_synth, seed=74, n_tests=20).head(6).copy()
    ledger["source"] = "upworthy"
    feats = []
    for i, j in enumerate(ledger["features_json"]):
        f = json.loads(j)
        f["post_launch"] = {"relative_lift": 10.0 + i, "relative_lift_se": 2.0 + i} if i != 3 else {"relative_lift": None, "relative_lift_se": None}
        feats.append(json.dumps(f))
    ledger["features_json"] = feats
    out = scale.relative_lift_ledger(ledger)
    assert list(out["y"].iloc[[0, 1, 2, 4]]) == [10.0, 11.0, 12.0, 14.0] and list(out["s"].iloc[[0, 5]]) == [2.0, 7.0]
    assert out["status"].iloc[3] == "low_exposure" and (out["status"].drop(out.index[3]) == "admitted").all()
    assert (ledger["y"] != out["y"]).any() and ledger["status"].eq("admitted").all()                      # the input is untouched


def test_realized_s_star_is_the_realized_standard_error_and_the_default_is_not(imp, make_synth):
    ledger = _synth(make_synth, seed=75, n_tests=120)
    h = imp("mootcourt.harness")
    rungs = {"P0": h.default_rungs("synthetic", ledger)["P0"]}
    sc = h.rolling_origin(ledger, rungs, h.quarterly_origins(ledger), source="synthetic", s_star_mode="realized")
    assert np.allclose(sc["s_star"], sc["s"])
    with pytest.raises(ValueError):
        h.rolling_origin(ledger, rungs, h.quarterly_origins(ledger), s_star_mode="oracle")


def test_cautionary_flags_are_validated_and_upworthy_only(imp, root):
    for bad in (["--effect-scale", "relative"], ["--effect-scale", "log"], ["--s-star", "oracle"]):
        assert _cli(imp, ["backtest", "--source", "synthetic", *bad], root).exit_code != 0
    res = _cli(imp, ["backtest", "--source", "synthetic", "--s-star", "realized", "--bootstrap", "20"], root)
    assert res.exit_code == 0 and list((root / "reports" / "ablations").glob("backtest-synthetic-*--s-star-realized.json"))


def test_readme_has_a_cautionary_block_with_calibration_by_precision(imp, root):
    mod = _renderer()
    reports = root / "reports"
    assert mod.cautionary_lines(reports) == []
    assert _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--s-star", "realized"], root).exit_code == 0
    src = next((reports / "ablations").glob("backtest-synthetic-*--s-star-realized.json"))
    (reports / "ablations" / f"backtest-upworthy-x--{mod.CAUTIONARY_SUFFIX}.json").write_text(src.read_text())
    text = "\n".join(mod.cautionary_lines(reports))
    assert "### The cautionary run" in text and "Calibration by precision" in text and "| P1 | 1 |" in text
    assert "--effect-scale relative --s-star realized" in text
