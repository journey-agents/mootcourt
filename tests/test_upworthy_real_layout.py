"""Builder additions: the loader on the real file's layout (no problem column, unnamed index as package id, mixed timestamps)."""
import csv

import pandas as pd
import pytest

HEADER = ["", "created_at", "updated_at", "clickability_test_id", "excerpt", "headline", "lede", "slug", "eyecatcher_id", "impressions",
          "clicks", "significance", "first_place", "winner", "share_text", "square", "test_week"]


def _write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)


def _r(idx, created, test, imp, clicks, headline, eye):
    return [idx, created, "2099-01-01 00:00:00", test, "ex", headline, "lede", "slug", eye, imp, clicks, 99.0, True, True, "", "", 201440]


def test_real_layout_without_problem_column_and_with_mixed_timestamps(imp, tmp_path):
    path = tmp_path / "real.csv"
    _write(path, [_r(7, "2014-09-28 10:00:00.250", "T1", 5000, 100, "A", "e1"), _r(3, "2014-09-28 10:00:00.250", "T1", 5000, 150, "B", "e1"),
                  _r(9, "2014-09-28 11:00:00", "T1", 5000, 90, "C", "e2")])
    out = imp("mootcourt.sources.upworthy").load_upworthy(path)
    assert set(out["status"]) == {"admitted"} and len(out) == 2
    # the tie on created_at goes to the lowest package index (3), so the reference is "B"
    assert sorted(out["variant_id"]) == ["7", "9"]
    # each contrast starts when both of its arms exist (REV-001): the later created_at of the variant and the reference
    by_variant = out.set_index("variant_id")["started_at"]
    assert by_variant["7"] == pd.Timestamp("2014-09-28 10:00:00.250", tz="UTC") and by_variant["9"] == pd.Timestamp("2014-09-28 11:00:00", tz="UTC")
    assert "2099" not in out.to_json(date_format="iso")


def test_missing_required_column_is_a_clear_error(imp, tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("created_at,headline\n2014-01-01 00:00:00,x\n")
    with pytest.raises(ValueError, match="lacks the expected columns"):
        imp("mootcourt.sources.upworthy").load_upworthy(path)


def test_zero_click_variant_is_low_clicks_not_a_crash(imp, tmp_path):
    path = tmp_path / "z.csv"
    _write(path, [_r(0, "2014-09-28 10:00:00", "T1", 5000, 100, "A", "e1"), _r(1, "2014-09-28 11:00:00", "T1", 5000, 0, "B", "e1")])
    out = imp("mootcourt.sources.upworthy").load_upworthy(path)
    assert list(out["status"]) == ["low_clicks"]
