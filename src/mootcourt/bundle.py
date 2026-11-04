"""Model bundle: one fit path shared by the card, the registry and the harness.

``fit_bundle`` fits the feature space, P0, P1, P2 (per cell), the stored novelty thresholds and the
retrieval index, and returns a ``ModelBundle`` that carries the ledger snapshot id, the model id and the
feature hash. ``save_bundle`` writes ``models/<model_id>/`` with a manifest holding the sha256 of every
artifact; ``load_bundle`` verifies every checksum before it loads anything.

Trust. Joblib (pickle) is used only for objects this program wrote and checksummed. A bundle is a local
artifact: it is never loaded from a download or from any path outside the models directory, and an id
that would leave that directory is rejected. The manifest carries its own digests, so the check catches
corruption, partial writes and a stray or unlisted file; it does not stop someone who can already write to
the models directory, because that person can rewrite the manifest too. ``load_bundle`` requires the
manifest to list exactly the files in the directory, requires the five artifacts below to be listed, reads
each file once and loads from the bytes it hashed.

The retrieval index is rebuilt at every fit and never updated incrementally. The model id is a
deterministic function of the snapshot id and the fitted parameters (rounded to 9 significant digits so
that harmless last-digit differences between machines do not change it). Units: effects are in the
ledger's units; origin semantics: a prediction at ``origin`` uses rows with status admitted and
``usable_after <= origin``. A bundle is fit once, on the rows visible at its ``as_of`` (all admitted rows by
default), so it records its ``fit_cutoff`` (the latest ``usable_after`` it saw) and refuses an origin earlier
than that; fit a new bundle with ``as_of`` set to the origin to predict there.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from mootcourt import scale
from mootcourt.config import (
    BANDWIDTH_MULTIPLIERS,
    HALF_LIFE_DAYS,
    KAPPA,
    LAMBDA_GRID,
    NU_GRID,
    P2_GUARD_MULT,
    P2_SELECTION_DEFAULT,
    TOP_M_NEIGHBORS,
)
from mootcourt.features import FeatureSpace, feature_hash, use_cell_only
from mootcourt.ledger import ADMITTED, series_ns, to_utc, visible_rows
from mootcourt.predictors.base import Predictive
from mootcourt.predictors.p0 import P0Predictor
from mootcourt.predictors.p1 import P1Predictor
from mootcourt.predictors.p2 import NeighborState, P2Predictor
from mootcourt.storage import visible_iterdir

BUNDLE_FORMAT = 1
MAX_EXPOSURE = 1e12         # a planned exposure above this is a typo, and its standard error overflows nothing but means nothing
# raised when the method changes in a way that makes a refit a different method (round 00: P0, P2 predictive family, pairwise features)
METHOD_VERSION = 2
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_DEFAULT_CTR = 0.02
REQUIRED_ARTIFACTS = frozenset(
    {"model.json", "space_arrays.npz", "p2_arrays.npz", "p0_rows.npz", "space_objects.joblib"})


class BundleIntegrityError(RuntimeError):
    """An artifact is missing, altered, or listed outside the bundle directory."""


@dataclass
class ModelBundle:
    """A fitted model: feature space, P0, P1, P2 and the version ids every card must carry."""

    model_id: str
    snapshot_id: str
    feature_hash: str
    source: str
    space: FeatureSpace
    p0: P0Predictor
    p1: P1Predictor
    p2: P2Predictor
    parameters: dict[str, Any]
    cell_stats: dict[str, dict[str, float]]
    p0_rows: dict[str, np.ndarray] = field(repr=False, default_factory=dict)
    fit_time: str = ""
    n_rows: int = 0
    backtest_summary: dict | None = None
    method_id: str = ""
    fit_as_of: str = ""           # the fit clock: only rows usable at this instant entered the fit ("" for a fit on every admitted row)

    # --------------------------------------------------------------- cutoff
    @property
    def fit_cutoff(self) -> pd.Timestamp | None:
        """Latest ``usable_after`` among the rows this bundle was fit on (None for an empty fit)."""
        ns = self.p0_rows.get("usable_ns")
        return None if ns is None or len(ns) == 0 else pd.Timestamp(int(np.max(ns)), tz="UTC")

    def check_origin(self, origin) -> None:
        """Raise ValueError when ``origin`` is earlier than the fit cutoff (parameters would use later rows)."""
        cutoff = self.fit_cutoff
        if cutoff is not None and pd.Timestamp(origin).tz_convert("UTC") < cutoff:
            raise ValueError(
                f"origin {pd.Timestamp(origin).isoformat()} is earlier than the fit cutoff {cutoff.isoformat()}; "
                "fit a bundle with as_of set to that origin to predict there")

    # ------------------------------------------------------------ features
    def transform_text(self, headline: str, image_changed: bool = False, cell: str | None = None,
                       exposure: float | None = None, reference: str | None = None) -> np.ndarray:
        """Standardized feature vector of one headline (1-D); ``exposure`` is the planned exposures per arm.

        ``reference`` is the reference headline of a pairwise space (None or empty: the fit-set mean reference vector).
        """
        return self.space.transform_text([headline], image_changed, cell=cell, exposure=exposure, reference=reference or None)[0]

    # ---------------------------------------------------------- predictions
    def cells(self) -> list[str]:
        """Cells that have fitted rows."""
        return sorted(self.p2._cells)

    def predict_all(self, x, s_star: float, cell: str, origin) -> dict[str, Predictive]:
        """Predictive of every rung (``P0``, ``P1``, ``P2``) for a query ``x`` standing at ``origin``.

        ``s_star`` is the standard error of the future estimate in the units of y.
        """
        self.check_origin(origin)
        return {
            "P0": self.p0.predict(x, s_star, cell, origin),
            "P1": self.p1.predict(x, s_star, cell, origin),
            "P2": self.p2.predict(x, s_star, cell, origin),
        }

    def neighbor_state(self, x, cell: str, origin) -> NeighborState:
        """P2 neighbors of ``x`` visible at ``origin`` (see ``P2Predictor.neighbor_state``)."""
        return self.p2.neighbor_state(x, cell, origin)

    def density(self, x, cell: str, origin) -> float:
        """Kernel density of ``x`` among the cell's rows visible at the origin."""
        return self.p2.density(x, cell, origin)

    def novelty_threshold(self, cell: str) -> float:
        """Stored 5th percentile of the leave-one-out density in the cell."""
        return self.p2.novelty_threshold(cell)

    def n_visible(self, cell: str, origin) -> int:
        """Admitted rows of the cell visible at the origin."""
        return self.p2.n_visible(cell, origin)

    def base_rate(self, cell: str, origin) -> float:
        """P0's empirical frequency of significant-positive outcomes in the cell at the origin."""
        return self.p0.sig_positive_frequency(cell, origin)

    def median_ctr_ref(self, cell: str) -> float:
        """Median reference-arm click-through rate in the cell (a probability), used to turn exposures into s*."""
        stats = self.cell_stats.get(cell)
        if stats is not None and "median_ctr_ref" in stats:
            return float(stats["median_ctr_ref"])
        known = [v["median_ctr_ref"] for v in self.cell_stats.values() if "median_ctr_ref" in v]
        return float(np.median(known)) if known else _DEFAULT_CTR

    def s_star(self, cell: str, impressions: float, impressions_variant: float | None = None) -> float:
        """Pre-launch standard error of the future estimate for planned exposures (see ``mootcourt.scale``).

        ``impressions`` is the reference arm's exposure and ``impressions_variant`` the variant's (default: equal arms).
        Upworthy: ``100 sqrt(c (1 - c) (1 / n_ref + 1 / n_var))`` with the cell's median reference rate ``c``. ASOS:
        ``sqrt(1 / n_ref + 1 / n_var)``. Any other source: the cell's median ``s sqrt(n)`` over its rows divided by
        ``sqrt(n)`` with ``n`` the mean of the two arms.
        """
        n_var = impressions if impressions_variant is None else impressions_variant
        if impressions <= 0 or n_var <= 0:
            raise ValueError("impressions per arm must be positive")
        if impressions > MAX_EXPOSURE or n_var > MAX_EXPOSURE:
            raise ValueError(f"impressions per arm must be at most {MAX_EXPOSURE:.0e}")
        if self.source == "upworthy":
            return float(scale.upworthy_s_star(impressions, n_var, self.median_ctr_ref(cell)))
        if self.source == "asos":
            return math.sqrt(1.0 / impressions + 1.0 / n_var)
        stats = self.cell_stats.get(cell) or next(iter(self.cell_stats.values()), {})
        n = 0.5 * (impressions + n_var)
        return float(stats.get("median_s_sqrt_n", 100.0 * math.sqrt(2.0 * _DEFAULT_CTR * (1.0 - _DEFAULT_CTR)))) / math.sqrt(n)


def method_id(space: FeatureSpace | None = None) -> str:
    """12 hex characters naming the METHOD a bundle was fit with, independent of the data it was fit on.

    The registry compares them: a bundle with the champion's method id on a newer snapshot is a refresh of the champion and replaces it
    without the challenger margin; a different method id is a different method and needs the margin (docs/operations.md). The id covers
    the method version, the fixed hyperparameters of the ladder and the kind of feature space (single headline or pairwise).
    """
    payload = {
        "version": METHOD_VERSION,
        "kappa": KAPPA,
        "nu_grid": [None if math.isinf(v) else v for v in NU_GRID],
        "lambda_grid": list(LAMBDA_GRID),
        "bandwidth_multipliers": list(BANDWIDTH_MULTIPLIERS),
        "guard": P2_GUARD_MULT,
        "selection": P2_SELECTION_DEFAULT,
        "pairwise": bool(space.pairwise) if space is not None else False,
        "top_m": TOP_M_NEIGHBORS,
        "half_lives": [str(h) for h in HALF_LIFE_DAYS],
    }
    if space is not None:  # the kind and size of the feature space: a source that gains headline text changes the method (REV-L-023)
        payload.update({"cell_only": bool(space.cell_only), "svd_dims": int(space.svd_dims), "min_df": int(space.min_df),
                        "backend": space.backend, "feature_set": space.feature_set})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------- fitting
def _round_sig(obj, digits: int = 9):
    if isinstance(obj, dict):
        return {str(k): _round_sig(v, digits) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_round_sig(v, digits) for v in obj]
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        if not math.isfinite(f) or f == 0.0:
            return None if not math.isfinite(f) else 0.0
        return float(f"{f:.{digits - 1}e}")
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _cell_stats(adm: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Per cell: the median reference click-through rate of concluded rows (history), the median
    ``s sqrt(n)`` (a source-free scale used for cards of sources without a rate) and the row count."""
    rates = scale.cell_median_ctr(adm)
    out: dict[str, dict[str, float]] = {}
    for cell, g in adm.groupby("cell"):
        n_arm = 0.5 * (g["n_ref"].to_numpy(float) + g["n_var"].to_numpy(float))
        out[str(cell)] = {"median_ctr_ref": rates.get(str(cell), _DEFAULT_CTR),
                          "median_s_sqrt_n": float(np.median(g["s"].to_numpy(float) * np.sqrt(n_arm))), "n": int(len(g))}
    return out


def fit_bundle(ledger: pd.DataFrame, source: str, snapshot_id: str, as_of=None, cell_only: bool | None = None) -> ModelBundle:
    """Fit all rungs on the ledger's admitted rows and return a bundle.

    ``as_of`` (timezone-aware) restricts the fit to rows visible at that instant; the default fits on every
    admitted row, which is right for a historical ledger whose rows are all final. ``cell_only`` defaults to
    True for the ASOS source and for any imported source whose rows carry no headline text; the features are then the cell and the number of variants.
    """
    rows = ledger if as_of is None else visible_rows(ledger, as_of)
    adm = rows.loc[rows["status"] == ADMITTED]
    if len(adm) == 0:
        if as_of is not None:
            raise ValueError(f"no admitted row is usable at the fit clock {to_utc(as_of).isoformat()}: cannot fit a bundle there")
        raise ValueError("cannot fit a bundle without admitted rows")
    space = FeatureSpace.fit(adm, cell_only=use_cell_only(source, adm) if cell_only is None else cell_only)
    p0 = P0Predictor().fit(adm)
    p1 = P1Predictor().fit(adm, data_end=as_of)
    p2 = P2Predictor().fit(adm, space, p1)
    fh = feature_hash(space)
    parameters = {
        "p1": p1.to_state(),
        "lambda_by_cell": p2.lambda_by_cell,
        "bandwidth_mult_by_cell": p2.bandwidth_mult_by_cell,
        "tau_res2_by_cell": p2.tau_res2_by_cell,
        "feature_hash": fh,
        "n_rows": int(len(adm)),
    }
    digest = hashlib.sha256(json.dumps(_round_sig(parameters), sort_keys=True).encode("utf-8")).hexdigest()
    model_id = hashlib.sha256(f"{snapshot_id}|{digest}".encode()).hexdigest()[:12]
    p0_rows = {
        "cell": np.array(adm["cell"].tolist(), dtype="U"), "usable_ns": series_ns(adm["usable_after"]),
        "y": adm["y"].to_numpy(float), "s": adm["s"].to_numpy(float),
    }
    return ModelBundle(
        model_id=model_id, snapshot_id=snapshot_id, feature_hash=fh, source=source, space=space, p0=p0, p1=p1, p2=p2,
        parameters=parameters, cell_stats=_cell_stats(adm), p0_rows=p0_rows,
        fit_time=dt.datetime.now(dt.timezone.utc).isoformat(), n_rows=int(len(adm)), method_id=method_id(space),
        fit_as_of=to_utc(as_of).isoformat() if as_of is not None else "",
    )


# ------------------------------------------------------------------- save/load
def bundle_dir(model_id: str, models_dir) -> Path:
    """Directory of a model id inside ``models_dir``; raises ValueError for an id that could leave it."""
    if not isinstance(model_id, str) or not _ID_PATTERN.match(model_id) or ".." in model_id:
        raise ValueError(f"invalid model id {model_id!r}")
    root = Path(models_dir).resolve()
    path = (root / model_id).resolve()
    if path.parent != root:
        raise ValueError(f"model id {model_id!r} resolves outside the models directory")
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _prefixed(prefix: str, arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {f"{prefix}{k}": v for k, v in arrays.items()}


def save_bundle(bundle: ModelBundle, models_dir) -> Path:
    """Write ``models/<model_id>/`` (arrays as npz, sklearn objects via joblib, JSON metadata) and return it."""
    final = bundle_dir(bundle.model_id, models_dir)
    root = final.parent
    root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=root, prefix=".tmp-"))
    try:
        sp = bundle.space.to_state()
        p2 = bundle.p2.to_state()
        np.savez(tmp / "space_arrays.npz", **sp["arrays"])
        np.savez(tmp / "p2_arrays.npz", **p2["arrays"])
        np.savez(tmp / "p0_rows.npz", **bundle.p0_rows)
        joblib.dump(sp["objects"], tmp / "space_objects.joblib")
        meta = {
            "space": sp["meta"], "p1": bundle.p1.to_state(), "p2": p2["meta"], "cell_stats": bundle.cell_stats,
            "source": bundle.source, "n_rows": bundle.n_rows,
        }
        (tmp / "model.json").write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")
        # AppleDouble companions (._name) that macOS writes on exFAT are not artifacts
        artifacts = {p.name: _sha256(p) for p in visible_iterdir(tmp)}
        manifest = {
            "format": BUNDLE_FORMAT, "model_id": bundle.model_id, "snapshot_id": bundle.snapshot_id,
            "feature_hash": bundle.feature_hash, "source": bundle.source,
            "parameters": {
                k: v for k, v in bundle.parameters.items() if k != "p1"
            } | {"p1_global": bundle.p1.to_state()["global"]},
            "fit_time": bundle.fit_time, "fit_as_of": bundle.fit_as_of, "backtest_summary": bundle.backtest_summary,
            "method_id": bundle.method_id, "artifacts": artifacts,
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        old = None
        if final.exists():                       # move the old bundle aside so the id is never missing
            old = root / f".old-{bundle.model_id}-{os.getpid()}"
            shutil.rmtree(old, ignore_errors=True)
            os.rename(final, old)
        os.rename(tmp, final)
        if old is not None:
            shutil.rmtree(old, ignore_errors=True)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return final


def read_manifest(model_id: str, models_dir) -> dict:
    """Read a bundle's manifest (no artifact is loaded, nothing is verified)."""
    path = bundle_dir(model_id, models_dir) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_bundle(model_id: str, models_dir) -> ModelBundle:
    """Verify every artifact checksum, then load the bundle. Raises BundleIntegrityError on any mismatch.

    The manifest must list exactly the files in the directory (besides itself) and must list the required
    artifacts. Each file is read once; its digest is checked on those bytes and the object is loaded from them.
    """
    d = bundle_dir(model_id, models_dir)
    mpath = d / "manifest.json"
    if not mpath.is_file():
        raise BundleIntegrityError(f"no manifest for model {model_id}")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    if manifest.get("format") != BUNDLE_FORMAT:
        raise BundleIntegrityError(f"unsupported bundle format {manifest.get('format')!r}")
    if manifest.get("model_id") != model_id:
        raise BundleIntegrityError(f"the manifest names model {manifest.get('model_id')!r}, not {model_id!r}")
    listed = manifest.get("artifacts")
    if not isinstance(listed, dict):
        raise BundleIntegrityError("the manifest has no artifact map")
    missing = REQUIRED_ARTIFACTS - set(listed)
    if missing:
        raise BundleIntegrityError(f"the manifest does not list required artifacts: {sorted(missing)}")
    present = {p.name for p in visible_iterdir(d)} - {"manifest.json"}  # dot files (.DS_Store) are never opened
    if present != set(listed):
        raise BundleIntegrityError(f"files and manifest disagree: unlisted {sorted(present - set(listed))}, "
                                   f"missing {sorted(set(listed) - present)}")
    data: dict[str, bytes] = {}
    for name, digest in listed.items():
        if "/" in name or "\\" in name or name.startswith("."):
            raise BundleIntegrityError(f"artifact name {name!r} is not a plain file name")
        f = d / name
        blob = f.read_bytes() if f.is_file() else None
        if blob is None or hashlib.sha256(blob).hexdigest() != digest:
            raise BundleIntegrityError(f"artifact {name} is missing or does not match its checksum")
        data[name] = blob

    def arrays(name: str) -> dict[str, np.ndarray]:
        with np.load(io.BytesIO(data[name])) as z:
            return {k: z[k] for k in z.files}

    meta = json.loads(data["model.json"].decode("utf-8"))
    space_arrays, p2_arrays, p0_rows = arrays("space_arrays.npz"), arrays("p2_arrays.npz"), arrays("p0_rows.npz")
    objects = joblib.load(io.BytesIO(data["space_objects.joblib"]))
    space = FeatureSpace.from_state({"arrays": space_arrays, "meta": meta["space"], "objects": objects})
    p1 = P1Predictor.from_state(meta["p1"])
    p2 = P2Predictor.from_state({"arrays": p2_arrays, "meta": meta["p2"]}, space, p1)
    frame = pd.DataFrame(
        {
            "cell": p0_rows["cell"].tolist(),
            "usable_after": pd.to_datetime(p0_rows["usable_ns"], unit="ns", utc=True),
            "y": p0_rows["y"], "s": p0_rows["s"], "status": ADMITTED,
        }
    )
    p0 = P0Predictor().fit(frame)
    parameters = {k: v for k, v in manifest["parameters"].items() if k != "p1_global"}
    parameters["p1"] = meta["p1"]
    return ModelBundle(
        model_id=manifest["model_id"], snapshot_id=manifest["snapshot_id"], feature_hash=manifest["feature_hash"],
        source=manifest["source"], space=space, p0=p0, p1=p1, p2=p2, parameters=parameters,
        cell_stats=meta["cell_stats"], p0_rows=p0_rows, fit_time=manifest["fit_time"], n_rows=meta["n_rows"],
        backtest_summary=manifest["backtest_summary"], method_id=str(manifest.get("method_id", "")),
        fit_as_of=str(manifest.get("fit_as_of", "") or ""),
    )
