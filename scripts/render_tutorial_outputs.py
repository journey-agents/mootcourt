#!/usr/bin/env python3
"""Write the command outputs shown in the documentation, or check that they are current.

Usage::

    python scripts/render_tutorial_outputs.py --write [FILE ...]
    python scripts/render_tutorial_outputs.py --check [FILE ...]     (exit code 1 when a page is stale)

With no FILE the pages are README.md, docs/commands.md, docs/troubleshooting.md and every docs/tutorials/*.md. The commands of
each page run as ``scripts/run_doc_snippets.py`` describes. The output of a ``bash run`` block is shown in the ``text output``
block that follows it; ``--write`` fills that block (and adds one after a run block that has none, unless the run block is tagged
``quiet``), ``--check`` compares the block with a fresh run. The comparison masks what changes between machines and days
(content hashes, snapshot ids, timings, versions, disk sizes, ages in days); every other character must match, so a number that
moves with the code is a failure that tells you to run ``--write``. Blocks that were skipped (``slow``, or ``needs=archives``
without the archives) keep the output they have.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("run_doc_snippets", ROOT / "scripts" / "run_doc_snippets.py")
rds = importlib.util.module_from_spec(_spec)
sys.modules["run_doc_snippets"] = rds
_spec.loader.exec_module(rds)


def default_pages() -> list[Path]:
    pages = [ROOT / "README.md", ROOT / "docs" / "commands.md", ROOT / "docs" / "troubleshooting.md"]
    pages += sorted((ROOT / "docs" / "tutorials").glob("[0-9]*.md"))
    return [p for p in pages if p.is_file()]


def compare(fr) -> list[str]:
    """Problems of one run: a block that failed, a shown output that differs, a run block with no shown output."""
    text = fr.path.read_text(encoding="utf-8")
    blocks = rds.parse_blocks(text)
    problems: list[str] = []
    for r in fr.results:
        where = f"{fr.path.name}:{r.block.start + 1}"
        if r.status in ("failed", "timeout"):
            problems.append(f"{where}: the block {r.status} ({r.note}); output tail:\n{r.output[-600:]}")
            continue
        if r.status == "skipped":
            continue
        idx = next(i for i, b in enumerate(blocks) if b.start == r.block.start)
        out = rds.output_block_of(blocks, idx, text)
        shown = rds.shown_lines(r, r.block, fr.home, fr.port)
        if r.block.option("quiet"):
            continue
        if not shown:
            if out is not None and out.body.strip():
                problems.append(f"{where}: the block prints nothing but the page shows output")
            continue
        if out is None:
            problems.append(f"{where}: the page shows no output for this block (run --write)")
        elif rds.mask(out.body.rstrip()) != rds.mask(shown):
            problems.append(f"{where}: the shown output is stale\n--- page\n{out.body}\n--- now\n{shown}")
    return problems


def render(fr) -> str:
    """The page text with every output block of an executed run block replaced (or added)."""
    text = fr.path.read_text(encoding="utf-8")
    blocks = rds.parse_blocks(text)
    lines = text.split("\n")
    edits = []                                   # (first line index, last line index exclusive, new lines), applied from the end
    for r in fr.results:
        if r.status != "ok" or r.block.option("quiet"):
            continue
        idx = next(i for i, b in enumerate(blocks) if b.start == r.block.start)
        out = rds.output_block_of(blocks, idx, text)
        shown = rds.shown_lines(r, r.block, fr.home, fr.port)
        new = ["```text output", *shown.split("\n"), "```"] if shown else []
        if out is not None:
            edits.append((out.start - 1, out.end, new))
        elif shown:
            edits.append((r.block.end, r.block.end, ["", *new]))
    for a, b, new in sorted(edits, key=lambda e: e[0], reverse=True):
        lines[a:b] = new
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    ap.add_argument("--slow", action="store_true", help="also run the blocks tagged slow")
    ap.add_argument("files", nargs="*", type=Path)
    args = ap.parse_args()
    bad = 0
    for page in args.files or default_pages():
        fr = rds.run_file(page, slow=args.slow)
        if args.check:
            problems = compare(fr)
        else:
            problems = [f"{page.name}:{r.block.start + 1}: the block {r.status} ({r.note}); output tail:\n{r.output[-600:]}"
                        for r in fr.results if r.status in ("failed", "timeout")]
        if args.write and not problems:
            new = render(fr)
            if new != page.read_text(encoding="utf-8"):
                page.write_text(new, encoding="utf-8")
                print(f"wrote {page}")
            else:
                print(f"{page} is current")
        for p in problems:
            print(p, file=sys.stderr)
        bad += len(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
