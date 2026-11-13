#!/usr/bin/env python3
"""The positive control read over several ledger seeds (docs/superpowers/plans/2026-11-13-reviewer-runs.md, Part B).

The paper sets one planted ledger (seed 7; 11,100 tests; a planted text lift of one percent) against the real archive. This script reads the
rolling backtest of that ledger and of the same ledger at other seeds, each through ``positive_control_rungs`` of ``scripts/paper_extras.py``
unchanged, and writes per seed:

* ``oracle_gain``: the log score per row of a model that is told the signal, minus P1's, pooled (nats);
* ``p2_gain``: P2 minus P1, pooled;
* ``recovered_pooled`` and ``recovered_headline_only``: P2's gain over the oracle's (None when the oracle's gain is not above zero);
* ``p2_minus_p1_headline_only``: P2 minus P1 in the headline-only cell;
* ``share_pairs_admitted``: the share of cell and origin pairs in which the guard admitted a weight.

Over the seeds it writes the median, the smallest and the largest of each, and ``inside_real_interval``: the number of seeds at which P2 minus
P1 in the headline-only cell falls inside the real archive's interval for that cell, read from the main backtest report. Five seeds are not a
distribution, and no interval over seeds is given.

Use: ``python scripts/positive_control_seeds.py --runs 7=DIR 8=DIR ... --main-report BACKTEST.json --out OUT.json``
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path

NUMERIC = ("oracle_gain", "p2_gain", "recovered_pooled", "recovered_headline_only", "p2_minus_p1_headline_only", "share_pairs_admitted")


def _p2(cell: dict) -> float:
    return float(next(r for r in cell["rungs"] if r["rung"] == "P2")["diff_logscore_vs_p1"])


def _share(gain: float, oracle: float) -> float | None:
    return float(gain / oracle) if oracle > 0 else None


def seed_record(run_doc: dict, seed: int) -> dict:
    """One seed's figures from one entry of ``positive_control_rungs(...)["runs"]``."""
    pooled, head = run_doc["by_cell"]["ALL"], run_doc["by_cell"]["headline_only"]
    oracle, oracle_head = float(pooled["oracle"]["gain_logscore_vs_p1"]), float(head["oracle"]["gain_logscore_vs_p1"])
    rec = {
        "seed": int(seed),
        "n_tests": run_doc.get("n_tests"),
        "oracle_gain": oracle,
        "p2_gain": _p2(pooled),
        "recovered_pooled": _share(_p2(pooled), oracle),
        "recovered_headline_only": _share(_p2(head), oracle_head),
        "p2_minus_p1_headline_only": _p2(head),
        "share_pairs_admitted": run_doc.get("share_pairs_admitted"),
    }
    if rec["recovered_pooled"] is None or rec["recovered_headline_only"] is None:
        rec["note"] = "the oracle's gain over P1 is not above zero, so a recovered share is not defined"
    return rec


def summarize(records: list[dict], real_lo: float, real_hi: float) -> dict:
    """The seeds side by side, with the median, smallest and largest of each figure (a seed without a value is left out of that figure)."""
    if not records:
        raise ValueError("no seed to summarize")
    stats = {"median": {}, "min": {}, "max": {}}
    for key in NUMERIC:
        vals = [float(r[key]) for r in records if r.get(key) is not None]
        for name, fn in (("median", statistics.median), ("min", min), ("max", max)):
            stats[name][key] = float(fn(vals)) if vals else None
    inside = sum(1 for r in records if real_lo <= r["p2_minus_p1_headline_only"] <= real_hi)
    return {"seeds": len(records), "by_seed": sorted(records, key=lambda r: r["seed"]), **stats, "inside_real_interval": int(inside),
            "real_interval": {"lo": float(real_lo), "hi": float(real_hi)}}


def real_interval(report: dict) -> tuple[float, float]:
    """The main report's unadjusted interval of P2 minus P1 on the log score in the headline-only cell."""
    row = next(r for r in report["tables"]["aggregate"] if r["cell"] == "headline_only" and r["rung"] == "P2")
    return float(row["logscore_vs_p1_lo"]), float(row["logscore_vs_p1_hi"])


def _paper_extras():
    path = Path(__file__).resolve().parent / "paper_extras.py"
    spec = importlib.util.spec_from_file_location("paper_extras", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("paper_extras", mod)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", required=True, nargs="+", help="SEED=DIR, one per seed; DIR holds one backtest of the planted ledger")
    ap.add_argument("--main-report", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--lift", type=float, default=1.0, help="the planted lift of the ledgers, in percent")
    a = ap.parse_args(argv)
    extras = _paper_extras()
    records = []
    for item in a.runs:
        seed, _, folder = item.partition("=")
        run = extras.positive_control_rungs([folder], strength=a.lift)["runs"][0]
        records.append({**seed_record(run, int(seed)), "report": run.get("report"), "snapshot_id": run.get("snapshot_id")})
        print(f"seed {seed} read", file=sys.stderr)
    lo, hi = real_interval(json.loads(a.main_report.read_text(encoding="utf-8")))
    doc = summarize(records, lo, hi)
    doc["inputs"] = {"planted_lift_percent": a.lift, "main_report": a.main_report.name,
                     "real_interval_key": "tables.aggregate[cell=headline_only,rung=P2] logscore_vs_p1_lo, logscore_vs_p1_hi"}
    a.out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {a.out} ({doc['seeds']} seeds)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
