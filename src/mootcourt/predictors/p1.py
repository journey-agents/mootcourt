"""P1 empirical-Bayes prior with partial pooling.

Per cell the true effect has a Student-t prior ``theta ~ t(mu, tau, nu)`` (``tau`` is the scale). The
parameters maximize the marginal likelihood ``sum_i log integral Normal(y_i | theta, s_i^2) t(theta) d theta``
with ``nu`` chosen from {3, 5, 10, 30, inf}. Units: ``mu`` and ``tau`` are in the units of y.

Two evaluations of the marginal likelihood exist and agree to about 1e-4 per 300 rows:

* ``marginal_loglik`` integrates on a theta grid. It is the definition and is what the tests compare
  with the closed Normal-Normal marginal.
* The optimizer uses ``_loglik_fast``: the same integral written as a scale mixture of normals,
  ``t(mu, tau, nu) = integral Normal(mu, tau^2 / g) Gamma(g; nu/2, nu/2) dg``, integrated over ``log g`` by
  the trapezoid rule (about 90 nodes). It costs about 90 normal densities per row instead of 801, which
  keeps a fit on 18000 rows to seconds. ``nu = inf`` uses the closed form.

Partial pooling (a documented simplification of a crossed random-effects fit). With ``g`` the global
fit over all admitted rows and ``w = n / (n + kappa)``, ``kappa = 20``:

* kind level: ``K_c = shrink(cell fit, g, n_c)``;
* period level: ``P_p = shrink(period fit over all cells, g, n_p)``;
* a period with fewer than 30 admitted rows carries no period information (its deviation is zero), and the
  "most recent period" used for an unseen period is the latest one with at least 30 rows;
* cell and period: ``K_c + (P_p - g) / 2`` for ``mu`` and ``log sd``, which is the mean of the kind value
  and the period value moved onto this cell. The scale is pooled as the standard deviation of the t
  prior, ``tau sqrt(nu / (nu - 2))``, so fits with different ``nu`` are comparable; period fits use the
  global ``nu`` only, because a tail shape cannot be estimated from one quarter. Averaging the raw kind and period values would pull a thin
  cell toward the mixture of all cells, so the period part enters as a deviation from the global fit.

An unseen period (the quarter being predicted never has history) uses the most recent visible
period's parameters. A cell never seen at fit time uses the global fit. ``nu`` is the cell's own when
its weight is at least one half, otherwise the global ``nu``.

Origin semantics: ``fit(rows)`` uses exactly the rows passed in (the harness passes rows with status
admitted and ``usable_after <= origin``); non-admitted rows are ignored.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize, special, stats

from mootcourt.config import KAPPA, NU_GRID
from mootcourt.ledger import ADMITTED, quarter_of
from mootcourt.predictors.base import Predictive, build_grid

_LOG_U_STEP = 0.25
_LOG_U = np.arange(-18.0, 4.5 + _LOG_U_STEP / 2, _LOG_U_STEP)
_MIN_FIT_ROWS = 3
MIN_PERIOD_ROWS = 30  # periods with fewer admitted rows carry no period information
_TAU_FLOOR_FRAC = 0.05
_LOG_2PI = math.log(2.0 * math.pi)


def shrink(value: float, target: float, n_c: float, kappa: float = KAPPA) -> float:
    """``target + (value - target) * n_c / (n_c + kappa)``: weight ``n_c / (n_c + kappa)`` on ``value``."""
    if n_c < 0 or kappa < 0:
        raise ValueError("n_c and kappa must be nonnegative")
    if n_c + kappa == 0:
        return target
    w = n_c / (n_c + kappa)
    return target + (value - target) * w


# ------------------------------------------------------------------ likelihood
def _loglik_normal(y: np.ndarray, s: np.ndarray, mu: float, tau: float) -> float:
    var = tau * tau + s * s
    return float(-0.5 * np.sum(np.log(2.0 * np.pi * var) + (y - mu) ** 2 / var))


def _loglik_fast(y: np.ndarray, s: np.ndarray, mu: float, tau: float, nu: float) -> float:
    """Marginal log likelihood by the scale-mixture representation (see module docstring)."""
    if math.isinf(nu):
        return _loglik_normal(y, s, mu, tau)
    a = nu / 2.0
    g = np.exp(_LOG_U)
    logw = a * math.log(a) + a * _LOG_U - a * g - special.gammaln(a) + math.log(_LOG_U_STEP)
    var = (tau * tau) / g[None, :] + (s * s)[:, None]
    logd = -0.5 * ((y - mu) ** 2)[:, None] / var - 0.5 * (np.log(var) + _LOG_2PI) + logw[None, :]
    return float(special.logsumexp(logd, axis=1).sum())


def _mixture_nodes(nu: float) -> tuple[np.ndarray, np.ndarray]:
    """Nodes ``g`` and weights of the scale-mixture integral ``t(nu) = integral Normal(0, 1 / g) Gamma(g; nu/2, nu/2) dg``.

    The same trapezoid over ``log g`` as the likelihood uses; the weights sum to one. ``nu`` must be finite.
    """
    a = nu / 2.0
    g = np.exp(_LOG_U)
    logw = a * math.log(a) + a * _LOG_U - a * g - special.gammaln(a) + math.log(_LOG_U_STEP)
    w = np.exp(logw - logw.max())
    return g, w / w.sum()


def marginal_logpdf_rows(y, s2, loc, scale, nu: float) -> np.ndarray:
    """Per-row log density of ``y`` when ``theta ~ t(loc, scale, nu)`` and ``y | theta ~ Normal(theta, s2)``.

    ``y``, ``s2``, ``loc`` and ``scale`` are arrays of one shape (or broadcastable), in the units of y; ``nu`` is a
    scalar and infinite gives the closed Normal. The t is integrated as a scale mixture of normals (about 90 nodes), so
    the same call scores a P1 prediction and a P2 prediction of the same family and the selection of lambda compares
    like with like.
    """
    y, s2, loc, scale = np.broadcast_arrays(*(np.asarray(v, dtype=np.float64) for v in (y, s2, loc, scale)))
    if math.isinf(nu):
        var = scale * scale + s2
        return -0.5 * (np.log(2.0 * np.pi * var) + (y - loc) ** 2 / var)
    g, w = _mixture_nodes(nu)
    var = (scale * scale)[..., None] / g + s2[..., None]
    logd = -0.5 * ((y - loc) ** 2)[..., None] / var - 0.5 * (np.log(var) + _LOG_2PI) + np.log(np.maximum(w, 1e-300))
    return special.logsumexp(logd, axis=-1)


def p_sig_t(loc, v, nu: float, s_star, z: float = 1.96):
    """P(y* > z s*) when ``theta ~ t(loc, scale, nu)`` with theta variance ``v`` (moment matched) and ``y* = theta + Normal(0, s*^2)``.

    ``loc`` and ``v`` may be arrays; ``s_star`` is a scalar in the units of y. The scale is ``sqrt(v (nu - 2) / nu)``;
    an infinite ``nu`` gives the closed Normal form. Agrees with the grid computation of ``Predictive.p_sig`` to about 1e-3.
    """
    loc, v = np.asarray(loc, dtype=np.float64), np.asarray(v, dtype=np.float64)
    if math.isinf(nu):
        return special.ndtr((loc - z * s_star) / np.sqrt(v + s_star * s_star))
    scale2 = v * (nu - 2.0) / nu
    g, w = _mixture_nodes(nu)
    sd = np.sqrt(scale2[..., None] / g + s_star * s_star)
    return (special.ndtr((loc[..., None] - z * s_star) / sd) * w).sum(axis=-1)


def marginal_loglik(y, s, mu: float, tau: float, nu: float, n_grid: int | None = None) -> float:
    """``sum_i log integral Normal(y_i | theta, s_i^2) t(theta | mu, tau, nu) d theta`` on a theta grid.

    ``y``, ``s``, ``mu`` and ``tau`` share units. The grid covers ``mu +/- 12 tau`` (``+/- 8 tau`` is
    too narrow for nu = 3) and is widened to reach every observation by 8 of its standard errors, with
    spacing at most half the smallest ``s``, between 801 and 20001 points.
    """
    y = np.asarray(y, dtype=np.float64)
    s = np.asarray(s, dtype=np.float64)
    span = 12.0 * tau
    lo = min(mu - span, float((y - 8.0 * s).min()))
    hi = max(mu + span, float((y + 8.0 * s).max()))
    if n_grid is None:
        n_grid = int(np.clip(math.ceil((hi - lo) / (0.5 * float(s.min()))), 801, 20001))
    th = np.linspace(lo, hi, n_grid)
    dx = th[1] - th[0]
    edges = np.concatenate([th - dx / 2.0, [th[-1] + dx / 2.0]])
    u = (edges - mu) / tau
    if math.isinf(nu):
        cdf, sf = special.ndtr(u), special.ndtr(-u)
    else:
        cdf, sf = stats.t.cdf(u, df=nu), stats.t.sf(u, df=nu)
    # upper tail through the survival function so far-out cells keep their (tiny) mass instead of cancelling to 0
    prior = np.where(u[:-1] >= 0.0, sf[:-1] - sf[1:], cdf[1:] - cdf[:-1])
    total = 0.0
    for a in range(0, len(y), 1024):
        z = (y[a:a + 1024, None] - th[None, :]) / s[a:a + 1024, None]
        like = np.exp(-0.5 * z * z) / (s[a:a + 1024, None] * math.sqrt(2.0 * math.pi))
        total += float(np.log(like @ prior).sum())
    return total


# ------------------------------------------------------------------------ fit
def fit_cell(y, s, nu_grid=NU_GRID) -> dict:
    """Maximum marginal likelihood ``(mu, tau, nu)`` for one set of rows.

    Returns ``{"mu", "tau", "nu", "loglik", "n"}`` (units of y). With fewer than 3 rows there is
    nothing to optimize, so the moment estimate is returned with ``nu = inf``.
    """
    y = np.asarray(y, dtype=np.float64)
    s = np.asarray(s, dtype=np.float64)
    n = len(y)
    if n == 0:
        raise ValueError("cannot fit a cell with no rows")
    mu0 = float(np.average(y, weights=1.0 / (s * s)))
    var_y = float(np.var(y)) if n > 1 else float(s.mean() ** 2)
    floor = _TAU_FLOOR_FRAC * math.sqrt(max(var_y, 1e-12))
    tau0 = math.sqrt(max(var_y - float(np.mean(s * s)), (0.1 ** 2) * max(var_y, 1e-12)))
    tau0 = max(tau0, floor)
    if n < _MIN_FIT_ROWS:
        return {"mu": mu0, "tau": tau0, "nu": math.inf, "loglik": _loglik_normal(y, s, mu0, tau0), "n": n}
    lo, hi = math.log(floor), math.log(max(10.0 * math.sqrt(var_y), 10.0 * floor))

    def optimise(nu: float, start: tuple[float, float]) -> tuple[float, float, float]:
        def nll(p):
            lt = min(max(p[1], lo), hi)
            return -_loglik_fast(y, s, p[0], math.exp(lt), nu) + 1e-6 * (p[1] - lt) ** 2

        res = optimize.minimize(nll, [start[0], math.log(start[1])], method="Nelder-Mead",
                                options={"xatol": 1e-4, "fatol": 1e-7, "maxiter": 400})
        lt = min(max(res.x[1], lo), hi)
        return float(res.x[0]), math.exp(lt), -float(res.fun)

    best = None
    start_normal = (mu0, tau0)
    for nu in sorted(nu_grid, key=lambda v: (math.isinf(v), v), reverse=True):
        start = start_normal
        if not math.isinf(nu) and best is not None and math.isinf(best["nu"]):
            start = (best["mu"], max(best["tau"] * math.sqrt(max(nu - 2.0, 1.0) / nu), floor))
        mu, tau, ll = optimise(nu, start)
        cand = {"mu": mu, "tau": tau, "nu": nu, "loglik": ll, "n": n}
        if best is None or ll > best["loglik"] + 1e-9:
            best = cand
        if math.isinf(nu):
            start_normal = (mu, tau)
    return best


def sd_equivalent(tau: float, nu: float) -> float:
    """Standard deviation of t(0, tau, nu) for nu > 2; ``tau`` for nu = inf. Comparable across nu."""
    return tau if math.isinf(nu) else tau * math.sqrt(nu / (nu - 2.0))


def scale_from_sd(sd: float, nu: float) -> float:
    """Inverse of ``sd_equivalent``."""
    return sd if math.isinf(nu) else sd * math.sqrt((nu - 2.0) / nu)


def _as_nu(v: float) -> float:
    return math.inf if v is None else float(v)


class P1Predictor:
    """Empirical-Bayes prior predictor with partial pooling on the kind and period dimensions."""

    def __init__(self, kappa: float = KAPPA, nu_grid=NU_GRID):
        self.kappa = kappa
        self.nu_grid = tuple(nu_grid)
        self._global: dict | None = None
        self._kind: dict[str, dict] = {}
        self._period: dict[str, dict] = {}
        self._ranges: dict[str, tuple[float, float]] = {}
        self._yrange_global: tuple[float, float] = (0.0, 0.0)
        self._rows: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._cache: dict[tuple[str, str], dict] = {}

    # ----------------------------------------------------------------- fitting
    def fit(self, rows: pd.DataFrame) -> P1Predictor:
        """Fit the global, per-cell and per-period parameters on the admitted rows passed in."""
        adm = rows.loc[rows["status"] == ADMITTED]
        if len(adm) == 0:
            raise ValueError("P1 needs at least one admitted row")
        y_all, s_all = adm["y"].to_numpy(float), adm["s"].to_numpy(float)
        self._global = fit_cell(y_all, s_all, self.nu_grid)
        self._yrange_global = (float(y_all.min()), float(y_all.max()))
        self._kind, self._period, self._ranges, self._rows, self._cache = {}, {}, {}, {}, {}
        for c, g in adm.groupby("cell"):
            y, s = g["y"].to_numpy(float), g["s"].to_numpy(float)
            self._rows[c] = (y, s)
            self._ranges[c] = (float(y.min()), float(y.max()))
            self._kind[c] = fit_cell(y, s, self.nu_grid)
        nu_g = (self._global["nu"],)
        for p, g in adm.groupby("period"):
            self._period[p] = fit_cell(g["y"].to_numpy(float), g["s"].to_numpy(float), nu_g)
        return self

    def global_params(self) -> dict:
        """Global fit over all admitted rows: ``{"mu", "tau", "nu", "n"}``."""
        return _public(self._global)

    def fit_cell_params(self, cell: str) -> dict:
        """The UNPOOLED fit of one cell (all periods), used to check parameter recovery."""
        if cell not in self._kind:
            raise KeyError(f"no admitted rows for cell {cell!r}")
        return _public(self._kind[cell])

    def y_range(self, cell: str) -> tuple[float, float]:
        """Observed range of y among the cell's fit rows (global range for an unseen cell)."""
        return self._ranges.get(cell, self._yrange_global)

    def last_period(self) -> str:
        """The most recent period with at least ``MIN_PERIOD_ROWS`` admitted rows (else the most recent one)."""
        solid = [p for p, v in self._period.items() if v["n"] >= MIN_PERIOD_ROWS]
        return max(solid) if solid else max(self._period)

    def cell_params(self, cell: str, period: str) -> dict:
        """Pooled parameters ``{"mu", "tau", "nu", "n_cell", "n_period"}`` for a cell in a period.

        A period with no rows uses the most recent visible period; a cell with no rows uses the global fit.
        """
        key = (cell, period)
        if key in self._cache:
            return dict(self._cache[key])
        g = self._global
        if cell not in self._kind:
            out = {"mu": float(g["mu"]), "tau": float(g["tau"]), "nu": _as_nu(g["nu"]), "n_cell": 0, "n_period": 0}
        else:
            per = period if period in self._period else self.last_period()
            kc, pp = self._kind[cell], self._period[per]
            n_c, n_p = kc["n"], pp["n"]
            if n_p < MIN_PERIOD_ROWS:
                pp, n_p = g, 0
            g_lsd = math.log(sd_equivalent(g["tau"], g["nu"]))
            k_mu = shrink(kc["mu"], g["mu"], n_c, self.kappa)
            k_lsd = shrink(math.log(sd_equivalent(kc["tau"], kc["nu"])), g_lsd, n_c, self.kappa)
            p_mu = shrink(pp["mu"], g["mu"], n_p, self.kappa)
            p_lsd = shrink(math.log(sd_equivalent(pp["tau"], pp["nu"])), g_lsd, n_p, self.kappa)
            mu = k_mu + 0.5 * (p_mu - g["mu"])
            lsd = k_lsd + 0.5 * (p_lsd - g_lsd)
            nu = kc["nu"] if n_c / (n_c + self.kappa) >= 0.5 else g["nu"]
            tau = scale_from_sd(math.exp(lsd), nu)
            out = {"mu": float(mu), "tau": float(tau), "nu": _as_nu(nu), "n_cell": int(n_c), "n_period": int(n_p)}
        self._cache[key] = out
        return dict(out)

    # --------------------------------------------------------------- predicting
    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:
        """Prior predictive for theta: the pooled t prior of the cell in the origin's quarter, on a grid.

        ``s_star`` (units of y) does not change the theta prior; it enters when the Predictive is
        scored or converted to p_sig. The grid covers the cell's observed y range.
        """
        par = self.cell_params(cell, quarter_of(origin))
        lo, hi = self._ranges.get(cell, self._yrange_global)
        grid = build_grid(par["mu"], par["tau"], y_min=lo, y_max=hi)
        return Predictive.from_t(grid, par["mu"], par["tau"], par["nu"])

    # ----------------------------------------------------------------- state
    def to_state(self) -> dict:
        """Plain-dict state (JSON-safe: infinite nu becomes None)."""
        def enc(d):
            return {k: (None if (k == "nu" and math.isinf(v)) else v) for k, v in d.items()}

        return {
            "kappa": self.kappa,
            "global": enc(self._global),
            "kind": {c: enc(v) for c, v in self._kind.items()},
            "period": {p: enc(v) for p, v in self._period.items()},
            "ranges": {c: list(v) for c, v in self._ranges.items()},
            "yrange_global": list(self._yrange_global),
        }

    @classmethod
    def from_state(cls, state: dict) -> P1Predictor:
        """Inverse of ``to_state``."""
        def dec(d):
            return {k: (math.inf if (k == "nu" and v is None) else v) for k, v in d.items()}

        p = cls(kappa=state["kappa"])
        p._global = dec(state["global"])
        p._kind = {c: dec(v) for c, v in state["kind"].items()}
        p._period = {k: dec(v) for k, v in state["period"].items()}
        p._ranges = {c: (v[0], v[1]) for c, v in state["ranges"].items()}
        p._yrange_global = (state["yrange_global"][0], state["yrange_global"][1])
        return p


def _public(d: dict) -> dict:
    return {"mu": float(d["mu"]), "tau": float(d["tau"]), "nu": _as_nu(d["nu"]), "n": int(d["n"])}
