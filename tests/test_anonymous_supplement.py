"""The anonymized supplement for a double-blind venue: what goes in, what is rewritten, and the check that stops the build."""
from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("anonymous_supplement", ROOT / "scripts" / "anonymous_supplement.py")
supplement = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(supplement)

COMMIT = "87163a63ec24ae5e7699ddb4697aea8eb1a0e52a"
COMMITS = frozenset({COMMIT})
NAME, PACKAGE, HOST = "Moot" + " Court", "moot" + "court", "git" + "hub.com"          # split so this file names none of them whole


def test_code_reports_plans_and_the_registration_go_in_and_identity_files_stay_out():
    for path in ("src/" + PACKAGE + "/cli.py", "scripts/simulated_readers.py", "tests/test_registry.py", "docs/confirmatory-registration.md",
                 "docs/superpowers/plans/a.md", "paper/data/run9-visible-exposure/README.md", "paper/summary_tables/readers.py",
                 "paper/build_tables.py", "pyproject.toml", "uv.lock", "Makefile", "DATA.md"):
        assert supplement.included(path), path
    for path in ("README.md", "LICENSE", "CITATION.cff", "CHANGELOG.md", "CLAUDE.md", "CONTRIBUTING.md", ".github/workflows/ci.yml",
                 "paper/main.tex", "paper/sections/results.tex", "paper/reviews/claims.md", "paper/dist/metadata.md",
                 "paper/references.bib", "paper/tmlr/preamble.tex", "mkdocs.yml", "scripts/anonymous_supplement.py",
                 "tests/test_anonymous_supplement.py", "scripts/tmlr_build.py", "tests/test_tmlr_build.py"):
        assert not supplement.included(path), path


def test_the_package_name_is_replaced_in_paths_and_in_text():
    assert supplement.anonymous_path("src/" + PACKAGE + "/cli.py") == "src/anontool/cli.py"
    assert supplement.anonymous_path(PACKAGE + ".toml") == "anontool.toml"
    text = supplement.scrub(f"{NAME} is the package {PACKAGE}; set {PACKAGE.upper()}_DATA_ROOT and run `moot backtest`.", COMMITS)
    assert text == "AnonTool is the package anontool; set ANONTOOL_DATA_ROOT and run `anontool backtest`."


def test_links_to_the_repository_the_archive_and_the_registry_are_withheld():
    text = supplement.scrub(f"See https://{HOST}/some-org/{PACKAGE}/pull/22 and https://osf.io/jf5ds and DOI 10.5281/zenodo.23988587. "
                            "Write to someone@example.org.", COMMITS)
    assert text == "See (link withheld) and (link withheld) and DOI (identifier withheld). Write to withheld@example.invalid."


def test_the_registry_pages_of_the_public_archives_are_kept():
    text = "The archive is at https://osf.io/jd64p/ and its files are listed through https://api.osf.io/v2/."
    assert supplement.scrub(text, COMMITS) == text


def test_the_names_in_the_project_metadata_are_withheld_wherever_they_appear(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nauthors = [{ name = "Ada Lovelace", email = "ada@example.org" }]\n')
    names = supplement.people(tmp_path)
    assert names == ("Ada Lovelace",)
    text = supplement.scrub('name = "Ada Lovelace"; user adalovelace wrote it; Ada is short, so the word alone stays', COMMITS, names)
    assert text == 'name = "(name withheld)"; user (name withheld) wrote it; Ada is short, so the word alone stays'


def test_a_commit_of_the_repository_is_withheld_and_other_digests_are_kept():
    snapshot, checksum = "2dc461f52ea4", "16388af7895ad7d18b7187b5b72267bfd798cb8e4f5cb1ee1e460d6eaa8ddf8d"
    text = supplement.scrub(f"commit {COMMIT} ({COMMIT[:7]}), snapshot {snapshot}, SHA-256 {checksum}, 1234567 rows", COMMITS)
    assert text == f"commit (commit withheld) ((commit withheld)), snapshot {snapshot}, SHA-256 {checksum}, 1234567 rows"


def test_a_file_that_still_names_the_project_is_reported():
    assert supplement.identity_hits("docs/a.md", b"nothing to see") == []
    assert supplement.identity_hits("docs/a.md", ("built by the " + PACKAGE + " team").encode()) != []
    assert supplement.identity_hits("src/" + PACKAGE + "/a.py", b"x = 1") != []          # the path counts too
    assert supplement.identity_hits("a.png", b"\x89PNG " + HOST.encode() + b"/x") != []          # and so does a binary file


def _tree(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / "repo" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path / "repo"


def test_the_archive_holds_the_rewritten_files_a_note_and_nothing_else(tmp_path):
    repo = _tree(tmp_path, {"src/" + PACKAGE + "/cli.py": f"import {PACKAGE}\n", "README.md": "who we are\n",
                            "docs/confirmatory-registration.md": f"Registered at https://osf.io/jf5ds from commit {COMMIT[:9]}.\n"})
    out = supplement.build(repo, tmp_path / "out.zip", files=["src/" + PACKAGE + "/cli.py", "README.md", "docs/confirmatory-registration.md"],
                           commits=COMMITS)
    with zipfile.ZipFile(out) as z:
        names = sorted(z.namelist())
        assert names == ["supplement/README.md", "supplement/docs/confirmatory-registration.md", "supplement/src/anontool/cli.py"]
        assert z.read("supplement/src/anontool/cli.py") == b"import anontool\n"
        assert z.read("supplement/docs/confirmatory-registration.md") == b"Registered at (link withheld) from commit (commit withheld).\n"
        assert b"who we are" not in z.read("supplement/README.md") and b"withheld" in z.read("supplement/README.md")
        assert {info.date_time for info in z.infolist()} == {(1980, 1, 1, 0, 0, 0)}          # no time of the build in the archive


def test_a_name_the_rewriting_does_not_know_stops_the_build_and_leaves_no_archive(tmp_path):
    word = supplement.FORBIDDEN[0]
    repo = _tree(tmp_path, {"docs/a.md": f"thanks to {word} for the idea\n"})
    with pytest.raises(SystemExit, match="docs/a.md"):
        supplement.build(repo, tmp_path / "out.zip", files=["docs/a.md"], commits=COMMITS)
    assert not (tmp_path / "out.zip").exists()
