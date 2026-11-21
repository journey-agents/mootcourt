#!/usr/bin/env python3
"""Simulated readers on the headline-only tests of one run: plan, run, canary, score.

A panel of ten model-played readers scores headline cards in matched feeds. The design is in
``docs/superpowers/specs/2026-11-18-llm-simulated-readers-design.md`` and the exact values in
``docs/superpowers/plans/2026-11-18-simulated-readers.md``. The manual page is ``docs/simulated-readers.md``.

* ``plan --ledger L --scores S --out DIR`` fixes the units, the feeds and the probe set, counts every call, and writes them with
  their SHA-256. No model is called. ``--expect-archive-counts`` stops with exit code 2 unless the counts are the archive's.
* ``run --model NAME --plan DIR --transcripts DIR --allow-model-calls`` makes the calls that are not stored yet. Without the flag
  it exits with code 2 before anything else. After five calls in a row without a usable reply it exits with code 3 and stores
  nothing from that streak; start it again later and it resumes.
* ``canary --model NAME --transcripts DIR --allow-model-calls`` makes one call on five invented headlines with the tool's event
  stream on and stores the tool's own start record. Exit code 4 means the record lists a tool or a server, the reply cannot
  be read, or the tool does not report its model and version.
* ``score --plan DIR --transcripts DIR --ledger L --out DIR --commit HASH`` writes one report per model and the agreement
  report. It never calls a model, and it exits with code 5 while any planned call of any model is not stored.
  ``--label NAME`` names the run in each report and in its file name.
* ``run`` and ``canary`` take ``--transport api`` to reach the model through the vendor's API in place of the command line
  tool. The request is the same; the key is read from the environment variable ``ANTHROPIC_API_KEY`` and never stored.
  ``--transport local`` reaches any model behind an endpoint in the common chat format, such as a local model server;
  ``score --models NAME`` then scores that model.
* ``compare --plan DIR --tool DIR --api DIR --reports DIR --label NAME --out DIR --commit HASH`` writes, for each model, how
  the plain panels of the two transports compare. It never calls a model.

A ledger or scores file is refused when its name, a folder of its path or the target of a link holds holdout,
confirmatory or undeployed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from mootcourt.simulators.readers import api, local, pipeline
from mootcourt.simulators.readers.command import TransportError, same_model, start_record
from mootcourt.simulators.readers.prompts import ReplyError, clicks_schema, parse_clicks, reader_prompt
from mootcourt.simulators.readers.protocol import KINDS, MODELS, PROFILES, SYSTEM_PROMPT
from mootcourt.simulators.readers.transcripts import TRANSPORTS, Transcripts

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


def commit_hash(text: str) -> str:
    """The commit a report is recorded under: 7 to 40 hexadecimal digits, as git prints it."""
    if not re.fullmatch(r"[0-9a-f]{7,40}", text):
        raise argparse.ArgumentTypeError(f"--commit takes the hash of a commit, 7 to 40 hexadecimal digits, and got {text!r}")
    return text


def refuse_names(*paths) -> None:
    """Stop when a word of ``REFUSED_NAMES`` is in the file's name, in a folder of its path, or in the path a link leads to."""
    for path in paths:
        given = Path(path)
        parts = {part.lower() for part in (*given.parts, *given.resolve().parts)}
        if any(word in part for part in parts for word in REFUSED_NAMES):
            raise SystemExit(f"refused: {given} is named as a file this script does not open")


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
    if args.model in MODELS or args.program != "claude" or args.transport == "local":
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
    if args.record_missing:
        pipeline.record_missing(plan, args.model, Transcripts(args.transcripts), args.record_missing, log=log)
    return pipeline.run_model(plan, args.model, Transcripts(args.transcripts), program=args.program, workers=args.workers,
                              kinds=tuple(args.kinds or KINDS), allow_model_calls=True, log=log, transport=args.transport)


def _local_canary(model: str, prompt: str) -> dict:
    """One call through the local endpoint: the request as sent and what came back. Such an endpoint has no tool to list."""
    reply = local.call(model, SYSTEM_PROMPT, prompt)
    return {"request": local.request_body(model, SYSTEM_PROMPT, prompt), "tools": [], "servers": [], "reply_text": reply.text,
            "reported_model": reply.reported_model, "tool_version": reply.tool_version, "usage": reply.usage, "transport": "local"}


def cmd_canary(args) -> int:
    if not args.allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return pipeline.EXIT_NOT_ALLOWED
    if not _model_allowed(args):
        return 1
    prompt = reader_prompt(PROFILES[0], list(CANARY_HEADLINES))
    try:
        record = (api.canary(args.model, SYSTEM_PROMPT, prompt) if args.transport == "api"
                  else _local_canary(args.model, prompt) if args.transport == "local"
                  else start_record(args.model, SYSTEM_PROMPT, prompt, clicks_schema(len(CANARY_HEADLINES)), program=args.program))
    except TransportError as exc:
        log(f"the canary call failed: {exc}")
        return pipeline.EXIT_TRANSPORT
    record.update(model=args.model, headlines=list(CANARY_HEADLINES))
    problems = []
    try:
        parse_clicks(record["reply_text"], len(CANARY_HEADLINES))
    except ReplyError as exc:
        problems.append(f"the reply cannot be read: {exc}")
    if not record["reported_model"] or not same_model(args.model, record["reported_model"]):
        problems.append(f"the tool reports the model as {record['reported_model']!r}")
    if not record["tool_version"]:
        problems.append("the tool reports no version")
    if record["tools"] or record["servers"]:
        problems.append(f"the tool's start record lists tools {record['tools']} and servers {record['servers']}; both must be empty")
    record["problems"] = problems
    out = Path(args.transcripts)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"canary-{args.model}.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if problems:
        log(f"canary of {args.model} failed: " + "; ".join(problems))
        return pipeline.EXIT_CANARY
    log(f"canary of {args.model}: no tool and no server listed, the reply reads, model and version reported")
    return 0


def cmd_score(args) -> int:
    refuse_names(args.ledger)
    plan = pipeline.Plan.load(args.plan)
    return pipeline.score(plan, Transcripts(args.transcripts), pd.read_parquet(args.ledger), args.out, args.commit, log=log,
                          label=args.label, models=tuple(args.models or MODELS))


def cmd_compare(args) -> int:
    plan = pipeline.Plan.load(args.plan)
    return pipeline.compare(plan, Transcripts(args.tool), Transcripts(args.api), args.reports, args.label, args.out, args.commit,
                            log=log)


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
        p.add_argument("--transport", choices=TRANSPORTS, default="tool",
                       help="tool: the command line tool; api: the vendor's API, with the key in ANTHROPIC_API_KEY; "
                            "local: an endpoint in the common chat format, with its address in MOOTCOURT_READERS_ENDPOINT")
        if name == "run":
            p.add_argument("--plan", required=True)
            p.add_argument("--kinds", nargs="*", choices=KINDS)
            p.add_argument("--workers", type=int, default=4)
            p.add_argument("--record-missing", nargs="*", metavar="REQUEST_HASH",
                           help="record these outstanding requests as missing, for a request the tool can never answer")
        p.set_defaults(run=command)
    p = sub.add_parser("score", help="write the reports from stored transcripts; no model")
    p.add_argument("--plan", required=True)
    p.add_argument("--transcripts", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True, type=commit_hash)
    p.add_argument("--label", help="a name for this run, written into each report and its file name")
    p.add_argument("--models", nargs="+", help="the models to score; the three hosted models when not given")
    p.set_defaults(run=cmd_score)
    p = sub.add_parser("compare", help="compare the run through the tool with the run through the API; no model")
    p.add_argument("--plan", required=True)
    p.add_argument("--tool", required=True, help="the transcripts of the run through the command line tool")
    p.add_argument("--api", required=True, help="the transcripts of the run through the API")
    p.add_argument("--reports", required=True, help="the folder with the model reports of both runs")
    p.add_argument("--label", required=True, help="the label of the API run's reports")
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True, type=commit_hash)
    p.set_defaults(run=cmd_compare)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
