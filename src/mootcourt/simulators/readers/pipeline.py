"""The three stages behind ``scripts/simulated_readers.py``: plan (no model), run (model calls), score (no model).

``plan`` fixes the units, the feeds and the probe set and counts every call. ``run`` makes the calls that are not yet
stored and can be started again at any time. ``score`` refuses until every planned call of every model is stored, then
reads only the transcripts, the plan and the ledger.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import pandas as pd

from mootcourt.simulators.readers import incontext, probes
from mootcourt.simulators.readers.align import visible_before
from mootcourt.simulators.readers.command import TransportError
from mootcourt.simulators.readers.feeds import build_feeds, feeds_checksum
from mootcourt.simulators.readers.inputs import load_units
from mootcourt.simulators.readers.measures import ModelRun, agreement_report, model_report
from mootcourt.simulators.readers.panel import answers_frame, directions, panel_scores, reader_scores
from mootcourt.simulators.readers.prompts import clicks_schema, parse_clicks, reader_prompt
from mootcourt.simulators.readers.protocol import (
    ARCHIVE_COUNTS,
    ARCHIVE_TOTALS,
    BRIEF_SYSTEM,
    COMPLETION_SYSTEM,
    FAMILIARITY_SYSTEM,
    KINDS,
    MAX_TRANSPORT_FAILURES,
    MODELS,
    N_READERS,
    PAIR_SYSTEM,
    PROBE_BATCH,
    PROFILES,
    SEED,
    SYSTEM_PROMPT,
)
from mootcourt.simulators.readers.transcripts import Transcripts, ask, request_hash

PLAN_FILES = ("arms.parquet", "contrasts.parquet", "feeds.parquet", "probes.json")
EXIT_NOT_ALLOWED, EXIT_TRANSPORT, EXIT_CANARY, EXIT_OUTSTANDING, EXIT_NOTE = 2, 3, 4, 5, 6


@dataclass(frozen=True)
class Call:
    """One planned request: what is sent, how its reply is read, and the labels that tie the reply back to the plan."""

    kind: str
    system: str
    prompt: str
    schema: dict
    parse: Callable[[str], object]
    meta: dict


@dataclass
class Plan:
    arms: pd.DataFrame
    contrasts: pd.DataFrame
    feeds: pd.DataFrame
    probe_units: list[str]
    snapshot: str = "unknown"

    @classmethod
    def load(cls, folder) -> "Plan":
        folder = Path(folder)
        info = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        for name, digest in info["sha256"].items():
            if _sha256(folder / name) != digest:
                raise ValueError(f"{name} in {folder} is not the file the plan recorded")
        return cls(arms=pd.read_parquet(folder / "arms.parquet"), contrasts=pd.read_parquet(folder / "contrasts.parquet"),
                   feeds=pd.read_parquet(folder / "feeds.parquet"),
                   probe_units=json.loads((folder / "probes.json").read_text(encoding="utf-8"))["units"], snapshot=info["snapshot"])

    def origin_names(self) -> dict[int, str]:
        first = self.arms.groupby("origin_index")["origin"].first()
        return {int(i): pd.Timestamp(o).strftime("%Y-%m-%d") for i, o in first.items()}


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_of(scores_path) -> str:
    """The snapshot identifier in the name of a saved scores file, or ``unknown``."""
    found = re.search(r"(\d{8}-[0-9a-f]{12})", Path(scores_path).name)
    return found.group(1) if found else "unknown"


def build_plan(ledger: pd.DataFrame, scores: pd.DataFrame, snapshot: str = "unknown") -> Plan:
    arms, contrasts = load_units(ledger, scores)
    return Plan(arms=arms, contrasts=contrasts, feeds=build_feeds(arms), probe_units=probes.probe_units(arms), snapshot=snapshot)


def plan_counts(plan: Plan) -> dict:
    by_origin = {}
    for index, name in plan.origin_names().items():
        arms = plan.arms[plan.arms["origin_index"] == index]
        feeds = plan.feeds[plan.feeds["origin_index"] == index]
        origin = arms["origin"].iloc[0]
        by_origin[name] = {
            "units": int(arms["unit_id"].nunique()), "contrasts": int((plan.contrasts["origin_index"] == index).sum()),
            "blocks": int(feeds["block_id"].nunique()), "feeds": int(feeds.groupby("block_id")["feed_index"].nunique().sum()),
            "earlier_contrasts_visible": int(len(visible_before(plan.contrasts, origin))),
            "earlier_units_visible": int(visible_before(plan.arms, origin)["unit_id"].nunique()),
        }
    return {"units": int(plan.arms["unit_id"].nunique()), "tests": int(plan.arms["test_id"].nunique()),
            "contrasts": int(len(plan.contrasts)), "blocks": int(plan.feeds["block_id"].nunique()),
            "feeds": int(sum(o["feeds"] for o in by_origin.values())), "by_origin": by_origin}


def archive_mismatches(counts: dict) -> list[str]:
    """Every count that differs from the archive's, as text. Empty when the plan is the archive's."""
    out = [f"{key}: found {counts[key]}, expected {value}" for key, value in ARCHIVE_TOTALS.items() if counts[key] != value]
    keys = ("units", "contrasts", "blocks", "feeds", "earlier_contrasts_visible", "earlier_units_visible")
    if set(counts["by_origin"]) != set(ARCHIVE_COUNTS):
        out.append(f"origins: found {sorted(counts['by_origin'])}, expected {sorted(ARCHIVE_COUNTS)}")
    for name, expected in ARCHIVE_COUNTS.items():
        found = counts["by_origin"].get(name)
        if found is not None and tuple(found[k] for k in keys) != expected:
            out.append(f"{name}: found {tuple(found[k] for k in keys)}, expected {expected}")
    return out


def write_plan(plan: Plan, out) -> dict:
    """Write the plan's files and ``plan.json`` with the counts, the count of calls by kind and each file's SHA-256."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    plan.arms.to_parquet(out / "arms.parquet", index=False)
    plan.contrasts.to_parquet(out / "contrasts.parquet", index=False)
    plan.feeds.to_parquet(out / "feeds.parquet", index=False)
    items = probes.completion_items(plan.arms, plan.probe_units)
    (out / "probes.json").write_text(json.dumps({
        "units": plan.probe_units, "completion_arms": int((~items["skipped"]).sum()), "completion_skipped": int(items["skipped"].sum()),
        "familiarity_arms": int(len(probes.familiarity_items(plan.arms, plan.probe_units))),
        "pairs": int(len(probes.pair_items(plan.contrasts, plan.arms, plan.probe_units)))}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    by_kind = planned_counts(plan)
    info = {"snapshot": plan.snapshot, "seed": SEED, "models": list(MODELS), "counts": plan_counts(plan),
            "calls": {"by_kind": by_kind, "per_model": sum(by_kind.values()), "all_models": len(MODELS) * sum(by_kind.values())},
            "feeds_checksum": feeds_checksum(plan.feeds), "sha256": {name: _sha256(out / name) for name in PLAN_FILES}}
    (out / "plan.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return info


# ---------------------------------------------------------------------------------------------------------------- calls
def _reader_calls(plan: Plan, kind: str, preface_of: dict[int, str] | None) -> list[Call]:
    """Ten reader calls per feed. With ``preface_of`` only the origins it names are read, each with its preface first."""
    headline = plan.arms.set_index("arm_id")["headline"]
    calls = []
    for (block_id, feed_index), feed in plan.feeds.groupby(["block_id", "feed_index"], sort=True):
        origin_index = int(feed["origin_index"].iloc[0])
        if preface_of is not None and origin_index not in preface_of:
            continue
        lines = [headline[a] for a in feed.sort_values("position")["arm_id"]]
        schema, n = clicks_schema(len(lines)), len(lines)
        for reader in range(1, N_READERS + 1):
            prompt = reader_prompt(PROFILES[reader - 1], lines, preface="" if preface_of is None else preface_of[origin_index])
            calls.append(Call(kind, SYSTEM_PROMPT, prompt, schema, lambda text, n=n: parse_clicks(text, n),
                              {"block_id": block_id, "feed_index": int(feed_index), "reader": reader}))
    return calls


def _later_origins(plan: Plan) -> list[int]:
    return [i for i in sorted(plan.origin_names()) if i > 0]


def note_calls(plan: Plan) -> list[Call]:
    return [Call("brief_note", BRIEF_SYSTEM, incontext.brief_prompt(plan.arms, incontext.brief_units(plan.arms, i)),
                 incontext.BRIEF_SCHEMA, incontext.parse_note, {"origin_index": i}) for i in _later_origins(plan)]


def _probe_calls(plan: Plan, kind: str) -> list[Call]:
    size = PROBE_BATCH[kind]
    if kind == "probe_completion":
        items = probes.completion_items(plan.arms, plan.probe_units)
        return [Call(kind, COMPLETION_SYSTEM, probes.completion_prompt(list(part["stem"])), probes.completions_schema(len(part)),
                     partial(probes.parse_completions, n=len(part)), {"arm_ids": list(part["arm_id"])})
                for part in probes.batches(items[~items["skipped"]], size)]
    if kind == "probe_familiarity":
        items = probes.familiarity_items(plan.arms, plan.probe_units)
        return [Call(kind, FAMILIARITY_SYSTEM, probes.familiarity_prompt(list(part["headline"])), probes.seen_schema(len(part)),
                     partial(probes.parse_seen, n=len(part)), {"arm_ids": list(part["arm_id"])})
                for part in probes.batches(items, size)]
    items = probes.pair_items(plan.contrasts, plan.arms, plan.probe_units)
    return [Call(kind, PAIR_SYSTEM, probes.pair_prompt(list(zip(part["a_headline"], part["b_headline"]))),
                 probes.winners_schema(len(part)), partial(probes.parse_winners, n=len(part)),
                 {"row_ids": list(part["row_id"])}) for part in probes.batches(items, size)]


def stored(transcripts: Transcripts, model: str, call: Call) -> dict | None:
    return transcripts.get(model, call.kind, request_hash(model, call.kind, call.system, call.prompt, call.schema))


def notes_of(plan: Plan, model: str, transcripts: Transcripts) -> dict[int, dict]:
    """The stored note record of each later origin that has one."""
    found = {}
    for call in note_calls(plan):
        record = stored(transcripts, model, call)
        if record is not None:
            found[call.meta["origin_index"]] = record
    return found


def calls_of(plan: Plan, model: str, kind: str, transcripts: Transcripts) -> tuple[list[Call], int]:
    """The calls of one kind that can be built now, and the count that cannot because their origin's note is not stored."""
    if kind == "plain":
        return _reader_calls(plan, kind, None), 0
    if kind == "brief_note":
        return note_calls(plan), 0
    if kind == "examples":
        prefaces = {i: incontext.examples_preface(plan.arms, incontext.example_units(plan.arms, i)) for i in _later_origins(plan)}
        return _reader_calls(plan, kind, prefaces), 0
    if kind == "brief":
        notes = {i: r for i, r in notes_of(plan, model, transcripts).items() if r["status"] == "ok"}
        calls = _reader_calls(plan, kind, {i: incontext.brief_preface(r["parsed"]) for i, r in notes.items()})
        return calls, planned_counts(plan)["brief"] - len(calls)
    return _probe_calls(plan, kind), 0


def planned_counts(plan: Plan) -> dict[str, int]:
    """The count of calls of each kind for one model. It reads no transcript."""
    feeds_later = plan.feeds[plan.feeds["origin_index"] > 0].groupby("block_id")["feed_index"].nunique().sum()
    feeds_all = plan.feeds.groupby("block_id")["feed_index"].nunique().sum()
    out = {"plain": int(N_READERS * feeds_all), "brief_note": len(_later_origins(plan)), "examples": int(N_READERS * feeds_later),
           "brief": int(N_READERS * feeds_later)}
    out.update({kind: len(_probe_calls(plan, kind)) for kind in PROBE_BATCH})
    return {kind: out[kind] for kind in KINDS}


def outstanding(plan: Plan, model: str, transcripts: Transcripts, kinds=KINDS) -> dict[str, int]:
    """Per kind, the count of planned calls of this model that are not stored."""
    out = {}
    for kind in kinds:
        calls, blocked = calls_of(plan, model, kind, transcripts)
        out[kind] = blocked + sum(1 for call in calls if stored(transcripts, model, call) is None)
    return out


# ------------------------------------------------------------------------------------------------------------------ run
def run_model(plan: Plan, model: str, transcripts: Transcripts, *, program: str = "claude", workers: int = 4, kinds=KINDS,
              allow_model_calls: bool = False, log: Callable[[str], None] = print) -> int:
    """Make the calls of one model that are not stored, kind by kind. Returns an exit code; 0 means nothing is outstanding."""
    if not allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return EXIT_NOT_ALLOWED
    for kind in [k for k in KINDS if k in kinds]:
        if kind == "brief":
            bad = {i: r["status"] for i, r in notes_of(plan, model, transcripts).items() if r["status"] != "ok"}
            if bad:
                log(f"the audience note of origin index {sorted(bad)} is recorded as {sorted(set(bad.values()))}; every reader call of "
                    "that origin depends on it, so the run stops here")
                return EXIT_NOTE
        calls, blocked = calls_of(plan, model, kind, transcripts)
        todo = [call for call in calls if stored(transcripts, model, call) is None]
        log(f"{model} {kind}: {len(calls) - len(todo)} stored, {len(todo)} to make")
        failures = _make(todo, model, transcripts, program, workers)
        if failures is not None or blocked:
            left = outstanding(plan, model, transcripts, kinds)
            why = (f"stopped after {MAX_TRANSPORT_FAILURES} transport failures in a row ({failures})" if failures is not None
                   else f"{blocked} reader calls wait for an audience note that is not stored")
            log(f"{model}: {why}; {sum(left.values())} calls outstanding: {left}")
            return EXIT_TRANSPORT
    left = outstanding(plan, model, transcripts, kinds)
    log(f"{model}: done, {sum(left.values())} calls outstanding")
    return 0 if not any(left.values()) else EXIT_TRANSPORT


def _make(todo: list[Call], model: str, transcripts: Transcripts, program: str, workers: int) -> str | None:
    """Make the calls with a few threads. Returns the last transport failure once five have come in a row, else None."""
    pending, lock, stop = iter(todo), threading.Lock(), threading.Event()
    state = {"streak": 0, "last": None}

    def work():
        while not stop.is_set():
            with lock:
                call = next(pending, None)
            if call is None:
                return
            try:
                ask(transcripts, model, call.kind, call.system, call.prompt, call.schema, call.parse, program=program,
                    allow_model_calls=True, meta=call.meta)
            except TransportError as exc:
                with lock:
                    state["streak"] += 1
                    state["last"] = str(exc)
                    if state["streak"] >= MAX_TRANSPORT_FAILURES:
                        stop.set()
            else:
                with lock:
                    state["streak"] = 0

    threads = [threading.Thread(target=work, daemon=True) for _ in range(max(1, min(workers, len(todo))))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return state["last"] if stop.is_set() else None


# ---------------------------------------------------------------------------------------------------------------- score
def _model_run(plan: Plan, model: str, transcripts: Transcripts, ledger: pd.DataFrame | None, commit: str) -> ModelRun:
    records: dict[str, list[tuple[Call, dict]]] = {}
    for kind in KINDS:
        calls, _ = calls_of(plan, model, kind, transcripts)
        records[kind] = [(call, stored(transcripts, model, call)) for call in calls]
    every = [record for pairs in records.values() for _, record in pairs]
    status = Counter(record["status"] for record in every)
    answers = {kind: answers_frame(record for _, record in records[kind]) for kind in ("plain", "examples", "brief")}

    def gathered(kind: str, key: str) -> dict:
        return {item: value for call, record in records[kind] if record["status"] == "ok"
                for item, value in zip(call.meta[key], record["parsed"])}

    plain = directions(plan.contrasts, panel_scores(reader_scores(plan.feeds, answers["plain"])))
    measured = probes.probe_measures(
        plan.arms, plan.contrasts, plan.probe_units, items=probes.completion_items(plan.arms, plan.probe_units),
        completions=gathered("probe_completion", "arm_ids"), seen=gathered("probe_familiarity", "arm_ids"),
        pairs=probes.pair_items(plan.contrasts, plan.arms, plan.probe_units), winners=gathered("probe_pairs", "row_ids"),
        panel_diff=pd.Series(plain["diff"].to_numpy(), index=plan.contrasts["row_id"]))
    measured["units"] = len(plan.probe_units)
    return ModelRun(
        arms=plan.arms, contrasts=plan.contrasts, feeds=plan.feeds, answers=answers,
        notes={call.meta["origin_index"]: incontext.clip_note(record["parsed"]) for call, record in records["brief_note"]},
        counts={"calls_planned": len(every), "calls_ok": status["ok"], "calls_invalid": status["invalid"],
                "calls_refusal": status["refusal"], "calls_by_kind": {kind: len(pairs) for kind, pairs in records.items()}},
        tool_versions=dict(Counter(str(record["tool_version"]) for record in every if record["status"] == "ok")),
        reported_models=dict(Counter(str(record["reported_model"]) for record in every if record["status"] == "ok")),
        commit=commit, ledger=ledger, probes=measured)


def score(plan: Plan, transcripts: Transcripts, ledger: pd.DataFrame, out, commit: str, models=MODELS,
          log: Callable[[str], None] = print) -> int:
    """Write one report per model and the agreement report, or refuse while any planned call of any model is not stored."""
    left = {model: outstanding(plan, model, transcripts) for model in models}
    if any(sum(kinds.values()) for kinds in left.values()):
        for model, kinds in left.items():
            if sum(kinds.values()):
                log(f"{model}: {sum(kinds.values())} calls outstanding: {kinds}")
        log("nothing is scored until every planned call of every model is stored or recorded as missing")
        return EXIT_OUTSTANDING
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    plain_of = {}
    for model in models:
        run = _model_run(plan, model, transcripts, ledger, commit)
        report = model_report(run, model)
        report["snapshot"] = plan.snapshot
        path = out / f"simulated-readers-{model}-{plan.snapshot}.json"
        path.write_text(json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        plain_of[model] = directions(plan.contrasts, panel_scores(reader_scores(plan.feeds, run.answers["plain"])))
        log(f"wrote {path}")
    agreement = {**agreement_report(plain_of), "snapshot": plan.snapshot, "commit": commit, "seed": SEED}
    path = out / f"simulated-readers-agreement-{plan.snapshot}.json"
    path.write_text(json.dumps(agreement, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    log(f"wrote {path}")
    return 0
