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
4. ``magnitude_miss``: the direction is right but ``y`` is outside the 90 percent interval of the observed estimate at the planned
   standard error (the interval the card stores for it; the interval for the true effect is narrower and would miss by construction).
5. ``hit``.

Scoring an outcome (round 00, docs/method.md calls 162 and 163). ``y`` and ``s`` are the realized estimate and standard error of the
ledger row; ``s`` defines the event only. The forecast that is scored is the card's own: the predictive it stored (family, degrees of
freedom, location, scale, grid and the planned ``s_star`` it recorded at issue, the scale known before launch, as in the backtest), so
the log score and the coverage of the 90 percent interval of the observed estimate are the backtest's, not those of a Normal rebuilt
from an interval. An ABSTAINED card is scored too: it keeps the forecast it withheld in a sealed block and the join scores that for
reliability, flagged (``abstained: true``), never dropped, so a cell whose entry is stale or marked drifted collects evidence and can
recover. This is the convention of the backtest and of the replay, and the replay calls this same function. A card from before schema
version 2 has no predictive and is scored by the Normal its point and interval imply (``legacy_normal: true``), and an abstained one has
no forecast to score. The baseline log score is P0 (the empirical base-rate forecaster) refit on the ledger rows visible at the card's
origin. Brier compares ``p_sig`` with the event ``y > z s``; the Brier baseline is the cell's significant-positive base rate stored on
the card.

Timing and one card per row (round 01, reviewer R2, docs/method.md calls 220 and 222). A card is pre-launch evidence only when both its
origin and its issue time are at or before the row's ``started_at``; a card that stood later is ``in_flight`` (before ``usable_after``) or
``after_result`` (at or after it), is recorded with the reason (``post_hoc: true``) and is never scored: no log score, no Brier, no miss
type, no reliability evidence. One card per row is scored, the earliest pre-launch card by issue time (the card id breaks a tie, and a row
already scored keeps its card); every other pre-launch card for the row is recorded as a reissue (``reissue: true``, ``superseded_by``) and
not scored. The replay issues one card per row at the week start on or before ``started_at``, so this rule changes none of its numbers.

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

from mootcourt.config import TRAILING_WEEKS, Z
from mootcourt.ledger import ADMITTED, append_rows, ensure_snapshot, read_ledger, write_ledger
from mootcourt.predictors.base import Predictive, build_grid
from mootcourt.predictors.p0 import P0Predictor
from mootcourt.reliability import build_reliability, mark_drift  # noqa: F401  (mark_drift is part of this module's API)
from mootcourt.storage import safe_chmod, visible_glob

P_CONFIDENT_HIGH = 0.6
P_CONFIDENT_LOW = 0.1
MISS_TYPES = ("abstained_but_clear", "confident_but_wrong", "direction_miss", "magnitude_miss", "hit")
TIMINGS = ("pre_launch", "in_flight", "after_result")
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


def card_forecast(card: dict) -> dict | None:
    """The forecast a card scores with: its issued prediction, or the one an abstained card withheld; None when there is none.

    Returns a dict with ``p_sig``, ``point``, ``interval_90_y`` (the interval of the observed estimate, None on a card of schema
    version 1), ``interval_90`` (of the true effect) and ``predictive`` (the stored spec with ``s_star``, None on version 1).
    """
    pred, issued = card["prediction"], card["abstention"]["status"] == "issue"
    src = pred if issued else card.get("withheld")
    if not src or src.get("p_sig") is None and src.get("point") is None:
        return None
    return {"p_sig": src.get("p_sig"), "point": src.get("point"), "interval_90": src.get("interval_90"), "interval_90_y": src.get("interval_90_y"),
            "predictive": src.get("predictive")}


def card_timing(card: dict, row) -> tuple[str, str | None]:
    """``(timing, reason)`` of a card against its ledger row (round 01, R2, docs/method.md call 220).

    ``pre_launch`` when the later of the card's origin and issue time is at or before the row's ``started_at`` (at the start instant the
    test has produced nothing yet, and the replay issues at the week start, which on the ASOS archive is the start instant of 44 of 337
    rows); ``in_flight`` when it is after the start and before ``usable_after``; ``after_result`` when it is at or after ``usable_after``.
    The reason is None for a pre-launch card and names the times otherwise.
    """
    issued, origin = pd.Timestamp(card["issued_at"]), pd.Timestamp(card["origin"])
    stood = max(issued, origin)
    started, usable = pd.Timestamp(row["started_at"]), pd.Timestamp(row["usable_after"])
    if stood <= started:
        return "pre_launch", None
    how = f"issued at {issued.isoformat()}" if issued >= origin else f"standing at an origin of {origin.isoformat()}"
    if stood < usable:
        return "in_flight", (f"card {how}, after the test started at {started.isoformat()} and before its result was usable at "
                             f"{usable.isoformat()}: in flight, not pre-launch evidence")
    return "after_result", (f"card {how}, at or after the result was usable at {usable.isoformat()} (the test started at "
                            f"{started.isoformat()}): post-hoc, not pre-launch evidence")


def _record(card: dict, row, now: dt.datetime) -> dict:
    """The part of an outcome record that describes the card and the row without scoring anything: every score null."""
    pred, issued = card["prediction"], card["abstention"]["status"] == "issue"
    iv = list(pred["interval_90"]) if issued and pred.get("interval_90") else None
    iv_y = list(pred["interval_90_y"]) if issued and pred.get("interval_90_y") else None
    return {
        "card_id": card["card_id"], "row_id": card["request"].get("row_id"),
        "test_id": row.get("test_id") if hasattr(row, "get") else None,
        "source": card["source"], "cell": card["cell"], "model_id": card["model_id"], "snapshot_id": card["snapshot_id"],
        "y": None, "s": None, "event": None, "abstained": not issued,
        "p_sig": pred.get("p_sig") if issued else None, "point": pred.get("point") if issued else None,
        "interval_90": iv, "interval_90_y": iv_y, "miss_type": None, "logscore": None, "p0_logscore": None, "scored_forecast": None,
        "legacy_normal": False, "covered_90": None, "brier": None, "p0_brier": None,
        "at": pd.Timestamp(row["usable_after"]).isoformat(), "joined_at": now.isoformat(),
        "card_issued_at": card["issued_at"], "card_origin": card["origin"], "row_started_at": pd.Timestamp(row["started_at"]).isoformat(),
        "timing": None, "post_hoc": False, "post_hoc_reason": None, "reissue": False, "superseded_by": None, "scored": False,
        "cell_mismatch": False, "cell_mismatch_reason": None,
        "ledger_snapshot_id": None,     # the snapshot that holds the outcome row, filled by the join that writes the record (call 249)
    }


def cell_mismatch_outcome(card: dict, row, now: dt.datetime) -> dict:
    """The record of a card whose ledger row has another cell than the card: not scored, no score of any kind (round 02, R2).

    The join matches a card to its row by row id, and the row's result is the result of the row's own metric, so a card issued for one
    cell would otherwise be scored against another metric's result and credited to the wrong cell's reliability entry."""
    why = (f"the card is for cell {card['cell']}, but its row {card['request'].get('row_id')} is in the ledger with cell {row['cell']}: "
           "scoring it would credit another metric's result to this cell")
    return {**_record(card, row, now), "cell_mismatch": True, "cell_mismatch_reason": why}


def reissue_outcome(card: dict, row, superseded_by: str, now: dt.datetime) -> dict:
    """The record of a pre-launch card for a row that another card already scores: not scored, pointing at the card that is."""
    return {**_record(card, row, now), "timing": "pre_launch", "reissue": True, "superseded_by": superseded_by}


def outcome_from_card(card: dict, row, p0: P0Predictor, now: dt.datetime) -> dict | None:
    """The outcome of one card given its ledger row, or None while the row's registered horizon has not passed at ``now``.

    ``card`` is the frozen card JSON, ``row`` the admitted ledger row (a mapping with ``y``, ``s``, ``started_at``, ``usable_after`` and,
    for the reliability interval, ``test_id``), ``p0`` the baseline fitted on the ledger. The miss type always follows the card as issued;
    the scores follow ``card_forecast``, so an abstained card is scored on the forecast it withheld. A card that is not pre-launch
    evidence (``card_timing``) gets a record with ``post_hoc: true``, the reason and no score at all: nothing of the result is credited to it.
    """
    if pd.Timestamp(row["usable_after"]) > pd.Timestamp(now):      # horizon guard: no outcome before its registered horizon
        return None
    timing, why = card_timing(card, row)
    if timing != "pre_launch":
        return {**_record(card, row, now), "timing": timing, "post_hoc": True, "post_hoc_reason": why}
    y, s = float(row["y"]), float(row["s"])
    star = card["request"].get("s_star")
    has_star = star is not None and math.isfinite(float(star)) and float(star) > 0
    if not has_star:        # no scale was known at issue: a log score on the realized s would leak the result (REV-039)
        LOG.warning("card %s has no usable s_star; its log scores are left null and it is excluded from reliability", card["card_id"])
    s_card = float(star) if has_star else s      # log scores use the scale known before launch, as in the backtest
    pred, issued = card["prediction"], card["abstention"]["status"] == "issue"
    event = y > Z * s
    iv = tuple(pred["interval_90"]) if issued and pred.get("interval_90") else None
    iv_y = tuple(pred["interval_90_y"]) if issued and pred.get("interval_90_y") else None
    base = card["evidence"].get("base_rate_sig_pos")
    origin = dt.datetime.fromisoformat(card["origin"])
    fc = card_forecast(card)
    p0_card = (pred.get("p0") or {}) if pred else {}
    if has_star and p0_card.get("var") is not None and p0_card.get("mean") is not None:
        # the card's own baseline: P0 as the bundle had it at issue, the same information the model had (REV-L-019)
        sd = max(math.sqrt(p0_card["var"]), 1e-6)
        p0_ls = float(-0.5 * ((y - p0_card["mean"]) / sd) ** 2 - math.log(sd * math.sqrt(2.0 * math.pi)))
    else:                       # a card from before the baseline was stored on it: P0 refit on the ledger rows visible at its origin
        try:
            p0_ls = float(p0.logscore(y, card["cell"], origin)) if has_star else None
        except ValueError:      # no row was visible at the card's origin: there is no baseline to compare with
            p0_ls = None
    p_scored = None if fc is None else fc.get("p_sig")
    logscore, legacy, cover90 = None, False, None
    if fc is not None and has_star:
        if fc.get("predictive"):
            pr = Predictive.from_spec(fc["predictive"])
            logscore = float(pr.logscore(y, s_card))
        else:                    # a card of schema version 1: a Normal from the point and the interval for the true effect
            legacy = True
            logscore = _forecast_logscore(fc.get("point"), fc.get("interval_90"), y, s_card)
        look = fc.get("interval_90_y")
        cover90 = None if not look else bool(look[0] <= y <= look[1])
    interval_for_miss = iv_y if iv_y is not None else iv
    return {
        **_record(card, row, now),
        "timing": "pre_launch",
        "scored": True,
        "y": y,
        "s": s,
        "event": bool(event),
        "abstained": not issued,
        "p_sig": pred.get("p_sig") if issued else None,
        "point": pred.get("point") if issued else None,
        "interval_90": list(iv) if iv else None,
        "interval_90_y": list(iv_y) if iv_y else None,
        "miss_type": type_miss(
            abstained=not issued,
            p_sig=pred.get("p_sig") if issued else None,
            point=pred.get("point") if issued else None,
            interval90=interval_for_miss,
            y=y,
            s=s,
        ),
        "logscore": logscore,
        "p0_logscore": p0_ls,
        "scored_forecast": "withheld" if (fc is not None and not issued) else ("issued" if fc is not None else None),
        "legacy_normal": legacy,
        "covered_90": cover90,
        "brier": float((p_scored - event) ** 2) if p_scored is not None else None,
        "p0_brier": float((base - event) ** 2) if base is not None else None,
    }


def _scored_by_row(out_dir: Path, source: str) -> dict[str, str]:
    """``row_id -> card_id`` of the outcome that scores each row (a file written before the flag existed is a scored one)."""
    found: dict[str, str] = {}
    for path in visible_glob(out_dir, "*.json"):
        try:
            o = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if o.get("source") == source and o.get("row_id") and o.get("scored", True):
            found[o["row_id"]] = o["card_id"]
    return found


def attach_outcomes(cards_dir, ledger: pd.DataFrame, source: str, now: dt.datetime, p0: P0Predictor | None = None,
                    ledger_snapshot: Callable[[], str] | None = None) -> list[dict]:
    """Write ``cards/outcomes/<card_id>.json`` for each card of ``source``, abstained or issued, whose row is now in the ledger.

    Existing outcome files are left alone (they are written once). Returns the records written: scored outcomes, post-hoc records and
    reissues (see the module docstring). Card files are only read. Rows that are not admitted (excluded from scoring) get no outcome.
    Horizon guard (builder call 42): a row whose ``usable_after`` is after ``now`` gets no outcome yet; it is attached by the first later
    join whose ``now`` is at or after ``usable_after``. One card per row (call 222): the candidates of a row are taken in issue order, the
    first pre-launch one is scored unless an earlier join already scored the row, the other pre-launch ones are reissues of it, and a card
    that is not pre-launch is recorded post-hoc whatever its place in the order.

    ``ledger_snapshot`` returns the id of the snapshot that holds the rows read here; it is called once, and only when a record is written,
    and each record carries it as ``ledger_snapshot_id`` (call 249), beside the card's own ``snapshot_id``.
    """
    cards_dir = Path(cards_dir)
    out_dir = cards_dir / "outcomes"
    adm = ledger.loc[ledger["status"] == ADMITTED].set_index("row_id")
    p0 = p0 or P0Predictor().fit(ledger.loc[(ledger["status"] == ADMITTED) & (ledger["source"] == source)])
    pending: dict[str, list[tuple[pd.Timestamp, str, dict]]] = {}
    for path in visible_glob(cards_dir, "*.json"):
        card = json.loads(path.read_text(encoding="utf-8"))
        row_id = card["request"].get("row_id")
        if card["source"] != source or not row_id or row_id not in adm.index or (out_dir / f"{card['card_id']}.json").exists():
            continue
        if pd.Timestamp(adm.loc[row_id, "usable_after"]) > pd.Timestamp(now):
            continue
        pending.setdefault(row_id, []).append((pd.Timestamp(card["issued_at"]), card["card_id"], card))
    written = []
    scored_before = _scored_by_row(out_dir, source) if pending else {}
    ledger_sid = None
    for row_id in sorted(pending):
        row = adm.loc[row_id]
        winner = scored_before.get(row_id)
        for _issued, card_id, card in sorted(pending[row_id], key=lambda c: (c[0], c[1])):
            timing, _why = card_timing(card, row)
            if card.get("cell") is not None and str(card["cell"]) != str(row["cell"]):
                outcome = cell_mismatch_outcome(card, row, now)        # before the order of the candidates: it never wins the row
            elif timing != "pre_launch":
                outcome = outcome_from_card(card, row, p0, now)
            elif winner is None:
                outcome = outcome_from_card(card, row, p0, now)
                winner = card_id
            else:
                outcome = reissue_outcome(card, row, winner, now)
            if ledger_snapshot is not None:
                ledger_sid = ledger_sid or ledger_snapshot()
                outcome["ledger_snapshot_id"] = ledger_sid
            _atomic_write(out_dir / f"{card_id}.json", json.dumps(outcome, indent=1, sort_keys=True) + "\n", read_only=True)
            written.append(outcome)
    return written


def reliability_row(o: dict) -> dict | None:
    """One outcome in the reliability schema (``cell``, ``at``, the four scores, ``test_id``), or None while a score is missing or the
    record is not a scored one (a post-hoc card or a reissue; a file written before the flag existed is scored).

    The one function the weekly join and the replay both use to turn outcomes into reliability evidence, abstained cards included.
    """
    if not o.get("scored", True) or None in (o["logscore"], o["p0_logscore"], o["brier"], o["p0_brier"]):
        return None
    return {"cell": o["cell"], "at": o["at"], "logscore": o["logscore"], "p0_logscore": o["p0_logscore"], "brier": o["brier"],
            "p0_brier": o["p0_brier"], "test_id": o.get("test_id")}


def load_outcomes(cards_dir, source: str) -> list[dict]:
    """All outcome files of a source in the reliability schema: every card that has a forecast to score, abstained ones included."""
    rows = []
    for path in visible_glob(Path(cards_dir) / "outcomes", "*.json"):
        o = json.loads(path.read_text(encoding="utf-8"))
        if o["source"] != source:
            continue
        r = reliability_row(o)
        if r is not None:
            rows.append(r)
    return rows


# --------------------------------------------------------------------- join
@dataclass(frozen=True)
class JoinResult:
    """What a join did."""

    n_new_rows: int
    n_outcomes: int                 # scored outcomes written
    snapshot_id: str | None
    reliability_path: Path
    miss_counts: dict
    n_post_hoc: int = 0             # cards recorded post-hoc at this join, never scored
    n_reissues: int = 0             # pre-launch cards for a row another card scores
    post_hoc: tuple = ()            # (card id, reason) of each post-hoc record written
    n_outside_window: int = 0       # scored outcomes dated before the trailing window of this join: they date no reliability entry (call 250)
    n_cell_mismatch: int = 0        # cards recorded unscored because their ledger row has another cell than the card (call 256)


def join_new_rows(loader: Callable[[], pd.DataFrame], *, ledger_dir, cards_dir, reports_dir, source: str,
                  now: dt.datetime | None = None) -> JoinResult:
    """One weekly join. ``loader()`` returns the concluded rows to add (a ledger frame, possibly empty).

    Idempotent: with the same inputs a second call finds no new rows and no new outcomes and changes nothing
    except the reliability ``as_of`` stamp (which is the same ``now`` in a repeated call). ``n_outcomes`` counts scored outcomes;
    post-hoc records and reissues are counted apart and never reach the reliability report.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    ledger_path = Path(ledger_dir) / "ledger.parquet"
    existing = read_ledger(ledger_path)
    merged = append_rows(existing, loader())
    n_new = len(merged) - len(existing)
    snapshot = None
    of_source = merged[merged["source"] == source].reset_index(drop=True)
    if n_new > 0:
        write_ledger(merged, ledger_path)
        snapshot = ensure_snapshot(of_source, ledger_dir)
    written = attach_outcomes(cards_dir, merged, source, now, ledger_snapshot=lambda: snapshot or ensure_snapshot(of_source, ledger_dir))
    scored = [o for o in written if o.get("scored")]
    post_hoc = tuple((o["card_id"], o["post_hoc_reason"]) for o in written if o.get("post_hoc"))
    n_reissues = sum(1 for o in written if o.get("reissue"))
    reports_dir = Path(reports_dir)
    path = reports_dir / f"reliability-{source}.json"
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    report = update_reliability(prev, load_outcomes(cards_dir, source), now, advance=bool(scored), source=source)
    _atomic_write(path, json.dumps(report, indent=1, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for o in scored:
        counts[o["miss_type"]] = counts.get(o["miss_type"], 0) + 1
    edge = pd.Timestamp(now) - pd.Timedelta(weeks=TRAILING_WEEKS)
    outside = sum(1 for o in scored if pd.Timestamp(o["at"]) <= edge)
    n_mismatch = sum(1 for o in written if o.get("cell_mismatch"))
    return JoinResult(n_new, len(scored), snapshot, path, counts, len(post_hoc), n_reissues, post_hoc, outside, n_mismatch)


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
