"""X10 of the paper version 2 plan: does the predicted distribution improve the choice of test size? (design note: docs/superpowers/plans/2026-11-06-x10-sizing-design.md)

A concluded archive test ran once, at one size, so sizing cannot be replayed. Two things are measured instead.

Part A, ``sizing_assurance``: at the size a test actually had (its planned exposure, here the realized impressions), does the forecast probability of a
significant-positive result match the realized rate across exposure bins?

Part B, ``evaluate_test_and_roll``: the decision problem of Feit and Berman (Test & Roll, Marketing Science 2019). A page has ``N`` impressions. A test gives ``n``
impressions to each of the variant and the reference, and the arm with the higher observed rate is shown to the remaining ``N - 2 n``. With ``theta`` the true
difference in rate (variant minus reference) and ``theta_hat ~ Normal(theta, s_n^2)``, ``s_n^2 = 2 c (1 - c) / n`` for a reference rate ``c``, the expected
gain over always showing the reference is ``n theta + (N - 2 n) theta Phi(theta / s_n)``; the oracle gain is ``N max(theta, 0)``; regret is their difference.
Three rules choose ``n`` from data visible at the origin: the out-of-time P1 prior (maximize expected gain under the cell's Student-t prior), a zero-mean
normal prior matched to the visible significant-positive base rate, and a fixed power rule. Regret is measured exactly (a sum over a grid) in a world that is
not the prior: the nonparametric maximum likelihood distribution of the effects (Kiefer and Wolfowitz, by EM) of the rows scored at that origin and cell.

Units: ``theta`` and ``mu``, ``tau`` in percentage points of click-through rate (divided by 100 where a rate is needed); sizes in impressions per arm; gains in
clicks.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import special, stats

from mootcourt import scale
from mootcourt.config import Z
from mootcourt.ledger import ADMITTED, quarter_of, visible_rows

AUDIENCE_MULTIPLES = (5, 20, 100)
PRIMARY_MULTIPLE = 20
POWER_REL_LIFT = 0.10
POWER_LEVEL = 0.80
POWER_ALPHA = 0.05
WORLD_SCALES = (1.0, 0.67, 1.5)
MIN_UNIT_ROWS = 100
MIN_UNIT_SHARE = 0.5
SIMILAR_SIZES = 0.10
SIMILAR_SHARE = 0.80
GRID_POINTS = 4001
NPMLE_GRID = 200
NPMLE_ITERATIONS = 300
RULES = ("prior", "base_rate", "power")


# --------------------------------------------------------------------------------------------------------------------------------- the decision problem
def se_of_difference(n, c):
    """Standard error of the difference in rates with ``n`` impressions in each arm and reference rate ``c`` (equal rates under the null)."""
    return np.sqrt(2.0 * c * (1.0 - c) / np.asarray(n, dtype=float))


def expected_gain(theta_pp, weights, n, N: float, c: float) -> np.ndarray:
    """Expected gain over always showing the reference, in clicks, for each size in ``n`` (an array or a scalar), under effects ``theta_pp`` with ``weights``."""
    theta = np.asarray(theta_pp, float)[None, :] / 100.0
    n = np.atleast_1d(np.asarray(n, float))
    s_n = se_of_difference(n, c)[:, None]
    w = np.asarray(weights, float)[None, :]
    return (w * (n[:, None] * theta + (N - 2.0 * n[:, None]) * theta * special.ndtr(theta / s_n))).sum(axis=1)


def oracle_gain(theta_pp, weights, N: float) -> float:
    return float(N * np.sum(np.asarray(weights, float) * np.maximum(np.asarray(theta_pp, float) / 100.0, 0.0)))


def regret(theta_pp, weights, n, N: float, c: float) -> np.ndarray:
    return oracle_gain(theta_pp, weights, N) - expected_gain(theta_pp, weights, n, N, c)


def size_grid(N: float, points: int = 400) -> np.ndarray:
    """Sizes to search: a geometric grid from 1 to N / 2 impressions per arm."""
    top = max(int(N // 2), 1)
    return np.unique(np.round(np.geomspace(1, top, points)).astype(int))


def t_prior_grid(mu: float, tau: float, nu: float, points: int = GRID_POINTS, tail: float = 1e-7) -> tuple[np.ndarray, np.ndarray]:
    """A grid over a Student-t prior (location ``mu``, scale ``tau``, ``nu`` degrees of freedom; infinite is normal) with quadrature weights summing to one."""
    if tau <= 0:
        return np.array([mu]), np.array([1.0])
    dist = stats.norm if math.isinf(nu) else stats.t(df=nu)
    q = float(dist.ppf(1.0 - tail))
    x = np.linspace(-q, q, points)
    w = dist.pdf(x)
    return mu + tau * x, w / w.sum()


def optimal_size(theta_pp, weights, N: float, c: float) -> int:
    """The size on the grid that maximizes the expected gain under the prior (the smallest of equals)."""
    grid = size_grid(N)
    return int(grid[int(np.argmax(expected_gain(theta_pp, weights, grid, N, c)))])


def feige_mcdowell_size(N: float, s_over_sigma: float) -> float:
    """The closed-form size of the paper for a normal prior of equal arms: ``sqrt(N / 4 (s / sigma)^2 + (3 / 4 (s / sigma)^2)^2) - 3 / 4 (s / sigma)^2``,
    with ``s`` the standard deviation of one unit's response and ``sigma`` the prior standard deviation of one arm's mean."""
    r = s_over_sigma**2
    return math.sqrt(N / 4.0 * r + (0.75 * r) ** 2) - 0.75 * r


# ---------------------------------------------------------------------------------------------------------------------------------------- the three rules
def prior_rule_size(mu: float, tau: float, nu: float, N: float, c: float) -> int:
    theta, w = t_prior_grid(mu, tau, nu)
    return optimal_size(theta, w, N, c)


def base_rate_tau(base_rate: float, s_star_pp: float, z: float = Z) -> float:
    """The standard deviation (pp) of a zero-mean normal prior under which the significant-positive event ``y > z s_star`` has probability ``base_rate``.

    ``P(y > z s) = Phi(-z s / sqrt(tau^2 + s^2))``, so ``tau = s sqrt((z / z_b)^2 - 1)`` with ``z_b`` the normal quantile of ``1 - base_rate``. Defined when the
    base rate exceeds ``1 - Phi(z)`` (0.025); at or below it the prior has no spread and ``tau`` is 0."""
    if not 0.0 < base_rate < 1.0:
        return 0.0
    zb = float(special.ndtri(1.0 - base_rate))
    return float(s_star_pp * math.sqrt((z / zb) ** 2 - 1.0)) if 0.0 < zb < z else 0.0


def base_rate_rule_size(base_rate: float, s_star_pp: float, N: float, c: float) -> int:
    tau = base_rate_tau(base_rate, s_star_pp)
    if tau <= 0:
        return 1
    theta, w = t_prior_grid(0.0, tau, math.inf)
    return optimal_size(theta, w, N, c)


def power_rule_size(c: float, rel_lift: float = POWER_REL_LIFT, power: float = POWER_LEVEL, alpha: float = POWER_ALPHA) -> int:
    """Impressions per arm for a two-sided test at level ``alpha`` to have power ``power`` against a relative lift ``rel_lift`` on reference rate ``c``."""
    za, zb = float(special.ndtri(1.0 - alpha / 2.0)), float(special.ndtri(power))
    delta = rel_lift * c
    return int(math.ceil((za + zb) ** 2 * 2.0 * c * (1.0 - c) / delta**2))


# --------------------------------------------------------------------------------------------------------------------------------- the world: NPMLE of effects
def npmle(y, s, grid_points: int = NPMLE_GRID, iterations: int = NPMLE_ITERATIONS) -> tuple[np.ndarray, np.ndarray]:
    """Nonparametric maximum likelihood estimate of the distribution of true effects behind estimates ``y`` with known standard errors ``s``.

    Kiefer and Wolfowitz: weights on a fixed grid (the 0.5th to the 99.5th percentile of ``y``, zero included), found by EM. Returns ``(grid, weights)``."""
    y, s = np.asarray(y, float), np.asarray(s, float)
    lo, hi = np.percentile(y, [0.5, 99.5])
    lo, hi = min(lo, 0.0), max(hi, 0.0)
    if hi - lo < 1e-9:
        return np.array([0.0]), np.array([1.0])
    grid = np.linspace(lo, hi, grid_points)
    z = (y[:, None] - grid[None, :]) / s[:, None]
    lik = np.exp(-0.5 * z * z) / s[:, None]
    lik = lik / np.maximum(lik.max(axis=1, keepdims=True), 1e-300)  # a row-wise scale does not change the EM fixed point
    w = np.full(grid_points, 1.0 / grid_points)
    for _ in range(iterations):
        mix = lik @ w
        w = w * (lik / np.maximum(mix, 1e-300)[:, None]).mean(axis=0)
        w = w / w.sum()
    return grid, w


# ------------------------------------------------------------------------------------------------------------------------------------------ evaluation
def _rel(x: float, oracle: float) -> float:
    return x / oracle if oracle > 0 else float("nan")


def _unit_sizes(visible_cell: pd.DataFrame, mu: float, tau: float, nu: float, m: float) -> dict:
    """The audience, the reference rate and the three sizes of one origin and cell from the rows visible at the origin."""
    expo = scale.planned_exposure(visible_cell)
    n_med = float(np.median(expo))
    c = scale.lookup_ctr(scale.cell_median_ctr(visible_cell), str(visible_cell["cell"].iloc[0]))
    N = m * 2.0 * n_med
    s_star = float(scale.upworthy_s_star(n_med, n_med, c))
    base = float((visible_cell["y"].to_numpy(float) > Z * visible_cell["s"].to_numpy(float)).mean())
    cap = max(int(N // 2), 1)
    sizes = {
        "prior": min(prior_rule_size(mu, tau, nu, N, c), cap),
        "base_rate": min(base_rate_rule_size(base, s_star, N, c), cap),
        "power": min(power_rule_size(c), cap),
    }
    return {
        "N": N,
        "reference_rate": c,
        "median_exposure": n_med,
        "s_star_median_pp": s_star,
        "visible_base_rate": base,
        "sizes": sizes,
        "cap": cap,
        "prior": {"mu": mu, "tau": tau, "nu": None if math.isinf(nu) else nu},
    }


def _regrets(unit: dict, theta, w) -> dict:
    N, c = unit["N"], unit["reference_rate"]
    sizes = dict(unit["sizes"])
    sizes["never_test"] = 0
    sizes["test_everything"] = unit["cap"]
    orc = oracle_gain(theta, w, N)
    out = {"oracle_gain": orc}
    for name, n in sizes.items():
        out[name] = float(regret(theta, w, n, N, c)[0]) if n > 0 else float(orc)  # never testing gains nothing over the reference
    return out


def evaluate_test_and_roll(
    ledger: pd.DataFrame,
    scores: pd.DataFrame,
    *,
    multiples=AUDIENCE_MULTIPLES,
    B: int = 200,
    seed: int = 0,
    min_rows: int = MIN_UNIT_ROWS,
    level: float = 0.90,
) -> dict | None:
    """Part B: regret of the three sizing rules per origin and cell, pooled, with by-test intervals and the conditions under which the claim is dropped.

    ``scores`` is the main run's score table (rung P1's rows give the rows scored at each origin: their ``y``, ``s``, ``cell`` and ``test_id``); ``ledger`` is the
    source's ledger, from which the rows visible at each origin and the P1 prior of that origin are rebuilt. Returns None without the needed columns."""
    from mootcourt.predictors.p1 import P1Predictor

    need = {"origin", "cell", "test_id", "y", "s", "rung"}
    if not need <= set(scores.columns) or "source" not in ledger.columns:
        return None
    adm = ledger[ledger["status"] == ADMITTED]
    p1_scores = scores[scores["rung"] == "P1"]
    rng = np.random.default_rng(seed)
    units: dict[float, list[dict]] = {m: [] for m in multiples}
    skipped: list[dict] = []
    a = (1.0 - level) / 2.0
    for origin, g_o in p1_scores.groupby("origin", sort=True):
        vis = visible_rows(adm, origin)
        if vis.empty:
            continue
        p1 = P1Predictor().fit(vis, data_end=origin)
        for cell, g in g_o.groupby("cell", sort=True):
            vc = vis[vis["cell"] == cell]
            if len(g) < min_rows or len(vc) < 30:
                skipped.append(
                    {"origin": pd.Timestamp(origin).isoformat(), "cell": str(cell), "scored_rows": int(len(g)), "visible_rows": int(len(vc))}
                )
                continue
            par = p1.cell_params(str(cell), quarter_of(origin))
            theta, w = npmle(g["y"].to_numpy(float), g["s"].to_numpy(float))
            codes, tests = pd.factorize(g["test_id"])
            idx_by_test = [np.flatnonzero(codes == k) for k in range(len(tests))]
            boot = []
            ys, ss = g["y"].to_numpy(float), g["s"].to_numpy(float)
            for _ in range(B):
                pick = rng.integers(0, len(tests), len(tests))
                rows = np.concatenate([idx_by_test[k] for k in pick])
                boot.append(npmle(ys[rows], ss[rows]))
            for m in multiples:
                unit = _unit_sizes(vc, par["mu"], par["tau"], par["nu"], m)
                worlds = {}
                for sc in WORLD_SCALES:
                    worlds[f"x{sc:g}"] = _regrets(unit, theta * sc, w)
                draws = [_regrets(unit, th, wt) for th, wt in boot]
                units[m].append(
                    {
                        "origin": pd.Timestamp(origin).isoformat(),
                        "cell": str(cell),
                        "scored_rows": int(len(g)),
                        "scored_tests": int(len(tests)),
                        **unit,
                        "regret": worlds,
                        "boot": draws,
                    }
                )
    out: dict = {
        "audience_multiples": list(multiples),
        "primary_multiple": PRIMARY_MULTIPLE,
        "bootstrap_resamples": B,
        "level": level,
        "seed": seed,
        "rules": list(RULES),
        "anchors": ["never_test", "test_everything"],
        "world_scales": [f"x{s:g}" for s in WORLD_SCALES],
        "units_skipped": skipped,
        "min_unit_rows": min_rows,
        "definition": "relative regret = sum over units of (oracle gain - expected gain) over the sum of oracle gains, in the world of the rows scored at the "
        "origin and cell (nonparametric maximum likelihood effect distribution); sizes come from rows visible at the origin only",
        "by_audience": {},
    }
    for m, us in units.items():
        if not us:
            continue
        pooled = {}
        names = list(RULES) + ["never_test", "test_everything"]
        for wname in [f"x{s:g}" for s in WORLD_SCALES]:
            tot_o = sum(u["regret"][wname]["oracle_gain"] for u in us)
            pooled[wname] = {r: _rel(sum(u["regret"][wname][r] for u in us), tot_o) for r in names}
        # intervals in the primary world: the draws refit the world on by-test resamples of each unit
        B_eff = len(us[0]["boot"])
        tot_o_d = np.array([sum(u["boot"][b]["oracle_gain"] for u in us) for b in range(B_eff)])
        draws = {r: np.array([sum(u["boot"][b][r] for u in us) for b in range(B_eff)]) / tot_o_d for r in names}
        est_o = sum(u["regret"]["x1"]["oracle_gain"] for u in us)
        est = {r: sum(u["regret"]["x1"][r] for u in us) / est_o for r in names}

        def pack(point, d):
            d = d[np.isfinite(d)]
            lo, hi = (float(x) for x in np.percentile(d, [100 * a, 100 * (1 - a)])) if len(d) > 1 else (None, None)
            return {"estimate": float(point), "lo": lo, "hi": hi, "se": float(np.std(d, ddof=1)) if len(d) > 1 else None}

        family = 2
        zq = float(special.ndtri(1.0 - (1.0 - level) / 2.0 / family))
        diffs = {}
        for left, right in (("prior", "base_rate"), ("prior", "power"), ("base_rate", "power")):
            d = pack(est[left] - est[right], draws[left] - draws[right])
            if (left, right) in (("prior", "base_rate"), ("prior", "power")) and d["se"] is not None:
                d["adjusted_lo"], d["adjusted_hi"], d["family_size"] = d["estimate"] - zq * d["se"], d["estimate"] + zq * d["se"], family
            diffs[f"{left}_minus_{right}"] = d
        sizes = np.array([[u["sizes"][r] for r in RULES] for u in us], float)
        spread = sizes.max(axis=1) / np.maximum(sizes.min(axis=1), 1.0)
        out["by_audience"][str(m)] = {
            "units": len(us),
            "pooled_relative_regret": pooled,
            "relative_regret_with_interval": {r: pack(est[r], draws[r]) for r in names},
            "paired_differences": diffs,
            "share_of_units_with_sizes_within_10_percent": float((spread <= 1.0 + SIMILAR_SIZES).mean()),
            "median_sizes": {r: float(np.median(sizes[:, i])) for i, r in enumerate(RULES)},
            "units_table": [{k: v for k, v in u.items() if k != "boot"} for u in us],
        }
    prim = out["by_audience"].get(str(PRIMARY_MULTIPLE))
    n_ok = prim["units"] if prim is not None else 0
    n_all = n_ok + len(skipped)
    feas = {
        "units_after_the_date_rule": n_all,
        "units_with_100_or_more_scored_rows": n_ok,
        "fewer_than_half_of_units_have_100_rows": bool(n_ok < MIN_UNIT_SHARE * n_all) if n_all else True,
        "sizes_within_10_percent_in_over_80_percent_of_units": bool(prim is not None and prim["share_of_units_with_sizes_within_10_percent"] > SIMILAR_SHARE),
    }
    not_evaluated = bool(feas["fewer_than_half_of_units_have_100_rows"] or feas["sizes_within_10_percent_in_over_80_percent_of_units"])
    claim = {"feasibility_failures": feas, "not_evaluated": not_evaluated}
    if not not_evaluated:
        d = prim["paired_differences"]
        straddle = lambda x: x.get("adjusted_lo") is None or (x["adjusted_lo"] <= 0.0 <= x["adjusted_hi"])  # noqa: E731
        null = bool(straddle(d["prior_minus_base_rate"]) and straddle(d["prior_minus_power"]))
        claim["prior_advantage_adjusted_interval_contains_zero_against_both"] = null
        claim["verdict"] = "evaluated; no measurable sizing advantage" if null else "evaluated; the prior rule's regret differs from a simpler rule's"
    else:
        claim["verdict"] = "not evaluated"
    claim["note"] = "regret differences are negative when the first rule costs less. A null is a result: it is reported as evaluated, not as not evaluated."
    out["claim"] = claim
    out["horizon_note"] = (
        "N is a synthetic horizon in impressions, a multiple of the cell's test scale; there is no money. The nonparametric world is fitted to the rows "
        "scored at that origin and cell, so regret measures each rule against what happened later; the 0.67 and 1.5 worlds are printed beside the main one."
    )
    return out


def sizing_assurance(
    scores: pd.DataFrame, *, rungs=("P0", "P1", "P2", "text_lr"), n_bins: int = 5, B: int = 500, seed: int = 0, level: float = 0.90
) -> dict | None:
    """Part A: by exposure bin, the forecast probability of a significant-positive result against the realized rate, out of time.

    Five equal-mass bins of the row's planned exposure, pooled and within each cell; per bin the rows, tests, mean exposure, mean forecast, realized rate and the
    difference (realized minus forecast) with a by-test interval; per rung one slope of that difference on standardized log exposure with a by-test interval."""
    need = {"exposure", "p_sig", "event", "test_id", "rung", "cell"}
    if not need <= set(scores.columns):
        return None
    a = (1.0 - level) / 2.0
    out: dict = {
        "n_bins": n_bins,
        "bootstrap_resamples": B,
        "level": level,
        "caveat": "the planned exposure of an archive row is its realized impressions, a stand-in; X3 reports what fixing it at the cell median does",
        "rungs": {},
    }
    for rung in rungs:
        g_all = scores[(scores["rung"] == rung) & scores["p_sig"].notna()]
        if g_all.empty:
            continue
        block = {}
        for label, g in [("ALL", g_all)] + [(str(c), h) for c, h in g_all.groupby("cell")]:
            if len(g) < 50 * n_bins:
                continue
            expo = g["exposure"].to_numpy(float)
            lx = np.log(np.maximum(expo, 1.0))
            bins = np.minimum((pd.Series(expo).rank(method="first").to_numpy() - 1) * n_bins // len(g), n_bins - 1).astype(int)
            codes, tests = pd.factorize(g["test_id"])
            rng = np.random.default_rng(seed)
            counts = rng.multinomial(len(tests), np.full(len(tests), 1.0 / len(tests)), size=B).astype(float)
            p, e = g["p_sig"].to_numpy(float), g["event"].to_numpy(float)
            rows = []
            for b in range(n_bins):
                m = bins == b
                nn = np.bincount(codes[m], minlength=len(tests)).astype(float)
                pe = np.bincount(codes[m], weights=e[m], minlength=len(tests))
                pp = np.bincount(codes[m], weights=p[m], minlength=len(tests))
                with np.errstate(invalid="ignore", divide="ignore"):
                    gap = (counts @ pe - counts @ pp) / (counts @ nn)
                gap = gap[np.isfinite(gap)]
                lo, hi = (float(x) for x in np.percentile(gap, [100 * a, 100 * (1 - a)])) if len(gap) > 1 else (None, None)
                rows.append(
                    {
                        "bin": b,
                        "rows": int(m.sum()),
                        "tests": int((nn > 0).sum()),
                        "mean_exposure": float(expo[m].mean()),
                        "mean_forecast": float(p[m].mean()),
                        "realized_rate": float(e[m].mean()),
                        "gap": float(e[m].mean() - p[m].mean()),
                        "gap_lo": lo,
                        "gap_hi": hi,
                    }
                )
            xs = (lx - lx.mean()) / (lx.std() if lx.std() > 0 else 1.0)
            r = e - p

            def slope(w):
                sw = w.sum()
                mx, mr = (w * xs).sum() / sw, (w * r).sum() / sw
                vx = (w * (xs - mx) ** 2).sum() / sw
                return float((w * (xs - mx) * (r - mr)).sum() / sw / vx) if vx > 0 else float("nan")

            est = slope(np.ones(len(g)))
            sl = np.array([slope(counts[b][codes]) for b in range(min(B, 300))])
            sl = sl[np.isfinite(sl)]
            lo, hi = (float(x) for x in np.percentile(sl, [100 * a, 100 * (1 - a)])) if len(sl) > 1 else (None, None)
            block[label] = {"bins": rows, "slope_gap_on_standardized_log_exposure": {"estimate": est, "lo": lo, "hi": hi}}
        out["rungs"][rung] = block
    return out if out["rungs"] else None


def sizing_evaluation(ledger: pd.DataFrame, scores: pd.DataFrame, *, B: int = 200, seed: int = 0, assurance_only: bool = False) -> dict | None:
    """The report key ``sizing_evaluation``: part A and, unless ``assurance_only``, part B."""
    part_a = sizing_assurance(scores, seed=seed)
    if part_a is None:
        return None
    return {
        "design_note": "docs/superpowers/plans/2026-11-06-x10-sizing-design.md",
        "assurance_by_exposure": part_a,
        "test_and_roll": None if assurance_only else evaluate_test_and_roll(ledger, scores, B=B, seed=seed),
    }
