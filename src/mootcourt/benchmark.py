"""Benchmarks: the scale run (``moot benchmark --scale N``) and the organization report card (``moot benchmark --ledger FILE``).

Scale run. It generates a synthetic ledger of N contrasts (the synthetic source, text signal on, two variants per test),
writes it under the experiments folder of the data root, and then times four things: the fit of a bundle (P0, P1 and P2 with
its selection), a backtest at the last few quarterly origins on a fixed sample of the rows scored at each origin, and a
number of issued cards against the fitted bundle, with the latency of each card. Peak resident memory is read from the
operating system after every stage (it only grows, so each value is the peak up to that point).

The backtest is deliberately smaller than the real one: a full rolling-origin backtest scores every row, and at a million
rows scoring each against every earlier row is hours of work that says nothing new about the size limits. The history
before each origin is complete; only the rows scored at the last origins are a seeded random sample, and the sample size is
in the output.

Units: times are seconds, latencies milliseconds, memory bytes. The report goes to ``reports/scale-<N>.json``; the ledger
and the other files of a run go under ``experiments/scale/`` of the storage root, never into the repository.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import platform
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt.config import BOOTSTRAP_RESAMPLES
from mootcourt.harness_stats import LEVEL
from mootcourt.settings import load_settings

SCALE_SCHEMA_VERSION = 1
DEFAULT_CARDS = 1000
DEFAULT_ORIGINS = 2
DEFAULT_SCORED_PER_ORIGIN = 2000
DEFAULT_SEED = 20261103
HEADLINE_WORDS = ("amazing", "secret", "dog", "teacher", "why", "how", "nobody", "everyone", "money", "future", "truth", "story",
                  "city", "river", "garden", "lesson", "dream", "history", "people", "idea")


def peak_rss_bytes() -> int:
    """Peak resident set size of this process in bytes (macOS reports bytes, Linux kilobytes)."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform == "darwin" else raw * 1024)


def disk_snapshot(*paths) -> dict:
    """Free gigabytes of the volume of each path (a path that does not exist yet uses its nearest parent)."""
    out = {}
    for p in paths:
        q = Path(p).resolve()
        while not q.exists() and q != q.parent:
            q = q.parent
        du = shutil.disk_usage(q)
        out[str(p)] = {"free_gb": round(du.free / 1024**3, 2), "used_gb": round(du.used / 1024**3, 2), "total_gb": round(du.total / 1024**3, 2)}
    return out


def make_scale_ledger(n: int, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """A synthetic ledger of ``n`` contrasts (``n // 2`` tests of two variants) with a headline text signal."""
    from mootcourt.sources import synthetic as syn

    if n < 8:
        raise ValueError("a scale ledger needs at least 8 contrasts")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=seed, n_tests=n // 2, variants_per_test=2, text_effect_strength=1.0))
    return ledger


def sample_scored_rows(ledger: pd.DataFrame, origins, per_origin: int, seed: int) -> pd.DataFrame:
    """Keep every row except that, in each scored quarter, only ``per_origin`` randomly chosen rows are kept.

    History before the first scored origin is untouched, so each model is fitted on the full history of its origin
    (up to the thinning of the scored quarters themselves).
    """
    rng = np.random.default_rng(seed)
    keep = np.ones(len(ledger), bool)
    started = ledger["started_at"]
    for t in origins:
        idx = np.flatnonzero(((started >= t) & (started < t + pd.DateOffset(months=3))).to_numpy())
        if len(idx) > per_origin:
            drop = rng.choice(idx, size=len(idx) - per_origin, replace=False)
            keep[drop] = False
    return ledger.loc[keep].reset_index(drop=True)


def _percentiles(ms: list[float]) -> dict:
    a = np.asarray(ms, float)
    return {"n": int(a.size), "p50_ms": round(float(np.percentile(a, 50)), 3), "p95_ms": round(float(np.percentile(a, 95)), 3),
            "max_ms": round(float(a.max()), 3), "mean_ms": round(float(a.mean()), 3)}


def _reliability_for(ledger: pd.DataFrame, as_of) -> dict:
    cells = {c: {"as_of": as_of.isoformat(), "rolling_logscore": -2.0, "p0_rolling_logscore": -2.1, "brier_skill": 0.1, "n": 500,
                 "drifted": False, "consecutive_below": 0} for c in sorted(ledger["cell"].unique())}
    return {"source": "synthetic", "as_of": as_of.isoformat(), "cells": cells}


def issue_cards(bundle, ledger: pd.DataFrame, n_cards: int, seed: int) -> tuple[list[float], dict]:
    """Issue ``n_cards`` cards at the end of the ledger and return the latency of each in milliseconds and the status counts."""
    from mootcourt import card as card_mod

    rng = np.random.default_rng(seed)
    now = pd.Timestamp(ledger["usable_after"].max()).to_pydatetime() + dt.timedelta(days=1)
    reliability = _reliability_for(ledger, now - dt.timedelta(days=1))
    cells = [("headline_only", False, True), ("image_only", True, False), ("both", True, True)]
    latencies, status = [], {}
    for i in range(n_cards):
        words = rng.choice(HEADLINE_WORDS, size=int(rng.integers(3, 9)), replace=True)
        _cell, image_changed, headline_changed = cells[i % len(cells)]
        req = card_mod.CardRequest(source="synthetic", headline=" ".join(words) + f" {i}", image_changed=image_changed,
                                   impressions=int(rng.integers(5000, 60000)), origin=now, headline_changed=headline_changed)
        t = time.perf_counter()
        c = card_mod.build_card(bundle, req, reliability=reliability, now=now)
        latencies.append((time.perf_counter() - t) * 1000.0)
        status[c.abstention.status] = status.get(c.abstention.status, 0) + 1
    return latencies, status


def run_scale(n: int, *, experiments_dir, reports_dir, seed: int = DEFAULT_SEED, n_cards: int = DEFAULT_CARDS, n_origins: int = DEFAULT_ORIGINS,
              scored_per_origin: int = DEFAULT_SCORED_PER_ORIGIN, log=lambda msg: None) -> dict:
    """Run the scale benchmark for ``n`` contrasts and write ``reports/scale-<n>.json``; returns the document."""
    from mootcourt import harness
    from mootcourt.bundle import fit_bundle
    from mootcourt.ledger import write_ledger

    if n_cards < 1 or n_origins < 1 or scored_per_origin < 1:
        raise ValueError("--cards, --origins and --scored-per-origin must each be at least 1")
    out_dir = Path(experiments_dir) / "scale"
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    disk_before = disk_snapshot("/", out_dir)
    stages: dict[str, dict] = {}
    t_run = time.perf_counter()

    t = time.perf_counter()
    ledger = make_scale_ledger(n, seed)
    stages["generate"] = {"seconds": round(time.perf_counter() - t, 2), "peak_rss_bytes": peak_rss_bytes(), "rows": int(len(ledger))}
    log(f"generated {len(ledger)} contrasts in {stages['generate']['seconds']} s")

    t = time.perf_counter()
    ledger_path = out_dir / f"ledger-{n}.parquet"
    write_ledger(ledger, ledger_path)
    stages["write_ledger"] = {"seconds": round(time.perf_counter() - t, 2), "peak_rss_bytes": peak_rss_bytes(),
                              "file_bytes": int(ledger_path.stat().st_size), "path": str(ledger_path)}
    log(f"wrote {ledger_path} ({stages['write_ledger']['file_bytes'] / 1e6:.0f} MB)")

    t = time.perf_counter()
    bundle = fit_bundle(ledger, "synthetic", f"scale-{n}")
    stages["fit"] = {"seconds": round(time.perf_counter() - t, 2), "peak_rss_bytes": peak_rss_bytes(), "n_rows": int(bundle.n_rows),
                     "lambda_by_cell": bundle.parameters["lambda_by_cell"], "top_m": _top_m()}
    log(f"fit in {stages['fit']['seconds']} s")

    origins_all = harness.quarterly_origins(ledger)
    origins = origins_all[-n_origins:]
    sampled = sample_scored_rows(ledger, origins, scored_per_origin, seed + 1)
    t = time.perf_counter()
    rungs = {k: v for k, v in harness.default_rungs("synthetic", sampled).items() if k in ("P0", "P1", "P2")}
    scores = harness.rolling_origin(sampled, rungs, origins, source="synthetic")
    per_rung = scores.groupby("rung").agg(n=("row_id", "size"), logscore=("logscore", "mean"), brier_event=("brier_event", "mean"))
    rung_rows = {k: {"n": int(v["n"]), "logscore": round(float(v["logscore"]), 4), "brier_event": round(float(v["brier_event"]), 4)}
                 for k, v in per_rung.iterrows()}
    stages["backtest"] = {"seconds": round(time.perf_counter() - t, 2), "peak_rss_bytes": peak_rss_bytes(),
                          "origins": [o.isoformat() for o in origins], "scored_per_origin": int(scored_per_origin),
                          "n_scored_rows": int(scores["row_id"].nunique()), "rungs": rung_rows}
    log(f"backtest of {stages['backtest']['n_scored_rows']} rows at {len(origins)} origins in {stages['backtest']['seconds']} s")

    t = time.perf_counter()
    latencies, status = issue_cards(bundle, ledger, n_cards, seed + 2)
    stages["cards"] = {"seconds": round(time.perf_counter() - t, 2), "peak_rss_bytes": peak_rss_bytes(), "statuses": status,
                       **_percentiles(latencies)}
    log(f"{n_cards} cards, p50 {stages['cards']['p50_ms']} ms, p95 {stages['cards']['p95_ms']} ms")

    total = time.perf_counter() - t_run
    doc = {
        "schema_version": SCALE_SCHEMA_VERSION, "kind": "scale", "n_contrasts": int(n), "seed": int(seed), "synthetic": True,
        "wall_seconds": round(total, 2), "peak_rss_bytes": peak_rss_bytes(), "peak_rss_gb": round(peak_rss_bytes() / 1024**3, 2),
        "card_latency_ms": _percentiles(latencies), "under_one_second_per_card": bool(np.percentile(latencies, 95) < 1000.0),
        "fit_under_one_hour": bool(stages["fit"]["seconds"] < 3600.0), "stages": stages,
        "disk_before": disk_before, "disk_after": disk_snapshot("/", out_dir),
        "machine": {"platform": platform.platform(), "cpus": os.cpu_count(), "python": platform.python_version(), "numpy": np.__version__,
                    "pandas": pd.__version__},
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    path = reports_dir / f"scale-{n}.json"
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    doc["report_path"] = str(path)
    return doc


def _top_m() -> int:
    from mootcourt.config import TOP_M_NEIGHBORS

    return int(TOP_M_NEIGHBORS)


# ====================================================================== organization report card
CARD_SCHEMA_VERSION = 2
CARD_SECTIONS = ("Ledger", "Gates", "Ladder", "Decision value", "Calibration by precision", "Limitations")
LIMITATIONS = (
    "The forecast is only as good as the ledger it was fit on.",
    "The gates say whether a skill difference is decidable at this n, not whether the tool is useful.",
    "A precedent forecast never replaces running the experiment.",
)
QUICK_GATES = {"reps": 400, "B": 300}
QUICK_GATES_FILE = "gates-quick.json"
DEFAULT_CARD_BOOTSTRAP = BOOTSTRAP_RESAMPLES


def _replicates(path: Path) -> str:
    """``N replicates`` from the ``reps`` field of a gates file, or ``replicates not recorded``."""
    try:
        reps = json.loads(Path(path).read_text(encoding="utf-8")).get("reps")
    except (OSError, ValueError):
        reps = None
    return f"{int(reps)} replicates" if reps else "replicates not recorded"


def _num(v, nd: int = 3) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "n/a"
    return f"{v:.{nd}f}"


def _research_target(gates: dict) -> float | None:
    """The research screen's power target: the smallest target in the gates file (the rule ``harness_stats.gate_status`` uses)."""
    by_target = gates.get("by_target")
    return float(min(by_target, key=float)) if by_target else None


def _decidable_headings(card: dict) -> list[tuple[str, str]]:
    """``(column heading, ladder key)`` of the decidable columns, read from the targets in the gates file.

    The research column is left out when the file has one target, or when both targets are equal.
    """
    dec, res = card.get("decision_target"), card.get("research_target")
    cols = [(f"decidable at {dec:.2f}" if dec is not None else "decidable", "decidable")]
    if res is not None and res != dec:
        cols.append((f"decidable at {res:.2f}", "decidable_research"))
    return cols


def build_report_card(doc: dict, scores: pd.DataFrame, *, ledger_stem: str, snapshot_id: str, gates: dict, gates_source: str) -> dict:
    """Distil a backtest document (``report.build_document``) into the report card: aggregate numbers only.

    The card has no row id, test id, headline or cell name, so an organization can publish it without sharing its data.
    """
    h, t = doc["header"], doc["tables"]
    primary = h["primary_rung"]
    agg = [r for r in t["aggregate"] if r["cell"] == "ALL"]
    ladder = []
    for r in agg:
        if r["kind"] != "ladder":
            continue
        ladder.append({"rung": r["rung"], "n": r["n"], "n_tests": r["n_tests"], "brier_skill": r["brier_skill"],
                       "brier_skill_lo": r["brier_skill_lo"], "brier_skill_hi": r["brier_skill_hi"], "coverage_80": r["coverage_80"],
                       "coverage_90": r["coverage_90"], "abstention_rate": r["abstention_rate"], "decidable": r["decidable_by_tests"],
                       "decidable_research": r["decidable_research_by_tests"]})
    prim = next(r for r in ladder if r["rung"] == primary)
    events = scores.loc[scores["rung"] == primary, "event"].astype(float)
    ab = next((r for r in t["abstention"] if r["cell"] == "ALL"), {})
    dv = [{"policy": r["policy"], "rung": r["rung"], "K": r["K"], "n_tests": r["n_tests"], "captured_fraction": r["captured_fraction"]}
          for r in t["decision_value"] if r["origin"] == "ALL" and r.get("budget", 0.25) == 0.25
          and (r["policy"] != "p_win" or r["rung"] in {x["rung"] for x in ladder})]
    calib = [{"decile": r["decile"], "exposure_lo": r["exposure_lo"], "exposure_hi": r["exposure_hi"], "n": r["n"], "mean_p_sig": r["mean_p_sig"],
              "event_rate": r["event_rate"]} for r in t["calibration_by_precision"] if r["rung"] == primary]
    return {
        "report_card_schema_version": CARD_SCHEMA_VERSION, "kind": "benchmark_report_card", "ledger_name": ledger_stem,
        "snapshot_id": snapshot_id,
        "ledger": {"n_admitted": h["admitted_rows"], "n_tests": prim["n_tests"], "n_scored": h["scored_rows"],
                   "n_cells": int(scores["cell"].nunique()), "origins_scored": h["origins_scored"],
                   "first_origin": h["first_origin"], "last_origin": h["last_origin"],
                   "base_rate": float(events.mean()), "synthetic": bool(h["synthetic"])},
        "gates": {k: {kk: int(vv) for kk, vv in v.items()} for k, v in (gates.get("by_target") or {}).items()},
        "gates_source": gates_source, "decision_target": gates.get("decision_target"), "research_target": _research_target(gates),
        "interval_level": LEVEL,
        "ladder_primary": primary, "ladder": ladder,
        "abstention": {"rate": prim["abstention_rate"], "support": ab.get("support"), "novelty": ab.get("novelty"),
                       "reliability": ab.get("reliability"), "instability": ab.get("instability"), "n": ab.get("n")},
        "decision_value": dv, "calibration_by_precision": calib, "limitations": list(LIMITATIONS),
        "bootstrap_resamples": h["bootstrap_resamples"], "seed": h["seed"], "boundary": h["boundary"],
    }


def card_markdown(card: dict) -> str:
    """The fixed one-page layout: the same sections, tables and columns for every ledger."""
    led, ladder = card["ledger"], card["ladder"]
    lines = [f"# Benchmark report card: {card['ledger_name']}", ""]
    tag = " Synthetic ledger: the numbers describe generated data." if led["synthetic"] else ""
    lines += [f"Snapshot {card['snapshot_id']}. Report card schema version {card['report_card_schema_version']}.{tag}", ""]
    lines += ["## Ledger", "",
              f"- Admitted contrasts: {led['n_admitted']}; tests with a scored contrast: {led['n_tests']}; cells: {led['n_cells']}",
              f"- Scored rows: {led['n_scored']} over {led['origins_scored']} quarterly origins, "
              f"{str(led['first_origin'])[:10]} to {str(led['last_origin'])[:10]}",
              f"- Base rate of a significant positive result: {_num(led['base_rate'])}", ""]
    lines += ["## Gates", "", f"Rows needed before a skill difference is decidable ({card['gates_source']}).", "",
              "| power target | n at skill 0.20 | n at skill 0.10 |", "|---|---|---|"]
    for target, g in sorted(card["gates"].items()):
        lines.append(f"| {target} | {g.get('n_200', 'n/a')} | {g.get('n_400', 'n/a')} |")
    cols = _decidable_headings(card)
    level = round(float(card.get("interval_level", LEVEL)) * 100)
    lines += ["", "## Ladder", "", f"All cells pooled. Intervals are {level} percent, bootstrapped by test. "
                                   "Decidable is read from the gate by tests.", "",
              "| rung | n | tests | Brier skill | interval | coverage 80 | coverage 90 | abstention | " + " | ".join(h for h, _ in cols) + " |",
              "|" + "---|" * (8 + len(cols))]
    for r in ladder:
        interval = f"{_num(r['brier_skill_lo'])} to {_num(r['brier_skill_hi'])}"
        lines.append(f"| {r['rung']} | {r['n']} | {r['n_tests']} | {_num(r['brier_skill'])} | {interval} | {_num(r['coverage_80'])} | "
                     f"{_num(r['coverage_90'])} | {_num(r['abstention_rate'])} | " + " | ".join(str(r[k]) for _, k in cols) + " |")
    ab = card["abstention"]
    lines += ["", f"Abstention rate {_num(ab['rate'])} on {ab['n']} rows; triggers fired: support {ab['support']}, novelty {ab['novelty']}, "
                  f"reliability {ab['reliability']}, instability {ab['instability']}.", ""]
    lines += ["## Decision value", "", "Share of the total positive lift captured by the top quarter of tests, by policy.", "",
              "| policy | rung | tests chosen | share captured |", "|---|---|---|---|"]
    for r in card["decision_value"]:
        lines.append(f"| {r['policy']} | {r['rung']} | {r['K']} of {r['n_tests']} | {_num(r['captured_fraction'])} |")
    lines += ["", "## Calibration by precision", "", f"Rung {card['ladder_primary']}, scored rows in ten bands of planned exposure.", "",
              "| decile | n | mean p_sig | event rate |", "|---|---|---|---|"]
    for r in card["calibration_by_precision"]:
        lines.append(f"| {r['decile']} | {r['n']} | {_num(r['mean_p_sig'])} | {_num(r['event_rate'])} |")
    lines += ["", "## Limitations", ""] + [f"- {s}" for s in card["limitations"]]
    return "\n".join(lines) + "\n"


def run_report_card(ledger_path, reports_dir, *, source: str | None = None, seed: int = DEFAULT_SEED, bootstrap: int = DEFAULT_CARD_BOOTSTRAP,
                    log=lambda msg: None) -> dict:
    """Run the standard protocol on a ledger and write ``reports/benchmark/<ledger-stem>-<snapshot>.{md,json}``.

    The protocol is the one every other report uses: rolling quarterly origins, the ladder P0, P1 and P2 (and P3 when the
    ledger carries team forecasts), gates at both power targets, calibration by precision, abstention and decision value.
    Raises ValueError for a ledger that is missing, does not conform, or holds several sources when none is chosen.
    """
    from mootcourt import harness, simulate
    from mootcourt.ledger import LedgerSchemaError, read_ledger, snapshot_id
    from mootcourt.report import build_document

    path = Path(ledger_path)
    if not path.is_file():
        raise ValueError(f"the ledger file {path} does not exist")
    try:
        ledger = read_ledger(path)
    except (LedgerSchemaError, KeyError, ValueError, OSError) as exc:
        raise ValueError(f"{path} is not a conformant ledger: {exc}") from None
    sources = sorted(ledger["source"].unique())
    if source is None:
        if len(sources) != 1:
            raise ValueError(f"the ledger holds several sources ({', '.join(sources)}); choose one with --source")
        source = sources[0]
    elif source not in sources:
        raise ValueError(f"the ledger has no source {source!r}; it holds {', '.join(sources)}")
    ledger = ledger[ledger["source"] == source].reset_index(drop=True)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    gates_path = reports_dir / "gates.json"
    if gates_path.exists():
        gates_source = f"from {gates_path.name} ({_replicates(gates_path)})"
    else:
        # Quick gates never take the shared file's place (REV-024): `moot backtest`, `moot card` and the promotion gate read gates.json.
        gates_path = reports_dir / "benchmark" / QUICK_GATES_FILE
        gates_path.parent.mkdir(parents=True, exist_ok=True)
        if not gates_path.exists():
            simulate.write_gates(gates_path, target=load_settings()["gate"]["target_power"], reps=QUICK_GATES["reps"], B=QUICK_GATES["B"],
                                 with_table=False)
        gates_source = f"quick power simulation from {gates_path.name} ({_replicates(gates_path)}); run `moot simulate power` for the full gates"
    gates = simulate.load_gates(gates_path)
    sid = snapshot_id(ledger)
    log(f"scoring {len(ledger)} contrasts of source {source}")
    scores = harness.rolling_origin(ledger, harness.default_rungs(source, ledger), harness.quarterly_origins(ledger), source=source)
    doc = build_document(scores, ledger=ledger, source=source, snapshot_id=sid, model_id="benchmark", feature_hash="none",
                         command=f"moot benchmark --ledger {path.name}", seed=seed, gates=gates, B=bootstrap)
    card = build_report_card(doc, scores, ledger_stem=path.stem, snapshot_id=sid, gates=gates, gates_source=gates_source)
    out = reports_dir / "benchmark"
    out.mkdir(parents=True, exist_ok=True)
    md_path, js_path = out / f"{path.stem}-{sid}.md", out / f"{path.stem}-{sid}.json"
    md_path.write_text(card_markdown(card), encoding="utf-8")
    js_path.write_text(json.dumps(card, indent=1, sort_keys=False, default=str) + "\n", encoding="utf-8")
    card["paths"] = {"md": str(md_path), "json": str(js_path)}
    return card
