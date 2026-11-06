"""Summary tables of the limitations section: the verdict on each hypothesis and the period rule of the guard."""
from datetime import datetime

from summary_tables import Raw, Table, derived, fmt, join, n, pct, pctw, v

UPWORTHY, ASOS, EXTRAS = "backtest-upworthy-*.json", "backtest-asos-*.json", "paper-extras-upworthy-*.json"
NUMBER_WORDS = {9: "nine"}


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


def _narrowest_origin(up):
    """The origin after burn-in where P1 leads P0 by least; an origin where P1 does not lead fails the build, since the row says above at every one."""
    def score(origin, rung):
        return up.get(f"tables.score_by_origin[origin={origin},rung={rung}].logscore")

    origins = [o["origin"] for o in up.get("tables.origins") if not o["burn_in"]]
    margins = {o: score(o, "P1") - score(o, "P0") for o in origins}
    if min(margins.values()) <= 0:
        raise ValueError("P1 is not above P0 at every origin after burn-in")
    return min(margins, key=margins.get)


def _h1_part1(up, extras):
    origin = _narrowest_origin(up)
    paired = f"p1_minus_p0_by_origin.by_origin[origin={origin}]"
    clear = extras.get("p1_minus_p0_by_origin.by_origin_clear_of_zero")
    if clear != len(extras.get("p1_minus_p0_by_origin.by_origin")):
        raise ValueError("the row says clear of zero at all origins")
    return join("above at every origin after burn-in; the narrowest margin {}, {} against {}; paired by test the difference there is {}, {},"
                " and clear of zero at all {} origins",
                datetime.fromisoformat(origin).strftime("%B %Y"),
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


def verdicts(r):
    up, _asos, extras = r(UPWORTHY), r(ASOS), r(EXTRAS)
    p1_all, p2_all, headline, image = _cell("P1", "ALL"), _cell("P2", "ALL"), _cell("P2", "headline_only"), _cell("P2", "image_only")
    issued, skill = "issued_ece_by_origin.issued", "issued_row_brier_skill.rungs.P2"
    deciles = "tables.coverage_by_se_ratio[rung=P1,decile={}].coverage_90"
    pooled_percentile = f"{issued}.pooled.ece_percentile"
    matched = "against the matched order, {}, adjusted interval {}"

    def diff(rung):
        return w(up, f"{_dv(rung)}.diff_matched", plus=True)

    def random_bound(rung):
        return span(up, f"{_dv(rung)}.diff_random_adjusted_lo", f"{_dv(rung)}.diff_random_adjusted_hi")

    rows = [
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H1, held in part} (Section~\ref{sec:ladder-results})} \\"),
        _row("H1 part 1", "P1 beats P0 on log score at every origin after burn-in", _h1_part1(up, extras), "held"),
        _row("H1 part 2", "P2 beats P1 on headline\\_only",
             join("{}, {}, with the family held fixed", w(up, f"{headline}.logscore_vs_p1", 4, plus=True),
                  span(up, f"{headline}.logscore_vs_p1_lo", f"{headline}.logscore_vs_p1_hi", 4)), "refuted"),
        _row("H1 part 3", "P2 does not beat P1 on image\\_only",
             join("{} nats, {}", w(up, f"{image}.logscore_vs_p1", 4, plus=True),
                  span(up, f"{image}.logscore_vs_p1_lo", f"{image}.logscore_vs_p1_hi", 4)), "held, as planned"),
        Raw(r"\midrule"),
        _group("H2, refuted"),
        _row("H2", "P2's Brier skill positive, its interval clear of zero",
             join("{}, {}, not clear of zero", w(up, f"{p2_all}.brier_skill"), span(up, f"{p2_all}.brier_skill_lo", f"{p2_all}.brier_skill_hi")),
             "refuted"),
        Raw(r"\midrule"),
        _group("H3, held in part"),
        _row("H3 part 1", "ECE of issued cards inside the central 90 percent of the null at most origins",
             join("inside at {} of the {} origins that issue cards, not at most of them; pooled at the {}th percentile of the clustered null",
                  n(extras, f"{issued}.origins_inside_central_90"), n(extras, f"{issued}.origins"), n(extras, pooled_percentile)),
             "refuted"),
        _row("H3 part 2", "80 and 90 percent coverage within 5 points of nominal",
             join("{} percent, {} to {}, and {} percent, {} to {}, within 5 points of nominal pooled; {} to {} across deciles"
                  " (a range, not an interval) of the realized level",
                  pct(up, f"{p1_all}.coverage_80"), pct(up, f"{p1_all}.coverage_80_lo"), pct(up, f"{p1_all}.coverage_80_hi"),
                  pct(up, f"{p1_all}.coverage_90"), pct(up, f"{p1_all}.coverage_90_lo"), pct(up, f"{p1_all}.coverage_90_hi"),
                  v(up, deciles.format(1), 2), v(up, deciles.format(10), 2)),
             "holds pooled, fails within strata"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H4, held in part} (Section~\ref{sec:abstention-results})} \\"),
        _row("H4 part 1", "issued cards above the full set on skill",
             join("issued rows {}, {}, against {} for the full set", w(extras, f"{skill}.issued.brier_skill"),
                  span(extras, f"{skill}.issued.brier_skill_lo", f"{skill}.issued.brier_skill_hi"), w(extras, f"{skill}.all.brier_skill")),
             "refuted"),
        _row("H4 part 2", "abstained rows lower on skill when forced",
             join("abstained rows, scored on the withheld forecast, above the full set at {}, {}", w(extras, f"{skill}.abstained.brier_skill"),
                  span(extras, f"{skill}.abstained.brier_skill_lo", f"{skill}.abstained.brier_skill_hi")),
             "refuted"),
        _row("H4 part 3", "abstention below 30 percent after burn-in",
             join("{} percent pooled and {} percent after the burn-in origin", pct(up, "tables.abstention[cell=ALL].rate"), _h4_after_burn_in(up)),
             "held"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H5, held in part under the stricter reading} (Sections~\ref{sec:hypotheses} and~\ref{sec:decision-results})} \\"),
        _row("H5, text classifier", "more positive lift than random at K = 25 percent of tests",
             join("against the arm-count-matched random order, {}, adjusted interval {}", diff("text_lr"), _adjusted(up, "text_lr")), "confirmed"),
        _row("H5, boosted model", "the same", join(matched, diff("GBM"), _adjusted(up, "GBM")), "confirmed"),
        _row("H5, precedent rung", "the same",
             join(matched + "; against the random order the plan names, adjusted bound {}", diff("P2"), _adjusted(up, "P2"), random_bound("P2")),
             "unresolved; confirmed against the plan's random order"),
        _row("H5, local comparison set", "the same",
             join(matched + "; against the random order the plan names, {}", diff("local_eb"), _adjusted(up, "local_eb"), random_bound("local_eb")),
             "unresolved on both"),
        _row("H5, prior", "the same",
             join("at the matched order within noise, {}, {}", w(up, f"{_dv('P1')}.diff_matched"),
                  span(up, f"{_dv('P1')}.diff_matched_lo", f"{_dv('P1')}.diff_matched_hi")), "failed"),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{4}{@{}l}{\textbf{H6, confirmed} (Section~\ref{sec:asos-results})} \\"),
        _row("H6 part 1", "every gate undecidable on the deployment-shaped archive", "undecidable at every gate", "held"),
        _row("H6 part 2", "P2 equals P1", "P2 equals P1 there", "held"),
    ]
    header = " & ".join(f"\\raggedright {h}" for h in ("hypothesis", "what was planned", "what was measured", "verdict"))
    return Table("verdicts", r"@{}p{0.11\textwidth}p{0.26\textwidth}p{0.43\textwidth}p{0.13\textwidth}@{}", [header], rows, end=r" \tabularnewline")


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
