"""Response simulators: the protocol, the request and result dataclasses, and request hashing.

A response simulator is any agent that, given a proposed experiment, returns its own probability that the
variant wins. The agent is outside this repository: adapters (stdio, http, recorded) attach it without a code
change. Nothing here calls a language model or the network.

What an agent may see. ``SimulationRequest`` carries aggregate, non-personal inputs only: the source, the cell,
the origin, the reference and variant headlines, two change flags, the planned exposures per arm, the standard
error known before launch, the action threshold and a budget. There is no user-level field, and ``from_wire``
rejects any key outside the schema.

What an agent may return. ``SimulationResult`` holds ``p_win_ai`` in [0, 1], the probability that the live test
ends with a significant positive estimate (the event ``p_sig`` forecasts), plus optional ``point_ai`` and
``interval_ai`` in the effect's units, the number of simulated respondents, optional aggregate ``raw_votes``,
latency and cost. A simulator that declines returns None.

Units: probabilities are unitless; ``point_ai`` and ``interval_ai`` are in the effect's units (percentage points
of click-through rate for Upworthy); ``latency_s`` is seconds; ``cost_usd`` is dollars.
"""
from __future__ import annotations

import hashlib
import json
import math
import numbers
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Protocol, runtime_checkable

COST_MODELS = ("free", "per_call", "per_token")
HASH_DIGITS = 9
MAX_OUTPUT_BYTES = 1_000_000                                # an agent's reply is a few hundred bytes; more than this is refused
BUILTIN_PROVIDER_IDS = ("null", "heuristic")                  # never trained on an archive, so they need no knowledge cutoff
FAILURE_KINDS = ("timeout", "start", "exit", "transport", "invalid", "error", "missing")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")        # provider ids and versions become folder names in the cache


class SimulatorError(ValueError):
    """A request or result broke the schema, or a provider could not be built."""


def _finite(v, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, numbers.Real):          # a numeric string or a flag is not a number here
        raise SimulatorError(f"{name} must be a number, got {v!r}")
    try:
        f = float(v)
    except (OverflowError, ValueError):                                 # an integer beyond the float range
        raise SimulatorError(f"{name} must be a number within the range of a float, got {v!r:.40}") from None
    if not math.isfinite(f):
        raise SimulatorError(f"{name} must be finite")
    return f


@dataclass(frozen=True)
class Budget:
    """Limits the agent is asked to respect: simulated respondents and wall-clock seconds."""

    max_respondents: int = 100
    max_seconds: float = 30.0

    def __post_init__(self):
        if _finite(self.max_respondents, "max_respondents") != int(self.max_respondents) or self.max_respondents < 1:
            raise SimulatorError("max_respondents must be a positive integer")
        if not _finite(self.max_seconds, "max_seconds") > 0:
            raise SimulatorError("max_seconds must be positive")


@dataclass(frozen=True)
class SimulationRequest:
    """One proposed experiment, as aggregate non-personal inputs.

    ``planned_n_ref`` and ``planned_n_var`` are the planned exposures per arm, ``s_star`` the standard error of
    the future estimate known before launch, ``action_threshold`` the probability level at which a decision would
    change. ``reference_headline`` may be empty when the reference is not known.
    """

    source: str
    cell: str
    origin: str
    reference_headline: str
    variant_headline: str
    image_changed: bool
    headline_changed: bool
    planned_n_ref: int
    planned_n_var: int
    s_star: float
    action_threshold: float
    budget: Budget = field(default_factory=Budget)

    def __post_init__(self):
        for name in ("source", "cell", "origin"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise SimulatorError(f"{name} must be a non-empty string")
        for name in ("reference_headline", "variant_headline"):
            if not isinstance(getattr(self, name), str):
                raise SimulatorError(f"{name} must be a string")
        if self.planned_n_ref < 1 or self.planned_n_var < 1:
            raise SimulatorError("planned exposures must be positive")
        if not _finite(self.s_star, "s_star") > 0:
            raise SimulatorError("s_star must be positive")
        _finite(self.action_threshold, "action_threshold")

    def to_wire(self) -> dict:
        """The one JSON-ready form that adapters send; built from the dataclass fields only."""
        d = asdict(self)
        d["image_changed"], d["headline_changed"] = bool(self.image_changed), bool(self.headline_changed)
        return d

    @classmethod
    def from_wire(cls, d: dict) -> SimulationRequest:
        """Parse the wire form; any key outside the schema is refused."""
        allowed = {f.name for f in fields(cls)}
        extra = set(d) - allowed
        if extra:
            raise SimulatorError(f"unknown request fields: {sorted(extra)}")
        d = dict(d)
        if "budget" in d:
            bextra = set(d["budget"]) - {"max_respondents", "max_seconds"}
            if bextra:
                raise SimulatorError(f"unknown budget fields: {sorted(bextra)}")
            d["budget"] = Budget(**d["budget"])
        try:
            return cls(**d)
        except TypeError as exc:
            raise SimulatorError(str(exc)) from None

    def request_hash(self) -> str:
        """Stable 16-hex-character key: sha256 of the canonical wire form with floats rounded to 9 digits."""
        return request_hash(self.to_wire())


def _canon(v):
    if isinstance(v, float):
        return round(v, HASH_DIGITS)
    if isinstance(v, dict):
        return {k: _canon(x) for k, x in v.items()}
    return v


def request_hash(wire: dict) -> str:
    """Hash of a wire-form request (see ``SimulationRequest.request_hash``)."""
    return hashlib.sha256(json.dumps(_canon(wire), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SimulationResult:
    """An agent's second opinion on one request. ``p_win_ai`` is P(significant and positive)."""

    p_win_ai: float
    point_ai: float | None = None
    interval_ai: tuple[float, float] | None = None
    n_simulated: int = 0
    raw_votes: dict | None = None
    provider_id: str = ""
    version: str = ""
    latency_s: float = 0.0
    cost_usd: float = 0.0
    notes: str = ""

    def __post_init__(self):
        p = _finite(self.p_win_ai, "p_win_ai")
        if not 0.0 <= p <= 1.0:
            raise SimulatorError(f"p_win_ai must be in [0, 1], got {p}")
        if self.point_ai is not None:
            _finite(self.point_ai, "point_ai")
        if self.interval_ai is not None:
            if not isinstance(self.interval_ai, (list, tuple)) or len(self.interval_ai) != 2:
                raise SimulatorError("interval_ai must hold exactly two numbers (low, high)")
            lo, hi = (_finite(v, "interval_ai") for v in self.interval_ai)
            if lo > hi:
                raise SimulatorError("interval_ai must be ordered (low, high)")
        if _finite(self.n_simulated, "n_simulated") != int(self.n_simulated) or self.n_simulated < 0:
            raise SimulatorError("n_simulated must be a non-negative integer")
        if self.raw_votes is not None:
            if not isinstance(self.raw_votes, dict) or not all(isinstance(k, str) for k in self.raw_votes):
                raise SimulatorError("raw_votes must map labels to aggregate counts")
            for k, v in self.raw_votes.items():
                _finite(v, f"raw_votes[{k}]")
        if _finite(self.latency_s, "latency_s") < 0 or _finite(self.cost_usd, "cost_usd") < 0:
            raise SimulatorError("latency_s and cost_usd must be non-negative")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["interval_ai"] = list(self.interval_ai) if self.interval_ai is not None else None
        return d

    @classmethod
    def from_dict(cls, d: dict, **defaults) -> SimulationResult:
        """Build from an agent's JSON; unknown keys are ignored, ``defaults`` fill provider id, version and so on."""
        if not isinstance(d, dict):
            raise SimulatorError(f"the result must be a JSON object, got {type(d).__name__}")
        known = {f.name for f in fields(cls)}
        data = {**defaults, **{k: v for k, v in d.items() if k in known}}
        if "p_win_ai" not in data:
            raise SimulatorError("the result has no p_win_ai")
        if data.get("interval_ai") is not None:
            if not isinstance(data["interval_ai"], (list, tuple)):
                raise SimulatorError("interval_ai must be a list of two numbers")
            data["interval_ai"] = tuple(data["interval_ai"])
        return cls(**data)


@dataclass(frozen=True)
class SimulatorInfo:
    """What a provider says about itself."""

    provider_id: str
    version: str
    knowledge_cutoff: str | None
    cost_model: str
    description: str

    def __post_init__(self):
        if not self.provider_id or not self.version:
            raise SimulatorError("a provider needs an id and a version")
        for name in ("provider_id", "version"):
            if not isinstance(getattr(self, name), str) or not SAFE_ID.fullmatch(getattr(self, name)):
                raise SimulatorError(f"{name} {getattr(self, name)!r}: use letters, digits, dot, underscore, hyphen, starting with a letter or digit")
        if self.cost_model not in COST_MODELS:
            raise SimulatorError(f"cost_model must be one of {COST_MODELS}")
        if self.knowledge_cutoff is not None:
            import datetime as dt

            try:
                dt.date.fromisoformat(self.knowledge_cutoff)
            except ValueError:
                raise SimulatorError("knowledge_cutoff must be an ISO date or None") from None


@runtime_checkable
class ResponseSimulator(Protocol):
    """Anything with ``describe`` and ``simulate``; ``simulate`` returns None when the agent declines."""

    def describe(self) -> SimulatorInfo:  # pragma: no cover - protocol
        ...

    def simulate(self, request: SimulationRequest) -> SimulationResult | None:  # pragma: no cover - protocol
        ...
