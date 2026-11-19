"""The panel score of an arm and the direction of a contrast.

Each reader's probabilities are centred on the mean of their call, so a reader's general level in one feed does not
enter. An arm read more than once is averaged over its repeats. A reader with any missing call in a block is left out
of that whole block, so every arm of a unit is averaged over the same readers. The direction of a contrast is the
sign of the variant's panel score minus the reference's; an exact tie counts as half.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from mootcourt.simulators.readers.protocol import HALVES, N_READERS

_ANSWER_COLUMNS = ["block_id", "feed_index", "reader", "position", "prob"]


def answers_frame(records: Iterable[dict]) -> pd.DataFrame:
    """One row per card of every stored reader call. Every position of a call whose status is not ``"ok"`` is NaN."""
    rows = []
    for record in records:
        meta = record["meta"]
        ok = record["status"] == "ok"
        n = len(record["parsed"]) if ok else record["request"]["schema"]["properties"]["clicks"]["minItems"]
        for position in range(1, n + 1):
            rows.append((meta["block_id"], int(meta["feed_index"]), int(meta["reader"]), position,
                         float(record["parsed"][position - 1]) if ok else np.nan))
    return pd.DataFrame(rows, columns=_ANSWER_COLUMNS)


def reader_scores(feeds: pd.DataFrame, answers: pd.DataFrame) -> pd.DataFrame:
    """One row per ``arm_id`` and ``reader`` with ``centred`` and ``raw``, for the readers who answered their whole block."""
    cards = feeds[["block_id", "feed_index", "position", "arm_id"]]
    readers = pd.DataFrame({"reader": sorted(answers["reader"].unique())})
    full = cards.merge(readers, how="cross").merge(answers, on=["block_id", "feed_index", "reader", "position"], how="left")
    whole = ~full["prob"].isna().groupby([full["block_id"], full["reader"]]).transform("any")
    kept = full[whole].copy()
    kept["centred"] = kept["prob"] - kept.groupby(["block_id", "feed_index", "reader"])["prob"].transform("mean")
    out = kept.groupby(["arm_id", "reader"], as_index=False).agg(centred=("centred", "mean"), raw=("prob", "mean"))
    return out[["arm_id", "reader", "centred", "raw"]]


def panel_scores(reader_scores: pd.DataFrame, weights: np.ndarray | None = None, readers: tuple[int, ...] | None = None) -> pd.Series:
    """The mean of ``centred`` per arm, or the weighted mean with the weights renormalised over the readers present.

    ``weights`` holds one weight per reader, reader 1 first. An arm whose present readers have no weight has no score.
    """
    rs = reader_scores if readers is None else reader_scores[reader_scores["reader"].isin(readers)]
    if weights is None:
        return rs.groupby("arm_id")["centred"].mean().rename("score")
    w = np.asarray(weights, dtype=float)
    if w.shape != (N_READERS,):
        raise ValueError(f"expected {N_READERS} weights, got {w.shape}")
    weight = pd.Series(w[rs["reader"].to_numpy() - 1], index=rs.index)
    total = weight.groupby(rs["arm_id"]).sum()
    score = (weight * rs["centred"]).groupby(rs["arm_id"]).sum() / total.where(total > 0)
    return score.dropna().rename("score")


def directions(contrasts: pd.DataFrame, arm_score: pd.Series) -> pd.DataFrame:
    """Per contrast: ``diff`` (variant minus reference), ``correct`` (1, 0, or 0.5 for a tie or for no reader), ``tie``, ``no_reader``."""
    diff = (contrasts["arm_id"].map(arm_score) - contrasts["ref_arm_id"].map(arm_score)).astype(float).to_numpy()
    return direction_frame(contrasts, diff)


def direction_frame(contrasts: pd.DataFrame, diff: np.ndarray) -> pd.DataFrame:
    """The same frame as ``directions`` from a difference that is already per contrast."""
    diff = np.asarray(diff, dtype=float)
    y = contrasts["y"].to_numpy(dtype=float)
    no_reader = np.isnan(diff)
    tie = diff == 0
    correct = np.where(no_reader | tie, 0.5, (np.sign(np.nan_to_num(diff)) == np.sign(y)).astype(float))
    return pd.DataFrame({"row_id": contrasts["row_id"].to_numpy(), "diff": diff, "correct": correct, "tie": tie,
                         "no_reader": no_reader})


def split_half_agreement(contrasts: pd.DataFrame, reader_scores: pd.DataFrame) -> dict:
    """The share of contrasts on which the two halves of the panel give the same nonzero sign. It reads no outcome."""
    halves = []
    for half in HALVES:
        score = panel_scores(reader_scores, readers=half)
        halves.append((contrasts["arm_id"].map(score) - contrasts["ref_arm_id"].map(score)).to_numpy(dtype=float))
    both = ~np.isnan(halves[0]) & ~np.isnan(halves[1])
    agree = both & (np.sign(halves[0]) == np.sign(halves[1])) & (halves[0] != 0)
    n = int(both.sum())
    return {"agree_share": float(agree.sum() / n) if n else float("nan"), "n": n}
