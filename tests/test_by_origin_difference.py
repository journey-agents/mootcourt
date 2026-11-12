"""The by-origin reading of a paired log score difference (scripts/by_origin_difference.py)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("by_origin_difference", Path(__file__).resolve().parents[1] / "scripts" / "by_origin_difference.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _scores():
    rng = np.random.default_rng(0)
    rows = []
    for k, (origin, shift, n) in enumerate([("2014-01-01", -0.2, 60), ("2014-04-01", 0.5, 300), ("2014-07-01", 0.0, 40)]):
        for i in range(n):
            base = rng.normal()
            rid, tid = f"r{k}-{i}", f"t{k}-{i // 2}"                    # two rows to a test
            rows.append({"row_id": rid, "test_id": tid, "origin": origin, "rung": "P0", "logscore": base})
            rows.append({"row_id": rid, "test_id": tid, "origin": origin, "rung": "P1", "logscore": base + shift + 0.01 * rng.normal()})
    rows.append({"row_id": "only-p1", "test_id": "x", "origin": "2014-07-01", "rung": "P1", "logscore": 9.0})   # scored by one rung: left out
    return pd.DataFrame(rows)


def test_the_difference_is_paired_by_row_and_read_four_ways(mod):
    d = mod.differences(_scores())
    assert len(d) == 400 and set(d.columns) == {"test_id", "origin", "d"}
    out = mod.summarize(d, B=200, seed=0)
    assert out["pooled"]["difference"] == pytest.approx(float(d["d"].mean()))
    by = {r["origin"][:10]: r for r in out["by_origin"]}
    assert by["2014-01-01"]["hi"] < 0 < by["2014-04-01"]["lo"] and by["2014-07-01"]["lo"] < 0 < by["2014-07-01"]["hi"]
    assert (out["by_origin_above_zero"], out["by_origin_below_zero"]) == (1, 1)
    loo = {r["left_out"][:10]: r for r in out["leave_one_origin_out"]}
    assert loo["2014-04-01"]["hi"] < 0 < loo["2014-01-01"]["lo"]        # the pooled lead rests on the one large origin
    assert loo["2014-04-01"]["n_rows"] == 100 and out["leave_one_origin_out_above_zero"] == 2
    eq = out["equal_origin_weight"]
    assert eq["difference"] == pytest.approx(np.mean([r["difference"] for r in out["by_origin"]])) and eq["lo"] < eq["difference"] < eq["hi"]
    assert eq["difference"] < out["pooled"]["difference"]               # equal weights take the large origin's lead down
    with pytest.raises(ValueError):
        mod.summarize(d.iloc[:0], B=10, seed=0)
