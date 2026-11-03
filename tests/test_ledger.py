"""T-002 contracts: ledger schema, statuses, snapshots, origin queries."""
import datetime as dt
import stat

import numpy as np
import pandas as pd
import pytest

UTC = dt.timezone.utc
EXPECTED_COLUMNS = [
    "row_id", "source", "test_id", "variant_id", "cell", "period", "started_at", "final_read_at",
    "usable_after", "y", "s", "n_ref", "n_var", "status", "features_json", "schema_version",
]
EXPECTED_STATUSES = {"admitted", "low_exposure", "low_clicks", "imbalance_flag", "missing_text", "single_arm", "duplicate_arm"}


def _mixed(ledger_builder):
    """One row per status plus extra admitted rows."""
    df = ledger_builder(n=12, test_size=1, seed=5)
    for i, status in enumerate(sorted(EXPECTED_STATUSES - {"admitted"})):
        df.loc[i, "status"] = status
    return df


def test_columns_and_statuses_exact(imp):
    ledger = imp("mootcourt.ledger")
    assert list(ledger.LEDGER_COLUMNS) == EXPECTED_COLUMNS
    assert len(ledger.LEDGER_COLUMNS) == 16
    assert ledger.SCHEMA_VERSION == 1
    assert set(ledger.STATUSES) == EXPECTED_STATUSES and len(ledger.STATUSES) == 7


def test_validate_ledger_accepts_good_frame(imp, tiny_ledger):
    imp("mootcourt.ledger").validate_ledger(tiny_ledger)


@pytest.mark.parametrize("breakage", ["missing_column", "wrong_dtype", "duplicate_row_id", "unknown_status"])
def test_validate_ledger_rejects_bad_frames(imp, ledger_builder, breakage):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=10)
    if breakage == "missing_column":
        df = df.drop(columns=["usable_after"])
    elif breakage == "wrong_dtype":
        df["y"] = df["y"].astype(str)
    elif breakage == "duplicate_row_id":
        df.loc[1, "row_id"] = df.loc[0, "row_id"]
    else:
        df.loc[0, "status"] = "mystery"
    with pytest.raises(ledger.LedgerSchemaError):
        ledger.validate_ledger(df)


def test_naive_timestamps_are_rejected(imp, ledger_builder):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=5)
    df["usable_after"] = df["usable_after"].dt.tz_localize(None)
    with pytest.raises(ledger.LedgerSchemaError):
        ledger.validate_ledger(df)


def test_visible_rows_boundary_is_inclusive_to_the_microsecond(imp, ledger_builder, origin):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=3, test_size=1)
    df["usable_after"] = pd.to_datetime(
        [origin - dt.timedelta(days=1), origin, origin + dt.timedelta(microseconds=1)], utc=True)
    got = ledger.visible_rows(df, origin)
    assert set(got["row_id"]) == set(df["row_id"].iloc[:2]), "row at origin visible, row one microsecond later not"


def test_visible_rows_only_admitted_and_cell_filter(imp, ledger_builder, origin):
    ledger = imp("mootcourt.ledger")
    df = _mixed(ledger_builder)
    df.loc[df.index[-3:], "cell"] = "image_only"
    got = ledger.visible_rows(df, origin)
    assert set(got["status"]) == {"admitted"}
    assert len(got) == (df["status"] == "admitted").sum()
    only = ledger.visible_rows(df, origin, cell="image_only")
    assert set(only["cell"]) == {"image_only"}


def test_visible_rows_before_everything_is_empty(imp, tiny_ledger):
    ledger = imp("mootcourt.ledger")
    early = pd.Timestamp("2012-01-01", tz="UTC")
    assert len(ledger.visible_rows(tiny_ledger, early)) == 0


def test_excluded_rows_survive_write_and_read(imp, ledger_builder, tmp_path):
    ledger = imp("mootcourt.ledger")
    df = _mixed(ledger_builder)
    path = tmp_path / "ledger.parquet"
    ledger.write_ledger(df, path)
    back = ledger.read_ledger(path)
    assert len(back) == len(df)
    assert set(back["status"]) == set(df["status"])
    assert set(back["status"]) >= EXPECTED_STATUSES


def test_parquet_round_trip_keeps_utc_timestamps(imp, ledger_builder, tmp_path):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=20)
    ledger.write_ledger(df, tmp_path / "l.parquet")
    back = ledger.read_ledger(tmp_path / "l.parquet")
    for col in ("started_at", "final_read_at", "usable_after"):
        assert str(back[col].dt.tz) == "UTC"
    pd.testing.assert_series_equal(back["usable_after"].reset_index(drop=True), df["usable_after"].reset_index(drop=True),
                                   check_names=False)


def test_snapshot_id_form_determinism_order_independence(imp, ledger_builder):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=30)
    today = dt.date(2026, 11, 2)
    sid = ledger.snapshot_id(df, today=today)
    assert sid.startswith("20261102-") and len(sid) == 8 + 1 + 12
    assert all(c in "0123456789abcdef" for c in sid.split("-")[1])
    assert ledger.snapshot_id(df, today=today) == sid
    assert ledger.snapshot_id(df.sample(frac=1.0, random_state=3), today=today) == sid


def test_snapshot_id_changes_when_one_row_is_added(imp, ledger_builder):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=30)
    extra = ledger_builder(n=1, id_prefix="extra")
    today = dt.date(2026, 11, 2)
    assert ledger.snapshot_id(pd.concat([df, extra], ignore_index=True), today=today) != ledger.snapshot_id(df, today=today)


def test_write_snapshot_is_read_only_and_refuses_duplicates(imp, ledger_builder, tmp_path):
    ledger = imp("mootcourt.ledger")
    df = ledger_builder(n=15)
    today = dt.date(2026, 11, 2)
    sid = ledger.write_snapshot(df, tmp_path, today=today)
    snap_dir = tmp_path / "snapshots" / sid
    assert snap_dir.is_dir()
    files = [p for p in snap_dir.rglob("*") if p.is_file()]
    assert files, "snapshot must contain files"
    for p in files:
        assert not (p.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)), f"{p} must be read-only"
    with pytest.raises(ledger.SnapshotExistsError):
        ledger.write_snapshot(df, tmp_path, today=today)
    assert ledger.latest_snapshot(tmp_path) == sid


def test_append_rows_is_idempotent_and_refuses_changes(imp, ledger_builder):
    ledger = imp("mootcourt.ledger")
    base = ledger_builder(n=10)
    new = ledger_builder(n=4, id_prefix="n")
    once = ledger.append_rows(base, new)
    twice = ledger.append_rows(once, new)
    assert len(once) == 14 and len(twice) == 14
    changed = new.copy()
    changed.loc[changed.index[0], "y"] += 1.0
    with pytest.raises(ledger.LedgerConflictError):
        ledger.append_rows(once, changed)


@pytest.mark.parametrize("ts,expected", [
    ("2014-01-01T00:00:00Z", "2014Q1"), ("2014-03-31T23:59:59Z", "2014Q1"),
    ("2014-04-01T00:00:00Z", "2014Q2"), ("2014-06-30T23:59:59Z", "2014Q2"),
    ("2014-07-01T00:00:00Z", "2014Q3"), ("2014-09-30T23:59:59Z", "2014Q3"),
    ("2014-10-01T00:00:00Z", "2014Q4"), ("2014-12-31T23:59:59Z", "2014Q4"),
])
def test_quarter_of_boundaries(imp, ts, expected):
    assert imp("mootcourt.ledger").quarter_of(pd.Timestamp(ts)) == expected


def test_make_row_id(imp):
    assert imp("mootcourt.ledger").make_row_id("upworthy", "T1", "P2") == "upworthy:T1:P2"


def test_nan_effect_allowed_only_on_excluded_rows(imp, ledger_builder):
    ledger = imp("mootcourt.ledger")
    ok = ledger_builder(n=4)
    ok.loc[0, ["y", "s"]] = np.nan
    ok.loc[0, "status"] = "single_arm"
    ledger.validate_ledger(ok)
    bad = ledger_builder(n=4)
    bad.loc[0, "y"] = np.nan
    with pytest.raises(ledger.LedgerSchemaError):
        ledger.validate_ledger(bad)
    bad2 = ledger_builder(n=4)
    bad2.loc[0, "s"] = 0.0
    with pytest.raises(ledger.LedgerSchemaError):
        ledger.validate_ledger(bad2)
