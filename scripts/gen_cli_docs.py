#!/usr/bin/env python3
"""Write docs/reference/cli.md from the command tree, or check that the committed file is current.

Usage: ``python scripts/gen_cli_docs.py --write`` or ``--check`` (exit code 1 when the file is stale).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import typer

OUT = Path(__file__).resolve().parents[1] / "docs" / "reference" / "cli.md"
HEADER = """# Command line

Every command is `moot <command>`. This page is generated from the command definitions by `scripts/gen_cli_docs.py`; run
`make docs` to refresh it. `moot <command> --help` prints the same text.

"""


def _default(p) -> str:
    d = p.default
    if d is None or d == () or (p.is_flag and d is False):
        return ""
    return f"`{d}`"


def _options_table(cmd) -> list[str]:
    rows = []
    for p in cmd.params:
        kind_of = getattr(p, "param_type_name", "")      # typer vendors its own click, so test by name
        if kind_of == "option":
            if p.name == "help":
                continue
            names = ", ".join(f"`{o}`" for o in p.opts + p.secondary_opts)
            kind = "flag" if p.is_flag else p.type.name
            rows.append(f"| {names} | {kind} | {_default(p)} | {(p.help or '').replace('|', '/')} |")
        elif kind_of == "argument":
            rows.append(f"| `{p.name.upper()}` | argument | {'required' if p.required else ''} | |")
    if not rows:
        return []
    return ["| Option | Type | Default | Meaning |", "|---|---|---|---|"] + rows + [""]


def _walk(cmd, path: list[str], depth: int, out: list[str]) -> None:
    out += [f"{'#' * depth} `{' '.join(path)}`", ""]
    doc = (cmd.help or "").strip()
    if doc:
        out += [doc, ""]
    out += _options_table(cmd)
    for name, sub in sorted(getattr(cmd, "commands", {}).items()):
        _walk(sub, path + [name], min(depth + 1, 4), out)


def render() -> str:
    from mootcourt.cli import app

    root = typer.main.get_command(app)
    out: list[str] = []
    for name, sub in sorted(root.commands.items()):
        _walk(sub, ["moot", name], 2, out)
    return HEADER + "\n".join(out).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = render()
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT}")
        return 0
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
        print(f"{OUT} is stale: run `python scripts/gen_cli_docs.py --write`", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
