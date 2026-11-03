"""ASOS Digital Experiments Dataset loader: one ledger row per treatment variant per decision metric, final checkpoint only.

Layout of the real file (``asos_digital_experiments_dataset.parquet``, 24,153 rows, 78 experiments): one row per
experiment, treatment variant, decision metric and checkpoint, with ``experiment_id``, ``variant_id``, ``metric_id``,
``time_since_start`` (days since the experiment began), the control group's ``count_c``, ``mean_c``, ``variance_c`` and
the treatment group's ``count_t``, ``mean_t``, ``variance_t``. There is no calendar date and no experiment content.
The loader reads that parquet (or the CSV of the same columns) and takes either the file or the directory holding it.

Contrast. For each (experiment, treatment variant, metric) only the row with the largest ``time_since_start`` becomes a
ledger row. Earlier checkpoints are never admitted as outcomes: they are the daily looks the registered horizon
forbids acting on. ``y`` is the standardized effect (mean difference over the pooled standard deviation, Cohen's d) and
``s`` the large-sample standard error of that d, ``sqrt((n_t + n_c) / (n_t n_c) + d^2 / (2 (n_t + n_c)))``. The effect
in the metric's own units and its standard error, ``sqrt(v_t/n_t + v_c/n_c)``, stay in the ``post_launch`` block of
``features_json`` as ``original_effect`` and ``original_se`` (realized values, never read by a feature).

Cell and features. The cell is the metric (``metric_<id>``), because experiment content is anonymized and the kind of
change is unknown. The feature space is cell only (metric id and the number of variants). With no text there is almost
nothing for the kernel to separate rows by within a metric, so **P2 is expected to degenerate to P1 here** (the design
spec says so and the report repeats it). It does so only approximately: the variant count still separates rows, and in
the 2 Nov 2026 run P2 and P1 scored differently on ASOS. Read the report, not this expectation.

Time. The file gives offsets, not dates. Experiments are placed on a nominal calendar (builder call 45): sorted by the
sha256 of their id, spread evenly from 2019-01-01 over 730 days (the 2019 to 2020 span in the datasheet). The order is
therefore arbitrary, not real, and the backtest on this source tests prediction across an arbitrary order, not drift
over time. ``started_at`` is the nominal start, ``final_read_at`` and ``usable_after`` are the start plus the last
checkpoint offset of the experiment, and ``period`` is the quarter of the final read.

Admission. A contrast is ``admitted`` when both arms hold at least 1000 users and the effect and its standard error are
finite with ``s > 0``. Otherwise it gets ``low_exposure`` (the closest status in the ledger vocabulary) and
``features_json`` records the reason in ``exclusion_detail`` (``missing_variance`` for the 15 contrasts of five
treatments whose variance entries are absent in the file, per the datasheet).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mootcourt.ledger import LEDGER_COLUMNS, SCHEMA_VERSION, make_row_id, quarter_of, validate_ledger

SOURCE = "asos"
PARQUET_NAME = "asos_digital_experiments_dataset.parquet"
CSV_NAME = "asos_digital_experiments_dataset.csv"
COLUMNS = ("experiment_id", "variant_id", "metric_id", "time_since_start", "count_c", "count_t", "mean_c", "mean_t", "variance_c",
           "variance_t")
NOMINAL_EPOCH = pd.Timestamp("2019-01-01", tz="UTC")
NOMINAL_SPAN_DAYS = 730
MIN_USERS = 1000


def _locate(path) -> Path:
    p = Path(path)
    if p.is_dir():
        for name in (PARQUET_NAME, CSV_NAME):
            if (p / name).is_file():
                return p / name
        raise FileNotFoundError(f"no {PARQUET_NAME} or {CSV_NAME} in {p}")
    if not p.is_file():
        raise FileNotFoundError(f"ASOS file not found: {p}")
    return p


def _read(path) -> pd.DataFrame:
    p = _locate(path)
    df = pd.read_parquet(p, columns=list(COLUMNS)) if p.suffix == ".parquet" else pd.read_csv(p, usecols=list(COLUMNS), dtype={"experiment_id": str})
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{p.name} lacks the expected columns {missing}")
    df["experiment_id"] = df["experiment_id"].astype(str)
    return df


def nominal_starts(experiment_ids) -> dict[str, pd.Timestamp]:
    """Nominal start of each experiment: ids sorted by sha256, spread evenly over the nominal span (call 45)."""
    ids = sorted(set(map(str, experiment_ids)), key=lambda e: hashlib.sha256(e.encode()).hexdigest())
    n = max(len(ids), 1)
    return {e: NOMINAL_EPOCH + pd.Timedelta(days=int(k * NOMINAL_SPAN_DAYS / n)) for k, e in enumerate(ids)}


def standardized_effect(mean_c: float, mean_t: float, var_c: float, var_t: float, n_c: float, n_t: float) -> tuple[float, float]:
    """Cohen's d (treatment minus control over the pooled sd) and its large-sample standard error.

    Raises ValueError when a variance is missing or the pooled variance is not positive.
    """
    if not np.isfinite([var_c, var_t]).all() or n_c < 2 or n_t < 2:
        raise ValueError("variance and counts are needed for a standardized effect")
    pooled = ((n_t - 1) * var_t + (n_c - 1) * var_c) / (n_t + n_c - 2)
    if not pooled > 0:
        raise ValueError("pooled variance must be positive")
    d = (mean_t - mean_c) / np.sqrt(pooled)
    return float(d), float(np.sqrt((n_t + n_c) / (n_t * n_c) + d * d / (2.0 * (n_t + n_c))))


def load_asos(path) -> pd.DataFrame:
    """Build the contrast ledger from the ASOS file (or the directory holding it); see the module docstring."""
    df = _read(path)
    key = ["experiment_id", "variant_id", "metric_id"]
    n_check = df.groupby(key)["time_since_start"].transform("size")
    last = df.loc[df.groupby(key)["time_since_start"].idxmax()].copy()
    last["n_checkpoints"] = n_check.loc[last.index].to_numpy()
    exp_final = df.groupby("experiment_id")["time_since_start"].max()
    n_variants = df.groupby("experiment_id")["variant_id"].nunique() + 1       # treatments plus the control
    starts = nominal_starts(df["experiment_id"].unique())
    rows = []
    for r in last.sort_values(key, kind="stable").itertuples(index=False):
        exp, variant, metric = r.experiment_id, int(r.variant_id), int(r.metric_id)
        start = starts[exp]
        final = start + pd.Timedelta(days=float(exp_final[exp]))
        n_c, n_t = float(r.count_c), float(r.count_t)
        orig_effect = float(r.mean_t - r.mean_c)
        detail, y, s, orig_se = None, np.nan, np.nan, None
        try:
            y, s = standardized_effect(r.mean_c, r.mean_t, r.variance_c, r.variance_t, n_c, n_t)
            orig_se = float(np.sqrt(r.variance_t / n_t + r.variance_c / n_c))
        except ValueError:
            detail = "missing_variance" if not np.isfinite([r.variance_c, r.variance_t]).all() else "degenerate_variance"
        if detail is None and min(n_c, n_t) < MIN_USERS:
            detail = "low_exposure"
        if detail is None and not (np.isfinite(y) and np.isfinite(s) and s > 0):
            detail = "degenerate_variance"
        feats = {"metric_id": metric, "n_variants": int(n_variants[exp]),
                 "post_launch": {"original_effect": orig_effect, "original_se": orig_se},
                 "original_unit": "metric units (treatment mean minus control mean)", "n_checkpoints": int(r.n_checkpoints),
                 "final_offset_days": float(exp_final[exp]), "calendar": "nominal"}
        if detail:
            feats["exclusion_detail"] = detail
        rows.append({"row_id": make_row_id(SOURCE, exp, f"v{variant}_m{metric}"), "source": SOURCE, "test_id": exp,
                     "variant_id": f"v{variant}_m{metric}", "cell": f"metric_{metric}", "period": quarter_of(final), "started_at": start,
                     "final_read_at": final, "usable_after": final, "y": y, "s": s, "n_ref": int(n_c), "n_var": int(n_t),
                     "status": "low_exposure" if detail else "admitted", "features_json": json.dumps(feats, sort_keys=True),
                     "schema_version": SCHEMA_VERSION})
    out = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    for c in ("y", "s"):
        out[c] = out[c].astype("float64")
    for c in ("n_ref", "n_var", "schema_version"):
        out[c] = out[c].astype("int64")
    for c in ("started_at", "final_read_at", "usable_after"):
        out[c] = pd.to_datetime(out[c], utc=True)
    validate_ledger(out)
    return out


def inventory(ledger: pd.DataFrame) -> dict:
    """Counts of experiments, contrasts and statuses, for DATA.md."""
    return {"experiments": int(ledger["test_id"].nunique()), "contrasts": int(len(ledger)),
            "treatments": int(ledger.assign(t=ledger["test_id"] + ledger["variant_id"].str.split("_m").str[0])["t"].nunique()),
            "by_status": {k: int(v) for k, v in ledger["status"].value_counts().sort_index().items()},
            "by_cell_admitted": {k: int(v) for k, v in ledger.loc[ledger["status"] == "admitted", "cell"].value_counts().sort_index().items()}}
