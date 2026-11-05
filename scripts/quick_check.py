#!/usr/bin/env python3
"""Tier B check: regenerate the sample ledger's backtest and diff it against the committed report.

The sample ledger is what ``moot init`` creates. This script runs ``init``, ``ingest``, ``fit`` and ``backtest`` for it in a temporary
project (its own data root, so nothing under the real data root is read or written) and compares the backtest report with
``tests/fixtures/quick-check/backtest-sample.json``. A change that must not move a number (CLI messages, the doctor, bookkeeping, tooling)
leaves the diff empty; any other result is a number that moved and the change belongs to Tier C.

The diff ignores what differs between runs by design: the header field ``model_id``, any ``created_at``, any field whose name ends in
``_seconds``, and the date prefix of a snapshot id (the digest after it is compared). Floats match to a relative 1e-9, except the fields
whose names end in ``_percentile`` or ``_percentile_independent``, which match to 2.0 percentile points. Those are ranks of the observed
calibration error within a Monte Carlo null of 500 draws, and the rank is not stable across platforms: a draw that reproduces the observed
per-bin event counts is a mathematical tie with the observed error, and whether floating point rounding puts it just below, equal or just
above depends on the order of the additions, which differs between CPU builds of numpy. Such draws count whole or half, so the percentile
moves by 0.2 points per draw; the Linux runs of the continuous integration differ from the Mac reference by up to 1.4 points and nothing
else differs. The null itself is drawn the same on both (a seeded PCG64 stream; no Cholesky factor and no matrix product).

    python scripts/quick_check.py                     # exit 0 when the diff is empty, 1 otherwise; prints the wall time
    python scripts/quick_check.py --write-reference   # regenerate the committed report (after a deliberate change of numbers)
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path("tests") / "fixtures" / "quick-check" / "backtest-sample.json"
SNAPSHOT = re.compile(r"\b\d{8}-([0-9a-f]{12})\b")
MAX_DIFFS = 40
PERCENTILE_TOLERANCE = 2.0          # percentile points, for the fields ending in _percentile or _percentile_independent
STEPS = (
    ("moot", "init", "--dir", "."),
    ("moot", "ingest", "--format", "generic", "--input", "mootcourt-data/data/sample-ledger.csv", "--source-name", "sample"),
    ("moot", "fit", "--source", "sample"),
    ("moot", "backtest", "--source", "sample"),
)


@dataclass
class QuickCheckResult:
    ok: bool
    diffs: list[str] = field(default_factory=list)
    seconds: float = 0.0


def _ignored(key: str) -> bool:
    return key in ("model_id", "created_at") or key.endswith("_seconds")


def _norm(value):
    return SNAPSHOT.sub(r"SNAPSHOT-\1", value) if isinstance(value, str) else value


def _is_percentile(key: str) -> bool:
    return key.endswith(("_percentile", "_percentile_independent"))


def diff_reports(ref, new, path: str = "", key: str = "") -> list[str]:
    """The differences between two report documents, one line each, apart from what the module docstring says is ignored."""
    out: list[str] = []
    if isinstance(ref, dict) and isinstance(new, dict):
        for k in sorted(set(ref) | set(new)):
            if _ignored(k):
                continue
            where = f"{path}.{k}" if path else k
            if k not in ref or k not in new:
                out.append(f"{where}: present in one report only")
            else:
                out += diff_reports(ref[k], new[k], where, k)
    elif isinstance(ref, list) and isinstance(new, list):
        if len(ref) != len(new):
            out.append(f"{path}: {len(ref)} entries != {len(new)} entries")
        else:
            for i, (a, b) in enumerate(zip(ref, new)):
                out += diff_reports(a, b, f"{path}[{i}]", key)
    elif isinstance(ref, float) or isinstance(new, float):
        same = isinstance(ref, (int, float)) and isinstance(new, (int, float)) and not isinstance(ref, bool) and not isinstance(new, bool) \
            and (ref == new or math.isclose(ref, new, rel_tol=1e-9, abs_tol=1e-12) or (math.isnan(ref) and math.isnan(new))
                 or (_is_percentile(key) and abs(ref - new) <= PERCENTILE_TOLERANCE * (1 + 1e-9)))
        if not same:
            out.append(f"{path}: {ref!r} != {new!r}")
    elif _norm(ref) != _norm(new) or type(ref) is not type(new):
        out.append(f"{path}: {ref!r} != {new!r}")
    return out


def _moot() -> list[str]:
    return [sys.executable, "-c", "import sys; from mootcourt.cli import app; sys.argv[0] = 'moot'; app()"]


@functools.cache
def regenerate() -> dict:
    """The sample ledger's backtest report, built in a temporary project; cached for the life of the process."""
    work = Path(tempfile.mkdtemp(prefix="moot-quick-check-"))
    try:
        env = {k: v for k, v in os.environ.items() if k != "MOOTCOURT_DATA_ROOT"}
        env["MOOTCOURT_DATA_ROOT"] = str(work / "mootcourt-data")
        for step in STEPS:
            done = subprocess.run(_moot() + list(step[1:]), cwd=work, env=env, capture_output=True, text=True)
            if done.returncode != 0:
                raise RuntimeError(f"`{' '.join(step)}` exited {done.returncode}:\n{(done.stdout + done.stderr)[-1500:]}")
        reports = sorted((work / "mootcourt-data" / "reports").glob("backtest-sample-*.json"))
        if not reports:
            raise RuntimeError("the backtest wrote no report")
        return json.loads(reports[-1].read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def quick_check(root: Path) -> QuickCheckResult:
    """Regenerate the sample backtest and diff it against ``root / REFERENCE``."""
    t0 = time.perf_counter()
    ref_path = Path(root) / REFERENCE
    if not ref_path.is_file():
        return QuickCheckResult(False, [f"{REFERENCE}: the committed sample report is missing"], time.perf_counter() - t0)
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    diffs = diff_reports(ref, regenerate())
    if len(diffs) > MAX_DIFFS:
        diffs = diffs[:MAX_DIFFS] + [f"... and {len(diffs) - MAX_DIFFS} more"]
    return QuickCheckResult(not diffs, diffs, time.perf_counter() - t0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write-reference", action="store_true", help="overwrite the committed sample report with a fresh one")
    a = ap.parse_args()
    if a.write_reference:
        t0 = time.perf_counter()
        dest = ROOT / REFERENCE
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(regenerate(), sort_keys=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"wrote {REFERENCE} in {time.perf_counter() - t0:.0f} s")
        return 0
    res = quick_check(ROOT)
    for d in res.diffs:
        print(f"DIFF {d}")
    verdict = "matches" if res.ok else "differs from"
    print(f"quick-check {'OK' if res.ok else 'FAILED'}: the sample backtest {verdict} {REFERENCE} ({res.seconds:.0f} s)")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
