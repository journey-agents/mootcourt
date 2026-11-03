#!/usr/bin/env python3
"""Turn the stage timings of a timed run into reports/run-log.json and reports/run-log.md.

Input is the stage file written by ``scripts/timed_run.sh``: one line per stage, ``<name> <exit code> <seconds>``. The data stage time
is the figure the download script printed for itself. When that run downloaded nothing, the figure is the time of the checksum
verification and is labelled so (code review finding REV-005); a true download time exists only for a run from a clean copy with an
empty data root. Compute is everything else in the main pipeline. Nothing is estimated.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from mootcourt.storage import storage_paths

MAIN = ("setup", "data", "power", "fit-upworthy", "backtest-upworthy", "fit-asos", "backtest-asos", "fit-synthetic", "backtest-synthetic")


def parse_stages(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].lstrip("-").isdigit():
            rows.append({"stage": parts[0], "exit_code": int(parts[1]), "seconds": float(parts[2])})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--stages", required=True)
    ap.add_argument("--data-log", required=True, help="log of the data stage; holds the download script's own timing")
    ap.add_argument("--out-dir", default=str(storage_paths().reports))
    ap.add_argument("--meta", action="append", default=[], help="key=value lines to record (commit or tree digest, python, machine)")
    args = ap.parse_args()
    stages = parse_stages(Path(args.stages).read_text(encoding="utf-8"))
    m = re.search(r"ok: (\d+) downloaded \((\d+) bytes\), (\d+) verified, ([\d.]+) s", Path(args.data_log).read_text(encoding="utf-8"))
    download = float(m.group(4)) if m else 0.0
    n_files, n_bytes = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    main_total = sum(s["seconds"] for s in stages if s["stage"] in MAIN)
    total = sum(s["seconds"] for s in stages)
    meta = dict(kv.split("=", 1) for kv in args.meta)
    is_download = n_files > 0
    # Said here, from the download script's own summary line, and nowhere else: a run that only verified archives already in place
    # must not claim a download (BUG-007).
    meta["data"] = (f"downloaded {n_files} file(s), {n_bytes} bytes, from OSF in this run" if is_download
                    else "verified checksums of existing archives; nothing was downloaded in this run")
    doc = {"stages": stages, "download_seconds": round(download, 1), "downloaded_files": n_files, "downloaded_bytes": n_bytes,
           "data_stage_kind": "download" if is_download else "checksum verification", "compute_seconds": round(total - download, 1),
           "total_seconds": round(total, 1), "main_pipeline_seconds": round(main_total, 1),
           "all_exit_codes_zero": all(s["exit_code"] == 0 for s in stages), "meta": meta}
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "run-log.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    md = ["# Run log", "", "A timed run of the pipeline. A run from a clean copy of the files git would commit says so on the `run` line;",
          "any other run states how it differs there.", ""]
    md += [f"- {k}: {v}" for k, v in sorted(meta.items())]
    md += ["", "| stage | exit code | seconds |", "|---|---|---|"] + [f"| {s['stage']} | {s['exit_code']} | {s['seconds']} |" for s in stages]
    what = (f"Download {doc['download_seconds']} s ({n_files} files, {n_bytes} bytes, the download script's own timing)" if is_download
            else f"Checksum verification {doc['download_seconds']} s, no download in this run (the download script's own timing)")
    md += ["", f"{what}. Compute {doc['compute_seconds']} s. Total {doc['total_seconds']} s.",
           f"Main pipeline ({', '.join(s['stage'] for s in stages if s['stage'] in MAIN)}): {doc['main_pipeline_seconds']} s, "
           "against the 30 minute budget."]
    (out / "run-log.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out}/run-log.json and {out}/run-log.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
