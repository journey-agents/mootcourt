#!/usr/bin/env python3
"""A reference forecast that reads no history, scored on the saved rows of one backtest (plan of 12 November 2026, Part D).

The reference knows each row's planned standard error ``s_star`` and nothing else, and assumes no effect: its density for the observed
estimate is Normal(0, s_star^2). The script reads the per-row scores a backtest saved and writes the reference's mean log score and, for P0
and P1, the paired difference ``logscore(rung) - logscore(reference)`` on the rows the rung scored (nats per row): pooled with an interval
by test, and at each origin. No model is run. The reference is a floor: it denies that tests differ.

Use: ``python scripts/no_history_reference.py --scores SCORES.parquet --report BACKTEST.json --out OUT.json``
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

_SD_FLOOR = 1e-6


def reference_logscore(y, s_star) -> np.ndarray:
    """Log density of ``y`` under Normal(0, s_star^2), in nats."""
    return stats.norm.logpdf(np.asarray(y, dtype=np.float64), 0.0, np.maximum(np.asarray(s_star, dtype=np.float64), _SD_FLOOR))


def summarize(scores: pd.DataFrame, B: int, seed: int, level: float = 0.9, rungs=("P0", "P1")) -> dict:
    """The reference's log score and each rung's paired difference from it. Raises ValueError when a rung has no rows."""
    out: dict = {}
    for rung in rungs:
        sub = scores[scores["rung"] == rung]
        if len(sub) == 0:
            raise ValueError(f"no rows for rung {rung}")
        ref = reference_logscore(sub["y"], sub["s_star"])
        d = pd.DataFrame({"test_id": sub["test_id"].to_numpy(), "origin": pd.to_datetime(sub["origin"], utc=True).to_numpy(),
                          "d": sub["logscore"].to_numpy(float) - ref})

        def one(frame: pd.DataFrame) -> dict:
            iv = hs.bootstrap_by_test(frame, "d", B=B, seed=seed, level=level)
            return {"difference": float(iv.estimate), "lo": float(iv.lo), "hi": float(iv.hi), "n_rows": int(len(frame)),
                    "n_tests": int(frame["test_id"].nunique())}

        by_origin = [{"origin": pd.Timestamp(o).isoformat(), **one(g)} for o, g in d.groupby("origin", sort=True)]
        out[rung] = {"logscore": float(sub["logscore"].mean()), "reference_logscore": float(ref.mean()), "minus_reference": one(d),
                     "by_origin": by_origin, "by_origin_above_zero": int(sum(1 for r in by_origin if r["lo"] > 0))}
    return {**out, "bootstrap_resamples": int(B), "seed": int(seed), "level": level,
            "reference": "Normal(0, s_star^2): the planned standard error of the row and no effect; it reads no ledger",
            "unit": "nats per row of log score, rung minus reference; intervals resample tests and hold the origins fixed"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scores", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    header = json.loads(args.report.read_text(encoding="utf-8"))["header"]
    sc = pd.read_parquet(args.scores, columns=["row_id", "test_id", "origin", "rung", "logscore", "y", "s_star"])
    doc = summarize(sc, int(header["bootstrap_resamples"]), int(header["seed"]))
    doc["inputs"] = {"scores": args.scores.name, "report": args.report.name}
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
