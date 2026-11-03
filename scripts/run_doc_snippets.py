#!/usr/bin/env python3
"""Run the commands shown in the documentation, so that a command in a page cannot drift from the CLI.

Usage::

    python scripts/run_doc_snippets.py README.md docs/tutorials/01-first-card.md [--keep] [--slow]

Which blocks run. A fenced block whose first line (the "info string") is ``bash run`` is executed. The words after ``run``
are options:

* ``exit=N``  the block must end with exit status N (default 0; ``moot doctor`` ends with 1 when it has warnings);
* ``needs=archives``  the block needs the two public archives; it is skipped when they are not on this machine
  (the raw files are copied from the data root named by ``MOOTCOURT_DATA_ROOT`` or from ``./data/raw`` into the temporary one,
  so nothing is downloaded and the real data root is never written);
* ``slow``  the block takes minutes; it runs only with ``--slow`` (or ``MOOT_DOCS_SLOW=1``);
* ``expect="text"``  (repeatable) the output must contain this text, after runs of blanks and box-drawing characters are collapsed;
  use it for an error whose rich panel wraps at a width that depends on the length of a path, instead of showing the panel;
* ``quiet``  the output of the block is not shown in the page (the renderer adds no output block);
* ``head=N``  only the first N lines of the output are shown in the page.

A block tagged ``bash`` alone, ``text`` or anything else is never run: use it for the install line, a download, a command
that edits a file in an editor, or a shell prompt transcript. A block tagged ``text output`` right after a run block holds the
output the page shows for it; ``scripts/render_tutorial_outputs.py`` writes and checks those.

How they run. Every block of one file runs, in order, in ONE bash session that starts in a fresh temporary home folder, the way
a reader's terminal keeps its folder and its ``export`` lines between commands. Standard input is empty, ``MOOTCOURT_DATA_ROOT``
is unset at the start, the environment of the process is otherwise kept, and the Python that runs this script comes first on
``PATH`` so that ``moot`` and ``python`` are the ones of this environment. The port 8731 that the serving tutorial uses is
replaced by a free port at run time and back in the output.

The functions at the end are what ``tests/test_docs_run.py`` and ``scripts/render_tutorial_outputs.py`` use.
"""
from __future__ import annotations

import argparse
import os
import queue
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_PORT = "8731"
BLOCK_TIMEOUT_S = 900
FENCE = re.compile(r"^```(.*)$")


@dataclass
class Block:
    """One fenced block: its info string, the line numbers of its fences (1-based) and its body."""

    info: str
    start: int
    end: int
    body: str

    @property
    def words(self) -> list[str]:
        try:
            return shlex.split(self.info)
        except ValueError:
            return self.info.split()

    @property
    def is_run(self) -> bool:
        return self.words[:2] == ["bash", "run"]

    @property
    def is_output(self) -> bool:
        return self.words[:2] == ["text", "output"]

    def options(self, name: str) -> list[str]:
        """Every value of a repeatable ``name=value`` option."""
        return [w.split("=", 1)[1] for w in self.words[2:] if w.startswith(name + "=")]

    def option(self, name: str, default=None):
        for w in self.words[2:]:
            if w == name:
                return True
            if w.startswith(name + "="):
                return w.split("=", 1)[1]
        return default


@dataclass
class Result:
    """What running one block gave. ``status`` is ``ok``, ``failed``, ``skipped`` or ``timeout``."""

    block: Block
    status: str
    exit_code: int | None = None
    output: str = ""
    seconds: float = 0.0
    note: str = ""


def parse_blocks(text: str) -> list[Block]:
    """Every fenced block of a Markdown text, in order. A fence is a line that starts with three backticks."""
    blocks: list[Block] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m or not lines[i].startswith("```"):
            i += 1
            continue
        info, start, body = m.group(1).strip(), i + 1, []
        i += 1
        while i < len(lines) and not lines[i].startswith("```"):
            body.append(lines[i])
            i += 1
        blocks.append(Block(info, start, i + 1, "\n".join(body)))
        i += 1
    return blocks


def output_block_of(blocks: list[Block], index: int, text: str) -> Block | None:
    """The ``text output`` block that directly follows run block ``index`` (only blank lines between), if any."""
    if index + 1 >= len(blocks) or not blocks[index + 1].is_output:
        return None
    lines = text.split("\n")
    between = lines[blocks[index].end: blocks[index + 1].start - 1]
    return blocks[index + 1] if all(not ln.strip() for ln in between) else None


def archives_present(root: Path | None = None) -> Path | None:
    """The raw-archive folder (it holds ``upworthy/`` and ``asos/``) of the data root in force, or None.

    The data root is ``root`` when given, else the environment variable ``MOOTCOURT_DATA_ROOT``, else the repository's own default.
    """
    from mootcourt.storage import storage_paths

    raw = storage_paths(root=root).raw if root else storage_paths().raw
    return raw if list((raw / "upworthy").glob("*.csv")) and list((raw / "asos").glob("*.parquet")) else None


def _free_port() -> str:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return str(s.getsockname()[1])


class _Shell:
    """One long-lived bash. Each block is sourced from a file with empty standard input, then a marker line carries its status."""

    def __init__(self, home: Path, env: dict[str, str]):
        self.home = home
        self.p = subprocess.Popen(["bash", "--noprofile", "--norc"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, bufsize=1, cwd=home, env=env)
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self.p.stdin.write("set -o pipefail\n")

    def _pump(self) -> None:
        for line in self.p.stdout:
            self.q.put(line)
        self.q.put(None)

    def run(self, script: str, timeout: float) -> tuple[int, str, bool]:
        mark = f"__MOOT_DOC_{uuid.uuid4().hex}__"
        f = self.home / f".block-{uuid.uuid4().hex}.sh"
        f.write_text(script + "\n", encoding="utf-8")
        self.p.stdin.write(f". '{f}' < /dev/null; __rc=$?; printf '%s%s\\n' '{mark}' \"$__rc\"\n")
        self.p.stdin.flush()
        out, deadline = [], time.monotonic() + timeout
        while True:
            try:
                line = self.q.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                if time.monotonic() >= deadline:
                    return 124, "".join(out), True
                continue
            if line is None:
                return 125, "".join(out), False
            if mark in line:
                before, _, rc = line.partition(mark)
                out.append(before)
                f.unlink(missing_ok=True)
                return int(rc.strip() or 0), "".join(out), False
            out.append(line)

    def close(self) -> None:
        try:
            self.p.stdin.write("kill $(jobs -p) 2>/dev/null; exit\n")
            self.p.stdin.flush()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def display_text(raw: str, home: Path, port: str | None = None) -> str:
    """Output as a page shows it: the temporary home becomes ``~``, the real port becomes the documented one, trailing blanks go."""
    text = raw
    for h in sorted({str(home), str(home.resolve())}, key=len, reverse=True):
        text = text.replace(h, "~")
    if port:
        text = text.replace(f"127.0.0.1:{port}", f"127.0.0.1:{DOC_PORT}").replace(f"localhost:{port}", f"localhost:{DOC_PORT}")
    return "\n".join(ln.rstrip() for ln in text.rstrip("\n").split("\n")) if text.strip() else ""


_MASKS = [
    (re.compile(r"\b\d{8}-[0-9a-f]{12}\b"), "<snapshot>"),
    (re.compile(r"\b[0-9a-f]{12,16}\b"), "<id>"),
    (re.compile(r"\b\d+\.\d+\.\d+\b"), "<version>"),
    (re.compile(r"\b\d+(\.\d+)? (s|seconds)\b"), "<time>"),
    (re.compile(r"\b\d+(\.\d+)? (KB|MB|GB|TB)\b"), "<size>"),
    (re.compile(r"\b\d+ days old\b"), "<n> days old"),
    (re.compile(r"\b\d+ days\b"), "<n> days"),
]


def mask(text: str) -> str:
    """Text with the values that change between machines and days replaced: ids (content hashes), timings, versions, sizes, ages."""
    for rx, rep in _MASKS:
        text = rx.sub(rep, text)
    return text


def shown_lines(result: Result, block: Block, home: Path, port: str | None) -> str:
    """The text a page should show for ``result``: the display text cut to the block's ``head=N`` lines."""
    text = display_text(result.output, home, port)
    head = block.option("head")
    if head:
        text = "\n".join(text.split("\n")[: int(head)])
    return text


@dataclass
class FileRun:
    """The outcome of running one Markdown file: a result per run block, the home used and the port substitution."""

    path: Path
    results: list[Result] = field(default_factory=list)
    home: Path | None = None
    port: str | None = None


def run_file(path: Path, *, slow: bool = False, keep: bool = False, workdir: Path | None = None) -> FileRun:
    """Run every ``bash run`` block of ``path`` in one session in a temporary home. Skips are recorded, not hidden."""
    text = Path(path).read_text(encoding="utf-8")
    blocks = parse_blocks(text)
    tmp = Path(tempfile.mkdtemp(prefix="moot-docs-", dir=workdir or "/tmp"))
    home = tmp / "home"
    home.mkdir()
    env = dict(os.environ)
    for k in ("MOOTCOURT_DATA_ROOT", "VIRTUAL_ENV", "GITHUB_ACTIONS"):
        env.pop(k, None)
    mpl = Path(tempfile.gettempdir()) / "moot-docs-mplconfig"              # shared, so the font cache is built once
    env.update({"HOME": str(home), "PATH": f"{Path(sys.executable).parent}{os.pathsep}{env.get('PATH', '')}", "MPLCONFIGDIR": str(mpl),
                "MPLBACKEND": "Agg", "NO_COLOR": "1", "COLUMNS": "100", "PYTHONDONTWRITEBYTECODE": "1", "XDG_CACHE_HOME": str(tmp / "cache"),
                "_TYPER_FORCE_DISABLE_TERMINAL": "1"})
    port = _free_port()
    fr = FileRun(Path(path), home=home, port=port)
    shell = _Shell(home, env)
    try:
        shell.run("python -c 'import matplotlib.pyplot' > /dev/null 2>&1", 120)       # the font cache is built once, out of sight of the pages
        for b in blocks:
            if not b.is_run:
                continue
            want = int(b.option("exit", 0))
            if b.option("needs") == "archives" and archives_present() is None:
                fr.results.append(Result(b, "skipped", note="the archives are not on this machine"))
                continue
            if b.option("slow") and not (slow or os.environ.get("MOOT_DOCS_SLOW") == "1"):
                fr.results.append(Result(b, "skipped", note="slow block; run with --slow"))
                continue
            if b.option("needs") == "archives":
                _stage_archives(shell, home)
            t0 = time.monotonic()
            rc, out, timed_out = shell.run(b.body.replace(DOC_PORT, port), BLOCK_TIMEOUT_S)
            status = "timeout" if timed_out else ("ok" if rc == want else "failed")
            note = "" if status == "ok" else f"exit {rc}, wanted {want}"
            flat = re.sub(r"[\s\u2500-\u257f]+", " ", display_text(out, home, port))
            for text in b.options("expect"):
                if text not in flat:
                    status, note = "failed", f"the output does not contain {text!r}"
            fr.results.append(Result(b, status, rc, out, time.monotonic() - t0, note))
    finally:
        shell.close()
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
    return fr


def _stage_archives(shell: _Shell, home: Path) -> None:
    """Copy the raw archives under the data root the page's shell has set (once); nothing is downloaded."""
    rc, out, _ = shell.run('printf "%s" "${MOOTCOURT_DATA_ROOT:-}"', 30)
    root = Path(out.strip()) if out.strip() else None
    if root is None or not str(root.resolve()).startswith(str(home.resolve())):
        raise RuntimeError("a needs=archives block runs before the page has exported MOOTCOURT_DATA_ROOT under the home folder")
    from mootcourt.storage import storage_paths

    src = archives_present()
    for sub in ("upworthy", "asos"):
        dst = storage_paths(root=root).raw / sub
        if not dst.exists():
            shutil.copytree(src / sub, dst)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--slow", action="store_true", help="also run the blocks tagged slow")
    ap.add_argument("--keep", action="store_true", help="keep the temporary home folder")
    args = ap.parse_args()
    bad = 0
    for f in args.files:
        fr = run_file(f, slow=args.slow, keep=args.keep)
        for r in fr.results:
            first = r.block.body.strip().split("\n")[0][:70]
            print(f"{f}:{r.block.start + 1}: {r.status.upper():8} {r.seconds:6.1f}s  {first}" + (f"   ({r.note})" if r.note else ""))
            if r.status in ("failed", "timeout"):
                bad += 1
                print(r.output[-1500:], file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
