#!/usr/bin/env python3
"""The split-half fit of a ledger with degrees of freedom and a standard deviation (docs/superpowers/plans/2026-11-13-reviewer-runs.md, Part F).

A backtest report holds, per cell, the prior's unpooled fit on the odd and on the even tests: a mean and a Student-t scale. The scale of a
Student-t is not a standard deviation, so it cannot be set beside the generator's normal standard deviation. This script refits the two
halves exactly as the report did (``harness_stats.split_half`` at the report's last origin) and writes, beside the report's keys, the
fitted degrees of freedom ``nu_*`` and the standard deviation ``sd_* = tau sqrt(nu / (nu - 2))`` of each half.

``matches_report`` is true when the refit reproduces the report's means and scales in every cell; the script exits with status 1 when it
does not, so a table never mixes a report with a different ledger. An infinite ``nu`` (a normal fit) is written as the word "inf".

Use: ``python scripts/split_half_spread.py --ledger LEDGER.parquet --report BACKTEST.json --out OUT.json``
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

from mootcourt import harness_stats as hs

TOL = 1e-9


def sd_or_none(tau: float, nu: float) -> float | None:
    """The standard deviation of a Student-t with scale ``tau`` and ``nu`` degrees of freedom; None when ``nu`` is 2 or less."""
    return hs._sd_of_fit({"tau": tau, "nu": nu})


def build(ledger: pd.DataFrame, report: dict) -> dict:
    """The split-half fit at the report's last origin with the added keys, checked against the report's own values."""
    origin = pd.Timestamp(report["header"]["last_origin"])
    fit = hs.split_half(ledger, origin)
    old = {r["cell"]: r for r in report["tables"]["split_half"]}
    same = set(fit) == set(old) and all(
        abs(float(fit[c][k]) - float(old[c][k])) <= TOL for c in fit if c in old for k in ("mu_odd", "mu_even", "tau_odd", "tau_even"))
    out = {}
    for cell, row in fit.items():
        out[cell] = {k: ("inf" if isinstance(v, float) and math.isinf(v) else v) for k, v in row.items()}
    return {"split_half": out, "matches_report": bool(same),
            "definition": "P1's unpooled fit on odd and on even tests at the report's last origin; nu is the fitted degrees of freedom "
                          "(the word inf for a normal fit) and sd the standard deviation tau sqrt(nu / (nu - 2))",
            "inputs": {"origin": origin.isoformat()}}


def main(argv=None) -> int:
    from mootcourt.ledger import read_ledger

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    doc = build(read_ledger(a.ledger), json.loads(a.report.read_text(encoding="utf-8")))
    doc["inputs"]["report"] = a.report.name
    a.out.write_text(json.dumps(doc, indent=1, allow_nan=False) + "\n")
    print(f"wrote {a.out}; matches the report: {doc['matches_report']}", file=sys.stderr)
    return 0 if doc["matches_report"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
