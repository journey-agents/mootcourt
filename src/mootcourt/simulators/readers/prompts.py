"""The reader's prompt, the schema of its reply and the check of a reply. A reply is accepted whole or rejected whole."""
from __future__ import annotations

import json
import math

from mootcourt.simulators.readers.protocol import READER_TEMPLATE


class ReplyError(ValueError):
    """A reply that does not hold exactly what was asked for."""


def one_line(headline: str) -> str:
    """A headline as one line: any run of white space, line breaks included, becomes one space."""
    return " ".join(str(headline).split())


def numbered(lines: list[str]) -> str:
    return "\n".join(f"{i}. {one_line(text)}" for i, text in enumerate(lines, start=1))


def reader_prompt(profile: str, headlines: list[str], preface: str = "") -> str:
    """The prompt of one reader over one feed. A preface, when given, comes first and is followed by one blank line."""
    body = (READER_TEMPLATE.replace("{profile}", profile).replace("{n}", str(len(headlines)))
            .replace("{feed}", numbered(headlines)))
    return f"{preface}\n\n{body}" if preface else body


def clicks_schema(n: int) -> dict:
    return {"type": "object",
            "properties": {"clicks": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 100},
                                      "minItems": n, "maxItems": n}},
            "required": ["clicks"], "additionalProperties": False}


def first_json_object(text: str) -> dict | None:
    """The JSON object that starts at the first brace of the text, or None. A later brace is never tried."""
    start = text.find("{")
    if start < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(text, start)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def is_refusal(text: str) -> bool:
    """A reply with no JSON object in it: the model answered in words and gave no numbers."""
    return first_json_object(text) is None


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_clicks(text: str, n: int) -> list[float]:
    """Exactly ``n`` numbers from 0 to 100 under the one key ``clicks``, or a ``ReplyError``. Nothing is clipped or filled in."""
    obj = first_json_object(text)
    if obj is None:
        raise ReplyError("the reply holds no JSON object")
    if set(obj) != {"clicks"} or not isinstance(obj["clicks"], list):
        raise ReplyError("the reply is not an object with the one key clicks holding a list")
    values = obj["clicks"]
    if len(values) != n:
        raise ReplyError(f"the reply holds {len(values)} numbers and {n} were asked for")
    if not all(is_number(v) and 0 <= v <= 100 for v in values):
        raise ReplyError("an entry is not a number from 0 to 100")
    return [float(v) for v in values]
