"""Recorded adapter: replay results from a JSONL file keyed by request hash.

This is how an expensive agent is backtested. ``moot simulators run`` writes one line per request; the harness reads
the file back without running the agent again. A request whose hash is not in the file is a decline.

Line format (one JSON object per line)::

    {"request_hash": "...", "provider_id": "...", "version": "...", "knowledge_cutoff": "2025-06-01" or null,
     "declined": false, "result": {...} or null, "latency_s": 0.0, "cost_usd": 0.0, "row_id": "...", "origin": "..."}
"""
from __future__ import annotations

import json
from pathlib import Path

from mootcourt.simulators.base import SimulationRequest, SimulationResult, SimulatorError, SimulatorInfo


def read_records(path) -> list[dict]:
    """All records of a JSONL file; a malformed line raises SimulatorError naming the line."""
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SimulatorError(f"{path}:{n}: not JSON ({exc})") from None
        if "request_hash" not in rec or "declined" not in rec:
            raise SimulatorError(f"{path}:{n}: needs request_hash and declined")
        out.append(rec)
    return out


def write_records(path, records) -> None:
    """Write records as JSONL (sorted keys, one object per line)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")


class RecordedSimulator:
    """Replays a records file. Mixed providers or versions in one file are refused: one file, one agent."""

    def __init__(self, path):
        self.path = Path(path)
        self.records = read_records(self.path)
        ids = {(r.get("provider_id"), r.get("version")) for r in self.records}
        if len(ids) > 1:
            raise SimulatorError(f"{self.path} mixes providers or versions: {sorted(map(str, ids))}")
        self._by_hash = {r["request_hash"]: r for r in self.records}
        self.last_note = ""
        self.last_failure: str | None = None
        self.cacheable = False                    # a replay never calls the agent, so the runner neither reads nor fills the agent's cache
        first = self.records[0] if self.records else {}
        self._info = SimulatorInfo(first.get("provider_id") or "recorded", first.get("version") or "0",
                                   first.get("knowledge_cutoff"), "free", f"Replay of {self.path.name}")

    def describe(self) -> SimulatorInfo:
        return self._info

    def lookup(self, request_hash: str) -> dict | None:
        return self._by_hash.get(request_hash)

    def simulate(self, request: SimulationRequest) -> SimulationResult | None:
        """The recorded result. A recorded failure and an absent hash stay failures (``last_failure``); only a recorded decline is a decline."""
        self.last_note, self.last_failure = "", None
        rec = self._by_hash.get(request.request_hash())
        if rec is None:
            self.last_failure, self.last_note = "missing", "the request is not in the records file"
        elif rec.get("declined") or rec.get("result") is None:
            self.last_failure = str(rec["failure"]) if rec.get("failure") else None
            self.last_note = str(rec.get("note") or ("recorded failure" if rec.get("failure") else "the agent declined"))
        else:
            return SimulationResult.from_dict(rec["result"], provider_id=self._info.provider_id, version=self._info.version)
        return None
