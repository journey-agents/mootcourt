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
    lvl = out["origin_level"]                                           # three origin means as the units: a wide interval that spans zero
    assert lvl["difference"] == pytest.approx(eq["difference"]) and lvl["origins"] == 3 and lvl["lo"] < 0 < lvl["hi"]
    assert lvl["hi"] - lvl["lo"] > eq["hi"] - eq["lo"]
    with pytest.raises(ValueError):
        mod.summarize(d.iloc[:0], B=10, seed=0)


def test_the_reference_without_history_is_a_centred_normal_at_the_planned_standard_error():
    from scipy import stats

    spec = importlib.util.spec_from_file_location("no_history_reference", Path(__file__).resolve().parents[1] / "scripts" / "no_history_reference.py")
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    assert ref.reference_logscore([0.0, 2.0], [1.0, 2.0]) == pytest.approx(stats.norm.logpdf([0.0, 2.0], 0.0, [1.0, 2.0]))
    rng = np.random.default_rng(1)
    n = 200
    y = rng.standard_t(3, n) * 2.0                                      # effects far wider than the planned noise of 0.5
    rows = pd.DataFrame({"row_id": [f"r{i}" for i in range(n)], "test_id": [f"t{i // 2}" for i in range(n)], "y": y, "s_star": 0.5,
                         "origin": ["2014-01-01"] * (n // 2) + ["2014-04-01"] * (n // 2)})
    good = rows.assign(rung="P1", logscore=stats.t.logpdf(y, 3, 0.0, 2.0))
    flat = rows.assign(rung="P0", logscore=stats.norm.logpdf(y, 0.0, y.std()))
    out = ref.summarize(pd.concat([good, flat]), B=100, seed=0)
    assert out["P1"]["minus_reference"]["lo"] > 0 and out["P0"]["minus_reference"]["lo"] > 0     # any fitted spread beats "no effect"
    assert out["P1"]["reference_logscore"] == pytest.approx(out["P0"]["reference_logscore"]) and len(out["P1"]["by_origin"]) == 2
    with pytest.raises(ValueError):
        ref.summarize(good, B=10, seed=0)                               # P0 has no rows
