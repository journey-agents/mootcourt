"""Score a recorded second opinion in the backtest: the agent rung, the stacked rung and the contamination split.

Inputs are the score table of ``harness.rolling_origin``, the ledger and a records file written by
``moot simulators run``. Rows are matched to records by request hash, rebuilt from the ledger row, the origin and the
pre-launch ``s_star`` of the score table, so the agent is never run here.

Two rungs are added, both derived from the base rung (P2 when present) so they cover the same rows and carry the
same abstention decisions:

* ``agent``: the agent's ``p_win_ai`` as ``p_sig``. Rows with no result (declined, or absent from the file) are not
  scored on this rung and are counted.
* ``P2+agent``: ``p_sig`` stacked as ``(1 - w) p_sig + w p_AI`` at the weight in force. A row without an opinion keeps
  ``p_sig``. At weight 0 the rung equals the base rung's probabilities.

Both rungs have probabilities only: no density, no intervals, no CRPS. Contamination: an origin earlier than the
provider's knowledge cutoff is flagged, because an agent trained after the cutoff may have seen the outcomes of a
public archive. A provider that declares no cutoff (other than the built-ins) is treated as unknown: every origin is
possibly contaminated.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mootcourt.predictors.second_opinion import WEIGHT_GRID
from mootcourt.simulators.base import BUILTIN_PROVIDER_IDS, Budget, SimulationResult, SimulatorError
from mootcourt.simulators.recorded import read_records
from mootcourt.simulators.runner import request_for_row

AGENT_RUNG = "agent"
STACK_RUNG = "P2+agent"
CONTAMINATION_SENTENCE = (
    "Limitation: an agent built on a language model may have seen this public archive in pretraining. Origins earlier than "
    "the provider's knowledge cutoff, or any origin when the provider declares no cutoff, are flagged as possibly contaminated, "
    "and contaminated and clean scores are reported separately. A weight is earned on clean origins only unless the run was "
    "told to include contaminated ones, and a weight earned that way is marked as contaminated wherever it is shown."
)
_DISTRIBUTION_COLUMNS = ("logscore", "crps", "p_win", "p_gt0", "lo80", "hi80", "lo90", "hi90", "brier_pos")


@dataclass
class SecondOpinionData:
    """A records file reduced to what the backtest needs."""

    by_hash: dict
    provider_id: str
    version: str
    knowledge_cutoff: str | None
    budget: Budget
    path: str

    @property
    def cutoff_unknown(self) -> bool:
        """True when the provider declares no knowledge cutoff and is not a built-in: every origin is then possibly contaminated."""
        return self.knowledge_cutoff is None and self.provider_id not in BUILTIN_PROVIDER_IDS


def validate_records(recs: list[dict], path) -> None:
    """Rebuild every answered record as a SimulationResult; a value that breaks the schema raises SimulatorError naming the record."""
    for n, r in enumerate(recs, 1):
        if r.get("declined") or r.get("result") is None:
            continue
        try:
            SimulationResult.from_dict(r["result"])
        except SimulatorError as exc:
            raise SimulatorError(f"{path}: record {n} (request {r.get('request_hash')}, row {r.get('row_id')}): {exc}") from None
        except (TypeError, ValueError, AttributeError, KeyError, OverflowError) as exc:
            raise SimulatorError(f"{path}: record {n} (request {r.get('request_hash')}, row {r.get('row_id')}): invalid result ({exc})") from None


def load_second_opinion(path) -> SecondOpinionData:
    """Read a records file; one provider and version per file."""
    recs = read_records(path)
    if not recs:
        raise SimulatorError(f"{path} has no records")
    validate_records(recs, path)
    ids = {(r.get("provider_id"), r.get("version")) for r in recs}
    if len(ids) != 1:
        raise SimulatorError(f"{path} mixes providers or versions: {sorted(map(str, ids))}")
    cutoffs = {r.get("knowledge_cutoff") for r in recs}
    if len(cutoffs) != 1:
        raise SimulatorError(f"{path} mixes knowledge cutoffs: {sorted(map(str, cutoffs))}; one file holds one agent at one cutoff")
    first = recs[0]
    try:
        budget = Budget(**first["budget"]) if first.get("budget") else Budget()
    except (TypeError, ValueError, OverflowError) as exc:
        raise SimulatorError(f"{path}: the budget of the first record is invalid ({exc})") from None
    return SecondOpinionData({r["request_hash"]: r for r in recs}, str(first.get("provider_id")), str(first.get("version")),
                             first.get("knowledge_cutoff"), budget, str(path))


def cutoff_timestamp(cutoff: str | None) -> pd.Timestamp | None:
    return None if cutoff is None else pd.Timestamp(dt.date.fromisoformat(cutoff), tz="UTC")


def is_contaminated(origin, cutoff: str | None, unknown_is_contaminated: bool = False) -> bool:
    """True when the origin is earlier than the knowledge cutoff.

    With no cutoff the answer is False, unless ``unknown_is_contaminated`` is set (a provider that should have declared
    one): then every origin is possibly contaminated.
    """
    c = cutoff_timestamp(cutoff)
    if c is None:
        return bool(unknown_is_contaminated)
    return pd.Timestamp(origin) < c


def hashes_for_scores(base: pd.DataFrame, ledger: pd.DataFrame, budget: Budget) -> pd.Series:
    """Request hash of every row of a score table (one rung's rows), rebuilt from the ledger."""
    by_id = ledger.drop_duplicates("row_id").set_index("row_id")
    out = []
    for r in base.itertuples(index=False):
        led = by_id.loc[r.row_id]
        row = led.to_dict()
        row["row_id"] = r.row_id
        out.append(request_for_row(pd.Series(row), float(r.s_star), r.origin, budget).request_hash())
    return pd.Series(out, index=base.index)


def opinions_for(base: pd.DataFrame, ledger: pd.DataFrame, data: SecondOpinionData) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """``(p_ai, point_ai, present, counts)`` aligned to ``base``; NaN where there is no opinion."""
    hashes = hashes_for_scores(base, ledger, data.budget)
    p_ai, point = np.full(len(base), np.nan), np.full(len(base), np.nan)
    missing = declined = failed = 0
    for i, h in enumerate(hashes.tolist()):
        rec = data.by_hash.get(h)
        if rec is None:
            missing += 1
        elif rec.get("declined") or rec.get("result") is None:
            if rec.get("failure"):
                failed += 1
            else:
                declined += 1
        else:
            p_ai[i] = float(rec["result"]["p_win_ai"])
            pt = rec["result"].get("point_ai")
            point[i] = np.nan if pt is None else float(pt)
    present = np.isfinite(p_ai)
    cost = sum(float(r.get("cost_usd") or 0.0) for h, r in data.by_hash.items())
    latency = sum(float(r.get("latency_s") or 0.0) for r in data.by_hash.values())
    counts = {"n_rows": int(len(base)), "n_with_opinion": int(present.sum()), "n_declined": declined, "n_failed": failed, "n_missing": missing,
              "cost_usd": cost, "latency_s": latency}
    return p_ai, point, present, counts


def add_agent_rungs(scores: pd.DataFrame, ledger: pd.DataFrame, data: SecondOpinionData, weight: float,
                    base_rung: str | None = None, weight_contaminated: bool = False) -> tuple[pd.DataFrame, dict]:
    """Append the ``agent`` and ``P2+agent`` rungs; returns the new table and the second-opinion metadata."""
    if not 0.0 <= weight <= 1.0:
        raise SimulatorError("weight must be in [0, 1]")
    base_rung = base_rung or ("P2" if (scores["rung"] == "P2").any() else str(scores["rung"].unique()[-1]))
    base = scores[scores["rung"] == base_rung].reset_index(drop=True)
    if base.empty:
        raise SimulatorError(f"the score table has no {base_rung} rows to attach a second opinion to")
    p_ai, point, present, counts = opinions_for(base, ledger, data)
    event = base["event"].to_numpy(float)

    agent = base[present].copy().reset_index(drop=True)
    agent["rung"] = AGENT_RUNG
    agent["p_sig"] = p_ai[present]
    agent["brier_event"] = (agent["p_sig"] - event[present]) ** 2
    for c in _DISTRIBUTION_COLUMNS:
        agent[c] = np.nan
    agent["point"] = point[present]
    has_pt = np.isfinite(agent["point"].to_numpy(float))
    agent["direction_correct"] = np.where(has_pt, (agent["point"].to_numpy(float) > 0) == (agent["y"].to_numpy(float) > 0), np.nan)

    stack = base.copy()
    stack["rung"] = STACK_RUNG
    p_sig = base["p_sig"].to_numpy(float)
    stacked = np.where(present, (1.0 - weight) * p_sig + weight * np.where(present, p_ai, 0.0), p_sig)
    stack["p_sig"] = stacked
    stack["brier_event"] = (stacked - event) ** 2
    for c in _DISTRIBUTION_COLUMNS:
        stack[c] = np.nan

    out = pd.concat([scores.assign(direction_correct=scores["direction_correct"].astype(float)), agent, stack], ignore_index=True)
    out.attrs = dict(scores.attrs)
    meta = {"provider_id": data.provider_id, "version": data.version, "knowledge_cutoff": data.knowledge_cutoff,
            "weight": float(weight), "weight_contaminated": bool(weight_contaminated), "cutoff_unknown": data.cutoff_unknown,
            "base_rung": base_rung, "file": data.path, "budget": {"max_respondents": data.budget.max_respondents,
                                                                                          "max_seconds": data.budget.max_seconds}, **counts}
    return out, meta


def clean_mask(origins: pd.Series, cutoff: str | None, unknown_is_contaminated: bool = False) -> np.ndarray:
    """True for rows at origins on or after the cutoff.

    With no cutoff every row is clean, unless ``unknown_is_contaminated`` is set: then no row is.
    """
    c = cutoff_timestamp(cutoff)
    if c is None:
        return np.full(len(origins), not unknown_is_contaminated, bool)
    return (pd.to_datetime(origins, utc=True) >= c).to_numpy()


def earn_frame(scores: pd.DataFrame, ledger: pd.DataFrame, data: SecondOpinionData, base_rung: str | None = None,
               include_contaminated: bool = False) -> pd.DataFrame:
    """Rows for ``earn_weight``: ``p_sig`` of the base rung, the event and the request hash, clean origins only by default."""
    base_rung = base_rung or ("P2" if (scores["rung"] == "P2").any() else str(scores["rung"].unique()[-1]))
    base = scores[scores["rung"] == base_rung].reset_index(drop=True)
    if not include_contaminated:
        base = base[clean_mask(base["origin"], data.knowledge_cutoff, data.cutoff_unknown)].reset_index(drop=True)
    base = base.assign(request_hash=hashes_for_scores(base, ledger, data.budget) if len(base) else pd.Series(dtype=str))
    keep = ["row_id", "origin", "p_sig", "event", "request_hash"] + (["test_id"] if "test_id" in base.columns else [])
    return base[keep].assign(event=lambda d: d["event"].astype(bool))


def uses_contaminated(frame: pd.DataFrame, data: SecondOpinionData) -> bool:
    """True when a row of the earn frame that carries an opinion lies at a contaminated origin."""
    answered = frame[[(data.by_hash.get(h) is not None and not data.by_hash[h].get("declined") and data.by_hash[h].get("result") is not None)
                      for h in frame["request_hash"]]]
    return bool((~clean_mask(answered["origin"], data.knowledge_cutoff, data.cutoff_unknown)).any()) if len(answered) else False


class RecordedProvider:
    """A ``SecondOpinionProvider`` over a records file: ``p_ai(row)`` looks the row's request hash up."""

    def __init__(self, data: SecondOpinionData):
        self.data = data

    def p_ai(self, row) -> float | None:
        rec = self.data.by_hash.get(row["request_hash"])
        if rec is None or rec.get("declined") or rec.get("result") is None:
            return None
        return float(rec["result"]["p_win_ai"])


__all__ = ["AGENT_RUNG", "STACK_RUNG", "CONTAMINATION_SENTENCE", "WEIGHT_GRID", "SecondOpinionData", "load_second_opinion",
           "add_agent_rungs", "earn_frame", "RecordedProvider", "is_contaminated", "clean_mask", "validate_records", "uses_contaminated"]
