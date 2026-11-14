"""The Brier skill by origin (scripts/by_origin_skill.py)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def bos():
    path = Path(__file__).resolve().parents[1] / "scripts" / "by_origin_skill.py"
    spec = importlib.util.spec_from_file_location("by_origin_skill", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _scores(zero_stratum=False):
    rng = np.random.default_rng(3)
    rows = []
    for k, origin in enumerate(pd.to_datetime(["2014-01-01", "2014-04-01", "2014-07-01"], utc=True)):
        for i in range(200):
            cell = "a" if i % 2 else "b"
            base = 0.0 if (zero_stratum and k == 0 and cell == "a") else 0.10
            e = float(rng.random() < 0.12)
            p = 0.12
            rows.append({"row_id": f"{k}-{i}", "test_id": f"{k}-{i // 2}", "origin": origin, "cell": cell, "rung": "P1", "event": e,
                         "brier_event": (p - e) ** 2, "p_base": base, "brier_base": (base - e) ** 2, "event_planned": e,
                         "brier_planned": (p - e) ** 2, "p_base_planned": base, "brier_base_planned": (base - e) ** 2, "n_visible_cell": 50})
    return pd.DataFrame(rows)


def test_the_pooled_skill_is_one_minus_the_ratio_of_the_sums(bos):
    s = _scores()
    doc = bos.summarize(s, "P1", "realized", B=50, seed=0)
    assert doc["pooled"]["skill"] == pytest.approx(1 - s["brier_event"].sum() / s["brier_base"].sum())
    assert len(doc["by_origin"]) == 3 and len(doc["leave_one_origin_out"]) == 3
    assert doc["origin_level"]["origins"] == 3
    assert doc["origin_level"]["lo"] <= doc["origin_level"]["skill"] <= doc["origin_level"]["hi"]
    assert doc["origin_level"]["skill"] == pytest.approx(np.mean([r["skill"] for r in doc["by_origin"]]))


def test_a_stratum_whose_base_rate_is_zero_is_listed_with_its_share_and_the_skill_without_it(bos):
    s = _scores(zero_stratum=True)
    doc = bos.summarize(s, "P1", "realized", B=50, seed=0)
    assert [(z["origin"][:10], z["cell"]) for z in doc["zero_base_rate_strata"]] == [("2014-01-01", "a")]
    z = doc["zero_base_rate_strata"][0]
    assert z["rows"] == 100 and 0 <= z["event_rate"] <= 1 and z["n_visible_cell"] == 50
    rest = s[~((s["origin"] == s["origin"].min()) & (s["cell"] == "a"))]
    assert doc["without_zero_base_rate_strata"]["skill"] == pytest.approx(1 - rest["brier_event"].sum() / rest["brier_base"].sum())
    assert _scores() is not None and bos.summarize(_scores(), "P1", "realized", B=20, seed=0)["zero_base_rate_strata"] == []
