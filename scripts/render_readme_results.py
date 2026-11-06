#!/usr/bin/env python3
"""Render the results block of docs/results.md from the backtest report JSON files, so no result number is typed by hand.

The block sits between ``<!-- moot-results:start -->`` and ``<!-- moot-results:end -->`` in docs/results.md (it lived in the
README until the README became a reader's entry point; the page keeps the name of the script). Every number in
it is read from ``reports/backtest-<source>-<snapshot>.json`` (and ``reports/gates.json``, plus the optional
``reports/card-latency.json`` and ``reports/run-log.json``). Use:

    python scripts/render_readme_results.py --write    # rewrite the block in docs/results.md and copy the figures to docs/figures
    python scripts/render_readme_results.py --check    # exit 1 if docs/results.md differs from the reports

The README holds a generated two-line summary between ``<!-- moot-headline:start -->`` and ``<!-- moot-headline:end -->``; ``--write`` and
``--check`` handle it with the page. ``render_block(reports_dir)`` returns the text between the markers; its figure links are
relative to docs/results.md.
"""
# ruff: noqa: E501  (the prose of the generated page is written as long literal strings)
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from mootcourt.storage import storage_paths, visible_glob

START, END = "<!-- moot-results:start -->", "<!-- moot-results:end -->"
HEAD_START, HEAD_END = "<!-- moot-headline:start -->", "<!-- moot-headline:end -->"      # the README's two-line summary
PAGE = Path("docs") / "results.md"               # the page that holds the block
FIGURES_DIR = Path("docs") / "figures"           # the figures it links, small and committed
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


def _ladder(doc: dict) -> list[dict]:
    """The ladder's own rows (P0 to P3); the challengers and the direction baselines have their own tables."""
    return [r for r in doc["tables"]["aggregate"] if r.get("kind", "ladder") == "ladder"]


def _dec(r: dict, key: str) -> str:
    return SHORT.get(r.get(key), r.get(key) or "n/a")


def results_table(doc: dict) -> list[str]:
    """The main table. The verdict at base rate 0.3 is shown only when it differs from the verdict at the cell's own nearest rate, and the by-row verdict
    only when the gates count rows (when they count tests it reads "not computed" on every row and says nothing)."""
    gate = doc["header"].get("gate_decision_target")
    gate_txt = f"{gate:.2f}" if gate is not None else "release"
    research = min(doc["header"].get("gate_by_target") or {"0.80": 0}, key=float)
    rows = _ladder(doc)
    show_03 = any(r.get("decidable_by_tests_base_0.3") != r.get("decidable_by_tests") for r in rows)
    show_rows = any(not str(r.get("decidable", "")).startswith("not computed") for r in rows)
    cols = [("cell", lambda r: r["cell"]), ("rung", lambda r: r["rung"]), ("n", lambda r: r["n"]), ("log score", lambda r: _f(r["logscore"])),
            ("Brier skill (90% interval)", lambda r: _ci(r, "brier_skill")),
            (f"decidable by tests ({gate_txt} gate, at the cell's base rate)", lambda r: _dec(r, "decidable_by_tests")),
            ("gate base rate", lambda r: _f(r.get("gate_base_rate"), 2))]
    if show_03:
        cols.append((f"decidable by tests ({gate_txt} gate, base rate 0.3)", lambda r: _dec(r, "decidable_by_tests_base_0.3")))
    if show_rows:
        cols.append((f"decidable by rows ({gate_txt} gate, overstates)", lambda r: SHORT.get(r["decidable"], r["decidable"])))
    cols += [(f"decidable by tests ({research} screen)", lambda r: _dec(r, "decidable_research_by_tests")),
             ("coverage 80% / 90%", lambda r: f"{_f(r['coverage_80'])} / {_f(r['coverage_90'])}"), ("abstention rate", lambda r: _f(r["abstention_rate"]))]
    out = ["| " + " | ".join(h for h, _ in cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(g(r)) for _, g in cols) + " |" for r in rows]
    return out


def _pair(r: dict, lo: str, hi: str) -> str:
    return f"{_f(r.get(lo))} to {_f(r.get(hi))}"


def adjusted_table(doc: dict) -> list[str]:
    """The pooled rows with the percentile interval beside the Bonferroni-adjusted bounds for the family the table shows."""
    rows = [r for r in _ladder(doc) if r["cell"] == "ALL"]
    out = ["Percentile intervals beside Bonferroni-adjusted bounds, all cells pooled. The adjusted bounds cover every interval of the aggregate table at once "
           "(its family size is in the last column); the pooled interval is the primary claim, a rule fixed after the data were seen, and the per-cell intervals are descriptive.", "",
           "| rung | tests | Brier skill (90% interval) | Brier skill, adjusted bounds | log score (90% interval) | log score, adjusted bounds | intervals in the family |",
           "|---|---|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {r.get('n_tests')} | {_ci(r, 'brier_skill')} | {_pair(r, 'adjusted_lo', 'adjusted_hi')} | {_ci(r, 'logscore')} | "
            f"{_pair(r, 'logscore_adjusted_lo', 'logscore_adjusted_hi')} | {r.get('family_size')} |" for r in rows]
    return out


def calibration_table(doc: dict) -> list[str]:
    """ECE against the clustered and the independent null, the equal-mass ECE and the design effect behind the clustering."""
    rows = [r for r in _ladder(doc) if r["cell"] == "ALL"]
    out = ["Calibration error of `p_sig`, all cells pooled. The percentile is read in a perfect-calibration null that draws the contrasts of one test "
           "together (500 draws, so 100 means above every draw); the independent null draws every row alone and is kept for comparison.", "",
           "| rung | ECE | percentile, clustered null | percentile, independent null | equal-mass ECE | percentile, equal-mass | design effect | within-test correlation |",
           "|---|---|---|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {_f(r.get('ece'))} | {_f(r.get('ece_percentile'), 1)} | {_f(r.get('ece_percentile_independent'), 1)} | "
            f"{_f(r.get('ece_equal_mass'))} | {_f(r.get('ece_equal_mass_percentile'), 1)} | {_f(r.get('design_effect'), 2)} | {_f(r.get('icc'))} |" for r in rows]
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
            f"Its calibration error is {_f(r['ece'])}, at percentile {_f(r['ece_percentile'], 1)} of the clustered perfect-calibration null. "
            "P0 is the base-rate forecaster the skill is measured against, so its skill is zero by construction.")


def sentence_rungs(doc: dict) -> str:
    rungs = {r["rung"]: r for r in _ladder(doc) if r["cell"] == "ALL"}
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


def discrimination_table(doc: dict) -> list[str]:
    """AUC and resolution per rung (discrimination, apart from skill) and the Brier skill on the event defined on the planned standard error."""
    rows = [r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL" and r.get("auc_event") is not None]
    if not rows:
        return []
    out = ["Discrimination apart from skill, all cells pooled. AUC is the chance that a row with the event gets a higher `p_sig` than a row without it (0.5 is no "
           "discrimination); resolution is the Murphy term of the Brier score: how far the observed event frequencies of equal-mass forecast bins lie from the overall event rate (zero when every bin has the overall rate, and not a measure of how much the forecasts vary). The last columns score the same "
           "forecast against the event defined on the planned standard error instead of the realized one; the headline skill stays on the realized event.", "",
           "| rung | AUC of the event (90% interval) | resolution of the event | event rate, realized standard error | event rate, planned standard error | "
           "Brier skill on the planned event (90% interval) |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['rung']} | {_ci(r, 'auc_event')} | {_f(r.get('resolution_event'), 5)} | {_f(r.get('p_sig_mean'))} (mean `p_sig`) | "
                   f"{_f(r.get('event_rate_planned'))} | {_ci(r, 'brier_skill_planned')} |")
    return out


def guard_pairs_lines(reports: Path, source: str) -> list[str]:
    """The pairs of cell and origin where the guard admitted a weight above zero: the gain it saw in selection against what the next quarter gave."""
    found = visible_glob(Path(reports), f"paper-extras-{source}-*.json")
    if not found:
        return []
    g = json.loads(found[-1].read_text(encoding="utf-8")).get("guard_pairs")
    if not g or not g.get("rows"):
        return []
    sm = g["summary"]
    out = [f"### Guard pairs, {source.capitalize()}", "",
           "Every pair of cell and origin where the admission guard allowed a weight on precedents above zero. The in-selection gain is the mean log-score gain over weight "
           "zero on the validation rows of the fit (nats per row); the realized difference is the log score of P2 minus P1 on the rows scored at that origin. "
           "A guard that works would show realized differences near or above the in-selection gain.", "",
           "| cell | origin | weight | in-selection gain | its standard error | scored rows | scored tests | realized P2 minus P1 |", "|---|---|---|---|---|---|---|---|"]
    out += [f"| {r['cell']} | {r['origin'][:10]} | {_f(r['lambda'], 2)} | {_f(r['in_selection_gain'], 4)} | {_f(r['in_selection_gain_se'], 4)} | "
            f"{r['n_scored_rows']} | {r['n_scored_tests']} | {r['realized_p2_minus_p1']:+.4f} |" for r in g["rows"]]
    out += ["", f"Pairs admitted: {sm['pairs_admitted']} of {sm['pairs_in_selection']}; mean in-selection gain {_f(sm['mean_in_selection_gain'], 4)}; "
            f"pairs with a negative realized difference: {sm['pairs_with_negative_realized']}. Pooled over the scored rows ({sm['pooled_rows']} rows, "
            f"{sm['pooled_tests']} tests) the realized difference is {sm['pooled_realized_p2_minus_p1']:+.4f} "
            f"({sm['pooled_lo']:+.4f} to {sm['pooled_hi']:+.4f}, {sm['level'] * 100:.0f} percent bootstrap interval by test).", ""]
    return out


def coverage_ratio_table(doc: dict) -> list[str]:
    """Coverage by decile of the realized over the planned standard error (an evaluation-time stratifier, never a forecast input)."""
    rows = [r for r in doc["tables"].get("coverage_by_se_ratio") or [] if r["rung"] in ("P1", doc["header"]["primary_rung"])]
    if not rows:
        return []
    out = ["Coverage by decile of the realized over the planned standard error. The forecaster fixes the level of the outcome rate at the cell median, so its planned "
           "standard error is too small when the realized rate is higher and too large when it is lower: coverage is near 0.90 on average and not within "
           "these groups. The realized standard error is used here to group rows and is never an input of a forecast.", "",
           "| rung | decile | realized over planned standard error | n | mean ratio | mean p_sig | event rate | coverage 80% | coverage 90% |",
           "|---|---|---|---|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {r['decile']} | {r['ratio_lo']:.2f} to {r['ratio_hi']:.2f} | {r['n']} | {_f(r['mean_ratio'], 3)} | {_f(r['mean_p_sig'])} | "
            f"{_f(r['event_rate'])} | {_f(r['coverage_80'])} | {_f(r['coverage_90'])} |" for r in rows]
    return out


DECISION_BUDGET = 0.25


def _dv_rows(doc: dict) -> list[dict]:
    return [r for r in doc["tables"]["decision_value"] if r["origin"] == "ALL" and abs(r["budget"] - DECISION_BUDGET) < 1e-9]


def decision_table(doc: dict) -> list[str]:
    """Decision value at a budget of 25 percent of the tests, pooled over origins, with the difference from random order."""
    rows = _dv_rows(doc)
    if not rows:
        return []
    order = {"random": 0, "p_win": 1, "oracle": 2}
    rows = sorted(rows, key=lambda r: (order.get(r["policy"], 9), r["rung"]))
    out = ["Decision value at a budget of 25 percent of the tests (budgets of 10 and 50 percent are in the report), pooled over origins. "
           "Random order captures K over n of the total positive lift exactly. Intervals are 90 percent bootstrap intervals that resample whole tests "
           "within each origin. A rung whose win probability is constant within a cell chooses by cell and then at random.", "",
           "| policy | rung | captured fraction (90% interval) | difference from random order (90% interval) | chooses by cell only |", "|---|---|---|---|---|"]
    for r in rows:
        cons = {True: "yes", False: "no"}.get(r.get("constant_within_cell"), "n/a")
        out.append(f"| {r['policy']} | {r['rung']} | {_f(r['captured_fraction'])} ({_f(r['captured_fraction_lo'])} to {_f(r['captured_fraction_hi'])}) | "
                   f"{r['diff_random']:+.4f} ({r['diff_random_lo']:+.4f} to {r['diff_random_hi']:+.4f}) | {cons} |")
    return out


def decision_sentence(doc: dict) -> str:
    rows = _dv_rows(doc)
    get = lambda pol, rung: next((r for r in rows if r["policy"] == pol and r["rung"] == rung), None)  # noqa: E731
    primary = doc["header"]["primary_rung"]
    rnd, pw, orc = get("random", "all"), get("p_win", primary), get("oracle", "all")
    if not (rnd and pw and orc):
        return ""
    return (f"Decision value, a quarter of the tests, pooled over origins: random order captures {_f(rnd['captured_fraction'])} of the total "
            f"positive observed lift, choosing by {primary} p_win captures {_f(pw['captured_fraction'])} "
            f"(a difference from random order of {pw['diff_random']:+.4f}, interval {pw['diff_random_lo']:+.4f} to {pw['diff_random_hi']:+.4f}), "
            f"and an oracle that knows the result captures {_f(orc['captured_fraction'])}.")


def power_lines(gates: dict) -> list[str]:
    ns = sorted({r["n"] for r in gates["table"]})
    skills = sorted({r["skill"] for r in gates["table"]})
    look = {(r["n"], r["skill"]): r["power"] for r in gates["table"]}
    out = ["| Brier skill \\ scored tests | " + " | ".join(str(n) for n in ns) + " |", "|---|" + "---|" * len(ns)]
    out += [f"| {k:.2f} | " + " | ".join(f"{look[(n, k)]:.2f}" for n in ns) + " |" for k in skills]
    sizes = ["| base rate | power target | tests for skill 0.20 | tests for skill 0.10 |", "|---|---|---|---|"]
    by_rate = gates.get("by_base_rate") or {f"{gates['base_rate']:.2f}": gates}
    for br in sorted(by_rate, key=float):
        for t in sorted(by_rate[br]["by_target"], key=float):
            tag = " (release gate)" if abs(float(t) - gates["decision_target"]) < 1e-9 else " (research screen)"
            sizes.append(f"| {br} | {t}{tag} | {by_rate[br]['by_target'][t]['n_200']} | {by_rate[br]['by_target'][t]['n_400']} |")
    return sizes + [""] + out


def direction_table(doc: dict) -> list[str]:
    """Direction accuracy beside its ceiling for every rung, the direction baselines included, and on decisive rows (|y| above 1.96 s)."""
    rows = [r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL"]
    out = ["| rung | kind | direction accuracy (90% interval) | ceiling | decisive rows | direction accuracy on decisive rows |", "|---|---|---|---|---|---|"]
    out += [f"| {r['rung']} | {r.get('kind', '')} | {_ci(r, 'direction_accuracy')} | {_f(r.get('direction_ceiling'))} | "
            f"{r.get('n_decisive') or 0} | {_f(r.get('direction_accuracy_decisive'))} |" for r in rows]
    return out


def _all_row(doc: dict, rung: str) -> dict | None:
    return next((r for r in doc["tables"]["aggregate"] if r["cell"] == "ALL" and r["rung"] == rung), None)


def challenger_lines(reports: Path, source: str = "upworthy") -> list[str]:
    """Challengers beside the ladder on the same origins and rows. They are rungs of the main report: each has a raw row and a recalibrated one (``+cal``)."""
    found = visible_glob(Path(reports), f"backtest-{source}-*.json")
    if not found:
        return []
    doc = json.loads(found[-1].read_text(encoding="utf-8"))
    names = doc["header"].get("challengers") or []
    if not names:
        return []
    out = [f"### Challengers, {source.capitalize()}", "",
           "Same features, same origins, same rows as the ladder; the rows are rungs of the main report. A recalibrated row (`+cal`) is the challenger's `p_sig` "
           "through a Platt map fit on the out-of-fold predictions of the rows visible at the origin, so nothing from the scored rows reaches the map; it "
           "carries a probability only. A rung without a density has no log score and a rung without a probability has no Brier skill. "
           "Direction accuracy on decisive rows counts the rows whose estimate is more than 1.96 standard errors from zero.", "",
           "| rung | kind | n | log score | Brier skill (90% interval) | direction accuracy | direction accuracy on decisive rows | abstention rate |",
           "|---|---|---|---|---|---|---|---|"]
    keep = [_all_row(doc, n) for n in ("P1", "P2", *names)]
    out += [f"| {r['rung']} | {r.get('kind', '')} | {r['n']} | {_f(r['logscore'])} | {_ci(r, 'brier_skill')} | {_f(r['direction_accuracy'])} | "
            f"{_f(r.get('direction_accuracy_decisive'))} | {_f(r['abstention_rate'])} |" for r in keep if r]
    p2 = _all_row(doc, "P2")
    for name in names:
        r = _all_row(doc, name)
        if r and p2 and r["logscore"] is not None and p2["logscore"] is not None:
            d = r["logscore"] - p2["logscore"]
            word = "better" if d > 0.005 else "worse" if d < -0.005 else "about equal"
            out += ["", f"{name} minus P2 log score is {d:+.4f}, so {name} is {word} than P2 on this score."]
    clear = [r["rung"] for r in (_all_row(doc, n) for n in names) if r and r.get("brier_skill_lo") is not None and r["brier_skill_lo"] > 0]
    out += ["", ("Challenger rows whose Brier skill interval excludes zero: " + ", ".join(clear) + ".") if clear
            else "No challenger row has a Brier skill interval that excludes zero."]
    return out + [""]


def _guard_setting(doc: dict) -> str:
    g = doc["header"].get("p2_guard")
    return "n/a" if g is None else (str(g) if g == "off" else f"{float(g):.1f}")


def ablation_lines(reports: Path, source: str = "upworthy") -> list[str]:
    """Ablations of one source: the main run and every report in ``ablations/``, P1 and P2 side by side, with the guard setting of each run."""
    reports = Path(reports)
    main_files = visible_glob(reports, f"backtest-{source}-*.json")
    # The trigger-removal runs change abstention only, so every column below equals the main run's; they have their own table in the paper.
    var_files = sorted((f for f in visible_glob((reports / "ablations"), f"backtest-{source}-*--*.json") if "--drop-trigger-" not in f.name),
                       key=lambda f: (f.stem.split("--", 1)[1].replace("+p2-guard-off", ""), f.stem.endswith("+p2-guard-off")))
    if not main_files or not var_files:
        return []
    docs = [("main run (defaults)", json.loads(main_files[-1].read_text(encoding="utf-8")))]
    docs += [(f.stem.split("--", 1)[1], json.loads(f.read_text(encoding="utf-8"))) for f in var_files]
    out = [f"### Ablations, {source.capitalize()}", "",
           "Each row is one backtest on the same origins with one setting changed, written to its own report under `reports/ablations/`. "
           "All cells pooled. P2 minus P1 is the log score the precedents add; a value near zero means P2 reduced to P1. A setting named with "
           "`+p2-guard-off` is the same ablation without the admission guard, and `guard` is the multiplier in force (a fixed `lambda` bypasses the guard). "
           "`n` counts scored rows, which differ only in the prelaunch admission run.", "",
           "| setting | guard | n | P1 log score | P2 log score | P2 minus P1 | P2 Brier skill (90% interval) | P2 direction accuracy | P2 coverage 90% |",
           "|---|---|---|---|---|---|---|---|---|"]
    for name, doc in docs:
        p1, p2 = _all_row(doc, "P1"), _all_row(doc, "P2")
        if p1 and p2:
            out.append(f"| {name} | {_guard_setting(doc)} | {p2['n']} | {_f(p1['logscore'])} | {_f(p2['logscore'])} | {p2['logscore'] - p1['logscore']:+.4f} | "
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
           "P2 reduces to P1 at a precedent weight (lambda) of zero. The admission guard decides when the weight may be above zero: for every cell and origin it "
           f"takes the validation rows of the fit, computes the log-score gain of each candidate weight over lambda 0, and admits a weight only when that gain "
           f"minus {_f(g['guard'], 1)} standard errors (clustered by test) is above zero; otherwise lambda is 0 and P2 equals P1. The guard works on "
           "validation rows inside the fit, so it limits how much noise the selection can fit; it does not promise that P2 beats P1 on later tests, "
           "which the paired comparison below measures. Guarded is the main run; unguarded is `--p2-guard off`, the earlier rule that takes the best of the "
           f"candidate weights whatever its noise. Both runs scored the same {g['n']} rows in {g['n_tests']} tests. "
           "Intervals are 90 percent bootstrap intervals by test.", "",
           "| selection | log score | CRPS | Brier skill | cells held at lambda 0 | held by the guard |", "|---|---|---|---|---|---|",
           f"| guarded | {ci(g, 'logscore')} | {ci(g, 'crps')} | {ci(g, 'brier_skill')} | {zero_g} | {held_g} |",
           f"| unguarded | {ci(u, 'logscore')} | {ci(u, 'crps')} | {ci(u, 'brier_skill')} | {zero_u} | {held_u} |",
           "", "Paired difference, guarded minus unguarded, on the same rows (positive log score and Brier skill favour the guard, "
           "negative CRPS favours the guard):", "",
           "| log score | CRPS | Brier skill |", "|---|---|---|", f"| {dci('logscore')} | {dci('crps')} | {dci('brier_skill')} |", ""]
    return out


def positive_control_lines(reports: Path) -> list[str]:
    """The synthetic archive with a planted text effect: does the guard admit a weight on precedents where there is something to learn?"""
    found = visible_glob(Path(reports) / "positive-control", "backtest-synthetic-*.json")
    if not found:
        return []
    doc = json.loads(found[-1].read_text(encoding="utf-8"))
    h = doc["header"]
    out = ["### Positive control, synthetic", "",
           "The synthetic archive with no text signal shows how often the guard admits a weight when no text signal is planted. An earlier version of this control admitted a weight in most cells at 3,700 tests; the cause was P1's thin latest period, which moved the level on a handful of rows and which the guard detected as a precedent gain, not the precedents (method call 198 and the period control). Under the period rule P1 takes its period level from the last complete quarter, and the share admitted with no planted signal is read from the table below. This run plants "
           "a text effect between headlines with and without a signal word (`moot simulate ledger --text-effect 1.0`, a 1.0 percent lift, "
           "0.33 to 0.67 prior standard deviations in the default cells) and runs the whole protocol on it. If the guard works, it should admit a weight "
           "in `headline_only`, where the effect is planted, and hold it at zero in the other cells. "
           f"{h['scored_rows']} rows scored over {h['origins_scored']} origins. Command: `{h['command']}`.", "",
           "| cell | rung | n | log score | Brier skill (90% interval) |", "|---|---|---|---|---|"]
    out += [f"| {r['cell']} | {r['rung']} | {r['n']} | {_f(r['logscore'])} | {_ci(r, 'brier_skill')} |"
            for r in doc["tables"]["aggregate"] if r["rung"] in ("P1", "P2") and r["cell"] != "ALL"]
    out += ["", "P2 selection by cell, over origins:", "",
            "| cell | origins | mean lambda | lambda zero | held by the guard |", "|---|---|---|---|---|"]
    out += [f"| {r['cell']} | {r['origins']} | {_f(r['lambda_mean'], 2)} | {_f(r['share_lambda_zero'], 2)} | {_f(r['share_guard_held'], 2)} |"
            for r in doc["tables"]["p2_selection_by_cell"]]
    extras = visible_glob(Path(reports), "paper-extras-synthetic-*.json")
    sens = json.loads(extras[-1].read_text(encoding="utf-8")).get("positive_control_sensitivity") if extras else None
    if sens:
        out += ["", f"Sensitivity of the guard: the share of cell fits (multiplier {_f(sens['multiplier'], 1)}) that admit a weight above zero, by the strength of the planted "
                "effect and the number of tests in the ledger. The strength over the prior standard deviation is given for the default `headline_only` cell.", "",
                "| tests in the ledger | planted lift (percent) | strength over prior standard deviation | cell fits | admitted | share admitted |",
                "|---|---|---|---|---|---|"]
        out += [f"| {r['n_tests']} | {_f(r['text_effect_strength'], 1)} | {_f(r['strength_over_prior_sd']['headline_only'], 2)} | {r['cells']} | "
                f"{r['admitted']} | {_f(r['share_admitted'], 2)} |" for r in sens["rows"]]
    return out + [""]


def proxy_lines(reports: Path) -> list[str]:
    """The exposure stand-in for the planned standard error: its correlation with the size of the effect, per archive."""
    out = []
    for src, title in SOURCES[:2]:
        found = visible_glob(Path(reports), f"paper-extras-{src}-*.json")
        if not found:
            return []
        c = json.loads(found[-1].read_text(encoding="utf-8"))["impressions_effect_correlation"]
        out.append((title, c))
    return ["### Admission and the exposure proxy", "",
            "The planned standard error is a function of the planned exposure, and the exposure of an archived test is a stand-in recorded after the fact. "
            "These correlations show how much of the effect the stand-in carries: the larger the correlation of the log exposure with the absolute standardized "
            "effect, the more a model that reads the exposure learns from information a launching team would not have had. "
            "`moot backtest --admission prelaunch` admits on exposure only and appears among the ablations above.", "",
            "| archive | rows | correlation of log exposure with absolute standardized effect | correlation with the significant-positive event | "
            "correlation of log run length with absolute standardized effect |", "|---|---|---|---|---|",
            *[f"| {t} | {c['n_rows']} | {_f(c['corr_log_impressions_abs_z'], 3)} | {_f(c['corr_log_impressions_event'], 3)} | "
              f"{_f(c.get('corr_log_run_length_abs_z'), 3)} |" for t, c in out], ""]


def replay_lines(reports: Path) -> list[str]:
    """The weekly replay: one card per row, joined the first week the outcome exists, abstained cards scored like the others."""
    rows = []
    for src, title in SOURCES[:2]:
        found = visible_glob(Path(reports), f"replay-{src}-*.json")
        if found:
            rows.append((title, json.loads(found[-1].read_text(encoding="utf-8"))))
    if not rows:
        return []
    out = ["### Weekly replay", "",
           "`scripts/replay_weekly.py` issues one card per admitted row at the start of the week its test starts and joins the outcome at the first weekly join "
           "after it exists. An abstained card keeps the forecast it withheld in its frozen file, and the join scores it like any other, flagged, so abstention does not stop a cell from "
           "recovering. Coverage is the share of observed estimates inside the 90 percent interval for the observed estimate that the card stores.", "",
           "| archive | weeks | cards | outcomes joined | abstained cards | flagged weeks | coverage 90% (n) | hit | magnitude miss | direction miss | "
           "confident but wrong | abstained but clear |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for title, d in rows:
        t, m = d["totals"], d["totals"]["miss_counts"]
        out.append(f"| {title} | {d['header']['n_weeks']} | {t['cards_issued']} | {t['outcomes_joined']} | {t['abstained']} | {t['n_flagged_weeks']} | "
                   f"{_f(t['coverage_90_all'], 3)} ({t['coverage_90_all_n']}) | {m['hit']} | {m['magnitude_miss']} | {m['direction_miss']} | "
                   f"{m['confident_but_wrong']} | {m['abstained_but_clear']} |")
    return out + [""]


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
            out.append(f"- Gate sizes (tests) at power {k}: n_200 = {v['n_200']}, n_400 = {v['n_400']}")
        out += ["", "| fraction | history rows | rung | Brier skill (90% interval) | seed sd | log score | direction accuracy |",
                "|---|---|---|---|---|---|---|"]
        out += [f"| {r['fraction']} | {r['n_fit_rows']:.0f} | {r['rung']} | {_f(r['skill'])} ({_f(r['skill_lo'])} to {_f(r['skill_hi'])}) | "
                f"{_f(r['skill_seed_sd'])} | {_f(r['logscore'])} | {_f(r['direction_accuracy'])} |" for r in doc["rows"]]
        out += ["", f"![learning curve, {doc['source']}](figures/learning_curve-{doc['source']}.png)", ""]
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


def counts_lines(h: dict) -> list[str]:
    """The counts of tests the header records and the guard setting of the run."""
    if "tests_in_ledger" not in h:
        return []
    guard = h.get("p2_guard")
    return [f"Tests: {h['tests_in_ledger']} in the ledger, {h['tests_admitted']} admitted, {h['tests_scored']} scored. {h.get('test_count_definition', '')}".rstrip(),
            "", f"P2 admission guard: {'off' if guard == 'off' else f'{_f(guard, 1)} standard errors'}.", ""]


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
        out += counts_lines(h)
        out += results_table(doc) + [""]
        out += ["P0 is the empirical base-rate forecaster, so its Brier skill is zero by construction and its interval has no width. "
                "The gate columns read the number of scored tests against the gate sized at the base rate nearest the cell's own. A column for the "
                "earlier convention (base rate 0.3) or for the by-row verdict appears only when it says something the first column does not.", ""]
        out += [sentence_skill(doc), "", bins_sentence(doc), "", sentence_rungs(doc), ""]
        out += adjusted_table(doc) + [""]
        out += calibration_table(doc) + [""]
        out += discrimination_table(doc) + [""]
        out += precision_table(doc) + [""]
        out += coverage_ratio_table(doc) + [""]
        out += ["Direction accuracy against its ceiling, every rung and the two direction baselines (always the reference arm, always the variant):",
                ""]
        out += direction_table(doc) + [""]
        if src == "asos":
            out += ["The ASOS calendar is nominal (see DATA.md): the file has no dates, so this backtest predicts across an arbitrary order and "
                    "says nothing about drift. Per-metric cells are small, and the table says which are undecidable at their n.", ""]
        if src == "upworthy":
            out += ["Abstention by trigger (rows that fired each trigger; a row can fire several):", ""] + abstention_table(doc)
            out += ["", doc["notes"]["abstention_triggers"], ""]
            out += decision_table(doc) + ["", decision_sentence(doc), ""]
    out += ["### Synthetic gate power (synthetic data only)", "",
            f"Share of simulated gates whose {gates['interval']['level'] * 100:.0f} percent bootstrap interval for the Brier gain clears zero. "
            f"A simulated ledger draws tests of {gates['interval']['rows_per_test']} rows on average with one forecast per test, and the interval resamples whole tests, "
            "so the sizes are numbers of tests, the unit the decidability columns count. "
            f"The first table sizes the gate at each base rate; the second is the power curve at base rate {gates['base_rate']}, "
            f"{gates['reps']} replicates, seed {gates['seed']}.", ""]
    out += power_lines(gates) + [""]
    out += ["### Figures", "",
            "Reliability diagram of p_sig, Upworthy:", "", "![reliability diagram, Upworthy](figures/reliability-upworthy.png)", "",
            "Decision value, Upworthy:", "", "![decision value, Upworthy](figures/decision_value-upworthy.png)", "",
            "Reliability diagram of p_sig, synthetic data with known truth:", "",
            "![reliability diagram, synthetic](figures/reliability-synthetic.png)", ""]
    out += challenger_lines(reports)
    for src, _title in SOURCES:
        out += ablation_lines(reports, src)
        out += guard_lines(reports, src)
        out += guard_pairs_lines(reports, src)
    out += positive_control_lines(reports)
    out += proxy_lines(reports)
    out += cautionary_lines(reports)
    out += replay_lines(reports)
    out += learning_curve_lines(reports)
    out += second_opinion_lines(reports)
    lat = reports / "card-latency.json"
    if lat.exists():
        L = json.loads(lat.read_text(encoding="utf-8"))
        out += ["### Card latency", "",
                f"Upworthy cards, {L['impressions']} impressions per arm, model {L['model_id']}. Milliseconds.", "",
                "| path | p50 | p95 | max |", "|---|---|---|---|"]
        for label, key in (("in process, bundle preloaded", "in_process_ms"), ("in process, weight on precedents forced to 0.5", "in_process_lambda_0.5_ms"),
                           ("HTTP service on loopback, bundle preloaded", "service_ms"), ("command line, fresh process", "cli_fresh_process_ms")):
            if key in L:
                out.append(f"| {label} | {L[key]['p50']} | {L[key]['p95']} | {L[key]['max']} |")
        st, st5 = L.get("statuses") or {}, L.get("statuses_lambda_0.5") or {}
        if st:
            out += ["", f"Of {sum(st.values())} made-up headlines, {st.get('abstain', 0)} abstained at the fitted weight on precedents"
                    + (f" and {st5.get('abstain', 0)} with the weight forced to 0.5." if st5 else ".")]
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
    """Copy the generated figures into the folder the results page links to (they are small and committed)."""
    src = reports_dir / "figures"
    if not src.is_dir() or src.resolve() == target.resolve():
        return 0
    target.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in visible_glob(src, "*.png"):
        shutil.copyfile(f, target / f.name)
        n += 1
    return n


def _verdict(row: dict) -> str:
    lo, hi = row["brier_skill_lo"], row["brier_skill_hi"]
    if hi < 0:
        return "worse than the constant base rate"
    return "better than the constant base rate" if lo > 0 else "not distinguishable from the constant base rate"


def headline_lines(reports_dir) -> list[str]:
    """The README's two-line summary, one line per archive, read from the report JSON like every other number."""
    reports = Path(reports_dir)
    out = []
    for src, title in SOURCES[:2]:
        doc = _latest(reports, src)
        p1, p2 = _row(doc, "ALL", "P1"), _row(doc, "ALL", "P2")
        cells = [r for r in doc["tables"]["aggregate"] if r["rung"] == "P2" and r["cell"] != "ALL"]
        undecided = sum(1 for r in cells if r.get("decidable_by_tests") == "undecidable at this n")
        out.append(f"- {title}, {p1['n']} scored rows: Brier skill against the base rate on all rows is {_ci(p1, 'brier_skill')} for P1 "
                   f"({_verdict(p1)}) and {_ci(p2, 'brier_skill')} for P2 ({_verdict(p2)}); "
                   f"{undecided} of {len(cells)} cells are undecidable at this n "
                   f"at the release gate.")
    return out


def _swap(text: str, start: str, end: str, body: str) -> tuple[str, str] | None:
    """(the text with the body between the markers replaced, the old body), or None when a marker is missing."""
    if start not in text or end not in text:
        return None
    head, rest = text.split(start, 1)
    old, tail = rest.split(end, 1)
    return head + start + "\n" + body + end + tail, old


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reports-dir", default=str(storage_paths().reports))
    ap.add_argument("--page", "--readme", dest="readme", default=str(root / PAGE), help="the page that holds the block (default docs/results.md)")
    ap.add_argument("--front", default=str(root / "README.md"), help="the file that holds the two-line headline summary (default README.md)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()
    page, front = Path(args.readme), Path(args.front)
    jobs = [(page, START, END, lambda: render_block(args.reports_dir), "results block"),
            (front, HEAD_START, HEAD_END, lambda: "\n".join(headline_lines(args.reports_dir)) + "\n", "headline summary")]
    texts = {path: path.read_text(encoding="utf-8") for path, *_ in jobs}
    for path, start, end, _body, _what in jobs:                  # every marker is checked before anything is written
        if start not in texts[path] or end not in texts[path]:
            print(f"{path} lacks the {start} and {end} markers", file=sys.stderr)
            return 2
    stale = 0
    for path, start, end, build, what in jobs:
        text, body = texts[path], build()
        new, old = _swap(text, start, end, body)
        if args.write:
            if new != text:
                path.write_text(new, encoding="utf-8")
            print(f"rewrote the {what} of {path}")
        elif old.strip() != body.strip():
            print(f"{path.name} {what} differs from the reports; run with --write", file=sys.stderr)
            stale += 1
        else:
            print(f"{path.name} {what} matches the reports")
    if args.write:
        sync_figures(Path(args.reports_dir), root / FIGURES_DIR)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
