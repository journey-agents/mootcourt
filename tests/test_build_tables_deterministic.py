"""The table builder's output must not depend on the interpreter's hash seed (round 01 verification of chunk P: six decision tables
changed between runs because policy rows were ordered by set iteration)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "paper" / "data" / "run8-randomization-window"


def _build(out: Path, seed: str) -> dict[str, bytes]:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    subprocess.run(
        [sys.executable, str(ROOT / "paper" / "build_tables.py"), "--reports", str(RUN), "--out", str(out)],
        check=True, env=env, cwd=ROOT, capture_output=True,
    )
    return {p.name: p.read_bytes() for p in sorted(out.glob("*.tex"))}


def test_tables_are_identical_under_different_hash_seeds(tmp_path):
    a = _build(tmp_path / "a", "0")
    b = _build(tmp_path / "b", "2")
    assert a.keys() == b.keys()
    differing = [name for name in a if a[name] != b[name]]
    assert differing == [], differing
    assert any(name.startswith("decision-") for name in a)
