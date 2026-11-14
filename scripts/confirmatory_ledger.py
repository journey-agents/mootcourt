#!/usr/bin/env python3
"""Build a ledger of its own from the Upworthy confirmatory packages file: the one guarded door to that file.

Every other script and the loader's callers read the exploratory file only, and ``scripts/download_data.py`` refuses the confirmatory,
holdout and undeployed files. The user decided on 14 November 2026 that the confirmatory file is read once, after the code is frozen and
the readings are registered (docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md, Part C). This script enforces the form of that
decision: it runs only with ``--decision 2026-11-14``, only on a file whose name says confirmatory, and only once (it refuses when its
output exists). It writes the ledger, its snapshot, and ``confirmatory-record.json`` beside it with the file's name, size and SHA-256, the
row counts and the time. The ledger holds the confirmatory rows only, so nothing fitted on the exploratory split is mixed with them.

Use: ``python scripts/confirmatory_ledger.py --file PATH --out DIR/data/ledger/ledger.parquet --decision 2026-11-14``
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from mootcourt.ledger import ensure_snapshot, write_ledger
from mootcourt.sources import upworthy

DECISION = "2026-11-14"
REFUSED = ("holdout", "undeployed", "exploratory")


def build(path, out, decision: str | None) -> dict:
    """The confirmatory ledger at ``out``; raises PermissionError unless the decision and the file name are the recorded ones."""
    path, out = Path(path), Path(out)
    if decision != DECISION:
        raise PermissionError("the confirmatory file is read only under the recorded decision; pass --decision with its date")
    name = path.name.lower()
    if "confirmatory" not in name or any(word in name for word in REFUSED):
        raise PermissionError(f"{path.name}: this script reads the confirmatory packages file and no other")
    if out.exists() or (out.parent / "confirmatory-record.json").exists():
        raise FileExistsError(f"{out.parent} already holds a confirmatory ledger; the file is read once")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    ledger = upworthy.load_upworthy(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_ledger(ledger, out)
    sid = ensure_snapshot(ledger.reset_index(drop=True), out.parent)
    doc = {"decision": decision, "file": path.name, "bytes": path.stat().st_size, "sha256": digest, "rows": int(len(ledger)),
           "admitted": int((ledger["status"] == "admitted").sum()), "tests": int(ledger["test_id"].nunique()), "snapshot": sid,
           "read_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (out.parent / "confirmatory-record.json").write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--decision", default=None)
    a = ap.parse_args(argv)
    try:
        doc = build(a.file, a.out, a.decision)
    except (PermissionError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(doc, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
