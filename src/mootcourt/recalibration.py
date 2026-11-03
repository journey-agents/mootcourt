"""Recalibration of a challenger's significant-positive probability, fit on visible rows only (docs/method.md call 168).

A challenger such as the gradient-boosted regressor discriminates a little and is badly calibrated, and the ladder's rungs
fall back to the prior where they have nothing to say. To compare like with like, every challenger also gets a recalibrated
row: its ``p_sig`` goes through a monotone map fit on out-of-fold predictions of the rows visible at the origin against the
events those rows had (the realized event of a concluded test is history). Nothing from the origin's own scored rows reaches
the map. With no signal the Platt slope goes to zero and the map returns the visible base rate, which is the fallback.

Two maps are available. ``platt`` (the default) is a logistic regression of the event on the logit of the probability: two
parameters, stable when events are rare. ``isotonic`` is the monotone step map, more flexible and noisier at the small row
counts of the first origins. Units: probabilities are unitless.
"""
from __future__ import annotations

import numpy as np

_EPS = 1e-4
METHODS = ("platt", "isotonic")
MIN_EVENTS = 5          # with fewer events (or fewer non-events) the map is the visible base rate


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=np.float64), _EPS, 1.0 - _EPS)
    return np.log(p / (1.0 - p))


class Calibrator:
    """A monotone map from a raw probability to a recalibrated one, fit once on (probability, event) pairs."""

    def __init__(self, method: str = "platt"):
        if method not in METHODS:
            raise ValueError(f"method must be one of {METHODS}")
        self.method = method
        self.n_fit = 0
        self.base_rate = float("nan")
        self._model = None

    def fit(self, p, event) -> Calibrator:
        """Fit on out-of-fold probabilities ``p`` and the 0/1 events they were issued for; returns self."""
        p, e = np.asarray(p, dtype=np.float64), np.asarray(event, dtype=np.float64)
        keep = np.isfinite(p) & np.isfinite(e)
        p, e = p[keep], e[keep]
        if len(p) == 0:
            raise ValueError("cannot recalibrate without rows")
        self.n_fit, self.base_rate = int(len(p)), float(e.mean())
        pos = int(e.sum())
        if pos < MIN_EVENTS or len(e) - pos < MIN_EVENTS:
            self._model = None
            return self
        if self.method == "platt":
            from sklearn.linear_model import LogisticRegression

            self._model = LogisticRegression(C=10.0, max_iter=500).fit(_logit(p).reshape(-1, 1), e.astype(int))
        else:
            from sklearn.isotonic import IsotonicRegression

            self._model = IsotonicRegression(y_min=_EPS, y_max=1.0 - _EPS, out_of_bounds="clip").fit(p, e)
        return self

    def transform(self, p) -> np.ndarray:
        """The recalibrated probabilities; the visible base rate when the fit had too few events."""
        p = np.asarray(p, dtype=np.float64)
        if self._model is None:
            return np.full(p.shape, self.base_rate)
        if self.method == "platt":
            return self._model.predict_proba(_logit(p).reshape(-1, 1))[:, 1]
        return np.asarray(self._model.predict(p), dtype=np.float64)


def time_folds(n: int, n_folds: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Contiguous folds of ``n`` time-ordered rows as ``(train_index, test_index)`` pairs; empty folds are dropped."""
    edges = np.linspace(0, n, n_folds + 1).astype(int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b > a:
            out.append((np.r_[0:a, b:n], np.arange(a, b)))
    return out
