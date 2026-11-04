"""Round 01, reviewer R2 (platform engineer), T-063: the loop never credits a card with information from after its issue time.

Six groups, one per finding: the post-hoc join guard (blocking), backdating refused, one scored card per row, the nightly fit under the
visibility rule, the paired promotion, and the card's own cell figure on the backtest line. The fixtures are the synthetic source (seconds)
and the sample ledger of ``moot init`` for the reproduction of R2's exp-120 case.
"""
from __future__ import annotations

import datetime as dt
import functools
import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

UTC = dt.timezone.utc
CELL = "headline_only"
GATES = {"n_200": 20, "n_400": 40, "interval": {"by": "test"}, "base_rate": 0.3}


def _fresh_report(as_of: dt.datetime, cell: str = CELL, source: str = "synthetic", n: int = 500) -> dict:
    return {"source": source, "as_of": as_of.isoformat(),
            "cells": {cell: {"as_of": as_of.isoformat(), "rolling_logscore": -2.0, "p0_rolling_logscore": -2.1, "brier_skill": 0.12,
                             "n": n, "drifted": False, "consecutive_below": 0}}}


@functools.lru_cache(maxsize=1)
def _ledger() -> pd.DataFrame:
    syn = importlib.import_module("mootcourt.sources.synthetic")
    full, _ = syn.generate(syn.SyntheticConfig(seed=161, n_tests=300, variants_per_test=1))
    return full


@functools.lru_cache(maxsize=1)
def _split():
    """``(old, new, bundle, origin, now0, rows)``: a bundle fit on the old rows, and the new rows that start after ``now0``."""
    from mootcourt.bundle import fit_bundle
    from mootcourt.ledger import snapshot_id

    full = _ledger()
    cut = full["started_at"].quantile(0.8)
    old, new = full[full["started_at"] < cut], full[full["started_at"] >= cut]
    bundle = fit_bundle(old, "synthetic", snapshot_id(old, today=dt.date(2014, 7, 1)))
    origin = old["usable_after"].max().to_pydatetime()
    now0 = origin + dt.timedelta(days=1)
    rows = new[(new["started_at"] > now0 + dt.timedelta(days=1)) & (new["cell"] == CELL)]
    assert len(rows) >= 3, "the fixture needs rows of the cell that start after the first issue time"
    return old, new, bundle, origin, now0, rows


def _request(row, origin, **over):
    from mootcourt.card import CardRequest

    kw = dict(source="synthetic", headline=json.loads(row.features_json)["headline"], image_changed=False, impressions=20000,
              origin=origin, row_id=row.row_id)
    kw.update(over)
    return CardRequest(**kw)


def _card(bundle, row, origin, now, report=None, **over):
    from mootcourt.card import build_card

    return build_card(bundle, _request(row, origin, **over), reliability=report or _fresh_report(now - dt.timedelta(days=1)), now=now)


def _dirs(tmp_path, old) -> dict:
    from mootcourt.ledger import write_ledger

    dirs = {k: tmp_path / k for k in ("ledger", "cards", "reports")}
    for d in dirs.values():
        d.mkdir()
    write_ledger(old, dirs["ledger"] / "ledger.parquet")
    return dirs


def _join(dirs, new, now):
    from mootcourt.loop import join_new_rows

    return join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic", now=now)


def _outcome(dirs, card_id) -> dict:
    return json.loads((dirs["cards"] / "outcomes" / f"{card_id}.json").read_text())


# ============================================================================ 1. the post-hoc join guard (blocking)
def test_a_card_is_pre_launch_only_when_issued_at_or_before_its_test_started_and_is_never_scored_otherwise():
    from mootcourt import card as card_mod
    from mootcourt.loop import outcome_from_card, reliability_row
    from mootcourt.predictors.p0 import P0Predictor

    old, new, bundle, origin, now0, rows = _split()
    row = rows.iloc[0]
    started, usable = row["started_at"].to_pydatetime(), row["usable_after"].to_pydatetime()
    p0 = P0Predictor().fit(old)
    join_at = usable + dt.timedelta(days=2)
    cases = {
        "pre_launch": now0,                                   # issued before the test started
        "at_start": started,                                  # issued at the start instant: the test has produced nothing yet
        "in_flight": started + dt.timedelta(seconds=1),       # one second into the test
        "after_result": usable + dt.timedelta(days=1),        # the result is in the ledger
    }
    outcomes = {}
    for name, when in cases.items():
        card = card_mod.to_json(_card(bundle, row, when, when))
        outcomes[name] = outcome_from_card(card, row, p0, join_at)
    for name in ("pre_launch", "at_start"):
        o = outcomes[name]
        assert o["timing"] == "pre_launch" and o["post_hoc"] is False and o["scored"] is True, name
        assert o["logscore"] is not None and reliability_row(o) is not None, name
    assert outcomes["in_flight"]["timing"] == "in_flight" and outcomes["after_result"]["timing"] == "after_result"
    for name in ("in_flight", "after_result"):
        o = outcomes[name]
        assert o["post_hoc"] is True and o["scored"] is False, name
        assert o["logscore"] is None and o["p0_logscore"] is None and o["brier"] is None and o["miss_type"] is None, name
        assert reliability_row(o) is None, "a post-hoc card is no reliability evidence"
        assert "started" in o["post_hoc_reason"] and o["card_issued_at"] and o["row_started_at"], name
    # the origin counts as much as the issue time: a card whose stated issue time predates launch but whose origin saw the result is post-hoc
    backdated = card_mod.to_json(_card(bundle, row, now0, now0))
    backdated["origin"] = (usable + dt.timedelta(days=1)).isoformat()
    o = outcome_from_card(backdated, row, p0, join_at)
    assert o["timing"] == "after_result" and o["post_hoc"] is True and o["scored"] is False
    # the horizon guard still comes first: before the horizon there is no outcome of any kind
    assert outcome_from_card(card_mod.to_json(_card(bundle, row, now0, now0)), row, p0, usable - dt.timedelta(seconds=1)) is None


def test_the_join_records_a_post_hoc_card_apart_and_keeps_it_out_of_the_reliability_report(tmp_path):
    from mootcourt import card as card_mod
    from mootcourt.loop import load_outcomes

    old, new, bundle, origin, now0, rows = _split()
    dirs = _dirs(tmp_path, old)
    row_a, row_b = rows.iloc[0], rows.iloc[1]
    pre = _card(bundle, row_a, now0, now0)
    late_at = row_b["usable_after"].to_pydatetime() + dt.timedelta(days=1)
    late = _card(bundle, row_b, late_at, late_at)
    for c in (pre, late):
        card_mod.freeze_card(c, dirs["cards"])
    join_at = max(row_a["usable_after"], row_b["usable_after"]).to_pydatetime() + dt.timedelta(days=2)
    res = _join(dirs, new, join_at)
    assert res.n_outcomes == 1 and res.n_post_hoc == 1 and res.n_reissues == 0
    assert res.post_hoc == ((late.card_id, _outcome(dirs, late.card_id)["post_hoc_reason"]),)
    assert _outcome(dirs, pre.card_id)["scored"] is True and _outcome(dirs, late.card_id)["post_hoc"] is True
    assert len(load_outcomes(dirs["cards"], "synthetic")) == 1
    report = json.loads(res.reliability_path.read_text())
    assert report["cells"][CELL]["n"] == 1 and report["cells"][CELL]["n_tests"] == 1
    again = _join(dirs, new.iloc[0:0], join_at + dt.timedelta(days=1))
    assert again.n_outcomes == 0 and again.n_post_hoc == 0, "outcome files are written once"


def _sample_world(tmp_path):
    """R2's scratch project: the sample ledger of ``moot init`` with a champion fit on every row, exp-120 included."""
    from mootcourt.bundle import fit_bundle, save_bundle
    from mootcourt.importers.ingest import import_file
    from mootcourt.importers.sample import sample_exchange
    from mootcourt.ledger import ensure_snapshot, write_ledger
    from mootcourt.registry import Registry
    from mootcourt.storage import storage_paths

    root = tmp_path / "mootcourt-data"
    layout = storage_paths(root=root)
    for folder in layout.named().values():
        folder.mkdir(parents=True, exist_ok=True)
    csv = tmp_path / "sample.csv"
    sample_exchange().to_csv(csv, index=False)
    ledger, _ = import_file("generic", csv, "sample")
    write_ledger(ledger, layout.ledger_path)
    sid = ensure_snapshot(ledger, layout.ledger_path.parent)
    bundle = fit_bundle(ledger, "sample", sid)
    save_bundle(bundle, layout.models)
    Registry(layout.models).register_model("sample", bundle.model_id)
    return layout, ledger, bundle


def test_r2_exp_120_a_card_issued_the_day_after_its_result_is_recorded_post_hoc_by_the_join_and_counted_by_the_doctor(tmp_path, monkeypatch):
    from mootcourt import onboarding
    from mootcourt.cli import app

    layout, ledger, bundle = _sample_world(tmp_path)
    row = ledger.set_index("row_id").loc["sample:exp-120:treatment::checkout_conversion"]
    assert str(row["started_at"])[:10] == "2025-12-15" and str(row["usable_after"])[:10] == "2025-12-29"
    assert bundle.fit_cutoff == row["usable_after"], "the champion was fit on the result, as in the review"
    common = ["--models-dir", str(layout.models), "--cards-dir", str(layout.cards), "--reports-dir", str(layout.reports)]
    res = CliRunner().invoke(app, ["card", "--source", "sample", "--cell", "checkout_conversion", "--impressions", "20000",
                                   "--row-id", "sample:exp-120:treatment::checkout_conversion", "--now", "2025-12-30T00:00:00+00:00", *common])
    assert res.exit_code == 0, res.output
    (card_file,) = [p for p in layout.cards.glob("*.json")]
    res = CliRunner().invoke(app, ["join", "--source", "sample", "--ledger", str(layout.ledger_path), "--cards-dir", str(layout.cards),
                                   "--reports-dir", str(layout.reports), "--now", "2025-12-31T00:00:00+00:00"])
    assert res.exit_code == 0, res.output
    assert "attached 0 outcomes" in res.output and "1 post-hoc card" in res.output, res.output
    outcome = json.loads((layout.cards / "outcomes" / card_file.name).read_text())
    assert outcome["post_hoc"] is True and outcome["timing"] == "after_result" and outcome["logscore"] is None
    report = json.loads((layout.reports / "reliability-sample.json").read_text())
    assert report["cells"] == {}, "the post-hoc card must not become the cell's window"
    # the doctor counts it
    (tmp_path / "mootcourt.toml").write_text(onboarding.config_text(data_root=root_of(layout), cells=["checkout_conversion"], name="r2"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    doc = onboarding.run_doctor(now=dt.datetime(2025, 12, 31, tzinfo=UTC), write=False)
    cards_check = next(c for c in doc["checks"] if c["name"] == "cards sample")
    assert cards_check["status"] == "warn" and "1 post-hoc" in cards_check["detail"] and "0 reissue" in cards_check["detail"]


def root_of(layout) -> Path:
    return Path(layout.root)


# ============================================================================ 2. backdating refused
def test_an_origin_after_the_issue_time_is_refused_on_every_interface(tmp_path):
    from fastapi.testclient import TestClient

    from mootcourt.bundle import save_bundle
    from mootcourt.mcp_server import tool_get_card
    from mootcourt.registry import Registry
    from mootcourt.service import ServingState, create_app

    old, new, bundle, origin, now0, rows = _split()
    row = rows.iloc[0]
    later = now0 + dt.timedelta(days=3)
    with pytest.raises(ValueError, match="origin"):
        _card(bundle, row, later, now0)
    same = _card(bundle, row, now0, now0)                      # an origin equal to the issue time is the normal card
    assert same.origin == same.issued_at
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    save_bundle(bundle, models)
    Registry(models).register_model("synthetic", bundle.model_id)
    (reports / "reliability-synthetic.json").write_text(json.dumps(_fresh_report(now0 - dt.timedelta(days=1))))
    client = TestClient(create_app(models, cards, reports_dir=reports, now=lambda: now0))
    payload = {"source": "synthetic", "headline": "a headline", "image_changed": False, "impressions": 20000, "origin": later.isoformat()}
    res = client.post("/card", json=payload)
    assert res.status_code == 422 and "origin" in res.json()["error"]
    assert list(cards.glob("*.json")) == [], "a refused card is not frozen"
    assert client.post("/card", json={**payload, "origin": now0.isoformat()}).status_code == 200
    state = ServingState(models, reports, now=lambda: now0)
    with pytest.raises(ValueError, match="origin"):
        tool_get_card(state, "synthetic", "a headline", False, 20000, origin=later.isoformat())


# ============================================================================ 3. one scored card per row
def test_two_pre_launch_cards_for_one_row_score_once_the_earliest_and_the_later_one_is_a_reissue(tmp_path):
    from mootcourt import card as card_mod

    old, new, bundle, origin, now0, rows = _split()
    dirs = _dirs(tmp_path, old)
    row = rows.iloc[0]
    first = _card(bundle, row, now0, now0)
    second = _card(bundle, row, now0 + dt.timedelta(hours=1), now0 + dt.timedelta(hours=1))
    assert first.card_id != second.card_id
    for c in (second, first):                                  # frozen in the other order: the issue time decides, not the file order
        card_mod.freeze_card(c, dirs["cards"])
    join_at = row["usable_after"].to_pydatetime() + dt.timedelta(days=1)
    res = _join(dirs, new, join_at)
    assert res.n_outcomes == 1 and res.n_reissues == 1 and res.n_post_hoc == 0
    scored, reissue = _outcome(dirs, first.card_id), _outcome(dirs, second.card_id)
    assert scored["scored"] is True and scored["reissue"] is False
    assert reissue["reissue"] is True and reissue["superseded_by"] == first.card_id and reissue["scored"] is False
    assert reissue["logscore"] is None and reissue["brier"] is None
    report = json.loads(res.reliability_path.read_text())
    assert report["cells"][CELL]["n"] == 1 and report["cells"][CELL]["n_tests"] == 1, "R2's n 2 case now counts the row once"
    # a card for the row that appears after the row was scored is a reissue too, whatever issue time it states
    third = _card(bundle, row, now0 - dt.timedelta(days=1), now0 - dt.timedelta(days=1))
    card_mod.freeze_card(third, dirs["cards"])
    res2 = _join(dirs, new.iloc[0:0], join_at + dt.timedelta(days=1))
    assert res2.n_outcomes == 0 and res2.n_reissues == 1
    assert _outcome(dirs, third.card_id)["superseded_by"] == first.card_id
    assert json.loads(res2.reliability_path.read_text())["cells"][CELL]["n"] == 1


def test_only_pre_launch_cards_compete_for_the_scored_slot(tmp_path):
    from mootcourt import card as card_mod

    old, new, bundle, origin, now0, rows = _split()
    dirs = _dirs(tmp_path, old)
    row = rows.iloc[0]
    flight_at = row["started_at"].to_pydatetime() + dt.timedelta(hours=1)
    flight = _card(bundle, row, flight_at, flight_at)
    pre = _card(bundle, row, now0 + dt.timedelta(hours=2), now0 + dt.timedelta(hours=2))
    for c in (flight, pre):
        card_mod.freeze_card(c, dirs["cards"])
    res = _join(dirs, new, row["usable_after"].to_pydatetime() + dt.timedelta(days=1))
    assert res.n_outcomes == 1 and res.n_post_hoc == 1 and res.n_reissues == 0
    assert _outcome(dirs, pre.card_id)["scored"] is True and _outcome(dirs, flight.card_id)["post_hoc"] is True


# ============================================================================ 4. the nightly fit under the visibility rule
def test_the_fit_command_takes_only_the_rows_usable_at_the_fit_clock(tmp_path):
    from mootcourt.bundle import load_bundle, read_manifest
    from mootcourt.ledger import visible_rows
    from mootcourt.registry import fit_command

    full = _ledger()
    clock = full["usable_after"].quantile(0.8).to_pydatetime()
    n_usable, n_all = len(visible_rows(full, clock)), int((full["status"] == "admitted").sum())
    assert n_usable < n_all, "the fixture needs rows that are not yet usable at the clock"
    ldir, mdir, rdir = tmp_path / "ledger", tmp_path / "models", tmp_path / "reports"
    for d in (ldir, mdir, rdir):
        d.mkdir()
    model_id, sid, role, summary = fit_command("synthetic", full, ldir, mdir, rdir, now=clock)
    bundle = load_bundle(model_id, mdir)
    assert bundle.n_rows == n_usable and bundle.fit_cutoff <= pd.Timestamp(clock)
    bundle.check_origin(clock)                                  # a card at the fit clock issues from this bundle
    manifest = read_manifest(model_id, mdir)
    assert manifest["fit_as_of"] == clock.isoformat()
    reg = json.loads((mdir / "registry.json").read_text())["synthetic"]
    assert reg["data_through"][model_id] == bundle.fit_cutoff.isoformat()


def test_moot_fit_takes_a_clock_and_records_it(tmp_path, monkeypatch):
    from mootcourt.bundle import read_manifest
    from mootcourt.cli import app
    from mootcourt.ledger import visible_rows, write_ledger

    full = _ledger()
    clock = full["usable_after"].quantile(0.8).to_pydatetime()
    monkeypatch.chdir(tmp_path)
    for d in ("data/ledger", "reports", "models"):
        (tmp_path / d).mkdir(parents=True)
    write_ledger(full, tmp_path / "data/ledger/ledger.parquet")
    res = CliRunner().invoke(app, ["fit", "--source", "synthetic", "--now", clock.isoformat()])
    assert res.exit_code == 0, res.output
    reg = json.loads((tmp_path / "models" / "registry.json").read_text())["synthetic"]
    manifest = read_manifest(reg["champion"], tmp_path / "models")
    assert manifest["fit_as_of"] == clock.isoformat() and manifest["parameters"]["n_rows"] == len(visible_rows(full, clock))
    assert f"{len(visible_rows(full, clock))} rows usable at" in res.output


# ============================================================================ 5. the paired promotion
def _scores(seed: int, n_tests: int = 40, better_by: float = 0.0, drop: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_tests):
        for v in range(3):
            base = 0.21
            rows.append({"row_id": f"s:t{t}:v{v}", "test_id": f"t{t}", "rung": "P2", "brier_base": base,
                         "brier_event": max(0.0, base - better_by + rng.normal(0.0, 0.01))})
    df = pd.DataFrame(rows)
    return df.iloc[drop:].reset_index(drop=True)


def test_paired_comparison_uses_common_rows_and_bootstraps_the_skill_difference_by_test():
    from mootcourt.registry import paired_comparison

    champ, chall = _scores(1), _scores(2, better_by=0.02, drop=10)
    out = paired_comparison(champ, chall, rung_champion="P2", rung_challenger="P2", B=100, seed=0)
    assert out["n_rows"] == 110 and out["n_tests"] == chall["test_id"].nunique() == 37 and out["level"] == 0.9
    assert out["skill_diff"] > 0 and out["lo"] > 0 and out["hi"] > out["lo"]
    expected = (champ.set_index("row_id").loc[chall["row_id"], "brier_event"].to_numpy() - chall["brier_event"].to_numpy()).mean() / 0.21
    assert out["skill_diff"] == pytest.approx(expected)
    tie = paired_comparison(champ, champ, rung_champion="P2", rung_challenger="P2", B=100, seed=0)
    assert tie["skill_diff"] == 0.0 and tie["lo"] == 0.0 and tie["hi"] == 0.0


def _reg(tmp_path, chall_summary=None):
    from mootcourt.registry import Registry

    reg = Registry(tmp_path)
    reg.register_model("s", "champ", {"brier_skill": 0.10, "n": 500, "n_tests": 150})
    reg.register_model("s", "chall", chall_summary if chall_summary is not None else {"brier_skill": 0.12, "n": 500, "n_tests": 150})
    return reg


def _paired(lo, hi=None, n_tests=150, n_rows=450):
    return {"skill_diff": (lo + (hi if hi is not None else lo + 0.02)) / 2, "lo": lo, "hi": hi if hi is not None else lo + 0.02,
            "n_tests": n_tests, "n_rows": n_rows, "level": 0.9, "resamples": 200, "champion_rung": "P2", "challenger_rung": "P2"}


@pytest.mark.parametrize("paired,promoted,needle", [
    (_paired(0.005, 0.03), True, ""),                        # the interval clears zero at the gate
    (_paired(-0.004, 0.03), False, "interval"),              # includes zero
    (_paired(0.005, 0.03, n_tests=30), False, "below gate"), # too few common tests for the challenger's skill
    (None, False, "paired"),                                 # no paired evidence at all
])
def test_promotion_needs_the_paired_interval_to_clear_the_margin_at_the_gate(tmp_path, paired, promoted, needle):
    reg = _reg(tmp_path)
    res = reg.promote("s", GATES, paired=paired)
    assert res.promoted is promoted, res.reason
    assert reg.get_champion("s") == ("chall" if promoted else "champ")
    if needle:
        assert needle in res.reason.lower(), res.reason
    if promoted:
        last = json.loads((tmp_path / "registry.json").read_text())["s"]["history"][-1]
        assert last["event"] == "promoted" and last["paired"]["lo"] == paired["lo"] and last["margin"] == 0.0


def test_the_promotion_margin_is_zero_by_default_and_the_earn_weight_margin_keeps_its_own_constant():
    from mootcourt import config

    assert config.PROMOTION_MARGIN == 0.0 and config.EARN_WEIGHT_MARGIN == 0.02


def test_promote_command_pairs_the_two_score_tables_by_row_and_refuses_a_shared_table(tmp_path):
    from mootcourt.registry import Registry, promote_command

    mdir, rdir = tmp_path / "models", tmp_path / "reports"
    mdir.mkdir(), rdir.mkdir()
    (rdir / "gates.json").write_text(json.dumps(GATES))
    champ, chall = _scores(1), _scores(2, better_by=0.03)
    champ.to_parquet(rdir / "scores-s-snapA.parquet", index=False)
    chall.to_parquet(rdir / "scores-s-snapB.parquet", index=False)
    reg = Registry(mdir)
    reg.register_model("s", "champ", {"brier_skill": 0.10, "n": 120, "n_tests": 40, "rung": "P2", "snapshot_id": "snapA",
                                      "report": "backtest-s-snapA.json", "scores": "scores-s-snapA.parquet"})
    reg.register_model("s", "chall", {"brier_skill": 0.12, "n": 120, "n_tests": 40, "rung": "P2", "snapshot_id": "snapA",
                                      "report": "backtest-s-snapA.json", "scores": "scores-s-snapA.parquet"})
    shared = promote_command(mdir, rdir, "s")
    assert shared.promoted is False and "same" in shared.reason.lower()
    res = promote_command(mdir, rdir, "s", challenger_scores=rdir / "scores-s-snapB.parquet")
    assert res.promoted is True, res.reason
    last = json.loads((mdir / "registry.json").read_text())["s"]["history"][-1]
    assert last["paired"]["n_rows"] == 120 and last["paired"]["challenger_scores"].endswith("scores-s-snapB.parquet")


# ============================================================================ 6. the card's own cell on the backtest line
def _report_doc() -> dict:
    agg = [
        {"cell": "ALL", "rung": "P2", "brier_skill": 0.0015, "brier_skill_lo": -0.0017, "brier_skill_hi": 0.0047, "n": 13247, "n_tests": 3797,
         "logscore": -0.885, "decidable_by_tests": "decidable at skill 0.20 and 0.10", "gate_base_rate": 0.09},
        {"cell": CELL, "rung": "P2", "brier_skill": -0.0048, "brier_skill_lo": -0.0085, "brier_skill_hi": -0.0016, "n": 7400, "n_tests": 2280,
         "logscore": -0.9, "decidable_by_tests": "decidable at skill 0.20 and 0.10", "gate_base_rate": 0.09},
        {"cell": "both", "rung": "P2", "brier_skill": 0.03, "brier_skill_lo": -0.05, "brier_skill_hi": 0.11, "n": 60, "n_tests": 20,
         "logscore": -1.1, "decidable_by_tests": "undecidable at this n", "gate_base_rate": 0.09},
        {"cell": "ALL", "rung": "P1", "brier_skill": 0.0015, "brier_skill_lo": -0.0018, "brier_skill_hi": 0.0048, "n": 13247, "n_tests": 3797,
         "logscore": -0.881, "decidable_by_tests": "decidable at skill 0.20 and 0.10", "gate_base_rate": 0.09},
    ]
    return {"header": {"snapshot_id": "20261103-aaaaaaaaaaaa"}, "tables": {"aggregate": agg}}


def test_the_backtest_summary_carries_every_cell_of_the_card_rung_with_its_decidability():
    from mootcourt.registry import backtest_summary

    s = backtest_summary(_report_doc(), "backtest-upworthy-20261103-aaaaaaaaaaaa.json")
    assert s["rung"] == "P2" and s["brier_skill"] == 0.0015 and s["n_tests"] == 3797
    assert s["scores"] == "scores-upworthy-20261103-aaaaaaaaaaaa.parquet"
    assert set(s["cells"]) == {CELL, "both"}
    c = s["cells"][CELL]
    assert c["brier_skill"] == -0.0048 and c["brier_skill_lo"] == -0.0085 and c["n_tests"] == 2280
    assert c["decidable_by_tests"] == "decidable at skill 0.20 and 0.10" and s["cells"]["both"]["decidable_by_tests"] == "undecidable at this n"


def test_the_card_prints_its_own_cell_figure_when_decidable_and_the_pooled_one_labelled_otherwise():
    import dataclasses

    from mootcourt import card as card_mod
    from mootcourt.registry import backtest_summary

    old, new, bundle, origin, now0, rows = _split()
    row = rows.iloc[0]
    summary = backtest_summary(_report_doc(), "backtest-synthetic-20261103-aaaaaaaaaaaa.json")
    bundle = dataclasses.replace(bundle, backtest_summary=summary)
    card = _card(bundle, row, now0, now0)
    sec = card_mod.to_markdown(card).split("## Skill at this n")[1].split("## Abstention")[0]
    assert card.skill.backtest["scope"] == "cell" and card.skill.backtest["cell"] == CELL
    assert "for this cell" in sec and "-0.005" in sec and "-0.009 to -0.002" in sec and "2280 tests" in sec
    assert "decidable at skill 0.20 and 0.10" in sec and "below zero" in sec
    assert "0.002 (90 percent interval -0.002 to 0.005)" not in sec, "the pooled figure must not stand in for the cell's own"
    # a cell whose own figure is undecidable gets the pooled figure, said to be pooled, with the reason
    undecidable = json.loads(json.dumps(summary))
    undecidable["cells"][CELL]["decidable_by_tests"] = "undecidable at this n"
    card2 = _card(dataclasses.replace(bundle, backtest_summary=undecidable), row, now0, now0)
    sec2 = card_mod.to_markdown(card2).split("## Skill at this n")[1].split("## Abstention")[0]
    assert card2.skill.backtest["scope"] == "pooled" and "pooled over all cells" in sec2 and "undecidable at this n" in sec2
    assert "0.002 (90 percent interval -0.002 to 0.005) over 3797 tests" in sec2
    # a summary without cells (written before this change) is pooled too, and says why
    bare = {k: v for k, v in summary.items() if k != "cells"}
    card3 = _card(dataclasses.replace(bundle, backtest_summary=bare), row, now0, now0)
    assert card3.skill.backtest["scope"] == "pooled" and "no row for this cell" in card_mod.to_markdown(card3)
