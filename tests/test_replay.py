"""Chunk I, E7: the weekly replay of an archive (scripts/replay_weekly.py), on a small synthetic ledger.

The replay must use only what the weekly loop could see: a card issued in week W comes from the champion bundle fitted at the latest
quarterly origin on or before W, and an outcome is joined at the first week on or after its ``usable_after``.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
WEEK = pd.Timedelta(days=7)


def _script():
    spec = importlib.util.spec_from_file_location("replay_weekly", ROOT / "scripts" / "replay_weekly.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["replay_weekly"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def synth():
    from mootcourt.sources import synthetic

    return synthetic.generate(synthetic.SyntheticConfig(seed=71, n_tests=170, variants_per_test=2))[0]


@pytest.fixture(scope="module")
def run(synth):
    mod = _script()
    doc, records = mod.replay(synth, "synthetic", "snap-test", keep_records=True)
    return mod, doc, records


def _same(a, b) -> bool:
    """Equal, with floats compared to 1e-9: the baseline's centring constant is the mean over all rows, a numerical shift that cancels in
    exact arithmetic and moves the last digits when later rows change."""
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float):
        return a == pytest.approx(b, rel=1e-9, abs=1e-12)
    return a == b


def test_the_replay_walks_weekly_joins_from_the_first_fitted_origin(run, synth):
    _mod, doc, records = run
    weeks = pd.to_datetime([w["week_start"] for w in doc["weeks"]], utc=True)
    assert len(weeks) > 20 and all(b - a == WEEK for a, b in zip(weeks[:-1], weeks[1:]))
    adm = synth[synth["status"] == "admitted"]
    first = weeks[0]
    assert first.day == 1 and first.month in (1, 4, 7, 10)                          # a quarterly origin
    issued_rows = adm[adm["started_at"] >= first]
    assert doc["header"]["n_cards"] == len(issued_rows) == sum(w["cards_issued"] for w in doc["weeks"]) == len(records)
    assert weeks[-1] >= adm["usable_after"].max()                              # the walk runs until the last outcome is usable
    for w in doc["weeks"]:
        assert 0 <= w["abstained"] <= w["cards_issued"]
        assert (w["abstention_rate"] is None) if w["cards_issued"] == 0 else w["abstention_rate"] == pytest.approx(w["abstained"] / w["cards_issued"])
        assert sum(w["miss_counts"].values()) == w["outcomes_joined"]
    assert doc["header"]["n_outcomes"] == sum(w["outcomes_joined"] for w in doc["weeks"])


def test_every_card_is_issued_in_the_week_its_test_starts_from_the_bundle_of_the_latest_quarter(run, synth):
    _mod, doc, records = run
    by_id = synth.set_index("row_id")
    origins = pd.to_datetime(sorted({w["bundle_origin"] for w in doc["weeks"]}), utc=True)
    for rec in records:
        week = pd.Timestamp(rec["issue_week"])
        row = by_id.loc[rec["card"]["request"]["row_id"]]
        assert week <= row["started_at"] < week + WEEK
        assert pd.Timestamp(rec["card"]["origin"]) == week and pd.Timestamp(rec["card"]["issued_at"]) == week
        assert pd.Timestamp(rec["bundle_origin"]) <= week
        assert pd.Timestamp(rec["bundle_origin"]) == max(o for o in origins if o <= week)
        assert pd.Timestamp(rec["fit_cutoff"]) <= pd.Timestamp(rec["bundle_origin"]) <= week      # the bundle saw nothing after its origin


def test_no_card_uses_a_row_usable_after_its_issue_week_and_no_outcome_is_joined_early(run, synth):
    _mod, doc, records = run
    by_id = synth.set_index("row_id")
    for w in doc["weeks"]:
        if w["cards_issued"]:
            assert pd.Timestamp(w["max_fit_cutoff"]) <= pd.Timestamp(w["week_start"])
    for rec in records:
        usable = by_id.loc[rec["card"]["request"]["row_id"], "usable_after"]
        out = rec["outcome"]
        assert out is not None                                                                  # the walk runs until the last result is usable
        joined = pd.Timestamp(rec["joined_week"])
        assert usable <= joined < usable + WEEK                                                 # the first weekly join on or after usable_after
        assert joined > pd.Timestamp(rec["issue_week"])
        assert pd.Timestamp(out["at"]) == usable and out["joined_at"] == rec["joined_week"]


def test_changing_results_that_become_usable_later_changes_nothing_up_to_that_week(synth):
    """The strong form of the leakage check: poison every row usable after week W and compare the weeks up to W."""
    mod = _script()
    base_doc, _ = mod.replay(synth, "synthetic", "snap-test", keep_records=True)
    weeks = [pd.Timestamp(w["week_start"]) for w in base_doc["weeks"]]
    cut = weeks[len(weeks) // 2]
    bad = synth.copy()
    late = bad["usable_after"] > cut
    assert late.sum() > 50
    rng = np.random.default_rng(3)
    bad.loc[late, "y"] = rng.normal(40.0, 40.0, int(late.sum()))
    bad.loc[late, "s"] = bad.loc[late, "s"] * 3.0
    poisoned_doc, _ = mod.replay(bad, "synthetic", "snap-test", keep_records=True)
    keep = [i for i, w in enumerate(weeks) if w <= cut]
    for i in keep:
        a, b = base_doc["weeks"][i], poisoned_doc["weeks"][i]
        assert _same(a, b), (weeks[i], a, b)
    assert base_doc["weeks"][-1] != poisoned_doc["weeks"][-1]                               # the later weeks do see the new results


def test_a_card_matches_a_card_issued_by_hand_from_a_bundle_fitted_at_the_same_origin(run, synth):
    from mootcourt import card as card_mod
    from mootcourt.abstain import AbstainConfig
    from mootcourt.bundle import fit_bundle

    _mod, doc, records = run
    rec = records[len(records) // 2]
    q = pd.Timestamp(rec["bundle_origin"])
    bundle = fit_bundle(synth, "synthetic", "snap-test", as_of=q)
    req = rec["request"]
    by = card_mod.build_card(bundle, req, reliability=rec["reliability_used"], now=pd.Timestamp(rec["issue_week"]).to_pydatetime(),
                             config=AbstainConfig())
    got = rec["card"]
    ref = card_mod.to_json(by)
    assert got["prediction"] == ref["prediction"] and got["abstention"]["status"] == ref["abstention"]["status"]
    assert got["model_id"] == bundle.model_id


def test_outcomes_are_typed_like_the_weekly_join_and_carry_the_shadow_scores(run):
    from mootcourt import loop

    _mod, _doc, records = run
    typed = 0
    for rec in records:
        out = rec["outcome"]
        if out is None:
            continue
        typed += 1
        card = rec["card"]
        issued = card["abstention"]["status"] == "issue"
        iv = tuple(card["prediction"]["interval_90"]) if issued and card["prediction"].get("interval_90") else None
        assert out["miss_type"] == loop.type_miss(abstained=not issued, p_sig=card["prediction"].get("p_sig") if issued else None,
                                                  point=card["prediction"].get("point") if issued else None, interval90=iv, y=out["y"], s=out["s"])
        assert out["miss_type"] in loop.MISS_TYPES
        assert out["abstained"] == (not issued)
    assert typed > 50


def test_the_rolling_coverage_is_the_share_of_trailing_issued_intervals_that_held_the_result(run):
    _mod, doc, records = run
    from mootcourt.config import TRAILING_WEEKS

    outs = [(pd.Timestamp(r["joined_week"]), r["outcome"]) for r in records if r["outcome"] is not None and r["outcome"]["interval_90"]]
    seen = 0
    for w in doc["weeks"]:
        t = pd.Timestamp(w["week_start"])
        win = [o for j, o in outs if j <= t and j > t - pd.Timedelta(weeks=TRAILING_WEEKS)]
        if not win:
            assert w["coverage_90"] is None and w["coverage_90_n"] == 0
            continue
        seen += 1
        hit = np.mean([o["interval_90"][0] <= o["y"] <= o["interval_90"][1] for o in win])
        assert w["coverage_90"] == pytest.approx(hit) and w["coverage_90_n"] == len(win)
    assert seen > 5


def test_flagged_weeks_follow_the_documented_reliability_rule(run):
    from mootcourt.config import DRIFT_CONSECUTIVE

    _mod, doc, _records = run
    flagged = set(doc["flagged_weeks"])
    for w in doc["weeks"]:
        assert (w["week_start"] in flagged) == bool(w["drifted_cells"])
        assert set(w["drifted_cells"]) <= set(w["below_cells"])
        for c, e in w["reliability"].items():
            assert e["drifted"] == (e["consecutive_below"] >= DRIFT_CONSECUTIVE)
            if c in w["drifted_cells"]:
                assert e["consecutive_below"] >= DRIFT_CONSECUTIVE
            if c in w["below_cells"]:
                assert e["consecutive_below"] >= 1
    assert doc["header"]["rule"]["drift_consecutive"] == DRIFT_CONSECUTIVE


def test_week_flags_read_a_reliability_report():
    mod = _script()
    report = {"source": "s", "as_of": "2014-01-01T00:00:00+00:00", "cells": {
        "a": {"consecutive_below": 0, "drifted": False}, "b": {"consecutive_below": 1, "drifted": False},
        "c": {"consecutive_below": 2, "drifted": True}, "d": {"consecutive_below": 5, "drifted": True}}}
    assert mod.week_flags(report) == (["b", "c", "d"], ["c", "d"])
    assert mod.week_flags(None) == ([], [])


def test_a_sustained_collapse_of_skill_is_flagged_by_the_replay(synth):
    """A late regime change that the champion cannot know: the loop must flag it once two joins in a row are below the baseline."""
    mod = _script()
    bad = synth.copy()
    start = bad["started_at"].quantile(0.7)
    late = bad["started_at"] >= start
    # the effect flips sign and widens far beyond what any earlier row showed
    bad.loc[late, "y"] = -bad.loc[late, "y"] * 6 + 25.0
    doc, _ = mod.replay(bad, "synthetic", "snap-test", keep_records=True)
    base = mod.replay(synth, "synthetic", "snap-test")
    new = sorted(set(doc["flagged_weeks"]) - set(base["flagged_weeks"]))
    assert new, "a sustained miss must be flagged beyond what the untouched archive already flags"
    assert pd.Timestamp(new[0]) > start
    assert len(doc["flagged_weeks"]) > len(base["flagged_weeks"])


def test_the_script_writes_the_replay_report_next_to_the_backtest(tmp_path, synth):
    from mootcourt.ledger import ensure_snapshot, write_ledger

    root = tmp_path / "root"
    write_ledger(synth, root / "data" / "ledger" / "ledger.parquet")
    (root / "reports").mkdir(parents=True)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "replay_weekly.py"), "--source", "synthetic"], capture_output=True, text=True,
                       env={**__import__("os").environ, "MOOTCOURT_DATA_ROOT": str(root)})
    assert r.returncode == 0, r.stderr
    sid = ensure_snapshot(synth, root / "data" / "ledger")
    out = root / "reports" / f"replay-synthetic-{sid}.json"
    doc = json.loads(out.read_text())
    assert doc["header"]["source"] == "synthetic" and doc["header"]["snapshot_id"] == sid
    assert {"header", "weeks", "flagged_weeks", "totals"} <= set(doc)
    assert doc["header"]["command"].startswith("python scripts/replay_weekly.py --source synthetic")
