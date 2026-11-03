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
    for r in new.head(5).itertuples():
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
