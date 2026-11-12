"""Summary tables, group results_a: the cautionary run, the ladder, the challengers, the guard, calibration and decisions (the gates of each stratum are in experiments)."""
from summary_tables import Raw, Table, ci, derived, fmt, join, lohi, month_year, n, narrowest_origin, pct, pctw, v

MAIN = "backtest-upworthy-*.json"
EXTRAS = "paper-extras-upworthy-*.json"
CAUTIONARY = "ablations/backtest-upworthy-*--effect-scale-relative+s-star-realized.json"
GUARD = "ablations/p2-guard-upworthy.json"
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


def ci_neg(rep, row, field_name, nd=4):
    """``ci`` of a difference read the other way round: the value negated and the bounds swapped."""
    keys = [f"{row}.{field_name}", f"{row}.{field_name}_lo", f"{row}.{field_name}_hi"]
    x, lo, hi = (-rep.get(k) for k in keys)
    return derived(f"{fmt(x, nd)} ({fmt(hi, nd)}, {fmt(lo, nd)})", *[rep.ref(k) for k in keys])


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
        [r"Brier skill (90\%)", join(r"\multicolumn{{4}}{{r}}{{{}}}", ci(run, agg("P1"), "brier_skill", 4))],
    ])


def p1_cells(r):
    main, extras = r(MAIN), r(EXTRAS)

    def gain(cell):
        return ci_neg(main, agg("P0", cell), "logscore_vs_p1")

    def cell(label, name):
        row = agg("P1", name)
        return [label, n(main, f"{row}.n_tests"), v(main, f"{row}.logscore"), v(main, f"{agg('P0', name)}.logscore"), gain(name), ci(main, row, "brier_skill", 4),
                lohi(main, f"{row}.adjusted_lo", f"{row}.adjusted_hi", 4)]

    narrowest = narrowest_origin(main)
    day = narrowest[:10]
    by_origin = f"p1_minus_p0_by_origin.by_origin[origin={narrowest}]"
    return Table("fmt-p1-cells", "lrrrrrr", [r"row & tests & P1 log score & P0 log score & P1 minus P0 (90\%) & P1 Brier skill (90\%) & adjusted"], [
        cell("pooled", "ALL"),
        cell("headline-only", "headline_only"),
        cell("image-only", "image_only"),
        cell("smallest", "both"),
        [f"{month_year(day)} (narrowest)", n(main, f"tables.origins[origin={narrowest}].n_tests"), v(main, origin_score(day, "P1")), v(main, origin_score(day, "P0")),
         ci(extras, by_origin, "difference", 4, lo="lo", hi="hi"), "", ""],
    ])


def direction(r):
    main = r(MAIN)

    def row(label, rung, auc=True):
        a = agg(rung)
        return [label, v(main, f"{a}.direction_accuracy"), v(main, f"{a}.direction_accuracy_decisive"), ci(main, a, "auc_direction_within") if auc else "none, one forecast"]

    return Table("fmt-direction", "lrrr", [r"rung & accuracy & accuracy, decisive & direction AUC within strata (90\%)"], [
        row("P1", "P1"),
        row("precedent rung (P2)", "P2"),
        row("text classifier", "text_lr"),
        row(r"\emph{always\_reference}", "always_reference", auc=False),
    ])


def challengers(r):
    main = r(MAIN)

    def interval(rung):
        return [ci(main, agg(rung), "brier_skill", 4), lohi(main, f"{agg(rung)}.adjusted_lo", f"{agg(rung)}.adjusted_hi", 4)]

    def row(label, rung):
        return [label, *interval(rung), *interval(f"{rung}+cal")]

    return Table("fmt-challengers", "lrrrr", [r"rung & raw (90\%) & raw, adjusted & recalibrated (90\%) & recalibrated, adjusted"], [
        [r"P1", *interval("P1"), "", ""],
        ["precedent rung (P2)", *interval("P2"), "", ""],
        row("boosted model", "GBM"),
        row("local comparison set", "local_eb"),
        row("text classifier", "text_lr"),
    ])


def auc_within(r):
    main = r(MAIN)
    field = "auc_event_within"

    def row(label, rung):
        return [label, ci(main, agg(rung), field), ci(main, agg(rung, "headline_only"), field)]

    return Table("fmt-auc-within", "lrr", [r"rung & all cells (90\%) & headline-only cell (90\%)"], [
        ["P0 (one forecast per stratum)", v(main, f"{agg('P0')}.{field}"), v(main, f"{agg('P0', 'headline_only')}.{field}")],
        row("P1", "P1"),
        row("precedent rung (P2)", "P2"),
        row("boosted model", "GBM"),
        row("local comparison set", "local_eb"),
        row("text classifier, raw", "text_lr"),
        row("text classifier, recalibrated", "text_lr+cal"),
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

    def diff(origin, nd=4):
        p1_key, p2_key = origin_score(origin, "P1"), origin_score(origin, "P2")
        return derived(fmt(main.get(p2_key) - main.get(p1_key), nd), main.ref(p2_key), main.ref(p1_key))

    def origin_row(label, origin):
        return [label, diff(origin), ci(extras, f"guard_pairs_rows.rows[origin={origin}T00:00:00+00:00]", "mean_diff", 4)]

    within = derived(f"within {fmt(max(move(o) for o in others), 3)} of zero", *[main.ref(origin_score(o, rung)) for o in others for rung in ("P1", "P2")])
    pooled = "guard_pairs_rows.pooled"
    return Table("fmt-p2-vs-p1", "lrr", ["difference & all rows & admitted pairs' rows"], [
        ["P2 minus P1, pooled", ci(main, agg("P2"), "logscore_vs_p1", 4),
         ci(extras, "guard_pairs.summary", "pooled_realized_p2_minus_p1", 4, lo="pooled_lo", hi="pooled_hi")],
        ["P2 minus P1, headline-only", ci(main, agg("P2", "headline_only"), "logscore_vs_p1", 4), ""],
        ["P2 minus P1, image-only", ci(main, agg("P2", "image_only"), "logscore_vs_p1", 4), ""],
        origin_row(f"{month_year(named[0])} origin", named[0]),
        origin_row(f"{month_year(named[1])} origin", named[1]),
        [f"the other {WORDS[len(others)]} origins", within, ""],
        ["location part", "", ci(extras, pooled, "location_part", 4)],
        ["scale part", "", ci(extras, pooled, "scale_part", 4)],
        ["guarded minus unguarded", ci(abl, "difference.logscore", "estimate", 4, lo="lo", hi="hi"), ""],
    ])


def calibration(r):
    main = r(MAIN)

    def row(rung):
        a = agg(rung)
        mass = join("{} ({})", v(main, f"{a}.ece_equal_mass"), v(main, f"{a}.ece_equal_mass_percentile", 0))
        return [rung, v(main, f"{a}.ece"), v(main, f"{a}.ece_percentile", 0), mass, v(main, f"{a}.coverage_80", 2), v(main, f"{a}.coverage_90", 2)]

    return Table("fmt-calibration", "lrrrrr", [r"rung & ECE & percentile & equal-mass ECE (percentile) & cov.\ 80 & cov.\ 90"],
                 [row("P0"), row("P1"), row("P2")])


def upper_bins(r):
    main, extras = r(MAIN), r(EXTRAS)
    lowest = "lowest_reliability_bin.rungs.P1"
    if extras.get(f"{lowest}.rows") != main.get("tables.reliability_bins[rung=P1,bin=0].n"):
        raise ValueError("the lowest bin of the extras is not the report's")
    if any(row["n"] for row in main.get("tables.reliability_bins") if row["rung"] == "P1" and row["bin"] > 2):
        raise ValueError("a bin above the third holds rows, so 'above 0.2' no longer names one bin")

    def row(label, b, gap=None):
        key = f"tables.reliability_bins[rung=P1,bin={b}]"
        if gap is None:
            gap = derived(fmt(main.get(f"{key}.freq") - main.get(f"{key}.mean_p"), 4), main.ref(f"{key}.freq"), main.ref(f"{key}.mean_p"))
        return [label, n(main, f"{key}.n"), v(main, f"{key}.mean_p"), pctw(main, f"{key}.freq", 1), gap]

    gap = ci(extras, lowest, "gap_observed_minus_forecast", 4, lo="gap_lo", hi="gap_hi")
    return Table("fmt-upper-bins", "lrrrr", [r"bin of $\psig$ & rows & mean & significant & observed minus", r" & & forecast & positive & forecast"],
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
    main = r(MAIN)

    def key(policy, rung=None):
        at_rung = f",rung={rung}" if rung else ""
        return f"tables.decision_value[origin=ALL,budget=0.25,policy={policy}{at_rung}]"

    def captured(policy, rung=None):
        return v(main, f"{key(policy, rung)}.captured_fraction")

    def rung_row(label, rung):
        row = key("p_win", rung)
        return [label, captured("p_win", rung), ci(main, row, "diff_random", 4), lohi(main, f"{row}.diff_random_adjusted_lo", f"{row}.diff_random_adjusted_hi", 4),
                ci(main, row, "diff_matched", 4), lohi(main, f"{row}.diff_matched_adjusted_lo", f"{row}.diff_matched_adjusted_hi", 4)]

    matched = [row for row in main.get("tables.decision_value") if row["origin"] == "ALL" and row["budget"] == 0.25 and row["policy"] == "random_matched"]
    low = min(matched, key=lambda x: x["captured_fraction"])
    high = max(matched, key=lambda x: x["captured_fraction"])
    baseline = join("{} to {}", captured("random_matched", low["rung"]), captured("random_matched", high["rung"]))
    return Table("fmt-decision", "lrrrrr", [r"policy & captured & minus random (90\%) & adjusted & minus matched (90\%) & adjusted"], [
        ["random order (exact)", captured("random"), "", "", "", ""],
        ["arm-count order", captured("arm_count"), ci(main, key("arm_count"), "diff_random", 4), "", "", ""],
        ["matched random (the baseline)", baseline, "", "", "", ""],
        rung_row("text classifier", "text_lr"),
        rung_row("boosted model", "GBM"),
        rung_row("local comparison set", "local_eb"),
        rung_row("precedent rung (P2)", "P2"),
        rung_row("P1", "P1"),
        rung_row("P0", "P0"),
        ["oracle", captured("oracle"), "", "", "", ""],
    ])


TABLES = [cautionary, p1_cells, direction, challengers, auc_within, guard, p2_vs_p1, calibration, upper_bins, deciles, decision]
