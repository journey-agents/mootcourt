"""Four ways to align the panel with earlier results. Each reads stored panel answers and makes no call.

At every scored origin a method is refitted on the units that a forecast standing at that origin may see: units of an
earlier origin whose result was in hand by the origin. ``visible_before`` is the one place that rule lives, and every
fit takes its training rows through it. At the first origin nothing is visible, so every method returns the plain
panel there.

1. ``direction_map``: a logistic regression of the observed direction on the panel difference.
2. ``reader_weights``: weights over the ten readers, fitted to the click counts of earlier arms.
3. ``audience_matching``: weights chosen only to match the mean click level, with no use of which arm won.
4. ``error_correction``: a map from panel score to click rate, then a linear correction on four traits of a headline.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, softmax
from sklearn.linear_model import LogisticRegression

from mootcourt.simulators.readers.panel import direction_frame, directions, panel_scores
from mootcourt.simulators.readers.protocol import N_READERS

SCALE = 10.0                    # a centred reader score is divided by this before any fit
WEIGHT_PENALTY = 1.0            # method 2: strength of the pull toward equal weights
MATCH_PENALTY = 0.01            # method 3: the same pull
EQUAL = 1.0 / N_READERS
_YOU = re.compile(r"\byou\b", re.I)


def visible_before(frame: pd.DataFrame, origin) -> pd.DataFrame:
    """Rows of an earlier origin whose result was usable by ``origin``: ``origin < origin`` and ``usable_after <= origin``."""
    at = pd.Timestamp(origin)
    return frame[(frame["origin"] < at) & (frame["usable_after"] <= at)]


def traits(headline: str) -> np.ndarray:
    """Four fixed traits: the count of words, a question mark, a digit, and the word "you"."""
    return np.array([float(len(headline.split())), float("?" in headline), float(any(c.isdigit() for c in headline)),
                     float(bool(_YOU.search(headline)))])


def _origins(contrasts: pd.DataFrame) -> list[tuple[int, pd.Timestamp]]:
    first = contrasts.groupby("origin_index")["origin"].first()
    return [(int(i), o) for i, o in first.items()]


def _reader_matrix(reader_scores: pd.DataFrame, column: str) -> pd.DataFrame:
    """Arms by readers, for the arms that all ten readers scored."""
    wide = reader_scores.pivot(index="arm_id", columns="reader", values=column).reindex(columns=range(1, N_READERS + 1))
    return wide.dropna()


def direction_map(arms: pd.DataFrame, contrasts: pd.DataFrame, reader_scores: pd.DataFrame) -> pd.DataFrame:
    """Method 1. Per contrast: ``p_variant``, the probability that the variant wins, ``base`` and ``correct``.

    ``base`` is the share of visible earlier contrasts that the variant won. Both are NaN at the first origin, where the
    plain panel's direction is returned.
    """
    contrasts = contrasts.reset_index(drop=True)
    out = directions(contrasts, panel_scores(reader_scores))
    x = out["diff"].to_numpy() / SCALE
    won = (contrasts["y"] > 0).to_numpy()
    y = contrasts["y"].to_numpy(dtype=float)
    p_variant, base = np.full(len(contrasts), np.nan), np.full(len(contrasts), np.nan)
    correct, tie = out["correct"].to_numpy().copy(), out["tie"].to_numpy().copy()
    for index, origin in _origins(contrasts):
        seen = np.zeros(len(contrasts), dtype=bool)
        seen[visible_before(contrasts, origin).index] = True
        scored = (contrasts["origin_index"] == index).to_numpy()
        if not seen.any():
            continue
        base[scored] = won[seen].mean()
        fit_on = seen & ~np.isnan(x)
        has = scored & ~np.isnan(x)
        if not fit_on.any():
            continue
        if len(set(won[fit_on])) < 2:
            p = np.full(int(has.sum()), float(won[fit_on][0]))
        else:
            model = LogisticRegression(C=1.0, max_iter=500).fit(x[fit_on].reshape(-1, 1), won[fit_on])
            p = model.predict_proba(x[has].reshape(-1, 1))[:, 1]
        p_variant[has] = p
        tie[has] = p == 0.5
        correct[has] = np.where(p == 0.5, 0.5, ((p > 0.5) == (y[has] > 0)).astype(float))
    return out.assign(p_variant=p_variant, base=base, correct=correct, tie=tie)


def brier_skill(contrasts: pd.DataFrame, mapped: pd.DataFrame) -> float:
    """One minus the Brier score of ``p_variant`` over that of ``base``, on the contrasts after the first origin that have both."""
    e = (contrasts["y"] > 0).to_numpy(dtype=float)
    p, base = mapped["p_variant"].to_numpy(), mapped["base"].to_numpy()
    use = ~np.isnan(p) & ~np.isnan(base)
    reference = float(((base[use] - e[use]) ** 2).sum())
    return float(1 - ((p[use] - e[use]) ** 2).sum() / reference) if reference > 0 else float("nan")


def _fit_reader_weights(x: np.ndarray, clicks: np.ndarray, impressions: np.ndarray) -> dict:
    """Minimise the mean negative binomial log likelihood per arm plus the pull toward equal weights."""
    n_arms = len(clicks)

    def objective(theta):
        w, a, b = softmax(theta[:N_READERS]), theta[N_READERS], np.exp(theta[N_READERS + 1])
        mean = x @ w
        eta = a + b * mean
        loss = (clicks * np.logaddexp(0, -eta) + (impressions - clicks) * np.logaddexp(0, eta)).sum() / n_arms
        d_eta = (impressions * expit(eta) - clicks) / n_arms
        d_w = b * (x.T @ d_eta) + 2 * WEIGHT_PENALTY * (w - EQUAL)
        d_u = w * (d_w - w @ d_w)
        grad = np.concatenate([d_u, [d_eta.sum(), b * (d_eta @ mean)]])
        return loss + WEIGHT_PENALTY * ((w - EQUAL) ** 2).sum(), grad

    rate = clicks.sum() / impressions.sum()
    start = np.concatenate([np.zeros(N_READERS), [np.log(rate / (1 - rate)), np.log(0.1)]])
    best = minimize(objective, start, jac=True, method="L-BFGS-B")
    return {"weights": [float(v) for v in softmax(best.x[:N_READERS])], "intercept": float(best.x[N_READERS]),
            "slope": float(np.exp(best.x[N_READERS + 1])), "n_arms": int(n_arms)}


def _fit_audience_matching(levels: np.ndarray, target: float, n_arms: int) -> dict:
    def objective(u):
        w = softmax(u)
        gap = w @ levels - target
        d_w = 2 * gap * levels + 2 * MATCH_PENALTY * (w - EQUAL)
        return gap ** 2 + MATCH_PENALTY * ((w - EQUAL) ** 2).sum(), w * (d_w - w @ d_w)

    best = minimize(objective, np.zeros(N_READERS), jac=True, method="L-BFGS-B")
    w = softmax(best.x)
    return {"weights": [float(v) for v in w], "panel_level": float(w @ levels), "click_rate": float(target), "n_arms": int(n_arms)}


def _weighted(arms, contrasts, reader_scores, fit_at_origin) -> tuple[pd.DataFrame, dict]:
    """Shared by methods 2 and 3: weights fitted per origin, then the weighted panel difference of that origin's contrasts."""
    diff = directions(contrasts, panel_scores(reader_scores))["diff"].to_numpy().copy()
    fits = {}
    for index, origin in _origins(contrasts):
        train = visible_before(arms, origin)
        if train.empty:
            continue
        fit = fit_at_origin(train.set_index("arm_id"))
        if fit is None:
            continue
        fits[index] = fit
        scored = contrasts[contrasts["origin_index"] == index]
        score = panel_scores(reader_scores, weights=np.array(fit["weights"]))
        diff[scored.index] = (scored["arm_id"].map(score) - scored["ref_arm_id"].map(score)).to_numpy(dtype=float)
    return direction_frame(contrasts, diff), fits


def reader_weights(arms: pd.DataFrame, contrasts: pd.DataFrame, reader_scores: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Method 2. Per contrast ``diff`` and ``correct``; the dict maps an origin index to the weights, intercept and slope."""
    centred = _reader_matrix(reader_scores, "centred") / SCALE

    def fit(train: pd.DataFrame):
        both = train.join(centred, how="inner")
        if both.empty:
            return None
        return _fit_reader_weights(both[list(centred.columns)].to_numpy(dtype=float), both["clicks"].to_numpy(dtype=float),
                                   both["impressions"].to_numpy(dtype=float))

    return _weighted(arms, contrasts.reset_index(drop=True), reader_scores, fit)


def audience_matching(arms: pd.DataFrame, contrasts: pd.DataFrame, reader_scores: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Method 3. Weights that bring the panel's mean click level to the mean click rate of earlier arms. No direction enters."""
    raw = _reader_matrix(reader_scores, "raw") / 100.0

    def fit(train: pd.DataFrame):
        both = train.join(raw, how="inner")
        if both.empty:
            return None
        levels = both[list(raw.columns)].to_numpy(dtype=float).mean(axis=0)
        return _fit_audience_matching(levels, float(both["clicks"].sum() / both["impressions"].sum()), len(both))

    return _weighted(arms, contrasts.reset_index(drop=True), reader_scores, fit)


def error_correction(arms: pd.DataFrame, contrasts: pd.DataFrame, reader_scores: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Method 4. A logistic curve from panel score to click rate, then a correction of its error on four traits."""
    contrasts = contrasts.reset_index(drop=True)
    score = panel_scores(reader_scores) / SCALE
    diff = directions(contrasts, panel_scores(reader_scores))["diff"].to_numpy().copy()
    by_arm = arms.set_index("arm_id")
    design = pd.DataFrame(np.column_stack([np.ones(len(by_arm)), np.vstack([traits(h) for h in by_arm["headline"]])]),
                          index=by_arm.index)
    fits = {}
    for index, origin in _origins(contrasts):
        train = visible_before(arms, origin).set_index("arm_id").join(score, how="inner")
        if train.empty:
            continue
        clicks, impressions = train["clicks"].to_numpy(dtype=float), train["impressions"].to_numpy(dtype=float)
        if clicks.sum() == 0 or clicks.sum() == impressions.sum():
            continue
        s = train["score"].to_numpy(dtype=float).reshape(-1, 1)
        curve = LogisticRegression(C=1e6, max_iter=1000).fit(
            np.vstack([s, s]), np.concatenate([np.ones(len(s)), np.zeros(len(s))]),
            sample_weight=np.concatenate([clicks, impressions - clicks]))
        error = clicks / impressions - curve.predict_proba(s)[:, 1]
        root = np.sqrt(impressions)
        beta, *_ = np.linalg.lstsq(design.loc[train.index].to_numpy() * root[:, None], error * root, rcond=None)
        fits[index] = {"curve_intercept": float(curve.intercept_[0]), "curve_slope": float(curve.coef_[0, 0]),
                       "correction": [float(v) for v in beta], "n_arms": int(len(train))}

        scored = contrasts[contrasts["origin_index"] == index]
        wanted = score.reindex(pd.unique(scored[["arm_id", "ref_arm_id"]].to_numpy().ravel())).dropna()
        corrected = pd.Series(curve.predict_proba(wanted.to_numpy().reshape(-1, 1))[:, 1] + design.loc[wanted.index].to_numpy() @ beta,
                              index=wanted.index)
        diff[scored.index] = (scored["arm_id"].map(corrected) - scored["ref_arm_id"].map(corrected)).to_numpy(dtype=float)
    return direction_frame(contrasts, diff), fits
