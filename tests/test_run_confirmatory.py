"""``scripts/run_confirmatory.sh``: the stage list, the dry run and the refusals. Nothing here runs a stage or reads a real ledger."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_confirmatory.sh"
SID = "20261114-0123456789ab"
STAGES = ["gates", "fit", "main", "by-origin", "by-origin-skill", "extras", "null-size", "smoothed-base", "one-contrast"]
RUN9_MAIN = ROOT / "paper" / "data" / "run9-visible-exposure" / "backtest-upworthy-20261106-2dc461f52ea4.json"


def run(args, script=SCRIPT, **kwargs):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PY"] = sys.executable
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, env=env, timeout=120, **kwargs)


@pytest.fixture()
def root(tmp_path):
    """A folder laid out like the data directory of the ledger, with empty stand-ins for the ledger and a record that names a snapshot."""
    d = tmp_path / "root"
    (d / "data" / "ledger").mkdir(parents=True)
    (d / "data" / "ledger" / "ledger.parquet").write_bytes(b"")
    (d / "data" / "ledger" / "confirmatory-record.json").write_text(json.dumps({"decision": "2026-11-14", "snapshot": SID}, indent=1) + "\n")
    return d


def files(d: Path) -> set[str]:
    return {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()}


def commands(stdout: str) -> dict[str, str]:
    """The dry run's lines by stage name; comment lines are left out."""
    return dict(line.split(": ", 1) for line in stdout.splitlines() if not line.startswith("#"))


def test_list_prints_the_stages_in_order():
    res = run(["--list"])
    assert res.returncode == 0, res.stderr
    assert res.stdout.split() == STAGES
    assert not any("window" in s or "randomization" in s for s in STAGES), "the run with the date rule off has no stage"


def test_dry_run_prints_every_command_and_writes_nothing(root):
    before = files(root)
    res = run(["--root", str(root), "--dry-run"])
    assert res.returncode == 0, res.stderr
    cmds = commands(res.stdout)
    assert list(cmds) == STAGES
    assert files(root) == before, "a dry run writes nothing"
    for name, cmd in cmds.items():
        assert f"MOOTCOURT_DATA_ROOT={root} " in cmd and " nice -n 19 " in cmd, name
    for name, theirs in (("gates", "gates"), ("fit", "fit-upworthy"), ("main", "main-upworthy"), ("extras", "extras-upworthy")):
        assert cmds[name].endswith(f"bash scripts/run_experiments.sh --only {theirs} {root}/logs"), name
    reports = root / "reports"
    scores, report = f"--scores {reports}/scores-upworthy-{SID}.parquet", f"--report {reports}/backtest-upworthy-{SID}.json"
    assert cmds["by-origin"].endswith(f"scripts/by_origin_difference.py {scores} {report} --out {reports}/by-origin-upworthy-{SID}.json")
    assert cmds["by-origin-skill"].endswith(f"scripts/by_origin_skill.py {scores} {report} --out {reports}/by-origin-skill-upworthy-{SID}.json")
    assert cmds["smoothed-base"].endswith(
        f"scripts/smoothed_base_skill.py {scores} {report} --out {reports}/smoothed-base-skill-upworthy-{SID}.json")
    assert cmds["null-size"].endswith(
        f"scripts/calibration_null_size.py {scores} --out {reports}/calibration-null-size-upworthy-{SID}.json --reps 400 --seed 20261113 --jobs 2")
    assert "rebuild_upworthy_ledger" not in res.stdout and "confirmatory_ledger" not in res.stdout and "fetch" not in res.stdout


def test_the_backtests_are_run_9s_main_command(root):
    """The main stage is run 9's stage, and the one-contrast run is the command of run 9's main report with one flag added."""
    main = json.loads(RUN9_MAIN.read_text(encoding="utf-8"))["header"]
    assert main["seed"] == 0 and main["bootstrap_resamples"] == 500
    recorded = main["command"].removeprefix("moot ")
    res = run(["--root", str(root), "--dry-run"])
    cmds = commands(res.stdout)
    assert cmds["one-contrast"].endswith("-m mootcourt.cli " + recorded.replace(" --seed 0", " --contrasts one --seed 0") + " --bootstrap 500")
    comment = [line for line in res.stdout.splitlines() if line.startswith("#") and " backtest " in line]
    assert len(comment) == 1 and recorded.startswith(comment[0].split("mootcourt.cli ", 1)[1])
    driver = (ROOT / "scripts" / "run_experiments.sh").read_text(encoding="utf-8")
    assert "bg main_source upworthy --challenger gbm --challenger local_eb --challenger text_lr" in driver
    assert 'step "main-$src" $MOOT backtest --source "$src" --origins quarterly "$@"' in driver
    listed = subprocess.run(["bash", "scripts/run_experiments.sh", "--list"], cwd=ROOT, capture_output=True, text=True, timeout=120,
                            env={**os.environ, "PY": sys.executable}).stdout.split()
    assert {"gates", "fit-upworthy", "main-upworthy", "extras-upworthy"} <= set(listed)


@pytest.mark.parametrize("missing", ["ledger.parquet", "confirmatory-record.json"])
def test_refuses_without_the_ledger_or_its_record(root, missing):
    (root / "data" / "ledger" / missing).unlink()
    before = files(root)
    for extra in ([], ["--dry-run"]):
        res = run(["--root", str(root), *extra])
        assert res.returncode == 1 and "missing input" in res.stderr and missing in res.stderr
        assert res.stdout == "" and files(root) == before


def test_refuses_a_record_without_a_snapshot(root):
    (root / "data" / "ledger" / "confirmatory-record.json").write_text("{}\n")
    res = run(["--root", str(root)])
    assert res.returncode == 1 and "no snapshot id" in res.stderr


def test_refuses_when_a_backtest_report_exists(root):
    (root / "reports").mkdir()
    (root / "reports" / "gates.json").write_text("{}\n")          # gates alone are not a result
    assert run(["--root", str(root), "--dry-run"]).returncode == 0
    (root / "reports" / "backtest-upworthy-20260101-aaaaaaaaaaaa.json").write_text("{}\n")
    before = files(root)
    for extra in ([], ["--dry-run"]):
        res = run(["--root", str(root), *extra])
        assert res.returncode == 1 and "runs once" in res.stderr
        assert res.stdout == "" and files(root) == before


def test_refuses_a_dirty_tree(root, tmp_path):
    """In a scratch repository: clean, the dry run is silent about the tree; with an uncommitted change under src/ a run stops first."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "src").mkdir()
    script = repo / "scripts" / "run_confirmatory.sh"
    shutil.copy(SCRIPT, script)
    (repo / "src" / "module.py").write_text("x = 1\n")
    git = ["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.invalid"]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    for args in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "first"]):
        subprocess.run([*git, *args], check=True, capture_output=True, env=env)
    clean = run(["--root", str(root), "--dry-run"], script=script)
    assert clean.returncode == 0 and clean.stderr == ""
    (repo / "src" / "module.py").write_text("x = 2\n")
    before = files(root)
    res = run(["--root", str(root)], script=script)
    assert res.returncode == 1 and "commit first" in res.stderr
    assert files(root) == before, "no log, no commit file, no report"
    noted = run(["--root", str(root), "--dry-run"], script=script)
    assert noted.returncode == 0 and "would be refused" in noted.stderr


def test_from_skips_earlier_stages_and_needs_the_main_report(root):
    res = run(["--root", str(root), "--dry-run", "--from", "extras"])
    assert res.returncode == 1 and "needs the main report" in res.stderr
    (root / "reports").mkdir()
    (root / "reports" / f"backtest-upworthy-{SID}.json").write_text("{}\n")
    res = run(["--root", str(root), "--dry-run", "--from", "extras"])
    assert res.returncode == 0 and list(commands(res.stdout)) == STAGES[STAGES.index("extras"):]
    assert run(["--root", str(root), "--dry-run", "--from", "main"]).returncode == 1, "from main the report must not exist"
    assert run(["--root", str(root), "--dry-run", "--from", "no-such-stage"]).returncode == 2


def test_usage_errors():
    assert run([]).returncode == 2
    assert run(["--unknown"]).returncode == 2
