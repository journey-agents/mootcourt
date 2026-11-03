"""T-039 contracts: the documentation site builds without warnings, every page carries the boundary sentence once, the CLI page is current."""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = "A precedent forecast is an argument about what to expect, not a replacement for running the experiment."
HAS_MKDOCS = importlib.util.find_spec("mkdocs") is not None and importlib.util.find_spec("material") is not None
needs_mkdocs = pytest.mark.skipif(not HAS_MKDOCS, reason="the docs extra is not installed")


def _config_text():
    return (ROOT / "mkdocs.yml").read_text(encoding="utf-8")


def test_mkdocs_config_names_the_material_theme_and_the_footer_sentence():
    text = _config_text()
    assert "name: material" in text and "strict: true" in text and f"copyright: {SENTENCE}" in text
    assert "mkdocstrings" in text and "superpowers/" in text            # the design spec is not published


def test_every_nav_entry_is_a_file_and_the_required_topics_are_present():
    nav = _config_text().split("\nnav:\n", 1)[1]
    files = re.findall(r":\s+([\w/.-]+\.md)\s*$", nav, re.M)         # plain text parse: the base install has no yaml reader
    assert files and all((ROOT / "docs" / f).is_file() for f in files), [f for f in files if not (ROOT / "docs" / f).is_file()]
    for needed in ("quickstart.md", "concepts.md", "faq.md", "landscape.md", "method.md", "limitations.md", "reference/cli.md", "reference/config.md",
                   "reference/api.md", "simulators.md", "benchmark.md", "operations.md", "howto/bring-a-ledger.md", "howto/serve-and-mcp.md"):
        assert needed in files, needed


def test_concepts_page_defines_the_required_terms():
    text = (ROOT / "docs" / "concepts.md").read_text(encoding="utf-8")
    for term in ("Ledger", "Cell", "Origin", "Ladder", "Abstention", "Card", "Harness", "Gates", "Decision value"):
        assert f"## {term}" in text, term


def test_the_sentence_is_in_the_config_and_in_no_page_body():
    for md in (ROOT / "docs").rglob("*.md"):
        if "superpowers" in md.parts or md.name.startswith("._"):
            continue
        assert SENTENCE not in md.read_text(encoding="utf-8"), f"{md} repeats the footer sentence"


def test_the_cli_reference_is_current():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_cli_docs.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    text = (ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    for cmd in ("backtest", "benchmark", "card", "doctor", "earn-weight", "fit", "ingest", "init", "join", "mcp", "promote", "serve", "simulators"):
        assert f"`moot {cmd}`" in text, cmd


@needs_mkdocs
def test_the_site_builds_with_warnings_as_errors_and_each_page_has_one_footer(tmp_path):
    r = subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict", "-d", str(tmp_path / "site")], capture_output=True, text=True,
                       cwd=ROOT, env={"NO_MKDOCS_2_WARNING": "1", "PATH": "/usr/bin:/bin"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARNING" not in r.stdout + r.stderr
    pages = [p for p in (tmp_path / "site").rglob("index.html") if "404" not in p.name]
    assert len(pages) >= 14
    for page in pages:
        assert page.read_text(encoding="utf-8").count(SENTENCE) == 1, page
    api = (tmp_path / "site" / "reference" / "api" / "index.html").read_text(encoding="utf-8")
    assert "read_ledger" in api and "build_card" in api and "run_report_card" in api       # generated from the docstrings
