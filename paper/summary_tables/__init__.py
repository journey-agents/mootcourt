"""The paper's summary tables, generated from the report files of the run folder.

Each group module (``paper/summary_tables/<group>.py``) lists functions in ``TABLES``; a function takes the ``Reports`` of the run folder and
returns a ``Table``. A number never appears as a literal: a cell is built with ``v``, ``n``, ``ci``, ``lohi`` or ``pct`` from a report and a
key path (the key syntax of ``scripts/claims_audit.py``), and the file written carries a ``% src:`` comment above each row naming its keys, so
each number traces to one report leaf. ``build_all`` runs from ``paper/build_tables.py``, so ``make tables`` regenerates these with the rest.
"""
from __future__ import annotations

import glob
import importlib
import json
import os
import pkgutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from claims_audit import resolve  # noqa: E402

MINUS_ZERO = "-"

# Tables in the LaTeX sources that hold no measured result, with why they are typed by hand. tests/test_summary_tables.py fails on any other.
HAND_TYPED = {
    "tab:fmt-archives": "the source archives' own counts, from DATA.md",
    "tab:fmt-protocol": "configuration constants",
    "tab:fmt-prior-work": "figures quoted from cited papers",
    "tab:landscape": "a survey of tools",
    "tab:schema": "field names of the exchange format",
    "tab:commands": "command lines",
    "tab:checksums": "file sizes and digests from data/CHECKSUMS.json",
}


def fmt(x, nd=3, comma=False, plus=False):
    """``x`` to ``nd`` places; a value that rounds to zero prints unsigned, as ``build_tables.f3`` does."""
    if x is None:
        raise ValueError("a generated cell has no value")
    text = f"{x:,.{nd}f}" if comma else f"{x:.{nd}f}"
    if text.startswith(MINUS_ZERO) and float(text.replace(",", "")) == 0.0:
        text = text[1:]
    if plus and not text.startswith(MINUS_ZERO) and float(text.replace(",", "")) != 0.0:
        text = "+" + text
    return text


class Cell(str):
    """A cell's text with the report keys it came from."""

    keys: tuple[str, ...] = ()


def _cell(text, *keys):
    c = Cell(text)
    c.keys = tuple(keys)
    return c


@dataclass
class Report:
    name: str
    doc: dict

    def get(self, key):
        return resolve(self.doc, key)

    def ref(self, key):
        return f"$RUN6/{self.name} {key}"


class Reports:
    """The JSON reports of a run folder, by glob pattern relative to it; a pattern must match exactly one file."""

    def __init__(self, root):
        self.root = str(root)
        self._cache: dict[str, Report] = {}

    def __call__(self, pattern) -> Report:
        if pattern not in self._cache:
            hits = sorted(glob.glob(os.path.join(self.root, pattern)))
            if len(hits) != 1:
                raise FileNotFoundError(f"{pattern}: {len(hits)} files under {self.root}")
            with open(hits[0]) as fh:
                self._cache[pattern] = Report(os.path.relpath(hits[0], self.root), json.load(fh))
        return self._cache[pattern]


def v(rep, key, nd=3, plus=False, scale=1.0, neg=False):
    """A number at ``nd`` places. ``scale`` multiplies (100 for a percent), ``neg`` negates."""
    x = rep.get(key) * scale * (-1 if neg else 1)
    return _cell(fmt(x, nd, plus=plus), rep.ref(key))


def n(rep, key, nd=0):
    """A count with thousands commas."""
    return _cell(fmt(rep.get(key), nd, comma=True), rep.ref(key))


def pct(rep, key, nd=0):
    """A share printed as a percent number, for a column whose header says percent, or with ``word=True`` by ``pctw``."""
    return _cell(fmt(rep.get(key) * 100, nd), rep.ref(key))


def pctw(rep, key, nd=0):
    return _cell(fmt(rep.get(key) * 100, nd) + " percent", rep.ref(key))


def lohi(rep, lo_key, hi_key, nd=3, scale=1.0):
    return _cell(f"({fmt(rep.get(lo_key) * scale, nd)}, {fmt(rep.get(hi_key) * scale, nd)})", rep.ref(lo_key), rep.ref(hi_key))


def ci(rep, row, field_name, nd=3, plus=False, scale=1.0, lo=None, hi=None):
    """``value (lo, hi)`` from a row path and a field, with the bounds at ``<field>_lo`` and ``<field>_hi`` unless named."""
    lo, hi = lo or f"{field_name}_lo", hi or f"{field_name}_hi"
    prefix = f"{row}." if row else ""
    a = v(rep, f"{prefix}{field_name}", nd, plus=plus, scale=scale)
    b = lohi(rep, f"{prefix}{lo}", f"{prefix}{hi}", nd, scale=scale)
    return _cell(f"{a} {b}", *a.keys, *b.keys)


def join(template, *cells):
    """A cell combining text and generated numbers, for example ``join("{} / {}", a, b)``."""
    return _cell(template.format(*cells), *[k for c in cells for k in getattr(c, "keys", ())])


@dataclass
class Raw:
    """A line written as it is: ``\\midrule``, a ``\\multicolumn`` group heading. It must hold no measured number."""

    text: str


@dataclass
class Table:
    name: str                       # the file is tables/<name>.tex; use the label without its tab: prefix
    spec: str                       # the tabular column spec, without braces
    header: list[str]               # header lines, each without the trailing \\
    rows: list = field(default_factory=list)   # each a list of cells, or a Raw
    end: str = r" \\"               # the row ending; tab:verdicts uses \tabularnewline
    source: str = ""                # what the file header names

    def render(self) -> str:
        out = [rf"\begin{{tabular}}{{{self.spec}}}", r"\toprule"]
        out += [h + self.end for h in self.header]
        out.append(r"\midrule")
        for row in self.rows:
            if isinstance(row, Raw):
                out.append(row.text)
                continue
            keys = [k for c in row for k in getattr(c, "keys", ())]
            if keys:
                out.append("% src: " + "; ".join(keys))
            out.append(" & ".join(str(c) for c in row) + self.end)
        out += [r"\bottomrule", r"\end{tabular}"]
        return "\n".join(out) + "\n"


def group_modules():
    pkg = Path(__file__).parent
    return [importlib.import_module(f"summary_tables.{m.name}") for m in pkgutil.iter_modules([str(pkg)])]


def build_all(root, out, write):
    reports = Reports(root)
    built = []
    for mod in group_modules():
        for fn in mod.TABLES:
            t = fn(reports)
            write(out, f"{t.name}.tex", t.source or f"the report keys named above each row ({mod.__name__.split('.')[-1]})", t.render())
            built.append(t.name)
    return built


def month_year(origin):
    """An origin's date as running text, for a label chosen by code: ``2015-01-01...`` is January 2015."""
    return datetime.fromisoformat(origin).strftime("%B %Y")


def narrowest_origin(rep):
    """The origin after burn-in where P1 leads P0 by least on log score; an origin where P1 does not lead fails the build, since the tables say above at every one."""
    def score(origin, rung):
        return rep.get(f"tables.score_by_origin[origin={origin},rung={rung}].logscore")

    origins = [o["origin"] for o in rep.get("tables.origins") if not o["burn_in"]]
    margins = {o: score(o, "P1") - score(o, "P0") for o in origins}
    if min(margins.values()) <= 0:
        raise ValueError("P1 is not above P0 at every origin after burn-in")
    return min(margins, key=margins.get)


derived = _cell   # a cell computed in Python from report leaves: ``derived(fmt(a + b), rep.ref(key_a), rep.ref(key_b))``
