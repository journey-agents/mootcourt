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


def _paired(lo, hi, n_tests):
    """Paired evidence as ``registry.paired_comparison`` returns it (round 01, R2, call 224): the two methods on the same rows."""
    return {"skill_diff": 0.5 * (lo + hi), "lo": lo, "hi": hi, "n_tests": n_tests, "n_rows": 3 * n_tests, "level": 0.9, "resamples": 200,
            "champion_rung": "P2", "challenger_rung": "P2"}


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


@pytest.mark.parametrize("chall,paired,promoted,needle", [
    ((0.15, 500), _paired(0.01, 0.09, 500), True, ""),                 # the paired interval clears zero at n >= n_400
    ((0.121, 500), _paired(0.001, 0.04, 500), True, ""),              # just above zero
    ((0.11, 500), _paired(-0.01, 0.03, 500), False, "interval"),      # the interval includes zero
    ((0.15, 300), _paired(0.01, 0.09, 300), False, "below gate"),     # clears zero but too few common tests for skill 0.10
    ((0.10, 500), _paired(0.0, 0.0, 500), False, "interval"),         # a tie: the same table on both sides
    ((0.15, 500), None, False, "paired"),                             # no paired evidence
    ("missing", _paired(0.01, 0.09, 500), False, "no backtest"),
])
def test_promotion_rule(imp, tmp_path, chall, paired, promoted, needle):
    reg = _registry(imp, tmp_path, chall=chall)
    res = reg.promote("synthetic", GATES, paired=paired)
    assert res.promoted is promoted, res.reason
    assert reg.get_champion("synthetic") == ("chall" if promoted else "champ"), "champion changes only on accept"
    if needle:
        assert needle in res.reason.lower()


def test_high_skill_challenger_needs_the_n_200_gate(imp, tmp_path):
    reg = _registry(imp, tmp_path, chall=(0.30, 250))
    assert reg.promote("synthetic", GATES, paired=_paired(0.05, 0.2, 250)).promoted is True
    reg2 = _registry(imp, tmp_path / "b", chall=(0.30, 150))
    (tmp_path / "b").mkdir(exist_ok=True)
    assert reg2.promote("synthetic", GATES, paired=_paired(0.05, 0.2, 150)).promoted is False


def test_a_margin_above_zero_must_be_cleared_by_the_lower_bound(imp, tmp_path):
    reg = _registry(imp, tmp_path, chall=(0.15, 500))
    assert reg.promote("synthetic", GATES, paired=_paired(0.015, 0.09, 500), margin=0.02).promoted is False
    assert reg.promote("synthetic", GATES, paired=_paired(0.025, 0.09, 500), margin=0.02).promoted is True


def test_promote_without_challenger_explains(imp, tmp_path):
    res = _registry(imp, tmp_path).promote("synthetic", GATES, paired=_paired(0.01, 0.09, 500))
    assert res.promoted is False and "challenger" in res.reason.lower()


def test_default_margin_is_a_config_constant(imp):
    assert imp("mootcourt.config").PROMOTION_MARGIN == 0.0, "the paired interval decides (round 01, R2)"


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


# ---------------------------------------------------------------- T6-plan row 1: the seed dated at the fit clock (R2 minor 9, call 248)
def _seed(last_result, cells=("a", "b"), with_marker=True):
    """A reliability file as ``write_reliability`` leaves it before any join: every date is the ledger's last result."""
    stamp = last_result.isoformat()
    report = {"source": "synthetic", "as_of": stamp,
              "cells": {c: {"as_of": stamp, "rolling_logscore": -2.0, "p0_rolling_logscore": -2.1, "brier_skill": 0.1, "n": 50,
                            "drifted": False, "consecutive_below": 0} for c in cells}}
    if with_marker:
        report["seed"] = {"last_result": stamp}
    return report


def _fit_world(imp, make_synth, tmp_path, seed_report):
    import datetime as dt

    full, _ = make_synth(seed=97, n_tests=120, variants_per_test=1)
    last = full["usable_after"].max().to_pydatetime()
    dirs = {k: tmp_path / k for k in ("ledger", "models", "reports")}
    for d in dirs.values():
        d.mkdir()
    report = seed_report(last)
    (dirs["reports"] / "reliability-synthetic.json").write_text(json.dumps(report), encoding="utf-8")
    return full, last, dirs, dt


def _fit(imp, full, dirs, clock):
    return imp("mootcourt.registry").fit_command("synthetic", full, dirs["ledger"], dirs["models"], dirs["reports"], now=clock)


def test_the_fit_dates_the_seed_at_the_fit_clock_when_the_last_result_is_within_the_staleness_limit(imp, make_synth, tmp_path):
    full, last, dirs, dt = _fit_world(imp, make_synth, tmp_path, _seed)
    clock = last + dt.timedelta(days=9)
    _fit(imp, full, dirs, clock)
    got = json.loads((dirs["reports"] / "reliability-synthetic.json").read_text())
    assert got["as_of"] == clock.isoformat()
    assert {c["as_of"] for c in got["cells"].values()} == {clock.isoformat()}
    assert got["seed"]["last_result"] == last.isoformat(), "the date of the last result stays, so a later fit can judge the limit again"
    ab = imp("mootcourt.abstain")
    assert ab.check_reliability(got, "a", clock + dt.timedelta(days=13)) is False, "fresh for the limit counted from the fit clock"


def test_the_fit_leaves_a_seed_alone_when_the_last_result_is_older_than_the_staleness_limit(imp, make_synth, tmp_path):
    full, last, dirs, dt = _fit_world(imp, make_synth, tmp_path, _seed)
    before = (dirs["reports"] / "reliability-synthetic.json").read_text()
    _fit(imp, full, dirs, last + dt.timedelta(days=15))
    assert (dirs["reports"] / "reliability-synthetic.json").read_text() == before


def test_the_fit_never_redates_a_report_a_join_has_written(imp, make_synth, tmp_path):
    full, last, dirs, dt = _fit_world(imp, make_synth, tmp_path, lambda t: _seed(t, with_marker=False))
    before = (dirs["reports"] / "reliability-synthetic.json").read_text()
    _fit(imp, full, dirs, last + dt.timedelta(days=3))
    assert (dirs["reports"] / "reliability-synthetic.json").read_text() == before


def test_the_fit_without_a_reliability_file_writes_none(imp, make_synth, tmp_path):
    full, last, dirs, dt = _fit_world(imp, make_synth, tmp_path, _seed)
    (dirs["reports"] / "reliability-synthetic.json").unlink()
    _fit(imp, full, dirs, last + dt.timedelta(days=3))
    assert not (dirs["reports"] / "reliability-synthetic.json").exists()


def test_a_seed_written_after_the_fit_is_dated_at_the_champions_fit_clock(imp, make_synth, tmp_path):
    """The quickstart fits first and runs the backtest second, so the seed does not exist yet when the fit runs."""
    full, last, dirs, dt = _fit_world(imp, make_synth, tmp_path, _seed)
    (dirs["reports"] / "reliability-synthetic.json").unlink()
    clock = last + dt.timedelta(days=4)
    _fit(imp, full, dirs, clock)
    (dirs["reports"] / "reliability-synthetic.json").write_text(json.dumps(_seed(last)), encoding="utf-8")
    assert imp("mootcourt.registry").date_seed_at_champion_fit(dirs["models"], dirs["reports"], "synthetic") is True
    assert json.loads((dirs["reports"] / "reliability-synthetic.json").read_text())["as_of"] == clock.isoformat()
    assert imp("mootcourt.registry").date_seed_at_champion_fit(dirs["models"], dirs["reports"], "nope") is False
