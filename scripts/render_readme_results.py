#!/usr/bin/env python3
"""Render the README results block from the backtest report JSON files, so no result number is typed by hand.

The block sits between ``<!-- moot-results:start -->`` and ``<!-- moot-results:end -->`` in README.md. Every number in
it is read from ``reports/backtest-<source>-<snapshot>.json`` (and ``reports/gates.json``, plus the optional
``reports/challenger-gbm/`` report, ``reports/card-latency.json`` and ``reports/run-log.json``). Use:

    python scripts/render_readme_results.py --write    # rewrite the block in README.md
    python scripts/render_readme_results.py --check    # exit 1 if README.md differs from the reports

``render_block(reports_dir)`` returns the text between the markers.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from mootcourt.storage import README_FIGURES, storage_paths, visible_glob

START, END = "<!-- moot-results:start -->", "<!-- moot-results:end -->"
SHORT = {"decidable at skill 0.20 and 0.10": "yes, both skills", "decidable at skill 0.20 only": "skill 0.20 only",
         "decidable at skill 0.10 only": "skill 0.10 only", "undecidable at this n": "undecidable"}
SOURCES = (("upworthy", "Upworthy"), ("asos", "ASOS"), ("synthetic", "Synthetic"))


def _f(v, nd: int = 4) -> str:
    return "n/a" if v is None else f"{v:.{nd}f}"


def _ci(row: dict, key: str) -> str:
    return f"{_f(row.get(key))} ({_f(row.get(key + '_lo'))} to {_f(row.get(key + '_hi'))})"


def _latest(reports: Path, source: str) -> dict:
    found = visible_glob(reports, f"backtest-{source}-*.json")
    if not found:
        raise FileNotFoundError(f"no backtest report for {source} in {reports}; run `make backtest SOURCE={source}` first")
    return json.loads(found[-1].read_text(encoding="utf-8"))


def _row(doc: dict, cell: str, rung: str) -> dict | None:
    return next((r for r in doc["tables"]["aggregate"] if r["cell"] == cell and r["rung"] == rung), None)


def results_table(doc: dict) -> list[str]:
    gate = doc["header"].get("gate_decision_target")
    gate_txt = f"{gate:.2f}" if gate is not None else "release"
    research = min(doc["header"].get("gate_by_target") or {"0.80": 0}, key=float)
    out = [f"| cell | rung | n | log score | Brier skill (90% interval) | decidable by tests ({gate_txt} gate) | "
           f"decidable by rows ({gate_txt} gate, overstates) | decidable by tests ({research} screen) | "
           "coverage 80% / 90% | abstention rate |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in doc["tables"]["aggregate"]:
        out.append(f"| {r['cell']} | {r['rung']} | {r['n']} | {_f(r['logscore'])} | {_ci(r, 'brier_skill')} | "
                   f"{SHORT.get(r.get('decidable_by_tests'), r.get('decidable_by_tests') or 'n/a')} | {SHORT.get(r['decidable'], r['decidable'])} | "
                   f"{SHORT.get(r.get('decidable_research_by_tests'), r.get('decidable_research_by_tests') or 'n/a')} | "
                   f"{_f(r['coverage_80'])} / {_f(r['coverage_90'])} | {_f(r['abstention_rate'])} |")
    return out


def abstention_table(doc: dict) -> list[str]:
    out = ["| cell | rows | abstention rate | support | novelty | reliability | instability |", "|---|---|---|---|---|---|---|"]
    out += [f"| {r['cell']} | {r['n']} | {_f(r['rate'])} | {r['support']} | {r['novelty']} | {r['reliability']} | {r['instability']} |"
            for r in doc["tables"]["abstention"]]
    return out


def sentence_skill(doc: dict) -> str:
    r = _row(doc, "ALL", doc["header"]["primary_rung"])
    lo, hi = r["brier_skill_lo"], r["brier_skill_hi"]
    verdict = ("worse than the constant base rate" if hi < 0 else "better than the constant base rate" if lo > 0
               else "not distinguishable from the constant base rate")
    return (f"{doc['header']['primary_rung']} Brier skill against the base rate on all rows: {_ci(r, 'brier_skill')}, which is {verdict}. "
            f"Its calibration error is {_f(r['ece'])}, at percentile {_f(r['ece_percentile'], 1)} of the perfect-calibration null.")


def sentence_rungs(doc: dict) -> str:
    rungs = {r["rung"]: r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL"}
    if "P0" not in rungs or "P1" not in rungs:
        return ""
    parts = [f"Log score on all rows: P0 {_f(rungs['P0']['logscore'])}, P1 {_f(rungs['P1']['logscore'])}"]
    if "P2" in rungs:
        parts[0] += f", P2 {_f(rungs['P2']['logscore'])}"
        diff = rungs["P2"]["logscore"] - rungs["P1"]["logscore"]
        verdict = ("adds nothing measurable over the prior" if abs(diff) < 0.005
                   else "scores better than the prior" if diff > 0 else "scores worse than the prior")
        parts.append(f"P2 minus P1 is {diff:+.4f}, so the precedent rung {verdict}")
    return ". ".join(parts) + "."


def bins_sentence(doc: dict) -> str:
    """Where the primary rung's p_sig is far from the observed frequency: its most populated bin with a predicted mean of at least 0.1."""
    rung = doc["header"]["primary_rung"]
    bins = [b for b in doc["tables"]["reliability_bins"] if b["rung"] == rung and isinstance(b.get("mean_p"), (int, float)) and b["mean_p"] >= 0.1]
    if not bins:
        return ""
    b = max(bins, key=lambda r: r["n"])
    return (f"Reliability bins: {rung} rows predicted between {_f(b['lo'], 2)} and {_f(b['hi'], 2)} "
            f"({b['n']} rows, mean predicted {_f(b['mean_p'])}) "
            f"were followed by a significant positive result {_f(b['freq'])} of the time.")


def precision_table(doc: dict) -> list[str]:
    """Calibration by precision for the prior (P1) and the primary rung: deciles of planned exposures per arm."""
    rows = doc["tables"].get("calibration_by_precision") or []
    keep = [r for r in rows if r["rung"] in ("P1", doc["header"]["primary_rung"])]
    if not keep:
        return []
    out = ["Calibration by precision: rows in deciles of planned exposures per arm (fewer groups when exposures tie). "
           "A forecaster calibrated overall but not within these groups is not calibrated; `mean p_sig` should match `event rate` "
           "and `coverage 90%` should be near 0.90 in every group.", "",
           "| rung | decile | planned exposures per arm | n | mean s_star | mean p_sig | event rate | coverage 90% |",
           "|---|---|---|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {r['decile']} | {r['exposure_lo']:.0f} to {r['exposure_hi']:.0f} | {r['n']} | {_f(r.get('mean_s_star'))} | "
            f"{_f(r['mean_p_sig'])} | {_f(r['event_rate'])} | {_f(r['coverage_90'])} |" for r in keep]
    return out


def decision_sentence(doc: dict) -> str:
    rows = [r for r in doc["tables"]["decision_value"] if r["origin"] == "ALL"]
    get = lambda pol, rung: next((r for r in rows if r["policy"] == pol and r["rung"] == rung), None)  # noqa: E731
    primary = doc["header"]["primary_rung"]
    rnd, pw, orc = get("random", "all"), get("p_win", primary), get("oracle", "all")
    if not (rnd and pw and orc):
        return ""
    return (f"Decision value, pooled over origins: choosing a quarter of the tests at random captures {_f(rnd['captured_fraction'])} of the total "
            f"positive observed lift, choosing by {primary} p_win captures {_f(pw['captured_fraction'])}, "
            f"and an oracle that knows the result captures "
            f"{_f(orc['captured_fraction'])}. No interval is computed for the difference between random and p_win, so it is not evidence of an edge.")


def power_lines(gates: dict) -> list[str]:
    ns = sorted({r["n"] for r in gates["table"]})
    skills = sorted({r["skill"] for r in gates["table"]})
    look = {(r["n"], r["skill"]): r["power"] for r in gates["table"]}
    out = ["| Brier skill \\ scored rows | " + " | ".join(str(n) for n in ns) + " |", "|---|" + "---|" * len(ns)]
    out += [f"| {k:.2f} | " + " | ".join(f"{look[(n, k)]:.2f}" for n in ns) + " |" for k in skills]
    sizes = ["| power target | rows for skill 0.20 | rows for skill 0.10 |", "|---|---|---|"]
    for t in sorted(gates["by_target"], key=float):
        tag = " (release gate)" if abs(float(t) - gates["decision_target"]) < 1e-9 else " (research screen)"
        sizes.append(f"| {t}{tag} | {gates['by_target'][t]['n_200']} | {gates['by_target'][t]['n_400']} |")
    return sizes + [""] + out


def direction_table(doc: dict) -> list[str]:
    """Direction accuracy beside its ceiling for every rung, the direction baselines included."""
    rows = [r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL"]
    out = ["| rung | kind | direction accuracy (90% interval) | ceiling |", "|---|---|---|---|"]
    out += [f"| {r['rung']} | {r.get('kind', '')} | {_ci(r, 'direction_accuracy')} | {_f(r.get('direction_ceiling'))} |" for r in rows]
    return out


def _all_row(doc: dict, rung: str) -> dict | None:
    return next((r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL" and r["rung"] == rung), None)


def challenger_lines(reports: Path, source: str = "upworthy") -> list[str]:
    """Challengers beside the ladder on the same origins and rows, from the report in ``challengers/`` (or the older ``challenger-gbm/``)."""
    reports = Path(reports)
    pattern = f"backtest-{source}-*.json"
    found = visible_glob((reports / "challengers"), pattern) or visible_glob((reports / "challenger-gbm"), pattern)
    if not found:
        return []
    doc = json.loads(found[-1].read_text(encoding="utf-8"))
    names = ", ".join(doc["header"].get("challengers") or ["GBM"])
    out = [f"### Challengers ({names}), {source.capitalize()}", "",
           "Same features, same origins, same rows as the ladder. Rows below are all cells pooled. `kind` marks challengers and direction baselines; "
           "a rung without a density has no log score, and a rung without a probability has no Brier skill.", "",
           "| rung | kind | n | log score | Brier skill (90% interval) | direction accuracy | abstention rate |", "|---|---|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {r.get('kind', '')} | {r['n']} | {_f(r['logscore'])} | {_ci(r, 'brier_skill')} | {_f(r['direction_accuracy'])} | "
            f"{_f(r['abstention_rate'])} |" for r in doc["tables"]["aggregate"] if r["cell"] == "ALL"]
    p2 = _all_row(doc, "P2")
    for name in doc["header"].get("challengers") or []:
        r = _all_row(doc, name)
        if r and p2 and r["logscore"] is not None and p2["logscore"] is not None:
            d = r["logscore"] - p2["logscore"]
            word = "better" if d > 0.005 else "worse" if d < -0.005 else "about equal"
            out += ["", f"{name} minus P2 log score is {d:+.4f}, so {name} is {word} than P2 on this score."]
    return out + [""]


def ablation_lines(reports: Path, source: str = "upworthy") -> list[str]:
    """Ablations of one source: the main run and every report in ``ablations/``, P1 and P2 side by side, and the per-cell P2 selections."""
    reports = Path(reports)
    main_files = visible_glob(reports, f"backtest-{source}-*.json")
    var_files = visible_glob((reports / "ablations"), f"backtest-{source}-*--*.json")
    if not main_files or not var_files:
        return []
    docs = [("main run (defaults)", json.loads(main_files[-1].read_text(encoding="utf-8")))]
    docs += [(f.stem.split("--", 1)[1], json.loads(f.read_text(encoding="utf-8"))) for f in var_files]
    out = [f"### Ablations, {source.capitalize()}", "",
           "Each row is one backtest on the same origins and rows with one setting changed, written to its own report under `reports/ablations/`. "
           "All cells pooled. P2 minus P1 is the log score the precedents add; a value near zero means P2 reduced to the prior.", "",
           "| setting | P1 log score | P2 log score | P2 minus P1 | P2 Brier skill (90% interval) | P2 direction accuracy | P2 coverage 90% |",
           "|---|---|---|---|---|---|---|"]
    for name, doc in docs:
        p1, p2 = _all_row(doc, "P1"), _all_row(doc, "P2")
        if p1 and p2:
            out.append(f"| {name} | {_f(p1['logscore'])} | {_f(p2['logscore'])} | {p2['logscore'] - p1['logscore']:+.4f} | "
                       f"{_ci(p2, 'brier_skill')} | {_f(p2['direction_accuracy'])} | {_f(p2['coverage_90'])} |")
    # Only the runs whose subject is the selection itself; the others fix or change one hyperparameter and are in the table above.
    sel = [(n, d) for n, d in docs if d["tables"].get("p2_selection_by_cell")
           and (n.startswith("main") or n.startswith("p2-selection") or n.startswith("recency"))]
    if sel:
        out += ["", "P2 selection by cell, over origins (lambda is the weight on precedents; `lambda zero` is the share of origins where it was 0):",
                "",
                "| setting | cell | selection | origins | mean lambda | lambda zero | mean bandwidth multiplier | median half-life (days) |",
                "|---|---|---|---|---|---|---|---|"]
        for name, doc in sel:
            for r in doc["tables"]["p2_selection_by_cell"]:
                hl = "none" if r["half_life_days_median"] is None else f"{r['half_life_days_median']:.0f}"
                out.append(f"| {name} | {r['cell']} | {r['selection']} | {r['origins']} | {_f(r['lambda_mean'], 2)} | "
                           f"{_f(r['share_lambda_zero'], 2)} | {_f(r['bandwidth_mult_mean'], 3)} | {hl} |")
    return out + [""]


def guard_lines(reports: Path, source: str) -> list[str]:
    """Guarded against unguarded P2 selection (``scripts/compare_guard.py`` writes the JSON read here)."""
    f = Path(reports) / "ablations" / f"p2-guard-{source}.json"
    if not f.exists():
        return []
    d = json.loads(f.read_text(encoding="utf-8"))
    g, u, diff = d["guarded"], d["unguarded"], d["difference"]

    def ci(row: dict, key: str) -> str:
        return f"{_f(row[key])} ({_f(row[key + '_lo'])} to {_f(row[key + '_hi'])})"

    def dci(key: str) -> str:
        return f"{diff[key]['estimate']:+.4f} ({diff[key]['lo']:+.4f} to {diff[key]['hi']:+.4f})"

    zero_g, zero_u = _f(g["share_lambda_zero"], 3), _f(u["share_lambda_zero"], 3)
    held_g, held_u = _f(g["share_guard_held"], 3), _f(u["share_guard_held"], 3)
    out = [f"### P2 admission guard, {source.capitalize()}", "",
           "The admission guard is the ladder's admission rule made operational: a rung is used only when it beats the rung below out of "
           "sample by more than noise. For every cell and origin, P2 uses a precedent weight lambda above zero only when its out-of-sample "
           f"log-score gain over lambda 0, minus {_f(g['guard'], 1)} standard errors across tests, is above zero; otherwise lambda is 0 "
           "and P2 equals P1. Guarded is the main run; unguarded is `--p2-guard off`, the earlier rule that takes the best of the "
           f"candidate lambdas whatever its noise. Both runs scored the same {g['n']} rows in {g['n_tests']} tests. "
           "Intervals are 90 percent bootstrap intervals by test.", "",
           "| selection | log score | CRPS | Brier skill | cells held at lambda 0 | held by the guard |", "|---|---|---|---|---|---|",
           f"| guarded | {ci(g, 'logscore')} | {ci(g, 'crps')} | {ci(g, 'brier_skill')} | {zero_g} | {held_g} |",
           f"| unguarded | {ci(u, 'logscore')} | {ci(u, 'crps')} | {ci(u, 'brier_skill')} | {zero_u} | {held_u} |",
           "", "Paired difference, guarded minus unguarded, on the same rows (positive log score and Brier skill favour the guard, "
           "negative CRPS favours the guard):", "",
           "| log score | CRPS | Brier skill |", "|---|---|---|", f"| {dci('logscore')} | {dci('crps')} | {dci('brier_skill')} |", ""]
    return out


CAUTIONARY_SUFFIX = "effect-scale-relative+s-star-realized"


def cautionary_lines(reports: Path, source: str = "upworthy") -> list[str]:
    """The cautionary run: relative lift as y and the realized standard error as the forecaster's scale, with calibration by precision."""
    found = visible_glob(Path(reports) / "ablations", f"backtest-{source}-*--{CAUTIONARY_SUFFIX}.json")
    if not found:
        return []
    doc = json.loads(found[-1].read_text(encoding="utf-8"))
    h = doc["header"]
    out = ["### The cautionary run", "",
           "The first full run scored Upworthy on the relative lift against the reference arm and gave the forecaster each row's realized standard error. "  # noqa: E501
           "It is reproduced here by `moot backtest --source upworthy --effect-scale relative --s-star realized`. A relative lift against a noisy reference "  # noqa: E501
           "arm is tied to its own standard error through the reference arm's realized rate, and the realized standard error is information from inside the "  # noqa: E501
           "test, so a calibrated forecaster could not have used it. The released protocol uses the absolute difference and a standard error known before launch.", "",  # noqa: E501
           f"{h['scored_rows']} rows scored over {h['origins_scored']} origins. Command: `{h['command']}`.", "",
           "| rung | n | log score | Brier skill (90% interval) | coverage 80% / 90% |", "|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {r['n']} | {_f(r['logscore'])} | {_ci(r, 'brier_skill')} | {_f(r['coverage_80'])} / {_f(r['coverage_90'])} |"
            for r in doc["tables"]["aggregate"] if r["cell"] == "ALL" and r["rung"] in ("P0", "P1", "P2", "GBM")]
    rows = [r for r in doc["tables"].get("calibration_by_precision") or [] if r["rung"] in ("P1", "P2")]
    if rows:
        out += ["", "Calibration by precision, deciles of the planned exposures per arm. `mean p_sig` should match `event rate` in every row; "
                "in the cautionary run it does not: p_sig is above the event rate in every decile, and the realized standard error stands in for information the forecaster could not have had.", "",  # noqa: E501
                "| rung | decile | planned exposures per arm | n | mean s_star | mean p_sig | event rate | coverage 90% |", "|---|---|---|---|---|---|---|---|"]  # noqa: E501
        out += [f"| {r['rung']} | {r['decile']} | {r['exposure_lo']:.0f} to {r['exposure_hi']:.0f} | {r['n']} | {_f(r.get('mean_s_star'))} | "
                f"{_f(r['mean_p_sig'])} | {_f(r['event_rate'])} | {_f(r['coverage_90'])} |" for r in rows]
    return out + [""]


def learning_curve_lines(reports: Path, source: str | None = None) -> list[str]:
    """The learning-curve tables, one per report file, with the gate sizes at both power targets."""
    files = visible_glob(reports, f"learning-curve-{source or '*'}-*.json")
    out: list[str] = []
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        out += [f"### Learning curve, {doc['source'].capitalize()}", "",
                f"Final origin {doc['final_origin'][:10]}, {doc['heldout_rows']} held-out rows in {doc['heldout_tests']} tests, "
                "the same in every run. "
                f"Each fraction keeps that share of the history's tests, {doc['seeds']} random subsamples per fraction. The interval is a 90 percent "
                "bootstrap by held-out test of the seed-averaged Brier skill.", ""]
        for k, v in sorted((doc["gates"].get("by_target") or {}).items(), key=lambda kv: float(kv[0])):
            out.append(f"- Gate sizes at power {k}: n_200 = {v['n_200']}, n_400 = {v['n_400']}")
        out += ["", "| fraction | history rows | rung | Brier skill (90% interval) | seed sd | log score | direction accuracy |",
                "|---|---|---|---|---|---|---|"]
        out += [f"| {r['fraction']} | {r['n_fit_rows']:.0f} | {r['rung']} | {_f(r['skill'])} ({_f(r['skill_lo'])} to {_f(r['skill_hi'])}) | "
                f"{_f(r['skill_seed_sd'])} | {_f(r['logscore'])} | {_f(r['direction_accuracy'])} |" for r in doc["rows"]]
        out += ["", f"![learning curve, {doc['source']}](reports/figures/learning_curve-{doc['source']}.png)", ""]
    return out


def second_opinion_lines(reports: Path) -> list[str]:
    """Lines for every recorded second opinion that was backtested: scores by contamination status and the limitation sentence."""
    docs = visible_glob(reports, "second-opinion-*/backtest-*--second-opinion.json")
    if not docs:
        return []
    out = ["### Second opinion from recorded agents", ""]
    sentence = ""
    for f in docs:
        doc = json.loads(f.read_text(encoding="utf-8"))
        so, src = doc["header"]["second_opinion"], doc["header"]["source"]
        sentence = doc["notes"]["second_opinion"]
        out += [f"Agent {so['provider_id']} version {so['version']} on {src}: weight in force {_f(so['weight'], 2)}; "
                f"{so['n_with_opinion']} of {so['n_rows']} rows had an opinion and {so['n_declined']} were declined. "
                f"The weight stays zero until it is earned on the backtest.", "",
                "| origins | rung | n | Brier | Brier skill (90% interval) |", "|---|---|---|---|---|"]
        out += [f"| {r['origins']} | {r['rung']} | {r['n']} | {_f(r['brier'])} | {_ci(r, 'brier_skill')} |" for r in doc["tables"]["second_opinion"]]
        out += [""]
    return out + [sentence, ""]


def render_block(reports_dir) -> str:
    reports = Path(reports_dir)
    gates = json.loads((reports / "gates.json").read_text(encoding="utf-8"))
    out = ["_Generated by `scripts/render_readme_results.py` from the report JSON files. Do not edit by hand. "
           "Intervals are 90 percent bootstrap intervals that resample whole tests._", ""]
    docs = {s: _latest(reports, s) for s, _ in SOURCES}
    for src, title in SOURCES:
        doc = docs[src]
        h = doc["header"]
        syn = " (synthetic data, known truth)" if h["synthetic"] else ""
        out += [f"### {title} backtest{syn}", "",
                f"Snapshot {h['snapshot_id']}, model {h['model_id']}, seed {h['seed']}. {h['scored_rows']} rows scored over "
                f"{h['origins_scored']} quarterly origins out of {h['admitted_rows']} admitted. Command: `{h['command']}`.", ""]
        out += results_table(doc) + [""]
        out += [sentence_skill(doc), "", bins_sentence(doc), "", sentence_rungs(doc), ""]
        out += precision_table(doc) + [""]
        out += ["Direction accuracy against its ceiling, every rung and the two direction baselines (always the reference arm, always the variant):",
                ""]
        out += direction_table(doc) + [""]
        if src == "asos":
            out += ["The ASOS calendar is nominal (see DATA.md): the file has no dates, so this backtest predicts across an arbitrary order and "
                    "says nothing about drift. Per-metric cells are small, and the table says which are undecidable at their n.", ""]
        if src == "upworthy":
            out += ["Abstention by trigger (rows that fired each trigger; a row can fire several):", ""] + abstention_table(doc)
            out += ["", doc["notes"]["abstention_triggers"], ""]
            out += [decision_sentence(doc), ""]
    h = docs["upworthy"]["header"]
    out += ["### Synthetic gate power (synthetic data only)", "",
            f"Share of simulated gates whose 95 percent bootstrap interval for the Brier gain clears zero, base rate {gates['base_rate']}, "
            f"{gates['reps']} replicates, seed {gates['seed']}. Sizes below read the same power curve at two levels.", ""]
    out += power_lines(gates) + [""]
    out += ["### Figures", "",
            "Reliability diagram of p_sig, Upworthy:", "", "![reliability diagram, Upworthy](reports/figures/reliability-upworthy.png)", "",
            "Decision value, Upworthy:", "", "![decision value, Upworthy](reports/figures/decision_value-upworthy.png)", "",
            "Reliability diagram of p_sig, synthetic data with known truth:", "",
            "![reliability diagram, synthetic](reports/figures/reliability-synthetic.png)", ""]
    out += challenger_lines(reports)
    for src, _title in SOURCES:
        out += ablation_lines(reports, src)
        out += guard_lines(reports, src)
    out += cautionary_lines(reports)
    out += learning_curve_lines(reports)
    out += second_opinion_lines(reports)
    lat = reports / "card-latency.json"
    if lat.exists():
        L = json.loads(lat.read_text(encoding="utf-8"))
        out += ["### Card latency", "",
                f"Upworthy cards, {L['impressions']} impressions per arm, model {L['model_id']}. Milliseconds.", "",
                "| path | p50 | p95 | max |", "|---|---|---|---|"]
        for label, key in (("in process, bundle preloaded", "in_process_ms"), ("HTTP service on loopback, bundle preloaded", "service_ms"),
                           ("command line, fresh process", "cli_fresh_process_ms")):
            out.append(f"| {label} | {L[key]['p50']} | {L[key]['p95']} | {L[key]['max']} |")
        out += [""]
    log = reports / "run-log.json"
    if log.exists():
        R = json.loads(log.read_text(encoding="utf-8"))
        out += ["### Run time", "", "| stage | seconds |", "|---|---|"]
        out += [f"| {s['stage']} | {s['seconds']} |" for s in R["stages"]]
        what = (f"Clean-clone download {R['download_seconds']} s ({R['downloaded_files']} files, {R['downloaded_bytes']} bytes)"
                if R.get("data_stage_kind") == "download"
                else f"Checksum verification {R['download_seconds']} s (no download in this run)")
        out += ["", f"{what}, compute {R['compute_seconds']} s, total {R['total_seconds']} s."]
    return "\n".join(out).rstrip() + "\n"


def sync_figures(reports_dir: Path, target: Path) -> int:
    """Copy the generated figures into the repo-local folder the README links to (they are small and committed)."""
    src = reports_dir / "figures"
    if not src.is_dir() or src.resolve() == target.resolve():
        return 0
    target.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in visible_glob(src, "*.png"):
        shutil.copyfile(f, target / f.name)
        n += 1
    return n


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reports-dir", default=str(storage_paths().reports))
    ap.add_argument("--readme", default=str(root / "README.md"))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()
    readme = Path(args.readme)
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(f"{readme} lacks the {START} and {END} markers", file=sys.stderr)
        return 2
    head, rest = text.split(START, 1)
    old, tail = rest.split(END, 1)
    block = render_block(args.reports_dir)
    new = head + START + "\n" + block + END + tail
    if args.write:
        readme.write_text(new, encoding="utf-8")
        sync_figures(Path(args.reports_dir), readme.parent / README_FIGURES)
        print(f"rewrote the results block of {readme}")
        return 0
    if old.strip() != block.strip():
        print("README.md results block differs from the reports; run with --write", file=sys.stderr)
        return 1
    print("README.md results block matches the reports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
