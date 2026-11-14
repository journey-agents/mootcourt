#!/usr/bin/env python3
"""The Brier skill of a rung by origin, from the saved scores of one backtest (addendum of 14 November 2026 to
docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md).

The pooled interval of a backtest report resamples tests and holds the origins fixed. With exposure fixed a rung's probability is one value
per cell and origin, so its skill is carried by a few levels in a few quarters. This script reads the per-row scores and writes, for one
rung and one definition of the event (``realized``: the event at realized precision; ``planned``: at planned precision), with the skill
``1 - sum(Brier) / sum(Brier of the base rate)``:

* ``pooled``: the skill and its interval by test, which reproduces the report's value;
* ``by_origin``: the skill at each origin with an interval that resamples the tests of that origin;
* ``leave_one_origin_out``: the pooled skill with each origin removed in turn, each with its interval by test;
* ``origin_level``: the mean of the origin skills with a Student-t interval, the origins as exchangeable units, and
  ``origin_level_leave_one_out``, the same with each origin removed in turn;
* ``zero_base_rate_strata``: each pair of origin and cell in which the base rate's probability is zero on every row, with its rows, the
  visible rows of the cell, its event rate and its share of the pooled Brier gain (the base rate's summed Brier score minus the rung's);
* ``without_zero_base_rate_strata``: the pooled skill and its interval by test without those pairs, and
  ``origin_level_without_zero_base_rate_strata``, the Student-t interval on the origin skills without them;
* ``level_gap``: the rung's mean probability minus the event rate, pooled with its interval by test, at each origin, and with a Student-t
  interval on the origin gaps (second addendum of 14 November 2026).

No model is run. The resample count and the seed are the report's.

Use: ``python scripts/by_origin_skill.py --scores SCORES.parquet --report BACKTEST.json --out OUT.json [--rungs P1 P2]``
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

EVENTS = {"realized": ("brier_event", "brier_base", "p_base", "event"),
          "planned": ("brier_planned", "brier_base_planned", "p_base_planned", "event_planned")}


def _skill(frame: pd.DataFrame, B: int, seed: int, level: float) -> dict:
    """The skill of a frame with columns ``b`` and ``base`` and its percentile interval by test."""
    ts = hs._TestSums(frame, {"b": frame["b"].to_numpy(float), "base": frame["base"].to_numpy(float)})
    counts = ts.resample_counts(B, np.random.default_rng(seed))
    with np.errstate(invalid="ignore", divide="ignore"):
        draws = 1.0 - (counts @ ts.sums["b"]) / (counts @ ts.sums["base"])
    lo, hi = hs._percentile_interval(draws, level)
    return {"skill": float(1.0 - frame["b"].sum() / frame["base"].sum()), "lo": float(lo), "hi": float(hi), "n_rows": int(len(frame)),
            "n_tests": int(frame["test_id"].nunique())}


def _t_interval(values: np.ndarray, level: float) -> dict:
    half = float(stats.t.ppf(0.5 + level / 2.0, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else float("nan")
    return {"skill": float(values.mean()), "lo": float(values.mean() - half), "hi": float(values.mean() + half), "origins": int(len(values))}


def summarize(scores: pd.DataFrame, rung: str, event: str, B: int, seed: int, level: float = 0.9) -> dict:
    """The readings of the module docstring for one rung and one event. Raises ValueError when the rung has no scored row."""
    brier, base, p_base, ev = EVENTS[event]
    g = scores[scores["rung"] == rung]
    g = g[np.isfinite(g[brier].to_numpy(float))]
    if g.empty:
        raise ValueError(f"no scored row for {rung}")
    d = pd.DataFrame({"test_id": g["test_id"].to_numpy(), "origin": pd.to_datetime(g["origin"], utc=True).to_numpy(), "cell": g["cell"].to_numpy(),
                      "b": g[brier].to_numpy(float), "base": g[base].to_numpy(float), "p_base": g[p_base].to_numpy(float),
                      "event": g[ev].to_numpy(float), "n_visible_cell": g["n_visible_cell"].to_numpy(float),
                      "gap": (g["p_sig"].to_numpy(float) - g[ev].to_numpy(float)) if "p_sig" in g else np.nan})
    groups = list(d.groupby("origin", sort=True))
    by_origin = [{"origin": pd.Timestamp(o).isoformat(), **_skill(f, B, seed, level)} for o, f in groups]
    loo = [{"left_out": pd.Timestamp(o).isoformat(), **_skill(d.drop(index=f.index), B, seed, level)} for o, f in groups] if len(groups) > 1 else []
    values = np.array([r["skill"] for r in by_origin], dtype=float)
    level_loo = [{"left_out": r["origin"], **_t_interval(np.delete(values, k), level)} for k, r in enumerate(by_origin)] if len(values) > 2 else []
    gain = float(d["base"].sum() - d["b"].sum())
    zero, drop = [], np.zeros(len(d), dtype=bool)
    for (o, cell), f in d.groupby(["origin", "cell"], sort=True):
        if float(f["p_base"].abs().max()) == 0.0:
            zero.append({"origin": pd.Timestamp(o).isoformat(), "cell": str(cell), "rows": int(len(f)), "n_tests": int(f["test_id"].nunique()),
                         "n_visible_cell": int(f["n_visible_cell"].max()), "event_rate": float(f["event"].mean()),
                         "share_of_pooled_gain": float((f["base"].sum() - f["b"].sum()) / gain) if gain != 0 else None})
            drop |= d.index.isin(f.index)
    doc = {
        "rung": rung, "event": event,
        "pooled": _skill(d, B, seed, level),
        "by_origin": by_origin,
        "by_origin_above_zero": int(sum(1 for r in by_origin if r["lo"] > 0)),
        "by_origin_below_zero": int(sum(1 for r in by_origin if r["hi"] < 0)),
        "leave_one_origin_out": loo,
        "leave_one_origin_out_above_zero": int(sum(1 for r in loo if r["lo"] > 0)),
        "origin_level": {**_t_interval(values, level), "note": "Student-t interval on the origin skills, the origins as exchangeable units"},
        "origin_level_leave_one_out": level_loo,
        "origin_level_leave_one_out_above_zero": int(sum(1 for r in level_loo if r["lo"] > 0)),
        "zero_base_rate_strata": zero,
        "bootstrap_resamples": int(B), "seed": int(seed), "level": level,
    }
    if zero:
        rest = d[~drop]
        doc["without_zero_base_rate_strata"] = _skill(rest, B, seed, level)
        doc["origin_level_without_zero_base_rate_strata"] = _t_interval(
            np.array([1.0 - f["b"].sum() / f["base"].sum() for _, f in rest.groupby("origin", sort=True)], dtype=float), level)
    if "p_sig" in g:          # the level: the rung's mean probability minus the event rate, with both units of resampling
        def gap(frame: pd.DataFrame) -> dict:
            iv = hs.bootstrap_by_test(frame, "gap", B=B, seed=seed, level=level)
            return {"gap": float(iv.estimate), "lo": float(iv.lo), "hi": float(iv.hi), "n_rows": int(len(frame))}

        gaps = [{"origin": pd.Timestamp(o).isoformat(), **gap(f)} for o, f in groups]
        level_iv = _t_interval(np.array([r["gap"] for r in gaps], dtype=float), level)
        doc["level_gap"] = {"pooled": gap(d), "by_origin": gaps, "by_origin_above_zero": int(sum(1 for r in gaps if r["gap"] > 0)),
                            "origin_level": {"gap": level_iv["skill"], "lo": level_iv["lo"], "hi": level_iv["hi"], "origins": level_iv["origins"]}}
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scores", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--rungs", nargs="+", default=["P1", "P2"])
    args = ap.parse_args()
    header = json.loads(args.report.read_text(encoding="utf-8"))["header"]
    columns = ["row_id", "test_id", "origin", "cell", "rung", "n_visible_cell", "p_sig", *sorted({c for cols in EVENTS.values() for c in cols})]
    sc = pd.read_parquet(args.scores, columns=columns)
    B, seed = int(header["bootstrap_resamples"]), int(header["seed"])
    doc = {"rungs": {r: {e: summarize(sc, r, e, B, seed) for e in EVENTS} for r in args.rungs},
           "definition": "skill = 1 - sum(Brier) / sum(Brier of the base rate) on the rows of the group; intervals resample tests and hold the "
                         "origins fixed, except origin_level, a Student-t interval on the origin skills",
           "inputs": {"scores": args.scores.name, "report": args.report.name}}
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
