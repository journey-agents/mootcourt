"""The stages behind the script, in process: what each prompt may hold, and when a run must stop instead of storing."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
from readers_world import make_world

from mootcourt.simulators.readers import pipeline, probes
from mootcourt.simulators.readers.align import visible_before
from mootcourt.simulators.readers.feeds import build_feeds
from mootcourt.simulators.readers.transcripts import Transcripts, request_hash

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fake_reader_tool", ROOT / "tests" / "fixtures" / "fake_reader_tool.py")
fake_reader_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_reader_tool)
MODEL = "claude-opus-5-5"


@pytest.fixture(scope="module")
def plan():
    world = make_world(seed=51, units=(40, 40, 40))
    return pipeline.Plan(arms=world.arms, contrasts=world.contrasts, feeds=build_feeds(world.arms),
                         probe_units=probes.probe_units(world.arms), snapshot="test")


def run(plan, folder, program, **kw):
    lines = []
    code = pipeline.run_model(plan, MODEL, Transcripts(folder), program=program, allow_model_calls=True, log=lines.append, **kw)
    return code, "\n".join(lines)


def test_every_prompt_shows_only_what_is_visible_at_its_origin(plan, tmp_path):
    t = Transcripts(tmp_path)
    plain, _ = pipeline.calls_of(plan, MODEL, "plain", t)
    assert plain and not any("% clicked" in c.prompt or "earlier tests" in c.prompt for c in plain)
    origin_of_block = plan.feeds.drop_duplicates("block_id").set_index("block_id").origin_index
    origins = plan.arms.groupby("origin_index").origin.first()
    examples, _ = pipeline.calls_of(plan, MODEL, "examples", t)
    assert examples and {int(origin_of_block[c.meta["block_id"]]) for c in examples} == {1, 2}
    for c in examples:
        allowed = set(visible_before(plan.arms, origins[origin_of_block[c.meta["block_id"]]]).headline)
        shown = set(re.findall(r"^   (.*) \(\d+\.\d\d% clicked\)$", c.prompt.split("The reader:")[0], re.M))
        assert shown and shown <= allowed
    for c in pipeline.note_calls(plan):
        allowed = set(visible_before(plan.arms, origins[c.meta["origin_index"]]).headline)
        assert set(re.findall(r"^   (.*) \(\d+\.\d\d% clicked\)$", c.prompt, re.M)) <= allowed


def test_no_two_planned_requests_are_the_same(plan, tmp_path):
    t = Transcripts(tmp_path)
    hashes = [request_hash(MODEL, c.kind, c.system, c.prompt, c.schema) for kind in ("plain", "examples", "probe_completion",
              "probe_familiarity", "probe_pairs", "brief_note") for c in pipeline.calls_of(plan, MODEL, kind, t)[0]]
    assert len(hashes) == len(set(hashes))
    pipeline.assert_unique_requests(plan)


def test_the_order_of_completion_items_does_not_mark_the_winner(plan):
    items = pipeline.completion_order(plan)
    winner_first = (items.role.to_numpy()[0::2] == "winner").mean()
    assert 0.3 < winner_first < 0.7 and not items.skipped.any()
    unit = items.arm_id.str.rsplit("#", n=1).str[0].to_numpy()
    assert (unit[1:] == unit[:-1]).mean() < 0.1                       # the two arms of a story are rarely neighbours


@pytest.mark.parametrize("workers", [1, 4])
def test_a_run_of_bad_replies_in_unknown_words_stops_the_run_and_stores_nothing(plan, tmp_path, workers):
    program = fake_reader_tool.make_fake(tmp_path / "f", say="The service is resting. Come back soon.")
    code, text = run(plan, tmp_path / "t", program, workers=workers, kinds=("plain",))
    assert code == pipeline.EXIT_TRANSPORT and "outstanding" in text
    assert Transcripts(tmp_path / "t").count(MODEL, "plain") == {}
    if workers == 1:
        assert program.calls() == 15                                     # five requests, three attempts each


def test_a_few_bad_replies_between_good_ones_are_stored_as_missing(plan, tmp_path):
    program = fake_reader_tool.make_fake(tmp_path / "f", bad_first=6, mode="planted")
    code, _ = run(plan, tmp_path / "t", program, workers=1, kinds=("plain",))
    assert code == 0 and Transcripts(tmp_path / "t").count(MODEL, "plain")["invalid"] == 2


def test_a_failure_inside_a_worker_is_raised_and_not_reported_as_done(plan, tmp_path):
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / MODEL).write_text("a file where the folder of the model should be")
    with pytest.raises(OSError):
        run(plan, tmp_path / "t", fake_reader_tool.make_fake(tmp_path / "f", mode="planted"), kinds=("plain",))


def test_an_origin_whose_note_was_refused_gets_no_brief_reader_and_blocks_nothing(plan, tmp_path):
    program = fake_reader_tool.make_fake(tmp_path / "f", mode="planted", refuse_some_notes=True)
    t = Transcripts(tmp_path / "t")
    code, text = run(plan, tmp_path / "t", program, workers=8, kinds=("brief_note", "brief"))
    status = {i: r["status"] for i, r in pipeline.notes_of(plan, MODEL, t).items()}
    assert sorted(status.values()) == ["ok", "refusal"], status         # this seed refuses one of the two notes
    assert code == 0 and "no audience note" in text
    left = pipeline.outstanding(plan, MODEL, t, kinds=("brief_note", "brief"))
    assert left == {"brief_note": 0, "brief": 0}
    refused = next(i for i, s in status.items() if s != "ok")
    blocks = set(plan.feeds[plan.feeds.origin_index == refused].block_id)
    assert not any(c.meta["block_id"] in blocks for c in pipeline.calls_of(plan, MODEL, "brief", t)[0])


def test_the_operator_can_record_one_named_request_as_missing(plan, tmp_path):
    t = Transcripts(tmp_path)
    call = pipeline.calls_of(plan, MODEL, "plain", t)[0][0]
    h = request_hash(MODEL, call.kind, call.system, call.prompt, call.schema)
    lines = []
    assert pipeline.record_missing(plan, MODEL, t, [h[:16]], log=lines.append) == 1
    stored = pipeline.stored(t, MODEL, call)
    assert stored["status"] == "invalid" and stored["recorded_by_operator"] is True and stored["meta"] == call.meta and h[:16] in lines[0]
    with pytest.raises(ValueError):
        pipeline.record_missing(plan, MODEL, t, ["0000000000000000"], log=lines.append)


def test_the_note_call_has_a_longer_time_cap(plan):
    assert pipeline.time_cap("brief_note") > pipeline.time_cap("plain") == 180.0
