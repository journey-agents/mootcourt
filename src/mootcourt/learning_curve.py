"""Learning curve: how skill grows with the amount of history, with the gate sizes alongside.

Design. One final origin ``T`` is chosen (the latest quarter start that holds at least ``HELDOUT_MIN`` admitted rows). The
rows scored are the admitted rows that start in the quarter of ``T``; they are the same in every run. The history is the
set of admitted rows usable at ``T``; for a fraction ``f`` below 1 a random ``f`` of its tests (whole tests, so contrasts
that share a reference arm stay together) is kept, and every rung is refit on that subsample and scored on the same
held-out rows. Each fraction is repeated for ``seeds`` random subsamples (fraction 1 is deterministic and runs once).

Reported per fraction and rung: the mean number of history rows, the Brier skill against the base rate averaged over
seeds, a 90 percent interval from bootstrapping the held-out tests (the draws of the seeds are averaged, so the interval
describes the seed-averaged skill on this held-out set), the spread of the skill across seeds, and the mean log score
and direction accuracy where the rung has them. The figure overlays the gate sizes at both power targets on the
history axis: they are the numbers of scored rows a cell needs before a skill can be called decidable, drawn here so the
history actually used can be read against them.

Round 00: the planned design is 20 seeds per fraction and a smallest fraction that crosses the gate (0.01 and 0.02 leave fewer rows than
the gate sizes), the direction baselines are left out of the table, and the gate sizes printed are those of the first base rate in gates.json.

Units: skill, Brier and accuracy are unitless; log scores are per unit of y.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np
import pandas as pd

from mootcourt import harness_stats as hs
from mootcourt.harness import MIN_FIT_ROWS, quarterly_origins, rolling_origin
from mootcourt.ledger import ADMITTED, to_utc, visible_rows
from mootcourt.report import clean, rung_kind

HELDOUT_MIN = 500
DEFAULT_FRACTIONS = (0.1, 0.25, 0.5, 1.0)
LEVEL_LO, LEVEL_HI = 5.0, 95.0


def parse_fractions(text: str) -> list[float]:
    """Fractions from a comma-separated string; each must be in (0, 1]."""
    out = [float(x) for x in text.split(",") if x.strip()]
    if not out or any(not 0.0 < f <= 1.0 for f in out):
        raise ValueError("fractions must be numbers in (0, 1], for example 0.1,0.25,0.5,1")
    return sorted(set(out))


def final_origin(ledger: pd.DataFrame, heldout_min: int = HELDOUT_MIN) -> pd.Timestamp:
    """The latest quarter start with at least ``heldout_min`` admitted rows starting in its quarter and enough history to fit.

    When no quarter holds that many rows (a small source), the quarter with the most rows is used, the latest one on a tie.
    """
    adm = ledger.loc[ledger["status"] == ADMITTED]
    origins = quarterly_origins(ledger)
    ends = origins[1:] + [origins[-1] + pd.DateOffset(months=3)]
    eligible = []
    for t, t_next in zip(origins, ends):
        n = int(((adm["started_at"] >= t) & (adm["started_at"] < t_next)).sum())
        if n > 0 and len(visible_rows(adm, t)) >= MIN_FIT_ROWS:
            eligible.append((t, n))
    if not eligible:
        raise ValueError("no origin has history to fit and rows to score")
    enough = [t for t, n in eligible if n >= heldout_min]
    return enough[-1] if enough else max(eligible, key=lambda tn: (tn[1], tn[0]))[0]


def subsample(ledger: pd.DataFrame, origin, fraction: float, seed: int) -> pd.DataFrame:
    """Keep every row except the admitted history rows of tests outside a random ``fraction`` of the history's tests."""
    if fraction >= 1.0:
        return ledger
    t = to_utc(origin)
    hist = visible_rows(ledger.loc[ledger["status"] == ADMITTED], t)
    tests = np.array(sorted(hist["test_id"].unique()))
    rng = np.random.default_rng(seed)
    keep = set(rng.choice(tests, size=max(1, int(round(fraction * len(tests)))), replace=False).tolist())
    drop = ledger["row_id"].isin(set(hist.loc[~hist["test_id"].isin(keep), "row_id"]))
    return ledger.loc[~drop].reset_index(drop=True)


def _metrics(scores: pd.DataFrame, rung: str, B: int, seed: int, base_ref: pd.Series) -> dict:
    """Scores of one run for one rung, against two base rates: the one the run's own history gives (``*_own``) and the full-history one.

    ``base_ref`` is the full-history P0 Brier score of every held-out row (the reference the main table uses), by ``row_id``; a point of the
    curve is scored against it so the baseline does not change with the amount of history, and the skill of a rung that does not improve with
    history does not rise because a thin history made the base rate worse (review R1, blocking 2)."""
    g = scores[scores["rung"] == rung]
    ref = base_ref.reindex(g["row_id"]).to_numpy(float)
    ok = np.isfinite(g["brier_event"].to_numpy(float)) & np.isfinite(ref)
    b = g["brier_event"].to_numpy(float)[ok]
    own, full = g["brier_base"].to_numpy(float)[ok], ref[ok]
    ls, dc = g["logscore"].to_numpy(float), g["direction_correct"].astype(float).to_numpy()
    g_ref = g.assign(brier_base=ref)
    return {
        "n_scored": int(len(g)),
        "n_scored_tests": int(g["test_id"].nunique()),
        "skill": float(1.0 - b.mean() / full.mean()) if ok.any() and full.mean() > 0 else None,
        "skill_own": float(1.0 - b.mean() / own.mean()) if ok.any() and own.mean() > 0 else None,
        "base_brier_full": float(full.mean()) if ok.any() else None,
        "base_brier_own": float(own.mean()) if ok.any() else None,
        "brier": float(b.mean()) if ok.any() else None,
        "logscore": float(np.nanmean(ls)) if np.isfinite(ls).any() else None,
        "direction_accuracy": float(np.nanmean(dc)) if np.isfinite(dc).any() else None,
        "draws": hs.brier_skill_draws(g_ref, B=B, seed=seed),
        "draws_own": hs.brier_skill_draws(g, B=B, seed=seed),
    }


def run_learning_curve(
    ledger: pd.DataFrame,
    source: str,
    factory: Callable[[pd.DataFrame], dict],
    fractions,
    seeds: int,
    gates: dict,
    *,
    B: int = 200,
    seed: int = 0,
    heldout_min: int = HELDOUT_MIN,
    verbose: bool = False,
) -> dict:
    """Run the curve. ``factory(ledger_subsample)`` returns the rung factories (``harness.default_rungs`` with the settings)."""
    T = final_origin(ledger, heldout_min)
    ref_scores = rolling_origin(ledger, factory(ledger), [T], source=source)  # the full history: the reference base rate of every point
    if ref_scores.empty:
        raise ValueError("the full history cannot be fitted, so the curve has no reference base rate")
    base_ref = ref_scores.drop_duplicates("row_id").set_index("row_id")["brier_base"].astype(float)
    runs: dict[tuple[float, str], list] = {}
    n_fit: dict[float, list[int]] = {}
    n_hist_tests: dict[float, list[int]] = {}
    held_rows = held_tests = 0
    skipped: dict[float, int] = {}
    for f in fractions:
        n_seeds = 1 if f >= 1.0 else seeds
        for k in range(n_seeds):
            sub = subsample(ledger, T, f, seed * 1000 + k)
            sc = ref_scores if f >= 1.0 else rolling_origin(sub, factory(sub), [T], source=source)
            if sc.empty:
                skipped.setdefault(f, 0)
                skipped[f] += 1
                continue
            hist = visible_rows(sub.loc[sub["status"] == ADMITTED], T)
            n_fit.setdefault(f, []).append(len(hist))
            n_hist_tests.setdefault(f, []).append(int(hist["test_id"].nunique()))
            held_rows, held_tests = int(sc["row_id"].nunique()), int(sc["test_id"].nunique())
            for rung in sorted(sc["rung"].unique()):
                if rung_kind(rung) == "baseline":  # the direction baselines have no Brier score: their columns would be empty (round 00 nit)
                    continue
                runs.setdefault((f, rung), []).append(_metrics(sc, rung, B, seed, base_ref))
            if verbose:
                print(f"learning curve: fraction {f}, seed {k}: {len(sub)} rows kept", flush=True)
    rows = []
    for (f, rung), ms in sorted(runs.items()):

        def interval(key, ms=ms):
            skills = [m[key.replace("draws", "skill")] for m in ms if m[key.replace("draws", "skill")] is not None]
            draws = np.nanmean(np.stack([m[key] for m in ms]), axis=0) if skills else np.full(B, np.nan)
            lo, hi = np.nanpercentile(draws, [LEVEL_LO, LEVEL_HI]) if np.isfinite(draws).any() else (np.nan, np.nan)
            sd = float(np.std(skills, ddof=1)) if len(skills) > 1 else None
            return lo, hi, sd

        def avg(key, ms=ms):
            vals = [m[key] for m in ms if m[key] is not None]
            return float(np.mean(vals)) if vals else None

        lo, hi, sd = interval("draws")
        lo_o, hi_o, sd_o = interval("draws_own")
        rows.append(
            {
                "fraction": f,
                "rung": rung,
                "kind": rung_kind(rung),
                "n_seeds": len(ms),
                "n_fit_rows": float(np.mean(n_fit[f])),
                "n_history_tests": float(np.mean(n_hist_tests[f])),
                "n_scored": ms[0]["n_scored"],
                "n_scored_tests": ms[0]["n_scored_tests"],
                "skill": avg("skill"),
                "skill_lo": lo,
                "skill_hi": hi,
                "skill_seed_sd": sd,
                "skill_own_base": avg("skill_own"),
                "skill_own_base_lo": lo_o,
                "skill_own_base_hi": hi_o,
                "skill_own_base_seed_sd": sd_o,
                "base_brier_full": avg("base_brier_full"),
                "base_brier_own": avg("base_brier_own"),
                "logscore": avg("logscore"),
                "direction_accuracy": avg("direction_accuracy"),
                "brier": avg("brier"),
            }
        )
    return clean(
        {
            "source": source,
            "final_origin": T.isoformat(),
            "heldout_rows": held_rows,
            "heldout_tests": held_tests,
            "fractions": list(fractions),
            "seeds": seeds,
            "skipped_runs": {str(k): v for k, v in skipped.items()},
            "skipped_note": "a subsample with too few history rows cannot be fitted and is left out" if skipped else "",
            "bootstrap_resamples": B,
            "skill_reference": (
                "skill is the Brier skill against the P0 base rate of the FULL history at the final origin (the reference of the main table), "
                "the same for every point; skill_own_base is against the base rate of each point's own subsample"
            ),
            "rungs": sorted({r["rung"] for r in rows}),
            "gates": {
                "n_200": gates.get("n_200"),
                "n_400": gates.get("n_400"),
                "by_target": gates.get("by_target"),
                "decision_target": gates.get("decision_target"),
            },
            "rows": rows,
        }
    )


def render_markdown(doc: dict) -> str:
    """Markdown table of the curve, a pure function of the document."""

    def f(v, nd=4):
        return "n/a" if v is None else f"{v:.{nd}f}"

    out = [
        f"# Learning curve: {doc['source']}",
        "",
        f"Final origin {doc['final_origin']}; {doc['heldout_rows']} held-out rows in {doc['heldout_tests']} tests, the same in every run. "
        f"Fractions {doc['fractions']} of the history's tests, {doc['seeds']} random subsamples each (fraction 1 runs once). "
        "Skill is the Brier skill against the P0 base rate of the FULL history at the final origin, the same for every point (the reference of "
        "the main table); the interval is a 90 percent bootstrap by held-out test of the seed-averaged skill. The column 'skill, own base' is "
        "against the base rate of each point's own subsample, which is a worse forecaster when the history is thin. The gate sizes count "
        "scored tests, and every point scores the same held-out tests (column scored tests), not the history rows.",
        "",
    ]
    g = doc["gates"]
    for k, v in sorted((g.get("by_target") or {}).items(), key=lambda kv: float(kv[0])):
        out.append(f"- Gate sizes at power {k}: n_200 = {v['n_200']}, n_400 = {v['n_400']}")
    out += [
        "",
        "| fraction | history rows | history tests | scored tests | rung | kind | skill (90% interval) | seed sd | skill, own base (90% interval) "
        "| log score | direction accuracy |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in doc["rows"]:
        out.append(
            f"| {r['fraction']} | {r['n_fit_rows']:.0f} | {r.get('n_history_tests') or 0:.0f} | {r.get('n_scored_tests', 0)} | {r['rung']} | "
            f"{r['kind']} | {f(r['skill'])} ({f(r['skill_lo'])} to {f(r['skill_hi'])}) | {f(r['skill_seed_sd'])} | "
            f"{f(r.get('skill_own_base'))} ({f(r.get('skill_own_base_lo'))} to {f(r.get('skill_own_base_hi'))}) | {f(r['logscore'])} | "
            f"{f(r['direction_accuracy'])} |"
        )
    return "\n".join(out) + "\n"


def plot_learning_curve(doc: dict, path) -> None:
    """Skill by history size per rung with 90 percent bands and the gate sizes as vertical lines."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = pd.DataFrame(doc["rows"])
    d = d[d["skill"].notna()]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for rung, g in d.groupby("rung"):
        g = g.sort_values("n_fit_rows")
        ax.plot(g["n_fit_rows"], g["skill"], marker="o", label=rung)
        ax.fill_between(g["n_fit_rows"], g["skill_lo"], g["skill_hi"], alpha=0.12)
    ax.axhline(0.0, color="0.5", linewidth=1)
    styles = {"0.80": "--", "0.90": ":"}
    for tgt, v in sorted((doc["gates"].get("by_target") or {}).items(), key=lambda kv: float(kv[0])):
        for key, color in (("n_200", "0.35"), ("n_400", "0.65")):
            ax.axvline(v[key], color=color, linestyle=styles.get(tgt, ":"), linewidth=1)
            ax.text(v[key], ax.get_ylim()[1], f" {key} @ {tgt}", rotation=90, va="top", fontsize=6)
    ax.set_xlabel("history rows used to fit")
    ax.set_ylabel("Brier skill against the full-history base rate")
    ax.set_title(f"Learning curve, {doc['source']}" + (" (synthetic data)" if doc["source"] == "synthetic" else ""))
    ax.legend(fontsize=7)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def write_learning_curve(doc: dict, out_dir, snapshot_id: str) -> dict:
    """Write ``learning-curve-<source>-<snapshot>.json``/``.md`` and ``figures/learning_curve-<source>.png``; returns the paths."""
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"learning-curve-{doc['source']}-{snapshot_id}"
    paths = {"json": out_dir / f"{stem}.json", "md": out_dir / f"{stem}.md", "figure": out_dir / "figures" / f"learning_curve-{doc['source']}.png"}
    paths["json"].write_text(json.dumps(doc, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    paths["md"].write_text(render_markdown(doc), encoding="utf-8")
    plot_learning_curve(doc, paths["figure"])
    return paths
