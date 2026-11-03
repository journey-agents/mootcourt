#!/usr/bin/env python3
"""Write column inventories of the two downloaded files and the ledger counts their loaders produce.

Outputs ``reports/data-inventory-upworthy.txt`` and ``reports/data-inventory-asos.txt``. The five former-staff
columns of the Upworthy file are listed by name only; their values are never read. Run it from the repository root:
``python scripts/data_inventory.py [--raw-dir data/raw] [--out-dir reports]``. Paths are arguments; nothing is executed
from the data directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from mootcourt.sources import asos, upworthy
from mootcourt.storage import storage_paths

UPWORTHY_FILE = "upworthy-archive-exploratory-packages-03.12.2020.csv"


def _table(df: pd.DataFrame) -> list[str]:
    lines = [f"{'column':<24}{'dtype':<12}{'nulls':>10}"]
    lines += [f"{c:<24}{str(df[c].dtype):<12}{int(df[c].isna().sum()):>10}" for c in df.columns]
    return lines


def upworthy_text(path: Path) -> str:
    header = list(pd.read_csv(path, nrows=0).columns)
    read = [c for c in header if c in upworthy.COLUMNS_USED or c in upworthy.PACKAGE_ID_COLUMNS]
    df = pd.read_csv(path, usecols=read, dtype={"clickability_test_id": str, "eyecatcher_id": str})
    ledger = upworthy.load_upworthy(path)
    out = [f"Upworthy exploratory packages file: {path.name}", f"rows (packages): {len(df)}", f"tests: {df['clickability_test_id'].nunique()}",
           f"header columns: {header}", "", "Columns read (dtype and null count):"] + _table(df)
    out += ["", "Columns never read (names only): " + ", ".join(c for c in header if c in upworthy.FORMER_STAFF_COLUMNS),
            f"Package id column: none is named; the unnamed first column {upworthy.PACKAGE_ID_COLUMNS[-1]!r} is a unique increasing index "
            f"(unique: {df[upworthy.PACKAGE_ID_COLUMNS[-1]].is_unique if upworthy.PACKAGE_ID_COLUMNS[-1] in df.columns else 'n/a'})",
            f"'problem' column present: {'problem' in header}", "",
            "Ledger produced by load_upworthy:", json.dumps(upworthy.inventory(ledger), indent=1)]
    return "\n".join(out) + "\n"


def asos_text(path: Path) -> str:
    df = pd.read_parquet(path)
    ledger = asos.load_asos(path.parent)
    out = [f"ASOS parquet: {path.name}", f"rows: {len(df)}", f"experiments: {df['experiment_id'].nunique()}",
           f"treatments (experiment, variant): {df.groupby(['experiment_id', 'variant_id']).ngroups}",
           f"metric ids: {sorted(df['metric_id'].unique().tolist())}", "", "Columns (dtype and null count):"] + _table(df)
    out += ["", "Ledger produced by load_asos:", json.dumps(asos.inventory(ledger), indent=1)]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    paths = storage_paths()
    ap.add_argument("--raw-dir", default=str(paths.raw))
    ap.add_argument("--out-dir", default=str(paths.reports))
    args = ap.parse_args()
    raw, out = Path(args.raw_dir), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "data-inventory-upworthy.txt").write_text(upworthy_text(raw / "upworthy" / UPWORTHY_FILE), encoding="utf-8")
    (out / "data-inventory-asos.txt").write_text(asos_text(raw / "asos" / asos.PARQUET_NAME), encoding="utf-8")
    print(f"wrote {out}/data-inventory-upworthy.txt and {out}/data-inventory-asos.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
