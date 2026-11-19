"""The measures: paired differences with block resampling, the family of three, ranking, and the report of one model."""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import scipy.special
from readers_world import make_answers, make_world

from mootcourt.simulators.readers.feeds import build_feeds
from mootcourt.simulators.readers.measures import ModelRun, accuracy, agreement_report, model_report, paired_difference, ranking
from mootcourt.simulators.readers.panel import direction_frame


def _rows(n_blocks=40, per_block=25, seed=0):
    r = np.random.default_rng(seed)
    block = np.repeat([f"b{i:02d}" for i in range(n_blocks)], per_block)
    row_id = [f"r{i:04d}" for i in range(len(block))]
    contrasts = pd.DataFrame({"row_id": row_id, "test_id": [f"t{i // 2}" for i in range(len(block))], "y": r.normal(0, 1, len(block))})
    return contrasts, pd.Series(block, index=row_id), r


def planted(shift: float, seed: int = 1):
    contrasts, block, r = _rows(seed=seed)
    b = (r.random(len(contrasts)) < 0.5).astype(float)
    a = np.clip(b + (r.random(len(contrasts)) < abs(shift)) * np.sign(shift), 0, 1) if shift else b.copy()
    if not shift:
        a = (r.random(len(contrasts)) < 0.5).astype(float)
    return SimpleNamespace(contrasts=contrasts, a=a, b=b, block=block)


simple = planted(0.1, seed=2)
simple.correct_with_two_ties_one_missing = direction_frame(
    pd.DataFrame({"row_id": ["a", "b", "c", "d", "e"], "y": [1.0, -1.0, 1.0, 1.0, -1.0]}), np.array([0.0, 0.0, np.nan, 2.0, 3.0]))


@pytest.fixture(scope="module")
def clustered():
    contrasts, block, r = _rows(seed=3)
    moves = pd.Series(r.random(block.nunique()) < 0.5, index=sorted(block.unique()))           # a whole block is right or wrong together
    a = block.map(moves).to_numpy(dtype=float)
    b = np.full(len(a), 0.5)
    iid_width = 2 * 1.645 * a.std() / np.sqrt(len(a))
    return SimpleNamespace(contrasts=contrasts, a=a, b=b, block=block, iid_width=iid_width)


def test_block_resampling_is_wider_than_row_noise_when_a_block_moves_together(clustered):
    d = paired_difference(clustered.contrasts, clustered.a, clustered.b, clustered.block, family=3)
    assert d["hi"] - d["lo"] > 3 * clustered.iid_width and d["family_size"] == 3
    assert d["test_hi"] - d["test_lo"] < d["hi"] - d["lo"]                           # tests are pairs of rows, far smaller than a block


def test_adjusted_bounds_use_the_family_of_three():
    d = paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3)
    z = scipy.special.ndtri(1 - 0.05 / 3)
    assert d["adjusted_hi"] == pytest.approx(d["estimate"] + z * d["se"]) and z == pytest.approx(2.128, abs=1e-3)
    assert d["adjusted_lo"] == pytest.approx(d["estimate"] - z * d["se"])
    assert d["estimate"] == pytest.approx(simple.a.mean() - simple.b.mean()) and d["n"] == len(simple.a)
    assert d["lo"] < d["estimate"] < d["hi"]


@pytest.mark.parametrize("shift, verdict", [(0.3, "above"), (0.0, "contains_zero"), (-0.3, "below")])
def test_verdict_reads_the_adjusted_interval(shift, verdict):
    w = planted(shift)
    assert paired_difference(w.contrasts, w.a, w.b, w.block, family=3)["verdict"] == verdict


def test_no_family_means_no_verdict_and_no_adjusted_bounds():
    d = paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=None)
    assert "verdict" not in d and "adjusted_lo" not in d


def test_a_family_without_a_verdict_keeps_the_adjusted_bounds():
    d = paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3, verdict=False)
    assert "verdict" not in d and d["family_size"] == 3 and d["adjusted_lo"] < d["adjusted_hi"]


def test_intervals_repeat():
    again = paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3)
    assert paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3) == again


@pytest.fixture(scope="module")
def planted_ranking():
    world = make_world(seed=31)
    c = world.contrasts
    return SimpleNamespace(contrasts=c, diff=pd.Series(c.y.to_numpy() * 1000, index=c.row_id))


def test_ranking_by_the_planted_effect_beats_the_arm_count_rule(planted_ranking):
    r = ranking(planted_ranking.contrasts, planted_ranking.diff)
    assert r["panel"]["estimate"] > r["arm_count"]["estimate"] and 0 <= r["matched_random"]["estimate"] <= 1
    assert r["panel_minus_arm_count"]["lo"] > 0 and r["panel_minus_matched_random"]["lo"] > 0
    assert r["panel_minus_arm_count"]["estimate"] == pytest.approx(r["panel"]["estimate"] - r["arm_count"]["estimate"])


def test_ranking_by_noise_is_not_shown_to_beat_its_matched_random_order(planted_ranking):
    c = planted_ranking.contrasts
    noise = pd.Series(np.random.default_rng(4).normal(size=len(c)), index=c.row_id)
    r = ranking(c, noise)
    assert r["panel_minus_matched_random"]["lo"] < 0 < r["panel_minus_matched_random"]["hi"]


def test_a_contrast_without_a_panel_difference_ranks_last(planted_ranking):
    c = planted_ranking.contrasts
    holed = planted_ranking.diff.copy()
    holed.iloc[:50] = np.nan
    assert 0 < ranking(c, holed)["panel"]["estimate"] <= ranking(c, planted_ranking.diff)["panel"]["estimate"]


def test_ties_and_missing_readers_are_counted():
    frame = simple.correct_with_two_ties_one_missing
    a = accuracy(frame, frame)
    assert (a["ties"], a["no_reader"]) == (2, 1) and a["n"] == 5 and a["accuracy"] == pytest.approx((0.5 * 3 + 1 + 0) / 5)
    half = accuracy(frame, frame, mask=np.array([False, False, False, True, True]))
    assert (half["n"], half["ties"], half["no_reader"], half["accuracy"]) == (2, 0, 0, 0.5)


@pytest.fixture(scope="module")
def tiny_run():
    world = make_world(seed=41, units=(60, 60, 60))
    feeds = build_feeds(world.arms)
    answers = make_answers(world, feeds)
    later = feeds.loc[feeds.origin_index > 0, "block_id"].unique()
    aligned = answers[answers.block_id.isin(later)]
    return ModelRun(arms=world.arms, contrasts=world.contrasts, feeds=feeds,
                    answers={"plain": answers, "examples": aligned, "brief": aligned},
                    notes={1: "They click on surprises.", 2: "They click on surprises and on lists."},
                    counts={"calls_planned": 10, "calls_ok": 10, "calls_invalid": 0, "calls_refusal": 0},
                    tool_versions={"1.0": 10}, reported_models={"m": 10}, commit="abc1234")


def test_only_the_primary_model_gets_a_verdict(tiny_run):
    assert "verdict" in model_report(tiny_run, "claude-opus-5-5")["readings"]["plain_minus_always_reference"]
    other = model_report(tiny_run, "claude-haiku-5-5")
    assert "verdict" not in other["readings"]["plain_minus_always_reference"]
    assert other["readings"]["plain_minus_always_reference"]["family_size"] == 3 and other["primary"] is False


def test_the_report_holds_every_fixed_key_and_is_plain_json(tiny_run):
    rep = model_report(tiny_run, "claude-opus-5-5")
    json.loads(json.dumps(rep, allow_nan=False))
    assert rep["primary"] is True and rep["seed"] == 20261118 and rep["commit"] == "abc1234"
    assert {"units", "tests", "contrasts", "blocks", "feeds", "calls_planned", "calls_ok", "calls_invalid",
            "calls_refusal"} <= set(rep["counts"])
    assert rep["counts"]["contrasts"] == len(tiny_run.contrasts)
    assert rep["counts"]["feeds"] == tiny_run.feeds.groupby("block_id").feed_index.nunique().sum()
    assert set(rep["baselines"]) == {"always_reference", "text_lr", "ceiling", "text_lr_minus_always_reference"}
    assert {"accuracy", "n", "ties", "no_reader", "accuracy_minus_half", "decisive", "split_half"} <= set(rep["plain"])
    assert set(rep["readings"]) == {"plain_minus_always_reference", "weights_minus_plain", "text_with_panel_minus_text"}
    assert set(rep["methods"]) == {"direction_map", "reader_weights", "audience_matching", "error_correction", "text_with_panel",
                                   "examples_in_prompt", "audience_brief"}
    for name, method in rep["methods"].items():
        if name != "text_with_panel":
            assert {"accuracy", "decisive_accuracy", "minus_plain", "minus_always_reference"} <= set(method), name
    assert rep["methods"]["text_with_panel"] is None and rep["readings"]["text_with_panel_minus_text"] is None      # no ledger here
    assert "brier_skill" in rep["methods"]["direction_map"] and set(rep["methods"]["reader_weights"]["fits"]) == {"2014-04-01", "2014-07-01"}
    note = rep["methods"]["audience_brief"]["notes"]["2014-04-01"]
    assert note["words"] == 4 and len(note["sha256"]) == 64 and "surprises" not in json.dumps(rep["methods"]["audience_brief"])
    assert set(rep["by_origin"]) == {"2014-01-01", "2014-04-01", "2014-07-01"}
    assert set(rep["by_origin"]["2014-01-01"]) == {"plain", "always_reference", "reader_weights"}
    assert {"panel", "arm_count", "matched_random", "panel_minus_arm_count", "panel_minus_matched_random"} <= set(rep["ranking"])


def test_the_report_s_numbers_are_the_measures_of_its_inputs(tiny_run):
    rep = model_report(tiny_run, "claude-opus-5-5")
    c = tiny_run.contrasts
    assert rep["baselines"]["always_reference"]["accuracy"] == pytest.approx(c.ref_correct.mean())
    assert rep["baselines"]["ceiling"]["accuracy"] == pytest.approx(c.dir_ceiling_row.mean())
    assert rep["plain"]["accuracy"] > 0.6 and rep["plain"]["decisive"]["n"] == int(c.decisive.sum())
    assert rep["readings"]["plain_minus_always_reference"]["estimate"] == pytest.approx(rep["plain"]["accuracy"] - c.ref_correct.mean())
    first = rep["by_origin"]["2014-01-01"]
    assert first["plain"]["accuracy"] == first["reader_weights"]["accuracy"]                   # nothing is visible at the first origin
    examples = rep["methods"]["examples_in_prompt"]
    assert examples["accuracy"] == pytest.approx(rep["plain"]["accuracy"]) and examples["minus_plain"]["estimate"] == 0.0


def test_agreement_between_models_leaves_ties_out():
    rows = ["a", "b", "c", "d"]
    one = pd.DataFrame({"row_id": rows, "diff": [1.0, -1.0, 0.0, 2.0]})
    two = pd.DataFrame({"row_id": rows, "diff": [2.0, 1.0, 3.0, np.nan]})
    out = agreement_report({"m1": one, "m2": two})
    assert out["pairs"]["m1__m2"] == {"agree_share": 0.5, "n": 2, "left_out": 2}
