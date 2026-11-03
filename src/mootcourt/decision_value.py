"""Decision value: what a prioritisation policy would have captured, reported apart from calibration.

For each origin the period's tests are the tests with scored rows. A test's value is the best positive
observed lift among its contrasts (zero when every contrast is negative), in the units of y. A budget of
``K = max(1, floor(frac * n_tests + 0.5))`` tests is chosen three ways:

* ``random``: uniformly without replacement, ``draws`` seeded draws averaged.
* ``p_win``: the tests with the highest score, where a test's score is the largest ``p_win`` among its
  contrasts under a rung. Ties at the cut are broken by their expected value under a random tie-break.
* ``oracle``: the tests with the highest value, which needs ``y`` and so cannot be run before the trial.

For each policy the table gives the value captured, the fraction of the period's total value captured, and
the regret against the oracle (oracle value minus the policy's value). A period with no positive lift has
fraction 0 and regret 0, never a division by zero. These numbers are never folded into a calibration score.

Units: value, captured and regret are in the units of y (percentage points of click-through rate for Upworthy); fractions are unitless.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FRACTION = 0.25
DRAWS = 200
POLICIES = ("random", "p_win", "oracle")


def budget_k(n_tests: int, frac: float = FRACTION) -> int:
    """Budget K for a period of ``n_tests`` tests: ``floor(frac * n + 0.5)``, at least one."""
    return max(1, int(np.floor(frac * n_tests + 0.5)))


def _top_k_value(score: np.ndarray, value: np.ndarray, k: int) -> float:
    """Value captured by taking the ``k`` highest scores; a tie at the cut contributes its mean value."""
    k = min(k, len(score))
    order = np.argsort(-score, kind="stable")
    cut = score[order[k - 1]]
    above = score > cut
    n_above = int(above.sum())
    tied = score == cut
    return float(value[above].sum() + (k - n_above) * value[tied].mean())


def _period_rows(values: np.ndarray, p_win: np.ndarray, frac: float, draws: int, rng: np.random.Generator) -> dict[str, float]:
    n = len(values)
    k = budget_k(n, frac)
    captured_oracle = _top_k_value(values, values, k)
    idx = rng.random((draws, n)).argsort(axis=1)[:, :k]
    captured_random = float(values[idx].sum(axis=1).mean())
    return {"K": k, "n_tests": n, "total": float(values.sum()), "random": captured_random,
            "p_win": _top_k_value(p_win, values, k), "oracle": captured_oracle}


def decision_value(scores: pd.DataFrame, ledger: pd.DataFrame | None = None, frac: float = FRACTION, draws: int = DRAWS,
                   seed: int = 0) -> pd.DataFrame:
    """Decision-value table: one row per origin, policy (and rung for ``p_win``), plus an ``ALL`` origin.

    Columns: origin, policy, rung, K, n_tests, total, captured, captured_fraction, regret. ``ledger`` is accepted
    for symmetry with the plan and is not needed: a period's tests are the tests with scored rows.
    """
    rng = np.random.default_rng(seed)
    df = scores if "rung" in scores.columns else scores.assign(rung="all")
    rungs = sorted(df["rung"].unique())
    rows: list[dict] = []
    pooled: dict[tuple[str, str], dict[str, float]] = {}

    def add(origin, policy, rung, k, n_tests, total, captured, oracle):
        frac_cap = captured / total if total > 0 else 0.0
        regret = (oracle - captured) if total > 0 else 0.0
        rows.append({"origin": origin, "policy": policy, "rung": rung, "K": k, "n_tests": n_tests, "total": total,
                     "captured": captured, "captured_fraction": frac_cap, "regret": regret})
        acc = pooled.setdefault((policy, rung), {"K": 0, "n_tests": 0, "total": 0.0, "captured": 0.0, "oracle": 0.0})
        acc["K"] += k
        acc["n_tests"] += n_tests
        acc["total"] += total
        acc["captured"] += captured
        acc["oracle"] += oracle

    for origin, g in df.groupby("origin", sort=True):
        value = g.groupby("test_id")["y"].max().clip(lower=0.0)
        tests = value.index
        v = value.to_numpy(float)
        first = True
        for rung in rungs:
            gr = g[g["rung"] == rung]
            if gr.empty:
                continue
            pw = gr.groupby("test_id")["p_win"].max().reindex(tests)
            if not pw.notna().any():     # a rung without a probability that the effect is positive has no ranking to judge
                continue
            if pw.isna().any():          # a rung that scored only some tests of the period is judged on those
                keep = pw.notna().to_numpy()
                v_r, p_r = v[keep], pw.to_numpy(float)[keep]
            else:
                v_r, p_r = v, pw.to_numpy(float)
            res = _period_rows(v_r, p_r, frac, draws, rng)
            if first:
                first = False
                add(origin, "random", "all", res["K"], res["n_tests"], res["total"], res["random"], res["oracle"])
                add(origin, "oracle", "all", res["K"], res["n_tests"], res["total"], res["oracle"], res["oracle"])
            add(origin, "p_win", rung, res["K"], res["n_tests"], res["total"], res["p_win"], res["oracle"])
    for (policy, rung), a in pooled.items():
        total = a["total"]
        rows.append({"origin": "ALL", "policy": policy, "rung": rung, "K": a["K"], "n_tests": a["n_tests"], "total": total,
                     "captured": a["captured"], "captured_fraction": a["captured"] / total if total > 0 else 0.0,
                     "regret": (a["oracle"] - a["captured"]) if total > 0 else 0.0})
    out = pd.DataFrame(rows)
    out["_a"] = (out["origin"].astype(str) == "ALL").astype(int)
    out["_p"] = out["policy"].map({p: i for i, p in enumerate(POLICIES)})
    return out.sort_values(["_a", "origin", "_p", "rung"], kind="stable").drop(columns=["_a", "_p"]).reset_index(drop=True)
