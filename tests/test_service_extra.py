"""Extra checks for the service and the MCP tool functions (builder additions)."""
import datetime as dt
import json

import pytest

NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=dt.timezone.utc)
PAYLOAD = {"source": "synthetic", "headline": "you will not believe what happened next", "image_changed": False, "impressions": 20000}


@pytest.fixture
def world(imp, tmp_path, make_synth, reliability_factory):
    ledger, _ = make_synth(seed=171, n_tests=300, variants_per_test=2)
    bm, reg = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-444444444444", as_of=NOW)
    bm.save_bundle(bundle, models)
    reg.Registry(models).register_model("synthetic", bundle.model_id)
    (reports / "reliability-synthetic.json").write_text(json.dumps(reliability_factory(as_of=NOW - dt.timedelta(days=1), n=500)))
    return models, cards, reports


def test_team_forecast_in_the_payload_is_frozen_with_the_card(imp, world):
    from fastapi.testclient import TestClient

    models, cards, reports = world
    client = TestClient(imp("mootcourt.service").create_app(models, cards, reports_dir=reports, now=lambda: NOW))
    j = client.post("/card", json={**PAYLOAD, "team_forecast": {"p_win_team": 0.7, "point_team": 1.5}}).json()
    assert j["team_forecast"]["p_win_team"] == 0.7 and j["team_forecast"]["frozen_at"] == NOW.isoformat()
    assert client.post("/card", json={**PAYLOAD, "team_forecast": {"p_win_team": 1.7, "point_team": 1.0}}).status_code == 422
    assert client.post("/card", json={**PAYLOAD, "impressions": 0}).status_code == 422


def test_known_source_without_a_report_is_404_with_a_hint(imp, world):
    from fastapi.testclient import TestClient

    models, cards, reports = world
    (reports / "reliability-synthetic.json").unlink()
    client = TestClient(imp("mootcourt.service").create_app(models, cards, reports_dir=reports, now=lambda: NOW))
    r = client.get("/reliability/synthetic")
    assert r.status_code == 404 and "moot backtest" in r.json()["error"]


def test_a_service_card_with_no_report_abstains_for_reliability(imp, world):
    from fastapi.testclient import TestClient

    models, cards, reports = world
    (reports / "reliability-synthetic.json").unlink()
    client = TestClient(imp("mootcourt.service").create_app(models, cards, reports_dir=reports, now=lambda: NOW))
    j = client.post("/card", json=PAYLOAD).json()
    assert j["abstention"]["status"] == "abstain" and "reliability" in j["abstention"]["reasons"]


def test_mcp_tool_functions_write_nothing_and_return_json(imp, world):
    models, cards, reports = world
    mcp_server, service = imp("mootcourt.mcp_server"), imp("mootcourt.service")
    state = service.ServingState(models, reports, lambda: NOW)
    card = json.loads(mcp_server.tool_get_card(state, "synthetic", "a plain headline", False, 20000))
    prec = json.loads(mcp_server.tool_list_precedents(state, "synthetic", "a plain headline", False, k=4))
    assert card["footer"] and len(prec) == 4 and list(cards.iterdir()) == []
    with pytest.raises(ValueError):
        mcp_server.tool_list_precedents(state, "synthetic", "x", False, k=0)
    with pytest.raises(service.UnknownSourceError):
        mcp_server.tool_get_card(state, "nope", "x", False, 100)
