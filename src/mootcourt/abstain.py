"""Abstention: four triggers, any one of which makes the card abstain.

1. Support. Fewer than 30 admitted rows visible at the origin in the kind-of-change cell, counted after
   pooling across periods (documented call).
2. Novelty. The query's kernel density among the cell's visible rows is below the 5th percentile of the
   leave-one-out density of those rows. The threshold is computed at fit and stored with the model.
3. Reliability. The reliability report for the cell is missing, older than 14 days, marks the cell
   drifted, or its rolling log score has been below the drift threshold for two consecutive weekly joins.
4. Decision instability. Resampling precedents by test (200 resamples, seeded) puts ``p_sig`` on the same
   side of the action threshold ``a`` as the full-sample ``p_sig`` in 80 percent or fewer of resamples.
   The resample is vectorized over the stored top-M neighbors with multinomial test counts; the part of
   the visible rows beyond the top M is kept fixed (documented call).

``p_sig`` here is the probability that the observed estimate is significant and positive (unitless).
Units: ``y``, ``s`` and ``s_star`` are in the units of y. Origin semantics: all inputs describe rows with
status admitted and ``usable_after <= origin``.

Reliability report schema (also used by ``loop.py``), one JSON document per source::

    {"source": str, "as_of": ISO-8601 with offset,
     "cells": {cell: {"as_of", "rolling_logscore", "p0_rolling_logscore", "brier_skill", "n",
                      "drifted", "consecutive_below"}}}
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import TypedDict

import numpy as np
from scipy import special

from mootcourt.config import (
    ACTION_THRESHOLD,
    BOOTSTRAP_RESAMPLES,
    DRIFT_CONSECUTIVE,
    NOVELTY_PERCENTILE,
    RELIABILITY_MAX_AGE_DAYS,
    SAME_SIDE_FRACTION,
    SUPPORT_MIN,
    Z,
)

TRIGGERS = ("support", "novelty", "reliability", "instability")


class CellReliability(TypedDict):
    """Rolling reliability of one cell, written by the weekly join."""

    as_of: str
    rolling_logscore: float
    p0_rolling_logscore: float
    brier_skill: float
    n: int
    drifted: bool
    consecutive_below: int


class ReliabilityReport(TypedDict):
    """Reliability report of one source."""

    source: str
    as_of: str
    cells: dict[str, CellReliability]


@dataclass(frozen=True)
class AbstainConfig:
    """Thresholds of the four triggers.

    ``disabled`` names triggers that are never evaluated: they add no reason and cannot make a card abstain, and the other
    triggers are computed exactly as before. It exists for the trigger-removal ablation of a backtest; the card, the service
    and the weekly loop always use the empty set.
    """

    support_min: int = SUPPORT_MIN
    novelty_percentile: float = NOVELTY_PERCENTILE
    reliability_max_age_days: int = RELIABILITY_MAX_AGE_DAYS
    drift_consecutive: int = DRIFT_CONSECUTIVE
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES
    action_threshold: float = ACTION_THRESHOLD
    same_side_fraction: float = SAME_SIDE_FRACTION
    disabled: frozenset = frozenset()

    def __post_init__(self) -> None:
        names = frozenset(self.disabled)
        unknown = sorted(names - set(TRIGGERS))
        if unknown:
            raise ValueError(f"unknown trigger {', '.join(unknown)}; the triggers are {', '.join(TRIGGERS)}")
        object.__setattr__(self, "disabled", names)

    def enabled(self, trigger: str) -> bool:
        """False for a trigger switched off (``--drop-trigger`` in a backtest); a live card never switches one off."""
        return trigger not in self.disabled


@dataclass(frozen=True)
class AbstainDecision:
    """Result of ``decide``: ``status`` is ``issue`` or ``abstain``; ``reasons`` lists every trigger that fired."""

    status: str
    reasons: tuple
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class InstabilityResult:
    """Outcome of the by-test bootstrap."""

    fires: bool
    same_side_fraction: float
    p_sig: float
    resamples: int


def check_support(n_visible: int, config: AbstainConfig | None = None) -> bool:
    """True (fires) when fewer than ``support_min`` admitted rows are visible in the cell."""
    if n_visible < 0:
        raise ValueError("n_visible must be nonnegative")
    return n_visible < (config or AbstainConfig()).support_min


def check_novelty(density: float, threshold: float) -> bool:
    """True (fires) when the query density is below the stored leave-one-out threshold."""
    return density < threshold


def _parse_time(value) -> dt.datetime:
    t = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(value)
    if t.tzinfo is None:
        raise ValueError("reliability timestamps must carry an offset")
    return t


def staleness_reason(as_of, now: dt.datetime, max_age_days: int = RELIABILITY_MAX_AGE_DAYS) -> str | None:
    """Why a reliability timestamp is unusable at ``now`` (dated after it, or older than ``max_age_days``), else None.

    The one rule the card and ``moot doctor`` share: an exact time comparison, not a whole-day count.
    """
    as_of = _parse_time(as_of)
    if as_of > now:
        return "reliability report is dated after the issue time"
    if now - as_of > dt.timedelta(days=max_age_days):
        return f"reliability report is older than {max_age_days} days"
    return None


def reliability_reason(report, cell: str, now: dt.datetime, config: AbstainConfig | None = None) -> str | None:
    """Why the reliability trigger fires, or None when the cell's report is fresh and not drifting."""
    cfg = config or AbstainConfig()
    if report is None:
        return "reliability report is missing"
    entry = report.get("cells", {}).get(cell)
    if entry is None:
        return f"reliability report has no entry for cell {cell}"
    stale = staleness_reason(entry.get("as_of") or report["as_of"], now, cfg.reliability_max_age_days)
    if stale:
        return stale
    if entry.get("drifted"):
        return f"cell {cell} is marked drifted"
    if entry.get("consecutive_below", 0) >= cfg.drift_consecutive:
        return f"rolling log score below the drift threshold for {entry['consecutive_below']} consecutive joins (drift)"
    return None


def check_reliability(report, cell: str, now: dt.datetime, config: AbstainConfig | None = None) -> bool:
    """True (fires) when the reliability report is missing, stale, drifted or below threshold twice in a row."""
    return reliability_reason(report, cell, now, config) is not None


def check_instability(state, s_star: float, seed: int = 0, config: AbstainConfig | None = None) -> InstabilityResult:
    """Bootstrap the precedents by test and test whether ``p_sig`` stays on one side of the action threshold.

    ``state`` is a P2 ``NeighborState``; ``s_star`` is the standard error of the future estimate (units of y).
    Each resample draws test counts from a multinomial over the distinct tests and multiplies every
    precedent's weight by its test's count. Returns the fraction of resamples on the same side of the
    threshold as the full-sample ``p_sig`` and whether it is at or below ``same_side_fraction``.
    """
    cfg = config or AbstainConfig()
    full = state.moments()
    p_full = _p_sig(full.theta_hat, full.v, s_star)
    if len(state.row_ids) == 0 or state.lam == 0.0:
        return InstabilityResult(False, 1.0, p_full, 0)
    tests, test_index = np.unique(np.asarray(state.test_ids), return_inverse=True)
    n_tests = len(tests)
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(n_tests, np.full(n_tests, 1.0 / n_tests), size=cfg.bootstrap_resamples).astype(np.float64)
    mult = counts[:, test_index]
    tau2 = state.tau * state.tau
    var = state.s ** 2 + tau2
    w = state.kernel / var
    t_sw, t_swy, t_sw2v, _ = state.tail
    sw = mult @ w + t_sw
    ok = sw > 0
    sw_safe = np.where(ok, sw, 1.0)
    m = (mult @ (w * state.y) + t_swy) / sw_safe
    v_m = (mult @ (w * w * var) + t_sw2v) / (sw_safe * sw_safe)
    theta = state.lam * m + (1.0 - state.lam) * state.mu
    v = state.lam * (v_m + state.tau_res2) + (1.0 - state.lam) * tau2
    p = _p_sig(theta, v, s_star)
    above = p >= cfg.action_threshold
    same = above == (p_full >= cfg.action_threshold)
    frac = float(np.mean(same[ok])) if ok.any() else 1.0
    return InstabilityResult(frac <= cfg.same_side_fraction, frac, p_full, int(cfg.bootstrap_resamples))


def _p_sig(theta_hat, v, s_star: float, z: float = Z):
    return special.ndtr((np.asarray(theta_hat) - z * s_star) / np.sqrt(np.asarray(v) + s_star * s_star))


def decide(
    *,
    n_support: int,
    density: float,
    density_threshold: float,
    reliability_report,
    cell: str,
    now: dt.datetime,
    neighbor_state=None,
    s_star: float = 1.0,
    config: AbstainConfig | None = None,
    seed: int = 0,
) -> AbstainDecision:
    """Run all four triggers; abstain when any fires and list every reason that fired.

    ``neighbor_state`` may be None (for example when there are no precedents), in which case the
    instability check is skipped and noted in ``details``.
    """
    cfg = config or AbstainConfig()
    reasons, details = [], {}
    if cfg.enabled("support") and check_support(n_support, cfg):
        reasons.append("support")
        details["support"] = f"{n_support} admitted rows visible in the cell, fewer than {cfg.support_min}"
    if cfg.enabled("novelty") and check_novelty(density, density_threshold):
        reasons.append("novelty")
        details["novelty"] = f"query density {density:.4g} is below the stored leave-one-out threshold {density_threshold:.4g}"
    why = reliability_reason(reliability_report, cell, now, cfg) if cfg.enabled("reliability") else None
    if why is not None:
        reasons.append("reliability")
        details["reliability"] = why
    if not cfg.enabled("instability"):
        details["instability_check"] = "disabled for this run"
    elif neighbor_state is not None:
        res = check_instability(neighbor_state, s_star, seed=seed, config=cfg)
        details["instability_same_side_fraction"] = res.same_side_fraction
        if res.fires:
            reasons.append("instability")
            details["instability"] = (
                f"p_sig stays on one side of {cfg.action_threshold} in {res.same_side_fraction:.0%} of "
                f"{res.resamples} resamples by test, at most {cfg.same_side_fraction:.0%}"
            )
    else:
        details["instability_check"] = "skipped: no precedents"
    return AbstainDecision("abstain" if reasons else "issue", tuple(reasons), details)
