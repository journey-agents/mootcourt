"""A small deterministic sample ledger in the exchange format, used by ``moot init``, the quickstart and the tests.

It is synthetic: 120 experiments over three years, each reporting three metrics for one treatment against a control, with relative
effects drawn around a small per-metric mean. Nothing in it comes from a real experiment. ``examples/ledgers/sample.csv`` is exactly
``sample_exchange().to_csv(index=False)``, and a test keeps the two equal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METRICS = {"checkout_conversion": (0.010, 0.030, 1.5), "pages_per_session": (0.000, 0.020, 1.0), "revenue_per_user": (0.005, 0.040, 3.0)}
N_EXPERIMENTS = 120


def sample_exchange(seed: int = 7, n_experiments: int = N_EXPERIMENTS) -> pd.DataFrame:
    """Exchange-format rows of the sample ledger. Relative effects; the standard error is ``scale / sqrt(units)`` per metric."""
    rng = np.random.default_rng(seed)
    start0 = pd.Timestamp("2023-01-09", tz="UTC")
    rows = []
    for e in range(n_experiments):
        start = start0 + pd.Timedelta(days=int(e * 9))
        end = start + pd.Timedelta(days=14)
        n = int(rng.integers(8000, 60000))
        for metric, (mu, tau, scale) in METRICS.items():
            se = scale * np.sqrt(2.0 / n)
            theta = rng.normal(mu, tau)
            rows.append({
                "experiment_id": f"exp-{e + 1:03d}", "variant_id": "treatment", "baseline_id": "control", "metric_id": metric,
                "effect": round(float(theta + rng.normal(0.0, se)), 6), "se": round(float(se), 6), "n_baseline": n, "n_variant": n,
                "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "ended_at": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "effect_unit": "relative", "source_system": "sample_generator", "variance_method": "normal approximation, fixed horizon",
            })
    return pd.DataFrame(rows)
