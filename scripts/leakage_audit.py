#!/usr/bin/env python3
"""Post-hoc leakage audit of a backtest score table against the ledger.

For every origin the fit set is rebuilt from the ledger as the admitted rows with ``usable_after <= origin``. The audit
asserts, per source and rung:

1. no scored row is in the fit set of its origin (a row is never both fit and scored);
2. no fit-set row has ``usable_after`` after the origin;
3. every scored row starts at or after its origin and before the next origin;
4. the ``usable_after`` stored in the score table equals the ledger's;
5. no ledger row carries a post-launch field (reference rate, clicks, realized standard error) among the top-level
   features, which are the only fields a feature may read (the nested ``post_launch`` block is not read);
6. for Upworthy and ASOS the ``s_star`` stored in the score table equals the pre-launch value recomputed from the
   planned exposures and the cell median rate of the rows visible at the origin, so no realized ``s`` reached it.

The harness also wraps the ``fit`` methods during the backtest and raises if a not-yet-usable row reaches them; this
script is the independent check on the result. Exit code 0 means zero violations. Usage:
``python scripts/leakage_audit.py --ledger data/ledger/ledger.parquet --scores reports/scores-upworthy-<snapshot>.parquet
--out reports/leakage-audit-upworthy.txt``
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from mootcourt import scale
from mootcourt.ledger import visible_rows


def audit(ledger: pd.DataFrame, scores: pd.DataFrame, source: str) -> tuple[list[str], int]:
    adm = ledger[(ledger["source"] == source) & (ledger["status"] == "admitted")].set_index("row_id")
    origins = sorted(scores["origin"].unique())
    nxt = dict(zip(origins, origins[1:] + [origins[-1] + pd.DateOffset(months=3)]))
    lines, violations = [], 0
    for rung in sorted(scores["rung"].unique()):
        sub = scores[scores["rung"] == rung]
        v_both = v_late = v_window = v_stamp = n_scored = 0
        for o in origins:
            scored = sub[sub["origin"] == o]
            fit = adm[adm["usable_after"] <= o]
            n_scored += len(scored)
            v_both += int(scored["row_id"].isin(fit.index).sum())
            v_late += int((fit["usable_after"] > o).sum())
            started = adm.loc[scored["row_id"], "started_at"]
            v_window += int(((started.to_numpy() < o) | (started.to_numpy() >= nxt[o])).sum())
            v_stamp += int((adm.loc[scored["row_id"], "usable_after"].to_numpy() != scored["usable_after"].to_numpy()).sum())
        v_scale = 0
        if "s_star" in sub.columns and source in ("upworthy", "asos"):
            full = ledger[ledger["source"] == source]
            for o in origins:
                scored = sub[sub["origin"] == o]
                if scored.empty:
                    continue
                rows = full.set_index("row_id").loc[scored["row_id"]].reset_index()
                expect = scale.s_star_rows(rows, visible_rows(full, o))
                v_scale += int((abs(expect - scored["s_star"].to_numpy(float)) > 1e-9 * (1 + abs(expect))).sum())
        violations += v_both + v_late + v_window + v_stamp + v_scale
        lines.append(f"{source} {rung}: origins {len(origins)}, scored rows {n_scored}; rows both fit and scored {v_both}; "
                     f"fit-set rows with usable_after > origin {v_late}; scored rows outside their origin window {v_window}; "
                     f"usable_after mismatches {v_stamp}; s_star not equal to the pre-launch value {v_scale}")
    bad = scale.audit_feature_fields(ledger.loc[ledger["source"] == source, "features_json"])
    lines.append(f"{source}: post-launch fields in features {len(bad)}" + (f" (for example {bad[0][1]})" if bad else ""))
    violations += len(bad)
    return lines, violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--scores", required=True, help="a scores-<source>-<snapshot>.parquet file")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    scores = pd.read_parquet(args.scores)
    ledger = pd.read_parquet(args.ledger)
    source = str(ledger.loc[ledger["row_id"] == scores["row_id"].iloc[0], "source"].iloc[0])
    lines, violations = audit(ledger, scores, source)
    text = "\n".join([f"Leakage audit of {Path(args.scores).name} against {Path(args.ledger).name}", *lines,
                      f"total violations: {violations}", "PASS" if violations == 0 else "FAIL"]) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
