"""Extra checks for the operational loop (builder additions)."""
import datetime as dt
import json
import os
import stat

import numpy as np


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
    for r in new.head(n_cards).itertuples():
        req = card_mod.CardRequest(source="synthetic", headline=json.loads(r.features_json)["headline"], image_changed=False,
                                   impressions=20000, origin=origin, row_id=r.row_id)
        card_mod.freeze_card(card_mod.build_card(bundle, req, reliability=report, now=now0), dirs["cards"])
    return dirs, new, now0


def test_outcome_files_are_read_only_hold_scores_and_match_the_ledger_row(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, new, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                       source="synthetic", now=new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1))
    ledger = new.set_index("row_id")
    for p in (dirs["cards"] / "outcomes").glob("*.json"):
        assert not os.stat(p).st_mode & stat.S_IWUSR
        o = json.loads(p.read_text())
        assert o["y"] == ledger.loc[o["row_id"], "y"] and o["s"] == ledger.loc[o["row_id"], "s"]
        assert np.isfinite(o["p0_logscore"])
        # round 00 (T-054, call 163): an abstained card is scored on the forecast it withheld, so only a card with no forecast at all has no score
        assert (o["logscore"] is None) == (o["scored_forecast"] is None)
        assert o["scored_forecast"] == ("withheld" if o["abstained"] else "issued")
        assert o["event"] == (o["y"] > 1.96 * o["s"])


def test_default_join_command_appends_nothing_and_changes_only_the_report(imp, tmp_path, make_synth, reliability_factory):
    loop = imp("mootcourt.loop")
    dirs, _, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    before = (dirs["ledger"] / "ledger.parquet").read_bytes()
    res = loop.join_command("synthetic", dirs["ledger"], dirs["cards"], dirs["reports"], now=now0)
    assert res.n_new_rows == 0 and res.n_outcomes == 0 and res.snapshot_id is None
    assert (dirs["ledger"] / "ledger.parquet").read_bytes() == before
    assert json.loads(res.reliability_path.read_text())["as_of"] == now0.isoformat()


def test_join_with_a_stream_file_appends_rows(imp, tmp_path, make_synth, reliability_factory):
    loop, ledger_mod = imp("mootcourt.loop"), imp("mootcourt.ledger")
    dirs, new, now0 = _world(imp, tmp_path, make_synth, reliability_factory)
    stream = tmp_path / "stream.parquet"
    ledger_mod.write_ledger(new, stream)
    res = loop.join_command("synthetic", dirs["ledger"], dirs["cards"], dirs["reports"], new_rows_path=stream,
                            now=new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1))
    assert res.n_new_rows == len(new) and res.snapshot_id and res.n_outcomes == 6
    assert sum(res.miss_counts.values()) == 6 and set(res.miss_counts) <= set(loop.MISS_TYPES)
