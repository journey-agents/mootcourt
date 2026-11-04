"""A small deterministic sample ledger in the exchange format, used by ``moot init``, the quickstart and the tests.

It is synthetic: 120 experiments over three years, each reporting three metrics for one treatment against a control, with relative
effects drawn around a small per-metric mean. Nothing in it comes from a real experiment. ``examples/ledgers/sample.csv`` is exactly
``sample_exchange().to_csv(index=False)``, and a test keeps the two equal.

Base rate (round 01, R6 minor 6 and question 5). The share of rows whose result is significant and positive is set by ``base_rate``
(default ``SAMPLE_BASE_RATE``, 0.09, the headline archive's rate, so that the first report and the quick gates a newcomer reads are of
the size the paper argues from): each metric's mean effect is the value at which a result at the metric's typical standard error (the
median planned units, ``TYPICAL_UNITS``) is significant and positive with that probability, given the metric's spread
(``metric_mean``). With the spreads of ``METRICS`` that mean is slightly negative, as the average product change is. ``base_rate=None``
keeps the fixed means of ``METRICS`` (the earlier sample, whose rate was about 0.20); the draws are the same in either case, so only the
means move.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from mootcourt.config import Z

METRICS = {"checkout_conversion": (0.010, 0.030, 1.5), "pages_per_session": (0.000, 0.020, 1.0), "revenue_per_user": (0.005, 0.040, 3.0)}
N_EXPERIMENTS = 120
SAMPLE_BASE_RATE = 0.09   # the headline archive's significant-positive rate (round 01, R6)
TYPICAL_UNITS = 34000     # the median of the planned units drawn per experiment (8,000 to 60,000)


def metric_mean(metric: str, base_rate: float | None) -> float:
    """The mean relative effect of ``metric`` at which a result at its typical standard error is significant and positive with probability
    ``base_rate``, given the metric's spread; the fixed mean of ``METRICS`` when ``base_rate`` is None."""
    mu, tau, scale = METRICS[metric]
    if base_rate is None:
        return float(mu)
    if not 0.0 < base_rate < 1.0:
        raise ValueError("base_rate must be between 0 and 1, or None for the fixed means")
    se = scale * np.sqrt(2.0 / TYPICAL_UNITS)
    return float(Z * se - stats.norm.ppf(1.0 - base_rate) * np.sqrt(tau * tau + se * se))


def sample_exchange(seed: int = 7, n_experiments: int = N_EXPERIMENTS, base_rate: float | None = SAMPLE_BASE_RATE) -> pd.DataFrame:
    """Exchange-format rows of the sample ledger. Relative effects around ``metric_mean(metric, base_rate)``; the standard error is
    ``scale * sqrt(2 / units)`` per metric."""
    rng = np.random.default_rng(seed)
    means = {m: metric_mean(m, base_rate) for m in METRICS}
    start0 = pd.Timestamp("2023-01-09", tz="UTC")
    rows = []
    for e in range(n_experiments):
        start = start0 + pd.Timedelta(days=int(e * 9))
        end = start + pd.Timedelta(days=14)
        n = int(rng.integers(8000, 60000))
        for metric, (_mu, tau, scale) in METRICS.items():
            se = scale * np.sqrt(2.0 / n)
            theta = rng.normal(means[metric], tau)
            rows.append({
                "experiment_id": f"exp-{e + 1:03d}", "variant_id": "treatment", "baseline_id": "control", "metric_id": metric,
                "effect": round(float(theta + rng.normal(0.0, se)), 6), "se": round(float(se), 6), "n_baseline": n, "n_variant": n,
                "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "ended_at": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "effect_unit": "relative", "source_system": "sample_generator", "variance_method": "normal approximation, fixed horizon",
            })
    return pd.DataFrame(rows)
