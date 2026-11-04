"""Features, kernel and retrieval index.

A ``FeatureSpace`` maps a ledger row (or a bare headline) to a standardized vector: TF-IDF (1 to 2
grams, ``min_df`` 3) on the headline reduced by TruncatedSVD to at most 64 dimensions, concatenated
with the named structured features and the log of the planned exposures per arm, then z-scored per column using
statistics from the fit set. Only the pre-launch allow-list of ``mootcourt.scale`` is read from a row's features;
a post-launch field among them raises ``PostLaunchFieldError``.

Pairwise text (round 00, docs/method.md call 167). When the rows carry a reference headline (Upworthy does), the text part is
three blocks of ``PAIRWISE_SVD_DIMS`` columns from one TF-IDF and SVD fit on the variant and reference headlines together: the
variant vector, the reference vector and their difference, and three pair features are appended after the structured ones (the
word-count difference, the character-count difference and the share of words the two headlines have in common). A contrast is a
pair, and a kernel on the variant text alone cannot represent what changed. Rows without a reference headline (synthetic, ASOS,
imported ledgers) keep the single-headline space and its feature hash. A card request without a reference headline gets the fit-set
mean reference vector.

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
# Pairwise features (round 00, call 167), added only when the rows carry a reference headline: the change between the arms.
PAIR_FEATURES = ["words_diff", "chars_diff", "shared_token_share"]
PAIRWISE_SVD_DIMS = 32          # per block: variant, reference and their difference, so the text part has three blocks
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


def _tokens(text: str) -> set:
    return {w.lower() for w in _WORD.findall(text or "")}


def pair_features(headline: str, reference: str) -> np.ndarray:
    """Unitless pair features, ordered as ``PAIR_FEATURES``: word-count difference, character-count difference and shared-word share."""
    a, b = _tokens(headline), _tokens(reference)
    union = a | b
    return np.array([len((headline or "").split()) - len((reference or "").split()),
                     len(headline or "") - len(reference or ""), (len(a & b) / len(union)) if union else 1.0], dtype=np.float64)


def parse_references(rows: pd.DataFrame) -> list[str]:
    """Reference headlines of ledger rows from the pre-launch allow-list (empty string where a row has none)."""
    return [str(prelaunch_view(json.loads(j)).get("reference_headline", "") or "") for j in rows["features_json"]]


def has_reference(rows: pd.DataFrame) -> bool:
    """True when at least one row carries a non-empty reference headline in its pre-launch features."""
    return any(r.strip() for r in parse_references(rows))


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
    pairwise: bool = False
    ref_fill: np.ndarray | None = None          # mean raw SVD vector of the fit set's reference headlines (a request without one gets it)

    @property
    def dim(self) -> int:
        """Number of output columns."""
        return int(self._columns().size)

    def _columns(self) -> np.ndarray:
        """Indices of the columns this space outputs: the text part, the structured part, or both (an ablation switch)."""
        n = int(self.mean.shape[0])
        if self.cell_only or self.feature_set == "both":
            return np.arange(n)
        n_text = self.svd_dims * (3 if self.pairwise else 1)
        return np.arange(n_text) if self.feature_set == "text" else np.arange(n_text, n)

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
        pairwise: bool | None = None,
    ) -> FeatureSpace:
        """Fit on the given rows (the caller passes only rows visible at the origin).

        ``svd_dims`` is capped at vocabulary size minus 1 and at rows minus 1; a cap is logged.
        With ``cell_only`` the space is the cell one-hot plus the variant count (metric id and number
        of variants), the degenerate space used for sources without text. Fitting is deterministic.

        ``pairwise`` None means "when the rows carry a reference headline"; ``False`` gives the single-headline space of
        earlier versions and ``True`` requires reference headlines.
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
        refs = parse_references(rows)
        pair = has_reference(rows) if pairwise is None else bool(pairwise)
        if pair and not has_reference(rows):
            raise ValueError("a pairwise feature space needs reference headlines in the rows")
        # each distinct text once: a shared reference is not weighted by its contrasts
        corpus = list(dict.fromkeys(heads + refs)) if pair else heads
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=min_df, dtype=np.float64)
        tfidf_all = vec.fit_transform(corpus)
        vocab = len(vec.vocabulary_)
        dims = PAIRWISE_SVD_DIMS if pair else svd_dims
        cap = min(dims, vocab - 1, len(corpus) - 1)
        if cap < 1:
            raise ValueError("not enough text to fit a feature space")
        if cap < dims:
            log.info("svd dims cap: requested %d, using %d (vocabulary %d, texts %d)", dims, cap, vocab, len(corpus))
        svd = TruncatedSVD(n_components=cap, random_state=_RANDOM_STATE)
        svd.fit(tfidf_all)
        u_var = svd.transform(vec.transform(heads))
        if pair:
            u_ref = svd.transform(vec.transform(refs))
            text = np.hstack([u_var, u_ref, u_var - u_ref])
            ref_fill = u_ref.mean(axis=0)
        else:
            text, ref_fill = u_var, None
        raw = np.hstack([text, cls._structured_matrix(heads, imgs, logexp, refs if pair else None)])
        mean, std = raw.mean(0), raw.std(0)
        std = np.where(std < _STD_FLOOR, 1.0, std)
        return cls(vec, svd, mean, std, cap, False, (), min_df, backend, feature_set, pair, ref_fill)

    @staticmethod
    def _structured_matrix(heads, imgs, logexp, refs=None) -> np.ndarray:
        base = np.array([structured_features(h, bool(i)) for h, i in zip(heads, imgs)]).reshape(len(heads), -1)
        cols = [base, np.asarray(logexp, dtype=np.float64).reshape(-1, 1)]
        if refs is not None:
            cols.append(np.array([pair_features(h, r) for h, r in zip(heads, refs)]).reshape(len(heads), -1))
        return np.hstack(cols)

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
        return self._transform(heads, imgs, logexp, parse_references(rows) if self.pairwise else None)

    def transform_text(self, headlines, image_changed=False, cell: str | None = None, n_variants: float = 2.0,
                       exposure=None, reference=None) -> np.ndarray:
        """Standardized features for bare headlines (unseen and out-of-vocabulary text is fine).

        ``image_changed`` is one flag or one per headline. ``cell`` and ``n_variants`` are used only
        by a cell-only space. ``exposure`` is the planned exposures per arm (one value or one per headline);
        left out, the fit-set average of the log exposure is used, which standardizes to zero. ``reference`` is the reference
        headline (one for all or one per headline) of a pairwise space; left out, the fit-set mean reference vector is used
        and the pair features are those of an empty reference.
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
        refs = None
        if self.pairwise:
            refs = [""] * len(heads) if reference is None else [str(r) for r in np.broadcast_to(np.asarray(reference, dtype=object), (len(heads),))]
        return self._transform(heads, imgs, logexp, refs, no_reference=reference is None)

    def _transform(self, heads, imgs, logexp, refs=None, no_reference: bool = False) -> np.ndarray:
        u_var = self.svd.transform(self.vectorizer.transform(heads))
        if self.pairwise:
            if no_reference and self.ref_fill is not None:
                u_ref = np.broadcast_to(self.ref_fill, u_var.shape)
            else:
                u_ref = self.svd.transform(self.vectorizer.transform(refs))
            text = np.hstack([u_var, u_ref, u_var - u_ref])
        else:
            text = u_var
        struct = self._structured_matrix(heads, imgs, logexp, refs if self.pairwise else None)
        if self.pairwise and no_reference:
            # no reference given: the pair features are neutral too, the fit-set means (a standardized zero), as the reference vector is (REV-L-014)
            struct[:, -len(PAIR_FEATURES):] = self.mean[-len(PAIR_FEATURES):]
        raw = np.hstack([text, struct])
        full = (raw - self.mean) / self.std
        return full if self.feature_set == "both" else full[:, self._columns()]

    # ---------------------------------------------------------------- state
    def to_state(self) -> dict[str, Any]:
        """Split into ``arrays`` (for npz), ``meta`` (JSON) and ``objects`` (sklearn, for joblib)."""
        return {
            "arrays": {"mean": self.mean, "std": self.std, **({"ref_fill": self.ref_fill} if self.ref_fill is not None else {})},
            "meta": {
                "svd_dims": self.svd_dims, "cell_only": self.cell_only, "cells": list(self.cells),
                "min_df": self.min_df, "backend": self.backend, "feature_set": self.feature_set, "pairwise": self.pairwise,
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
            int(m["min_df"]), str(m["backend"]), str(m.get("feature_set", "both")), bool(m.get("pairwise", False)),
            np.asarray(state["arrays"]["ref_fill"]) if "ref_fill" in state["arrays"] else None,
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
    if space.pairwise:                                 # a single-headline space keeps the hash it always had
        payload["pairwise"] = True
        payload["pair_features"] = PAIR_FEATURES
        payload["svd_dims"] = space.svd_dims
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
