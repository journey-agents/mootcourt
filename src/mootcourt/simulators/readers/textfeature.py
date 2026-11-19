"""Method 5: the panel difference as one more feature of the package's text classifier.

At each origin the classifier is fitted as the main run fits it: on the admitted rows of the source that are visible at
the origin, every cell. "Without" is ``mootcourt.harness.TextLR`` itself. "With" is a subclass that adds one column to
the design: the panel difference divided by 10 for a row that has one, and zero for any other row. A training row has
a panel difference only if it was a scored headline-only row of an earlier origin; a scored row has its own. The
harness is not edited, and the panel difference is no outcome: it is what the readers said about two headlines.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse

from mootcourt.harness import TextLR
from mootcourt.ledger import ADMITTED, visible_rows

SCALE = 10.0


class TextLRWithPanel(TextLR):
    """The text classifier with one more column, looked up by ``row_id``. A row with no value gets zero."""

    def __init__(self, rows: pd.DataFrame, feature: dict, seed: int = 0, pairwise: bool | None = None):
        self._feature = feature
        self._column = self._lookup(rows)
        super().__init__(rows, seed=seed, pairwise=pairwise)

    def _lookup(self, rows: pd.DataFrame) -> np.ndarray:
        return np.array([self._feature.get(row_id, 0.0) for row_id in rows["row_id"]], dtype=np.float64)

    def _design(self, heads, refs, cells):
        return sparse.hstack([super()._design(heads, refs, cells), sparse.csr_matrix(self._column[:, None])], format="csr")

    def _scored_design(self, scored: pd.DataFrame):
        self._column = self._lookup(scored)
        return super()._scored_design(scored)


def text_with_panel(ledger: pd.DataFrame, contrasts: pd.DataFrame, panel_diff: pd.Series, pairwise: bool | None = None) -> pd.DataFrame:
    """Per contrast, in the order given: ``p_without``, ``p_with`` (probability that the variant wins) and whether each is right.

    ``panel_diff`` is indexed by ``row_id``. A direction is right when ``p > 0.5`` and the variant won or ``p <= 0.5`` and
    it lost, which is the rule of the main run's text rung.
    """
    contrasts = contrasts.reset_index(drop=True)
    by_row = ledger.drop_duplicates("row_id").set_index("row_id", drop=False)
    absent = sorted(set(contrasts["row_id"]) - set(by_row.index))
    if absent:
        raise ValueError(f"{len(absent)} contrasts are absent from the ledger, the first being {absent[0]}")
    admitted = ledger[ledger["status"] == ADMITTED]
    if "source" in ledger.columns:
        admitted = admitted[admitted["source"].isin(set(by_row.loc[contrasts["row_id"], "source"]))]
    feature = {row_id: float(v) / SCALE for row_id, v in panel_diff.items() if np.isfinite(v)}

    p_without, p_with = np.full(len(contrasts), np.nan), np.full(len(contrasts), np.nan)
    for origin, group in contrasts.groupby("origin", sort=True):
        visible = visible_rows(admitted, origin)
        scored = by_row.loc[group["row_id"]].reset_index(drop=True)
        y = scored["y"].to_numpy(dtype=float)
        for target, model in ((p_without, TextLR(visible, pairwise=pairwise)),
                              (p_with, TextLRWithPanel(visible, feature, pairwise=pairwise))):
            target[group.index] = model.score_block(scored, y, None, origin)[0]["p_gt0"]
    won = contrasts["y"].to_numpy(dtype=float) > 0
    return pd.DataFrame({"row_id": contrasts["row_id"].to_numpy(), "correct_without": ((p_without > 0.5) == won).astype(float),
                         "correct_with": ((p_with > 0.5) == won).astype(float), "p_without": p_without, "p_with": p_with})
