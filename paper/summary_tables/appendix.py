"""Summary tables of the appendix: the deployment-shaped archive, the synthetic truth, the planted ledger, wall time and the snapshots."""
import fnmatch
import os

from mootcourt.sources.synthetic import _DEFAULT_CELLS
from summary_tables import Raw, Table, ci, derived, fmt, join, n, v

UPWORTHY, ASOS = "upworthy", "asos"
RUN = "$RUN6"
LOGSCORE_P1 = "tables.aggregate[cell=ALL,rung=P1].logscore"
BRIER_P1 = "tables.aggregate[cell=ALL,rung=P1].brier_skill"
SENSITIVITY = "positive_control_sensitivity.rows[n_tests=11100,text_effect_strength=1.0]"
SPELLED = {2: "two", 3: "three", 10: "ten"}


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
        ["log of the run length", v(extras_a, "impressions_effect_correlation.corr_log_run_length_abs_z"), ""],
        rule,
        heading("Abstention and the support trigger"),
        ["abstention rate, main run", v(extras_a, f"{support_run}.issued_in_main.abstention_rate"),
         v(extras_u, f"{support_run}.issued_in_main.abstention_rate")],
        ["abstention rate, support off", v(extras_a, f"{support_run}.issued_in_ablation.abstention_rate"),
         v(extras_u, f"{support_run}.issued_in_ablation.abstention_rate")],
        ["rows released, in tests", join("{} in {}", n(support_a, f"{released}.n"), n(support_a, f"{released}.n_tests")), n(support_u, f"{released}.n")],
        ["Brier skill of the released rows", ci(support_a, released, "brier_skill"), ""],
        rule,
        heading("Drift and the weekly replay"),
        [join("P1 skill, first nominal year, {} tests", n(a, f"{first}.n_tests")), ci(a, first, "brier_skill"), ""],
        [join("P1 skill, second nominal year, {} tests", n(a, f"{second}.n_tests")), ci(a, second, "brier_skill"), ""],
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
        heading("The learning curve at the final origin, P1"),
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


def _stages(r):
    """Seconds by stage from the driver's ``stages.txt`` (lines of name, exit code, seconds); marker lines carry no seconds."""
    stages = {}
    with open(os.path.join(r.root, "stages.txt")) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) == 3:
                stages[parts[0]] = int(parts[2])
    return stages


def app_driver(r):
    stages = _stages(r)
    used = set()

    def pick(*patterns):
        names = [s for s in stages if any(fnmatch.fnmatch(s, p) for p in patterns)]
        if not names or used & set(names):
            raise ValueError(f"{patterns}: stages empty or counted twice")
        used.update(names)
        return names

    def seconds(names, *patterns):
        return derived(fmt(sum(stages[s] for s in names), 0, comma=True), f"{RUN}/stages.txt {' '.join(patterns)}")

    def group(label, *patterns):
        names = pick(*patterns)
        count = len(names)
        return [label.format(count=count, word=SPELLED.get(count, count)), seconds(names, *patterns)]

    outside = [
        group("the {count} headline-archive ablations", "ablation-upworthy-*"),
        group("the {word} extras files", "extras-*"),
        group("the {word} learning curves", "lc-*"),
        group("the planted ledgers", "pc*"),
        group("the refresh check", "refresh-check"),
        group("the {word} replays", "replay-*"),
        group("the {word} deployment-shaped ablations", "ablation-asos-*"),
        group("the cautionary run", "cautionary"),
        group("the {word} guard comparisons", "guard-compare-*"),
        group("the ablation that includes the randomization window", "window-ablation"),
        group("the gates at each stratum's own dependence, {word} archives", "gates-strata-*"),
        group("the sizing evaluation", "sizing-*"),
    ]
    outside_names = sorted(used)
    timed_patterns = ("gates", "fit-*", "main-*", "audit-*", "latency")
    timed_names = pick(*timed_patterns)
    if used != set(stages):
        raise ValueError(f"stages in no group: {sorted(set(stages) - used)}")
    summary = [
        ["outside the timed run's stages", derived(fmt(sum(stages[s] for s in outside_names), 0, comma=True), f"{RUN}/stages.txt outside the timed run's stage names")],
        ["the timed run's stages", seconds(timed_names, *timed_patterns)],
        Raw(r"\midrule"),
        ["all stages", derived(fmt(sum(stages.values()), 0, comma=True), f"{RUN}/stages.txt seconds summed")],
    ]
    return Table("fmt-app-driver", "lr", ["stages & seconds"], [*outside, Raw(r"\midrule"), *summary])


def app_latency(r):
    rep = r("card-latency.json")

    def dotted(top, name):
        """A leaf whose top-level key holds a dot, which the key syntax cannot step into."""
        return derived(fmt(rep.doc[top][name], 1), rep.ref(f"{top}.{name}"))

    return Table("fmt-app-latency", "lrr", ["how the card is produced & median & at most"], [
        ["in process, bundle preloaded", v(rep, "in_process_ms.p50", 1), v(rep, "in_process_ms.max", 1)],
        ["same, weight forced to 0.5", dotted("in_process_lambda_0.5_ms", "p50"), dotted("in_process_lambda_0.5_ms", "max")],
        ["through the loopback service", v(rep, "service_ms.p50", 1), v(rep, "service_ms.max", 1)],
        ["fresh process", join("{} s", v(rep, "cli_fresh_process_ms.p50", 2, scale=0.001)), ""],
        ["of which loading the bundle", v(rep, "bundle_load_ms", 0), ""],
    ])


def app_scale(r):
    def row(size):
        rep = r(f"scale/scale-{size}.json")
        return [n(rep, "n_contrasts"), n(rep, "stages.fit.seconds"), v(rep, "card_latency_ms.p50_ms", 1), v(rep, "peak_rss_gb", 2)]

    return Table("fmt-app-scale", "rrrr", ["contrasts & fit (s) & median card (ms) & peak memory (GiB)"], [row(100000), row(1000000)])


def _tt(text, *keys):
    return derived(rf"\texttt{{{text}}}", *keys)


def _snapshot(label, rep, prefix, feature_hash):
    snapshot, model = f"{prefix}.snapshot_id", f"{prefix}.model_id"
    date, digest = rep.get(snapshot).split("-")
    feature = _tt(rep.get(f"{prefix}.feature_hash"), rep.ref(f"{prefix}.feature_hash")) if feature_hash else ""
    return [label, _tt(date, rep.ref(snapshot)), _tt(digest, rep.ref(snapshot)), _tt(rep.get(model), rep.ref(model)), feature]


def app_snapshots(r):
    return Table("fmt-app-snapshots", "lllll", ["ledger & date & snapshot & model & feature hash"], [
        _snapshot("headline archive", _main(r, UPWORTHY), "header", True),
        _snapshot("deployment-shaped", _main(r, ASOS), "header", True),
        _snapshot("synthetic", _main(r, "synthetic"), "header", True),
        _snapshot("positive control", r("positive-control/backtest-synthetic-*.json"), "header", False),
        _snapshot("planted ledger, 11,100 tests", r("paper-extras-synthetic-*.json"), "positive_control_rungs.runs[n_tests=11100]", False),
    ])


def app_tail(r):
    rep = r("paper-extras-synthetic-*.json")

    def row(size):
        key = f"top_m_tail_share.by_size[contrasts={size}]"
        share = f"{key}.share_p2_weight"
        return [n(rep, f"{key}.contrasts"), v(rep, f"{share}.mean", 2), join("{} to {}", v(rep, f"{share}.p10", 2), v(rep, f"{share}.p90", 2))]

    return Table("fmt-app-tail", "rrr", ["contrasts & mean share & 10th to 90th percentile"], [row(10000), row(100000), row(300000)])


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


def _p1_logscore(r, source, setting):
    return v(_ablation(r, source, setting), LOGSCORE_P1)


def ablations_asos_p1(r):
    settings = ("p2-guard-off", "prior-normal", "kappa-0.0", "kappa-5.0", "kappa-80.0")
    return Table("ablations-asos-p1", "lrrrrr", [r" & every other row & \emph{prior-normal} & $\kappa = 0$ & $\kappa = 5$ & $\kappa = 80$"],
                 [["P1 log score", *[_p1_logscore(r, ASOS, s) for s in settings]]])


def ablations_upworthy_p1(r):
    settings = ("lambda-0.0", "prior-normal", "admission-prelaunch", "contrasts-one", "kappa-0.0", "kappa-5.0", "kappa-80.0")
    header = [r" & every other row & \emph{prior-normal} & \emph{admission-prelaunch} & \emph{contrasts-one} & $\kappa = 0$ & $\kappa = 5$ & $\kappa = 80$"]
    scored = [n(_ablation(r, UPWORTHY, s), "header.scored_rows") for s in ("admission-prelaunch", "contrasts-one")]
    return Table("ablations-upworthy-p1", "lrrrrrrr", header, [
        ["P1 log score", *[_p1_logscore(r, UPWORTHY, s) for s in settings]],
        ["scored rows, where different", "", "", *scored, "", "", ""],
    ])


TABLES = [app_asos, app_syn_truth, app_pc_point, app_pc_sizes, app_driver, app_latency, app_scale, app_snapshots, app_tail,
          gates_dependence, ablations_asos_p1, ablations_upworthy_p1]
