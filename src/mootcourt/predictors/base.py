"""Predictive distributions on a theta grid, scoring primitives and the Predictor protocol.

A ``Predictive`` is a probability mass function over a uniform grid of ``theta`` values (801 points
spanning the fitted cell mean plus or minus 8 tau, widened to cover the observed range of y). Every
downstream quantity is computed from the grid only. Units: ``theta``, ``y``, ``y_star``, ``s`` (standard
error of the observed estimate), intervals and means are all in the same units, percentage points of
click-through rate for the Upworthy archive. Probabilities are unitless.

The distribution of the observed estimate is ``y* = theta + Normal(0, s^2)``.

* ``p_win(delta) = P(theta > delta)``.
* ``p_sig(s, z) = P(y* > z s)``, significant and positive.
* Log score is the exact mixture density ``log sum_j pmf_j Normal(y; theta_j, s^2)``.
* CRPS method. For a mixture of normals with weights ``pmf_j`` the CRPS at ``y`` is exactly
  ``sum_j pmf_j A(theta_j - y, s) - 0.5 sum_jk pmf_j pmf_k A(theta_j - theta_k, s sqrt(2))`` with
  ``A(m, sd) = m (2 Phi(m / sd) - 1) + 2 sd phi(m / sd)``. On a uniform grid the double sum depends only
  on the lag ``j - k``, so the weight autocorrelation is computed once per predictive (cached) and
  each row costs one O(G) pass. Rows are scored in chunks. No O(G^2) double sum is formed per row, and
  scoring 20000 rows takes seconds.

Origin semantics: a Predictor stands at an origin and may use only rows with status admitted and
``usable_after <= origin``; ``predict(x, s_star, cell, origin)`` returns a ``Predictive``.
"""
from __future__ import annotations

import math
from typing import Protocol

import numpy as np
from scipy import special, stats

from mootcourt.config import GRID_SPAN_TAU, THETA_GRID_N, Z

_CHUNK = 512
_SQRT2 = np.sqrt(2.0)
_SQRT2PI = np.sqrt(2.0 * np.pi)


def build_grid(
    mu: float,
    tau: float,
    y_min: float | None = None,
    y_max: float | None = None,
    n: int = THETA_GRID_N,
    span: float = GRID_SPAN_TAU,
) -> np.ndarray:
    """Uniform theta grid of ``n`` points over ``mu +/- span * tau``, widened to cover ``[y_min, y_max]``.

    ``mu`` and ``tau`` are in the units of y. Raises ValueError unless ``tau > 0``.
    """
    if not np.isfinite(mu) or not np.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be positive and finite")
    lo, hi = mu - span * tau, mu + span * tau
    if y_min is not None:
        lo = min(lo, float(y_min))
    if y_max is not None:
        hi = max(hi, float(y_max))
    return np.linspace(lo, hi, n)


def _a_fn(m: np.ndarray, sd) -> np.ndarray:
    """E|X| for X ~ Normal(m, sd^2): ``m (2 Phi(m/sd) - 1) + 2 sd phi(m/sd)``."""
    u = m / sd
    return m * (2.0 * special.ndtr(u) - 1.0) + 2.0 * sd * np.exp(-0.5 * u * u) / _SQRT2PI


def _check_s(s) -> np.ndarray:
    s = np.asarray(s, dtype=np.float64)
    if not np.all(np.isfinite(s)) or np.any(s <= 0):
        raise ValueError("s must be positive and finite (same units as y)")
    return s


class Predictive:
    """Probability mass function ``pmf`` over a uniform ``theta`` grid."""

    def __init__(self, theta: np.ndarray, pmf: np.ndarray, spec: dict | None = None):
        theta = np.asarray(theta, dtype=np.float64)
        pmf = np.asarray(pmf, dtype=np.float64)
        if theta.ndim != 1 or theta.shape != pmf.shape or len(theta) < 3:
            raise ValueError("theta and pmf must be 1-D arrays of equal length")
        if not np.all(np.isfinite(pmf)) or np.any(pmf < 0):
            raise ValueError("pmf must be finite and nonnegative")
        total = pmf.sum()
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"pmf must sum to 1, got {total}")
        self.theta = theta
        self.pmf = pmf / total
        self.dx = float(theta[1] - theta[0])
        self._cdf = np.cumsum(self.pmf)
        self._autocorr: np.ndarray | None = None
        self.spec = spec          # how this predictive was built (family, degrees of freedom, location, scale, grid), or None

    # ------------------------------------------------------------ builders
    @classmethod
    def from_normal(cls, theta: np.ndarray, mu: float, sd: float) -> Predictive:
        """Normal(mu, sd^2) placed on the grid by integrating over each bin; tails beyond it are renormalized."""
        return cls.from_family(theta, mu, sd, math.inf)

    @classmethod
    def from_t(cls, theta: np.ndarray, loc: float, scale: float, nu: float) -> Predictive:
        """Student-t(loc, scale, nu) placed on the grid by integrating over each bin; ``nu`` infinite is the Normal."""
        return cls.from_family(theta, loc, scale, nu)

    @classmethod
    def from_family(cls, theta: np.ndarray, loc: float, scale: float, nu: float) -> Predictive:
        """The one builder behind ``from_normal`` and ``from_t``: bin masses of a location-scale family, renormalized.

        ``spec`` records the family, the degrees of freedom, the location, the scale and the grid, which is everything
        ``from_spec`` needs to rebuild the same object (the card stores it so a later score is the backtest's score).
        """
        theta = np.asarray(theta, dtype=np.float64)
        dx = theta[1] - theta[0]
        edges = np.concatenate([theta - dx / 2.0, [theta[-1] + dx / 2.0]])
        u = (edges - loc) / max(scale, 1e-12)
        cdf = special.ndtr(u) if math.isinf(nu) else stats.t.cdf(u, df=nu)
        pmf = np.diff(cdf)
        total = pmf.sum()
        if total <= 0:  # loc far outside the grid: put all mass on the nearest point
            pmf = np.zeros_like(theta)
            pmf[int(np.argmin(np.abs(theta - loc)))] = 1.0
        else:
            pmf = pmf / total
        spec = {"family": "normal" if math.isinf(nu) else "student_t", "df": None if math.isinf(nu) else float(nu),
                "location": float(loc), "scale": float(scale), "grid_lo": float(theta[0]), "grid_hi": float(theta[-1]),
                "grid_n": int(len(theta))}
        return cls(theta, pmf, spec)

    @classmethod
    def from_spec(cls, spec: dict) -> Predictive:
        """Rebuild the predictive a ``spec`` describes (the inverse of the ``spec`` attribute), on the same grid."""
        nu = math.inf if spec.get("df") is None else float(spec["df"])
        theta = np.linspace(float(spec["grid_lo"]), float(spec["grid_hi"]), int(spec["grid_n"]))
        return cls.from_family(theta, float(spec["location"]), float(spec["scale"]), nu)

    # ------------------------------------------------------- theta moments
    def mean(self) -> float:
        """Mean of theta (point estimate, units of y)."""
        return float(self.theta @ self.pmf)

    def var(self) -> float:
        """Variance of theta (units of y squared)."""
        m = self.mean()
        return float(((self.theta - m) ** 2) @ self.pmf)

    def _edges_cdf(self) -> tuple[np.ndarray, np.ndarray]:
        edges = np.concatenate([self.theta - self.dx / 2.0, [self.theta[-1] + self.dx / 2.0]])
        return edges, np.concatenate([[0.0], self._cdf])

    def quantile(self, q: float) -> float:
        """Quantile of theta, treating each grid bin as uniform (units of y)."""
        edges, cdf = self._edges_cdf()
        return float(np.interp(q, cdf, edges))

    def prob_gt(self, delta: float) -> float:
        """P(theta > delta), with the bin containing delta split linearly."""
        edges, cdf = self._edges_cdf()
        return float(1.0 - np.interp(delta, edges, cdf))

    def p_win(self, delta: float = 0.0) -> float:
        """P(theta > delta); ``delta`` is in the units of y and defaults to 0."""
        return self.prob_gt(delta)

    # --------------------------------------------- observed-estimate view
    def p_sig(self, s_star, z: float = Z):
        """P(y* > z s_star): the chance the observed estimate is significant and positive.

        ``s_star`` is the standard error of the future estimate (units of y); scalar or array.
        """
        s = _check_s(s_star)
        out = special.ndtr(self.theta[None, :] / s.reshape(-1, 1) - z) @ self.pmf
        return float(out[0]) if s.ndim == 0 else out.reshape(s.shape)

    def _cdf_ystar(self, t: np.ndarray, s: float) -> np.ndarray:
        return special.ndtr((t[:, None] - self.theta[None, :]) / s) @ self.pmf

    def quantile_ystar(self, q: float, s_star: float) -> float:
        """Quantile of y* = theta + Normal(0, s_star^2), from the mixture cdf on a 2G-point grid."""
        s = float(_check_s(s_star))
        t = np.linspace(self.theta[0] - 7.0 * s, self.theta[-1] + 7.0 * s, 2 * len(self.theta))
        return float(np.interp(q, self._cdf_ystar(t, s), t))

    def interval(self, level: float, s_star: float | None = None) -> tuple[float, float]:
        """Central interval of the given level (for example 0.8 or 0.9), units of y.

        Without ``s_star`` it is the interval for theta; with ``s_star`` it is for the observed
        estimate y*.
        """
        a = (1.0 - level) / 2.0
        if s_star is None:
            return self.quantile(a), self.quantile(1.0 - a)
        return self.quantile_ystar(a, s_star), self.quantile_ystar(1.0 - a, s_star)

    # ------------------------------------------------------------- scoring
    def logscore(self, y, s_star):
        """Log of the exact mixture density of y* at ``y`` (higher is better; units: log per unit y)."""
        y = np.asarray(y, dtype=np.float64)
        s = _check_s(s_star)
        yb, sb = np.broadcast_arrays(y, s)
        out = np.empty(yb.size)
        yf, sf = yb.ravel(), sb.ravel()
        with np.errstate(divide="ignore"):
            logw = np.log(self.pmf)
        for a in range(0, len(yf), _CHUNK):
            sl = slice(a, a + _CHUNK)
            z = (yf[sl, None] - self.theta[None, :]) / sf[sl, None]
            comp = logw[None, :] - 0.5 * z * z - np.log(sf[sl, None] * _SQRT2PI)
            out[sl] = special.logsumexp(comp, axis=1)
        return float(out[0]) if yb.ndim == 0 else out.reshape(yb.shape)

    def _weight_autocorr(self) -> np.ndarray:
        """r[m] = sum_j pmf_j pmf_{j+m} for m = 0..G-1, cached."""
        if self._autocorr is None:
            full = np.correlate(self.pmf, self.pmf, mode="full")
            self._autocorr = full[len(self.pmf) - 1:]
        return self._autocorr

    def crps(self, y, s_star):
        """Continuous ranked probability score of y* at ``y`` (lower is better; units of y)."""
        y = np.asarray(y, dtype=np.float64)
        s = _check_s(s_star)
        yb, sb = np.broadcast_arrays(y, s)
        yf, sf = yb.ravel(), sb.ravel()
        out = np.empty(len(yf))
        r = self._weight_autocorr()
        lags = np.arange(len(r)) * self.dx
        for a in range(0, len(yf), _CHUNK):
            sl = slice(a, a + _CHUNK)
            sc = sf[sl, None]
            first = _a_fn(self.theta[None, :] - yf[sl, None], sc) @ self.pmf
            a_lag = _a_fn(lags[None, :], sc * _SQRT2)
            second = 0.5 * (r[0] * a_lag[:, 0] + 2.0 * (a_lag[:, 1:] @ r[1:]))
            out[sl] = first - second
        return float(out[0]) if yb.ndim == 0 else out.reshape(yb.shape)


class Predictor(Protocol):
    """A rung of the ladder. ``predict`` may use only rows visible at ``origin``."""

    def predict(self, x, s_star: float, cell: str, origin) -> Predictive:  # pragma: no cover - protocol
        """Predictive for the true effect theta of a contrast in ``cell`` standing at ``origin``."""
        ...
