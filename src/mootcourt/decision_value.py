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
BUDGETS = (0.25, 0.10, 0.50)  # the main budget first: callers that read one row per policy and origin get 25 percent
BOOTSTRAP = 500
DRAWS = 200  # kept for callers of the earlier signature; random order is now exact
POLICIES = ("random", "random_matched", "arm_count", "p_win", "oracle")
LEVEL = 0.90
NOTE_RANDOM = "random order captures K over n of the total by linearity (exact expectation, no draws)"
NOTE_MATCHED = (
    "random order within arm-count strata, matched to the arm-count composition of the set the rung chooses (exact expectation); "
    "the number of contrasts is known before launch, so this is the baseline a rung must beat (docs/method.md call 201)"
)
NOTE_ARMS = "ranks tests by their number of contrasts and reads no forecast (ties at the cut resolved by their expected value)"
NOTE_CELL = (
    "p_win is constant within a cell at every origin: the policy chooses by cell and then at random, "
    "so only between-cell differences can move it off random order"
)


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


def _matched_value(score: np.ndarray, values: np.ndarray, arms: np.ndarray, k: int) -> float:
    """Expected value of a random choice that matches the arm-count composition of the set chosen by ``score``.

    The chosen set is the top ``k`` by score; a tie at the cut is chosen with equal probability (so each tied test has weight
    ``(k - n_above) / n_tied``). Within each arm-count stratum a random choice of the same number of tests has the stratum's mean
    value per test, so the baseline is the sum over tests of ``weight * mean value of its stratum`` (review R1: the number of contrasts
    is a field known before launch and drives both the value of a test and the largest ``p_win`` among its contrasts)."""
    k = min(k, len(score))
    order = np.argsort(-score, kind="stable")
    cut = score[order[k - 1]]
    above, tied = score > cut, score == cut
    n_above, n_tied = int(above.sum()), int(tied.sum())
    weight = above.astype(float) + tied * ((k - n_above) / n_tied)
    out = 0.0
    for a in np.unique(arms[weight > 0]):
        m = arms == a
        out += float(weight[m].sum()) * float(values[m].mean())
    return out


def _period(values: np.ndarray, p_win: np.ndarray, frac: float, arms: np.ndarray | None = None) -> dict[str, float]:
    n = len(values)
    k = budget_k(n, frac)
    total = float(values.sum())
    out = {
        "K": k,
        "n_tests": n,
        "total": total,
        "random": total * min(k, n) / n,
        "p_win": _top_k_value(p_win, values, k),
        "oracle": _top_k_value(values, values, k),
    }
    if arms is not None:
        out["matched"] = _matched_value(p_win, values, arms, k)
        out["arm_count"] = _top_k_value(arms.astype(float), values, k)
    return out


def _ci(draws: np.ndarray) -> tuple[float | None, float | None]:
    d = draws[np.isfinite(draws)]
    if len(d) == 0:
        return None, None
    a = (1.0 - LEVEL) / 2.0
    lo, hi = np.percentile(d, [100 * a, 100 * (1 - a)])
    return float(lo), float(hi)


def _se(draws: np.ndarray) -> float | None:
    d = draws[np.isfinite(draws)]
    return float(np.std(d, ddof=1)) if len(d) > 1 else None


def apply_bonferroni(frame: pd.DataFrame) -> pd.DataFrame:
    """Add Bonferroni-adjusted bounds to the decision-value table and drop the private standard-error columns.

    Family (docs/method.md call 200): the intervals of the claim the table makes, which rung ranks tests better than random order. That is
    the number ``m`` of rungs whose POOLED (``ALL`` origin) ``p_win`` row has a difference-from-random interval of positive width at the
    row's budget; every row of that budget (the per-origin rows are descriptive) gets the same ``m`` in ``family_size``. The bound is the
    estimate plus or minus the bootstrap standard error times the normal quantile of ``1 - (1 - level) / 2 / m``, as in the aggregate table
    (call 174). The three intervals of a row (captured fraction, regret, difference from random order) are views of one comparison and share ``m``.
    """
    from scipy import special

    out = frame.copy()
    pooled = out[(out["origin"].astype(str) == "ALL") & (out["policy"] == "p_win") & ((out["diff_random_hi"] - out["diff_random_lo"]) > 0)]
    m_by_budget = pooled.groupby("budget").size()
    out["family_size"] = out["budget"].map(m_by_budget).fillna(0).astype(int)
    z = out["family_size"].map(lambda m: float(special.ndtri(1.0 - (1.0 - LEVEL) / 2.0 / m)) if m else float("nan"))
    for est, lo, hi, se in (
        ("diff_matched", "diff_matched_adjusted_lo", "diff_matched_adjusted_hi", "_se_diff_matched"),
        ("captured_fraction", "captured_fraction_adjusted_lo", "captured_fraction_adjusted_hi", "_se_captured_fraction"),
        ("regret", "regret_adjusted_lo", "regret_adjusted_hi", "_se_regret"),
        ("diff_random", "diff_random_adjusted_lo", "diff_random_adjusted_hi", "_se_diff_random"),
    ):
        out[est] = pd.to_numeric(out[est])
        out[se] = pd.to_numeric(out[se])
        ok = out[se].notna() & out["family_size"].gt(0)
        half = np.where(out[se] > 1e-12, z * out[se], 0.0)  # a row without sampling variation (random order is exact) keeps its estimate
        out[lo] = np.where(ok, out[est] - half, np.nan)
        out[hi] = np.where(ok, out[est] + half, np.nan)
    return out.drop(columns=["_se_captured_fraction", "_se_regret", "_se_diff_random", "_se_diff_matched"])


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
    se_f, se_r, se_d = _se(dfr), _se(drg), _se(dfr - rfr_d)
    if pol == "p_win" and "mat" in acc:
        mat = sum(x["matched"] for x in parts)
        mfr = mat / total if total > 0 else 0.0
        mfr_d, _ = _frac_regret(acc["mat"][sel_rows].sum(axis=0), o, t)
        (mlo, mhi), se_m, dm = _ci(dfr - mfr_d), _se(dfr - mfr_d), fr - mfr
    else:
        mfr, dm, mlo, mhi, se_m = None, None, None, None, None
    const = rung != "all" and all(periods[i]["rungs"][rung][2] for i in sel_rows if rung in periods[i]["rungs"])
    note = (
        NOTE_RANDOM
        if pol == "random"
        else NOTE_MATCHED
        if pol == "random_matched"
        else NOTE_ARMS
        if pol == "arm_count"
        else (NOTE_CELL if (pol == "p_win" and const) else "")
    )
    return {
        "origin": origin,
        "policy": pol,
        "rung": rung,
        "budget": budget,
        "K": k,
        "n_tests": n,
        "total": total,
        "captured": cap,
        "captured_fraction": fr,
        "captured_fraction_lo": flo,
        "captured_fraction_hi": fhi,
        "regret": (orc - cap) if total > 0 else 0.0,
        "regret_lo": rlo,
        "regret_hi": rhi,
        "random_fraction": rfr,
        "diff_random": fr - rfr,
        "diff_random_lo": dlo,
        "diff_random_hi": dhi,
        "matched_fraction": mfr,
        "diff_matched": dm,
        "diff_matched_lo": mlo,
        "diff_matched_hi": mhi,
        "constant_within_cell": bool(const) if pol == "p_win" else None,
        "note": note,
        "_se_captured_fraction": se_f,
        "_se_regret": se_r,
        "_se_diff_random": se_d,
        "_se_diff_matched": se_m,
    }


def decision_value(
    scores: pd.DataFrame,
    ledger: pd.DataFrame | None = None,
    frac: float | None = None,
    draws: int = DRAWS,
    seed: int = 0,
    fractions=BUDGETS,
    B: int = BOOTSTRAP,
) -> pd.DataFrame:
    """Decision-value table: one row per origin, budget, policy (and rung for ``p_win``), plus an ``ALL`` origin.

    Columns: origin, policy, rung, budget, K, n_tests, total, captured, captured_fraction (with ``_lo`` and ``_hi``), regret (with
    ``_lo`` and ``_hi``), random_fraction, diff_random (the captured fraction minus the random policy's, with ``_lo`` and ``_hi``),
    constant_within_cell and note, plus Bonferroni-adjusted bounds for the three intervals (``*_adjusted_lo``, ``*_adjusted_hi``) and the
    ``family_size`` they use (``apply_bonferroni``). ``frac`` (one budget) replaces ``fractions``; ``ledger`` and ``draws`` are accepted for the
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
        # the number of contrasts of each test (distinct scored rows): a field known before launch
        arms = (g.groupby("test_id")["row_id"].nunique() if "row_id" in g.columns else g.groupby("test_id").size()).reindex(tests).to_numpy(float)
        per_rung = {}
        for rung in rungs:
            gr = g[g["rung"] == rung]
            if gr.empty:
                continue
            pw = gr.groupby("test_id")["p_win"].max().reindex(tests)
            if not pw.notna().any():  # a rung without a probability that the effect is positive has no ranking to judge
                continue
            keep = pw.notna().to_numpy()
            p = pw.to_numpy(float)
            # constant within a cell: every contrast of the rung in a cell has the same p_win at this origin (P0, and P1 and P2 where lambda is zero)
            const = "cell" in gr.columns and bool((gr.groupby("cell")["p_win"].nunique(dropna=True) <= 1).all())
            per_rung[rung] = (keep, np.where(keep, p, 0.0), const)
        if per_rung:
            periods.append({"origin": origin, "v": v, "arms": arms, "rungs": per_rung})
    rows: list[dict] = []
    for f in budgets:
        # point values per origin and the bootstrap draws of every (policy, rung) at this budget
        point: dict[tuple, dict[str, float]] = {}
        draw_acc: dict[tuple, dict] = {}
        keys: list[tuple] = []
        for pi, per in enumerate(periods):
            first = True
            for rung, (keep, p, _const) in per["rungs"].items():
                res = _period(per["v"][keep], p[keep], f, per["arms"][keep])
                if first:
                    first = False
                    point[(pi, "random", "all")] = {**res, "captured": res["random"], "oracle_captured": res["oracle"]}
                    point[(pi, "oracle", "all")] = {**res, "captured": res["oracle"], "oracle_captured": res["oracle"]}
                    point[(pi, "arm_count", "all")] = {**res, "captured": res["arm_count"], "oracle_captured": res["oracle"]}
                point[(pi, "p_win", rung)] = {**res, "captured": res["p_win"], "oracle_captured": res["oracle"]}
                point[(pi, "random_matched", rung)] = {**res, "captured": res["matched"], "oracle_captured": res["oracle"]}
        keys = sorted({(pol, rung) for (_, pol, rung) in point})
        for pol, rung in keys:
            draw_acc[(pol, rung)] = {
                "cap": np.zeros((len(periods), B)),
                "orc": np.zeros((len(periods), B)),
                "tot": np.zeros((len(periods), B)),
                "rnd": np.zeros((len(periods), B)),
                "mat": np.zeros((len(periods), B)),
            }
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
                    res = _period(per["v"][sel], p[sel], f, per["arms"][sel])
                    if first:
                        first = False
                        for pol, cap in (("random", res["random"]), ("oracle", res["oracle"]), ("arm_count", res["arm_count"])):
                            a = draw_acc[(pol, "all")]
                            a["cap"][pi, b], a["orc"][pi, b], a["tot"][pi, b], a["rnd"][pi, b] = cap, res["oracle"], res["total"], res["random"]
                    a = draw_acc[("p_win", rung)]
                    a["cap"][pi, b], a["orc"][pi, b], a["tot"][pi, b], a["rnd"][pi, b] = res["p_win"], res["oracle"], res["total"], res["random"]
                    a["mat"][pi, b] = res["matched"]
                    a = draw_acc[("random_matched", rung)]
                    a["cap"][pi, b], a["orc"][pi, b], a["tot"][pi, b], a["rnd"][pi, b] = res["matched"], res["oracle"], res["total"], res["random"]

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
    out = apply_bonferroni(out)
    out["_a"] = (out["origin"].astype(str) == "ALL").astype(int)
    out["_p"] = out["policy"].map({p: i for i, p in enumerate(POLICIES)})
    out["_b"] = out["budget"].map({b: i for i, b in enumerate(budgets)})
    return out.sort_values(["_a", "origin", "_b", "_p", "rung"], kind="stable").drop(columns=["_a", "_p", "_b"]).reset_index(drop=True)
