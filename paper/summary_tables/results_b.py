"""Summary tables, group results_b: abstention, drift, the deployment-shaped archive and the positive control (Sections 6.5 to 6.8)."""
from summary_tables import Raw, Table, ci, derived, fmt, join, lohi, n, pctw, v

MAIN = "backtest-upworthy-*.json"
EXTRAS = "paper-extras-upworthy-*.json"
ASOS = "backtest-asos-*.json"
ASOS_EXTRAS = "paper-extras-asos-*.json"
SYNTHETIC_EXTRAS = "paper-extras-synthetic-*.json"
CONTROL = "positive-control/backtest-synthetic-*.json"
WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def abstention_triggers(r):
    main, extras = r(MAIN), r(EXTRAS)
    row = "tables.abstention[cell=ALL]"
    # The cells where the support trigger fires, and the pairs (cell, origin) where the guard holds the precedent weight at zero.
    abst = [c for c in main.get("tables.abstention") if c["cell"] != "ALL"]
    two = derived(WORDS[sum(c["support"] > 0 for c in abst)], *[main.ref(f"tables.abstention[cell={c['cell']}].support") for c in abst])
    sel = main.get("tables.p2_selection_by_cell")
    zero_keys = [main.ref(f"tables.p2_selection_by_cell[cell={c['cell']}].{f}") for c in sel for f in ("share_lambda_zero", "origins")]
    zero = derived(fmt(sum(c["share_lambda_zero"] * c["origins"] for c in sel), 0), *zero_keys)
    novelty_share = derived(fmt(main.get(f"{row}.novelty") / main.get(f"{row}.n") * 100, 1) + r"\%", main.ref(f"{row}.novelty"), main.ref(f"{row}.n"))
    return Table("fmt-abstention-triggers", r"lrrp{0.5\columnwidth}", ["trigger & rows & share & when it fires"], [
        ["reliability", n(main, f"{row}.reliability"), "", "on the rows of the burn-in origin and never after"],
        ["support", n(main, f"{row}.support"), "", join("on rows of the burn-in origin, in the {} cells with fewer than 30 visible rows", two)],
        ["novelty", n(main, f"{row}.novelty"), novelty_share, "the only trigger that fires after burn-in"],
        ["decision instability", n(main, f"{row}.instability"), "", join("never, being off by construction in the {} pairs where the precedent weight is zero", zero)],
        Raw(r"\midrule"),
        ["any trigger", n(extras, "issued_row_brier_skill.rungs.P2.abstained.n"), join(r"{}\%", v(main, f"{row}.rate", 1, scale=100)), "the pooled abstention rate"],
    ])


def abstention_rows(r):
    main, extras = r(MAIN), r(EXTRAS)
    agg = "tables.aggregate[cell=ALL,rung=P2]"

    def row(label, side, log):
        key = f"issued_row_brier_skill.rungs.P2.{side}"
        return [label, n(extras, f"{key}.n"), ci(extras, key, "brier_skill"), log, v(extras, f"{key}.event_rate", 2)]

    return Table("fmt-abstention-rows", "lrrrr", [r"row set & rows & Brier skill (90\%) & log score & event rate"], [
        row("issued", "issued", v(main, f"{agg}.logscore_nonabstained")),
        row("abstained", "abstained", ""),
        row("all rows", "all", v(main, f"{agg}.logscore")),
    ])


def abstention_released(r):
    main = r(MAIN)
    agg = "tables.aggregate[cell=ALL,rung=P2]"

    def released(label, trigger):
        rep = r(f"ablations/backtest-upworthy-*--drop-trigger-{trigger}.json")
        key = "tables.released_rows[cell=ALL,rung=P2]"
        return [label, n(rep, f"{key}.n"), ci(rep, key, "logscore"), ci(rep, key, "direction_accuracy")]

    return Table("fmt-abstention-released", "lrrr", [r"rows & count & log score (90\%) & direction accuracy (90\%)"], [
        released("released by novelty", "novelty"),
        released("burn-in rows released by reliability alone", "reliability"),
        Raw(r"\midrule"),
        ["issued rows, main run", n(main, f"{agg}.n_nonabstained"), ci(main, agg, "logscore_nonabstained"), ci(main, agg, "direction_accuracy_nonabstained")],
    ])


def drift_year(r):
    main = r(MAIN)

    def row(year, adjusted=False):
        key = f"tables.score_by_year[cell=ALL,rung=P1,year={year}]"
        return [v(main, f"{key}.year", 0), n(main, f"{key}.n_tests"), ci(main, key, "brier_skill"),
                lohi(main, f"{key}.adjusted_lo", f"{key}.adjusted_hi") if adjusted else "", v(main, f"{key}.event_rate")]

    return Table("fmt-drift-year", "rrrrr", [r"year & tests & P1 Brier skill (90\%) & adjusted interval & significant-positive rate"], [
        row(2013), row(2014), row(2015, adjusted=True),
    ])


def asos(r):
    rep, gates = r(ASOS), r("gates.json")
    extras, headline = r(ASOS_EXTRAS), r(EXTRAS)
    agg = "tables.aggregate[cell=ALL,rung=P1]"
    origins = "header.origins_scored"
    base = rep.get(f"{agg}.gate_base_rate")
    gate = f'by_base_rate["{fmt(base, 2)}"]'
    corr = "impressions_effect_correlation.corr_log_impressions_abs_z"
    return Table("fmt-asos", "lr", ["figure & value"], [
        ["scored contrasts", n(rep, "header.scored_rows")],
        ["experiments", n(rep, "header.tests_scored")],
        ["nominal quarterly origins", derived(WORDS[rep.get(origins)], rep.ref(origins))],
        [join("gate at base rate {} (tests)", v(rep, f"{agg}.gate_base_rate", 2)), join("{} and {}", n(gates, f"{gate}.n_200"), n(gates, f"{gate}.n_400"))],
        ["abstention rate", v(rep, f"{agg}.abstention_rate")],
        ["support trigger, rows at the early origins", n(rep, "tables.abstention[cell=ALL].support")],
        [r"P1 Brier skill (90\%)", ci(rep, agg, "brier_skill")],
        ["P1 Brier skill, adjusted interval", lohi(rep, f"{agg}.adjusted_lo", f"{agg}.adjusted_hi")],
        ["expected calibration error", v(rep, f"{agg}.ece")],
        ["calibration percentile", v(rep, f"{agg}.ece_percentile", 1)],
        ["design effect", v(rep, f"{agg}.design_effect", 1)],
        ["coverage of the 80 and 90 percent intervals", join("{} and {}", v(rep, f"{agg}.coverage_80", 2), v(rep, f"{agg}.coverage_90", 2))],
        ["exposure stand-in against the absolute standardized effect, correlation", v(extras, corr)],
        ["the same correlation on the headline archive", v(headline, corr)],
    ])


def control(r):
    extras, whole = r(SYNTHETIC_EXTRAS), r(CONTROL)

    def row(size, cell_figure=False):
        key = f"positive_control_sensitivity.rows[n_tests={size},text_effect_strength=1.0]"
        cell = v(extras, f"{key}.by_cell[cell=headline_only].recovered_fraction", 2) if cell_figure else ""
        return [n(extras, f"{key}.n_tests"), n(extras, f"{key}.rows_per_cell"), join("{} of cells", pctw(extras, f"{key}.share_admitted")),
                ci(extras, key, "recovered_fraction", 2), cell]

    run = "positive_control_rungs.runs[n_tests=2000]"
    scored = extras.get(f"{run}.rows_per_cell_scored")
    planted = "tables.p2_selection_by_cell[cell=headline_only].share_lambda_zero"
    if whole.get(planted) != 1.0:
        raise ValueError("the guard admits a weight in the planted cell: the row's wording no longer holds")
    return Table("fmt-control", "rrlrr", [r"tests & rows per cell & guard admits the lift & recovered (90\%) & headline-only recovered"], [
        row(300),
        row(1000),
        [join("{} ({} contrasts)", n(extras, f"{run}.n_tests"), n(whole, "header.admitted_rows")),
         derived("about " + fmt(round(scored, -2), 0, comma=True), extras.ref(f"{run}.rows_per_cell_scored")),
         derived("none in the planted cell", whole.ref(planted)), "", ""],
        row(11100, cell_figure=True),
    ])


def control_rungs(r):
    extras = r(SYNTHETIC_EXTRAS)

    def key(size, cell, rung):
        return f'positive_control_rungs.runs[n_tests={size}].by_cell["{cell}"].rungs[rung={rung}]'

    def diff(size, cell, rung, name, nd):
        return ci(extras, key(size, cell, rung), name, nd)

    return Table("fmt-control-rungs", "lrr", ["rung and measure & 2,000 tests & 11,100 tests"], [
        ["text classifier, Brier skill", ci(extras, key(2000, "ALL", "text_lr"), "brier_skill"), ci(extras, key(11100, "ALL", "text_lr"), "brier_skill")],
        ["boosted model, headline-only, Brier minus P1", diff(2000, "headline_only", "GBM", "diff_brier_vs_p1", 4), ""],
        ["boosted model, headline-only, log score minus P1", v(extras, key(2000, "headline_only", "GBM") + ".diff_logscore_vs_p1"), ""],
        ["P2, log score minus P1 (nats)", diff(2000, "ALL", "P2", "diff_logscore_vs_p1", 4), diff(11100, "ALL", "P2", "diff_logscore_vs_p1", 4)],
        ["P2, share of the oracle's gain", "", v(extras, key(11100, "ALL", "P2") + ".recovered_fraction_logscore", 2)],
    ])


TABLES = [abstention_triggers, abstention_rows, abstention_released, drift_year, asos, control, control_rungs]
