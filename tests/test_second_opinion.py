"""T-008 contracts: second opinion at weight zero."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "mootcourt"


class _Informative:
    def p_ai(self, row):
        return 0.9 if row["event"] else 0.1


class _Uninformative:
    def p_ai(self, row):
        return 0.5


def _scored(n, seed=0, base=0.3):
    rng = np.random.default_rng(seed)
    event = rng.random(n) < base
    return pd.DataFrame({"p_sig": np.full(n, base), "event": event})


def test_null_provider_returns_none(imp):
    so = imp("mootcourt.predictors.second_opinion")
    assert so.NullProvider().p_ai({"event": True}) is None


def test_stack_arithmetic(imp):
    stack = imp("mootcourt.predictors.second_opinion").stack
    assert stack(0.3, 0.9, 0.5) == pytest.approx(0.6)
    assert stack(0.3, 0.9, 0.0) == 0.3
    assert stack(0.3, None, 0.7) == 0.3
    with pytest.raises(ValueError):
        stack(0.3, 0.9, 1.5)


def test_informative_provider_earns_weight_at_gate(imp):
    so = imp("mootcourt.predictors.second_opinion")
    res = so.earn_weight(_Informative(), _scored(400), n_gate=200, margin=0.01)
    assert res.weight > 0.0


def test_uninformative_provider_stays_zero(imp):
    so = imp("mootcourt.predictors.second_opinion")
    assert so.earn_weight(_Uninformative(), _scored(400), n_gate=200, margin=0.01).weight == 0.0


def test_informative_provider_below_gate_stays_zero(imp):
    so = imp("mootcourt.predictors.second_opinion")
    res = so.earn_weight(_Informative(), _scored(100), n_gate=200, margin=0.01)
    assert res.weight == 0.0 and "gate" in res.message.lower()


def test_null_provider_stays_zero_and_says_so(imp):
    so = imp("mootcourt.predictors.second_opinion")
    res = so.earn_weight(so.NullProvider(), _scored(400), n_gate=200, margin=0.01)
    assert res.weight == 0.0 and "stays 0" in res.message


def test_weight_file_round_trip_defaults_to_zero(imp, tmp_path):
    so = imp("mootcourt.predictors.second_opinion")
    path = tmp_path / "second_opinion.json"
    assert so.load_weight(path) == 0.0
    so.save_weight(path, 0.25)
    assert so.load_weight(path) == 0.25
    assert json.loads(path.read_text())["weight"] == 0.25


def test_no_llm_or_network_client_imports_in_src():
    """Generic rule: outside the two server modules, only standard-library modules that do no network
    work and the declared numeric and serving dependencies may be imported."""
    import ast
    import sys

    runtime = {"mootcourt", "numpy", "scipy", "pandas", "sklearn", "joblib", "matplotlib", "typer",
               "fastapi", "pydantic", "uvicorn", "mcp"}
    network_stdlib = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "xmlrpc", "asyncio", "telnetlib"}
    allowed = {"service.py", "mcp_server.py", "http.py", "onboarding.py"}
    # http.py is the loopback-only HTTP simulator adapter (T-029); onboarding.py has the doctor's configured-URL health check (T-035)
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name in allowed:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                ok = top in runtime or (top in sys.stdlib_module_names and top not in network_stdlib)
                if not ok:
                    offenders.append(f"{path.relative_to(SRC)}: {name}")
    assert SRC.exists(), "src/mootcourt must exist"
    assert offenders == []
