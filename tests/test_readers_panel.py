"""The panel score: centring per call, repeats averaged, the tie rule and the two rules for missing replies."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mootcourt.simulators.readers.panel import answers_frame, directions, panel_scores, reader_scores, split_half_agreement
from mootcourt.simulators.readers.prompts import clicks_schema


def _feeds(block_id, layout):
    """``layout`` is a list of feeds, each a list of arm identifiers in position order."""
    return [{"block_id": block_id, "origin_index": 0, "feed_index": f, "position": p, "unit_id": arm.split("#")[0], "arm_id": arm}
            for f, feed in enumerate(layout) for p, arm in enumerate(feed, start=1)]


@pytest.fixture
def feeds2():
    first = [["u1#0", "u2#0"], ["u1#1", "u2#1"], ["u1#0", "u2#2"]]          # u1 has two arms and three feeds: one is read twice
    second = [["u9#0", "u3#0"], ["u9#1", "u3#1"]]
    return pd.DataFrame(_feeds("0-00", first) + _feeds("0-01", second))


@pytest.fixture
def base_answers(feeds2):
    r = np.random.default_rng(5)
    calls = feeds2[["block_id", "feed_index", "position"]]
    frames = [calls.assign(reader=reader, prob=r.uniform(5, 60, len(calls)).round(1)) for reader in range(1, 11)]
    return pd.concat(frames, ignore_index=True)[["block_id", "feed_index", "reader", "position", "prob"]]


@pytest.fixture
def contrasts2():
    rows = [("r1", "u1#1", "u1#0", 0.02), ("r2", "u2#1", "u2#0", 0.03), ("r3", "u2#2", "u2#0", -0.01), ("r4", "u7#1", "u7#0", 0.01)]
    return pd.DataFrame([{"row_id": r, "arm_id": a, "ref_arm_id": b, "y": y} for r, a, b, y in rows])


def test_centring_removes_a_call_s_level(feeds2, base_answers):
    shifted = base_answers.assign(prob=lambda d: d.prob + np.where((d.reader == 3) & (d.feed_index == 0), 20, 0))
    a, b = reader_scores(feeds2, base_answers), reader_scores(feeds2, shifted)
    pd.testing.assert_series_equal(panel_scores(a), panel_scores(b))


def test_the_centred_score_is_the_probability_minus_the_mean_of_its_call(feeds2, base_answers):
    s = reader_scores(feeds2, base_answers).set_index(["arm_id", "reader"])
    call = base_answers[(base_answers.block_id == "0-01") & (base_answers.feed_index == 1) & (base_answers.reader == 2)]
    prob = call[call.position == 1].prob.iloc[0]                             # u9#1 is at position 1 of feed 1
    assert s.loc[("u9#1", 2), "centred"] == pytest.approx(prob - call.prob.mean())
    assert s.loc[("u9#1", 2), "raw"] == pytest.approx(prob)


def test_repeats_of_an_arm_are_averaged(feeds2, base_answers):
    # unit u1 has two arms in a block of three feeds, so one arm is read twice by every reader
    s = reader_scores(feeds2, base_answers)
    assert s[(s.arm_id == "u1#0") & (s.reader == 1)].shape[0] == 1
    mine = base_answers[(base_answers.reader == 1) & (base_answers.block_id == "0-00") & (base_answers.position == 1)]
    assert s[(s.arm_id == "u1#0") & (s.reader == 1)].raw.iloc[0] == pytest.approx(mine[mine.feed_index.isin([0, 2])].prob.mean())


def test_a_reader_missing_one_feed_leaves_the_whole_block(feeds2, base_answers):
    holed = base_answers.copy()
    holed.loc[(holed.reader == 4) & (holed.block_id == "0-00") & (holed.feed_index == 1), "prob"] = np.nan
    s = reader_scores(feeds2, holed)
    assert 4 not in set(s[s.arm_id.str.startswith(("u1", "u2"))].reader)   # the units of block 0-00
    assert 4 in set(s[s.arm_id.str.startswith("u9")].reader)               # a unit of another block
    assert s[s.arm_id == "u1#0"].reader.nunique() == 9


def test_a_call_that_was_never_answered_also_drops_the_reader_from_the_block(feeds2, base_answers):
    absent = base_answers[~((base_answers.reader == 4) & (base_answers.block_id == "0-00") & (base_answers.feed_index == 1))]
    s = reader_scores(feeds2, absent)
    assert s[s.arm_id == "u1#0"].reader.nunique() == 9 and 4 in set(s[s.arm_id == "u9#0"].reader)


def test_tie_counts_half_and_no_reader_is_counted_apart(contrasts2):
    d = directions(contrasts2, pd.Series({"u1#0": 1.0, "u1#1": 1.0, "u2#0": 0.0, "u2#1": 2.0, "u2#2": 1.0}))
    assert list(d.correct[:2]) == [0.5, 1.0] and bool(d.tie[0]) and not bool(d.no_reader[0])
    assert bool(d.no_reader.iloc[-1]) and d.correct.iloc[-1] == 0.5 and not bool(d.tie.iloc[-1])
    assert list(d.row_id) == list(contrasts2.row_id) and d.correct[2] == 0.0


def test_direction_is_the_sign_of_variant_minus_reference(contrasts2):
    d = directions(contrasts2, pd.Series({"u1#0": 0.0, "u1#1": -3.0, "u2#0": 0.0, "u2#1": 2.0}))
    assert d.correct[0] == float(contrasts2.y[0] < 0) and d["diff"][0] == -3.0


def test_weights_are_renormalised_over_the_readers_present(feeds2, base_answers):
    holed = base_answers.copy()
    holed.loc[(holed.reader == 10) & (holed.block_id == "0-00"), "prob"] = np.nan
    s = reader_scores(feeds2, holed)
    weights = np.array([0.5] + [0.0] * 8 + [0.5])                           # readers 1 and 10 only
    only_first = s[s.reader == 1].set_index("arm_id").centred
    assert panel_scores(s, weights=weights)["u1#0"] == pytest.approx(only_first["u1#0"])
    both = s[s.reader.isin([1, 10])].groupby("arm_id").centred.mean()
    assert panel_scores(s, weights=weights)["u9#0"] == pytest.approx(both["u9#0"])
    assert panel_scores(s, readers=(1, 10))["u9#0"] == pytest.approx(both["u9#0"])


def test_split_half_reads_no_outcome(contrasts2, feeds2, base_answers):
    s = reader_scores(feeds2, base_answers)
    out = split_half_agreement(contrasts2, s)
    assert out == split_half_agreement(contrasts2.assign(y=-contrasts2.y), s)
    assert out["n"] == 3 and 0.0 <= out["agree_share"] <= 1.0


def test_answers_come_from_stored_records_and_a_bad_record_is_all_missing():
    request = {"schema": clicks_schema(2)}
    records = [
        {"status": "ok", "parsed": [10.0, 30.0], "meta": {"block_id": "0-00", "feed_index": 0, "reader": 1}, "request": request},
        {"status": "invalid", "parsed": None, "meta": {"block_id": "0-00", "feed_index": 1, "reader": 1}, "request": request},
    ]
    a = answers_frame(records)
    assert list(a.columns) == ["block_id", "feed_index", "reader", "position", "prob"] and list(a.position) == [1, 2, 1, 2]
    assert list(a.prob[:2]) == [10.0, 30.0] and a.prob[2:].isna().all()
