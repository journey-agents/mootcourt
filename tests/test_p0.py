"""T-005 contracts: P0 base rate."""
import datetime as dt

import pandas as pd
import pytest

UTC = dt.timezone.utc


def test_p0_matches_cell_mean_and_variance(imp, tiny_ledger, origin):
    p0 = imp("mootcourt.predictors.p0").P0Predictor().fit(tiny_ledger)
    pred = p0.predict(None, 1.0, "headline_only", origin)
    assert pred.mean() == pytest.approx(tiny_ledger["y"].mean(), abs=0.02)
    assert pred.var() == pytest.approx(tiny_ledger["y"].var(ddof=0), rel=0.02)
    assert pred.pmf.sum() == pytest.approx(1.0, abs=1e-12)


def test_p0_uses_only_visible_admitted_rows(imp, ledger_builder, origin):
    df = ledger_builder(n=200, mu=2.0, tau=1.0, seed=3)
    poison = ledger_builder(n=50, mu=500.0, tau=1.0, seed=4, id_prefix="x")
    poison.loc[poison.index[:25], "status"] = "low_exposure"       # excluded
    poison.loc[poison.index[25:], "usable_after"] = origin + pd.Timedelta(days=1)  # not yet visible
    full = pd.concat([df, poison], ignore_index=True)
    p0 = imp("mootcourt.predictors.p0").P0Predictor().fit(full)
    pred = p0.predict(None, 1.0, "headline_only", origin)
    assert pred.mean() == pytest.approx(df["y"].mean(), abs=0.05), "poisoned rows leaked into P0"


def test_p0_sig_positive_frequency(imp, ledger_builder, origin):
    df = ledger_builder(n=400, seed=5)
    p0 = imp("mootcourt.predictors.p0").P0Predictor().fit(df)
    expected = float((df["y"] > 1.96 * df["s"]).mean())
    assert p0.sig_positive_frequency("headline_only", origin) == pytest.approx(expected, abs=1e-12)


def test_p0_falls_back_to_global_for_small_cell(imp, ledger_builder, origin):
    big = ledger_builder(n=300, cell="headline_only", seed=6)
    tiny = ledger_builder(n=1, cell="image_only", seed=7, id_prefix="t")
    p0 = imp("mootcourt.predictors.p0").P0Predictor().fit(pd.concat([big, tiny], ignore_index=True))
    pred = p0.predict(None, 1.0, "image_only", origin)
    glob = pd.concat([big, tiny])["y"]
    assert pred.mean() == pytest.approx(glob.mean(), abs=0.05)
    assert p0.used_global_fallback("image_only", origin) is True
    assert p0.used_global_fallback("headline_only", origin) is False


def test_p0_unknown_cell_with_no_rows_raises(imp, origin):
    empty = imp("mootcourt.ledger")
    p0 = imp("mootcourt.predictors.p0").P0Predictor()
    with pytest.raises(ValueError):
        p0.fit(pd.DataFrame({c: [] for c in empty.LEDGER_COLUMNS}))


def test_p0_with_a_t_density_fits_heavy_tails_and_leaves_everything_else_alone(imp, ledger_builder, origin):
    """The setting changes the density of the log score only: probabilities and intervals are those of the normal base rate."""
    import numpy as np
    from scipy import stats

    p0_mod = imp("mootcourt.predictors.p0")
    rng = np.random.default_rng(0)
    y = stats.t.rvs(3, loc=0.1, scale=0.5, size=400, random_state=rng)          # heavy tails: three degrees of freedom
    rows = ledger_builder(n=400, seed=5)
    rows["y"], rows["s"] = y, 0.2
    cell = str(rows["cell"].iloc[0])
    normal, heavy = p0_mod.P0Predictor().fit(rows), p0_mod.P0Predictor(density="t").fit(rows)
    f_n, f_t = normal.forecast(cell, origin), heavy.forecast(cell, origin)
    assert f_t == f_n                                                              # p_sig, p_dir, the quantiles, the mean and the variance
    sd = np.sqrt(f_n.var)
    assert np.allclose(normal.logscore(y, cell, origin), stats.norm.logpdf(y, f_n.mean, sd))          # the default is the normal formula
    nu, loc, scale = heavy.density_params(cell, origin)
    assert nu in (3, 5) and abs(loc - 0.1) < 0.1 and 0.35 < scale < 0.65
    assert np.allclose(heavy.logscore(y, cell, origin), stats.t.logpdf(y, nu, loc, scale))
    assert heavy.logscore(y, cell, origin).mean() > normal.logscore(y, cell, origin).mean() + 0.05     # the heavy tails are found
    cols, keep = heavy.score_block(rows, y, np.full(len(y), 0.2), origin)
    assert keep.all() and np.allclose(cols["p_sig"], f_n.p_sig) and np.allclose(cols["logscore"], heavy.logscore(y, cell, origin))


def test_p0_with_a_t_density_on_normal_data_stays_close_to_the_normal_and_rejects_an_unknown_density(imp, ledger_builder, origin):
    import numpy as np

    p0_mod = imp("mootcourt.predictors.p0")
    rng = np.random.default_rng(1)
    y = rng.normal(0.0, 0.4, size=400)
    rows = ledger_builder(n=400, seed=6)
    rows["y"], rows["s"] = y, 0.2
    cell = str(rows["cell"].iloc[0])
    normal, heavy = p0_mod.P0Predictor().fit(rows), p0_mod.P0Predictor(density="t").fit(rows)
    assert heavy.density_params(cell, origin)[0] >= 10                              # no heavy tails to find
    assert abs(heavy.logscore(y, cell, origin).mean() - normal.logscore(y, cell, origin).mean()) < 0.02
    few = ledger_builder(n=3, seed=7)
    thin = p0_mod.P0Predictor(density="t").fit(few)
    assert np.isinf(thin.density_params(str(few["cell"].iloc[0]), origin)[0])       # too few rows to fit a tail: the normal limit
    with pytest.raises(ValueError, match="density"):
        p0_mod.P0Predictor(density="cauchy")


def test_the_base_density_setting_reaches_the_rung_and_names_the_ablation(imp, tiny_ledger, origin):
    harness, cli = imp("mootcourt.harness"), imp("mootcourt.cli")
    default = harness.default_rungs("synthetic", tiny_ledger)["P0"](tiny_ledger, origin)
    heavy = harness.default_rungs("synthetic", tiny_ledger, base_density="t")["P0"](tiny_ledger, origin)
    assert default.density == "normal" and heavy.density == "t"
    args = ("both", None, None, None, "t", None, None)
    assert cli._variant_settings(*args) == {}                                                        # the main run keeps its name
    assert cli._variant_settings(*args, base_density="t") == {"base_density": "t"}
