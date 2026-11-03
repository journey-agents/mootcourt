"""Readers that map vendor result exports to the exchange format (``exchange.py``).

Every reader returns a frame in the exchange columns; ``moot ingest --format NAME`` then checks it and converts it to ledger rows.
A reader derives the standard error from what the export carries, in this order: a standard error field, interval bounds,
an interval half-width, a p-value. Where an export does not state the confidence level or the interval scale, the reader
takes an explicit option (``ci_level``, ``ci_kind``) with the default named below, writes the assumption into the row's
``variance_method`` provenance and the user confirms it against their own export. The documentation behind each mapping is
cited in the reader's docstring, and ``docs/ledger-format.md`` lists, per format, what is documented and what is assumed.

Documented mappings: ``statsig`` (warehouse results view), ``optimizely`` (CSV export), ``harness`` (CSV and JSON), ``growthbook``
(experiment results API and bulk snapshots), ``jetstream`` (Mozilla result tables). Not documented publicly, so they ship a template to
edit: ``eppo`` and the Statsig CSV download. ``generic`` reads a file already in the exchange columns, or any file through a
mapping file. The word Statsig appears here only as the name of the surveyed export format.
"""
from __future__ import annotations

import json
import tomllib
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from mootcourt.importers.exchange import OPTIONAL, REQUIRED, read_table

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "examples" / "mappings"


class MappingError(ValueError):
    """The input does not have the columns or structure the format needs."""


def z_of(level: float) -> float:
    """Two-sided normal critical value of a confidence level in (0, 1)."""
    if not 0.0 < level < 1.0:
        raise ValueError("a confidence level must be strictly between 0 and 1")
    return float(stats.norm.ppf(0.5 + level / 2.0))


def se_from_bounds(lo, hi, level: float) -> np.ndarray:
    """Standard error implied by a symmetric normal interval ``[lo, hi]`` at confidence ``level``."""
    return (pd.to_numeric(hi, errors="coerce") - pd.to_numeric(lo, errors="coerce")) / (2.0 * z_of(level))


def se_from_halfwidth(half, level: float) -> np.ndarray:
    """Standard error implied by an interval half-width at confidence ``level``."""
    return pd.to_numeric(half, errors="coerce").abs() / z_of(level)


def se_from_pvalue(effect, p, ) -> np.ndarray:
    """Standard error implied by a two-sided p-value: ``|effect| / z`` with ``z = Phi^-1(1 - p / 2)``. NaN when ``p`` is not in (0, 1)."""
    p = pd.to_numeric(p, errors="coerce").to_numpy(float)
    e = np.abs(pd.to_numeric(effect, errors="coerce").to_numpy(float))
    ok = (p > 0) & (p < 1)
    z = np.where(ok, stats.norm.ppf(1.0 - np.where(ok, p, 0.5) / 2.0), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ok & (z > 0), e / z, np.nan)


def _need(df: pd.DataFrame, cols, fmt: str) -> None:
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise MappingError(f"the {fmt} export lacks the documented column(s) {miss}; found {list(df.columns)[:12]}")


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _frame(**cols) -> pd.DataFrame:
    return pd.DataFrame(cols)


# ------------------------------------------------------------------ generic and templates
def apply_mapping(raw: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Build an exchange frame from ``raw`` using a mapping dict (``[columns]``, ``[constants]``, ``[options]`` of a mapping file).

    ``columns`` maps an exchange column (or ``ci_low``, ``ci_high``, ``ci_halfwidth``, ``p_value`` for deriving ``se``) to a column of
    ``raw``; ``constants`` gives the same value to every row; ``options`` holds ``ci_level`` (default 0.95) and ``scale`` (a factor
    applied to ``effect`` and ``se``, default 1, for example 0.01 when an export reports percent).
    Raises MappingError naming the missing input column.
    """
    cols, consts, opts = mapping.get("columns", {}), mapping.get("constants", {}), mapping.get("options", {})
    for ex, src in cols.items():
        if src not in raw.columns:
            raise MappingError(f"mapping: column {src!r} (for {ex}) is not in the input; found {list(raw.columns)[:12]}")
    pick = {ex: raw[src] for ex, src in cols.items()}
    out = pd.DataFrame(index=raw.index)
    for ex in REQUIRED + OPTIONAL + [c for c in raw.columns if c.startswith("feature_")] + (["headline"] if "headline" in raw.columns else []):
        if ex in pick:
            out[ex] = pick[ex]
        elif ex in raw.columns and not cols:
            out[ex] = raw[ex]
    for k, v in consts.items():
        out[k] = v
    level = float(opts.get("ci_level", 0.95))
    derived = None
    if "se" not in out.columns or out["se"].isna().all():
        if "ci_low" in pick and "ci_high" in pick:
            out["se"] = se_from_bounds(pick["ci_low"], pick["ci_high"], level)
            derived = f"se from ci_low/ci_high taken as symmetric bounds at {level:.2f} (mapping option ci_level)"
        elif "ci_halfwidth" in pick:
            out["se"] = se_from_halfwidth(pick["ci_halfwidth"], level)
            derived = f"se from ci_halfwidth taken as a half-width at {level:.2f} (mapping option ci_level)"
        elif "p_value" in pick and "effect" in out.columns:
            out["se"] = se_from_pvalue(out["effect"], pick["p_value"])
            derived = "se from the two-sided p-value and the effect under a normal approximation"
    if derived:                               # the assumption travels with every row (REV-043)
        out["variance_method"] = (out["variance_method"].astype(str).str.strip() + "; " + derived) if "variance_method" in out.columns else derived
    scale = float(opts.get("scale", 1.0))
    if scale != 1.0:
        for c in ("effect", "se"):
            if c in out.columns:
                out[c] = _num(out[c]) * scale
    return out.reset_index(drop=True)


def load_mapping(path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"mapping file not found: {p}")
    return tomllib.loads(p.read_text(encoding="utf-8"))


def read_generic(path, mapping: dict | None = None, **_) -> pd.DataFrame:
    """A file already in the exchange columns (no mapping), or any CSV or Parquet file read through a mapping file.

    Specification: docs/ledger-format.md. Template: examples/mappings/generic.toml.
    """
    raw = read_table(path)
    return apply_mapping(raw, mapping) if mapping else raw


def read_template(name: str, path, mapping: dict | None = None, **_) -> pd.DataFrame:
    """Formats whose export schema is not documented publicly: a mapping file is required; the template is in examples/mappings."""
    if not mapping:
        raise MappingError(
            f"the {name} export has no publicly documented column list, so there is no built-in mapping. Copy "
            f"examples/mappings/{name}.toml, edit the column names to match your export, and pass it with --mapping")
    return apply_mapping(read_table(path), mapping)


# ------------------------------------------------------------------ Statsig warehouse view
def read_statsig(path, ci_level: float = 0.95, effect_scale: str = "absolute", **_) -> pd.DataFrame:
    """The Statsig Warehouse Native results view ``statsig_daily_results`` as a CSV or Parquet extract.

    Documentation of the view (42 columns, fetched 3 November 2026): https://docs.statsig.com/experiments/interpreting-results/access-whn
    and the Console API for decisions: https://docs.statsig.com/console-api/experiments.
    Mapping: experimentName to experiment_id; controlGroupName to baseline_id; testGroupName to variant_id; metricName to metric_id;
    absoluteDelta (or relativeDelta with ``effect_scale="relative"``) to effect; controlUnits and testUnits to n_baseline and n_variant;
    experimentStartTs and experimentEndTs (milliseconds) to started_at and ended_at; useCUPED, useSequential to provenance.
    The view has one row per ``ds`` (day); the latest ``ds`` per experiment, groups and metric is the final read.
    NOT DOCUMENTED: whether absoluteDeltaCI and relativeDeltaCI are a half-width or a bound, and their confidence level. The page types
    them as a single number, so this reader takes the value as the interval half-width at ``ci_level`` (default 0.95) and says so in
    ``variance_method``. Confirm against your own export; if your CI is on another convention, use the template mapping instead.
    """
    raw = read_table(path)
    rel = effect_scale == "relative"
    eff_c, ci_c = ("relativeDelta", "relativeDeltaCI") if rel else ("absoluteDelta", "absoluteDeltaCI")
    _need(raw, ["experimentName", "controlGroupName", "testGroupName", "metricName", eff_c, ci_c, "controlUnits", "testUnits",
                "experimentStartTs", "experimentEndTs"], "statsig")
    d = raw.copy()
    if "ds" in d.columns:
        d["_ds"] = pd.to_datetime(d["ds"], utc=True, errors="coerce", format="mixed")
        d = d.sort_values("_ds", kind="stable").groupby(["experimentName", "controlGroupName", "testGroupName", "metricName"], as_index=False).tail(1)
    se = se_from_halfwidth(d[ci_c], ci_level)
    seq = d["useSequential"].astype(str).str.lower().isin(["true", "1"]) if "useSequential" in d.columns else pd.Series(False, index=d.index)
    cuped = d["useCUPED"].astype(str).str.lower().isin(["true", "1"]) if "useCUPED" in d.columns else pd.Series(False, index=d.index)
    method = f"statsig view {ci_c} taken as half-width at {ci_level:.2f} (assumed, not documented)"
    return _frame(
        experiment_id=d["experimentName"].to_numpy(), variant_id=d["testGroupName"].to_numpy(), baseline_id=d["controlGroupName"].to_numpy(),
        metric_id=d["metricName"].to_numpy(), effect=_num(d[eff_c]).to_numpy(), se=np.asarray(se),
        n_baseline=_num(d["controlUnits"]).to_numpy(), n_variant=_num(d["testUnits"]).to_numpy(),
        started_at=pd.to_datetime(_num(d["experimentStartTs"]), unit="ms", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ").to_numpy(),
        ended_at=pd.to_datetime(_num(d["experimentEndTs"]), unit="ms", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ").to_numpy(),
        effect_unit="relative" if rel else "absolute", source_system="statsig_view", variance_method=method,
        cuped=cuped.to_numpy(), sequential=seq.to_numpy(),
    )


# ------------------------------------------------------------------ Optimizely CSV
def read_optimizely(path, experiment_id: str | None = None, ci_level: float = 0.90, **_) -> pd.DataFrame:
    """The Optimizely CSV export of an experiment (20 columns).

    Documentation (fetched 3 November 2026): https://docs.optimizely.com/web-experimentation/docs/D9uo-reference-for-columns-in-csv-export-files-for-campaigns-and-experiments
    Mapping: Variation ID to variant_id (the row with Is Baseline Variation true is the baseline); Metric Event ID to metric_id;
    Improvement Value from Baseline to effect; Confidence Interval - Low and - High to se; Denominator Value to n_baseline and n_variant;
    Start Time (UTC) and End Time (UTC) to started_at and ended_at; Is Improvement Significant to decision.
    NOT DOCUMENTED: the unit of Improvement Value from Baseline, the scale of the interval and its confidence level. This reader keeps
    the value as exported with ``effect_unit`` "as_exported" and takes the interval as symmetric bounds at ``ci_level`` (default 0.90,
    the vendor's usual setting, an assumption). The export has no experiment id column, so ``experiment_id`` (``--experiment-id``) is required.
    """
    if not experiment_id:
        raise MappingError("the Optimizely CSV carries no experiment id; pass --experiment-id")
    raw = read_table(path)
    base = ["Start Time (UTC)", "End Time (UTC)", "Variation ID", "Is Baseline Variation", "Metric Event ID", "Denominator Value",
            "Improvement Value from Baseline", "Confidence Interval - Low", "Confidence Interval - High"]
    _need(raw, base, "optimizely")
    is_base = raw["Is Baseline Variation"].astype(str).str.lower().isin(["true", "1", "yes"])
    b = raw[is_base].drop_duplicates("Metric Event ID").set_index("Metric Event ID")
    v = raw[~is_base]
    v = v[v["Metric Event ID"].isin(b.index)]
    nb = v["Metric Event ID"].map(_num(b["Denominator Value"]))
    method = f"optimizely csv interval low/high taken as symmetric bounds at {ci_level:.2f} (assumed, not documented)"
    sig = v["Is Improvement Significant"].to_numpy() if "Is Improvement Significant" in v.columns else ""
    return _frame(
        experiment_id=experiment_id, variant_id=v["Variation ID"].to_numpy(),
        baseline_id=v["Metric Event ID"].map(b["Variation ID"]).to_numpy(), metric_id=v["Metric Event ID"].to_numpy(),
        effect=_num(v["Improvement Value from Baseline"]).to_numpy(),
        se=np.asarray(se_from_bounds(v["Confidence Interval - Low"], v["Confidence Interval - High"], ci_level)),
        n_baseline=nb.to_numpy(), n_variant=_num(v["Denominator Value"]).to_numpy(),
        started_at=v["Start Time (UTC)"].to_numpy(), ended_at=v["End Time (UTC)"].to_numpy(), effect_unit="as_exported",
        source_system="optimizely_csv", variance_method=method, decision=sig,
    )


# ------------------------------------------------------------------ Harness FME
_HARNESS_CSV = ["Metric", "Impact", "Impact lies above", "Impact lies below", "pValue", "Baseline sample size", "Comparison sample size",
                "Baseline treatment", "Comparison treatment", "Version start time", "Version end time"]


def read_harness(path, experiment_id: str | None = None, **_) -> pd.DataFrame:
    """The Harness Feature Management and Experimentation "Share results" download, CSV or JSON.

    Documentation (fetched in the landscape survey, 1.5): https://developer.harness.io/feature-management-experimentation/use-fme/experimentation/experiment-results/sharing-experiment-results/index
    CSV, one row per metric: Metric to metric_id; Impact to effect; Impact lies above and Impact lies below to the interval bounds;
    Baseline sample size and Comparison sample size to n_baseline and n_variant; Baseline treatment and Comparison treatment to
    baseline_id and variant_id; Version start time and Version end time to started_at and ended_at; Multiple comparison correction to
    provenance. JSON: the same per metric as impact, impactLower, impactUpper, pValue, sampleSizeOfBaseline, sampleSizeOfComparison with
    significanceThreshold, mcc and srmPValue beside them. The confidence level is 1 minus the exported significance threshold
    (``Experiment significance threshold`` or ``significanceThreshold``) when present, else 0.95 (an assumption stated in the row).
    The download has no experiment id, so ``experiment_id`` (``--experiment-id``, the split name) is required unless the JSON names it
    in ``split``. The interval is on the scale of Impact.
    """
    p = Path(path)
    if p.suffix.lower() == ".json":
        return _harness_json(p, experiment_id)
    if not experiment_id:
        raise MappingError("the Harness CSV carries no experiment id; pass --experiment-id (the split name)")
    raw = read_table(p)
    _need(raw, _HARNESS_CSV, "harness")
    thr = _num(raw["Experiment significance threshold"]) if "Experiment significance threshold" in raw.columns else pd.Series(np.nan, index=raw.index)
    level = (1.0 - thr).fillna(0.95)
    se = np.array([float(se_from_bounds(lo, hi, lv)) for lo, hi, lv in zip(raw["Impact lies below"], raw["Impact lies above"], level, strict=True)])
    method = np.where(thr.notna().to_numpy(), "harness csv interval lower/upper bounds at 1 minus the exported significance threshold ("
                      + level.map("{:.2f}".format).to_numpy() + ")", "harness csv interval lower/upper bounds taken at 0.95 "
                      "(assumed, the export has no significance threshold)")
    mcc = raw["Multiple comparison correction"].to_numpy() if "Multiple comparison correction" in raw.columns else ""
    return _frame(
        experiment_id=experiment_id, variant_id=raw["Comparison treatment"].to_numpy(), baseline_id=raw["Baseline treatment"].to_numpy(),
        metric_id=raw["Metric"].to_numpy(), effect=_num(raw["Impact"]).to_numpy(), se=se,
        n_baseline=_num(raw["Baseline sample size"]).to_numpy(), n_variant=_num(raw["Comparison sample size"]).to_numpy(),
        started_at=raw["Version start time"].to_numpy(), ended_at=raw["Version end time"].to_numpy(), effect_unit="as_exported",
        source_system="harness_csv", variance_method=method,
        multiple_comparison=mcc,
    )


def _harness_json(p: Path, experiment_id: str | None) -> pd.DataFrame:
    doc = json.loads(p.read_text(encoding="utf-8"))
    metrics: list[dict] = []

    def walk(o):
        if isinstance(o, dict):
            if "impact" in o and ("impactLower" in o or "impactUpper" in o):
                metrics.append(o)
            else:
                for v in o.values():
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(doc)
    if not metrics:
        raise MappingError("harness json: no metric objects with impact, impactLower and impactUpper were found")
    top = doc if isinstance(doc, dict) else {}
    exp = experiment_id or top.get("split") or top.get("splitName")
    if not exp:
        raise MappingError("the Harness JSON does not name the split; pass --experiment-id")
    rows = []
    for m in metrics:
        thr = m.get("significanceThreshold", top.get("significanceThreshold"))
        level = 1.0 - float(thr) if thr is not None else 0.95
        how = (f"harness json impactLower/impactUpper bounds at 1 minus the exported significance threshold ({level:.2f})" if thr is not None
               else "harness json impactLower/impactUpper bounds taken at 0.95 (assumed, the export has no significance threshold)")
        miss = [k for k in ("name", "sampleSizeOfBaseline", "sampleSizeOfComparison") if k not in m]
        if miss:
            raise MappingError(f"harness json: metric object lacks {miss}")
        rows.append({
            "experiment_id": exp, "variant_id": m.get("comparisonTreatment", top.get("comparisonTreatment", "")),
            "baseline_id": m.get("baselineTreatment", top.get("baselineTreatment", "")), "metric_id": m.get("key", m["name"]),
            "effect": m["impact"], "se": float(se_from_bounds(m.get("impactLower"), m.get("impactUpper"), level)),
            "n_baseline": m["sampleSizeOfBaseline"], "n_variant": m["sampleSizeOfComparison"],
            "started_at": m.get("versionStartTime", top.get("versionStartTime", "")),
            "ended_at": m.get("versionEndTime", top.get("versionEndTime", "")),
            "effect_unit": "as_exported", "source_system": "harness_json",
            "variance_method": how,
            "multiple_comparison": m.get("mcc", top.get("mcc", "")),
            "srm_flag": (m.get("srmPValue", top.get("srmPValue")) is not None and float(m.get("srmPValue", top.get("srmPValue"))) < 0.001),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ GrowthBook
def read_growthbook(path, experiment_id: str | None = None, engine: str | None = None, started_at: str | None = None,
                    ci_level: float = 0.95, **_) -> pd.DataFrame:
    """GrowthBook experiment results, from the results API or the bulk-results snapshots, saved as JSON.

    Documentation (fetched 3 November 2026): https://docs.growthbook.io/api/experiments/operation/getExperimentResults and the
    bulk-results source description https://raw.githubusercontent.com/growthbook/growthbook/main/docs/app/experiment-bulk-results-api.mdx.
    Shape: ``result.results[].metrics[].variations[].analyses[]``. The first variation of a metric is the control. Mapping: result.experimentId
    to experiment_id; metricId to metric_id; variationId to variant_id; analyses[].percentChange to effect (a relative change);
    analyses[].effectStandardError to se (the documented "standard error of the estimated effect"); variation users to n_baseline and
    n_variant; result.dateStart and dateEnd to started_at and ended_at; engine, numerator, denominator and stddev to provenance;
    results[].checks.srm (a p-value) below 0.001 to srm_flag. Bulk snapshots (``snapshotId``, ``dateCreated``, ``results``) are accepted
    as a list or under ``snapshots`` or ``results``: the latest snapshot per experiment is the final read and ``dateCreated`` is its end
    when ``dateEnd`` is absent. A snapshot carries no start date, so ``started_at`` (``--started-at``) supplies it when ``dateStart`` is
    absent; without either the rows fail the conformance check with started_at missing. ``engine`` ("frequentist" or "bayesian") selects
    the analysis when several are present; default the first. When an analysis has no ``effectStandardError``, the standard error comes
    from ``ciLow`` and ``ciHigh`` as symmetric bounds at ``ci_level`` (default 0.95, an assumption written into the row).
    """
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    units: list[dict] = []
    if isinstance(doc, dict) and "result" in doc:
        units = [doc["result"]]
    else:
        items = doc if isinstance(doc, list) else (doc.get("snapshots") or doc.get("results") or doc.get("items") or [])
        latest: dict[str, dict] = {}
        for it in items:
            if not isinstance(it, dict) or "results" not in it:
                continue
            key = str(it.get("experimentId", experiment_id or ""))
            if key not in latest or str(it.get("dateCreated", "")) >= str(latest[key].get("dateCreated", "")):
                latest[key] = it
        units = list(latest.values())
    if not units:
        raise MappingError("growthbook: no result object (expected result.results[] or a list of snapshots with results)")
    rows = []
    for u in units:
        exp = u.get("experimentId") or experiment_id
        if not exp:
            raise MappingError("growthbook: the result does not name the experiment; pass --experiment-id")
        start, end = u.get("dateStart") or started_at, u.get("dateEnd") or u.get("dateCreated") or u.get("dateUpdated")
        for res in u["results"]:
            srm = (res.get("checks") or {}).get("srm")
            for met in res.get("metrics", []):
                vars_ = met.get("variations", [])
                if len(vars_) < 2:
                    continue
                control = vars_[0]
                for var in vars_[1:]:
                    an = _pick_analysis(var.get("analyses", []), engine)
                    if an is None:
                        continue
                    se = an.get("effectStandardError")
                    how = f"growthbook {an.get('engine', 'unknown')} effectStandardError"
                    if se is None and an.get("ciLow") is not None:
                        se = float(se_from_bounds(an["ciLow"], an["ciHigh"], ci_level))
                        how = (f"growthbook {an.get('engine', 'unknown')} ciLow/ciHigh taken as symmetric bounds at {ci_level:.2f} "
                               "(assumed, effectStandardError is absent)")
                    rows.append({
                        "experiment_id": exp, "variant_id": var.get("variationId"), "baseline_id": control.get("variationId"),
                        "metric_id": met.get("metricId"), "effect": an.get("percentChange"), "se": se,
                        "n_baseline": control.get("users"), "n_variant": var.get("users"), "started_at": start, "ended_at": end,
                        "effect_unit": "relative", "source_system": "growthbook_api",
                        "variance_method": how,
                        "numerator": an.get("numerator"), "denominator": an.get("denominator"),
                        "srm_flag": srm is not None and float(srm) < 0.001,
                    })
    if not rows:
        raise MappingError("growthbook: the results hold no variation with an analysis")
    return pd.DataFrame(rows)


def _pick_analysis(analyses: list[dict], engine: str | None):
    if not analyses:
        return None
    if engine:
        for a in analyses:
            if a.get("engine") == engine:
                return a
        return None
    return analyses[0]


# ------------------------------------------------------------------ Mozilla Jetstream
def read_jetstream(path, experiment_id: str | None = None, started_at: str | None = None, ended_at: str | None = None,
                   n_baseline: int | None = None, n_variant: int | None = None, statistic: str = "mean", comparison: str = "relative_uplift",
                   analysis_basis: str = "enrollments", **_) -> pd.DataFrame:
    """A Mozilla Jetstream statistics table (``statistics_<slug>_{day,week,overall}``) exported to CSV or Parquet.

    Documentation (fetched in the landscape survey, 2.7): https://docs.telemetry.mozilla.org/datasets/jetstream.
    Columns used: branch, comparison_to_branch, metric, statistic, comparison, segment, analysis_basis, window_index, point, lower, upper,
    ci_width. Rows kept: segment "all", the given ``statistic`` (default mean) and ``comparison`` (default relative_uplift, or difference),
    the given ``analysis_basis`` (default "enrollments"; the table holds one set of rows per basis, so a table with both would
    otherwise repeat every contrast) and the last window_index. Mapping: branch to variant_id; comparison_to_branch to baseline_id;
    metric to metric_id; point to effect; the
    interval lower and upper at confidence ci_width (a fraction, default 0.95 if absent) to se.
    NOT IN THE TABLE: the experiment slug, the dates and the number of clients per branch, so ``experiment_id``, ``started_at``,
    ``ended_at``, ``n_baseline`` and ``n_variant`` are required options (the enrollment window is described by window_index).
    """
    missing = [n for n, v in (("--experiment-id", experiment_id), ("--started-at", started_at), ("--ended-at", ended_at),
                              ("--n-baseline", n_baseline), ("--n-variant", n_variant)) if v is None]
    if missing:
        raise MappingError(f"the Jetstream table has no slug, dates or client counts; pass {', '.join(missing)}")
    raw = read_table(path)
    _need(raw, ["branch", "comparison_to_branch", "metric", "statistic", "comparison", "point", "lower", "upper"], "jetstream")
    d = raw[(raw["statistic"] == statistic) & (raw["comparison"] == comparison)]
    if "segment" in d.columns:
        d = d[d["segment"] == "all"]
    if d.empty:        # name the statistic or comparison first: the bases of an empty frame would be listed as []
        raise MappingError(f"jetstream: no rows with statistic {statistic!r} and comparison {comparison!r} for segment all")
    if "analysis_basis" in d.columns:
        present = sorted(d["analysis_basis"].dropna().astype(str).unique())
        if analysis_basis not in present:
            raise MappingError(f"jetstream: no rows with analysis_basis {analysis_basis!r}; the table has {present} (set --analysis-basis)")
        d = d[d["analysis_basis"].astype(str) == analysis_basis]
    d = d[d["branch"] != d["comparison_to_branch"]]
    if "window_index" in d.columns and len(d):
        w = _num(d["window_index"])
        d = d[w == w.max()]
    if d.empty:
        raise MappingError(f"jetstream: no rows with statistic {statistic!r} and comparison {comparison!r} for segment all")
    basis_label = analysis_basis if "analysis_basis" in d.columns else "all-basis"
    level = _num(d["ci_width"]).fillna(0.95) if "ci_width" in d.columns else pd.Series(0.95, index=d.index)
    se = np.array([float(se_from_bounds(lo, hi, lv)) for lo, hi, lv in zip(d["lower"], d["upper"], level, strict=True)])
    return _frame(
        experiment_id=experiment_id, variant_id=d["branch"].to_numpy(), baseline_id=d["comparison_to_branch"].to_numpy(),
        metric_id=d["metric"].to_numpy(), effect=_num(d["point"]).to_numpy(), se=se, n_baseline=n_baseline, n_variant=n_variant,
        started_at=started_at, ended_at=ended_at, effect_unit="relative" if comparison == "relative_uplift" else "absolute",
        source_system="jetstream",
        variance_method=f"jetstream {statistic} {comparison} {basis_label} lower/upper at ci_width",
    )


FORMATS: dict[str, Callable] = {
    "generic": read_generic,
    "statsig": read_statsig,
    "optimizely": read_optimizely,
    "harness": read_harness,
    "growthbook": read_growthbook,
    "jetstream": read_jetstream,
    "eppo": lambda path, mapping=None, **kw: read_template("eppo", path, mapping),
}
DOCUMENTED = ("statsig", "optimizely", "harness", "growthbook", "jetstream")
TEMPLATE_ONLY = ("eppo",)


def read_format(fmt: str, path, mapping: dict | None = None, **options) -> pd.DataFrame:
    """Read ``path`` with the named format. Unknown names raise ValueError listing the formats."""
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}; the formats are {', '.join(FORMATS)}")
    opts = {k: v for k, v in options.items() if v is not None}
    if fmt == "statsig" and mapping:                     # the CSV download has no documented columns: a mapping file replaces the view reader
        return apply_mapping(read_table(path), mapping)
    return FORMATS[fmt](path, mapping=mapping, **opts)
