"""Summary tables of the paper's front matter: the results at a glance and the inputs of the gate."""
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


def _gate(rep, gates):
    """The tests the release gate asks for at the archive's base rate, and the claim that gate leaves decidable."""
    row = _agg("P1")
    rate = rep.get(f"{row}.gate_base_rate")
    tests = n(gates, f'by_base_rate["{rate:.2f}"].by_target["0.90"].n_400')
    word = derived(rep.get(f"{row}.decidable_by_tests").split()[0], rep.ref(f"{row}.decidable_by_tests"))
    return join("{} at {}; {}", tests, v(rep, f"{row}.gate_base_rate", 2), word)


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
    up, asos, syn, gates = r(UPWORTHY), r(ASOS), r(SYNTHETIC), r("gates.json")
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
        ["P1 Brier skill against the base rate (90\\%)", *[ci(a, p1, "brier_skill") for a in archives]],
        ["release gate, tests at base rate; pooled claim", *[_gate(a, gates) for a in archives]],
        ["P1 ECE, percentile of the clustered null", *[_ece_percentile(a) for a in archives]],
        ["P1 coverage of the 80 / 90 percent intervals",
         *[join("{} / {}", v(a, f"{p1}.coverage_80", 2), v(a, f"{p1}.coverage_90", 2)) for a in archives]],
        ["P1 90 percent coverage, most to least precise decile",
         join("{} to {}", v(up, "tables.coverage_by_se_ratio[rung=P1,decile=1].coverage_90", 2),
              v(up, "tables.coverage_by_se_ratio[rung=P1,decile=10].coverage_90", 2)), "n/a", "n/a"],
        ["abstention rate", *[v(a, f"{p1}.abstention_rate") for a in archives]],
        ["P2 minus P1, paired log score (90\\%)", ci(up, p2, "logscore_vs_p1", 4),
         join(held, v(asos, f"{p2}.logscore_vs_p1", 4)), join(held, v(syn, f"{p2}.logscore_vs_p1", 4))],
        ["best decision value at a quarter budget (90\\%)", _best_decision(up, "text_lr", "text classifier"),
         _best_decision(asos, "P1", "all rungs"), _best_decision(syn, "P1", "prior")],
        ["P1 decision value at a quarter budget (90\\%)", *[ci(a, _dv("P1"), "diff_matched") for a in archives]],
    ])


def gate_inputs(r):
    gates = r("gates.json")

    def row(rate):
        at = f'by_base_rate["{rate}"]'
        return [rate, v(gates, f"{at}.rows_per_test", 1), v(gates, f"{at}.icc", 2),
                n(gates, f'{at}.by_target["0.90"].n_200'), n(gates, f'{at}.by_target["0.90"].n_400')]

    return Table("fmt-gate-inputs", "rrrrr",
                 ["base rate & rows per test & within-test correlation & tests for skill 0.20 & tests for skill 0.10"],
                 [row("0.09"), row("0.14"), row("0.30")])


TABLES = [glance, gate_inputs]
