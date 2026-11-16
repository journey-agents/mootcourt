"""The two tables of the registered confirmatory analysis (docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md, sections "Part C" and
"Registration of the confirmatory reading"): each reading on the exploratory split and on the confirmatory split, side by side.

The exploratory column reads the run folder the build is given, as every other table does. The confirmatory column reads ``RUN10``, an
explicit folder, so that ``make tables RUN=...`` can never point it at another run. A verdict word is chosen by code from the registered rule
and names the report keys that chose it.
"""
from pathlib import Path

from summary_tables import Raw, Report, Reports, Table, ci, derived, join, lohi, n, v
from summary_tables.experiments import EXTRAS, MAIN, _agg, _heading, sci

RUN10 = Path(__file__).resolve().parents[1] / "data" / "run10-confirmatory"
RUN10_NAME = "paper/data/run10-confirmatory"
BY_ORIGIN = "by-origin-upworthy-*.json"
SMOOTHED = "smoothed-base-skill-upworthy-*.json"
SIZE = "calibration-null-size-upworthy-*.json"
ONE = "ablations/backtest-upworthy-*--contrasts-one.json"
RECORD = "confirmatory-record.json"
ARM = 'ranking_paired.budgets["0.25"].differences.text_lr_minus_arm_count'
MARGIN = 0.0010          # the registration: an end at 0.0010 or closer to zero is not clear


class Run10Report(Report):
    """A report of the confirmatory run folder; its keys are named by the folder's path, since ``$RUN6`` stands for the run of the build."""

    def ref(self, key):
        return f"{RUN10_NAME}/{self.name} {key}"


def run10():
    """The reports of the confirmatory run folder, by glob pattern."""
    reports = Reports(RUN10)

    def get(pattern):
        rep = reports(pattern)
        return Run10Report(rep.name, rep.doc)

    return get


def lead_word(lo, hi):
    """Reading 1: "confirmed" needs the interval with the quarters as units above zero, "base rate ahead" needs it below zero."""
    if lo > 0:
        return "confirmed"
    if hi < 0:
        return "base rate ahead"
    return "not shown"


def skill_word(adjusted_lo, origin_lo):
    """Reading 2: "shown" needs the interval by test, adjusted for three readings, and the interval with the quarters as units both above
    zero by more than the margin."""
    return "shown" if adjusted_lo > MARGIN and origin_lo > MARGIN else "not shown"


def rank_word(lo):
    """Reading 3: "ranks better than counting arms" only if the 90 percent interval of the paired difference lies above zero."""
    return "ranks better than counting arms" if lo > 0 else "not shown to rank better than counting arms"


def _four_or_five(rep, row, field_name):
    """Four places, or five where an end of the interval would print as zero at four and so hide its sign."""
    try:
        return sci(rep, row, field_name, 4)
    except ValueError:
        return sci(rep, row, field_name, 5)


def _check(exp, conf):
    """Each split's reports agree with one another, and the confirmatory folder is the registered run."""
    record = conf(RECORD)
    if record.get("decision") != "2026-11-14" or record.get("snapshot") != conf(MAIN).get("header.snapshot_id"):
        raise ValueError("the confirmatory folder's record does not name the decision of 14 November 2026 and the main report's snapshot")
    for name, r in (("exploratory", exp), ("confirmatory", conf)):
        main, origins, smooth = r(MAIN), r(BY_ORIGIN), r(SMOOTHED)
        if abs(origins.get("pooled.difference") + main.get(f"{_agg('P0')}.logscore_vs_p1")) > 1e-9:
            raise ValueError(f"{name}: the by-origin report does not reproduce the main report's pooled difference")
        if smooth.get("pseudo_rows") != 30:
            raise ValueError(f"{name}: the smoothed base rate is the registered one, with 30 pseudo-rows")
        for rung in ("P1", "P2"):
            if smooth.get(f"rungs.{rung}.pooled.family_size") != 3 or smooth.get(f"rungs.{rung}.origin_level.origins") != 7:
                raise ValueError(f"{name}: the row labels say three readings and seven quarters")
            if abs(smooth.get(f"rungs.{rung}.unsmoothed.pooled.skill") - main.get(f"{_agg(rung)}.brier_skill")) > 1e-9:
                raise ValueError(f"{name}: the smoothed-base script does not reproduce the main report's skill of {rung}")
        if main.get(f"{_agg('P2')}.family_size") != 52:
            raise ValueError(f"{name}: a row label says 52 intervals")
        if origins.get("origin_level.origins") != 7 or main.get("header.origins_scored") != 7:
            raise ValueError(f"{name}: the row labels say seven quarters")
        for binning, field_name in (("equal_width", "ece_percentile"), ("equal_mass", "ece_equal_mass_percentile")):
            at = f"rows[rung=P1,stratum=ALL,binning={binning},truth=observed].observed_percentile"
            if abs(r(SIZE).get(at) - main.get(f"{_agg('P1')}.{field_name}")) > 1e-9:
                raise ValueError(f"{name}: the size script does not reproduce the main report's calibration percentile ({binning})")
    if "text_lr" in exp(ONE).get("header.rungs") or "text_lr" not in conf(ONE).get("header.rungs"):
        raise ValueError("the table says the text classifier ran with one contrast per test on the confirmatory split only")
    if conf(ONE).get("header.variant.contrasts") != "one":
        raise ValueError("the secondary run is the one with one contrast per test")


def _both(r, conf):
    def both(fn):
        return [fn(split) for split in (r, conf)]

    return both


def confirmatory(r):
    """The three primary readings on both splits, with the registered verdict of the confirmatory split."""
    conf = run10()
    _check(r, conf)
    both = _both(r, conf)
    c_origins, c_smooth, c_extras = conf(BY_ORIGIN), conf(SMOOTHED), conf(EXTRAS)
    lead = derived(lead_word(c_origins.get("origin_level.lo"), c_origins.get("origin_level.hi")), c_origins.ref("origin_level.lo"),
                   c_origins.ref("origin_level.hi"))
    skill = derived(skill_word(c_smooth.get("rungs.P1.pooled.adjusted_lo"), c_smooth.get("rungs.P1.origin_level.lo")),
                    c_smooth.ref("rungs.P1.pooled.adjusted_lo"), c_smooth.ref("rungs.P1.origin_level.lo"))
    rank = derived(rank_word(c_extras.get(f"{ARM}.lo")), c_extras.ref(f"{ARM}.lo"))
    rows = [
        ["tests scored", *both(lambda s: n(s(MAIN), "header.tests_scored")), ""],
        ["rows scored", *both(lambda s: n(s(MAIN), "header.scored_rows")), ""],
        Raw(r"\midrule"),
        [r"1. P1 minus P0, log score in nats, pooled, tests resampled",
         *both(lambda s: sci(s(MAIN), _agg("P0"), "logscore_vs_p1", 4, "logscore_vs_p1_lo", "logscore_vs_p1_hi", neg=True)), ""],
        [r"\quad the lead with the seven quarters as units", *both(lambda s: _four_or_five(s(BY_ORIGIN), "origin_level", "difference")), lead],
        Raw(r"\midrule"),
        [r"2. P1 Brier skill against the smoothed base rate, pooled, tests resampled",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P1.pooled", "skill")), ""],
        [r"\quad the same, interval adjusted for three readings",
         *both(lambda s: lohi(s(SMOOTHED), "rungs.P1.pooled.adjusted_lo", "rungs.P1.pooled.adjusted_hi", 4)), ""],
        [r"\quad the skill with the seven quarters as units", *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P1.origin_level", "skill")), skill],
        [r"\quad against the unsmoothed base rate, pooled, tests resampled (no verdict)",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P1.unsmoothed.pooled", "skill")), ""],
        [r"\quad against the unsmoothed base rate, the seven quarters as units (no verdict)",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P1.unsmoothed.origin_level", "skill")), ""],
        Raw(r"\midrule"),
        [r"3. text classifier minus the arm-count rule, captured lift at a quarter budget, all contrasts",
         *both(lambda s: sci(s(EXTRAS), ARM, "estimate", 4)), rank],
    ]
    return Table("fmt-confirmatory", r"p{5.6cm}rrp{2.4cm}", ["reading & exploratory split & confirmatory split & registered verdict,",
                                                             " & & & confirmatory split"], rows,
                 source="the report keys named above each row (confirmatory); the confirmatory column reads paper/data/run10-confirmatory")


def _p2_cell(rep, cell):
    """P2 minus P1 in one cell: the estimate with its interval by test, and the bounds adjusted for 52. Where the guard gave the precedents
    no weight at any origin, P2 is P1, every key is zero or null, and the two cells say so."""
    at = f"tables.aggregate[cell={cell},rung=P2]"
    keys = [f"{at}.logscore_vs_p1", f"{at}.logscore_vs_p1_lo", f"{at}.logscore_vs_p1_hi", f"{at}.logscore_vs_p1_adjusted_lo",
            f"{at}.logscore_vs_p1_adjusted_hi"]
    values = [rep.get(k) for k in keys]
    if rep.get(f"{at}.family_size") != 52:
        raise ValueError(f"{rep.name}: a row label says 52 intervals")
    if all(x == 0 for x in values[:3]) and values[3] is None and values[4] is None:
        same = derived("equal to P1", *[rep.ref(k) for k in keys[:3]])
        return same, derived("equal to P1", *[rep.ref(k) for k in keys[3:]])
    return sci(rep, at, "logscore_vs_p1", 4, "logscore_vs_p1_lo", "logscore_vs_p1_hi"), lohi(rep, keys[3], keys[4], 4)


def confirmatory_secondary(r):
    """The registered secondary readings on both splits; none carries a verdict word. The two rows by cell were added after a review of the
    confirmatory section (the pooled row averages two cells of opposite sign)."""
    conf = run10()
    _check(r, conf)
    both = _both(r, conf)

    def percentile(binning):
        at = f"rows[rung=P1,stratum=ALL,binning={binning},truth=observed]"
        return both(lambda s: join("{} against {}", v(s(SIZE), f"{at}.observed_percentile", 1), v(s(SIZE), f"{at}.critical_95", 1)))

    def by_cell(cell, label):
        cells = both(lambda s: _p2_cell(s(MAIN), cell))
        return [[f"P2 minus P1 in the {label} cell, tests resampled", cells[0][0], cells[1][0]],
                [rf"\quad the {label} cell, interval adjusted for 52", cells[0][1], cells[1][1]]]

    one_row = "tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung=text_lr]"
    not_run = derived("not run", r(ONE).ref("header.rungs"))
    rows = [
        ["P1 calibration percentile against its simulated critical value, equal-width bins", *percentile("equal_width")],
        [r"\quad the same, equal-mass bins", *percentile("equal_mass")],
        ["P1 coverage of the 80 percent interval", *both(lambda s: ci(s(MAIN), _agg("P1"), "coverage_80", 3))],
        ["P1 coverage of the 90 percent interval", *both(lambda s: ci(s(MAIN), _agg("P1"), "coverage_90", 3))],
        Raw(r"\midrule"),
        ["P2 minus P1, log score in nats, pooled, tests resampled",
         *both(lambda s: sci(s(MAIN), _agg("P2"), "logscore_vs_p1", 4, "logscore_vs_p1_lo", "logscore_vs_p1_hi"))],
        [r"\quad pooled, interval adjusted for the 52 intervals of the report's aggregate table",
         *both(lambda s: lohi(s(MAIN), f"{_agg('P2')}.logscore_vs_p1_adjusted_lo", f"{_agg('P2')}.logscore_vs_p1_adjusted_hi", 4))],
        *by_cell("headline_only", "headline-only"),
        *by_cell("image_only", "image-only"),
        ["P2 Brier skill against the unsmoothed base rate, pooled, tests resampled",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P2.unsmoothed.pooled", "skill"))],
        [r"\quad against the unsmoothed base rate, P2 with the seven quarters as units",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P2.unsmoothed.origin_level", "skill"))],
        ["P2 Brier skill against the smoothed base rate, pooled, tests resampled",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P2.pooled", "skill"))],
        [r"\quad against the smoothed base rate, P2 with the seven quarters as units",
         *both(lambda s: _four_or_five(s(SMOOTHED), "rungs.P2.origin_level", "skill"))],
        Raw(r"\midrule"),
        _heading("One contrast per test, where the arm-count rule cannot order tests", 3),
        ["text classifier minus the random order, captured lift at a quarter budget", not_run,
         sci(conf(ONE), one_row, "diff_random", 4, "diff_random_lo", "diff_random_hi")],
        ["text classifier, AUC within pairs of origin and cell", not_run,
         sci(conf(ONE), _agg("text_lr"), "auc_event_within", 3, "auc_event_within_lo", "auc_event_within_hi")],
    ]
    return Table("fmt-confirmatory-secondary", r"p{7.4cm}rr", ["reading & exploratory split & confirmatory split"], rows,
                 source="the report keys named above each row (confirmatory); the confirmatory column reads paper/data/run10-confirmatory")


TABLES = [confirmatory, confirmatory_secondary]
