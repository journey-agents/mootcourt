"""T-012 contracts: synthetic ledger CLI and gate power."""
import json
import time

import pytest


def test_gate_power_is_seed_deterministic(imp):
    sim = imp("mootcourt.simulate")
    a = sim.gate_power(150, 0.20, base=0.30, reps=120, B=100, seed=5)
    b = sim.gate_power(150, 0.20, base=0.30, reps=120, B=100, seed=5)
    assert a == b and 0.0 <= a <= 1.0


def test_power_rises_with_n_and_with_skill(imp):
    sim = imp("mootcourt.simulate")
    kw = dict(base=0.30, reps=200, B=100, seed=1)
    p_small, p_big = sim.gate_power(60, 0.20, **kw), sim.gate_power(600, 0.20, **kw)
    assert p_big > p_small + 0.2
    q_low, q_high = sim.gate_power(250, 0.05, **kw), sim.gate_power(250, 0.30, **kw)
    assert q_high > q_low + 0.1


def test_false_positive_rate_at_zero_skill_is_small(imp):
    sim = imp("mootcourt.simulate")
    assert sim.gate_power(300, 0.0, base=0.30, reps=300, B=100, seed=2) <= 0.06


def test_gate_power_rejects_bad_inputs(imp):
    sim = imp("mootcourt.simulate")
    with pytest.raises(ValueError):
        sim.gate_power(0, 0.2)
    with pytest.raises(ValueError):
        sim.gate_power(100, 1.5)
    with pytest.raises(ValueError):
        sim.gate_power(100, 0.2, base=1.0)


def test_n_for_power_returns_smallest_grid_n_meeting_target(imp):
    sim = imp("mootcourt.simulate")
    grid = [50, 100, 200, 400, 800, 1600]
    n = sim.n_for_power(0.20, target=0.80, base=0.30, reps=150, B=100, seed=3, grid=grid)
    assert n in grid
    assert sim.gate_power(n, 0.20, base=0.30, reps=150, B=100, seed=3) >= 0.80
    smaller = [g for g in grid if g < n]
    if smaller:
        assert sim.gate_power(smaller[-1], 0.20, base=0.30, reps=150, B=100, seed=3) < 0.80
    harder = sim.n_for_power(0.10, target=0.80, base=0.30, reps=150, B=100, seed=3, grid=grid)
    assert harder >= n


def test_write_gates_schema_and_load_gates(imp, tmp_path):
    sim = imp("mootcourt.simulate")
    path = tmp_path / "gates.json"
    sim.write_gates(path, reps=60, B=50, seed=4, grid=[50, 100, 200, 400, 800, 1600, 3200])
    data = json.loads(path.read_text())
    for key in ("n_200", "n_400", "base_rate", "target_power", "reps", "seed", "label", "skills"):
        assert key in data
    assert data["label"] == "synthetic" and data["skills"] == {"n_200": 0.20, "n_400": 0.10}
    assert data["n_400"] >= data["n_200"]
    loaded = sim.load_gates(path)
    assert loaded["n_200"] == data["n_200"] and loaded["n_400"] == data["n_400"]


def test_load_gates_missing_file_tells_the_user_what_to_run(imp, tmp_path):
    with pytest.raises(FileNotFoundError, match="moot simulate power"):
        imp("mootcourt.simulate").load_gates(tmp_path / "nope.json")


def test_cli_simulate_ledger_writes_valid_synthetic_ledger(imp, tmp_path):
    from typer.testing import CliRunner

    out = tmp_path / "ledger.parquet"
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["simulate", "ledger", "--out", str(out)])
    assert res.exit_code == 0, res.output
    ledger = imp("mootcourt.ledger")
    df = ledger.read_ledger(out)
    ledger.validate_ledger(df)
    assert set(df["source"]) == {"synthetic"}


def test_cli_simulate_power_writes_gates_json(imp, tmp_path, monkeypatch):
    from typer.testing import CliRunner

    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["simulate", "power", "--reps", "40", "--bootstrap", "40"])
    assert res.exit_code == 0, res.output
    assert (tmp_path / "reports" / "gates.json").exists()
    assert "synthetic" in res.output.lower()


@pytest.mark.slow
def test_full_power_run_finishes_in_three_minutes(imp, tmp_path):
    sim = imp("mootcourt.simulate")
    t = time.perf_counter()
    sim.write_gates(tmp_path / "gates.json")
    assert time.perf_counter() - t < 180
