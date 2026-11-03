"""Builder additions (T-022): appending already-known rows must keep the ledger valid, whatever time resolution each side has."""
import datetime as dt
import zoneinfo

import pandas as pd


def _with_unit(df, unit, stdlib_tz=False):
    """Copy with every time column at one resolution. The loaders carry datetime.timezone.utc; a ledger read from parquet carries
    zoneinfo UTC. Mixing the two tz objects and two resolutions is what once turned the timestamps into objects."""
    out = df.copy()
    tz = dt.timezone.utc if stdlib_tz else zoneinfo.ZoneInfo("UTC")
    for c in ("started_at", "final_read_at", "usable_after"):
        out[c] = out[c].astype(f"datetime64[{unit}, UTC]").dt.tz_convert(tz)
    return out


def test_appending_only_known_rows_is_a_no_op_even_with_mixed_time_units(imp, make_synth):
    ledger = imp("mootcourt.ledger")
    df = make_synth(seed=3, n_tests=30, variants_per_test=2)[0]
    base = _with_unit(df, "ns")
    base["started_at"] = base["started_at"].astype("datetime64[us, UTC]").dt.tz_convert(zoneinfo.ZoneInfo("UTC"))
    out = ledger.append_rows(base, _with_unit(df, "us", stdlib_tz=True))
    assert len(out) == len(base)
    ledger.validate_ledger(out)


def test_appending_new_rows_with_mixed_units_keeps_utc_datetimes(imp, make_synth):
    ledger = imp("mootcourt.ledger")
    df = make_synth(seed=4, n_tests=30, variants_per_test=2)[0].reset_index(drop=True)
    first, second = df.iloc[:20], df.iloc[20:]
    out = ledger.append_rows(_with_unit(first, "ns"), _with_unit(second, "us", stdlib_tz=True))
    ledger.validate_ledger(out)
    assert len(out) == len(df)
    assert pd.api.types.is_datetime64_any_dtype(out["final_read_at"])
