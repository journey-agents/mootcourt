"""The transcript store: every request and its reply, one file per request, keyed by a hash of the request.

A stored reply is never asked for again, so a rerun and every scoring step read the store and call no model. A call
is made only when the caller passes ``allow_model_calls=True``. A transport failure stores no record; when bad replies
came before it, a note beside the record's place keeps them, so the request resumes with what is left of its attempts.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from mootcourt.simulators.cache import SimulationCache
from mootcourt.simulators.readers import api, local
from mootcourt.simulators.readers.command import TransportError, call, same_model
from mootcourt.simulators.readers.prompts import ReplyError, is_refusal

TRANSPORTS = ("tool", "api", "local")
ATTEMPTS = 3          # the first call and two retries with the same input


class ModelCallsNotAllowed(RuntimeError):
    """A reply is not stored and the caller did not allow a model call."""


def request_hash(model: str, kind: str, system: str, prompt: str, schema: dict) -> str:
    text = json.dumps({"model": model, "kind": kind, "system": system, "prompt": prompt, "schema": schema},
                      sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Transcripts:
    """Files under ``<root>/<model>/<kind>/<request hash>.json``, written whole or not at all."""

    def __init__(self, root):
        self.root = Path(root)
        self._files = SimulationCache(self.root)          # its paths and its atomic write; records here have their own shape

    def path(self, model: str, kind: str, h: str) -> Path:
        return self._files.path(model, kind, h)

    def get(self, model: str, kind: str, h: str) -> dict | None:
        return _read(self.path(model, kind, h))

    def put(self, model: str, kind: str, h: str, record: dict) -> Path:
        return self._files.put(model, kind, h, record)

    def records(self, model: str, kind: str) -> list[dict]:
        folder = self.path(model, kind, "x").parent
        found = (_read(p) for p in sorted(folder.glob("*.json")) if not p.name.startswith(".")) if folder.is_dir() else ()
        return [r for r in found if r is not None]

    def count(self, model: str, kind: str) -> dict[str, int]:
        """The number of stored records by status."""
        return dict(Counter(r["status"] for r in self.records(model, kind)))


def _read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) and record.get("status") in {"ok", "invalid", "refusal"} else None


def _pending(note: Path) -> dict:
    """The bad replies a request already drew before a transport failure, or none."""
    empty = {"replies": [], "seconds": 0.0, "usage": None, "status": "invalid"}
    try:
        held = json.loads(note.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    ok = isinstance(held, dict) and isinstance(held.get("replies"), list) and all(isinstance(r, str) for r in held["replies"])
    return {**empty, **held} if ok else empty


def ask(transcripts: Transcripts, model: str, kind: str, system: str, prompt: str, schema: dict, parse: Callable[[str], object],
        *, program: str = "claude", allow_model_calls: bool = False, time_cap_s: float = 180.0, meta: dict | None = None,
        hold_bad: bool = False, transport: str = "tool") -> dict:
    """The stored record of this request, made by up to three calls when none is stored and calls are allowed.

    ``parse`` reads a reply's text and raises ``ReplyError`` when the reply is not what was asked for. The status is
    ``"ok"``, or after three bad replies ``"refusal"`` when the last one holds no JSON object and ``"invalid"``
    otherwise. The text of each bad reply before the last is kept under ``earlier_replies``. A ``TransportError`` passes
    through and no record is stored; a reply that reports another model than the one
    asked for is such an error. With ``hold_bad`` a record that is not ``"ok"`` is returned and not stored, so the caller can
    decide whether it was a real reply or the sign of a failing transport. ``transport`` is ``"tool"`` for the command line
    tool, ``"api"`` for the vendor's API or ``"local"`` for an endpoint in the common chat format; the request and its hash
    are the same for all three.
    """
    if transport not in TRANSPORTS:
        raise ValueError(f"unknown transport {transport!r}")
    h = request_hash(model, kind, system, prompt, schema)
    stored = transcripts.get(model, kind, h)
    if stored is not None:
        return stored
    if not allow_model_calls:
        raise ModelCallsNotAllowed(f"no stored reply for request {h[:12]} of {model}, and model calls are not allowed")
    note = transcripts.path(model, kind, h).with_suffix(".pending")
    held = _pending(note)
    parsed, status, reply = None, held["status"], None
    seconds, attempts, usage, bad = held["seconds"], len(held["replies"]), held["usage"], list(held["replies"])
    while attempts < ATTEMPTS:
        try:
            reply = (api.call(model, system, prompt, schema, time_cap_s=time_cap_s) if transport == "api"
                     else local.call(model, system, prompt, schema, time_cap_s=time_cap_s) if transport == "local"
                     else call(model, system, prompt, schema, program=program, time_cap_s=time_cap_s))
            if not same_model(model, reply.reported_model):
                raise TransportError(f"asked {model} and the tool reports another model, {reply.reported_model}")
        except TransportError:
            if bad:          # the bad replies so far are kept, so the request does not start again with a full budget
                note.parent.mkdir(parents=True, exist_ok=True)
                note.write_text(json.dumps({"replies": bad, "seconds": seconds, "usage": usage, "status": status}), encoding="utf-8")
            raise
        attempts += 1
        seconds += reply.seconds
        if reply.usage is not None:          # every attempt is paid for, so the counts add up over attempts
            usage = {name: (usage or {}).get(name, 0) + value for name, value in reply.usage.items()}
        try:
            parsed, status = parse(reply.text), "ok"
            break
        except ReplyError:
            status = "refusal" if is_refusal(reply.text) else "invalid"
            bad.append(reply.text)
    last = reply.text if reply is not None else bad[-1]          # no call is made when the budget was spent before a failure
    earlier = bad if status == "ok" else bad[:-1]
    record = {"status": status, "request_hash": h, "request": {"model": model, "kind": kind, "system": system, "prompt": prompt, "schema": schema},
              "meta": meta or {}, "reply_text": last, "parsed": parsed, "attempts": attempts,
              "reported_model": reply.reported_model if reply is not None else model,
              "tool_version": reply.tool_version if reply is not None else None, "seconds": round(seconds, 3),
              "stored_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if earlier:
        record["earlier_replies"] = earlier
    if usage is not None:
        record["usage"] = usage
    note.unlink(missing_ok=True)
    if status == "ok" or not hold_bad:
        transcripts.put(model, kind, h, record)
    return record
