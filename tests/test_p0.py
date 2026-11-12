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


def test_recent_share_mirrors_the_period_rule_of_the_prior(imp):
    import numpy as np

    p0_mod = imp("mootcourt.predictors.p0")
    origin = pd.Timestamp("2014-07-01", tz="UTC")
    # all rows: 40 in 2014Q1 at a share of 0.5, 40 in 2014Q2 at 0.1, 5 in 2014Q3 (the quarter being forecast, not complete)
    ev_all = np.r_[np.tile([1.0, 0.0], 20), np.r_[np.ones(4), np.zeros(36)], np.ones(5)]
    per_all = np.array(["2014Q1"] * 40 + ["2014Q2"] * 40 + ["2014Q3"] * 5, dtype=object)
    ev_cell, per_cell = ev_all[:50], per_all[:50]                       # 40 rows of Q1 and 10 of Q2: the cell has no solid Q2 of its own
    share = float(ev_cell.mean())
    assert p0_mod.last_complete_period(per_all, origin) == "2014Q2"     # the newest quarter that has ended and holds 30 rows
    assert p0_mod.last_complete_period(per_cell, origin) == "2014Q1"
    assert p0_mod.recent_share(ev_cell, per_cell, ev_all, per_all, origin, "none") == share
    quarter = p0_mod.recent_share(ev_cell, per_cell, ev_all, per_all, origin, "quarter")
    assert quarter == pytest.approx(share + (0.1 - float(ev_all.mean())) / 2.0)
    assert p0_mod.recent_share(ev_cell, per_cell, ev_all, per_all, origin, "cell-quarter") == pytest.approx(0.5)
    early = pd.Timestamp("2014-01-15", tz="UTC")                        # no quarter is complete yet: both rules leave the share alone
    for rule in ("quarter", "cell-quarter"):
        assert p0_mod.recent_share(ev_cell, per_cell, ev_all, per_all, early, rule) == share
    assert p0_mod.recent_share(np.ones(40), per_all[:40], np.ones(80), per_all[:80], origin, "quarter") == 1.0   # clipped to the unit interval
    with pytest.raises(ValueError, match="recency"):
        p0_mod.P0Predictor(recency="monthly")


def test_a_recency_rule_moves_only_the_probability_of_the_event(imp, ledger_builder):
    import numpy as np

    p0_mod = imp("mootcourt.predictors.p0")
    old = ledger_builder(n=300, mu=3.0, tau=1.0, seed=31, id_prefix="a")
    new = ledger_builder(n=300, mu=-3.0, tau=1.0, seed=32, id_prefix="b")
    old["usable_after"], old["period"] = pd.Timestamp("2014-02-01", tz="UTC"), "2014Q1"
    new["usable_after"], new["period"] = pd.Timestamp("2014-05-01", tz="UTC"), "2014Q2"
    df = pd.concat([old, new], ignore_index=True)
    origin, cell = pd.Timestamp("2014-07-01", tz="UTC"), str(df["cell"].iloc[0])
    plain = p0_mod.P0Predictor().fit(df)
    y = np.linspace(-5.0, 5.0, 11)
    f0 = plain.forecast(cell, origin)
    for rule in ("quarter", "cell-quarter"):
        rec = p0_mod.P0Predictor(recency=rule).fit(df)
        f1 = rec.forecast(cell, origin)
        assert f1.p_sig < f0.p_sig                                       # the last quarter's results are lower, so the probability falls
        assert rec.sig_positive_frequency(cell, origin) == f1.p_sig
        assert (f1.mean, f1.var, f1.p_dir, f1.lo80, f1.hi90) == (f0.mean, f0.var, f0.p_dir, f0.lo80, f0.hi90)
        assert np.array_equal(rec.logscore(y, cell, origin), plain.logscore(y, cell, origin))
    sig_new = float((new["y"] > p0_mod.Z * new["s"]).mean())
    assert p0_mod.P0Predictor(recency="cell-quarter").fit(df).forecast(cell, origin).p_sig == pytest.approx(sig_new)


def test_the_base_recency_setting_reaches_the_rung_the_planned_event_and_the_name(imp, tiny_ledger, origin):
    import numpy as np

    harness, cli = imp("mootcourt.harness"), imp("mootcourt.cli")
    rung = harness.default_rungs("synthetic", tiny_ledger, base_recency="quarter")["P0"](tiny_ledger, origin)
    assert rung.recency == "quarter" and harness.default_rungs("synthetic", tiny_ledger)["P0"](tiny_ledger, origin).recency == "none"
    args = ("both", None, None, None, "t", None, None)
    assert cli._variant_settings(*args, base_recency="quarter") == {"base_recency": "quarter"}
    both = cli._variant_settings(*args, exposure="cell-median", base_recency="quarter")
    assert cli._variant_name(both) == "exposure-cell-median+base-recency-quarter"
    visible = tiny_ledger.copy()
    half = len(visible) // 2
    visible["period"] = ["2013Q1"] * half + ["2013Q2"] * (len(visible) - half)
    visible.loc[visible.index[half:], "y"] = -50.0                       # the last quarter has no significant positive result
    later = pd.Timestamp("2013-07-01", tz="UTC")
    plain = harness._planned_event_base(visible, visible.head(5), "realized")
    assert np.array_equal(plain, harness._planned_event_base(visible, visible.head(5), "realized", later, "none"))
    moved = harness._planned_event_base(visible, visible.head(5), "realized", later, "cell-quarter")
    assert np.all(moved == 0.0) and np.all(plain > 0.0)
