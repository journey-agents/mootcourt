"""T-027 contracts: an outcome exists only once its registered horizon has passed."""
import datetime as dt
import json

import pandas as pd

UTC = dt.timezone.utc


def _world(imp, tmp_path, make_synth, reliability_factory, n_cards=6):
    ledger_mod, bundle_mod, card_mod = imp("mootcourt.ledger"), imp("mootcourt.bundle"), imp("mootcourt.card")
    full, _ = make_synth(seed=161, n_tests=300, variants_per_test=1)
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
    issued = new[new["started_at"] > now0].head(n_cards)  # issued before the test starts (call 220)
    for r in issued.itertuples():
        req = card_mod.CardRequest(source="synthetic", headline=json.loads(r.features_json)["headline"], image_changed=False,
                                   impressions=20000, origin=origin, row_id=r.row_id)
        card_mod.freeze_card(card_mod.build_card(bundle, req, reliability=report, now=now0), dirs["cards"])
    return dirs, new, issued, now0


def _outcome_ids(dirs):
    return {p.stem for p in (dirs["cards"] / "outcomes").glob("*.json")} if (dirs["cards"] / "outcomes").exists() else set()


def test_row_is_attached_at_the_first_join_at_or_after_its_horizon(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, issued, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    due = sorted(pd.to_datetime(issued["usable_after"], utc=True))
    assert due[0] < due[-1], "the fixture needs cards with different horizons"
    now1 = due[2].to_pydatetime()
    kw = dict(ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"], source="synthetic")
    r1 = loop.join_new_rows(lambda: new, now=now1, **kw)
    n_due1 = int((pd.to_datetime(issued["usable_after"], utc=True) <= now1).sum())
    assert r1.n_outcomes == n_due1 < len(issued)
    first = _outcome_ids(dirs)
    # the join at the horizon itself counts (at or after)
    assert len(first) == n_due1
    now2 = due[-1].to_pydatetime() + dt.timedelta(days=1)
    r2 = loop.join_new_rows(lambda: new.iloc[0:0], now=now2, **kw)
    assert r2.n_outcomes == len(issued) - n_due1
    assert len(_outcome_ids(dirs)) == len(issued) and first <= _outcome_ids(dirs)


def test_join_before_every_horizon_writes_no_outcome_and_no_reliability_entry(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, issued, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    earliest = pd.to_datetime(issued["usable_after"], utc=True).min().to_pydatetime()
    before = earliest - dt.timedelta(seconds=1)
    res = loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                             source="synthetic", now=before)
    assert res.n_new_rows == len(new) and res.n_outcomes == 0
    assert _outcome_ids(dirs) == set()
    report = json.loads(res.reliability_path.read_text())
    assert report["cells"] == {}, "a result before its registered horizon must not reach the reliability report"


def test_reliability_ignores_outcomes_dated_after_now_but_keeps_the_lower_bound(imp):
    rel = imp("mootcourt.reliability")
    now = dt.datetime(2020, 6, 1, tzinfo=UTC)

    def rows(at, n, ls):
        return [{"cell": "c", "at": at, "logscore": ls, "p0_logscore": -2.0, "brier": 0.1, "p0_brier": 0.2} for _ in range(n)]

    good = rows(now - dt.timedelta(days=3), 12, -1.9)
    future_bad = rows(now + dt.timedelta(days=1), 40, -9.0)
    stale = rows(now - dt.timedelta(weeks=9), 40, -9.0)
    rep = rel.build_reliability(None, good + future_bad + stale, now, source="s")
    assert rep["cells"]["c"]["n"] == 12 and abs(rep["cells"]["c"]["rolling_logscore"] + 1.9) < 1e-9
    assert rep["cells"]["c"]["drifted"] is False
    only_future = rel.build_reliability(None, future_bad, now, source="s")
    assert only_future["cells"] == {}
    exactly_now = rel.build_reliability(None, rows(now, 10, -1.9), now, source="s")
    assert exactly_now["cells"]["c"]["n"] == 10, "an outcome dated exactly now is known"


def test_future_outcomes_cannot_trigger_drift(imp):
    rel = imp("mootcourt.reliability")
    now = dt.datetime(2020, 6, 1, tzinfo=UTC)
    bad_future = [{"cell": "c", "at": now + dt.timedelta(days=2), "logscore": -9.0, "p0_logscore": -2.0, "brier": 0.5, "p0_brier": 0.2}] * 30
    rep = None
    for k in range(3):
        rep = rel.build_reliability(rep, bad_future, now + dt.timedelta(days=k * 0), source="s")
    assert not rep["cells"]


def test_method_doc_records_the_horizon_rule():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "docs" / "method.md").read_text().lower()
    assert "an outcome exists only once its registered horizon has passed" in text
