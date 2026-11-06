"""Upworthy Research Archive loader: one ledger row per variant contrast (exploratory split only).

The loader takes the path of the exploratory packages file as an argument. It reads only the columns in
``COLUMNS_USED`` plus the package id column when the file has one (the ``problem`` flag is read when present;
the real file lacks it). It never reads the former-staff columns (square, significance, first_place, winner,
updated_at). Nothing here touches the network or runs anything from the file.

Contrast. Within a test (``clickability_test_id``) the reference arm is the package with the earliest
``created_at``. Ties go to the lowest package id, or to the package listed first when the file has no id. Every
other package is one contrast against it. The real exploratory file has no named id column: its unnamed first
column is a unique, increasing package index of the full archive, and that is used as the package id (builder
call 44). Timestamps in the file carry no zone and are read as UTC.

Effect. ``y`` is the absolute difference in click-through rate in percentage points, ``100 * (ctr_v - ctr_r)``, and
its standard error is ``s = 100 * sqrt(ctr_v (1 - ctr_v) / n_v + ctr_r (1 - ctr_r) / n_r)`` from two independent
binomials (``ctr = clicks / impressions``). The relative lift ``(ctr_v - ctr_r) / ctr_r * 100`` and its delta-method
standard error are kept for display in the row's ``post_launch`` block and are never a label or an input: a ratio
against a noisy reference arm couples the effect to its own standard error (docs/method.md).

Pre-launch and post-launch fields. ``features_json`` holds the pre-launch fields at the top level (headline,
reference headline, whether the headline or the image changed, number of variants, and the raw text fields) and
everything only known after the test runs (reference and variant click-through rates, clicks, relative lift) in the
nested ``post_launch`` object. The feature builder reads the allow-list only and raises if a post-launch field sits
at the top level (``mootcourt.scale``). Cell statistics of concluded tests, such as the median reference rate, read
the ``post_launch`` block of rows already visible at the origin.

Cell. ``headline_only``, ``image_only`` or ``both`` from comparing the headline and ``eyecatcher_id`` of the variant
with the reference. A row for which no kind of change exists (identical arms, a test with a single package) carries
the cell ``unclassified``; it is never admitted.

Admission status, exactly one per row, in this precedence (builder call 43):
``single_arm`` (the test has fewer than two packages), ``missing_text`` (an empty headline in either arm),
``duplicate_arm`` (same headline and same image as the reference), ``imbalance_flag`` (the problem flag is set in
either arm, or the test started from 2013-06-25 to 2014-01-10 inclusive, the window the archive's June 2024 notice discourages; method
call 275), ``low_exposure`` (fewer than 1000 impressions in either arm), ``low_clicks`` (fewer than 10 clicks in either arm, where the
binomial standard error and the rate are unreliable), else ``admitted``.

Time. ``started_at`` of a contrast is the later of the two arms' ``created_at`` values, the first instant at which both
arms existed (code review finding REV-001: on the real file 34 tests have packages created up to 14.9 days after the
reference, and keying the horizon on the reference alone made 15 admitted rows visible before their variant existed).
``final_read_at`` and ``usable_after`` are test level (REV-026): seven days after the creation of the latest arm of the
test, the same instant for every contrast of the test, because the shared reference arm keeps accruing impressions and
clicks until the last arm ends and an earlier sibling row would expose it (the horizon of seven days is a modeling choice
for this archive). ``period`` is the calendar quarter of the final read. A single-package test keeps its one arm's time.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt.config import HORIZON_DAYS_UPWORTHY
from mootcourt.ledger import LEDGER_COLUMNS, SCHEMA_VERSION, make_row_id, quarter_of, validate_ledger

SOURCE = "upworthy"
COLUMNS_USED = ("created_at", "test_week", "clickability_test_id", "impressions", "clicks", "headline", "eyecatcher_id",
                "problem", "excerpt", "lede", "slug", "share_text")
OPTIONAL_COLUMNS = ("problem",)          # absent from the real exploratory file (builder call 44); the imbalance status then never fires
PACKAGE_ID_COLUMNS = ("id", "package_id", "Unnamed: 0")   # the real file has no named id; its unnamed first column is the package index
FORMER_STAFF_COLUMNS = ("square", "significance", "first_place", "winner", "updated_at")
# first and last day, UTC and inclusive: the tests the archive's June 2024 notice discourages (paper v2 plan, D1)
RANDOMIZATION_WINDOW = ("2013-06-25", "2014-01-10")
MIN_IMPRESSIONS = 1000
MIN_CLICKS = 10
_TRUE = {"true", "t", "1", "yes", "y"}


def diff_and_se(clicks_ref: float, n_ref: float, clicks_var: float, n_var: float) -> tuple[float, float]:
    """Absolute CTR difference in percentage points and its binomial standard error (percentage points).

    ``y = 100 (ctr_v - ctr_r)`` and ``s = 100 sqrt(ctr_v (1 - ctr_v) / n_v + ctr_r (1 - ctr_r) / n_r)``.
    Raises ValueError for a non-positive impression count or when the standard error is zero.
    """
    if min(n_ref, n_var) <= 0:
        raise ValueError("the difference needs at least one impression in each arm")
    cv, cr = clicks_var / n_var, clicks_ref / n_ref
    var = cv * (1.0 - cv) / n_var + cr * (1.0 - cr) / n_ref
    if not var > 0:
        raise ValueError("the standard error is zero (no variation in either arm)")
    return 100.0 * (cv - cr), 100.0 * math.sqrt(var)


def lift_and_se(clicks_ref: float, n_ref: float, clicks_var: float, n_var: float) -> tuple[float, float]:
    """Relative CTR lift in percent and its delta-method standard error (percent), for display only.

    Raises ValueError when either arm has zero clicks or zero impressions (the lift or its error is undefined).
    """
    if min(clicks_ref, clicks_var) <= 0 or min(n_ref, n_var) <= 0:
        raise ValueError("lift and standard error need at least one click and one impression in each arm")
    ratio = (clicks_var / n_var) / (clicks_ref / n_ref)
    var_log = 1.0 / clicks_var - 1.0 / n_var + 1.0 / clicks_ref - 1.0 / n_ref
    return 100.0 * (ratio - 1.0), 100.0 * ratio * math.sqrt(max(var_log, 0.0))


def _text(v) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def _flag(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return False
    return str(v).strip().lower() in _TRUE


def _read(path: Path) -> tuple[pd.DataFrame, str | None]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Upworthy file not found: {path}")
    header = list(pd.read_csv(path, nrows=0).columns)
    missing = [c for c in COLUMNS_USED if c not in header and c not in OPTIONAL_COLUMNS]
    if missing:
        raise ValueError(f"{path.name} lacks the expected columns {missing}")
    id_col = next((c for c in PACKAGE_ID_COLUMNS if c in header), None)
    use = [c for c in COLUMNS_USED if c in header] + ([id_col] if id_col else [])
    df = pd.read_csv(path, usecols=use, dtype={"clickability_test_id": str, "eyecatcher_id": str, **({id_col: str} if id_col else {})})
    if "problem" not in df.columns:
        df["problem"] = False
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, format="ISO8601")
    df["_order"] = np.arange(len(df))
    if id_col:
        df["_pkg"] = df[id_col].astype(str)
        df["_pkg_sort"] = pd.to_numeric(df[id_col], errors="coerce").fillna(np.inf)
    return df, id_col


def _kind(head_changed: bool, image_changed: bool) -> str:
    if head_changed and image_changed:
        return "both"
    return "headline_only" if head_changed else ("image_only" if image_changed else "unclassified")


def _window_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    """The window as a half-open interval [first day 00:00, day after the last day 00:00) in UTC."""
    first, last = RANDOMIZATION_WINDOW
    return pd.Timestamp(first, tz="UTC"), pd.Timestamp(last, tz="UTC") + pd.Timedelta(days=1)


def load_upworthy(path, exclude_randomization_window: bool = True) -> pd.DataFrame:
    """Build the contrast ledger from the exploratory packages file at ``path``; see the module docstring.

    ``exclude_randomization_window`` (default True) gives the status ``imbalance_flag`` to every contrast of a test that started inside
    ``RANDOMIZATION_WINDOW`` (the start of a test is the earliest ``created_at`` of its packages). False is run 7's configuration,
    the ablation ``include-randomization-window``; it changes statuses only, never a row, an effect or a time.
    """
    df, id_col = _read(path)
    win_lo, win_hi = _window_bounds()
    has_id = id_col is not None
    horizon = pd.Timedelta(days=HORIZON_DAYS_UPWORTHY)
    rows: list[dict] = []
    for test_id, g in df.groupby("clickability_test_id", sort=False):
        sort_cols = ["created_at"] + (["_pkg_sort", "_pkg"] if has_id else []) + ["_order"]
        g = g.sort_values(sort_cols, kind="stable")
        ref = g.iloc[0]
        n_pk = len(g)
        ids = [str(v) for v in g["_pkg"]] if has_id else [f"p{k}" for k in range(n_pk)]
        if n_pk < 2:
            started = ref["created_at"]
            final = started + horizon
            base = {"source": SOURCE, "test_id": str(test_id), "period": quarter_of(final), "started_at": started, "final_read_at": final,
                    "usable_after": final, "schema_version": SCHEMA_VERSION}
            rows.append({**base, "row_id": make_row_id(SOURCE, str(test_id), ids[0]), "variant_id": ids[0], "cell": "unclassified",
                         "y": np.nan, "s": np.nan, "n_ref": int(ref["impressions"]), "n_var": int(ref["impressions"]),
                         "status": "single_arm",
                         "features_json": json.dumps({"headline": _text(ref["headline"]), "n_variants": n_pk}, sort_keys=True)})
            continue
        hr, er = _text(ref["headline"]), _text(ref["eyecatcher_id"])
        in_window = bool(exclude_randomization_window and win_lo <= g["created_at"].min() < win_hi)
        # The reference arm is shared by every contrast of the test and keeps accruing until the test's last arm ends, so
        # the final read is test level: seven days after the creation of the latest arm (REV-026). started_at stays per contrast.
        final = g["created_at"].max() + horizon
        for k in range(1, n_pk):
            v = g.iloc[k]
            started = max(ref["created_at"], v["created_at"])       # both arms exist from here on (REV-001)
            base = {"source": SOURCE, "test_id": str(test_id), "period": quarter_of(final), "started_at": started, "final_read_at": final,
                    "usable_after": final, "schema_version": SCHEMA_VERSION}
            hv, ev = _text(v["headline"]), _text(v["eyecatcher_id"])
            head_changed, image_changed = hv != hr, ev != er
            nr, nv, cr, cv = int(ref["impressions"]), int(v["impressions"]), int(ref["clicks"]), int(v["clicks"])
            if not hr.strip() or not hv.strip():
                status = "missing_text"
            elif not head_changed and not image_changed:
                status = "duplicate_arm"
            elif in_window or _flag(ref["problem"]) or _flag(v["problem"]):
                status = "imbalance_flag"
            elif min(nr, nv) < MIN_IMPRESSIONS:
                status = "low_exposure"
            elif min(cr, cv) < MIN_CLICKS:
                status = "low_clicks"
            else:
                status = "admitted"
            y = s = np.nan
            post = {"clicks_ref": cr, "clicks_var": cv, "ctr_ref": (cr / nr) if nr > 0 else None,
                    "ctr_var": (cv / nv) if nv > 0 else None}
            if min(nr, nv) > 0:
                try:
                    y, s = diff_and_se(cr, nr, cv, nv)
                except ValueError:
                    pass                                   # both arms constant: no standard error, never admitted
            if min(cr, cv) > 0 and min(nr, nv) > 0:
                post["relative_lift"], post["relative_lift_se"] = lift_and_se(cr, nr, cv, nv)
            feats = {"headline": hv, "excerpt": _text(v["excerpt"]), "lede": _text(v["lede"]), "slug": _text(v["slug"]),
                     "share_text": _text(v["share_text"]), "image_changed": bool(image_changed), "headline_changed": bool(head_changed),
                     "n_variants": n_pk, "reference_headline": hr, "post_launch": post}
            rows.append({**base, "row_id": make_row_id(SOURCE, str(test_id), ids[k]), "variant_id": ids[k],
                         "cell": _kind(head_changed, image_changed), "y": y, "s": s, "n_ref": nr, "n_var": nv, "status": status,
                         "features_json": json.dumps(feats, sort_keys=True)})
    out = pd.DataFrame(rows, columns=LEDGER_COLUMNS) if rows else pd.DataFrame({c: [] for c in LEDGER_COLUMNS})
    out["y"], out["s"] = out["y"].astype("float64"), out["s"].astype("float64")
    out["n_ref"], out["n_var"] = out["n_ref"].astype("int64"), out["n_var"].astype("int64")
    out["schema_version"] = out["schema_version"].astype("int64")
    for c in ("started_at", "final_read_at", "usable_after"):
        out[c] = pd.to_datetime(out[c], utc=True)
    validate_ledger(out)
    return out


def inventory(ledger: pd.DataFrame) -> dict:
    """Counts of tests, contrasts and statuses, for DATA.md."""
    return {"tests": int(ledger["test_id"].nunique()), "contrasts_and_single_arms": int(len(ledger)),
            "by_status": {k: int(v) for k, v in ledger["status"].value_counts().sort_index().items()},
            "by_cell_admitted": {k: int(v) for k, v in ledger.loc[ledger["status"] == "admitted", "cell"].value_counts().sort_index().items()}}
