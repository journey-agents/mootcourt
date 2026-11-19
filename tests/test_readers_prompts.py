"""The reader prompt, the ten profiles and the reply schema: fixed copy, and replies that are checked and never clipped."""
from __future__ import annotations

import re

import pytest

from mootcourt.simulators.readers.prompts import ReplyError, clicks_schema, is_refusal, parse_clicks, reader_prompt
from mootcourt.simulators.readers.protocol import PROFILES, READER_TEMPLATE, SYSTEM_PROMPT


def test_prompt_shows_headlines_only_and_no_identifier():
    p = reader_prompt(PROFILES[0], ["Alpha beta", "Gamma delta"])
    assert "1. Alpha beta\n2. Gamma delta" in p and "exactly 2 numbers" in p
    assert not re.search(r"[0-9a-f]{24}|#\d|@20", p)


def test_the_prompt_is_the_fixed_template():
    p = reader_prompt("You are a reader.", ["Alpha beta", "Gamma delta"])
    assert p == ('The reader: You are a reader.\n\nThe feed:\n1. Alpha beta\n2. Gamma delta\n\n'
                 'Reply as {"clicks": [...]} with exactly 2 numbers, one for each headline in order, each from 0 to 100.')


def test_a_preface_comes_first_and_is_followed_by_one_blank_line():
    p = reader_prompt("You are a reader.", ["Alpha beta"], preface="What is known: little.")
    assert p.startswith("What is known: little.\n\nThe reader: You are a reader.")


def test_a_headline_with_a_line_break_stays_on_one_line():
    p = reader_prompt("R", ["Alpha\nbeta  gamma", "Delta"])
    assert "1. Alpha beta gamma\n2. Delta" in p


def test_no_profile_and_no_prompt_names_a_year_or_the_publisher():
    for text in (*PROFILES, READER_TEMPLATE):
        assert not re.search(r"\b20\d\d\b|upworthy", text, re.I)
    assert "between 2013 and 2015" in SYSTEM_PROMPT and "upworthy" not in SYSTEM_PROMPT.lower()


def test_there_are_ten_distinct_profiles():
    assert len(PROFILES) == 10 == len(set(PROFILES))


def test_the_schema_fixes_the_count_and_the_range():
    s = clicks_schema(3)
    assert s["properties"]["clicks"]["minItems"] == 3 == s["properties"]["clicks"]["maxItems"]
    assert s["properties"]["clicks"]["items"] == {"type": "number", "minimum": 0, "maximum": 100}
    assert s["required"] == ["clicks"] and s["additionalProperties"] is False


@pytest.mark.parametrize("text", ['{"clicks": [10, 101]}', '{"clicks": [10]}', '{"clicks": [10, "20"]}', '{"clicks": [10, null]}',
                                  '{"clicks": [10, true]}', '{"clicks": [10, -1]}', '{"clicks": [10, NaN]}', '{"clicks": 10}',
                                  '{"clicks": [10, 20], "note": "x"}', '[10, 20]', "I would click the first."])
def test_bad_replies_are_rejected_and_never_clipped(text):
    with pytest.raises(ReplyError):
        parse_clicks(text, 2)


def test_a_good_reply_inside_other_text_is_read():
    assert parse_clicks('Here: {"clicks": [0, 100]}', 2) == [0.0, 100.0]


def test_a_reply_without_json_is_a_refusal():
    assert is_refusal("I cannot play this role.") and not is_refusal('{"clicks": [1]}')
    assert is_refusal("I cannot {play} this role.")
