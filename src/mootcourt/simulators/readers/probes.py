"""Three probes of what the model may recall about the archive, on a fixed draw of 300 units.

Completion: given the first four words of a headline, write the rest; the overlap with the published words is compared
between each unit's winning arm and one other arm. Familiarity: how sure the model is that it has seen a headline.
Pairs: the direct question of which of two headlines had the higher click rate, with the publisher named. The probes
describe the risk that a model's answers rest on recall. They cannot rule it out.
"""
from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd

from mootcourt.simulators.readers.prompts import ReplyError, first_json_object, is_number, numbered, one_line
from mootcourt.simulators.readers.protocol import (
    COMPLETION_TEMPLATE,
    FAMILIARITY_TEMPLATE,
    MIN_COMPLETION_WORDS,
    N_PROBE_UNITS,
    PAIR_TEMPLATE,
    STEM_WORDS,
    rng,
)

_OTHER_DRAW, _FAMILIARITY_SHUFFLE, _PAIR_SHUFFLE, _PAIR_ORDER, _COMPLETION_SHUFFLE = 0, 1, 2, 3, 4          # keys of the probe_items stream


def _arm_number(arm_id: str) -> int:
    return int(arm_id.rsplit("#", 1)[1])


def probe_units(arms: pd.DataFrame, n: int = N_PROBE_UNITS) -> list[str]:
    """The probe set: ``n`` units drawn once from all units, or every unit when fewer exist."""
    units = sorted(arms["unit_id"].unique())
    if len(units) <= n:
        return units
    return [units[i] for i in rng("probe_set").choice(len(units), size=n, replace=False)]


def completion_items(arms: pd.DataFrame, unit_ids: list[str]) -> pd.DataFrame:
    """Two arms per unit: the winner (highest click rate, lowest arm number on a tie) and one other, drawn. Short arms are skipped."""
    draw = rng("probe_items", _OTHER_DRAW)
    by_unit = {u: g for u, g in arms[arms["unit_id"].isin(unit_ids)].groupby("unit_id")}
    rows = []
    for unit in unit_ids:
        group = by_unit[unit].assign(number=lambda d: d["arm_id"].map(_arm_number), rate=lambda d: d["clicks"] / d["impressions"])
        group = group.sort_values(["rate", "number"], ascending=[False, True])
        winner, rest = group.iloc[0], group.iloc[1:].sort_values("number")
        chosen = [("winner", winner)]
        if len(rest):
            chosen.append(("other", rest.iloc[int(draw.integers(len(rest)))]))
        for role, arm in chosen:
            words = str(arm["headline"]).split()
            skipped = len(words) < MIN_COMPLETION_WORDS
            rows.append({"arm_id": arm["arm_id"], "role": role, "stem": "" if skipped else " ".join(words[:STEM_WORDS]),
                         "rest": "" if skipped else " ".join(words[STEM_WORDS:]), "skipped": skipped})
    return pd.DataFrame(rows, columns=["arm_id", "role", "stem", "rest", "skipped"])


def completion_order(items: pd.DataFrame) -> pd.DataFrame:
    """The completion items that are asked, shuffled, so that neither position nor a neighbour marks the winning arm."""
    asked = items[~items["skipped"]].reset_index(drop=True)
    return asked.iloc[rng("probe_items", _COMPLETION_SHUFFLE).permutation(len(asked))].reset_index(drop=True)


def familiarity_items(arms: pd.DataFrame, unit_ids: list[str]) -> pd.DataFrame:
    """Every arm of the probe units, shuffled."""
    mine = arms[arms["unit_id"].isin(unit_ids)].sort_values("arm_id")[["arm_id", "headline"]].reset_index(drop=True)
    return mine.iloc[rng("probe_items", _FAMILIARITY_SHUFFLE).permutation(len(mine))].reset_index(drop=True)


def pair_items(contrasts: pd.DataFrame, arms: pd.DataFrame, unit_ids: list[str]) -> pd.DataFrame:
    """Every scored contrast of the probe units, shuffled, with a drawn order of its two headlines."""
    mine = contrasts[contrasts["unit_id"].isin(unit_ids)].sort_values("row_id")[["row_id", "arm_id", "ref_arm_id"]].reset_index(drop=True)
    mine = mine.iloc[rng("probe_items", _PAIR_SHUFFLE).permutation(len(mine))].reset_index(drop=True)
    variant_first = rng("probe_items", _PAIR_ORDER).random(len(mine)) < 0.5
    headline = arms.set_index("arm_id")["headline"]
    a = np.where(variant_first, mine["arm_id"], mine["ref_arm_id"])
    b = np.where(variant_first, mine["ref_arm_id"], mine["arm_id"])
    return pd.DataFrame({"row_id": mine["row_id"].to_numpy(), "a_arm_id": a, "b_arm_id": b,
                         "a_headline": headline.reindex(a).to_numpy(), "b_headline": headline.reindex(b).to_numpy()})


def batches(frame: pd.DataFrame, size: int) -> list[pd.DataFrame]:
    return [frame.iloc[start:start + size] for start in range(0, len(frame), size)]


def _fill(template: str, items: str, n: int) -> str:
    return template.replace("{items}", items).replace("{n}", str(n))


def completion_prompt(stems: list[str]) -> str:
    return _fill(COMPLETION_TEMPLATE, numbered(stems), len(stems))


def familiarity_prompt(headlines: list[str]) -> str:
    return _fill(FAMILIARITY_TEMPLATE, numbered(headlines), len(headlines))


def pair_prompt(pairs: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"{i}. A: {one_line(a)}\n   B: {one_line(b)}" for i, (a, b) in enumerate(pairs, start=1))
    return _fill(PAIR_TEMPLATE, lines, len(pairs))


def _list_schema(key: str, n: int, items: dict) -> dict:
    return {"type": "object", "properties": {key: {"type": "array", "items": items, "minItems": n, "maxItems": n}},
            "required": [key], "additionalProperties": False}


def completions_schema(n: int) -> dict:
    return _list_schema("completions", n, {"type": "string"})


def seen_schema(n: int) -> dict:
    return _list_schema("seen", n, {"type": "number", "minimum": 0, "maximum": 100})


def winners_schema(n: int) -> dict:
    return _list_schema("winners", n, {"type": "string", "enum": ["A", "B"]})


def _parse_list(text: str, key: str, n: int, accept) -> list:
    obj = first_json_object(text)
    if obj is None or set(obj) != {key} or not isinstance(obj[key], list) or len(obj[key]) != n or not all(accept(v) for v in obj[key]):
        raise ReplyError(f"the reply is not an object with the one key {key} holding {n} valid entries")
    return obj[key]


def parse_completions(text: str, n: int) -> list[str]:
    return _parse_list(text, "completions", n, lambda v: isinstance(v, str))


def parse_seen(text: str, n: int) -> list[float]:
    return [float(v) for v in _parse_list(text, "seen", n, lambda v: is_number(v) and 0 <= v <= 100)]


def parse_winners(text: str, n: int) -> list[str]:
    return _parse_list(text, "winners", n, lambda v: v in ("A", "B"))


def _tokens(text: str) -> Counter:
    return Counter(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def token_f1(completion: str, truth: str) -> float:
    """F1 over the two multisets of lower-cased tokens. Two empty texts score 0."""
    a, b = _tokens(completion), _tokens(truth)
    common = sum((a & b).values())
    if common == 0:
        return 0.0
    precision, recall = common / sum(a.values()), common / sum(b.values())
    return 2 * precision * recall / (precision + recall)


def _sign_accuracy(guess: np.ndarray, y: np.ndarray) -> float:
    """Share of signs matched, an exact zero counting as half."""
    return float(np.where(guess == 0, 0.5, np.sign(guess) == np.sign(y)).mean()) if len(y) else float("nan")


def probe_measures(arms: pd.DataFrame, contrasts: pd.DataFrame, unit_ids: list[str], *, items: pd.DataFrame | None = None,
                   completions: dict | None = None, seen: dict | None = None, pairs: pd.DataFrame | None = None,
                   winners: dict | None = None, panel_diff: pd.Series | None = None) -> dict:
    """The measures of the probes that were answered. An item without a reply is left out and the counts say how many remain."""
    out: dict = {}
    scored = contrasts[contrasts["unit_id"].isin(unit_ids)]
    if items is not None and completions is not None:
        kept = items[~items["skipped"] & items["arm_id"].isin(completions)].copy()
        kept["f1"] = [token_f1(completions[r.arm_id], r.rest) for r in kept.itertuples()]
        kept["unit_id"] = kept["arm_id"].str.rsplit("#", n=1).str[0]
        wide = kept.pivot(index="unit_id", columns="role", values="f1").reindex(columns=["winner", "other"]).dropna()
        difference = (wide["winner"] - wide["other"]).to_numpy()
        n = len(wide)
        out["completion"] = {
            "f1_winner": float(wide["winner"].mean()) if n else float("nan"),
            "f1_other": float(wide["other"].mean()) if n else float("nan"),
            "f1_difference": float(difference.mean()) if n else float("nan"),
            "f1_difference_se": float(difference.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan"),
            "n_pairs": int(n), "n_skipped": int(items["skipped"].sum()),
        }
    if seen is not None:
        rating = pd.Series(seen, dtype=float)
        gap = (scored["arm_id"].map(rating) - scored["ref_arm_id"].map(rating)).to_numpy(dtype=float)
        has = ~np.isnan(gap)
        result = {"direction_accuracy": _sign_accuracy(gap[has], scored["y"].to_numpy(dtype=float)[has]), "n": int(has.sum()),
                  "ties": int((gap[has] == 0).sum())}
        if panel_diff is not None:
            panel = scored["row_id"].map(panel_diff).to_numpy(dtype=float)
            both = has & ~np.isnan(panel) & (gap != 0) & (panel != 0)
            result["agreement_with_panel"] = float((np.sign(gap[both]) == np.sign(panel[both])).mean()) if both.any() else float("nan")
            result["agreement_n"] = int(both.sum())
        out["familiarity"] = result
    if pairs is not None and winners is not None:
        answered = pairs[pairs["row_id"].isin(winners)].merge(scored[["row_id", "arm_id", "y"]], on="row_id")
        picked = np.where(answered["row_id"].map(winners) == "A", answered["a_arm_id"], answered["b_arm_id"])
        truth = np.where(answered["y"] > 0, answered["arm_id"], np.where(answered["a_arm_id"] == answered["arm_id"],
                                                                         answered["b_arm_id"], answered["a_arm_id"]))
        out["pairs"] = {"direction_accuracy": float((picked == truth).mean()) if len(answered) else float("nan"),
                        "n": int(len(answered))}
    return out
