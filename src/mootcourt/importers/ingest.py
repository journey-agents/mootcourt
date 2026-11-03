"""``moot ingest --format`` and ``moot ledger check``: the command-line side of the importers."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from mootcourt.importers.exchange import (
    MIN_EXPOSURE_DEFAULT,
    ExchangeError,
    admission_summary,
    check_exchange,
    errors_of,
    ledger_unit_violations,
    read_table,
    to_ledger,
)
from mootcourt.importers.vendors import MappingError, load_mapping, read_format


def import_file(fmt: str, path, source: str, mapping_path=None, min_exposure: int = MIN_EXPOSURE_DEFAULT, usable_delay_days: float = 0.0,
                now: dt.datetime | None = None, **options) -> tuple[pd.DataFrame, list]:
    """Read ``path`` in format ``fmt`` and return ``(ledger_rows, warnings)``.

    Raises ExchangeError (violations name the row and column), MappingError (the file lacks what the format needs) or FileNotFoundError.
    """
    mapping = load_mapping(mapping_path) if mapping_path else None
    frame = read_format(fmt, path, mapping=mapping, **options)
    violations = check_exchange(frame, now)
    if errors_of(violations):
        raise ExchangeError(errors_of(violations))
    ledger = to_ledger(frame, source, min_exposure=min_exposure, usable_delay_days=usable_delay_days, now=now)
    return ledger, [v for v in violations if v.severity != "error"]


def check_file(path, now: dt.datetime | None = None) -> list:
    """Violations of ``path`` against the exchange format, or against the ledger schema when the file is a ledger (has ``row_id``)."""
    df = read_table(path)
    if "row_id" in df.columns:
        return check_ledger_frame(Path(path), now)
    return check_exchange(df, now)


def check_ledger_frame(path: Path, now: dt.datetime | None = None) -> list:
    """Conformance of a ledger Parquet file: schema, duplicate ids, impossible values, horizon violations, missing provenance."""
    import json

    import numpy as np

    from mootcourt.importers.exchange import Violation
    from mootcourt.ledger import LedgerSchemaError, read_ledger, validate_ledger

    out: list[Violation] = []
    try:
        df = read_ledger(path)
        validate_ledger(df)
    except (LedgerSchemaError, ValueError, KeyError) as exc:
        return [Violation(0, "schema", str(exc))]
    now_t = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    for i in np.flatnonzero((df["usable_after"] < df["final_read_at"]).to_numpy()):
        out.append(Violation(int(i) + 1, "usable_after", "is before final_read_at (horizon violation)"))
    for i in np.flatnonzero((df["final_read_at"] < df["started_at"]).to_numpy()):
        out.append(Violation(int(i) + 1, "final_read_at", "is before started_at"))
    for i in np.flatnonzero((df["final_read_at"] > now_t).to_numpy()):
        out.append(Violation(int(i) + 1, "final_read_at", "is in the future (horizon violation)"))
    for i in np.flatnonzero(((df["n_ref"] < 0) | (df["n_var"] < 0)).to_numpy()):
        out.append(Violation(int(i) + 1, "n_ref", "exposures must not be negative"))
    for i, js in enumerate(df["features_json"]):
        try:
            prov = (json.loads(js) or {}).get("provenance")
        except ValueError:
            out.append(Violation(i + 1, "features_json", "is not valid JSON"))
            continue
        if df["source"].iat[i] not in ("upworthy", "asos", "synthetic") and not prov:
            out.append(Violation(i + 1, "features_json", "has no provenance block (source_system, variance_method)", "warning"))
    out += ledger_unit_violations(df)
    return out


def format_summary(summary: dict) -> str:
    lines = [f"{summary['rows']} rows from {summary['experiments']} experiments"]
    lines += [f"  {k}: {v}" for k, v in summary["by_status"].items()]
    if summary["admitted_by_cell"]:
        lines.append("admitted by cell: " + ", ".join(f"{k} {v}" for k, v in summary["admitted_by_cell"].items()))
    if summary["first_final_read"]:
        lines.append(f"final reads from {summary['first_final_read'][:10]} to {summary['last_final_read'][:10]}")
    return "\n".join(lines)


__all__ = ["import_file", "check_file", "format_summary", "admission_summary", "MappingError"]
