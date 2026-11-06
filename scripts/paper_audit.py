#!/usr/bin/env python3
"""The paper's mechanical audits: every number matches its ``% src:`` line, and every path a ``% src:`` line names exists.

Convention: a comment line that starts with ``% src:`` (with continuation comment lines under it) sits above the sentence it documents and names
where that sentence's numbers come from; ``$RUN6/`` in it stands for the current run folder.

``number_audit(paper_dir, run_dir)``: for every sentence below a ``% src:`` comment, each number in the sentence is matched, at the sentence's
precision (or times 100 for a percent), against, in order, the numeric leaves of every ``$RUN6/<file>.json`` the comment names, the numbers of
every ``tables/<name>.tex`` the comment names, and the numbers quoted in the comment. A number that matches none is listed as unmatched. A
number that matches only a number quoted in the comment is also unmatched when that quoted number is itself a rounding of a leaf of the named
reports: a rounded comment cannot vouch for a double-rounded number (round 03). A derived number that no leaf carries passes on its comment.

``source_resolution(paper_dir, run_dir)``: every path in a ``% src`` line (a run-folder path, ``paper/data/``, ``tables/``, ``src/mootcourt/``,
``DATA.md``, ``data/CHECKSUMS`` or an absolute path) must exist. A line that names no JSON report is counted apart (``nojson``) and is not a failure.

    python scripts/paper_audit.py [--paper paper] [--run paper/data/run8-randomization-window]    # exit 1 on any unmatched number or missing path
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

NUM = re.compile(r"(?<![\w.])-?\d[\d,]*\.?\d*(?![\w])")
# Numbers that carry no claim: the 1.96 multiplier, the common levels and fractions, small counts and years.
IGNORE = {1.96, 0.9, 0.8, 0.05, 0.1, 0.25, 0.5, 2013, 2014, 2015, 2019, 2020, 30, 14, 10, 100, 1000, 1, 2, 3, 4, 5, 6, 7, 8, 9, 20, 32, 80, 90, 95}
MACROS = r"\\(?:ref|cite|label|input|put|multiput|line|rule|makebox|circle\*?|resizebox|begin|end|setlength|unitlength|texttt)\{[^}]*\}"
SOURCE_TOKEN = re.compile(r"(?:\$RUN6/|paper/data/|/Volumes/[^\s,;)]+|tables/|data/CHECKSUMS|src/mootcourt/|DATA\.md)[\w\-./+*]*")


@dataclass
class NumberAudit:
    checked: int = 0
    tiers: dict[str, int] = field(default_factory=lambda: {"src": 0, "table": 0, "json": 0})
    unmatched: list[tuple[str, int, str, str, str]] = field(default_factory=list)     # file, line, token, src line, sentence

    @property
    def ok(self) -> bool:
        return not self.unmatched


@dataclass
class SourceResolution:
    counts: dict[str, int] = field(default_factory=lambda: {"resolved": 0, "unresolved": 0, "nojson": 0})
    bad: list[tuple[str, str, int, list[str], str]] = field(default_factory=list)       # class, file, line, missing paths, the line

    @property
    def unresolved(self) -> list[tuple[str, str, int, list[str], str]]:
        return [b for b in self.bad if b[0] == "unresolved"]

    @property
    def ok(self) -> bool:
        return not self.unresolved


def _files(paper: Path) -> list[Path]:
    return [paper / "main.tex"] + [Path(p) for p in sorted(glob.glob(str(paper / "sections" / "*.tex")))]


def _nums(s: str) -> list[tuple[str, float]]:
    out = []
    for m in NUM.finditer(s):
        try:
            out.append((m.group(0), float(m.group(0).replace(",", ""))))
        except ValueError:
            pass
    return out


def _decimals(tok: str) -> int:
    return len(tok.split(".")[1]) if "." in tok else 0


def _leaves(o, acc: list[float]) -> None:
    if isinstance(o, dict):
        for v in o.values():
            _leaves(v, acc)
    elif isinstance(o, list):
        for v in o:
            _leaves(v, acc)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        acc.append(float(o))
    elif isinstance(o, str):
        acc.extend(v for _, v in _nums(o))


def _close(cand: float, v: float, d: int) -> bool:
    return abs(round(cand, d) - v) < 1e-9 or abs(cand - v) < 0.5 * 10 ** (-d) + 1e-12


def _traces_to_leaf(value: float, decimals: int, leaves: set[float]) -> bool:
    """True when ``value``, a number quoted in a comment at ``decimals`` places, is a rounding of some numeric leaf of the named reports."""
    return any(_close(c, value, decimals) for w in leaves for c in (w, w * 100, w / 100, abs(w)))


def _src_block(lines: list[str], i: int) -> tuple[str, int]:
    """The ``% src:`` comment starting at line ``i`` with its continuation comment lines, and the index of the first line after it."""
    src, j = lines[i], i + 1
    while j < len(lines) and lines[j].startswith("%"):
        src += " " + lines[j]
        j += 1
    return src, j


def number_audit(paper_dir: Path, run_dir: Path) -> NumberAudit:
    paper_dir, run_dir = Path(paper_dir), Path(run_dir)
    res = NumberAudit()
    json_cache: dict[Path, set[float]] = {}
    table_cache: dict[str, list[float]] = {}

    def json_numbers(path: Path) -> set[float]:
        if path not in json_cache:
            acc: list[float] = []
            if path.exists():
                try:
                    _leaves(json.loads(path.read_text(encoding="utf-8")), acc)
                except (OSError, ValueError):
                    pass
            json_cache[path] = set(acc)
        return json_cache[path]

    def table_numbers(name: str) -> list[float]:
        if name not in table_cache:
            p = paper_dir / "tables" / f"{name}.tex"
            table_cache[name] = [v for _, v in _nums(p.read_text(encoding="utf-8"))] if p.exists() else []
        return table_cache[name]

    for f in _files(paper_dir):
        if not f.exists():
            continue
        lines = f.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(lines):
            if lines[i].startswith("% src:"):
                src, j = _src_block(lines, i)
                if j >= len(lines):
                    break
                sent = lines[j]
                sc = re.sub(MACROS, " ", sent)
                sc = re.sub(r"\\put\([^)]*\)", " ", sc)
                sc = re.sub(r"\$[^$]*\$", " ", sc)
                srcn = [v for _, v in _nums(src)]
                srcdec = [(v, _decimals(t)) for t, v in _nums(src) if _decimals(t) >= 1]
                tabn: list[float] = []
                for name in re.findall(r"tables/([\w\-]+)\.tex", src):
                    tabn += table_numbers(name)
                jsn: set[float] = set()
                for jp in re.findall(r"\$RUN6/([\w\-./+]+\.json)", src):
                    jsn |= json_numbers(run_dir / jp)
                for tok, v in _nums(sc):
                    if abs(v) in IGNORE:
                        continue
                    res.checked += 1
                    d, tier = _decimals(tok), None
                    # the report leaf first, then the tables, then the comment: a comment that carries rounded digits cannot vouch for a number
                    # that its own leaf does not round to (round 03, decision 30)
                    for cands, name in ((jsn, "json"), (tabn, "table"), (srcn, "src")):
                        if any(_close(c, v, d) for w in cands for c in (w, w * 100, w / 100, abs(w))):
                            tier = name
                            break
                    if tier == "src" and any(_traces_to_leaf(ct, cd, jsn) for ct, cd in srcdec if _close(ct, v, d)):
                        tier = None      # the comment's digits are a rounding of a leaf, and the printed number is not a rounding of that leaf
                    if tier:
                        res.tiers[tier] += 1
                    else:
                        res.unmatched.append((str(f.relative_to(paper_dir)), j + 1, tok, src[:110], sc.strip()[:70]))
                i = j
            i += 1
    return res


def source_resolution(paper_dir: Path, run_dir: Path) -> SourceResolution:
    paper_dir, run_dir = Path(paper_dir).resolve(), Path(run_dir).resolve()
    repo = paper_dir.parent
    res = SourceResolution()

    def exists(p: str) -> bool:
        return any(Path(c).exists() for c in (p, repo / p, paper_dir / p))

    for f in _files(paper_dir):
        if not f.exists():
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
            if not line.startswith("% src"):
                continue
            paths = []
            for t in SOURCE_TOKEN.findall(line):
                e = t.rstrip(".,;)")
                paths.append(str(run_dir / e[len("$RUN6/"):]) if e.startswith("$RUN6/") else e)
            missing = [p for p in paths if not exists(p)]
            if missing:
                cls = "unresolved"
            elif not any(p.endswith(".json") for p in paths):
                cls = "nojson"
            else:
                cls = "resolved"
            res.counts[cls] += 1
            if cls != "resolved":
                res.bad.append((cls, str(f.relative_to(paper_dir)), n, missing[:2], line[:110]))
    return res


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--paper", default=str(root / "paper"))
    ap.add_argument("--run", default=None, help="run folder; default the newest folder under <paper>/data by name")
    a = ap.parse_args(argv)
    paper = Path(a.paper)
    run = Path(a.run) if a.run else sorted(p for p in (paper / "data").iterdir() if p.is_dir())[-1]
    na = number_audit(paper, run)
    print(f"numbers checked {na.checked} {na.tiers} unmatched {len(na.unmatched)}")
    for f, line, tok, src, sent in na.unmatched:
        print(f"  {f}:{line} {tok} | {sent}\n      src: {src}")
    sr = source_resolution(paper, run)
    print(f"sources {sr.counts}")
    for cls, f, line, missing, text in sr.bad:
        if cls == "unresolved":
            print(f"  {f}:{line} missing {missing} | {text}")
    return 0 if na.ok and sr.ok else 1


if __name__ == "__main__":
    sys.exit(main())
