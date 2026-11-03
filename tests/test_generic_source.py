"""T-034/T-035: an imported source is forecast with exposure-scaled standard errors and cell-only features."""
import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner


@pytest.fixture(scope="module")
def sample_ledger(tmp_path_factory):
    import importlib

    tmp = tmp_path_factory.mktemp("gs")
    path = tmp / "l.parquet"
    from mootcourt.importers.sample import sample_exchange
    ex = tmp / "s.csv"
    sample_exchange().to_csv(ex, index=False)
    res = CliRunner().invoke(importlib.import_module("mootcourt.cli").app, ["ingest", "--format", "generic", "--input", str(ex),
                                                                            "--source-name", "sample", "--ledger", str(path)])
    assert res.exit_code == 0, res.output
    return importlib.import_module("mootcourt.ledger").read_ledger(path)


def test_generic_s_star_never_uses_the_rows_own_standard_error(imp, sample_ledger):
    scale = imp("mootcourt.scale")
    led = sample_ledger
    cut = led["usable_after"].quantile(0.5)
    visible, scored = led[led["usable_after"] <= cut], led[led["usable_after"] > cut].copy()
    a = scale.s_star_rows(scored, visible)
    scored["s"] = scored["s"] * 7.0
    b = scale.s_star_rows(scored, visible)
    assert np.allclose(a, b)
    first = scored.iloc[0]
    med = scale.median_s_sqrt_n(visible)[first["cell"]]
    assert a[0] == pytest.approx(med / np.sqrt(0.5 * (first["n_ref"] + first["n_var"])))


def test_synthetic_s_star_is_still_as_given(imp, make_synth):
    scale = imp("mootcourt.scale")
    led = make_synth(seed=3, n_tests=60, variants_per_test=2)[0]
    assert np.allclose(scale.s_star_rows(led, led), led["s"].to_numpy())


def test_sources_without_headline_text_get_the_cell_only_space(imp, sample_ledger, make_synth):
    f = imp("mootcourt.features")
    assert f.use_cell_only("sample", sample_ledger) is True and f.use_cell_only("asos", None) is True
    assert f.use_cell_only("upworthy", sample_ledger) is False
    assert f.use_cell_only("synthetic", make_synth(seed=3, n_tests=20, variants_per_test=2)[0]) is False
    with_text = sample_ledger.copy()
    with_text["features_json"] = '{"headline": "a title"}'
    assert f.use_cell_only("sample", with_text) is False


def test_a_backtest_runs_on_an_imported_source(imp, sample_ledger):
    harness = imp("mootcourt.harness")
    rungs = {k: v for k, v in harness.default_rungs("sample", sample_ledger).items() if k in ("P0", "P1", "P2")}
    sc = harness.rolling_origin(sample_ledger, rungs, harness.quarterly_origins(sample_ledger), source="sample")
    assert len(sc) > 100 and set(sc["rung"]) == {"P0", "P1", "P2"}
    assert (sc["s_star"] != sc["s"]).any() and isinstance(sc, pd.DataFrame)
