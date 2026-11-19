"""Methods 6 and 7: earlier results shown to the reader, drawn only from what is visible at the origin."""
from __future__ import annotations

import re

import pytest
from readers_world import make_world

from mootcourt.simulators.readers.align import visible_before
from mootcourt.simulators.readers.incontext import (
    BRIEF_SCHEMA,
    brief_preface,
    brief_prompt,
    brief_units,
    clip_note,
    example_units,
    examples_preface,
    parse_note,
)
from mootcourt.simulators.readers.prompts import ReplyError, reader_prompt
from mootcourt.simulators.readers.protocol import BRIEF_SYSTEM, BRIEF_TEMPLATE, EXAMPLES_HEADER


@pytest.fixture(scope="module")
def world():
    return make_world()


def test_examples_come_only_from_units_visible_at_the_origin(world):
    ids = example_units(world.arms, 2)
    seen = set(visible_before(world.arms, world.origin(2)).unit_id)
    assert len(ids) == 10 == len(set(ids)) and set(ids) <= seen


def test_a_unit_whose_result_is_not_in_hand_is_never_drawn(world):
    late = world.with_unit_usable_only_after(origin_index=1)
    assert "t_late@2014-01-01" not in brief_units(late.arms, 1)
    assert "t_late@2014-01-01" in brief_units(late.arms, 2)
    assert set(example_units(late.arms, 1)) <= set(visible_before(late.arms, late.origin(1)).unit_id)


def test_no_draw_exists_at_the_first_origin(world):
    for draw in (example_units, brief_units):
        with pytest.raises(ValueError):
            draw(world.arms, 0)


def test_the_preface_shows_rates_and_no_identifier(world):
    text = examples_preface(world.arms, example_units(world.arms, 2))
    assert text.startswith(EXAMPLES_HEADER) and re.search(r"\(\d+\.\d\d% clicked\)", text)
    assert not re.search(r"@|#\d", text)


def test_a_unit_is_its_number_then_one_line_per_arm_with_its_click_rate(world):
    unit = world.arms.unit_id.iloc[0]
    arms = world.arms[world.arms.unit_id == unit]
    lines = examples_preface(world.arms, [unit]).split("\n")
    assert lines[0] == EXAMPLES_HEADER and lines[1] == "1." and len(lines) == 2 + len(arms)
    first = arms.iloc[0]
    assert lines[2] == f"   {first.headline} ({100 * first.clicks / first.impressions:.2f}% clicked)"


def test_the_brief_draw_takes_every_unit_when_fewer_than_200_exist(world):
    assert set(brief_units(world.arms, 1)) == set(visible_before(world.arms, world.origin(1)).unit_id)


def test_the_brief_draw_holds_200_when_more_exist():
    big = make_world(seed=14, units=(260, 5, 5))
    ids = brief_units(big.arms, 1)
    assert len(ids) == 200 == len(set(ids)) and ids == brief_units(big.arms, 1)


def test_a_long_note_is_cut_at_150_words():
    assert len(clip_note("w " * 400).split()) == 150 and clip_note("short note") == "short note"


def test_draws_repeat(world):
    assert example_units(world.arms, 2) == example_units(world.arms, 2)
    assert example_units(world.arms, 2) != example_units(world.arms, 1)


def test_the_brief_prompt_is_the_fixed_template_around_the_units(world):
    ids = brief_units(world.arms, 1)[:3]
    text = brief_prompt(world.arms, ids)
    head, tail = BRIEF_TEMPLATE.split("{units}")
    assert text.startswith(head) and text.endswith(tail) and "3.\n" in text and "4.\n" not in text
    assert 'Reply as {"note": "..."}.' in text and "upworthy" not in (text + BRIEF_SYSTEM).lower()


def test_the_note_goes_before_the_reader_and_is_cut(world):
    preface = brief_preface("word " * 300)
    assert preface.startswith("What is known about this site's audience from earlier tests: word word")
    assert len(preface.split()) == 150 + 10
    prompt = reader_prompt("You are a reader.", ["Alpha beta"], preface=preface)
    assert prompt.startswith(preface + "\n\nThe reader: You are a reader.")


def test_a_note_is_read_from_the_reply_or_rejected():
    assert parse_note('{"note": " They click on surprises. "}') == "They click on surprises."
    assert BRIEF_SCHEMA["required"] == ["note"]
    for bad in ('{"note": ""}', '{"note": 3}', '{"text": "x"}', "They click on surprises."):
        with pytest.raises(ReplyError):
            parse_note(bad)
