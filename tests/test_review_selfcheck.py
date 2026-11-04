"""Task 4: the self-check gate that must be green before a review round is dispatched."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"pending-markers", "number-audit", "source-resolution", "writing-rules", "forbidden-terms", "paper-builds", "tables-byte-identical",
         "docs-current", "claims-audit", "release-check"}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sc():
    return _load("review_selfcheck")


@pytest.fixture(scope="module")
def pa():
    return _load("paper_audit")


@pytest.fixture()
def tmp_repo(tmp_path):
    """A bare repository skeleton: a paper folder with one run folder and nothing else, so every heavy check fails fast."""
    (tmp_path / "paper" / "sections").mkdir(parents=True)
    (tmp_path / "paper" / "tables").mkdir()
    (tmp_path / "paper" / "data" / "run1").mkdir(parents=True)
    (tmp_path / "paper" / "main.tex").write_text("\\documentclass{article}\n")
    return tmp_path


def _item(report, name):
    return next((ok, detail) for n, ok, detail in report.items if n == name)


def test_a_pending_marker_fails_the_selfcheck(tmp_repo, sc):
    (tmp_repo / "paper/sections/x.tex").write_text("% PENDING-T999\n")
    report = sc.run_selfcheck(tmp_repo)
    assert report.ok is False
    ok, detail = _item(report, "pending-markers")
    assert ok is False and "x.tex:1" in detail


def test_no_pending_marker_passes_that_item(tmp_repo, sc):
    (tmp_repo / "paper/sections/x.tex").write_text("Text.\n")
    assert _item(sc.run_selfcheck(tmp_repo), "pending-markers")[0] is True


def test_report_lists_every_item_with_its_status(tmp_repo, sc):
    report = sc.run_selfcheck(tmp_repo)
    names = [name for name, _, _ in report.items]
    assert NAMES <= set(names) and len(names) == len(set(names)), "every check runs once and none short-circuits"
    assert report.ok is False
    for name in NAMES:
        assert f"`{name}`" in report.markdown or name in report.markdown
    assert _item(report, "claims-audit") == (False, "claims register missing")


def test_a_failing_item_does_not_stop_the_others(tmp_repo, sc, monkeypatch):
    def boom(repo):
        raise RuntimeError("exploded")

    monkeypatch.setattr(sc, "check_pending_markers", boom)
    report = sc.run_selfcheck(tmp_repo)
    assert _item(report, "pending-markers")[0] is False and "exploded" in _item(report, "pending-markers")[1]
    assert len(report.items) >= len(NAMES)


def test_main_exits_nonzero_when_an_item_fails_and_writes_the_report(tmp_repo, sc, capsys):
    (tmp_repo / "paper/sections/x.tex").write_text("% PENDING-T999\n")
    code = sc.main(["--repo", str(tmp_repo), "--date", "2026-11-04"])
    assert code == 1
    out = tmp_repo / ".claude" / "fleet" / "selfcheck-2026-11-04.md"
    assert out.is_file() and "pending-markers" in out.read_text()
    assert "FAIL" in capsys.readouterr().out


# ---------------------------------------------------------------------------------------------------- paper_audit
def _paper(tmp_path: Path, tex: str, table: str | None = None) -> tuple[Path, Path]:
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    (paper / "tables").mkdir()
    run = paper / "data" / "run9"
    run.mkdir(parents=True)
    (run / "report.json").write_text('{"tables": {"aggregate": [{"logscore": -0.8566, "n": 13247}]}}')
    (paper / "main.tex").write_text("\\input{sections/a}\n")
    (paper / "sections" / "a.tex").write_text(tex)
    if table:
        (paper / "tables" / "t.tex").write_text(table)
    return paper, run


def test_number_audit_matches_a_number_to_its_report(tmp_path, pa):
    paper, run = _paper(tmp_path, "% src: $RUN6/report.json tables.aggregate logscore -0.8566 n 13247\nThe score is minus 0.857 on 13,247 rows.\n")
    res = pa.number_audit(paper, run)
    assert res.unmatched == [] and res.checked == 2


def test_number_audit_lists_a_number_no_source_carries(tmp_path, pa):
    paper, run = _paper(tmp_path, "% src: $RUN6/report.json logscore -0.8566\nThe score is 0.857 on 4,321 rows.\n")
    res = pa.number_audit(paper, run)
    assert [u[2] for u in res.unmatched] == ["4,321"]


def test_source_resolution_flags_a_path_that_does_not_exist(tmp_path, pa):
    paper, run = _paper(tmp_path, "% src: $RUN6/report.json and $RUN6/missing.json\nText 0.5.\n")
    res = pa.source_resolution(paper, run)
    assert res.unresolved and "missing.json" in res.unresolved[0][3][0]
    paper, run = _paper(tmp_path / "ok", "% src: $RUN6/report.json\nText.\n")
    assert pa.source_resolution(paper, run).unresolved == []


def test_claims_audit_item_reads_the_register_when_it_exists(tmp_repo, sc):
    import json

    (tmp_repo / "paper/data/run1/report.json").write_text(json.dumps({"header": {"scored_rows": 13247}}))
    reg = tmp_repo / "paper" / "reviews"
    reg.mkdir()
    head = "| id | section | sentence | report path | key path | printed value | interval kind | status |\n|---|---|---|---|---|---|---|---|\n"
    (reg / "claims.md").write_text(head + "| C1 | 6 | s | report.json | header.scored_rows | 13,247 | none | supported |\n")
    assert _item(sc.run_selfcheck(tmp_repo), "claims-audit") == (True, "1 claims, 0 failing")
    (reg / "claims.md").write_text(head + "| C1 | 6 | s | report.json | header.scored_rows | 13,248 | none | supported |\n")
    ok, detail = _item(sc.run_selfcheck(tmp_repo), "claims-audit")
    assert ok is False and "C1" in detail
