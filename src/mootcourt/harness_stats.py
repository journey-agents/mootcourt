"""Backtest statistics: by-test bootstrap, calibration against a null, coverage, split-half, gates.

Everything here consumes the per-row score table of ``harness.rolling_origin``.

Interval rule. Every 90 percent interval on an aggregate score is a bootstrap that resamples whole tests,
never rows, because contrasts of one test share a reference arm and are not independent. Per-test sums are
computed once, so a resample is one multinomial draw of test counts and a matrix product; 20000 rows with
500 resamples take a few seconds.

Gate rule. A rung in a cell is decidable at skill 0.20 when its scored row count reaches ``n_200`` and at
skill 0.10 when it reaches ``n_400``; both numbers are read from gates.json (``simulate.load_gates``) and
never hardcoded. They are the sizes at the release gate (power 0.90); the sizes at the research screen (power
0.80) are printed beside them as ``decidable_research`` (builder call 41). The headline is the count of tests
(``decidable_by_tests`` and ``decidable_research_by_tests``): contrasts of one test share a reference arm and the
power simulation resamples independent rows, so applying its sizes to clustered rows overstates decidability
(code review finding REV-003, builder call 83). The row count (``decidable``, ``decidable_research``) is printed
beside it and labelled as the by-row figure.

Round 00 additions (docs/method.md calls 170 to 176): the perfect-calibration null is clustered by test (a one-factor Gaussian copula
whose within-test correlation is estimated from the rows, so contrasts of one test are drawn together) and the design effect is
reported; coverage is also tabulated by decile of the ratio of the realized to the planned standard error; the gate for a group is
read at the base rate nearest to the group's own event rate, with the old base rate 0.3 kept beside it; every aggregate row carries
Bonferroni-adjusted bounds (the bootstrap standard error times the Bonferroni normal quantile for the family of intervals the table
shows) beside the percentile intervals.

Units: log scores are per unit of y, CRPS is in the units of y, Brier scores and coverage are unitless.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import special

from mootcourt.config import BY_ORIGIN_RESAMPLES, Z
from mootcourt.ledger import ADMITTED, visible_rows
from mootcourt.predictors.p1 import P1Predictor
from mootcourt.simulate import select_gates

CIRCULARITY_NOTE = (
    "Scores are computed against the observed estimate with known standard error, not against the unknown "
    "true effect. This is the only option when no ground truth exists: the true effect of a past test is "
    "never observed, so a predictor can only be asked about the estimate the test produced."
)
TRIGGERS = ("support", "novelty", "reliability", "instability")
DEFAULT_B = 500
LEVEL = 0.90
# perfect-calibration null draws: the percentile resolves at most (draws - 1) / draws, so 100 means "above every draw"
NULL_DRAWS = 500
LEGACY_BASE_RATE = 0.30               # the base rate of the gates before round 00, kept as a labelled column


@dataclass(frozen=True)
class Interval:
    """A statistic with its bootstrap interval (``level`` central, by test)."""

    estimate: float
    lo: float
    hi: float
    level: float = LEVEL
    B: int = DEFAULT_B


# ---------------------------------------------------------------- bootstrap
class _TestSums:
    """Per-test sums of named columns plus the row count, for fast bootstrap by test."""

    def __init__(self, df: pd.DataFrame, columns: dict[str, np.ndarray]):
        codes, uniques = pd.factorize(df["test_id"])
        self.n_tests = len(uniques)
        self.counts = np.bincount(codes, minlength=self.n_tests).astype(np.float64)
        self.sums = {k: np.bincount(codes, weights=np.asarray(v, dtype=np.float64), minlength=self.n_tests) for k, v in columns.items()}
        self.tests = uniques

    def resample_counts(self, B: int, rng: np.random.Generator) -> np.ndarray:
        """Multinomial test counts, shape (B, n_tests): how many times each test is drawn in each resample."""
        return rng.multinomial(self.n_tests, np.full(self.n_tests, 1.0 / self.n_tests), size=B).astype(np.float64)


def _percentile_interval(draws: np.ndarray, level: float) -> tuple[float, float]:
    a = (1.0 - level) / 2.0
    lo, hi = np.nanpercentile(draws, [100 * a, 100 * (1 - a)])
    return float(lo), float(hi)


def bootstrap_by_test(scores: pd.DataFrame, stat: str, B: int = DEFAULT_B, seed: int = 0, level: float = LEVEL) -> Interval:
    """Mean of column ``stat`` with a percentile bootstrap interval that resamples whole tests.

    ``scores`` needs ``test_id`` and the column. Raises KeyError for a missing column and ValueError for
    an empty frame.
    """
    if stat not in scores.columns:
        raise KeyError(stat)
    if len(scores) == 0:
        raise ValueError("cannot bootstrap an empty score table")
    ts = _TestSums(scores, {stat: scores[stat].to_numpy(float)})
    counts = ts.resample_counts(B, np.random.default_rng(seed))
    den = counts @ ts.counts
    draws = (counts @ ts.sums[stat]) / np.where(den > 0, den, np.nan)
    lo, hi = _percentile_interval(draws, level)
    return Interval(float(scores[stat].mean()), lo, hi, level, B)


# -------------------------------------------------------------- calibration
def _bin_index(p: np.ndarray, n_bins: int) -> np.ndarray:
    return np.minimum((np.asarray(p, float) * n_bins).astype(int), n_bins - 1)


def reliability_bins(p, event, n_bins: int = 10) -> pd.DataFrame:
    """Reliability table: per equal-width bin of ``p``, the row count, mean predicted p and observed frequency."""
    p, e = np.asarray(p, float), np.asarray(event, float)
    idx = _bin_index(p, n_bins)
    n = np.bincount(idx, minlength=n_bins)
    sp = np.bincount(idx, weights=p, minlength=n_bins)
    se = np.bincount(idx, weights=e, minlength=n_bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_p, freq = sp / n, se / n
    return pd.DataFrame({"bin": np.arange(n_bins), "lo": np.arange(n_bins) / n_bins, "hi": (np.arange(n_bins) + 1) / n_bins,
                         "n": n, "mean_p": mean_p, "freq": freq})


def ece(p, event, n_bins: int = 10) -> float:
    """Expected calibration error: bin-weighted mean absolute gap between mean predicted p and observed frequency."""
    t = reliability_bins(p, event, n_bins)
    t = t[t["n"] > 0]
    return float((t["n"] * (t["mean_p"] - t["freq"]).abs()).sum() / t["n"].sum())


def _quantile_bin_index(p: np.ndarray, n_bins: int) -> np.ndarray:
    """Equal-mass bin of each probability: the minimum rank cut into ``n_bins``, so equal probabilities share a bin."""
    p = np.asarray(p, float)
    rank_min = pd.Series(p).rank(method="min").to_numpy() - 1.0
    return np.minimum((rank_min * n_bins // max(len(p), 1)).astype(int), n_bins - 1)


def ece_equal_mass(p, event, n_bins: int = 10) -> float:
    """Expected calibration error over ``n_bins`` equal-mass bins (the estimator less sensitive to which bins are populated)."""
    p, e = np.asarray(p, float), np.asarray(event, float)
    idx = _quantile_bin_index(p, n_bins)
    sp, se = np.bincount(idx, weights=p, minlength=n_bins), np.bincount(idx, weights=e, minlength=n_bins)
    return float(np.abs(sp - se).sum() / len(p))


def design_effect(p, event, test_ids) -> dict:
    """Clustering of the residuals ``event - p`` by test.

    ``design_effect`` is the variance of the total residual with whole tests as the units (``sum_t (sum_{i in t} r_i)^2``) over its
    independent-rows value (``sum_i p_i (1 - p_i)``); it is near 1 when contrasts of a test are as independent as the null says. ``icc`` is the
    within-test correlation of the standardized residuals implied by it, ``(deff - 1) / (m - 1)`` with ``m`` the size-weighted mean test
    size, clipped to [0, 0.99]; it is the correlation the clustered null uses.
    """
    p, e = np.asarray(p, float), np.asarray(event, float)
    codes, _ = pd.factorize(pd.Series(np.asarray(test_ids)))
    sizes = np.bincount(codes).astype(float)
    r = e - p
    num = float((np.bincount(codes, weights=r) ** 2).sum())
    den = float((p * (1.0 - p)).sum())
    deff = num / den if den > 0 else 1.0
    m = float((sizes ** 2).sum() / sizes.sum())
    icc = 0.0 if m <= 1.0 else float(np.clip((deff - 1.0) / (m - 1.0), 0.0, 0.99))
    return {"design_effect": float(deff), "icc": icc, "mean_test_size": m, "n_tests": int(len(sizes))}


def ece_null(p, draws: int = NULL_DRAWS, seed: int = 0, n_bins: int = 10, test_ids=None, icc: float = 0.0, equal_mass: bool = False) -> np.ndarray:
    """ECE of ``draws`` outcome sets drawn from the predicted probabilities (the perfect-calibration null).

    Without ``test_ids`` the outcomes are independent Bernoulli(p). With them, contrasts of one test are drawn together: a one-factor
    Gaussian copula with within-test correlation ``icc`` (one shared normal per test plus one per row) keeps every marginal at its
    ``p`` and makes outcomes of a test move together, which is what a shared reference arm does. ``icc = 0`` is the independent null.
    ``equal_mass`` bins by quantile instead of equal width.
    """
    p = np.asarray(p, float)
    if p.size == 0 or np.any(p < 0) or np.any(p > 1) or not np.all(np.isfinite(p)):
        raise ValueError("p must be a non-empty array of probabilities in [0, 1]")
    rng = np.random.default_rng(seed)
    idx = _quantile_bin_index(p, n_bins) if equal_mass else _bin_index(p, n_bins)
    sp = np.bincount(idx, weights=p, minlength=n_bins)
    out = np.empty(draws)
    clustered = test_ids is not None and icc > 0.0
    if clustered:
        codes, uniq = pd.factorize(pd.Series(np.asarray(test_ids)))
        thr = special.ndtri(np.clip(p, 1e-12, 1.0 - 1e-12))
        a, b = np.sqrt(icc), np.sqrt(1.0 - icc)
    for a0 in range(0, draws, 100):
        m = min(100, draws - a0)
        if clustered:
            z = a * rng.standard_normal((m, len(uniq)))[:, codes] + b * rng.standard_normal((m, p.size))
            e = (z < thr[None, :]).astype(np.float64)
        else:
            e = (rng.random((m, p.size)) < p[None, :]).astype(np.float64)
        se = np.stack([np.bincount(idx, weights=row, minlength=n_bins) for row in e])
        out[a0:a0 + m] = np.abs(sp[None, :] - se).sum(axis=1) / p.size          # sum_b n_b |mean_p - freq| / N
    return out


def ece_percentile(p, event, draws: int = NULL_DRAWS, seed: int = 0, n_bins: int = 10, test_ids=None, icc: float = 0.0,
                   equal_mass: bool = False) -> float:
    """Percentile (0 to 100) of the observed ECE within the perfect-calibration null; ties count half.

    A value of 100 means the observed ECE is above every draw; ``draws`` draws resolve percentiles only up to ``100 (draws - 1) / draws``.
    """
    obs = ece_equal_mass(p, event, n_bins) if equal_mass else ece(p, event, n_bins)
    null = ece_null(p, draws, seed, n_bins, test_ids, icc, equal_mass)
    return float(100.0 * (np.mean(null < obs) + 0.5 * np.mean(null == obs)))


# ----------------------------------------------------------------- coverage
def interval_coverage(y, lo, hi) -> float:
    """Share of ``y`` inside ``[lo, hi]`` (inclusive)."""
    y, lo, hi = np.asarray(y, float), np.asarray(lo, float), np.asarray(hi, float)
    return float(np.mean((y >= lo) & (y <= hi)))


def coverage_by_cell(scores: pd.DataFrame) -> pd.DataFrame:
    """Coverage of the 80 and 90 percent intervals for y per cell, plus an ``ALL`` row."""
    rows = []
    for cell, g in [("ALL", scores)] + list(scores.groupby("cell")):
        rows.append({"cell": cell, "n": len(g), "coverage_80": interval_coverage(g["y"], g["lo80"], g["hi80"]),
                     "coverage_90": interval_coverage(g["y"], g["lo90"], g["hi90"])})
    return pd.DataFrame(rows)


# -------------------------------------------------------- calibration by precision
PRECISION_COLUMNS = ["rung", "decile", "exposure_lo", "exposure_hi", "n", "mean_p_sig", "event_rate", "coverage_90", "mean_s_star"]


def calibration_by_precision(scores: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    """Calibration within strata of precision: deciles of the planned exposures per arm.

    The decile edges come from the distinct scored rows, so every rung is binned the same way; tied exposures
    give fewer bins (one when they are all equal). Per rung and bin: ``n`` rows, the mean ``p_sig``, the rate of
    the significant-positive event, the coverage of the 90 percent interval of ``y`` and the mean ``s_star``. A
    forecaster that is calibrated overall but not within these strata is not calibrated. Returns an empty frame
    when the score table has no ``exposure`` column.
    """
    if "exposure" not in scores.columns or scores.empty:
        return pd.DataFrame(columns=PRECISION_COLUMNS)
    uniq = scores.drop_duplicates("row_id")["exposure"].to_numpy(float)
    inner = np.unique(np.quantile(uniq, np.linspace(0.0, 1.0, n_bins + 1)[1:-1]))
    rows = []
    for rung in sorted(scores["rung"].unique()):
        g = scores[scores["rung"] == rung]
        bin_of = np.searchsorted(inner, g["exposure"].to_numpy(float), side="right")
        for k in np.unique(bin_of):
            b = g[bin_of == k]
            rows.append({
                "rung": rung, "decile": 0, "exposure_lo": float(b["exposure"].min()), "exposure_hi": float(b["exposure"].max()),
                "n": int(len(b)), "mean_p_sig": float(b["p_sig"].mean()) if b["p_sig"].notna().any() else float("nan"),
                "event_rate": float(b["event"].astype(float).mean()),
                "coverage_90": float("nan") if b["lo90"].isna().all() else interval_coverage(b["y"], b["lo90"], b["hi90"]),
                "mean_s_star": float(b["s_star"].mean()) if "s_star" in b else float("nan"),
            })
    out = pd.DataFrame(rows, columns=PRECISION_COLUMNS)
    out["decile"] = out.groupby("rung").cumcount() + 1
    return out


# ------------------------------------------------- coverage by realized over planned precision
RATIO_COLUMNS = ["rung", "decile", "ratio_lo", "ratio_hi", "n", "mean_ratio", "coverage_80", "coverage_90", "event_rate", "mean_p_sig"]


def coverage_by_se_ratio(scores: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    """Coverage of the 80 and 90 percent intervals within deciles of the ratio of the realized to the planned standard error.

    The realized standard error depends on the exposure and on the realized click-through level, while the forecaster fixes the level at
    the cell median, so a forecast calibrated overall can be wrong in both directions inside strata of this ratio (round 00, R1). The
    ratio is ``s / s_star`` per scored row; the decile edges come from the distinct scored rows, so every rung is binned the same way.
    The ratio is an evaluation-time stratifier (it uses the realized ``s``) and never an input to a forecast. Per rung and decile:
    ``n``, the mean ratio, the 80 and 90 percent coverage of ``y`` (NaN for a rung without intervals), the event rate and the mean
    ``p_sig``. Returns an empty frame when the table has no ``s`` or ``s_star`` column.
    """
    if "s_star" not in scores.columns or "s" not in scores.columns or scores.empty:
        return pd.DataFrame(columns=RATIO_COLUMNS)
    uniq = scores.drop_duplicates("row_id")
    ratio_u = (uniq["s"] / uniq["s_star"]).to_numpy(float)
    inner = np.unique(np.quantile(ratio_u[np.isfinite(ratio_u)], np.linspace(0.0, 1.0, n_bins + 1)[1:-1]))
    rows = []
    for rung in sorted(scores["rung"].unique()):
        g = scores[scores["rung"] == rung]
        ratio = (g["s"] / g["s_star"]).to_numpy(float)
        bin_of = np.searchsorted(inner, ratio, side="right")
        for k in np.unique(bin_of):
            b = g[bin_of == k]
            r = ratio[bin_of == k]
            has80, has90 = not b["lo80"].isna().all(), not b["lo90"].isna().all()
            rows.append({
                "rung": rung, "decile": 0, "ratio_lo": float(r.min()), "ratio_hi": float(r.max()), "n": int(len(b)), "mean_ratio": float(r.mean()),
                "coverage_80": interval_coverage(b["y"], b["lo80"], b["hi80"]) if has80 else float("nan"),
                "coverage_90": interval_coverage(b["y"], b["lo90"], b["hi90"]) if has90 else float("nan"),
                "event_rate": float(b["event"].astype(float).mean()),
                "mean_p_sig": float(b["p_sig"].mean()) if b["p_sig"].notna().any() else float("nan"),
            })
    out = pd.DataFrame(rows, columns=RATIO_COLUMNS)
    out["decile"] = out.groupby("rung").cumcount() + 1
    return out


# --------------------------------------------------------------- split-half
def split_half(ledger: pd.DataFrame, origin=None) -> dict[str, dict[str, float]]:
    """P1 fit on odd and on even tests; the gap in (mu, tau) per cell at ``origin`` (default every admitted row).

    Tests are ordered by id and numbered; odd and even refer to that number. Parameters are the unpooled
    per-cell fit. A cell missing from either half is skipped.
    """
    rows = visible_rows(ledger, origin) if origin is not None else ledger.loc[ledger["status"] == ADMITTED]
    codes = pd.Series(pd.factorize(rows["test_id"], sort=True)[0], index=rows.index)
    fits = {k: P1Predictor().fit(rows[(codes % 2 == k).to_numpy()]) for k in (0, 1)}
    out: dict[str, dict[str, float]] = {}
    for cell in sorted(rows["cell"].unique()):
        try:
            odd, even = fits[1].fit_cell_params(cell), fits[0].fit_cell_params(cell)
        except KeyError:
            continue
        out[cell] = {"mu_odd": odd["mu"], "mu_even": even["mu"], "tau_odd": odd["tau"], "tau_even": even["tau"],
                     "mu_gap": abs(odd["mu"] - even["mu"]), "tau_gap": abs(odd["tau"] - even["tau"]),
                     "n_odd": odd["n"], "n_even": even["n"]}
    return out


# -------------------------------------------------------------------- gates
def _label_for(n: int, n_20: int, n_10: int) -> tuple[str, bool, bool]:
    d20, d10 = n >= n_20, n >= n_10
    if d20 and d10:
        label = "decidable at skill 0.20 and 0.10"
    elif d20:
        label = "decidable at skill 0.20 only"
    elif d10:
        label = "decidable at skill 0.10 only"
    else:
        label = "undecidable at this n"
    return label, bool(d20), bool(d10)


def gate_status(n: int, gates: dict) -> dict:
    """Decidability at a realized ``n``.

    ``gates`` is the dict ``simulate.load_gates`` returns: ``n_200`` and ``n_400`` at the decision target (the
    release gate) and, when present, ``by_target`` with the research screen. ``label`` applies the release gate;
    ``label_research`` applies the research screen's sizes (None when ``by_target`` is absent).
    """
    label, d20, d10 = _label_for(n, gates["n_200"], gates["n_400"])
    out = {"n": int(n), "decidable_at_0.20": d20, "decidable_at_0.10": d10, "label": label, "label_research": None}
    by_target = gates.get("by_target")
    if by_target:
        research = by_target[min(by_target, key=float)]
        out["label_research"] = _label_for(n, research["n_200"], research["n_400"])[0]
    return out


# -------------------------------------------------------------- abstention
def abstention_summary(scores: pd.DataFrame) -> pd.DataFrame:
    """Abstention rate and the count of rows that fired each trigger, per cell plus ``ALL``.

    Abstention is a property of the row, shared by every rung, so one rung is counted (``P2`` if present).
    """
    df = scores
    if "rung" in df.columns:
        rung = "P2" if (df["rung"] == "P2").any() else sorted(df["rung"].unique())[0]
        df = df[df["rung"] == rung]
    rows = []
    for cell, g in [("ALL", df)] + list(df.groupby("cell")):
        reasons = g["abstain_reasons"].fillna("").map(lambda r: set(filter(None, str(r).split(","))))
        row = {"cell": cell, "n": len(g), "rate": float(g["abstain"].mean()) if len(g) else float("nan")}
        for t in TRIGGERS:
            row[t] = int(reasons.map(lambda r, t=t: t in r).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def abstention_trigger_note(scores: pd.DataFrame) -> str:
    """One paragraph saying which abstention triggers never fired and whether drift ever did (builder call 49).

    Counts rows of the primary rung. ``Reliability`` rows at the first scored origin are the burn-in (no report exists yet);
    rows after it can only come from a stale or drifted report. A run that switched triggers off (``--drop-trigger``, recorded in
    ``scores.attrs["dropped_triggers"]``) says so first and leaves those triggers out of the "never fired" list.
    """
    df = scores
    if "rung" in df.columns:
        df = df[df["rung"] == ("P2" if (df["rung"] == "P2").any() else sorted(df["rung"].unique())[0])]
    dropped = [t for t in TRIGGERS if t in set(scores.attrs.get("dropped_triggers") or [])]
    reasons = df["abstain_reasons"].fillna("").map(lambda r: set(filter(None, str(r).split(","))))
    counts = {t: int(reasons.map(lambda r, t=t: t in r).sum()) for t in TRIGGERS}
    never = [t for t in TRIGGERS if counts[t] == 0 and t not in dropped]
    live = [t for t in TRIGGERS if t not in dropped]
    every = "All four" if not dropped else f"All {len(live)} remaining"
    head = f"Never fired in this backtest: {', '.join(never)}." if never else f"{every} triggers fired at least once."
    if dropped:
        head = f"Disabled for this run: {', '.join(sorted(dropped))}. " + head
    first = df["origin"].min()
    after = int((reasons.map(lambda r: "reliability" in r) & (df["origin"] > first)).sum())
    if "reliability" in dropped:
        return head
    tail = f" After the burn-in origin the reliability trigger fired on {after} rows"
    tail += ", so no cell was marked drifted and every reliability abstention is the missing report at the burn-in origin." if after == 0 else "."
    return head + tail


# ------------------------------------------------------------- aggregation
def _na(x) -> float | None:
    return None if x is None or not np.isfinite(x) else float(x)


def _bonferroni(est: float, draws: np.ndarray, family: int) -> tuple[float | None, float | None]:
    """Bonferroni-adjusted 90 percent bounds: the estimate plus or minus the bootstrap standard error times the quantile of ``1 - 0.05 / family``."""
    d = draws[np.isfinite(draws)]
    if not np.isfinite(est) or len(d) < 2 or family < 1:
        return None, None
    half = float(special.ndtri(1.0 - (1.0 - LEVEL) / 2.0 / family)) * float(np.std(d, ddof=1))
    return float(est - half), float(est + half)


def _group_table_impl(g: pd.DataFrame, base_sums: tuple[pd.DataFrame, str] | None, gates: dict, B: int, seed: int, family: int = 1) -> dict:
    """One row of the aggregate table for a (cell, rung) group.

    ``family`` is the number of intervals the table shows, for the Bonferroni-adjusted bounds (``adjusted_lo``, ``adjusted_hi`` for the
    Brier skill and ``logscore_adjusted_lo``, ``logscore_adjusted_hi`` for the log score).
    """
    n = len(g)
    ev = g["event"].to_numpy(float)
    cov80 = ((g["y"] >= g["lo80"]) & (g["y"] <= g["hi80"])).to_numpy(float)
    cov90 = ((g["y"] >= g["lo90"]) & (g["y"] <= g["hi90"])).to_numpy(float)
    cov80[g["lo80"].isna().to_numpy()] = np.nan          # a rung without an interval has no coverage, not zero coverage
    cov90[g["lo90"].isna().to_numpy()] = np.nan
    ab = g["abstain"].to_numpy(bool)
    keep = (~ab).astype(float)
    cols: dict[str, np.ndarray] = {
        "logscore": g["logscore"].to_numpy(float), "crps": g["crps"].to_numpy(float),
        "brier": g["brier_event"].to_numpy(float), "dir": g["direction_correct"].to_numpy(float),
        "cov80": cov80, "cov90": cov90, "abstain": ab.astype(float),
    }
    for k in ("logscore", "crps", "brier", "dir"):
        cols[k + "_na"] = cols[k] * keep
    cols["keep"] = keep
    if "brier_floor_row" in g.columns:
        cols["floor"], cols["ceiling"] = g["brier_floor_row"].to_numpy(float), g["dir_ceiling_row"].to_numpy(float)
    if "brier_base" in g.columns:
        cols["base"] = g["brier_base"].to_numpy(float)
    base_n = None if "base" in cols else base_sums
    ts = _TestSums(g, cols)
    counts = ts.resample_counts(B, np.random.default_rng(seed))
    den = counts @ ts.counts
    den_safe = np.where(den > 0, den, np.nan)
    den_keep = counts @ ts.sums["keep"]
    den_keep_safe = np.where(den_keep > 0, den_keep, np.nan)

    def mean_ci(name: str, na: bool = False):
        s = ts.sums[name]
        est = s.sum() / (ts.sums["keep"].sum() if na else ts.counts.sum()) if (ts.sums["keep"].sum() if na else ts.counts.sum()) > 0 else float("nan")
        draws = (counts @ s) / (den_keep_safe if na else den_safe)
        lo, hi = _percentile_interval(draws, LEVEL) if np.isfinite(draws).any() else (float("nan"), float("nan"))
        return float(est), lo, hi

    row: dict = {"n": n, "n_tests": ts.n_tests, "family_size": int(family)}
    for key, name in (("logscore", "logscore"), ("crps", "crps"), ("brier", "brier"), ("direction_accuracy", "dir"),
                      ("coverage_80", "cov80"), ("coverage_90", "cov90"), ("abstention_rate", "abstain")):
        est, lo, hi = mean_ci(name)
        row[key] = est
        if key != "abstention_rate":
            row[key + "_lo"], row[key + "_hi"] = lo, hi
        if key == "logscore":
            row["logscore_adjusted_lo"], row["logscore_adjusted_hi"] = _bonferroni(est, (counts @ ts.sums["logscore"]) / den_safe, family)
    # Brier skill against the base rate (call 1): 1 - Brier / Brier_base, resampled by test.
    if "base" in ts.sums:
        b_est, b0_est = ts.sums["brier"].sum() / ts.counts.sum(), ts.sums["base"].sum() / ts.counts.sum()
        draws = 1.0 - ((counts @ ts.sums["brier"]) / den_safe) / ((counts @ ts.sums["base"]) / den_safe)
        row["brier_base"] = float(b0_est)
    elif base_n is not None:
        p0_tab, _ = base_n
        t_idx = pd.Index(ts.tests)
        p0_sum = p0_tab["sum"].reindex(t_idx).fillna(0.0).to_numpy()
        p0_cnt = p0_tab["n"].reindex(t_idx).fillna(0.0).to_numpy()
        b_est = ts.sums["brier"].sum() / ts.counts.sum()
        b0_est = p0_sum.sum() / p0_cnt.sum() if p0_cnt.sum() > 0 else float("nan")
        d0 = counts @ p0_cnt
        draws = 1.0 - ((counts @ ts.sums["brier"]) / den_safe) / ((counts @ p0_sum) / np.where(d0 > 0, d0, np.nan))
        row["brier_base"] = float(b0_est)
    else:
        b_est, b0_est, draws = float("nan"), float("nan"), np.full(B, np.nan)
        row["brier_base"] = None
    row["brier_skill"] = _na(1.0 - b_est / b0_est) if np.isfinite(b0_est) and b0_est > 0 else None
    lo, hi = _percentile_interval(draws, LEVEL) if np.isfinite(draws).any() else (float("nan"), float("nan"))
    row["brier_skill_lo"], row["brier_skill_hi"] = _na(lo), _na(hi)
    row["adjusted_lo"], row["adjusted_hi"] = _bonferroni(row["brier_skill"] if row["brier_skill"] is not None else float("nan"), draws, family)
    if "floor" in ts.sums:
        row["brier_floor"] = float(ts.sums["floor"].sum() / ts.counts.sum())
        row["direction_ceiling"] = float(ts.sums["ceiling"].sum() / ts.counts.sum())
    # Non-abstained rows (call 2).
    n_na = int(keep.sum())
    row["n_nonabstained"] = n_na
    if n_na > 0:
        for key, name in (("logscore", "logscore_na"), ("crps", "crps_na"), ("brier", "brier_na"), ("direction_accuracy", "dir_na")):
            est, lo, hi = mean_ci(name, na=True)
            row[key + "_nonabstained"], row[key + "_nonabstained_lo"], row[key + "_nonabstained_hi"] = est, lo, hi
    # Calibration against the perfect-calibration null, clustered by test (call 172); the independent-rows percentile is kept beside it.
    fin = np.isfinite(g["p_sig"].to_numpy(float))
    if fin.sum() >= 2:
        p_f, e_f, t_f = g["p_sig"].to_numpy(float)[fin], ev[fin], g["test_id"].to_numpy()[fin]
        de = design_effect(p_f, e_f, t_f)
        row["ece"] = ece(p_f, e_f)
        row["ece_percentile"] = ece_percentile(p_f, e_f, draws=NULL_DRAWS, seed=seed, test_ids=t_f, icc=de["icc"])
        row["ece_percentile_independent"] = ece_percentile(p_f, e_f, draws=NULL_DRAWS, seed=seed)
        row["ece_equal_mass"] = ece_equal_mass(p_f, e_f)
        row["ece_equal_mass_percentile"] = ece_percentile(p_f, e_f, draws=NULL_DRAWS, seed=seed, test_ids=t_f, icc=de["icc"], equal_mass=True)
        row["design_effect"], row["icc"] = de["design_effect"], de["icc"]
    # Decisive rows: the direction of the estimate on rows whose result was significant either way (the pairwise accuracy of the
    # winner-prediction literature), beside the all-rows direction accuracy.
    if "s" in g.columns:
        dec = (np.abs(g["y"].to_numpy(float)) > Z * g["s"].to_numpy(float)) & np.isfinite(g["direction_correct"].to_numpy(float))
        row["n_decisive"] = int(dec.sum())
        row["direction_accuracy_decisive"] = float(g["direction_correct"].to_numpy(float)[dec].mean()) if dec.any() else None
    # Gates are read at the base rate nearest to this group's own event rate; the base rate 0.3 of the earlier gates stays beside them.
    sel = select_gates(gates, float(ev.mean()) if len(ev) else None)
    row["gate_base_rate"] = sel.get("base_rate")
    st = gate_status(n, sel)
    row["decidable"] = st["label"]
    row["decidable_research"] = st["label_research"]
    st_tests = gate_status(ts.n_tests, sel)
    row["decidable_by_tests"] = st_tests["label"]
    row["decidable_research_by_tests"] = st_tests["label_research"]
    legacy = select_gates(gates, LEGACY_BASE_RATE, exact=True)
    row["decidable_by_tests_base_0.3"] = gate_status(ts.n_tests, legacy)["label"] if legacy else None
    return row


def _group_table(*args, **kwargs) -> dict:
    """``_group_table_impl`` with the arithmetic warnings of empty or degenerate bootstrap draws silenced: a cell with no events has a
    zero base Brier score and a skill that is simply undefined, which the table records as None."""
    import warnings

    with np.errstate(divide="ignore", invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return _group_table_impl(*args, **kwargs)


def aggregate_scores(scores: pd.DataFrame, gates: dict, B: int = DEFAULT_B, seed: int = 0, family_size: int | None = None) -> pd.DataFrame:
    """Aggregate table per cell and rung (plus an ``ALL`` cell), with 90 percent by-test bootstrap intervals.

    Columns: n, n_tests, logscore, crps, brier, brier_skill, direction_accuracy, coverage_80, coverage_90,
    abstention_rate, each with ``_lo`` and ``_hi`` where an interval applies; the same scores on
    non-abstained rows (``*_nonabstained``); the Brier floor and direction ceiling from the shrunken
    posterior when the columns exist; ECE and its percentile in the null; and ``decidable`` from the gates.
    The Brier skill baseline is the ``brier_base`` column (the cell's significant-positive base rate, call 1)
    when present, otherwise the P0 rung's Brier score on the same tests. Every row also carries the Bonferroni-adjusted bounds for the
    family of ``family_size`` intervals (default: the number of (cell, rung) rows of the table), the design effect and the clustered
    ECE percentile, the decisive-row direction accuracy and the gate read at the base rate nearest to the group's own.
    """
    rows = []
    p0_by_cell: dict[str, pd.DataFrame] = {}
    if "brier_base" not in scores.columns and (scores["rung"] == "P0").any():
        p0 = scores[scores["rung"] == "P0"]
        for cell, g in [("ALL", p0)] + list(p0.groupby("cell")):
            grp = g.groupby("test_id")["brier_event"]
            p0_by_cell[cell] = pd.DataFrame({"sum": grp.sum(), "n": grp.size().astype(float)})
    family = (
        family_size if family_size is not None else int(sum(1 + scores.loc[scores["rung"] == r, "cell"].nunique() for r in scores["rung"].unique()))
    )
    for rung in sorted(scores["rung"].unique()):
        sr = scores[scores["rung"] == rung]
        for cell, g in [("ALL", sr)] + list(sr.groupby("cell")):
            base = (p0_by_cell[cell], "P0") if cell in p0_by_cell else None
            row = _group_table(g, base, gates, B, seed, family)
            rows.append({"cell": cell, "rung": rung, **row})
    out = pd.DataFrame(rows)
    order = {"ALL": 0}
    out["_c"] = out["cell"].map(lambda c: order.get(c, 1))
    return out.sort_values(["_c", "cell", "rung"]).drop(columns="_c").reset_index(drop=True)


def brier_skill_draws(g: pd.DataFrame, B: int = DEFAULT_B, seed: int = 0) -> np.ndarray:
    """Bootstrap-by-test draws of ``1 - Brier / Brier_base`` for one rung's rows (rows without a Brier score are left out).

    The same ``seed`` over the same tests gives the same resamples, so draws from several runs on one held-out set can be averaged.
    """
    g = g[np.isfinite(g["brier_event"].to_numpy(float))]
    if g.empty:
        return np.full(B, np.nan)
    ts = _TestSums(g, {"b": g["brier_event"].to_numpy(float), "base": g["brier_base"].to_numpy(float)})
    counts = ts.resample_counts(B, np.random.default_rng(seed))
    with np.errstate(invalid="ignore", divide="ignore"):
        return 1.0 - (counts @ ts.sums["b"]) / (counts @ ts.sums["base"])


YEAR_COLUMNS = ["n", "n_tests", "logscore", "logscore_lo", "logscore_hi", "logscore_adjusted_lo", "logscore_adjusted_hi", "brier_skill",
                "brier_skill_lo", "brier_skill_hi", "adjusted_lo", "adjusted_hi", "family_size",
                "direction_accuracy", "direction_accuracy_lo", "direction_accuracy_hi", "abstention_rate"]


def by_year(scores: pd.DataFrame, years, gates: dict, B: int = DEFAULT_B, seed: int = 0) -> pd.DataFrame:
    """The headline scores per calendar year, rung and cell (plus an ``ALL`` cell).

    ``years`` is one year per row of ``scores`` (the calendar year of the test's start, see ``report.row_years``). Every scored row
    falls in exactly one year, so the groups partition the rows of each rung. Each year is scored with ``aggregate_scores`` on its own
    rows (same definitions, same by-test bootstrap, same seed), so a year's numbers are those the full table would give on that slice.
    """
    years = pd.Series(np.asarray(years), index=scores.index)
    parts = []
    family = int(sum(1 + scores.loc[(scores["rung"] == r) & (years == y), "cell"].nunique() for y in years.unique() for r in scores["rung"].unique()
                     if ((scores["rung"] == r) & (years == y)).any()))
    for year in sorted(years.unique()):
        agg = aggregate_scores(scores[years == year], gates, B=B, seed=seed, family_size=family)
        keep = agg[["cell", "rung", *[c for c in YEAR_COLUMNS if c in agg.columns]]].copy()
        keep.insert(0, "year", int(year))
        parts.append(keep)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["year", "cell", "rung", *YEAR_COLUMNS])


RELEASED_COLUMNS = ["n", "n_tests", "logscore", "logscore_lo", "logscore_hi", "brier", "brier_skill", "brier_skill_lo", "brier_skill_hi",
                    "direction_accuracy", "direction_accuracy_lo", "direction_accuracy_hi"]


def released_rows(main_scores: pd.DataFrame, ablation_scores: pd.DataFrame, gates: dict, B: int = DEFAULT_B, seed: int = 0,
                  rung: str = "P2") -> list[dict]:
    """Scores of the rows a trigger-removal run releases: abstained under the full trigger set and issued under the ablation.

    Both tables must hold the same rows of ``rung`` with the same scores (abstention does not change a score, only whether the card
    is issued); a mismatch raises ValueError. Each row of the result is one cell (plus ``ALL``) with the same columns and the same
    by-test bootstrap as the aggregate table (n, n_tests, log score, Brier, Brier skill, direction accuracy with 90 percent
    intervals), plus the event rate and the mean ``p_sig`` of the released rows and how many rows each run abstained on. A run that
    releases nothing gives an ``ALL`` row with n = 0 and no scores.
    """
    m = main_scores[main_scores["rung"] == rung].set_index("row_id").sort_index()
    a = ablation_scores[ablation_scores["rung"] == rung].set_index("row_id").sort_index()
    if len(m) == 0 or not m.index.equals(a.index):
        raise ValueError(f"the main run and the ablation must hold the same rows of rung {rung} (main {len(m)}, ablation {len(a)})")
    if not np.allclose(m["logscore"].to_numpy(float), a["logscore"].to_numpy(float), rtol=0, atol=1e-9, equal_nan=True):
        raise ValueError("the main run and the ablation scored differently: they are not the same run apart from the dropped trigger")
    out_of = m["abstain"].to_numpy(bool) & ~a["abstain"].to_numpy(bool)
    rel = a[out_of].reset_index()
    base = {"rung": rung, "n_abstained_main": int(m["abstain"].sum()), "n_abstained_ablation": int(a["abstain"].sum()), "n_rows": int(len(m))}
    if rel.empty:
        empty = {k: (0 if k in ("n", "n_tests") else None) for k in RELEASED_COLUMNS}
        return [{"cell": "ALL", **base, **empty, "event_rate": None, "mean_p_sig": None}]
    agg = aggregate_scores(rel, gates, B=B, seed=seed)
    rows = []
    for _, r in agg.iterrows():
        g = rel if r["cell"] == "ALL" else rel[rel["cell"] == r["cell"]]
        rows.append({"cell": r["cell"], **base, **{k: r[k] for k in RELEASED_COLUMNS},
                     "event_rate": float(g["event"].mean()), "mean_p_sig": float(g["p_sig"].mean())})
    return rows


def by_origin(scores: pd.DataFrame, column: str = "logscore", B: int = BY_ORIGIN_RESAMPLES, seed: int = 0) -> pd.DataFrame:
    """Mean of ``column`` per origin and rung with a by-test 90 percent interval."""
    rows = []
    for (origin, rung), g in scores.groupby(["origin", "rung"], sort=True):
        if not g[column].notna().any():
            continue
        iv = bootstrap_by_test(g, column, B=B, seed=seed)
        rows.append({"origin": origin, "rung": rung, "n": len(g), column: iv.estimate, column + "_lo": iv.lo, column + "_hi": iv.hi})
    return pd.DataFrame(rows)
