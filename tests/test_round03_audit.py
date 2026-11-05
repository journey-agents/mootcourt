"""Round 03, decision 30: the number audit matches a printed number to the report leaf first, so a rounded comment cannot vouch for it."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pa():
    spec = importlib.util.spec_from_file_location("paper_audit_r03", ROOT / "scripts" / "paper_audit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["paper_audit_r03"] = mod
    spec.loader.exec_module(mod)
    return mod


def _paper(tmp_path: Path, tex: str) -> tuple[Path, Path]:
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    run = paper / "data" / "run9"
    run.mkdir(parents=True)
    (run / "report.json").write_text('{"tables": {"aggregate": [{"brier": 0.053846, "n": 13247, "diff": 0.1493}]}}')
    (paper / "main.tex").write_text("\\input{sections/a}\n")
    (paper / "sections" / "a.tex").write_text(tex)
    return paper, run


def test_a_double_rounded_number_does_not_pass_on_the_strength_of_a_rounded_comment(tmp_path, pa):
    bad = _paper(tmp_path / "bad", "% src: $RUN6/report.json tables.aggregate brier 0.05385\nThe Brier score is 0.0539 on 13,247 rows.\n")
    res = pa.number_audit(*bad)
    assert [u[2] for u in res.unmatched] == ["0.0539"], res.unmatched


def test_the_leaf_rounded_once_passes_with_the_same_comment(tmp_path, pa):
    good = _paper(tmp_path / "good", "% src: $RUN6/report.json tables.aggregate brier 0.05385\nThe Brier score is 0.0538 on 13,247 rows.\n")
    assert pa.number_audit(*good).unmatched == []


def test_a_derived_number_that_no_leaf_carries_still_passes_on_its_comment(tmp_path, pa):
    paper, run = _paper(tmp_path, "% src: $RUN6/report.json 13247 minus 988 = 12259\nThe other rows number 12,259.\n")
    assert pa.number_audit(paper, run).unmatched == []
