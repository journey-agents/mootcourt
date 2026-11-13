#!/usr/bin/env python3
"""The learning curve read at every origin (docs/superpowers/plans/2026-11-13-reviewer-runs.md, Part D).

``moot backtest --learning-curve ... --learning-curve-origin DATE`` writes one curve per origin. This script reads those documents and
writes one row per origin for one rung (P1 by default): the paired difference of the rung fitted on one quarter, and on one half, of the
history from the same rung fitted on all of it, on the same held-out rows, from the document's ``paired_vs_full``.

Sign convention, the document's: ``log_diff`` is the smaller history's log score minus the full history's (nats per row), so below zero
means the smaller history is worse; ``brier_diff`` is the full history's Brier score minus the smaller history's, so below zero again means
the smaller history is worse. A fraction whose subsamples could not be fitted at an origin has ``fitted: false`` and is counted under
``not_fitted``, on neither side.

``worse_at_quarter`` and ``worse_at_half`` count the origins at which the interval of ``log_diff`` lies wholly below zero.

Use: ``python scripts/learning_curve_origins.py --curves CURVE.json ... --out OUT.json [--rung P1]``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FRACTIONS = {"quarter": 0.25, "half": 0.5}


def origin_row(doc: dict, rung: str = "P1") -> dict:
    """One origin's row from one curve document."""
    row = {"origin": str(doc["final_origin"])[:10], "heldout_rows": doc.get("heldout_rows"), "heldout_tests": doc.get("heldout_tests"),
           "seeds": doc.get("seeds")}
    for name, fraction in FRACTIONS.items():
        got = next((r for r in doc.get("paired_vs_full", []) if r["rung"] == rung and abs(float(r["fraction"]) - fraction) < 1e-9), None)
        if got is None or got.get("logscore_minus_full") is None:
            row[name] = {"fitted": False}
            continue
        row[name] = {"fitted": True, "log_diff": got["logscore_minus_full"], "log_lo": got["logscore_lo"], "log_hi": got["logscore_hi"],
                     "brier_diff": got["brier_gain_over_full"], "brier_lo": got["brier_lo"], "brier_hi": got["brier_hi"],
                     "n_seeds": got.get("n_seeds")}
    return row


def _worse(cell: dict) -> bool:
    return bool(cell.get("fitted")) and cell["log_hi"] is not None and cell["log_hi"] < 0.0


def summarize(docs: list[dict], rung: str = "P1") -> dict:
    """The rows in origin order with the two counts; raises ValueError when an origin appears twice."""
    rows = sorted((origin_row(d, rung) for d in docs), key=lambda r: r["origin"])
    origins = [r["origin"] for r in rows]
    if len(set(origins)) != len(origins):
        raise ValueError(f"an origin appears more than once: {origins}")
    return {
        "rung": rung,
        "origins": len(rows),
        "worse_at_quarter": sum(_worse(r["quarter"]) for r in rows),
        "worse_at_half": sum(_worse(r["half"]) for r in rows),
        "not_fitted": sum(not r[name]["fitted"] for r in rows for name in FRACTIONS),
        "rows": rows,
        "definition": "log_diff: the log score of the rung fitted on the fraction of the history minus the same rung fitted on all of it, on "
                      "the same held-out rows (below zero: the smaller history is worse); worse_at_*: origins whose interval of log_diff "
                      "lies below zero",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--curves", required=True, nargs="+", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--rung", default="P1")
    a = ap.parse_args(argv)
    doc = summarize([json.loads(p.read_text(encoding="utf-8")) for p in a.curves], a.rung)
    doc["inputs"] = {"curves": [p.name for p in a.curves]}
    a.out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {a.out} ({doc['origins']} origins)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
