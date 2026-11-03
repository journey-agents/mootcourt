"""The ledger: one row per concluded variant contrast, with admission recorded as a status.

Units: ``y`` is the observed effect and ``s`` its standard error, both on the same scale (percentage points of
click-through rate for Upworthy, the metric's own units or standardized units for other sources).

Origin semantics: a predictor standing at ``origin`` may see a row only when its status is
``admitted`` and ``usable_after <= origin``. The comparison is inclusive: a row whose ``usable_after``
equals the origin is visible, a row one microsecond later is not.

Admission is a status, never a filter. Excluded rows stay in the file and in every snapshot; callers
decide the status and this module validates it. All timestamps are timezone-aware UTC.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt.storage import safe_chmod, visible_iterdir

SCHEMA_VERSION = 1

LEDGER_COLUMNS = [
    "row_id", "source", "test_id", "variant_id", "cell", "period",
    "started_at", "final_read_at", "usable_after", "y", "s",
    "n_ref", "n_var", "status", "features_json", "schema_version",
]

ADMITTED = "admitted"
STATUSES = ("admitted", "low_exposure", "low_clicks", "imbalance_flag", "missing_text", "single_arm", "duplicate_arm")

EXCLUSION_REASONS = {
    "admitted": "admitted",
    "low_exposure": "fewer than 1000 exposures in at least one arm",
    "low_clicks": "fewer than 10 clicks in at least one arm",
    "imbalance_flag": "randomization imbalance flag is set",
    "missing_text": "a headline is empty",
    "single_arm": "the test has only one package, so there is no contrast",
    "duplicate_arm": "the variant is identical to the reference arm",
}

_STRING_COLUMNS = ["row_id", "source", "test_id", "variant_id", "cell", "period", "status", "features_json"]
_TIME_COLUMNS = ["started_at", "final_read_at", "usable_after"]
_FLOAT_COLUMNS = ["y", "s"]
_INT_COLUMNS = ["n_ref", "n_var", "schema_version"]


class LedgerSchemaError(ValueError):
    """The frame does not match the ledger schema."""


class SnapshotExistsError(FileExistsError):
    """A snapshot with this id already exists and snapshots are immutable."""


class LedgerConflictError(ValueError):
    """An append tried to change a row that already exists."""


def exclusion_reason(status: str) -> str:
    """Return the plain-language reason for a status; raise LedgerSchemaError for an unknown status."""
    try:
        return EXCLUSION_REASONS[status]
    except KeyError:
        raise LedgerSchemaError(f"unknown status {status!r}; expected one of {STATUSES}") from None


def metric_of(features_json: str) -> str:
    """The metric id a row carries in its features (imported ledgers record ``metric_id``), or "" for single-metric sources."""
    try:
        return str((json.loads(features_json) or {}).get("metric_id", ""))
    except (ValueError, TypeError, AttributeError):
        return ""


def make_row_id(source: str, test_id: str, variant_id: str) -> str:
    """Stable row id: ``source:test_id:variant_id``."""
    return f"{source}:{test_id}:{variant_id}"


def resolve_row_id(source: str, row_id: str | None = None, test_id: str | None = None, variant_id: str | None = None) -> str | None:
    """The ledger row id a card is joined to: ``row_id`` as given, or ``make_row_id(source, test_id, variant_id)``; None when neither is given.

    Raises ValueError when both forms are given, when only one of ``test_id`` and ``variant_id`` is given, or when a part is empty or
    contains a newline (the id is a file-safe key, and the join matches it exactly).
    """
    if row_id is not None and (test_id is not None or variant_id is not None):
        raise ValueError("give either a row id or a test id with a variant id, not both")
    if row_id is None and test_id is None and variant_id is None:
        return None
    if row_id is None:
        if not test_id or not variant_id:
            raise ValueError("a ledger row key needs both a test id and a variant id")
        row_id = make_row_id(source, test_id, variant_id)
    if not str(row_id).strip() or "\n" in str(row_id):
        raise ValueError("the row id must be a non-empty single line")
    return str(row_id)


def to_utc(ts) -> pd.Timestamp:
    """Coerce a datetime-like to a timezone-aware UTC Timestamp; naive values are rejected."""
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware UTC; got a naive value")
    return t.tz_convert("UTC")


def timestamp_ns(ts) -> int:
    """Nanoseconds since the Unix epoch of a timezone-aware timestamp."""
    return int(to_utc(ts).as_unit("ns").value)


def series_ns(series: pd.Series) -> np.ndarray:
    """Nanoseconds since the Unix epoch of a timezone-aware datetime series, as int64."""
    return series.dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()


def quarter_of(ts) -> str:
    """Calendar quarter label of a timestamp in UTC, for example ``2014Q3``."""
    t = pd.Timestamp(ts)
    if t.tzinfo is not None:
        t = t.tz_convert("UTC")
    return f"{t.year}Q{(t.month - 1) // 3 + 1}"


def validate_ledger(df: pd.DataFrame) -> None:
    """Raise LedgerSchemaError unless ``df`` is a valid ledger frame.

    Checks: exactly the 16 columns, dtypes, timezone-aware UTC timestamps, unique ``row_id``, known
    ``status`` and ``schema_version`` equal to 1. ``y`` and ``s`` may be NaN only on non-admitted
    rows; an admitted row needs finite ``y`` and finite ``s > 0`` (same units as ``y``).
    """
    cols = list(df.columns)
    missing = [c for c in LEDGER_COLUMNS if c not in cols]
    extra = [c for c in cols if c not in LEDGER_COLUMNS]
    if missing:
        raise LedgerSchemaError(f"missing columns: {missing}")
    if extra:
        raise LedgerSchemaError(f"unexpected columns: {extra}")
    for c in _STRING_COLUMNS:
        if not df[c].map(lambda v: isinstance(v, str)).all():
            raise LedgerSchemaError(f"column {c} must hold strings only")
    for c in _TIME_COLUMNS:
        dtype = df[c].dtype
        if not isinstance(dtype, pd.DatetimeTZDtype):
            raise LedgerSchemaError(f"column {c} must be timezone-aware UTC datetimes, got {dtype}")
        if str(dtype.tz) != "UTC":
            raise LedgerSchemaError(f"column {c} must be in UTC, got {dtype.tz}")
        if df[c].isna().any():
            raise LedgerSchemaError(f"column {c} has missing timestamps")
    for c in _FLOAT_COLUMNS:
        if not pd.api.types.is_float_dtype(df[c]):
            raise LedgerSchemaError(f"column {c} must be float, got {df[c].dtype}")
    for c in _INT_COLUMNS:
        if not pd.api.types.is_integer_dtype(df[c]):
            raise LedgerSchemaError(f"column {c} must be integer, got {df[c].dtype}")
    if df["row_id"].duplicated().any():
        raise LedgerSchemaError("duplicate row_id")
    bad = sorted(set(df["status"]) - set(STATUSES))
    if bad:
        raise LedgerSchemaError(f"unknown status values: {bad}")
    if (df["schema_version"] != SCHEMA_VERSION).any():
        raise LedgerSchemaError(f"schema_version must be {SCHEMA_VERSION}")
    admitted = df["status"] == ADMITTED
    y, s = df.loc[admitted, "y"].to_numpy(), df.loc[admitted, "s"].to_numpy()
    if not np.isfinite(y).all():
        raise LedgerSchemaError("admitted rows need a finite y")
    if not (np.isfinite(s).all() and (s > 0).all()):
        raise LedgerSchemaError("admitted rows need a finite s greater than zero")


def visible_rows(df: pd.DataFrame, origin, cell: str | None = None) -> pd.DataFrame:
    """Rows a predictor standing at ``origin`` may see.

    Returns rows with status ``admitted`` and ``usable_after <= origin`` (inclusive, to the
    microsecond), optionally restricted to one cell. ``origin`` must be timezone-aware.
    """
    t = to_utc(origin)
    mask = (df["status"] == ADMITTED) & (df["usable_after"] <= t)
    if cell is not None:
        mask &= df["cell"] == cell
    return df.loc[mask]


def write_ledger(df: pd.DataFrame, path) -> Path:
    """Validate and write the ledger to parquet atomically; excluded rows are kept."""
    validate_ledger(df)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(fd)
    try:
        df.to_parquet(tmp, index=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def read_ledger(path) -> pd.DataFrame:
    """Read a ledger parquet file and validate it."""
    df = pd.read_parquet(path)
    df = df[LEDGER_COLUMNS] if set(LEDGER_COLUMNS) <= set(df.columns) else df
    validate_ledger(df)
    return df.reset_index(drop=True)


def content_digest(df: pd.DataFrame) -> str:
    """Full sha256 hex of the canonical ledger content.

    Rows are sorted by ``row_id``; columns are taken in schema order; timestamps enter as UTC nanoseconds
    (so the storage resolution does not matter), floats as IEEE bytes with one pattern for NaN, integers as
    int64 and strings as UTF-8 with a separator that cannot occur in the text. The digest therefore does not
    depend on row order, and it changes when any value of any row changes, ids included.
    """
    order = np.argsort(df["row_id"].to_numpy(dtype=object).astype(str), kind="stable")
    h = hashlib.sha256()
    h.update(f"schema_version={SCHEMA_VERSION};rows={len(df)}\n".encode())
    for c in LEDGER_COLUMNS:
        col = df[c].iloc[order]
        h.update(f"|{c}|".encode())
        if c in _TIME_COLUMNS:
            h.update(series_ns(col).tobytes())
        elif c in _FLOAT_COLUMNS:
            v = col.to_numpy(np.float64).copy()
            v[np.isnan(v)] = np.nan                     # one NaN bit pattern
            h.update(v.tobytes())
        elif c in _INT_COLUMNS:
            h.update(col.to_numpy(np.int64).tobytes())
        else:
            h.update("\x1f".join(col.astype(str).tolist()).encode("utf-8"))
    return h.hexdigest()


def snapshot_id(df: pd.DataFrame, today: dt.date | None = None) -> str:
    """Snapshot id ``YYYYMMDD-<12 hex>``.

    The hex part is the first 12 characters of the canonical content digest (``content_digest``), so it does
    not depend on row order and changes when a row id is added or removed and also when any value of any
    row changes. ``today`` is injectable for tests; the default is the current UTC date.
    """
    day = today or dt.datetime.now(dt.timezone.utc).date()
    return f"{day:%Y%m%d}-{content_digest(df)[:12]}"


def snapshots_dir(ledger_dir) -> Path:
    """Directory holding immutable snapshot folders."""
    return Path(ledger_dir) / "snapshots"


def write_snapshot(df: pd.DataFrame, ledger_dir, today: dt.date | None = None) -> str:
    """Write an immutable copy of the ledger to ``<ledger_dir>/snapshots/<id>/`` and return the id.

    Files are made read-only. Raises SnapshotExistsError if the id already exists.
    """
    validate_ledger(df)
    sid = snapshot_id(df, today=today)
    root = snapshots_dir(ledger_dir)
    final = root / sid
    if final.exists():
        raise SnapshotExistsError(f"snapshot {sid} already exists")
    root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=root, prefix=".tmp-"))
    try:
        write_ledger(df, tmp / "ledger.parquet")
        manifest = {
            "snapshot_id": sid,
            "content_digest": content_digest(df),
            "schema_version": SCHEMA_VERSION,
            "n_rows": int(len(df)),
            "status_counts": {k: int(v) for k, v in df["status"].value_counts().items()},
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        for p in visible_iterdir(tmp):
            safe_chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        os.rename(tmp, final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return sid


def read_snapshot(ledger_dir, sid: str) -> pd.DataFrame:
    """Read the ledger frame stored in snapshot ``sid``."""
    return read_ledger(snapshots_dir(ledger_dir) / sid / "ledger.parquet")


def latest_snapshot(ledger_dir) -> str | None:
    """Id of the newest snapshot (date prefix, then directory mtime), or None when there is none."""
    root = snapshots_dir(ledger_dir)
    if not root.is_dir():
        return None
    found = [p for p in visible_iterdir(root) if p.is_dir()]
    if not found:
        return None
    return max(found, key=lambda p: (p.name.split("-")[0], p.stat().st_mtime_ns, p.name)).name


def append_rows(df: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Append ``new`` rows to ``df``; idempotent on ``row_id`` and never changes an existing row.

    A row in ``new`` whose id already exists must be identical (NaN equals NaN) or
    LedgerConflictError is raised. Returns a new frame; inputs are not modified.
    """
    validate_ledger(new)
    if new["row_id"].duplicated().any():
        raise LedgerSchemaError("duplicate row_id in the appended rows")
    known = new["row_id"].isin(set(df["row_id"]))
    if known.any():
        old = df.set_index("row_id").loc[new.loc[known, "row_id"]]
        incoming = new.loc[known].set_index("row_id")[list(old.columns)]
        same = ((old == incoming) | (old.isna() & incoming.isna())).all(axis=1)
        if not same.all():
            raise LedgerConflictError(f"rows would change: {sorted(same.index[~same.to_numpy()])[:5]}")
    fresh = new.loc[~known]
    if fresh.empty:                       # nothing to add: concatenating with an empty frame can turn timestamps into objects
        return df.copy()
    out = pd.concat([df, fresh], ignore_index=True)
    for c in _TIME_COLUMNS:               # frames written at different time resolutions meet here; settle on one dtype
        out[c] = pd.to_datetime(out[c], utc=True)
    validate_ledger(out)
    return out


def ensure_snapshot(df: pd.DataFrame, ledger_dir, today: dt.date | None = None) -> str:
    """Id of the snapshot that holds exactly these rows, writing one when none exists.

    Snapshot ids are ``<date>-<12 hex of the content digest>``. An existing snapshot is reused, whatever its
    date, only when its stored digest equals the digest of ``df``, so repeated runs on an unchanged ledger
    name the same snapshot and a ledger whose values changed gets a new one.
    """
    digest = content_digest(df)
    root = snapshots_dir(ledger_dir)
    if root.is_dir():
        for p in visible_iterdir(root):
            if p.is_dir() and p.name.split("-", 1)[-1] == digest[:12]:
                try:
                    stored = json.loads((p / "manifest.json").read_text(encoding="utf-8")).get("content_digest")
                except (OSError, ValueError):
                    stored = None
                if stored == digest:
                    return p.name
    return write_snapshot(df, ledger_dir, today=today)
