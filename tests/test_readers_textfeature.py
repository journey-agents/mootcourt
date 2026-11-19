"""Method 5: the panel difference as one more feature of the package's text classifier, refitted at each origin."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from mootcourt import harness
from mootcourt.simulators.readers.textfeature import text_with_panel
from mootcourt.sources import synthetic


@pytest.fixture(scope="module")
def synth():
    ledger = synthetic.generate(synthetic.SyntheticConfig(seed=62, n_tests=500, variants_per_test=1, text_effect_strength=2.0,
                                                          cell_params={"headline_only": (0.0, 0.5)}, s_scale=1.0))[0]
    rungs = harness.default_rungs("synthetic", ledger, "text_lr")
    scores = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger), source="synthetic")
    text = scores[scores["rung"] == "text_lr"].reset_index(drop=True)
    origins = sorted(text["origin"].unique())
    contrasts = text[["row_id", "origin", "y"]].assign(origin_index=text["origin"].map({o: i for i, o in enumerate(origins)}))
    return SimpleNamespace(
        ledger=ledger, contrasts=contrasts, package_text_lr_p_gt0=text["p_gt0"].to_numpy(),
        package_correct=text["direction_correct"].to_numpy(dtype=float),
        zero_diff=pd.Series(0.0, index=contrasts["row_id"]),
        diff_equal_to_planted_effect=pd.Series(10.0 * np.sign(contrasts["y"].to_numpy()), index=contrasts["row_id"]),
    )


def test_without_the_feature_it_is_the_package_s_text_classifier(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.zero_diff)
    assert len(set(synth.contrasts.origin_index)) >= 3 and list(out.row_id) == list(synth.contrasts.row_id)
    assert np.allclose(out.p_without, synth.package_text_lr_p_gt0)
    assert np.array_equal(out.correct_without, synth.package_correct)


def test_a_feature_of_zeros_changes_nothing(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.zero_diff)
    assert np.allclose(out.p_with, out.p_without, atol=1e-9)


def test_an_informative_feature_raises_accuracy_after_the_first_origin(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.diff_equal_to_planted_effect)
    later = (synth.contrasts.origin_index > 0).values
    assert out.correct_with[later].mean() > out.correct_without[later].mean()
    assert np.allclose(out.p_without, synth.package_text_lr_p_gt0)          # the feature never reaches the plain classifier


def test_the_first_origin_is_unchanged_by_any_feature(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.diff_equal_to_planted_effect)
    first = (synth.contrasts.origin_index == 0).values
    assert np.allclose(out.p_with[first], out.p_without[first], atol=1e-9)


def test_a_row_without_a_panel_answer_enters_as_zero(synth):
    holed = synth.diff_equal_to_planted_effect.copy()
    last = synth.contrasts.row_id[(synth.contrasts.origin_index == synth.contrasts.origin_index.max()).values]
    holed[last.iloc[0]] = np.nan
    a = text_with_panel(synth.ledger, synth.contrasts, holed).set_index("row_id")
    b = text_with_panel(synth.ledger, synth.contrasts, holed.drop(last.iloc[0])).set_index("row_id")
    assert np.allclose(a.p_with, b.p_with) and a.loc[last.iloc[0], "p_with"] == pytest.approx(a.loc[last.iloc[0], "p_without"], abs=0.2)


def test_a_feature_on_a_row_not_yet_visible_changes_no_earlier_fit(synth):
    # change the feature of the rows scored at the last origin: fits of earlier origins must not move
    changed = synth.diff_equal_to_planted_effect.copy()
    last = (synth.contrasts.origin_index == synth.contrasts.origin_index.max()).values
    changed[synth.contrasts.row_id[last]] *= -1
    a = text_with_panel(synth.ledger, synth.contrasts, synth.diff_equal_to_planted_effect)
    b = text_with_panel(synth.ledger, synth.contrasts, changed)
    assert np.allclose(a.p_with[~last], b.p_with[~last]) and not np.allclose(a.p_with[last], b.p_with[last])
