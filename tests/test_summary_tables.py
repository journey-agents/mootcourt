"""Every results table of the paper is generated: a hand-typed tabular must be listed, with its reason, in HAND_TYPED,
and each summary table's numbers trace to report keys."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RUN = PAPER / "data" / "run8-randomization-window"
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
        assert (f"tables/{name}" in tex) != (name in st.NOT_INPUT_YET), name
        text = (tmp_path / f"{name}.tex").read_text(encoding="utf-8")
        assert text == (PAPER / "tables" / f"{name}.tex").read_text(encoding="utf-8"), f"{name}: the committed table is stale"
        assert "% src: $RUN6/" in text or name in {"fmt-app-driver", "fmt-app-syn-truth"}, name


def test_a_missing_report_key_stops_the_build_rather_than_printing_a_blank():
    import pytest

    rep = st.Report("x.json", {"tables": {}})
    with pytest.raises(KeyError):
        st.v(rep, "tables.aggregate[cell=ALL].brier_skill")
