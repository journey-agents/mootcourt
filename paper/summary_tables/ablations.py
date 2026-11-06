"""Summary tables of the ablations section."""
from summary_tables import Table, ci, join, n, pctw, v

ALL = "tables.aggregate[cell=ALL]"
P1, P2 = "tables.aggregate[cell=ALL,rung=P1]", "tables.aggregate[cell=ALL,rung=P2]"
MAIN = "backtest-upworthy-*.json"


def _abl(name):
    return f"ablations/backtest-upworthy-*--{name}.json"


def p2_settings(r):
    def row(label, on, off=None, paired=None):
        on = r(on)
        off = r(off) if off else None
        return [label, v(on, f"{P2}.logscore"), v(off, f"{P2}.logscore") if off else "",
                ci(on, P2, "brier_skill", 4), ci(off, P2, "brier_skill", 4) if off else "",
                paired or ci(on, P2, "logscore_vs_p1", 5), ci(off, P2, "logscore_vs_p1", 5) if off else ""]

    def both(label, name):
        return row(label, _abl(name), _abl(f"{name}+p2-guard-off"))

    prelaunch, one = _abl("admission-prelaunch"), _abl("contrasts-one")
    zero, main = r(_abl("lambda-0.0")), r(MAIN)
    if abs(zero.get(f"{P2}.logscore") - main.get(f"{P1}.logscore")) > 1e-9:
        raise ValueError("the row says the fixed weight zero is P1 exactly")
    return Table("fmt-p2-settings", "lrrrrrr", [
        "& \\multicolumn{2}{c}{P2 log score} & \\multicolumn{2}{c}{P2 Brier skill (90\\%)} & \\multicolumn{2}{c}{P2 minus P1, paired (90\\%)}",
        "setting & guard on & guard off & guard on & guard off & guard on & guard off"], [
        row("main run (forward chaining, guard at two standard errors)", MAIN, _abl("p2-guard-off")),
        row("guard at one standard error", _abl("p2-guard-1.0")),
        row("fixed weight $\\lambda = 0$ (P1 exactly)", _abl("lambda-0.0"), paired="equals P1"),
        row("fixed weight $\\lambda = 0.2$", _abl("lambda-0.2")),
        row("fixed weight $\\lambda = 0.5$", _abl("lambda-0.5")),
        row("fixed weight $\\lambda = 1$", _abl("lambda-1.0")),
        both("bandwidth multiplier 1/8", "bandwidth-mult-0.125"),
        both("bandwidth multiplier 1/4", "bandwidth-mult-0.25"),
        both("bandwidth multiplier 1/2", "bandwidth-mult-0.5"),
        both("bandwidth multiplier 1", "bandwidth-mult-1.0"),
        both("text features alone", "features-text"),
        both("structured features alone", "features-structured"),
        both("single-headline space, no reference headline", "pairwise-off"),
        both("leave-one-test-out selection", "p2-selection-loto"),
        both("leave-one-test-out with a recency kernel", "p2-selection-loto+recency-select"),
        both("recency kernel under forward chaining", "recency-select"),
        row(join("admission on exposure alone ({} rows)", n(r(prelaunch), "header.scored_rows")), prelaunch),
        row(join("one contrast per test, the earliest ({} rows)", n(r(one), "header.scored_rows")), one),
    ])


def selection_rule(r):
    rep = r("paper-extras-upworthy-*.json")

    def cell(guard):
        return ci(rep, f"p2_selection_comparison.{guard}.pooled", "difference", 4, lo="lo", hi="hi")

    return Table("fmt-selection-rule", "lrr", [" & guard on & guard off"],
                 [["forward chaining minus leave-one-test-out", cell("guard_on"), cell("guard_off")]])


def guard_threshold(r):
    rep = r("paper-extras-synthetic-*.json")
    large = [3700, 11100]

    def rate(multiplier):
        return pctw(rep, f"guard_admission_rates.by_multiplier[multiplier={multiplier}].share_admitted")

    def control(size, field="share_admitted"):
        return f"guard_period_control.rows[arm=new_rule,n_tests={size}].{field}"

    header = join("guard threshold & {} tests & {} tests & {} tests", n(rep, "guard_admission_rates.inputs.n_tests"),
                  *[n(rep, control(size, "n_tests")) for size in large])
    return Table("fmt-guard-threshold", "lrrr", [header], [
        ["one standard error", rate("1.0"), "", ""],
        ["1.5 standard errors", rate("1.5"), "", ""],
        ["two standard errors (the default)", rate("2.0"), *[pctw(rep, control(size)) for size in large]],
        ["no guard", rate("off"), "", ""],
    ])


def prior_settings(r):
    def row(label, pattern):
        rep = r(pattern)
        return [label, v(rep, f"{P1}.logscore"), ci(rep, P1, "brier_skill", 4)]

    return Table("fmt-prior-settings", "lrr", ["prior & P1 log score & P1 Brier skill (90\\%)"], [
        row("Student-t, $\\kappa = 0$", _abl("kappa-0.0")),
        row("Student-t, $\\kappa = 5$", _abl("kappa-5.0")),
        row("Student-t, $\\kappa = 20$ (the main run)", MAIN),
        row("Student-t, $\\kappa = 80$", _abl("kappa-80.0")),
        row("normal, $\\kappa = 20$", _abl("prior-normal")),
    ])


def admission(r):
    main, pre = r(MAIN), r(_abl("admission-prelaunch"))

    def row(label, rep):
        return [label, n(rep, "header.scored_rows"), v(rep, f"{ALL}.brier_base", 4),
                ci(rep, P1, "brier_skill", 4), ci(rep, P2, "brier_skill", 4)]

    return Table("fmt-admission", "lrrrr", ["admission & contrasts & base Brier score & P1 Brier skill (90\\%) & P2 Brier skill (90\\%)"],
                 [row("realized clicks (the main run)", main), row("exposure alone", pre)])


def learning(r):
    rep = r("learning-curve-upworthy-*.json")

    def row(fraction):
        p1, p2 = f"rows[fraction={fraction},rung=P1]", f"rows[fraction={fraction},rung=P2]"
        spread = v(rep, f"{p1}.skill_seed_sd") if rep.get(f"{p1}.skill_seed_sd") is not None else ""   # one fit at the full history, no spread
        return [fraction, n(rep, f"{p1}.n_fit_rows"), ci(rep, p1, "skill"), ci(rep, p2, "skill"), spread,
                v(rep, f"{p1}.brier", 4), v(rep, f"{p2}.brier", 4)]

    return Table("fmt-learning", "rrrrrrr",
                 ["fraction & history rows & P1 skill (90\\%) & P2 skill (90\\%) & seed spread, P1 & P1 Brier score & P2 Brier score"],
                 [row(f) for f in ("0.01", "0.02", "0.05", "0.10", "0.25", "0.50", "1.00")])


TABLES = [p2_settings, selection_rule, guard_threshold, prior_settings, admission, learning]
