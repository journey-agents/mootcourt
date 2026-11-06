#!/usr/bin/env python3
"""Assemble a ``paper/data/<run>`` folder from a data root's reports and the previous run folder.

The new folder starts as a byte copy of the old one (so the files that are not rerun, such as ``gates.json``, ``scale/`` and ``run-log.json``,
stay byte-identical), then every JSON the reports directory holds under the layout of a run folder replaces the old one:
the three main backtests, the learning curves, the replays, the paper extras and ``card-latency.json`` at the top;
``ablations/backtest-*.json`` and ``ablations/p2-guard-*.json``;
``positive-control/backtest-synthetic-*.json``, its ``gates.json`` and ``reliability-synthetic.json``, and the backtest reports of the planted-ledger
folders under ``positive-control/rungs/<n>/``. Files of the old run that the new reports no longer have (an ablation that was renamed) are removed.
It prints the files that are new, replaced with different bytes, identical to the old run, and removed, so a README can list what was rerun.

Use: ``python scripts/assemble_run_folder.py REPORTS_DIR OLD_RUN_DIR NEW_RUN_DIR [--keep PATH ...]`` (``--keep`` names old files, relative to the run
folder, that are copied from the old run even when the reports have a file of that name).

Tier C update: ``python scripts/assemble_run_folder.py --update RUN_DIR REPORT [REPORT ...]`` copies only the named reports into the run folder
(a report under ``ablations/``, ``positive-control/`` or ``positive-control/rungs/<n>/`` keeps that place) and then checks the folder as a whole.
It refuses, and copies nothing, when the result would hold a stale dependent: a backtest whose header gates differ from the gates file beside it,
a file measured on a model that is not the model of any backtest in the folder, or a file of one source and snapshot with no backtest of that
source and snapshot. Rerun the stage that is stale and update it in the same call.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
import tempfile
from pathlib import Path

TOP = ("backtest-*.json", "learning-curve-*.json", "replay-*.json", "paper-extras-*.json", "gates-by-stratum-*.json")
# the ablation run that includes the randomization window (paper v2 plan, X1); its report sits in this folder
WINDOW_DIR = "include-randomization-window"
TOP_FILES = (
    "card-latency.json",
    "gates.json",
    "run-log.json",
    "leakage-audit-upworthy.json",
    "leakage-audit-asos.json",
    "leakage-audit-synthetic.json",
)


def collect(reports: Path) -> dict[str, Path]:
    """Relative path in a run folder -> source file under the reports directory."""
    out: dict[str, Path] = {}
    for pat in TOP:
        for f in sorted(reports.glob(pat)):
            out[f.name] = f
    for name in TOP_FILES:
        if (reports / name).is_file():
            out[name] = reports / name
    for pat in ("backtest-*.json", "p2-guard-*.json"):
        for f in sorted((reports / "ablations").glob(pat)):
            out[f"ablations/{f.name}"] = f
    for f in sorted((reports / WINDOW_DIR).glob("backtest-*.json")):
        out[f"{WINDOW_DIR}/{f.name}"] = f
    pc = reports / "positive-control"
    for name in ("gates.json", "reliability-synthetic.json"):
        if (pc / name).is_file():
            out[f"positive-control/{name}"] = pc / name
    for f in sorted(pc.glob("backtest-synthetic-*.json")):
        out[f"positive-control/{f.name}"] = f
    for sub in sorted((pc / "rungs").glob("*")) if (pc / "rungs").is_dir() else []:
        for f in sorted(sub.glob("backtest-synthetic-*.json")):
            out[f"positive-control/rungs/{sub.name}/{f.name}"] = f
        for f in sorted(sub.glob("backtest-synthetic-*.md")):
            out[f"positive-control/rungs/{sub.name}/{f.name}"] = f
    return out


def assemble(reports: Path, old: Path, new: Path, keep: tuple[str, ...] = ()) -> dict[str, list[str]]:
    if new.exists():
        raise SystemExit(f"{new} exists; remove it first")
    shutil.copytree(old, new)
    fresh = collect(reports)
    report: dict[str, list[str]] = {"new": [], "changed": [], "identical": [], "removed": []}
    old_rel = {
        str(p.relative_to(new)) for p in new.rglob("*") if p.is_file() and p.name != "README.md" and not str(p.relative_to(new)).startswith("scale/")
    }
    for rel, src in fresh.items():
        if rel in keep:
            continue
        dest = new / rel
        existed = dest.exists()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        if not existed:
            report["new"].append(rel)
        elif filecmp.cmp(old / rel, dest, shallow=False):
            report["identical"].append(rel)
        else:
            report["changed"].append(rel)
    for rel in sorted(old_rel - set(fresh) - set(keep)):
        if rel.startswith("positive-control/") and rel.endswith("gates.json"):
            report["identical"].append(rel)  # simulations and timings are copied from the old run on purpose
            continue
        (new / rel).unlink()
        report["removed"].append(rel)
    return report


def _relative_name(path: Path) -> str:
    """The place of a report in a run folder, from the folder it sits in."""
    parent = path.parent
    if parent.name == "ablations":
        return f"ablations/{path.name}"
    if parent.name == WINDOW_DIR:
        return f"{WINDOW_DIR}/{path.name}"
    if parent.name == "positive-control":
        return f"positive-control/{path.name}"
    if parent.parent.name == "rungs":
        return f"positive-control/rungs/{parent.name}/{path.name}"
    return path.name


def _load(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def stale_problems(run: Path) -> list[str]:
    """What is stale in a run folder: gates, models and snapshots that do not line up. Empty when the folder is consistent."""
    problems: list[str] = []
    mains = {p.name: _load(p) for p in sorted(run.glob("backtest-*.json"))}
    gates = _load(run / "gates.json").get("by_target")
    for name, doc in mains.items():
        held = doc.get("header", {}).get("gate_by_target")
        if gates is not None and held is not None and held != gates:
            problems.append(f"{name}: built with gates {json.dumps(held, sort_keys=True)}, but gates.json holds {json.dumps(gates, sort_keys=True)}; "
                            "rerun the backtest after the gates")
    models = {d.get("header", {}).get("model_id") for d in mains.values()} - {None}
    cl = run / "card-latency.json"
    if cl.is_file() and models:
        mid = _load(cl).get("model_id")
        if mid is not None and mid not in models:
            problems.append(f"card-latency.json: measured on model {mid}, but the backtests in the folder are model {', '.join(sorted(models))}; "
                            "rerun the card latency")
    stems = {n[len("backtest-"):] for n in mains}
    for prefix in ("learning-curve-", "replay-", "paper-extras-"):
        for f in sorted(run.glob(f"{prefix}*.json")):
            stem = f.name[len(prefix):]
            if stem not in stems:
                problems.append(f"{f.name}: no backtest of the same source and snapshot in the folder ({stem[:-5]}); rerun the backtest or the stage")
                continue
            hdr = _load(f).get("header", {})
            main_hdr = mains[f"backtest-{stem}"].get("header", {})
            for key in ("snapshot_id", "model_id"):
                if key in hdr and key in main_hdr and hdr[key] != main_hdr[key]:
                    problems.append(f"{f.name}: {key} {hdr[key]} differs from the backtest's {main_hdr[key]}")
    return problems


def update(run: Path, reports: list[Path]) -> dict[str, list[str]]:
    """Copy the named reports into ``run`` and refuse, copying nothing, if the folder would then hold a stale dependent."""
    if not run.is_dir():
        raise SystemExit(f"{run} is not a run folder")
    for r in reports:
        if not r.is_file():
            raise SystemExit(f"{r} is not a file")
    with tempfile.TemporaryDirectory() as tmp:
        trial = Path(tmp) / "trial"
        shutil.copytree(run, trial)
        for r in reports:
            dest = trial / _relative_name(r)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(r, dest)
        problems = stale_problems(trial)
    if problems:
        raise SystemExit("refusing to update, a stale dependent would remain:\n  " + "\n  ".join(problems))
    out: dict[str, list[str]] = {"new": [], "changed": [], "identical": []}
    for r in reports:
        rel = _relative_name(r)
        dest = run / rel
        kind = "new" if not dest.exists() else ("identical" if filecmp.cmp(r, dest, shallow=False) else "changed")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(r, dest)
        out[kind].append(rel)
    return out


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        ap = argparse.ArgumentParser(prog="assemble_run_folder.py --update", description="Copy only the named reports into a run folder.")
        ap.add_argument("run_dir")
        ap.add_argument("reports", nargs="+")
        a = ap.parse_args(sys.argv[2:])
        rep = update(Path(a.run_dir), [Path(x) for x in a.reports])
        for k, v in rep.items():
            print(f"{k}: {len(v)}")
            for x in v:
                print(f"  {x}")
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("reports_dir")
    ap.add_argument("old_run_dir")
    ap.add_argument("new_run_dir")
    ap.add_argument("--keep", nargs="*", default=[])
    a = ap.parse_args()
    rep = assemble(Path(a.reports_dir), Path(a.old_run_dir), Path(a.new_run_dir), tuple(a.keep))
    for k, v in rep.items():
        print(f"{k}: {len(v)}")
        for x in v:
            print(f"  {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
