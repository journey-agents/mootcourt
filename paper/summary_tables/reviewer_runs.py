"""Tables of the reviewer runs of 13 November 2026 (docs/superpowers/plans/2026-11-13-reviewer-runs.md), one function per table.

Every cell comes from a report key of the reports those runs added to the run folder. A report that is missing stops the build.
"""
from summary_tables import Raw, Table, derived, month_year, n, v
from summary_tables.experiments import MAIN, sci

SIZE = "calibration-null-size-upworthy-*.json"
SEEDS = "positive-control-seeds.json"
ORIGINS = "learning-curve-origins/learning-curve-origins-upworthy-*.json"
STRATA = (("all cells", "ALL"), ("headline-only", "headline_only"), ("image-only", "image_only"), ("smallest", "both"))


def calibration_size(r):
    """Part A: how often the calibration procedure rejects forecasts that are calibrated by construction, at the observed within-test correlation."""
    rep, main = r(SIZE), r(MAIN)

    def row(rung, label, stratum):
        at = f"rows[rung={rung},stratum={stratum},binning=equal_width,truth=observed]"
        observed = f"tables.aggregate[cell={stratum},rung={rung}].ece_percentile"
        if abs(rep.get(f"{at}.observed_percentile") - main.get(observed)) > 1e-9:
            raise ValueError(f"{rung} {stratum}: the size script does not reproduce the report's calibration percentile")
        zero = f"rows[rung={rung},stratum={stratum},binning=equal_width,truth=zero]"
        double = f"rows[rung={rung},stratum={stratum},binning=equal_width,truth=double]"
        return [f"{rung}, {label}", v(rep, f"{at}.rho_observed", 2), sci(rep, at, "reject_95", 4, "reject_95_lo", "reject_95_hi"),
                v(rep, f"{zero}.reject_95", 3), v(rep, f"{double}.reject_95", 3), v(rep, f"{at}.critical_95", 1), v(main, observed, 1)]

    rows = []
    for rung in ("P0", "P1", "P2"):
        rows += [row(rung, label, stratum) for label, stratum in STRATA]
        if rung != "P2":
            rows.append(Raw(r"\midrule"))
    return Table("fmt-calibration-size", "lrrrrrr",
                 ["rung and stratum & latent & rejection share at & rejection share, & rejection share, & 95th percentile & percentile",
                  r" & correlation & that correlation (95\%) & no correlation & twice the correlation & under calibration & observed"], rows)


def control_seeds(r):
    """Part B: the planted control at five ledger seeds, 11,100 tests and a planted lift of one percent."""
    rep = r(SEEDS)
    seeds = [s["seed"] for s in rep.get("by_seed")]
    if rep.get("seeds") != len(seeds):
        raise ValueError("the seeds report's count differs from its rows")
    lo, hi = rep.get("real_interval.lo"), rep.get("real_interval.hi")

    def cells(at):
        return [v(rep, f"{at}.oracle_gain", 4), v(rep, f"{at}.p2_gain", 4), v(rep, f"{at}.recovered_pooled", 2),
                v(rep, f"{at}.recovered_headline_only", 2), v(rep, f"{at}.p2_minus_p1_headline_only", 4)]

    def seed_row(seed):
        at = f"by_seed[seed={seed}]"
        d = rep.get(f"{at}.p2_minus_p1_headline_only")
        inside = derived("yes" if lo <= d <= hi else "no", rep.ref(f"{at}.p2_minus_p1_headline_only"), rep.ref("real_interval.lo"),
                         rep.ref("real_interval.hi"))
        return [f"seed {seed}", *cells(at), v(rep, f"{at}.share_pairs_admitted", 2), inside]

    def stat_row(label, key):
        return [label, *cells(key), v(rep, f"{key}.share_pairs_admitted", 2), ""]

    count = sum(1 for s in rep.get("by_seed") if lo <= s["p2_minus_p1_headline_only"] <= hi)
    if count != rep.get("inside_real_interval"):
        raise ValueError("the count of seeds inside the real interval differs from the rows")
    return Table("fmt-control-seeds", "lrrrrrrl",
                 ["ledger & oracle minus P1 & P2 minus P1 & share recovered, & share recovered, & P2 minus P1, & pairs & inside the real",
                  " & (nats) & (nats) & pooled & headline-only & headline-only (nats) & admitted & interval"],
                 [*(seed_row(s) for s in seeds), Raw(r"\midrule"), stat_row("median", "median"), stat_row("smallest", "min"),
                  stat_row("largest", "max")])


def learning_origins(r):
    """Part D: P1 fitted on a quarter and on a half of the history against P1 fitted on all of it, at each scored origin."""
    rep = r(ORIGINS)
    origins = [row["origin"] for row in rep.get("rows")]

    def part(origin, name, field, nd, lo, hi):
        at = f"rows[origin={origin}].{name}"
        if not rep.get(f"{at}.fitted"):
            return derived("not fitted", rep.ref(f"{at}.fitted"))
        return sci(rep, at, field, nd, lo, hi)

    def row(origin):
        at = f"rows[origin={origin}]"
        return [month_year(origin), n(rep, f"{at}.heldout_rows"), part(origin, "quarter", "log_diff", 4, "log_lo", "log_hi"),
                part(origin, "half", "log_diff", 4, "log_lo", "log_hi"), part(origin, "quarter", "brier_diff", 5, "brier_lo", "brier_hi"),
                part(origin, "half", "brier_diff", 5, "brier_lo", "brier_hi")]

    return Table("fmt-learning-origins", "lrrrrr",
                 ["origin & held-out & log score, a quarter of the & log score, half of the & Brier gain, a quarter of the & Brier gain, half of the",
                  r" & rows & history minus all of it (90\%) & history minus all of it (90\%) & history over all of it (90\%) & history over all of it (90\%)"],
                 [row(o) for o in origins])


def horizon(r):
    """Run 9, Part B: the ladder with each test's end assumed 7 (the main run), 14 and 28 days after its last arm was created. The column
    without the first origin was added after the 28-day result was seen."""
    runs = (("7 (main run)", r(MAIN), r("by-origin-upworthy-*.json")),
            ("14", r("horizon-14/backtest-upworthy-*.json"), r("horizon-14/by-origin-upworthy-*.json")),
            ("28", r("horizon-28/backtest-upworthy-*.json"), r("horizon-28/by-origin-upworthy-*.json")))
    p0, p1 = "tables.aggregate[cell=ALL,rung=P0]", "tables.aggregate[cell=ALL,rung=P1]"

    def row(label, back, origins):
        if abs(origins.get("pooled.difference") + back.get(f"{p0}.logscore_vs_p1")) > 1e-9:
            raise ValueError(f"{origins.name} does not reproduce the pooled difference of {back.name}")
        first = min(o["left_out"] for o in origins.get("leave_one_origin_out"))
        return [label, n(back, f"{p1}.n_tests"), n(back, f"{p1}.n"), sci(back, p0, "logscore_vs_p1", 4, "logscore_vs_p1_lo", "logscore_vs_p1_hi", neg=True),
                sci(origins, f"leave_one_origin_out[left_out={first}]", "difference", 4),
                sci(back, p1, "brier_skill", 4, "brier_skill_lo", "brier_skill_hi")]

    return Table("fmt-horizon", "lrrrrr",
                 ["assumed end, days after & tests & rows & P1 minus P0, & the same, without & P1 Brier skill",
                  r"the last arm was created & & & log score (90\%) & the first origin (90\%) & (90\%)"],
                 [row(*run) for run in runs])


TABLES = [calibration_size, control_seeds, learning_origins, horizon]
