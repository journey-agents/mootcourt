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
from scipy import special

from mootcourt.abstain import AbstainConfig, AbstainDecision, check_instability, decide, reliability_reason
from mootcourt.bundle import ModelBundle
from mootcourt.config import ACTION_THRESHOLD, BOUNDARY_SENTENCE, Z
from mootcourt.predictors.p2 import NeighborState
from mootcourt.predictors.p3 import TeamForecast
from mootcourt.storage import safe_chmod


class CardFrozenError(FileExistsError):
    """A frozen card with this id already exists and is never overwritten."""


# ----------------------------------------------------------------- request
@dataclass(frozen=True)
class CardRequest:
    """What the caller asks about: a proposed change and its planned exposure.

    ``impressions`` is the planned exposures per arm. ``origin`` is when the card stands (default: now);
    ``team_forecast`` is the team's own forecast, stored frozen. ``cell`` overrides the derived cell (needed
    for sources whose cell is a metric id).
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


@dataclass(frozen=True)
class Robustness:
    """Section 5: how fragile the opinion is."""

    k: int
    dismissals_needed: int | None
    bootstrap_same_side: float
    action_threshold: float
    resamples: int


@dataclass(frozen=True)
class Skill:
    """Section 6: the cell's latest Brier skill against P0 from the reliability report."""

    available: bool
    brier_skill: float | None
    n: int | None
    as_of: str | None


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


def _p_sig_closed(sw, swy, sw2v, lam, mu, tau, tau_res2, s_star, z=Z):
    m = swy / sw
    v_m = sw2v / (sw * sw)
    theta = lam * m + (1.0 - lam) * mu
    v = lam * (v_m + tau_res2) + (1.0 - lam) * tau * tau
    return float(special.ndtr((theta - z * s_star) / math.sqrt(v + s_star * s_star)))


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
    start_above = _p_sig_closed(sw, swy, sw2v, st.lam, st.mu, st.tau, st.tau_res2, s_star) >= threshold
    for step, i in enumerate(order[:k], start=1):
        sw -= w[i]
        swy -= w[i] * st.y[i]
        sw2v -= w[i] * w[i] * var[i]
        if sw <= 1e-12 * max(1.0, w.sum()):
            return None
        above = _p_sig_closed(sw, swy, sw2v, st.lam, st.mu, st.tau, st.tau_res2, s_star) >= threshold
        if above != start_above:
            return step
    return None


def _iso(t: dt.datetime) -> str:
    if t.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return t.isoformat()


def build_card(
    bundle: ModelBundle,
    request: CardRequest,
    reliability: dict | None = None,
    now: dt.datetime | None = None,
    config: AbstainConfig | None = None,
) -> Card:
    """Issue a card from a fitted bundle.

    ``reliability`` is the source's reliability report (or None); ``now`` is the issue time (injectable).
    Raises ValueError if the bundle lacks a snapshot id, model id or feature hash, or the request is invalid.
    """
    for name in ("snapshot_id", "model_id", "feature_hash"):
        if not getattr(bundle, name):
            raise ValueError(f"cannot issue a card: the bundle has no {name}")
    cfg = config or AbstainConfig()
    now = now or dt.datetime.now(dt.timezone.utc)
    origin = request.origin or now
    cell = request.cell or derive_cell(request.source, request.image_changed, request.headline_changed)
    s_star = bundle.s_star(cell, request.impressions)
    echo = RequestEcho(request.headline, bool(request.image_changed), bool(request.headline_changed),
                       int(request.impressions), s_star, request.row_id)
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
                         Robustness(0, None, 1.0, cfg.action_threshold, 0), _skill(reliability, cell), decision)
    x = bundle.transform_text(request.headline, request.image_changed, cell=cell, exposure=request.impressions)
    state = bundle.neighbor_state(x, cell, origin)
    p0 = bundle.p0.predict(x, s_star, cell, origin)
    main = bundle.p2.predictive_from_state(state, x, s_star, cell, origin)
    mo = state.moments() if (len(state.row_ids) or state.tail[0] > 0) else None
    n_eff = mo.n_eff if mo else 0.0
    evidence = Evidence(n_cell, float(n_eff), bundle.base_rate(cell, origin))
    prediction = Prediction(
        "P2", state.lam, main.p_sig(s_star), main.mean(), tuple(main.interval(0.8)), tuple(main.interval(0.9)),
        main.p_win(0.0), p0.p_sig(s_star), p0.mean(),
    )
    k = max(1, int(round(n_eff))) if n_eff else 0
    inst = check_instability(state, s_star, seed=0, config=cfg)
    robust = Robustness(k, robustness_dismissals(state, s_star, cfg.action_threshold, k), inst.same_side_fraction,
                        cfg.action_threshold, inst.resamples)
    decision = decide(
        n_support=n_cell, density=bundle.density(x, cell, origin), density_threshold=bundle.novelty_threshold(cell),
        reliability_report=reliability, cell=cell, now=now, neighbor_state=state, s_star=s_star, config=cfg,
    )
    card = _assemble(bundle, request, cell, origin, now, echo, evidence, prediction, robust, _skill(reliability, cell), decision)
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
    s_star = bundle.s_star(g.cell, request.impressions)
    x = bundle.transform_text(request.headline, request.image_changed, cell=g.cell, exposure=request.impressions)
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


def _skill(reliability: dict | None, cell: str) -> Skill:
    entry = (reliability or {}).get("cells", {}).get(cell)
    if not entry:
        return Skill(False, None, None, None)
    return Skill(True, entry.get("brier_skill"), entry.get("n"), entry.get("as_of"))


def content_id(card: Card) -> str:
    """Card id: 16 hex characters of sha256 over the full card content without the id (sorted keys).

    Anything shown on the card, the reliability state and the team forecast included, therefore changes the id.
    """
    body = {k: v for k, v in to_json(card).items() if k != "card_id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _assemble(bundle, request, cell, origin, now, echo, evidence, prediction, robust, skill, decision) -> Card:
    issued, origin_s = _iso(now), _iso(origin)
    card = Card("", request.source, cell, origin_s, bundle.snapshot_id, bundle.model_id, bundle.feature_hash,
                issued, echo, evidence, prediction, request.team_forecast, robust, skill, decision, BOUNDARY_SENTENCE)
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
    """JSON-safe dict of the card. An abstained card carries only P0 in ``prediction``."""
    p = card.prediction
    p0 = None if p.p0_p_sig is None else {"p_sig": p.p0_p_sig, "mean": p.p0_mean}
    if _issued(card):
        prediction = {
            "rung": p.rung, "lambda": p.lam, "p_sig": p.p_sig, "point": p.point,
            "interval_80": list(p.interval_80) if p.interval_80 else None,
            "interval_90": list(p.interval_90) if p.interval_90 else None,
            "p_win": p.p_win, "p0": p0,
        }
    else:
        prediction = {"rung": "P0", "p0": p0}
    team = None if card.team_forecast is None else card.team_forecast.to_dict()
    out = {
        "card_id": card.card_id, "source": card.source, "cell": card.cell, "origin": card.origin,
        "snapshot_id": card.snapshot_id, "model_id": card.model_id, "feature_hash": card.feature_hash,
        "issued_at": card.issued_at,
        "request": dataclasses.asdict(card.request),
        "evidence": dataclasses.asdict(card.evidence),
        "prediction": prediction,
        "team_forecast": team,
        "robustness": dataclasses.asdict(card.robustness),
        "skill": dataclasses.asdict(card.skill),
        "abstention": {"status": card.abstention.status, "reasons": list(card.abstention.reasons),
                       "details": {k: v for k, v in card.abstention.details.items()}},
        "footer": card.footer,
    }
    if card.second_opinion is not None:
        out["second_opinion"] = dataclasses.asdict(card.second_opinion)
    if card.guardrails:
        out["guardrails"] = [{"cell": g.cell, "delta": g.delta, "status": g.status, "reasons": list(g.reasons), "details": dict(g.details),
                              "n_cell": g.n_cell, "p_harm": g.p_harm, "point": g.point,
                              "interval_90": list(g.interval_90) if g.interval_90 else None} for g in card.guardrails]
    return out


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
            f"- P(true effect above 0): {_num(p.p_win)}",
            f"- Rung: {p.rung}, weight on precedents {_num(p.lam, 1)}",
        ]
    else:
        out += ["- No usable prediction is issued."]
        if p.p0_p_sig is not None:
            out += [f"- P0 base rate: P(significant and positive) {_num(p.p0_p_sig)}, mean effect in the cell {_num(p.p0_mean, 2)} {u}"]
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
    out += [
        "", "## Robustness", "",
        f"- Top precedents considered (k = round of the effective number): {rb.k}",
        f"- Precedents to dismiss, highest weight first, to move p_sig across {rb.action_threshold}: {need}",
        f"- Share of {rb.resamples} resamples by test with p_sig on the same side of {rb.action_threshold}: {_num(rb.bootstrap_same_side, 2)}",
        "", "## Skill at this n", "",
    ]
    if sk.available:
        out += [f"- Brier skill against P0: {_num(sk.brier_skill)} measured on {sk.n} rows, as of {sk.as_of}"]
    else:
        out += ["- Not measured: the reliability report has no entry for this cell."]
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
               config: AbstainConfig | None = None) -> tuple[Card, float]:
    """Build a card and return it with the issue time in seconds (the bundle is already in memory)."""
    t = time.perf_counter()
    card = build_card(bundle, request, reliability=reliability, now=now, config=config)
    return card, time.perf_counter() - t
