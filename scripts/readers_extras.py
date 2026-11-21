#!/usr/bin/env python3
"""Readings of the simulated readers added after the first two runs, and the calls of an open model that they need.

The plan is ``docs/superpowers/plans/2026-11-21-readers-quarters-and-open-model.md``. The manual page is
``docs/simulated-readers.md``.

* ``quarters --plan DIR --transcripts DIR --ledger L --out DIR --commit HASH`` writes, for each model, the three readings
  with the seven quarters as the units and the interval of the familiarity probe. It reads stored replies and calls no model.
* ``effort-canary --model NAME --out FILE --allow-model-calls`` makes twenty reader calls on invented headlines through the
  local endpoint and writes the tokens and seconds they took. It reads no archive headline.
* ``direct --model NAME --plan DIR --transcripts DIR --allow-model-calls`` makes the calls of the direct judgment that are
  not stored yet, through the local endpoint.
* ``embed --model NAME --plan DIR --ledger L --out FILE --allow-model-calls`` asks the local endpoint for the embedding of
  every headline of the source and writes them to one file.
* ``open-model --model NAME --plan DIR --transcripts DIR --ledger L --out DIR --commit HASH`` writes the report of the
  direct judgment and, with ``--vectors FILE --embedding-model NAME``, of the embedding classifier. ``--panel
  NAME=DIR:MODEL`` names a stored plain panel to add to that classifier and may be given several times. No model is called.

A ledger is refused when its name, a folder of its path or the target of a link holds holdout, confirmatory or undeployed.
The endpoint's address is read from ``MOOTCOURT_READERS_ENDPOINT``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt.simulators.readers import direct, embedfeature, extras, local, pipeline
from mootcourt.simulators.readers.command import TransportError
from mootcourt.simulators.readers.panel import directions, panel_scores, reader_scores
from mootcourt.simulators.readers.prompts import ReplyError, parse_clicks, reader_prompt
from mootcourt.simulators.readers.protocol import MODELS, PROFILES, SYSTEM_PROMPT
from mootcourt.simulators.readers.transcripts import Transcripts

_spec = importlib.util.spec_from_file_location("simulated_readers", Path(__file__).with_name("simulated_readers.py"))
_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_main)
log, refuse_names, commit_hash, CANARY_HEADLINES = _main.log, _main.refuse_names, _main.commit_hash, _main.CANARY_HEADLINES


def _write(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    log(f"wrote {path}")


def _outstanding(plan, models, transcripts) -> bool:
    left = {model: pipeline.outstanding(plan, model, transcripts) for model in models}
    for model, kinds in left.items():
        if sum(kinds.values()):
            log(f"{model}: {sum(kinds.values())} calls outstanding: {kinds}")
    return any(sum(kinds.values()) for kinds in left.values())


def _seen(plan, model: str, transcripts: Transcripts) -> dict:
    calls, _ = pipeline.calls_of(plan, model, "probe_familiarity", transcripts)
    records = [(call, pipeline.stored(transcripts, model, call)) for call in calls]
    return {arm: value for call, record in records if record["status"] == "ok" for arm, value in zip(call.meta["arm_ids"], record["parsed"])}


def cmd_quarters(args) -> int:
    refuse_names(args.ledger)
    plan, transcripts, ledger = pipeline.Plan.load(args.plan), Transcripts(args.transcripts), pd.read_parquet(args.ledger)
    if _outstanding(plan, args.models, transcripts):
        return pipeline.EXIT_OUTSTANDING
    for model in args.models:
        run = pipeline._model_run(plan, model, transcripts, ledger, args.commit)
        report = extras.quarters_report(run, model, seen=_seen(plan, model, transcripts), probe_units=plan.probe_units)
        report["snapshot"] = plan.snapshot
        if args.label:
            report["run_label"] = args.label
        _write(Path(args.out) / pipeline.report_name(f"quarters-{model}", plan.snapshot, args.label), report)
    return 0


def cmd_effort_canary(args) -> int:
    if not args.allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return pipeline.EXIT_NOT_ALLOWED
    orders = (list(CANARY_HEADLINES), list(reversed(CANARY_HEADLINES)))
    prompts = [reader_prompt(profile, order) for order in orders for profile in PROFILES]
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=len(prompts)) as pool:
            replies = list(pool.map(lambda prompt: local.call(args.model, SYSTEM_PROMPT, prompt, time_cap_s=600.0), prompts))
    except TransportError as exc:
        log(f"the canary failed: {exc}")
        return pipeline.EXIT_TRANSPORT
    wall = time.monotonic() - started
    readable = 0
    for reply in replies:
        try:
            parse_clicks(reply.text, len(CANARY_HEADLINES))
            readable += 1
        except ReplyError:
            pass
    tokens_in = [reply.usage["input_tokens"] for reply in replies]
    tokens_out = [reply.usage["output_tokens"] for reply in replies]
    _write(Path(args.out), {
        "model": args.model, "calls": len(replies), "readable": readable, "headlines": list(CANARY_HEADLINES),
        "setting": local.version(), "reported_models": sorted({str(reply.reported_model) for reply in replies}),
        "input_tokens_mean": float(np.mean(tokens_in)), "output_tokens_mean": float(np.mean(tokens_out)),
        "output_tokens_max": int(max(tokens_out)), "wall_seconds": round(wall, 1),
        "output_tokens_per_second_at_this_concurrency": float(sum(tokens_out) / wall) if wall > 0 else None})
    return 0 if readable == len(replies) else pipeline.EXIT_CANARY


def cmd_direct(args) -> int:
    if not args.allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return pipeline.EXIT_NOT_ALLOWED
    plan, transcripts = pipeline.Plan.load(args.plan), Transcripts(args.transcripts)
    calls = direct.direct_calls(plan, pipeline.Call)
    todo = [call for call in calls if pipeline.stored(transcripts, args.model, call) is None]
    log(f"{args.model} direct: {len(calls) - len(todo)} stored, {len(todo)} to make")
    failure = pipeline._make(todo, args.model, transcripts, "claude", args.workers, "local")
    left = sum(1 for call in calls if pipeline.stored(transcripts, args.model, call) is None)
    log(f"{args.model} direct: {left} calls outstanding" + (f"; stopped: {failure}" if failure else ""))
    return 0 if left == 0 else pipeline.EXIT_TRANSPORT


def cmd_embed(args) -> int:
    if not args.allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return pipeline.EXIT_NOT_ALLOWED
    refuse_names(args.ledger)
    plan = pipeline.Plan.load(args.plan)
    texts = embedfeature.headlines_of(pd.read_parquet(args.ledger), plan.contrasts)
    log(f"{len(texts)} headlines to embed with {args.model}")
    try:
        vectors = np.asarray(local.embed(args.model, texts), dtype=np.float32)
    except TransportError as exc:
        log(f"the embedding failed: {exc}")
        return pipeline.EXIT_TRANSPORT
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, texts=np.array(texts, dtype=object), vectors=vectors, model=np.array(args.model))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    log(f"wrote {out}: {vectors.shape[0]} vectors of dimension {vectors.shape[1]}, SHA-256 {digest}")
    return 0


def _direct_frame(plan, model: str, transcripts: Transcripts) -> tuple[pd.DataFrame | None, dict]:
    calls = direct.direct_calls(plan, pipeline.Call)
    records = [(call, pipeline.stored(transcripts, model, call)) for call in calls]
    if all(record is None for _, record in records):
        return None, {}
    if any(record is None for _, record in records):
        raise SystemExit(f"{sum(1 for _, r in records if r is None)} calls of the direct judgment are not stored")
    winners = {row: value for call, record in records if record["status"] == "ok" for row, value in zip(call.meta["row_ids"], record["parsed"])}
    counts = {"calls_planned": len(records), "calls_ok": sum(1 for _, r in records if r["status"] == "ok"),
              "calls_not_usable": sum(1 for _, r in records if r["status"] != "ok"),
              "settings": sorted({str(r["tool_version"]) for _, r in records if r["status"] == "ok"})}
    items = direct.direct_items(plan.contrasts, plan.arms, plan.feeds)
    return direct.direct_frame(plan.contrasts.reset_index(drop=True), items, winners), counts


def _plain_diff(plan, model: str, transcripts: Transcripts) -> pd.Series:
    if _outstanding(plan, [model], transcripts):
        raise SystemExit(f"the plain panel of {model} is not fully stored")
    run = pipeline._model_run(plan, model, transcripts, None, "")
    plain = directions(plan.contrasts, panel_scores(reader_scores(plan.feeds, run.answers["plain"])))
    return pd.Series(plain["diff"].to_numpy(), index=plan.contrasts["row_id"])


def cmd_open_model(args) -> int:
    refuse_names(args.ledger)
    plan, transcripts, ledger = pipeline.Plan.load(args.plan), Transcripts(args.transcripts), pd.read_parquet(args.ledger)
    if _outstanding(plan, [args.model], transcripts):
        return pipeline.EXIT_OUTSTANDING
    run = pipeline._model_run(plan, args.model, transcripts, ledger, args.commit)
    frame, counts = _direct_frame(plan, args.model, transcripts)
    embedding = None
    if args.vectors:
        stored = np.load(args.vectors, allow_pickle=True)
        table = embedfeature.unit_vectors(list(stored["texts"]), stored["vectors"])
        contrasts = plan.contrasts.reset_index(drop=True)
        embedding = {"model": args.embedding_model or str(stored["model"]),
                     "without": embedfeature.embedding_directions(ledger, contrasts, table)["correct"].to_numpy(), "with_panel": {}}
        for spec in args.panel or []:
            name, _, rest = spec.partition("=")
            root, _, model = rest.rpartition(":")
            diff = _plain_diff(plan, model, Transcripts(root))
            embedding["with_panel"][name] = embedfeature.embedding_directions(ledger, contrasts, table, diff)["correct"].to_numpy()
            log(f"embedding classifier with the panel {name}: done")
    report = extras.open_model_report(run, args.model, frame, embedding)
    report["snapshot"] = plan.snapshot
    if frame is not None:
        report["direct"]["counts"] = counts
    if args.vectors:
        report["embedding"]["vectors_sha256"] = hashlib.sha256(Path(args.vectors).read_bytes()).hexdigest()
    if args.label:
        report["run_label"] = args.label
    _write(Path(args.out) / pipeline.report_name(f"open-model-{args.model}", plan.snapshot, args.label), report)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("quarters", help="the three readings with the quarters as the units; no model")
    p.add_argument("--plan", required=True)
    p.add_argument("--transcripts", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True, type=commit_hash)
    p.add_argument("--label")
    p.add_argument("--models", nargs="+", default=list(MODELS))
    p.set_defaults(run=cmd_quarters)
    p = sub.add_parser("effort-canary", help="twenty reader calls on invented headlines, to measure tokens")
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--allow-model-calls", action="store_true")
    p.set_defaults(run=cmd_effort_canary)
    p = sub.add_parser("direct", help="make the calls of the direct judgment")
    p.add_argument("--model", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--transcripts", required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--allow-model-calls", action="store_true")
    p.set_defaults(run=cmd_direct)
    p = sub.add_parser("embed", help="embed every headline of the source")
    p.add_argument("--model", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--allow-model-calls", action="store_true")
    p.set_defaults(run=cmd_embed)
    p = sub.add_parser("open-model", help="the report of the direct judgment and the embedding classifier; no model")
    p.add_argument("--model", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--transcripts", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True, type=commit_hash)
    p.add_argument("--label")
    p.add_argument("--vectors")
    p.add_argument("--embedding-model")
    p.add_argument("--panel", action="append", metavar="NAME=DIR:MODEL")
    p.set_defaults(run=cmd_open_model)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
