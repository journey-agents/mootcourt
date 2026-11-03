"""The operational loop: join outcomes to issued cards, type each miss, rewrite reliability, mark drift.

``join_new_rows`` is the weekly step. It appends new concluded rows to the ledger (idempotent on the row id),
writes a snapshot when the ledger changed, writes ``cards/outcomes/<card_id>.json`` for every issued card whose
row is now in the ledger (card files are never touched, outcome files are written once), and rewrites
``reports/reliability-<source>.json`` from the outcomes of the trailing eight weeks. Drift and the reliability
window are in ``reliability.py``.

Miss types, one per joined card, in this precedence (builder call 14):

1. ``abstained_but_clear``: the card abstained and ``|y| > z s`` (the result was clear after all).
2. ``confident_but_wrong``: it did not abstain, and either ``p_sig >= 0.6`` while ``y <= z s`` or
   ``p_sig <= 0.1`` while ``y > z s``.
3. ``direction_miss``: the sign of the point estimate differs from the sign of ``y`` and ``|y| > s``.
4. ``magnitude_miss``: the direction is right but ``y`` is outside the 90 percent interval.
5. ``hit``.

Scoring an outcome. ``y`` and ``s`` are the realized estimate and standard error of the ledger row; ``s`` defines the
event only. The model log score is that of ``Normal(point, sd_theta^2 + s_star^2)`` with the ``s_star`` the card
recorded at issue (the scale known before launch, as in the backtest), where ``point`` and the 90 percent interval of theta come from
the frozen card (the working predictive of an issued P2 card is exactly Normal; a card that fell back to P1's
t prior is scored by this Normal approximation). Abstained cards have no model log score (``null``) and are not
counted in reliability, because the card made no claim. The baseline log score is P0 refit on the ledger rows
visible at the card's origin. Brier compares ``p_sig`` with the event ``y > z s``; the Brier baseline is the
cell's significant-positive base rate stored on the card.

Units: ``y``, ``s`` and the point estimate are in the source's unit (percentage points for Upworthy); probabilities
are unitless; log scores are per unit of y.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from mootcourt.config import Z
from mootcourt.ledger import ADMITTED, append_rows, ensure_snapshot, read_ledger, write_ledger
from mootcourt.predictors.base import Predictive, build_grid
from mootcourt.predictors.p0 import P0Predictor
from mootcourt.reliability import build_reliability, mark_drift  # noqa: F401  (mark_drift is part of this module's API)
from mootcourt.storage import safe_chmod, visible_glob

P_CONFIDENT_HIGH = 0.6
P_CONFIDENT_LOW = 0.1
MISS_TYPES = ("abstained_but_clear", "confident_but_wrong", "direction_miss", "magnitude_miss", "hit")
_Z90 = float(stats.norm.ppf(0.95))
LOG = logging.getLogger("mootcourt.loop")


def type_miss(*, abstained: bool, p_sig: float | None, point: float | None, interval90: tuple | None, y: float, s: float) -> str:
    """Type one joined card; see the module docstring for the precedence. Raises ValueError unless ``s > 0``."""
    if not s > 0:
        raise ValueError("s must be positive")
    event = y > Z * s
    if abstained:
        return "abstained_but_clear" if abs(y) > Z * s else "hit"
    if p_sig is not None and ((p_sig >= P_CONFIDENT_HIGH and not event) or (p_sig <= P_CONFIDENT_LOW and event)):
        return "confident_but_wrong"
    if point is not None and np.sign(point) != np.sign(y) and abs(y) > s:
        return "direction_miss"
    if interval90 is not None and not (interval90[0] <= y <= interval90[1]):
        return "magnitude_miss"
    return "hit"


def update_reliability(prev: dict | None, outcomes, now: dt.datetime, advance: bool = True, source: str | None = None) -> dict:
    """Rewrite the reliability report as of ``now``; see ``reliability.build_reliability``."""
    return build_reliability(prev, outcomes, now, advance=advance, source=source)


# ------------------------------------------------------------------ outcomes
def _atomic_write(path: Path, text: str, read_only: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    if read_only:
        safe_chmod(tmp, 0o444)
    os.replace(tmp, path)


def _forecast_logscore(point, interval90, y: float, s: float) -> float | None:
    """Log score of the Normal forecast described by a point and a 90 percent interval; None without both."""
    if interval90 is None or point is None:
        return None
    sd = max((interval90[1] - interval90[0]) / (2.0 * _Z90), 1e-6)
    grid = build_grid(point, sd)
    return float(Predictive.from_normal(grid, point, sd).logscore(y, s))


def _model_logscore(card: dict, y: float, s: float) -> float | None:
    pred = card["prediction"]
    if card["abstention"]["status"] != "issue":
        return None
    return _forecast_logscore(pred.get("point"), pred.get("interval_90"), y, s)


def outcome_from_card(card: dict, row, p0: P0Predictor, now: dt.datetime, forecast: dict | None = None) -> dict | None:
    """The outcome of one issued card given its ledger row, or None while the row's registered horizon has not passed at ``now``.

    ``card`` is the frozen card JSON, ``row`` the admitted ledger row (a mapping with ``y``, ``s`` and ``usable_after``), ``p0`` the
    baseline fitted on the ledger. The miss type always follows the card as issued. ``forecast`` (a dict with ``point``,
    ``interval_90`` and ``p_sig``) replaces the forecast that is scored: the weekly join scores only issued cards and passes
    nothing, while the replay of an archive scores the forecast an abstained card would have made, as the backtest does, so the
    reliability report has evidence in cells where every card abstained.
    """
    if pd.Timestamp(row["usable_after"]) > pd.Timestamp(now):      # horizon guard: no outcome before its registered horizon
        return None
    y, s = float(row["y"]), float(row["s"])
    star = card["request"].get("s_star")
    has_star = star is not None and math.isfinite(float(star)) and float(star) > 0
    if not has_star:        # no scale was known at issue: a log score on the realized s would leak the result (REV-039)
        LOG.warning("card %s has no usable s_star; its log scores are left null and it is excluded from reliability", card["card_id"])
    s_card = float(star) if has_star else s      # log scores use the scale known at issue, as in the backtest
    pred, issued = card["prediction"], card["abstention"]["status"] == "issue"
    event = y > Z * s
    iv = tuple(pred["interval_90"]) if issued and pred.get("interval_90") else None
    base = card["evidence"].get("base_rate_sig_pos")
    origin = dt.datetime.fromisoformat(card["origin"])
    scored = forecast if forecast is not None else ({"point": pred.get("point"), "interval_90": pred.get("interval_90"), "p_sig": pred.get("p_sig")}
                                                    if issued else None)
    try:
        p0_ls = float(p0.predict(None, s_card, card["cell"], origin).logscore(y, s_card)) if has_star else None
    except ValueError:          # no row was visible at the card's origin: there is no baseline to compare with
        p0_ls = None
    p_scored = None if scored is None else scored.get("p_sig")
    return {
        "card_id": card["card_id"], "row_id": card["request"].get("row_id"), "source": card["source"], "cell": card["cell"],
        "model_id": card["model_id"],
        "snapshot_id": card["snapshot_id"], "y": y, "s": s, "event": bool(event), "abstained": not issued,
        "p_sig": pred.get("p_sig") if issued else None, "point": pred.get("point") if issued else None, "interval_90": list(iv) if iv else None,
        "miss_type": type_miss(abstained=not issued, p_sig=pred.get("p_sig") if issued else None, point=pred.get("point") if issued else None,
                               interval90=iv, y=y, s=s),
        "logscore": (_forecast_logscore(scored.get("point"), scored.get("interval_90"), y, s_card)
                     if scored is not None and has_star else None),
        "p0_logscore": p0_ls,
        "brier": float((p_scored - event) ** 2) if p_scored is not None else None,
        "p0_brier": float((base - event) ** 2) if base is not None else None,
        "at": pd.Timestamp(row["usable_after"]).isoformat(), "joined_at": now.isoformat(),
    }


def attach_outcomes(cards_dir, ledger: pd.DataFrame, source: str, now: dt.datetime, p0: P0Predictor | None = None) -> list[dict]:
    """Write ``cards/outcomes/<card_id>.json`` for each issued card of ``source`` whose row is now in the ledger.

    Existing outcome files are left alone (they are written once). Returns the outcomes written. Card files are
    only read. Rows that are not admitted (excluded from scoring) get no outcome. Horizon guard (builder call 42):
    a row whose ``usable_after`` is after ``now`` gets no outcome yet; it is attached by the first later join whose
    ``now`` is at or after ``usable_after``.
    """
    cards_dir = Path(cards_dir)
    adm = ledger.loc[ledger["status"] == ADMITTED].set_index("row_id")
    p0 = p0 or P0Predictor().fit(ledger.loc[(ledger["status"] == ADMITTED) & (ledger["source"] == source)])
    written = []
    for path in visible_glob(cards_dir, "*.json"):
        card = json.loads(path.read_text(encoding="utf-8"))
        out_path = cards_dir / "outcomes" / f"{card['card_id']}.json"
        row_id = card["request"].get("row_id")
        if card["source"] != source or not row_id or row_id not in adm.index or out_path.exists():
            continue
        outcome = outcome_from_card(card, adm.loc[row_id], p0, now)
        if outcome is None:
            continue
        _atomic_write(out_path, json.dumps(outcome, indent=1, sort_keys=True) + "\n", read_only=True)
        written.append(outcome)
    return written


def load_outcomes(cards_dir, source: str) -> list[dict]:
    """All outcome files of a source in the reliability schema (issued cards only, where both scores exist)."""
    rows = []
    for path in visible_glob(Path(cards_dir) / "outcomes", "*.json"):
        o = json.loads(path.read_text(encoding="utf-8"))
        if o["source"] != source or None in (o["logscore"], o["p0_logscore"], o["brier"], o["p0_brier"]):
            continue
        rows.append({"cell": o["cell"], "at": o["at"], "logscore": o["logscore"], "p0_logscore": o["p0_logscore"],
                     "brier": o["brier"], "p0_brier": o["p0_brier"]})
    return rows


# --------------------------------------------------------------------- join
@dataclass(frozen=True)
class JoinResult:
    """What a join did."""

    n_new_rows: int
    n_outcomes: int
    snapshot_id: str | None
    reliability_path: Path
    miss_counts: dict


def join_new_rows(loader: Callable[[], pd.DataFrame], *, ledger_dir, cards_dir, reports_dir, source: str,
                  now: dt.datetime | None = None) -> JoinResult:
    """One weekly join. ``loader()`` returns the concluded rows to add (a ledger frame, possibly empty).

    Idempotent: with the same inputs a second call finds no new rows and no new outcomes and changes nothing
    except the reliability ``as_of`` stamp (which is the same ``now`` in a repeated call).
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    ledger_path = Path(ledger_dir) / "ledger.parquet"
    existing = read_ledger(ledger_path)
    merged = append_rows(existing, loader())
    n_new = len(merged) - len(existing)
    snapshot = None
    if n_new > 0:
        write_ledger(merged, ledger_path)
        snapshot = ensure_snapshot(merged[merged["source"] == source].reset_index(drop=True), ledger_dir)
    written = attach_outcomes(cards_dir, merged, source, now)
    reports_dir = Path(reports_dir)
    path = reports_dir / f"reliability-{source}.json"
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    report = update_reliability(prev, load_outcomes(cards_dir, source), now, advance=bool(written), source=source)
    _atomic_write(path, json.dumps(report, indent=1, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for o in written:
        counts[o["miss_type"]] = counts.get(o["miss_type"], 0) + 1
    return JoinResult(n_new, len(written), snapshot, path, counts)


def join_command(source: str, ledger_dir, cards_dir, reports_dir, new_rows_path=None, now: dt.datetime | None = None) -> JoinResult:
    """The ``moot join`` step: pick the loader for the source and run ``join_new_rows``.

    The real archives are static, so by default a join of ``upworthy``, ``asos`` or ``synthetic`` appends nothing
    new; ``new_rows_path`` names a ledger parquet of concluded rows to append (a stream, or a test).
    """
    ledger_path = Path(ledger_dir) / "ledger.parquet"
    if new_rows_path is not None:
        def loader():
            return read_ledger(new_rows_path)
    else:
        def loader():
            return read_ledger(ledger_path).iloc[0:0]
    return join_new_rows(loader, ledger_dir=ledger_dir, cards_dir=cards_dir, reports_dir=reports_dir, source=source, now=now)
