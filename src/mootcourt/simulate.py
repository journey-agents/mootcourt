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

By test (round 00, docs/method.md call 170). The archive's rows come in tests that share a reference arm, and the harness reports a
90 percent interval that resamples whole tests. ``gate_power`` can therefore draw ``rows_per_test`` rows per test (one forecast per
test shared by its rows, outcomes independent given it, test sizes ``1 + Poisson(rows_per_test - 1)``), bootstrap by test and clear the
gate when the lower end of the ``level`` interval is above zero; ``n`` is then a number of tests, the unit the harness counts
decidability in. The defaults (one row per test, a 95 percent interval) are the earlier per-row simulation; ``write_gates`` uses the
by-test, 90 percent version. The gates are written at one or several base rates, because the sizes depend on it: at a base rate of 0.09
a Brier skill of 0.10 is a much smaller absolute difference than at 0.30, and the harness reads each group's gate at the base rate
nearest to the group's own event rate (``select_gates``).

Dependence within a test (review L, REV-L-008). With ``icc`` above zero the outcomes of one test are no longer independent given the
forecast: they share a latent Gaussian factor whose correlation is chosen so that the BINARY correlation of two outcomes of a test equals
``icc`` (``latent_rho_for_icc``), which is the within-test correlation the harness measures from the design effect. The released gates use
the measured values of each source (``SOURCE_DEPENDENCE``): rows per test and binary correlation from the Upworthy backtest at base rate
0.09, from ASOS at 0.14, and the Upworthy values at 0.30 where no archive exists.

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
DEFAULT_ROWS_PER_TEST = 3.5     # Upworthy: 13,247 scored rows over 3,797 tests
DEFAULT_LEVEL = 0.90            # the harness's interval
# (rows per test, binary within-test correlation of the event) measured on the archives (round 00 backtests; docs/method.md call 170)
SOURCE_DEPENDENCE = {0.09: (3.5, 0.13), 0.14: (5.0, 0.67), 0.30: (3.5, 0.13)}
LEGACY_LEVEL = 0.95             # the per-row simulation of earlier versions
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
MAX_SECONDS = 180.0            # per base rate
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


def latent_rho_for_icc(p: float, icc: float) -> float:
    """Latent Gaussian correlation whose thresholding at ``Phi^-1(p)`` gives two outcomes with binary correlation ``icc``."""
    if icc <= 0.0:
        return 0.0
    from scipy import optimize, special
    from scipy.stats import multivariate_normal

    t = float(special.ndtri(p))

    def binary_corr(rho: float) -> float:
        c = float(multivariate_normal.cdf([t, t], mean=[0.0, 0.0], cov=[[1.0, rho], [rho, 1.0]])) - p * p
        return c / (p * (1.0 - p))

    if binary_corr(0.999) <= icc:
        return 0.999
    return float(optimize.brentq(lambda r: binary_corr(r) - icc, 0.0, 0.999, xtol=1e-6))


def gate_power(n: int, skill: float, base: float = DEFAULT_BASE, reps: int = DEFAULT_REPS, B: int = DEFAULT_BOOTSTRAP,
               seed: int = DEFAULT_SEED, rows_per_test: float = 1.0, level: float = LEGACY_LEVEL, icc: float = 0.0) -> float:
    """Share of ``reps`` simulated gates whose ``level`` bootstrap interval for the Brier gain clears zero.

    ``n`` units per replicate (rows when ``rows_per_test`` is 1, else tests of that mean size), true Brier skill ``skill`` against the
    constant ``base`` rate, ``B`` bootstrap resamples per replicate (of rows, or of whole tests when ``rows_per_test`` is above 1).
    Deterministic for a fixed ``seed``. Synthetic data only.
    """
    _check(n, skill, base)
    if reps < 1 or B < 2:
        raise ValueError("reps must be at least 1 and B at least 2")
    if rows_per_test < 1.0 or not 0.0 < level < 1.0:
        raise ValueError("rows_per_test must be at least 1 and level in (0, 1)")
    rng = np.random.default_rng(seed)
    ab = _beta_params(base, skill)
    rho = latent_rho_for_icc(base, icc) if rows_per_test > 1.0 else 0.0
    lo_pct = 100.0 * (1.0 - level) / 2.0
    passed = 0
    for _ in range(reps):
        if rows_per_test == 1.0:
            p = np.full(n, base) if ab is None else rng.beta(ab[0], ab[1], n)
            e = (rng.random(n) < p).astype(np.float64)
            d = (base - e) ** 2 - (p - e) ** 2
            idx = rng.integers(0, n, size=(B, n))
            means = d[idx].mean(axis=1)
        else:
            m = 1 + rng.poisson(rows_per_test - 1.0, n)
            pt = np.full(n, base) if ab is None else rng.beta(ab[0], ab[1], n)       # one forecast per test, shared by its rows
            tot = int(m.sum())
            test_of = np.repeat(np.arange(n), m)
            p = pt[test_of]
            if rho > 0.0:
                from scipy import special

                z = np.sqrt(rho) * rng.standard_normal(n)[test_of] + np.sqrt(1.0 - rho) * rng.standard_normal(tot)
                e = (z < special.ndtri(np.clip(p, 1e-12, 1.0 - 1e-12))).astype(np.float64)
            else:
                e = (rng.random(tot) < p).astype(np.float64)
            d_t = np.bincount(test_of, weights=(base - e) ** 2 - (p - e) ** 2, minlength=n)
            counts = rng.multinomial(n, np.full(n, 1.0 / n), size=B).astype(np.float64)
            means = (counts @ d_t) / (counts @ m.astype(np.float64))
        if np.percentile(means, lo_pct) > 0.0:
            passed += 1
    return passed / reps


def n_for_power(skill: float, target: float = DEFAULT_TARGET, base: float = DEFAULT_BASE, reps: int = DEFAULT_REPS,
                B: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED, grid=None, deadline: float | None = None, memo: dict | None = None,
                rows_per_test: float = 1.0, level: float = LEGACY_LEVEL, icc: float = 0.0) -> int:
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
            power = gate_power(ns[mid], skill, base=base, reps=reps, B=B, seed=seed, rows_per_test=rows_per_test, level=level, icc=icc)
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
                B: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED, rows_per_test: float = 1.0, level: float = LEGACY_LEVEL,
                icc: float = 0.0) -> list[dict]:
    """Power by n and skill, as a list of rows ``{"n", "skill", "power"}`` (synthetic)."""
    return [{"n": int(n), "skill": float(k),
             "power": gate_power(int(n), float(k), base=base, reps=reps, B=B, seed=seed, rows_per_test=rows_per_test, level=level, icc=icc)}
            for k in skills for n in ns]


def format_table(rows: list[dict], level: float = LEGACY_LEVEL, by: str = "row") -> str:
    """Plain-text table of power by n (columns, in tests when ``by`` is ``test``) and skill (rows), headed as synthetic."""
    ns = sorted({r["n"] for r in rows})
    lookup = {(r["n"], r["skill"]): r["power"] for r in rows}
    lines = [f"Gate power (synthetic data only), share of simulated gates whose {level * 100:g} percent interval clears zero (n in {by}s)",
             "skill \\ n  " + "".join(f"{n:>8d}" for n in ns)]
    for k in sorted({r["skill"] for r in rows}):
        lines.append(f"{k:<10.2f} " + "".join(f"{lookup[(n, k)]:>8.2f}" for n in ns))
    return "\n".join(lines)


RELEASE_BASE_RATES = (0.09, 0.14, 0.30)     # the Upworthy archive (event rate about 0.09), ASOS (about 0.14) and the base rate of the earlier gates


def _entry(base: float, target: float, reps: int, B: int, seed: int, grid, with_table: bool, deadline: float, rows_per_test: float,
           level: float, icc: float = 0.0, progress=None, t0: float | None = None) -> dict:
    """The gate sizes at one base rate: ``n_200``, ``n_400`` and ``by_target`` (both power targets) and the optional power table.

    ``progress`` (a callable taking one line) is told each size as it is found, with the elapsed seconds since ``t0``."""
    targets = sorted({RESEARCH_TARGET, float(target)})
    memo: dict = {}
    t0 = time.monotonic() if t0 is None else t0
    by_target: dict = {}
    for t in targets:
        by_target[f"{t:.2f}"] = {}
        for key, skill in GATE_SKILLS.items():
            by_target[f"{t:.2f}"][key] = n_for_power(skill, t, base, reps, B, seed, grid, deadline, memo, rows_per_test, level, icc)
            if progress is not None:
                progress(f"progress: base rate {base:.2f}, power {t:.2f}, skill {skill:.2f}: n = {by_target[f'{t:.2f}'][key]} "
                         f"({time.monotonic() - t0:.0f} s elapsed)")
    out = {**by_target[f"{float(target):.2f}"], "base_rate": float(base), "by_target": by_target, "rows_per_test": float(rows_per_test),
           "icc": float(icc), "latent_rho": latent_rho_for_icc(base, icc) if rows_per_test > 1.0 else 0.0}
    if with_table:
        ns = sorted(set(TABLE_NS) | {n for v in by_target.values() for n in v.values()})
        out["table"] = power_table(ns, TABLE_SKILLS, base, reps, B, seed, rows_per_test, level, icc)
        if time.monotonic() > deadline:
            raise PowerBudgetExceeded("the power run passed its time cap; lower --reps or --bootstrap")
    return out


def _at(value, base: float) -> float:
    """``value`` for a base rate: the number itself, or the entry of a dict keyed by base rate (the nearest key)."""
    if isinstance(value, dict):
        return float(value[min(value, key=lambda k: abs(k - base))])
    return float(value)


def write_gates(path=None, base: float = DEFAULT_BASE, target: float = DEFAULT_TARGET, reps: int = DEFAULT_REPS,
                B: int = DEFAULT_BOOTSTRAP, seed: int = DEFAULT_SEED, grid=None, with_table: bool = True,
                max_seconds: float = MAX_SECONDS, base_rates=None, rows_per_test=1.0, level: float = LEGACY_LEVEL,
                table_all: bool = False, icc=0.0, progress=None, dependence_source: str | None = None) -> dict:
    """Run the power simulation and write ``gates.json``; returns the document.

    ``progress`` (a callable taking one line) is told each size as it is found; ``dependence_source`` says where ``rows_per_test`` and
    ``icc`` came from and is recorded in the file (round 01, R6; call 207).

    Two power targets are read from one simulated power curve: the research screen (``RESEARCH_TARGET``) and the
    decision target ``target`` (the release gate, ``DEFAULT_TARGET``). ``by_target`` holds ``n_200`` (skill 0.20)
    and ``n_400`` (skill 0.10) for each target keyed like ``"0.80"``; the top-level ``n_200`` and ``n_400`` are
    the decision target's values at the first base rate. The run stops with PowerBudgetExceeded after ``max_seconds`` for each base rate.

    ``base_rates`` (default: just ``base``) writes the gates at several base rates: ``by_base_rate`` is keyed like ``"0.09"`` and
    holds the same fields per base rate, and the top level is a copy of the first. ``rows_per_test`` above 1 simulates tests of that
    mean size and bootstraps by test (``n`` is then a number of tests); ``level`` is the interval whose lower end must clear zero. ``rows_per_test``
    and ``icc`` (the binary within-test correlation of the event) may each be a number or a dict keyed by base rate (``SOURCE_DEPENDENCE``); each base
    rate's entry records the values it used. The power table is written for the first base rate only unless ``table_all``.
    """
    start = time.monotonic()
    rates = [float(b) for b in (base_rates if base_rates is not None else (base,))]
    if not rates:
        raise ValueError("base_rates is empty")
    entries = {}
    for i, b in enumerate(rates):
        # the power table is the slow part (n up to 2000 at every skill) and is printed for the first base rate only; the sizes are at every rate
        entries[f"{b:.2f}"] = _entry(b, target, reps, B, seed, grid, with_table and (i == 0 or table_all), time.monotonic() + max_seconds,
                                     _at(rows_per_test, b), level, _at(icc, b), progress=progress, t0=start)
    first = entries[f"{rates[0]:.2f}"]
    doc = {
        **{k: v for k, v in first.items() if k != "table"}, "target_power": float(target), "decision_target": float(target),
        "research_target": RESEARCH_TARGET, "reps": reps, "bootstrap": B, "seed": seed, "label": SYNTHETIC_LABEL, "skills": dict(GATE_SKILLS),
        "interval": {"level": float(level), "by": "test" if first["rows_per_test"] > 1.0 else "row", "rows_per_test": first["rows_per_test"],
                     "icc": first["icc"],
                     "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive "
                                   "of that rate (docs/method.md call 170)"},
        "note": "n_200 and n_400 are the values this run produced on synthetic data at the decision target; by_target holds both "
                "targets, which read the same power curve at different levels. Nothing downstream hardcodes any of these sizes. "
                "by_base_rate holds the same sizes at each simulated base rate; the top level is the first of them.",
    }
    if dependence_source:
        doc["dependence_source"] = str(dependence_source)
    if "table" in first:
        doc["table"] = first["table"]
    if len(rates) > 1 or base_rates is not None:
        doc["by_base_rate"] = entries
    doc["seconds"] = round(time.monotonic() - start, 1)
    path = Path(path) if path is not None else storage_paths().gates_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return doc


def ledger_dependence(ledger) -> dict:
    """Rows per test, base rate and within-test correlation of the significant-positive event, measured on a ledger's admitted rows.

    The event is ``y > Z s`` per row; the correlation is the ``icc`` of ``harness_stats.design_effect`` with the base rate as the forecast,
    the rule the clustered null and the released gates use (call 207). Raises ValueError for a ledger without admitted rows.
    """
    from mootcourt.config import Z
    from mootcourt.harness_stats import design_effect

    adm = ledger.loc[ledger["status"] == "admitted"]
    if adm.empty:
        raise ValueError("the ledger has no admitted rows to measure the dependence on")
    event = (adm["y"].to_numpy(float) > Z * adm["s"].to_numpy(float)).astype(float)
    base = float(event.mean())
    n_tests = int(adm["test_id"].nunique())
    rows_per_test = float(len(adm)) / n_tests
    icc = 0.0
    if 0.0 < base < 1.0 and rows_per_test > 1.0:
        icc = float(design_effect(np.full(len(adm), base), event, adm["test_id"].to_numpy())["icc"])
    return {"base_rate": base, "rows_per_test": rows_per_test, "icc": icc, "n_tests": n_tests, "n_rows": int(len(adm))}


def _entry_ints(e: dict) -> dict:
    out = {"n_200": int(e["n_200"]), "n_400": int(e["n_400"])}
    if "base_rate" in e:
        out["base_rate"] = float(e["base_rate"])
    if "by_target" in e:
        out["by_target"] = {k: {kk: int(vv) for kk, vv in v.items()} for k, v in e["by_target"].items()}
    for key in ("rows_per_test", "icc"):                     # the dependence the sizes were simulated with, for the per-cell gate read (call 205)
        if e.get(key) is not None:
            out[key] = float(e[key])
    return out


def load_gates(path=None) -> dict:
    """Read the gates from gates.json (default ``reports/gates.json``).

    Returns ``n_200`` and ``n_400`` at the decision target plus, when the file has them, ``decision_target``,
    ``by_target`` (both targets), ``base_rate`` and ``by_base_rate`` (the same sizes at every simulated base rate, keyed by the rate
    as a float). A file from before the two-target change has only the first two keys.
    Raises FileNotFoundError, with the command to run, when the file is missing.
    """
    p = Path(path) if path is not None else storage_paths().gates_path
    if not p.exists():
        raise FileNotFoundError(f"{p} is missing: {RUN_HINT}")
    data = json.loads(p.read_text(encoding="utf-8"))
    out: dict = _entry_ints(data)
    if "by_target" in data:
        out["decision_target"] = float(data.get("decision_target", data.get("target_power", DEFAULT_TARGET)))
    if "by_base_rate" in data:
        out["by_base_rate"] = {float(k): {**_entry_ints(v), "decision_target": out.get("decision_target", DEFAULT_TARGET)}
                               for k, v in data["by_base_rate"].items()}
    if "interval" in data:
        out["interval"] = dict(data["interval"])
    return out


def select_gates(gates: dict, rate: float | None, exact: bool = False) -> dict | None:
    """The gate sizes at the simulated base rate nearest to ``rate`` (the group's own event rate).

    ``gates`` is what ``load_gates`` returns. A file with one base rate, or none recorded, is returned as it is. ``rate`` None gives the
    top level. With ``exact`` the entry must be within 1e-6 of ``rate``, else None: that is how the labelled base rate 0.3 column
    asks for the earlier gates.
    """
    by = gates.get("by_base_rate")
    if not by:
        if exact:
            return gates if gates.get("base_rate") is not None and abs(float(gates["base_rate"]) - float(rate)) < 1e-6 else None
        return gates
    if rate is None or not np.isfinite(rate):
        return gates
    best = min(by, key=lambda b: abs(b - rate))
    if exact and abs(best - rate) > 1e-6:
        return None
    return by[best]
