#!/usr/bin/env python3
"""The claims audit: every claim of the register resolves to a value in a report, and the printed value is that value.

The register (paper/reviews/claims.md) holds a Markdown table with the columns
``id | section | sentence | report path | key path | printed value | interval kind | status``. The report path is relative to the run folder.
The key path is ``tables.<name>[<col>=<value>[,<col>=<value>]].<field>`` for a row of a report table (a table is the report's
``tables[<name>]``, a list of dicts or a dict with ``rows``), or a plain dotted path for a scalar such as ``header.scored_rows``.
The printed value is compared at its own precision (the decimals of the printed string): ``minus 0.857`` and ``-0.857`` both mean negative,
a trailing percent sign compares against the value times 100, and thousands commas are dropped; text after the first number (an interval)
is not compared; a unit word (nats, points, s, tests, rows) is ignored. When the report holds text or a boolean the printed value is compared
as words, case and spacing ignored. A key may start with ``neg:`` (negate the found value) and ``pct:`` (times 100), in either order. A number
passes when it differs from the found value by at most half a unit of the last printed decimal. A quoted segment such as
``by_base_rate["0.09"]`` indexes a dict. A row whose report path is ``none`` skips the lookup and passes, and so does a row whose
status is ``removed``.

    python scripts/claims_audit.py [REGISTER] [RUN_DIR]    # exit 1 when any row fails; one line per failing row
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

NUMBER = re.compile(r"(minus\s+|-\s*)?(\d[\d,]*\.?\d*)\s*(%|percent)?", re.I)
STEP = re.compile(r"^(\w+)((?:\[[^\]]*\])*)$")
BRACKET = re.compile(r"\[([^\]]*)\]")
PREFIXES = ("neg:", "pct:")


@dataclass
class ClaimResult:
    id: str
    ok: bool
    reason: str


def _cells(line: str) -> list[str]:
    return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]


def parse_register(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) >= 8 and re.fullmatch(r"C\d+", cells[0]):
            rows.append(cells[:8])
    return rows


def _split_path(key: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in key:
        if ch == "." and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        depth += (ch == "[") - (ch == "]")
        cur += ch
    return parts + [cur]


def _equal(cell, want: str) -> bool:
    return str(cell) == want or (isinstance(cell, (int, float)) and not isinstance(cell, bool) and _as_float(want) == float(cell))


def _as_float(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def resolve(doc, key: str):
    """The value at a key path; raises KeyError with what is missing.

    A segment is ``name`` or ``name`` followed by brackets: ``["k"]`` indexes a dict by the quoted key, ``[col=value,...]`` picks the first row
    of a table (a list of dicts, or a dict with ``rows``) whose columns equal the values.
    """
    node = doc
    for part in _split_path(key):
        m = STEP.match(part)
        if not m:
            raise KeyError(f"bad key step {part!r}")
        name, brackets = m.groups()
        if not isinstance(node, dict) or name not in node:
            raise KeyError(f"no {name!r} at {part!r}")
        node = node[name]
        for sel in BRACKET.findall(brackets):
            if len(sel) >= 2 and sel[0] == sel[-1] and sel[0] in "\"'":
                if not isinstance(node, dict) or sel[1:-1] not in node:
                    raise KeyError(f"no key {sel} in {name!r}")
                node = node[sel[1:-1]]
                continue
            if isinstance(node, dict) and "rows" in node:
                node = node["rows"]
            if not isinstance(node, list):
                raise KeyError(f"{name!r} is not a table")
            conds = [c.split("=", 1) for c in sel.split(",") if "=" in c]
            hits = [r for r in node if isinstance(r, dict) and all(k in r and _equal(r[k], v) for k, v in conds)]
            if not hits:
                raise KeyError(f"no row with {sel} in {name!r}")
            node = hits[0]
    return node


def _words(text: str) -> str:
    return " ".join(str(text).lower().split())


def _compare(printed: str, found, scaled: bool = False) -> tuple[bool, str]:
    """Printed value against the found one. Text or a boolean is compared as words; a number to half a unit of the last printed decimal.

    ``scaled`` is true when the key carried ``pct:``, so a printed percent word is not scaled a second time."""
    if isinstance(found, (bool, str)):
        want = _words(found if isinstance(found, str) else str(found).lower())
        return (_words(printed) == want, "" if _words(printed) == want else f"printed {printed!r} but the report holds {found!r}")
    m = NUMBER.search(printed)
    if not m:
        return False, f"printed value {printed!r} holds no number but the report holds {found!r}"
    if not isinstance(found, (int, float)):
        return False, f"report holds {found!r}, not a number, for printed {printed}"
    token = m.group(2).replace(",", "")
    decimals = len(token.split(".")[1]) if "." in token else 0
    want = float(token) * (-1 if m.group(1) else 1)
    got = float(found) * 100 if m.group(3) and not scaled else float(found)
    if abs(got - want) <= 0.5 * 10 ** (-decimals) * (1 + 1e-9):
        return True, ""
    return False, f"printed {printed} but the report holds {format(got, '.10g')}"


def claims_audit(register_path: Path, run_dir: Path) -> list[ClaimResult]:
    results: list[ClaimResult] = []
    for cid, _section, _sentence, report, key, printed, _kind, status in parse_register(Path(register_path).read_text(encoding="utf-8")):
        if status.lower() == "removed":
            results.append(ClaimResult(cid, True, "removed"))
            continue
        if report.lower() == "none" or key.lower() == "none":
            results.append(ClaimResult(cid, True, "no report value to compare"))
            continue
        path = Path(report)
        if not path.is_file():
            path = Path(run_dir) / report
        if not path.is_file():
            path = Path(run_dir) / Path(report).name
        if not path.is_file():
            results.append(ClaimResult(cid, False, f"report {report} not found in {run_dir}"))
            continue
        steps = []
        while key.startswith(PREFIXES):
            steps.append(key[:4])
            key = key[4:]
        try:
            found = resolve(json.loads(path.read_text(encoding="utf-8")), key)
        except (KeyError, ValueError) as exc:
            results.append(ClaimResult(cid, False, f"{key} does not resolve in {report}: {exc}"))
            continue
        if steps and (isinstance(found, bool) or not isinstance(found, (int, float))):
            results.append(ClaimResult(cid, False, f"{key} holds {found!r}, which neg: and pct: cannot transform"))
            continue
        for step in reversed(steps):
            found = -found if step == "neg:" else found * 100
        ok, reason = _compare(printed, found, "pct:" in steps)
        results.append(ClaimResult(cid, ok, reason or "matches"))
    return results


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(__file__).resolve().parents[1]
    register = Path(args[0]) if args else root / "paper" / "reviews" / "claims.md"
    data = root / "paper" / "data"
    run = Path(args[1]) if len(args) > 1 else sorted(p for p in data.iterdir() if p.is_dir())[-1]
    bad = [r for r in claims_audit(register, run) if not r.ok]
    for r in bad:
        print(f"{r.id}: {r.reason}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
