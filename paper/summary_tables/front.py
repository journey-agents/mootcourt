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
    """One archive and the synthetic check. The retailer's archive is an appendix check of the mechanics and has no column here."""
    up, syn = r(UPWORTHY), r(SYNTHETIC)
    up_extras, origins = r("paper-extras-upworthy-*.json"), r("by-origin-upworthy-*.json")
    skills = r("by-origin-skill-upworthy-*.json")
    archives = (up, syn)
    p1, p2 = _agg("P1"), _agg("P2")
    if abs(origins.get("pooled.difference") + up.get(f"{_agg('P0')}.logscore_vs_p1")) > 1e-9:
        raise ValueError("the by-origin report does not reproduce the main report's pooled difference")
    if any(row["lambda"] != 0 for row in syn.get("tables.p2_selection")):
        raise ValueError("the row says the guard holds the weight at zero")
    arm = 'ranking_paired.budgets["0.25"].differences.text_lr_minus_arm_count'
    lo, hi = up_extras.get(f"{arm}.lo"), up_extras.get(f"{arm}.hi")
    if not lo < 0 < hi:
        raise ValueError("the row is labelled as a difference whose interval spans zero")

    return Table("glance", "lrr", [" & headline archive & synthetic ledger (no planted text signal)"], [
        ["scored tests / rows", *[join("{} / {}", n(a, "header.tests_scored"), n(a, "header.scored_rows")) for a in archives]],
        ["P1 minus P0, log score in nats per contrast (90\\%, tests resampled)", *[_gain_over_p0(a) for a in archives]],
        ["the same, the seven quarters as units (90\\%)",
         join("{} ({}, {})", v(origins, "origin_level.difference", 3), v(origins, "origin_level.lo", 3), v(origins, "origin_level.hi", 3)), "not computed"],
        ["P1 Brier skill, significance judged at the test's own standard error (90\\%, unadjusted)", *[ci(a, p1, "brier_skill", 4) for a in archives]],
        ["the same, the seven quarters as units (90\\%)",
         join("{} ({}, {})", v(skills, "rungs.P1.realized.origin_level.skill", 4), v(skills, "rungs.P1.realized.origin_level.lo", 4),
              v(skills, "rungs.P1.realized.origin_level.hi", 4)), "not computed"],
        ["P1 Brier skill, significance judged at the planned standard error (90\\%, unadjusted)", *[ci(a, p1, "brier_skill_planned", 4) for a in archives]],
        ["P1 ECE, percentile of the clustered null", *[_ece_percentile(a) for a in archives]],
        ["P1 coverage of the 80 / 90 percent intervals",
         *[join("{} / {}", v(a, f"{p1}.coverage_80", 2), v(a, f"{p1}.coverage_90", 2)) for a in archives]],
        ["P2 minus P1, paired log score (90\\%)", ci(up, p2, "logscore_vs_p1", 4),
         join("{}; guard holds $\\lambda$ at zero", v(syn, f"{p2}.logscore_vs_p1", 4))],
        ["text classifier minus the arm-count rule, captured lift at a quarter budget (90\\%)",
         join("{} ({}, {})", v(up_extras, f"{arm}.estimate", 3), v(up_extras, f"{arm}.lo", 3), v(up_extras, f"{arm}.hi", 3)), "not computed"],
    ])


TABLES = [glance]
