"""Pre-launch scale: the standard error a forecaster may use, and the fields it may read.

A forecast is made before the test runs. Two things follow, and this module is where both are enforced.

Fields. A feature may use only the pre-launch allow-list ``PRELAUNCH_FEATURES``: the headline, the reference
headline, whether the headline or the image changed, the number of variants, the planned exposures per arm, the
cell and the period. ``prelaunch_view`` returns those fields from a ledger row's features and raises
``PostLaunchFieldError`` if a post-launch field (reference click-through rate, clicks, realized standard error)
sits among them. Ledger rows keep such fields inside the nested ``post_launch`` block, which no feature reads;
cell statistics of concluded tests (history visible at the origin) may read it.

Scale. ``s_star`` is the standard error of the future estimate known at launch. For Upworthy it comes from the
planned exposures per arm and the median reference click-through rate ``c`` of the cell among rows visible at the
origin: ``s_star = 100 sqrt(c (1 - c) (1 / n_ref + 1 / n_var))``, which is ``100 sqrt(2 c (1 - c) / n_arm)`` for equal
arms. For ASOS it is ``sqrt(1 / n_ref + 1 / n_var)`` (the standardized effect at zero). For the synthetic source the
generator fixes the standard error before the test and it is used as given. The realized ``s`` defines only the
event ``y > 1.96 s`` and is never an input to a predictor.

Units: percentage points of click-through rate for Upworthy, standard deviations for ASOS.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

PRELAUNCH_FEATURES = (
    "headline", "reference_headline", "headline_changed", "image_changed", "n_variants",
    "planned_exposures", "cell", "period",
)
# Fields known only after the test has run; none may appear among the fields a feature reads.
POST_LAUNCH_FIELDS = (
    "ctr_ref", "ctr_var", "clicks", "clicks_ref", "clicks_var", "s", "realized_s", "y",
    "relative_lift", "relative_lift_se",
)
POST_LAUNCH_BLOCK = "post_launch"
DEFAULT_CTR = 0.02
# set to "relative" by ``relative_lift_ledger(planned=True)``: s_star_rows then returns the relative lift's planned standard error
PLANNED_SCALE_COLUMN = "planned_scale"
_CTR_FLOOR = 1e-6


class PostLaunchFieldError(ValueError):
    """A feature input contains a field that is only known after the test has run."""


def post_launch_fields(features: dict) -> list[str]:
    """Post-launch field names found among the top-level keys of a features dict (the nested block is allowed)."""
    return sorted(set(features) & set(POST_LAUNCH_FIELDS))


def prelaunch_view(features: dict) -> dict:
    """The pre-launch fields of a features dict; raises ``PostLaunchFieldError`` on any post-launch field."""
    bad = post_launch_fields(features)
    if bad:
        raise PostLaunchFieldError(f"post-launch fields are not allowed as features: {bad}")
    return {k: features[k] for k in PRELAUNCH_FEATURES if k in features}


def audit_feature_fields(features_json: pd.Series) -> list[tuple[int, list[str]]]:
    """``(position, fields)`` for every row whose top-level features carry a post-launch field."""
    out = []
    for i, j in enumerate(features_json.tolist()):
        bad = post_launch_fields(json.loads(j))
        if bad:
            out.append((i, bad))
    return out


# ----------------------------------------------------------------------- s_star
def upworthy_s_star(n_ref, n_var, ctr) -> np.ndarray:
    """``100 sqrt(c (1 - c) (1 / n_ref + 1 / n_var))`` in percentage points (arrays broadcast)."""
    n_ref, n_var, c = (np.asarray(v, dtype=np.float64) for v in (n_ref, n_var, ctr))
    if np.any(n_ref <= 0) or np.any(n_var <= 0):
        raise ValueError("planned exposures must be positive")
    if np.any((c <= 0) | (c >= 1)):
        raise ValueError("the click-through rate must be in (0, 1)")
    return 100.0 * np.sqrt(c * (1.0 - c) * (1.0 / n_ref + 1.0 / n_var))


def ctr_from_se(n_arm, s_pp) -> float:
    """Invert ``s = 100 sqrt(2 c (1 - c) / n)`` for ``c`` (the lower root); 0.5 when no root exists."""
    k = float(n_arm) * (float(s_pp) / 100.0) ** 2 / 2.0
    return 0.5 if k >= 0.25 else (1.0 - math.sqrt(1.0 - 4.0 * k)) / 2.0


def row_ctr_ref(features_json: str) -> float | None:
    """Reference click-through rate of a concluded Upworthy row, from its ``post_launch`` block (history only)."""
    v = json.loads(features_json).get(POST_LAUNCH_BLOCK, {}).get("ctr_ref")
    return None if v is None else float(v)


def cell_median_ctr(visible: pd.DataFrame) -> dict[str, float]:
    """Median reference click-through rate per cell among the rows given (the caller passes visible rows only).

    Rows without a recorded rate contribute the rate implied by their exposures and standard error. A cell with
    no rows is absent from the result; use ``lookup_ctr`` for the fallback chain.
    """
    out: dict[str, float] = {}
    for cell, g in visible.groupby("cell"):
        vals = []
        for j, nr, nv, s in zip(g["features_json"], g["n_ref"], g["n_var"], g["s"]):
            c = row_ctr_ref(j)
            vals.append(c if c is not None else ctr_from_se(0.5 * (nr + nv), s))
        vals = [v for v in vals if v is not None and v > 0]
        if vals:
            out[str(cell)] = float(np.median(vals))
    return out


def lookup_ctr(by_cell: dict[str, float], cell: str) -> float:
    """Median rate of the cell, else the median over cells, else the module default."""
    if cell in by_cell:
        return max(by_cell[cell], _CTR_FLOOR)
    if by_cell:
        return max(float(np.median(list(by_cell.values()))), _CTR_FLOOR)
    return DEFAULT_CTR


def s_star_rows(scored: pd.DataFrame, visible: pd.DataFrame) -> np.ndarray:
    """Pre-launch ``s_star`` for each row of ``scored`` given the rows visible at the origin.

    Upworthy rows use planned exposures and the visible cell median rate; ASOS rows use the planned exposures;
    the synthetic generator uses the standard error fixed at launch, as given; any other source (an imported ledger) uses the
    exposure-scaled rule: the cell's median ``s sqrt(n)`` over the visible rows divided by ``sqrt(n)`` of the row's planned exposure
    (``generic_s_star``), so the standard error used for forecasting never comes from the row's own result.
    """
    n = len(scored)
    out = np.array(scored["s"].to_numpy(float), copy=True)
    source = scored["source"].to_numpy(dtype=object)
    up = source == "upworthy"
    if up.any():
        by_cell = cell_median_ctr(visible[visible["source"] == "upworthy"] if "source" in visible else visible)
        c = np.array([lookup_ctr(by_cell, str(k)) for k in scored["cell"].to_numpy()[up]])
        out[up] = upworthy_s_star(scored["n_ref"].to_numpy()[up], scored["n_var"].to_numpy()[up], c)
        if PLANNED_SCALE_COLUMN in scored.columns:
            # relative lift at planned precision (X2): the standard error of a ratio at zero effect is s_star / c
            rel = (scored[PLANNED_SCALE_COLUMN].to_numpy(dtype=object)[up] == "relative")
            out[np.flatnonzero(up)[rel]] = out[np.flatnonzero(up)[rel]] / c[rel]
    asos = source == "asos"
    if asos.any():
        out[asos] = np.sqrt(1.0 / scored["n_ref"].to_numpy(float)[asos] + 1.0 / scored["n_var"].to_numpy(float)[asos])
    other = ~(up | asos | (source == "synthetic"))
    if other.any():
        out[other] = generic_s_star(scored, visible, other)
    assert out.shape == (n,)
    return out


def median_s_sqrt_n(rows: pd.DataFrame) -> dict[str, float]:
    """Per cell, the median of ``s sqrt(n)`` with ``n`` the mean of the two arms' exposures (the scale of one unit of exposure)."""
    out: dict[str, float] = {}
    for cell, g in rows.groupby("cell"):
        n_arm = 0.5 * (g["n_ref"].to_numpy(float) + g["n_var"].to_numpy(float))
        v = g["s"].to_numpy(float) * np.sqrt(n_arm)
        v = v[np.isfinite(v) & (v > 0)]
        if len(v):
            out[str(cell)] = float(np.median(v))
    return out


def generic_s_star(scored: pd.DataFrame, visible: pd.DataFrame, mask: np.ndarray) -> np.ndarray:
    """Pre-launch ``s_star`` for the rows of ``scored`` selected by ``mask``: cell median ``s sqrt(n)`` of ``visible`` over ``sqrt(planned n)``.

    A cell with no visible row uses the median over cells; with no visible row at all the row's own ``s`` is kept (nothing else is known).
    """
    by_cell = median_s_sqrt_n(visible)
    fallback = float(np.median(list(by_cell.values()))) if by_cell else None
    sub = scored[mask]
    n_arm = planned_exposure(sub)
    out = np.array(sub["s"].to_numpy(float), copy=True)
    for i, (cell, n_i) in enumerate(zip(sub["cell"].astype(str).to_numpy(), n_arm, strict=True)):
        c = by_cell.get(cell, fallback)
        if c is not None and n_i > 0:
            out[i] = c / np.sqrt(n_i)
    return out


def relative_lift_ledger(ledger: pd.DataFrame, planned: bool = False) -> pd.DataFrame:
    """The Upworthy rows of ``ledger`` re-expressed as the first run had them: ``y`` the relative lift in percent and ``s`` its standard error.

    Both come from the ``post_launch`` block, where the ledger keeps them as display data. A relative lift against a noisy reference arm
    couples ``y`` to ``s``; this transform exists only to reproduce that cautionary run (``--effect-scale relative``). Rows of other sources
    are left as they are; an Upworthy row whose lift is missing or not finite becomes ``low_exposure`` so it is never scored.
    """
    out = ledger.copy()
    up = (out["source"] == "upworthy").to_numpy()
    y, s = out["y"].to_numpy(float).copy(), out["s"].to_numpy(float).copy()
    bad = np.zeros(len(out), bool)
    for i in np.flatnonzero(up):
        post = json.loads(out["features_json"].iat[i]).get(POST_LAUNCH_BLOCK, {})
        ly, ls = post.get("relative_lift"), post.get("relative_lift_se")
        if ly is None or ls is None or not np.isfinite(ly) or not np.isfinite(ls) or ls <= 0:
            bad[i] = True
        else:
            y[i], s[i] = float(ly), float(ls)
    out["y"], out["s"] = y, s
    out.loc[bad, "status"] = "low_exposure"
    if planned:
        # X2, relative lift at PLANNED precision: the forecaster is given the standard error a launch can know, ``s_star / c`` (pre-launch
        # exposure and the visible cell median rate), in the units of the relative lift, instead of the realized one of the cautionary run
        out[PLANNED_SCALE_COLUMN] = "relative"
    return out


def cell_median_exposure_ledger(ledger: pd.DataFrame, visible_only: bool = False) -> pd.DataFrame:
    """The ledger with the planned exposure of every Upworthy row set to the median of its cell (X3, the exposure stand-in fixed).

    By default the median is over the whole ledger, rows that conclude after a forecast's origin included: a diagnostic, since no forecast
    could have had that value. With ``visible_only`` each row gets the median over the cell's admitted rows that were usable by the start
    of the calendar quarter (UTC) in which the row's test started, which is the set visible at the row's quarterly origin. A row with no
    such earlier rows (the first quarters of a cell) takes the earliest such median its cell has, or the whole-ledger median when the cell
    never has one (docs/superpowers/plans/2026-11-12-base-rate-recency-and-origins.md, Part E).

    The planned exposure of a row is the mean of its two arms' realized impressions (``planned_exposure``), a stand-in for the exposure a
    launch would have planned. Here both arms of every row get their cell's median planned exposure over the admitted rows (at least one
    impression), a constant per cell that carries no information about the row, so ``s_star``, the exposure feature and the ranking that read
    exposure lose their row-level variation. ``y``, ``s`` and the statuses are unchanged. A view: the stored ledger is not changed.
    """
    out = ledger.copy()
    up = (out["source"] == "upworthy").to_numpy()
    adm = up & (out["status"] == "admitted").to_numpy()
    expo = planned_exposure(out)
    for cell in out.loc[adm, "cell"].unique():
        m = adm & (out["cell"] == cell).to_numpy()
        med = max(int(round(float(np.median(expo[m])))), 1)
        sel = up & (out["cell"] == cell).to_numpy()
        if visible_only:
            started = pd.to_datetime(out["started_at"], utc=True)
            quarter = pd.to_datetime({"year": started.dt.year, "month": (started.dt.month - 1) // 3 * 3 + 1, "day": 1}, utc=True)
            usable = pd.to_datetime(out["usable_after"], utc=True)
            by_quarter = {}
            for q in sorted(quarter[sel].unique()):
                vis = m & (usable <= q).to_numpy()
                by_quarter[q] = max(int(round(float(np.median(expo[vis])))), 1) if vis.any() else None
            first = next((x for x in by_quarter.values() if x is not None), med)
            values = np.array([by_quarter[q] if by_quarter[q] is not None else first for q in quarter[sel]])
            out.loc[sel, "n_ref"] = values
            out.loc[sel, "n_var"] = values
            continue
        out.loc[sel, "n_ref"] = med
        out.loc[sel, "n_var"] = med
    out["n_ref"], out["n_var"] = out["n_ref"].astype("int64"), out["n_var"].astype("int64")
    return out


def prelaunch_admission_ledger(ledger: pd.DataFrame) -> pd.DataFrame:
    """The ledger re-admitted on exposure only: a ``low_clicks`` row with a finite estimate and standard error becomes ``admitted``.

    The minimum-clicks rule is decided on realized clicks, an outcome a launching team cannot know, so it conditions the scored population
    on a post-launch quantity (round 00, R2). This view drops that rule and keeps the exposure rule, which depends on the planned
    exposure; every contrast whose estimate and standard error exist is then scored. It is the ``--admission prelaunch`` ablation: the
    main run keeps the ledger's statuses. Rows of any other status are untouched.
    """
    out = ledger.copy()
    ok = (
        (out["status"] == "low_clicks")
        & np.isfinite(out["y"].to_numpy(float))
        & (out["s"].to_numpy(float) > 0)
        & np.isfinite(out["s"].to_numpy(float))
    )
    out.loc[ok.to_numpy(), "status"] = "admitted"
    return out


def planned_exposure(rows: pd.DataFrame) -> np.ndarray:
    """Planned exposures per arm of ledger rows: the mean of the two arms' impressions."""
    return 0.5 * (rows["n_ref"].to_numpy(float) + rows["n_var"].to_numpy(float))


def one_contrast_per_test_ledger(ledger):
    """A view of the ledger with one admitted contrast per test: the admitted row with the lowest ``row_id`` of each test is kept, the other
    admitted rows are dropped (not relabelled), so every test has one headline against its reference and the number of arms plays no part.
    Rows that are not admitted are kept as they are. The stored ledger is not changed."""
    adm = ledger["status"] == "admitted"
    first = ledger.loc[adm].sort_values("row_id", kind="stable").drop_duplicates("test_id", keep="first").index
    return ledger.loc[~adm | ledger.index.isin(first)].reset_index(drop=True)

