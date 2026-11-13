#!/usr/bin/env python3
"""How often the report's calibration procedure rejects forecasts that are calibrated (docs/superpowers/plans/2026-11-13-reviewer-runs.md, Part A).

The backtest report places a rung's expected calibration error in a null clustered by test. The within-test correlation of that null is
estimated from the same outcomes the procedure then tests, so its rejection rate under calibration is not known by construction. This script
measures it. For one rung and one stratum of a saved score table it keeps the real forecasts ``p`` and test identifiers, and repeats:

1. draw outcomes from ``p`` with a known latent within-test correlation ``rho_true`` (one shared normal per test plus one per row, the copula
   of ``harness_stats.ece_null``), so the forecasts are calibrated by construction;
2. run the report's procedure unchanged on those outcomes (``design_effect``, ``latent_rho_for_design_effect``, ``ece_percentile``);
3. record the percentile.

``rho_true`` takes three values: zero, the latent correlation the procedure gives on the real outcomes (``observed``), and twice that, capped
at 0.99 (``double``). Per row the output holds the share of repetitions with a percentile above 95 and above 99, each with a Wilson 95 percent
interval, and ``critical_95``, the 95th percentile of the recorded percentiles (the empirical critical value).

No model is run and no report is changed. The outcome draws use their own random stream; ``ece_null`` is called, never edited.

Use: ``python scripts/calibration_null_size.py --scores SCORES.parquet --out OUT.json [--reps 400] [--seed 20261113] [--jobs 4]``
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import special

from mootcourt import harness_stats as hs

RUNGS = ("P0", "P1", "P2")
STRATA = ("ALL", "headline_only", "image_only", "both")
TRUTHS = ("zero", "observed", "double")
BINNINGS = ("equal_width", "equal_mass")
WILSON_Z = 1.959963984540054


def draw_events(p, test_ids, rho: float, rng) -> np.ndarray:
    """Outcomes (0.0 or 1.0) with marginals ``p`` and latent within-test correlation ``rho`` (a one-factor Gaussian copula)."""
    p = np.asarray(p, float)
    if rho <= 0.0:
        return (rng.random(p.size) < p).astype(np.float64)
    codes, uniq = pd.factorize(pd.Series(np.asarray(test_ids)))
    z = np.sqrt(rho) * rng.standard_normal(len(uniq))[codes] + np.sqrt(1.0 - rho) * rng.standard_normal(p.size)
    return (z < special.ndtri(np.clip(p, 1e-12, 1.0 - 1e-12))).astype(np.float64)


def procedure_rho(p, event, test_ids, seed: int = 0) -> float:
    """The latent correlation the report's procedure estimates from these outcomes."""
    de = hs.design_effect(p, event, test_ids)
    return float(hs.latent_rho_for_design_effect(p, test_ids, de["design_effect"], seed=seed))


def procedure_percentile(p, event, test_ids, equal_mass: bool = False, seed: int = 0) -> float:
    """The report's clustered calibration percentile of these forecasts against these outcomes (``harness_stats`` aggregate, call 172)."""
    rho = procedure_rho(p, event, test_ids, seed)
    return float(hs.ece_percentile(p, event, draws=hs.NULL_DRAWS, seed=seed, test_ids=test_ids, icc=rho, equal_mass=equal_mass))


def wilson(k: int, n: int) -> tuple[float, float]:
    """The Wilson 95 percent interval of ``k`` successes in ``n`` trials."""
    if n <= 0:
        return (float("nan"), float("nan"))
    z2 = WILSON_Z**2
    ph = k / n
    mid = (ph + z2 / (2 * n)) / (1 + z2 / n)
    half = WILSON_Z * np.sqrt(ph * (1 - ph) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return (float(max(0.0, mid - half)), float(min(1.0, mid + half)))


def size_row(p, test_ids, rho_true: float, reps: int, seed: int, equal_mass: bool = False) -> dict:
    """The rejection shares of the procedure over ``reps`` outcome sets drawn from ``p`` at ``rho_true``."""
    p, test_ids = np.asarray(p, float), np.asarray(test_ids)
    rng = np.random.default_rng(seed)
    pct = np.array([procedure_percentile(p, draw_events(p, test_ids, rho_true, rng), test_ids, equal_mass=equal_mass) for _ in range(int(reps))])
    out = {"reps": int(reps), "rho_true": float(rho_true), "constant_forecast": bool(np.ptp(p) == 0.0),
           "critical_95": float(np.percentile(pct, 95)), "n_rows": int(p.size), "n_tests": int(pd.unique(test_ids).size)}
    for level in (95, 99):
        k = int((pct > level).sum())
        lo, hi = wilson(k, int(reps))
        out[f"reject_{level}"], out[f"reject_{level}_lo"], out[f"reject_{level}_hi"] = k / int(reps), lo, hi
    return out


def _stratum(scores: pd.DataFrame, rung: str, stratum: str):
    g = scores[scores["rung"] == rung]
    if stratum != "ALL":
        g = g[g["cell"] == stratum]
    fin = np.isfinite(g["p_sig"].to_numpy(float))
    return g["p_sig"].to_numpy(float)[fin], g["event"].to_numpy(float)[fin], g["test_id"].to_numpy()[fin]


def _one(args) -> dict:
    p, t, rho_true, reps, seed, equal_mass, head = args
    return {**head, **size_row(p, t, rho_true, reps, seed, equal_mass=equal_mass)}


def summarize(scores: pd.DataFrame, rungs=RUNGS, strata=STRATA, reps: int = 400, seed: int = 20261113, jobs: int = 1) -> dict:
    """One row per rung, stratum, binning and truth; a rung or stratum with fewer than two finite forecasts is left out."""
    items = []
    for rung in rungs:
        for stratum in strata:
            p, e, t = _stratum(scores, rung, stratum)
            if p.size < 2:
                continue
            rho_obs = procedure_rho(p, e, t)
            rho = {"zero": 0.0, "observed": rho_obs, "double": min(0.99, 2.0 * rho_obs)}
            for binning in BINNINGS:
                em = binning == "equal_mass"
                observed = procedure_percentile(p, e, t, equal_mass=em)
                for truth in TRUTHS:
                    head = {"rung": rung, "stratum": stratum, "binning": binning, "truth": truth, "rho_observed": float(rho_obs),
                            "observed_percentile": observed}
                    items.append((p, t, rho[truth], int(reps), [int(seed), len(items)], em, head))
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            rows = list(pool.map(_one, items))
    else:
        rows = [_one(it) for it in items]
    return {
        "definition": "outcomes drawn from the rung's own forecasts with latent within-test correlation rho_true; the report's procedure "
                      "(design effect, latent correlation, clustered ECE percentile) is run on each draw; reject_95 is the share of draws "
                      "with a percentile above 95",
        "inputs": {"rungs": list(rungs), "strata": list(strata), "reps": int(reps), "seed": int(seed), "null_draws": int(hs.NULL_DRAWS),
                   "procedure_seed": 0, "truths": {"zero": "rho_true 0", "observed": "the latent correlation the procedure gives on the real "
                                                   "outcomes", "double": "twice the observed value, capped at 0.99"}},
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scores", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--reps", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261113)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    doc = summarize(pd.read_parquet(a.scores), reps=a.reps, seed=a.seed, jobs=a.jobs)
    doc["inputs"]["scores"] = a.scores.name
    a.out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {a.out} ({len(doc['rows'])} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
