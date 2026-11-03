"""Second opinion at weight zero.

``p_stack = (1 - w) p_sig + w p_AI``. A provider has one method, ``p_ai(row)``, returning a probability
in [0, 1] or None. The default ``NullProvider`` returns None and the weight is 0. ``earn_weight`` chooses
``w`` on a grid by Brier score on the origins before an inner cut and judges it on the origins from the cut on:
it writes ``w > 0`` only when the stacked Brier beats the plain ``p_sig`` Brier on the later rows by at least
``margin`` (a Brier skill gain, relative to the constant base rate) with at least ``n_gate`` later rows that
carry an opinion. The weight is never chosen and judged on the same rows. Otherwise the weight stays 0 and the
message says why.

Probabilities are unitless. ``scored_rows`` must already be out of origin: ``p_sig`` was issued before
the outcome ``event`` (significant and positive) was known. No code in this module calls an LLM or the
network; a real provider is supplied by the caller.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

WEIGHT_GRID = tuple(round(0.05 * i, 2) for i in range(21))


class SecondOpinionProvider(Protocol):
    """Anything with ``p_ai(row)`` returning a probability or None."""

    def p_ai(self, row) -> float | None:  # pragma: no cover - protocol
        """Probability that the outcome is significant and positive, or None when there is no opinion."""
        ...


class NullProvider:
    """The default provider: no opinion, so the stacking weight stays 0."""

    def p_ai(self, row) -> float | None:
        """Always None."""
        return None


def stack(p_sig: float, p_ai: float | None, w: float) -> float:
    """``(1 - w) p_sig + w p_ai``; returns ``p_sig`` unchanged when ``p_ai`` is None or ``w`` is 0."""
    if not 0.0 <= w <= 1.0:
        raise ValueError("w must be in [0, 1]")
    if p_ai is None or w == 0.0:
        return p_sig
    return (1.0 - w) * p_sig + w * p_ai


@dataclass(frozen=True)
class EarnResult:
    """Outcome of ``earn_weight``.

    ``n`` counts the judged rows that carry an opinion, ``n_tests`` the distinct tests among them (the number the
    gate compares, call 83: rows of one test are not independent), ``n_chosen`` the rows the weight was chosen on, and
    ``cut`` is the first origin of the judged rows. The Brier scores are the judged rows' own.
    """

    weight: float
    message: str
    n: int
    brier_base: float | None = None
    brier_stacked: float | None = None
    n_chosen: int = 0
    cut: str | None = None
    n_tests: int = 0


def _split_in_time(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, str | None]:
    """Boolean masks ``(chosen, judged)`` over ``rows`` (already limited to rows with an opinion) and the cut label.

    With an ``origin`` column the cut falls between origins, at the first origin where at least half of the rows
    lie before it. Without one the rows are taken as time ordered and split at the middle. Fewer than two origins,
    or fewer than two rows, cannot be split: both masks are empty.
    """
    n = len(rows)
    none = np.zeros(n, bool)
    if n < 2:
        return none, none, None
    if "origin" not in rows.columns:
        k = n // 2
        idx = np.arange(n)
        return idx < k, idx >= k, f"row {k + 1}"
    origin = pd.to_datetime(rows["origin"], utc=True)
    uniq = np.sort(origin.unique())
    if len(uniq) < 2:
        return none, none, None
    counts = np.array([(origin <= u).sum() for u in uniq])
    k = int(np.argmax(counts >= n / 2.0))                   # last origin that still belongs to the chosen part
    if k >= len(uniq) - 1:
        k = len(uniq) - 2
    cut = uniq[k + 1]
    chosen = (origin < cut).to_numpy()
    return chosen, ~chosen, pd.Timestamp(cut).isoformat()


def earn_weight(provider: SecondOpinionProvider, scored_rows: pd.DataFrame, n_gate: int, margin: float) -> EarnResult:
    """Choose ``w`` on the early origins and judge it on the later ones; keep 0 unless the gate and the margin are both met.

    ``scored_rows`` has ``p_sig`` and boolean ``event`` and, for a real run, ``origin``. The rows on which the
    provider gave an opinion are split in time at an inner cut. ``w`` is the grid value with the best Brier score
    before the cut. It is kept only when, from the cut on, the stacked Brier beats plain ``p_sig`` by at least
    ``margin`` (the Brier improvement divided by the Brier score of the constant base rate of those later rows,
    the same units as the promotion margin) and the later rows with an opinion come from at least ``n_gate`` distinct
    tests (``test_id``; a frame without that column counts every row as its own test). The weight is never
    chosen and judged on the same rows, so the gain is not inflated by the search.
    """
    opinions = [provider.p_ai(row) for _, row in scored_rows.iterrows()]
    n_all = len(scored_rows)
    have = np.array([o is not None for o in opinions], dtype=bool)
    if int(have.sum()) == 0:
        return EarnResult(0.0, "the provider gave no opinion; weight stays 0", n_all)
    rows = scored_rows[have].reset_index(drop=True)
    ai_all = np.array([o for o in opinions if o is not None], dtype=float)
    chosen, judged, cut = _split_in_time(rows)
    if cut is None:
        return EarnResult(0.0, "the rows with an opinion come from fewer than two origins, so the weight cannot be chosen on earlier "
                               "origins and judged on later ones; weight stays 0", int(have.sum()))
    n_j, n_c = int(judged.sum()), int(chosen.sum())
    n_t = int(rows.loc[judged, "test_id"].nunique()) if "test_id" in rows.columns else n_j
    if n_t < n_gate:
        return EarnResult(0.0, f"{n_j} judged rows with an opinion from {n_t} tests is below the gate of {n_gate} tests; weight stays 0",
                          n_j, n_chosen=n_c, cut=cut, n_tests=n_t)
    p, e = rows["p_sig"].to_numpy(float), rows["event"].to_numpy(float)
    best_w, best_c = 0.0, float(np.mean((p[chosen] - e[chosen]) ** 2))
    for w in WEIGHT_GRID:
        b = float(np.mean(((1.0 - w) * p[chosen] + w * ai_all[chosen] - e[chosen]) ** 2))
        if b < best_c - 1e-15:
            best_w, best_c = w, b
    pj, ej, aj = p[judged], e[judged], ai_all[judged]
    base = float(np.mean((pj - ej) ** 2))
    stacked = float(np.mean(((1.0 - best_w) * pj + best_w * aj - ej) ** 2))
    ref = float(np.mean(ej) * (1.0 - np.mean(ej)))              # Brier score of the constant base rate on the judged rows
    where = f"chosen on origins before {cut} ({n_c} rows), judged on {cut} onwards ({n_j} rows, {n_t} tests)"
    if best_w > 0.0 and ref > 0.0 and (base - stacked) / ref >= margin:
        return EarnResult(float(best_w), f"weight {best_w} earned, {where}: Brier {stacked:.4f} against {base:.4f}", n_j, base, stacked, n_c, cut,
                          n_t)
    return EarnResult(0.0, f"the stacked Brier {stacked:.4f} at weight {best_w} does not beat {base:.4f} by a skill margin of {margin}, "
                           f"{where}; weight stays 0", n_j, base, stacked, n_c, cut, n_t)


def load_weight(path) -> float:
    """Read the stacking weight from a JSON file; a missing file means 0."""
    path = Path(path)
    if not path.exists():
        return 0.0
    w = float(json.loads(path.read_text(encoding="utf-8"))["weight"])
    if not 0.0 <= w <= 1.0:
        raise ValueError("stored weight is outside [0, 1]")
    return w


def save_weight(path, weight: float) -> None:
    """Write the stacking weight to a JSON file atomically."""
    if not 0.0 <= weight <= 1.0:
        raise ValueError("weight must be in [0, 1]")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"weight": weight}, fh)
    os.replace(tmp, path)
