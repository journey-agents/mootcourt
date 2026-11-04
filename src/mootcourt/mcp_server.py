"""MCP server over stdio: three read-only tools, ``get_card``, ``list_precedents`` and ``reliability_report``.

Read and propose only: ``get_card`` issues a card but never freezes it, so no tool writes anything and a test
checks the cards directory is unchanged. The bundles are loaded once at startup. Every tool returns a JSON
string in one text content item; an unknown source raises, which the SDK reports as a tool error.

Run with ``python -m mootcourt.mcp_server`` (or ``moot mcp``). ``--cards-dir`` is accepted for symmetry with
``moot serve`` and is never written. The SDK is imported lazily and both its 2.x server class (``MCPServer``)
and the 1.x one (``FastMCP``) are supported.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from mootcourt import card as card_mod
from mootcourt.config import BOUNDARY_SENTENCE
from mootcourt.service import ServingState
from mootcourt.storage import storage_paths

TOOL_NAMES = ("get_card", "list_precedents", "reliability_report")


def _parse_origin(value: str | None) -> dt.datetime | None:
    if value is None:
        return None
    t = dt.datetime.fromisoformat(value)
    if t.tzinfo is None:
        raise ValueError("origin needs a UTC offset, for example 2014-07-15T12:00:00+00:00")
    return t


def tool_get_card(state: ServingState, source: str, headline: str, image_changed: bool, impressions: int, origin: str | None = None,
                  cell: str | None = None, headline_changed: bool = True, row_id: str | None = None, test_id: str | None = None,
                  variant_id: str | None = None, reference_headline: str = "", impressions_variant: int | None = None) -> str:
    """Issue a card without freezing it and return its JSON (without the sealed forecast of an abstained card).

    ``row_id`` (or ``test_id`` with ``variant_id``) names the ledger row a frozen copy of this card would be joined to; the tool never freezes,
    so it only echoes the key, and the same key on ``moot card`` or ``POST /card`` freezes the card the weekly join can score.
    """
    issued = state.issue({"source": source, "headline": headline, "image_changed": image_changed, "impressions": impressions,
                          "origin": _parse_origin(origin), "cell": cell, "headline_changed": headline_changed, "row_id": row_id,
                          "test_id": test_id, "variant_id": variant_id, "reference_headline": reference_headline,
                          "impressions_variant": impressions_variant})
    return json.dumps(card_mod.public_json(card_mod.to_json(issued)), sort_keys=True)


def tool_list_precedents(state: ServingState, source: str, headline: str, image_changed: bool, k: int = 5, origin: str | None = None,
                         cell: str | None = None, headline_changed: bool = True, reference_headline: str = "") -> str:
    """The ``k`` highest-weight precedents for a proposed headline, sorted by weight descending, as a JSON list."""
    if k < 1:
        raise ValueError("k must be at least 1")
    bundle = state.bundle(source)
    at = _parse_origin(origin) or state.now()
    bundle.check_origin(at)                # an origin before the fit cutoff would use parameters fitted on later rows
    cell = cell or card_mod.derive_cell(source, image_changed, headline_changed)
    x = bundle.transform_text(headline, image_changed, cell=cell, reference=reference_headline or None)
    table = bundle.p2.top_precedents(x, cell, at, k)
    return json.dumps(table.to_dict(orient="records"))


def tool_reliability_report(state: ServingState, source: str) -> str:
    """The current reliability report of a source as JSON."""
    state.bundle(source)
    report = state.reliability(source)
    if report is None:
        raise ValueError(f"no reliability report for source {source}; run `moot backtest` or `moot join`")
    return json.dumps(report)


def build_server(models_dir, reports_dir, now=None):
    """Register the three tools on an MCP server whose bundles are preloaded."""
    try:
        from mcp.server.mcpserver import MCPServer as Server
    except ImportError:  # mcp 1.x
        from mcp.server.fastmcp import FastMCP as Server
    state = ServingState(models_dir, reports_dir, now)
    server = Server("mootcourt", instructions=BOUNDARY_SENTENCE)
    try:
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError:  # mcp 1.x
        from mcp.server.fastmcp.exceptions import ToolError
    from mootcourt.service import UnknownSourceError

    def refusing(fn):
        """A refusal (a bad row id, an unknown source, a cell to name) reaches the client as its one-line message, not as 'Error executing tool'."""
        import functools

        @functools.wraps(fn)
        def wrapped(*a, **k):
            try:
                return fn(*a, **k)
            except (ValueError, UnknownSourceError) as exc:
                raise ToolError(str(exc.args[0]) if isinstance(exc, KeyError) and exc.args else str(exc)) from None
        return wrapped

    @server.tool(name="get_card", description="Issue a read-only pre-trial card for a proposed experiment. Nothing is frozen or written. "
                                              "Leave the headline out for a ledger without headline text, and name the cell.")
    @refusing
    def get_card(source: str, impressions: int, headline: str = "", image_changed: bool = False, origin: str | None = None,
                 cell: str | None = None, headline_changed: bool = True, row_id: str | None = None, test_id: str | None = None,
                 variant_id: str | None = None, reference_headline: str = "", impressions_variant: int | None = None) -> str:
        return tool_get_card(state, source, headline, image_changed, impressions, origin, cell, headline_changed, row_id, test_id, variant_id,
                             reference_headline, impressions_variant)

    @server.tool(name="list_precedents", description="Top-k weighted precedents (row id, weight, kernel, y, s, test id) for a proposed headline.")
    @refusing
    def list_precedents(source: str, headline: str = "", image_changed: bool = False, k: int = 5, origin: str | None = None,
                        cell: str | None = None, headline_changed: bool = True) -> str:
        return tool_list_precedents(state, source, headline, image_changed, k, origin, cell, headline_changed)

    @server.tool(name="reliability_report", description="The per-cell rolling reliability report of a source.")
    @refusing
    def reliability_report(source: str) -> str:
        return tool_reliability_report(state, source)

    return server


def main(argv: list[str] | None = None) -> None:
    """Entry point: parse the directories and serve over stdio."""
    ap = argparse.ArgumentParser(prog="mootcourt.mcp_server", description="Read-only MCP server for Moot Court (stdio).")
    paths = storage_paths()
    ap.add_argument("--models-dir", type=Path, default=paths.models)
    ap.add_argument("--cards-dir", type=Path, default=paths.cards, help="accepted for symmetry with `moot serve`; never written")
    ap.add_argument("--reports-dir", type=Path, default=paths.reports)
    ap.add_argument("--now", default=None, help="fixed clock, ISO-8601 with offset (for tests)")
    args = ap.parse_args(argv)
    fixed = _parse_origin(args.now)
    build_server(args.models_dir, args.reports_dir, (lambda: fixed) if fixed else None).run(transport="stdio")


if __name__ == "__main__":
    main()
