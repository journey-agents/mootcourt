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
from mootcourt.simulators.readers.measures import ModelRun, agreement_report, model_report, transport_report
from mootcourt.simulators.readers.panel import answers_frame, directions, panel_scores, reader_scores
from mootcourt.simulators.readers.prompts import clicks_schema, parse_clicks, reader_prompt
from mootcourt.simulators.readers.protocol import (
    ARCHIVE_COUNTS,
    ARCHIVE_TOTALS,
    BRIEF_SYSTEM,
    COMPLETION_SYSTEM,
    DEFAULT_TIME_CAP_S,
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
    TIME_CAP_S,
)
from mootcourt.simulators.readers.transcripts import Transcripts, ask, request_hash

PLAN_FILES = ("arms.parquet", "contrasts.parquet", "feeds.parquet", "probes.json")
EXIT_NOT_ALLOWED, EXIT_TRANSPORT, EXIT_CANARY, EXIT_OUTSTANDING = 2, 3, 4, 5


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
    assert_unique_requests(plan)
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
        return [Call(kind, COMPLETION_SYSTEM, probes.completion_prompt(list(part["stem"])), probes.completions_schema(len(part)),
                     partial(probes.parse_completions, n=len(part)), {"arm_ids": list(part["arm_id"])})
                for part in probes.batches(completion_order(plan), size)]
    if kind == "probe_familiarity":
        items = probes.familiarity_items(plan.arms, plan.probe_units)
        return [Call(kind, FAMILIARITY_SYSTEM, probes.familiarity_prompt(list(part["headline"])), probes.seen_schema(len(part)),
                     partial(probes.parse_seen, n=len(part)), {"arm_ids": list(part["arm_id"])})
                for part in probes.batches(items, size)]
    items = probes.pair_items(plan.contrasts, plan.arms, plan.probe_units)
    return [Call(kind, PAIR_SYSTEM, probes.pair_prompt(list(zip(part["a_headline"], part["b_headline"]))),
                 probes.winners_schema(len(part)), partial(probes.parse_winners, n=len(part)),
                 {"row_ids": list(part["row_id"])}) for part in probes.batches(items, size)]


def completion_order(plan: Plan) -> pd.DataFrame:
    return probes.completion_order(probes.completion_items(plan.arms, plan.probe_units))


def time_cap(kind: str) -> float:
    return TIME_CAP_S.get(kind, DEFAULT_TIME_CAP_S)


def assert_unique_requests(plan: Plan) -> None:
    """Stop when two planned requests that need no note would be the same request: their replies could not be told apart."""
    empty = Transcripts(Path("/nonexistent-transcripts"))
    for kind in KINDS:
        if kind == "brief":          # the same feeds as the examples kind, behind another preface
            continue
        calls, _ = calls_of(plan, MODELS[0], kind, empty)
        hashes = [request_hash(MODELS[0], c.kind, c.system, c.prompt, c.schema) for c in calls]
        if len(hashes) != len(set(hashes)):
            raise ValueError(f"{len(hashes) - len(set(hashes))} planned requests of kind {kind} repeat another request")


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
        # An origin whose note was asked for and is not a usable reply gets no brief reader at all: its contrasts are
        # then counted as having no reader under method 7. An origin whose note is not stored yet blocks its reader calls.
        every = notes_of(plan, model, transcripts)
        notes = {i: r for i, r in every.items() if r["status"] == "ok"}
        calls = _reader_calls(plan, kind, {i: incontext.brief_preface(r["parsed"]) for i, r in notes.items()})
        waiting = [i for i in _later_origins(plan) if i not in every]
        per_feed = plan.feeds[plan.feeds["origin_index"].isin(waiting)].groupby("block_id")["feed_index"].nunique().sum()
        return calls, int(N_READERS * per_feed)
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
def record_missing(plan: Plan, model: str, transcripts: Transcripts, hashes: list[str], log: Callable[[str], None] = print) -> int:
    """Record named planned requests as missing, by the operator's explicit word. For a request the tool can never answer.

    Each name is a request hash or its first 16 or more characters. A name that matches no planned request that is still
    outstanding is an error. The record says who made it, and the run folder lists every one.
    """
    planned = {}
    for kind in KINDS:
        for call in calls_of(plan, model, kind, transcripts)[0]:
            planned[request_hash(model, call.kind, call.system, call.prompt, call.schema)] = call
    done = 0
    for name in hashes:
        found = [h for h in planned if h.startswith(name)] if len(name) >= 16 else []
        if len(found) != 1 or stored(transcripts, model, planned[found[0]]) is not None:
            raise ValueError(f"{name} does not name exactly one outstanding planned request of {model}")
        call = planned[found[0]]
        transcripts.put(model, call.kind, found[0], {
            "status": "invalid", "request_hash": found[0], "recorded_by_operator": True, "meta": call.meta, "reply_text": "",
            "parsed": None, "attempts": 0, "reported_model": None, "tool_version": None, "seconds": 0.0,
            "request": {"model": model, "kind": call.kind, "system": call.system, "prompt": call.prompt, "schema": call.schema}})
        log(f"{model} {call.kind}: request {name} recorded as missing by the operator")
        done += 1
    return done


def run_model(plan: Plan, model: str, transcripts: Transcripts, *, program: str = "claude", workers: int = 4, kinds=KINDS,
              allow_model_calls: bool = False, log: Callable[[str], None] = print, transport: str = "tool") -> int:
    """Make the calls of one model that are not stored, kind by kind. Returns an exit code; 0 means nothing is outstanding."""
    if not allow_model_calls:
        log("model calls are not allowed: pass --allow-model-calls to make them")
        return EXIT_NOT_ALLOWED
    for kind in [k for k in KINDS if k in kinds]:
        if kind == "brief":
            bad = sorted(i for i, r in notes_of(plan, model, transcripts).items() if r["status"] != "ok")
            if bad:
                log(f"{model}: no audience note for origin index {bad}; those origins get no brief reader and count as no reader")
        calls, blocked = calls_of(plan, model, kind, transcripts)
        todo = [call for call in calls if stored(transcripts, model, call) is None]
        log(f"{model} {kind}: {len(calls) - len(todo)} stored, {len(todo)} to make")
        failure = _make(todo, model, transcripts, program, workers, transport)
        if failure is not None or blocked:
            left = outstanding(plan, model, transcripts, kinds)
            why = (f"stopped after {MAX_TRANSPORT_FAILURES} calls in a row without a usable reply ({failure})" if failure is not None
                   else f"{blocked} reader calls wait for an audience note that is not stored")
            log(f"{model}: {why}; {sum(left.values())} calls outstanding: {left}")
            return EXIT_TRANSPORT
    left = outstanding(plan, model, transcripts, kinds)
    log(f"{model}: done, {sum(left.values())} calls outstanding")
    return 0 if not any(left.values()) else EXIT_TRANSPORT


def _make(todo: list[Call], model: str, transcripts: Transcripts, program: str, workers: int, transport: str = "tool") -> str | None:
    """Make the calls with a few threads. Returns a description once five calls in a row gave no usable reply, else None.

    A transport failure stores nothing. A reply that is still bad after its retries is held back and stored as missing
    only once a later call succeeds: a run of five such replies is far more likely a limit or an error in words the
    wrapper does not know than five refusals, so the run stops and the held replies are dropped. A failure of any other
    kind inside a worker stops the run and is raised.
    """
    pending, lock, stop = iter(todo), threading.Lock(), threading.Event()
    state = {"streak": 0, "last": None, "held": [], "error": None}

    def work():
        while not stop.is_set():
            with lock:
                call = next(pending, None)
            if call is None:
                return
            try:
                record = ask(transcripts, model, call.kind, call.system, call.prompt, call.schema, call.parse, program=program,
                             allow_model_calls=True, meta=call.meta, hold_bad=True, time_cap_s=time_cap(call.kind),
                             transport=transport)
                with lock:
                    if record["status"] == "ok":
                        if stop.is_set():          # the run has already stopped: the held replies stay dropped
                            return
                        state["streak"] = 0
                        for held in state["held"]:
                            transcripts.put(model, held["request"]["kind"], held["request_hash"], held)
                        state["held"] = []
                        continue
                    state["held"].append(record)
                    failure = f"a reply recorded as {record['status']}: {record['reply_text'].strip()[:120]}"
            except TransportError as exc:
                failure = str(exc)
            except BaseException as exc:          # a worker must not end silently: stop the others and raise in the caller
                with lock:
                    state["error"] = exc
                stop.set()
                return
            with lock:
                state["streak"] += 1
                state["last"] = failure
                if state["streak"] >= MAX_TRANSPORT_FAILURES:
                    stop.set()

    threads = [threading.Thread(target=work, daemon=True) for _ in range(max(1, min(workers, len(todo))))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if state["error"] is not None:
        raise state["error"]
    if stop.is_set():
        return state["last"]
    for held in state["held"]:          # fewer than five bad replies at the end of a kind: stored as missing
        transcripts.put(model, held["request"]["kind"], held["request_hash"], held)
    return None


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
        notes={call.meta["origin_index"]: incontext.clip_note(record["parsed"]) for call, record in records["brief_note"]
               if record["status"] == "ok"},
        notes_missing=[call.meta["origin_index"] for call, record in records["brief_note"] if record["status"] != "ok"],
        counts={"calls_planned": len(every), "calls_ok": status["ok"], "calls_invalid": status["invalid"],
                "calls_refusal": status["refusal"],
                "calls_recorded_by_operator": sum(1 for record in every if record.get("recorded_by_operator")),
                "calls_by_kind": {kind: len(pairs) for kind, pairs in records.items()}},
        tool_versions=dict(Counter(str(record["tool_version"]) for record in every if record["status"] == "ok")),
        reported_models=dict(Counter(str(record["reported_model"]) for record in every if record["status"] == "ok")),
        commit=commit, ledger=ledger, probes=measured)


def report_name(what: str, snapshot: str, label: str | None = None) -> str:
    """The file name of a report. A run with a label carries it in the name, so two runs can share a folder."""
    return f"simulated-readers-{what}-{label + '-' if label else ''}{snapshot}.json"


def score(plan: Plan, transcripts: Transcripts, ledger: pd.DataFrame, out, commit: str, models=MODELS,
          log: Callable[[str], None] = print, label: str | None = None) -> int:
    """Write one report per model and the agreement report, or refuse while any planned call of any model is not stored.

    With a ``label`` each report holds it as ``run_label`` and carries it in its file name; without one nothing differs.
    """
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
        if label:
            report["run_label"] = label
        path = out / report_name(model, plan.snapshot, label)
        path.write_text(json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        plain_of[model] = directions(plan.contrasts, panel_scores(reader_scores(plan.feeds, run.answers["plain"])))
        log(f"wrote {path}")
    agreement = {**agreement_report(plain_of), "snapshot": plan.snapshot, "commit": commit, "seed": SEED}
    if label:
        agreement["run_label"] = label
    path = out / report_name("agreement", plan.snapshot, label)
    path.write_text(json.dumps(agreement, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    log(f"wrote {path}")
    return 0


READINGS = ("plain_minus_always_reference", "weights_minus_plain", "text_with_panel_minus_text")


def compare(plan: Plan, tool: Transcripts, api: Transcripts, reports, label: str, out, commit: str, models=MODELS,
            log: Callable[[str], None] = print) -> int:
    """Write, for each model, the comparison of the run through the tool with the run through the API. No model is called.

    ``reports`` is the folder that holds the model reports of both runs; those of the API run carry ``label`` in their names.
    The three readings of each run are copied from those reports, so the comparison adds only what needs both runs.
    """
    for name, store in (("tool", tool), ("api", api)):
        left = {model: sum(outstanding(plan, model, store).values()) for model in models}
        if any(left.values()):
            log(f"the {name} run has calls outstanding: {left}")
            return EXIT_OUTSTANDING
    reports, out = Path(reports), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for model in models:
        plain = {}
        for name, store in (("tool", tool), ("api", api)):
            calls, _ = calls_of(plan, model, "plain", store)
            answers = answers_frame(stored(store, model, call) for call in calls)
            plain[name] = directions(plan.contrasts, panel_scores(reader_scores(plan.feeds, answers)))
        report = transport_report(plan.contrasts, plan.feeds, plain["tool"], plain["api"])
        saved = {"tool": json.loads((reports / report_name(model, plan.snapshot)).read_text(encoding="utf-8")),
                 "api": json.loads((reports / report_name(model, plan.snapshot, label)).read_text(encoding="utf-8"))}
        report["readings"] = {reading: {name: saved[name]["readings"][reading] for name in ("tool", "api")} for reading in READINGS}
        report.update(model=model, snapshot=plan.snapshot, commit=commit, seed=SEED, run_label=label,
                      commits={name: saved[name]["commit"] for name in ("tool", "api")})
        path = out / report_name(f"transport-{model}", plan.snapshot)
        path.write_text(json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        log(f"wrote {path}")
    return 0
