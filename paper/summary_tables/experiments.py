"""Summary tables of the paper version 2 plan's experiments X1 to X10 (docs/superpowers/plans/2026-11-06-paper-v2-plan.md), one function per table.

Every cell comes from a report key: the extras keys named in each function, the main report and the ablation that includes the randomization window.
Literal words that state a measured fact are derived or guarded by a raised error, as in the other groups.
"""
from summary_tables import Raw, Table, ci, derived, fmt, join, lohi, month_year, n, v
from summary_tables.results_a import DECIDABLE

MAIN = "backtest-upworthy-*.json"
WINDOW = "include-randomization-window/backtest-upworthy-*.json"
EXTRAS = "paper-extras-upworthy-*.json"
ASOS_EXTRAS = "paper-extras-asos-*.json"
SYNTHETIC_EXTRAS = "paper-extras-synthetic-*.json"
CURVE = "learning-curve-upworthy-*.json"
BUDGETS = ("0.10", "0.25", "0.50")
AUDIENCES = ("5", "20", "100")


def _agg(rung):
    return f"tables.aggregate[cell=ALL,rung={rung}]"


def _heading(text, width):
    return Raw(rf"\multicolumn{{{width}}}{{@{{}}l}}{{\emph{{{text}}}}} \\")


def sci(rep, row, field_name, nd=4, lo="lo", hi="hi", neg=False):
    """``value (lo, hi)``, optionally negated with the bounds swapped; a nonzero bound that would print as zero fails the build, since it hides its sign."""
    prefix = f"{row}." if row else ""
    keys = [f"{prefix}{field_name}", f"{prefix}{lo}", f"{prefix}{hi}"]
    x, low, high = (rep.get(k) for k in keys)
    if neg:
        x, low, high = -x, -high, -low
    for bound in (low, high):
        if abs(bound) > 1e-12 and float(fmt(bound, nd)) == 0.0:
            raise ValueError(f"{rep.name} {keys[0]}: a bound rounds to zero at {nd} places; print more")
    return derived(f"{fmt(x, nd)} ({fmt(low, nd)}, {fmt(high, nd)})", *[rep.ref(k) for k in keys])


def window(r):
    """X1: the main run against the ablation that includes the randomization window, side by side."""
    main, abl = r(MAIN), r(WINDOW)

    def both(fn, *args, **kw):
        return [fn(main, *args, **kw), fn(abl, *args, **kw)]

    def skill(rung):
        return both(sci, _agg(rung), "brier_skill", 4, "brier_skill_lo", "brier_skill_hi")

    def within(rung):
        return both(sci, _agg(rung), "auc_event_within", 3, "auc_event_within_lo", "auc_event_within_hi")

    return Table("fmt-window", "lrr", ["figure & window excluded & window included", " & (main) & (ablation)"], [
        ["tests scored", *both(n, "header.tests_scored")],
        ["rows scored", *both(n, "header.scored_rows")],
        ["origins scored", *both(n, "header.origins_scored")],
        Raw(r"\midrule"),
        [r"P1 Brier skill (90\%)", *skill("P1")],
        [r"P2 Brier skill (90\%)", *skill("P2")],
        [r"text classifier Brier skill (90\%)", *skill("text_lr")],
        Raw(r"\midrule"),
        [r"P1 minus P0, log score (90\%)", *both(sci, _agg("P0"), "logscore_vs_p1", 4, "logscore_vs_p1_lo", "logscore_vs_p1_hi", neg=True)],
        [r"P2 minus P1, log score (90\%)", *both(sci, _agg("P2"), "logscore_vs_p1", 4, "logscore_vs_p1_lo", "logscore_vs_p1_hi")],
        Raw(r"\midrule"),
        [r"P1 AUC within strata (90\%)", *within("P1")],
        [r"P2 AUC within strata (90\%)", *within("P2")],
        [r"text classifier AUC within strata (90\%)", *within("text_lr")],
        Raw(r"\midrule"),
        ["P1 ECE percentile", *both(v, f"{_agg('P1')}.ece_percentile", 1)],
        ["P2 ECE percentile", *both(v, f"{_agg('P2')}.ece_percentile", 1)],
    ])


def leak_choices(r):
    """X2: which single choice of the cautionary run makes the reversal."""
    rep = r(EXTRAS)
    named = []

    def below(run):
        """Where P1's AUC interval lies wholly below one half, read from the interval and checked against the report's own flags."""
        p1, flags = f"effect_scale_choices.runs.{run}.rungs.P1", f"effect_scale_choices.runs.{run}.p1_ranking"
        pooled, inside = rep.get(f"{p1}.auc_event_hi") < 0.5, rep.get(f"{p1}.auc_event_within_hi") < 0.5
        if pooled != rep.get(f"{flags}.auc_event_below_half") or inside != rep.get(f"{flags}.auc_event_within_below_half"):
            raise ValueError(f"{run}: the report's below-half flags disagree with its intervals")
        if pooled:
            named.append(run)
        text = {(True, True): "pooled and within", (False, True): "within only", (True, False): "pooled only", (False, False): "neither"}[(pooled, inside)]
        return derived(text, rep.ref(f"{p1}.auc_event_hi"), rep.ref(f"{p1}.auc_event_within_hi"))

    def row(scale, precision, run):
        at = f"effect_scale_choices.runs.{run}"
        p1 = f"{at}.rungs.P1"
        return [scale, precision, v(rep, f"{at}.event_rate", 3), ci(rep, p1, "auc_event", 3), ci(rep, p1, "auc_event_within", 3),
                sci(rep, p1, "brier_skill", 4, "brier_skill_lo", "brier_skill_hi"), below(run)]

    rows = [row("absolute", "planned (main)", "main"), row("relative", "planned", "relative_planned"), row("absolute", "realized", "absolute_realized"),
            row("relative", "realized (cautionary)", "cautionary")]
    if named != rep.get("effect_scale_choices.runs_where_p1_auc_interval_is_below_half"):
        raise ValueError("the runs whose pooled interval lies below one half differ from the report's list")
    return Table("fmt-leak-choices", "llrrrrl",
                 ["effect scale & precision & event rate & P1 AUC, pooled & P1 AUC, within & P1 Brier skill & AUC interval", r" & & & (90\%) & (90\%) & (90\%) & below 0.5"], rows)


def exposure_fixed(r):
    """X3: exposure fixed at the cell median against the main run."""
    rep = r(EXTRAS)
    top = "exposure_fixed"

    def row(rung, run, label):
        at = f"{top}.by_cell.ALL.{run}.{rung}"
        constant = f"{top}.p_sig_constant_within_origin_and_cell.{run}.{rung}"
        return [label, v(rep, f"{top}.auc_event_within_ties_exact.{run}.{rung}"), ci(rep, at, "auc_event_within", 3),
                sci(rep, at, "brier_skill", 4, "brier_skill_lo", "brier_skill_hi"), v(rep, f"{at}.logscore", 4), v(rep, f"{at}.ece", 4),
                join("{} of {}", n(rep, f"{constant}.strata_with_one_value"), n(rep, f"{constant}.origin_cell_strata"))]

    def by_cell(label, cell, rung):
        at = f"{top}.by_cell.{cell}"
        return [label, v(rep, f"{at}.main.{rung}.auc_event_within"), v(rep, f"{at}.fixed.{rung}.auc_event_within"),
                v(rep, f"{at}.main.{rung}.brier_skill", 4), v(rep, f"{at}.fixed.{rung}.brier_skill", 4), "", ""]

    return Table("fmt-exposure-fixed", "lrrrrrr",
                 ["all cells & AUC within, & AUC within & Brier skill & log score & ECE & strata with", r" & ties exact & (90\%) & (90\%) & & & one forecast"], [
        row("P1", "main", "P1, main"),
        row("P1", "fixed", "P1, exposure fixed"),
        row("P2", "main", "P2, main"),
        row("P2", "fixed", "P2, exposure fixed"),
        Raw(r"\midrule"),
        Raw(r"by cell & AUC within, main & AUC within, fixed & skill, main & skill, fixed & & \\"),
        Raw(r"\midrule"),
        by_cell("headline-only, P1", "headline_only", "P1"),
        by_cell("headline-only, P2", "headline_only", "P2"),
        by_cell("image-only, P1", "image_only", "P1"),
        by_cell("image-only, P2", "image_only", "P2"),
        by_cell("smallest, P1", "both", "P1"),
        by_cell("smallest, P2", "both", "P2"),
    ])


def prior_family(r):
    """X4: the prior's family on the standardized effect; in-sample marginal likelihood gains in nats."""
    rep = r(EXTRAS)

    def row(label, cell):
        at = f"prior_family_scale.by_cell.{cell}"
        def gain(name):
            return join("{} ({})", v(rep, f"{at}.{name}.gain_total", 1), n(rep, f"{at}.{name}.nu_best"))
        levels = f"{at}.level_bins"
        return [label, n(rep, f"{at}.rows"), gain("pp"), gain("relative"), v(rep, f"{levels}.gain_normal_by_level_over_single_normal", 1),
                v(rep, f"{levels}.gain_t_within_level_bins_over_normal_within_level_bins", 1), v(rep, f"{levels}.share_of_t_gain_reached_by_normal_by_level", 2)]

    return Table("fmt-prior-family", "lrrrrrr",
                 [r"cell & rows & $t$, points & $t$, over rate & normal & $t$ within & level gain",
                  r" & & ($\nu$) & ($\nu$) & by level & levels & over $t$ gain"], [
        row("all", "ALL"), row("headline-only", "headline_only"), row("image-only", "image_only"), row("smallest", "both"),
    ])


def ranking_paired(r):
    """X5: captured fraction by policy and paired differences at three budgets, the exposure-only policy in both directions, the planted ledgers at a quarter."""
    rep, syn = r(EXTRAS), r(SYNTHETIC_EXTRAS)

    def at(budget):
        return f'ranking_paired.budgets["{budget}"]'

    def policy(label, name):
        return [label, *[v(rep, f"{at(b)}.policies.{name}.estimate", 4) for b in BUDGETS]]

    def diff(label, name):
        return [label, *[sci(rep, f"{at(b)}.differences.{name}", "estimate") for b in BUDGETS]]

    def adjusted(name):
        return ["\\quad adjusted", *[lohi(rep, f"{at(b)}.differences.{name}.adjusted_lo", f"{at(b)}.differences.{name}.adjusted_hi", 4) for b in BUDGETS]]

    def planted(size):
        return f'positive_control_decision_value.{size}.paired.budgets["0.25"]'

    def planted_policy(label, size, name):
        return [label, "", v(syn, f"{planted(size)}.policies.{name}.estimate", 4), ""]

    def planted_diff(label, size, name, nd=4):
        key = f"{planted(size)}.differences.{name}"
        return [label, "", sci(syn, key, "estimate", nd), ""]

    def planted_adjusted(size, name, nd=4):
        key = f"{planted(size)}.differences.{name}"
        return ["\\quad adjusted", "", lohi(syn, f"{key}.adjusted_lo", f"{key}.adjusted_hi", nd), ""]

    return Table("fmt-ranking-paired", "lrrr", ["policy or difference & budget 0.10 & budget 0.25 & budget 0.50"], [
        _heading("Captured fraction, headline archive", 4),
        policy("random order", "random"),
        policy("arm count", "arm_count"),
        policy("exposure only, most precise first", "s_star"),
        policy("exposure only, least precise first", "s_star_desc"),
        policy("P1", "P1"),
        policy("P2", "P2"),
        policy("text classifier", "text_lr"),
        Raw(r"\midrule"),
        _heading(r"Paired differences by test (90\%)", 4),
        diff("P2 minus P1", "P2_minus_P1"),
        adjusted("P2_minus_P1"),
        diff("text classifier minus P1", "text_lr_minus_P1"),
        adjusted("text_lr_minus_P1"),
        diff("least precise first minus arm count", "s_star_desc_minus_arm_count"),
        diff("most precise first minus arm count", "s_star_minus_arm_count"),
        diff("P2 minus least precise first", "P2_minus_s_star_desc"),
        diff("P2 minus most precise first", "P2_minus_s_star"),
        Raw(r"\midrule"),
        [join("\\emph{{Planted ledger, {} tests scored}}", n(syn, "positive_control_decision_value.n11100.tests")), "", "", ""],
        planted_policy("P1", "n11100", "P1"),
        planted_policy("P2", "n11100", "P2"),
        planted_policy("text classifier", "n11100", "text_lr"),
        planted_diff("P2 minus P1", "n11100", "P2_minus_P1", 5),
        planted_adjusted("n11100", "P2_minus_P1", 5),
        planted_diff("text classifier minus P1", "n11100", "text_lr_minus_P1"),
        planted_adjusted("n11100", "text_lr_minus_P1"),
        [join("\\emph{{Planted ledger, {} tests scored}}", n(syn, "positive_control_decision_value.n2000.tests")), "", "", ""],
        planted_policy("P1", "n2000", "P1"),
        planted_policy("P2", "n2000", "P2"),
        planted_policy("text classifier", "n2000", "text_lr"),
        planted_diff("text classifier minus P1", "n2000", "text_lr_minus_P1"),
        planted_adjusted("n2000", "text_lr_minus_P1"),
    ])


def abstention_composition(r):
    """X6: abstained against issued excluding burn-in, pooled and within origin-and-cell strata, against one common baseline."""
    rep, main = r(EXTRAS), r(MAIN)
    top = "abstention_composition"
    rungs = ("P1", "P2")
    origins = main.get("tables.origins")
    later_full = [o for o in origins if o["abstention_rate"] == 1.0 and not o["burn_in"]]
    if len(later_full) != 1:
        raise ValueError("the row names one origin after burn-in that abstains on every row")
    full = later_full[0]
    full_keys = [main.ref(f"tables.origins[origin={full['origin']}].{f}") for f in ("n_scored", "abstention_rate")]

    def both(fn):
        return [fn(rung) for rung in rungs]

    def group_size(side):
        return both(lambda g: join("{} / {}", n(rep, f"{top}.{g}.{side}.rows"), n(rep, f"{top}.{g}.{side}.tests")))

    def skill(side):
        return both(lambda g: sci(rep, f"{top}.{g}.{side}", "skill"))

    def rate(cell):
        return both(lambda g: join("{} of {}", v(rep, f"{top}.{g}.abstention_rate_by_cell.{cell}.rate", 3), n(rep, f"{top}.{g}.abstention_rate_by_cell.{cell}.rows")))

    def pooled_rate(g):
        a, t = rep.get(f"{top}.{g}.abstained_rows"), rep.get(f"{top}.{g}.rows")
        return derived(f"{fmt(a / t, 3)} of {fmt(t, 0, comma=True)}", rep.ref(f"{top}.{g}.abstained_rows"), rep.ref(f"{top}.{g}.rows"))

    def rate_without_full(g):
        a, t = rep.get(f"{top}.{g}.abstained_rows") - full["n_scored"], rep.get(f"{top}.{g}.rows") - full["n_scored"]
        return derived(f"{fmt(a / t, 3)} of {fmt(t, 0, comma=True)}", rep.ref(f"{top}.{g}.abstained_rows"), rep.ref(f"{top}.{g}.rows"), *full_keys)

    strat = "stratified_issued_minus_abstained_skill"
    return Table("fmt-abstention-composition", "lrr", [" & P1 & P2"], [
        ["issued, rows / tests", *group_size("issued")],
        [r"issued, Brier skill (90\%)", *skill("issued")],
        ["abstained, rows / tests", *group_size("abstained")],
        [r"abstained, Brier skill (90\%)", *skill("abstained")],
        Raw(r"\midrule"),
        ["issued minus abstained, pooled", *both(lambda g: v(rep, f"{top}.{g}.pooled_issued_minus_abstained_skill", 4))],
        [r"issued minus abstained, within (90\%)", *both(lambda g: sci(rep, f"{top}.{g}.{strat}", "estimate"))],
        ["strata holding both groups", *both(lambda g: join("{} of {}", n(rep, f"{top}.{g}.{strat}.strata_with_both_groups"), n(rep, f"{top}.{g}.{strat}.strata_total")))],
        Raw(r"\midrule"),
        ["abstention rate, all cells, of rows", *both(pooled_rate)],
        [f"the same without {month_year(full['origin'])}", *both(rate_without_full)],
        ["abstention rate, headline-only, of rows", *rate("headline_only")],
        ["abstention rate, image-only, of rows", *rate("image_only")],
        ["abstention rate, smallest, of rows", *rate("both")],
    ])


def gates_strata(r):
    """X7: one gate rule for every stratum: tests against the stratum's own simulated sizes; adjusted intervals below."""
    rep, asos = r(EXTRAS), r(ASOS_EXTRAS)
    top = "gates_by_stratum.strata"

    def verdict(extras, stratum):
        """The stratum's verdict, checked against the one rule."""
        at = f"{top}.{stratum}"
        tests, n200, n400 = extras.get(f"{at}.tests"), extras.get(f"{at}.own_gate.n_200"), extras.get(f"{at}.own_gate.n_400")
        expected = "both skills" if tests >= n400 else "skill 0.20 only" if tests >= n200 else "neither"
        text = DECIDABLE[extras.get(f"{at}.verdict")]
        if text != expected:
            raise ValueError(f"{stratum}: the report's verdict {text} is not the one rule's {expected}")
        return derived(text, extras.ref(f"{at}.verdict"), extras.ref(f"{at}.tests"), extras.ref(f"{at}.own_gate.n_200"), extras.ref(f"{at}.own_gate.n_400"))

    def gate_row(label, extras, stratum):
        at, dep = f"{top}.{stratum}", f"{top}.{stratum}.dependence"
        return [label, n(extras, f"{at}.tests"), v(extras, f"{dep}.base_rate", 2), v(extras, f"{dep}.rows_per_test", 1), v(extras, f"{dep}.icc", 2),
                n(extras, f"{at}.own_gate.n_200"), n(extras, f"{at}.own_gate.n_400"), verdict(extras, stratum)]

    def skill(extras, stratum, rung, width):
        key = f"{top}.{stratum}.rungs.{rung}"
        if rung not in extras.get(f"{top}.{stratum}.rungs"):
            return rf"\multicolumn{{{width}}}{{r}}{{}}"
        cell = sci(extras, key, "brier_skill", 4, "adjusted_lo", "adjusted_hi")
        return join("\\multicolumn{{" + str(width) + "}}{{r}}{{{}}}", cell)

    def skill_row(label, extras, stratum):
        return [label, skill(extras, stratum, "P1", 2), skill(extras, stratum, "P2", 2), skill(extras, stratum, "text_lr", 3)]

    families = {rep.get(f"{top}.{s}.family_size") for s in ("ALL", "headline_only", "image_only", "both")}
    if len(families) != 1:
        raise ValueError("the headline archive's strata hold different families")
    family_note = join("Brier skill with adjusted interval (family of {} on the headline archive, {} on the deployment-shaped one)",
                       n(rep, f"{top}.ALL.family_size"), n(asos, f"{top}.ALL.family_size"))
    return Table("fmt-gates-strata", "lrrrrrrl",
                 ["stratum & tests & base & rows & within-test & gate, skill & gate, skill & decidable", " & & rate & per test & corr. & 0.20 & 0.10 & "], [
        gate_row("headline archive, pooled", rep, "ALL"),
        gate_row("headline-only", rep, "headline_only"),
        gate_row("image-only", rep, "image_only"),
        gate_row("smallest", rep, "both"),
        gate_row("deployment-shaped, pooled", asos, "ALL"),
        Raw(r"\midrule"),
        [join(r"\multicolumn{{8}}{{@{{}}l}}{{\emph{{{}}}}}", family_note)],
        Raw(r"stratum & \multicolumn{2}{r}{P1} & \multicolumn{2}{r}{P2} & \multicolumn{3}{r}{text classifier} \\"),
        Raw(r"\midrule"),
        skill_row("headline archive, pooled", rep, "ALL"),
        skill_row("headline-only", rep, "headline_only"),
        skill_row("image-only", rep, "image_only"),
        skill_row("smallest", rep, "both"),
        skill_row("deployment-shaped, pooled", asos, "ALL"),
    ])


def drift_null(r):
    """X8: the ECE of the significance probability against the current null and the drift-matched null."""
    rep = r(EXTRAS)

    def row(rung):
        at = f"drift_matched_null.rungs.{rung}"
        pooled = f"{at}.pooled"
        drift = f"{pooled}.drift_matched_null"
        origins = rep.get(f"{at}.by_origin")
        inside = sum(o["drift_matched_null"]["ece_inside_central_90"] for o in origins.values())
        count = derived(f"{inside} of {len(origins)}", *[rep.ref(f'{at}.by_origin["{o}"].drift_matched_null.ece_inside_central_90') for o in sorted(origins)])
        word = derived("yes" if rep.get(f"{drift}.ece_inside_central_90") else "no", rep.ref(f"{drift}.ece_inside_central_90"))
        return [rung, v(rep, f"{pooled}.ece", 4), v(rep, f"{pooled}.current_null.percentile", 1), v(rep, f"{drift}.percentile", 1),
                join("{} {}", v(rep, f"{drift}.mean", 4), lohi(rep, f"{drift}.p5", f"{drift}.p95", 4)), word, count]

    return Table("fmt-drift-null", "lrrrrlr",
                 ["rung & ECE & percentile, & percentile, & drift null, & inside, & origins", r" & & current null & drift null & mean (central 90\%) & pooled & inside"],
                 [row("P0"), row("P1"), row("P2")])


def calibration_shift(r):
    """X8b: the ECE before and after an oracle level shift per origin and cell, with the null built from the shifted forecasts."""
    rep = r(EXTRAS)
    top = "calibration_within_period"

    def row(label, rung, group):
        at = f"{top}.rungs.{rung}.by_stratum_group.{group}"
        return [label, n(rep, f"{at}.rows"), v(rep, f"{at}.ece_before", 4), v(rep, f"{at}.ece_after", 4), v(rep, f"{at}.share_of_ece_removed", 2),
                v(rep, f"{at}.null_mean", 4), v(rep, f"{at}.after_percentile_in_null", 1)]

    return Table("fmt-calibration-shift", "lrrrrrr",
                 ["rung, stratum & rows & ECE as & ECE after & share & null mean, & percentile in", r" & & issued & the shift & removed & shifted & that null"], [
        row("P0, all cells", "P0", "ALL"),
        row("P1, all cells", "P1", "ALL"),
        row("P2, all cells", "P2", "ALL"),
        row("P1, headline-only", "P1", "headline_only"),
        row("P1, image-only", "P1", "image_only"),
        row("P1, smallest", "P1", "both"),
    ])


def learning_paired(r):
    """X9: the learning curve paired with P1 on the same held-out rows."""
    rep = r(CURVE)

    def row(fraction):
        p2, text = f"paired_vs_p1[fraction={fraction},rung=P2]", f"paired_vs_p1[fraction={fraction},rung=text_lr]"
        return [fraction, sci(rep, p2, "logscore_minus_p1", 4, "logscore_lo", "logscore_hi"), sci(rep, p2, "brier_gain_over_p1", 6, "brier_lo", "brier_hi"),
                sci(rep, text, "brier_gain_over_p1", 4, "brier_lo", "brier_hi")]

    return Table("fmt-learning-paired", "rrrr",
                 ["fraction & P2 minus P1, & P2 Brier gain & text classifier Brier", r" & log score (90\%) & over P1 (90\%) & gain over P1 (90\%)"],
                 [row(f) for f in ("0.01", "0.02", "0.05", "0.1", "0.25", "0.5", "1.0")])


def auc_by_year(r):
    """X9: the event AUC by year within origin and within origin and cell, which the 2015 skill is read against."""
    rep = r(EXTRAS)

    def auc(year, rung, name):
        return sci(rep, f'within_origin_auc_by_year.years["{year}"].{rung}.{name}', "estimate", 3)

    def row(year, name):
        at = f'within_origin_auc_by_year.years["{year}"]'
        return [year, n(rep, f"{at}.P1.tests"), *[auc(year, rung, name) for rung in ("P0", "P1", "P2", "text_lr")]]

    return Table("fmt-auc-by-year", "lrrrrr", [r"year & tests & P0 (90\%) & P1 (90\%) & P2 (90\%) & text classifier (90\%)"], [
        _heading("Within origin", 6),
        row("2013", "auc_within_origin"), row("2014", "auc_within_origin"), row("2015", "auc_within_origin"),
        Raw(r"\midrule"),
        _heading("Within origin and cell", 6),
        row("2013", "auc_within_origin_and_cell"), row("2014", "auc_within_origin_and_cell"), row("2015", "auc_within_origin_and_cell"),
    ])


def sizing(r):
    """X10: test-and-roll sizes; relative regret by rule across audience multiples and worlds, median sizes, paired differences, feasibility."""
    rep = r(EXTRAS)
    top = "sizing_evaluation.test_and_roll"

    def at(m):
        return f'{top}.by_audience["{m}"]'

    def regret(label, rule):
        return [label, *[sci(rep, f"{at(m)}.relative_regret_with_interval.{rule}", "estimate", 3) for m in AUDIENCES]]

    def world(label, scale, rule):
        return [label, *[v(rep, f'{at(m)}.pooled_relative_regret["{scale}"].{rule}') for m in AUDIENCES]]

    def size(label, rule):
        return [label, *[n(rep, f"{at(m)}.median_sizes.{rule}") for m in AUDIENCES]]

    def diff(label, name, nd=4):
        return [label, *[sci(rep, f"{at(m)}.paired_differences.{name}", "estimate", nd) for m in AUDIENCES]]

    def adjusted(name, nd=4):
        return ["\\quad adjusted", *[lohi(rep, f"{at(m)}.paired_differences.{name}.adjusted_lo", f"{at(m)}.paired_differences.{name}.adjusted_hi", nd) for m in AUDIENCES]]

    failures = f"{top}.claim.feasibility_failures"
    feasible = join("{} of {}", n(rep, f"{failures}.units_with_100_or_more_scored_rows"), n(rep, f"{failures}.units_after_the_date_rule"))
    return Table("fmt-sizing", "lrrr", [r"rule or difference & audience multiple 5 & multiple 20 (primary) & multiple 100"], [
        _heading(r"Relative regret, world as fitted (90\%)", 4),
        regret("prior rule", "prior"),
        regret("base-rate rule", "base_rate"),
        regret("fixed power rule", "power"),
        regret("never test", "never_test"),
        regret("test the whole audience", "test_everything"),
        Raw(r"\midrule"),
        _heading("Relative regret, other worlds", 4),
        world("prior rule, world at 0.67", "x0.67", "prior"),
        world("base-rate rule, world at 0.67", "x0.67", "base_rate"),
        world("fixed power rule, world at 0.67", "x0.67", "power"),
        world("prior rule, world at 1.5", "x1.5", "prior"),
        world("base-rate rule, world at 1.5", "x1.5", "base_rate"),
        world("fixed power rule, world at 1.5", "x1.5", "power"),
        Raw(r"\midrule"),
        _heading("Median size per arm, impressions", 4),
        size("prior rule", "prior"),
        size("base-rate rule", "base_rate"),
        size("fixed power rule", "power"),
        Raw(r"\midrule"),
        _heading(r"Paired differences in relative regret (90\%)", 4),
        diff("prior minus base-rate", "prior_minus_base_rate"),
        adjusted("prior_minus_base_rate"),
        diff("prior minus fixed power", "prior_minus_power", 3),
        adjusted("prior_minus_power", 3),
        Raw(r"\midrule"),
        _heading("Feasibility", 4),
        [r"units with 100 or more scored rows", "", feasible, ""],
        ["share of units with sizes within 10 percent", *[v(rep, f"{at(m)}.share_of_units_with_sizes_within_10_percent", 2) for m in AUDIENCES]],
    ])


def assurance(r):
    """X10 part A: forecast probability of significance against the realized rate in each exposure bin, pooled over cells."""
    rep = r(EXTRAS)
    rungs = ("P0", "P1", "P2", "text_lr")

    def at(rung):
        return f"sizing_evaluation.assurance_by_exposure.rungs.{rung}.ALL"

    names = {0: "lowest", 4: "highest"}
    count = len(rep.get(f"{at('P1')}.bins"))
    if count != 5:
        raise ValueError("the table reads five exposure bins")

    def row(b):
        key = f"{at('P1')}.bins[bin={b}]"
        return [names.get(b, str(b + 1)), n(rep, f"{key}.mean_exposure"), v(rep, f"{key}.realized_rate"), *[v(rep, f"{at(g)}.bins[bin={b}].mean_forecast") for g in rungs]]

    def above(g):
        bins = rep.get(f"{at(g)}.bins")
        return derived(f"{sum(x['mean_forecast'] > x['realized_rate'] for x in bins)} of {len(bins)}", *[rep.ref(f"{at(g)}.bins[bin={x['bin']}].mean_forecast") for x in bins])

    def slope(g, name):
        return v(rep, f"{at(g)}.slope_gap_on_standardized_log_exposure.{name}", 4)

    def bounds(g):
        return lohi(rep, f"{at(g)}.slope_gap_on_standardized_log_exposure.lo", f"{at(g)}.slope_gap_on_standardized_log_exposure.hi", 4)

    return Table("fmt-assurance", "lrrrrrr",
                 ["exposure & mean & realized & P0 & P1 & P2 & text", "bin & exposure & rate & forecast & forecast & forecast & classifier"],
                 [row(b) for b in range(count)] + [
        Raw(r"\midrule"),
        ["bins above the rate", "", "", *[above(g) for g in rungs]],
        ["slope", "", "", *[slope(g, "estimate") for g in rungs]],
        [r"\quad 90\%", "", "", *[bounds(g) for g in rungs]],
    ])


TABLES = [window, leak_choices, exposure_fixed, prior_family, ranking_paired, abstention_composition, gates_strata, drift_null, calibration_shift, learning_paired,
          auc_by_year, sizing, assurance]
