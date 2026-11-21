"""Units, arms and contrasts of the headline-only cell, read from the ledger and a run's saved row scores.

A unit is a pair of test and origin. An arm is a distinct headline within a unit, because a card shows a headline and
nothing else: contrasts whose variants carry the same headline share one arm, and that arm's clicks and impressions
are summed over them.
"""
from __future__ import annotations

import json

import pandas as pd

from mootcourt.simulators.readers.protocol import CELL, Z

_REFERENCE_RUNG = "always_reference"
_TEXT_RUNG = "text_lr"


def _features(value) -> dict:
    return value if isinstance(value, dict) else json.loads(value)


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def load_units(ledger: pd.DataFrame, scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(arms, contrasts)`` for the headline-only cell. See the module text for what a unit and an arm are."""
    cell = scores[scores["cell"] == CELL]
    ref = cell[cell["rung"] == _REFERENCE_RUNG]
    text = cell[cell["rung"] == _TEXT_RUNG].set_index("row_id")["direction_correct"]
    if ref["row_id"].duplicated().any() or text.index.duplicated().any():
        raise ValueError("a scored row appears twice in one rung")

    led = ledger.drop_duplicates("row_id").set_index("row_id")
    absent = sorted(set(ref["row_id"]) - set(led.index))
    if absent:
        raise ValueError(f"{len(absent)} scored rows are absent from the ledger, the first being {absent[0]}")

    rows = ref[["row_id", "test_id", "origin", "y", "s", "direction_correct", "dir_ceiling_row", "s_star"]].copy()
    rows = rows.rename(columns={"direction_correct": "ref_correct"})
    rows["origin"] = _utc(rows["origin"])
    rows["text_lr_correct"] = rows["row_id"].map(text)
    if rows["text_lr_correct"].isna().any():
        raise ValueError("a scored row has no saved direction of the text classifier")
    origins = sorted(rows["origin"].unique())
    rows["origin_index"] = rows["origin"].map({o: i for i, o in enumerate(origins)}).astype(int)
    rows["unit_id"] = rows["test_id"].astype(str) + "@" + rows["origin"].dt.strftime("%Y-%m-%d")

    on = led.loc[rows["row_id"]]
    feats = [_features(v) for v in on["features_json"]]
    rows["headline"] = [f["headline"] for f in feats]
    rows["reference_headline"] = [f["reference_headline"] for f in feats]
    rows["clicks_ref"] = [f["post_launch"]["clicks_ref"] for f in feats]
    rows["clicks_var"] = [f["post_launch"]["clicks_var"] for f in feats]
    rows["n_ref"] = on["n_ref"].to_numpy()
    rows["n_var"] = on["n_var"].to_numpy()
    rows["usable_after"] = _utc(on["usable_after"]).to_numpy()
    rows["usable_after"] = _utc(rows["usable_after"])

    arm_rows, arm_of_row, ref_of_row = [], {}, {}
    for unit_id, g in rows.sort_values("row_id").groupby("unit_id", sort=True):
        if g["reference_headline"].nunique() != 1:
            raise ValueError(f"unit {unit_id} has {g['reference_headline'].nunique()} reference headlines")
        if g["clicks_ref"].nunique() != 1 or g["n_ref"].nunique() != 1:
            raise ValueError(f"unit {unit_id} has reference counts that differ between its rows")
        first = g.iloc[0]
        common = {"unit_id": unit_id, "test_id": first["test_id"], "origin": first["origin"],
                  "origin_index": int(first["origin_index"]), "usable_after": g["usable_after"].max()}
        arm_rows.append({**common, "arm_id": f"{unit_id}#0", "headline": first["reference_headline"], "is_reference": True,
                         "clicks": first["clicks_ref"], "impressions": first["n_ref"]})
        k = 0
        for headline, v in g.groupby("headline", sort=False):          # g is in row_id order, so this is first row_id order
            if headline == first["reference_headline"]:
                raise ValueError(f"a variant headline of unit {unit_id} equals its reference")
            k += 1
            arm_rows.append({**common, "arm_id": f"{unit_id}#{k}", "headline": headline, "is_reference": False,
                             "clicks": v["clicks_var"].sum(), "impressions": v["n_var"].sum()})
            for row_id in v["row_id"]:
                arm_of_row[row_id] = f"{unit_id}#{k}"
                ref_of_row[row_id] = f"{unit_id}#0"

    arms = pd.DataFrame(arm_rows)[["unit_id", "test_id", "origin", "origin_index", "arm_id", "headline", "is_reference",
                                   "clicks", "impressions", "usable_after"]]
    rows["arm_id"] = rows["row_id"].map(arm_of_row)
    rows["ref_arm_id"] = rows["row_id"].map(ref_of_row)
    rows["decisive"] = rows["y"].abs() > Z * rows["s"]
    contrasts = rows[["row_id", "unit_id", "test_id", "origin", "origin_index", "arm_id", "ref_arm_id", "y", "s", "decisive",
                      "usable_after", "ref_correct", "text_lr_correct", "dir_ceiling_row", "s_star"]]
    return arms.reset_index(drop=True), contrasts.sort_values(["origin_index", "row_id"]).reset_index(drop=True)
