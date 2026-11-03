"""Build the rolling-origin request set and run a provider over it, with the cache.

The request set is exactly the set of rows the backtest scores: for each quarterly origin, the admitted rows that
start in that quarter, when at least ``MIN_FIT_ROWS`` rows are visible at the origin. The standard error in each
request is the pre-launch ``s_star`` the harness uses, so the request hash computed here equals the one the backtest
recomputes from the ledger.
"""
from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mootcourt import scale
from mootcourt.config import ACTION_THRESHOLD
from mootcourt.harness import MIN_FIT_ROWS, quarterly_origins
from mootcourt.ledger import ADMITTED, to_utc, visible_rows
from mootcourt.simulators.base import Budget, ResponseSimulator, SimulationRequest
from mootcourt.simulators.cache import SimulationCache
from mootcourt.simulators.recorded import write_records


@dataclass(frozen=True)
class RequestItem:
    row_id: str
    origin: str
    request: SimulationRequest


@dataclass
class RunSummary:
    n_requests: int
    n_called: int
    n_cached: int
    n_declined: int
    cost_usd: float
    latency_s: float
    out_path: str
    n_failed: int = 0               # calls that failed (timeout, start, exit, transport, invalid, error): recorded, never cached


def request_for_row(row, s_star: float, origin, budget: Budget | None = None, threshold: float = ACTION_THRESHOLD) -> SimulationRequest:
    """The request for one ledger row (a namedtuple or Series with the ledger columns) at an origin."""
    f = scale.prelaunch_view(json.loads(row.features_json if hasattr(row, "features_json") else row["features_json"]))
    get = (lambda k: getattr(row, k)) if hasattr(row, "features_json") else (lambda k: row[k])
    return SimulationRequest(
        source=str(get("source")), cell=str(get("cell")), origin=to_utc(origin).isoformat(),
        reference_headline=str(f.get("reference_headline", "")), variant_headline=str(f.get("headline", "")),
        image_changed=bool(f.get("image_changed", False)), headline_changed=bool(f.get("headline_changed", True)),
        planned_n_ref=int(get("n_ref")), planned_n_var=int(get("n_var")), s_star=float(s_star),
        action_threshold=float(threshold), budget=budget or Budget(),
    )


def scored_blocks(ledger: pd.DataFrame, origins=None) -> Iterator[tuple[pd.Timestamp, pd.DataFrame, pd.DataFrame, object]]:
    """``(origin, scored rows, visible rows, s_star array)`` for each origin the backtest scores."""
    adm = ledger.loc[ledger["status"] == ADMITTED]
    origins = sorted(to_utc(o) for o in (origins if origins is not None else quarterly_origins(ledger)))
    ends = origins[1:] + [origins[-1] + pd.DateOffset(months=3)]
    for t, t_next in zip(origins, ends):
        scored = adm[(adm["started_at"] >= t) & (adm["started_at"] < t_next)].reset_index(drop=True)
        if scored.empty:
            continue
        visible = visible_rows(adm, t)
        if len(visible) < MIN_FIT_ROWS:
            continue
        yield t, scored, visible, scale.s_star_rows(scored, visible)


def build_requests(ledger: pd.DataFrame, origins=None, budget: Budget | None = None, limit: int | None = None) -> list[RequestItem]:
    """One request per scored row of the rolling-origin backtest (optionally the first ``limit``)."""
    items: list[RequestItem] = []
    for t, scored, _visible, s_star in scored_blocks(ledger, origins):
        for i, row in enumerate(scored.itertuples(index=False)):
            items.append(RequestItem(row.row_id, t.isoformat(), request_for_row(row, s_star[i], t, budget)))
            if limit is not None and len(items) >= limit:
                return items
    return items


def run(simulator: ResponseSimulator, items: list[RequestItem], out_path, cache: SimulationCache | None = None) -> RunSummary:
    """Run ``simulator`` over ``items`` and write one JSONL record per request.

    Each record has the request hash, provider id, version, knowledge cutoff, whether the agent declined, the result,
    latency and cost. A cache hit is returned without calling the agent. ``cost_usd`` and ``latency_s`` in the
    summary count only calls made in this run.

    Only an answer or an explicit decline (the agent said ``null``) is cached. A timeout, a command that would not
    start, a non-zero exit, a connection error or an output that is not a valid result is a transient failure: the
    record has ``declined`` true, a ``failure`` kind and the reason in ``note``, and it is not cached, so the next run
    asks the agent again. A simulator that raises is treated the same way (kind ``error``), so one bad call never
    loses the records of the others.
    """
    info = simulator.describe()
    if getattr(simulator, "cacheable", True) is False:
        cache = None                          # a replay of a records file never calls the agent, so it must not fill the agent's cache
    records, called, cached, declined, failed, cost, latency = [], 0, 0, 0, 0, 0.0, 0.0
    for it in items:
        h = it.request.request_hash()
        hit = cache.get(info.provider_id, info.version, h) if cache is not None else None
        if hit is not None:
            # The cache key has no cutoff, so a hit takes the provider's identity from the current describe() (REV-006): a corrected
            # knowledge cutoff then reaches the records, and contamination is judged from it.
            rec, was_cached = {**hit, "provider_id": info.provider_id, "version": info.version, "knowledge_cutoff": info.knowledge_cutoff}, True
            cached += 1
        else:
            t0 = time.perf_counter()
            failure, note = None, ""
            try:
                res = simulator.simulate(it.request)
                note = getattr(simulator, "last_note", "")
                if res is None:
                    failure = getattr(simulator, "last_failure", None)
            except Exception as exc:  # one bad call becomes a recorded failure; the run goes on
                res, failure, note = None, "error", f"{type(exc).__name__}: {exc}"
            wall = time.perf_counter() - t0
            called += 1
            rec = {"request_hash": h, "provider_id": info.provider_id, "version": info.version,
                   "knowledge_cutoff": info.knowledge_cutoff, "declined": res is None,
                   "result": None if res is None else res.to_dict(),
                   "latency_s": float(res.latency_s if res is not None and res.latency_s else wall),
                   "cost_usd": float(res.cost_usd) if res is not None else 0.0, "note": note,
                   "budget": it.request.to_wire()["budget"]}
            if failure:
                rec["failure"] = str(failure)
            elif cache is not None:
                cache.put(info.provider_id, info.version, h, rec)
            cost += rec["cost_usd"]
            latency += rec["latency_s"]
            was_cached = False
        declined += int(bool(rec["declined"]) and not rec.get("failure"))
        failed += int(bool(rec.get("failure")))
        records.append({**rec, "row_id": it.row_id, "origin": it.origin, "cached": was_cached})
    write_records(Path(out_path), records)
    return RunSummary(len(items), called, cached, declined, cost, latency, str(out_path), failed)
