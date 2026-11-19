"""Blocks and matched feeds: every feed of a block shows the same units in the same positions, one arm of each."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mootcourt.simulators.readers.feeds import build_feeds, feeds_checksum


def synthetic_arms(sizes=(70, 31), seed=3) -> pd.DataFrame:
    r = np.random.default_rng(seed)
    rows = []
    for origin_index, n in enumerate(sizes):
        for u in range(n):
            unit_id = f"t{origin_index}_{u:03d}@2014-0{origin_index + 1}-01"
            for k in range(int(r.integers(2, 7))):
                rows.append({"unit_id": unit_id, "origin_index": origin_index, "arm_id": f"{unit_id}#{k}",
                             "headline": f"Headline {origin_index} {u} {k}", "is_reference": k == 0})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def arms():
    return synthetic_arms()


@pytest.fixture(scope="module")
def feeds(arms):
    return build_feeds(arms)


def test_every_feed_of_a_block_holds_the_same_units_in_the_same_positions(feeds):
    for _, b in feeds.groupby("block_id"):
        layouts = {tuple(f.sort_values("position").unit_id) for _, f in b.groupby("feed_index")}
        assert len(layouts) == 1


def test_each_arm_appears_and_no_arm_twice_before_all_appeared(arms, feeds):
    for (block, unit), g in feeds.groupby(["block_id", "unit_id"]):
        k = arms[arms.unit_id == unit].shape[0]
        seq = list(g.sort_values("feed_index").arm_id)
        assert set(seq[:k]) == set(arms[arms.unit_id == unit].arm_id) or len(seq) < k
        assert len(set(seq[:k])) == min(k, len(seq))


def test_blocks_stay_within_an_origin_and_hold_at_most_30(feeds):
    assert feeds.groupby("block_id").origin_index.nunique().max() == 1
    assert feeds.groupby("block_id").unit_id.nunique().max() <= 30


def test_feed_count_is_the_largest_arm_count(arms, feeds):
    n = arms.groupby("unit_id").size()
    for block, b in feeds.groupby("block_id"):
        assert b.feed_index.nunique() == n[b.unit_id.unique()].max()


def test_two_builds_are_identical(arms):
    assert feeds_checksum(build_feeds(arms)) == feeds_checksum(build_feeds(arms))


def test_every_unit_is_in_exactly_one_block_and_blocks_are_numbered_per_origin(arms, feeds):
    assert feeds.groupby("unit_id").block_id.nunique().max() == 1
    assert set(feeds.unit_id) == set(arms.unit_id)
    assert sorted(feeds.block_id.unique()) == ["0-00", "0-01", "0-02", "1-00", "1-01"]
    assert feeds.position.min() == 1 and feeds.feed_index.min() == 0


def test_units_of_a_block_have_similar_arm_counts(arms, feeds):
    n = arms.groupby("unit_id").size()
    largest = feeds.groupby("block_id").unit_id.unique().map(lambda u: n[u].max())
    smallest = feeds.groupby("block_id").unit_id.unique().map(lambda u: n[u].min())
    assert largest["0-00"] <= smallest["0-01"] and largest["0-01"] <= smallest["0-02"]


def test_the_row_order_of_the_input_does_not_change_the_feeds(arms):
    assert feeds_checksum(build_feeds(arms.sample(frac=1.0, random_state=1))) == feeds_checksum(build_feeds(arms))
