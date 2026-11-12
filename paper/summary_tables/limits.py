"""Summary tables of the limitations section: the verdict on each hypothesis and the period rule of the guard."""
from summary_tables import Raw, Table, derived, fmt, join, month_year, n, narrowest_origin, pct, pctw, v

UPWORTHY, ASOS, EXTRAS = "backtest-upworthy-*.json", "backtest-asos-*.json", "paper-extras-upworthy-*.json"
CURVE, SYNTHETIC = "learning-curve-upworthy-*.json", "paper-extras-synthetic-*.json"
ASOS_GUARD_OFF = "ablations/backtest-asos-*--p2-guard-off.json"
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


def _h1_part1(up, extras):
    origin = narrowest_origin(up)
    paired = f"p1_minus_p0_by_origin.by_origin[origin={origin}]"
    clear = extras.get("p1_minus_p0_by_origin.by_origin_clear_of_zero")
    if clear != len(extras.get("p1_minus_p0_by_origin.by_origin")):
        raise ValueError("the row says clear of zero at all origins")
    return join("above at every origin after burn-in; the narrowest margin {}, {} against {}; paired by test the difference there is {}, {},"
                " and clear of zero at all {} origins",
                month_year(origin),
                w(up, f"tables.score_by_origin[origin={origin},rung=P1].logscore"),
                w(up, f"tables.score_by_origin[origin={origin},rung=P0].logscore"),
                w(extras, f"{paired}.difference", plus=True), span(extras, f"{paired}.lo", f"{paired}.hi"),
                derived(NUMBER_WORDS[clear], extras.ref("p1_minus_p0_by_origin.by_origin_clear_of_zero")))


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

    if not up.get(f"{p2_all}.brier_skill_lo") < 0 < up.get(f"{p2_all}.brier_skill_hi"):
        fail("not clear of zero")
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


def _h1_part2(up, syn):
    """The headline-only difference beside what a planted lift returns in a cell of that size under the same backtest: the verdict word rests on the second being inside the first."""
    headline = _cell("P2", "headline_only")
    planted = 'positive_control_rungs.runs[n_tests=11100].by_cell["headline_only"].rungs[rung=P2].diff_logscore_vs_p1'
    if not up.get(f"{headline}.logscore_vs_p1_lo") < syn.get(planted) < up.get(f"{headline}.logscore_vs_p1_hi"):
        raise ValueError("the row says the interval contains the planted gain")
    return join("{}, {}; the interval contains the {} that a planted lift returns in a cell of this size under the same backtest",
                w(up, f"{headline}.logscore_vs_p1", 4, plus=True),
                span(up, f"{headline}.logscore_vs_p1_lo", f"{headline}.logscore_vs_p1_hi", 4),
                w(syn, planted, 4))


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
    return join("abstained rows, scored on the withheld forecast: with the burn-in origin, above the full set at {}, {}; without it, {}, {}, against {}, {} for issued rows, no measurable difference",
                w(extras, f"{skill}.abstained.brier_skill"), span(extras, f"{skill}.abstained.brier_skill_lo", f"{skill}.abstained.brier_skill_hi"),
                w(extras, f"{composition}.abstained.skill", 4), span(extras, f"{composition}.abstained.lo", f"{composition}.abstained.hi", 4),
                w(extras, f"{composition}.issued.skill", 4), span(extras, f"{composition}.issued.lo", f"{composition}.issued.hi", 4))


def _not_shown_word(up, rung):
    """The verdict of a rung whose adjusted interval spans zero against the matched order: it holds against the plan's random order only where that adjusted bound clears zero."""
    if up.get(f"{_dv(rung)}.diff_matched_adjusted_lo") > 0:
        raise ValueError(f"{rung} clears zero against the matched order; the word is wrong")
    if up.get(f"{_dv(rung)}.diff_random_adjusted_lo") > 0:
        return "not shown against the matched order; held against the plan's random order"
    return "not shown against both orders"


def verdicts(r):
    up, _asos, extras, curve, syn = r(UPWORTHY), r(ASOS), r(EXTRAS), r(CURVE), r(SYNTHETIC)
    p1_all, p2_all, image = _cell("P1", "ALL"), _cell("P2", "ALL"), _cell("P2", "image_only")
    issued, skill = "issued_ece_by_origin.issued", "issued_row_brier_skill.rungs.P2"
    deciles = "tables.coverage_by_se_ratio[rung=P1,decile={}].coverage_90"
    pooled_percentile = f"{issued}.pooled.ece_percentile"
    matched = "against the matched order, {}, adjusted interval {}; against the random order the plan names, adjusted {}"

    def diff(rung):
        return w(up, f"{_dv(rung)}.diff_matched", plus=True)

    def random_bound(rung):
        return span(up, f"{_dv(rung)}.diff_random_adjusted_lo", f"{_dv(rung)}.diff_random_adjusted_hi")

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
        _row("H1 part 1", "P1 beats P0, scored with a normal density as written, on log score at every origin after burn-in", _h1_part1(up, extras), "held"),
        _row("H1 part 2", "P2 beats P1 on headline\\_only", _h1_part2(up, syn), "not shown"),
        _row("H1 part 3", "P2 does not beat P1 on image\\_only",
             join("{} nats, {}: the guard admitted no weight in this cell at any origin", w(up, f"{image}.logscore_vs_p1", 4, plus=True),
                  span(up, f"{image}.logscore_vs_p1_lo", f"{image}.logscore_vs_p1_hi", 4)), "held"),
        Raw(r"\midrule"),
        _group("H2, not shown read pooled; undecidable as written; above zero at one earlier origin, where the base rate lags"),
        _row("H2, read pooled", "P2's Brier skill positive, its interval clear of zero, pooled over origins",
             join("{}, {}, not clear of zero", w(up, f"{p2_all}.brier_skill", 4), span(up, f"{p2_all}.brier_skill_lo", f"{p2_all}.brier_skill_hi", 4)),
             "not shown"),
        _row("H2, as written", "the same at the final origin; the gate decidable there", _h2_as_written(up, curve, extras),
             join("above zero at {}, with that caution, not counted as holding; undecidable at {}", month_year(curve.get("final_origin")), month_year(up.get("header.last_origin")))),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H3, in part} (see~\ref{sec:calibration-results})} \\"),
        _row("H3 part 1", "ECE of issued cards inside the central 90 percent of the null at most origins",
             join("inside at {} of the {} origins that issue cards, not at most of them; pooled at the {}th percentile of the clustered null",
                  n(extras, f"{issued}.origins_inside_central_90"), n(extras, f"{issued}.origins"), n(extras, pooled_percentile)),
             "failed"),
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
             join("issued rows {}, {}, against {} for the full set", w(extras, f"{skill}.issued.brier_skill", 4),
                  span(extras, f"{skill}.issued.brier_skill_lo", f"{skill}.issued.brier_skill_hi", 4), w(extras, f"{skill}.all.brier_skill", 4)),
             "failed"),
        _row("H4 part 2", "abstained rows lower on skill when forced", _h4_part2(extras, skill), "failed on all rows; not shown once burn-in is excluded"),
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
