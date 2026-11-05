"""Round 02, Tier B rows that change a table of the paper and no number in it: R1-F1, R1-F2, R1-F8 and R5-F8 (task R02-B).

Each test builds a small report file, runs the table builder on it and reads the LaTeX it writes.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _builder():
    spec = importlib.util.spec_from_file_location("build_tables_r02", ROOT / "paper" / "build_tables.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.set_reports_root(None)
    return mod


def _tex(out: Path, name: str) -> list[str]:
    return [ln for ln in (out / name).read_text().splitlines() if not ln.startswith("%")]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.rstrip("\\ ").split("&")]


# ---- R1-F1: the learning-curve detail prints the raw Brier score, the base rates and the seed spread
def test_r1_the_learning_detail_table_prints_the_raw_brier_score_the_base_rates_and_the_seed_spread(tmp_path):
    bt = _builder()
    rows = []
    for frac, fit, brier, own, sd in ((0.01, 122.65, 0.0554, 0.0602, 0.0359), (1.0, 11997.0, 0.0538, 0.0555, 0.0019)):
        rows.append({"fraction": frac, "rung": "P1", "n_fit_rows": fit, "n_history_tests": 35.0, "n_scored_tests": 318, "skill": 0.0007,
                     "skill_own_base": 0.0679, "brier": brier, "base_brier_own": own, "base_brier_full": 0.0555, "skill_seed_sd": sd})
    path = tmp_path / "learning-curve-upworthy-X.json"
    path.write_text(json.dumps({"rows": rows, "bootstrap_resamples": 500}))
    out = tmp_path / "out"
    out.mkdir()
    bt.learning_detail_table(str(path), "upworthy", str(out))
    lines = _tex(out, "learning-detail-upworthy.tex")
    head = next(ln for ln in lines if ln.startswith("fraction"))
    for needle in ("P1 Brier score", "base Brier score, own", "base Brier score, full history", "seed spread"):
        assert needle in head, (needle, head)
    first = _cells(next(ln for ln in lines if ln.startswith("0.01")))
    assert {"0.0554", "0.0602", "0.0555", "0.0359"} <= set(first), first
    last = _cells(next(ln for ln in lines if ln.startswith("1.00")))
    assert {"0.0538", "0.0555", "0.0019"} <= set(last), last


# ------------------------------------------------------------------ R1-F2: the ablation table prints the paired P2 minus P1 difference
def test_r1_the_ablation_table_prints_the_paired_p2_minus_p1_interval_with_the_guard_on_and_off(tmp_path):
    bt = _builder()
    ab = tmp_path / "ablations"
    ab.mkdir()

    def report(skill, diff, lo, hi):
        row = {"cell": "ALL", "rung": "P2", "logscore": -0.856, "brier_skill": skill, "brier_skill_lo": skill - 0.003,
               "brier_skill_hi": skill + 0.003, "logscore_vs_p1": diff, "logscore_vs_p1_lo": lo, "logscore_vs_p1_hi": hi}
        return {"header": {"p2_guard": "on", "bootstrap_resamples": 500, "snapshot_id": "S"}, "tables": {"aggregate": [row]}}

    (ab / "backtest-upworthy-S--admission-prelaunch.json").write_text(json.dumps(report(0.0025, 0.00092, 0.00026, 0.00161)))
    (ab / "backtest-upworthy-S--admission-prelaunch+p2-guard-off.json").write_text(json.dumps(report(0.0011, -0.0031, -0.0040, -0.0022)))
    out = tmp_path / "out"
    out.mkdir()
    bt.ablation_table(str(tmp_path), "upworthy", str(out))
    lines = _tex(out, "ablations-upworthy.tex")
    head = next(ln for ln in lines if ln.startswith("setting"))
    assert head.count("minus P1") == 2, head
    row = next(ln for ln in lines if ln.startswith("admission-prelaunch"))
    assert "0.00092 (0.00026, 0.00161)" in row and "-0.00310 (-0.00400, -0.00220)" in row, row


# ------------------------------------------------------------------ R1-F8: the positive-control gain table prints the oracle's interval
def test_r1_the_positive_control_gain_table_prints_the_oracle_gain_with_its_interval(tmp_path):
    bt = _builder()
    row = {"n_tests": 2000, "rows_per_cell": 1300, "text_effect_strength": 1.0, "share_admitted": 0.5, "realized_gain": 0.0001,
           "realized_gain_lo": -0.0002, "realized_gain_hi": 0.0003, "oracle_gain": 0.0204, "oracle_gain_lo": 0.0189, "oracle_gain_hi": 0.0221,
           "recovered_fraction": 0.01, "recovered_fraction_lo": -0.01, "recovered_fraction_hi": 0.02, "brier_skill_p1": 0.01, "brier_skill_p2": 0.01}
    sens = {"rows": [row], "inputs": {}, "multiplier": 1}
    (tmp_path / "paper-extras-synthetic-X.json").write_text(json.dumps({"positive_control_sensitivity": sens}))
    out = tmp_path / "out"
    out.mkdir()
    bt.positive_control_gain_table(str(tmp_path), str(out))
    lines = _tex(out, "positive-control-gain.tex")
    assert "oracle $-$ P1 (90\\%)" in next(ln for ln in lines if ln.startswith("tests"))
    assert "0.0204 (0.0189, 0.0221)" in next(ln for ln in lines if ln.startswith("2,000"))


# ------------------------------------------------------------------ R5-F8: the decision-interval tables keep the matched columns only
def test_r5_the_decision_interval_tables_drop_the_unmatched_random_columns(tmp_path):
    bt = _builder()
    base = {"origin": "ALL", "budget": 0.25, "captured_fraction": 0.30, "captured_fraction_lo": 0.28, "captured_fraction_hi": 0.32, "regret": 12.0,
            "regret_lo": 11.0, "regret_hi": 13.0, "family_size": 5}
    rows = [{**base, "policy": "random", "rung": "all"},
            {**base, "policy": "arm_count", "rung": "all", "diff_random": 0.05, "diff_random_lo": 0.04, "diff_random_hi": 0.06,
             "diff_random_adjusted_lo": 0.03, "diff_random_adjusted_hi": 0.07, "diff_matched": 0.01, "diff_matched_lo": 0.002,
             "diff_matched_hi": 0.02, "diff_matched_adjusted_lo": -0.001, "diff_matched_adjusted_hi": 0.03}]
    rep = {"_path": "r.json", "tables": {"decision_value": rows}}
    out = tmp_path / "out"
    out.mkdir()
    bt.decision_intervals_table(rep, "upworthy", str(out))
    lines = _tex(out, "decision-intervals-upworthy.tex")
    head = next(ln for ln in lines if ln.startswith("budget"))
    assert "minus arm-count-matched random (90" in head and "minus matched, Bonferroni-adjusted" in head
    assert "minus random (90" not in head and "minus random, Bonferroni" not in head, head
    assert head.count("&") + 1 == len(_cells(next(ln for ln in lines if ln.startswith("0.25 & arm")))) == 8
    assert "{llrrrrrr}" in "\n".join(lines)


# ------------------------------------------------------------------ R4 via R6.11: no signed zero in a table
def test_r4_the_formatter_prints_no_signed_zero():
    bt = _builder()
    assert bt.f3(-0.00001, 4) == "0.0000" and bt.f3(-0.0, 3) == "0.000" and bt.f3(-0.0004, 3) == "0.000"
    assert bt.f3(-0.0006, 3) == "-0.001" and bt.f3(0.0123, 2) == "0.01" and bt.f3(None) == ""
    assert bt.fr(-0.0001) == "0.000" and bt.fr(-12.34) == "-12.3"
    assert bt.interval({"k": -0.00001, "k_lo": -0.00002, "k_hi": 0.0003}, "k", 4) == "0.0000 (0.0000, 0.0003)"


# ------------------------------------------------------------------ round 03, decisions 28 and 29
def test_r3_the_paired_ablation_column_prints_five_decimals(tmp_path):
    bt = _builder()
    ab = tmp_path / "ablations"
    ab.mkdir()
    row = {"cell": "ALL", "rung": "P2", "logscore": -0.856, "brier_skill": 0.002, "brier_skill_lo": 0.0, "brier_skill_hi": 0.004,
           "logscore_vs_p1": 0.00031, "logscore_vs_p1_lo": -0.00002, "logscore_vs_p1_hi": 0.00071}
    rep = {"header": {"p2_guard": "on", "bootstrap_resamples": 500, "snapshot_id": "S"}, "tables": {"aggregate": [row]}}
    (ab / "backtest-upworthy-S--kappa-5.0.json").write_text(json.dumps(rep))
    out = tmp_path / "out"
    out.mkdir()
    bt.ablation_table(str(tmp_path), "upworthy", str(out))
    line = next(ln for ln in _tex(out, "ablations-upworthy.tex") if ln.startswith("kappa"))
    assert "0.00031 (-0.00002, 0.00071)" in line, line


def _pair_row(mean, lo, hi):
    return {"origin": "2013-10-01", "cell": "headline_only", "lambda": 0.5, "rows": 100, "share_p2_better": 0.5, "share_p2_better_lo": 0.4,
            "share_p2_better_hi": 0.6, "median_diff": -0.002, "median_diff_lo": -0.003, "median_diff_hi": -0.001, "mean_diff": mean,
            "mean_diff_lo": lo, "mean_diff_hi": hi, "decisive": {"rows": 10, "mean_diff": -0.005}, "non_decisive": {"mean_diff": 0.003},
            "location_part": 0.0035, "location_part_lo": 0.0025, "location_part_hi": 0.0046, "scale_part": -0.0026, "scale_part_lo": -0.004,
            "scale_part_hi": -0.001}


def test_r3_the_rows_table_prints_the_median_interval_and_the_one_pooled_interval_of_the_guard_pairs_table(tmp_path):
    bt = _builder()
    extras = {"guard_pairs_rows": {"rows": [_pair_row(-0.0276, -0.0341, -0.0206)], "pooled": _pair_row(0.00097, -0.00075, 0.00271),
                                   "inputs": {"bootstrap_resamples": 500}, "decomposition": {"defined": True}},
              "guard_pairs": {"rows": [], "summary": {"pooled_realized_p2_minus_p1": 0.00097, "pooled_lo": -0.00073, "pooled_hi": 0.00251,
                                                      "bootstrap_resamples": 500}}}
    (tmp_path / "paper-extras-upworthy-X.json").write_text(json.dumps(extras))
    out = tmp_path / "out"
    out.mkdir()
    bt.guard_pairs_rows_table(str(tmp_path), str(out))
    lines = _tex(out, "guard-pairs-rows.tex")
    pooled = next(ln for ln in lines if ln.startswith("pooled"))
    assert "0.0010 (-0.0007, 0.0025)" in pooled, pooled        # the interval of Table guard-pairs, to the digit
    assert "-0.0020 (-0.0030, -0.0010)" in pooled, pooled        # the median now carries its interval
    first = next(ln for ln in lines if ln.startswith("2013-10-01"))
    assert "-0.0276 (-0.0341, -0.0206)" in first and "-0.0020 (-0.0030, -0.0010)" in first
