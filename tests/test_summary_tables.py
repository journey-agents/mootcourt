"""Every results table of the paper is generated: a hand-typed tabular must be listed, with its reason, in HAND_TYPED,
and each summary table's numbers trace to report keys."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RUN = PAPER / "data" / "run9-visible-exposure"
sys.path.insert(0, str(PAPER))
import summary_tables as st  # noqa: E402


def _sources():
    return [PAPER / "main.tex", *sorted((PAPER / "sections").glob("*.tex"))]


def test_every_hand_typed_tabular_in_the_sources_is_listed_and_every_listed_one_exists():
    found = set()
    for f in _sources():
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\\begin\{tabular\}", text):
            labels = re.findall(r"\\label\{(tab:[^}]+)\}", text[: m.start()])
            found.add(labels[-1] if labels else f.name)
    assert found == set(st.HAND_TYPED), found ^ set(st.HAND_TYPED)


def test_each_summary_table_is_input_by_the_sources_and_its_number_rows_name_their_keys(tmp_path):
    cmd = [sys.executable, str(PAPER / "build_tables.py"), "--reports", str(RUN), "--out", str(tmp_path)]
    subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)
    reports = st.Reports(RUN)
    tex = "".join(f.read_text(encoding="utf-8") for f in _sources())
    names = [fn(reports).name for mod in st.group_modules() for fn in mod.TABLES]
    assert len(names) == len(set(names)) and len(names) >= 40
    for name in names:
        assert f"tables/{name}" in tex, name
        text = (tmp_path / f"{name}.tex").read_text(encoding="utf-8")
        assert text == (PAPER / "tables" / f"{name}.tex").read_text(encoding="utf-8"), f"{name}: the committed table is stale"
        assert "% src: $RUN6/" in text or name == "fmt-app-syn-truth", name


def test_a_missing_report_key_stops_the_build_rather_than_printing_a_blank():
    import pytest

    rep = st.Report("x.json", {"tables": {}})
    with pytest.raises(KeyError):
        st.v(rep, "tables.aggregate[cell=ALL].brier_skill")


def _row(table, label):
    """The one row of a built table whose first cell ends with ``label`` (the verdict rows carry a ragged-right prefix)."""
    hits = [row for row in table.rows if not isinstance(row, st.Raw) and str(row[0]).endswith(label)]
    assert len(hits) == 1, (label, len(hits))
    return hits[0]


def test_the_glance_gives_the_skill_by_quarters_without_the_zero_base_rate_pair_directly_after_the_skill_by_quarters():
    from summary_tables import front

    rows = front.glance(st.Reports(RUN)).rows
    labels = [str(row[0]) for row in rows]
    at = labels.index("P1 Brier skill, significance judged at the test's own standard error (90\\%, unadjusted)")
    assert labels[at + 1] == "the same, the seven quarters as units (90\\%)"
    assert labels[at + 2] == "the same, the seven quarters as units, without the one cell and quarter whose base rate is zero (90\\%)"
    cell = rows[at + 2][1]
    at_key = "rungs.P1.realized.origin_level_without_zero_base_rate_strata"
    assert [k.split(" ", 1)[1] for k in cell.keys] == [f"{at_key}.{leaf}" for leaf in ("skill", "lo", "hi")]
    assert re.fullmatch(r"-?\d\.\d{4} \(-?\d\.\d{4}, -?\d\.\d{4}\)", str(cell)), cell
    assert str(rows[at + 2][2]) == "not computed"


def test_a_verdict_is_failed_only_where_the_interval_lies_wholly_on_the_wrong_side_of_zero():
    import pytest
    from summary_tables import limits

    assert limits._wrong_side_word(-0.2, -0.3, -0.1) == "failed"
    assert limits._wrong_side_word(-0.2, -0.3, 0.1) == "not supported"
    assert limits._wrong_side_word(-0.2, -0.3, 0.0) == "not supported"
    with pytest.raises(ValueError):          # an estimate on the claim's side is neither word
        limits._wrong_side_word(0.2, -0.3, 0.4)

    reports = st.Reports(RUN)
    table = limits.verdicts(reports)
    up = reports(limits.UPWORTHY)
    headline, prior = limits._cell("P2", "headline_only"), limits._dv("P1")
    cases = (("H1 part 2", f"{headline}.logscore_vs_p1", f"{headline}.logscore_vs_p1_lo", f"{headline}.logscore_vs_p1_hi"),
             ("H5, prior", f"{prior}.diff_matched", f"{prior}.diff_matched_lo", f"{prior}.diff_matched_hi"))
    for label, *keys in cases:
        verdict = _row(table, label)[-1]
        word = limits._wrong_side_word(*(up.get(k) for k in keys))
        assert str(verdict).removeprefix("\\raggedright ").startswith(word), (label, verdict)
        assert [k.split(" ", 1)[1] for k in verdict.keys] == keys, label          # the word names the numbers that chose it


def test_the_direction_auc_of_a_rung_with_one_forecast_per_pair_prints_no_interval():
    from summary_tables import results_a

    table = results_a.direction(st.Reports(RUN))
    p1 = _row(table, "P1")
    assert str(p1[-1]) == "one forecast per pair"
    assert any("constant_within_cell" in k for k in p1[-1].keys) and any("exposure_strata_with_one_value" in k for k in p1[-1].keys)
    assert re.fullmatch(r"\d\.\d{3} \(\d\.\d{3}, \d\.\d{3}\)", str(_row(table, "precedent rung (P2)")[-1]))
    assert re.fullmatch(r"\d\.\d{3} \(\d\.\d{3}, \d\.\d{3}\)", str(_row(table, "text classifier")[-1]))
