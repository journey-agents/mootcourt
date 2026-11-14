#!/usr/bin/env python3
"""Fetch the Upworthy confirmatory packages file once, under the user's recorded decision, and record its checksum.

``scripts/download_data.py`` refuses this file. The user decided on 14 November 2026 that it is read once, after the code is frozen and
the readings are registered (docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md, Registration of the confirmatory reading).
This script is the door for the download: it runs only with ``--decision 2026-11-14``, lists the archive's node through the OSF API as the
download script does, fetches the one file whose name says confirmatory (never a holdout, undeployed or exploratory file), refuses when
its record already exists, and writes ``confirmatory-fetch-record.json`` beside the file with its name, size, SHA-256, address and time.
It does not open the file. ``scripts/confirmatory_ledger.py`` is the one script that reads it.

Use: ``python scripts/fetch_confirmatory.py --dest DIR --decision 2026-11-14``
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("download_data", Path(__file__).resolve().parent / "download_data.py")
dd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dd)

DECISION = "2026-11-14"
REFUSED = ("holdout", "undeployed", "exploratory")
RECORD = "confirmatory-fetch-record.json"


def fetch_once(dest, decision: str | None) -> dict:
    """The record of the one fetch into ``dest``; raises PermissionError without the recorded decision, FileExistsError on a second
    fetch, LookupError unless exactly one file of the listing is the confirmatory file."""
    dest = Path(dest)
    if decision != DECISION:
        raise PermissionError("the confirmatory file is fetched only under the recorded decision; pass --decision with its date")
    if (dest / RECORD).exists():
        raise FileExistsError(f"{dest} already holds a fetch record; the file is fetched once")
    node = dd.NODES["upworthy"]
    hits = [f for f in dd.list_files(dd.DEFAULT_BASE_URL, node)
            if "confirmatory" in f["name"].lower() and not any(w in f["name"].lower() for w in REFUSED) and dd._safe_name(f["name"])]
    if len(hits) != 1:
        raise LookupError(f"expected exactly one confirmatory file in OSF node {node}; found {sorted(f['name'] for f in hits)}")
    f = hits[0]
    digest, size = dd.fetch(f["url"], dest / f["name"], f.get("size"))
    doc = {"decision": decision, "node": node, "file": f["name"], "url": f["url"], "bytes": int(size), "sha256": digest,
           "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (dest / RECORD).write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--decision", default=None)
    a = ap.parse_args(argv)
    try:
        doc = fetch_once(a.dest, a.decision)
    except (PermissionError, FileExistsError, LookupError, dd.DownloadError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(doc, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
