"""The input loader of the simulated readers: arms are distinct headlines, units are pairs of test and origin."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from mootcourt.simulators.readers.inputs import load_units
from mootcourt.simulators.readers.protocol import rng

O1, O2 = "2014-01-01", "2014-04-01"


def _ledger_row(row_id, test_id, headline, reference, clicks_ref, clicks_var, cell="headline_only", n=1000):
    return {
        "row_id": row_id, "test_id": test_id, "cell": cell, "n_ref": n, "n_var": n,
        "usable_after": pd.Timestamp("2013-12-01", tz="UTC"),
        "features_json": json.dumps({"headline": headline, "reference_headline": reference,
                                     "post_launch": {"clicks_ref": clicks_ref, "clicks_var": clicks_var}}),
    }


def _score_rows(row_id, test_id, origin, y, s=0.01, cell="headline_only"):
    base = {"row_id": row_id, "test_id": test_id, "cell": cell, "origin": pd.Timestamp(origin, tz="UTC"), "y": y, "s": s,
            "dir_ceiling_row": 0.9, "s_star": 0.02}
    return [
        {**base, "rung": "always_reference", "direction_correct": float(y < 0)},
        {**base, "rung": "text_lr", "direction_correct": float(y > 0)},
        {**base, "rung": "ridge", "direction_correct": 1.0},
    ]


@pytest.fixture
def frames():
    ledger = [
        _ledger_row("a1", "t_plain", "Plain variant words", "Plain reference words", 40, 55),
        _ledger_row("d1", "t_dup", "Same words", "Dup reference", 20, 30),
        _ledger_row("d2", "t_dup", "Same words", "Dup reference", 20, 50),
        _ledger_row("d3", "t_dup", "Other words", "Dup reference", 20, 10),
        _ledger_row("s1", "t_span", "Span early variant", "Span reference", 10, 30),
        _ledger_row("s2", "t_span", "Span late variant", "Span reference", 10, 5),
        _ledger_row("row_other_cell", "t_other", "Other cell variant", "Other cell reference", 10, 5, cell="image_only"),
    ]
    scores = (
        _score_rows("a1", "t_plain", O1, 0.02)
        + _score_rows("d1", "t_dup", O1, 0.01)
        + _score_rows("d2", "t_dup", O1, 0.03)
        + _score_rows("d3", "t_dup", O1, -0.01)
        + _score_rows("s1", "t_span", O1, 0.05)
        + _score_rows("s2", "t_span", O2, -0.001)
        + _score_rows("row_other_cell", "t_other", O1, 0.01, cell="image_only")
    )
    return pd.DataFrame(ledger), pd.DataFrame(scores)


def test_arms_are_distinct_headlines_and_share_clicks(frames):
    arms, contrasts = load_units(*frames)
    u = arms[arms.test_id == "t_dup"]
    assert list(u.is_reference) == [True, False, False]          # three rows, two variant headlines
    shared = u[u.headline == "Same words"].iloc[0]
    assert (shared.clicks, shared.impressions) == (30 + 50, 1000 + 1000)
    assert contrasts[contrasts.test_id == "t_dup"].arm_id.nunique() == 2


def test_a_test_at_two_origins_makes_two_units(frames):
    arms, _ = load_units(*frames)
    assert arms[arms.test_id == "t_span"].unit_id.nunique() == 2
    assert arms[(arms.test_id == "t_span") & arms.is_reference].shape[0] == 2


def test_baseline_columns_come_from_the_saved_rungs(frames):
    _, contrasts = load_units(*frames)
    assert set(contrasts.ref_correct.unique()) <= {0.0, 1.0}
    assert contrasts.decisive.equals(contrasts.y.abs() > 1.96 * contrasts.s)
    assert (contrasts.ref_correct + contrasts.text_lr_correct == 1.0).all()      # the fixture's two rungs are opposite


def test_only_the_headline_only_cell_is_read(frames):
    _, contrasts = load_units(*frames)
    assert "row_other_cell" not in set(contrasts.row_id)


def test_identifiers_and_the_reference_arm(frames):
    arms, contrasts = load_units(*frames)
    u = arms[arms.unit_id == "t_dup@2014-01-01"]
    assert list(u.arm_id) == ["t_dup@2014-01-01#0", "t_dup@2014-01-01#1", "t_dup@2014-01-01#2"]
    assert (u.clicks.iloc[0], u.impressions.iloc[0]) == (20, 1000)
    c = contrasts.set_index("row_id")
    assert c.loc["d3", "arm_id"] == "t_dup@2014-01-01#2" and c.loc["d3", "ref_arm_id"] == "t_dup@2014-01-01#0"
    assert sorted(arms.origin_index.unique()) == [0, 1] and c.loc["s2", "origin_index"] == 1


def test_a_scored_row_absent_from_the_ledger_is_an_error(frames):
    ledger, scores = frames
    with pytest.raises(ValueError, match="absent from the ledger"):
        load_units(ledger[ledger.row_id != "a1"], scores)


def test_two_reference_headlines_in_a_unit_are_an_error(frames):
    ledger, scores = frames
    ledger = ledger.copy()
    feats = json.loads(ledger.loc[ledger.row_id == "d3", "features_json"].iloc[0])
    feats["reference_headline"] = "A second reference"
    ledger.loc[ledger.row_id == "d3", "features_json"] = json.dumps(feats)
    with pytest.raises(ValueError, match="reference headlines"):
        load_units(ledger, scores)


def test_a_variant_equal_to_its_reference_is_an_error(frames):
    ledger, scores = frames
    ledger = ledger.copy()
    feats = json.loads(ledger.loc[ledger.row_id == "a1", "features_json"].iloc[0])
    feats["headline"] = feats["reference_headline"]
    ledger.loc[ledger.row_id == "a1", "features_json"] = json.dumps(feats)
    with pytest.raises(ValueError, match="equals its reference"):
        load_units(ledger, scores)


def test_rng_streams_are_independent_and_repeatable():
    assert rng("blocks", 0).integers(1 << 30) == rng("blocks", 0).integers(1 << 30)
    assert rng("blocks", 0).integers(1 << 30) != rng("arms", 0).integers(1 << 30)
