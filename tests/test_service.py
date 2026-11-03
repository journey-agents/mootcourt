"""T-018 contracts: HTTP service (FastAPI), read-only apart from freezing a card."""
import datetime as dt
import json

import pytest

NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def served(imp, tmp_path, make_synth, reliability_factory):
    """A saved champion bundle, a fresh reliability report and an app over them."""
    ledger, _ = make_synth(seed=101, n_tests=300, variants_per_test=2)
    bm, reg = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-111111111111", as_of=NOW)
    bm.save_bundle(bundle, models)
    reg.Registry(models).register_model("synthetic", bundle.model_id)
    report = reliability_factory(as_of=NOW - dt.timedelta(days=1), n=500)
    (reports / "reliability-synthetic.json").write_text(json.dumps(report))
    app = imp("mootcourt.service").create_app(models, cards, reports_dir=reports, now=lambda: NOW)
    from fastapi.testclient import TestClient
    return TestClient(app), bundle, cards, reports, ledger


PAYLOAD = {"source": "synthetic", "headline": "you will not believe what happened next",
           "image_changed": False, "impressions": 20000}


def test_health_is_ok(served):
    client = served[0]
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_post_card_returns_card_json_with_ids_and_boundary(served, spec_boundary_sentence):
    client, bundle, *_ = served
    r = client.post("/card", json=PAYLOAD)
    assert r.status_code == 200
    j = r.json()
    assert j["snapshot_id"] == bundle.snapshot_id and j["model_id"] == bundle.model_id
    assert j["feature_hash"] == bundle.feature_hash and j["issued_at"] and j["footer"] == spec_boundary_sentence


def test_post_card_freezes_exactly_one_file(served):
    client, _, cards, *_ = served
    client.post("/card", json=PAYLOAD)
    files = list(cards.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["card_id"]


def test_same_request_via_cli_and_service_gives_identical_json(served, imp, tmp_path):
    from typer.testing import CliRunner

    client, bundle, cards, reports, ledger = served
    svc = client.post("/card", json=PAYLOAD).json()
    cli_cards = tmp_path / "cli_cards"
    cli_cards.mkdir()
    res = CliRunner().invoke(imp("mootcourt.cli").app, [
        "card", "--source", "synthetic", "--headline", PAYLOAD["headline"], "--image-changed", "false",
        "--impressions", "20000", "--json", "--models-dir", str(tmp_path / "models"), "--cards-dir", str(cli_cards),
        "--reports-dir", str(reports), "--now", NOW.isoformat()])
    assert res.exit_code == 0, res.output
    cli = json.loads(res.output)
    for j in (svc, cli):
        j.pop("issued_at", None)
        j.pop("card_id", None)
    assert svc == cli


def test_invalid_payload_is_422_and_unknown_source_is_404(served):
    client = served[0]
    assert client.post("/card", json={"source": "synthetic"}).status_code == 422
    r = client.get("/reliability/nosuchsource")
    assert r.status_code == 404 and "error" in r.json()
    assert client.post("/card", json={**PAYLOAD, "source": "nosuchsource"}).status_code == 404


def test_reliability_endpoint_returns_the_report(served):
    client, *_, reports, _ = served
    r = client.get("/reliability/synthetic")
    assert r.status_code == 200 and r.json() == json.loads((reports / "reliability-synthetic.json").read_text())


def test_routes_are_read_only_apart_from_post_card(served):
    client = served[0]
    seen = set()
    for route in client.app.routes:
        if route.path.startswith(("/docs", "/redoc", "/openapi")):
            continue
        for m in route.methods - {"HEAD", "OPTIONS"}:
            seen.add((m, route.path))
    assert seen == {("GET", "/health"), ("GET", "/reliability/{source}"), ("POST", "/card")}


def test_get_endpoints_do_not_write(served):
    client, _, cards, reports, _ = served
    before = sorted(p.name for p in cards.iterdir())
    client.get("/health"), client.get("/reliability/synthetic")
    assert sorted(p.name for p in cards.iterdir()) == before


def test_preloaded_bundle_keeps_latency_under_one_second(served):
    import time
    client = served[0]
    client.post("/card", json=PAYLOAD)
    t = time.perf_counter()
    client.post("/card", json={**PAYLOAD, "headline": "another plain headline"})
    assert time.perf_counter() - t < 1.0


def test_serve_binds_loopback_by_default(imp):
    cli = imp("mootcourt.cli")
    assert cli.DEFAULT_SERVE_HOST == "127.0.0.1"
