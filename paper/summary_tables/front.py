"""Summary tables of the paper's front matter: the results at a glance."""
from summary_tables import Table, ci, derived, fmt, join, n, v

UPWORTHY, ASOS, SYNTHETIC = "backtest-upworthy-*.json", "backtest-asos-*.json", "backtest-synthetic-*.json"


def _agg(rung):
    return f"tables.aggregate[cell=ALL,rung={rung}]"


def _dv(rung):
    return f"tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung={rung}]"


def _gain_over_p0(rep):
    """P1 minus P0: the key holds P0 minus P1, so the value negates and the bounds swap."""
    row = _agg("P0")
    x, lo, hi = (rep.get(f"{row}.logscore_vs_p1{s}") for s in ("", "_lo", "_hi"))
    return derived(f"{fmt(-x)} ({fmt(-hi)}, {fmt(-lo)})", *[rep.ref(f"{row}.logscore_vs_p1{s}") for s in ("", "_lo", "_hi")])


def _gate(extras):
    """The tests the release gate asks for at the archive's own dependence, the one rule of Section 5, and the pooled claim's verdict."""
    at = "gates_by_stratum.strata.ALL"
    word = derived(extras.get(f"{at}.verdict").split()[0], extras.ref(f"{at}.verdict"))
    return join("{} at {}; {}", n(extras, f"{at}.own_gate.n_400"), v(extras, f"{at}.dependence.base_rate", 2), word)


def _gate_scaled(rep):
    """An archive with no stratum simulation: the report's gate scaled to the archive's dependence, which the caption says."""
    row = _agg("P1")
    word = derived(rep.get(f"{row}.decidable_by_tests_cell").split()[0], rep.ref(f"{row}.decidable_by_tests_cell"))
    return join("{} at {}; {}", n(rep, f"{row}.gate_cell_n_400"), v(rep, f"{row}.gate_base_rate", 2), word)


def _ece_percentile(rep):
    key = f"{_agg('P1')}.ece_percentile"
    return derived(f"{rep.get(key):g}", rep.ref(key))


def _decision_rows(rep):
    return [row for row in rep.get("tables.decision_value")
            if row["origin"] == "ALL" and row["budget"] == 0.25 and row["policy"] == "p_win"]


def _best_decision(rep, rung, label):
    """The named rung's decision value; a rung that overtakes it fails the build, since the row says best."""
    top = max(row["diff_matched"] for row in _decision_rows(rep))
    if rep.get(f"{_dv(rung)}.diff_matched") < top - 1e-9:
        raise ValueError(f"{rep.name}: {rung} is no longer the best decision value")
    return join(label + " {}", ci(rep, _dv(rung), "diff_matched"))


def glance(r):
    up, asos, syn = r(UPWORTHY), r(ASOS), r(SYNTHETIC)
    up_extras, asos_extras = r("paper-extras-upworthy-*.json"), r("paper-extras-asos-*.json")
    archives = (up, asos, syn)
    p1, p2 = _agg("P1"), _agg("P2")
    if max(abs(row["diff_matched"]) for row in _decision_rows(asos)) > 1e-9:
        raise ValueError("the ASOS row says all rungs hold a decision value of zero")
    held = "{}; guard holds $\\lambda$ at zero"
    if any(row["lambda"] != 0 for a in (asos, syn) for row in a.get("tables.p2_selection")):
        raise ValueError("the row says the guard holds the weight at zero")

    return Table("glance", "lrrr", [" & Upworthy (headline archive) & ASOS (deployment-shaped) & Synthetic (no planted text signal)"], [
        ["scored tests / rows", *[join("{} / {}", n(a, "header.tests_scored"), n(a, "header.scored_rows")) for a in archives]],
        ["P1 log score gain over P0, nats (90\\%)", *[_gain_over_p0(a) for a in archives]],
        ["P1 Brier skill, event at realized precision (90\\%)", *[ci(a, p1, "brier_skill", 4) for a in archives]],
        ["P1 Brier skill, event at planned precision (90\\%, unadjusted)", *[ci(a, p1, "brier_skill_planned", 4) for a in archives]],
        ["gate for skill 0.10, tests at base rate; pooled claim", _gate(up_extras), _gate(asos_extras), _gate_scaled(syn)],
        ["P1 ECE, percentile of the clustered null", *[_ece_percentile(a) for a in archives]],
        ["P1 coverage of the 80 / 90 percent intervals",
         *[join("{} / {}", v(a, f"{p1}.coverage_80", 2), v(a, f"{p1}.coverage_90", 2)) for a in archives]],
        ["P1 90 percent coverage, deciles of realized over planned $s$",
         join("{} to {}", v(up, "tables.coverage_by_se_ratio[rung=P1,decile=1].coverage_90", 2),
              v(up, "tables.coverage_by_se_ratio[rung=P1,decile=10].coverage_90", 2)), "n/a", "n/a"],
        ["abstention rate", *[v(a, f"{p1}.abstention_rate") for a in archives]],
        ["P2 minus P1, paired log score (90\\%)", ci(up, p2, "logscore_vs_p1", 4),
         join(held, v(asos, f"{p2}.logscore_vs_p1", 4)), join(held, v(syn, f"{p2}.logscore_vs_p1", 4))],
        ["best decision value at a quarter budget (90\\%)", _best_decision(up, "text_lr", "text classifier"),
         _best_decision(asos, "P1", "all rungs"), _best_decision(syn, "P1", "prior")],
        ["P1 decision value at a quarter budget (90\\%)", *[ci(a, _dv("P1"), "diff_matched") for a in archives]],
    ])


TABLES = [glance]
