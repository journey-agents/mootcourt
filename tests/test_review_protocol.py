"""Convergence plan Task 2: the closed review rubric and the amended review protocol.

Two checks on committed text, each a regex or substring pass over one Markdown file:
  * ``paper/reviews/rubric.md`` has one section per reviewer role R1 to R6 with at least eight items each, every item a line of the
    form ``- [Rk.n] <check> <severity>``, and states the rule that a finding naming no claim id and no rubric id is a suggestion;
  * ``paper/reviews/protocol.md`` states the three convergence rules: a finding names the claim it weakens or the rubric item it
    fails, the same six reviewers continue across rounds, and the loop is capped at two further rounds after round 01.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBRIC = ROOT / "paper" / "reviews" / "rubric.md"
PROTOCOL = ROOT / "paper" / "reviews" / "protocol.md"


def test_rubric_has_six_roles_with_at_least_eight_items_each():
    text = RUBRIC.read_text(encoding="utf-8")
    for k in range(1, 7):
        ids = re.findall(rf"^- \[R{k}\.(\d+)\]", text, flags=re.M)
        assert len(ids) >= 8, k
    assert "names no claim id and no rubric id is a suggestion" in text


def test_protocol_states_the_three_convergence_rules():
    text = PROTOCOL.read_text(encoding="utf-8")
    assert "names the claim it weakens or the rubric item it fails" in text
    assert "The same six reviewers continue" in text
    assert "at most two further rounds" in text
