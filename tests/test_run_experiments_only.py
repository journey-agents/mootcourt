"""Tier C tooling: ``scripts/run_experiments.sh --list``, ``--only <stage>[,<stage>]`` and ``--dry-run``."""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_experiments.sh"


def run(args, tmp_path, py=None, env_extra=None):
    env = {**os.environ, "PY": py or sys.executable, "MOOTCOURT_DATA_ROOT": str(tmp_path / "data-root")}
    env.update(env_extra or {})
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, env=env, timeout=120)


@pytest.fixture()
def stub(tmp_path):
    """A stand-in interpreter: answers the two path queries of the script and records every other call."""
    calls = tmp_path / "calls.txt"
    path = tmp_path / "stub-python"
    path.write_text(f'#!/bin/bash\nif [ "$1" = "-c" ]; then echo "{tmp_path}/fake-root"; exit 0; fi\necho "$*" >> "{calls}"\n')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path, calls


def test_list_prints_every_stage_and_runs_nothing(tmp_path):
    res = run(["--list"], tmp_path)
    assert res.returncode == 0, res.stderr
    stages = res.stdout.split()
    assert stages[0] == "gates" and "main-synthetic" in stages and "lc-upworthy" in stages and "fit-asos" in stages
    assert "ablation-upworthy-p2-guard_off" in stages or any(s.startswith("ablation-upworthy-") for s in stages)
    assert stages.index("fit-upworthy") < stages.index("main-upworthy") < stages.index("lc-upworthy") < stages.index("latency")
    assert len(stages) == len(set(stages)), "each stage is listed once"
    assert not (tmp_path / "data-root").exists(), "listing creates nothing"


def test_only_with_dry_run_prints_just_the_named_stage(tmp_path):
    res = run(["--only", "fit-synthetic", "--dry-run"], tmp_path)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().splitlines() == ["fit-synthetic"]


def test_only_takes_several_stages_and_a_glob_in_script_order(tmp_path):
    res = run(["--only", "latency,fit-*", "--dry-run"], tmp_path)
    assert res.stdout.split() == ["fit-upworthy", "fit-asos", "fit-synthetic", "latency"]


def test_an_unknown_stage_is_refused(tmp_path):
    res = run(["--only", "no-such-stage", "--dry-run"], tmp_path)
    assert res.returncode == 2 and "no-such-stage" in res.stderr


def test_only_runs_the_named_stage_and_nothing_else(tmp_path, stub):
    py, calls = stub
    logs = tmp_path / "logs"
    res = run(["--only", "fit-synthetic", str(logs)], tmp_path, py=str(py))
    assert res.returncode == 0, res.stderr
    assert calls.read_text().strip().splitlines() == ["-m mootcourt.cli fit --source synthetic"]
    lines = (logs / "stages.txt").read_text().strip().splitlines()
    assert [ln.split()[:2] for ln in lines] == [["fit-synthetic", "0"]], "no other stage and no experiments-done marker"


def test_without_flags_the_usage_is_unchanged(tmp_path):
    res = run([], tmp_path)
    assert res.returncode != 0 and "usage" in res.stderr


def test_the_script_is_shellcheck_clean_when_shellcheck_is_installed():
    if subprocess.run(["which", "shellcheck"], capture_output=True).returncode != 0:
        pytest.skip("shellcheck is not installed")
    res = subprocess.run(["shellcheck", "-S", "warning", str(SCRIPT)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout
