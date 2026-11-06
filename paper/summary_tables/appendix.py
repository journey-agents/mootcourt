"""Summary tables of the appendix: the deployment-shaped archive, the synthetic truth, the planted ledger and the snapshots."""
import glob
import os

from mootcourt.sources.synthetic import _DEFAULT_CELLS
from summary_tables import Raw, Table, ci, derived, fmt, join, n, v

UPWORTHY, ASOS = "upworthy", "asos"
LOGSCORE_P1 = "tables.aggregate[cell=ALL,rung=P1].logscore"
BRIER_P1 = "tables.aggregate[cell=ALL,rung=P1].brier_skill"
SENSITIVITY = "positive_control_sensitivity.rows[n_tests=11100,text_effect_strength=1.0]"
NOT_APPLICABLE = "n/a"


def _rung(name):
    return f"tables.aggregate[cell=ALL,rung={name}]"


def _decision(rung):
    return f"tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung={rung}]"


def _released(r, source):
    return r(f"ablations/backtest-{source}-*--drop-trigger-support.json")


def _main(r, source):
    return r(f"backtest-{source}-*.json")


def _ablation(r, source, setting):
    return r(f"ablations/backtest-{source}-*--{setting}.json")


def _of(numerator, denominator, numerator_keys):
    """``a of b``, with ``a`` a count computed from the leaves named and ``b`` a count."""
    return derived(f"{fmt(numerator, 0)} of {fmt(denominator, 0)}", *numerator_keys)


def _pairs(rep, block, admitted):
    share, cells = rep.get(f"{block}.share_lambda_zero"), rep.get(f"{block}.cells_origins")
    count = cells * (1 - share) if admitted else cells * share
    return _of(round(count), cells, [rep.ref(f"{block}.share_lambda_zero"), rep.ref(f"{block}.cells_origins")])


def _skipped(rep):
    return derived(f"{fmt(rep.get('skipped_runs').get('0.05', 0), 0)} of {fmt(rep.get('seeds'), 0)}", rep.ref("skipped_runs"), rep.ref("seeds"))


def _nats_lost(main, normal):
    a, b = main.get(LOGSCORE_P1), normal.get(LOGSCORE_P1)
    return derived(fmt(a - b), main.ref(LOGSCORE_P1), normal.ref(LOGSCORE_P1))


def app_asos(r):
    a, u = _main(r, ASOS), _main(r, UPWORTHY)
    guard_a, guard_u = r("ablations/p2-guard-asos.json"), r("ablations/p2-guard-upworthy.json")
    off_a, off_u = _ablation(r, ASOS, "p2-guard-off"), _ablation(r, UPWORTHY, "p2-guard-off")
    extras_a, extras_u = r("paper-extras-asos-*.json"), r("paper-extras-upworthy-*.json")
    support_a, support_u = _released(r, ASOS), _released(r, UPWORTHY)
    replay_a, replay_u = r("replay-asos-*.json"), r("replay-upworthy-*.json")
    normal_a, normal_u = _ablation(r, ASOS, "prior-normal"), _ablation(r, UPWORTHY, "prior-normal")
    k0_a, k80_a = _ablation(r, ASOS, "kappa-0.0"), _ablation(r, ASOS, "kappa-80.0")
    k0_u, k80_u = _ablation(r, UPWORTHY, "kappa-0.0"), _ablation(r, UPWORTHY, "kappa-80.0")
    curve_a, curve_u = r("learning-curve-asos-*.json"), r("learning-curve-upworthy-*.json")
    support_run = "trigger_ablation_released_rows.runs[dropped_trigger=support]"
    released = "tables.released_rows[cell=ALL]"
    year = "tables.score_by_year[year={},cell=ALL,rung=P1]"
    first, second = year.format(2019), year.format(2020)
    curve = "rows[rung=P1,fraction={}]"

    def both(fn, *args, **kw):
        return [fn(a, *args, **kw), fn(u, *args, **kw)]

    def replays(fn, key):
        return [fn(replay_a, key), fn(replay_u, key)]

    def heading(text):
        return Raw(rf"\multicolumn{{3}}{{l}}{{\emph{{{text}}}}} \\")

    rule = Raw(r"\midrule")
    rows = [
        ["tests scored", *both(n, "header.tests_scored")],
        rule,
        heading("The guard on P2"),
        ["pairs at $\\lambda = 0$, guard on", _pairs(guard_a, "guarded", False), _pairs(guard_u, "guarded", False)],
        ["pairs admitted, guard off", _pairs(guard_a, "unguarded", True), _pairs(guard_u, "unguarded", True)],
        ["P2 minus P1 log score, guard off", ci(off_a, _rung("P2"), "logscore_vs_p1", 5), ci(off_u, _rung("P2"), "logscore_vs_p1", 5)],
        rule,
        heading("The boosted model and the local comparison set"),
        ["boosted model, Brier skill, raw", *both(v, f"{_rung('GBM')}.brier_skill")],
        ["local comparison set, Brier skill, raw", *both(v, f"{_rung('local_eb')}.brier_skill")],
        ["boosted model, recalibrated", *both(ci, _rung("GBM+cal"), "brier_skill")],
        ["local comparison set, recalibrated", *both(ci, _rung("local_eb+cal"), "brier_skill")],
        ["boosted model, decision value", *both(ci, _decision("GBM"), "diff_random")],
        ["local comparison set, decision value", *both(ci, _decision("local_eb"), "diff_random")],
        rule,
        heading("The exposure stand-in, correlation with the absolute standardized effect"),
        ["log of the user count", v(extras_a, "impressions_effect_correlation.corr_log_impressions_abs_z"),
         v(extras_u, "impressions_effect_correlation.corr_log_impressions_abs_z")],
        ["log of the run length", v(extras_a, "impressions_effect_correlation.corr_log_run_length_abs_z"), NOT_APPLICABLE],
        rule,
        heading("Abstention and the support trigger"),
        ["abstention rate, main run", v(extras_a, f"{support_run}.issued_in_main.abstention_rate"),
         v(extras_u, f"{support_run}.issued_in_main.abstention_rate")],
        ["abstention rate, support off", v(extras_a, f"{support_run}.issued_in_ablation.abstention_rate"),
         v(extras_u, f"{support_run}.issued_in_ablation.abstention_rate")],
        ["rows released, in tests", join("{} in {}", n(support_a, f"{released}.n"), n(support_a, f"{released}.n_tests")), n(support_u, f"{released}.n")],
        ["Brier skill of the released rows", ci(support_a, released, "brier_skill"), NOT_APPLICABLE],
        rule,
        heading("Drift and the weekly replay"),
        [join("P1 skill, first nominal year, {} tests", n(a, f"{first}.n_tests")), ci(a, first, "brier_skill"), NOT_APPLICABLE],
        [join("P1 skill, second nominal year, {} tests", n(a, f"{second}.n_tests")), ci(a, second, "brier_skill"), NOT_APPLICABLE],
        ["weeks replayed", *replays(n, "header.n_weeks")],
        ["cards", *replays(n, "header.n_cards")],
        ["cards abstained", *replays(n, "totals.abstained")],
        ["weeks flagged", *replays(n, "totals.n_flagged_weeks")],
        ["coverage of the 90 percent interval", *replays(v, "totals.coverage_90_all")],
        ["joined outcomes behind that coverage", *replays(n, "totals.coverage_90_all_n")],
        rule,
        heading("The prior's settings, P1"),
        ["log score, main settings", v(guard_a, "guarded.logscore"), v(u, LOGSCORE_P1)],
        ["log score, normal prior", v(normal_a, LOGSCORE_P1), v(normal_u, LOGSCORE_P1)],
        ["nats lost by the normal prior",
         derived(fmt(guard_a.get("guarded.logscore") - normal_a.get(LOGSCORE_P1)), guard_a.ref("guarded.logscore"), normal_a.ref(LOGSCORE_P1)),
         _nats_lost(u, normal_u)],
        ["Brier skill, normal prior", v(normal_a, BRIER_P1), v(normal_u, BRIER_P1)],
        ["log score at $\\kappa = 0$ and $\\kappa = 80$", join("{}, {}", v(k0_a, LOGSCORE_P1), v(k80_a, LOGSCORE_P1)),
         join("{}, {}", v(k0_u, LOGSCORE_P1), v(k80_u, LOGSCORE_P1))],
        rule,
        heading("The learning curve at one origin, P1"),
        ["held-out rows", n(curve_a, "heldout_rows"), n(curve_u, "heldout_rows")],
        ["held-out tests", n(curve_a, "heldout_tests"), n(curve_u, "heldout_tests")],
        ["five-percent subsamples not fit", _skipped(curve_a), _skipped(curve_u)],
        ["skill at fraction 0.05", ci(curve_a, curve.format(0.05), "skill"), ci(curve_u, curve.format(0.05), "skill")],
        ["skill at the full ledger", ci(curve_a, curve.format(1.0), "skill"), ci(curve_u, curve.format(1.0), "skill")],
    ]
    return Table("fmt-app-asos", "lll", ["figure & deployment-shaped & headline"], rows)


def app_syn_truth(r):
    rep = _main(r, "synthetic")
    source = "src/mootcourt/sources/synthetic.py _DEFAULT_CELLS"

    def row(label, cell):
        key = f"tables.split_half[cell={cell}]"
        mean, spread = _DEFAULT_CELLS[cell]
        return [label, derived(fmt(mean, 1), f"{source} {cell}"), v(rep, f"{key}.mu_odd", 2), v(rep, f"{key}.mu_even", 2),
                derived(fmt(spread, 1), f"{source} {cell}"), v(rep, f"{key}.tau_odd", 2), v(rep, f"{key}.tau_even", 2),
                join("{} / {}", n(rep, f"{key}.n_odd"), n(rep, f"{key}.n_even"))]

    header = [r" & \multicolumn{3}{c}{mean} & \multicolumn{3}{c}{spread} & ",
              "\\cmidrule(lr){2-4} \\cmidrule(lr){5-7}\ncell & true & odd & even & true & odd & even & rows, odd / even"]
    return Table("fmt-app-syn-truth", "lrrrrrrr", header,
                 [row("headline only", "headline_only"), row("image only", "image_only"), row("both", "both")])


def app_pc_point(r):
    rep = r("paper-extras-synthetic-*.json")

    def recovered(cell):
        return v(rep, f"{SENSITIVITY}.by_cell[cell={cell}].recovered_fraction", 2)

    return Table("fmt-app-pc-point", "lrrr", [" & P1 & P2 & oracle"], [
        ["Brier skill", v(rep, f"{SENSITIVITY}.brier_skill_p1"), v(rep, f"{SENSITIVITY}.brier_skill_p2"), v(rep, f"{SENSITIVITY}.brier_skill_oracle")],
        Raw(r"\midrule"),
        Raw(r" & headline only & both & image only \\"),
        Raw(r"\midrule"),
        ["recovered fraction", recovered("headline_only"), recovered("both"), recovered("image_only")],
    ])


def app_pc_sizes(r):
    rep = r("paper-extras-synthetic-*.json")
    sizes = (2000, 11100)

    def run(size):
        return f"positive_control_rungs.runs[n_tests={size}]"

    def pairs(size):
        """The admitted count is the share of pairs admitted times the pairs in that run's own selection table."""
        report = r(f"positive-control/rungs/n{size}/backtest-synthetic-*.json")
        total = len(report.get("tables.p2_selection"))
        share = rep.get(f"{run(size)}.share_pairs_admitted")
        return _of(round(share * total), total, [rep.ref(f"{run(size)}.share_pairs_admitted"), report.ref("tables.p2_selection")])

    def auc(size, rung):
        return v(rep, f"{run(size)}.by_cell.headline_only.rungs[rung={rung}].auc_event")

    return Table("fmt-app-pc-sizes", "lrr", [" & 2,000 tests & 11,100 tests"], [
        ["scored rows per cell", *[n(rep, f"{run(s)}.rows_per_cell_scored") for s in sizes]],
        ["pairs admitted", *[pairs(s) for s in sizes]],
        ["event AUC, text classifier", *[auc(s, "text_lr") for s in sizes]],
        ["event AUC, P1", *[auc(s, "P1") for s in sizes]],
    ])


def _tt(text, *keys):
    return derived(rf"\texttt{{{text}}}", *keys)


def _snapshot(label, rep):
    snapshot, model, feature = "header.snapshot_id", "header.model_id", "header.feature_hash"
    date, digest = rep.get(snapshot).split("-")
    return [label, _tt(date, rep.ref(snapshot)), _tt(digest, rep.ref(snapshot)), _tt(rep.get(model), rep.ref(model)), _tt(rep.get(feature), rep.ref(feature))]


def app_snapshots(r):
    return Table("fmt-app-snapshots", "lllll", ["ledger & date & snapshot & model & feature hash"], [
        _snapshot("headline archive", _main(r, UPWORTHY)),
        _snapshot("headline archive, randomization window included", r("include-randomization-window/backtest-upworthy-*.json")),
        _snapshot("deployment-shaped", _main(r, ASOS)),
        _snapshot("synthetic", _main(r, "synthetic")),
        _snapshot("planted ledger, 2,000 tests", r("positive-control/backtest-synthetic-*.json")),
        _snapshot("planted ledger, 11,100 tests", r("positive-control/rungs/n11100/backtest-synthetic-*.json")),
    ])


def gates_dependence(r):
    rep = r("gates.json")

    def leaf(rate, name):
        return f'by_base_rate["{rate}"].{name}'

    def merged(name, nd):
        """The cell of the row that merges two base rates; it exists only while the two rates' leaves agree."""
        low, high = rep.get(leaf("0.09", name)), rep.get(leaf("0.30", name))
        if low != high:
            raise ValueError(f"{name}: the base rates 0.09 and 0.30 differ, so their row must split")
        return derived(fmt(low, nd), rep.ref(leaf("0.09", name)), rep.ref(leaf("0.30", name)))

    return Table("gates-dependence", "lrr", ["base rate & rows per test & within-test correlation"], [
        ["0.09 and 0.30", merged("rows_per_test", 1), merged("icc", 2)],
        ["0.14", v(rep, leaf("0.14", "rows_per_test"), 1), v(rep, leaf("0.14", "icc"), 2)],
    ])


def ablations_upworthy_p1(r):
    """P1's log score and scored rows for each setting that changes either; a setting left out that does change one stops the build."""
    named = ("prior-normal", "kappa-0.0", "kappa-5.0", "kappa-80.0", "admission-prelaunch", "contrasts-one", "s-star-realized",
             "exposure-cell-median", "effect-scale-relative", "effect-scale-relative+s-star-realized")
    main = _main(r, UPWORTHY)
    for path in sorted(glob.glob(os.path.join(r.root, "ablations", "backtest-upworthy-*--*.json"))):
        setting = os.path.basename(path)[:-len(".json")].split("--", 1)[1]
        rep = _ablation(r, UPWORTHY, setting)
        same = abs(rep.get(LOGSCORE_P1) - main.get(LOGSCORE_P1)) < 1e-9 and rep.get("header.scored_rows") == main.get("header.scored_rows")
        if same == (setting in named):
            raise ValueError(f"{setting}: P1's row must be printed exactly when the setting changes it")

    def row(label, rep):
        return [label, v(rep, LOGSCORE_P1), n(rep, "header.scored_rows")]

    rows = [row("every other setting, and the main run", main), Raw(r"\midrule"),
            *[row(rf"\emph{{{setting}}}", _ablation(r, UPWORTHY, setting)) for setting in named]]
    return Table("ablations-upworthy-p1", "lrr", ["setting & P1 log score & scored rows"], rows)


TABLES = [app_asos, app_syn_truth, app_pc_point, app_pc_sizes, app_snapshots, gates_dependence, ablations_upworthy_p1]
