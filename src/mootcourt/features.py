"""Features, kernel and retrieval index.

A ``FeatureSpace`` maps a ledger row (or a bare headline) to a standardized vector: TF-IDF (1 to 2
grams, ``min_df`` 3) on the headline reduced by TruncatedSVD to at most 64 dimensions, concatenated
with the named structured features and the log of the planned exposures per arm, then z-scored per column using
statistics from the fit set. Only the pre-launch allow-list of ``mootcourt.scale`` is read from a row's features;
a post-launch field among them raises ``PostLaunchFieldError``.

Kernel: ``k(x, x_i) = exp(-d^2 / (2 h^2))`` with ``d`` the Euclidean distance on standardized
features and ``h`` the median pairwise distance of the fit set (median heuristic).

Memory rules. No function here forms an n by n matrix. Dense work is done in chunks of rows, and a
query keeps only the top ``m`` weights (default 1000). Units: features are unitless; the kernel and
the densities are unitless. Origin semantics live in the ledger: callers pass only rows visible at
the origin (status admitted and usable_after <= origin) when they fit a space or build an index.

The index is rebuilt at every fit and never updated incrementally.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from mootcourt.config import NOVELTY_PERCENTILE, SVD_DIMS, TOP_M_NEIGHBORS
from mootcourt.scale import planned_exposure, prelaunch_view

log = logging.getLogger(__name__)

STRUCTURED_FEATURES = [
    "n_words", "has_question", "has_number", "has_quote", "starts_pronoun", "image_changed",
    "has_exclaim", "n_chars",
]
EXPOSURE_FEATURES = ["log_exposure"]          # natural log of the planned exposures per arm, appended after the structured ones
_PRONOUNS = frozenset(
    "i me my mine we us our ours you your yours he him his she her hers it its they them their theirs "
    "this that these those who".split()
)
_NUMBER = re.compile(r"\d")
_QUOTES = ('"', "“", "”")
_WORD = re.compile(r"[A-Za-z']+")
_RANDOM_STATE = 0
_BANDWIDTH_SAMPLE = 2000
_STD_FLOOR = 1e-12
FEATURE_SETS = ("text", "structured", "both")


def has_text(rows: pd.DataFrame) -> bool:
    """True when at least one row carries a non-empty ``headline`` in its pre-launch features.

    Ledgers imported from experiment platforms usually carry none; their space is then the cell one-hot (``cell_only``).
    """
    for js in rows["features_json"]:
        try:
            if str((json.loads(js) or {}).get("headline", "")).strip():
                return True
        except (ValueError, TypeError):
            continue
    return False


def use_cell_only(source: str, rows: pd.DataFrame | None) -> bool:
    """Whether the source's features are the cell one-hot only: ASOS always, any other source when no row has headline text."""
    if source == "asos":
        return True
    return rows is not None and len(rows) > 0 and source not in ("upworthy", "synthetic") and not has_text(rows)


def structured_features(headline: str, image_changed: bool = False) -> np.ndarray:
    """Unitless structured features of one headline, ordered as ``STRUCTURED_FEATURES``.

    Counts and 0/1 flags: word count, question mark, a digit, a double quote, first word is a
    pronoun, the image changed, an exclamation mark, character count.
    """
    text = headline or ""
    words = text.split()
    first = _WORD.findall(words[0].lower()) if words else []
    return np.array(
        [
            len(words),
            1.0 if "?" in text else 0.0,
            1.0 if _NUMBER.search(text) else 0.0,
            1.0 if any(q in text for q in _QUOTES) else 0.0,
            1.0 if first and first[0] in _PRONOUNS else 0.0,
            1.0 if image_changed else 0.0,
            1.0 if "!" in text else 0.0,
            float(len(text)),
        ],
        dtype=np.float64,
    )


def _parse_rows(rows: pd.DataFrame) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """Headlines, image-changed flags, variant counts and log planned exposures of ledger rows.

    Reads the pre-launch allow-list only (``scale.prelaunch_view``); a post-launch field raises.
    """
    heads, imgs, nvar = [], [], []
    for j in rows["features_json"]:
        f = prelaunch_view(json.loads(j))
        heads.append(str(f.get("headline", "")))
        imgs.append(bool(f.get("image_changed", False)))
        nvar.append(float(f.get("n_variants", 2)))
    logexp = np.log(np.maximum(planned_exposure(rows), 1.0))
    return heads, np.array(imgs, dtype=bool), np.array(nvar), logexp


@dataclass
class FeatureSpace:
    """Fitted feature map. Build with ``FeatureSpace.fit``; ``transform`` is pure."""

    vectorizer: Any
    svd: Any
    mean: np.ndarray
    std: np.ndarray
    svd_dims: int
    cell_only: bool = False
    cells: tuple[str, ...] = ()
    min_df: int = 3
    backend: str = "tfidf"
    feature_set: str = "both"

    @property
    def dim(self) -> int:
        """Number of output columns."""
        return int(self._columns().size)

    def _columns(self) -> np.ndarray:
        """Indices of the columns this space outputs: the text part, the structured part, or both (an ablation switch)."""
        n = int(self.mean.shape[0])
        if self.cell_only or self.feature_set == "both":
            return np.arange(n)
        return np.arange(self.svd_dims) if self.feature_set == "text" else np.arange(self.svd_dims, n)

    # ------------------------------------------------------------------ fit
    @classmethod
    def fit(
        cls,
        rows: pd.DataFrame,
        min_df: int = 3,
        svd_dims: int = SVD_DIMS,
        cell_only: bool = False,
        backend: str = "tfidf",
        feature_set: str = "both",
    ) -> FeatureSpace:
        """Fit on the given rows (the caller passes only rows visible at the origin).

        ``svd_dims`` is capped at vocabulary size minus 1 and at rows minus 1; a cap is logged.
        With ``cell_only`` the space is the cell one-hot plus the variant count (metric id and number
        of variants), the degenerate space used for sources without text. Fitting is deterministic.
        """
        if feature_set not in FEATURE_SETS:
            raise ValueError(f"feature_set must be one of {FEATURE_SETS}")
        if backend != "tfidf":
            raise RuntimeError(
                "the sentence-embedding backend is optional and off by default: install the 'embeddings' extra "
                "and pass --embeddings; no model is downloaded in the default path"
            )
        if cell_only:
            cells = tuple(sorted(rows["cell"].unique()))
            _, _, nvar, _ = _parse_rows(rows)
            raw = cls._cell_matrix(rows["cell"].tolist(), nvar, cells)
            mean, std = raw.mean(0), raw.std(0)
            std = np.where(std < _STD_FLOOR, 1.0, std)
            return cls(None, None, mean, std, 0, True, cells, min_df, backend, feature_set)
        heads, imgs, _, logexp = _parse_rows(rows)
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=min_df, dtype=np.float64)
        tfidf = vec.fit_transform(heads)
        vocab = len(vec.vocabulary_)
        cap = min(svd_dims, vocab - 1, len(heads) - 1)
        if cap < 1:
            raise ValueError("not enough text to fit a feature space")
        if cap < svd_dims:
            log.info("svd dims cap: requested %d, using %d (vocabulary %d, rows %d)", svd_dims, cap, vocab, len(heads))
        svd = TruncatedSVD(n_components=cap, random_state=_RANDOM_STATE)
        reduced = svd.fit_transform(tfidf)
        raw = np.hstack([reduced, cls._structured_matrix(heads, imgs, logexp)])
        mean, std = raw.mean(0), raw.std(0)
        std = np.where(std < _STD_FLOOR, 1.0, std)
        return cls(vec, svd, mean, std, cap, False, (), min_df, backend, feature_set)

    @staticmethod
    def _structured_matrix(heads, imgs, logexp) -> np.ndarray:
        base = np.array([structured_features(h, bool(i)) for h, i in zip(heads, imgs)]).reshape(len(heads), -1)
        return np.hstack([base, np.asarray(logexp, dtype=np.float64).reshape(-1, 1)])

    @staticmethod
    def _cell_matrix(cell_values, nvar, cells) -> np.ndarray:
        onehot = np.array([[1.0 if c == k else 0.0 for k in cells] for c in cell_values]).reshape(len(cell_values), -1)
        return np.hstack([onehot, np.asarray(nvar, dtype=np.float64).reshape(-1, 1)])

    # ------------------------------------------------------------ transform
    def transform(self, rows: pd.DataFrame) -> np.ndarray:
        """Standardized feature matrix for ledger rows, shape ``(len(rows), dim)``."""
        heads, imgs, nvar, logexp = _parse_rows(rows)
        if self.cell_only:
            raw = self._cell_matrix(rows["cell"].tolist(), nvar, self.cells)
            return (raw - self.mean) / self.std
        return self._transform(heads, imgs, logexp)

    def transform_text(self, headlines, image_changed=False, cell: str | None = None, n_variants: float = 2.0,
                       exposure=None) -> np.ndarray:
        """Standardized features for bare headlines (unseen and out-of-vocabulary text is fine).

        ``image_changed`` is one flag or one per headline. ``cell`` and ``n_variants`` are used only
        by a cell-only space. ``exposure`` is the planned exposures per arm (one value or one per headline);
        left out, the fit-set average of the log exposure is used, which standardizes to zero.
        """
        heads = [str(h) for h in headlines]
        imgs = np.broadcast_to(np.asarray(image_changed, dtype=bool), (len(heads),))
        if self.cell_only:
            raw = self._cell_matrix([cell] * len(heads), np.full(len(heads), n_variants), self.cells)
            return (raw - self.mean) / self.std
        if exposure is None:
            logexp = np.full(len(heads), self.mean[-1])
        else:
            expo = np.broadcast_to(np.asarray(exposure, dtype=np.float64), (len(heads),))
            if np.any(expo <= 0):
                raise ValueError("planned exposures must be positive")
            logexp = np.log(expo)
        return self._transform(heads, imgs, logexp)

    def _transform(self, heads, imgs, logexp) -> np.ndarray:
        reduced = self.svd.transform(self.vectorizer.transform(heads))
        raw = np.hstack([reduced, self._structured_matrix(heads, imgs, logexp)])
        full = (raw - self.mean) / self.std
        return full if self.feature_set == "both" else full[:, self._columns()]

    # ---------------------------------------------------------------- state
    def to_state(self) -> dict[str, Any]:
        """Split into ``arrays`` (for npz), ``meta`` (JSON) and ``objects`` (sklearn, for joblib)."""
        return {
            "arrays": {"mean": self.mean, "std": self.std},
            "meta": {
                "svd_dims": self.svd_dims, "cell_only": self.cell_only, "cells": list(self.cells),
                "min_df": self.min_df, "backend": self.backend, "feature_set": self.feature_set,
            },
            "objects": {"vectorizer": self.vectorizer, "svd": self.svd},
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> FeatureSpace:
        """Inverse of ``to_state``."""
        m = state["meta"]
        return cls(
            state["objects"]["vectorizer"], state["objects"]["svd"], np.asarray(state["arrays"]["mean"]),
            np.asarray(state["arrays"]["std"]), int(m["svd_dims"]), bool(m["cell_only"]), tuple(m["cells"]),
            int(m["min_df"]), str(m["backend"]), str(m.get("feature_set", "both")),
        )


def feature_hash(space: FeatureSpace) -> str:
    """12 hex characters identifying the feature definition.

    Depends on the vocabulary, the SVD dimension count, the structured feature list, the n-gram
    range, ``min_df`` and the cell-only flag. It is a function of those values only, so it is stable
    across processes; it does not hash floating point arrays.
    """
    vocab = sorted(space.vectorizer.vocabulary_) if space.vectorizer is not None else []
    payload = {
        "vocab": vocab, "svd_dims": space.svd_dims, "structured": STRUCTURED_FEATURES + EXPOSURE_FEATURES, "ngram": [1, 2],
        "min_df": space.min_df, "cell_only": space.cell_only, "cells": list(space.cells), "backend": space.backend,
    }
    if space.feature_set != "both":                    # the default keeps the hash of every earlier model
        payload["feature_set"] = space.feature_set
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]


# ------------------------------------------------------------------ kernel
def sq_dists(x: np.ndarray, X: np.ndarray, sq: np.ndarray | None = None) -> np.ndarray:
    """Squared Euclidean distances from one vector to every row, clipped at zero."""
    if sq is None:
        sq = np.einsum("ij,ij->i", X, X)
    d2 = sq - 2.0 * (X @ x) + float(x @ x)
    np.maximum(d2, 0.0, out=d2)
    return d2


def median_bandwidth(X: np.ndarray) -> float:
    """Median heuristic: the median pairwise Euclidean distance of the rows of ``X``.

    Exact for up to 2000 rows; above that, computed on a deterministic subsample of 2000 rows so no
    large pairwise matrix is formed. Returns 1.0 when all rows coincide.
    """
    A = np.asarray(X, dtype=np.float64)
    if len(A) > _BANDWIDTH_SAMPLE:
        A = A[np.random.default_rng(_RANDOM_STATE).choice(len(A), _BANDWIDTH_SAMPLE, replace=False)]
    sq = np.einsum("ij,ij->i", A, A)
    d2 = sq[:, None] - 2.0 * (A @ A.T) + sq[None, :]
    np.maximum(d2, 0.0, out=d2)
    h = float(np.median(np.sqrt(d2[np.triu_indices(len(A), k=1)])))
    return h if h > 0 else 1.0


def kernel_weights(x: np.ndarray, X: np.ndarray, h: float) -> np.ndarray:
    """``exp(-d^2 / (2 h^2))`` of the query ``x`` against every row of ``X`` (unitless, in (0, 1])."""
    d2 = sq_dists(np.asarray(x), np.asarray(X))
    return np.exp(-d2 / (2.0 * h * h))


@dataclass
class Index:
    """Retrieval index: standardized rows, their squared norms and the bandwidth ``h``."""

    X: np.ndarray
    sq: np.ndarray
    h: float

    @property
    def n(self) -> int:
        """Number of indexed rows."""
        return int(self.X.shape[0])


def build_index(X: np.ndarray, h: float | None = None) -> Index:
    """Build a retrieval index over rows ``X``; ``h`` defaults to the median heuristic."""
    X = np.asarray(X)
    sq = np.einsum("ij,ij->i", X, X)
    return Index(X=X, sq=sq, h=float(h) if h is not None else median_bandwidth(X))


def top_m_neighbors(x: np.ndarray, index: Index, m: int = TOP_M_NEIGHBORS) -> tuple[np.ndarray, np.ndarray]:
    """Indices and kernel weights of the ``m`` highest-weight rows, sorted by weight descending.

    Returns all rows when ``m >= n``. Allocates only vectors of length n.
    """
    d2 = sq_dists(np.asarray(x, dtype=index.X.dtype), index.X, index.sq)
    n = len(d2)
    if m >= n:
        order = np.argsort(d2, kind="stable")
    else:
        part = np.argpartition(d2, m - 1)[:m]
        order = part[np.argsort(d2[part], kind="stable")]
    w = np.exp(-d2[order].astype(np.float64) / (2.0 * index.h * index.h))
    return order, w


def density(x: np.ndarray, index: Index) -> float:
    """Mean kernel weight of the query against all indexed rows (unitless kernel density)."""
    d2 = sq_dists(np.asarray(x, dtype=index.X.dtype), index.X, index.sq)
    return float(np.exp(-d2.astype(np.float64) / (2.0 * index.h * index.h)).mean())


def loo_density(index: Index, chunk: int = 512) -> np.ndarray:
    """Leave-one-out kernel density per indexed row: ``sum_{j != i} k(x_i, x_j) / (n - 1)``.

    Computed in chunks of ``chunk`` rows, so memory is about ``chunk * n`` values, never ``n * n``.
    """
    X, sq, n = index.X, index.sq, index.n
    out = np.empty(n, dtype=np.float64)
    inv = -1.0 / (2.0 * index.h * index.h)
    for a in range(0, n, chunk):
        b = min(a + chunk, n)
        d2 = X[a:b] @ X.T
        d2 *= -2.0
        d2 += sq[a:b, None]
        d2 += sq[None, :]
        np.maximum(d2, 0.0, out=d2)
        d2 *= inv
        np.exp(d2, out=d2)
        d2[np.arange(b - a), np.arange(a, b)] = 0.0
        out[a:b] = d2.sum(axis=1, dtype=np.float64)
    return out / max(n - 1, 1)


def novelty_threshold(index: Index, pct: float = NOVELTY_PERCENTILE, chunk: int = 512) -> float:
    """The ``pct``-th percentile of the leave-one-out density; queries below it are novel."""
    return float(np.percentile(loo_density(index, chunk=chunk), pct))
