"""Reliability report: rolling skill per cell, drift counters, one implementation for backtest and join.

The report schema is the one in ``abstain.py``::

    {"source": str, "as_of": ISO-8601 with offset,
     "cells": {cell: {"as_of", "rolling_logscore", "p0_rolling_logscore", "brier_skill", "n",
                      "drifted", "consecutive_below"}}}

An outcome is one scored prediction whose truth is known: ``cell``, ``at`` (when the outcome became
known), ``logscore`` of the model, ``p0_logscore`` of the baseline on the same row, ``brier`` of the model
and ``p0_brier`` of the baseline (squared error of p_sig against the significant-positive event, the
baseline being the cell's base rate). Log scores are per unit of the effect scale; Brier scores are
unitless.

Rules (builder calls 4 and 26):

* The window keeps outcomes dated after ``now - TRAILING_WEEKS`` weeks and not after ``now`` (builder call 42): an
  outcome exists only once its registered horizon has passed, so one dated in the future is not evidence yet and is
  ignored, whatever the caller handed in.
* A cell is below threshold when its rolling log score is more than ``DRIFT_LOGSCORE_MARGIN`` nats under
  the baseline on the same rows. That needs at least ``MIN_DRIFT_N`` outcomes in the window; with fewer, or
  with none, the counters are carried unchanged because there is no evidence either way.
* ``consecutive_below`` counts joins in a row that were below threshold. The cell is drifted when it
  reaches ``DRIFT_CONSECUTIVE``, and one later join that is not below threshold clears it.
* An entry's own ``as_of`` is the last time the cell had outcomes in the window. A cell with none keeps its old entry
  and its old ``as_of`` (only the report-level ``as_of`` moves), so the staleness trigger of ``abstain`` fires after
  ``reliability_max_age_days`` and a cell that stopped receiving outcomes is never reported as current (builder call
  82, code review finding REV-002). The backtest replay calls this same function, so it behaves the same way.
* Every entry also carries the window's evidence about its own precision (round 00, call 166): ``n_tests`` (distinct tests among the
  window's outcomes when the outcomes carry a ``test_id``), the 90 percent by-test bootstrap interval of the Brier skill
  (``brier_skill_lo``, ``brier_skill_hi``, 200 seeded resamples) and ``window_weeks``, so a card never prints a bare number.
* ``advance=False`` is a join that brought no new outcomes: the counters are carried unchanged. A cell whose window
  still holds outcomes gets a fresh ``as_of``; a cell whose window is empty keeps its old one.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from mootcourt.config import DRIFT_CONSECUTIVE, DRIFT_LOGSCORE_MARGIN, TRAILING_WEEKS

MIN_DRIFT_N = 10
SKILL_RESAMPLES = 200
_OUTCOME_COLUMNS = ["cell", "at", "logscore", "p0_logscore", "brier", "p0_brier"]


def _frame(outcomes) -> pd.DataFrame:
    if isinstance(outcomes, pd.DataFrame):
        df = outcomes.copy()
    else:
        rows = list(outcomes)
        df = pd.DataFrame(rows, columns=_OUTCOME_COLUMNS + (["test_id"] if any("test_id" in r for r in rows) else []))
    if len(df) == 0:
        df = pd.DataFrame({c: [] for c in _OUTCOME_COLUMNS})
    df["at"] = pd.to_datetime(df["at"], utc=True, format="ISO8601")
    return df


def skill_interval(
    brier: np.ndarray, base: np.ndarray, test_ids, B: int = SKILL_RESAMPLES, seed: int = 0
) -> tuple[float | None, float | None, int | None]:
    """90 percent by-test bootstrap interval of ``1 - mean(brier) / mean(base)`` and the number of tests; ``(None, None, None)`` without ids.

    Outcomes without a test id (files written before ids were stored) are left out of the resampling; when none has one the answer is None."""
    if test_ids is None:
        return None, None, None
    ids = pd.Series(np.asarray(test_ids, dtype=object))
    keep = ids.notna().to_numpy() & (ids.astype(str).str.strip() != "").to_numpy()
    if not keep.any():                # files written before test ids were stored, or rows without one: no clusters, no interval (REV-L-001)
        return None, None, None
    brier, base = np.asarray(brier, float)[keep], np.asarray(base, float)[keep]
    codes, uniq = pd.factorize(ids[keep])
    t = len(uniq)
    if t < 2:
        return None, None, int(t)
    sb = np.bincount(codes, weights=brier, minlength=t)
    s0 = np.bincount(codes, weights=base, minlength=t)
    counts = np.random.default_rng(seed).multinomial(t, np.full(t, 1.0 / t), size=B).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        draws = 1.0 - (counts @ sb) / (counts @ s0)
    draws = draws[np.isfinite(draws)]
    if len(draws) < 2:
        return None, None, int(t)
    lo, hi = np.percentile(draws, [5.0, 95.0])
    return float(lo), float(hi), int(t)


def _iso(t: dt.datetime) -> str:
    if t.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return t.isoformat()


def mark_drift(previous: dict | None, below: bool | None) -> tuple[int, bool]:
    """Next ``(consecutive_below, drifted)`` given the previous entry and whether this join was below threshold.

    ``below`` None means no evidence: the counters carry over.
    """
    prev_n = int((previous or {}).get("consecutive_below", 0))
    prev_drift = bool((previous or {}).get("drifted", False))
    if below is None:
        return prev_n, prev_drift
    n = prev_n + 1 if below else 0
    return n, n >= DRIFT_CONSECUTIVE


def build_reliability(prev: dict | None, outcomes, now: dt.datetime, advance: bool = True, source: str | None = None) -> dict:
    """Rewrite the reliability report as of ``now`` from the outcomes known so far.

    ``prev`` is the previous report or None. See the module docstring for the rules.
    """
    now_iso = _iso(now)
    src = source if source is not None else (prev or {}).get("source", "")
    prev_cells = (prev or {}).get("cells", {})
    df = _frame(outcomes if outcomes is not None else [])
    t_now = pd.Timestamp(now).tz_convert("UTC")
    win = df[(df["at"] > t_now - pd.Timedelta(weeks=TRAILING_WEEKS)) & (df["at"] <= t_now)]
    if prev is not None and not advance:
        backed = set(win["cell"])
        return {"source": src, "as_of": now_iso,
                "cells": {c: ({**e, "as_of": now_iso} if c in backed else dict(e)) for c, e in prev_cells.items()}}
    cells: dict[str, dict] = {}
    for cell in sorted(set(prev_cells) | set(win["cell"])):
        g = win[win["cell"] == cell]
        old = prev_cells.get(cell)
        if len(g) == 0:
            if old is not None:
                cells[cell] = dict(old)                 # keep the old as_of: no outcome in the window means the entry ages
            continue
        ls, p0 = float(g["logscore"].mean()), float(g["p0_logscore"].mean())
        b, b0 = float(g["brier"].mean()), float(g["p0_brier"].mean())
        n = int(len(g))
        below = (ls - p0 < -DRIFT_LOGSCORE_MARGIN) if n >= MIN_DRIFT_N else None
        consecutive, drifted = mark_drift(old, below)
        lo_s, hi_s, n_tests = skill_interval(
            g["brier"].to_numpy(), g["p0_brier"].to_numpy(), g["test_id"].to_numpy() if "test_id" in g.columns else None
        )
        cells[cell] = {
            "as_of": now_iso, "rolling_logscore": ls, "p0_rolling_logscore": p0,
            "brier_skill": (1.0 - b / b0) if b0 > 0 and np.isfinite(b0) else None,
            "n": n, "drifted": bool(drifted), "consecutive_below": int(consecutive),
            "n_tests": n_tests, "brier_skill_lo": lo_s, "brier_skill_hi": hi_s, "window_weeks": TRAILING_WEEKS,
        }
    return {"source": src, "as_of": now_iso, "cells": cells}
