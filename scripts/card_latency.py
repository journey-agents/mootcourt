#!/usr/bin/env python3
"""Measure card latency three ways and print a Markdown block for the run log.

1. The command line, end to end in a fresh process (includes imports and the bundle load).
2. In process with the bundle preloaded: 30 timed issues (the budget in the spec is under one second).
3. Through the HTTP service on the loopback address: 30 timed ``POST /card`` calls after the bundles are preloaded.

A fourth timing (round 00, R2) issues the same cards with the weight on precedents forced to 0.5 (``p2.lambda_override`` on the preloaded
bundle): with a weight of zero the dismissal walk and the instability bootstrap return at once, so the first timing is the degenerate path
and the one with precedents in play is the honest cost of a card that uses them.

Issue time is measured without the file write for (2); the service and CLI calls include freezing the card, into a temporary
directory so ``cards/`` is not touched. Usage: ``python scripts/card_latency.py --source upworthy``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np

from mootcourt.storage import storage_paths

HEADLINES = ["Why this one change doubled what people do next", "Nobody expected this to work", "A simple fact about your mornings",
             "What happens when you ask the question first", "This is the reason you keep scrolling", "How 3 small edits changed everything"]


def stats(xs: list[float]) -> dict:
    a = np.array(xs)
    return {"n": len(xs), "p50": float(np.percentile(a, 50)), "p95": float(np.percentile(a, 95)), "max": float(a.max())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default="upworthy")
    paths = storage_paths()
    ap.add_argument("--models-dir", default=str(paths.models))
    ap.add_argument("--reports-dir", default=str(paths.reports))
    ap.add_argument("--impressions", type=int, default=20000)
    ap.add_argument("--calls", type=int, default=30)
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--json-out", default=None, help="also write the numbers as JSON")
    args = ap.parse_args()

    from mootcourt import card as card_mod
    from mootcourt.bundle import load_bundle
    from mootcourt.cli import resolve_model_id

    models, reports = Path(args.models_dir), Path(args.reports_dir)
    report = card_mod.load_reliability_report(reports, args.source)
    as_of = dt.datetime.fromisoformat(report["as_of"]) if report else dt.datetime.now(dt.timezone.utc)
    now = as_of + dt.timedelta(days=1)       # a time at which the reliability report is fresh, so the card can issue
    mid = resolve_model_id(models, args.source)
    t = time.perf_counter()
    bundle = load_bundle(mid, models)
    load_s = time.perf_counter() - t

    issue = []
    status = {}
    for i in range(args.calls):
        req = card_mod.CardRequest(source=args.source, headline=f"{HEADLINES[i % len(HEADLINES)]} {i}", image_changed=False,
                                   impressions=args.impressions, origin=now, headline_changed=True)
        t = time.perf_counter()
        c = card_mod.build_card(bundle, req, reliability=report, now=now)
        issue.append(time.perf_counter() - t)
        status[c.abstention.status] = status.get(c.abstention.status, 0) + 1

    weighted, statuses_w = [], {}
    saved = bundle.p2.lambda_override
    bundle.p2.lambda_override = 0.5
    try:
        for i in range(args.calls):
            req = card_mod.CardRequest(source=args.source, headline=f"{HEADLINES[i % len(HEADLINES)]} w{i}", image_changed=False,
                                       impressions=args.impressions, origin=now, headline_changed=True)
            t = time.perf_counter()
            c = card_mod.build_card(bundle, req, reliability=report, now=now)
            weighted.append(time.perf_counter() - t)
            statuses_w[c.abstention.status] = statuses_w.get(c.abstention.status, 0) + 1
    finally:
        bundle.p2.lambda_override = saved

    with tempfile.TemporaryDirectory() as tmp:
        cli = []
        for i in range(3):
            cmd = [sys.executable, "-m", "mootcourt.cli", "card", "--source", args.source, "--headline", f"{HEADLINES[i]} cli",
                   "--image-changed", "false", "--impressions", str(args.impressions), "--now", now.isoformat(), "--origin", now.isoformat(),
                   "--models-dir", str(models), "--reports-dir", str(reports), "--cards-dir", tmp, "--json"]
            t = time.perf_counter()
            r = subprocess.run(cmd, capture_output=True, text=True)
            cli.append(time.perf_counter() - t)
            if r.returncode != 0:
                print(r.stderr, file=sys.stderr)
                return 1
        proc = subprocess.Popen([sys.executable, "-m", "mootcourt.cli", "serve", "--port", str(args.port), "--models-dir", str(models),
                                 "--reports-dir", str(reports), "--cards-dir", tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{args.port}"
            for _ in range(120):
                try:
                    urllib.request.urlopen(base + "/health", timeout=1).read()
                    break
                except Exception:
                    time.sleep(0.5)
            svc = []
            for i in range(args.calls):
                body = json.dumps({"source": args.source, "headline": f"{HEADLINES[i % len(HEADLINES)]} svc {i}", "image_changed": False,
                                   "impressions": args.impressions, "origin": now.isoformat()}).encode()
                req = urllib.request.Request(base + "/card", data=body, headers={"Content-Type": "application/json"})
                t = time.perf_counter()
                urllib.request.urlopen(req, timeout=10).read()
                svc.append(time.perf_counter() - t)
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    ms = lambda d: {k: (round(v * 1000, 1) if k != "n" else v) for k, v in d.items()}  # noqa: E731
    print(f"Card latency, source {args.source}, model {mid}, {args.impressions} impressions per arm\n")
    print(f"- Bundle load (once per process): {load_s * 1000:.0f} ms")
    print(f"- In process, bundle preloaded, {args.calls} issues (milliseconds): {ms(stats(issue))}; statuses {status}")
    print(f"- In process, weight on precedents forced to 0.5, {args.calls} issues (milliseconds): {ms(stats(weighted))}; "
          f"statuses {statuses_w}")
    print(f"- Command line, fresh process each time, 3 runs (milliseconds): {ms(stats(cli))}")
    print(f"- HTTP service on loopback, bundle preloaded, {args.calls} POST /card calls (milliseconds): {ms(stats(svc))}")
    ok = stats(issue)["p95"] < 1.0 and stats(svc)["p95"] < 1.0 and stats(weighted)["p95"] < 1.0
    if args.json_out:
        doc = {"source": args.source, "model_id": mid, "impressions": args.impressions, "bundle_load_ms": round(load_s * 1000, 1),
               "in_process_ms": ms(stats(issue)), "in_process_lambda_0.5_ms": ms(stats(weighted)),
               "cli_fresh_process_ms": ms(stats(cli)), "service_ms": ms(stats(svc)),
               "statuses": status, "statuses_lambda_0.5": statuses_w, "under_one_second_p95": bool(ok)}
        Path(args.json_out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"- Under one second at p95 with the index preloaded: {'yes' if ok else 'no'}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
