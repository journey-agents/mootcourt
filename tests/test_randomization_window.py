"""X1 (paper v2 plan, D1): tests that started from 2013-06-25 to 2014-01-10 inclusive get the status imbalance_flag.

The archive's maintainers (June 2024 notice, https://upworthy.natematias.com/about-the-archive) report randomization problems in tests of that
window. The exploratory file we read has no flag column, so the loader applies the date rule by default; ``exclude_randomization_window=False``
is run 7's configuration, the ablation ``include-randomization-window``.
"""

import csv

import pandas as pd
import pytest

from mootcourt.sources import upworthy as up

COLUMNS = [
    "created_at",
    "test_week",
    "clickability_test_id",
    "impressions",
    "clicks",
    "headline",
    "eyecatcher_id",
    "excerpt",
    "lede",
    "slug",
    "share_text",
]


def _pair(test, ref_at, var_at, imp=5000):
    def mk(at, clicks, head):
        return {
            "created_at": at,
            "test_week": "201301",
            "clickability_test_id": test,
            "impressions": imp,
            "clicks": clicks,
            "headline": head,
            "eyecatcher_id": "e1",
            "excerpt": "x",
            "lede": "l",
            "slug": "s",
            "share_text": "t",
        }

    return [mk(ref_at, 100, f"{test} ref"), mk(var_at, 140, f"{test} var")]


def _write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


BOUNDARIES = {
    "first_day_start": ("2013-06-25 00:00:00", True),
    "day_before": ("2013-06-24 23:59:59", False),
    "last_day_late": ("2014-01-10 23:59:59", True),
    "day_after": ("2014-01-11 00:00:00", False),
    "inside": ("2013-10-01 12:00:00", True),
    "ordinary_2014": ("2014-09-28 10:00:00", False),
}


@pytest.fixture
def csv_path(tmp_path):
    rows = []
    for name, (at, _) in BOUNDARIES.items():
        rows += _pair(name, at, at)
    p = tmp_path / "u.csv"
    _write(p, rows)
    return p


def test_boundary_tests_get_the_status_and_outside_ones_do_not(csv_path):
    out = up.load_upworthy(csv_path)
    got = dict(zip(out["test_id"], out["status"]))
    for name, (_, inside) in BOUNDARIES.items():
        assert got[name] == ("imbalance_flag" if inside else "admitted"), name


def test_the_window_follows_the_test_start_not_the_variant(tmp_path):
    # the reference arm is created the day before the window, a variant a day later: the test started outside, so it is not flagged
    p = tmp_path / "u.csv"
    _write(p, _pair("late_variant", "2013-06-24 10:00:00", "2013-06-25 10:00:00"))
    assert set(up.load_upworthy(p)["status"]) == {"admitted"}


def test_ablation_regenerates_the_old_statuses(csv_path):
    out = up.load_upworthy(csv_path, exclude_randomization_window=False)
    assert set(out["status"]) == {"admitted"}
    on = up.load_upworthy(csv_path)
    # same rows, same effects; only the status differs
    assert list(out["row_id"]) == list(on["row_id"])
    pd.testing.assert_series_equal(out["y"], on["y"])
    assert (on["status"] == "imbalance_flag").sum() == 3 and (out["status"] == "imbalance_flag").sum() == 0


def test_earlier_statuses_keep_their_precedence(tmp_path):
    rows = _pair("dup", "2013-10-01 10:00:00", "2013-10-01 10:00:00")
    rows[1]["headline"] = rows[0]["headline"]  # same headline and image: duplicate_arm outranks imbalance_flag
    low = _pair("low", "2013-10-01 10:00:00", "2013-10-01 10:00:00", imp=500)  # low_exposure ranks after imbalance_flag
    p = tmp_path / "u.csv"
    _write(p, rows + low)
    got = dict(zip(up.load_upworthy(p)["test_id"], up.load_upworthy(p)["status"]))
    assert got == {"dup": "duplicate_arm", "low": "imbalance_flag"}


def test_inventory_counts_the_flagged_rows(csv_path):
    inv = up.inventory(up.load_upworthy(csv_path))
    assert inv["by_status"]["imbalance_flag"] == 3


def test_window_constants_are_the_notice_dates():
    assert up.RANDOMIZATION_WINDOW == ("2013-06-25", "2014-01-10")


def test_replace_source_swaps_only_the_upworthy_rows(csv_path):
    from mootcourt.ledger import LedgerSchemaError, content_digest, replace_source
    from mootcourt.sources import synthetic as synth

    other, _ = synth.generate(synth.SyntheticConfig(seed=0, n_tests=20))
    on = up.load_upworthy(csv_path)
    off = up.load_upworthy(csv_path, exclude_randomization_window=False)
    run8 = pd.concat([on, other], ignore_index=True)
    back = replace_source(run8, off, "upworthy")
    assert list(back["source"]) == ["upworthy"] * len(off) + ["synthetic"] * len(other)
    assert set(back[back["source"] == "upworthy"]["status"]) == {"admitted"}
    pd.testing.assert_frame_equal(back[back["source"] == "synthetic"].reset_index(drop=True), other.reset_index(drop=True))
    # the ablation regenerates run 7's ledger: the same content digest as the ledger built without the rule
    run7 = pd.concat([off, other], ignore_index=True)
    assert content_digest(back) == content_digest(run7)
    assert content_digest(run8) != content_digest(run7)  # a different content, so a different snapshot id
    with pytest.raises(LedgerSchemaError):
        replace_source(run8, other, "upworthy")
