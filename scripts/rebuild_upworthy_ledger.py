#!/usr/bin/env python3
"""Rebuild the Upworthy rows of a ledger from the downloaded exploratory file under one setting of the randomization-window rule.

Paper v2 plan, D1: the main analysis gives the status ``imbalance_flag`` to every contrast of a test that started from 2013-06-25 to 2014-01-10
(``--window on``, the loader's default); ``--window off`` is run 7's configuration, the ablation ``include-randomization-window``.
``moot ingest`` never
changes a row that is already in the ledger, so a staging root built from run 7's ledger needs this explicit replacement. The other sources' rows are
untouched. The snapshot of the result is written (or reused when a snapshot holds exactly these rows, which is how ``--window off`` is seen to
regenerate run 7's ledger: it names run 7's snapshot).

Use: ``python scripts/rebuild_upworthy_ledger.py --window on|off [--ledger PATH] [--raw-dir DIR] [--out PATH] [--expect-digest HEX12]``.
Without ``--out`` the
ledger is rewritten in place. Needs MOOTCOURT_DATA_ROOT, or the paths given.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mootcourt.ledger import ensure_snapshot, read_ledger, replace_source, write_ledger
from mootcourt.sources import upworthy
from mootcourt.storage import storage_paths, visible_glob


def main() -> int:
    paths = storage_paths()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--window", choices=("on", "off"), required=True)
    ap.add_argument("--ledger", default=str(paths.ledger_path))
    ap.add_argument("--raw-dir", default=str(paths.raw))
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--expect-digest",
        default=None,
        help="exit 1 unless the Upworthy snapshot of the result ends with these 12 hex characters of the content digest "
        "(run 7's is 4bfb354b87e3: --window off must regenerate it)",
    )
    a = ap.parse_args()
    files = visible_glob(Path(a.raw_dir) / "upworthy", "*exploratory*packages*.csv")
    if not files:
        print(f"no exploratory Upworthy file under {a.raw_dir}/upworthy", file=sys.stderr)
        return 2
    ledger = read_ledger(a.ledger)
    new = upworthy.load_upworthy(files[0], exclude_randomization_window=(a.window == "on"))
    out = replace_source(ledger, new, "upworthy")
    dest = Path(a.out) if a.out else Path(a.ledger)
    write_ledger(out, dest)
    sid = ensure_snapshot(out[out["source"] == "upworthy"].reset_index(drop=True), dest.parent)
    n_flag = int((new["status"] == "imbalance_flag").sum())
    print(
        f"window {a.window}: {len(new)} Upworthy contrasts, {int((new['status'] == 'admitted').sum())} admitted, {n_flag} imbalance_flag; "
        f"snapshot {sid}; ledger {dest}"
    )
    if a.expect_digest and sid.split("-", 1)[-1] != a.expect_digest:
        print(f"expected a snapshot with content digest {a.expect_digest}, got {sid}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
