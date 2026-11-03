"""T-025 contracts: offline suite, lint, and the coverage map in reports/verification.md."""
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP_TOPICS = ["admission statuses", "origin visibility", "leakage guard", "P1 recovery", "P2 with lambda 0",
              "abstention triggers", "calibration null", "gate arithmetic", "registry promotion", "join miss typing",
              "card renderers", "service", "MCP", "writing rules"]


def test_network_is_blocked_for_the_whole_suite():
    with pytest.raises(RuntimeError):
        socket.create_connection(("198.51.100.7", 443), timeout=1)


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_ruff_is_clean():
    r = subprocess.run(["ruff", "check", "."], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]


def test_verification_md_has_a_coverage_map_that_names_real_tests():
    path = ROOT / "reports" / "verification.md"
    assert path.exists(), "T-025 must write reports/verification.md"
    text = path.read_text(encoding="utf-8")
    all_tests = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py"))
    for topic in MAP_TOPICS:
        line = next((ln for ln in text.splitlines() if topic.lower() in ln.lower() and "test_" in ln), None)
        assert line, f"coverage map lacks a line for {topic}"
        for name in re.findall(r"\btest_[A-Za-z0-9_]+", line):
            assert f"def {name}" in all_tests, f"{name} named for {topic} does not exist"
    for item in range(1, 6):
        assert re.search(rf"item {item}\b.*\b(pass|fail)", text, re.I), f"verification.md lacks pass/fail for item {item}"
