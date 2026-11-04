#!/usr/bin/env python3
"""Write ``score-report-<python>.json``: the scores of P0, P1 and P2 on a small fixed-seed backtest of the bundled sample ledger.

The continuous-integration job runs this on every Python version it tests and uploads the file as the workflow artifact
``score-report-<python>`` (round 01, R5 minor 8), so the paper can name the artifact instead of quoting a cross-platform number. The
backtest is the one ``moot init`` leads a newcomer to: the sample ledger of ``mootcourt.importers.sample`` (deterministic, seed 7, 120
experiments, three metrics, base rate ``SAMPLE_BASE_RATE``) imported through the generic exchange format, fit and scored by the harness at
its quarterly origins with the ladder only. For each rung the file holds the mean log score and the Brier skill against P0 over every
scored row, to six decimals, with the rows and tests they were measured on, and the Python, platform and numerical-library versions.

Nothing is downloaded and no data root is read or written: the ledger lives in a temporary folder for the length of the run.

Use: ``uv run python scripts/ci_score_report.py --out score-report-3.12.json`` (default name: ``score-report-<python>.json`` in the
working folder). ``build_report()`` returns the document.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata as md
import json
import platform
import sys
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1
RUNGS = ("P0", "P1", "P2")
PACKAGES = ("numpy", "scipy", "pandas", "scikit-learn")


def python_version() -> str:
    return ".".join(str(v) for v in sys.version_info[:3])


def build_report(seed: int = 0) -> dict:
    """The score report: a fixed-seed backtest of the sample ledger with P0, P1 and P2, every number rounded to six decimals."""
    from mootcourt.harness import default_rungs, quarterly_origins, rolling_origin
    from mootcourt.importers.ingest import import_file
    from mootcourt.importers.sample import N_EXPERIMENTS, SAMPLE_BASE_RATE, sample_exchange

    with tempfile.TemporaryDirectory() as folder:
        csv = Path(folder) / "sample.csv"
        sample_exchange().to_csv(csv, index=False)
        ledger, _warnings = import_file("generic", csv, "sample")
    rungs = default_rungs("sample", ledger)                       # the ladder only: P0, P1, P2
    scores = rolling_origin(ledger, rungs, quarterly_origins(ledger), source="sample")
    by_rung = {}
    for rung in RUNGS:
        g = scores[scores["rung"] == rung]
        brier, base = float(g["brier_event"].mean()), float(g["brier_base"].mean())
        by_rung[rung] = {
            "rows": int(len(g)),
            "tests": int(g["test_id"].nunique()),
            "logscore": round(float(g["logscore"].mean()), 6),
            "brier": round(brier, 6),
            "brier_skill": round(1.0 - brier / base, 6) if base > 0 else None,
        }
    p1 = scores[scores["rung"] == "P1"]
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": {k: md.version(k) for k in PACKAGES},
        "seed": int(seed),
        "ledger": {
            "generator": f"mootcourt.importers.sample.sample_exchange(seed=7, n_experiments={N_EXPERIMENTS}, base_rate={SAMPLE_BASE_RATE})",
            "import": "importers.ingest.import_file('generic', ..., 'sample')",
            "rows": int(len(ledger)),
            "scored_rows": int(len(p1)),
            "scored_tests": int(p1["test_id"].nunique()),
            "origins": int(p1["origin"].nunique()),
        },
        "rungs": by_rung,
        "definitions": {
            "logscore": "mean log density of the observed estimate under the rung's predictive over every scored row, nats",
            "brier_skill": "one minus the mean Brier of p_sig over the mean Brier of P0's visible event rate on the same rows (zero for P0)",
            "seed": "the harness's fixed seeds (generator 7, selection subsample 0); no bootstrap is computed here",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=None, help="where to write the JSON (default: score-report-<python>.json in the working folder)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else Path(f"score-report-{python_version()}.json")
    doc = build_report(seed=args.seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}: " + ", ".join(f"{r} log score {v['logscore']} skill {v['brier_skill']}" for r, v in doc["rungs"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
