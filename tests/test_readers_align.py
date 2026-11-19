"""Alignment methods 1 to 4: each is fitted only on what is visible at an origin, and equals the plain panel at the first."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from readers_world import make_world

from mootcourt.simulators.readers.align import (
    audience_matching,
    brier_skill,
    direction_map,
    error_correction,
    reader_weights,
    traits,
    visible_before,
)
from mootcourt.simulators.readers.panel import directions, panel_scores


@pytest.fixture(scope="module")
def world():
    return make_world()


@pytest.fixture(scope="module")
def world_with_question_mark_effect():
    return make_world(seed=12, question_effect=0.6, effect_sd=0.1)


def test_visible_before_needs_an_earlier_origin_and_a_result_in_hand(world):
    late = world.with_unit_usable_only_after(origin_index=1)
    seen = visible_before(late.arms, late.origin(1))
    assert set(seen.origin_index) == {0} and "t_late@2014-01-01" not in set(seen.unit_id)
    assert "t_late@2014-01-01" in set(visible_before(late.arms, late.origin(2)).unit_id)
    assert visible_before(late.arms, late.origin(0)).empty


def test_every_method_equals_the_plain_panel_at_the_first_origin(world):
    plain = directions(world.contrasts, panel_scores(world.rs))
    for fit in (direction_map, reader_weights, audience_matching, error_correction):
        out = fit(world.arms, world.contrasts, world.rs)
        out = out[0] if isinstance(out, tuple) else out
        first = world.contrasts.origin_index == 0
        assert np.array_equal(out.correct[first.values], plain.correct[first.values])
        assert list(out.row_id) == list(world.contrasts.row_id)


def test_reader_weights_find_the_informative_reader_and_help(world):
    out, fits = reader_weights(world.arms, world.contrasts, world.rs)
    assert np.argmax(fits[2]["weights"]) == 6 and fits[2]["slope"] > 0
    later = (world.contrasts.origin_index > 0).values
    assert out.correct[later].mean() > directions(world.contrasts, panel_scores(world.rs)).correct[later].mean()


def test_reader_weights_move_well_away_from_equal_weights_when_one_reader_carries_the_signal(world):
    _, fits = reader_weights(world.arms, world.contrasts, world.rs)
    assert fits[2]["weights"][6] > 0.3 and sum(fits[2]["weights"]) == pytest.approx(1.0)


def test_reader_weights_stay_near_equal_when_no_reader_carries_a_signal():
    w = make_world(seed=13, informative=False)
    _, fits = reader_weights(w.arms, w.contrasts, w.rs)
    assert max(fits[2]["weights"]) < 0.25


def test_a_unit_not_yet_usable_changes_no_fit(world):
    # the added unit starts at origin 0 with a decisive planted signal, and its usable_after is later than origin 1
    late = world.with_unit_usable_only_after(origin_index=1)
    at1 = world.contrasts.row_id[world.contrasts.origin_index == 1]
    at2 = world.contrasts.row_id[world.contrasts.origin_index == 2]
    for fit, column in ((direction_map, "p_variant"), (reader_weights, "diff"), (audience_matching, "diff"), (error_correction, "diff")):
        a, b = fit(world.arms, world.contrasts, world.rs), fit(late.arms, late.contrasts, late.rs)
        a, b = (a[0] if isinstance(a, tuple) else a), (b[0] if isinstance(b, tuple) else b)
        assert np.allclose(a.set_index("row_id")[column][at1], b.set_index("row_id")[column][at1], equal_nan=True)
        # the same unit is visible at the next origin, and there it does change the fit
        assert not np.allclose(a.set_index("row_id")[column][at2], b.set_index("row_id")[column][at2], equal_nan=True)


def test_audience_matching_ignores_which_arm_won(world):
    flipped = world.contrasts.assign(y=-world.contrasts.y)
    a, fa = audience_matching(world.arms, world.contrasts, world.rs)
    b, fb = audience_matching(world.arms, flipped, world.rs)
    assert np.allclose(fa[2]["weights"], fb[2]["weights"]) and np.allclose(a["diff"], b["diff"], equal_nan=True)


def test_audience_matching_leans_on_the_readers_whose_level_is_nearest_the_click_rate(world):
    _, fits = audience_matching(world.arms, world.contrasts, world.rs)
    w = fits[2]["weights"]
    assert w[0] > w[9] and sum(w) == pytest.approx(1.0)          # reader 1 has the lowest raw level in this world


def test_traits_are_the_four_fixed_ones():
    assert list(traits("Why would YOU read 9 things?")) == [6.0, 1.0, 1.0, 1.0]
    assert list(traits("Your youth")) == [2.0, 0.0, 0.0, 0.0]


def test_direction_map_returns_probabilities_and_a_base(world):
    out = direction_map(world.arms, world.contrasts, world.rs)
    later = (world.contrasts.origin_index > 0).values
    assert out.p_variant[later].between(0, 1).all() and out.p_variant[~later].isna().all()
    assert out.base[later].between(0, 1).all() and out.base[later].nunique() == 2
    earlier = world.contrasts[world.contrasts.origin_index == 0]
    assert out.base[(world.contrasts.origin_index == 1).values].iloc[0] == pytest.approx((earlier.y > 0).mean())
    assert brier_skill(world.contrasts, out) > 0


def test_a_probability_of_exactly_one_half_counts_half(world):
    # no panel difference anywhere and as many earlier contrasts won as lost: the fitted probability is one half
    first = world.contrasts[world.contrasts.origin_index == 0]
    kept = world.contrasts.drop(first.index[:len(first) % 2]).reset_index(drop=True)
    at0 = np.flatnonzero((kept.origin_index == 0).values)
    kept.loc[at0, "y"] = np.where(np.arange(len(at0)) % 2 == 0, 0.01, -0.01)
    out = direction_map(world.arms, kept, world.rs.assign(centred=0.0))
    at1 = (kept.origin_index == 1).values
    assert (out.p_variant[at1] == 0.5).all() and (out.correct[at1] == 0.5).all() and out.tie[at1].all()


def test_the_row_labels_of_the_input_do_not_matter(world):
    shifted = world.contrasts.set_axis(world.contrasts.index + 1000)
    for fit in (direction_map, reader_weights, audience_matching, error_correction):
        a, b = fit(world.arms, world.contrasts, world.rs), fit(world.arms, shifted, world.rs)
        a, b = (a[0] if isinstance(a, tuple) else a), (b[0] if isinstance(b, tuple) else b)
        assert np.allclose(a["diff"], b["diff"], equal_nan=True) and np.array_equal(a.correct, b.correct)


def test_error_correction_uses_a_planted_trait(world_with_question_mark_effect):
    w = world_with_question_mark_effect
    out, _ = error_correction(w.arms, w.contrasts, w.rs)
    later = (w.contrasts.origin_index > 0).values
    assert out.correct[later].mean() > directions(w.contrasts, panel_scores(w.rs)).correct[later].mean()


def test_a_contrast_without_a_reader_stays_a_half_in_every_method(world):
    rs = world.rs[~world.rs.arm_id.isin(world.contrasts.arm_id[world.contrasts.origin_index == 2].iloc[:1])]
    row = world.contrasts.row_id[world.contrasts.origin_index == 2].iloc[0]
    for fit in (direction_map, reader_weights, audience_matching, error_correction):
        out = fit(world.arms, world.contrasts, rs)
        out = (out[0] if isinstance(out, tuple) else out).set_index("row_id")
        assert out.loc[row, "correct"] == 0.5 and bool(out.loc[row, "no_reader"])


def test_outputs_are_frames_with_the_shared_columns(world):
    out, fits = error_correction(world.arms, world.contrasts, world.rs)
    assert {"row_id", "diff", "correct", "tie", "no_reader"} <= set(out.columns) and set(fits) == {1, 2}
    assert isinstance(direction_map(world.arms, world.contrasts, world.rs), pd.DataFrame)
