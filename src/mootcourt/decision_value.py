"""Decision value: what a prioritisation policy would have captured, reported apart from calibration.

For each origin the period's tests are the tests with scored rows. A test's value is the best positive
observed lift among its contrasts (zero when every contrast is negative), in the units of y. A budget of
``K = max(1, floor(frac * n_tests + 0.5))`` tests is chosen three ways:

* ``random``: uniformly without replacement. Its expected capture is ``K / n`` of the period's total value by linearity of
  expectation, so it is computed exactly (round 00, docs/method.md call 173: the 200 seeded draws it replaced measured nothing).
* ``p_win``: the tests with the highest score, where a test's score is the largest ``p_win`` among its
  contrasts under a rung. Ties at the cut are broken by their expected value under a random tie-break.
* ``oracle``: the tests with the highest value, which needs ``y`` and so cannot be run before the trial.

The budget is a share of the period's tests, 10, 25 and 50 percent (``BUDGETS``); the main one, 25 percent, comes first in the table.
Every policy row carries a 90 percent bootstrap interval that resamples whole tests within each origin (the pooled ``ALL`` row
resamples within every origin and pools them) for the captured fraction, the regret and the difference from random order, and a
``note`` field. A rung whose ``p_win`` is constant within a cell (P0, and P1 and P2 wherever lambda is zero) ranks cells and then
breaks ties at random, so its capture equals random order apart from between-cell differences; ``constant_within_cell`` says which
rows are such, and the note says it in words.

For each policy the table gives the value captured, the fraction of the period's total value captured, and
the regret against the oracle (oracle value minus the policy's value). A period with no positive lift has
fraction 0 and regret 0, never a division by zero. These numbers are never folded into a calibration score.

Units: value, captured and regret are in the units of y (percentage points of click-through rate for Upworthy); fractions are unitless.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FRACTION = 0.25
BUDGETS = (0.25, 0.10, 0.50)          # the main budget first: callers that read one row per policy and origin get 25 percent
BOOTSTRAP = 500
DRAWS = 200                           # kept for callers of the earlier signature; random order is now exact
POLICIES = ("random", "p_win", "oracle")
LEVEL = 0.90
NOTE_RANDOM = "random order captures K over n of the total by linearity (exact expectation, no draws)"
NOTE_CELL = ("p_win is constant within a cell at every origin: the policy chooses by cell and then at random, "
             "so only between-cell differences can move it off random order")


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


def _period(values: np.ndarray, p_win: np.ndarray, frac: float) -> dict[str, float]:
    n = len(values)
    k = budget_k(n, frac)
    total = float(values.sum())
    return {"K": k, "n_tests": n, "total": total, "random": total * min(k, n) / n, "p_win": _top_k_value(p_win, values, k),
            "oracle": _top_k_value(values, values, k)}


def _ci(draws: np.ndarray) -> tuple[float | None, float | None]:
    d = draws[np.isfinite(draws)]
    if len(d) == 0:
        return None, None
    a = (1.0 - LEVEL) / 2.0
    lo, hi = np.percentile(d, [100 * a, 100 * (1 - a)])
    return float(lo), float(hi)


def _frac_regret(captured: np.ndarray, oracle: np.ndarray, total: np.ndarray):
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(total > 0, captured / total, 0.0)
    return frac, np.where(total > 0, oracle - captured, 0.0)


def _make_row(origin, pol: str, rung: str, budget: float, sel_rows: list[int], parts: list[dict], acc: dict, periods: list[dict]) -> dict:
    """One row of the table from the point values of its periods and their bootstrap draws (``acc``: sums per period and resample)."""
    k, n = sum(x["K"] for x in parts), sum(x["n_tests"] for x in parts)
    total, cap = sum(x["total"] for x in parts), sum(x["captured"] for x in parts)
    orc, rnd = sum(x["oracle_captured"] for x in parts), sum(x["random"] for x in parts)
    fr = cap / total if total > 0 else 0.0
    rfr = rnd / total if total > 0 else 0.0
    c, o, t, r = (acc[key][sel_rows].sum(axis=0) for key in ("cap", "orc", "tot", "rnd"))
    dfr, drg = _frac_regret(c, o, t)
    rfr_d, _ = _frac_regret(r, o, t)
    (flo, fhi), (rlo, rhi), (dlo, dhi) = _ci(dfr), _ci(drg), _ci(dfr - rfr_d)
    const = rung != "all" and all(periods[i]["rungs"][rung][2] for i in sel_rows if rung in periods[i]["rungs"])
    note = NOTE_RANDOM if pol == "random" else (NOTE_CELL if (pol == "p_win" and const) else "")
    return {"origin": origin, "policy": pol, "rung": rung, "budget": budget, "K": k, "n_tests": n, "total": total, "captured": cap,
            "captured_fraction": fr, "captured_fraction_lo": flo, "captured_fraction_hi": fhi,
            "regret": (orc - cap) if total > 0 else 0.0, "regret_lo": rlo, "regret_hi": rhi,
            "random_fraction": rfr, "diff_random": fr - rfr, "diff_random_lo": dlo, "diff_random_hi": dhi,
            "constant_within_cell": bool(const) if pol == "p_win" else None, "note": note}


def decision_value(scores: pd.DataFrame, ledger: pd.DataFrame | None = None, frac: float | None = None, draws: int = DRAWS,
                   seed: int = 0, fractions=BUDGETS, B: int = BOOTSTRAP) -> pd.DataFrame:
    """Decision-value table: one row per origin, budget, policy (and rung for ``p_win``), plus an ``ALL`` origin.

    Columns: origin, policy, rung, budget, K, n_tests, total, captured, captured_fraction (with ``_lo`` and ``_hi``), regret (with
    ``_lo`` and ``_hi``), random_fraction, diff_random (the captured fraction minus the random policy's, with ``_lo`` and ``_hi``),
    constant_within_cell and note. ``frac`` (one budget) replaces ``fractions``; ``ledger`` and ``draws`` are accepted for the
    earlier signature and are not needed. The intervals are percentile intervals of ``B`` seeded resamples of whole tests within each
    origin; the ``ALL`` row pools the origins in each resample.
    """
    rng = np.random.default_rng(seed)
    budgets = (float(frac),) if frac is not None else tuple(float(f) for f in fractions)
    df = scores if "rung" in scores.columns else scores.assign(rung="all")
    rungs = sorted(df["rung"].unique())
    # per origin: test values and, per rung, the kept mask, the p_win per test and whether p_win is constant within a cell
    periods: list[dict] = []
    for origin, g in df.groupby("origin", sort=True):
        value = g.groupby("test_id")["y"].max().clip(lower=0.0)
        tests = value.index
        v = value.to_numpy(float)
        per_rung = {}
        for rung in rungs:
            gr = g[g["rung"] == rung]
            if gr.empty:
                continue
            pw = gr.groupby("test_id")["p_win"].max().reindex(tests)
            if not pw.notna().any():     # a rung without a probability that the effect is positive has no ranking to judge
                continue
            keep = pw.notna().to_numpy()
            p = pw.to_numpy(float)
            # constant within a cell: every contrast of the rung in a cell has the same p_win at this origin (P0, and P1 and P2 where lambda is zero)
            const = "cell" in gr.columns and bool((gr.groupby("cell")["p_win"].nunique(dropna=True) <= 1).all())
            per_rung[rung] = (keep, np.where(keep, p, 0.0), const)
        if per_rung:
            periods.append({"origin": origin, "v": v, "rungs": per_rung})
    rows: list[dict] = []
    for f in budgets:
        # point values per origin and the bootstrap draws of every (policy, rung) at this budget
        point: dict[tuple, dict[str, float]] = {}
        draw_acc: dict[tuple, dict] = {}
        keys: list[tuple] = []
        for pi, per in enumerate(periods):
            first = True
            for rung, (keep, p, _const) in per["rungs"].items():
                res = _period(per["v"][keep], p[keep], f)
                if first:
                    first = False
                    point[(pi, "random", "all")] = {**res, "captured": res["random"], "oracle_captured": res["oracle"]}
                    point[(pi, "oracle", "all")] = {**res, "captured": res["oracle"], "oracle_captured": res["oracle"]}
                point[(pi, "p_win", rung)] = {**res, "captured": res["p_win"], "oracle_captured": res["oracle"]}
        keys = sorted({(pol, rung) for (_, pol, rung) in point})
        for pol, rung in keys:
            draw_acc[(pol, rung)] = {"cap": np.zeros((len(periods), B)), "orc": np.zeros((len(periods), B)), "tot": np.zeros((len(periods), B)),
                                     "rnd": np.zeros((len(periods), B))}
        for pi, per in enumerate(periods):
            n_all = len(per["v"])
            idx = rng.integers(0, n_all, size=(B, n_all))
            for b in range(B):
                ib = idx[b]
                first = True
                for rung, (keep, p, _const) in per["rungs"].items():
                    sel = ib[keep[ib]]
                    if len(sel) == 0:
                        continue
                    res = _period(per["v"][sel], p[sel], f)
                    if first:
                        first = False
                        for pol, cap in (("random", res["random"]), ("oracle", res["oracle"])):
                            a = draw_acc[(pol, "all")]
                            a["cap"][pi, b], a["orc"][pi, b], a["tot"][pi, b], a["rnd"][pi, b] = cap, res["oracle"], res["total"], res["random"]
                    a = draw_acc[("p_win", rung)]
                    a["cap"][pi, b], a["orc"][pi, b], a["tot"][pi, b], a["rnd"][pi, b] = res["p_win"], res["oracle"], res["total"], res["random"]

        for pol, rung in keys:
            for pi, per in enumerate(periods):
                if (pi, pol, rung) in point:
                    rows.append(_make_row(per["origin"], pol, rung, f, [pi], [point[(pi, pol, rung)]], draw_acc[(pol, rung)], periods))
            members = [pi for pi in range(len(periods)) if (pi, pol, rung) in point]
            if members:
                rows.append(_make_row("ALL", pol, rung, f, members, [point[(pi, pol, rung)] for pi in members], draw_acc[(pol, rung)], periods))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["_a"] = (out["origin"].astype(str) == "ALL").astype(int)
    out["_p"] = out["policy"].map({p: i for i, p in enumerate(POLICIES)})
    out["_b"] = out["budget"].map({b: i for i, b in enumerate(budgets)})
    return out.sort_values(["_a", "origin", "_b", "_p", "rung"], kind="stable").drop(columns=["_a", "_p", "_b"]).reset_index(drop=True)
