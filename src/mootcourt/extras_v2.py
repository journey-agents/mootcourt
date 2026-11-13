"""Analyses of the paper version 2 plan (run 8): pure functions over the stored score tables, reports and ledger.

Each function reads what a finished backtest wrote (the score table, the report) or the ledger, returns a plain dict that ``scripts/paper_extras.py``
stores under its own key, and never refits a model. A function whose input file does not exist returns None, so a partial data root still produces
a report. Units follow the score tables: percentage points of click-through rate for Upworthy, probabilities and Brier scores unitless.

Keys (X numbers are the plan's experiments):

* X1 ``randomization_window``: the date rule of the archive's June 2024 notice, the tests and rows it flags, the headline numbers of the main run, of
  the ablation that includes the window and of run 7 side by side, and a leaf-by-leaf check that the ablation regenerates run 7.
* X2 ``effect_scale_choices``: the main run, the cautionary run, relative lift at planned precision and absolute effect at realized precision.
* X3 ``exposure_fixed``: the main run against the run with every row's planned exposure set to its cell's median.
* X4 ``prior_family_scale``: Student-t against normal prior on the effect in percentage points and on the effect divided by the reference click-through rate.
* X5 ``ranking_paired``: captured lift of P2, the text classifier and P1 paired by test, an exposure-only policy beside the arm-count policy.
* X6 ``abstention_composition``: abstained against issued rows without the burn-in origin, within origin-and-cell strata, against one baseline.
* X7 ``gates_by_stratum``: the gate sizes simulated at each stratum's own dependence and one verdict rule for every stratum and rung.
* X8 ``drift_matched_null``: the calibration null with event rates that follow the trailing window, beside the current null.
* X9 ``within_origin_auc_by_year`` and ``lowest_reliability_bin``: discrimination inside origins and the lowest reliability bin.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import special

from mootcourt import decision_value as dv
from mootcourt import harness_stats as hs
from mootcourt.config import NU_GRID
from mootcourt.storage import storage_paths, visible_glob

LEVEL = hs.LEVEL
DEFAULT_B = 500
RUNG_ORDER = ("P0", "P1", "P2", "GBM", "local_eb", "text_lr")
HEADLINE_RUNGS = ("P0", "P1", "P2", "text_lr", "GBM", "local_eb")
HEADLINE_FIELDS = (
    "n",
    "n_tests",
    "brier_skill",
    "brier_skill_lo",
    "brier_skill_hi",
    "logscore",
    "auc_event",
    "auc_event_lo",
    "auc_event_hi",
    "auc_event_within",
    "auc_event_within_lo",
    "auc_event_within_hi",
    "ece",
    "ece_percentile",
    "event_rate",
    "decidable_by_tests",
)


# ----------------------------------------------------------------------------------------------------------------------------- reading
def _load(path: Path) -> dict | None:
    path = Path(path)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _scores(path: Path) -> pd.DataFrame | None:
    path = Path(path)
    return pd.read_parquet(path) if path.is_file() else None


def _ablation(reports_dir: Path, source: str, sid: str, suffix: str) -> tuple[Path, Path]:
    d = Path(reports_dir) / "ablations"
    return d / f"backtest-{source}-{sid}--{suffix}.json", d / f"scores-{source}-{sid}--{suffix}.parquet"


def _agg(doc: dict | None, cell: str = "ALL", rungs=HEADLINE_RUNGS, fields=HEADLINE_FIELDS) -> dict | None:
    """The aggregate rows of one cell of a report as ``{rung: {field: value}}``."""
    if doc is None:
        return None
    out = {}
    for r in doc.get("tables", {}).get("aggregate", []):
        if r.get("cell") == cell and r.get("rung") in rungs:
            out[r["rung"]] = {k: r.get(k) for k in fields}
    return out


def _numeric_leaves(obj, prefix="") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_numeric_leaves(v, f"{prefix}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_numeric_leaves(v, f"{prefix}[{i}]"))
    elif isinstance(obj, bool) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        out[prefix] = float(obj)
    return out


# ------------------------------------------------------------------------------------------------------------------- X1: the notice
SKIP_HEADER = ("model_id", "snapshot_id", "feature_hash", "command", "created_at", "boundary")


def compare_reports(a: dict, b: dict, rel_tol: float = 1e-9, abs_tol: float = 1e-12) -> dict:
    """Leaf-by-leaf comparison of the numeric leaves of two backtest reports, ignoring the header fields that name a model, a snapshot or a time.

    The tolerance is the one of ``scripts/quick_check.py`` (relative 1e-9, absolute 1e-12). Returns the counts, the leaves present in one report only and the
    first differences."""
    la = {k: v for k, v in _numeric_leaves({**a, "header": {h: x for h, x in a.get("header", {}).items() if h not in SKIP_HEADER}}).items()}
    lb = {k: v for k, v in _numeric_leaves({**b, "header": {h: x for h, x in b.get("header", {}).items() if h not in SKIP_HEADER}}).items()}
    common = sorted(set(la) & set(lb))
    diffs = [(k, la[k], lb[k]) for k in common if not (la[k] == lb[k] or math.isclose(la[k], lb[k], rel_tol=rel_tol, abs_tol=abs_tol))]
    return {
        "leaves_compared": len(common),
        "leaves_only_in_first": len(set(la) - set(lb)),
        "leaves_only_in_second": len(set(lb) - set(la)),
        "leaves_different": len(diffs),
        "rel_tol": rel_tol,
        "abs_tol": abs_tol,
        "first_differences": [{"leaf": k, "first": x, "second": y} for k, x, y in diffs[:10]],
    }


def randomization_window_summary(
    reports_dir, source: str, snapshot_id: str, ledger: pd.DataFrame, *, ablation_dir=None, run7_report=None, run7_scores=None
) -> dict | None:
    """X1. The rule's effect on the ledger and the headline numbers of the main run, the ablation that includes the window and run 7.

    ``ablation_dir`` is the folder of the ablation run (``include-randomization-window``: its own ledger at ``data/ledger/ledger.parquet`` and its report and
    score table beside); ``run7_report`` and ``run7_scores`` are run 7's main report and score table. Any of the three may be missing; the parts that need
    them are None."""
    if source != "upworthy":
        return None
    reports_dir = Path(reports_dir)
    main_doc = _load(reports_dir / f"backtest-{source}-{snapshot_id}.json")
    out: dict = {
        "window": {
            "first_day": "2013-06-25",
            "last_day": "2014-01-10",
            "inclusive": True,
            "basis": "UTC date of the earliest created_at of the test's packages",
        },
        "notice": "https://upworthy.natematias.com/about-the-archive (June 2024: evidence of randomization problems in about 22 percent of tests; "
        "causal or confirmatory use of tests from 25 June 2013 to 10 January 2014 is discouraged)",
        "ledger_statuses_main": {k: int(v) for k, v in ledger["status"].value_counts().sort_index().items()},
        "tests_in_ledger": int(ledger["test_id"].nunique()),
    }
    abl_dir = Path(ablation_dir) if ablation_dir else None
    abl_ledger = None
    abl_ledger_path = storage_paths(root=abl_dir).ledger_path if abl_dir is not None else None
    if abl_ledger_path is not None and abl_ledger_path.is_file():
        from mootcourt.ledger import read_ledger

        al = read_ledger(abl_ledger_path)
        abl_ledger = al[al["source"] == source].reset_index(drop=True)
        joined = ledger[["row_id", "test_id", "status"]].merge(
            abl_ledger[["row_id", "status"]].rename(columns={"status": "status_ablation"}), on="row_id", how="outer"
        )
        moved = joined[joined["status"] != joined["status_ablation"]]
        out["ledger_statuses_ablation"] = {k: int(v) for k, v in abl_ledger["status"].value_counts().sort_index().items()}
        out["rows_changed_by_the_rule"] = int(len(moved))
        out["rows_changed_from_admitted"] = int((moved["status_ablation"] == "admitted").sum())
        out["tests_with_a_changed_row"] = int(moved["test_id"].nunique())
        out["tests_with_an_admitted_row_removed"] = int(moved.loc[moved["status_ablation"] == "admitted", "test_id"].nunique())
        out["admitted_rows"] = {"main": int((ledger["status"] == "admitted").sum()), "ablation": int((abl_ledger["status"] == "admitted").sum())}
    abl_doc = scores_abl = None
    if abl_dir is not None:
        files = visible_glob(abl_dir, f"backtest-{source}-*.json")
        abl_doc = _load(files[0]) if files else None
        sc = visible_glob(abl_dir, f"scores-{source}-*.parquet")
        scores_abl = _scores(sc[0]) if sc else None
    run7_doc = _load(Path(run7_report)) if run7_report else None
    main_scores = _scores(reports_dir / f"scores-{source}-{snapshot_id}.parquet")
    out["headline"] = {
        "main": _agg(main_doc),
        "include_randomization_window": _agg(abl_doc),
        "run7": _agg(run7_doc),
    }
    out["headline_by_cell"] = {
        name: {c: _agg(doc, c, ("P0", "P1", "P2", "text_lr")) for c in ("headline_only", "image_only", "both")}
        for name, doc in (("main", main_doc), ("include_randomization_window", abl_doc), ("run7", run7_doc))
    }

    def hdr(doc):
        if doc is None:
            return None
        h = doc["header"]
        return {
            k: h.get(k)
            for k in (
                "ledger_rows",
                "admitted_rows",
                "scored_rows",
                "not_scored_rows",
                "tests_in_ledger",
                "tests_admitted",
                "tests_scored",
                "origins_scored",
                "first_origin",
                "last_origin",
                "skipped_origins",
            )
        }

    out["counts"] = {"main": hdr(main_doc), "include_randomization_window": hdr(abl_doc), "run7": hdr(run7_doc)}
    if abl_doc is not None and run7_doc is not None:
        out["ablation_vs_run7"] = {"report_leaves": compare_reports(abl_doc, run7_doc)}
        rid_a = None if scores_abl is None else set(scores_abl["row_id"])
        rid_7 = None
        if run7_scores and Path(run7_scores).is_file():
            rid_7 = set(pd.read_parquet(run7_scores, columns=["row_id"])["row_id"])
        if rid_a is not None and rid_7 is not None:
            out["ablation_vs_run7"]["scored_rows"] = {
                "ablation": len(rid_a),
                "run7": len(rid_7),
                "same_row_ids": rid_a == rid_7,
                "only_in_ablation": len(rid_a - rid_7),
                "only_in_run7": len(rid_7 - rid_a),
            }
    if main_scores is not None and scores_abl is not None:
        out["rows_scored_only_in_ablation"] = int(len(set(scores_abl["row_id"]) - set(main_scores["row_id"])))
        out["rows_scored_only_in_main"] = int(len(set(main_scores["row_id"]) - set(scores_abl["row_id"])))
    return out


# --------------------------------------------------------------------------------------------------------------- X2 and X3: ablations
RUN_SETTINGS = {
    "main": "absolute effect at planned precision (the default)",
    "cautionary": "relative lift at realized precision (the first run: both changes)",
    "relative_planned": "relative lift at planned precision (effect scale changed alone)",
    "absolute_realized": "absolute effect at realized precision (s_star changed alone)",
}


def _reversal(rows: dict | None) -> dict | None:
    """P1's AUC for the significance event, pooled and within strata, and whether its interval lies below one half."""
    if not rows or "P1" not in rows:
        return None
    r = rows["P1"]
    below = lambda lo, hi: None if lo is None or hi is None else bool(hi < 0.5)  # noqa: E731
    return {
        "auc_event": r.get("auc_event"),
        "auc_event_below_half": below(r.get("auc_event_lo"), r.get("auc_event_hi")),
        "auc_event_within": r.get("auc_event_within"),
        "auc_event_within_below_half": below(r.get("auc_event_within_lo"), r.get("auc_event_within_hi")),
        "brier_skill": r.get("brier_skill"),
        "brier_skill_below_zero": None if r.get("brier_skill_hi") is None else bool(r["brier_skill_hi"] < 0),
    }


def effect_scale_choices(reports_dir, source: str, snapshot_id: str) -> dict | None:
    """X2. Which of the two choices of the first run (the effect scale and the standard error given to the forecaster) makes P1's ranking reverse."""
    if source != "upworthy":
        return None
    reports_dir = Path(reports_dir)
    files = {
        "main": reports_dir / f"backtest-{source}-{snapshot_id}.json",
        "cautionary": _ablation(reports_dir, source, snapshot_id, "effect-scale-relative+s-star-realized")[0],
        "relative_planned": _ablation(reports_dir, source, snapshot_id, "effect-scale-relative")[0],
        "absolute_realized": _ablation(reports_dir, source, snapshot_id, "s-star-realized")[0],
    }
    runs = {}
    for name, f in files.items():
        doc = _load(f)
        if doc is None:
            runs[name] = None
            continue
        rows = _agg(doc, "ALL", ("P0", "P1", "P2", "text_lr"))
        runs[name] = {
            "setting": RUN_SETTINGS[name],
            "report": f.name,
            "variant": doc["header"].get("variant"),
            "event_rate": (rows.get("P1") or {}).get("event_rate"),
            "rungs": rows,
            "p1_ranking": _reversal(rows),
        }
    if all(v is None for v in runs.values()):
        return None
    reversed_in = [n for n, v in runs.items() if v and v["p1_ranking"] and v["p1_ranking"]["auc_event_below_half"]]
    return {
        "runs": runs,
        "runs_where_p1_auc_interval_is_below_half": reversed_in,
        "units": "the relative runs score the relative lift in percent, so log scores and CRPS are not comparable across effect scales; the AUC, the Brier "
        "skill and the ECE are unitless and are",
        "definition": "reversed means the 90 percent by-test interval of P1's pooled AUC for the significant-positive event lies below 0.5",
    }


EXPOSURE_FIXED_DEFINITIONS = {
    "exposure-cell-median": "every Upworthy row's two arms get the median planned exposure of its cell (admitted rows); y, s and the statuses "
                            "are unchanged",
    "exposure-cell-median-visible": "every Upworthy row's two arms get the median planned exposure of its cell over the admitted rows usable "
                                    "by the start of the row's calendar quarter, so no later row is read; y, s and the statuses are unchanged",
}


def exposure_fixed(reports_dir, source: str, snapshot_id: str, variant: str = "exposure-cell-median") -> dict | None:
    """X3. The main run against the run that sets every row's planned exposure to its cell's median.

    ``variant`` names the ablation report read: ``exposure-cell-median`` (the median over the whole ledger, a diagnostic that reads later
    rows) or ``exposure-cell-median-visible`` (the median over the rows visible at the row's quarter)."""
    if variant not in EXPOSURE_FIXED_DEFINITIONS:
        raise ValueError(f"variant must be one of {sorted(EXPOSURE_FIXED_DEFINITIONS)}")
    if source != "upworthy":
        return None
    reports_dir = Path(reports_dir)
    main_doc = _load(reports_dir / f"backtest-{source}-{snapshot_id}.json")
    jf, sf = _ablation(reports_dir, source, snapshot_id, variant)
    fixed_doc = _load(jf)
    if main_doc is None or fixed_doc is None:
        return None
    rungs = ("P0", "P1", "P2", "text_lr", "GBM", "local_eb")
    out: dict = {
        "definition": EXPOSURE_FIXED_DEFINITIONS[variant],
        "report": jf.name,
        "by_cell": {},
    }
    for cell in ("ALL", "headline_only", "image_only", "both"):
        a, b = _agg(main_doc, cell, rungs), _agg(fixed_doc, cell, rungs)
        if not a or not b:
            continue
        delta = {}
        for r in a:
            if r in b:
                delta[r] = {
                    k: (None if a[r].get(k) is None or b[r].get(k) is None else b[r][k] - a[r][k])
                    for k in ("brier_skill", "logscore", "auc_event", "auc_event_within", "ece", "ece_percentile")
                }
        out["by_cell"][cell] = {"main": a, "fixed": b, "fixed_minus_main": delta}
    sc_main, sc_fixed = _scores(reports_dir / f"scores-{source}-{snapshot_id}.parquet"), _scores(sf)
    const = {}
    for name, sc in (("main", sc_main), ("fixed", sc_fixed)):
        if sc is None:
            const[name] = None
            continue
        const[name] = {}
        for r in ("P1", "P2"):
            g = sc[sc["rung"] == r]
            if g.empty:
                continue
            nun = g.assign(p_sig=g["p_sig"].round(9)).groupby(["origin", "cell"])["p_sig"].nunique(dropna=True)
            const[name][r] = {
                "origin_cell_strata": int(len(nun)),
                "strata_with_one_value": int((nun <= 1).sum()),
                "share_of_strata_with_one_value": float((nun <= 1).mean()),
            }
        if sc is not None:
            ex = sc[sc["rung"] == "P1"].groupby(["origin", "cell"])["exposure"].nunique()
            const[name]["exposure_strata_with_one_value"] = float((ex <= 1).mean())
    out["p_sig_constant_within_origin_and_cell"] = const
    # Forecasts equal to a few units in the last place are ties in fact; the report's AUC breaks them by rounding noise. Here the forecasts are rounded to 9
    # decimals first, so a forecast that is constant within a stratum has AUC one half exactly.
    exact: dict = {}
    for name, sc in (("main", sc_main), ("fixed", sc_fixed)):
        if sc is None or "event" not in sc.columns:
            continue
        exact[name] = {}
        for r in ("P0", "P1", "P2"):
            g = sc[(sc["rung"] == r) & sc["p_sig"].notna()]
            if g.empty:
                continue
            codes, _ = pd.factorize(g["test_id"])
            strata = (g["origin"].astype(str) + "|" + g["cell"].astype(str)).to_numpy()
            exact[name][r] = hs.within_strata(g["p_sig"].round(9).to_numpy(float), g["event"].to_numpy(float), strata, codes, None)[0]
    out["auc_event_within_ties_exact"] = exact
    return out


# --------------------------------------------------------------------------------------------------------------------- X4: prior family
def _fit_loglik(y: np.ndarray, s: np.ndarray, nu_grid) -> dict:
    from mootcourt.predictors.p1 import fit_cell

    f = fit_cell(y, s, nu_grid)
    return {"mu": f["mu"], "tau": f["tau"], "nu": None if math.isinf(f["nu"]) else f["nu"], "loglik": f["loglik"], "n": f["n"]}


def _family_gain(y: np.ndarray, s: np.ndarray, nu_grid=NU_GRID) -> dict:
    t = _fit_loglik(y, s, nu_grid)
    n = _fit_loglik(y, s, (math.inf,))
    return {
        "n": int(len(y)),
        "nu_best": t["nu"],
        "loglik_t": t["loglik"],
        "loglik_normal": n["loglik"],
        "gain_total": t["loglik"] - n["loglik"],
        "gain_per_row": (t["loglik"] - n["loglik"]) / len(y),
    }


def prior_family_scale(ledger: pd.DataFrame, source: str, n_level_bins: int = 3) -> dict | None:
    """X4. Is the Student-t gain over the normal prior a heavy tail of the effects or a mixture of scales over the click-through level?

    A diagnostic on the admitted rows, in sample (maximum marginal likelihood per cell, as P1 fits it, with nu from the same grid). Four fits per cell, all
    scored in one unit (the log density of y in percentage points, so the gains are comparable):

    * ``pp``: effect and standard error in percentage points, t against normal (the gain the paper reports for the t prior);
    * ``relative``: the effect and its standard error divided by the row's reference click-through rate, a prior on the standardized effect; the log density
      moves back to percentage points by the Jacobian, which adds the same constant to both families, so the gain is unchanged;
    * ``level_bins``: normal priors fitted separately within bins of the reference rate (a mixture over the click-through level, with the level observed),
      against the single normal in percentage points; and the t gain that remains inside the bins.

    The reference rate is a post-launch quantity (it comes from the test's own result), which is allowed here because nothing forecasts from it: the
    diagnostic asks what family describes the marginal distribution of concluded tests."""
    if source != "upworthy":
        return None
    adm = ledger[ledger["status"] == "admitted"]
    ctr = np.array([json.loads(j).get("post_launch", {}).get("ctr_ref") for j in adm["features_json"]], dtype=object)
    ok = np.array([c is not None and c > 0 for c in ctr])
    adm, ctr = adm[ok], ctr[ok].astype(float)
    y, s = adm["y"].to_numpy(float), adm["s"].to_numpy(float)
    cells = adm["cell"].to_numpy()

    def block(mask: np.ndarray) -> dict:
        yy, ss, cc = y[mask], s[mask], ctr[mask]
        out = {"rows": int(mask.sum()), "pp": _family_gain(yy, ss), "relative": _family_gain(yy / cc, ss / cc)}
        edges = np.quantile(cc, np.linspace(0, 1, n_level_bins + 1))
        idx = np.clip(np.searchsorted(edges, cc, side="right") - 1, 0, n_level_bins - 1)
        ll_norm_bins = ll_t_bins = 0.0
        bins = []
        for b in range(n_level_bins):
            m = idx == b
            if m.sum() < 30:
                continue
            g = _family_gain(yy[m], ss[m])
            ll_norm_bins += g["loglik_normal"]
            ll_t_bins += g["loglik_t"]
            bins.append({"ctr_lo": float(edges[b]), "ctr_hi": float(edges[b + 1]), **g})
        base = out["pp"]
        out["level_bins"] = {
            "bins": bins,
            "gain_normal_by_level_over_single_normal": ll_norm_bins - base["loglik_normal"],
            "gain_t_within_level_bins_over_normal_within_level_bins": ll_t_bins - ll_norm_bins,
            "gain_t_single_over_single_normal": base["gain_total"],
            "share_of_t_gain_reached_by_normal_by_level": (ll_norm_bins - base["loglik_normal"]) / base["gain_total"]
            if base["gain_total"] > 0
            else None,
        }
        return out

    result = {"ALL": block(np.ones(len(y), bool))}
    for c in sorted(set(cells)):
        if (cells == c).sum() >= 100:
            result[str(c)] = block(cells == c)
    return {
        "by_cell": result,
        "n_level_bins": n_level_bins,
        "nu_grid": [None if math.isinf(v) else v for v in NU_GRID],
        "definition": "gains are maximized marginal log likelihoods of t minus normal, in nats, in sample; see the function docstring",
    }


# ------------------------------------------------------------------------------------------------------------------- X5: captured lift
def _test_frames(scores: pd.DataFrame, rungs) -> list[dict]:
    """Per origin: test values, arms, the exposure-only score and each rung's test score (the largest p_win among its contrasts)."""
    out = []
    for origin, g in scores.groupby("origin", sort=True):
        value = g.groupby("test_id")["y"].max().clip(lower=0.0)
        tests = value.index
        arms = g.groupby("test_id")["row_id"].nunique().reindex(tests).to_numpy(float)
        s_star = g.drop_duplicates("row_id").groupby("test_id")["s_star"].min().reindex(tests).to_numpy(float)
        per = {}
        for r in rungs:
            gr = g[g["rung"] == r]
            if gr.empty or not gr["p_win"].notna().any():
                continue
            per[r] = gr.groupby("test_id")["p_win"].max().reindex(tests).to_numpy(float)
        out.append({"origin": origin, "v": value.to_numpy(float), "arms": arms, "s_star": s_star, "p": per})
    return out


def _captured(score: np.ndarray, v: np.ndarray, frac: float) -> float:
    return dv._top_k_value(score, v, dv.budget_k(len(v), frac))


def ranking_paired(
    scores: pd.DataFrame,
    *,
    rungs=("P0", "P1", "P2", "text_lr", "GBM", "local_eb"),
    comparisons=(("P2", "P1"), ("text_lr", "P1")),
    budgets=dv.BUDGETS,
    B: int = DEFAULT_B,
    seed: int = 0,
    level: float = LEVEL,
) -> dict | None:
    """X5. Captured fraction of each ranking policy and its pairwise differences, resampling whole tests within each origin.

    The policies are the rungs' ``p_win`` (the largest among a test's contrasts), the arm-count policy, the exposure-only policy (tests ranked by the
    smallest planned standard error ``s_star`` among their contrasts, lowest first: it reads no forecast either; ``s_star_desc`` is the opposite order), random
    order (exact) and the oracle.
    Captured fraction is the captured value over the total value of the period, pooled over origins as in the decision-value table. A difference is paired:
    both policies see the same resampled tests. Adjusted bounds use the Bonferroni normal quantile for the family of the listed comparisons at each budget
    (``family_size``). Rows with no ``p_win`` for a rung are left out of that rung only."""
    if scores.empty or "p_win" not in scores.columns or "s_star" not in scores.columns:
        return None
    frames = _test_frames(scores, rungs)
    avail = [r for r in rungs if all(r in f["p"] for f in frames)]
    comps = [(a, b) for a, b in comparisons if a in avail and b in avail]
    extra = [("s_star", "arm_count"), ("s_star_desc", "arm_count")] + [(r, "s_star") for r in avail] + [(r, "s_star_desc") for r in avail]
    extra += [(r, "arm_count") for r in avail]
    rng = np.random.default_rng(seed)
    out: dict = {
        "policies": avail + ["arm_count", "s_star", "s_star_desc", "random", "oracle"],
        "bootstrap_resamples": B,
        "level": level,
        "seed": seed,
        "definition": "captured fraction = value captured by the K highest-ranked tests over the total value of the period (value = the best positive y "
        "among the test's contrasts), pooled over origins; s_star policy ranks tests by the smallest planned standard error of their contrasts (the "
        "most precise tests first, fixed before the run); s_star_desc is the opposite order (the least precise first), added beside it because the direction "
        "of an exposure-only policy was not specified by the plan",
        "budgets": {},
    }
    idx = [rng.integers(0, len(f["v"]), size=(B, len(f["v"]))) for f in frames]  # the same resamples for every policy and budget

    def policy_score(f, name):
        if name == "arm_count":
            return f["arms"]
        if name == "s_star":
            return -f["s_star"]
        if name == "s_star_desc":
            return f["s_star"]
        return np.where(np.isfinite(f["p"][name]), f["p"][name], 0.0)

    names = avail + ["arm_count", "s_star", "s_star_desc"]
    for frac in budgets:
        pt = {n: 0.0 for n in names + ["random", "oracle"]}
        tot = 0.0
        for f in frames:
            for n in names:
                pt[n] += _captured(policy_score(f, n), f["v"], frac)
            pt["oracle"] += _captured(f["v"], f["v"], frac)
            pt["random"] += float(f["v"].sum()) * dv.budget_k(len(f["v"]), frac) / len(f["v"])
            tot += float(f["v"].sum())
        dr = {n: np.zeros(B) for n in names + ["random", "oracle"]}
        dt = np.zeros(B)
        for fi, f in enumerate(frames):
            for b in range(B):
                ib = idx[fi][b]
                v = f["v"][ib]
                k = dv.budget_k(len(v), frac)
                dt[b] += v.sum()
                dr["random"][b] += v.sum() * k / len(v)
                dr["oracle"][b] += dv._top_k_value(v, v, k)
                for n in names:
                    dr[n][b] += dv._top_k_value(policy_score(f, n)[ib], v, k)
        with np.errstate(invalid="ignore", divide="ignore"):
            frac_draws = {n: np.where(dt > 0, d / dt, np.nan) for n, d in dr.items()}
        a = (1.0 - level) / 2.0

        def pack(est, draws):
            d = draws[np.isfinite(draws)]
            lo, hi = (float(x) for x in np.percentile(d, [100 * a, 100 * (1 - a)])) if len(d) > 1 else (None, None)
            return {"estimate": float(est), "lo": lo, "hi": hi, "se": float(np.std(d, ddof=1)) if len(d) > 1 else None}

        row = {"policies": {n: pack(pt[n] / tot, frac_draws[n]) for n in pt}, "total_value": tot, "n_tests": int(sum(len(f["v"]) for f in frames))}
        m = len(comps)
        zq = float(special.ndtri(1.0 - (1.0 - level) / 2.0 / m)) if m else float("nan")
        diffs = {}
        for a_name, b_name in comps + [c for c in extra if c[0] in names and c[1] in names]:
            d = pack(pt[a_name] / tot - pt[b_name] / tot, frac_draws[a_name] - frac_draws[b_name])
            if (a_name, b_name) in comps and d["se"] is not None:
                d["adjusted_lo"], d["adjusted_hi"] = d["estimate"] - zq * d["se"], d["estimate"] + zq * d["se"]
                d["family_size"] = m
            diffs[f"{a_name}_minus_{b_name}"] = d
        row["differences"] = diffs
        out["budgets"][f"{frac:.2f}"] = row
    out["family_size_adjusted_comparisons"] = len(comps)
    out["adjusted_comparisons"] = [f"{a}_minus_{b}" for a, b in comps]
    return out


def positive_control_decision_value(run_dirs, *, B: int = 200, seed: int = 0) -> dict | None:
    """X5, planted ledgers. The decision-value table's pooled rows and the paired differences on each planted-ledger backtest folder."""
    out = {}
    for d in run_dirs:
        d = Path(d)
        sc = visible_glob(d, "scores-synthetic-*.parquet")
        if not sc:
            continue
        scores = pd.read_parquet(sc[0])
        table = dv.decision_value(scores, B=B, seed=seed)
        pooled = table[table["origin"].astype(str) == "ALL"]
        rows = [
            {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v) for k, v in r.items()}
            for r in pooled[
                [
                    "policy",
                    "rung",
                    "budget",
                    "captured_fraction",
                    "captured_fraction_lo",
                    "captured_fraction_hi",
                    "random_fraction",
                    "diff_random",
                    "diff_random_lo",
                    "diff_random_hi",
                    "diff_matched",
                    "diff_matched_lo",
                    "diff_matched_hi",
                ]
            ].to_dict("records")
        ]
        out[d.name] = {
            "scores": sc[0].name,
            "tests": int(scores["test_id"].nunique()),
            "pooled_rows": rows,
            "paired": ranking_paired(scores, B=B, seed=seed, budgets=(0.25,)),
        }
    return out or None


# -------------------------------------------------------------------------------------------------------------------- X6: abstention
def _stratum_sums(g: pd.DataFrame, codes: np.ndarray, n_tests: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.bincount(codes, weights=g["brier_event"].to_numpy(float), minlength=n_tests),
        np.bincount(codes, weights=g["brier_base"].to_numpy(float), minlength=n_tests),
        np.bincount(codes, minlength=n_tests).astype(float),
    )


def abstention_composition(scores: pd.DataFrame, *, rungs=("P1", "P2"), B: int = DEFAULT_B, seed: int = 0, level: float = LEVEL) -> dict | None:
    """X6. Skill on abstained rows against issued rows, without the burn-in origin, pooled and within origin-and-cell strata.

    Abstention is a property of the row shared by every rung. The burn-in is the first scored origin (no reliability report exists yet, so every row
    abstains on it). Pooled skill is ``1 - sum Brier / sum base Brier`` over the group's rows. The two groups have different mixes of cells and origins, and
    the baseline (the trailing-window base rate of the row's cell at its origin) differs with them; so the within-strata read compares the groups inside
    each origin-and-cell stratum, where one baseline serves both: the stratified difference is the mean over strata that hold both groups of
    ``skill(issued) - skill(abstained)``, weighted by ``n_i n_a / (n_i + n_a)``. Intervals resample whole tests."""
    need = {"abstain", "brier_event", "brier_base", "origin", "cell", "test_id", "rung"}
    if not need <= set(scores.columns):
        return None
    first = scores["origin"].min()
    out: dict = {
        "burn_in_origin": pd.Timestamp(first).isoformat(),
        "bootstrap_resamples": B,
        "level": level,
        "definition": "skill = 1 - sum(Brier) / sum(base Brier) of the group's rows; the base rate is the trailing-window rate of the row's cell at its "
        "origin, the same number for every row of a stratum",
    }
    rng = np.random.default_rng(seed)
    a = (1.0 - level) / 2.0
    for rung in rungs:
        g = scores[(scores["rung"] == rung) & (scores["origin"] > first) & scores["brier_event"].notna() & scores["brier_base"].notna()].copy()
        if g.empty:
            continue
        codes, tests = pd.factorize(g["test_id"])
        n_t = len(tests)
        counts = rng.multinomial(n_t, np.full(n_t, 1.0 / n_t), size=B).astype(float)
        g["_c"] = codes
        ab = g["abstain"].to_numpy(bool)
        res: dict = {"rows": int(len(g)), "tests": int(n_t), "abstained_rows": int(ab.sum()), "issued_rows": int((~ab).sum())}

        def skill_block(mask):
            sb, s0, sn = _stratum_sums(g[mask], g.loc[mask, "_c"].to_numpy(), n_t)
            est = 1.0 - sb.sum() / s0.sum() if s0.sum() > 0 else None
            with np.errstate(invalid="ignore", divide="ignore"):
                draws = 1.0 - (counts @ sb) / (counts @ s0)
            d = draws[np.isfinite(draws)]
            lo, hi = (float(x) for x in np.percentile(d, [100 * a, 100 * (1 - a)])) if len(d) > 1 else (None, None)
            return {
                "rows": int(mask.sum()),
                "tests": int((sn > 0).sum()),
                "brier": float(sb.sum() / sn.sum()) if sn.sum() > 0 else None,
                "brier_base": float(s0.sum() / sn.sum()) if sn.sum() > 0 else None,
                "skill": None if est is None else float(est),
                "lo": lo,
                "hi": hi,
            }

        res["issued"], res["abstained"] = skill_block(~ab), skill_block(ab)
        # stratified difference
        strata = (g["origin"].astype(str) + "|" + g["cell"].astype(str)).to_numpy()
        parts = []
        for s_ in pd.unique(strata):
            m = strata == s_
            if (m & ab).any() and (m & ~ab).any():
                si = _stratum_sums(g[m & ~ab], g.loc[m & ~ab, "_c"].to_numpy(), n_t)
                sa = _stratum_sums(g[m & ab], g.loc[m & ab, "_c"].to_numpy(), n_t)
                parts.append((s_, si, sa))

        def strat(cnt: np.ndarray):
            num = np.zeros(cnt.shape[0])
            den = np.zeros(cnt.shape[0])
            for _, (bi, b0i, ni), (ba, b0a, na) in parts:
                n_i, n_a = cnt @ ni, cnt @ na
                with np.errstate(invalid="ignore", divide="ignore"):
                    d = (1.0 - (cnt @ bi) / (cnt @ b0i)) - (1.0 - (cnt @ ba) / (cnt @ b0a))
                w = np.where((n_i > 0) & (n_a > 0), n_i * n_a / np.maximum(n_i + n_a, 1.0), 0.0)
                ok = np.isfinite(d)
                num += np.where(ok, w * np.where(ok, d, 0.0), 0.0)
                den += np.where(ok, w, 0.0)
            with np.errstate(invalid="ignore", divide="ignore"):
                return np.where(den > 0, num / den, np.nan)

        if parts:
            est = float(strat(np.ones((1, n_t)))[0])
            d = strat(counts)
            d = d[np.isfinite(d)]
            lo, hi = (float(x) for x in np.percentile(d, [100 * a, 100 * (1 - a)])) if len(d) > 1 else (None, None)
            res["stratified_issued_minus_abstained_skill"] = {
                "estimate": est,
                "lo": lo,
                "hi": hi,
                "strata_with_both_groups": len(parts),
                "strata_total": int(len(pd.unique(strata))),
            }
            res["pooled_issued_minus_abstained_skill"] = (
                None if res["issued"]["skill"] is None or res["abstained"]["skill"] is None else res["issued"]["skill"] - res["abstained"]["skill"]
            )
        comp = g.assign(_a=ab).groupby("cell")["_a"].agg(["mean", "size"])
        res["abstention_rate_by_cell"] = {str(k): {"rate": float(v["mean"]), "rows": int(v["size"])} for k, v in comp.iterrows()}
        out[rung] = res
    return out if len(out) > 4 else None


# ------------------------------------------------------------------------------------------------------------------------ X7: gates
def stratum_dependence(g: pd.DataFrame) -> dict:
    """Base rate, rows per test and within-test correlation of the significant-positive event of one stratum's rows (one rung), measured as the gates do."""
    ev = g["event"].to_numpy(float)
    base = float(ev.mean())
    rpt = len(g) / g["test_id"].nunique()
    icc = 0.0
    if 0.0 < base < 1.0 and rpt > 1.0:
        icc = float(hs.design_effect(np.full(len(ev), base), ev, g["test_id"].to_numpy())["icc"])
    return {"base_rate": base, "rows_per_test": float(rpt), "icc": icc, "n_rows": int(len(g)), "n_tests": int(g["test_id"].nunique())}


def gates_by_stratum(
    scores: pd.DataFrame,
    gates_doc: dict | None,
    *,
    rungs=("P1", "P2", "GBM", "local_eb", "text_lr"),
    B: int = DEFAULT_B,
    seed: int = 0,
    level: float = LEVEL,
) -> dict | None:
    """X7. Brier skill of each rung in each stratum (cell and pooled) with an interval adjusted within the stratum, and one gate rule for all.

    ``gates_doc`` is the file ``scripts/gates_by_stratum.py`` wrote: for each stratum, the gate sizes simulated at the stratum's OWN base rate, rows per test and
    within-test correlation. The verdict is the same rule for every stratum and rung: the number of tests against the stratum's own ``n_200`` and
    ``n_400`` at the decision target (``hs.gate_status``), with the research screen beside it. The adjusted interval of a rung is its Brier skill plus or
    minus the bootstrap standard error times the Bonferroni normal quantile for the intervals reported in that stratum (``family_size``: the rungs listed)."""
    if gates_doc is None:
        return None
    out: dict = {
        "rule": "decidable_by_tests: tests in the stratum against the stratum's own simulated n_200 and n_400 at the decision target (research screen beside)",
        "gates_file_header": {k: gates_doc.get(k) for k in ("reps", "bootstrap", "seed", "decision_target", "research_target", "interval")},
        "strata": {},
    }
    for cell, entry in gates_doc.get("strata", {}).items():
        sub = scores if cell == "ALL" else scores[scores["cell"] == cell]
        rows = {}
        draws = {}
        for r in rungs:
            g = sub[(sub["rung"] == r) & sub["brier_event"].notna()]
            if g.empty:
                continue
            dr = hs.brier_skill_draws(g, B=B, seed=seed)
            sk = 1.0 - g["brier_event"].sum() / g["brier_base"].sum()
            rows[r] = {
                "rows": int(len(g)),
                "tests": int(g["test_id"].nunique()),
                "brier_skill": float(sk),
                "lo": float(np.nanpercentile(dr, 100 * (1 - level) / 2)),
                "hi": float(np.nanpercentile(dr, 100 * (1 - (1 - level) / 2))),
                "se": float(np.nanstd(dr, ddof=1)),
            }
            draws[r] = dr
        m = len(rows)
        zq = float(special.ndtri(1.0 - (1.0 - level) / 2.0 / m)) if m else float("nan")
        n_tests = int(sub["test_id"].nunique())
        own = {"n_200": entry["n_200"], "n_400": entry["n_400"], "by_target": entry.get("by_target")}
        status = hs.gate_status(n_tests, own)
        for v in rows.values():
            v["adjusted_lo"], v["adjusted_hi"], v["family_size"] = v["brier_skill"] - zq * v["se"], v["brier_skill"] + zq * v["se"], m
            v["verdict"] = status["label"]
            v["verdict_research"] = status["label_research"]
        out["strata"][cell] = {
            "tests": n_tests,
            "dependence": entry.get("dependence"),
            "own_gate": own,
            "verdict": status["label"],
            "verdict_research": status["label_research"],
            "family_size": m,
            "rungs": rows,
        }
    return out


# ----------------------------------------------------------------------------------------------------------------------------- X8: null
def ece_null_drift(p, q, draws: int = hs.NULL_DRAWS, seed: int = 0, n_bins: int = 10, test_ids=None, icc: float = 0.0) -> np.ndarray:
    """ECE of the forecasts ``p`` against ``draws`` outcome sets drawn from the probabilities ``q`` (the trailing-window event rates).

    Same construction as ``harness_stats.ece_null`` (a one-factor Gaussian copula for the dependence within a test, ``icc`` the latent correlation), with the
    probabilities that generate the outcomes ``q`` and the bins fixed by the forecasts ``p``. With ``q = p`` it is that function."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    if p.shape != q.shape or p.size == 0 or not (np.all(np.isfinite(p)) and np.all(np.isfinite(q))) or q.min() < 0 or q.max() > 1:
        raise ValueError("p and q must be probabilities of one shape")
    rng = np.random.default_rng(seed)
    idx = hs._bin_index(p, n_bins)
    sp = np.bincount(idx, weights=p, minlength=n_bins)
    out = np.empty(draws)
    clustered = test_ids is not None and icc > 0.0
    if clustered:
        codes, uniq = pd.factorize(pd.Series(np.asarray(test_ids)))
        thr = special.ndtri(np.clip(q, 1e-12, 1.0 - 1e-12))
        a, b = np.sqrt(icc), np.sqrt(1.0 - icc)
    for a0 in range(0, draws, 100):
        m = min(100, draws - a0)
        if clustered:
            z = a * rng.standard_normal((m, len(uniq)))[:, codes] + b * rng.standard_normal((m, p.size))
            e = (z < thr[None, :]).astype(np.float64)
        else:
            e = (rng.random((m, p.size)) < q[None, :]).astype(np.float64)
        se = np.stack([np.bincount(idx, weights=row, minlength=n_bins) for row in e])
        out[a0 : a0 + m] = np.abs(sp[None, :] - se).sum(axis=1) / p.size
    return out


def drift_matched_null(scores: pd.DataFrame, *, rungs=("P0", "P1", "P2"), draws: int = hs.NULL_DRAWS, seed: int = 0) -> dict | None:
    """X8. The ECE of each rung in the current null (outcomes drawn from the rung's own forecasts) and in a null whose event rates follow the trailing window.

    ``p_base`` is the share of events among the visible rows of the row's cell at its origin: the event rate the world had in the window just before the test.
    In the drift-matched null the outcomes are drawn with probability ``p_base`` (clustered by test with the latent correlation that gives the design effect of
    the observed outcomes about ``p_base``), and the rung's forecasts are scored against them in the same bins. A rung whose observed ECE lies inside that
    null is as well calibrated as the world's own drift allows; one above it is not. Pooled over rows and at each origin. The current-null percentile
    reproduces the report's ``ece_percentile`` (same draws and seed)."""
    need = {"p_sig", "event", "p_base", "test_id", "rung", "origin"}
    if not need <= set(scores.columns):
        return None
    out: dict = {
        "draws": draws,
        "seed": seed,
        "definition": "drift-matched null: outcomes drawn with probability p_base (the trailing-window event rate of the row's cell at its origin), clustered "
        "by test; current null: outcomes drawn with the rung's own forecasts, clustered at the observed design effect (the report's null)",
        "rungs": {},
    }
    for rung in rungs:
        g = scores[(scores["rung"] == rung) & scores["p_sig"].notna() & scores["p_base"].notna()]
        if g.empty:
            continue

        def one(h: pd.DataFrame) -> dict:
            p, q, e, t = h["p_sig"].to_numpy(float), h["p_base"].to_numpy(float), h["event"].to_numpy(float), h["test_id"].to_numpy()
            obs = hs.ece(p, e)
            de = hs.design_effect(p, e, t)
            rho = hs.latent_rho_for_design_effect(p, t, de["design_effect"], seed=seed)
            cur = hs.ece_null(p, draws, seed, test_ids=t, icc=rho)
            de_q = hs.design_effect(q, e, t)
            rho_q = hs.latent_rho_for_design_effect(q, t, de_q["design_effect"], seed=seed)
            dr = ece_null_drift(p, q, draws, seed, test_ids=t, icc=rho_q)
            lo, hi = (float(x) for x in np.percentile(dr, [5, 95]))
            return {
                "rows": int(len(h)),
                "tests": int(len(set(t))),
                "ece": float(obs),
                "mean_forecast": float(p.mean()),
                "mean_p_base": float(q.mean()),
                "event_rate": float(e.mean()),
                "current_null": {"percentile": hs.null_percentile(cur, obs), "mean": float(cur.mean()), "design_effect": de["design_effect"]},
                "drift_matched_null": {
                    "percentile": hs.null_percentile(dr, obs),
                    "mean": float(dr.mean()),
                    "p5": lo,
                    "p95": hi,
                    "design_effect": de_q["design_effect"],
                    "ece_inside_central_90": bool(lo <= obs <= hi),
                },
            }

        pooled = one(g)
        by_origin = {pd.Timestamp(o).isoformat(): one(h) for o, h in g.groupby("origin", sort=True) if len(h) >= 50 and 0 < h["event"].mean() < 1}
        out["rungs"][rung] = {"pooled": pooled, "by_origin": by_origin}
    return out if out["rungs"] else None


# ------------------------------------------------------------------------------------------------------------------------------ X9
def _ci(draws: np.ndarray, level: float = LEVEL):
    d = draws[np.isfinite(draws)]
    if len(d) < 2:
        return None, None
    return tuple(float(x) for x in np.percentile(d, [100 * (1 - level) / 2, 100 * (1 - (1 - level) / 2)]))


def within_origin_auc_by_year(scores: pd.DataFrame, *, rungs=("P0", "P1", "P2", "text_lr"), B: int = DEFAULT_B, seed: int = 0) -> dict | None:
    """X9. AUC of ``p_sig`` for the significant-positive event inside origins, by calendar year of the origin, and inside origin-and-cell strata.

    Inside an origin the base-rate movement between origins cannot credit a rung (a forecast constant within the origin has AUC one half). The figure of a
    group is the mean over its strata weighted by their rows (``harness_stats.within_strata``); intervals resample whole tests."""
    need = {"p_sig", "event", "origin", "cell", "test_id", "rung"}
    if not need <= set(scores.columns):
        return None
    out: dict = {"bootstrap_resamples": B, "years": {}}
    years = pd.to_datetime(scores["origin"], utc=True).dt.year
    for rung in rungs:
        g_all = scores[scores["rung"] == rung]
        if g_all.empty:
            continue
        for label, mask in [("ALL", np.ones(len(g_all), bool))] + [(str(y), (years[g_all.index] == y).to_numpy()) for y in sorted(years.unique())]:
            g = g_all[mask]
            if g.empty or g["event"].nunique() < 2:
                continue
            codes, tests = pd.factorize(g["test_id"])
            rng = np.random.default_rng(seed)
            counts = rng.multinomial(len(tests), np.full(len(tests), 1.0 / len(tests)), size=B).astype(float)
            p, e = g["p_sig"].to_numpy(float), g["event"].to_numpy(float)
            row: dict = {"rows": int(len(g)), "tests": int(len(tests)), "event_rate": float(e.mean())}
            for name, strata in (
                ("origin", g["origin"].astype(str).to_numpy()),
                ("origin_and_cell", (g["origin"].astype(str) + "|" + g["cell"].astype(str)).to_numpy()),
            ):
                auc, lo, hi, *_ = hs.within_strata(p, e, strata, codes, counts)
                row[f"auc_within_{name}"] = {"estimate": auc, "lo": lo, "hi": hi}
            pooled, plo, phi = hs.auc_by_test(p, e, codes, counts)
            row["auc_pooled"] = {"estimate": pooled, "lo": plo, "hi": phi}
            if "brier_event" in g.columns and "brier_base" in g.columns:
                b, b0 = g["brier_event"].to_numpy(float), g["brier_base"].to_numpy(float)
                ok = np.isfinite(b) & np.isfinite(b0)
                row["brier_skill"] = float(1.0 - b[ok].sum() / b0[ok].sum()) if ok.any() and b0[ok].sum() > 0 else None
            out["years"].setdefault(label, {})[rung] = row
    return out if out["years"] else None


def lowest_reliability_bin(scores: pd.DataFrame, *, rungs=("P0", "P1", "P2"), n_bins: int = 10, B: int = DEFAULT_B, seed: int = 0) -> dict | None:
    """X9. The lowest populated bin of the equal-width reliability table: rows, mean forecast, observed frequency and the gap with a by-test interval."""
    if not {"p_sig", "event", "test_id", "rung"} <= set(scores.columns):
        return None
    out: dict = {"n_bins": n_bins, "bootstrap_resamples": B, "rungs": {}}
    for rung in rungs:
        g = scores[(scores["rung"] == rung) & scores["p_sig"].notna()]
        if g.empty:
            continue
        p, e = g["p_sig"].to_numpy(float), g["event"].to_numpy(float)
        idx = hs._bin_index(p, n_bins)
        table = hs.reliability_bins(p, e, n_bins)
        k = int(table.loc[table["n"] > 0, "bin"].min())
        m = idx == k
        sub = g[m]
        codes, tests = pd.factorize(sub["test_id"])
        rng = np.random.default_rng(seed)
        counts = rng.multinomial(len(tests), np.full(len(tests), 1.0 / len(tests)), size=B).astype(float)
        pe = np.bincount(codes, weights=sub["event"].to_numpy(float), minlength=len(tests))
        pp = np.bincount(codes, weights=sub["p_sig"].to_numpy(float), minlength=len(tests))
        nn = np.bincount(codes, minlength=len(tests)).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            gap = (counts @ pe - counts @ pp) / (counts @ nn)
        lo, hi = _ci(gap)
        out["rungs"][rung] = {
            "bin": k,
            "lo_edge": k / n_bins,
            "hi_edge": (k + 1) / n_bins,
            "rows": int(m.sum()),
            "tests": int(len(tests)),
            "share_of_rows": float(m.mean()),
            "mean_forecast": float(p[m].mean()),
            "observed_frequency": float(e[m].mean()),
            "gap_observed_minus_forecast": float(e[m].mean() - p[m].mean()),
            "gap_lo": lo,
            "gap_hi": hi,
            "by_origin": {
                pd.Timestamp(o).isoformat(): {
                    "rows": int(len(h)),
                    "mean_forecast": float(h["p_sig"].mean()),
                    "observed_frequency": float(h["event"].mean()),
                }
                for o, h in sub.groupby("origin", sort=True)
            },
        }
    return out if out["rungs"] else None


# ---------------------------------------------------------------------------------------------------------------------------------------------- X8b
def logit_shift_to_mean(p, target: float, tol: float = 1e-10) -> tuple[np.ndarray, float]:
    """``p`` shifted on the logit scale by the one constant that makes its mean equal ``target`` (bisection); returns the shifted forecasts and the shift."""
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    z = special.logit(p)
    lo, hi = -20.0, 20.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if special.expit(z + mid).mean() < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    c = 0.5 * (lo + hi)
    return special.expit(z + c), float(c)


def calibration_within_period(
    scores: pd.DataFrame, *, rungs=("P0", "P1", "P2"), draws: int = hs.NULL_DRAWS, seed: int = 0, min_rows: int = 50
) -> dict | None:
    """X8b. Calibration after removing the level error of each origin-and-cell stratum.

    X8 (``drift_matched_null``) draws outcomes at the trailing base rate; it does not say whether a rung's departure from calibration comes from the event
    rate moving. This diagnostic does: each row's forecast is shifted on the logit scale by the single constant per origin-and-cell stratum that makes the mean
    forecast equal the realized event rate there (an oracle level correction, so a diagnostic and not a forecast). ECE with the same bins is computed before
    and after, the after value is placed in a null that draws outcomes from the shifted forecasts, clustered at the design effect measured for the shifted
    forecasts (500 draws, the seed rule of the current null), and the share of ECE removed is reported, pooled and by cell. A stratum with fewer than
    ``min_rows`` rows, or with no events or only events, is not shifted and is listed. Level error is what the shift removes; what remains is shape."""
    need = {"p_sig", "event", "test_id", "rung", "origin", "cell"}
    if not need <= set(scores.columns):
        return None
    out: dict = {
        "draws": draws,
        "seed": seed,
        "min_rows": min_rows,
        "rungs": {},
        "definition": "per origin-and-cell stratum, forecasts shifted on the logit scale so their mean equals the realized event rate (oracle level "
        "correction, a diagnostic); ECE before and after in the same 10 equal-width bins; null for the after value draws outcomes "
        "from the shifted forecasts, clustered at their measured design effect; added after X8's result was seen",
    }
    for rung in rungs:
        g = scores[(scores["rung"] == rung) & scores["p_sig"].notna()].reset_index(drop=True)
        if g.empty:
            continue
        g["p_shift"] = g["p_sig"].to_numpy(float)
        unshifted = []
        shifts = []
        for (o, c), h in g.groupby(["origin", "cell"], sort=True):
            e = h["event"].to_numpy(float)
            if len(h) < min_rows or e.min() == e.max():
                unshifted.append({"origin": pd.Timestamp(o).isoformat(), "cell": str(c), "rows": int(len(h))})
                continue
            ps, sh = logit_shift_to_mean(h["p_sig"].to_numpy(float), float(e.mean()))
            g.loc[h.index, "p_shift"] = ps
            shifts.append(sh)

        def one(h: pd.DataFrame) -> dict:
            p, ps, e, t = h["p_sig"].to_numpy(float), h["p_shift"].to_numpy(float), h["event"].to_numpy(float), h["test_id"].to_numpy()
            before, after = hs.ece(p, e), hs.ece(ps, e)
            de = hs.design_effect(ps, e, t)
            rho = hs.latent_rho_for_design_effect(ps, t, de["design_effect"], seed=seed)
            null = hs.ece_null(ps, draws, seed, test_ids=t, icc=rho)
            return {
                "rows": int(len(h)),
                "tests": int(len(set(t))),
                "ece_before": float(before),
                "ece_after": float(after),
                "share_of_ece_removed": float(1.0 - after / before) if before > 0 else None,
                "after_percentile_in_null": hs.null_percentile(null, after),
                "null_mean": float(null.mean()),
                "design_effect_after": de["design_effect"],
            }

        res = {"ALL": one(g)}
        for c, h in g.groupby("cell"):
            if len(h) >= min_rows and h["event"].nunique() == 2:
                res[str(c)] = one(h)
        out["rungs"][rung] = {
            "by_stratum_group": res,
            "unshifted_strata": unshifted,
            "strata_shifted": len(shifts),
            "shift_logit_median": float(np.median(shifts)) if shifts else None,
            "shift_logit_range": [float(min(shifts)), float(max(shifts))] if shifts else None,
        }
    return out if out["rungs"] else None
