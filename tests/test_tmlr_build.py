"""The anonymized single-column version is assembled from the paper's one set of sources (``scripts/tmlr_build.py``, ``make tmlr``).

These tests build a small paper folder and check the four things the script does: the preamble and the abstract are replaced, marked
blocks move to the start of the appendix with their stub left behind, comment lines are dropped, and a file that would still typeset the
author, the repository, a release or a commit is refused. The last test assembles the real sources, so a named string that enters the
paper without its anonymous branch fails here.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tmlr_build", ROOT / "scripts" / "tmlr_build.py")
tb = importlib.util.module_from_spec(_spec)
sys.modules["tmlr_build"] = tb
_spec.loader.exec_module(tb)

MAIN = r"""%% tmlr:preamble-begin
\documentclass[sigconf,nonacm]{acmart}
\newif\iftmlr
\begin{document}
\title{A Title}
\author{Some Name}
%% tmlr:preamble-end
%% tmlr:abstract-begin
\begin{abstract}
Long structured abstract.
\end{abstract}
\maketitle
%% tmlr:abstract-end
\section{Introduction}
% src: a path in the repository
Body text. The code is at \iftmlr the supplementary material\else https://github.com/someone/repo\fi.
\input{sections/results}
\bibliographystyle{ACM-Reference-Format}
\bibliography{references}
\input{sections/appendix}
\end{document}
"""
RESULTS = r"""\section{Results}
Kept in the body.
%% tmlr:move-begin sizing
%% tmlr:stub sizing Sizing is reported in Appendix~\ref{sec:sizing}.
\subsection{Sizing}
\label{sec:sizing}
\paragraph{Detail.} Moved text.
%% tmlr:move-end sizing
After the block.
"""
APPENDIX = "\\clearpage\n\\appendix\n\\section{Tables}\nAppendix text.\n"


@pytest.fixture
def paper(tmp_path, monkeypatch):
    monkeypatch.setattr(tb, "SIDEWAYS", ())          # the small paper has no wide table
    (tmp_path / "sections").mkdir()
    (tmp_path / "tmlr").mkdir()
    (tmp_path / "main.tex").write_text(MAIN)
    (tmp_path / "sections" / "results.tex").write_text(RESULTS)
    (tmp_path / "sections" / "appendix.tex").write_text(APPENDIX)
    (tmp_path / "sections" / "abstract-tmlr.tex").write_text("% src: a report key\nOne paragraph.\n")
    preamble = "\\documentclass{article}\n\\newif\\iftmlr\n\\tmlrtrue\n\\title{@@TITLE@@}\n\\begin{document}\n\\maketitle\n"
    (tmp_path / "tmlr" / "preamble.tex").write_text(preamble)
    return tmp_path


def test_the_preamble_and_abstract_are_replaced_and_the_title_is_carried_over(paper):
    text = tb.assemble(paper)
    assert text.startswith("\\documentclass{article}")
    assert "\\title{A Title}" in text and "acmart" not in text and "Some Name" not in text
    assert "\\begin{abstract}\nOne paragraph.\n\\end{abstract}" in text and "Long structured abstract" not in text
    assert text.count("\\maketitle") == 1


def test_a_marked_block_moves_to_the_start_of_the_appendix_and_leaves_its_stub(paper):
    text = tb.assemble(paper)
    body, appendix = text.split("\\appendix\n")
    assert "Sizing is reported in Appendix~\\ref{sec:sizing}." in body and "Moved text." not in body
    assert "Kept in the body." in body and "After the block." in body
    assert appendix.index("\\section{Sizing}") < appendix.index("\\section{Tables}")          # promoted, and before the old appendix
    assert "\\paragraph{Detail.} Moved text." in appendix and "\\subsection{Sizing}" not in text
    assert "tmlr:" not in text


def test_comment_lines_are_dropped_and_the_bibliography_style_is_swapped(paper):
    text = tb.assemble(paper)
    assert "% src" not in text and "repository" not in text
    assert "\\bibliographystyle{plainnat}" in text and "ACM-Reference-Format" not in text


def test_a_named_string_outside_its_anonymous_branch_is_refused(paper):
    main = paper / "main.tex"
    main.write_text(main.read_text().replace("Body text.", "Body text by Yingjie."))
    with pytest.raises(ValueError, match="would show identity"):
        tb.assemble(paper)


def test_the_named_branch_of_a_conditional_is_allowed_and_a_split_conditional_is_not(paper):
    assert tb.check_anonymous("see \\iftmlr the supplement\\else https://github.com/x/y\\fi now") == []
    with pytest.raises(ValueError, match="without its"):
        tb.strip_named_branches("see \\iftmlr the supplement\\else https://github.com/x/y\nnext line\\fi")


def test_an_unclosed_or_mismatched_move_block_is_an_error():
    with pytest.raises(ValueError, match="not closed"):
        tb.move_blocks(["%% tmlr:move-begin a", "x"])
    with pytest.raises(ValueError, match="does not close"):
        tb.move_blocks(["%% tmlr:move-begin a", "x", "%% tmlr:move-end b"])


def test_the_real_sources_assemble_into_a_file_that_shows_no_identity():
    text = tb.assemble(ROOT / "paper")
    assert tb.check_anonymous(text) == []
    assert "\\author{Anonymous authors" in text
    assert text.count("\\begin{abstract}") == 1 and text.count("\\appendix") == 1
    assert "tmlr:" not in text.replace("tmlr/tmlr", "")


def test_floats_are_placed_where_cited_and_tables_only_shrink():
    text = ("\\begin{table}[t]\n\\resizebox{\\columnwidth}{!}{\\input{tables/a}}\n\\end{table}\n"
            "\\begin{table*}[tp]\n\\input{tables/b-c}\n\\end{table*}\n")
    out = tb.single_column_layout(text)
    assert "\\begin{table}[!htbp]" in out and "\\begin{table*}[!htbp]" in out and "[t]" not in out
    assert "\\resizebox" not in out and out.count("\\adjustbox{max width=\\textwidth}{\\input{tables/") == 2


def test_a_named_wide_table_is_set_on_a_turned_page(monkeypatch):
    monkeypatch.setattr(tb, "SIDEWAYS", ("tab:wide",))
    text = ("\\begin{table*}[!htbp]\\centering\n\\caption{C}\n\\label{tab:wide}\n\\adjustbox{max width=\\textwidth}{X}\n\\end{table*}\n"
            "\\begin{table}[!htbp]\n\\label{tab:other}\n\\adjustbox{max width=\\textwidth}{Y}\n\\end{table}\n")
    out = tb.turn_wide_tables(text)
    assert "\\begin{sidewaystable}\\centering" in out and "\\end{sidewaystable}" in out and "table*" not in out
    assert "\\adjustbox{max width=\\textheight}{X}" in out and "\\adjustbox{max width=\\textwidth}{Y}" in out
    monkeypatch.setattr(tb, "SIDEWAYS", ("tab:absent",))
    with pytest.raises(ValueError, match="no table carries"):
        tb.turn_wide_tables(text)


def test_the_package_name_is_withheld_and_a_surviving_name_is_refused(paper):
    out = tb.withhold_name("Moot Court runs \\texttt{moot backtest} from the package \\texttt{mootcourt}; a moot point stays.")
    assert "Moot Court" not in out and "mootcourt" not in out and "\\texttt{anontool backtest}" in out and "a moot point stays" in out
    assert tb.check_anonymous("The Moot Court package") != []
    main = paper / "main.tex"
    main.write_text(main.read_text().replace("Body text.", "Body text of Moot Court."))
    assert "AnonTool" in tb.assemble(paper)


def test_with_a_stubs_marker_the_pointer_sentences_form_one_paragraph_there(paper):
    results = paper / "sections" / "results.tex"
    results.write_text(results.read_text() + "%% tmlr:stubs-here\nLast line.\n")
    body = tb.assemble(paper).split("\\appendix\n")[0]
    assert "\\paragraph{Reported in the appendix.} Sizing is reported in Appendix~\\ref{sec:sizing}." in body
    assert body.index("After the block.") < body.index("\\paragraph{Reported in the appendix.}") < body.index("Last line.")
    assert body.count("Sizing is reported") == 1 and "tmlr:" not in body
