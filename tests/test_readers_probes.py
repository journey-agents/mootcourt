"""The three probes of what a model may recall: completion of a headline, familiarity with it, and a direct question."""
from __future__ import annotations

import pandas as pd
import pytest
from readers_world import make_world

from mootcourt.simulators.readers.probes import (
    batches,
    completion_items,
    completion_prompt,
    familiarity_items,
    familiarity_prompt,
    pair_items,
    pair_prompt,
    parse_completions,
    parse_seen,
    parse_winners,
    probe_measures,
    probe_units,
    token_f1,
)
from mootcourt.simulators.readers.prompts import ReplyError
from mootcourt.simulators.readers.protocol import COMPLETION_TEMPLATE, FAMILIARITY_TEMPLATE, PAIR_TEMPLATE


@pytest.fixture(scope="module")
def world():
    return make_world()


world_large = world


def unit_of(arm_ids: pd.Series) -> pd.Series:
    return arm_ids.str.rsplit("#", n=1).str[0]


def test_token_f1():
    assert token_f1("the cat sat", "The cat, sat!") == 1.0
    assert token_f1("a b", "c d") == 0.0 and token_f1("", "") == 0.0
    assert token_f1("a b c d", "a b") == pytest.approx(2 * 0.5 * 1.0 / 1.5)
    assert token_f1("a a b", "a b b") == pytest.approx(2 / 3)                     # multisets: one a and one b in common


def test_the_winner_is_the_arm_with_the_highest_click_rate(world):
    items = completion_items(world.arms, probe_units(world.arms, 20))
    w = items[items.role == "winner"].merge(world.arms, on="arm_id")
    best = (world.arms.assign(rate=lambda d: d.clicks / d.impressions).sort_values(["rate", "arm_id"], ascending=[False, True])
            .groupby("unit_id").arm_id.first())
    assert (w.arm_id.values == best[w.unit_id].values).all()
    assert len(w) == 20 and (items.groupby(unit_of(items.arm_id)).role.apply(sorted).map(tuple) == ("other", "winner")).all()
    assert (items.groupby(unit_of(items.arm_id)).arm_id.nunique() == 2).all()


def test_short_headlines_are_skipped_and_counted(world):
    items = completion_items(world.arms, list(world.units_with_a_short_headline))
    assert items.skipped.any() and (items[~items.skipped].stem.str.split().str.len() == 4).all()
    longer = items.merge(world.arms, on="arm_id")
    assert (longer.skipped == (longer.headline.str.split().str.len() < 8)).all()


def test_the_stem_and_the_rest_rebuild_the_headline(world):
    items = completion_items(world.arms, probe_units(world.arms, 20)).merge(world.arms, on="arm_id")
    ok = items[~items.skipped]
    assert ((ok.stem + " " + ok.rest).str.split().str.join(" ") == ok.headline.str.split().str.join(" ")).all()


def test_only_the_pair_prompt_names_the_publisher():
    assert "Upworthy" in PAIR_TEMPLATE
    assert "upworthy" not in (COMPLETION_TEMPLATE + FAMILIARITY_TEMPLATE).lower()


def test_the_probe_set_repeats_and_holds_300(world_large):
    a = probe_units(world_large.arms)
    assert a == probe_units(world_large.arms) and len(a) == 300 == len(set(a))


def test_familiarity_holds_every_arm_once_and_pairs_every_contrast_once(world):
    units = probe_units(world.arms, 30)
    seen = familiarity_items(world.arms, units)
    assert sorted(seen.arm_id) == sorted(world.arms[world.arms.unit_id.isin(units)].arm_id)
    pairs = pair_items(world.contrasts, world.arms, units)
    scored = world.contrasts[world.contrasts.unit_id.isin(units)]
    assert sorted(pairs.row_id) == sorted(scored.row_id)
    both = pairs.merge(scored, on="row_id")
    assert (both[["a_arm_id", "b_arm_id"]].apply(sorted, axis=1).map(tuple)
            == both[["arm_id", "ref_arm_id"]].apply(sorted, axis=1).map(tuple)).all()
    assert 0.2 < (both.a_arm_id == both.arm_id).mean() < 0.8                      # the variant is A about half the time
    assert list(pairs.row_id) != sorted(pairs.row_id) and pairs.equals(pair_items(world.contrasts, world.arms, units))


def test_batches_cut_a_frame_in_order():
    parts = batches(pd.DataFrame({"x": range(25)}), 10)
    assert [len(p) for p in parts] == [10, 10, 5] and list(pd.concat(parts).x) == list(range(25))


def test_the_prompts_are_the_fixed_copy_around_numbered_items():
    c = completion_prompt(["One two three four", "Five six seven eight"])
    assert c.startswith("Below are the first four words of headlines published on a news and entertainment site between 2013 and 2015.")
    assert "\n\n1. One two three four\n2. Five six seven eight\n\n" in c
    assert c.endswith('Reply as {"completions": [...]} with exactly 2 strings, one for each line in order.')
    f = familiarity_prompt(["Alpha beta"])
    assert "\n\n1. Alpha beta\n\n" in f and f.endswith('Reply as {"seen": [...]} with exactly 1 numbers, one for each headline in order.')
    p = pair_prompt([("First a", "First b"), ("Second a", "Second b")])
    assert "\n\n1. A: First a\n   B: First b\n2. A: Second a\n   B: Second b\n\n" in p
    assert p.endswith('Reply as {"winners": [...]} with exactly 2 entries, each "A" or "B".')


def test_probe_replies_are_checked_whole():
    assert parse_completions('{"completions": ["x y", "z"]}', 2) == ["x y", "z"]
    assert parse_seen('{"seen": [0, 100]}', 2) == [0.0, 100.0] and parse_winners('{"winners": ["A", "B"]}', 2) == ["A", "B"]
    for parse, bad in ((parse_completions, '{"completions": ["x"]}'), (parse_completions, '{"completions": ["x", 3]}'),
                       (parse_seen, '{"seen": [0, 101]}'), (parse_winners, '{"winners": ["A", "C"]}'), (parse_winners, "A and B")):
        with pytest.raises(ReplyError):
            parse(bad, 2)


def _oracle(world, units):
    pairs = pair_items(world.contrasts, world.arms, units)
    truth = world.contrasts.set_index("row_id")
    winners = {r.row_id: ("A" if (r.a_arm_id == truth.loc[r.row_id, "arm_id"]) == (truth.loc[r.row_id, "y"] > 0) else "B")
               for r in pairs.itertuples()}
    return pairs, winners


def test_a_model_that_knows_the_winner_scores_one_on_pairs(world):
    units = probe_units(world.arms, 40)
    pairs, winners = _oracle(world, units)
    out = probe_measures(world.arms, world.contrasts, units, pairs=pairs, winners=winners)
    assert out["pairs"]["direction_accuracy"] == 1.0 and out["pairs"]["n"] == len(pairs)
    flipped = {k: ("B" if v == "A" else "A") for k, v in winners.items()}
    assert probe_measures(world.arms, world.contrasts, units, pairs=pairs, winners=flipped)["pairs"]["direction_accuracy"] == 0.0


def test_completion_and_familiarity_measures(world):
    units = probe_units(world.arms, 40)
    items = completion_items(world.arms, units)
    # a model that recalls winners word for word and writes nothing useful for the others
    completions = {r.arm_id: (r.rest if r.role == "winner" else "nothing like it") for r in items[~items.skipped].itertuples()}
    rate = world.arms.set_index("arm_id").eval("clicks / impressions")
    seen = (100 * rate / rate.max()).to_dict()                                    # familiarity that tracks the click rate
    panel = world.contrasts.set_index("row_id").y * 1.0                             # a panel difference with the sign of the outcome
    out = probe_measures(world.arms, world.contrasts, units, items=items, completions=completions, seen=seen, panel_diff=panel)
    c = out["completion"]
    assert c["f1_winner"] == 1.0 and c["f1_other"] < 0.2 and c["f1_difference"] == pytest.approx(c["f1_winner"] - c["f1_other"])
    kept = items[~items.skipped].groupby(unit_of(items[~items.skipped].arm_id)).size()
    assert c["n_pairs"] == int((kept == 2).sum()) and c["n_skipped"] == int(items.skipped.sum())
    f = out["familiarity"]
    assert f["direction_accuracy"] == 1.0 and f["agreement_with_panel"] == 1.0
    assert f["n"] == int(world.contrasts.unit_id.isin(units).sum())


def test_a_missing_reply_leaves_its_items_out_of_the_count(world):
    units = probe_units(world.arms, 40)
    pairs, winners = _oracle(world, units)
    dropped = dict(list(winners.items())[5:])
    assert probe_measures(world.arms, world.contrasts, units, pairs=pairs, winners=dropped)["pairs"]["n"] == len(pairs) - 5
