"""T-018 contracts: read-only MCP server over stdio."""
import asyncio
import datetime as dt
import json
import sys

import pytest

NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def dirs(imp, tmp_path, make_synth, reliability_factory):
    ledger, _ = make_synth(seed=102, n_tests=300, variants_per_test=2)
    bm, reg = imp("mootcourt.bundle"), imp("mootcourt.registry")
    models, cards, reports = tmp_path / "models", tmp_path / "cards", tmp_path / "reports"
    for d in (models, cards, reports):
        d.mkdir()
    bundle = bm.fit_bundle(ledger, "synthetic", "20261102-222222222222", as_of=NOW)
    bm.save_bundle(bundle, models)
    reg.Registry(models).register_model("synthetic", bundle.model_id)
    (reports / "reliability-synthetic.json").write_text(json.dumps(reliability_factory(as_of=NOW - dt.timedelta(days=1), n=500)))
    return models, cards, reports


def _run(coro_fn, dirs):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    models, cards, reports = dirs
    params = StdioServerParameters(command=sys.executable, args=[
        "-m", "mootcourt.mcp_server", "--models-dir", str(models), "--cards-dir", str(cards),
        "--reports-dir", str(reports), "--now", NOW.isoformat()])

    async def main():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await coro_fn(session)

    return asyncio.run(asyncio.wait_for(main(), timeout=120))


def test_tools_list_is_exactly_the_three_read_only_tools(imp, dirs):
    imp("mootcourt.mcp_server")

    async def go(session):
        return sorted(t.name for t in (await session.list_tools()).tools)

    assert _run(go, dirs) == ["get_card", "list_precedents", "reliability_report"]


def test_each_tool_returns_valid_content_and_nothing_is_written(imp, dirs):
    imp("mootcourt.mcp_server")
    models, cards, reports = dirs
    before = sorted(p.name for p in cards.iterdir())

    async def go(session):
        card = await session.call_tool("get_card", {"source": "synthetic", "headline": "a plain headline",
                                                    "image_changed": False, "impressions": 20000})
        prec = await session.call_tool("list_precedents", {"source": "synthetic", "headline": "a plain headline",
                                                           "image_changed": False, "k": 3})
        rel = await session.call_tool("reliability_report", {"source": "synthetic"})
        return [json.loads(r.content[0].text) for r in (card, prec, rel)]

    card, prec, rel = _run(go, dirs)
    assert {"snapshot_id", "model_id", "feature_hash", "footer"} <= set(card)
    assert len(prec) == 3 and {"row_id", "weight", "y", "s"} <= set(prec[0])
    assert prec == sorted(prec, key=lambda r: -r["weight"])
    assert "cells" in rel
    assert sorted(p.name for p in cards.iterdir()) == before, "MCP tools must not write cards"


def test_unknown_source_is_a_tool_error_not_a_crash(imp, dirs):
    imp("mootcourt.mcp_server")

    async def go(session):
        return await session.call_tool("reliability_report", {"source": "nosuchsource"})

    res = _run(go, dirs)
    # mcp 1.x spells the flag isError, mcp 2.x spells it is_error; the assertion is the same
    assert (getattr(res, "isError", None) or getattr(res, "is_error", None)) is True
