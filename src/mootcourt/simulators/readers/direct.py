"""The direct judgment: the model is asked which of two headlines more people would click, with no reader in between.

Every scored contrast is asked once. A call holds ten contrasts of one block, so the intervals that resample whole
blocks apply as they do to the panel. The order of the contrasts within a block and the order of the two headlines of a
contrast are drawn from a seeded stream. No profile, no feed, no publisher and no date is named. This kind is no part
of the planned calls of a run: it has its own stage and its own report.
"""
from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd

from mootcourt.simulators.readers import probes
from mootcourt.simulators.readers.panel import direction_frame
from mootcourt.simulators.readers.prompts import one_line
from mootcourt.simulators.readers.protocol import COMPLETION_SYSTEM, rng

KIND = "direct"
DIRECT_SYSTEM = COMPLETION_SYSTEM
DIRECT_TEMPLATE = (
    "Each pair below holds two headlines written for the same story. For each pair, say which headline more people would "
    "click.\n"
    "\n"
    "{items}\n"
    "\n"
    'Reply as {"winners": [...]} with exactly {n} entries, each "A" or "B".'
)
DIRECT_BATCH = 10
_SHUFFLE, _ORDER = 0, 1          # keys of the direct_items stream


def direct_items(contrasts: pd.DataFrame, arms: pd.DataFrame, feeds: pd.DataFrame) -> pd.DataFrame:
    """Every contrast with its block, in a drawn order within the block, and a drawn order of its two headlines."""
    block_of_unit = feeds.drop_duplicates("unit_id").set_index("unit_id")["block_id"]
    mine = contrasts.sort_values("row_id")[["row_id", "unit_id", "arm_id", "ref_arm_id"]].reset_index(drop=True)
    mine["block_id"] = mine["unit_id"].map(block_of_unit)
    if mine["block_id"].isna().any():
        raise ValueError("a contrast has no block")
    mine = mine.iloc[rng("direct_items", _SHUFFLE).permutation(len(mine))]
    mine = mine.sort_values("block_id", kind="stable").reset_index(drop=True)
    variant_first = rng("direct_items", _ORDER).random(len(mine)) < 0.5
    headline = arms.set_index("arm_id")["headline"]
    a = np.where(variant_first, mine["arm_id"], mine["ref_arm_id"])
    b = np.where(variant_first, mine["ref_arm_id"], mine["arm_id"])
    return pd.DataFrame({"row_id": mine["row_id"].to_numpy(), "block_id": mine["block_id"].to_numpy(), "variant_first": variant_first,
                         "a_headline": headline.reindex(a).to_numpy(), "b_headline": headline.reindex(b).to_numpy()})


def direct_prompt(pairs: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"{i}. A: {one_line(a)}\n   B: {one_line(b)}" for i, (a, b) in enumerate(pairs, start=1))
    return probes._fill(DIRECT_TEMPLATE, lines, len(pairs))


def direct_calls(plan, call_type) -> list:
    """The calls of the direct judgment for a plan: ten contrasts per call, never across two blocks."""
    items = direct_items(plan.contrasts, plan.arms, plan.feeds)
    calls = []
    for block_id, block in items.groupby("block_id", sort=True):
        for part in probes.batches(block, DIRECT_BATCH):
            calls.append(call_type(KIND, DIRECT_SYSTEM, direct_prompt(list(zip(part["a_headline"], part["b_headline"]))),
                                   probes.winners_schema(len(part)), partial(probes.parse_winners, n=len(part)),
                                   {"row_ids": list(part["row_id"]), "block_id": block_id}))
    return calls


def direct_frame(contrasts: pd.DataFrame, items: pd.DataFrame, winners: dict) -> pd.DataFrame:
    """Per contrast, in the order of ``contrasts``: plus one when the variant was picked, minus one for the reference, no reader when unanswered."""
    variant_first = items.set_index("row_id")["variant_first"]
    diff = []
    for row_id in contrasts["row_id"]:
        picked = winners.get(row_id)
        diff.append(np.nan if picked is None else 1.0 if (picked == "A") == bool(variant_first[row_id]) else -1.0)
    return direction_frame(contrasts, np.array(diff, dtype=float))
