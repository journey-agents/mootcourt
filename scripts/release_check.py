#!/usr/bin/env python3
"""Run the automatic part of the release checklist in docs/release.md and print one line per check.

Exit code 0 when every check passes, 1 otherwise. Needs ``uv`` and the dev and docs extras.

Network: the wheel check builds the package and installs the wheel with its dependencies from the package index, so it needs
network access (or a warm uv cache); every other check is local. Nothing else in this script contacts a server.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = ("CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "LICENSE", "README.md", "Dockerfile",
                  ".github/workflows/ci.yml", "mkdocs.yml", "docs/release.md")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def check_versions() -> str | None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    init = re.search(r'__version__ = "([^"]+)"', (ROOT / "src" / "mootcourt" / "__init__.py").read_text(encoding="utf-8"))
    if not init or init.group(1) != version:
        return f"pyproject says {version} but the package says {init.group(1) if init else 'nothing'}"
    top = re.search(r"^## \[([^\]]+)\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    if not top or top.group(1) != version:
        return f"the newest CHANGELOG entry is {top.group(1) if top else 'missing'}, not {version}"
    return None


def check_files() -> str | None:
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    return f"missing: {', '.join(missing)}" if missing else None


def check_process(cmd: list[str]) -> str | None:
    r = run(cmd)
    if r.returncode == 0:
        return None
    out = (r.stdout + r.stderr).strip()
    failed = [ln for ln in out.splitlines() if ln.startswith(("FAILED ", "ERROR "))]        # a test run: name the failing tests
    return "; ".join(failed)[-600:] if failed else out[-600:]


def check_wheel() -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        r = run(["uv", "build", "--out-dir", tmp])
        if r.returncode != 0:
            return (r.stdout + r.stderr).strip()[-600:]
        wheels = sorted(Path(tmp).glob("*.whl"))
        if not wheels:
            return "no wheel was built"
        with zipfile.ZipFile(wheels[0]) as z:
            names = z.namelist()
        if not any(n.endswith("mootcourt/cli.py") for n in names) or not any(n.endswith("entry_points.txt") for n in names):
            return "the wheel lacks the package or its entry points"
        venv = Path(tmp) / "venv"
        for cmd in (["uv", "venv", str(venv)], ["uv", "pip", "install", "--python", str(venv / "bin" / "python"), str(wheels[0])]):
            r = run(cmd)
            if r.returncode != 0:
                return (r.stdout + r.stderr).strip()[-600:]
        r = run([str(venv / "bin" / "moot"), "--version"])
        return None if r.returncode == 0 and r.stdout.strip() else "the installed wheel does not run `moot --version`"


def main() -> int:
    checks = [
        ("version and changelog agree", check_versions),
        ("required files exist", check_files),
        ("ruff is clean", lambda: check_process(["uv", "run", "ruff", "check", "src", "tests", "scripts"])),
        ("tests pass", lambda: check_process(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"])),
        ("wheel builds, installs and runs", check_wheel),
        ("documentation builds without warnings", lambda: check_process(["make", "docs"])),
        ("results block in the README is current", lambda: check_process(["uv", "run", "python", "scripts/render_readme_results.py", "--check"])),
    ]
    failed = 0
    for name, fn in checks:
        problem = fn()
        print(f"{'ok  ' if problem is None else 'FAIL'} {name}" + (f": {problem}" if problem else ""), flush=True)
        failed += problem is not None
    print("docker is not part of this script: run `make docker-check` where a Docker daemon is available")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
