"""T-016 contracts: registry, champion/challenger, promote."""
import json
import threading

import pytest

GATES = {"n_200": 200, "n_400": 400}


def _registry(imp, tmp_path, champ=(0.10, 500), chall=None):
    reg = imp("mootcourt.registry").Registry(tmp_path)
    reg.register_model("synthetic", "champ", backtest_summary={"brier_skill": champ[0], "n": champ[1]} if champ else None)
    if chall is not None:
        reg.register_model("synthetic", "chall",
                           backtest_summary=None if chall == "missing" else {"brier_skill": chall[0], "n": chall[1]})
    return reg


def test_first_model_becomes_champion_later_ones_become_challenger(imp, tmp_path):
    reg = _registry(imp, tmp_path, chall=(0.2, 500))
    assert reg.get_champion("synthetic") == "champ"
    assert reg.get_challenger("synthetic") == "chall"
    reg.set_challenger("synthetic", "other")
    assert reg.get_challenger("synthetic") == "other"
    assert (tmp_path / "registry.json").exists()


def test_get_champion_unknown_source_raises(imp, tmp_path):
    with pytest.raises(KeyError):
        imp("mootcourt.registry").Registry(tmp_path).get_champion("nope")


@pytest.mark.parametrize("chall,promoted,needle", [
    ((0.15, 500), True, ""),                    # wins by 0.05 > 0.02 margin at n >= n_400
    ((0.121, 500), True, ""),                   # wins by 0.021, just above margin
    ((0.11, 500), False, "short by"),           # wins by 0.01 < margin
    ((0.15, 300), False, "below gate"),         # wins but n below the gate for skill 0.10
    ((0.10, 500), False, "short by"),           # tie
    ("missing", False, "no backtest"),
])
def test_promotion_rule(imp, tmp_path, chall, promoted, needle):
    reg = _registry(imp, tmp_path, chall=chall)
    res = reg.promote("synthetic", GATES, margin=0.02)
    assert res.promoted is promoted
    assert reg.get_champion("synthetic") == ("chall" if promoted else "champ"), "champion changes only on accept"
    if needle:
        assert needle in res.reason.lower()


def test_high_skill_challenger_needs_the_n_200_gate(imp, tmp_path):
    reg = _registry(imp, tmp_path, chall=(0.30, 250))
    assert reg.promote("synthetic", GATES, margin=0.02).promoted is True
    reg2 = _registry(imp, tmp_path / "b", chall=(0.30, 150))
    (tmp_path / "b").mkdir(exist_ok=True)
    assert reg2.promote("synthetic", GATES, margin=0.02).promoted is False


def test_promote_without_challenger_explains(imp, tmp_path):
    res = _registry(imp, tmp_path).promote("synthetic", GATES, margin=0.02)
    assert res.promoted is False and "challenger" in res.reason.lower()


def test_default_margin_is_a_config_constant(imp):
    assert imp("mootcourt.config").PROMOTION_MARGIN == 0.02


def test_writes_are_atomic_and_readers_never_see_partial_json(imp, tmp_path):
    reg = _registry(imp, tmp_path)
    errors, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            try:
                json.loads((tmp_path / "registry.json").read_text())
            except Exception as e:                                         # partial or missing file
                errors.append(repr(e))

    t = threading.Thread(target=reader)
    t.start()
    for i in range(300):
        reg.set_challenger("synthetic", f"m{i}")
    stop.set()
    t.join()
    assert errors == []
    assert not list(tmp_path.glob("*.tmp")) and not list(tmp_path.glob("registry.json.*"))


def test_fit_command_writes_bundle_and_fills_backtest_slot(imp, tmp_path, monkeypatch, make_synth):
    from typer.testing import CliRunner

    monkeypatch.chdir(tmp_path)
    for d in ("data/ledger", "reports", "models"):
        (tmp_path / d).mkdir(parents=True)
    ledger_mod = imp("mootcourt.ledger")
    ledger, _ = make_synth(seed=96, n_tests=120, variants_per_test=2)
    ledger_mod.write_ledger(ledger, tmp_path / "data/ledger/ledger.parquet")
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["fit", "--source", "synthetic"])
    assert res.exit_code == 0, res.output
    dirs = [p for p in (tmp_path / "models").iterdir() if p.is_dir()]
    assert len(dirs) == 1 and (dirs[0] / "manifest.json").exists()
    reg = json.loads((tmp_path / "models" / "registry.json").read_text())
    assert reg["synthetic"]["champion"] == dirs[0].name


def test_earn_weight_cli_reports_weight_stays_zero(imp, tmp_path, monkeypatch):
    from typer.testing import CliRunner

    monkeypatch.chdir(tmp_path)
    (tmp_path / "models").mkdir()
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["earn-weight"])
    assert res.exit_code == 0, res.output
    assert "stays 0" in res.output
