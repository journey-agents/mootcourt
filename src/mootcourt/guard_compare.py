"""Guarded against unguarded P2 selection on the same rows (builder call 86).

``compare_guard`` takes the score tables and report documents of two backtests of one source and snapshot that differ only in the P2
admission guard (the main run and the ``--p2-guard off`` ablation). It returns a JSON-ready dict with, for the rung (P2 by default):

* each run's own all-rows log score, CRPS and Brier skill with the 90 percent by-test bootstrap interval from its report,
* the paired mean differences (guarded minus unguarded) for log score, CRPS and Brier skill, each with a bootstrap interval that
  resamples whole tests, computed on the rows both runs scored (the Brier skill difference is the Brier difference divided by the mean
  base-rate Brier, so its sign is the same as the skill difference),
* the share of (cell, origin) selections held at lambda 0 in each run, and the share the guard turned from a positive lambda into zero.

Units: log score per unit of y (higher is better), CRPS in the units of y (lower is better), Brier skill unitless.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mootcourt import harness_stats as hs

RUNG = "P2"


def _row(doc: dict, rung: str) -> dict:
    return next(r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL" and r["rung"] == rung)


def _own(doc: dict, rung: str) -> dict:
    r = _row(doc, rung)
    keep = ("n", "n_tests", "logscore", "crps", "brier_skill")
    out = {k: r[k] for k in keep}
    for k in ("logscore", "crps", "brier_skill"):
        out[k + "_lo"], out[k + "_hi"] = r[k + "_lo"], r[k + "_hi"]
    sel = [s for s in (doc["tables"].get("p2_selection") or []) if s.get("rung") == rung]
    out["cells_origins"] = len(sel)
    out["share_lambda_zero"] = float(np.mean([s["lambda"] == 0 for s in sel])) if sel else None
    held = [s.get("guard_held") for s in sel if s.get("guard_held") is not None]
    out["share_guard_held"] = float(np.mean(held)) if held else None
    out["guard"] = next((s.get("guard") for s in sel), None)
    return out


def _paired(a: pd.DataFrame, b: pd.DataFrame, column: str, scale: float, B: int, seed: int) -> dict:
    m = a[["row_id", "test_id", column]].merge(b[["row_id", column]], on="row_id", suffixes=("_a", "_b"))
    frame = pd.DataFrame({"test_id": m["test_id"], "d": (m[column + "_a"] - m[column + "_b"]) * scale})
    iv = hs.bootstrap_by_test(frame, "d", B=B, seed=seed)
    return {"estimate": iv.estimate, "lo": iv.lo, "hi": iv.hi, "n": int(len(m))}


def compare_guard(guarded_scores: pd.DataFrame, unguarded_scores: pd.DataFrame, guarded_doc: dict, unguarded_doc: dict,
                  rung: str = RUNG, B: int = hs.DEFAULT_B, seed: int = 0) -> dict:
    """See the module docstring. Raises ValueError when the two runs are not on the same snapshot."""
    gh, uh = guarded_doc["header"], unguarded_doc["header"]
    if gh["snapshot_id"] != uh["snapshot_id"] or gh["source"] != uh["source"]:
        raise ValueError("the two runs must use the same source and snapshot")
    ga, ua = (s[s["rung"] == rung] for s in (guarded_scores, unguarded_scores))
    base = float(ga["brier_base"].mean())
    out = {
        "source": gh["source"], "snapshot_id": gh["snapshot_id"], "rung": rung, "bootstrap_resamples": B, "seed": seed,
        "guarded": _own(guarded_doc, rung), "unguarded": _own(unguarded_doc, rung),
        "difference": {"logscore": _paired(ga, ua, "logscore", 1.0, B, seed), "crps": _paired(ga, ua, "crps", 1.0, B, seed),
                       "brier_skill": _paired(ua, ga, "brier_event", 1.0 / base, B, seed)},
        "note": ("difference is guarded minus unguarded; positive log score and Brier skill differences favour the guard, "
                 "a negative CRPS difference favours the guard"),
    }
    return out
