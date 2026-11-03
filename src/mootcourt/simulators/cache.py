"""Result cache: ``cache/simulators/<provider_id>/<version>/<request_hash>.json`` under the storage root.

A hit never calls the agent again. A decline is cached too, so a deterministic refusal is not retried. A new version
of a provider has its own folder, so its results never mix with an older version's.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from mootcourt.simulators.base import SimulationResult


def _safe(part: str) -> str:
    """A folder or file name that cannot climb out of the cache: other characters become underscores, a leading dot too."""
    out = re.sub(r"[^A-Za-z0-9._-]", "_", part).lstrip(".") or "_"
    return out


class SimulationCache:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, provider_id: str, version: str, request_hash: str) -> Path:
        return self.root / _safe(provider_id) / _safe(version) / f"{_safe(request_hash)}.json"

    def get(self, provider_id: str, version: str, request_hash: str) -> dict | None:
        p = self.path(provider_id, version, request_hash)
        if not p.is_file():
            return None
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            declined = rec.get("declined")
            if not isinstance(declined, bool) or (rec.get("result") is None) != declined:
                return None            # an answer needs a result, a decline carries none, and the flag must be a real bool (REV-F-004)
            if not declined:
                SimulationResult.from_dict(rec["result"])          # an entry that no longer passes the result schema is a miss (REV-037)
        except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError):
            return None
        return rec

    def put(self, provider_id: str, version: str, request_hash: str, record: dict) -> Path:
        p = self.path(provider_id, version, request_hash)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
        return p
