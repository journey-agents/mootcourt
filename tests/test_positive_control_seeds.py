"""The positive control summarized over ledger seeds (scripts/positive_control_seeds.py)."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def pcs():
    path = Path(__file__).resolve().parents[1] / "scripts" / "positive_control_seeds.py"
    spec = importlib.util.spec_from_file_location("positive_control_seeds", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rec(seed, share, d):
    return {"seed": seed, "oracle_gain": 0.02, "p2_gain": 0.02 * share, "recovered_pooled": share,
            "recovered_headline_only": share / 3, "p2_minus_p1_headline_only": d, "share_pairs_admitted": 0.5}


def make_run_doc(p2_gain, oracle_gain, admitted):
    """A run shaped like one entry of ``positive_control_rungs(...)["runs"]``."""
    def cell(p2, oracle):
        return {"oracle": {"gain_logscore_vs_p1": oracle},
                "rungs": [{"rung": "P1", "diff_logscore_vs_p1": 0.0}, {"rung": "P2", "diff_logscore_vs_p1": p2}]}
    return {"n_tests": 11100, "share_pairs_admitted": admitted, "by_cell": {"ALL": cell(p2_gain, oracle_gain),
                                                                          "headline_only": cell(p2_gain / 2, oracle_gain)}}


def test_median_and_range_over_seeds(pcs):
    doc = pcs.summarize([rec(7, 0.09, 0.0004), rec(8, 0.0, 0.0), rec(9, 0.20, 0.0020)], real_lo=-0.0007, real_hi=0.0010)
    assert doc["seeds"] == 3
    assert doc["median"]["recovered_pooled"] == pytest.approx(0.09)
    assert doc["min"]["recovered_pooled"] == 0.0 and doc["max"]["recovered_pooled"] == pytest.approx(0.20)
    assert doc["inside_real_interval"] == 2


def test_a_seed_with_no_admission_is_zero_and_kept(pcs):
    r = pcs.seed_record(make_run_doc(p2_gain=0.0, oracle_gain=0.02, admitted=0.0), seed=8)
    assert r["recovered_pooled"] == 0.0 and r["share_pairs_admitted"] == 0.0
    doc = pcs.summarize([r], real_lo=-0.001, real_hi=0.001)
    assert doc["seeds"] == 1 and doc["inside_real_interval"] == 1


def test_an_oracle_without_gain_gives_no_share_and_a_note(pcs):
    r = pcs.seed_record(make_run_doc(p2_gain=0.001, oracle_gain=0.0, admitted=0.2), seed=9)
    assert r["recovered_pooled"] is None and "note" in r
    doc = pcs.summarize([r, rec(7, 0.1, 0.0)], real_lo=-0.001, real_hi=0.001)
    assert doc["median"]["recovered_pooled"] == pytest.approx(0.1)          # the seed without a share is left out of that statistic only
