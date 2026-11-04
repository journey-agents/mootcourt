"""T-017 contracts: join, miss typing, reliability, drift."""
import datetime as dt
import json

import pytest

UTC = dt.timezone.utc
NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=UTC)
Z = 1.96


def _t(imp, **kw):
    base = dict(abstained=False, p_sig=0.5, point=1.0, interval90=(-5.0, 5.0), y=1.0, s=1.0)
    base.update(kw)
    return imp("mootcourt.loop").type_miss(**base)


# one test per miss type, plus precedence checks
def test_abstained_but_clear(imp):
    assert _t(imp, abstained=True, y=5.0, s=1.0) == "abstained_but_clear"


def test_abstained_and_not_clear_is_a_hit(imp):
    assert _t(imp, abstained=True, y=1.0, s=1.0) == "hit"


def test_confident_but_wrong_high_p_no_event(imp):
    assert _t(imp, p_sig=0.7, y=1.0, s=1.0) == "confident_but_wrong"


def test_confident_but_wrong_low_p_with_event(imp):
    assert _t(imp, p_sig=0.05, point=-1.0, y=5.0, s=1.0) == "confident_but_wrong"


def test_direction_miss(imp):
    assert _t(imp, p_sig=0.4, point=2.0, y=-3.0, s=1.0, interval90=(-9.0, 9.0)) == "direction_miss"


def test_magnitude_miss(imp):
    assert _t(imp, p_sig=0.4, point=1.0, y=4.0, s=2.0, interval90=(-1.0, 3.0)) == "magnitude_miss"


def test_hit(imp):
    assert _t(imp, p_sig=0.4, point=1.0, y=1.5, s=1.0, interval90=(-3.0, 4.0)) == "hit"


def test_precedence_confident_beats_direction(imp):
    assert _t(imp, p_sig=0.8, point=2.0, y=-3.0, s=1.0) == "confident_but_wrong"


def test_precedence_abstained_beats_everything(imp):
    assert _t(imp, abstained=True, p_sig=0.8, point=2.0, y=-9.0, s=1.0) == "abstained_but_clear"


def test_direction_miss_needs_more_than_one_standard_error(imp):
    assert _t(imp, p_sig=0.4, point=2.0, y=-0.5, s=1.0, interval90=(-9.0, 9.0)) == "hit"


def test_type_miss_rejects_nonpositive_s(imp):
    with pytest.raises(ValueError):
        _t(imp, s=0.0)


# reliability and drift ----------------------------------------------------
def _outcomes(cell, n, delta, when, base_ls=-2.0):
    """delta = model log score minus P0 log score for each outcome."""
    return [{"cell": cell, "at": (when + dt.timedelta(hours=i)).isoformat(), "logscore": base_ls + delta,
             "p0_logscore": base_ls, "brier": 0.2, "p0_brier": 0.21} for i in range(n)]


def test_update_reliability_rolling_window_and_skill(imp):
    loop = imp("mootcourt.loop")
    old = _outcomes("a", 10, -5.0, NOW - dt.timedelta(weeks=9))      # outside the trailing 8 weeks
    new = _outcomes("a", 20, 0.3, NOW - dt.timedelta(days=3))
    rep = loop.update_reliability(None, old + new, NOW, advance=True)
    c = rep["cells"]["a"]
    assert c["n"] == 20 and c["rolling_logscore"] == pytest.approx(-1.7)
    assert c["p0_rolling_logscore"] == pytest.approx(-2.0)
    assert c["brier_skill"] == pytest.approx(1 - 0.2 / 0.21)
    assert c["drifted"] is False and c["consecutive_below"] == 0
    assert rep["as_of"] == NOW.isoformat()


def test_drift_after_two_consecutive_bad_joins_and_clears_later(imp, reliability_factory):
    loop, ab = imp("mootcourt.loop"), imp("mootcourt.abstain")
    t1 = NOW
    good = _outcomes("a", 30, 0.2, t1 - dt.timedelta(days=2))
    r1 = loop.update_reliability(None, good, t1, advance=True)
    assert r1["cells"]["a"]["drifted"] is False
    t2 = t1 + dt.timedelta(days=7)
    bad = _outcomes("a", 30, -0.5, t2 - dt.timedelta(days=2))        # 0.5 nats below P0 > 0.10 threshold
    r2 = loop.update_reliability(r1, good + bad, t2, advance=True)
    assert r2["cells"]["a"]["consecutive_below"] == 1 and r2["cells"]["a"]["drifted"] is False
    t3 = t2 + dt.timedelta(days=7)
    bad2 = _outcomes("a", 60, -0.5, t3 - dt.timedelta(days=2))
    r3 = loop.update_reliability(r2, good + bad + bad2, t3, advance=True)
    assert r3["cells"]["a"]["consecutive_below"] >= 2 and r3["cells"]["a"]["drifted"] is True
    r4 = r3
    assert ab.check_reliability(r4, "a", t3 + dt.timedelta(days=1)) is True
    # a later join with the bad outcomes aged out of the 8-week window and fresh good ones clears it
    t5 = t3 + dt.timedelta(weeks=10)
    fresh = _outcomes("a", 40, 0.2, t5 - dt.timedelta(days=2))
    r5 = loop.update_reliability(r4, good + bad + bad2 + fresh, t5, advance=True)
    assert r5["cells"]["a"]["drifted"] is False and r5["cells"]["a"]["consecutive_below"] == 0
    assert ab.check_reliability(r5, "a", t5) is False


def test_no_new_outcomes_refreshes_as_of_but_not_counters(imp):
    loop = imp("mootcourt.loop")
    bad = _outcomes("a", 30, -0.5, NOW - dt.timedelta(days=2))
    r1 = loop.update_reliability(None, bad, NOW, advance=True)
    later = NOW + dt.timedelta(days=7)
    r2 = loop.update_reliability(r1, bad, later, advance=False)
    assert r2["as_of"] == later.isoformat() and r2["cells"]["a"]["as_of"] == later.isoformat()
    assert r2["cells"]["a"]["consecutive_below"] == r1["cells"]["a"]["consecutive_below"]


# join end to end ------------------------------------------------------------
def _setup(imp, tmp_path, make_synth, reliability_factory):
    ledger_mod, bundle_mod, card_mod = imp("mootcourt.ledger"), imp("mootcourt.bundle"), imp("mootcourt.card")
    full, _ = make_synth(seed=97, n_tests=300, variants_per_test=1)
    cut = full["started_at"].quantile(0.8)
    old, new = full[full["started_at"] < cut], full[full["started_at"] >= cut]
    dirs = {k: tmp_path / k for k in ("ledger", "cards", "reports")}
    for d in dirs.values():
        d.mkdir()
    ledger_mod.write_ledger(old, dirs["ledger"] / "ledger.parquet")
    bundle = bundle_mod.fit_bundle(old, "synthetic", ledger_mod.snapshot_id(old, today=dt.date(2014, 7, 1)))
    origin = old["usable_after"].max().to_pydatetime()
    now0 = origin + dt.timedelta(days=1)
    report = reliability_factory(as_of=now0 - dt.timedelta(days=1), n=500)
    cards = []
    for r in new[new["started_at"] > now0].head(5).itertuples():  # issued before the test starts (call 220)
        req = card_mod.CardRequest(source="synthetic", headline=json.loads(r.features_json)["headline"],
                                   image_changed=False, impressions=20000, origin=origin, row_id=r.row_id)
        c = card_mod.build_card(bundle, req, reliability=report, now=now0)
        card_mod.freeze_card(c, dirs["cards"])
        cards.append(c)
    return dirs, new, cards, now0


def test_join_appends_rows_snapshots_and_writes_outcomes_without_touching_cards(
        imp, tmp_path, make_synth, reliability_factory):
    loop, ledger_mod = imp("mootcourt.loop"), imp("mootcourt.ledger")
    dirs, new, cards, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    before = {p.name: p.read_bytes() for p in dirs["cards"].glob("*.json")}
    res = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"],
                             reports_dir=dirs["reports"], source="synthetic", now=new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1))
    assert res.n_new_rows == len(new) and res.snapshot_id
    assert len(ledger_mod.read_ledger(dirs["ledger"] / "ledger.parquet")) > len(new)
    outcomes = sorted((dirs["cards"] / "outcomes").glob("*.json"))
    assert len(outcomes) == len(cards)
    out = json.loads(outcomes[0].read_text())
    assert out["miss_type"] in {"abstained_but_clear", "confident_but_wrong", "direction_miss", "magnitude_miss", "hit"}
    assert {"card_id", "row_id", "y", "s", "logscore", "p0_logscore"} <= set(out)
    assert {p.name: p.read_bytes() for p in dirs["cards"].glob("*.json")} == before, "card files must never change"
    assert (dirs["reports"] / "reliability-synthetic.json").exists()


def test_join_is_idempotent(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, _, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    kw = dict(ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic", now=now0 + dt.timedelta(days=7))
    loop.join_new_rows(lambda: new, **kw)

    def state():
        return {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    first = state()
    second_res = loop.join_new_rows(lambda: new, **kw)
    assert second_res.n_new_rows == 0
    assert state() == first


def test_join_with_no_new_rows_still_refreshes_as_of(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, _, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    empty = new.iloc[0:0]
    later = now0 + dt.timedelta(days=14)
    loop.join_new_rows(lambda: empty, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                       source="synthetic", now=later)
    rep = json.loads((dirs["reports"] / "reliability-synthetic.json").read_text())
    assert rep["as_of"] == later.isoformat()


def test_stale_reliability_report_makes_cards_abstain(imp, make_synth, reliability_factory):
    card_mod, bundle_mod = imp("mootcourt.card"), imp("mootcourt.bundle")
    ledger, _ = make_synth(seed=98, n_tests=200, variants_per_test=1)
    bundle = bundle_mod.fit_bundle(ledger, "synthetic", "20261102-ffffffffffff")
    origin = ledger["usable_after"].max().to_pydatetime()
    now = origin + dt.timedelta(days=1)
    stale = reliability_factory(as_of=now - dt.timedelta(days=15), n=500)
    req = card_mod.CardRequest(source="synthetic", headline="a plain headline", image_changed=False,
                               impressions=20000, origin=origin)
    c = card_mod.build_card(bundle, req, reliability=stale, now=now)
    assert c.abstention.status == "abstain" and "reliability" in c.abstention.reasons
    drifted = reliability_factory(as_of=now - dt.timedelta(days=1), drifted=True, n=500)
    c2 = card_mod.build_card(bundle, req, reliability=drifted, now=now)
    assert "reliability" in c2.abstention.reasons and "drift" in c2.abstention.details["reliability"].lower()


# T6-plan row 2 (R2 nit 1, call 249): the ledger snapshot that holds the outcome row
def test_the_outcome_names_the_ledger_snapshot_that_holds_its_row(imp, tmp_path, make_synth, reliability_factory):
    loop, ledger_mod = imp("mootcourt.loop"), imp("mootcourt.ledger")
    dirs, new, cards, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    res = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic",
                             now=new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1))
    outcomes = [json.loads(p.read_text()) for p in sorted((dirs["cards"] / "outcomes").glob("*.json"))]
    assert len(outcomes) == len(cards) and res.snapshot_id
    for o in outcomes:
        assert o["ledger_snapshot_id"] == res.snapshot_id and o["snapshot_id"] != o["ledger_snapshot_id"], "the card's own snapshot stays apart"
        held = ledger_mod.read_ledger(dirs["ledger"] / "snapshots" / o["ledger_snapshot_id"] / "ledger.parquet")
        assert o["row_id"] in set(held["row_id"])


def test_an_outcome_attached_by_a_join_that_added_no_rows_names_the_snapshot_of_the_ledger_it_read(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, cards, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    kw = dict(ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic")
    last = new["usable_after"].max().to_pydatetime()
    first = loop.join_new_rows(lambda: new, now=now0 + dt.timedelta(days=1), **kw)         # rows appended, no horizon passed yet
    assert first.n_outcomes == 0 and first.snapshot_id
    later = loop.join_new_rows(lambda: new.iloc[0:0], now=last + dt.timedelta(days=1), **kw)
    assert later.n_new_rows == 0 and later.n_outcomes == len(cards)
    ids = {json.loads(p.read_text())["ledger_snapshot_id"] for p in (dirs["cards"] / "outcomes").glob("*.json")}
    assert ids == {first.snapshot_id}, "the snapshot of the unchanged ledger is reused, not written again"
    assert len(list((dirs["ledger"] / "snapshots").iterdir())) == 1


# T6-plan row 3 (R2 nit 3, call 250): a join that brings outcomes older than the window says so
def _expected_outside(dirs, now):
    import pandas as pd

    limit = pd.Timestamp(now) - pd.Timedelta(weeks=8)
    return sum(1 for p in (dirs["cards"] / "outcomes").glob("*.json") if pd.Timestamp(json.loads(p.read_text())["at"]) <= limit)


def test_a_join_counts_the_outcomes_that_fall_before_the_trailing_window(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, cards, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    late = new["usable_after"].max().to_pydatetime() + dt.timedelta(days=200)
    kw = dict(ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic")
    res = loop.join_new_rows(lambda: new, now=late, **kw)
    assert res.n_outcomes == len(cards) and res.n_outside_window == len(cards) == _expected_outside(dirs, late)


def test_a_join_inside_the_window_counts_none_outside_it(imp, tmp_path, make_synth, reliability_factory):
    import pandas as pd

    loop = imp("mootcourt.loop")
    dirs, new, cards, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    ids = [json.loads(p.read_text())["request"]["row_id"] for p in dirs["cards"].glob("*.json")]
    first_at = new.set_index("row_id").loc[ids, "usable_after"].min()
    res = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic",
                             now=pd.Timestamp(first_at).to_pydatetime() + dt.timedelta(days=1))
    assert res.n_outcomes >= 1 and res.n_outside_window == 0


def test_moot_join_prints_one_line_when_outcomes_predate_the_window(imp, tmp_path, make_synth, reliability_factory):
    from typer.testing import CliRunner

    dirs, new, cards, now0 = _setup(imp, tmp_path, make_synth, reliability_factory)
    rows = tmp_path / "new.parquet"
    imp("mootcourt.ledger").write_ledger(new, rows)
    late = (new["usable_after"].max().to_pydatetime() + dt.timedelta(days=200)).isoformat()
    args = ["join", "--source", "synthetic", "--ledger", str(dirs["ledger"] / "ledger.parquet"), "--cards-dir", str(dirs["cards"]),
            "--reports-dir", str(dirs["reports"]), "--new-rows", str(rows), "--now", late]
    res = CliRunner().invoke(imp("mootcourt.cli").app, args)
    assert res.exit_code == 0, res.output
    lines = [ln for ln in res.output.splitlines() if "trailing 8 weeks" in ln]
    assert len(lines) == 1 and f"{len(cards)} of the {len(cards)} attached outcomes" in lines[0], res.output
    again = CliRunner().invoke(imp("mootcourt.cli").app, args)
    assert "trailing 8 weeks" not in again.output, "a join that attaches nothing says nothing about the window"
