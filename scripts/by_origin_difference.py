#!/usr/bin/env python3
"""The log score of P1 minus P0 by origin, from the saved scores of one backtest (docs/superpowers/plans/2026-11-12-base-rate-recency-and-origins.md).

The pooled interval of a backtest report resamples tests and holds the origins fixed. This script reads the per-row scores the backtest saved
and writes, for ``logscore(P1) - logscore(P0)`` on the rows both rungs scored (nats per row):

* ``pooled``: the mean and its interval by test, which reproduces the report's ``logscore_vs_p1`` of P0 with the sign turned;
* ``by_origin``: the mean at each origin with an interval that resamples the tests of that origin;
* ``leave_one_origin_out``: the pooled mean with each origin removed in turn, each with its interval by test;
* ``equal_origin_weight``: the mean of the origin means, each origin counting once, with an interval that resamples tests within each origin;
* ``origin_level``: the same mean with the origins as the units, a Student-t interval on the origin means (it treats them as exchangeable).

No model is run. The resample count and the seed are the report's. The intervals do not resample origins.

Use: ``python scripts/by_origin_difference.py --scores SCORES.parquet --report BACKTEST.json --out OUT.json``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from mootcourt import harness_stats as hs


def differences(scores: pd.DataFrame, a: str = "P1", b: str = "P0") -> pd.DataFrame:
    """Per row scored by both rungs: ``test_id``, ``origin`` and ``d``, the log score of ``a`` minus that of ``b``."""
    x, y = scores[scores["rung"] == a].set_index("row_id"), scores[scores["rung"] == b].set_index("row_id")
    common = x.index.intersection(y.index)
    return pd.DataFrame({"test_id": x.loc[common, "test_id"].to_numpy(), "origin": pd.to_datetime(x.loc[common, "origin"], utc=True).to_numpy(),
                         "d": x.loc[common, "logscore"].to_numpy(float) - y.loc[common, "logscore"].to_numpy(float)})


def summarize(d: pd.DataFrame, B: int, seed: int, level: float = 0.9) -> dict:
    """The four readings of the module docstring for a frame of ``differences``. Raises ValueError for an empty frame."""
    if len(d) == 0:
        raise ValueError("no row is scored by both rungs")

    def one(frame: pd.DataFrame) -> dict:
        iv = hs.bootstrap_by_test(frame, "d", B=B, seed=seed, level=level)
        return {"difference": float(iv.estimate), "lo": float(iv.lo), "hi": float(iv.hi), "n_rows": int(len(frame)),
                "n_tests": int(frame["test_id"].nunique())}

    groups = list(d.groupby("origin", sort=True))
    by_origin = [{"origin": pd.Timestamp(o).isoformat(), **one(g)} for o, g in groups]
    loo = [{"left_out": pd.Timestamp(o).isoformat(), **one(d.drop(index=g.index))} for o, g in groups] if len(groups) > 1 else []
    draws = []
    for i, (_, g) in enumerate(groups):          # tests are resampled within each origin, and each origin's mean counts once
        ts = hs._TestSums(g, {"d": g["d"].to_numpy(float)})
        counts = ts.resample_counts(B, np.random.default_rng(seed + i))
        den = counts @ ts.counts
        draws.append((counts @ ts.sums["d"]) / np.where(den > 0, den, np.nan))
    lo, hi = hs._percentile_interval(np.mean(np.vstack(draws), axis=0), level)
    means = np.array([r["difference"] for r in by_origin], dtype=float)
    half = float(stats.t.ppf(0.5 + level / 2.0, len(means) - 1) * means.std(ddof=1) / np.sqrt(len(means))) if len(means) > 1 else float("nan")
    return {
        "pooled": one(d),
        "by_origin": by_origin,
        "by_origin_above_zero": int(sum(1 for r in by_origin if r["lo"] > 0)),
        "by_origin_below_zero": int(sum(1 for r in by_origin if r["hi"] < 0)),
        "by_origin_estimate_above_zero": int(sum(1 for r in by_origin if r["difference"] > 0)),
        "leave_one_origin_out": loo,
        "leave_one_origin_out_above_zero": int(sum(1 for r in loo if r["lo"] > 0)),
        "equal_origin_weight": {"difference": float(np.mean([r["difference"] for r in by_origin])), "lo": lo, "hi": hi, "origins": len(by_origin)},
        "origin_level": {"difference": float(means.mean()), "lo": float(means.mean() - half), "hi": float(means.mean() + half),
                         "origins": len(means), "note": "Student-t interval on the origin means, the origins as exchangeable units"},
        "bootstrap_resamples": int(B), "seed": int(seed), "level": level,
        "unit": "nats per row of log score, P1 minus P0; intervals resample tests and hold the origins fixed",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scores", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    header = json.loads(args.report.read_text(encoding="utf-8"))["header"]
    sc = pd.read_parquet(args.scores, columns=["row_id", "test_id", "origin", "rung", "logscore"])
    doc = summarize(differences(sc), int(header["bootstrap_resamples"]), int(header["seed"]))
    doc["inputs"] = {"scores": args.scores.name, "report": args.report.name, "variant": header.get("variant", header.get("settings", {}))}
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
