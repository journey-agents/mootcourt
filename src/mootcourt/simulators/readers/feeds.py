"""Blocks of units and their matched feeds.

Units of one origin are cut into blocks of at most 30 after ordering by arm count, so a block's units have similar arm
counts. A block has as many feeds as its largest arm count. Every feed of a block shows the same units in the same
positions and one arm of each, so two arms of a unit are read under the same surroundings.
"""
from __future__ import annotations

import hashlib

import pandas as pd

from mootcourt.simulators.readers.protocol import BLOCK_SIZE, rng


def build_feeds(arms: pd.DataFrame) -> pd.DataFrame:
    """One row per card: ``block_id``, ``origin_index``, ``feed_index`` (from 0), ``position`` (from 1), ``unit_id``, ``arm_id``."""
    out = []
    for origin_index, of_origin in arms.groupby("origin_index", sort=True):
        origin_index = int(origin_index)
        arm_ids = {u: sorted(g["arm_id"], key=_arm_number) for u, g in of_origin.groupby("unit_id")}
        units = sorted(arm_ids)
        shuffled = [units[i] for i in rng("blocks", origin_index).permutation(len(units))]
        ordered = sorted(shuffled, key=lambda u: len(arm_ids[u]))          # stable: the draw orders units within a count
        for block, start in enumerate(range(0, len(ordered), BLOCK_SIZE)):
            members = ordered[start:start + BLOCK_SIZE]
            n_feeds = max(len(arm_ids[u]) for u in members)
            sequences = {}
            for rank, unit in enumerate(members):
                draw, seq = rng("arms", origin_index, block, rank), []
                while len(seq) < n_feeds:
                    seq.extend(arm_ids[unit][i] for i in draw.permutation(len(arm_ids[unit])))
                sequences[unit] = seq[:n_feeds]
            layout = [members[i] for i in rng("positions", origin_index, block).permutation(len(members))]
            for feed_index in range(n_feeds):
                for position, unit in enumerate(layout, start=1):
                    out.append({"block_id": f"{origin_index}-{block:02d}", "origin_index": origin_index,
                                "feed_index": feed_index, "position": position, "unit_id": unit,
                                "arm_id": sequences[unit][feed_index]})
    return pd.DataFrame(out, columns=["block_id", "origin_index", "feed_index", "position", "unit_id", "arm_id"])


def _arm_number(arm_id: str) -> int:
    return int(arm_id.rsplit("#", 1)[1])


def feeds_checksum(feeds: pd.DataFrame) -> str:
    """SHA-256 of the feeds sorted by block, feed and position, written as CSV."""
    ordered = feeds.sort_values(["block_id", "feed_index", "position"])
    return hashlib.sha256(ordered.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()
