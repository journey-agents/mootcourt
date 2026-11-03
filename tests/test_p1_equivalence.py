"""T-006 addition: the fast scale-mixture likelihood used by the optimizer agrees with the grid definition."""
import numpy as np
import pytest


@pytest.mark.parametrize("nu", [3, 5, 10, 30, float("inf")])
def test_fast_likelihood_matches_grid_definition(imp, nu):
    p1 = imp("mootcourt.predictors.p1")
    rng = np.random.default_rng(7)
    s = rng.uniform(0.3, 2.0, 300)
    y = 1.0 + 2.0 * rng.standard_t(5, 300) + rng.normal(0, s)
    grid = p1.marginal_loglik(y, s, mu=1.0, tau=2.0, nu=nu)
    fast = p1._loglik_fast(y, s, 1.0, 2.0, nu)
    assert fast == pytest.approx(grid, rel=1e-4)
