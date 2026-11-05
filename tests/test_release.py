"""T-036 contracts: packaging, CI, Docker and release hygiene."""
import importlib.util
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PROJECT = PYPROJECT["project"]


def _load_release_check():
    spec = importlib.util.spec_from_file_location("release_check", ROOT / "scripts" / "release_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pyproject_is_release_ready():
    assert PROJECT["name"] == "mootcourt" and PROJECT["version"] == "1.0.0" and PROJECT["requires-python"] == ">=3.11"
    assert PROJECT["authors"][0]["name"] == "Yingjie Li" and "@" in PROJECT["authors"][0]["email"]
    assert PROJECT["license"]["text"] == "MIT" and "MIT" in (ROOT / "LICENSE").read_text(encoding="utf-8")[:40]
    assert "License :: OSI Approved :: MIT License" in PROJECT["classifiers"]
    for v in ("3.11", "3.12", "3.13"):
        assert f"Programming Language :: Python :: {v}" in PROJECT["classifiers"]
    assert any(c.startswith("Development Status") for c in PROJECT["classifiers"]) and len(PROJECT["keywords"]) >= 5
    assert PROJECT["readme"] == "README.md" and PROJECT["description"]
    assert PROJECT["scripts"]["moot"] == "mootcourt.cli:app"
    extras = PROJECT["optional-dependencies"]
    assert {"dev", "docs", "simulators"} <= set(extras)
    assert any(d.startswith("mkdocs-material") for d in extras["docs"]) and any(d.startswith("mkdocstrings") for d in extras["docs"])


def test_the_version_is_stated_once_and_semantic():
    assert re.fullmatch(r"\d+\.\d+\.\d+", PROJECT["version"])
    assert _load_release_check().check_versions() is None
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "semantic versioning" in changelog.lower() and f"## [{PROJECT['version']}]" in changelog
    assert "semantic versioning" in (ROOT / "docs" / "release.md").read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("name", ["CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "LICENSE", "Dockerfile", ".dockerignore",
                                  "mkdocs.yml", "docs/release.md", "scripts/release_check.py", ".github/workflows/ci.yml"])
def test_release_files_exist_and_are_not_empty(name):
    p = ROOT / name
    assert p.is_file() and len(p.read_text(encoding="utf-8").strip()) > 80, name


def test_the_workflow_runs_every_required_check():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for needle in ("ruff check", "pytest", '"3.11"', '"3.12"', '"3.13"', "tests/test_writing_rules.py", "uv build", "mkdocs build --strict",
                   "pull_request", "permissions:", "contents: read"):
        assert needle in text, needle
    assert 'MOOTCOURT_DATA_ROOT: ""' in text, "the tests run with no data root"
    assert not re.search(r"download_data|moot ingest --source|curl |wget ", text), "no job fetches data"
    # the docker job was added for REV-028 of the chunk E review
    assert re.findall(r"^  ([a-z-]+):$", text.split("jobs:", 1)[1], re.M) == ["lint", "test", "writing-rules", "build", "docs", "docker"]


def test_the_dockerfile_runs_as_a_non_root_user_with_the_data_root_as_a_volume():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    user = [ln for ln in lines if ln.startswith("USER ")]
    assert user and user[-1] != "USER root" and "USER 0" not in user[-1]
    assert any(ln.startswith("VOLUME") and "/data" in ln for ln in lines)
    assert any("MOOTCOURT_DATA_ROOT=/data" in ln for ln in lines)
    assert lines[-1] == 'CMD ["moot", "doctor"]'
    assert not re.search(r"FROM\s+\S+:latest|FROM\s+[^:\s]+\s*$", text, re.M), "base images are pinned to a tag"
    assert "apt-get" not in text and "curl" not in text and "ADD http" not in text
    assert (ROOT / ".dockerignore").read_text(encoding="utf-8").count("\n") > 5


def test_make_targets_for_docs_docker_and_release():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("docs:", "docker-check:", "release-check:", "build:"):
        assert re.search(rf"^{re.escape(target)}", mk, re.M), target
    assert "mkdocs build --strict" in mk and "docker build" in mk and "scripts/release_check.py" in mk
    # the shell variable wins over the untracked .env file
    assert "ifndef MOOTCOURT_DATA_ROOT" in mk


def test_the_release_page_holds_the_checklist_and_states_what_was_not_run():
    text = (ROOT / "docs" / "release.md").read_text(encoding="utf-8")
    for needle in ("make release-check", "make docker-check", "uv build", "make docs", "moot doctor", "non-root", "not running"):
        assert needle in text, needle


def test_release_check_script_reports_a_missing_file(tmp_path, monkeypatch):
    mod = _load_release_check()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    assert "missing" in mod.check_files()
