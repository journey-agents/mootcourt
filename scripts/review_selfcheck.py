#!/usr/bin/env python3
"""The self-check gate: every mechanical check a review round needs, run in order, none skipped when another fails.

    make selfcheck        # exit 1 when any item fails; writes .claude/fleet/selfcheck-<YYYY-MM-DD>.md

Items, each a function ``check_<name>(repo) -> (ok, detail)``:

  pending-markers        no ``% PENDING-`` comment in a .tex file of paper/
  number-audit           every number below a ``% src:`` line matches its source (scripts/paper_audit.py)
  source-resolution      every path a ``% src:`` line names exists
  writing-rules          no em or en dash and no role noun in any file git would commit (the scanner of tests/test_writing_rules.py)
  forbidden-terms        no digest of either tier in any file git would commit, names included (the same scanner)
  paper-builds           ``make paper`` exits 0; the page count is read with pypdf, or pdfinfo when pypdf is not installed
  tables-byte-identical  ``make tables`` leaves paper/tables exactly as it was before the self-check started
  docs-current           the three ``--check`` scripts of the documentation exit 0
  claims-audit           scripts/claims_audit.py against paper/reviews/claims.md, value by value
  release-check          scripts/release_check.py (lint, tests, wheel, docs); the slowest item, last

The run folder is the newest folder under paper/data by name.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING = re.compile(r"%\s*PENDING-")


@dataclass
class SelfCheckReport:
    items: list[tuple[str, bool, str]]
    ok: bool
    markdown: str


# ----------------------------------------------------------------------------------------------------------------------- helpers
def _run(cmd: list[str], repo: Path, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=timeout)


def _tail(done: subprocess.CompletedProcess, n: int = 3) -> str:
    lines = [ln for ln in (done.stdout + done.stderr).strip().splitlines() if ln.strip()]
    return " / ".join(lines[-n:])[:400]


def _load_module(path: Path, name: str):
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_dir_of(repo: Path) -> Path:
    """The newest run folder under paper/data, by name."""
    data = repo / "paper" / "data"
    runs = sorted(p for p in data.iterdir() if p.is_dir()) if data.is_dir() else []
    if not runs:
        raise FileNotFoundError(f"no run folder under {data}")
    return runs[-1]


def _paper_audit(repo: Path):
    return _load_module(Path(__file__).with_name("paper_audit.py"), "paper_audit")


def _scanner(repo: Path):
    return _load_module(repo / "tests" / "test_writing_rules.py", "selfcheck_writing_rules")


def _py(repo: Path) -> list[str]:
    return [sys.executable]


def _snapshot(folder: Path) -> dict[str, bytes]:
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()} if folder.is_dir() else {}


def _git_status(repo: Path, path: str) -> str:
    done = _run(["git", "status", "--porcelain", path], repo, 120)
    return done.stdout.strip()


# ----------------------------------------------------------------------------------------------------------------------- checks
def check_pending_markers(repo: Path) -> tuple[bool, str]:
    hits = []
    for f in sorted((repo / "paper").rglob("*.tex")):
        if "dist" in f.relative_to(repo / "paper").parts:
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if PENDING.search(line):
                hits.append(f"{f.relative_to(repo)}:{n}")
    return (not hits, "none" if not hits else f"{len(hits)} marker(s): " + ", ".join(hits[:8]))


def check_number_audit(repo: Path) -> tuple[bool, str]:
    res = _paper_audit(repo).number_audit(repo / "paper", run_dir_of(repo))
    detail = f"{res.checked} numbers checked, {len(res.unmatched)} unmatched"
    if res.unmatched:
        detail += ": " + "; ".join(f"{f}:{n} {tok}" for f, n, tok, _s, _t in res.unmatched[:8])
    return res.ok, detail


def check_source_resolution(repo: Path) -> tuple[bool, str]:
    res = _paper_audit(repo).source_resolution(repo / "paper", run_dir_of(repo))
    detail = f"{res.counts['resolved']} resolved, {res.counts['unresolved']} unresolved, {res.counts['nojson']} without a report"
    if res.unresolved:
        detail += ": " + "; ".join(f"{f}:{n} {m}" for _c, f, n, m, _l in res.unresolved[:6])
    return res.ok, detail


def _scan(repo: Path, tier: str) -> tuple[bool, str]:
    sc = _scanner(repo)
    files = sc.tracked_text_files(repo)
    hits: list[tuple[str, int, str]] = []
    if tier == "style":
        for path in files:
            hits += sc.scan_file(path, set(), repo, rules={"dash", "role"}, restricted=None) if sc.classify(path, repo) else []
    else:
        digests = sc.load_digests(repo / "tests" / "forbidden_terms.sha256")
        restricted = sc.load_restricted(repo / "tests" / "restricted_terms.sha256")
        if not digests:
            return False, "tests/forbidden_terms.sha256 holds no digest"
        hits = sc.scan_repo(repo, files, digests, restricted)
    detail = f"{len(files)} files scanned, {len(hits)} hit(s)"
    if hits:
        detail += ": " + "; ".join(f"{f}:{n} {what}" for f, n, what in hits[:6])
    return not hits, detail


def check_writing_rules(repo: Path) -> tuple[bool, str]:
    return _scan(repo, "style")


def check_forbidden_terms(repo: Path) -> tuple[bool, str]:
    return _scan(repo, "terms")


def _page_count(pdf: Path) -> int | None:
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(pdf)).pages)
    except ImportError:
        pass
    if shutil.which("pdfinfo"):
        m = re.search(r"^Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout, re.M)
        return int(m.group(1)) if m else None
    return None


def check_paper_builds(repo: Path) -> tuple[bool, str]:
    done = _run(["make", "paper"], repo)
    if done.returncode != 0:
        return False, f"make paper exited {done.returncode}: {_tail(done)}"
    pages = _page_count(repo / "paper" / "main.pdf")
    return pages is not None, f"make paper exit 0, {pages} pages" if pages is not None else "make paper exit 0, but no page count could be read"


def check_tables_identical(repo: Path, before: dict[str, bytes] | None = None) -> tuple[bool, str]:
    tables = repo / "paper" / "tables"
    before = _snapshot(tables) if before is None else before
    done = _run(["make", "tables"], repo)
    if done.returncode != 0:
        return False, f"make tables exited {done.returncode}: {_tail(done)}"
    after = _snapshot(tables)
    moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    uncommitted = _git_status(repo, "paper/tables")
    note = f"; uncommitted changes in paper/tables (git status): {len(uncommitted.splitlines())} file(s)" if uncommitted else ""
    if moved:
        return False, f"{len(moved)} table file(s) changed by make tables: " + ", ".join(moved[:6]) + note
    return True, f"{len(after)} files regenerated byte-identical{note}"


def check_docs_current(repo: Path) -> tuple[bool, str]:
    failed, ran = [], []
    for script in ("gen_cli_docs.py", "render_tutorial_outputs.py", "render_readme_results.py"):
        done = _run(_py(repo) + [f"scripts/{script}", "--check"], repo, 3600)
        ran.append(script)
        if done.returncode != 0:
            failed.append(f"{script}: {_tail(done, 2)}")
    return (not failed, "; ".join(failed) if failed else "; ".join(ran) + " --check exit 0")


def check_claims_audit(repo: Path) -> tuple[bool, str]:
    register = repo / "paper" / "reviews" / "claims.md"
    if not register.is_file():
        return False, "claims register missing"
    results = _load_module(Path(__file__).with_name("claims_audit.py"), "claims_audit").claims_audit(register, run_dir_of(repo))
    bad = [r for r in results if not r.ok]
    detail = f"{len(results)} claims, {len(bad)} failing"
    if bad:
        detail += ": " + "; ".join(f"{r.id} {r.reason}" for r in bad[:6])
    return not bad, detail


def check_release_check(repo: Path) -> tuple[bool, str]:
    script = repo / "scripts" / "release_check.py"
    if not script.is_file():
        return False, "scripts/release_check.py missing"
    done = _run(_py(repo) + [str(script)], repo, 7200)
    fails = [ln for ln in done.stdout.splitlines() if ln.startswith("FAIL")]
    return done.returncode == 0, "every release check passed" if done.returncode == 0 else "; ".join(fails[:4]) or _tail(done)


# ----------------------------------------------------------------------------------------------------------------------- the gate
def run_selfcheck(repo: Path) -> SelfCheckReport:
    repo = Path(repo)
    tables_before = _snapshot(repo / "paper" / "tables")      # taken first: `make paper` rebuilds the tables too
    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("pending-markers", lambda: check_pending_markers(repo)),
        ("number-audit", lambda: check_number_audit(repo)),
        ("source-resolution", lambda: check_source_resolution(repo)),
        ("writing-rules", lambda: check_writing_rules(repo)),
        ("forbidden-terms", lambda: check_forbidden_terms(repo)),
        ("paper-builds", lambda: check_paper_builds(repo)),
        ("tables-byte-identical", lambda: check_tables_identical(repo, tables_before)),
        ("docs-current", lambda: check_docs_current(repo)),
        ("claims-audit", lambda: check_claims_audit(repo)),
        ("release-check", lambda: check_release_check(repo)),
    ]
    items: list[tuple[str, bool, str]] = []
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as exc:       # a check that cannot run is a failed check, and the others still run
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        items.append((name, bool(ok), " ".join(str(detail).split())[:600]))
    ok_all = all(ok for _n, ok, _d in items)
    return SelfCheckReport(items, ok_all, render_markdown(items, ok_all))


def render_markdown(items: list[tuple[str, bool, str]], ok: bool, date: str | None = None) -> str:
    lines = [f"# Self-check {date or dt.date.today().isoformat()}: {'PASS' if ok else 'FAIL'}", "",
             "| item | status | detail |", "|---|---|---|"]
    lines += [f"| `{name}` | {'PASS' if good else 'FAIL'} | {detail.replace('|', '/')} |" for name, good, detail in items]
    lines += ["", f"{sum(g for _n, g, _d in items)} of {len(items)} items pass."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(ROOT))
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)
    repo = Path(a.repo)
    report = run_selfcheck(repo)
    out = repo / ".claude" / "fleet" / f"selfcheck-{a.date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(report.items, report.ok, a.date), encoding="utf-8")
    for name, ok, detail in report.items:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    print(f"selfcheck {'PASS' if report.ok else 'FAIL'}; report {out}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
