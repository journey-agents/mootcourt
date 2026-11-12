#!/usr/bin/env python3
"""Assemble the anonymized, single-column submission source from the paper's one set of sources (``make tmlr``).

The paper has one source: ``paper/main.tex`` and ``paper/sections/*.tex``, which build the named preprint. This script writes a second
main file, ``paper/tmlr-submission.tex``, from the same text, so the two versions cannot drift apart. It does four things and nothing else:

1. Preamble. The lines between ``%% tmlr:preamble-begin`` and ``%% tmlr:preamble-end`` of ``main.tex`` (the class, the title block, the
   author) are replaced by ``paper/tmlr/preamble.tex``, which sets ``\\tmlrtrue``, takes the title from ``main.tex`` and names no author.
2. Abstract. The lines between ``%% tmlr:abstract-begin`` and ``%% tmlr:abstract-end`` are replaced by one paragraph, the text of
   ``paper/sections/abstract-tmlr.tex`` (kept with the sections so that the number audit reads it).
3. Order. Every ``\\input{sections/NAME}`` is expanded in place. A block between ``%% tmlr:move-begin ID`` and ``%% tmlr:move-end ID`` is
   cut from the body and placed at the start of the appendix, in the order of the blocks; a first ``\\subsection`` heading of a moved
   block becomes a ``\\section`` (inside it ``\\paragraph`` stays). A line ``%% tmlr:stub ID TEXT`` right after the begin marker gives the
   sentence left in the body where the block was; with a line ``%% tmlr:stubs-here`` in the sources the stub sentences are gathered
   there as one paragraph, in the order of the blocks.
4. Bibliography style. ``ACM-Reference-Format`` becomes ``tmlr`` when ``paper/tmlr/tmlr.bst`` exists and ``plainnat`` otherwise.
5. Layout and name. Floats are placed where they are cited and tables keep their natural size up to the text width
   (``single_column_layout``). The package's name is replaced by a neutral one (``withhold_name``), since the name leads to the repository.

Identity is handled in the sources, not here: text that would name the author, the repository, a release or a commit is written as
``\\iftmlr ANONYMOUS\\else NAMED\\fi``. This script then refuses to write a file in which a named branch could still be typeset or a
forbidden string appears outside a comment (``check_anonymous``). Comment lines are dropped from the output, since ``% src:`` lines name
paths of the repository.

Use: ``python scripts/tmlr_build.py --paper paper [--compile]``. With ``--compile`` it runs tectonic on the result and reports the page
count and any undefined reference.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

OUT_NAME = "tmlr-submission.tex"
FORBIDDEN = ("yingjie", "journey", "github.com", "zenodo", "5e4fedf", "a7e9f44", "5a68256", "145eaf7", "liyingjie", "moot court", "mootcourt",
             "independent researcher", "seattle")
_INPUT = re.compile(r"^\\input\{sections/([A-Za-z0-9_-]+)\}\s*$")
_BEGIN = re.compile(r"^%% tmlr:move-begin (\S+)\s*$")
_END = re.compile(r"^%% tmlr:move-end (\S+)\s*$")
_STUB = re.compile(r"^%% tmlr:stub (\S+) (.+)$")
STUBS_HERE = "%% tmlr:stubs-here"
# tables too wide to read at the text width of one column; they are set on a turned page
SIDEWAYS = ("tab:glance", "tab:main-upworthy")


def expand_inputs(paper: Path) -> list[str]:
    """``main.tex`` as lines, with every ``\\input{sections/NAME}`` replaced by that file's lines."""
    out: list[str] = []
    for line in (paper / "main.tex").read_text().split("\n"):
        m = _INPUT.match(line)
        if m:
            out += (paper / "sections" / f"{m.group(1)}.tex").read_text().rstrip("\n").split("\n")
        else:
            out.append(line)
    return out


def replace_region(lines: list[str], name: str, new: list[str]) -> list[str]:
    """The lines with the region between ``%% tmlr:NAME-begin`` and ``%% tmlr:NAME-end`` (markers included) replaced by ``new``."""
    begin, end = f"%% tmlr:{name}-begin", f"%% tmlr:{name}-end"
    try:
        i, j = lines.index(begin), lines.index(end)
    except ValueError:
        raise ValueError(f"main.tex has no {begin} and {end} pair") from None
    if j < i:
        raise ValueError(f"{end} comes before {begin}")
    return lines[:i] + new + lines[j + 1:]


def move_blocks(lines: list[str]) -> list[str]:
    """Cut each marked block, leave its stub sentence, and place the blocks right after ``\\appendix`` in their order."""
    body: list[str] = []
    moved: list[list[str]] = []
    stubs: list[str] = []
    gather = STUBS_HERE in lines          # with this marker the stub sentences form one paragraph there, not one line per block
    current: str | None = None
    block: list[str] = []
    for line in lines:
        b, e, s = _BEGIN.match(line), _END.match(line), _STUB.match(line)
        if b:
            if current is not None:
                raise ValueError(f"move block {b.group(1)} opens inside {current}")
            current, block = b.group(1), []
        elif e:
            if e.group(1) != current:
                raise ValueError(f"move-end {e.group(1)} does not close {current}")
            moved.append(_promote(block))
            current = None
        elif s and current == s.group(1) and not block:
            stubs.append(s.group(2))
            if not gather:
                body += ["", s.group(2), ""]
        elif current is not None:
            block.append(line)
        else:
            body.append(line)
    if current is not None:
        raise ValueError(f"move block {current} is not closed")
    if gather:
        at_stub = body.index(STUBS_HERE)
        body[at_stub:at_stub + 1] = ["", "\\paragraph{Reported in the appendix.} " + " ".join(stubs), ""] if stubs else []
    if not moved:
        return body
    at = [i for i, line in enumerate(body) if line.strip() == "\\appendix"]
    if len(at) != 1:
        raise ValueError("the sources must hold exactly one \\appendix line")
    flat = [line for blk in moved for line in ["", *blk]]
    return body[: at[0] + 1] + flat + body[at[0] + 1:]


def _promote(block: list[str]) -> list[str]:
    """A moved block whose first heading is a ``\\subsection`` becomes a section of the appendix."""
    for i, line in enumerate(block):
        if line.startswith("\\section"):
            return block
        if line.startswith("\\subsection"):
            return block[:i] + ["\\section" + line[len("\\subsection"):]] + block[i + 1:]
    return block


def drop_comments(lines: list[str]) -> list[str]:
    """Whole-line comments removed (source lines name repository paths); ``%`` inside a line is left alone."""
    return [line for line in lines if not line.lstrip().startswith("%")]


def title_of(paper: Path) -> str:
    m = re.search(r"^\\title\{(.+)\}\s*$", (paper / "main.tex").read_text(), flags=re.M)
    if not m:
        raise ValueError("main.tex has no \\title{...} on one line")
    return m.group(1)


def strip_named_branches(text: str) -> str:
    """The text with each ``\\iftmlr A\\else B\\fi`` reduced to ``A`` (for the identity check only; LaTeX does this when it typesets).

    A conditional is on one line and is not nested; one that breaks either rule is an error, since the check could then miss a named branch.
    """
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        if line.count("\\iftmlr") != line.count("\\fi") and "\\iftmlr" in line and "\\newif" not in line:
            raise ValueError(f"line {n}: an \\iftmlr without its \\fi on the same line")
        out.append(re.sub(r"\\iftmlr\b(.*?)\\else\b.*?\\fi\b", r"\1", line))
    return "\n".join(out)


def check_anonymous(text: str) -> list[str]:
    """Forbidden strings that the anonymous version would typeset, each with its line number."""
    hits = []
    for n, line in enumerate(strip_named_branches(text).split("\n"), 1):
        low = line.lower()
        hits += [f"line {n}: {word!r} in {line.strip()[:90]!r}" for word in FORBIDDEN if word in low]
    return hits


def single_column_layout(text: str) -> str:
    """Floats placed where they are cited, and tables at their natural size up to the text width.

    The sources are written for two columns: floats ask for the top of a column and tables are stretched to the column width. In one
    column that sends most tables to the end of the document and enlarges narrow ones, so every float takes ``[!htbp]`` and every
    ``\\resizebox{WIDTH}{!}{`` becomes an ``adjustbox`` that only shrinks. A table input on a line of its own gets the same box.
    """
    text = re.sub(r"\\begin\{(table|figure)(\*?)\}\[[^\]]*\]", r"\\begin{\1\2}[!htbp]", text)
    text = re.sub(r"\\resizebox\{[^{}]*\}\{!\}\{", lambda m: "\\adjustbox{max width=\\textwidth}{", text)
    text = re.sub(r"(?m)^\\input\{(tables/[A-Za-z0-9_-]+)\}$", lambda m: "\\adjustbox{max width=\\textwidth}{\\input{" + m.group(1) + "}}", text)
    # a tabular typed in the sources (not input from a generated file) starts and ends on lines of its own
    text = re.sub(r"(?m)^(\\begin\{tabular\})", lambda m: "\\adjustbox{max width=\\textwidth}{" + m.group(1), text)
    return re.sub(r"(?m)^(\\end\{tabular\})$", lambda m: m.group(1) + "}", text)


def turn_wide_tables(text: str) -> str:
    """The tables named in ``SIDEWAYS`` set on a turned page, where they keep a readable size; a missing label is an error."""
    for label in SIDEWAYS:
        at = text.find(f"\\label{{{label}}}")
        if at < 0:
            raise ValueError(f"no table carries the label {label}")
        begin = max(text.rfind("\\begin{table*}", 0, at), text.rfind("\\begin{table}", 0, at))
        star = "*" if text.startswith("\\begin{table*}", begin) else ""
        end = text.index(f"\\end{{table{star}}}", at)
        block = text[begin:end]
        block = re.sub(r"^\\begin\{table\*?\}\[[^\]]*\]", lambda m: "\\begin{sidewaystable}", block)
        block = block.replace("max width=\\textwidth", "max width=\\textheight")
        text = text[:begin] + block + "\\end{sidewaystable}" + text[end + len(f"\\end{{table{star}}}"):]
    return text


def withhold_name(text: str) -> str:
    """The package's name, its import name and its command replaced by neutral ones, since the name leads to the repository."""
    text = text.replace("Moot Court", "AnonTool").replace("mootcourt", "anontool")
    text = text.replace("run8-randomization-window", "run-final")
    return re.sub(r"\\texttt\{moot ", lambda m: "\\texttt{anontool ", text)


def assemble(paper: Path) -> str:
    lines = expand_inputs(paper)
    preamble = (paper / "tmlr" / "preamble.tex").read_text().rstrip("\n").replace("@@TITLE@@", title_of(paper)).split("\n")
    abstract = drop_comments((paper / "sections" / "abstract-tmlr.tex").read_text().rstrip("\n").split("\n"))
    lines = replace_region(lines, "preamble", preamble)
    lines = replace_region(lines, "abstract", ["\\begin{abstract}", *abstract, "\\end{abstract}"])
    lines = drop_comments(move_blocks(lines))
    style = "tmlr/tmlr" if (paper / "tmlr" / "tmlr.bst").is_file() else "plainnat"
    text = "\n".join(lines).replace("\\bibliographystyle{ACM-Reference-Format}", f"\\bibliographystyle{{{style}}}")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = withhold_name(turn_wide_tables(single_column_layout(text)))
    hits = check_anonymous(text)
    if hits:
        raise ValueError("the anonymous version would show identity:\n  " + "\n  ".join(hits))
    return text if text.endswith("\n") else text + "\n"


def compile_pdf(paper: Path) -> tuple[int, list[str]]:
    """Run tectonic on the assembled file; return the page count and the undefined references or citations."""
    run = subprocess.run(["tectonic", "-X", "compile", "--keep-logs", OUT_NAME], cwd=paper, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(run.stdout[-3000:] + run.stderr[-3000:])
    log = (paper / OUT_NAME.replace(".tex", ".log")).read_text(errors="replace")
    pages = re.search(r"Output written on .*\((\d+) pages?", log)
    undefined = sorted(set(re.findall(r"(?:Reference|Citation) `([^']+)' on page", log)))
    return (int(pages.group(1)) if pages else -1), undefined


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--paper", type=Path, default=Path("paper"))
    ap.add_argument("--compile", action="store_true", help="also run tectonic on the result")
    a = ap.parse_args(argv)
    try:
        text = assemble(a.paper)
    except ValueError as e:
        print(f"tmlr_build: {e}", file=sys.stderr)
        return 1
    out = a.paper / OUT_NAME
    out.write_text(text)
    print(f"wrote {out} ({len(text.splitlines())} lines)")
    if a.compile:
        pages, undefined = compile_pdf(a.paper)
        print(f"pages {pages}; undefined references or citations {len(undefined)}")
        for u in undefined:
            print(f"  {u}")
        return 1 if undefined else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
