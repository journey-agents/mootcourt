"""T-040 contracts: several metrics per contrast, guardrails on the card, one report block per metric."""
import datetime as dt
import json

import pandas as pd
import pytest
from typer.testing import CliRunner

UTC = dt.timezone.utc
NOW = dt.datetime(2025, 12, 30, tzinfo=UTC)
METRICS = ["checkout_conversion", "pages_per_session", "revenue_per_user"]


@pytest.fixture(scope="module")
def ledger(tmp_path_factory):
    import importlib

    from mootcourt.importers.sample import sample_exchange
    tmp = tmp_path_factory.mktemp("mm")
    csv = tmp / "s.csv"
    sample_exchange().to_csv(csv, index=False)
    path = tmp / "l.parquet"
    res = CliRunner().invoke(importlib.import_module("mootcourt.cli").app,
                             ["ingest", "--format", "generic", "--input", str(csv), "--source-name", "sample", "--ledger", str(path)])
    assert res.exit_code == 0, res.output
    return importlib.import_module("mootcourt.ledger").read_ledger(path)


@pytest.fixture(scope="module")
def bundle(ledger):
    import importlib

    return importlib.import_module("mootcourt.bundle").fit_bundle(ledger, "sample", "20261103-aaaaaaaaaaaa")


def _report(cells=METRICS, as_of=NOW - dt.timedelta(days=1)):
    return {"source": "sample", "as_of": as_of.isoformat(),
            "cells": {c: {"as_of": as_of.isoformat(), "rolling_logscore": 1.0, "p0_rolling_logscore": 0.9, "brier_skill": 0.05, "n": 60,
                          "drifted": False, "consecutive_below": 0} for c in cells}}


def _request(imp, **kw):
    card = imp("mootcourt.card")
    base = dict(source="sample", headline="", image_changed=False, impressions=20000, origin=NOW, cell="checkout_conversion")
    base.update(kw)
    return card.CardRequest(**base)


# ---------------------------------------------------------------- the ledger
def test_metric_is_part_of_the_row_key_and_the_single_metric_path_is_unchanged(imp, ledger):
    assert ledger["row_id"].is_unique and ledger["test_id"].nunique() == 120 and len(ledger) == 360
    one = ledger[ledger["test_id"] == "exp-001"]
    assert sorted(one["variant_id"]) == [f"treatment::{m}" for m in METRICS] and set(one["cell"]) == set(METRICS)
    assert {imp("mootcourt.ledger").metric_of(j) for j in one["features_json"]} == set(METRICS)
    assert imp("mootcourt.ledger").metric_of('{"headline": "x"}') == "" and imp("mootcourt.ledger").metric_of("not json") == ""


def test_the_cell_key_may_include_the_metric_and_more(imp, tmp_path):
    from mootcourt.importers.sample import sample_exchange
    ex = sample_exchange().iloc[:6].assign(cell=lambda d: "area_x/" + d["metric_id"])
    led = imp("mootcourt.importers.exchange").to_ledger(ex.astype(str), "s", now=NOW)
    assert set(led["cell"]) == {f"area_x/{m}" for m in METRICS}


def test_single_metric_loaders_are_unchanged(imp, make_synth):
    led = make_synth(seed=3, n_tests=30, variants_per_test=2)[0]
    assert all(imp("mootcourt.ledger").metric_of(j) == "" for j in led["features_json"])


# ---------------------------------------------------------------- the harness and the report
def _scores(imp, ledger):
    harness = imp("mootcourt.harness")
    rungs = {k: v for k, v in harness.default_rungs("sample", ledger).items() if k in ("P0", "P1", "P2")}
    return harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger), source="sample")


def test_the_score_table_names_the_metric_and_each_metric_has_its_block(imp, ledger):
    sc = _scores(imp, ledger)
    assert set(sc["metric"]) == set(METRICS)
    doc = json.loads(json.dumps(imp("mootcourt.report").build_document(
        sc, ledger=ledger, source="sample", snapshot_id="20261103-aaaaaaaaaaaa", model_id="m", feature_hash="f", command="c", seed=0,
        gates={"n_200": 175, "n_400": 375}, B=40)))
    blocks = {b["metric"]: b for b in doc["tables"]["by_metric"]}
    assert set(blocks) == set(METRICS) and doc["header"]["metrics"] == METRICS
    assert sum(1 for b in blocks.values() if b["primary"]) == 1 and doc["header"]["primary_metric"] in METRICS
    total = sc[sc["rung"] == "P2"]["row_id"].nunique()
    assert sum(b["n_rows"] for b in blocks.values()) == total
    for m, b in blocks.items():
        want = sc[(sc["rung"] == "P1") & (sc["metric"] == m)]["logscore"].mean()
        got = next(r for r in b["aggregate"] if r["cell"] == "ALL" and r["rung"] == "P1")["logscore"]
        assert got == pytest.approx(want)


def test_decision_value_uses_the_primary_metric_only(imp, ledger):
    sc = _scores(imp, ledger)
    kw = dict(ledger=ledger, source="sample", snapshot_id="20261103-aaaaaaaaaaaa", model_id="m", feature_hash="f", command="c", seed=0,
              gates={"n_200": 175, "n_400": 375}, B=30)
    rep = imp("mootcourt.report")
    a = rep.build_document(sc, primary_metric="revenue_per_user", **kw)
    b = rep.build_document(sc, primary_metric="pages_per_session", **kw)
    assert a["header"]["primary_metric"] == "revenue_per_user"
    only = sc[sc["metric"] == "revenue_per_user"]
    want = imp("mootcourt.decision_value").decision_value(only, ledger, seed=0)
    got = pd.DataFrame(a["tables"]["decision_value"])
    assert got["n_tests"].sum() == want["n_tests"].sum() and a["tables"]["decision_value"] != b["tables"]["decision_value"]
    with pytest.raises(ValueError, match="primary metric"):
        rep.build_document(sc, primary_metric="nope", **kw)


def test_markdown_has_one_block_per_metric_and_a_single_metric_report_is_unchanged(imp, ledger, make_synth):
    rep, harness = imp("mootcourt.report"), imp("mootcourt.harness")
    sc = _scores(imp, ledger)
    doc = json.loads(json.dumps(rep.build_document(sc, ledger=ledger, source="sample", snapshot_id="20261103-aaaaaaaaaaaa", model_id="m",
                                                   feature_hash="f", command="c", seed=0, gates={"n_200": 175, "n_400": 375}, B=30)))
    md = rep.render_markdown(doc)
    for m in METRICS:
        assert f"### Metric {m}" in md
    assert md.count("(primary)") == 1
    syn = make_synth(seed=141, n_tests=120, variants_per_test=2)[0]
    rungs = {k: v for k, v in harness.default_rungs("synthetic").items() if k in ("P0", "P1")}
    ssc = harness.rolling_origin(syn, rungs, harness.quarterly_origins(syn))
    assert "metric" not in ssc.columns
    sdoc = json.loads(json.dumps(rep.build_document(ssc, ledger=syn, source="synthetic", snapshot_id="20261103-bbbbbbbbbbbb", model_id="m",
                                                    feature_hash="f", command="c", seed=0, gates={"n_200": 175, "n_400": 375}, B=30)))
    assert "by_metric" not in sdoc["tables"] and "metrics" not in sdoc["header"] and "## Metrics" not in rep.render_markdown(sdoc)


# ---------------------------------------------------------------- the card
def test_guardrails_show_p_harm_from_the_same_ladder(imp, bundle):
    card = imp("mootcourt.card")
    g = (card.Guardrail("revenue_per_user", 0.02), card.Guardrail("pages_per_session", 0.01))
    c = card.build_card(bundle, _request(imp, guardrails=g), reliability=_report(), now=NOW)
    assert [v.cell for v in c.guardrails] == ["revenue_per_user", "pages_per_session"]
    for v in c.guardrails:
        assert v.status == "issue" and 0.0 <= v.p_harm <= 1.0 and v.n_cell == 120 and v.interval_90[0] < v.interval_90[1]
    v = c.guardrails[0]
    # recompute by hand from the same predictive
    s_star = bundle.s_star("revenue_per_user", 20000)
    x = bundle.transform_text("", False, cell="revenue_per_user", exposure=20000)
    st = bundle.neighbor_state(x, "revenue_per_user", NOW)
    main = bundle.p2.predictive_from_state(st, x, s_star, "revenue_per_user", NOW)
    assert v.p_harm == pytest.approx(1.0 - main.prob_gt(-0.02))
    j = card.to_json(c)
    assert [g_["cell"] for g_ in j["guardrails"]] == ["revenue_per_user", "pages_per_session"]
    assert j["guardrails"][0]["p_harm"] == pytest.approx(v.p_harm)
    md = card.to_markdown(c)
    assert "## Guardrails" in md and "revenue_per_user: P(true effect below -0.02)" in md


def test_p_harm_falls_as_the_margin_grows(imp, bundle):
    card = imp("mootcourt.card")
    ps = []
    for delta in (0.005, 0.02, 0.08):
        c = card.build_card(bundle, _request(imp, guardrails=(card.Guardrail("revenue_per_user", delta),)), reliability=_report(), now=NOW)
        ps.append(c.guardrails[0].p_harm)
    assert ps[0] > ps[1] > ps[2]


def test_a_guardrail_abstains_on_its_own_and_hides_its_number(imp, bundle):
    card = imp("mootcourt.card")
    rel = _report(cells=["checkout_conversion", "pages_per_session"])         # no reliability entry for revenue_per_user
    c = card.build_card(bundle, _request(imp, guardrails=(card.Guardrail("revenue_per_user", 0.02), card.Guardrail("pages_per_session", 0.02),
                                                          card.Guardrail("not_a_metric", 0.02))), reliability=rel, now=NOW)
    by = {v.cell: v for v in c.guardrails}
    assert c.abstention.status == "issue"                                       # the primary metric is fine
    assert by["pages_per_session"].status == "issue"
    assert by["revenue_per_user"].status == "abstain" and "reliability" in by["revenue_per_user"].reasons and by["revenue_per_user"].p_harm is None
    assert by["not_a_metric"].status == "abstain" and "support" in by["not_a_metric"].reasons
    md = card.to_markdown(c)
    assert "revenue_per_user: abstained, no p_harm is shown." in md and "Reason reliability" in md
    j = card.to_json(c)["guardrails"]
    assert next(x for x in j if x["cell"] == "revenue_per_user")["p_harm"] is None


def test_card_without_guardrails_is_byte_identical_to_before(imp, bundle):
    card = imp("mootcourt.card")
    plain = card.build_card(bundle, _request(imp), reliability=_report(), now=NOW)
    assert "guardrails" not in card.to_json(plain) and "## Guardrails" not in card.to_markdown(plain)
    with_g = card.build_card(bundle, _request(imp, guardrails=(card.Guardrail("revenue_per_user", 0.02),)), reliability=_report(), now=NOW)
    assert with_g.card_id != plain.card_id and with_g.prediction == plain.prediction and with_g.robustness == plain.robustness


def test_invalid_guardrails_are_refused(imp, bundle):
    card = imp("mootcourt.card")
    for g, msg in ((card.Guardrail("revenue_per_user", 0.0), "above zero"), (card.Guardrail("checkout_conversion", 0.1), "appears once"),):
        with pytest.raises(ValueError, match=msg):
            card.build_card(bundle, _request(imp, guardrails=(g,)), reliability=_report(), now=NOW)
    with pytest.raises(ValueError, match="appears once"):
        card.build_card(bundle, _request(imp, guardrails=(card.Guardrail("revenue_per_user", 0.1), card.Guardrail("revenue_per_user", 0.2))),
                        reliability=_report(), now=NOW)


def test_cli_guardrail_option(imp, tmp_path, monkeypatch):
    app = imp("mootcourt.cli").app
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    r = CliRunner()
    for args in (["init"], ["ingest", "--format", "generic", "--input", "mootcourt-data/data/sample-ledger.csv", "--source-name", "sample"],
                 ["fit", "--source", "sample"], ["backtest", "--source", "sample"]):
        assert r.invoke(app, args).exit_code == 0
    base = ["card", "--source", "sample", "--cell", "checkout_conversion", "--impressions", "20000", "--now", "2025-12-30T00:00:00+00:00"]
    res = r.invoke(app, base + ["--guardrail", "revenue_per_user:0.02", "--guardrail", "pages_per_session:0.01"])
    assert res.exit_code == 0, res.output
    assert "## Guardrails" in res.output and "pages_per_session: P(true effect below -0.01)" in res.output
    bad = r.invoke(app, base + ["--guardrail", "revenue_per_user"])
    assert bad.exit_code != 0 and "CELL:DELTA" in bad.output


def test_service_accepts_guardrails(imp, bundle):
    svc = imp("mootcourt.service")
    p = svc.CardPayload(source="sample", headline="x", image_changed=False, impressions=100, cell="a",
                        guardrails=[{"cell": "b", "delta": 0.1}])
    assert p.guardrails[0].cell == "b"
    with pytest.raises(ValueError):
        svc.CardPayload(source="sample", headline="x", image_changed=False, impressions=100, guardrails=[{"cell": "b", "delta": 0}])
