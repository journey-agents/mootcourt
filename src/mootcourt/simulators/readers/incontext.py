"""Methods 6 and 7: earlier results put in front of the reader.

Method 6 shows ten earlier units with their click rates before the feed. Method 7 has the model write a note of at
most 150 words from a draw of 200 earlier units, and every reader of the origin receives that note. Both draw only
from units that ``visible_before`` allows at the origin, so neither exists at the first origin.
"""
from __future__ import annotations

import pandas as pd

from mootcourt.simulators.readers.align import visible_before
from mootcourt.simulators.readers.prompts import ReplyError, first_json_object, one_line
from mootcourt.simulators.readers.protocol import (
    BRIEF_PREFACE,
    BRIEF_TEMPLATE,
    EXAMPLES_HEADER,
    N_BRIEF_UNITS,
    N_EXAMPLES,
    NOTE_WORDS,
    rng,
)

BRIEF_SCHEMA = {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"], "additionalProperties": False}


def _visible_units(arms: pd.DataFrame, origin_index: int) -> list[str]:
    if origin_index <= 0:
        raise ValueError("no earlier result is visible at the first origin")
    origin = arms.loc[arms["origin_index"] == origin_index, "origin"].iloc[0]
    return sorted(visible_before(arms, origin)["unit_id"].unique())


def _draw(units: list[str], n: int, stream: str, origin_index: int) -> list[str]:
    if len(units) <= n:
        return units
    return [units[i] for i in rng(stream, origin_index).choice(len(units), size=n, replace=False)]


def example_units(arms: pd.DataFrame, origin_index: int, n: int = N_EXAMPLES) -> list[str]:
    """Ten units visible at the origin, drawn once per origin: every feed of the origin shows the same ten."""
    return _draw(_visible_units(arms, origin_index), n, "examples", origin_index)


def brief_units(arms: pd.DataFrame, origin_index: int, n: int = N_BRIEF_UNITS) -> list[str]:
    """Two hundred units visible at the origin, or every visible unit when fewer exist."""
    return _draw(_visible_units(arms, origin_index), n, "brief_draw", origin_index)


def _arm_number(arm_id: str) -> int:
    return int(arm_id.rsplit("#", 1)[1])


def render_units(arms: pd.DataFrame, unit_ids: list[str]) -> str:
    """Each unit as its number, then one line per arm: three spaces, the headline, and its click rate to two decimals."""
    by_unit = {u: g for u, g in arms[arms["unit_id"].isin(unit_ids)].groupby("unit_id")}
    lines = []
    for number, unit in enumerate(unit_ids, start=1):
        lines.append(f"{number}.")
        group = by_unit[unit]
        for _, arm in group.iloc[group["arm_id"].map(_arm_number).argsort(kind="stable")].iterrows():
            lines.append(f"   {one_line(arm['headline'])} ({100 * arm['clicks'] / arm['impressions']:.2f}% clicked)")
    return "\n".join(lines)


def examples_preface(arms: pd.DataFrame, unit_ids: list[str]) -> str:
    return EXAMPLES_HEADER + "\n" + render_units(arms, unit_ids)


def brief_prompt(arms: pd.DataFrame, unit_ids: list[str]) -> str:
    return BRIEF_TEMPLATE.replace("{units}", render_units(arms, unit_ids))


def clip_note(note: str, max_words: int = NOTE_WORDS) -> str:
    """The note unchanged when it has at most ``max_words`` words, and its first ``max_words`` words otherwise."""
    words = note.split()
    return note if len(words) <= max_words else " ".join(words[:max_words])


def brief_preface(note: str) -> str:
    return BRIEF_PREFACE.replace("{note}", one_line(clip_note(note)))


def parse_note(text: str) -> str:
    obj = first_json_object(text)
    if obj is None or set(obj) != {"note"} or not isinstance(obj["note"], str) or not obj["note"].strip():
        raise ReplyError("the reply is not an object with the one key note holding text")
    return obj["note"].strip()
