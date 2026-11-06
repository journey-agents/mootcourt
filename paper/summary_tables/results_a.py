"""Summary tables, group results_a: the cautionary run, the ladder, the challengers, the guard, the gates, calibration and decisions (Sections 6.1 to 6.4)."""
from summary_tables import Raw, Table, ci, derived, fmt, join, lohi, month_year, n, narrowest_origin, pct, pctw, v

MAIN = "backtest-upworthy-*.json"
EXTRAS = "paper-extras-upworthy-*.json"
CAUTIONARY = "ablations/backtest-upworthy-*--effect-scale-relative+s-star-realized.json"
GUARD = "ablations/p2-guard-upworthy.json"
GATES = "gates.json"
GATE = 'by_base_rate["0.09"].by_target["0.90"]'
SIM = 'by_base_rate["0.09"]'
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
DECIDABLE = {"decidable at skill 0.20 and 0.10": "both skills", "decidable at skill 0.20 only": "skill 0.20 only", "undecidable at this n": "neither"}


def agg(rung, cell="ALL"):
    return f"tables.aggregate[cell={cell},rung={rung}]"


def origin_score(origin, rung):
    return f"tables.score_by_origin[origin={origin}T00:00:00+00:00,rung={rung}].logscore"


def signed_ci(rep, row, field_name, nd=3):
    """As ``ci``, but a bound that rounds to zero keeps its sign, so a negative bound reads as negative."""
    a = v(rep, f"{row}.{field_name}", nd)
    lo_key, hi_key = f"{row}.{field_name}_lo", f"{row}.{field_name}_hi"
    return derived(f"{a} ({rep.get(lo_key):.{nd}f}, {rep.get(hi_key):.{nd}f})", *a.keys, rep.ref(lo_key), rep.ref(hi_key))


def decidable(rep, key):
    return derived(DECIDABLE[rep.get(key)], rep.ref(key))


def admitted(rep, share_key, count_key):
    """The pairs a share of held-at-zero pairs leaves admitted."""
    return (1 - rep.get(share_key)) * rep.get(count_key)


def cautionary(r):
    extras, run = r(EXTRAS), r(CAUTIONARY)

    def row(label, decile, event_nd):
        key = f"cautionary_deciles.rows[rung=P1,decile={decile}]"
        return [label, v(extras, f"{key}.y_mean", 0), pct(extras, f"{key}.event", event_nd), pct(extras, f"{key}.p_sig"), v(extras, f"{key}.cov90", 2)]

    return Table("fmt-cautionary", "lrrrr", [r"decile of $s$ & mean effect (\%) & event rate (\%) & P1 mean $\psig$ (\%) & cov.\ 90"], [
        row("1 (most precise)", 1, 1),
        row("10 (least precise)", 10, 0),
        Raw(r"\midrule"),
        [r"Brier skill (90\%)", join(r"\multicolumn{{4}}{{r}}{{{}}}", ci(run, agg("P1"), "brier_skill"))],
    ])


def p1_cells(r):
    main = r(MAIN)

    def cell(label, name, skill=ci):
        row = agg("P1", name)
        return [label, n(main, f"{row}.n_tests"), "", "", skill(main, row, "brier_skill"), ""]

    p1 = agg("P1")
    narrowest = narrowest_origin(main)[:10]
    return Table("fmt-p1-cells", "lrrrrr", [r"row & tests & P1 log score & P0 log score & Brier skill (90\%) & adjusted"], [
        ["pooled", n(main, "header.tests_scored"), v(main, f"{p1}.logscore"), v(main, f"{agg('P0')}.logscore"), ci(main, p1, "brier_skill"),
         lohi(main, f"{p1}.adjusted_lo", f"{p1}.adjusted_hi")],
        [f"{month_year(narrowest)} (narrowest)", "", v(main, origin_score(narrowest, "P1")), v(main, origin_score(narrowest, "P0")), "", ""],
        cell("image-only", "image_only"),
        cell("headline-only", "headline_only"),
        cell("both changed", "both", signed_ci),
    ])


def direction(r):
    main = r(MAIN)

    def row(label, rung, auc=True, accuracy=True):
        a = agg(rung)
        return [label, v(main, f"{a}.direction_accuracy") if accuracy else "", v(main, f"{a}.direction_accuracy_decisive") if accuracy else "",
                v(main, f"{a}.auc_direction") if auc else ""]

    return Table("fmt-direction", "lrrr", ["rung & accuracy & accuracy, decisive & direction AUC"], [
        row("P1 (the ladder)", "P1"),
        row(r"\emph{always\_reference}", "always_reference", auc=False),
        row("text classifier", "text_lr"),
        row("P2", "P2", accuracy=False),
    ])


def challengers(r):
    main = r(MAIN)
    cal = agg("text_lr+cal")
    # The recalibrated text classifier's bound near zero is read at four places, so its lower bound stays visible.
    text_cal = join("{} {}", v(main, f"{cal}.brier_skill"), lohi(main, f"{cal}.brier_skill_lo", f"{cal}.brier_skill_hi", 4))

    def row(label, rung):
        return [label, ci(main, agg(rung), "brier_skill"), ci(main, agg(f"{rung}+cal"), "brier_skill"), ""]

    return Table("fmt-challengers", "lrrr", [r"challenger & raw (90\%) & recalibrated (90\%) & adjusted"], [
        row("boosted model", "GBM"),
        row("local comparison set", "local_eb"),
        ["text classifier", ci(main, agg("text_lr"), "brier_skill"), text_cal, lohi(main, f"{cal}.adjusted_lo", f"{cal}.adjusted_hi")],
        ["precedent rung (P2)", ci(main, agg("P2"), "brier_skill", 4), "", lohi(main, f"{agg('P2')}.adjusted_lo", f"{agg('P2')}.adjusted_hi", 4)],
    ])


def auc_within(r):
    main = r(MAIN)
    field = "auc_event_within"
    return Table("fmt-auc-within", "lrr", ["rung & all cells & headline-only cell"], [
        ["P0", v(main, f"{agg('P0')}.{field}"), ""],
        ["P1", ci(main, agg("P1"), field), ci(main, agg("P1", "headline_only"), field)],
        ["P2", ci(main, agg("P2"), field), ci(main, agg("P2", "headline_only"), field)],
        ["text classifier, raw", ci(main, agg("text_lr"), field), ""],
        ["text classifier, recalibrated", "", ci(main, agg("text_lr+cal", "headline_only"), field)],
    ])


def guard(r):
    main, extras, abl = r(MAIN), r(EXTRAS), r(GUARD)
    summary = "guard_pairs.summary"
    p1, p2 = agg("P1"), agg("P2")
    unguarded = derived(fmt(admitted(abl, "unguarded.share_lambda_zero", "unguarded.cells_origins"), 0),
                        abl.ref("unguarded.share_lambda_zero"), abl.ref("unguarded.cells_origins"))

    def by_cell(cell):
        key = f"tables.p2_selection_by_cell[cell={cell}]"
        count = fmt(admitted(main, f"{key}.share_lambda_zero", f"{key}.origins"), 0)
        return derived("none" if float(count) == 0 else count, main.ref(f"{key}.share_lambda_zero"), main.ref(f"{key}.origins"))

    return Table("fmt-guard", "lrrr", [r" & P1 & P2, guarded & P2, unguarded"], [
        [join("pairs admitted, of {}", n(extras, f"{summary}.pairs_in_selection")), "", n(extras, f"{summary}.pairs_admitted"), unguarded],
        ["headline-only, image-only, smallest", "", join("{}, {}, {}", by_cell("headline_only"), by_cell("image_only"), by_cell("both")), ""],
        ["log score", v(main, f"{p1}.logscore"), v(main, f"{p2}.logscore"), v(abl, "unguarded.logscore")],
        [r"Brier skill (90\%)", ci(main, p1, "brier_skill", 4), ci(main, p2, "brier_skill", 4), ci(abl, "unguarded", "brier_skill", 4)],
    ])


def p2_vs_p1(r):
    main, extras, abl = r(MAIN), r(EXTRAS), r(GUARD)
    # The two origins where the guard's choice moves the log score most, chosen here by the size of the difference, so they follow the run.
    origins = sorted({row["origin"][:10] for row in main.get("tables.score_by_origin")})

    def move(origin):
        return abs(main.get(origin_score(origin, "P2")) - main.get(origin_score(origin, "P1")))

    ranked = sorted(origins, key=lambda o: (-move(o), o))
    named, others = sorted(ranked[:2]), ranked[2:]

    def diff(origin, nd=3):
        p1_key, p2_key = origin_score(origin, "P1"), origin_score(origin, "P2")
        return derived(fmt(main.get(p2_key) - main.get(p1_key), nd), main.ref(p2_key), main.ref(p1_key))

    def origin_row(label, origin):
        return [label, diff(origin), ci(extras, f"guard_pairs_rows.rows[origin={origin}T00:00:00+00:00]", "mean_diff")]

    within = derived(f"within {fmt(max(move(o) for o in others), 3)} of zero", *[main.ref(origin_score(o, rung)) for o in others for rung in ("P1", "P2")])
    pooled = "guard_pairs_rows.pooled"
    return Table("fmt-p2-vs-p1", "lrr", ["difference & all rows & admitted pairs' rows"], [
        ["P2 minus P1, pooled", ci(main, agg("P2"), "logscore_vs_p1", 4),
         ci(extras, "guard_pairs.summary", "pooled_realized_p2_minus_p1", 4, lo="pooled_lo", hi="pooled_hi")],
        origin_row(f"{month_year(named[0])} origin", named[0]),
        origin_row(f"{month_year(named[1])} origin", named[1]),
        [f"the other {WORDS[len(others)]} origins", within, ""],
        ["location part", "", ci(extras, pooled, "location_part", 4)],
        ["scale part", "", ci(extras, pooled, "scale_part", 4)],
        ["guarded minus unguarded", ci(abl, "difference.logscore", "estimate", 4, lo="lo", hi="hi"), ""],
    ])


def gates(r):
    main, sim = r(MAIN), r(GATES)
    gate = [n(sim, f"{GATE}.n_200"), n(sim, f"{GATE}.n_400")]

    def own(label, tests, cell, verdict):
        a = agg("P1", cell)
        return [label, tests, v(main, f"{a}.gate_cell_rows_per_test", 1), v(main, f"{a}.gate_cell_icc", 2), n(main, f"{a}.gate_cell_n_200"),
                n(main, f"{a}.gate_cell_n_400"), decidable(main, f"{a}.{verdict}")]

    def simulated(label, cell):
        a = agg("P1", cell)
        return [label, n(main, f"{a}.n_tests"), "", "", *gate, decidable(main, f"{a}.decidable_by_tests")]

    both = agg("P1", "both")
    if fmt(main.get(f"{agg('P1')}.gate_base_rate"), 2) != "0.09":
        raise ValueError("the simulation row reads the base rate 0.09 and the archive's rate rounds to another")
    return Table("fmt-gates", "lrrrrrl", ["stratum & tests & rows per test & within-test corr. & gate, skill 0.20 & gate, skill 0.10 & decidable"], [
        ["simulation", "", v(sim, f"{SIM}.rows_per_test", 1), v(sim, f"{SIM}.icc", 2), *gate, ""],
        own("pooled, at its own dependence", n(main, "header.tests_scored"), "ALL", "decidable_by_tests"),
        simulated("headline-only", "headline_only"),
        simulated("image-only", "image_only"),
        simulated("smallest, at the simulated dependence", "both"),
        own("smallest, at its own dependence", n(main, f"{both}.n_tests"), "both", "decidable_by_tests_cell"),
    ])


def calibration(r):
    main = r(MAIN)

    def row(rung, equal_mass=False):
        a = agg(rung)
        mass = join("{} ({})", v(main, f"{a}.ece_equal_mass"), v(main, f"{a}.ece_equal_mass_percentile", 0)) if equal_mass else ""
        return [rung, v(main, f"{a}.ece"), v(main, f"{a}.ece_percentile", 0), mass, v(main, f"{a}.coverage_80", 2), v(main, f"{a}.coverage_90", 2)]

    return Table("fmt-calibration", "lrrrrr", [r"rung & ECE & percentile & equal-mass ECE & cov.\ 80 & cov.\ 90"],
                 [row("P0"), row("P1", equal_mass=True), row("P2")])


def upper_bins(r):
    main, extras = r(MAIN), r(EXTRAS)
    lowest = "lowest_reliability_bin.rungs.P1"
    if extras.get(f"{lowest}.rows") != main.get("tables.reliability_bins[rung=P1,bin=0].n"):
        raise ValueError("the lowest bin of the extras is not the report's")
    if any(row["n"] for row in main.get("tables.reliability_bins") if row["rung"] == "P1" and row["bin"] > 2):
        raise ValueError("a bin above the third holds rows, so 'above 0.2' no longer names one bin")

    def row(label, b, gap=""):
        key = f"tables.reliability_bins[rung=P1,bin={b}]"
        return [label, n(main, f"{key}.n"), v(main, f"{key}.mean_p"), pctw(main, f"{key}.freq", 1), gap]

    gap = ci(extras, lowest, "gap_observed_minus_forecast", 4, lo="gap_lo", hi="gap_hi")
    return Table("fmt-upper-bins", "lrrrr", [r"bin of $\psig$ & rows & mean & significant & observed minus", r" & & forecast & positive & forecast (90\%)"],
                 [row("0 to 0.1", 0, gap), row("0.1 to 0.2", 1), row("above 0.2", 2)])


def deciles(r):
    main = r(MAIN)

    def span(table, nd, field, high_field=None):
        """The lowest to the highest value of P1 over the ten deciles, with each end's report key."""
        rows = [row for row in main.get(f"tables.{table}") if row["rung"] == "P1"]
        high_field = high_field or field
        low, high = min(rows, key=lambda x: x[field]), max(rows, key=lambda x: x[high_field])
        return derived(f"{fmt(low[field], nd)} to {fmt(high[high_field], nd)}", main.ref(f"tables.{table}[rung=P1,decile={low['decile']}].{field}"),
                       main.ref(f"tables.{table}[rung=P1,decile={high['decile']}].{high_field}"))

    ratio = "tables.coverage_by_se_ratio[rung=P1,decile={}].coverage_90"
    falling = join("{} to {}", v(main, ratio.format(1), 2), v(main, ratio.format(10), 2))
    return Table("fmt-deciles", "lrrrr", [r"deciles of & ratio span & mean $\psig$ & event rate & cov.\ 90"], [
        ["planned exposure", "", span("calibration_by_precision", 3, "mean_p_sig"), span("calibration_by_precision", 3, "event_rate"),
         span("calibration_by_precision", 2, "coverage_90")],
        [r"realized over planned $s$", span("coverage_by_se_ratio", 2, "ratio_lo", "ratio_hi"), span("coverage_by_se_ratio", 3, "mean_p_sig"),
         span("coverage_by_se_ratio", 3, "event_rate"), falling],
    ])


def decision(r):
    main, extras = r(MAIN), r(EXTRAS)
    paired = 'ranking_paired.budgets["0.25"].differences.P2_minus_P1'

    def key(policy, rung=None):
        at_rung = f",rung={rung}" if rung else ""
        return f"tables.decision_value[origin=ALL,budget=0.25,policy={policy}{at_rung}]"

    def captured(policy, rung=None):
        return v(main, f"{key(policy, rung)}.captured_fraction")

    def rung_row(label, rung):
        row = key("p_win", rung)
        return [label, captured("p_win", rung), "", ci(main, row, "diff_matched"),
                lohi(main, f"{row}.diff_matched_adjusted_lo", f"{row}.diff_matched_adjusted_hi")]

    matched = [row for row in main.get("tables.decision_value") if row["origin"] == "ALL" and row["budget"] == 0.25 and row["policy"] == "random_matched"]
    low = min(matched, key=lambda x: x["captured_fraction"])
    high = max(matched, key=lambda x: x["captured_fraction"])
    baseline = join("{} to {}", captured("random_matched", low["rung"]), captured("random_matched", high["rung"]))
    return Table("fmt-decision", "lrrrr", [r"policy & captured & minus random (90\%) & minus matched (90\%) & adjusted"], [
        ["random order (exact)", captured("random"), "", "", ""],
        ["arm-count order", captured("arm_count"), ci(main, key("arm_count"), "diff_random"), "", ""],
        ["matched random (the baseline)", baseline, "", "", ""],
        rung_row("text classifier", "text_lr"),
        rung_row("boosted model", "GBM"),
        rung_row("local comparison set", "local_eb"),
        rung_row("precedent rung (P2)", "P2"),
        rung_row("P1", "P1"),
        rung_row("P0", "P0"),
        ["oracle", captured("oracle"), "", "", ""],
        Raw(r"\midrule"),
        ["P2 minus P1, paired by test", ci(extras, paired, "estimate", lo="lo", hi="hi"), "", "", lohi(extras, f"{paired}.adjusted_lo", f"{paired}.adjusted_hi")],
    ])


TABLES = [cautionary, p1_cells, direction, challengers, auc_within, guard, p2_vs_p1, gates, calibration, upper_bins, deciles, decision]
