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
