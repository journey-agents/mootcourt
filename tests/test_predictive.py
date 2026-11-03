"""T-005 contracts: Predictive on the theta grid, scoring primitives."""
import time

import numpy as np
import pytest
from scipy import stats


def _normal_predictive(imp, mu=1.0, tau=2.0):
    base = imp("mootcourt.predictors.base")
    grid = base.build_grid(mu, tau)
    return base.Predictive.from_normal(grid, mu, tau), grid


def test_grid_is_801_points_spanning_8_tau(imp):
    base = imp("mootcourt.predictors.base")
    grid = base.build_grid(1.0, 2.0)
    assert len(grid) == 801
    assert grid[0] <= 1.0 - 16.0 + 1e-9 and grid[-1] >= 1.0 + 16.0 - 1e-9
    d = np.diff(grid)
    np.testing.assert_allclose(d, d[0], rtol=1e-9)


def test_grid_covers_observed_y_range(imp):
    base = imp("mootcourt.predictors.base")
    grid = base.build_grid(0.0, 1.0, y_min=-50.0, y_max=70.0)
    assert grid[0] <= -50.0 and grid[-1] >= 70.0 and len(grid) == 801


def test_grid_rejects_nonpositive_tau(imp):
    with pytest.raises(ValueError):
        imp("mootcourt.predictors.base").build_grid(0.0, 0.0)


def test_pmf_sums_to_one_and_rejects_bad_pmf(imp):
    base = imp("mootcourt.predictors.base")
    pred, grid = _normal_predictive(imp)
    assert pred.pmf.sum() == pytest.approx(1.0, abs=1e-12)
    with pytest.raises(ValueError):
        base.Predictive(grid, np.full(len(grid), 2.0))
    with pytest.raises(ValueError):
        base.Predictive(grid, -np.ones(len(grid)))


def test_closed_forms_for_normal_predictive(imp):
    pred, _ = _normal_predictive(imp, 1.0, 2.0)
    s = 1.5
    total_sd = np.sqrt(2.0 ** 2 + s ** 2)
    assert pred.mean() == pytest.approx(1.0, abs=0.02)
    assert pred.var() == pytest.approx(4.0, rel=0.01)
    assert pred.quantile(0.9) == pytest.approx(stats.norm.ppf(0.9, 1.0, 2.0), abs=0.05)
    assert pred.prob_gt(0.5) == pytest.approx(stats.norm.sf(0.5, 1.0, 2.0), rel=0.01)
    assert pred.p_win() == pytest.approx(stats.norm.sf(0.0, 1.0, 2.0), rel=0.01)
    assert pred.p_sig(s, z=1.96) == pytest.approx(stats.norm.sf(1.96 * s, 1.0, total_sd), rel=0.01)
    lo, hi = pred.interval(0.9, s_star=s)
    assert lo == pytest.approx(stats.norm.ppf(0.05, 1.0, total_sd), abs=0.05)
    assert hi == pytest.approx(stats.norm.ppf(0.95, 1.0, total_sd), abs=0.05)


def test_logscore_and_crps_match_closed_forms(imp):
    pred, _ = _normal_predictive(imp, 1.0, 2.0)
    s = 1.5
    sd = np.sqrt(4.0 + s * s)
    for y in (-3.0, 0.5, 1.0, 4.2):
        ls = pred.logscore(y, s)
        assert ls == pytest.approx(stats.norm.logpdf(y, 1.0, sd), rel=0.01)
        z = (y - 1.0) / sd
        crps = sd * (z * (2 * stats.norm.cdf(z) - 1) + 2 * stats.norm.pdf(z) - 1 / np.sqrt(np.pi))
        assert pred.crps(y, s) == pytest.approx(crps, rel=0.01)


def test_crps_matches_monte_carlo_on_skewed_predictive(imp):
    base = imp("mootcourt.predictors.base")
    grid = base.build_grid(2.0, 3.0)
    pmf = np.exp(-0.5 * ((grid - 1.0) / 1.5) ** 2) * (1 + 3 * (grid > 1.0) * (grid - 1.0))  # right-skewed
    pmf = np.clip(pmf, 0, None) / np.clip(pmf, 0, None).sum()
    pred = base.Predictive(grid, pmf)
    s, y = 1.2, 3.0
    rng = np.random.default_rng(0)
    draws = rng.choice(grid, size=200000, p=pmf) + rng.normal(0, s, 200000)
    other = rng.permutation(draws)
    mc = np.abs(draws - y).mean() - 0.5 * np.abs(draws - other).mean()
    assert pred.crps(y, s) == pytest.approx(mc, rel=0.02)


def test_scores_are_vectorised_and_validate_s(imp):
    pred, _ = _normal_predictive(imp)
    y = np.array([0.0, 1.0, 2.0])
    s = np.array([1.0, 1.5, 2.0])
    assert pred.logscore(y, s).shape == (3,) and pred.crps(y, s).shape == (3,)
    with pytest.raises(ValueError):
        pred.logscore(0.0, -1.0)


@pytest.mark.slow
def test_scoring_20000_rows_in_under_60_seconds(imp):
    pred, _ = _normal_predictive(imp)
    rng = np.random.default_rng(1)
    y = rng.normal(1, 3, 20000)
    s = rng.uniform(0.5, 3, 20000)
    t = time.perf_counter()
    pred.crps(y, s)
    pred.logscore(y, s)
    assert time.perf_counter() - t < 60


def test_module_docstring_names_the_crps_method(imp):
    doc = (imp("mootcourt.predictors.base").__doc__ or "").lower()
    assert "crps" in doc and ("fft" in doc or "chunk" in doc)
