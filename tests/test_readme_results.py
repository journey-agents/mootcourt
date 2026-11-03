"""T-023 contracts: README, DATA.md and docs content, generated results block."""
import importlib.util
import re
from pathlib import Path

import pytest
from conftest import real_paths

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- moot-results:start -->", "<!-- moot-results:end -->"


def _read(rel):
    path = ROOT / rel
    assert path.exists(), f"{rel} must exist"
    return path.read_text(encoding="utf-8")


def test_first_screen_has_tagline_boundary_and_transfer_caveat(spec_boundary_sentence):
    readme = _read("README.md")
    first = "\n".join(readme.splitlines()[:40])
    assert spec_boundary_sentence in first
    assert re.search(r"headline tests.{0,80}(do|does) not transfer.{0,60}product deployments", first, re.I | re.S)
    assert readme.find(START) == -1 or readme.find(START) > readme.find(spec_boundary_sentence)


def test_results_block_has_the_required_tables_and_figures():
    readme = _read("README.md")
    assert START in readme and END in readme
    block = readme.split(START, 1)[1].split(END, 1)[0]
    for col in ("n", "log score", "Brier skill", "decidable", "coverage", "abstention rate"):
        assert re.search(col, block, re.I), f"results table lacks column {col}"
    for needle in ("Upworthy", "ASOS", "synthetic", "reliability", "decision value"):
        assert needle.lower() in block.lower(), f"results block lacks {needle}"
    assert re.search(r"!\[[^\]]*\]\(reports/figures/[^)]+\.png\)", readme)


@pytest.mark.realdata
def test_results_block_is_regenerated_exactly_from_report_json():
    script = ROOT / "scripts" / "render_readme_results.py"
    assert script.exists()
    spec = importlib.util.spec_from_file_location("render_readme_results", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    readme = _read("README.md")
    block = readme.split(START, 1)[1].split(END, 1)[0]
    assert mod.render_block(real_paths().reports).strip() == block.strip()


def test_readme_sections_and_commands():
    readme = _read("README.md")
    low = readme.lower()
    for cmd in ("make data", "make fit", "make backtest", "moot card", "moot serve", "moot mcp"):
        assert cmd in readme, f"quickstart lacks {cmd}"
    assert "--challenger gbm" in readme and "gradient" in low
    assert re.search(r"what (this|it|the project) (does|do) not show", low)
    assert "no auth" in low or "no authentication" in low
    assert "never loaded from downloads" in low or "local artifacts" in low


def test_data_md_sources_licenses_and_citations():
    data = _read("DATA.md")
    for needle in ("CC BY 4.0", "Cornell", "Matias", "10.1038/s41597-021-00934-7", "2111.10198",
                   "checksum", "admission", "contrast"):
        assert needle.lower() in data.lower(), f"DATA.md lacks {needle}"


def test_method_and_operations_docs():
    method = _read("docs/method.md").lower()
    for needle in ("partial pooling", "random-effects", "top-m", "7-day", "circular"):
        assert needle in method, f"method.md lacks {needle}"
    ops = _read("docs/operations.md").lower()
    for needle in ("nightly", "weekly", "drift", "join", "fit"):
        assert needle in ops, f"operations.md lacks {needle}"


def _word(*codes):
    return "".join(map(chr, codes))


def test_no_reader_naming_or_personal_process_wording():
    # The published pages are held to both tiers of the writing rules by digest (REV-050), and to a few stems that are not in the
    # digest files. Every word below is built with chr() so this file passes the scan it enforces, and the match runs on tokens,
    # so a word split over a line break or written in camelCase is found too.
    from test_writing_rules import load_digests, load_restricted, scan_text, tokens_of

    digests, restricted = load_digests(), load_restricted()
    hiring, recruit = _word(104, 105, 114, 105, 110, 103), _word(114, 101, 99, 114, 117, 105, 116)
    applying, application = _word(97, 112, 112, 108, 121, 105, 110, 103), _word(97, 112, 112, 108, 105, 99, 97, 116, 105, 111, 110)
    for rel in ("README.md", "DATA.md", "docs/method.md", "docs/operations.md"):
        text = _read(rel)
        assert scan_text(text, {"role", "tokens"}, digests, restricted) == [], rel
        words = [w for w, _n, _whole in tokens_of(text)]
        assert hiring not in words and not [w for w in words if w.startswith(recruit)], rel
        pairs = list(zip(words, words[1:], strict=False))
        assert (applying, "for") not in pairs and ("job", application) not in pairs, rel
