"""A second text classifier for the third reading: logistic regression on headline embeddings.

It is fitted as the text classifier of the main run is fitted, at each origin on the admitted rows of the source that
are visible at the origin, every cell. Its design is the difference of the two headlines' embeddings, the variant's own
embedding and one column per cell. A row without a reference headline has a zero vector in its place, as the word-count
design has. With a panel one more column is added: the panel difference divided by ten for a row that has one, and zero
for any other row, as in method 5. The embeddings are computed once, elsewhere, and arrive here as a table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mootcourt.features import _parse_rows, parse_references
from mootcourt.ledger import ADMITTED, visible_rows
from mootcourt.simulators.readers.textfeature import SCALE

C = 1.0          # the library's default, not tuned
MAX_ITER = 2000


def headlines_of(ledger: pd.DataFrame, contrasts: pd.DataFrame) -> list[str]:
    """Every headline and reference headline of the admitted rows of the contrasts' source, each once, sorted."""
    rows = _admitted(ledger, contrasts)
    return sorted({text for text in _parse_rows(rows)[0] + parse_references(rows) if text.strip()})


def _admitted(ledger: pd.DataFrame, contrasts: pd.DataFrame) -> pd.DataFrame:
    admitted = ledger[ledger["status"] == ADMITTED]
    if "source" in ledger.columns:
        by_row = ledger.drop_duplicates("row_id").set_index("row_id")
        admitted = admitted[admitted["source"].isin(set(by_row.loc[contrasts["row_id"], "source"]))]
    return admitted


def unit_vectors(texts: list[str], vectors) -> dict[str, np.ndarray]:
    """A table from text to its embedding at unit length."""
    table = {}
    for text, vector in zip(texts, vectors):
        v = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(v))
        table[text] = v / norm if norm > 0 else v
    return table


def _design(rows: pd.DataFrame, table: dict, cells: tuple, feature: dict | None) -> np.ndarray:
    heads, refs = _parse_rows(rows)[0], parse_references(rows)
    missing = sorted({t for t in heads + refs if t.strip() and t not in table})
    if missing:
        raise ValueError(f"{len(missing)} headlines have no embedding, the first being {missing[0]!r}")
    width = len(next(iter(table.values())))
    zero = np.zeros(width, dtype=np.float32)
    own = np.stack([table.get(h, zero) for h in heads])
    ref = np.stack([table.get(r, zero) for r in refs])
    onehot = (np.asarray(rows["cell"], dtype=object)[:, None] == np.asarray(cells, dtype=object)[None, :]).astype(np.float32)
    parts = [own - ref, own, onehot]
    if feature is not None:
        parts.append(np.array([feature.get(row_id, 0.0) for row_id in rows["row_id"]], dtype=np.float32)[:, None])
    return np.hstack(parts)


def embedding_directions(ledger: pd.DataFrame, contrasts: pd.DataFrame, table: dict, panel_diff: pd.Series | None = None,
                         seed: int = 0) -> pd.DataFrame:
    """Per contrast, in the order given: ``p`` (probability that the variant wins) and whether the direction is right.

    A direction is right when ``p > 0.5`` and the variant won or ``p <= 0.5`` and it lost, the rule of the text classifier.
    """
    from sklearn.linear_model import LogisticRegression

    contrasts = contrasts.reset_index(drop=True)
    by_row = ledger.drop_duplicates("row_id").set_index("row_id", drop=False)
    admitted = _admitted(ledger, contrasts)
    feature = None if panel_diff is None else {row_id: float(v) / SCALE for row_id, v in panel_diff.items() if np.isfinite(v)}
    p = np.full(len(contrasts), np.nan)
    for origin, group in contrasts.groupby("origin", sort=True):
        visible = visible_rows(admitted, origin)
        cells = tuple(sorted(visible["cell"].unique()))
        label = visible["y"].to_numpy(dtype=float) > 0
        scored = by_row.loc[group["row_id"]].reset_index(drop=True)
        if label.all() or not label.any():
            p[group.index] = float(label.mean())
            continue
        model = LogisticRegression(C=C, max_iter=MAX_ITER, random_state=seed).fit(_design(visible, table, cells, feature), label)
        p[group.index] = model.predict_proba(_design(scored, table, cells, feature))[:, 1]
    won = contrasts["y"].to_numpy(dtype=float) > 0
    return pd.DataFrame({"row_id": contrasts["row_id"].to_numpy(), "p": p, "correct": ((p > 0.5) == won).astype(float)})
