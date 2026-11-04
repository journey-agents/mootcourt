"""The card: a pre-trial opinion issued before an experiment launches.

One frozen dataclass, ``Card``, holds the eight sections of spec section 10 in order: header (source,
cell, origin, ledger snapshot id, model id, feature hash, issued_at), evidence, prediction, team forecast,
robustness, skill at this n, abstention status and reasons, and the footer. The Markdown and JSON
renderers both read that dataclass, so they cannot disagree.

Units: effects, intervals and the point estimate are in the source's unit (percentage points of click-through
rate for Upworthy, standard deviations for ASOS, percent lift for the synthetic source); ``s_star`` is the
standard error of the future estimate in the same unit, derived before launch from the planned exposures per arm.
Probabilities are unitless. Origin semantics: the card is computed from rows with status admitted and
``usable_after <= origin``.

An abstained card shows the reasons and P0 only. The renderers decide what to hide from the abstention
status itself, so replacing the decision on an issued card cannot leak an estimate.

The footer is the boundary sentence from ``config.BOUNDARY_SENTENCE`` on every rendered card.
Every card carries the ledger snapshot id, the model id and the feature hash; ``build_card`` raises
ValueError when any of them is missing. ``freeze_card`` writes ``cards/<card_id>.json`` once, read-only.

Schema version 2 (round 00, docs/method.md calls 162, 163 and 166). The prediction carries the predictive itself: its family (Student
t, or Normal), degrees of freedom, location and scale, the grid it was built on and the planned standard error ``s_star``, so the weekly
join and the replay score a result with the card's own predictive and not a Normal rebuilt from an interval. It carries two intervals:
the 80 and 90 percent intervals for the true effect (what the team reads) and the 80 and 90 percent intervals for the observed estimate
at the planned standard error (what coverage is scored against, as in the backtest). An abstained card keeps the forecast it withheld in
a sealed ``withheld`` block of the frozen file: the join scores it for reliability so a stale or drifted cell can recover, and no
renderer, no response of the service and no tool shows it (``public_json`` drops it). The skill line carries the trailing Brier skill
with its by-test bootstrap interval, the number of tests, the gate verdict at that n and the latest gated backtest figure. The
precedent robustness numbers read "not applicable" where the weight on precedents is zero and are omitted on an abstained card.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mootcourt.abstain import AbstainConfig, AbstainDecision, check_instability, decide, reliability_reason
from mootcourt.bundle import ModelBundle
from mootcourt.config import ACTION_THRESHOLD, BOUNDARY_SENTENCE, Z
from mootcourt.predictors.p1 import p_sig_t
from mootcourt.predictors.p2 import NeighborState
from mootcourt.predictors.p3 import TeamForecast
from mootcourt.storage import safe_chmod

CARD_SCHEMA_VERSION = 2


class CardFrozenError(FileExistsError):
    """A frozen card with this id already exists and is never overwritten."""


# ----------------------------------------------------------------- request
@dataclass(frozen=True)
class CardRequest:
    """What the caller asks about: a proposed change and its planned exposure.

    ``impressions`` is the planned exposures of the reference arm (per arm when the arms are equal) and
    ``impressions_variant`` those of the variant arm (default: the same). ``origin`` is when the card stands (default: now);
    ``team_forecast`` is the team's own forecast, stored frozen. ``cell`` overrides the derived cell (needed
    for sources whose cell is a metric id). ``row_id`` is the ledger row the card will be joined to (``source:test_id:variant_id``,
    see ``mootcourt.ledger.make_row_id``). ``reference_headline`` is the reference arm's headline, read by a pairwise feature space.
    """

    source: str
    headline: str
    image_changed: bool
    impressions: int
    origin: dt.datetime | None = None
    team_forecast: TeamForecast | None = None
    row_id: str | None = None
    headline_changed: bool = True
    cell: str | None = None
    guardrails: tuple = ()
    reference_headline: str = ""
    impressions_variant: int | None = None


@dataclass(frozen=True)
class Guardrail:
    """A guardrail metric on the card: its cell and the harm margin ``delta`` (above zero, in the cell's effect units).

    The card reports ``p_harm = P(theta < -delta)``, the probability that the true effect on this metric is worse than minus ``delta``.
    """

    cell: str
    delta: float


def derive_cell(source: str, image_changed: bool, headline_changed: bool = True) -> str:
    """Kind of change: ``headline_only`` if the image is unchanged, ``both`` if image and headline changed,
    ``image_only`` if only the image changed. (For sources keyed by metric the caller supplies the cell.)"""
    if not image_changed:
        return "headline_only"
    return "both" if headline_changed else "image_only"


def s_star_from_exposure(impressions_per_arm: float, base_ctr: float) -> float:
    """Standard error (percentage points) of an absolute click-through difference at rate ``p`` in both arms.

    Two independent binomials with equal exposure ``n``: ``s = 100 sqrt(2 p (1 - p) / n)``.
    Raises ValueError unless ``n > 0`` and ``0 < p < 1``.
    """
    if impressions_per_arm <= 0:
        raise ValueError("impressions per arm must be positive")
    if not 0.0 < base_ctr < 1.0:
        raise ValueError("base click-through rate must be in (0, 1)")
    return 100.0 * math.sqrt(2.0 * base_ctr * (1.0 - base_ctr) / impressions_per_arm)


# -------------------------------------------------------------------- card
@dataclass(frozen=True)
class RequestEcho:
    """The request as the card saw it, with the derived standard error."""

    headline: str
    image_changed: bool
    headline_changed: bool
    impressions: int
    s_star: float
    row_id: str | None
    reference_headline: str = ""
    impressions_variant: int | None = None


@dataclass(frozen=True)
class Evidence:
    """Section 2: how much precedent there is."""

    n_cell: int
    n_eff: float
    base_rate_sig_pos: float | None


@dataclass(frozen=True)
class Prediction:
    """Section 3: the model's numbers. Renderers show them only when the card is issued."""

    rung: str
    lam: float | None
    p_sig: float | None
    point: float | None
    interval_80: tuple | None
    interval_90: tuple | None
    p_win: float | None
    p0_p_sig: float | None
    p0_mean: float | None
    interval_80_y: tuple | None = None        # 80 percent interval for the observed estimate at the planned standard error
    interval_90_y: tuple | None = None
    predictive: dict | None = None            # family, df, location, scale, grid and s_star: everything a later score needs
    p0_var: float | None = None               # P0's variance of y: with p0_mean, the baseline log score of the join is the card's own (REV-L-019)


@dataclass(frozen=True)
class Robustness:
    """Section 5: how fragile the opinion is. ``applicable`` is False where the weight on precedents is zero (the card uses the prior)."""

    k: int
    dismissals_needed: int | None
    bootstrap_same_side: float
    action_threshold: float
    resamples: int
    applicable: bool = True


@dataclass(frozen=True)
class Skill:
    """Section 6: the cell's trailing Brier skill against the cell base rate from the reliability report, with its interval and verdict.

    ``brier_skill_lo`` and ``brier_skill_hi`` are the 90 percent by-test bootstrap interval of the window, ``n_tests`` the tests in it,
    ``verdict`` says whether that many tests can decide a skill at the gate, and ``backtest`` is the latest gated figure from the
    bundle's backtest (skill, interval, tests, rung) when the bundle has one.
    """

    available: bool
    brier_skill: float | None
    n: int | None
    as_of: str | None
    brier_skill_lo: float | None = None
    brier_skill_hi: float | None = None
    n_tests: int | None = None
    window_weeks: int | None = None
    verdict: str | None = None
    backtest: dict | None = None


@dataclass(frozen=True)
class SecondOpinionView:
    """An outside agent's opinion shown beside ``p_sig``, with the provider and the weight in force.

    ``p_ai`` is None when the agent declined. ``weight`` is the stacking weight earned on the backtest (0 until
    earned); ``p_stack`` is ``(1 - weight) p_sig + weight p_ai`` and is None on an abstained card or a decline.
    ``contaminated`` is true when that weight was earned with origins earlier than the agent's knowledge cutoff.
    """

    provider_id: str
    version: str
    knowledge_cutoff: str | None
    p_ai: float | None
    weight: float
    p_stack: float | None
    contaminated: bool = False          # the weight was earned with origins the agent may have seen; always last


@dataclass(frozen=True)
class GuardrailView:
    """One guardrail metric on a card, from the same ladder as the primary metric, with its own abstention.

    ``p_harm``, ``point`` and ``interval_90`` are None when the guardrail abstained (a metric whose evidence is thin shows its reasons
    and no number, whatever the primary metric did).
    """

    cell: str
    delta: float
    status: str
    reasons: tuple
    details: dict
    n_cell: int
    p_harm: float | None
    point: float | None
    interval_90: tuple | None


@dataclass(frozen=True)
class Card:
    """A pre-trial opinion. Field order: header, then the sections in spec order."""

    card_id: str
    source: str
    cell: str
    origin: str
    snapshot_id: str
    model_id: str
    feature_hash: str
    issued_at: str
    request: RequestEcho
    evidence: Evidence
    prediction: Prediction
    team_forecast: TeamForecast | None
    robustness: Robustness
    skill: Skill
    abstention: AbstainDecision
    footer: str
    second_opinion: SecondOpinionView | None = None
    guardrails: tuple = ()
    withheld: dict | None = None          # the forecast an abstained card did not issue, sealed for the join (never rendered)


def _p_sig_closed(sw, swy, sw2v, lam, mu, tau, tau_res2, s_star, nu=math.inf, z=Z):
    m = swy / sw
    v_m = sw2v / (sw * sw)
    theta = lam * m + (1.0 - lam) * mu
    v = lam * (v_m + tau_res2) + (1.0 - lam) * tau * tau
    return float(p_sig_t(theta, v, nu, s_star, z))


def robustness_dismissals(st: NeighborState, s_star: float, threshold: float = ACTION_THRESHOLD, k: int | None = None) -> int | None:
    """Precedents to dismiss, highest weight first, to move ``p_sig`` across ``threshold``; None if more than ``k``.

    Greedy: precedents are ordered by their P2 weight ``kernel / (s^2 + tau^2)`` and removed one at a time,
    recomputing the closed-form ``p_sig`` incrementally from running sums (the unlisted tail stays).
    Returns the number removed when ``p_sig`` first lands on the other side of ``threshold``.
    """
    n = len(st.row_ids)
    if n == 0:
        return None
    k = n if k is None else min(k, n)
    var = st.s ** 2 + st.tau ** 2
    w = st.kernel / var
    order = np.argsort(-w, kind="stable")
    sw, swy = float(w.sum()) + st.tail[0], float((w * st.y).sum()) + st.tail[1]
    sw2v = float((w * w * var).sum()) + st.tail[2]
    w_total = float(w.sum()) + st.tail[0]          # relative to the weight the state started with, so the kernel's absolute scale does not matter
    start_above = _p_sig_closed(sw, swy, sw2v, st.lam, st.mu, st.tau, st.tau_res2, s_star, st.nu) >= threshold
    for step, i in enumerate(order[:k], start=1):
        sw -= w[i]
        swy -= w[i] * st.y[i]
        sw2v -= w[i] * w[i] * var[i]
        if sw <= 1e-12 * w_total:
            return None
        above = _p_sig_closed(sw, swy, sw2v, st.lam, st.mu, st.tau, st.tau_res2, s_star, st.nu) >= threshold
        if above != start_above:
            return step
    return None


def _iso(t: dt.datetime) -> str:
    if t.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return t.isoformat()


def _predictive_block(main, s_star: float) -> dict:
    """The predictive of a card as stored: its spec (family, df, location, scale, grid) and the planned standard error."""
    spec = dict(main.spec) if main.spec else {"family": "grid", "df": None, "location": main.mean(), "scale": math.sqrt(main.var()),
                                              "grid_lo": float(main.theta[0]), "grid_hi": float(main.theta[-1]), "grid_n": int(len(main.theta))}
    return {**spec, "s_star": float(s_star)}


def _y_intervals(main, s_star: float) -> tuple[tuple, tuple]:
    """80 and 90 percent intervals of the observed estimate at ``s_star``, computed as the backtest computes them."""
    from mootcourt.harness import ystar_intervals

    iv = ystar_intervals(main, [s_star])
    return ((float(iv[0.8][0][0]), float(iv[0.8][1][0])), (float(iv[0.9][0][0]), float(iv[0.9][1][0])))


def _p0_view(bundle, cell: str, origin):
    """P0's forecast of the cell (None when the cell has no visible row): the baseline of the card."""
    try:
        return bundle.p0.forecast(cell, origin)
    except ValueError:
        return None


def build_card(
    bundle: ModelBundle,
    request: CardRequest,
    reliability: dict | None = None,
    now: dt.datetime | None = None,
    config: AbstainConfig | None = None,
    gates: dict | None = None,
) -> Card:
    """Issue a card from a fitted bundle.

    ``reliability`` is the source's reliability report (or None); ``now`` is the issue time (injectable); ``gates`` is what
    ``simulate.load_gates`` returns, for the gate verdict of the skill line (None: the line says the sizes are not available).
    Raises ValueError if the bundle lacks a snapshot id, model id or feature hash, or the request is invalid.
    """
    for name in ("snapshot_id", "model_id", "feature_hash"):
        if not getattr(bundle, name):
            raise ValueError(f"cannot issue a card: the bundle has no {name}")
    cfg = config or AbstainConfig()
    now = now or dt.datetime.now(dt.timezone.utc)
    origin = request.origin or now
    cell = request.cell or derive_cell(request.source, request.image_changed, request.headline_changed)
    known = bundle.cells()
    if request.cell is None and known and cell not in known and not set(known) & {"headline_only", "image_only", "both"}:
        # a ledger keyed by metric (or any other cell) has no kind-of-change cells: forecasting a cell that does not exist would be silent nonsense
        raise ValueError(f"this ledger's cells are {', '.join(known)}; the card needs --cell (or the cell field) to name one of them")
    n_var = request.impressions_variant if request.impressions_variant is not None else request.impressions
    s_star = bundle.s_star(cell, request.impressions, n_var)
    echo = RequestEcho(request.headline, bool(request.image_changed), bool(request.headline_changed),
                       int(request.impressions), s_star, request.row_id, request.reference_headline or "",
                       None if request.impressions_variant is None else int(request.impressions_variant))
    bundle.check_origin(origin)
    n_cell = bundle.n_visible(cell, origin)
    if n_cell == 0:
        reasons, details = ["support"], {"support": f"no admitted rows in cell {cell} are visible at the origin"}
        why = reliability_reason(reliability, cell, now, cfg)
        if why is not None:                       # every triggered reason is listed, not only the first
            reasons.append("reliability")
            details["reliability"] = why
        decision = AbstainDecision("abstain", tuple(reasons), details)
        return _assemble(bundle, request, cell, origin, now, echo, Evidence(0, 0.0, None),
                         Prediction("P2", None, None, None, None, None, None, None, None),
                         Robustness(0, None, 1.0, cfg.action_threshold, 0, False), _skill(reliability, cell, bundle, gates, origin), decision, None)
    exposure = 0.5 * (request.impressions + n_var)
    x = bundle.transform_text(request.headline, request.image_changed, cell=cell, exposure=exposure, reference=request.reference_headline)
    state = bundle.neighbor_state(x, cell, origin)
    p0 = _p0_view(bundle, cell, origin)
    main = bundle.p2.predictive_from_state(state, x, s_star, cell, origin)
    mo = state.moments() if (len(state.row_ids) or state.tail[0] > 0) else None
    n_eff = mo.n_eff if mo else 0.0
    evidence = Evidence(n_cell, float(n_eff), bundle.base_rate(cell, origin))
    iv80_y, iv90_y = _y_intervals(main, s_star)
    prediction = Prediction(
        "P2", state.lam, main.p_sig(s_star), main.mean(), tuple(main.interval(0.8)), tuple(main.interval(0.9)),
        main.p_win(0.0), None if p0 is None else p0.p_sig, None if p0 is None else p0.mean, iv80_y, iv90_y, _predictive_block(main, s_star),
        None if p0 is None else p0.var,
    )
    k = max(1, int(round(n_eff))) if n_eff else 0
    inst = check_instability(state, s_star, seed=0, config=cfg)
    robust = Robustness(k, robustness_dismissals(state, s_star, cfg.action_threshold, k), inst.same_side_fraction,
                        cfg.action_threshold, inst.resamples, bool(state.lam > 0.0))
    decision = decide(
        n_support=n_cell, density=bundle.density(x, cell, origin), density_threshold=bundle.novelty_threshold(cell),
        reliability_report=reliability, cell=cell, now=now, neighbor_state=state, s_star=s_star, config=cfg,
    )
    withheld = None
    if decision.status != "issue":
        withheld = {"rung": prediction.rung, "lambda": prediction.lam, "p_sig": prediction.p_sig, "point": prediction.point,
                    "interval_80": list(prediction.interval_80), "interval_90": list(prediction.interval_90),
                    "interval_80_y": list(iv80_y), "interval_90_y": list(iv90_y), "p_win": prediction.p_win, "predictive": prediction.predictive}
    card = _assemble(bundle, request, cell, origin, now, echo, evidence, prediction, robust, _skill(reliability, cell, bundle, gates, origin),
                     decision, withheld)
    return _with_guardrails(card, bundle, request, origin, now, reliability, cfg) if request.guardrails else card


def guardrail_view(bundle: ModelBundle, request: CardRequest, g: Guardrail, origin: dt.datetime, now: dt.datetime,
                   reliability: dict | None, cfg: AbstainConfig) -> GuardrailView:
    """``p_harm`` and the abstention of one guardrail metric, from the same ladder (P2 with its weight, P1 where the weight is 0)."""
    n_cell = bundle.n_visible(g.cell, origin)
    if n_cell == 0:
        reasons, details = ["support"], {"support": f"no admitted rows in cell {g.cell} are visible at the origin"}
        why = reliability_reason(reliability, g.cell, now, cfg)
        if why is not None:
            reasons.append("reliability")
            details["reliability"] = why
        return GuardrailView(g.cell, g.delta, "abstain", tuple(reasons), details, 0, None, None, None)
    n_var = request.impressions_variant if request.impressions_variant is not None else request.impressions
    s_star = bundle.s_star(g.cell, request.impressions, n_var)
    x = bundle.transform_text(request.headline, request.image_changed, cell=g.cell, exposure=0.5 * (request.impressions + n_var),
                              reference=request.reference_headline)
    state = bundle.neighbor_state(x, g.cell, origin)
    main = bundle.p2.predictive_from_state(state, x, s_star, g.cell, origin)
    decision = decide(
        n_support=n_cell, density=bundle.density(x, g.cell, origin), density_threshold=bundle.novelty_threshold(g.cell),
        reliability_report=reliability, cell=g.cell, now=now, neighbor_state=state, s_star=s_star, config=cfg,
    )
    p_harm = float(1.0 - main.prob_gt(-g.delta))
    if decision.status != "issue":
        return GuardrailView(g.cell, g.delta, "abstain", tuple(decision.reasons), dict(decision.details), n_cell, None, None, None)
    return GuardrailView(g.cell, g.delta, "issue", (), {}, n_cell, p_harm, main.mean(), tuple(main.interval(0.9)))


def _with_guardrails(card: Card, bundle: ModelBundle, request: CardRequest, origin: dt.datetime, now: dt.datetime,
                     reliability: dict | None, cfg: AbstainConfig) -> Card:
    seen = {card.cell}
    views = []
    for g in request.guardrails:
        if not isinstance(g, Guardrail):
            g = Guardrail(*g)
        if not g.delta > 0:
            raise ValueError(f"guardrail {g.cell}: the harm margin delta must be above zero")
        if g.cell in seen:
            raise ValueError(f"guardrail {g.cell}: a metric appears once, as the primary metric or as one guardrail")
        seen.add(g.cell)
        views.append(guardrail_view(bundle, request, g, origin, now, reliability, cfg))
    card = dataclasses.replace(card, guardrails=tuple(views))
    return dataclasses.replace(card, card_id=content_id(card))


def gate_verdict(n_tests: int | None, lo, hi, gates: dict | None, base_rate: float | None) -> str:
    """Whether ``n_tests`` tests can decide a skill at the gate (read at the base rate nearest to ``base_rate``), and what the interval says."""
    if n_tests is None:
        return "the number of tests in the window is not recorded, so the skill cannot be judged"
    if gates is None:
        return f"{n_tests} tests; gate sizes are not available (run `moot simulate gate-power`)"
    from mootcourt import harness_stats as hs
    from mootcourt.simulate import select_gates

    sel = select_gates(gates, base_rate) or gates
    st = hs.gate_status(int(n_tests), sel)
    where = f" at base rate {sel['base_rate']:.2f}" if sel.get("base_rate") is not None else ""
    side = ""
    if lo is not None and hi is not None:
        side = (
            ", and its interval includes zero"
            if lo <= 0.0 <= hi
            else (", and its interval is above zero" if lo > 0 else ", and its interval is below zero")
        )
    unit = (gates.get("interval") or {}).get("by")
    caveat = "" if unit == "test" else " (this gates file was simulated per row, which overstates what tests can decide)"
    word = "tests" if unit == "test" else "rows"
    need = f" (the gate needs {sel['n_400']} {word} for a skill of 0.10 and {sel['n_200']} for 0.20{where}){caveat}"
    return f"{n_tests} tests: {st['label']}{need}{side}"


def _skill(reliability: dict | None, cell: str, bundle=None, gates: dict | None = None, origin=None) -> Skill:
    entry = (reliability or {}).get("cells", {}).get(cell)
    backtest = None
    summary = getattr(bundle, "backtest_summary", None) if bundle is not None else None
    if summary and summary.get("brier_skill") is not None:
        backtest = {k: summary.get(k) for k in ("rung", "brier_skill", "brier_skill_lo", "brier_skill_hi", "n_tests", "n", "snapshot_id")}
    if not entry:
        return Skill(False, None, None, None, backtest=backtest)
    lo, hi, n_tests = entry.get("brier_skill_lo"), entry.get("brier_skill_hi"), entry.get("n_tests")
    base = None
    if bundle is not None and origin is not None:
        try:
            base = bundle.base_rate(cell, origin)
        except ValueError:
            base = None
    return Skill(True, entry.get("brier_skill"), entry.get("n"), entry.get("as_of"), lo, hi, n_tests, entry.get("window_weeks"),
                 gate_verdict(n_tests, lo, hi, gates, base), backtest)


def content_id(card: Card) -> str:
    """Card id: 16 hex characters of sha256 over the full card content without the id (sorted keys).

    Anything shown on the card, the reliability state and the team forecast included, therefore changes the id.
    """
    body = {k: v for k, v in to_json(card).items() if k != "card_id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _assemble(bundle, request, cell, origin, now, echo, evidence, prediction, robust, skill, decision, withheld=None) -> Card:
    issued, origin_s = _iso(now), _iso(origin)
    card = Card("", request.source, cell, origin_s, bundle.snapshot_id, bundle.model_id, bundle.feature_hash,
                issued, echo, evidence, prediction, request.team_forecast, robust, skill, decision, BOUNDARY_SENTENCE, withheld=withheld)
    return dataclasses.replace(card, card_id=content_id(card))


# --------------------------------------------------------------- renderers
def _issued(card: Card) -> bool:
    return card.abstention.status == "issue"


def _unit(source: str) -> str:
    """Unit of effects for a source, as written after a number on the card."""
    return {"upworthy": "percentage points", "asos": "standard deviations", "synthetic": "percent lift"}.get(source, "units of the ledger's effect")


def _num(v, nd=3) -> str:
    return "n/a" if v is None else f"{v:.{nd}f}"


def to_json(card: Card) -> dict:
    """JSON-safe dict of the card as it is frozen. An abstained card carries only P0 in ``prediction`` and, sealed, the forecast it withheld.

    ``withheld`` is for the weekly join and the replay, which score it for reliability; ``public_json`` drops it for every response.
    """
    p = card.prediction
    p0 = None if p.p0_p_sig is None else {"p_sig": p.p0_p_sig, "mean": p.p0_mean, "var": p.p0_var}
    if _issued(card):
        prediction = {
            "rung": p.rung, "lambda": p.lam, "p_sig": p.p_sig, "point": p.point,
            "interval_80": list(p.interval_80) if p.interval_80 else None,
            "interval_90": list(p.interval_90) if p.interval_90 else None,
            "interval_80_y": list(p.interval_80_y) if p.interval_80_y else None,
            "interval_90_y": list(p.interval_90_y) if p.interval_90_y else None,
            "p_win": p.p_win, "p0": p0, "predictive": p.predictive,
        }
    else:
        prediction = {"rung": "P0", "p0": p0}
    team = None if card.team_forecast is None else card.team_forecast.to_dict()
    rb = dataclasses.asdict(card.robustness)
    if not _issued(card):
        rb = {"applicable": False, "reason": "an abstained card shows no robustness numbers"}
    out = {
        "schema_version": CARD_SCHEMA_VERSION, "card_id": card.card_id, "source": card.source, "cell": card.cell, "origin": card.origin,
        "snapshot_id": card.snapshot_id, "model_id": card.model_id, "feature_hash": card.feature_hash,
        "issued_at": card.issued_at,
        "request": dataclasses.asdict(card.request),
        "evidence": dataclasses.asdict(card.evidence),
        "prediction": prediction,
        "team_forecast": team,
        "robustness": rb,
        "skill": dataclasses.asdict(card.skill),
        "abstention": {"status": card.abstention.status, "reasons": list(card.abstention.reasons),
                       "details": {k: v for k, v in card.abstention.details.items()}},
        "footer": card.footer,
    }
    if card.withheld is not None:
        out["withheld"] = card.withheld
    if card.second_opinion is not None:
        out["second_opinion"] = dataclasses.asdict(card.second_opinion)
    if card.guardrails:
        out["guardrails"] = [{"cell": g.cell, "delta": g.delta, "status": g.status, "reasons": list(g.reasons), "details": dict(g.details),
                              "n_cell": g.n_cell, "p_harm": g.p_harm, "point": g.point,
                              "interval_90": list(g.interval_90) if g.interval_90 else None} for g in card.guardrails]
    return out


def public_json(doc: dict) -> dict:
    """The card JSON without its sealed ``withheld`` forecast: what a response, a tool or a screen may show."""
    return {k: v for k, v in doc.items() if k != "withheld"}


def _second_opinion_lines(card: Card) -> list[str]:
    so, p = card.second_opinion, card.prediction
    who = f"{so.provider_id} version {so.version}"
    if so.knowledge_cutoff:
        who += f", knowledge cutoff {so.knowledge_cutoff}"
    lines = [f"- Provider: {who}"]
    if not _issued(card):
        lines.append("- The card abstained, so no second opinion is shown.")
        return lines
    if so.p_ai is None:
        lines.append("- The second opinion abstained: the agent gave no answer for this request.")
    else:
        lines.append(f"- P(significant and positive) according to the agent: {_num(so.p_ai)}")
        if _issued(card):
            lines.append(f"- Model, side by side: P(significant and positive) {_num(p.p_sig)}")
    lines.append(f"- Weight in force: {_num(so.weight, 2)}")
    if so.weight > 0.0 and so.contaminated:
        lines.append("- This weight was earned with contaminated origins: the agent may have seen those outcomes in training, so treat it with care.")
    if so.weight == 0.0:
        lines.append("- The weight is zero: the agent has not earned a place in the number yet, so the model's p_sig is the one that counts.")
    elif so.p_stack is not None:
        lines.append(f"- Stacked P(significant and positive) at that weight: {_num(so.p_stack)}")
    return lines


def _skill_lines(sk: Skill) -> list[str]:
    """The skill section: never a bare number, always its window, interval, test count and the gate verdict at that n."""
    out: list[str] = []
    if sk.available:
        if sk.brier_skill_lo is not None and sk.brier_skill_hi is not None:
            iv = f" (90 percent interval {_num(sk.brier_skill_lo)} to {_num(sk.brier_skill_hi)}, by test)"
        else:
            iv = " (no interval is recorded in this reliability report, so this number cannot be judged)"
        win = f"trailing {sk.window_weeks} weeks" if sk.window_weeks else "trailing window"
        tests = f" from {sk.n_tests} tests" if sk.n_tests is not None else ""
        out += [f"- Brier skill against the cell base rate, {win}: {_num(sk.brier_skill)}{iv}, measured on {sk.n} rows{tests}, as of {sk.as_of}"]
        out += [f"- Gate at this n: {sk.verdict or 'no verdict is available'}"]
    else:
        out += ["- Not measured: the reliability report has no entry for this cell."]
    if sk.backtest:
        b = sk.backtest
        iv = (f" (90 percent interval {_num(b.get('brier_skill_lo'))} to {_num(b.get('brier_skill_hi'))})"
              if b.get("brier_skill_lo") is not None else "")
        out += [f"- Latest gated backtest, rung {b.get('rung')}: Brier skill {_num(b.get('brier_skill'))}{iv} over {b.get('n_tests') or b.get('n')} "
                f"{'tests' if b.get('n_tests') else 'rows'}"]
    return out


def to_markdown(card: Card) -> str:
    """Markdown rendering; sections in spec order, ending with the boundary sentence."""
    r, e, p, rb, sk = card.request, card.evidence, card.prediction, card.robustness, card.skill
    u = _unit(card.source)
    out = [
        "# Moot Court card", "",
        f"- Card id: {card.card_id}",
        f"- Source: {card.source}",
        f"- Cell: {card.cell}",
        f"- Origin: {card.origin}",
        f"- Ledger snapshot: {card.snapshot_id}",
        f"- Model: {card.model_id}",
        f"- Feature hash: {card.feature_hash}",
        f"- Issued at: {card.issued_at}",
        f"- Request: headline \"{r.headline}\", image changed: {'yes' if r.image_changed else 'no'}, "
        f"exposures per arm: {r.impressions}, standard error of the future estimate: {r.s_star:.3f} {u}",
        "", "## Evidence", "",
        f"- Admitted rows in the cell visible at the origin: {e.n_cell}",
        f"- Effective number of precedents: {e.n_eff:.1f}",
        f"- Base rate of significant positive results in the cell (P0): {_num(e.base_rate_sig_pos)}",
        "", "## Prediction", "",
    ]
    if _issued(card):
        out += [
            f"- P(significant and positive): {_num(p.p_sig)}",
            f"- Point estimate: {_num(p.point, 2)} {u}",
            f"- 80 percent interval for the true effect: {_num(p.interval_80[0], 2)} to {_num(p.interval_80[1], 2)} {u}",
            *([f"- 80 percent interval for the result of the test at the planned standard error: {_num(p.interval_80_y[0], 2)} to "
               f"{_num(p.interval_80_y[1], 2)} {u}"] if p.interval_80_y else []),
            f"- P(true effect above 0): {_num(p.p_win)}",
            f"- Rung: {p.rung}, weight on precedents {_num(p.lam, 1)}",
        ]
    else:
        out += ["- No usable prediction is issued."]
        if p.p0_p_sig is not None:
            out += [f"- This is the base rate the card declined to improve on, not a forecast of this test: P(significant and positive) "
                    f"{_num(p.p0_p_sig)}, mean effect in the cell {_num(p.p0_mean, 2)} {u}"]
        else:
            out += ["- P0 is unavailable because the cell has no visible rows."]
    out += ["", "## Team forecast", ""]
    if card.team_forecast is None:
        out += ["- None provided."]
    else:
        t = card.team_forecast
        out += [
            f"- Frozen at {t.frozen_at.isoformat()}: P(true effect above 0) {_num(t.p_win_team)}, "
            f"point forecast {_num(t.point_team, 2)} {u}"
        ]
        if _issued(card):
            out += [f"- Model, side by side: P(true effect above 0) {_num(p.p_win)}, point estimate {_num(p.point, 2)} {u}"]
    if card.second_opinion is not None:
        out += ["", "## Second opinion", ""] + _second_opinion_lines(card)
    if card.guardrails:
        out += ["", "## Guardrails", "",
                "p_harm is the probability that the true effect on the metric is worse than minus the margin, "
                "from the same ladder as the primary metric."]
        for g in card.guardrails:
            if g.status == "issue":
                out += [f"- {g.cell}: P(true effect below -{g.delta:g}) {_num(g.p_harm)}, point estimate {_num(g.point, 2)} {u}, "
                        f"90 percent interval {_num(g.interval_90[0], 2)} to {_num(g.interval_90[1], 2)} {u}, based on {g.n_cell} rows"]
            else:
                out += [f"- {g.cell}: abstained, no p_harm is shown."] + [f"  - Reason {rs}: {g.details.get(rs, rs)}" for rs in g.reasons]
    need = f"{rb.dismissals_needed}" if rb.dismissals_needed is not None else f"more than {rb.k}"
    out += ["", "## Robustness", ""]
    if not _issued(card):
        out += ["- Not shown: an abstained card issues no opinion for a robustness number to describe."]
    elif not rb.applicable:
        out += ["- Not applicable: the weight on precedents is zero, so the card uses the cell prior and no precedent can change it."]
    else:
        out += [
            f"- Top precedents considered (k = round of the effective number): {rb.k}",
            f"- Precedents to dismiss, highest weight first, to move p_sig across {rb.action_threshold}: {need}",
            f"- Share of {rb.resamples} resamples by test with p_sig on the same side of {rb.action_threshold}: {_num(rb.bootstrap_same_side, 2)}",
        ]
    out += ["", "## Skill at this n", ""]
    out += _skill_lines(sk)
    out += ["", "## Abstention", "", f"- Status: {card.abstention.status}"]
    if card.abstention.reasons:
        for reason in card.abstention.reasons:
            out += [f"- Reason {reason}: {card.abstention.details.get(reason, reason)}"]
    else:
        out += ["- Reasons: none"]
    out += ["", "---", "", card.footer]
    return "\n".join(out) + "\n"


def with_second_opinion(card: Card, provider_id: str, version: str, knowledge_cutoff: str | None, p_ai: float | None, weight: float,
                        contaminated: bool = False) -> Card:
    """A copy of the card carrying the outside agent's opinion; the card id is recomputed over the new content.

    The stack is computed only for an issued card with an opinion. At weight 0 it equals ``p_sig``.
    """
    from mootcourt.predictors.second_opinion import stack

    p_stack = None
    if not _issued(card):
        p_ai = None                                # an abstained card shows no estimate, the agent's included
    if _issued(card) and p_ai is not None and card.prediction.p_sig is not None:
        p_stack = stack(card.prediction.p_sig, p_ai, weight)
    view = SecondOpinionView(provider_id, version, knowledge_cutoff, p_ai, float(weight), p_stack, bool(contaminated) and float(weight) > 0.0)
    card = dataclasses.replace(card, second_opinion=view)
    return dataclasses.replace(card, card_id=content_id(card))


# ------------------------------------------------------------------ freeze
def freeze_or_load(card: Card, cards_dir) -> dict:
    """Freeze ``card``, or return the content already frozen under its id.

    The returned dict is the JSON of the file on disk. When a file with this id exists and its content
    differs from ``card`` the call raises ``CardFrozenError``: the caller never shows a card that differs
    from the record kept.
    """
    try:
        freeze_card(card, cards_dir)
    except CardFrozenError:
        on_disk = json.loads((Path(cards_dir) / f"{card.card_id}.json").read_text(encoding="utf-8"))
        if on_disk != json.loads(json.dumps(to_json(card), sort_keys=True)):
            raise CardFrozenError(f"card {card.card_id} is frozen with different content") from None
        return on_disk
    return to_json(card)


def _create_exclusive(tmp: str, final: Path, card: Card) -> None:
    """Copy the synced temporary file to ``final`` with an exclusive create; used where hard links are unavailable."""
    try:
        fd = os.open(final, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError:
        raise CardFrozenError(f"card {card.card_id} is already frozen") from None
    try:
        with os.fdopen(fd, "wb") as out, open(tmp, "rb") as src:
            out.write(src.read())
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        try:
            os.unlink(final)
        except OSError:
            pass
        raise
    safe_chmod(final, 0o444)


def freeze_card(card: Card, cards_dir) -> Path:
    """Write ``cards/<card_id>.json`` atomically and read-only; refuse to overwrite.

    The file is written and synced under a temporary name, then hard-linked to its final name, which
    fails if the name exists, so a second call can never replace a frozen card.
    """
    cards_dir = Path(cards_dir)
    cards_dir.mkdir(parents=True, exist_ok=True)
    final = cards_dir / f"{card.card_id}.json"
    fd, tmp = tempfile.mkstemp(dir=cards_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(to_json(card), fh, indent=1, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        safe_chmod(tmp, 0o444)
        try:
            os.link(tmp, final)
        except FileExistsError:
            raise CardFrozenError(f"card {card.card_id} is already frozen") from None
        except OSError:
            _create_exclusive(tmp, final, card)   # no hard links on this volume (exFAT): exclusive create instead
    finally:
        os.unlink(tmp)
    return final


def load_reliability_report(reports_dir, source: str) -> dict | None:
    """Read ``reports/reliability-<source>.json`` or return None when it does not exist."""
    path = Path(reports_dir) / f"reliability-{source}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def time_issue(bundle: ModelBundle, request: CardRequest, reliability: dict | None, now: dt.datetime | None = None,
               config: AbstainConfig | None = None, gates: dict | None = None) -> tuple[Card, float]:
    """Build a card and return it with the issue time in seconds (the bundle is already in memory)."""
    t = time.perf_counter()
    card = build_card(bundle, request, reliability=reliability, now=now, config=config, gates=gates)
    return card, time.perf_counter() - t
