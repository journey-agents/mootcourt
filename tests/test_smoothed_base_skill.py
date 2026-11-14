"""The Brier skill against the smoothed base rate (scripts/smoothed_base_skill.py)."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def sbs():
    return _load("smoothed_base_skill")


@pytest.fixture(scope="module")
def bos():
    return _load("by_origin_skill")


def _tiny():
    """Two origins. The first has cell a (10 visible rows, no event) and cell b (20 visible rows, 6 events); the second has cell a only
    (40 visible rows, 4 events)."""
    o1, o2 = pd.to_datetime(["2014-01-01", "2014-04-01"], utc=True)
    spec = [(o1, "a", 10, 0.0, [0, 1, 0]), (o1, "b", 20, 0.3, [1, 0, 0, 1]), (o2, "a", 40, 0.1, [0, 0, 1])]
    rows = []
    for o, cell, n, p_base, events in spec:
        for i, e in enumerate(events):
            rows.append({"row_id": f"{o.date()}-{cell}-{i}", "test_id": f"{o.date()}-{cell}-{i}", "origin": o, "cell": cell, "rung": "P1",
                         "event": float(e), "brier_event": (0.2 - e) ** 2, "p_base": p_base, "brier_base": (p_base - e) ** 2,
                         "n_visible_cell": n})
    return pd.DataFrame(rows)


def _scores():
    rng = np.random.default_rng(5)
    rows = []
    for k, origin in enumerate(pd.to_datetime(["2014-01-01", "2014-04-01", "2014-07-01", "2014-10-01"], utc=True)):
        for i in range(200):
            cell = "a" if i % 2 else "b"
            n = 40 if cell == "a" else 25
            base = (0 if (k == 0 and cell == "a") else 3 + k) / n
            e = float(rng.random() < 0.12)
            p = 0.11 + 0.01 * k
            rows.append({"row_id": f"{k}-{i}", "test_id": f"{k}-{i // 2}", "origin": origin, "cell": cell, "rung": "P1", "event": e,
                         "brier_event": (p - e) ** 2, "p_base": base, "brier_base": (base - e) ** 2, "n_visible_cell": n})
    return pd.DataFrame(rows)


def test_the_number_of_pseudo_rows_is_thirty(sbs):
    assert sbs.PSEUDO_ROWS == 30


def test_the_smoothed_rate_on_a_hand_made_frame_with_a_cell_without_events(sbs):
    doc = sbs.summarize(_tiny(), "P1", B=20, seed=0)
    strata = {(s["origin"][:10], s["cell"]): s for s in doc["strata"]}
    assert set(strata) == {("2014-01-01", "a"), ("2014-01-01", "b"), ("2014-04-01", "a")}
    a = strata[("2014-01-01", "a")]
    assert (a["n"], a["k"], a["p_base"]) == (10, 0, 0.0)
    assert a["p_pool"] == pytest.approx(6 / 30)
    assert a["smoothed"] == pytest.approx((0 + 30 * 0.2) / (10 + 30))          # 0.15: above zero although the cell has no event
    b = strata[("2014-01-01", "b")]
    assert (b["n"], b["k"]) == (20, 6) and b["smoothed"] == pytest.approx((6 + 30 * 0.2) / (20 + 30))
    # the pooled skill is against the Brier score of the smoothed rate on the realized event, row by row
    s = _tiny()
    smoothed = np.array([0.15] * 3 + [0.24] * 4 + [0.10] * 3)
    assert doc["pooled"]["skill"] == pytest.approx(1 - s["brier_event"].sum() / ((smoothed - s["event"]) ** 2).sum())
    assert doc["pooled"]["n_rows"] == 10


def test_the_pooled_share_is_taken_over_the_cells_of_one_origin_only(sbs):
    doc = sbs.summarize(_tiny(), "P1", B=20, seed=0)
    strata = {(s["origin"][:10], s["cell"]): s for s in doc["strata"]}
    second = strata[("2014-04-01", "a")]
    assert second["p_pool"] == pytest.approx(4 / 40)                           # not (0 + 6 + 4) / (10 + 20 + 40)
    assert second["smoothed"] == pytest.approx((4 + 30 * 0.1) / (40 + 30))
    assert strata[("2014-01-01", "b")]["p_pool"] == pytest.approx(6 / 30)      # each cell once, however many rows it has


def test_a_count_of_events_that_is_not_an_integer_raises(sbs):
    s = _tiny()
    s.loc[s["cell"] == "b", "p_base"] = 0.123                                  # 0.123 * 20 = 2.46 events
    with pytest.raises(ValueError, match="integer"):
        sbs.summarize(s, "P1", B=20, seed=0)
    s = _tiny()
    s.loc[s["cell"] == "b", "p_base"] = 0.3 + 1e-9                             # within the tolerance: read as 6
    doc = sbs.summarize(s, "P1", B=20, seed=0)
    assert {x["cell"]: x["k"] for x in doc["strata"] if x["origin"][:10] == "2014-01-01"} == {"a": 0, "b": 6}


def test_a_cell_whose_rows_disagree_on_its_counts_raises(sbs):
    s = _tiny()
    s.loc[s.index[0], "n_visible_cell"] = 11
    with pytest.raises(ValueError, match="one value"):
        sbs.summarize(s, "P1", B=20, seed=0)


def test_the_unsmoothed_block_equals_a_direct_computation_and_the_by_origin_script(sbs, bos):
    s = _scores()
    doc = sbs.summarize(s, "P1", B=60, seed=0)
    un = doc["unsmoothed"]
    assert un["pooled"]["skill"] == pytest.approx(1 - s["brier_event"].sum() / s["brier_base"].sum())
    per_origin = [1 - f["brier_event"].sum() / f["brier_base"].sum() for _, f in s.groupby("origin", sort=True)]
    assert un["origin_level"]["skill"] == pytest.approx(np.mean(per_origin))
    half = stats.t.ppf(0.95, 3) * np.std(per_origin, ddof=1) / 2.0
    assert un["origin_level"]["lo"] == pytest.approx(np.mean(per_origin) - half)
    assert un["origin_level"]["hi"] == pytest.approx(np.mean(per_origin) + half)
    ref = bos.summarize(s, "P1", "realized", B=60, seed=0)
    for key in ("skill", "lo", "hi", "n_rows", "n_tests"):
        assert un["pooled"][key] == pytest.approx(ref["pooled"][key])
    for key in ("skill", "lo", "hi", "origins"):
        assert un["origin_level"][key] == pytest.approx(ref["origin_level"][key])


def test_the_smoothed_readings_by_test_and_by_origin(sbs):
    s = _scores()
    doc = sbs.summarize(s, "P1", B=60, seed=0)
    pooled = doc["pooled"]
    assert pooled["lo"] <= pooled["skill"] <= pooled["hi"]
    assert pooled["skill"] != pytest.approx(doc["unsmoothed"]["pooled"]["skill"])
    assert len(doc["by_origin"]) == 4 and doc["origin_level"]["origins"] == 4
    assert doc["origin_level"]["skill"] == pytest.approx(np.mean([r["skill"] for r in doc["by_origin"]]))
    assert doc["origin_level"]["lo"] <= doc["origin_level"]["skill"] <= doc["origin_level"]["hi"]
    loo = doc["origin_level_leave_one_out"]
    assert len(loo) == 4 and all(r["origins"] == 3 for r in loo)
    assert [r["left_out"] for r in loo] == [r["origin"] for r in doc["by_origin"]]
    assert doc["origin_level_leave_one_out_above_zero"] == sum(1 for r in loo if r["lo"] > 0)
    assert (doc["bootstrap_resamples"], doc["seed"], doc["level"]) == (60, 0, 0.9)


def test_the_adjusted_interval_is_the_normal_one_for_a_family_of_three(sbs):
    from mootcourt import harness_stats as hs

    s = _scores()
    doc = sbs.summarize(s, "P1", B=60, seed=0)
    pooled = doc["pooled"]
    assert pooled["family_size"] == 3
    strata = {(pd.Timestamp(x["origin"]), x["cell"]): x["smoothed"] for x in doc["strata"]}
    smoothed = np.array([strata[(o, c)] for o, c in zip(s["origin"], s["cell"])])
    base = (smoothed - s["event"].to_numpy(float)) ** 2
    ts = hs._TestSums(s, {"b": s["brier_event"].to_numpy(float), "base": base})
    counts = ts.resample_counts(60, np.random.default_rng(0))
    draws = 1.0 - (counts @ ts.sums["b"]) / (counts @ ts.sums["base"])
    half = stats.norm.ppf(1 - 0.05 / 3) * draws.std(ddof=1)
    assert pooled["adjusted_lo"] == pytest.approx(pooled["skill"] - half)
    assert pooled["adjusted_hi"] == pytest.approx(pooled["skill"] + half)
    assert pooled["adjusted_hi"] - pooled["adjusted_lo"] > pooled["hi"] - pooled["lo"]


def test_a_rung_without_rows_raises(sbs):
    with pytest.raises(ValueError, match="no scored row for P2"):
        sbs.summarize(_scores(), "P2", B=20, seed=0)


def test_the_command_line_writes_the_file(sbs, tmp_path, monkeypatch):
    scores, report, out = tmp_path / "scores-x.parquet", tmp_path / "backtest-x.json", tmp_path / "out.json"
    _scores().to_parquet(scores)
    report.write_text(json.dumps({"header": {"bootstrap_resamples": 40, "seed": 7}}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["smoothed_base_skill.py", "--scores", str(scores), "--report", str(report), "--out", str(out),
                                      "--rungs", "P1"])
    assert sbs.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["pseudo_rows"] == 30 and "definition" in doc
    assert doc["inputs"] == {"scores": "scores-x.parquet", "report": "backtest-x.json"}
    assert set(doc["rungs"]) == {"P1"}
    rung = doc["rungs"]["P1"]
    for key in ("pooled", "by_origin", "origin_level", "origin_level_leave_one_out", "origin_level_leave_one_out_above_zero", "unsmoothed",
                "strata"):
        assert key in rung
    assert (rung["bootstrap_resamples"], rung["seed"]) == (40, 7)
    assert len(rung["strata"]) == 8
