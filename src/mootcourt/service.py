"""HTTP service: ``POST /card``, ``GET /reliability/{source}`` and ``GET /health``.

The service is read-only. The only write anywhere is that ``POST /card`` freezes the card it issues under the
cards directory (one new file per card, never modified later), which is how every card in the system is
recorded; no other route changes state, and a test enumerates the routes to prove it.

Bundles are loaded once at startup, for every source that has a champion in ``models/registry.json``, and kept
in memory, so a card costs the issue time only (milliseconds), not a joblib load. The reliability report is read
from ``reports/reliability-<source>.json`` on every request because the weekly join rewrites it.

The service binds to loopback by default (see ``moot serve``) and claims no authentication: put it behind your
own gateway if it must be reachable from elsewhere. The boundary sentence is in every card's footer and in the
health response.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from mootcourt import card as card_mod
from mootcourt.bundle import ModelBundle, load_bundle
from mootcourt.config import BOUNDARY_SENTENCE
from mootcourt.ledger import resolve_row_id
from mootcourt.predictors.p3 import TeamForecast
from mootcourt.registry import Registry
from mootcourt.settings import abstain_config
from mootcourt.storage import storage_paths


class UnknownSourceError(KeyError):
    """No model is registered for the requested source."""


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class ServingState:
    """Preloaded champion bundles plus the directories to read reliability from and freeze cards into."""

    def __init__(self, models_dir, reports_dir, now: Callable[[], dt.datetime] | None = None, config=None):
        self.models_dir, self.reports_dir = Path(models_dir), Path(reports_dir)
        self.now = now or _utc_now
        # The configured action threshold, read once at startup from the project file in the working directory (restart to change it),
        # through the same function as `moot card`, so one request gives one card id and one abstention on every path.
        self.config = config if config is not None else abstain_config()
        self.bundles: dict[str, ModelBundle] = {}
        reg = Registry(self.models_dir)
        for source in reg.sources():
            try:
                self.bundles[source] = load_bundle(reg.get_champion(source), self.models_dir)
            except KeyError:
                continue

    def bundle(self, source: str) -> ModelBundle:
        """The preloaded champion of a source; UnknownSourceError when there is none."""
        try:
            return self.bundles[source]
        except KeyError:
            raise UnknownSourceError(f"no model is registered for source {source}; known sources: {sorted(self.bundles)}") from None

    def reliability(self, source: str) -> dict | None:
        """The current reliability report of a source, or None when no report exists."""
        return card_mod.load_reliability_report(self.reports_dir, source)

    def request(self, payload: dict) -> card_mod.CardRequest:
        """Build a CardRequest from a plain dict (the same fields as the CLI options)."""
        now = self.now()
        team = payload.get("team_forecast")
        return card_mod.CardRequest(
            source=payload["source"], headline=payload.get("headline") or "", image_changed=bool(payload.get("image_changed", False)),
            impressions=int(payload["impressions"]), origin=payload.get("origin") or now,
            headline_changed=bool(payload.get("headline_changed", True)), cell=payload.get("cell"),
            row_id=resolve_row_id(payload["source"], payload.get("row_id"), payload.get("test_id"), payload.get("variant_id")),
            reference_headline=payload.get("reference_headline") or "",
            impressions_variant=None if payload.get("impressions_variant") is None else int(payload["impressions_variant"]),
            team_forecast=TeamForecast.create(team["p_win_team"], team["point_team"], clock=self.now) if team else None,
            guardrails=tuple(card_mod.Guardrail(g["cell"], float(g["delta"])) for g in (payload.get("guardrails") or [])),
        )

    def issue(self, payload: dict) -> card_mod.Card:
        """Issue a card (not frozen) from a payload with the bundle preloaded."""
        req = self.request(payload)
        return card_mod.build_card(self.bundle(req.source), req, reliability=self.reliability(req.source), now=self.now(), config=self.config,
                                   gates=self.gates())

    def gates(self) -> dict | None:
        """The gates of the reports folder (read on each request, like the reliability report), or None when there is no gates.json."""
        from mootcourt import simulate

        try:
            return simulate.load_gates(self.reports_dir / "gates.json")
        except FileNotFoundError:
            return None


class TeamPayload(BaseModel):
    """A team forecast supplied at issue; frozen with the card."""

    p_win_team: float = Field(ge=0.0, le=1.0)
    point_team: float


class GuardrailPayload(BaseModel):
    """A guardrail metric: its cell and the harm margin delta (above zero)."""

    cell: str = Field(max_length=64)
    delta: float = Field(gt=0, allow_inf_nan=False)


class CardPayload(BaseModel):
    """Request body of ``POST /card``: the same fields as the ``moot card`` options."""

    source: str = Field(max_length=64)
    headline: str = Field(default="", max_length=1000)       # optional, as on the command line: a ledger without headline text has none
    image_changed: bool = False
    impressions: int = Field(gt=0, le=10**12)
    origin: dt.datetime | None = None
    headline_changed: bool = True
    cell: str | None = Field(default=None, max_length=64)
    row_id: str | None = Field(default=None, max_length=256)          # the ledger row the weekly join attaches the outcome to
    test_id: str | None = Field(default=None, max_length=200)         # with variant_id: the ledger row key, instead of row_id
    variant_id: str | None = Field(default=None, max_length=200)
    reference_headline: str = Field(default="", max_length=1000)
    impressions_variant: int | None = Field(default=None, gt=0, le=10**12)
    team_forecast: TeamPayload | None = None
    guardrails: list[GuardrailPayload] = Field(default_factory=list, max_length=20)


def create_app(models_dir, cards_dir, reports_dir=None, now: Callable[[], dt.datetime] | None = None, trusted_hosts=None):
    """Build the FastAPI app over a models directory; ``cards_dir`` is where issued cards are frozen.

    ``trusted_hosts`` (a list of Host header values, without ports) refuses any other Host header with a 400. ``moot serve`` passes the
    loopback names when it binds to loopback, so a web page cannot reach the service through a DNS name that resolves to 127.0.0.1.
    """
    state = ServingState(models_dir, reports_dir if reports_dir is not None else storage_paths().reports, now)
    cards_dir = Path(cards_dir)
    app = FastAPI(title="Moot Court", description=BOUNDARY_SENTENCE)
    if trusted_hosts:
        from starlette.middleware.trustedhost import TrustedHostMiddleware

        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(trusted_hosts))

    def not_found(message: str) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": message})

    @app.get("/health")
    def health():
        return {"status": "ok", "sources": sorted(state.bundles), "boundary": BOUNDARY_SENTENCE}

    @app.get("/reliability/{source}")
    def reliability(source: str):
        if source not in state.bundles:
            return not_found(f"no model is registered for source {source}; known sources: {sorted(state.bundles)}")
        report = state.reliability(source)
        if report is None:
            return not_found(f"no reliability report for source {source}; run `moot backtest` or `moot join`")
        return report

    @app.post("/card")
    def post_card(payload: CardPayload):
        data = payload.model_dump()
        if data["origin"] is not None and data["origin"].tzinfo is None:
            return JSONResponse(status_code=422, content={"error": "origin needs a UTC offset"})
        try:
            issued = state.issue(data)
        except UnknownSourceError as exc:
            return not_found(str(exc))
        except ValueError as exc:
            return JSONResponse(status_code=422, content={"error": str(exc)})
        try:
            return card_mod.public_json(card_mod.freeze_or_load(issued, cards_dir))  # the one write: the new card file, or the identical frozen one
        except card_mod.CardFrozenError as exc:
            return JSONResponse(status_code=409, content={"error": str(exc)})

    app.state.serving = state
    return app
