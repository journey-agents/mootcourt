"""Task 3: the claims audit compares the printed value of each claim with the value in its report, not only the path."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEAD = "| id | section | sentence | report path | key path | printed value | interval kind | status |\n|---|---|---|---|---|---|---|---|\n"


@pytest.fixture(scope="module")
def ca():
    spec = importlib.util.spec_from_file_location("claims_audit", ROOT / "scripts" / "claims_audit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["claims_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def run_dir(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "report.json").write_text(json.dumps({
        "header": {"origins_scored": 9, "scored_rows": 13247},
        "tables": {"aggregate": [{"predictor": "p1", "cell": "ALL", "rung": "P1", "logscore_vs_p1": 0.0, "skill": -0.0158},
                                 {"predictor": "p2", "cell": "ALL", "rung": "P2", "logscore_vs_p1": 0.0004, "skill": 0.0301}],
                   "wrapped": {"rows": [{"k": "a", "v": 0.857}]}}}))
    return run


def register(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "claims.md"
    path.write_text(HEAD + "\n".join(rows) + "\n")
    return path


def row(cid="C9", path="report.json", key="tables.aggregate[predictor=p2].logscore_vs_p1", value="0.0004", kind="adjusted", status="supported"):
    return f"| {cid} | 6 | A sentence. | {path} | {key} | {value} | {kind} | {status} |"


def test_every_claim_resolves_to_a_value_in_a_report(tmp_path, ca, run_dir):
    reg = register(tmp_path, row(), row("C10", key="header.scored_rows", value="13,247"), row("C11", key="header.origins_scored", value="9"),
                   row("C12", key="tables.aggregate[cell=ALL,rung=P1].skill", value="minus 0.016"),
                   row("C13", key="tables.aggregate[predictor=p2].skill", value="3.0%"),
                   row("C14", key="tables.wrapped[k=a].v", value="0.857"),
                   row("C15", path="none", key="none", value="none"))
    results = ca.claims_audit(reg, run_dir)
    assert [r.id for r in results] == ["C9", "C10", "C11", "C12", "C13", "C14", "C15"]
    assert [r.id for r in results if not r.ok] == []


def test_a_value_that_moved_is_reported(tmp_path, ca, run_dir):
    results = ca.claims_audit(register(tmp_path, row(value="0.0040")), run_dir)
    assert results[0].ok is False and "0.0004" in results[0].reason and "0.0040" in results[0].reason


def test_a_missing_report_or_key_is_reported(tmp_path, ca, run_dir):
    reg = register(tmp_path, row("C1", path="gone.json"), row("C2", key="tables.aggregate[predictor=p9].skill"),
                   row("C3", key="tables.aggregate[predictor=p2].nothing"), row("C4", key="tables.nothing[a=b].c"))
    results = ca.claims_audit(reg, run_dir)
    assert [r.ok for r in results] == [False] * 4
    assert "gone.json" in results[0].reason and "predictor=p9" in results[1].reason


def test_sign_is_compared(tmp_path, ca, run_dir):
    results = ca.claims_audit(register(tmp_path, row(key="tables.aggregate[predictor=p2].skill", value="minus 0.030")), run_dir)
    assert results[0].ok is False


def test_main_exits_one_and_prints_one_line_per_failing_row(tmp_path, ca, run_dir, capsys):
    reg = register(tmp_path, row(), row("C10", value="0.5"))
    assert ca.main([str(reg), str(run_dir)]) == 1
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1 and out[0].startswith("C10")
    assert ca.main([str(register(tmp_path, row())), str(run_dir)]) == 0


# ----------------------------------------------------------------------------------------------- gaps found on the real register
@pytest.fixture()
def rich(tmp_path):
    run = tmp_path / "rich"
    run.mkdir()
    (run / "r.json").write_text(json.dumps({
        "by_base_rate": {"0.09": {"by_target": {"0.90": {"n_400": 250}}}},
        "flag": True, "verdict": "undecidable at this n",
        "tables": {"t": [{"rung": "P0", "d": -0.1493, "pts": 0.03946, "x": 14.15}]}}))
    return run


def _one(ca, tmp_path, run, key, value):
    return ca.claims_audit(register(tmp_path, row(path="r.json", key=key, value=value)), run)[0]


def test_neg_and_pct_prefixes_transform_the_found_value_and_compose(tmp_path, ca, rich):
    assert _one(ca, tmp_path, rich, "neg:tables.t[rung=P0].d", "0.149").ok
    assert _one(ca, tmp_path, rich, "pct:tables.t[rung=P0].pts", "3.9 points").ok
    assert _one(ca, tmp_path, rich, "neg:pct:tables.t[rung=P0].d", "14.9").ok
    assert not _one(ca, tmp_path, rich, "tables.t[rung=P0].d", "0.149").ok, "without neg: the sign counts"


def test_quoted_dictionary_keys_index_a_dict(tmp_path, ca, rich):
    assert _one(ca, tmp_path, rich, 'by_base_rate["0.09"].by_target["0.90"].n_400', "250").ok
    res = _one(ca, tmp_path, rich, 'by_base_rate["0.14"].by_target["0.90"].n_400', "250")
    assert not res.ok and "0.14" in res.reason


def test_non_numeric_printed_values_compare_as_text(tmp_path, ca, rich):
    assert _one(ca, tmp_path, rich, "flag", "true").ok and _one(ca, tmp_path, rich, "flag", "True").ok
    assert not _one(ca, tmp_path, rich, "flag", "false").ok
    assert _one(ca, tmp_path, rich, "verdict", "Undecidable  at this  n").ok
    assert not _one(ca, tmp_path, rich, "verdict", "decidable at skill 0.20 and 0.10").ok


def test_tolerance_is_half_a_unit_of_the_last_printed_decimal(tmp_path, ca, rich):
    assert _one(ca, tmp_path, rich, "tables.t[rung=P0].x", "14.2").ok
    assert _one(ca, tmp_path, rich, "tables.t[rung=P0].x", "14.1").ok
    assert not _one(ca, tmp_path, rich, "tables.t[rung=P0].x", "14.3").ok
    res = _one(ca, tmp_path, rich, "tables.t[rung=P0].pts", "0.040")
    assert not res.ok and "0.040" in res.reason and "0.03946" in res.reason


def test_units_and_signs_words_are_stripped_before_parsing(tmp_path, ca, rich):
    for printed in ("14.2 nats", "plus 14.2", "14.2 s", "14.2 rows", "14.2 tests"):
        assert _one(ca, tmp_path, rich, "tables.t[rung=P0].x", printed).ok, printed
    assert _one(ca, tmp_path, rich, "tables.t[rung=P0].d", "minus 0.149 nats").ok
