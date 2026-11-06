"""Summary tables, group results_b: abstention, drift, the deployment-shaped archive and the positive control (Sections 6.5 to 6.8)."""
from summary_tables import Raw, Table, ci, derived, fmt, join, lohi, month_year, n, pctw, v

MAIN = "backtest-upworthy-*.json"
EXTRAS = "paper-extras-upworthy-*.json"
ASOS = "backtest-asos-*.json"
ASOS_EXTRAS = "paper-extras-asos-*.json"
SYNTHETIC_EXTRAS = "paper-extras-synthetic-*.json"
CONTROL = "positive-control/backtest-synthetic-*.json"
WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def _all_abstaining(main):
    """The origins on which every card abstains, in words, with their dates; the burn-in origin always among them."""
    origins = [o for o in main.get("tables.origins") if o["abstention_rate"] == 1.0]
    burn = [o for o in origins if o["burn_in"]]
    if len(burn) != 1:
        raise ValueError("the wording names one burn-in origin among the origins that abstain on every row")
    later = [month_year(o["origin"]) for o in origins if not o["burn_in"]]
    words = " and ".join(["the burn-in origin", *later])
    return origins, words


def abstention_triggers(r):
    main, extras = r(MAIN), r(EXTRAS)
    row = "tables.abstention[cell=ALL]"
    full, full_words = _all_abstaining(main)
    full_keys = [main.ref(f"tables.origins[origin={o['origin']}].{f}") for o in full for f in ("n_scored", "abstention_rate")]
    # The wording of the "when it fires" column, each clause checked against the reports, so a run that falsifies one stops the build.
    if main.get(f"{row}.reliability") != sum(o["n_scored"] for o in full):
        raise ValueError("the reliability trigger does not fire on exactly the rows of the origins that abstain on every row")
    without_novelty = r("ablations/backtest-upworthy-*--drop-trigger-novelty.json")
    full_origins = {o["origin"] for o in full}
    if any(o["abstention_rate"] != 0 for o in without_novelty.get("tables.origins") if o["origin"] not in full_origins):
        raise ValueError("a trigger other than novelty fires after the origins that abstain on every row")
    burn_origins = {o["origin"] for o in main.get("tables.origins") if o["burn_in"]}
    thin = [c for c in main.get("tables.p2_selection") if c["n_rows"] < 30]
    if {c["origin"] for c in thin} != burn_origins or {c["cell"] for c in thin} != {c["cell"] for c in main.get("tables.abstention") if c["cell"] != "ALL" and c["support"] > 0}:
        raise ValueError("the support trigger does not fire only at the burn-in origin, in the cells below 30 visible rows")
    if main.get(f"{row}.instability") != 0:
        raise ValueError("the row says the decision instability trigger never fires")
    # The cells where the support trigger fires, and the pairs (cell, origin) where the guard holds the precedent weight at zero.
    abst = [c for c in main.get("tables.abstention") if c["cell"] != "ALL"]
    two = derived(WORDS[sum(c["support"] > 0 for c in abst)], *[main.ref(f"tables.abstention[cell={c['cell']}].support") for c in abst])
    sel = main.get("tables.p2_selection_by_cell")
    zero_keys = [main.ref(f"tables.p2_selection_by_cell[cell={c['cell']}].{f}") for c in sel for f in ("share_lambda_zero", "origins")]
    zero = derived(fmt(sum(c["share_lambda_zero"] * c["origins"] for c in sel), 0), *zero_keys)
    def share(trigger):
        return derived(fmt(main.get(f"{row}.{trigger}") / main.get(f"{row}.n") * 100, 1) + r"\%", main.ref(f"{row}.{trigger}"), main.ref(f"{row}.n"))

    pairs = main.get("tables.p2_selection")
    others = derived(WORDS[len(pairs) - int(round(sum(c["share_lambda_zero"] * c["origins"] for c in sel)))], main.ref("tables.p2_selection"), *zero_keys)
    return Table("fmt-abstention-triggers", r"lrrp{0.5\columnwidth}", ["trigger & rows & share & when it fires"], [
        ["reliability", n(main, f"{row}.reliability"), share("reliability"), derived(f"on every row of {full_words}, and never after", main.ref(f"{row}.reliability"), *full_keys)],
        ["support", n(main, f"{row}.support"), share("support"), join("on rows of the burn-in origin, in the {} cells with fewer than 30 visible rows", two)],
        ["novelty", n(main, f"{row}.novelty"), share("novelty"), derived("the only trigger at the origins after those", without_novelty.ref("tables.origins"))],
        ["decision instability", n(main, f"{row}.instability"), share("instability"),
         join("never: off by construction in the {} pairs where the precedent weight is zero, and it did not fire in the other {}", zero, others)],
        Raw(r"\midrule"),
        ["any trigger", n(extras, "issued_row_brier_skill.rungs.P2.abstained.n"), join(r"{}\%", v(main, f"{row}.rate", 1, scale=100)), "the pooled abstention rate"],
    ])


def abstention_rows(r):
    main, extras = r(MAIN), r(EXTRAS)
    agg = "tables.aggregate[cell=ALL,rung=P2]"

    count, issued = f"{agg}.n", f"{agg}.n_nonabstained"
    total, kept = main.get(f"{agg}.logscore"), main.get(f"{agg}.logscore_nonabstained")
    abstained_log = derived(fmt((total * main.get(count) - kept * main.get(issued)) / (main.get(count) - main.get(issued))), main.ref(f"{agg}.logscore"),
                            main.ref(f"{agg}.logscore_nonabstained"), main.ref(count), main.ref(issued))

    def row(label, side, log):
        key = f"issued_row_brier_skill.rungs.P2.{side}"
        return [label, n(extras, f"{key}.n"), ci(extras, key, "brier_skill", 4), log, v(extras, f"{key}.event_rate", 2)]

    return Table("fmt-abstention-rows", "lrrrr", [r"row set & rows & Brier skill (90\%) & log score & event rate"], [
        row("issued", "issued", v(main, f"{agg}.logscore_nonabstained")),
        row("abstained", "abstained", abstained_log),
        row("all rows", "all", v(main, f"{agg}.logscore")),
    ])


def abstention_released(r):
    main = r(MAIN)
    agg = "tables.aggregate[cell=ALL,rung=P2]"
    full, full_words = _all_abstaining(main)
    # The rows reliability alone withholds sit at the origins that abstain on every row: dropping it changes nothing elsewhere.
    without = {o["origin"]: o["abstention_rate"] for o in r("ablations/backtest-upworthy-*--drop-trigger-reliability.json").get("tables.origins")}
    moved = {o["origin"] for o in main.get("tables.origins") if abs(o["abstention_rate"] - without[o["origin"]]) > 1e-12}
    if moved != {o["origin"] for o in full}:
        raise ValueError("dropping the reliability trigger changes other origins than those the row names")

    def released(label, trigger):
        rep = r(f"ablations/backtest-upworthy-*--drop-trigger-{trigger}.json")
        key = "tables.released_rows[cell=ALL,rung=P2]"
        return [label, n(rep, f"{key}.n"), ci(rep, key, "logscore"), ci(rep, key, "direction_accuracy")]

    return Table("fmt-abstention-released", r"p{0.3\columnwidth}rrr", [r"rows & count & log score (90\%) & direction accuracy (90\%)"], [
        released("released by novelty", "novelty"),
        released(f"released by reliability alone, at {full_words}", "reliability"),
        Raw(r"\midrule"),
        ["issued rows, main run", n(main, f"{agg}.n_nonabstained"), ci(main, agg, "logscore_nonabstained"), ci(main, agg, "direction_accuracy_nonabstained")],
    ])


def drift_year(r):
    main = r(MAIN)

    def row(year):
        key = f"tables.score_by_year[cell=ALL,rung=P1,year={year}]"
        return [v(main, f"{key}.year", 0), n(main, f"{key}.n_tests"), ci(main, key, "brier_skill", 4),
                lohi(main, f"{key}.adjusted_lo", f"{key}.adjusted_hi", 4), v(main, f"{key}.event_rate")]

    return Table("fmt-drift-year", "rrrrr", [r"year & tests & P1 Brier skill (90\%) & adjusted interval & significant-positive rate"], [
        row(2013), row(2014), row(2015),
    ])


def asos(r):
    rep = r(ASOS)
    extras, headline = r(ASOS_EXTRAS), r(EXTRAS)
    agg = "tables.aggregate[cell=ALL,rung=P1]"
    origins = "header.origins_scored"
    own = "gates_by_stratum.strata.ALL"
    corr = "impressions_effect_correlation.corr_log_impressions_abs_z"

    def recalibrated(rung):
        return ci(rep, f"tables.aggregate[cell=ALL,rung={rung}+cal]", "brier_skill", 4)

    def over_random(rung):
        return ci(rep, f"tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung={rung}]", "diff_random", 4)

    def over_matched(rung):
        key = f"tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung={rung}]"
        if abs(rep.get(f"{key}.diff_matched")) > 1e-9:
            raise ValueError("the row says zero by construction")
        return v(rep, f"{key}.diff_matched")

    return Table("fmt-asos", "lr", ["figure & value"], [
        ["scored contrasts", n(rep, "header.scored_rows")],
        ["experiments scored", n(rep, "header.tests_scored")],
        ["nominal quarterly origins", derived(WORDS[rep.get(origins)], rep.ref(origins))],
        [join("own gate at skill 0.20 and 0.10, tests (base rate {})", v(extras, f"{own}.dependence.base_rate", 2)),
         join("{} and {}", n(extras, f"{own}.own_gate.n_200"), n(extras, f"{own}.own_gate.n_400"))],
        ["abstention rate", v(rep, f"{agg}.abstention_rate")],
        ["support trigger, rows at the early origins", n(rep, "tables.abstention[cell=ALL].support")],
        [r"P1 Brier skill (90\%)", ci(rep, agg, "brier_skill", 4)],
        ["P1 Brier skill, adjusted interval", lohi(rep, f"{agg}.adjusted_lo", f"{agg}.adjusted_hi", 4)],
        ["expected calibration error", v(rep, f"{agg}.ece")],
        ["calibration percentile", v(rep, f"{agg}.ece_percentile", 1)],
        ["design effect", v(rep, f"{agg}.design_effect", 1)],
        ["coverage of the 80 and 90 percent intervals", join("{} and {}", v(rep, f"{agg}.coverage_80", 2), v(rep, f"{agg}.coverage_90", 2))],
        [r"boosted model, recalibrated Brier skill (90\%)", recalibrated("GBM")],
        [r"local comparison set, recalibrated Brier skill (90\%)", recalibrated("local_eb")],
        [r"boosted model, lift minus random order, quarter of tests (90\%)", over_random("GBM")],
        [r"local comparison set, the same (90\%)", over_random("local_eb")],
        ["both, lift minus the matched order, quarter of tests", join("{} and {}", over_matched("GBM"), over_matched("local_eb"))],
        [r"exposure stand-in, correlation with $|$standardized effect$|$", v(extras, corr)],
        ["the same correlation on the headline archive", v(headline, corr)],
    ])


def control(r):
    extras, whole = r(SYNTHETIC_EXTRAS), r(CONTROL)

    def split_row(size):
        key = f"positive_control_sensitivity.rows[n_tests={size},text_effect_strength=1.0]"
        cell = f"{key}.by_cell[cell=headline_only]"
        return [n(extras, f"{key}.n_tests"), n(extras, f"{key}.rows_per_cell"), pctw(extras, f"{key}.share_admitted"), ci(extras, key, "recovered_fraction", 4),
                ci(extras, cell, "recovered_fraction", 4) if extras.get(f"{cell}.recovered_fraction") is not None else ""]

    def rolling_row(size):
        run = f"positive_control_rungs.runs[n_tests={size}]"

        def rung(cell):
            return f'{run}.by_cell["{cell}"].rungs[rung=P2]'

        return [n(extras, f"{run}.n_tests"), n(extras, f"{run}.rows_per_cell_scored"), pctw(extras, f"{run}.share_pairs_admitted"),
                v(extras, f"{rung('ALL')}.recovered_fraction_logscore", 4), v(extras, f"{rung('headline_only')}.recovered_fraction_logscore", 4)]

    planted = "tables.p2_selection_by_cell[cell=headline_only].share_lambda_zero"
    if whole.get(planted) != 1.0:
        raise ValueError("the guard admits a weight in the planted cell at 2,000 tests: the sentence reading the table no longer holds")
    return Table("fmt-control", "rrrrr", [r"tests & rows per cell & guard admits & P2's share of the oracle's gain & headline-only cell"], [
        Raw(r"\multicolumn{5}{@{}l}{\emph{End-of-ledger split: 15 percent of tests held out, 12 seeds; ledger rows per cell; share of cells admitted; 90\% intervals}} \\"),
        split_row(300),
        split_row(1000),
        split_row(11100),
        Raw(r"\midrule"),
        Raw(r"\multicolumn{5}{@{}l}{\emph{Rolling backtest, the design the real archive gets: scored rows per cell; share of cell-origin pairs admitted}} \\"),
        rolling_row(2000),
        rolling_row(11100),
    ])


def control_rungs(r):
    extras = r(SYNTHETIC_EXTRAS)

    def key(size, cell, rung):
        return f'positive_control_rungs.runs[n_tests={size}].by_cell["{cell}"].rungs[rung={rung}]'

    def both(fn):
        return [fn(2000), fn(11100)]

    return Table("fmt-control-rungs", "lrr", [r"rung and measure (90\%) & 2,000 tests & 11,100 tests"], [
        ["P1, Brier skill", *both(lambda s: ci(extras, key(s, "ALL", "P1"), "brier_skill", 4))],
        ["text classifier, Brier skill", *both(lambda s: ci(extras, key(s, "ALL", "text_lr"), "brier_skill", 4))],
        ["boosted model, headline-only, Brier minus P1", *both(lambda s: ci(extras, key(s, "headline_only", "GBM"), "diff_brier_vs_p1", 4))],
        ["boosted model, headline-only, log score minus P1", *both(lambda s: ci(extras, key(s, "headline_only", "GBM"), "diff_logscore_vs_p1", 4))],
        ["P2, log score minus P1, all cells", *both(lambda s: ci(extras, key(s, "ALL", "P2"), "diff_logscore_vs_p1", 4))],
        ["P2, log score minus P1, headline-only", *both(lambda s: ci(extras, key(s, "headline_only", "P2"), "diff_logscore_vs_p1", 4))],
        ["P2, Brier minus P1, all cells", *both(lambda s: ci(extras, key(s, "ALL", "P2"), "diff_brier_vs_p1", 5))],
    ])


TABLES = [abstention_triggers, abstention_rows, abstention_released, drift_year, asos, control, control_rungs]
