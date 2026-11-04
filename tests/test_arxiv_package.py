"""T-080: the arXiv source package.

``scripts/arxiv_package.py`` (``make arxiv``) packs ``main.tex``, the sections, the tables, the figure PDFs, the precompiled ``main.bbl`` (and the
``.bib`` beside it), any local class or style file, and nothing else, into ``paper/dist/arxiv-<date>.tar.gz``; its check unpacks the tarball,
drops the ``.bib`` and compiles the way arXiv does (pdflatex, the ``.bbl`` standing in for BibTeX), requiring the page count of the ordinary
build and no undefined reference. The tests run when tectonic (the paper's own builder) is on the path and skip otherwise; the pdflatex
compile runs only where pdflatex is installed.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
needs_tectonic = pytest.mark.skipif(shutil.which("tectonic") is None, reason="tectonic is not on the path")


def _script():
    spec = importlib.util.spec_from_file_location("arxiv_package_t", ROOT / "scripts" / "arxiv_package.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def built_paper(tmp_path_factory):
    """A scratch copy of the paper sources with the figures drawn from the run folder and the bibliography compiled by tectonic."""
    if shutil.which("tectonic") is None:
        pytest.skip("tectonic is not on the path")
    scratch = tmp_path_factory.mktemp("arxiv") / "paper"
    scratch.mkdir()
    for name in ("main.tex", "references.bib"):
        shutil.copy(ROOT / "paper" / name, scratch / name)
    for folder in ("sections", "tables"):
        shutil.copytree(ROOT / "paper" / folder, scratch / folder)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "paper_figures.py"), "--run", str(ROOT / "paper" / "data" / "run5-period-rule"),
                    "--out", str(scratch / "figures")], check=True, capture_output=True, text=True)
    subprocess.run(["tectonic", "-X", "compile", "--keep-intermediates", "--keep-logs", "main.tex"], cwd=scratch, check=True,
                   capture_output=True, text=True)
    assert (scratch / "main.bbl").exists() and (scratch / "main.pdf").exists()
    return scratch


@needs_tectonic
def test_the_package_holds_the_sources_the_bbl_the_tables_and_the_figures_and_nothing_else(built_paper, tmp_path):
    mod = _script()
    tarball = mod.build_package(built_paper, tmp_path / "dist", date="20261104")
    assert tarball == tmp_path / "dist" / "arxiv-20261104.tar.gz" and tarball.exists()
    with tarfile.open(tarball) as tar:
        members = tar.getmembers()
    names = sorted(m.name for m in members if m.isfile())
    assert "main.tex" in names and "main.bbl" in names and "references.bib" in names
    top = ("main.tex", "main.bbl", "references.bib")
    assert all(n in top or n.startswith(("sections/", "tables/", "figures/")) for n in names), names
    assert all(n.endswith((".tex", ".bbl", ".bib", ".pdf")) for n in names)
    assert not any(n.endswith("figures.json") or n == "main.pdf" for n in names)
    assert {n for n in names if n.startswith("sections/")} == {f"sections/{p.name}" for p in (built_paper / "sections").glob("*.tex")}
    assert {n for n in names if n.startswith("tables/")} == {f"tables/{p.name}" for p in (built_paper / "tables").glob("*.tex")}
    tex_files = [built_paper / "main.tex"] + sorted((built_paper / "sections").glob("*.tex"))
    text = "\n".join(p.read_text(encoding="utf-8") for p in tex_files)
    for target in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        assert target in names, target
    for target in re.findall(r"\\input\{([^}]+)\}", text):
        assert f"{target}.tex" in names, target
    assert all(m.uid == 0 and m.gid == 0 and m.uname == "" and m.gname == "" for m in members)
    again = mod.build_package(built_paper, tmp_path / "dist2", date="20261104")
    assert again.read_bytes() == tarball.read_bytes()          # reproducible: the same sources give the same bytes
    assert tarball.stat().st_size < 5_000_000


@needs_tectonic
def test_the_bbl_alone_resolves_every_citation_with_the_same_page_count(built_paper, tmp_path):
    mod = _script()
    tarball = mod.build_package(built_paper, tmp_path / "dist", date="20261104")
    reference = mod.pages_of(built_paper / "main.log")
    assert reference > 10
    got = mod.compile_check(tarball, tmp_path / "check", engine="tectonic")
    assert got["engine"] == "tectonic" and got["pages"] == reference and got["undefined"] == [] and got["bib_removed"] is True


@pytest.mark.skipif(shutil.which("pdflatex") is None or shutil.which("tectonic") is None, reason="pdflatex and tectonic are both needed")
def test_the_package_compiles_under_pdflatex_the_way_arxiv_does(built_paper, tmp_path):
    mod = _script()
    tarball = mod.build_package(built_paper, tmp_path / "dist", date="20261104")
    reference = mod.pages_of(built_paper / "main.log")
    got = mod.compile_check(tarball, tmp_path / "check", engine="pdflatex")
    assert got["engine"] == "pdflatex" and got["pages"] == reference and got["undefined"] == []


def test_the_makefile_has_the_arxiv_targets_and_the_dist_notes_name_the_engine():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^arxiv:", mk, re.M) and re.search(r"^arxiv-check:", mk, re.M) and "scripts/arxiv_package.py" in mk
    readme = (ROOT / "paper" / "dist" / "README-arxiv.md").read_text(encoding="utf-8")
    assert "pdflatex" in readme.lower() and "main.bbl" in readme and "TeX Live 2025" in readme
    meta = (ROOT / "paper" / "dist" / "metadata.md").read_text(encoding="utf-8")
    assert "stat.ML" in meta and "cs.LG" in meta and "stat.ME" in meta and "CC BY 4.0" in meta and "mootcourt-plan" in meta
    assert "\\" not in meta.split("## Abstract", 1)[1].split("##", 1)[0]          # the abstract is plain text
