#!/usr/bin/env python3
"""Replay an archive at weekly joins and write ``reports/replay-<source>-<snapshot>.json``.

The replay asks what the weekly loop (``moot join``) would have done had it run over the whole archive, using only what was
visible at each week. Design calls, also stated in the report header:

* Weeks. A week starts at a Monday-agnostic seven-day step from the first quarterly origin at which a champion can be fitted
  (at least ``MIN_FIT_ROWS`` admitted rows visible, the first scored origin of the backtest) and runs until the last result is usable.
* Issue cadence. One card per admitted ledger row, issued at the start of the week in which its test starts (``started_at`` in
  the week), with ``origin`` and issue time both equal to that week start. Rows that start before the first week are history.
* Bundle. The champion bundle fitted at the latest quarterly origin on or before the week (``fit_bundle(..., as_of=origin)``), so a
  card never sees a row whose ``usable_after`` is later than its week. Bundles are fitted once per quarter, as the loop would
  refit quarterly, not weekly.
* Join. At each week start, every card whose row has ``usable_after`` on or before that week and is not yet joined gets its outcome,
  typed by the same function the weekly join uses (``loop.outcome_from_card``); then the reliability report is rewritten by the same
  rule (``reliability.build_reliability``, trailing eight weeks, ``advance`` only when outcomes arrived); then the week's cards are
  issued against that report.
* Reliability evidence. The report is built from the forecast each card made, abstained or not (as the backtest does), because a
  loop whose only evidence were issued cards could never leave an all-abstaining burn-in. The typed misses follow the card as issued.
* Coverage. The rolling 90 percent coverage of a week is the share of issued cards joined in the trailing eight weeks whose
  result lay inside the card's 90 percent interval (abstained cards have no interval).
* Flagged week. A week is flagged when the report written at its join marks at least one cell drifted: two joins in a row with at
  least ten outcomes in the window and a rolling log score more than 0.10 nats under the baseline (``abstain.py``, ``reliability.py``).
  ``below_cells`` lists the cells below threshold at the join (a first warning); ``drift_onsets`` the weeks a cell newly drifted.
* Abstentions by trigger. ``weeks[].abstained_by_trigger`` counts the cards of the week that carried each trigger as a reason (a card can
  carry several, so the counts can add up to more than ``abstained``); ``totals.abstained_by_trigger`` sums the weeks.

Use: ``python scripts/replay_weekly.py --source upworthy``. Nothing is written to the ledger, the cards folder or the models folder.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt import card as card_mod
from mootcourt import loop
from mootcourt.abstain import TRIGGERS, AbstainConfig
from mootcourt.bundle import fit_bundle
from mootcourt.config import DRIFT_CONSECUTIVE, DRIFT_LOGSCORE_MARGIN, RELIABILITY_MAX_AGE_DAYS, TRAILING_WEEKS
from mootcourt.harness import MIN_FIT_ROWS, quarterly_origins
from mootcourt.ledger import ADMITTED, ensure_snapshot, read_ledger, visible_rows
from mootcourt.predictors.p0 import P0Predictor
from mootcourt.reliability import MIN_DRIFT_N, build_reliability
from mootcourt.report import clean
from mootcourt.scale import prelaunch_view
from mootcourt.storage import storage_paths

WEEK = pd.Timedelta(days=7)
_OUTCOME_KEYS = ("logscore", "p0_logscore", "brier", "p0_brier")


def week_flags(report: dict | None) -> tuple[list[str], list[str]]:
    """``(below_cells, drifted_cells)`` of a reliability report: cells below threshold at the last join, and cells marked drifted."""
    cells = (report or {}).get("cells", {})
    below = sorted(c for c, e in cells.items() if int(e.get("consecutive_below", 0)) >= 1 or e.get("drifted"))
    drifted = sorted(c for c, e in cells.items() if e.get("drifted"))
    return below, drifted


def _request(row, source: str) -> card_mod.CardRequest:
    f = prelaunch_view(json.loads(row.features_json))
    return card_mod.CardRequest(
        source=source, headline=str(f.get("headline", "")), image_changed=bool(f.get("image_changed", False)),
        impressions=max(1, int(round(float(0.5 * (row.n_ref + row.n_var))))), origin=row.week, row_id=row.row_id,
        headline_changed=bool(f.get("headline_changed", True)), cell=row.cell)


def _compact(report: dict | None) -> dict:
    keys = ("n", "consecutive_below", "drifted", "rolling_logscore", "p0_rolling_logscore", "brier_skill")
    return {c: {k: e.get(k) for k in keys} for c, e in (report or {}).get("cells", {}).items()}


def replay(ledger: pd.DataFrame, source: str, snapshot_id: str, *, keep_records: bool = False, verbose: bool = False):
    """Replay ``ledger`` (rows of one source) at weekly joins. Returns the report document, and the per-card records when asked.

    Raises ValueError when no quarterly origin has enough admitted rows to fit a champion.
    """
    adm = ledger.loc[(ledger["status"] == ADMITTED) & (ledger["source"] == source)].reset_index(drop=True)
    if adm.empty:
        raise ValueError(f"the ledger has no admitted rows for source {source}")
    origins = [o for o in quarterly_origins(adm) if len(visible_rows(adm, o)) >= MIN_FIT_ROWS]
    if not origins:
        raise ValueError(f"no quarterly origin has {MIN_FIT_ROWS} visible admitted rows, so no champion can be fitted")
    first = origins[0]
    last = max(adm["usable_after"].max(), adm["started_at"].max())
    weeks = []
    t = first
    while True:
        weeks.append(t)
        if t >= last:
            break
        t = t + WEEK
    adm = adm.assign(week=lambda d: d["started_at"].map(lambda ts: first + WEEK * int((ts - first) // WEEK)))
    rows = adm[adm["started_at"] >= first].sort_values(["started_at", "row_id"])
    by_week = {w: list(g.itertuples(index=False)) for w, g in rows.groupby("week")}
    by_id = adm.set_index("row_id")
    p0 = P0Predictor().fit(adm)
    cfg = AbstainConfig()
    bundles: dict[pd.Timestamp, object] = {}
    pending: list[dict] = []
    outcomes_rel: list[dict] = []
    joined_issued: list[tuple[pd.Timestamp, dict]] = []
    records: list[dict] = []
    report, prev_flagged = None, set()
    week_docs, miss_total = [], {m: 0 for m in loop.MISS_TYPES}
    flagged_weeks, onsets, n_cards = [], [], 0
    t0 = time.perf_counter()
    for t in weeks:
        # 1. join: outcomes of cards whose results are usable at this week
        written, still = [], []
        for rec in pending:
            usable = pd.Timestamp(by_id.loc[rec["card"]["request"]["row_id"], "usable_after"])
            if usable > t:
                still.append(rec)
                continue
            out = loop.outcome_from_card(rec["card"], by_id.loc[rec["card"]["request"]["row_id"]], p0, t.to_pydatetime(), forecast=rec["forecast"])
            rec["outcome"], rec["joined_week"] = out, t.isoformat()
            written.append(out)
        pending = still
        for out in written:
            miss_total[out["miss_type"]] += 1
            if None not in (out[k] for k in _OUTCOME_KEYS):
                outcomes_rel.append({"cell": out["cell"], "at": out["at"], **{k: out[k] for k in _OUTCOME_KEYS}})
            if not out["abstained"] and out["interval_90"]:
                joined_issued.append((t, out))
        # 2. reliability, by the rule of the weekly join
        report = build_reliability(report, outcomes_rel, t.to_pydatetime(), advance=bool(written), source=source)
        below, drifted = week_flags(report)
        if drifted:
            flagged_weeks.append(t.isoformat())
        onsets += [{"week_start": t.isoformat(), "cell": c} for c in drifted if c not in prev_flagged]
        prev_flagged = set(drifted)
        # 3. issue the cards of the tests that start this week
        q = max(o for o in origins if o <= t)
        if q not in bundles:
            bundles[q] = fit_bundle(ledger.loc[ledger["source"] == source], source, snapshot_id, as_of=q)
            if verbose:
                print(f"fitted the bundle of origin {q.date()} on {bundles[q].n_rows} rows ({time.perf_counter() - t0:.0f} s)", file=sys.stderr)
        bundle = bundles[q]
        issued = abstained = 0
        by_trigger = dict.fromkeys(TRIGGERS, 0)
        for row in by_week.get(t, []):
            request = _request(row, source)
            card = card_mod.build_card(bundle, request, reliability=report, now=t.to_pydatetime(), config=cfg)
            if bundle.fit_cutoff is not None and bundle.fit_cutoff > t:
                raise RuntimeError(f"the bundle of origin {q} saw a result usable after week {t}")
            p = card.prediction
            rec = {"card": card_mod.to_json(card), "request": request, "issue_week": t.isoformat(), "bundle_origin": q.isoformat(),
                   "fit_cutoff": None if bundle.fit_cutoff is None else bundle.fit_cutoff.isoformat(), "reliability_used": report,
                   "forecast": {"point": p.point, "interval_90": p.interval_90, "p_sig": p.p_sig}, "outcome": None, "joined_week": None}
            pending.append(rec)
            if keep_records:
                records.append(rec)
            issued += 1
            abstained += int(card.abstention.status != "issue")
            for reason in card.abstention.reasons:
                by_trigger[reason] += 1
        n_cards += issued
        win = [o for j, o in joined_issued if t - pd.Timedelta(weeks=TRAILING_WEEKS) < j <= t]
        cover = float(np.mean([o["interval_90"][0] <= o["y"] <= o["interval_90"][1] for o in win])) if win else None
        counts = {m: 0 for m in loop.MISS_TYPES}
        for out in written:
            counts[out["miss_type"]] += 1
        week_docs.append({
            "week_start": t.isoformat(), "bundle_origin": q.isoformat(),
            "max_fit_cutoff": None if bundle.fit_cutoff is None else bundle.fit_cutoff.isoformat(),
            "cards_issued": issued, "abstained": abstained, "abstained_by_trigger": by_trigger,
            "abstention_rate": (abstained / issued) if issued else None,
            "outcomes_joined": len(written), "miss_counts": counts, "coverage_90": cover, "coverage_90_n": len(win),
            "below_cells": below, "drifted_cells": drifted, "flagged": bool(drifted), "reliability": _compact(report),
        })
    n_out = sum(w["outcomes_joined"] for w in week_docs)
    allw = [o for _, o in joined_issued]
    doc = {
        "header": {
            "source": source, "snapshot_id": snapshot_id, "command": f"python scripts/replay_weekly.py --source {source}",
            "week_days": 7, "first_week": weeks[0].isoformat(), "last_week": weeks[-1].isoformat(), "n_weeks": len(weeks),
            "n_cards": n_cards, "n_outcomes": n_out, "bundle_origins": [o.isoformat() for o in sorted(bundles)],
            "rule": {"trailing_weeks": TRAILING_WEEKS, "drift_consecutive": DRIFT_CONSECUTIVE, "drift_logscore_margin": DRIFT_LOGSCORE_MARGIN,
                     "min_drift_n": MIN_DRIFT_N, "reliability_max_age_days": RELIABILITY_MAX_AGE_DAYS},
            "notes": [
                "One card per admitted row, issued at the start of the week its test starts, from the champion bundle fitted at the latest "
                "quarterly origin on or before that week.",
                "Outcomes are joined at the first weekly join on or after usable_after, typed by the weekly join's own rule.",
                "The reliability report is built from the forecast of every card, abstained or not, as the backtest does; "
                "typed misses follow the card as issued.",
                "Rolling coverage is over issued cards joined in the trailing eight weeks. A flagged week is one whose report marks a cell drifted.",
            ],
        },
        "weeks": week_docs,
        "flagged_weeks": flagged_weeks,
        "drift_onsets": onsets,
        "totals": {
            "cards_issued": n_cards, "outcomes_joined": n_out, "miss_counts": miss_total, "n_flagged_weeks": len(flagged_weeks),
            "abstained": int(sum(w["abstained"] for w in week_docs)),
            "abstained_by_trigger": {t: int(sum(w["abstained_by_trigger"][t] for w in week_docs)) for t in TRIGGERS},
            "coverage_90_all": float(np.mean([o["interval_90"][0] <= o["y"] <= o["interval_90"][1] for o in allw])) if allw else None,
            "coverage_90_all_n": len(allw),
        },
    }
    doc = clean(doc)
    return (doc, records) if keep_records else doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", required=True)
    paths = storage_paths()
    ap.add_argument("--ledger", default=str(paths.ledger_path))
    ap.add_argument("--reports-dir", default=str(paths.reports))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    ledger_path = Path(args.ledger)
    df = read_ledger(ledger_path)
    df = df[df["source"] == args.source].reset_index(drop=True)
    if df.empty:
        print(f"the ledger {ledger_path} has no rows for source {args.source}", file=sys.stderr)
        return 1
    sid = ensure_snapshot(df, ledger_path.parent)
    t0 = time.perf_counter()
    doc = replay(df, args.source, sid, verbose=args.verbose)
    out = Path(args.reports_dir) / f"replay-{args.source}-{sid}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(out)
    t = doc["totals"]
    print(f"replayed {doc['header']['n_weeks']} weeks, {t['cards_issued']} cards, {t['outcomes_joined']} outcomes, "
          f"{t['n_flagged_weeks']} flagged weeks in {time.perf_counter() - t0:.1f} s")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
