#!/usr/bin/env python3
"""Recompute the discrimination, planned-event and decision-value adjusted-bound columns of existing backtest reports from their stored score tables.

A report's ``tables.aggregate`` rows carry ``auc_*`` and ``resolution_*`` keys. When the definition of those columns changes (review N,
REV-N-001: the resolution is the Murphy term over equal-mass forecast bins, not the spread of the forecast) the reports can be brought up to
date without rerunning a backtest: this script reads each ``backtest-*.json`` and the ``scores-*.parquet`` beside it, recomputes the keys for
every (cell, rung) row with the report's own bootstrap settings (``header.bootstrap_resamples``, ``header.seed``), writes the JSON back and
regenerates the Markdown from it. Nothing else in a report changes; the AUC values are recomputed too and must equal the stored ones
(a mismatch aborts, which shows the score table is not the one the report was built from).

Run it on the data root, where the score tables live: a folder of copied report JSONs (the paper data) holds no score tables, so every report there is
skipped; skipped reports are counted in the closing line and make ``--check`` exit 1.

Use: ``python scripts/refresh_discrimination.py REPORTS_DIR [--check]`` (REPORTS_DIR holds ``backtest-*.json``; ``ablations/`` and
``positive-control/`` below it are visited too).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt import harness_stats as hs
from mootcourt.report import clean, render_markdown

KEYS = (
    "auc_event",
    "auc_event_lo",
    "auc_event_hi",
    "auc_direction",
    "auc_direction_lo",
    "auc_direction_hi",
    "resolution_event",
    "resolution_event_lo",
    "resolution_event_hi",
    "resolution_direction",
    "resolution_direction_lo",
    "resolution_direction_hi",
    *(f"{q}_{k}_within{s}" for q in ("auc", "resolution") for k in ("event", "direction") for s in ("", "_lo", "_hi")),
    "event_rate_planned",
    "p_sig_mean",
    "brier_planned",
    "brier_base_planned",
    "brier_skill_planned",
    "brier_skill_planned_lo",
    "brier_skill_planned_hi",
)


def group_values(g: pd.DataFrame, B: int, seed: int) -> dict:
    ts = hs._TestSums(g, {"a": np.zeros(len(g))})
    counts = ts.resample_counts(B, np.random.default_rng(seed))
    row: dict = {}
    hs._discrimination(row, g, ts, counts)
    hs._planned_event_sensitivity(row, g, ts, counts)
    return row


def _refresh_rows(json_path: Path, rows: list, scores: pd.DataFrame, B: int, seed: int) -> int:
    changed = 0
    for r in rows:
        sr = scores[scores["rung"] == r["rung"]]
        g = sr if r["cell"] == "ALL" else sr[sr["cell"] == r["cell"]]
        if g.empty:
            continue
        new = group_values(g, B, seed)
        for k in ("auc_event", "auc_direction"):
            old, now = r.get(k), new.get(k)
            if (old is None) != (now is None) or (old is not None and abs(old - now) > 1e-9):
                raise SystemExit(f"{json_path.name}: {r['cell']}/{r['rung']} {k} is {old} in the report and {now} from the score table")
        for k in KEYS:
            if k in new:
                value = None if new[k] is None or (isinstance(new[k], float) and not np.isfinite(new[k])) else float(new[k])
                if r.get(k) != value:
                    changed += 1
                    r[k] = value
    return changed


DECISION_KEYS = (
    "captured_fraction_adjusted_lo",
    "captured_fraction_adjusted_hi",
    "regret_adjusted_lo",
    "regret_adjusted_hi",
    "diff_random_adjusted_lo",
    "diff_random_adjusted_hi",
    "family_size",
)
DECISION_CHECKED = (
    "K",
    "n_tests",
    "total",
    "captured",
    "captured_fraction",
    "captured_fraction_lo",
    "captured_fraction_hi",
    "regret",
    "regret_lo",
    "regret_hi",
    "random_fraction",
    "diff_random",
    "diff_random_lo",
    "diff_random_hi",
)


def _origin_key(o) -> str:
    return "ALL" if str(o) == "ALL" else pd.Timestamp(o).tz_convert("UTC").isoformat()


def _refresh_decision(json_path: Path, doc: dict, scores: pd.DataFrame) -> int:
    """Recompute ``tables.decision_value`` from the score table with the report's seed and settings and replace the table with it.

    Every unadjusted value of every stored row must reproduce (an abort otherwise); the rows the stored table lacks (the arm-count policies
    and the matched differences of method call 201) and the Bonferroni-adjusted bounds (call 200) come from the recomputation. Returns the number
    of values that differ from the stored table (a new row counts all its values)."""
    from mootcourt.decision_value import decision_value
    from mootcourt.report import DECISION_BOOTSTRAP

    rows = doc["tables"].get("decision_value")
    if not rows:
        return 0
    h = doc["header"]
    pm = h.get("primary_metric")
    part = scores[scores["metric"].astype(str) == str(pm)] if pm is not None and "metric" in scores.columns else scores
    fresh = decision_value(part, seed=int(h["seed"]), B=min(int(h["bootstrap_resamples"]), DECISION_BOOTSTRAP))
    new_rows = clean(fresh)
    stored = {(_origin_key(r["origin"]), r["policy"], r["rung"], float(r["budget"])): r for r in rows}
    changed = 0
    for r in new_rows:
        old = stored.get((_origin_key(r["origin"]), r["policy"], r["rung"], float(r["budget"])))
        if old is None:
            changed += len(r)
            continue
        for k in DECISION_CHECKED:
            a, b = old.get(k), r.get(k)
            if (a is None) != (b is None) or (a is not None and abs(float(a) - float(b)) > 1e-9):
                raise SystemExit(
                    f"{json_path.name}: decision value {k} of {r['origin']}/{r['policy']}/{r['rung']} is {a} in the report and {b} from the scores"
                )
        changed += sum(1 for k, v in r.items() if k not in old or old[k] != v)
    if len(new_rows) < len(rows):
        raise SystemExit(f"{json_path.name}: the recomputed decision table has fewer rows than the report")
    doc["tables"]["decision_value"] = new_rows
    return changed


def refresh(json_path: Path, check: bool = False) -> tuple[int, int]:
    """Returns ``(values changed, 1 if the report was skipped else 0)``."""
    scores_path = json_path.with_name(json_path.name.replace("backtest-", "scores-", 1)).with_suffix(".parquet")
    doc = json.loads(json_path.read_text(encoding="utf-8"))
    rows = doc["tables"]["aggregate"]
    if not any("resolution_event" in r for r in rows):
        return 0, 0
    if not scores_path.exists():
        print(f"skipped {json_path.name}: no score table beside it", file=sys.stderr)
        return 0, 1
    scores = pd.read_parquet(scores_path)
    B, seed = int(doc["header"]["bootstrap_resamples"]), int(doc["header"]["seed"])
    changed = 0
    blocks = [(rows, scores, B)] + [
        (m["aggregate"], scores[scores["metric"].astype(str) == str(m["metric"])], min(B, hs.DEFAULT_B)) for m in doc["tables"].get("by_metric", [])
    ]
    for block_rows, block_scores, block_B in blocks:
        changed += _refresh_rows(json_path, block_rows, block_scores, block_B, seed)
    changed += _refresh_decision(json_path, doc, scores)
    if changed and not check:
        json_path.write_text(json.dumps(clean(doc), indent=1, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8")
        json_path.with_suffix(".md").write_text(render_markdown(doc), encoding="utf-8")
    print(f"{json_path.name}: {changed} values {'differ' if check else 'updated'}")
    return changed, 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("reports_dir")
    ap.add_argument("--check", action="store_true", help="report what would change and write nothing")
    args = ap.parse_args()
    root = Path(args.reports_dir)
    files = (
        sorted(root.glob("backtest-*.json"))
        + sorted((root / "ablations").glob("backtest-*.json"))
        + sorted((root / "positive-control").glob("backtest-*.json"))
    )
    results = [refresh(f, args.check) for f in files]
    total, skipped = sum(r[0] for r in results), sum(r[1] for r in results)
    print(f"{len(files)} reports, {skipped} skipped (no score table), {total} values {'would change' if args.check else 'updated'}")
    if args.check and skipped:
        print("error: some reports were not checked", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
