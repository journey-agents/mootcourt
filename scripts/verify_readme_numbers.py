#!/usr/bin/env python3
"""Independent check of the numbers in the results block of docs/results.md (the block lived in the README until the README became
a reader's entry point; the script keeps its name).

Standard library plus pandas only; nothing is imported from mootcourt. The script reads the page, finds every
table in the results block, re-derives numbers from the report JSON files under the data root (and, for the
backtest tables, from the per-row score tables next to them), and compares each to the printed value at the
printed precision. It exits 1 when a number disagrees or when a table has fewer than three numbers checked.

Usage: MOOTCOURT_DATA_ROOT=/path/to/root python scripts/verify_readme_numbers.py [--page docs/results.md] [--reports DIR]
Without either it looks in reports/ of the working folder and, finding no backtest report, ends in one line naming both.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from pathlib import Path

import pandas as pd

NUM = re.compile(r"[+-]?\d+(?:\.\d+)?")
RESULTS = []          # (section, table_label, token, derived, ok)


def decimals(tok: str) -> int:
    return len(tok.split(".")[1]) if "." in tok else 0


def check(section: str, label: str, tok: str, derived) -> bool:
    """Compare one printed token with a derived value at the printed precision."""
    tok = tok.strip()
    if derived is None or (isinstance(derived, float) and math.isnan(derived)):
        ok = tok == "n/a"
        RESULTS.append((section, label, tok, "nan" if derived is not None else "None", ok))
        return ok
    if tok == "n/a":
        RESULTS.append((section, label, tok, derived, False))
        return False
    d = decimals(tok)
    ok = abs(float(derived) - float(tok)) <= 0.5 * 10 ** (-d) + 1e-9
    RESULTS.append((section, label, tok, derived, ok))
    return ok


def parse_tables(block: list[str]) -> list[tuple[list[str], list[list[str]]]]:
    """Every pipe table in `block` as (header cells, body rows)."""
    out, i = [], 0
    while i < len(block):
        if block[i].startswith("|") and i + 1 < len(block) and re.match(r"^\|[-| ]+\|$", block[i + 1].strip()):
            head = [c.strip() for c in block[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(block) and block[j].startswith("|"):
                rows.append([c.strip() for c in block[j].strip().strip("|").split("|")])
                j += 1
            out.append((head, rows))
            i = j
        else:
            i += 1
    return out


def split_sections(text: str) -> dict[str, list[str]]:
    m = re.search(r"<!-- moot-results:start -->(.*)<!-- moot-results:end -->", text, re.S)
    if not m:
        sys.exit("the page has no results block")
    sections, cur = {}, None
    for ln in m.group(1).splitlines():
        if ln.startswith("### "):
            cur = ln[4:].strip()
            sections[cur] = []
        elif cur:
            sections[cur].append(ln)
    return sections


class MissingInput(Exception):
    """A report the page cites is not under the reports folder; ``main`` turns it into one line naming the folder flag."""


def jload(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise MissingInput(path) from None


def newest(pattern: str) -> str:
    """The last file that matches the glob pattern, in name order; ``MissingInput`` when none does."""
    found = sorted(glob.glob(pattern))
    if not found:
        raise MissingInput(pattern)
    return found[-1]


def agg(report: dict) -> dict:
    return {(r["cell"], r["rung"]): r for r in report["tables"]["aggregate"]}


def skill(r: dict) -> float:
    return 1.0 - r["brier"] / r["brier_base"]       # re-derived, not read from brier_skill


def tri(tok: str) -> list[str]:
    """'-0.0078 (-0.0120 to -0.0032)' -> three tokens."""
    return NUM.findall(tok)


def check_triple(sec, label, tok, point, lo, hi):
    t = tri(tok)
    if len(t) != 3:
        return check(sec, label, "n/a", point) if tok.startswith("n/a") else RESULTS.append((sec, label, tok, "unparsed", False))
    check(sec, label + " point", t[0], point)
    check(sec, label + " lo", t[1], lo)
    check(sec, label + " hi", t[2], hi)


# ------------------------------------------------------------------ backtest sections
def pair_tokens(tok: str) -> list[str]:
    """'-0.0048 to 0.0077' -> two tokens."""
    return NUM.findall(tok)


def verify_backtest(sec: str, lines: list[str], reports: Path, source: str):
    text = "\n".join(lines)
    snap = re.search(r"Snapshot (\S+?),", text).group(1)
    path = reports / f"backtest-{source}-{snap}.json"
    rep = jload(str(path))
    a = agg(rep)
    hdr = rep["header"]
    m = re.search(r"(\d+) rows scored over (\d+) quarterly origins out of (\d+) admitted", text)
    check(sec, "header", m.group(1), hdr["scored_rows"])
    check(sec, "header", m.group(2), hdr["origins_scored"])
    check(sec, "header", m.group(3), hdr["admitted_rows"])
    m = re.search(r"Tests: (\d+) in the ledger, (\d+) admitted, (\d+) scored", text)
    check(sec, "tests in the ledger", m.group(1), hdr["tests_in_ledger"])
    check(sec, "tests admitted", m.group(2), hdr["tests_admitted"])
    check(sec, "tests scored", m.group(3), hdr["tests_scored"])
    m = re.search(r"P2 admission guard: ([\d.]+) standard errors", text)
    check(sec, "p2 guard", m.group(1), hdr["p2_guard"])
    scores_path = glob.glob(str(reports / f"scores-{source}-{snap}.parquet"))
    sc = pd.read_parquet(scores_path[0]) if scores_path else None
    for head, rows in parse_tables(lines):
        if head[:3] == ["cell", "rung", "n"]:
            label = "main table"
            col = {h: k for k, h in enumerate(head)}

            def find(prefix, col=col):
                return next((k for h, k in col.items() if h.startswith(prefix)), None)

            c_cov, c_abs, c_gbr = col["coverage 80% / 90%"], col["abstention rate"], col["gate base rate"]
            c_near = find("decidable by tests (0.90 gate, at the cell")
            c_03, c_rows = find("decidable by tests (0.90 gate, base rate 0.3)"), find("decidable by rows")
            c_res = next(k for h, k in col.items() if h.startswith("decidable by tests (") and h.endswith("screen)"))
            short = {"decidable at skill 0.20 and 0.10": "yes, both skills", "decidable at skill 0.20 only": "skill 0.20 only",
                     "decidable at skill 0.10 only": "skill 0.10 only", "undecidable at this n": "undecidable"}
            for r in rows:
                cell, rung = r[0], r[1]
                j = a[(cell, rung)]
                check(sec, f"{label} {cell}/{rung} n", r[2], j["n"])
                if r[3] != "n/a":
                    check(sec, f"{label} {cell}/{rung} logscore", r[3], j["logscore"])
                    check_triple(sec, f"{label} {cell}/{rung} brier skill", r[4], skill(j),
                                 j["brier_skill_lo"], j["brier_skill_hi"])
                    c = tri(r[c_cov])
                    check(sec, f"{label} {cell}/{rung} cov80", c[0], j["coverage_80"])
                    check(sec, f"{label} {cell}/{rung} cov90", c[1], j["coverage_90"])
                check(sec, f"{label} {cell}/{rung} gate base rate", r[c_gbr], j["gate_base_rate"])
                for col_i, key in ((c_near, "decidable_by_tests"), (c_03, "decidable_by_tests_base_0.3"), (c_rows, "decidable"),
                                   (c_res, "decidable_research_by_tests")):
                    if col_i is not None:
                        want = short.get(j[key], j[key])
                        RESULTS.append((sec, f"{label} {cell}/{rung} {key}", r[col_i], want, r[col_i] == want))
                if c_03 is None:          # a column that is left out must be redundant: the verdict at base rate 0.3 equals the nearest one
                    RESULTS.append((sec, f"{label} {cell}/{rung} base 0.3 column omitted", j["decidable_by_tests_base_0.3"], j["decidable_by_tests"],
                                    j["decidable_by_tests_base_0.3"] == j["decidable_by_tests"]))
                if c_rows is None:
                    RESULTS.append((sec, f"{label} {cell}/{rung} by-row column omitted", j["decidable"], "not computed",
                                    str(j["decidable"]).startswith("not computed")))
                check(sec, f"{label} {cell}/{rung} abstention", r[c_abs], j["abstention_rate"])
                if sc is not None and rung in ("P0", "P1", "P2"):
                    s = sc[sc["rung"] == rung] if cell == "ALL" else sc[(sc["rung"] == rung) & (sc["cell"] == cell)]
                    check(sec, f"scores parquet {cell}/{rung} n", r[2], len(s))
                    check(sec, f"scores parquet {cell}/{rung} logscore", r[3], s["logscore"].mean())
                    check(sec, f"scores parquet {cell}/{rung} abstention", r[c_abs], s["abstain"].mean())
                    inside90 = ((s["y"] >= s["lo90"]) & (s["y"] <= s["hi90"])).mean()
                    check(sec, f"scores parquet {cell}/{rung} cov90", c[1], inside90)
        elif head[:2] == ["rung", "tests"]:
            for r in rows:
                j = a[("ALL", r[0])]
                check(sec, f"adjusted {r[0]} tests", r[1], j["n_tests"])
                check_triple(sec, f"adjusted {r[0]} skill", r[2], skill(j), j["brier_skill_lo"], j["brier_skill_hi"])
                t = pair_tokens(r[3]) or ["n/a", "n/a"]               # a rung with no width (P0) has no adjusted bounds
                check(sec, f"adjusted {r[0]} skill adjusted lo", t[0], j["adjusted_lo"])
                check(sec, f"adjusted {r[0]} skill adjusted hi", t[1], j["adjusted_hi"])
                check_triple(sec, f"adjusted {r[0]} logscore", r[4], j["logscore"], j["logscore_lo"], j["logscore_hi"])
                t = pair_tokens(r[5]) or ["n/a", "n/a"]
                check(sec, f"adjusted {r[0]} logscore adjusted lo", t[0], j["logscore_adjusted_lo"])
                check(sec, f"adjusted {r[0]} logscore adjusted hi", t[1], j["logscore_adjusted_hi"])
                check(sec, f"adjusted {r[0]} family", r[6], j["family_size"])
        elif head[:2] == ["rung", "AUC of the event (90% interval)"]:
            for r in rows:
                j = a[("ALL", r[0])]
                check_triple(sec, f"auc {r[0]}", r[1], j["auc_event"], j["auc_event_lo"], j["auc_event_hi"])
                check(sec, f"resolution {r[0]}", r[2], j["resolution_event"])
                check(sec, f"mean p_sig {r[0]}", re.match(r"([-\d.]+)", r[3]).group(1), j["p_sig_mean"])
                check(sec, f"planned event rate {r[0]}", r[4], j["event_rate_planned"])
                check_triple(sec, f"planned skill {r[0]}", r[5], j["brier_skill_planned"], j["brier_skill_planned_lo"], j["brier_skill_planned_hi"])
        elif head[:2] == ["rung", "ECE"]:
            for r in rows:
                j = a[("ALL", r[0])]
                for col, key in ((1, "ece"), (2, "ece_percentile"), (3, "ece_percentile_independent"), (4, "ece_equal_mass"),
                                 (5, "ece_equal_mass_percentile"), (6, "design_effect"), (7, "icc")):
                    check(sec, f"calibration {r[0]} {key}", r[col], j[key])
        elif head[:2] == ["rung", "decile"] and head[2] == "planned exposures per arm":
            for r in rows:
                rung, dec = r[0], int(r[1])
                j = next(x for x in rep["tables"]["calibration_by_precision"] if x["rung"] == rung and x["decile"] == dec)
                check(sec, f"calibration {rung} d{dec} n", r[3], j["n"])
                check(sec, f"calibration {rung} d{dec} mean p_sig", r[5], j["mean_p_sig"])
                check(sec, f"calibration {rung} d{dec} event rate", r[6], j["event_rate"])
                check(sec, f"calibration {rung} d{dec} cov90", r[7], j["coverage_90"])
        elif head[:2] == ["rung", "decile"] and head[2].startswith("realized over planned"):
            for r in rows:
                rung, dec = r[0], int(r[1])
                j = next(x for x in rep["tables"]["coverage_by_se_ratio"] if x["rung"] == rung and x["decile"] == dec)
                lo, hi = pair_tokens(r[2])
                check(sec, f"ratio {rung} d{dec} lo", lo, j["ratio_lo"])
                check(sec, f"ratio {rung} d{dec} hi", hi, j["ratio_hi"])
                for col, key in ((3, "n"), (4, "mean_ratio"), (5, "mean_p_sig"), (6, "event_rate"), (7, "coverage_80"), (8, "coverage_90")):
                    check(sec, f"ratio {rung} d{dec} {key}", r[col], j[key])
        elif head[:2] == ["rung", "kind"] and "ceiling" in head:
            for r in rows:
                j = a[("ALL", r[0])]
                t = tri(r[2])
                if t:
                    check(sec, f"direction {r[0]}", t[0], j["direction_accuracy"])
                    check(sec, f"direction {r[0]} lo", t[1], j["direction_accuracy_lo"])
                else:
                    check(sec, f"direction {r[0]}", "n/a", j["direction_accuracy"])
                check(sec, f"direction {r[0]} ceiling", r[3], j["direction_ceiling"])
                check(sec, f"direction {r[0]} decisive rows", r[4], j.get("n_decisive") or 0)
                check(sec, f"direction {r[0]} decisive accuracy", r[5], j.get("direction_accuracy_decisive"))
        elif head[0] == "policy":
            dv = rep["tables"]["decision_value"]
            for r in rows:
                pol, rung = r[0], r[1]
                allrow = next(x for x in dv if x["origin"] == "ALL" and x["policy"] == pol and x["rung"] == rung and abs(x["budget"] - 0.25) < 1e-9)
                per = [x for x in dv if x["origin"] != "ALL" and x["policy"] == pol and x["rung"] == rung and abs(x["budget"] - 0.25) < 1e-9]
                t = tri(r[2])
                pooled_fraction = sum(x["captured"] for x in per) / sum(x["total"] for x in per)
                check(sec, f"decision {pol}/{rung} captured (pooled from the origins)", t[0], pooled_fraction)
                check(sec, f"decision {pol}/{rung} captured lo", t[1], allrow["captured_fraction_lo"])
                check(sec, f"decision {pol}/{rung} captured hi", t[2], allrow["captured_fraction_hi"])
                t = tri(r[3])
                check(sec, f"decision {pol}/{rung} difference", t[0], allrow["diff_random"])
                check(sec, f"decision {pol}/{rung} difference lo", t[1], allrow["diff_random_lo"])
                check(sec, f"decision {pol}/{rung} difference hi", t[2], allrow["diff_random_hi"])
        elif head[:2] == ["cell", "rows"]:
            tab = {x["cell"]: x for x in rep["tables"]["abstention"]}
            for r in rows:
                j = tab[r[0]]
                check(sec, f"trigger {r[0]} rows", r[1], j["n"])
                check(sec, f"trigger {r[0]} rate", r[2], j["rate"])
                for k, name in enumerate(["support", "novelty", "reliability", "instability"]):
                    check(sec, f"trigger {r[0]} {name}", r[3 + k], j[name])
    # sentences
    dv = rep["tables"]["decision_value"]
    m = re.search(r"random order captures ([\d.]+) of the total .* P2 p_win captures ([\d.]+) \(a difference from random order of ([-+\d.]+), "
                  r"interval ([-+\d.]+) to ([-+\d.]+)\), and an oracle .* captures ([\d.]+)\.", text)
    if m:
        def pooled(policy, rung):
            sel = [x for x in dv if x["origin"] != "ALL" and x["policy"] == policy and abs(x["budget"] - 0.25) < 1e-9
                   and (rung is None or x["rung"] == rung)]
            return sum(x["captured"] for x in sel) / sum(x["total"] for x in sel)
        pw = next(x for x in dv if x["origin"] == "ALL" and x["policy"] == "p_win" and x["rung"] == "P2" and abs(x["budget"] - 0.25) < 1e-9)
        check(sec, "decision value random", m.group(1), pooled("random", None))
        check(sec, "decision value p_win", m.group(2), pooled("p_win", "P2"))
        check(sec, "decision value difference", m.group(3), pw["diff_random"])
        check(sec, "decision value difference lo", m.group(4), pw["diff_random_lo"])
        check(sec, "decision value difference hi", m.group(5), pw["diff_random_hi"])
        check(sec, "decision value oracle", m.group(6), pooled("oracle", None))
    m = re.search(r"Log score on all rows: P0 ([-\d.]+), P1 ([-\d.]+), P2 ([-\d.]+)\.", text)
    for k, rung in enumerate(["P0", "P1", "P2"]):
        check(sec, f"sentence logscore {rung}", m.group(1 + k), a[("ALL", rung)]["logscore"])
    m = re.search(r"P2 minus P1 is ([-+\d.]+),", text)
    check(sec, "sentence P2 minus P1", m.group(1), a[("ALL", "P2")]["logscore"] - a[("ALL", "P1")]["logscore"])


# ------------------------------------------------------------------ the other sections
def verify_gates(sec, lines, reports):
    g = jload(str(reports / "gates.json"))
    by_skill_n = {(r["skill"], r["n"]): r["power"] for r in g["table"]}
    for head, rows in parse_tables(lines):
        if head[0] == "base rate":
            for r in rows:
                key = "0.80" if r[1].startswith("0.80") else "0.90"
                sizes = g["by_base_rate"][r[0]]["by_target"][key]
                check(sec, f"tests for skill 0.20 at {key}, base rate {r[0]}", r[2], sizes["n_200"])
                check(sec, f"tests for skill 0.10 at {key}, base rate {r[0]}", r[3], sizes["n_400"])
        else:
            ns = [int(x) for x in head[1:]]
            for r in rows:
                sk = float(r[0])
                for n, tok in zip(ns, r[1:]):
                    check(sec, f"power skill {sk} n {n}", tok, by_skill_n[(sk, n)])
    text = "\n".join(lines)
    m = re.search(r"base rate ([\d.]+), (\d+) replicates, seed (\d+)", text)
    check(sec, "base rate", m.group(1), g["base_rate"])
    check(sec, "replicates", m.group(2), g["reps"])
    check(sec, "seed", m.group(3), g["seed"])
    m = re.search(r"whose (\d+) percent bootstrap interval .* tests of ([\d.]+) rows on average", text)
    check(sec, "interval level", m.group(1), g["interval"]["level"] * 100)
    check(sec, "rows per test", m.group(2), g["interval"]["rows_per_test"])


def verify_latency(sec, lines, reports):
    j = jload(str(reports / "card-latency.json"))
    keys = {"in process, bundle preloaded": "in_process_ms", "in process, weight on precedents forced to 0.5": "in_process_lambda_0.5_ms",
            "HTTP service on loopback, bundle preloaded": "service_ms", "command line, fresh process": "cli_fresh_process_ms"}
    for _head, rows in parse_tables(lines):
        for r in rows:
            for col, name in zip(r[1:], ("p50", "p95", "max")):
                check(sec, f"{r[0]} {name}", col, j[keys[r[0]]][name])
    text = "\n".join(lines)
    check(sec, "model id (as number of characters)", str(len(re.search(r"model (\w+)\.", text).group(1))), len(j["model_id"]))
    m = re.search(r"Of (\d+) made-up headlines, (\d+) abstained at the fitted weight on precedents and (\d+) with the weight forced to 0.5", text)
    check(sec, "headlines", m.group(1), sum(j["statuses"].values()))
    check(sec, "abstained at the fitted weight", m.group(2), j["statuses"].get("abstain", 0))
    check(sec, "abstained at 0.5", m.group(3), j["statuses_lambda_0.5"].get("abstain", 0))


def verify_runtime(sec, lines, reports):
    j = jload(str(reports / "run-log.json"))
    st = {s["stage"]: s["seconds"] for s in j["stages"]}
    for _head, rows in parse_tables(lines):
        for r in rows:
            check(sec, f"stage {r[0]}", r[1], st[r[0]])
    body = "\n".join(lines)
    m = re.search(r"download ([\d.]+) s \((\d+) files, (\d+) bytes.*compute ([\d.]+) s, total ([\d.]+) s", body)
    if m:                                                           # a run from a clean copy that downloaded the archives
        seconds, files, size, compute, total = m.groups()
    else:                                                           # a run that only verified the checksums of archives already in place
        m = re.search(r"Checksum verification ([\d.]+) s \(no download in this run\), compute ([\d.]+) s, total ([\d.]+) s", body)
        seconds, compute, total = m.groups()
        files, size = "0", "0"
        kind = j.get("data_stage_kind")
        RESULTS.append((sec, "data stage kind", "checksum verification", kind, kind == "checksum verification"))
    check(sec, "download seconds", seconds, j["download_seconds"])
    check(sec, "downloaded files", files, j["downloaded_files"])
    check(sec, "downloaded bytes", size, j["downloaded_bytes"])
    check(sec, "compute seconds", compute, j["compute_seconds"])
    check(sec, "total seconds", total, j["total_seconds"])
    check(sec, "stage seconds minus download equals compute", compute, sum(st.values()) - j["download_seconds"])


def latest_snapshot(reports: Path, source: str) -> str:
    name = Path(newest(str(reports / f"backtest-{source}-*.json"))).name
    return name[len(f"backtest-{source}-"):-len(".json")]


def verify_challengers(sec, lines, reports, source):
    rep = jload(str(reports / f"backtest-{source}-{latest_snapshot(reports, source)}.json"))
    a = agg(rep)
    for _head, rows in parse_tables(lines):
        for r in rows:
            j = a[("ALL", r[0])]
            check(sec, f"{r[0]} n", r[2], j["n"])
            check(sec, f"{r[0]} logscore", r[3], j["logscore"] if r[3] != "n/a" else None)
            if r[4] != "n/a (n/a to n/a)":
                check_triple(sec, f"{r[0]} skill", r[4], skill(j), j["brier_skill_lo"], j["brier_skill_hi"])
            check(sec, f"{r[0]} direction", r[5], j["direction_accuracy"])
            check(sec, f"{r[0]} decisive direction", r[6], j.get("direction_accuracy_decisive"))
            check(sec, f"{r[0]} abstention", r[7], j["abstention_rate"])
    text = "\n".join(lines)
    for name in ("GBM", "local_eb"):
        m = re.search(rf"{name} minus P2 log score is ([-+\d.]+)", text)
        if m:
            check(sec, f"{name} minus P2", m.group(1), a[("ALL", name)]["logscore"] - a[("ALL", "P2")]["logscore"])
    named = re.search(r"Challenger rows whose Brier skill interval excludes zero: ([^.]*)\.", text)
    want = sorted(n for n in rep["header"]["challengers"] if a[("ALL", n)]["brier_skill_lo"] is not None and skill(a[("ALL", n)]) is not None
                  and a[("ALL", n)]["brier_skill_lo"] > 0)
    got = sorted(x.strip() for x in named.group(1).split(",")) if named else []
    RESULTS.append((sec, "challenger rows whose interval excludes zero", ",".join(got), ",".join(want), got == want))


def ablation_file(reports: Path, source: str, setting: str) -> str:
    snap = latest_snapshot(reports, source)
    if setting.startswith("main run"):
        return str(reports / f"backtest-{source}-{snap}.json")
    return str(reports / "ablations" / f"backtest-{source}-{snap}--{setting}.json")


def verify_ablations(sec, lines, reports, source):
    for head, rows in parse_tables(lines):
        if head[0] == "setting" and "P1 log score" in head:
            for r in rows:
                doc = jload(ablation_file(reports, source, r[0]))
                a = agg(doc)
                p1, p2 = a[("ALL", "P1")], a[("ALL", "P2")]
                want = doc["header"].get("p2_guard")
                check(sec, f"{r[0]} guard", r[1], want) if want != "off" else RESULTS.append((sec, f"{r[0]} guard", r[1], want, r[1] == "off"))
                check(sec, f"{r[0]} n", r[2], p2["n"])
                check(sec, f"{r[0]} P1 logscore", r[3], p1["logscore"])
                check(sec, f"{r[0]} P2 logscore", r[4], p2["logscore"])
                check(sec, f"{r[0]} P2 minus P1", r[5], p2["logscore"] - p1["logscore"])
                check_triple(sec, f"{r[0]} P2 skill", r[6], skill(p2), p2["brier_skill_lo"], p2["brier_skill_hi"])
                check(sec, f"{r[0]} P2 direction", r[7], p2["direction_accuracy"])
                check(sec, f"{r[0]} P2 coverage90", r[8], p2["coverage_90"])
        elif head[0] == "setting" and "mean lambda" in head:
            for r in rows:
                doc = jload(ablation_file(reports, source, r[0]))
                j = next(x for x in doc["tables"]["p2_selection_by_cell"] if x["cell"] == r[1])
                check(sec, f"{r[0]} {r[1]} origins", r[3], j["origins"])
                check(sec, f"{r[0]} {r[1]} mean lambda", r[4], j["lambda_mean"])
                check(sec, f"{r[0]} {r[1]} lambda zero", r[5], j["share_lambda_zero"])
                check(sec, f"{r[0]} {r[1]} bandwidth", r[6], j["bandwidth_mult_mean"])


def verify_guard(sec, lines, reports, source):
    main = agg(jload(ablation_file(reports, source, "main run")))[("ALL", "P2")]
    off = agg(jload(ablation_file(reports, source, "p2-guard-off")))[("ALL", "P2")]
    for head, rows in parse_tables(lines):
        if head[0] == "selection":
            for r in rows:
                j = main if r[0] == "guarded" else off
                t = tri(r[1])
                check(sec, f"{r[0]} logscore", t[0], j["logscore"])
                check(sec, f"{r[0]} logscore lo", t[1], j["logscore_lo"])
                check(sec, f"{r[0]} crps", tri(r[2])[0], j["crps"])
                check(sec, f"{r[0]} skill", tri(r[3])[0], skill(j))
        elif head[0] == "log score":
            t = tri(" ".join(rows[0][:1]))
            check(sec, "paired log score difference", t[0], main["logscore"] - off["logscore"])
            check(sec, "paired crps difference", tri(rows[0][1])[0], main["crps"] - off["crps"])
            check(sec, "paired skill difference", tri(rows[0][2])[0], skill(main) - skill(off))


def verify_cautionary(sec, lines, reports):
    snap = latest_snapshot(reports, "upworthy")
    rel_report = jload(str(reports / "ablations" / f"backtest-upworthy-{snap}--effect-scale-relative+s-star-realized.json"))
    a = agg(rel_report)
    for head, rows in parse_tables(lines):
        if head[0] == "rung" and "n" in head and "coverage 80% / 90%" in head:
            for r in rows:
                j = a[("ALL", r[0])]
                check(sec, f"{r[0]} n", r[1], j["n"])
                check(sec, f"{r[0]} logscore", r[2], j["logscore"])
                check_triple(sec, f"{r[0]} skill", r[3], skill(j), j["brier_skill_lo"], j["brier_skill_hi"])
                c = tri(r[4])
                check(sec, f"{r[0]} cov80", c[0], j["coverage_80"])
                check(sec, f"{r[0]} cov90", c[1], j["coverage_90"])
        elif head[:2] == ["rung", "decile"]:
            cal = rel_report["tables"]["calibration_by_precision"]
            for r in rows:
                j = next(x for x in cal if x["rung"] == r[0] and x["decile"] == int(r[1]))
                check(sec, f"cautionary {r[0]} d{r[1]} n", r[3], j["n"])
                check(sec, f"cautionary {r[0]} d{r[1]} mean s_star", r[4], j["mean_s_star"])
                check(sec, f"cautionary {r[0]} d{r[1]} event rate", r[6], j["event_rate"])


def verify_learning(sec, lines, reports, source):
    f = newest(str(reports / f"learning-curve-{source}-*.json"))
    j = jload(f)
    text = "\n".join(lines)
    m = re.search(r"Final origin ([\d-]+), (\d+) held-out rows in (\d+) tests", text)
    check(sec, "heldout rows", m.group(2), j["heldout_rows"])
    check(sec, "heldout tests", m.group(3), j["heldout_tests"])
    check(sec, "final origin year", m.group(1)[:4], int(j["final_origin"][:4]))
    g = j["gates"]["by_target"]
    for tgt, n200, n400 in re.findall(r"power (0\.\d+): n_200 = (\d+), n_400 = (\d+)", text):
        check(sec, f"gate n_200 at {tgt}", n200, g[f"{float(tgt):.2f}"]["n_200"])
        check(sec, f"gate n_400 at {tgt}", n400, g[f"{float(tgt):.2f}"]["n_400"])
    for head, rows in parse_tables(lines):
        if head[0] == "fraction":
            for r in rows:
                x = next(z for z in j["rows"] if abs(z["fraction"] - float(r[0])) < 1e-9 and z["rung"] == r[2])
                tag = f"fraction {r[0]} {r[2]}"
                check(sec, tag + " history rows", r[1], round(x["n_fit_rows"]))
                check_triple(sec, tag + " skill", r[3], x["skill"], x["skill_lo"], x["skill_hi"])
                check(sec, tag + " seed sd", r[4], x["skill_seed_sd"])
                check(sec, tag + " logscore", r[5], x["logscore"] if x.get("logscore") is not None else None)
                check(sec, tag + " direction", r[6], x["direction_accuracy"])


def verify_positive_control(sec, lines, reports):
    rep = jload(newest(str(reports / "positive-control" / "backtest-synthetic-*.json")))
    a = agg(rep)
    sens = jload(newest(str(reports / "paper-extras-synthetic-*.json")))["positive_control_sensitivity"]
    text = "\n".join(lines)
    m = re.search(r"(\d+) rows scored over (\d+) origins", text)
    check(sec, "header", m.group(1), rep["header"]["scored_rows"])
    check(sec, "header", m.group(2), rep["header"]["origins_scored"])
    for head, rows in parse_tables(lines):
        if head[:2] == ["cell", "rung"]:
            for r in rows:
                j = a[(r[0], r[1])]
                check(sec, f"{r[0]}/{r[1]} n", r[2], j["n"])
                check(sec, f"{r[0]}/{r[1]} logscore", r[3], j["logscore"])
                check_triple(sec, f"{r[0]}/{r[1]} skill", r[4], skill(j), j["brier_skill_lo"], j["brier_skill_hi"])
        elif head[:2] == ["cell", "origins"]:
            for r in rows:
                j = next(x for x in rep["tables"]["p2_selection_by_cell"] if x["cell"] == r[0])
                check(sec, f"selection {r[0]} origins", r[1], j["origins"])
                check(sec, f"selection {r[0]} mean lambda", r[2], j["lambda_mean"])
                check(sec, f"selection {r[0]} lambda zero", r[3], j["share_lambda_zero"])
                check(sec, f"selection {r[0]} held by the guard", r[4], j["share_guard_held"])
        elif head[0] == "tests in the ledger":
            for r in rows:
                j = next(x for x in sens["rows"] if x["n_tests"] == int(r[0]) and abs(x["text_effect_strength"] - float(r[1])) < 1e-9)
                check(sec, f"sensitivity {r[0]} {r[1]} strength over prior sd", r[2], j["strength_over_prior_sd"]["headline_only"])
                check(sec, f"sensitivity {r[0]} {r[1]} cell fits", r[3], j["cells"])
                check(sec, f"sensitivity {r[0]} {r[1]} admitted", r[4], j["admitted"])
                check(sec, f"sensitivity {r[0]} {r[1]} share", r[5], j["admitted"] / j["cells"])
    check(sec, "multiplier", re.search(r"multiplier ([\d.]+)", text).group(1), sens["multiplier"])


def verify_proxy(sec, lines, reports):
    for _head, rows in parse_tables(lines):
        for r in rows:
            src = {"Upworthy": "upworthy", "ASOS": "asos"}[r[0]]
            c = jload(newest(str(reports / f"paper-extras-{src}-*.json")))["impressions_effect_correlation"]
            check(sec, f"{r[0]} rows", r[1], c["n_rows"])
            check(sec, f"{r[0]} corr abs z", r[2], c["corr_log_impressions_abs_z"])
            check(sec, f"{r[0]} corr event", r[3], c["corr_log_impressions_event"])
            check(sec, f"{r[0]} corr run length", r[4], c.get("corr_log_run_length_abs_z"))


def verify_replay(sec, lines, reports):
    for _head, rows in parse_tables(lines):
        for r in rows:
            src = {"Upworthy": "upworthy", "ASOS": "asos"}[r[0]]
            d = jload(newest(str(reports / f"replay-{src}-*.json")))
            t, m = d["totals"], d["totals"]["miss_counts"]
            cov, n = re.match(r"([\d.]+) \((\d+)\)", r[6]).groups()
            check(sec, f"{r[0]} weeks", r[1], d["header"]["n_weeks"])
            check(sec, f"{r[0]} cards", r[2], t["cards_issued"])
            check(sec, f"{r[0]} outcomes", r[3], t["outcomes_joined"])
            check(sec, f"{r[0]} abstained", r[4], t["abstained"])
            check(sec, f"{r[0]} flagged weeks", r[5], t["n_flagged_weeks"])
            check(sec, f"{r[0]} coverage", cov, t["coverage_90_all"])
            check(sec, f"{r[0]} coverage n", n, t["coverage_90_all_n"])
            for col, key in ((7, "hit"), (8, "magnitude_miss"), (9, "direction_miss"), (10, "confident_but_wrong"), (11, "abstained_but_clear")):
                check(sec, f"{r[0]} {key}", r[col], m[key])


def verify_guard_pairs(sec, lines, reports, source):
    g = jload(newest(str(reports / f"paper-extras-{source}-*.json")))["guard_pairs"]
    for head, rows in parse_tables(lines):
        if head[0] == "cell":
            for r in rows:
                j = next(x for x in g["rows"] if x["cell"] == r[0] and x["origin"][:10] == r[1])
                for col, key in ((2, "lambda"), (3, "in_selection_gain"), (4, "in_selection_gain_se"), (5, "n_scored_rows"), (6, "n_scored_tests"),
                                 (7, "realized_p2_minus_p1")):
                    check(sec, f"pair {r[0]} {r[1]} {key}", r[col], j[key])
    sm = g["summary"]
    text = "\n".join(lines)
    m = re.search(r"Pairs admitted: (\d+) of (\d+); mean in-selection gain ([-\d.]+); pairs with a negative realized difference: (\d+)\. "
                  r"Pooled over the scored rows \((\d+) rows, (\d+) tests\) the realized difference is ([-+\d.]+) \(([-+\d.]+) to ([-+\d.]+),", text)
    keys = ("pairs_admitted", "pairs_in_selection", "mean_in_selection_gain", "pairs_with_negative_realized", "pooled_rows", "pooled_tests",
            "pooled_realized_p2_minus_p1", "pooled_lo", "pooled_hi")
    for k, key in enumerate(keys):
        check(sec, f"guard pairs {key}", m.group(1 + k), sm[key])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    here = Path(__file__).resolve().parents[1]
    ap.add_argument("--page", "--readme", dest="readme", default=str(here / "docs" / "results.md"), help="the page that holds the results block")
    ap.add_argument("--reports", default=None)
    ap.add_argument("--min-per-table", type=int, default=3)
    args = ap.parse_args()
    root = os.environ.get("MOOTCOURT_DATA_ROOT")
    reports = Path(args.reports) if args.reports else (Path(root) / "reports" if root else here / "reports")
    if not reports.is_dir() or not list(reports.glob("backtest-*.json")):
        sys.exit(f"no backtest reports in {reports}: set MOOTCOURT_DATA_ROOT to a data root that holds them, or pass --reports DIR "
                 "(for the published reports of the paper, --reports paper/data/run7-tie-rank)")
    try:
        page_text = Path(args.readme).read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit(f"cannot read the page {args.readme}: {exc.strerror or exc}; pass --page FILE")
    sections = split_sections(page_text)
    handlers = {
        "Upworthy backtest": lambda s, ln: verify_backtest(s, ln, reports, "upworthy"),
        "ASOS backtest": lambda s, ln: verify_backtest(s, ln, reports, "asos"),
        "Synthetic backtest (synthetic data, known truth)": lambda s, ln: verify_backtest(s, ln, reports, "synthetic"),
        "Synthetic gate power (synthetic data only)": lambda s, ln: verify_gates(s, ln, reports),
        "Challengers, Upworthy": lambda s, ln: verify_challengers(s, ln, reports, "upworthy"),
        "Ablations, Upworthy": lambda s, ln: verify_ablations(s, ln, reports, "upworthy"),
        "P2 admission guard, Upworthy": lambda s, ln: verify_guard(s, ln, reports, "upworthy"),
        "Ablations, Asos": lambda s, ln: verify_ablations(s, ln, reports, "asos"),
        "P2 admission guard, Asos": lambda s, ln: verify_guard(s, ln, reports, "asos"),
        "Guard pairs, Upworthy": lambda s, ln: verify_guard_pairs(s, ln, reports, "upworthy"),
        "Positive control, synthetic": lambda s, ln: verify_positive_control(s, ln, reports),
        "Admission and the exposure proxy": lambda s, ln: verify_proxy(s, ln, reports),
        "The cautionary run": lambda s, ln: verify_cautionary(s, ln, reports),
        "Weekly replay": lambda s, ln: verify_replay(s, ln, reports),
        "Learning curve, Asos": lambda s, ln: verify_learning(s, ln, reports, "asos"),
        "Learning curve, Upworthy": lambda s, ln: verify_learning(s, ln, reports, "upworthy"),
        "Card latency": lambda s, ln: verify_latency(s, ln, reports),
        "Run time": lambda s, ln: verify_runtime(s, ln, reports),
    }
    skipped = [k for k in sections if k not in handlers and parse_tables(sections[k])]
    for name, fn in handlers.items():
        if name not in sections:
            RESULTS.append((name, "section missing in the page", "", "", False))
            continue
        try:
            fn(name, sections[name])
        except MissingInput as exc:
            sys.exit(f"missing under {reports}: {Path(str(exc)).name} (needed by the section {name!r}); pass --reports DIR with the reports the page "
                     "was written from (for the published reports of the paper, --reports paper/data/run7-tie-rank)")
    bad = [r for r in RESULTS if not r[4]]
    print(f"page: {args.readme}\nreports: {reports}\n")
    print(f"{'section':<52}{'checked':>9}{'mismatch':>10}")
    fail = False
    for name in handlers:
        rs = [r for r in RESULTS if r[0] == name]
        nb = sum(1 for r in rs if not r[4])
        low = len([r for r in rs if r[4]]) < args.min_per_table
        fail |= low
        print(f"{name:<52}{len(rs):>9}{nb:>10}{'   TOO FEW' if low else ''}")
    for k in skipped:
        print(f"{k:<52}{'not checked (no table handler)':>30}")
    print(f"\ntotal checked {len(RESULTS)}, mismatches {len(bad)}")
    for r in bad[:40]:
        print(f"MISMATCH [{r[0]}] {r[1]}: printed {r[2]!r}, derived {r[3]!r}")
    return 1 if bad or fail else 0


if __name__ == "__main__":
    sys.exit(main())
