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


def relative_lift_ledger(ledger: pd.DataFrame) -> pd.DataFrame:
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
    return out


def planned_exposure(rows: pd.DataFrame) -> np.ndarray:
    """Planned exposures per arm of ledger rows: the mean of the two arms' impressions."""
    return 0.5 * (rows["n_ref"].to_numpy(float) + rows["n_var"].to_numpy(float))
