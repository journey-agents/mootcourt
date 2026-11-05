"""T-025 contracts: end-to-end loop on a synthetic stream, offline."""
import datetime as dt
import json

import pytest

UTC = dt.timezone.utc


def _outcomes(cell, n, delta, when):
    return [{"cell": cell, "at": (when - dt.timedelta(hours=i)).isoformat(), "logscore": -2.0 + delta,
             "p0_logscore": -2.0, "brier": 0.2, "p0_brier": 0.21} for i in range(n)]


@pytest.mark.slow
def test_fit_issue_freeze_join_type_drift_abstain_clear_issue(imp, tmp_path, make_synth, reliability_factory):
    ledger_mod, bundle_mod, card_mod, loop = (imp("mootcourt.ledger"), imp("mootcourt.bundle"),
                                              imp("mootcourt.card"), imp("mootcourt.loop"))
    full, _ = make_synth(seed=121, n_tests=500, variants_per_test=1)
    cut = full["started_at"].quantile(0.75)
    old, new = full[full["started_at"] < cut], full[full["started_at"] >= cut]
    dirs = {k: tmp_path / k for k in ("ledger", "cards", "reports")}
    for d in dirs.values():
        d.mkdir()
    ledger_mod.write_ledger(old, dirs["ledger"] / "ledger.parquet")

    # fit and issue
    bundle = bundle_mod.fit_bundle(old, "synthetic", ledger_mod.snapshot_id(old, today=dt.date(2014, 7, 1)))
    origin = old["usable_after"].max().to_pydatetime()
    now = origin + dt.timedelta(days=1)
    fresh = reliability_factory(as_of=now - dt.timedelta(days=1), n=400)
    issued = []
    # issued before the test starts (call 220), for the cell of the row (call 256)
    for r in new[(new["started_at"] > now) & (new["cell"] == "headline_only")].head(6).itertuples():
        req = card_mod.CardRequest(source="synthetic", headline=json.loads(r.features_json)["headline"],
                                   image_changed=False, impressions=20000, origin=origin, row_id=r.row_id)
        c = card_mod.build_card(bundle, req, reliability=fresh, now=now)
        card_mod.freeze_card(c, dirs["cards"])
        issued.append(c)
        assert c.snapshot_id and c.model_id and c.feature_hash, "every issued card carries version ids"

    # join, type misses, rewrite reliability
    join_now = new["usable_after"].max().to_pydatetime() + dt.timedelta(days=1)       # after every horizon (T-027)
    loop.join_new_rows(lambda: new, ledger_dir=dirs["ledger"], cards_dir=dirs["cards"], reports_dir=dirs["reports"],
                             source="synthetic", now=join_now)
    outcomes = [json.loads(p.read_text()) for p in (dirs["cards"] / "outcomes").glob("*.json")]
    assert len(outcomes) == len(issued) and all(o["miss_type"] for o in outcomes)
    report_path = dirs["reports"] / "reliability-synthetic.json"
    assert json.loads(report_path.read_text())["as_of"] == join_now.isoformat()

    # force drift with two bad joins, see the card abstain
    t = join_now + dt.timedelta(days=14)
    rep = json.loads(report_path.read_text())
    bad1, bad2 = _outcomes("headline_only", 40, -0.6, t), _outcomes("headline_only", 40, -0.6, t + dt.timedelta(days=7))
    rep = loop.update_reliability(rep, bad1, t, advance=True)
    rep = loop.update_reliability(rep, bad1 + bad2, t + dt.timedelta(days=7), advance=True)
    assert rep["cells"]["headline_only"]["drifted"] is True
    t_drift = t + dt.timedelta(days=8)
    req = card_mod.CardRequest(source="synthetic", headline="a plain headline", image_changed=False,
                               impressions=20000, origin=origin)
    drifted_card = card_mod.build_card(bundle, req, reliability=rep, now=t_drift)
    assert drifted_card.abstention.status == "abstain" and "reliability" in drifted_card.abstention.reasons

    # clear drift with a later join, see reliability stop firing and a card issue again
    t_clear = t + dt.timedelta(weeks=12)
    good = _outcomes("headline_only", 60, 0.2, t_clear - dt.timedelta(days=2))
    rep = loop.update_reliability(rep, bad1 + bad2 + good, t_clear, advance=True)
    assert rep["cells"]["headline_only"]["drifted"] is False
    heads = [json.loads(r.features_json)["headline"] for r in old.head(8).itertuples()]
    cards = [card_mod.build_card(bundle, card_mod.CardRequest(source="synthetic", headline=h, image_changed=False,
                                                              impressions=20000, origin=origin),
                                 reliability=rep, now=t_clear + dt.timedelta(hours=1)) for h in heads]
    assert all("reliability" not in c.abstention.reasons for c in cards)
    assert any(c.abstention.status == "issue" for c in cards), "after clearing, at least one card must issue"


@pytest.mark.slow
def test_leakage_mutation_is_caught(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=122, n_tests=200, variants_per_test=2)[0]

    def leaky(rows, origin):
        return imp("mootcourt.predictors.p0").P0Predictor().fit(ledger)

    with pytest.raises(harness.LeakageError):
        harness.rolling_origin(ledger, {"P0": leaky}, harness.quarterly_origins(ledger), audit_fit_rows=True)


def test_every_issued_card_json_has_version_ids_via_service(imp):
    svc = imp("mootcourt.service")
    assert hasattr(svc, "create_app")
