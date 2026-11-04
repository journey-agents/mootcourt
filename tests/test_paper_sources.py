"""T-075 item 1 (round 01: R1 major 4, R3 major 6, R5 major 1): every number in a paper caption traces to a source.

A float (``table``, ``table*``, ``figure``, ``figure*``) of ``paper/sections/*.tex`` or ``paper/main.tex`` whose caption contains a digit must
carry a source: a ``% src:`` line (inside the float or in the comment block right before it), a ``% table:`` reference, a generated table
(``\\input{tables/...}``, whose first line names the report JSON it came from) or a generated figure (a comment naming ``figures.json``, the
index of every plotted value). The check is a regex pass over the files and runs in well under a second.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_FILES = sorted((ROOT / "paper" / "sections").glob("*.tex")) + [ROOT / "paper" / "main.tex"]
FLOAT = re.compile(r"\\begin\{(table\*?|figure\*?)\}(.*?)\\end\{\1\}", re.S)
SOURCE_MARKS = ("% src:", "% table:", "figures.json")


def _caption(body: str) -> str | None:
    """The text of the first ``\\caption{...}`` of a float body, braces matched; None when the float has no caption."""
    at = body.find("\\caption")
    if at < 0:
        return None
    i = body.find("{", at)
    depth = 0
    for j in range(i, len(body)):
        if body[j] == "{":
            depth += 1
        elif body[j] == "}":
            depth -= 1
            if depth == 0:
                return body[i + 1:j]
    return body[i + 1:]


def _preceding_comments(text: str, start: int) -> list[str]:
    """The contiguous comment lines right before position ``start`` (the convention: the source comment sits above the float)."""
    lines, pos = [], start
    while pos > 0:
        prev = text.rfind("\n", 0, pos - 1)
        line = text[prev + 1:pos].strip()
        if not line.startswith("%"):
            break
        lines.append(line)
        pos = prev + 1
    return lines


def has_source(text: str, match: re.Match) -> bool:
    body = match.group(2)
    block = body + "\n" + "\n".join(_preceding_comments(text, match.start()))
    return any(mark in block for mark in SOURCE_MARKS) or bool(re.search(r"\\input\{tables/", body))


def floats_without_source(text: str) -> list[str]:
    """The captions (first 80 characters) of the floats whose caption carries a digit and which carry no source."""
    out = []
    for m in FLOAT.finditer(text):
        cap = _caption(m.group(2))
        if cap is not None and re.search(r"\d", cap) and not has_source(text, m):
            out.append(cap[:80])
    return out


def test_a_caption_with_a_digit_and_no_source_is_reported_and_each_source_form_clears_it():
    bare = "\\begin{table}\n\\caption{Skill of 0.0015 on 3,797 tests.}\n\\begin{tabular}{l}x\\\\\\end{tabular}\n\\end{table}\n"
    assert floats_without_source(bare) == ["Skill of 0.0015 on 3,797 tests."]
    assert floats_without_source("% src: run5/backtest.json tables.aggregate\n" + bare) == []
    assert floats_without_source(bare.replace("\\begin{tabular}{l}x\\\\\\end{tabular}", "\\input{tables/main-upworthy}")) == []
    assert floats_without_source(bare.replace("\\caption{", "% table: tab:main\n\\caption{")) == []
    fig = "% Figure 3: drawn from run5; every plotted value is listed in paper/figures/figures.json.\n" + bare.replace("table", "figure")
    assert floats_without_source(fig) == []
    assert floats_without_source(bare.replace("0.0015 on 3,797", "the base rate").replace("Skill", "Skill")) == []  # no digit, no source needed
    assert floats_without_source("text % src: a\n\n" + bare) == ["Skill of 0.0015 on 3,797 tests."]  # a comment not adjacent to the float


def test_every_caption_with_a_digit_in_the_paper_has_a_source_and_the_check_is_fast():
    t0 = time.perf_counter()
    missing = {f.name: floats_without_source(f.read_text(encoding="utf-8")) for f in PAPER_FILES}
    missing = {k: v for k, v in missing.items() if v}
    assert not missing, missing
    assert sum(len(FLOAT.findall(f.read_text(encoding="utf-8"))) for f in PAPER_FILES) > 40  # the scan saw the floats
    assert time.perf_counter() - t0 < 2.0
