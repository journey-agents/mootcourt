#!/usr/bin/env python3
"""Simulated readers on the headline-only tests of one run: plan, run, canary, score.

A panel of ten model-played readers scores headline cards in matched feeds. The design is in
``docs/superpowers/specs/2026-11-18-llm-simulated-readers-design.md`` and the exact values in
``docs/superpowers/plans/2026-11-18-simulated-readers.md``. The manual page is ``docs/simulated-readers.md``.

* ``plan --ledger L --scores S --out DIR`` fixes the units, the feeds and the probe set, counts every call, and writes them with
  their SHA-256. No model is called. ``--expect-archive-counts`` stops with exit code 2 unless the counts are the archive's.
* ``run --model NAME --plan DIR --transcripts DIR --allow-model-calls`` makes the calls that are not stored yet. Without the flag
  it exits with code 2 before anything else. After five transport failures in a row it exits with code 3; start it again later
  and it resumes.
* ``canary --model NAME --transcripts DIR --allow-model-calls`` makes one call on five invented headlines with the tool's event
  stream on and stores the tool's own start record. Exit code 4 means the record lists a tool or a server.
* ``score --plan DIR --transcripts DIR --ledger L --out DIR --commit HASH`` writes one report per model and the agreement
  report. It never calls a model, and it exits with code 5 while any planned call of any model is not stored.

A ledger or scores file whose name holds holdout, confirmatory or undeployed is refused.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from mootcourt.simulators.readers import pipeline
from mootcourt.simulators.readers.command import TransportError, start_record
from mootcourt.simulators.readers.prompts import clicks_schema, reader_prompt
from mootcourt.simulators.readers.protocol import KINDS, MODELS, PROFILES, SYSTEM_PROMPT
from mootcourt.simulators.readers.transcripts import Transcripts

REFUSED_NAMES = ("holdout", "confirmatory", "undeployed")

# Invented for the canary. None is an archive headline.
CANARY_HEADLINES = (
    "A town of nine hundred people voted on what to do with its only traffic light",
    "What a retired bus driver keeps in the glove box, and why her neighbours ask to see it",
    "Three students built a boat from milk cartons and it crossed the lake",
    "The reason this bakery closes at noon on Tuesdays is not what you would guess",
    "He counted every bird in his garden for a year and wrote down what changed",
)


def log(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def refuse_names(*paths) -> None:
    for path in paths:
        name = Path(path).name.lower()
        if any(word in name for word in REFUSED_NAMES):
            raise SystemExit(f"refused: {Path(path).name} is named as a file this script does not open")


def cmd_plan(args) -> int:
    refuse_names(args.ledger, args.scores)
    plan = pipeline.build_plan(pd.read_parquet(args.ledger), pd.read_parquet(args.scores), pipeline.snapshot_of(args.scores))
    if args.expect_archive_counts:
        wrong = pipeline.archive_mismatches(pipeline.plan_counts(plan))
        if wrong:
            log("the counts are not the archive's, so nothing is written:\n  " + "\n  ".join(wrong))
            return pipeline.EXIT_NOT_ALLOWED
    info = pipeline.write_plan(plan, args.out)
    print(json.dumps(info, indent=1, sort_keys=True))
    return 0


def _model_allowed(args) -> bool:
    if args.model in MODELS or args.program != "claude":
        return True
    log(f"{args.model} is not one of {', '.join(MODELS)}")
    return False


def cmd_run(args) -> int:
    if not args.allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return pipeline.EXIT_NOT_ALLOWED
    if not _model_allowed(args):
        return 1
    plan = pipeline.Plan.load(args.plan)
    return pipeline.run_model(plan, args.model, Transcripts(args.transcripts), program=args.program, workers=args.workers,
                              kinds=tuple(args.kinds or KINDS), allow_model_calls=True, log=log)


def cmd_canary(args) -> int:
    if not args.allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return pipeline.EXIT_NOT_ALLOWED
    if not _model_allowed(args):
        return 1
    try:
        record = start_record(args.model, SYSTEM_PROMPT, reader_prompt(PROFILES[0], list(CANARY_HEADLINES)),
                              clicks_schema(len(CANARY_HEADLINES)), program=args.program)
    except TransportError as exc:
        log(f"the canary call failed: {exc}")
        return pipeline.EXIT_TRANSPORT
    record.update(model=args.model, headlines=list(CANARY_HEADLINES))
    out = Path(args.transcripts)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"canary-{args.model}.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if record["tools"] or record["servers"]:
        log(f"the tool's start record lists tools {record['tools']} and servers {record['servers']}; both must be empty")
        return pipeline.EXIT_CANARY
    log(f"canary of {args.model}: no tool and no server listed")
    return 0


def cmd_score(args) -> int:
    refuse_names(args.ledger)
    plan = pipeline.Plan.load(args.plan)
    return pipeline.score(plan, Transcripts(args.transcripts), pd.read_parquet(args.ledger), args.out, args.commit, log=log)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("plan", help="fix units, feeds and probes; count the calls; no model")
    p.add_argument("--ledger", required=True)
    p.add_argument("--scores", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--expect-archive-counts", action="store_true")
    p.set_defaults(run=cmd_plan)
    for name, command in (("run", cmd_run), ("canary", cmd_canary)):
        p = sub.add_parser(name)
        p.add_argument("--model", required=True)
        p.add_argument("--transcripts", required=True)
        p.add_argument("--allow-model-calls", action="store_true")
        p.add_argument("--program", default="claude")
        if name == "run":
            p.add_argument("--plan", required=True)
            p.add_argument("--kinds", nargs="*", choices=KINDS)
            p.add_argument("--workers", type=int, default=4)
        p.set_defaults(run=command)
    p = sub.add_parser("score", help="write the reports from stored transcripts; no model")
    p.add_argument("--plan", required=True)
    p.add_argument("--transcripts", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True)
    p.set_defaults(run=cmd_score)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
