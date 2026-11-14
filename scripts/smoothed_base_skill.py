#!/usr/bin/env python3
"""The Brier skill of a rung against a smoothed base rate, from the saved scores of one backtest (section "Registration of the
confirmatory reading" of docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md, written 14 November 2026).

The base rate of a cell at an origin is the share of events among the cell's visible rows, so a cell with few visible rows and no event
forecasts zero and is charged a full unit of Brier score by each event. The registered smoothed base rate shrinks the cell toward the
origin: for a cell with ``k`` events among ``n`` visible rows, and with ``p_pool`` the sum of ``k`` over the cells scored at that origin
divided by the sum of ``n`` over those cells, it is ``(k + m * p_pool) / (n + m)`` with ``m = 30`` (``PSEUDO_ROWS``; fixed by the
registration, not an option). ``n`` is the saved ``n_visible_cell`` and ``k`` is ``p_base * n_visible_cell``, which must be an integer
within 1e-6. The Brier score of the smoothed base rate on a row is ``(smoothed - event) ** 2`` on the realized event.

For each rung the script writes, with the skill ``1 - sum(Brier) / sum(Brier of the smoothed base rate)``:

* ``pooled``: the skill, its 90 percent percentile interval by test, and ``adjusted_lo`` and ``adjusted_hi``, the interval adjusted by
  Bonferroni for a family of three readings (``family_size``): the estimate plus or minus the standard deviation of the bootstrap draws
  times the normal quantile of ``1 - 0.05 / 3``;
* ``by_origin``: the skill at each origin with an interval that resamples the tests of that origin;
* ``origin_level``: the mean of the origin skills with a Student-t 90 percent interval, the origins as exchangeable units, and
  ``origin_level_leave_one_out``, the same with each origin removed in turn;
* ``unsmoothed``: ``pooled`` and ``origin_level`` against the stored Brier score of the unsmoothed base rate, which reproduce the values
  of scripts/by_origin_skill.py and carry no verdict;
* ``strata``: one record per origin and cell with ``n``, ``k``, ``p_base``, ``p_pool`` and ``smoothed``.

No model is run. The resample count and the seed are the report's.

Use: ``python scripts/smoothed_base_skill.py --scores SCORES.parquet --report BACKTEST.json --out OUT.json [--rungs P1 P2]``
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

PSEUDO_ROWS = 30          # m of the registration: the row count the paper uses as the least for a quarter's level; not tuned
FAMILY_SIZE = 3           # the primary readings of the registration
INTEGER_TOLERANCE = 1e-6


def _skill(frame: pd.DataFrame, base: str, B: int, seed: int, level: float) -> dict:
    """The skill of a frame with column ``b`` against the column ``base``, its percentile interval by test and the adjusted interval."""
    ts = hs._TestSums(frame, {"b": frame["b"].to_numpy(float), "base": frame[base].to_numpy(float)})
    counts = ts.resample_counts(B, np.random.default_rng(seed))
    with np.errstate(invalid="ignore", divide="ignore"):
        draws = 1.0 - (counts @ ts.sums["b"]) / (counts @ ts.sums["base"])
    lo, hi = hs._percentile_interval(draws, level)
    skill = float(1.0 - frame["b"].sum() / frame[base].sum())
    half = float(stats.norm.ppf(1.0 - (1.0 - level) / 2.0 / FAMILY_SIZE) * np.nanstd(draws, ddof=1))
    return {"skill": skill, "lo": float(lo), "hi": float(hi), "adjusted_lo": skill - half, "adjusted_hi": skill + half,
            "family_size": FAMILY_SIZE, "n_rows": int(len(frame)), "n_tests": int(frame["test_id"].nunique())}


def _t_interval(values: np.ndarray, level: float) -> dict:
    half = float(stats.t.ppf(0.5 + level / 2.0, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else float("nan")
    return {"skill": float(values.mean()), "lo": float(values.mean() - half), "hi": float(values.mean() + half), "origins": int(len(values))}


def strata_of(d: pd.DataFrame) -> pd.DataFrame:
    """One row per origin and cell of ``d`` with ``n``, ``k``, ``p_base``, ``p_pool`` and ``smoothed``. Raises ValueError when a cell's
    rows disagree on ``p_base`` or ``n_visible_cell``, or when ``p_base * n_visible_cell`` is not an integer within the tolerance."""
    cells = d.groupby(["origin", "cell"], sort=True).agg(p_base=("p_base", "first"), p_base_values=("p_base", "nunique"),
                                                         n=("n_visible_cell", "first"), n_values=("n_visible_cell", "nunique")).reset_index()
    bad = cells[(cells["p_base_values"] != 1) | (cells["n_values"] != 1)]
    if len(bad):
        raise ValueError(f"p_base and n_visible_cell must each hold one value per origin and cell; they do not in {len(bad)} pairs, first "
                         f"{bad.iloc[0]['origin']} {bad.iloc[0]['cell']}")
    n = cells["n"].to_numpy(float)
    raw = cells["p_base"].to_numpy(float) * n
    k = np.rint(raw)
    off = ~(np.abs(raw - k) <= INTEGER_TOLERANCE) | ~(np.abs(n - np.rint(n)) <= INTEGER_TOLERANCE)
    if off.any():
        i = int(np.flatnonzero(off)[0])
        raise ValueError(f"p_base * n_visible_cell is not an integer within {INTEGER_TOLERANCE} in {int(off.sum())} pairs of origin and "
                         f"cell, first {cells.iloc[i]['origin']} {cells.iloc[i]['cell']}: {raw[i]!r} of {n[i]!r}")
    cells["k"], cells["n"] = k, np.rint(n)
    sums = cells.groupby("origin", sort=True)[["k", "n"]].transform("sum")
    cells["p_pool"] = sums["k"] / sums["n"]
    cells["smoothed"] = (cells["k"] + PSEUDO_ROWS * cells["p_pool"]) / (cells["n"] + PSEUDO_ROWS)
    return cells[["origin", "cell", "n", "k", "p_base", "p_pool", "smoothed"]]


def summarize(scores: pd.DataFrame, rung: str, B: int, seed: int, level: float = 0.9) -> dict:
    """The readings of the module docstring for one rung. Raises ValueError when the rung has no scored row."""
    g = scores[scores["rung"] == rung]
    g = g[np.isfinite(g["brier_event"].to_numpy(float))]
    if g.empty:
        raise ValueError(f"no scored row for {rung}")
    d = pd.DataFrame({"test_id": g["test_id"].to_numpy(), "origin": pd.to_datetime(g["origin"], utc=True).to_numpy(), "cell": g["cell"].to_numpy(),
                      "b": g["brier_event"].to_numpy(float), "base": g["brier_base"].to_numpy(float), "p_base": g["p_base"].to_numpy(float),
                      "event": g["event"].to_numpy(float), "n_visible_cell": g["n_visible_cell"].to_numpy(float)})
    cells = strata_of(d)
    d["smoothed"] = d[["origin", "cell"]].merge(cells[["origin", "cell", "smoothed"]], on=["origin", "cell"], how="left")["smoothed"].to_numpy(float)
    d["base_smoothed"] = (d["smoothed"] - d["event"]) ** 2
    groups = list(d.groupby("origin", sort=True))

    by_origin = [{"origin": pd.Timestamp(o).isoformat(), **_skill(f, "base_smoothed", B, seed, level)} for o, f in groups]
    for r in by_origin:           # the adjustment belongs to the pooled reading only
        for key in ("adjusted_lo", "adjusted_hi", "family_size"):
            del r[key]
    values = np.array([r["skill"] for r in by_origin], dtype=float)
    level_loo = [{"left_out": r["origin"], **_t_interval(np.delete(values, k), level)} for k, r in enumerate(by_origin)] if len(values) > 2 else []
    plain = np.array([1.0 - f["b"].sum() / f["base"].sum() for _, f in groups], dtype=float)
    note = "Student-t interval on the origin skills, the origins as exchangeable units"
    return {
        "rung": rung, "event": "realized",
        "pooled": _skill(d, "base_smoothed", B, seed, level),
        "by_origin": by_origin,
        "origin_level": {**_t_interval(values, level), "note": note},
        "origin_level_leave_one_out": level_loo,
        "origin_level_leave_one_out_above_zero": int(sum(1 for r in level_loo if r["lo"] > 0)),
        "unsmoothed": {"pooled": _skill(d, "base", B, seed, level), "origin_level": {**_t_interval(plain, level), "note": note},
                       "note": "against the stored Brier score of the unsmoothed base rate; carries no verdict"},
        "strata": [{"origin": pd.Timestamp(r.origin).isoformat(), "cell": str(r.cell), "n": int(r.n), "k": int(r.k), "p_base": float(r.p_base),
                    "p_pool": float(r.p_pool), "smoothed": float(r.smoothed)} for r in cells.itertuples(index=False)],
        "bootstrap_resamples": int(B), "seed": int(seed), "level": level,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scores", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--rungs", nargs="+", default=["P1", "P2"])
    args = ap.parse_args()
    header = json.loads(args.report.read_text(encoding="utf-8"))["header"]
    sc = pd.read_parquet(args.scores, columns=["test_id", "origin", "cell", "rung", "n_visible_cell", "brier_event", "brier_base", "p_base", "event"])
    B, seed = int(header["bootstrap_resamples"]), int(header["seed"])
    doc = {"rungs": {r: summarize(sc, r, B, seed) for r in args.rungs},
           "definition": "smoothed base rate of a cell at an origin = (k + m * p_pool) / (n + m), with k events among the cell's n visible "
                         "rows (k = p_base * n_visible_cell), p_pool = sum of k over the cells scored at that origin / sum of n over those "
                         "cells, and m = pseudo_rows; skill = 1 - sum(Brier) / sum((smoothed - event)^2) on the realized event; intervals "
                         "resample tests and hold the origins fixed, adjusted_lo and adjusted_hi are the estimate plus or minus the "
                         "bootstrap standard deviation times the normal quantile of 1 - 0.05 / family_size, and origin_level is a "
                         "Student-t interval on the origin skills",
           "pseudo_rows": PSEUDO_ROWS,
           "inputs": {"scores": args.scores.name, "report": args.report.name}}
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
