"""Synthetic gate power: how many scored rows are needed before a skill claim can be decided.

The release gate asks whether a predictor's Brier score beats the constant base rate by a margin that a
95 percent bootstrap interval can resolve. This module simulates that gate on synthetic data only, so
every number it writes is labelled synthetic.

Simulation. For one replicate, ``n`` calibrated probabilities are drawn from a Beta distribution whose
mean is the base rate and whose variance is ``skill * base * (1 - base)``. For a calibrated forecaster
the Brier score is ``base (1 - base) - Var(p)``, so that variance gives Brier skill ``skill`` against the
constant base rate exactly. Outcomes are drawn from the probabilities. The per-row Brier difference
``(base - e)^2 - (p - e)^2`` is bootstrapped (rows are independent here, so the resampling is per row; a
caller with clustered rows should resample by test) and the replicate passes the gate when the lower end
of the 95 percent interval is above zero. Power is the share of replicates that pass.

Units: probabilities and Brier skill are unitless. The seed is fixed per call, so a result is a pure
function of its arguments.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import numpy as np

from mootcourt.storage import storage_paths

SYNTHETIC_LABEL = "synthetic"
DEFAULT_BASE = 0.30
DEFAULT_TARGET = 0.90          # the release gate: the decision target for decidable or undecidable
RESEARCH_TARGET = 0.80         # the research screen, reported beside the release gate
TARGETS = (RESEARCH_TARGET, DEFAULT_TARGET)
DEFAULT_REPS = 1000
DEFAULT_BOOTSTRAP = 500
DEFAULT_SEED = 20261102
DEFAULT_GRID = tuple(range(25, 801, 25)) + tuple(range(900, 3201, 100))
GATE_SKILLS = {"n_200": 0.20, "n_400": 0.10}
TABLE_NS = (100, 250, 500, 1000, 2000)
TABLE_SKILLS = (0.05, 0.10, 0.20, 0.30)
MAX_SECONDS = 180.0
RUN_HINT = "run `moot simulate power` to create it"


class PowerBudgetExceeded(RuntimeError):
    """The power run used more than its time cap; lower --reps or --bootstrap."""


def _check(n: int, skill: float, base: float) -> None:
    if int(n) != n or n < 2:
        raise ValueError("n must be an integer of at least 2")
    if not 0.0 <= skill < 1.0:
        raise ValueError("skill must be in [0, 1)")
    if not 0.0 < base < 1.0:
        raise ValueError("base must be strictly between 0 and 1")


def _beta_params(base: float, skill: float) -> tuple[float, float] | None:
    """Beta(a, b) with mean ``base`` and variance ``skill * base * (1 - base)``; None when skill is 0."""
    if skill == 0.0:
        return None
    var = skill * base * (1.0 - base)
    k = base * (1.0 - base) / var - 1.0          # a + b
    return base * k, (1.0 - base) * k


def gate_power(n: int, skill: float, base: float = DEFAULT_BASE, reps: int = DEFAULT_REPS, B: int = DEFAULT_BOOTSTRAP,
               seed: int = DEFAULT_SEED) -> float:
    """Share of ``reps`` simulated gates whose 95 percent bootstrap interval for the Brier gain clears zero.

    ``n`` rows per replicate, true Brier skill ``skill`` against the constant ``base`` rate, ``B``
    bootstrap resamples per replicate. Deterministic for a fixed ``seed``. Synthetic data only.
    """
    _check(n, skill, base)
    if reps < 1 or B < 2:
        raise ValueError("reps must be at least 1 and B at least 2")
    rng = np.random.default_rng(seed)
    ab = _beta_params(base, skill)
    passed = 0
    for _ in range(reps):
        p = np.full(n, base) if ab is None else rng.beta(ab[0], ab[1], n)
        e = (rng.random(n) < p).astype(np.float64)
        d = (base - e) ** 2 - (p - e) ** 2
        idx = rng.integers(0, n, size=(B, n))
        means = d[idx].mean(axis=1)
        if np.percentile(means, 2.5) > 0.0:
            passed += 1
    return passed / reps


def n_for_power(skill: float, target: float = DEFAULT_TARGET, base: float = DEFAULT_BASE, reps: int = DEFAULT_REPS,
                B: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED, grid=None, deadline: float | None = None, memo: dict | None = None) -> int:
    """Smallest ``n`` on ``grid`` whose simulated power reaches ``target`` (power is assumed monotone in n).

    A bisection over the sorted grid, so the answer is the smallest grid value that meets the target and
    the grid value just below it was simulated and fell short. ``deadline`` is a ``time.monotonic()``
    instant; passing it raises PowerBudgetExceeded. ``memo`` is an optional dict that caches simulated powers by
    ``(n, skill)`` so several targets can share one simulation per grid point. Raises ValueError when even the
    largest grid value falls short.
    """
    ns = sorted(set(int(g) for g in (grid if grid is not None else DEFAULT_GRID)))
    if not ns:
        raise ValueError("the grid is empty")
    lo, hi = 0, len(ns)
    while lo < hi:
        if deadline is not None and time.monotonic() > deadline:
            raise PowerBudgetExceeded("the power run passed its time cap; lower --reps or --bootstrap")
        mid = (lo + hi) // 2
        key = (ns[mid], skill)
        if memo is not None and key in memo:
            power = memo[key]
        else:
            power = gate_power(ns[mid], skill, base=base, reps=reps, B=B, seed=seed)
            if memo is not None:
                memo[key] = power
        if power >= target:
            hi = mid
        else:
            lo = mid + 1
    if lo == len(ns):
        raise ValueError(f"no n up to {ns[-1]} reaches power {target} at skill {skill}")
    return ns[lo]


def power_table(ns=TABLE_NS, skills=TABLE_SKILLS, base: float = DEFAULT_BASE, reps: int = DEFAULT_REPS,
                B: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED) -> list[dict]:
    """Power by n and skill, as a list of rows ``{"n", "skill", "power"}`` (synthetic)."""
    return [{"n": int(n), "skill": float(k), "power": gate_power(int(n), float(k), base=base, reps=reps, B=B, seed=seed)}
            for k in skills for n in ns]


def format_table(rows: list[dict]) -> str:
    """Plain-text table of power by n (columns) and skill (rows), headed as synthetic."""
    ns = sorted({r["n"] for r in rows})
    lookup = {(r["n"], r["skill"]): r["power"] for r in rows}
    lines = ["Gate power (synthetic data only), share of simulated gates whose 95 percent interval clears zero",
             "skill \\ n  " + "".join(f"{n:>8d}" for n in ns)]
    for k in sorted({r["skill"] for r in rows}):
        lines.append(f"{k:<10.2f} " + "".join(f"{lookup[(n, k)]:>8.2f}" for n in ns))
    return "\n".join(lines)


def write_gates(path=None, base: float = DEFAULT_BASE, target: float = DEFAULT_TARGET, reps: int = DEFAULT_REPS,
                B: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED, grid=None, with_table: bool = True,
                max_seconds: float = MAX_SECONDS) -> dict:
    """Run the power simulation and write ``gates.json``; returns the document.

    Two power targets are read from one simulated power curve: the research screen (``RESEARCH_TARGET``) and the
    decision target ``target`` (the release gate, ``DEFAULT_TARGET``). ``by_target`` holds ``n_200`` (skill 0.20)
    and ``n_400`` (skill 0.10) for each target keyed like ``"0.80"``; the top-level ``n_200`` and ``n_400`` are
    the decision target's values. The run stops with PowerBudgetExceeded after ``max_seconds``.
    """
    start = time.monotonic()
    deadline = start + max_seconds
    targets = sorted({RESEARCH_TARGET, float(target)})
    memo: dict = {}
    by_target = {f"{t:.2f}": {key: n_for_power(skill, t, base, reps, B, seed, grid, deadline, memo) for key, skill in GATE_SKILLS.items()}
                 for t in targets}
    found = by_target[f"{float(target):.2f}"]
    doc = {
        **found, "base_rate": base, "target_power": float(target), "decision_target": float(target), "research_target": RESEARCH_TARGET,
        "by_target": by_target, "reps": reps, "bootstrap": B, "seed": seed, "label": SYNTHETIC_LABEL, "skills": dict(GATE_SKILLS),
        "note": "n_200 and n_400 are the values this run produced on synthetic data at the decision target; by_target holds both "
                "targets, which read the same power curve at different levels. Nothing downstream hardcodes any of these sizes.",
    }
    if with_table:
        ns = sorted(set(TABLE_NS) | {n for v in by_target.values() for n in v.values()})
        doc["table"] = power_table(ns, TABLE_SKILLS, base, reps, B, seed)
        if time.monotonic() > deadline:
            raise PowerBudgetExceeded("the power run passed its time cap; lower --reps or --bootstrap")
    doc["seconds"] = round(time.monotonic() - start, 1)
    path = Path(path) if path is not None else storage_paths().gates_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return doc


def load_gates(path=None) -> dict:
    """Read the gates from gates.json (default ``reports/gates.json``).

    Returns ``n_200`` and ``n_400`` at the decision target plus, when the file has them, ``decision_target`` and
    ``by_target`` (both targets). A file from before the two-target change has only the first two keys.
    Raises FileNotFoundError, with the command to run, when the file is missing.
    """
    p = Path(path) if path is not None else storage_paths().gates_path
    if not p.exists():
        raise FileNotFoundError(f"{p} is missing: {RUN_HINT}")
    data = json.loads(p.read_text(encoding="utf-8"))
    out: dict = {"n_200": int(data["n_200"]), "n_400": int(data["n_400"])}
    if "by_target" in data:
        out["decision_target"] = float(data.get("decision_target", data.get("target_power", DEFAULT_TARGET)))
        out["by_target"] = {k: {kk: int(vv) for kk, vv in v.items()} for k, v in data["by_target"].items()}
    return out
