"""The transcript store: every request and its reply, one file per request, keyed by a hash of the request.

A stored reply is never asked for again, so a rerun and every scoring step read the store and call no model. A call
is made only when the caller passes ``allow_model_calls=True``. A transport failure stores nothing.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from mootcourt.simulators.cache import SimulationCache
from mootcourt.simulators.readers.command import call
from mootcourt.simulators.readers.prompts import ReplyError, is_refusal

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


def ask(transcripts: Transcripts, model: str, kind: str, system: str, prompt: str, schema: dict, parse: Callable[[str], object],
        *, program: str = "claude", allow_model_calls: bool = False, time_cap_s: float = 180.0, meta: dict | None = None) -> dict:
    """The stored record of this request, made by up to three calls when none is stored and calls are allowed.

    ``parse`` reads a reply's text and raises ``ReplyError`` when the reply is not what was asked for. The status is
    ``"ok"``, or after three bad replies ``"refusal"`` when the last one holds no JSON object and ``"invalid"``
    otherwise. A ``TransportError`` passes through and nothing is stored.
    """
    h = request_hash(model, kind, system, prompt, schema)
    stored = transcripts.get(model, kind, h)
    if stored is not None:
        return stored
    if not allow_model_calls:
        raise ModelCallsNotAllowed(f"no stored reply for request {h[:12]} of {model}, and model calls are not allowed")
    parsed, status, reply, seconds, attempts = None, "invalid", None, 0.0, 0
    while attempts < ATTEMPTS:
        attempts += 1
        reply = call(model, system, prompt, schema, program=program, time_cap_s=time_cap_s)
        seconds += reply.seconds
        try:
            parsed, status = parse(reply.text), "ok"
            break
        except ReplyError:
            status = "refusal" if is_refusal(reply.text) else "invalid"
    record = {"status": status, "request": {"model": model, "kind": kind, "system": system, "prompt": prompt, "schema": schema},
              "meta": meta or {}, "reply_text": reply.text, "parsed": parsed, "attempts": attempts,
              "reported_model": reply.reported_model, "tool_version": reply.tool_version, "seconds": round(seconds, 3),
              "stored_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    transcripts.put(model, kind, h, record)
    return record
