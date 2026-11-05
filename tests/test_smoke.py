"""T-001 contracts: skeleton, config constants, CLI version, plumbing."""
import shutil
import socket
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_package_imports_and_version(imp):
    pkg = imp("mootcourt")
    assert pkg.__version__ == "1.0.0"


def test_cli_version_prints_1_0_0(imp):
    from typer.testing import CliRunner

    app = imp("mootcourt.cli").app
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output


def test_config_constants_exact(imp, spec_boundary_sentence):
    c = imp("mootcourt.config")
    assert c.THETA_GRID_N == 801
    assert c.GRID_SPAN_TAU == 8
    assert c.Z == 1.96
    assert c.ACTION_THRESHOLD == 0.35
    assert c.KAPPA == 20
    assert tuple(c.NU_GRID[:4]) == (3, 5, 10, 30) and c.NU_GRID[4] == float("inf")
    assert [round(x, 10) for x in c.LAMBDA_GRID] == [round(i / 10, 10) for i in range(11)]
    assert c.BOOTSTRAP_RESAMPLES == 200
    assert c.SUPPORT_MIN == 30
    assert c.RELIABILITY_MAX_AGE_DAYS == 14
    assert c.DRIFT_CONSECUTIVE == 2
    assert c.TRAILING_WEEKS == 8
    assert c.HORIZON_DAYS_UPWORTHY == 7
    assert c.BOUNDARY_SENTENCE == spec_boundary_sentence


def test_license_is_mit_with_author():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Yingjie Li" in text


def test_pyproject_pins_minimum_dependency_versions():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = " ".join(data["project"]["dependencies"]).lower()
    for name in ("numpy>=1.26", "scipy>=1.11", "pandas>=2.1", "pyarrow>=14", "scikit-learn>=1.4",
                 "typer>=0.12", "fastapi>=0.110", "uvicorn>=0.29", "mcp>=1.2", "matplotlib>=3.8"):
        assert name in deps.replace(" ", ""), f"missing pinned minimum {name}"
    assert data["project"]["requires-python"].replace(" ", "").startswith(">=3.11")
    assert data["project"]["scripts"]["moot"] == "mootcourt.cli:app"
    assert data["build-system"]["requires"] == ["hatchling"] or "hatchling" in " ".join(data["build-system"]["requires"])


def test_gitignore_rules_and_check_ignore():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("data/raw/", "data/ledger/", ".claude/"):
        assert entry in text, f".gitignore must list {entry}"
    for path in ("data/raw/upworthy/x.csv", "data/ledger/ledger.parquet", "reports/backtest-x.md",
                 "models/abc/manifest.json", "cards/c1.json", ".claude/fleet/plan.json"):
        rc = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode
        assert rc == 0, f"{path} must be git-ignored"
    for path in ("reports/figures/reliability.png", "data/.gitkeep", "reports/.gitkeep",
                 "models/.gitkeep", "cards/.gitkeep"):
        rc = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode
        assert rc == 1, f"{path} must not be git-ignored"


@pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")
def test_make_dry_run_resolves_every_target():
    for target in ("data", "fit", "backtest", "card", "serve", "test", "lint", "power"):
        r = subprocess.run(["make", "-n", target], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, f"make -n {target} failed: {r.stderr}"


def test_socket_guard_blocks_public_address():
    with pytest.raises(RuntimeError):
        socket.create_connection(("93.184.216.34", 80), timeout=1)


def test_socket_guard_allows_loopback_listener():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    cli = socket.create_connection(srv.getsockname(), timeout=2)
    cli.close()
    srv.close()


def test_markers_registered(pytestconfig):
    markers = " ".join(pytestconfig.getini("markers"))
    assert "slow" in markers and "realdata" in markers
