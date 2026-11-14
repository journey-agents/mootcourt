"""Summary tables of the limitations section: the verdict on each hypothesis and the period rule of the guard."""
from summary_tables import Raw, Table, derived, fmt, join, month_year, n, pct, pctw, v

UPWORTHY, ASOS, EXTRAS = "backtest-upworthy-*.json", "backtest-asos-*.json", "paper-extras-upworthy-*.json"
CURVE, SYNTHETIC = "learning-curve-upworthy-*.json", "paper-extras-synthetic-*.json"
# the first specification: the main run of run 8, a normal base rate and each row's own realized traffic as its planned exposure
FIRST = "ablations/backtest-upworthy-*--exposure-planned+base-density-normal.json"
BY_ORIGIN = ("by-origin-upworthy-*.json", "ablations/by-origin-upworthy-*--base-density-normal.json",
             "ablations/by-origin-upworthy-*--exposure-planned+base-density-normal.json")
ASOS_GUARD_OFF = "ablations/backtest-asos-*--p2-guard-off.json"
NEAR_ZERO = 0.0005        # a bound within a few ten-thousandths of zero is not read as clearing it (Section 5 of the paper)
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def _words(x, nd, plus):
    """A number in running text: a sign is a word, and a value that rounds to zero has none unless ``plus`` asks for one."""
    text = fmt(abs(x), nd)
    if x < 0 and float(text) != 0.0:
        return "minus " + text
    return "plus " + text if plus else text


def w(rep, key, nd=3, plus=False):
    return derived(_words(rep.get(key), nd, plus), rep.ref(key))


def span(rep, lo, hi, nd=3):
    return join("{} to {}", w(rep, lo, nd), w(rep, hi, nd))


def _cell(rung, name):
    return f"tables.aggregate[cell={name},rung={rung}]"


def _dv(rung):
    return f"tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung={rung}]"


def _row(*cells):
    return [join("\\raggedright {}", c) for c in cells]


def _group(text):
    return Raw(rf"\multicolumn{{4}}{{@{{}}l}}{{\textbf{{{text}}}}} \\")


def _adjusted(rep, rung):
    """Where the family-adjusted interval of the matched difference sits."""
    lo_key, hi_key = f"{_dv(rung)}.diff_matched_adjusted_lo", f"{_dv(rung)}.diff_matched_adjusted_hi"
    lo, hi = rep.get(lo_key), rep.get(hi_key)
    text = "above zero" if lo > 0 else "below zero" if hi < 0 else "spanning zero"
    return derived(text, rep.ref(lo_key), rep.ref(hi_key))


def _h1_part1(main, normal, first):
    """H1 part 1 from the three by-origin reports: the main run (Student-t base rate), the normal base rate the plan's code used, and the
    first specification (that density with each row's own realized traffic). The counts are of origins whose paired interval lies above zero."""
    total = len(main.get("by_origin"))
    if first.get("by_origin_above_zero") != total:
        raise ValueError("the row says above zero at every origin in the first specification")
    if normal.get("by_origin_above_zero") == total or normal.get("by_origin_below_zero") != 0:
        raise ValueError("the row says above zero at some origins and below at none with the normal base rate")

    def count(rep, key):
        return derived(NUMBER_WORDS[rep.get(key)], rep.ref(key))

    return join("in the first specification, which read each row's own realized traffic, the paired difference lies above zero at all {} scored origins;"
                " with exposure fixed on visible rows and the same normal density, at {} of them and below zero at none;"
                " in the main run, where the base rate is a Student-t, above zero at {} and below at {}",
                derived(NUMBER_WORDS[total], first.ref("by_origin_above_zero")), count(normal, "by_origin_above_zero"),
                count(main, "by_origin_above_zero"), count(main, "by_origin_below_zero"))


def _h4_after_burn_in(up):
    """The abstention rate without the burn-in origin, on which every card abstains: pooled abstained rows less that origin's, over the rows left."""
    all_rate, all_n = "tables.abstention[cell=ALL].rate", "tables.abstention[cell=ALL].n"
    burn = [o["origin"] for o in up.get("tables.origins") if o["burn_in"]]
    keys = [k for o in burn for k in (f"tables.origins[origin={o}].n_scored", f"tables.origins[origin={o}].abstention_rate")]
    burn_rows = sum(up.get(k) for k in keys[::2])
    burn_abstained = sum(up.get(a) * up.get(b) for a, b in zip(keys[::2], keys[1::2]))
    rate = (up.get(all_rate) * up.get(all_n) - burn_abstained) / (up.get(all_n) - burn_rows)
    return derived(fmt(rate * 100, 1), up.ref(all_rate), up.ref(all_n), *[up.ref(k) for k in keys])


def _guard_verdict_wording(up, asos, extras, p2_all, p1_all, issued, skill):
    """The measured words typed in the rows of ``verdicts``: each is checked here, so a change of run that falsifies one stops the build."""
    def fail(words):
        raise ValueError(f"the verdicts table says {words!r} and the report does not")

    if up.get(f"{p2_all}.brier_skill_lo") <= 0 or up.get(f"{p2_all}.brier_skill") >= 0.015:
        fail("clear of zero, and about one percent")
    if 2 * extras.get(f"{issued}.origins_inside_central_90") > extras.get(f"{issued}.origins"):
        fail("not at most of them")
    for name, nominal in (("coverage_80", 0.80), ("coverage_90", 0.90)):
        if abs(up.get(f"{p1_all}.{name}") - nominal) > 0.05:
            fail("within 5 points of nominal pooled")
    if extras.get(f"{skill}.abstained.brier_skill") <= extras.get(f"{skill}.all.brier_skill"):
        fail("abstained rows above the full set")
    if not up.get(f"{_dv('P1')}.diff_matched_lo") < 0 < up.get(f"{_dv('P1')}.diff_matched_hi"):
        fail("at the matched order within noise")
    aggregate = [row for row in asos.get("tables.aggregate") if row["cell"] == "ALL" and row.get("decidable_by_tests")]
    if not aggregate or any(not row["decidable_by_tests"].startswith("undecidable") for row in aggregate):
        fail("undecidable at every gate")
    if asos.get(f"{_cell('P2', 'ALL')}.logscore_vs_p1") != 0:
        fail("P2 equals P1 on this archive")


def _h1_part2(up, seeds):
    """The headline-only difference beside what a planted lift returns in a cell of that size under the same backtest, at five ledger seeds."""
    headline = _cell("P2", "headline_only")
    if up.get(f"{headline}.logscore_vs_p1") >= 0 or up.get(f"{headline}.logscore_vs_p1_hi") <= 0:
        raise ValueError("the verdict says the estimate is on the wrong side and its interval contains zero")
    if abs(seeds.get("real_interval.hi") - up.get(f"{headline}.logscore_vs_p1_hi")) > 1e-12:
        raise ValueError("the seeds report was not read against this run's interval")
    inside, total = seeds.get("inside_real_interval"), seeds.get("seeds")
    if not 0 < inside < total:
        raise ValueError("the row says the planted gain falls inside the interval at some seeds and not at all")
    return join("{}, {}; the interval contains what a planted lift returns in a cell of this size under the same backtest at {} of {} ledger seeds"
                " (median {}, largest {})",
                w(up, f"{headline}.logscore_vs_p1", 4, plus=True),
                span(up, f"{headline}.logscore_vs_p1_lo", f"{headline}.logscore_vs_p1_hi", 4),
                derived(NUMBER_WORDS[inside], seeds.ref("inside_real_interval")), derived(NUMBER_WORDS[total], seeds.ref("seeds")),
                w(seeds, "median.p2_minus_p1_headline_only", 4), w(seeds, "max.p2_minus_p1_headline_only", 4))


def _h2_as_written(up, curve, extras):
    """H2 at the final origin, as the plan words it: the learning curve's final origin at the full history, the calendar's last origin by its test count, and the base rate's lag."""
    final = curve.get("final_origin")
    last = up.get("header.last_origin")
    p2 = "rows[fraction=1.0,rung=P2]"
    gate_key = "gates_by_stratum.strata.ALL.own_gate.n_400"
    tests, gate = curve.get("heldout_tests"), extras.get(gate_key)
    last_tests = f"tables.origins[origin={last}].n_tests"
    smallest_gate = min(s["own_gate"]["n_200"] for s in extras.get("gates_by_stratum.strata").values())
    if curve.get(f"{p2}.skill_lo") <= 0 or tests < gate:
        raise ValueError("the row says held at the learning curve's final origin")
    if up.get(last_tests) >= smallest_gate:
        raise ValueError("the row says the last origin is below every gate")
    p0, event = f'drift_matched_null.rungs.P0.by_origin["{final}"].mean_forecast', f'drift_matched_null.rungs.P0.by_origin["{final}"].event_rate'
    if extras.get(p0) <= extras.get(event):
        raise ValueError("the row says the base rate lags above the event rate")
    return join("at {}, the latest origin with enough held-out rows for the learning curve: {}, {}, on {} tests, where the pooled gate of {} was simulated at the pooled event rate and not at this origin's; there the base rate is {} and the event rate {},"
                " so the base rate lags and part of the skill may be that lag; at {}, the last origin of the calendar: {} tests, below every gate",
                month_year(final),
                w(curve, f"{p2}.skill"), span(curve, f"{p2}.skill_lo", f"{p2}.skill_hi"), n(curve, "heldout_tests"), n(extras, gate_key),
                w(extras, p0), w(extras, event), month_year(last), n(up, last_tests))


def _h4_part2(extras, skill):
    composition = "abstention_composition.P2"
    if extras.get(f"{composition}.abstained.lo") > extras.get(f"{composition}.issued.skill") or extras.get(f"{composition}.abstained.hi") < extras.get(f"{composition}.issued.skill"):
        raise ValueError("the row says the two groups do not differ measurably without burn-in")
    return join("abstained rows, scored on the withheld forecast: with the burn-in origin, above the full set at {}, {}; without it, {}, {}, against {}, {} for issued rows,"
                " no measurable difference; within a pair of origin and cell the prior gives both groups the same probability, so a difference there reads"
                " event rates and not forecasts",
                w(extras, f"{skill}.abstained.brier_skill"), span(extras, f"{skill}.abstained.brier_skill_lo", f"{skill}.abstained.brier_skill_hi"),
                w(extras, f"{composition}.abstained.skill", 4), span(extras, f"{composition}.abstained.lo", f"{composition}.abstained.hi", 4),
                w(extras, f"{composition}.issued.skill", 4), span(extras, f"{composition}.issued.lo", f"{composition}.issued.hi", 4))


def _h2_gate(up, extras):
    """H2's gate claim: the calendar's last origin by its test count against the pooled gates at power 0.90."""
    last = up.get("header.last_origin")
    last_tests = f"tables.origins[origin={last}].n_tests"
    gate = "gates_by_stratum.strata.ALL.own_gate"
    if up.get(last_tests) >= extras.get(f"{gate}.n_200"):
        raise ValueError("the row says the last origin is below both released gates")
    return join("the last origin of the calendar, {}, holds {} tests, below the gate of {} for a skill of 0.10 and below every other gate",
                month_year(last), n(up, last_tests), n(extras, f"{gate}.n_400"))


def _h4_part2_verdict(extras):
    """The verdict of H4 part 2: failed with the burn-in origin; without it the pooled estimate and the estimate within pairs lie on opposite sides."""
    pooled = "abstention_composition.P2.pooled_issued_minus_abstained_skill"
    within = "abstention_composition.P2.stratified_issued_minus_abstained_skill.estimate"
    if extras.get(pooled) <= 0 or extras.get(within) >= 0:
        raise ValueError("the verdict says the pooled estimate is on the claim's side and the estimate within pairs on the other")
    return derived("failed on all rows; with burn-in excluded, the pooled estimate is on the claim's side and the estimate within pairs of origin"
                   " and cell on the other, and neither reads the forecasts", extras.ref(pooled), extras.ref(within))


def _not_shown_word(up, rung):
    """The verdict of a rung whose adjusted interval spans zero against the matched order: it holds against the plan's random order only where that adjusted bound clears zero."""
    if up.get(f"{_dv(rung)}.diff_matched_adjusted_lo") > 0:
        raise ValueError(f"{rung} clears zero against the matched order; the word is wrong")
    if up.get(f"{_dv(rung)}.diff_random_adjusted_lo") > NEAR_ZERO:
        return "not shown against the matched order; held against the plan's random order"
    if up.get(f"{_dv(rung)}.diff_random_adjusted_lo") > 0:
        return "not shown against both orders; against the random order the adjusted lower end is too close to zero to read as clear of it"
    return "not shown against both orders"


def verdicts(r):
    up, _asos, extras, curve = r(UPWORTHY), r(ASOS), r(EXTRAS), r(CURVE)
    first = r(FIRST)
    skill_origin = r("by-origin-skill-upworthy-*.json")
    burn = [o["origin"] for o in up.get("tables.origins") if o["burn_in"]]
    if len(burn) != 1:
        raise ValueError("the rows name one burn-in origin")
    burn_in = burn[0]
    if skill_origin.get(f"rungs.P2.realized.leave_one_origin_out[left_out={burn_in}].skill") >= extras.get("issued_row_brier_skill.rungs.P2.issued.brier_skill"):
        raise ValueError("the row says issued rows are above the full set once burn-in is left out")
    if skill_origin.get("rungs.P2.realized.origin_level.lo") <= 0 or skill_origin.get("rungs.P2.realized.without_zero_base_rate_strata.lo") <= 0:
        raise ValueError("the row says the skill of P2 is clear of zero with the quarters as units and without the stratum whose base rate is zero")
    if not first.get(f"{_cell('P2', 'ALL')}.brier_skill_lo") < 0 < first.get(f"{_cell('P2', 'ALL')}.brier_skill_hi"):
        raise ValueError("the row says the skill of P2 is not clear of zero in the first specification")
    p1_all, p2_all, image = _cell("P1", "ALL"), _cell("P2", "ALL"), _cell("P2", "image_only")
    issued, skill = "issued_ece_by_origin.issued", "issued_row_brier_skill.rungs.P2"
    deciles = "tables.coverage_by_se_ratio[rung=P1,decile={}].coverage_90"
    pooled_percentile = f"{issued}.pooled.ece_percentile"
    matched = "against the matched order, {}, adjusted interval {}; against the random order the plan names, adjusted {}"

    def diff(rung):
        return w(up, f"{_dv(rung)}.diff_matched", plus=True)

    def random_bound(rung):
        return span(up, f"{_dv(rung)}.diff_random_adjusted_lo", f"{_dv(rung)}.diff_random_adjusted_hi", 4)

    def not_shown(rung, label):
        return _row(label, "the same", join(matched, diff(rung), _adjusted(up, rung), random_bound(rung)), _not_shown_word(up, rung))

    _guard_verdict_wording(up, _asos, extras, p2_all, p1_all, issued, skill)
    if up.get(f"{_dv('text_lr')}.diff_matched_adjusted_lo") <= 0:
        raise ValueError("the row says the text classifier holds against the matched order")
    if any(row["lambda"] != 0 for row in up.get("tables.p2_selection") if row["cell"] == "image_only"):
        raise ValueError("the row says the guard admitted no weight in image_only")
    if up.get("tables.origins[origin=2014-01-01T00:00:00+00:00].abstention_rate") != 1 or up.get("tables.origins[origin=2014-01-01T00:00:00+00:00].burn_in"):
        raise ValueError("the row says January 2014 abstains on every row and stays in the after-burn-in rate")
    guard_off = r(ASOS_GUARD_OFF)
    if guard_off.get(f"{_cell('P2', 'ALL')}.logscore_vs_p1") == 0:
        raise ValueError("the row says the guard is what keeps P2 at P1 on the retailer's archive")
    rows = [
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H1, in part} (see~\ref{sec:ladder-results})} \\"),
        _row("H1 part 1", "P1 beats P0 on log score at every origin after burn-in, P0 scored with a normal density, as in the code committed with the plan",
             _h1_part1(*(r(name) for name in BY_ORIGIN)), "held in the first specification; with exposure fixed, not shown against the normal base rate and failed in the main run"),
        _row("H1 part 2", "P2 beats P1 on headline\\_only", _h1_part2(up, r("positive-control-seeds.json")), "failed: the estimate is on the wrong side, and its interval contains zero"),
        _row("H1 part 3", "P2 does not beat P1 on image\\_only",
             join("{} nats, {}: the guard gave no weight in this cell at any origin", w(up, f"{image}.logscore_vs_p1", 4, plus=True),
                  span(up, f"{image}.logscore_vs_p1_lo", f"{image}.logscore_vs_p1_hi", 4)), "held"),
        Raw(r"\midrule"),
        _group("H2, in part: the gate claim failed; read pooled, a skill of about one percent in the main run and none shown in the first specification"),
        _row("H2, read pooled", "P2's Brier skill positive, its interval clear of zero, pooled over origins",
             join("{}, {}, with tests resampled; {}, {}, with the seven quarters as units; without the one cell and quarter in which the base rate"
                  " is zero, {}, {}; in the first specification {}, {}, not clear of zero",
                  w(up, f"{p2_all}.brier_skill", 4), span(up, f"{p2_all}.brier_skill_lo", f"{p2_all}.brier_skill_hi", 4),
                  w(skill_origin, "rungs.P2.realized.origin_level.skill", 4),
                  span(skill_origin, "rungs.P2.realized.origin_level.lo", "rungs.P2.realized.origin_level.hi", 4),
                  w(skill_origin, "rungs.P2.realized.without_zero_base_rate_strata.skill", 4),
                  span(skill_origin, "rungs.P2.realized.without_zero_base_rate_strata.lo", "rungs.P2.realized.without_zero_base_rate_strata.hi", 4),
                  w(first, f"{p2_all}.brier_skill", 4), span(first, f"{p2_all}.brier_skill_lo", f"{p2_all}.brier_skill_hi", 4)),
             "held in the main run, with tests resampled and with the seven quarters as the units, at about one percent of the base rate's score; not shown in the first specification"),
        _row("H2, as written", "the same at the final origin", _h2_as_written(up, curve, extras),
             join("above zero at {}, with that caution, not counted as holding; undecidable at {}", month_year(curve.get("final_origin")), month_year(up.get("header.last_origin")))),
        _row("H2, the gate", "the released gate decidable at the final origin", _h2_gate(up, extras), "failed"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H3, in part} (see~\ref{sec:calibration-results})} \\"),
        _row("H3 part 1", "ECE of issued cards inside the central 90 percent of the null at most origins",
             join("inside the central 90 percent (a two-sided count) at {} of the {} origins that issue cards, not at most of them; pooled over issued rows the percentile is {}, which is"
                  " within simulation error of the line at 95 and is not read",
                  n(extras, f"{issued}.origins_inside_central_90"), n(extras, f"{issued}.origins"), v(extras, pooled_percentile, 1)),
             "failed, on the count of origins"),
        _row("H3 part 2", "80 and 90 percent coverage within 5 points of nominal",
             join("{} percent, {} to {}, and {} percent, {} to {}, within 5 points of nominal pooled; {} to {} across deciles"
                  " (a range, not an interval) of the ratio of realized to planned standard error",
                  pct(up, f"{p1_all}.coverage_80"), pct(up, f"{p1_all}.coverage_80_lo"), pct(up, f"{p1_all}.coverage_80_hi"),
                  pct(up, f"{p1_all}.coverage_90"), pct(up, f"{p1_all}.coverage_90_lo"), pct(up, f"{p1_all}.coverage_90_hi"),
                  v(up, deciles.format(1), 2), v(up, deciles.format(10), 2)),
             "held, read pooled; the fall across deciles is descriptive"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H4, in part} (see~\ref{sec:abstention-results})} \\"),
        _row("H4 part 1", "issued cards above the full set on skill",
             join("issued rows {}, {}, against {} for the full set; without the burn-in origin, on which every card abstains, the full set is at {}",
                  w(extras, f"{skill}.issued.brier_skill", 4),
                  span(extras, f"{skill}.issued.brier_skill_lo", f"{skill}.issued.brier_skill_hi", 4), w(extras, f"{skill}.all.brier_skill", 4),
                  w(skill_origin, f"rungs.P2.realized.leave_one_origin_out[left_out={burn_in}].skill", 4)),
             "failed on all rows; with burn-in excluded, on the claim's side, given as measured with no interval"),
        _row("H4 part 2", "abstained rows lower on skill when forced", _h4_part2(extras, skill), _h4_part2_verdict(extras)),
        _row("H4 part 3", "abstention below 30 percent after burn-in",
             join("{} percent pooled and {} percent after the burn-in origin, January 2014 included", pct(up, "tables.abstention[cell=ALL].rate"), _h4_after_burn_in(up)),
             "held"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H5, in part} (Sections~\ref{sec:hypotheses} and~\ref{sec:decision-results})} \\"),
        _row("H5, text classifier", "more positive lift than random at K = 25 percent of tests",
             join("against the arm-count-matched random order, {}, adjusted interval {}", diff("text_lr"), _adjusted(up, "text_lr")), "held against the matched order"),
        not_shown("GBM", "H5, boosted model"),
        not_shown("P2", "H5, precedent rung"),
        not_shown("local_eb", "H5, local comparison set"),
        _row("H5, prior", "the same",
             join("at the matched order within noise, {}, {}", w(up, f"{_dv('P1')}.diff_matched"),
                  span(up, f"{_dv('P1')}.diff_matched_lo", f"{_dv('P1')}.diff_matched_hi")), "failed"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H6, held} (see~\ref{sec:asos-results})} \\"),
        _row("H6 part 1", "every gate undecidable on the retailer's archive", "undecidable at every gate",
             join("held, a result {} tests could not have avoided", n(_asos, f"{_cell('P2', 'ALL')}.n_tests"))),
        _row("H6 part 2", "P2 equals P1", "P2 equals P1 on this archive, because the guard holds the weight at zero", "held"),
    ]
    header = " & ".join(f"\\raggedright {h}" for h in ("hypothesis", "what was planned", "what was measured", "verdict"))
    return Table("verdicts", r"@{}p{0.10\textwidth}p{0.21\textwidth}p{0.45\textwidth}p{0.17\textwidth}@{}", [header], rows, end=r" \tabularnewline")


def period_rule(r):
    rep = r("paper-extras-synthetic-*.json")
    small, large = 3700, 11100

    def at(arm, size, field):
        return f"guard_period_control.rows[arm={arm},n_tests={size}].{field}"

    def row(label, arm, rows=True):
        cells = [label]
        for size in (small, large):
            cells.append(pctw(rep, at(arm, size, "share_admitted")))
            cells.append(n(rep, at(arm, size, "mean_rows_in_period_level")) if rows else "none")
        return cells

    top = join("& \\multicolumn{{2}}{{c}}{{{} tests}} & \\multicolumn{{2}}{{c}}{{{} tests}}",
               n(rep, at("new_rule", small, "n_tests")), n(rep, at("new_rule", large, "n_tests")))
    return Table("fmt-period-rule", "lrrrr", [top, "rule for the period level & share & rows & share & rows"], [
        row("old rule (the latest period, however thin)", "old_rule"),
        row("no period at all", "old_rule_no_period", rows=False),
        row("rule in force (last complete quarter)", "new_rule"),
    ])


TABLES = [verdicts, period_rule]
