#!/usr/bin/env python3
"""Write the guarded-versus-unguarded P2 comparison of one source to ``<reports>/ablations/p2-guard-<source>.json``.

The main report is the guarded run; the unguarded run is the ablation written by ``moot backtest --p2-guard off``. Both must be on the
latest snapshot of the source. Use: ``python scripts/compare_guard.py --source upworthy``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from mootcourt.guard_compare import compare_guard
from mootcourt.storage import storage_paths, visible_glob


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", required=True)
    ap.add_argument("--reports-dir", default=None)
    ap.add_argument("--bootstrap", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    reports = Path(args.reports_dir) if args.reports_dir else storage_paths().reports
    main_json = visible_glob(reports, f"backtest-{args.source}-*.json")[-1]
    sid = main_json.stem.split(f"backtest-{args.source}-", 1)[1]
    off_json = reports / "ablations" / f"backtest-{args.source}-{sid}--p2-guard-off.json"
    gdoc, udoc = (json.loads(p.read_text(encoding="utf-8")) for p in (main_json, off_json))
    gs = pd.read_parquet(reports / f"scores-{args.source}-{sid}.parquet")
    us = pd.read_parquet(reports / "ablations" / f"scores-{args.source}-{sid}--p2-guard-off.parquet")
    doc = compare_guard(gs, us, gdoc, udoc, B=args.bootstrap, seed=args.seed)
    out = reports / "ablations" / f"p2-guard-{args.source}.json"
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
