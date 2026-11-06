#!/usr/bin/env python3
"""Simulate the release gates at each stratum's OWN dependence and write ``<reports>/gates-by-stratum-<source>-<snapshot>.json`` (X7 of the paper v2 plan).

The gates of ``moot simulate gate-power`` are sized at three simulated base rates with the rows per test and the within-test correlation measured on one
archive each, and the report reads a cell's gate at the nearest base rate, scaled to first order for the cell's own dependence (docs/method.md call 205). Here
every stratum of the main run (each cell and the pooled rows) gets its own simulation: the base rate of the significant-positive event, the rows per test and
the binary within-test correlation measured on the stratum's rows of rung P1 in the main score table, then ``simulate._entry`` as ``write_gates`` calls it
(by-test bootstrap, 90 percent interval, both power targets, the two skills). The default settings of the gate-power stage are used (1,000 replicates, 500
resamples, its seed), so the pooled stratum can be read against ``gates.json``.

Use: ``python scripts/gates_by_stratum.py --source upworthy [--reps N] [--bootstrap B] [--grid-max N]``. Synthetic data only; the output says so.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

from mootcourt import simulate
from mootcourt.extras_v2 import stratum_dependence
from mootcourt.ledger import ensure_snapshot, read_ledger
from mootcourt.storage import storage_paths

NOT_REACHED = 10**9


def compute(
    scores: pd.DataFrame,
    *,
    reps: int,
    B: int,
    seed: int,
    grid=None,
    rung: str = "P1",
    target: float = simulate.DEFAULT_TARGET,
    level: float = simulate.DEFAULT_LEVEL,
    verbose: bool = False,
) -> dict:
    g = scores[scores["rung"] == rung]
    strata = {}
    t0 = time.monotonic()
    for cell in ["ALL"] + sorted(g["cell"].unique()):
        sub = g if cell == "ALL" else g[g["cell"] == cell]
        if sub["event"].nunique() < 2:
            continue
        dep = stratum_dependence(sub)
        rpt = dep["rows_per_test"] if dep["rows_per_test"] > 1.0 else 1.0
        try:
            e = simulate._entry(
                dep["base_rate"],
                target,
                reps,
                B,
                seed,
                grid,
                False,
                time.monotonic() + 36000.0,
                rpt,
                level,
                dep["icc"],
                progress=(lambda line: print(f"{cell}: {line}", flush=True)) if verbose else None,
                t0=t0,
            )
            e = {
                "n_200": int(e["n_200"]),
                "n_400": int(e["n_400"]),
                "by_target": {k: {kk: int(vv) for kk, vv in v.items()} for k, v in e["by_target"].items()},
                "latent_rho": float(e["latent_rho"]),
                "reached": True,
            }
        except ValueError as exc:  # no n on the grid reaches the target power: the gate is beyond the grid
            e = {
                "n_200": NOT_REACHED,
                "n_400": NOT_REACHED,
                "by_target": {f"{t:.2f}": {"n_200": NOT_REACHED, "n_400": NOT_REACHED} for t in sorted({simulate.RESEARCH_TARGET, float(target)})},
                "reached": False,
                "reason": str(exc),
            }
        strata[cell] = {**e, "dependence": dep}
    return {
        "label": simulate.SYNTHETIC_LABEL,
        "rung": rung,
        "reps": reps,
        "bootstrap": B,
        "seed": seed,
        "decision_target": float(target),
        "research_target": simulate.RESEARCH_TARGET,
        "skills": dict(simulate.GATE_SKILLS),
        "interval": {"level": float(level), "by": "test"},
        "strata": strata,
        "note": "each stratum's sizes are simulated at the base rate, rows per test and within-test correlation measured on its own P1 rows in the main score "
        "table; sizes are numbers of tests; 1000000000 means no size on the grid reached the power",
    }


def main() -> int:
    paths = storage_paths()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", required=True)
    ap.add_argument("--ledger", default=str(paths.ledger_path))
    ap.add_argument("--reports-dir", default=str(paths.reports))
    ap.add_argument("--reps", type=int, default=simulate.DEFAULT_REPS)
    ap.add_argument("--bootstrap", type=int, default=simulate.DEFAULT_BOOTSTRAP)
    ap.add_argument("--seed", type=int, default=simulate.DEFAULT_SEED)
    ap.add_argument("--grid-max", type=int, default=0, help="largest n of the grid; 0 keeps the default grid (up to 3200 tests)")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    ledger_path = Path(a.ledger)
    df = read_ledger(ledger_path)
    df = df[df["source"] == a.source].reset_index(drop=True)
    sid = ensure_snapshot(df, ledger_path.parent)
    sc_path = Path(a.reports_dir) / f"scores-{a.source}-{sid}.parquet"
    if not sc_path.is_file():
        print(f"no score table {sc_path}; run the main backtest first", file=sys.stderr)
        return 1
    grid = [n for n in simulate.DEFAULT_GRID if n <= a.grid_max] if a.grid_max else None
    t0 = time.perf_counter()
    doc = compute(pd.read_parquet(sc_path), reps=a.reps, B=a.bootstrap, seed=a.seed, grid=grid, verbose=a.verbose)
    doc["source"], doc["snapshot_id"], doc["seconds"] = a.source, sid, round(time.perf_counter() - t0, 1)
    out = Path(a.reports_dir) / f"gates-by-stratum-{a.source}-{sid}.json"
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out} in {doc['seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
