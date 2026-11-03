"""The vendor-neutral ledger exchange format: reading, conformance checking and conversion to the ledger.

One exchange row is one contrast: one variant against one baseline on one metric of one experiment, at the final read.
``docs/ledger-format.md`` is the specification; this module is its executable form.

Required columns: ``experiment_id``, ``variant_id``, ``metric_id``, ``effect``, ``se``, ``n_baseline``, ``n_variant``,
``started_at``, ``ended_at``. Optional columns: ``baseline_id``, ``effect_unit``, ``cell``, ``status``, ``usable_after``,
``decision``, ``decision_threshold``, ``srm_flag``, and the provenance fields ``source_system``, ``variance_method``,
``cuped``, ``sequential``, ``winsorized``, ``multiple_comparison``, ``numerator``, ``denominator``. Any column starting with
``feature_`` is kept as a pre-launch feature (the ``feature_`` prefix is dropped); ``headline`` is a pre-launch feature too.

Units: ``effect`` is treatment minus baseline and ``se`` its standard error, both in ``effect_unit``: ``absolute`` (difference in
the metric's own units), ``relative`` (a fractional change), ``standardized`` (in standard deviations), or ``as_exported`` (a
vendor export that does not state its unit; kept as exported). Any other value is an error, and rows pooled in one cell (the
``cell`` column, else the metric) must share one unit: the check names the rows that differ. Counts must be whole numbers
no larger than 2**53. Timestamps are ISO-8601; a value without an offset is read as UTC.

Checks name the 1-based data row and the column. Violations of severity ``error`` stop an import; ``warning`` violations
(a missing standard error, which makes the row ``low_exposure``; missing provenance; identical arms) are reported by
``moot ledger check`` and printed by ``moot ingest`` but do not stop it.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt.ledger import LEDGER_COLUMNS, SCHEMA_VERSION, make_row_id, quarter_of, validate_ledger

REQUIRED = ["experiment_id", "variant_id", "metric_id", "effect", "se", "n_baseline", "n_variant", "started_at", "ended_at"]
OPTIONAL = ["baseline_id", "effect_unit", "cell", "status", "usable_after", "decision", "decision_threshold", "srm_flag",
            "source_system", "variance_method", "cuped", "sequential", "winsorized", "multiple_comparison", "numerator", "denominator"]
PROVENANCE = ["source_system", "variance_method"]
_TIME = ["started_at", "ended_at", "usable_after"]
UNITS = ("absolute", "relative", "standardized", "as_exported")
MAX_COUNT = 2 ** 53                     # the largest count a float64 holds exactly
MIN_EXPOSURE_DEFAULT = 100
MAX_REPORTED = 200


@dataclass(frozen=True)
class Violation:
    """One finding: the 1-based data row (0 for a whole-file finding), the column and a message."""

    row: int
    column: str
    message: str
    severity: str = "error"

    def __str__(self) -> str:
        where = f"row {self.row}, column {self.column}" if self.row else f"column {self.column}"
        return f"{self.severity}: {where}: {self.message}"


class ExchangeError(ValueError):
    """Raised when an exchange file has error-level violations; ``violations`` lists them."""

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        shown = "\n".join(str(v) for v in violations[:10])
        more = f"\n... and {len(violations) - 10} more" if len(violations) > 10 else ""
        super().__init__(f"{len(violations)} problem(s) in the exchange file:\n{shown}{more}")


def read_table(path) -> pd.DataFrame:
    """Read a CSV or Parquet file by suffix; every value of a CSV is read as text first so checks can name the bad cell."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"file not found: {p}")
    if p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    if p.suffix.lower() in (".csv", ".tsv", ".txt"):
        return pd.read_csv(p, dtype=str, keep_default_na=False, sep="\t" if p.suffix.lower() == ".tsv" else ",")
    raise ValueError(f"unsupported file type {p.suffix!r}; use .csv or .parquet")


def _num(series: pd.Series) -> pd.Series:
    """Numbers of a column as float64; a blank cell or a Parquet null (pd.NA of a nullable integer column) becomes NaN."""
    return pd.to_numeric(series.replace("", np.nan), errors="coerce").astype("float64")


def _exceeds_max_count(raw: pd.Series, arr: np.ndarray) -> list[int]:
    """1-based rows whose exact value is above 2**53. A float64 rounds 2**53 + 1 down to 2**53, so the rows that reach the bound as a
    float are re-read from the cell itself (text, integer or float) and compared as exact decimals."""
    out = []
    for i in np.flatnonzero(np.isfinite(arr) & (arr >= MAX_COUNT)):
        cell = raw.iloc[int(i)]
        try:
            exact = Decimal(cell) if isinstance(cell, float) else Decimal(str(cell).strip())
        except InvalidOperation:
            exact = Decimal(float(arr[int(i)]))
        if exact > MAX_COUNT:
            out.append(int(i) + 1)
    return out


def _times(raw: pd.Series) -> pd.Series:
    """UTC timestamps of a column; unparseable and blank values become NaT."""
    if pd.api.types.is_datetime64_any_dtype(raw):
        return pd.to_datetime(raw, utc=True)
    txt = raw.astype(str).str.strip().replace({"": np.nan, "nan": np.nan, "None": np.nan, "NaT": np.nan})
    return pd.to_datetime(txt, utc=True, errors="coerce", format="ISO8601")


def _blank(raw: pd.Series) -> pd.Series:
    """True where a cell is empty or the text of a missing value."""
    return raw.isna() | raw.astype(str).str.strip().isin(["", "nan", "None", "NaT"])


def _bad_cells(raw: pd.Series, parsed: pd.Series) -> list[int]:
    blank = _blank(raw)
    return [int(i) + 1 for i in np.flatnonzero((parsed.isna() & ~blank).to_numpy())]


def check_exchange(df: pd.DataFrame, now: dt.datetime | None = None) -> list[Violation]:
    """All violations of the exchange format in ``df``, errors first. See the module docstring."""
    out: list[Violation] = []
    missing = [c for c in REQUIRED if c not in df.columns]
    for c in missing:
        out.append(Violation(0, c, "required column is missing"))
    if missing:
        return out
    now = now or dt.datetime.now(dt.timezone.utc)

    def add(rows, col, msg, sev="error"):
        for r in rows:
            if len(out) < MAX_REPORTED:
                out.append(Violation(int(r), col, msg, sev))

    for col in ("experiment_id", "variant_id", "metric_id"):
        txt = df[col].astype(str).str.strip()
        add([i + 1 for i in np.flatnonzero((df[col].isna() | (txt == "") | (txt.str.lower() == "nan")).to_numpy())], col, "must not be empty")
    eff, se = _num(df["effect"]), _num(df["se"])
    add(_bad_cells(df["effect"], eff), "effect", "is not a number")
    add([i + 1 for i in np.flatnonzero((~np.isfinite(eff.to_numpy(float)) & eff.notna().to_numpy()))], "effect", "must be finite")
    add([i + 1 for i in np.flatnonzero(_blank(df["effect"]).to_numpy())], "effect", "is missing")
    add(_bad_cells(df["se"], se), "se", "is not a number")
    add([i + 1 for i in np.flatnonzero((se <= 0).to_numpy())], "se", "must be greater than zero")
    add([i + 1 for i in np.flatnonzero(np.isinf(se.to_numpy(float)))], "se", "must be finite")
    add([i + 1 for i in np.flatnonzero(_blank(df["se"]).to_numpy())], "se", "is missing, so the row is excluded as low_exposure", "warning")
    for col in ("n_baseline", "n_variant"):
        n = _num(df[col])
        add(_bad_cells(df[col], n), col, "is not a number")
        add([i + 1 for i in np.flatnonzero((n < 0).to_numpy())], col, "must not be negative")
        arr = n.to_numpy(float)
        add([i + 1 for i in np.flatnonzero(np.isinf(arr))], col, "must be finite")
        add([i + 1 for i in np.flatnonzero(np.isfinite(arr) & ((n % 1) != 0).fillna(False).to_numpy())], col, "must be a whole number of units")
        add(_exceeds_max_count(df[col], arr), col, f"is too large (above 2**53 = {MAX_COUNT}, the largest exact count)")
        add([i + 1 for i in np.flatnonzero(_blank(df[col]).to_numpy())], col, "is missing")
    t: dict[str, pd.Series] = {}
    for col in _TIME:
        if col not in df.columns:
            continue
        raw = df[col]
        parsed = _times(raw)
        t[col] = parsed
        add(_bad_cells(raw, parsed), col, "is not an ISO-8601 timestamp")
        if col != "usable_after":
            add([i + 1 for i in np.flatnonzero(_blank(raw).to_numpy())], col, "is missing")
    if "started_at" in t and "ended_at" in t:
        add([i + 1 for i in np.flatnonzero((t["ended_at"] < t["started_at"]).to_numpy())], "ended_at", "is before started_at")
        add([i + 1 for i in np.flatnonzero((t["ended_at"] > pd.Timestamp(now)).to_numpy())], "ended_at",
            "is in the future: a result that is not final yet cannot be in a ledger (horizon)")
        if "usable_after" in t:
            bad = (t["usable_after"] < t["ended_at"]).to_numpy()
            add([i + 1 for i in np.flatnonzero(bad)], "usable_after",
                "is before ended_at: a row cannot be visible before its result is final (horizon)")
    key = df[["experiment_id", "variant_id", "metric_id"]].astype(str)
    dup = key.duplicated(keep=False).to_numpy()
    first_seen: dict[tuple, int] = {}
    for i in np.flatnonzero(dup):
        k = tuple(key.iloc[i])
        if k in first_seen:
            add([i + 1], "variant_id", f"duplicate of row {first_seen[k]} (same experiment_id, variant_id and metric_id)")
        else:
            first_seen[k] = int(i) + 1
    # The ledger row id is source:experiment:variant::metric, so two different triples can still give one id when a part holds a colon.
    composed = (key["experiment_id"] + ":" + key["variant_id"] + "::" + key["metric_id"]).to_numpy()
    seen_id: dict[str, int] = {}
    triple_of: dict[str, tuple] = {}
    colons = (key["variant_id"].str.contains("::", regex=False) | key["metric_id"].str.contains("::", regex=False)).to_numpy()
    for i, cid in enumerate(composed):
        if colons[i]:
            continue                                      # a "::" in a part is already an error of its own (above)
        if cid in seen_id and triple_of[cid] != tuple(key.iloc[i]):
            add([i + 1], "variant_id", f"row id collision with row {seen_id[cid]}: experiment_id, variant_id and metric_id of the two rows "
                                       f"differ but join to the same ledger row id {cid!r}; remove the colon from one of the ids")
        seen_id.setdefault(cid, i + 1)
        triple_of.setdefault(cid, tuple(key.iloc[i]))
    if "baseline_id" in df.columns:
        same = (df["baseline_id"].astype(str) == df["variant_id"].astype(str)) & (df["baseline_id"].astype(str).str.strip() != "")
        add([i + 1 for i in np.flatnonzero(same.to_numpy())], "baseline_id", "equals variant_id, so the row is excluded as duplicate_arm", "warning")
    if "status" in df.columns:
        from mootcourt.ledger import STATUSES

        bad = ~(_blank(df["status"]) | df["status"].astype(str).str.strip().isin(STATUSES))      # a Parquet null is missing, not the text None
        add([i + 1 for i in np.flatnonzero(bad.to_numpy())], "status", f"must be one of {', '.join(STATUSES)}")
    for col in ("variant_id", "metric_id"):
        has = df[col].astype(str).str.contains("::", regex=False)
        add([i + 1 for i in np.flatnonzero(has.to_numpy())], col,
            "must not contain '::' (the ledger joins variant and metric with it, so two different pairs could collide)")
    out.extend(_unit_violations(df, len(out)))
    for col in PROVENANCE:
        if col not in df.columns:
            out.append(Violation(0, col, "provenance column is missing", "warning"))
        else:
            empty = _blank(df[col])
            add([i + 1 for i in np.flatnonzero(empty.to_numpy())], col, "provenance value is empty", "warning")
    out.sort(key=lambda v: (v.severity != "error", v.row))
    return out


def _unit_key(unit: str, system: str) -> str:
    """The unit rows are pooled by. ``as_exported`` says only that the vendor's number was kept, and two vendors' numbers need not share a
    scale, so it is pooled per vendor (``as_exported:<source_system>``); every other unit has one meaning everywhere."""
    return f"{unit}:{system}" if unit == "as_exported" and system else unit


def _unit_violations(df: pd.DataFrame, already: int) -> list[Violation]:
    """Errors for an ``effect_unit`` outside ``UNITS`` and for rows of one cell that disagree on the unit."""
    if "effect_unit" not in df.columns:
        return []
    out: list[Violation] = []
    raw = df["effect_unit"]
    unit = raw.where(~_blank(raw), "absolute").astype(str).str.strip()
    for i in np.flatnonzero((~unit.isin(UNITS)).to_numpy()):
        out.append(Violation(int(i) + 1, "effect_unit", f"{unit.iloc[i]!r} is not one of {', '.join(UNITS)}"))
    if "source_system" in df.columns:
        system = df["source_system"].where(~_blank(df["source_system"]), "").astype(str).str.strip()
    else:
        system = pd.Series("", index=df.index)
    keys = [_unit_key(u, sy) for u, sy in zip(unit, system, strict=True)]
    cell = df["cell"].where(~_blank(df["cell"]), df["metric_id"]) if "cell" in df.columns else df["metric_id"]
    known = unit.isin(UNITS)
    for name, idx in pd.Series(range(len(df))).groupby(cell.astype(str).str.strip().to_numpy()):
        rows = [int(i) for i in idx if known.iloc[int(i)]]
        if not rows:
            continue
        first = rows[0]
        for i in rows[1:]:
            if keys[i] != keys[first]:
                out.append(Violation(i + 1, "effect_unit", f"unit {keys[i]!r} differs from {keys[first]!r} used by row {first + 1} in cell "
                                                          f"{name!r}; rows pooled in one cell must share a unit"))
    return out[: max(MAX_REPORTED - already, 0)]


def _unit_parts(features_json: str) -> tuple[str, str]:
    """The ``effect_unit`` and the ``source_system`` a ledger row's features record."""
    try:
        feats = json.loads(features_json) or {}
        prov = feats.get("provenance") or {}
        return str(feats.get("effect_unit") or "absolute"), str(prov.get("source_system") or "")
    except (ValueError, TypeError, AttributeError):
        return "absolute", ""


def _unit_of(features_json: str) -> str:
    return _unit_key(*_unit_parts(features_json))


def ledger_unit_violations(ledger: pd.DataFrame) -> list[Violation]:
    """Units of a ledger: each row's ``effect_unit`` must be in ``UNITS`` and agree with the first row of its (source, cell) group
    (``as_exported`` is compared together with the vendor, see ``_unit_key``). Rows are numbered from 1."""
    out: list[Violation] = []
    first: dict[tuple, tuple[int, str]] = {}
    for i, (s, c, f) in enumerate(zip(ledger["source"], ledger["cell"], ledger["features_json"], strict=True), 1):
        unit, system = _unit_parts(f)
        if unit not in UNITS:
            out.append(Violation(i, "effect_unit", f"{unit!r} is not one of {', '.join(UNITS)}"))
            continue
        key = _unit_key(unit, system)
        if (s, c) not in first:
            first[(s, c)] = (i, key)
        elif first[(s, c)][1] != key:
            j, other = first[(s, c)]
            out.append(Violation(i, "effect_unit", f"unit {key!r} differs from {other!r} used by row {j} in cell {c!r} of source {s!r}; "
                                                  "rows pooled in one cell must share a unit"))
    return out[:MAX_REPORTED]


def unit_conflicts(existing: pd.DataFrame, new: pd.DataFrame) -> list[str]:
    """Messages for cells of ``new`` whose unit differs from the unit the same cell already has in ``existing`` (same source).

    Rows pooled in one cell must share a unit across imports as well as within one file.
    """
    out: list[str] = []
    if new.empty or existing.empty:
        return out
    old = existing[existing["source"].isin(new["source"].unique())]
    if old.empty:
        return out
    have = {(s, c): _unit_of(f) for s, c, f in zip(old["source"], old["cell"], old["features_json"], strict=True)}
    for s, c, f in zip(new["source"], new["cell"], new["features_json"], strict=True):
        u = _unit_of(f)
        if (s, c) in have and have[(s, c)] != u:
            out.append(f"cell {c!r} of source {s!r} already holds rows with effect_unit {have[(s, c)]!r}; the new rows use {u!r}, "
                       "and rows pooled in one cell must share a unit. Use another --source-name or convert the effects to the same unit.")
            break
    return out


def errors_of(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.severity == "error"]


def _txt(r, d: pd.DataFrame, col: str) -> str:
    """The stripped text of a cell, empty when the column is absent or the value is missing."""
    if col not in d.columns:
        return ""
    v = r[col]
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("nan", "None", "NaT") else str(v).strip()


def _bool(v) -> bool | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip().lower()
    if s in ("true", "t", "1", "yes", "y"):
        return True
    if s in ("false", "f", "0", "no", "n"):
        return False
    return None


def to_ledger(df: pd.DataFrame, source: str, min_exposure: int = MIN_EXPOSURE_DEFAULT, usable_delay_days: float = 0.0,
              now: dt.datetime | None = None) -> pd.DataFrame:
    """Convert a checked exchange frame to ledger rows with source ``source``.

    ``test_id`` is the experiment, ``variant_id`` is ``<variant>::<metric>`` so the metric is part of the row key, and the cell
    defaults to the metric id. Status: the given ``status`` if present, else ``duplicate_arm`` (variant equals baseline),
    ``imbalance_flag`` (sample ratio mismatch flag), ``low_exposure`` (a missing standard error, with ``exclusion_detail``
    ``missing_variance``, or fewer than ``min_exposure`` units in an arm), else ``admitted``. ``usable_after`` defaults to
    ``ended_at`` plus ``usable_delay_days``. Raises ExchangeError when the frame has error-level violations.
    """
    errs = errors_of(check_exchange(df, now))
    if errs:
        raise ExchangeError(errs)
    d = df.reset_index(drop=True)
    eff, se = _num(d["effect"]).to_numpy(float), _num(d["se"]).to_numpy(float)
    nb, nv = _num(d["n_baseline"]).to_numpy(float), _num(d["n_variant"]).to_numpy(float)
    start, end = _times(d["started_at"]), _times(d["ended_at"])
    ua = end + pd.Timedelta(days=usable_delay_days)
    if "usable_after" in d.columns:
        ua = _times(d["usable_after"]).fillna(ua)
    rows = []
    for i in range(len(d)):
        r = d.iloc[i]
        detail = None
        given, base = _txt(r, d, "status"), _txt(r, d, "baseline_id")
        if given and given != "admitted":
            status = given                     # a stated exclusion is kept; a stated "admitted" cannot lift a derived one (REV-033)
        elif base and base == str(r["variant_id"]):
            status = "duplicate_arm"
        elif _bool(_txt(r, d, "srm_flag")):
            status = "imbalance_flag"
        elif not (math.isfinite(se[i]) and se[i] > 0):
            status, detail = "low_exposure", "missing_variance"
        elif min(nb[i], nv[i]) < min_exposure:
            status = "low_exposure"
        else:
            status = "admitted"
        unit = _txt(r, d, "effect_unit") or "absolute"
        feats: dict = {"metric_id": str(r["metric_id"]), "effect_unit": unit}
        if detail:
            feats["exclusion_detail"] = detail
        if _txt(r, d, "headline"):
            feats["headline"] = _txt(r, d, "headline")
        for c in d.columns:
            if c.startswith("feature_") and _txt(r, d, c):
                feats[c[len("feature_"):]] = r[c] if not isinstance(r[c], (np.generic,)) else r[c].item()
        prov = {c: (_txt(r, d, c) or None) for c in PROVENANCE}
        for c in ("cuped", "sequential", "winsorized", "multiple_comparison", "numerator", "denominator", "decision", "decision_threshold"):
            if _txt(r, d, c):
                prov[c] = _bool(_txt(r, d, c)) if c in ("cuped", "sequential", "winsorized") else _txt(r, d, c)
        feats["provenance"] = {k: v for k, v in prov.items() if v is not None}
        cell = _txt(r, d, "cell") or str(r["metric_id"])
        vid = f"{r['variant_id']}::{r['metric_id']}"
        rows.append({
            "row_id": make_row_id(source, str(r["experiment_id"]), vid), "source": source, "test_id": str(r["experiment_id"]), "variant_id": vid,
            "cell": cell, "period": quarter_of(end.iloc[i]), "started_at": start.iloc[i], "final_read_at": end.iloc[i], "usable_after": ua.iloc[i],
            "y": float(eff[i]), "s": float(se[i]) if math.isfinite(se[i]) and se[i] > 0 else float("nan"),
            "n_ref": int(nb[i]), "n_var": int(nv[i]), "status": status,
            "features_json": json.dumps(feats, sort_keys=True), "schema_version": SCHEMA_VERSION,
        })
    out = pd.DataFrame(rows, columns=LEDGER_COLUMNS) if rows else pd.DataFrame({c: [] for c in LEDGER_COLUMNS})
    out["y"], out["s"] = out["y"].astype("float64"), out["s"].astype("float64")
    out["n_ref"], out["n_var"] = out["n_ref"].astype("int64"), out["n_var"].astype("int64")
    out["schema_version"] = out["schema_version"].astype("int64")
    for c in ("started_at", "final_read_at", "usable_after"):
        out[c] = pd.to_datetime(out[c], utc=True)
    bad_adm = (out["status"] == "admitted") & ~(np.isfinite(out["y"]) & (out["s"] > 0))
    out.loc[bad_adm, "status"] = "low_exposure"
    validate_ledger(out)
    return out


def admission_summary(ledger: pd.DataFrame) -> dict:
    """Counts for ``--dry-run``: rows by status, admitted rows by cell, experiments and the date span of admitted rows."""
    adm = ledger[ledger["status"] == "admitted"]
    return {"rows": int(len(ledger)), "experiments": int(ledger["test_id"].nunique()),
            "by_status": {k: int(v) for k, v in ledger["status"].value_counts().sort_index().items()},
            "admitted_by_cell": {k: int(v) for k, v in adm["cell"].value_counts().sort_index().items()},
            "first_final_read": None if adm.empty else adm["final_read_at"].min().isoformat(),
            "last_final_read": None if adm.empty else adm["final_read_at"].max().isoformat()}


def delta_method_ratio_se(n_b: float, mean_num_b: float, mean_den_b: float, var_num_b: float, var_den_b: float, cov_b: float,
                          n_v: float, mean_num_v: float, mean_den_v: float, var_num_v: float, var_den_v: float, cov_v: float) -> tuple[float, float]:
    """Effect and standard error of a ratio metric (sum of numerators over sum of denominators) by the delta method.

    Per arm the ratio is ``R = mean_num / mean_den`` with ``Var(R) = (var_num / mean_den^2 - 2 mean_num cov / mean_den^3 +
    mean_num^2 var_den / mean_den^4) / n``, where the variances and the covariance are per randomization unit. The effect is
    ``R_variant - R_baseline`` and ``se = sqrt(Var(R_v) + Var(R_b))``. Raises ValueError for a non-positive denominator mean or count.

    A library helper: no reader or mapping calls it (an export that carries per-arm means, variances and a covariance needs it, and
    none of the documented formats does). Use it to prepare the ``effect`` and ``se`` columns of an exchange file.
    """
    if min(n_b, n_v) <= 0 or min(mean_den_b, mean_den_v) <= 0:
        raise ValueError("counts and denominator means must be positive")

    def var(n, mn, md, vn, vd, c):
        return (vn / md ** 2 - 2.0 * mn * c / md ** 3 + mn ** 2 * vd / md ** 4) / n

    r_b, r_v = mean_num_b / mean_den_b, mean_num_v / mean_den_v
    total = var(n_b, mean_num_b, mean_den_b, var_num_b, var_den_b, cov_b) + var(n_v, mean_num_v, mean_den_v, var_num_v, var_den_v, cov_v)
    if total < 0:
        raise ValueError("the variance estimate is negative; check the covariance")
    return r_v - r_b, math.sqrt(total)
