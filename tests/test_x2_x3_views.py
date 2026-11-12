"""X2 and X3 of the paper v2 plan: the planned-precision relative-lift view and the exposure fixed at the cell median."""

import json

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner


def _upworthy_like(make_synth, n_tests=60, seed=81):
    ledger = make_synth(seed=seed, n_tests=n_tests, variants_per_test=2)[0].copy()
    ledger["source"] = "upworthy"
    feats = []
    for i, (j, nr, nv, s) in enumerate(zip(ledger["features_json"], ledger["n_ref"], ledger["n_var"], ledger["s"])):
        f = json.loads(j)
        c = 0.02 + 0.001 * (i % 5)
        f["post_launch"] = {"ctr_ref": c, "relative_lift": 5.0 + (i % 7), "relative_lift_se": 3.0 + (i % 3)}
        feats.append(json.dumps(f))
    ledger["features_json"] = feats
    ledger["n_ref"] = (3000 + 100 * (np.arange(len(ledger)) % 9)).astype("int64")
    ledger["n_var"] = ledger["n_ref"] + 50
    return ledger


def test_planned_relative_standard_error_is_s_star_over_the_cell_rate(imp, make_synth):
    scale = imp("mootcourt.scale")
    ledger = _upworthy_like(make_synth)
    base = scale.s_star_rows(ledger, ledger)
    view = scale.relative_lift_ledger(ledger, planned=True)
    assert (view[scale.PLANNED_SCALE_COLUMN] == "relative").all()
    by_cell = scale.cell_median_ctr(ledger)
    c = np.array([scale.lookup_ctr(by_cell, k) for k in ledger["cell"]])
    got = scale.s_star_rows(view, view)
    assert np.allclose(got, base / c)
    # without the marker (the cautionary run's view) s_star_rows is unchanged
    assert np.allclose(scale.s_star_rows(scale.relative_lift_ledger(ledger), ledger), base)


def test_planned_relative_view_leaves_other_sources_alone(imp, make_synth):
    scale = imp("mootcourt.scale")
    ledger = _upworthy_like(make_synth, n_tests=20)
    ledger.loc[ledger.index[:5], "source"] = "synthetic"
    view = scale.relative_lift_ledger(ledger, planned=True)
    assert np.allclose(scale.s_star_rows(view, view)[:5], ledger["s"].to_numpy()[:5])


def test_cell_median_exposure_is_constant_within_a_cell_and_leaves_y_and_s(imp, make_synth):
    scale = imp("mootcourt.scale")
    ledger = _upworthy_like(make_synth)
    ledger.loc[ledger.index[3], "status"] = "low_exposure"
    view = scale.cell_median_exposure_ledger(ledger)
    expo = scale.planned_exposure(view)
    for cell, g in view.groupby("cell"):
        assert len(set(expo[g.index])) == 1
        adm = (ledger["cell"] == cell) & (ledger["status"] == "admitted")
        assert expo[g.index[0]] == pytest.approx(float(np.median(scale.planned_exposure(ledger)[adm.to_numpy()])), abs=1.0)
    assert view["y"].equals(ledger["y"]) and view["s"].equals(ledger["s"]) and view["status"].equals(ledger["status"])
    assert (view["n_ref"] == ledger["n_ref"]).sum() < len(ledger)  # and the input is untouched
    assert ledger["n_ref"].nunique() > 3
    # the planned standard error now varies only through the cell's median click-through rate
    s_star = scale.s_star_rows(view, view)
    for cell, g in view.groupby("cell"):
        assert np.allclose(s_star[g.index], s_star[g.index[0]])


def test_cell_median_exposure_over_visible_rows_reads_nothing_after_the_quarter_start(imp, make_synth):
    scale = imp("mootcourt.scale")
    ledger = _upworthy_like(make_synth)
    half = len(ledger) // 2
    early, late = ledger.index[:half], ledger.index[half:]
    for rows, month in ((early, 2), (late, 5)):
        ledger.loc[rows, "started_at"] = pd.Timestamp(2014, month, 1, tz="UTC")
        ledger.loc[rows, "usable_after"] = pd.Timestamp(2014, month, 10, tz="UTC")
    ledger.loc[late, ["n_ref", "n_var"]] = ledger.loc[late, ["n_ref", "n_var"]].to_numpy() * 50      # later tests get far more traffic
    view = scale.cell_median_exposure_ledger(ledger, visible_only=True)
    expo, raw = scale.planned_exposure(view), scale.planned_exposure(ledger)
    adm = (ledger["status"] == "admitted").to_numpy()
    for cell in ledger["cell"].unique():
        in_cell = (ledger["cell"] == cell).to_numpy()
        e, la = np.flatnonzero(in_cell & ledger.index.isin(early)), np.flatnonzero(in_cell & ledger.index.isin(late))
        if len(e) == 0 or len(la) == 0:
            continue
        seen = float(np.median(raw[in_cell & adm & ledger.index.isin(early)]))
        assert np.allclose(expo[la], seen, atol=1.0)                    # the second quarter reads only the first quarter's rows
        assert np.allclose(expo[e], seen, atol=1.0)                     # the first quarter has no earlier rows: the earliest median
        whole = scale.planned_exposure(scale.cell_median_exposure_ledger(ledger))
        assert whole[la[0]] > expo[la[0]]                               # the whole-ledger median has seen the later traffic
    assert view["y"].equals(ledger["y"]) and view["s"].equals(ledger["s"])


def test_exposure_flag_is_validated_and_upworthy_only(imp, tmp_path):
    cli = imp("mootcourt.cli")
    res = CliRunner().invoke(cli.app, ["backtest", "--source", "synthetic", "--exposure", "cell-median"], env={"MOOTCOURT_DATA_ROOT": str(tmp_path)})
    assert res.exit_code != 0 and "Upworthy" in res.output
    res = CliRunner().invoke(cli.app, ["backtest", "--source", "upworthy", "--exposure", "fixed"], env={"MOOTCOURT_DATA_ROOT": str(tmp_path)})
    assert res.exit_code != 0


def test_variant_names_of_the_new_runs(imp):
    cli = imp("mootcourt.cli")
    v = cli._variant_settings("both", None, None, None, "t", None, None, exposure="cell-median")
    assert v == {"exposure": "cell-median"} and cli._variant_name(v) == "exposure-cell-median"
    v = cli._variant_settings("both", None, None, None, "t", None, None, exposure="cell-median-visible", base_density="t")
    assert cli._variant_name(v) == "exposure-cell-median-visible+base-density-t"
    v = cli._variant_settings("both", None, None, None, "t", None, None, effect_scale="relative")
    assert cli._variant_name(v) == "effect-scale-relative" and cli._variant_flags(v) == " --effect-scale relative"
    v = cli._variant_settings("both", None, None, None, "t", None, None, s_star="realized")
    assert cli._variant_name(v) == "s-star-realized"


GATES = {
    "n_200": 20,
    "n_400": 30,
    "target_power": 0.9,
    "decision_target": 0.9,
    "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}},
}


def test_the_three_single_change_runs_write_their_named_reports(imp, make_synth, tmp_path):
    root = tmp_path / "root"
    imp("mootcourt.ledger").write_ledger(_upworthy_like(make_synth, n_tests=400, seed=5), root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "gates.json").write_text(json.dumps(GATES))
    cli = imp("mootcourt.cli")
    for flags, name in (
        (["--exposure", "cell-median"], "exposure-cell-median"),
        (["--effect-scale", "relative"], "effect-scale-relative"),
        (["--s-star", "realized"], "s-star-realized"),
    ):
        res = CliRunner().invoke(cli.app, ["backtest", "--source", "upworthy", "--bootstrap", "20", *flags], env={"MOOTCOURT_DATA_ROOT": str(root)})
        assert res.exit_code == 0, res.output
        assert list((root / "reports" / "ablations").glob(f"backtest-upworthy-*--{name}.json"))
    fixed = next((root / "reports" / "ablations").glob("scores-upworthy-*--exposure-cell-median.parquet"))
    import pandas as pd

    sc = pd.read_parquet(fixed)
    assert (sc.groupby("cell")["exposure"].nunique() == 1).all()  # the exposure the forecaster saw is the cell's constant
