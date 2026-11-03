"""Backtest report writer: JSON first, Markdown rendered from the JSON, figures, reliability seed.

``write_report`` builds one JSON document from the score table (header, notes, tables), writes it, renders the
Markdown from that same document with ``render_markdown`` and draws four PNG figures with the Agg backend.
Because the Markdown is a function of the JSON, every number it prints can be found in the JSON. Floats are
printed with four decimals everywhere.

Header: source, ledger snapshot id, model id, feature hash, command line, seed, the gate sizes used and, for
the synthetic source only, the label ``synthetic``. The boundary sentence is in every header exactly as spec
section 1 gives it, and the circularity note states that scores are against the observed estimate with known
standard error.

Units: as in ``harness_stats``. Output files: ``backtest-<source>-<snapshot_id>.md`` and ``.json``,
``scores-<source>-<snapshot_id>.parquet`` (the per-row table), ``figures/<name>-<source>.png`` and, when
missing or older, ``reliability-<source>.json``.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mootcourt import harness_stats as hs  # noqa: E402
from mootcourt.config import BOUNDARY_SENTENCE, BY_ORIGIN_RESAMPLES  # noqa: E402
from mootcourt.decision_value import decision_value  # noqa: E402
from mootcourt.harness import BURN_IN_NOTE, MIN_FIT_ROWS  # noqa: E402
from mootcourt.reliability import build_reliability  # noqa: E402

SYNTHETIC = "synthetic"
P0_SKILL_NOTE = (
    "P0 is the empirical base-rate forecaster: its significant-positive probability is the visible event rate of its cell, the same "
    "quantity the Brier skill is measured against, so its Brier skill is zero by construction and its calibration is a real out-of-time "
    "check of the base rate. A rung's Brier skill is always against that cell base rate, never against another rung."
)
INTERVAL_NOTE = (
    "Three interval conventions are used. Every score interval is a 90 percent percentile bootstrap that resamples whole tests. "
    "The ECE percentile is read in a perfect-calibration null whose outcomes are drawn by test (contrasts of one test move together, "
    "with the within-test correlation estimated from the rows); 500 draws resolve percentiles up to 99.8, so 100 means above every draw. "
    "The gate simulation bootstraps by test and uses a 90 percent interval. Columns named adjusted_lo and adjusted_hi, and those ending "
    "in _adjusted_lo and _adjusted_hi, are Bonferroni-adjusted bounds for the family of intervals the table shows (the bootstrap "
    "standard error times the Bonferroni normal quantile); the per-cell and per-year intervals are descriptive."
)
CALIBRATION_NOTE = (
    "design_effect is the variance of the total residual with whole tests as the units over its independent-rows value; icc is the "
    "within-test correlation of the standardized residuals it implies and drives the clustered null. ece_percentile_independent is the "
    "percentile in the earlier null that draws every row independently, kept for comparison."
)
DECISION_NOTE = (
    "Random order captures K over n of the total by linearity, so it is exact, not a draw. A rung whose p_win is constant within a cell "
    "chooses by cell and then at random; its capture differs from random order only through between-cell differences. Intervals "
    "resample whole tests within each origin."
)
MIN_BIN_N = 10          # bins with fewer rows are in the tables but not drawn
DECISION_BOOTSTRAP = 500
FIGURE_NAMES = ("reliability", "score_by_origin", "coverage", "decision_value")
RUNG_NOTES = {
    "P0": "empirical base-rate forecaster of the visible ledger per cell: p_sig is the visible event rate, so its Brier skill is zero "
          "by construction",
    "P1": "empirical-Bayes prior per cell, pooled over kind of change and period",
    "P2": "weighted precedents (kernel regression on headline features) shrunk toward P1",
    "P3": "the team's own forecast, where the source has one",
    "GBM": "gradient-boosted challenger on the same features, precision weighted with a time-ordered search, spread from out-of-fold residuals",
    "local_eb": "challenger: empirical-Bayes prior fit on the k nearest visible rows in feature space, no shrinkage to the cell prior",
    "text_lr": "challenger: TF-IDF and logistic regression on the headline text (the difference of the two headlines where present), "
               "probabilities used directly (no density)",
    "GBM+cal": "the GBM's p_sig through a Platt map fit on out-of-fold predictions of the visible rows only; probabilities only",
    "local_eb+cal": "local_eb's p_sig through a Platt map fit on out-of-fold predictions of the visible rows only; probabilities only",
    "text_lr+cal": "text_lr's p_sig through a Platt map fit on out-of-fold predictions of the visible rows only; probabilities only",
    "always_reference": "direction baseline: the reference arm wins (creation-order effect); direction accuracy only",
    "always_variant": "direction baseline: the variant wins; direction accuracy only",
    "agent": "an outside agent's recorded probability that the test ends significant and positive; probabilities only",
    "P2+agent": "p_sig of P2 stacked with the agent at the weight in force; probabilities only",
}
CHALLENGER_RUNGS = ("GBM", "local_eb", "text_lr", "GBM+cal", "local_eb+cal", "text_lr+cal")
BASELINE_RUNGS = ("always_reference", "always_variant")
SECOND_OPINION_RUNGS = ("agent", "P2+agent")


def rung_kind(rung: str) -> str:
    """Which family a rung belongs to: the ladder, a challenger, a direction baseline or a second opinion."""
    if rung in CHALLENGER_RUNGS:
        return "challenger"
    if rung in BASELINE_RUNGS:
        return "baseline"
    if rung in SECOND_OPINION_RUNGS:
        return "second_opinion"
    return "ladder"


def selection_by_cell(selections: list[dict]) -> list[dict]:
    """Per rung and cell: how often and how strongly the precedents were used, summarised over origins."""
    if not selections:
        return []
    df = pd.DataFrame(selections)
    out = []
    for (rung, cell), g in df.groupby(["rung", "cell"], sort=True):
        hl = g["half_life_days"]
        out.append({"rung": rung, "cell": cell, "selection": g["selection"].iloc[0], "origins": int(len(g)),
                    "lambda_mean": float(g["lambda"].mean()), "lambda_min": float(g["lambda"].min()), "lambda_max": float(g["lambda"].max()),
                    "share_lambda_zero": float((g["lambda"] == 0).mean()), "bandwidth_mult_mean": float(g["bandwidth_mult"].mean()),
                    "half_life_days_median": None if hl.isna().all() else float(hl.median()), "share_no_decay": float(hl.isna().mean()),
                    **_guard_summary(g)})
    return out


def _guard_summary(g: pd.DataFrame) -> dict:
    """Admission-guard fields of one rung and cell over origins (None when the records carry none, as in reports before the guard)."""
    if "guard_held" not in g.columns or g["guard_held"].isna().all():
        return {"guard": None, "share_guard_held": None, "lambda_unguarded_mean": None, "gain_mean": None, "gain_se_mean": None}
    guard = g["guard"].iloc[0]
    return {"guard": None if pd.isna(guard) else float(guard), "share_guard_held": float(g["guard_held"].astype(float).mean()),
            "lambda_unguarded_mean": float(g["lambda_unguarded"].mean()), "gain_mean": float(g["gain"].mean()),
            "gain_se_mean": float(g["gain_se"].mean())}


@dataclass
class ReportPaths:
    """Files written by ``write_report``."""

    md: Path
    json: Path
    scores: Path
    figures: dict[str, Path] = field(default_factory=dict)
    reliability: Path | None = None


# ---------------------------------------------------------------- cleaning
def clean(obj):
    """JSON-safe copy: numpy to python, NaN and infinity to None, timestamps to ISO strings."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return clean(obj.to_dict(orient="records"))
    if isinstance(obj, (pd.Timestamp, dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if math.isfinite(f) else None
    return obj


def _records(df: pd.DataFrame) -> list[dict]:
    return clean(df)


# ------------------------------------------------------------------- doc
def _is_synthetic(ledger: pd.DataFrame, source: str) -> bool:
    return source == SYNTHETIC or (len(ledger) > 0 and bool((ledger["source"] == SYNTHETIC).all()))


def _second_opinion_table(scores: pd.DataFrame, meta: dict, gates: dict, B: int, seed: int) -> list[dict]:
    """Scores of the base rung, the agent rung and the stacked rung on all, contaminated and clean origins."""
    from mootcourt.simulators.scoring import AGENT_RUNG, STACK_RUNG, clean_mask

    rungs = [meta["base_rung"], AGENT_RUNG, STACK_RUNG]
    sub = scores[scores["rung"].isin(rungs)]
    # The agent rung keeps only rows with an opinion, so the base rung is also shown on exactly those rows.
    agent_ids = set(sub.loc[sub["rung"] == AGENT_RUNG, "row_id"])
    same_rows = sub[(sub["rung"] == meta["base_rung"]) & sub["row_id"].isin(agent_ids)].assign(rung=f"{meta['base_rung']} on agent rows")
    sub = pd.concat([sub, same_rows], ignore_index=True) if len(same_rows) else sub
    clean_rows = clean_mask(sub["origin"], meta.get("knowledge_cutoff"), bool(meta.get("cutoff_unknown", False)))
    out = []
    for label, mask in (("all", np.ones(len(sub), bool)), ("contaminated", ~clean_rows), ("clean", clean_rows)):
        part = sub[mask]
        if part.empty:
            continue
        agg = hs.aggregate_scores(part, gates, B=min(B, BY_ORIGIN_RESAMPLES), seed=seed)
        for r in agg[agg["cell"] == "ALL"].to_dict(orient="records"):
            out.append({"origins": label, **{k: r.get(k) for k in ("rung", "n", "n_tests", "brier", "brier_lo", "brier_hi", "brier_base",
                                                                    "brier_skill", "brier_skill_lo", "brier_skill_hi", "ece",
                                                                    "direction_accuracy", "decidable", "decidable_by_tests")}})
    return out


def build_document(scores: pd.DataFrame, *, ledger: pd.DataFrame, source: str, snapshot_id: str, model_id: str, feature_hash: str,
                   command: str, seed: int, gates: dict, B: int = hs.DEFAULT_B, second_opinion: dict | None = None,
                   extra_notes: dict | None = None, variant: dict | None = None, primary_metric: str | None = None,
                   reference_scores: pd.DataFrame | None = None, reference_files: dict | None = None) -> dict:
    """The report as a JSON-ready dict (see the module docstring).

    A ledger with several metrics per experiment (``scores`` has a ``metric`` column with two or more values) gets one block per metric
    under ``tables.by_metric``, each scored separately; the decision value uses the primary metric only (``primary_metric``, default
    the metric with the most scored rows). A single-metric source gets exactly the report it always had.

    ``reference_scores`` is the score table of the main run on the same snapshot, given for a trigger-removal run (``--drop-trigger``): the
    report then also holds ``tables.released_rows``, the scores of the rows the main run abstained on and this run issues. It adds a table
    and changes no other. ``reference_files`` (``main_report`` and ``main_scores`` file names) is recorded in the header.
    """
    agg = hs.aggregate_scores(scores, gates, B=B, seed=seed)
    agg.insert(2, "kind", agg["rung"].map(rung_kind))
    primary = next((r for r in ("P2", "P1", "P0") if (scores["rung"] == r).any()), sorted(scores["rung"].unique())[-1])
    metrics = sorted(m for m in scores["metric"].dropna().unique() if m) if "metric" in scores.columns else []
    multi = len(metrics) >= 2
    by_metric, pm = [], None
    if multi:
        counts = scores[scores["rung"] == primary]["metric"].value_counts()
        pm = primary_metric or sorted(counts.index, key=lambda m: (-counts[m], m))[0]
        if pm not in metrics:
            raise ValueError(f"primary metric {pm!r} is not among the scored metrics {metrics}")
        for m in metrics:
            part = scores[scores["metric"] == m]
            a = hs.aggregate_scores(part, gates, B=min(B, hs.DEFAULT_B), seed=seed)
            a.insert(2, "kind", a["rung"].map(rung_kind))
            by_metric.append({"metric": m, "primary": m == pm, "n_rows": int(part.loc[part["rung"] == primary, "row_id"].nunique()),
                              "aggregate": a})
    dv = decision_value(scores[scores["metric"] == pm] if multi else scores, ledger, seed=seed, B=min(B, DECISION_BOOTSTRAP))
    first = scores["origin"].min()
    by_origin = scores[scores["rung"] == primary].groupby("origin").agg(
        n_scored=("row_id", "size"), n_tests=("test_id", "nunique"), abstention_rate=("abstain", "mean"),
        logscore=("logscore", "mean")).reset_index()
    by_origin["burn_in"] = by_origin["origin"] == first
    stats_by_origin = hs.by_origin(scores, "logscore", B=min(B, BY_ORIGIN_RESAMPLES), seed=seed)
    bins = []
    for rung in sorted(scores["rung"].unique()):
        g = scores[(scores["rung"] == rung) & scores["p_sig"].notna()]
        if g.empty:
            continue
        t = hs.reliability_bins(g["p_sig"], g["event"])
        t.insert(0, "rung", rung)
        bins.append(t)
    adm = ledger.loc[ledger["status"] == "admitted"]
    header = {
        "source": source, "snapshot_id": snapshot_id, "model_id": model_id, "feature_hash": feature_hash, "command": command,
        "seed": int(seed), "bootstrap_resamples": int(B), "gate_n_200": int(gates["n_200"]), "gate_n_400": int(gates["n_400"]),
        "gate_decision_target": gates.get("decision_target"), "gate_by_target": gates.get("by_target"),
        "boundary": BOUNDARY_SENTENCE, "synthetic": _is_synthetic(ledger, source), "primary_rung": primary,
        "rungs": sorted(scores["rung"].unique()),
        "challengers": [r for r in sorted(scores["rung"].unique()) if rung_kind(r) == "challenger"],
        "direction_baselines": [r for r in sorted(scores["rung"].unique()) if rung_kind(r) == "baseline"],
        "origins_scored": int(scores["origin"].nunique()), "first_origin": first, "last_origin": scores["origin"].max(),
        "skipped_origins": list(scores.attrs.get("skipped_origins", [])), "min_fit_rows": MIN_FIT_ROWS,
        "ledger_rows": int(len(ledger)), "admitted_rows": int(len(adm)),
        "scored_rows": int(scores.loc[scores["rung"] == primary, "row_id"].nunique()),
    }
    header["not_scored_rows"] = header["admitted_rows"] - header["scored_rows"]
    header.update(test_counts(ledger, scores, primary))
    header["p2_guard"] = guard_setting(scores)
    if gates.get("by_base_rate"):
        header["gate_base_rates"] = sorted(gates["by_base_rate"])
        header["gate_by_base_rate"] = {f"{b:.2f}": {"n_200": v["n_200"], "n_400": v["n_400"]} for b, v in sorted(gates["by_base_rate"].items())}
    if gates.get("interval"):
        header["gate_interval"] = gates["interval"]
    if multi:
        header["metrics"], header["primary_metric"] = metrics, pm
    if variant:
        header["variant"] = variant
    notes = {"circularity": hs.CIRCULARITY_NOTE, "burn_in": BURN_IN_NOTE, "abstention_triggers": hs.abstention_trigger_note(scores),
             "rungs": {r: RUNG_NOTES.get(r, "") for r in header["rungs"]}, "p0_skill": P0_SKILL_NOTE, "intervals": INTERVAL_NOTE,
             "calibration_null": CALIBRATION_NOTE, "decision_value": DECISION_NOTE}
    so_table = None
    if second_opinion:
        from mootcourt.simulators.scoring import CONTAMINATION_SENTENCE

        header["second_opinion"] = second_opinion
        notes["second_opinion"] = CONTAMINATION_SENTENCE
        so_table = _second_opinion_table(scores, second_opinion, gates, B, seed)
    released = None
    if reference_scores is not None and primary in set(reference_scores["rung"]):
        released = hs.released_rows(reference_scores, scores, gates, B=B, seed=seed, rung=primary)
        header["released_rows_reference"] = dict(reference_files or {})
        notes["released_rows"] = ("Rows released by the dropped trigger: abstained in the main run and issued in this run. Their scores are "
                                  "this run's scores, which equal the main run's (abstention does not change a score).")
    notes.update(extra_notes or {})
    return clean({
        "header": header,
        "notes": notes,
        "tables": {
            "aggregate": agg, **({"by_metric": by_metric} if multi else {}), "decision_value": dv,
            "abstention": hs.abstention_summary(scores), "origins": by_origin,
            "score_by_origin": stats_by_origin, "score_by_year": hs.by_year(scores, row_years(scores, ledger), gates, B=B, seed=seed),
            "reliability_bins": pd.concat(bins, ignore_index=True),
            "coverage": hs.coverage_by_cell(scores[scores["rung"] == primary]),
            "calibration_by_precision": hs.calibration_by_precision(scores),
            "coverage_by_se_ratio": hs.coverage_by_se_ratio(scores),
            "split_half": [{"cell": c, **v} for c, v in _split_half(ledger, scores["origin"].max()).items()],
            "p2_selection": pd.DataFrame(scores.attrs.get("selections") or []),
            "p2_selection_by_cell": selection_by_cell(scores.attrs.get("selections") or []),
            **({"second_opinion": so_table} if so_table is not None else {}),
            **({"released_rows": released} if released is not None else {}),
        },
    })


def guard_setting(scores: pd.DataFrame):
    """The P2 admission guard multiplier the run used (a number), or ``"off"``; None when no P2 selection was recorded."""
    recs = scores.attrs.get("selections") or []
    for r in recs:
        if r.get("rung") == "P2":
            g = r.get("guard")
            return "off" if g is None or (isinstance(g, float) and math.isnan(g)) else float(g)
    return None


TEST_COUNT_DEFINITION = (
    "Tests in the ledger are the distinct test ids of every row of the source whatever its status. Tests admitted are the distinct test "
    "ids with at least one admitted contrast. Tests scored are the admitted tests with at least one contrast scored by the primary rung. "
    "The difference between admitted and scored is the contrasts of the first quarters, before the first origin with enough visible rows "
    "to fit (they are history only), plus any test whose contrasts all fall there."
)


def test_counts(ledger: pd.DataFrame, scores: pd.DataFrame, primary: str) -> dict:
    """Tests in the ledger, admitted and scored, with the definition of each (the header states why the counts differ)."""
    adm = ledger.loc[ledger["status"] == "admitted"]
    scored = scores.loc[scores["rung"] == primary]
    return {"tests_in_ledger": int(ledger["test_id"].nunique()), "tests_admitted": int(adm["test_id"].nunique()),
            "tests_scored": int(scored["test_id"].nunique()), "test_count_definition": TEST_COUNT_DEFINITION}


def row_years(scores: pd.DataFrame, ledger: pd.DataFrame) -> np.ndarray:
    """Calendar year (UTC) in which the test of each scored row started, from the ledger's ``started_at``.

    A row scored at origin t starts in the quarter of t, so this is also the year of its origin; the ledger value is used so the
    definition does not depend on the origin grid. A row id absent from the ledger falls back to the year of its origin.
    """
    started = ledger.drop_duplicates("row_id").set_index("row_id")["started_at"]
    year = pd.to_datetime(started.reindex(scores["row_id"]).to_numpy(), utc=True).year.to_numpy(dtype=float)
    fallback = pd.DatetimeIndex(pd.to_datetime(scores["origin"], utc=True)).year.to_numpy(dtype=float)
    return np.where(np.isnan(year), fallback, year).astype(int)


def _split_half(ledger: pd.DataFrame, origin=None) -> dict:
    """Split-half prior check at the final scored origin, so only rows a fitted model could see are used."""
    try:
        return hs.split_half(ledger, origin)
    except (ValueError, KeyError):
        return {}


# -------------------------------------------------------------- markdown
def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v).replace("|", "/")


def _table(rows: list[dict], columns: list[str]) -> list[str]:
    cols = [c for c in columns if any(c in r for r in rows)]
    if not cols:
        return []
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    lines += ["| " + " | ".join(_fmt(r.get(c)) for c in cols) + " |" for r in rows]
    return lines + [""]


_AGG_GROUPS = [
    ("Rows, tests, gates and abstention (the headline decidability is by tests; the by-row columns are beside it)",
     ["cell", "rung", "kind", "n", "n_tests", "n_nonabstained", "abstention_rate", "gate_base_rate", "decidable_by_tests",
      "decidable_by_tests_base_0.3", "decidable_research_by_tests", "decidable", "decidable_research"]),
    ("Log score and CRPS, all predicted rows (higher log score is better, lower CRPS is better)",
     ["cell", "rung", "logscore", "logscore_lo", "logscore_hi", "crps", "crps_lo", "crps_hi"]),
    ("Brier score of p_sig against the significant-positive event, with skill against the base rate",
     ["cell", "rung", "brier", "brier_lo", "brier_hi", "brier_base", "brier_skill", "brier_skill_lo", "brier_skill_hi", "brier_floor"]),
    ("Calibration of p_sig against the perfect-calibration null, clustered by test",
     ["cell", "rung", "ece", "ece_percentile", "ece_percentile_independent", "ece_equal_mass", "ece_equal_mass_percentile", "design_effect", "icc"]),
    ("Bonferroni-adjusted bounds for the family of intervals of this table (descriptive intervals are the unadjusted ones above)",
     ["cell", "rung", "family_size", "brier_skill", "adjusted_lo", "adjusted_hi", "logscore", "logscore_adjusted_lo", "logscore_adjusted_hi"]),
    ("Direction accuracy and coverage of the intervals for y",
     ["cell", "rung", "direction_accuracy", "direction_accuracy_lo", "direction_accuracy_hi", "n_decisive", "direction_accuracy_decisive",
      "direction_ceiling",
      "coverage_80", "coverage_80_lo", "coverage_80_hi", "coverage_90", "coverage_90_lo", "coverage_90_hi"]),
    ("The same scores on non-abstained rows only",
     ["cell", "rung", "logscore_nonabstained", "logscore_nonabstained_lo", "logscore_nonabstained_hi",
      "crps_nonabstained", "crps_nonabstained_lo", "crps_nonabstained_hi", "brier_nonabstained", "brier_nonabstained_lo",
      "brier_nonabstained_hi", "direction_accuracy_nonabstained", "direction_accuracy_nonabstained_lo",
      "direction_accuracy_nonabstained_hi"]),
]


def render_markdown(doc: dict) -> str:
    """Render the report Markdown from the JSON document. Pure function of ``doc``."""
    h, notes, t = doc["header"], doc["notes"], doc["tables"]
    out = [f"# Backtest report: {h['source']}", ""]
    if h["synthetic"]:
        out += ["**Synthetic data.** Every number below comes from simulated tests with known truth. "
                "It shows the method works, not what any real archive says.", ""]
    out += [
        f"> {h['boundary']}",
        "",
        "## Header",
        "",
        f"- Source: {h['source']}",
        f"- Ledger snapshot: {h['snapshot_id']}",
        f"- Model: {h['model_id']}",
        f"- Feature hash: {h['feature_hash']}",
        f"- Command: `{h['command']}`",
        f"- Seed: {h['seed']}, bootstrap resamples: {h['bootstrap_resamples']}",
        *([f"- Variant (an ablation, not the main run): {json.dumps(h['variant'], sort_keys=True)}"] if h.get("variant") else []),
        f"- Gate sizes from the power simulation at the release gate"
        f"{' (power ' + format(h['gate_decision_target'], '.2f') + ')' if h.get('gate_decision_target') else ''}: "
        f"n_200 = {h['gate_n_200']} (skill 0.20), n_400 = {h['gate_n_400']} (skill 0.10)",
        *_research_gate_lines(h),
        f"- Rungs: {', '.join(h['rungs'])}; primary rung for decisions and plots: {h['primary_rung']}",
        f"- Origins scored: {h['origins_scored']} from {h['first_origin']} to {h['last_origin']}",
        f"- Origins with fewer than {h['min_fit_rows']} visible rows (nothing fitted): {', '.join(h['skipped_origins']) or 'none'}",
        f"- Ledger rows: {h['ledger_rows']}, admitted: {h['admitted_rows']}, scored: {h['scored_rows']}, "
        f"admitted but never scored (before the first fit): {h['not_scored_rows']}",
        *(
            [
                f"- Tests: {h['tests_in_ledger']} in the ledger, {h['tests_admitted']} admitted, {h['tests_scored']} scored. "
                f"{h['test_count_definition']}"
            ]
            if "tests_scored" in h
            else []
        ),
        *([f"- P2 admission guard: {h['p2_guard']}"] if h.get("p2_guard") is not None else []),
        *(
            [
                "- Gate sizes by base rate (tests): "
                + "; ".join(f"{b}: n_200 {v['n_200']}, n_400 {v['n_400']}" for b, v in h["gate_by_base_rate"].items())
            ]
            if h.get("gate_by_base_rate")
            else []
        ),
        "",
        "## How to read the scores",
        "",
        notes["circularity"],
        "",
        notes["burn_in"],
        "",
        "Intervals are 90 percent bootstrap intervals that resample whole tests. Scores are given on all predicted rows "
        "(so rungs are comparable) and, separately, on rows where the card would not have abstained.",
        "",
        notes.get("p0_skill", ""),
        "",
        notes.get("intervals", ""),
        "",
        notes.get("calibration_null", ""),
        "",
        "Rungs:",
        "",
    ]
    out += [f"- {r}: {d}" for r, d in notes["rungs"].items() if d] + [""]
    out += ["## Scores by cell and rung", ""]
    seen: set[str] = set()
    agg = t["aggregate"]
    for title, cols in _AGG_GROUPS:
        out += [f"### {title}", ""] + _table(agg, cols)
        seen.update(cols)
    rest = [c for c in (agg[0].keys() if agg else []) if c not in seen]
    if rest:
        out += ["### Other columns", ""] + _table(agg, ["cell", "rung"] + rest)
    if "second_opinion" in h:
        so = h["second_opinion"]
        out += ["## Second opinion", "",
                f"- Provider: {so['provider_id']} version {so['version']}, knowledge cutoff {so.get('knowledge_cutoff') or 'none declared'}",
                f"- Weight in force: {_fmt(so['weight'])} (zero until earned on the backtest)"
                + (" (earned with contaminated origins)" if so.get("weight_contaminated") and so["weight"] else ""),
                f"- Rows scored by the base rung {so['base_rung']}: {so['n_rows']}; with an opinion: {so['n_with_opinion']}; "
                f"declined: {so['n_declined']}; failed calls: {so.get('n_failed', 0)}; absent from the records file: {so['n_missing']}",
                f"- Cost of the recorded run: {_fmt(so['cost_usd'])} dollars, latency {_fmt(so['latency_s'])} seconds in total",
                "", notes["second_opinion"], "",
                f"The rung `{so['base_rung']} on agent rows` is the base rung on the rows where the agent gave an opinion. "
                "Compare the agent with it, not with the base rung on all rows.", ""]
        out += _table(t.get("second_opinion", []), ["origins", "rung", "n", "brier", "brier_lo", "brier_hi", "brier_base", "brier_skill",
                                                    "brier_skill_lo", "brier_skill_hi", "direction_accuracy", "decidable_by_tests", "decidable"])
    for key, title in (("local_eb", "Local empirical Bayes"), ("selection", "P2 selection"), ("learning_curve", "Learning curve")):
        if key in notes:
            out += [f"## {title}", "", notes[key], ""]
    if t.get("p2_selection_by_cell"):
        out += ["## P2 selection by cell", "",
                "How lam (the weight on precedents), the bandwidth multiplier and the recency half-life were chosen, summarised over the origins. "
                "`share_lambda_zero` is the share of origins where the selection gave up on precedents and P2 equalled P1 in that cell. "
                "`guard` is the admission guard multiplier: lam above zero is used only when its out-of-sample log-score gain over lam 0 "
                "minus that many standard errors (across tests) is above zero, the ladder admission rule made operational. "
                "`share_guard_held` is the share of origins where the guard forced lam to 0 although the earlier rule would have used "
                "the precedents; `gain_mean` and `gain_se_mean` are the gain of the best candidate and its standard error, averaged over "
                "origins. The per-origin values are in the JSON under `p2_selection`.", ""]
        out += _table(t["p2_selection_by_cell"], ["rung", "cell", "selection", "origins", "lambda_mean", "lambda_min", "lambda_max",
                                                  "share_lambda_zero", "guard", "share_guard_held", "lambda_unguarded_mean", "gain_mean",
                                                  "gain_se_mean", "bandwidth_mult_mean", "half_life_days_median", "share_no_decay"])
    if t.get("by_metric"):
        out += ["## Metrics", "",
                f"This ledger has {len(t['by_metric'])} metrics per experiment, each scored separately below. "
                f"The pooled `ALL` rows above mix metrics of different scales; read the blocks. "
                f"The decision value uses the primary metric ({h['primary_metric']}) only.", ""]
        for blk in t["by_metric"]:
            out += [f"### Metric {blk['metric']}" + (" (primary)" if blk["primary"] else ""), "", f"{blk['n_rows']} scored rows.", ""]
            rows = [r for r in blk["aggregate"] if r["cell"] == "ALL"]
            out += _table(rows, ["rung", "kind", "n", "n_tests", "logscore", "logscore_lo", "logscore_hi", "crps", "brier_skill", "brier_skill_lo",
                                 "brier_skill_hi", "direction_accuracy", "decidable_by_tests"])
    out += ["## Abstention by trigger", "", "Counts of rows that fired each trigger (a row can fire several).", ""]
    out += _table(t["abstention"], ["cell", "n", "rate", "support", "novelty", "reliability", "instability"])
    out += [notes["abstention_triggers"], ""]
    if t.get("released_rows"):
        out += ["## Released rows", "", notes["released_rows"], ""]
        out += _table(t["released_rows"], ["cell", "rung", "n", "n_tests", "logscore", "logscore_lo", "logscore_hi", "brier", "brier_skill",
                                           "brier_skill_lo", "brier_skill_hi", "direction_accuracy", "direction_accuracy_lo",
                                           "direction_accuracy_hi", "event_rate", "mean_p_sig", "n_abstained_main", "n_abstained_ablation"])
    out += ["## Origins", "", "The first scored origin is the burn-in origin.", ""]
    out += _table(t["origins"], ["origin", "n_scored", "n_tests", "abstention_rate", "logscore", "burn_in"])
    out += ["### Log score by origin with 90 percent intervals", ""]
    out += _table(t["score_by_origin"], ["origin", "rung", "n", "logscore", "logscore_lo", "logscore_hi"])
    out += ["### Scores by calendar year of the test start", "",
            "Each scored row belongs to the year in which its test started; the years partition the scored rows. Brier skill and "
            "log score carry 90 percent by-test intervals.", ""]
    out += _table(t.get("score_by_year", []), ["year", "cell", "rung", "n", "n_tests", "logscore", "logscore_lo", "logscore_hi", "brier_skill",
                                                "brier_skill_lo", "brier_skill_hi", "direction_accuracy", "abstention_rate"])
    out += ["## Coverage of the intervals for y (primary rung)", ""]
    out += _table(t["coverage"], ["cell", "n", "coverage_80", "coverage_90"])
    out += ["## Coverage by realized over planned standard error", "",
            "Rows grouped in deciles of the ratio of the realized to the planned standard error (an evaluation-time stratifier: the realized "
            "standard error is never a forecast input). The forecaster fixes the click-through level at the cell median, so the ratio varies "
            "with the realized level; `coverage_80` and `coverage_90` should be near 0.80 and 0.90 in every decile. A rung that is not in "
            "range here is not calibrated within strata, whatever its pooled coverage.", ""]
    out += _table(t.get("coverage_by_se_ratio", []), ["rung", "decile", "ratio_lo", "ratio_hi", "n", "mean_ratio", "coverage_80", "coverage_90",
                                                      "event_rate", "mean_p_sig"])
    out += ["## Calibration by precision", "",
            "Rows grouped in deciles of the planned exposures per arm (fewer groups when exposures tie). A forecaster that is "
            "calibrated overall but not within these groups is not calibrated. `mean_p_sig` should match `event_rate`, and "
            "`coverage_90` should be near 0.90, in every group.", ""]
    out += _table(t.get("calibration_by_precision", []), ["rung", "decile", "exposure_lo", "exposure_hi", "n", "mean_s_star",
                                                          "mean_p_sig", "event_rate", "coverage_90"])
    out += ["## Reliability bins of p_sig", ""]
    out += _table(t["reliability_bins"], ["rung", "bin", "lo", "hi", "n", "mean_p", "freq"])
    out += ["## Split-half check of the prior", "", "P1 fit on odd tests and on even tests; the gap in the cell mean and spread.", ""]
    out += _table(t["split_half"], ["cell", "mu_odd", "mu_even", "mu_gap", "tau_odd", "tau_even", "tau_gap", "n_odd", "n_even"])
    out += ["## Decision value", "",
            "Reported separately from calibration and never combined with it. Each origin picks K tests (10, 25 and 50 percent of the "
            "period's tests, rounded, at least one) at random, by p_win, or by an oracle that knows y. Captured is the lift won in the units "
            "of y, the fraction is of the period's total positive observed lift, and regret is the oracle's capture minus the policy's. "
            + notes.get("decision_value", ""), ""]
    out += _table(t["decision_value"], ["origin", "policy", "rung", "budget", "K", "n_tests", "total", "captured", "captured_fraction",
                                        "captured_fraction_lo", "captured_fraction_hi", "regret", "regret_lo", "regret_hi", "random_fraction",
                                        "diff_random", "diff_random_lo", "diff_random_hi", "constant_within_cell"])
    out += ["## Figures", ""] + [f"- figures/{n}-{h['source']}.png" for n in FIGURE_NAMES] + [""]
    return "\n".join(out)


def _is_release(k: str, h: dict) -> bool:
    target = h.get('gate_decision_target')
    return target is not None and abs(float(k) - target) < 1e-9


def _research_gate_lines(h: dict) -> list[str]:
    by = h.get("gate_by_target")
    if not by:
        return []
    return [f"- At power {k}: n_200 = {v['n_200']} (skill 0.20), n_400 = {v['n_400']} (skill 0.10)"
            f"{' (release gate)' if _is_release(k, h) else ' (research screen)'}"
            for k, v in sorted(by.items(), key=lambda kv: float(kv[0]))]


# ----------------------------------------------------------------- figures
def _label(doc: dict) -> str:
    return " (synthetic data)" if doc["header"]["synthetic"] else ""


def plot_reliability(doc: dict, path: Path) -> Path:
    """Reliability diagram of p_sig per rung: observed frequency against mean predicted probability."""
    bins = pd.DataFrame(doc["tables"]["reliability_bins"])
    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    ax.plot([0, 1], [0, 1], color="0.6", linestyle="--", label="perfect calibration")
    for rung, g in bins.groupby("rung"):
        g = g[g["n"] >= MIN_BIN_N]
        ax.plot(g["mean_p"], g["freq"], marker="o", label=rung)
    ax.set_xlabel("mean predicted P(significant and positive)")
    ax.set_ylabel("observed frequency")
    ax.set_title("Reliability of p_sig, bins of at least 10 rows" + _label(doc))
    ax.legend(fontsize=8)
    return _save(fig, path)


def plot_score_by_origin(doc: dict, path: Path) -> Path:
    """Mean log score per origin and rung with 90 percent by-test intervals."""
    d = pd.DataFrame(doc["tables"]["score_by_origin"])
    d["origin"] = pd.to_datetime(d["origin"])
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for rung, g in d.groupby("rung"):
        g = g.dropna(subset=["logscore"])
        if g.empty:
            continue
        ax.plot(g["origin"], g["logscore"], marker="o", label=rung)
        ax.fill_between(g["origin"], g["logscore_lo"], g["logscore_hi"], alpha=0.12)
    ax.set_xlabel("origin (quarter start)")
    ax.set_ylabel("mean log score of the observed estimate")
    ax.set_title("Log score by origin" + _label(doc))
    ax.legend(fontsize=8)
    fig.autofmt_xdate()
    return _save(fig, path)


def plot_coverage(doc: dict, path: Path) -> Path:
    """Coverage of the 80 and 90 percent intervals for y per cell against their nominal levels."""
    d = pd.DataFrame(doc["tables"]["coverage"])
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    x = np.arange(len(d))
    ax.bar(x - 0.2, d["coverage_80"], width=0.4, label="80 percent interval")
    ax.bar(x + 0.2, d["coverage_90"], width=0.4, label="90 percent interval")
    ax.axhline(0.8, color="C0", linestyle="--", linewidth=1)
    ax.axhline(0.9, color="C1", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(d["cell"], rotation=20)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("share of observed y inside")
    ax.set_title(f"Interval coverage, rung {doc['header']['primary_rung']}" + _label(doc))
    ax.legend(fontsize=8, loc="lower right")
    return _save(fig, path)


def plot_decision_value(doc: dict, path: Path) -> Path:
    """Share of the period's total positive lift captured by each policy, pooled over origins."""
    d = pd.DataFrame(doc["tables"]["decision_value"])
    d = d[(d["origin"] == "ALL") & (d["budget"] == 0.25)] if "budget" in d.columns else d[d["origin"] == "ALL"]
    primary = doc["header"]["primary_rung"]
    d = d[(d["rung"] == primary) | (d["rung"] == "all")]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    labels = [f"{p}" for p in d["policy"]]
    ax.bar(labels, d["captured_fraction"], color=["0.6", "C0", "C2"][: len(d)])
    for i, v in enumerate(d["captured_fraction"]):
        ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("fraction of total positive lift captured")
    ax.set_title("Decision value at K = 25 percent of tests" + _label(doc))
    return _save(fig, path)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


# ------------------------------------------------------------- reliability
def write_reliability(scores: pd.DataFrame, source: str, out_dir, as_of: dt.datetime | None = None, overwrite: bool = False) -> Path:
    """Seed ``reliability-<source>.json`` from the backtest scores, in the schema the abstention trigger reads.

    The report is stamped ``as_of`` (default: when the last outcome became known, so it describes the end of the
    archive) and holds, per cell, the log score and Brier skill of the primary rung over the trailing eight weeks.
    An existing file is replaced only when ``overwrite`` is true or the new report is newer, so a backtest never
    wipes the drift counters a weekly join has written.
    """
    out_dir = Path(out_dir)
    path = out_dir / f"reliability-{source}.json"
    rung = "P2" if (scores["rung"] == "P2").any() else ("P1" if (scores["rung"] == "P1").any() else sorted(scores["rung"].unique())[-1])
    main = scores[scores["rung"] == rung]
    when = pd.Timestamp(as_of).tz_convert("UTC") if as_of is not None else main["usable_after"].max()
    base = scores[scores["rung"] == "P0"].set_index("row_id")["logscore"] if (scores["rung"] == "P0").any() else None
    p0_ls = main["logscore"].to_numpy() if base is None else base.reindex(main["row_id"]).to_numpy()
    outcomes = pd.DataFrame({"cell": main["cell"].to_numpy(), "at": main["usable_after"].to_numpy(), "logscore": main["logscore"].to_numpy(),
                             "p0_logscore": p0_ls, "brier": main["brier_event"].to_numpy(), "p0_brier": main["brier_base"].to_numpy(),
                             "test_id": main["test_id"].to_numpy()})
    report = build_reliability(None, outcomes, when.to_pydatetime(), advance=True, source=source)
    if path.exists() and not overwrite:
        old = json.loads(path.read_text(encoding="utf-8"))
        if dt.datetime.fromisoformat(old["as_of"]) >= when.to_pydatetime():
            return path
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(clean(report), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


# ------------------------------------------------------------------- write
def write_report(scores: pd.DataFrame, *, ledger: pd.DataFrame, source: str, snapshot_id: str, model_id: str, feature_hash: str,
                 command: str, seed: int, gates: dict, out_dir, B: int = hs.DEFAULT_B, second_opinion: dict | None = None,
                 extra_notes: dict | None = None, suffix: str = "", main: bool = True, variant: dict | None = None,
                 primary_metric: str | None = None, reference_scores: pd.DataFrame | None = None,
                 reference_files: dict | None = None) -> ReportPaths:
    """Write the JSON, the Markdown, the score table, the figures and the reliability seed; return their paths.

    ``suffix`` names a variant (``--setting`` is appended to the file stem). ``main=False`` is for variants and
    ablations: no figures are drawn and the reliability seed is not touched.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = build_document(scores, ledger=ledger, source=source, snapshot_id=snapshot_id, model_id=model_id,
                         feature_hash=feature_hash, command=command, seed=seed, gates=gates, B=B, second_opinion=second_opinion,
                         extra_notes=extra_notes, variant=variant, primary_metric=primary_metric,
                         reference_scores=reference_scores, reference_files=reference_files)
    stem = f"backtest-{source}-{snapshot_id}" + (f"--{suffix}" if suffix else "")
    paths = ReportPaths(md=out_dir / f"{stem}.md", json=out_dir / f"{stem}.json",
                        scores=out_dir / f"scores-{source}-{snapshot_id}{'--' + suffix if suffix else ''}.parquet")
    paths.json.write_text(json.dumps(doc, indent=1, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8")
    paths.md.write_text(render_markdown(doc), encoding="utf-8")
    scores.to_parquet(paths.scores, index=False)
    if not main:
        return paths
    fig_dir = out_dir / "figures"
    paths.figures = {
        "reliability": plot_reliability(doc, fig_dir / f"reliability-{source}.png"),
        "score_by_origin": plot_score_by_origin(doc, fig_dir / f"score_by_origin-{source}.png"),
        "coverage": plot_coverage(doc, fig_dir / f"coverage-{source}.png"),
        "decision_value": plot_decision_value(doc, fig_dir / f"decision_value-{source}.png"),
    }
    paths.reliability = write_reliability(scores, source, out_dir)
    return paths
