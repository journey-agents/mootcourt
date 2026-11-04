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
    # The generated block moved from the README to docs/results.md when the README became a reader's entry point (T-053); its figure links
    # are relative to that page and the figures are copied to docs/figures.
    readme = _read("docs/results.md")
    assert START in readme and END in readme
    assert START not in _read("README.md")
    block = readme.split(START, 1)[1].split(END, 1)[0]
    for col in ("n", "log score", "Brier skill", "decidable", "coverage", "abstention rate"):
        assert re.search(col, block, re.I), f"results table lacks column {col}"
    for needle in ("Upworthy", "ASOS", "synthetic", "reliability", "decision value"):
        assert needle.lower() in block.lower(), f"results block lacks {needle}"
    links = re.findall(r"!\[[^\]]*\]\((figures/[^)]+\.png)\)", readme)
    assert links and all((ROOT / "docs" / link).is_file() for link in links)


@pytest.mark.realdata
def test_results_block_is_regenerated_exactly_from_report_json():
    script = ROOT / "scripts" / "render_readme_results.py"
    assert script.exists()
    spec = importlib.util.spec_from_file_location("render_readme_results", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    readme = _read("docs/results.md")
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


# ----------------------------------------------------------------------------------- T-055: the renderer on the chunk L report layout
def test_the_sentence_that_each_rung_generalizes_the_one_below_is_replaced_by_what_each_rung_adds():
    for rel in ("README.md", "docs/results.md", "docs/concepts.md"):
        text = _read(rel)
        assert "generalizes the one below" not in text and "generalization of the one below" not in text, rel
    results = _read("docs/results.md")
    assert "P1 adds a fitted partially pooled Student-t prior" in results
    assert "P2 adds kernel-weighted precedents under an admission guard" in results
    assert re.search(r"P2 adds kernel-weighted precedents", _read("README.md")), "the README says what each rung adds"


def test_the_results_block_carries_the_chunk_l_tables():
    block = _read("docs/results.md").split(START, 1)[1].split(END, 1)[0]
    for needle in ("Challengers, Upworthy", "GBM+cal", "Positive control, synthetic", "Admission and the exposure proxy", "Weekly replay",
                   "realized over planned standard error", "difference from random order", "Bonferroni-adjusted", "percentile, clustered null",
                   "tests for skill 0.20", "base rate", "+p2-guard-off", "admission-prelaunch", "Tests: ", "P2 admission guard: ",
                   "weight on precedents forced to 0.5"):
        assert needle in block, f"the results block lacks {needle!r}"
    assert "95 percent bootstrap interval for the Brier gain clears zero, base rate 0.3" not in block
    assert "reports/challengers" not in block
    assert "zero by construction" in block                                  # P0's Brier skill is never read as a deficit
    assert "-0.1237" not in block


def test_the_renderer_filters_decision_value_to_one_budget_and_the_challengers_come_from_the_main_report():
    spec = importlib.util.spec_from_file_location("render_readme_results", ROOT / "scripts" / "render_readme_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    def row(policy, rung, budget, cap, lo, hi, diff, dlo, dhi, const):
        return {"origin": "ALL", "policy": policy, "rung": rung, "budget": budget, "captured_fraction": cap, "captured_fraction_lo": lo,
                "captured_fraction_hi": hi, "diff_random": diff, "diff_random_lo": dlo, "diff_random_hi": dhi, "constant_within_cell": const}

    doc = {"header": {"primary_rung": "P2"}, "tables": {"decision_value": [
        row("random", "all", 0.1, 0.1, 0.1, 0.1, 0.0, 0.0, 0.0, None), row("random", "all", 0.25, 0.25, 0.25, 0.25, 0.0, 0.0, 0.0, None),
        row("p_win", "P2", 0.25, 0.3, 0.2, 0.4, 0.05, 0.01, 0.09, False), row("oracle", "all", 0.25, 0.7, 0.6, 0.8, 0.45, 0.4, 0.5, None)]}}
    table = "\n".join(mod.decision_table(doc))
    assert "0.1000" not in table and "0.2500" in table and "+0.0500 (+0.0100 to +0.0900)" in table
    sentence = mod.decision_sentence(doc)
    assert "a difference from random order of +0.0500" in sentence and "No interval is computed" not in sentence
    src = (ROOT / "scripts" / "render_readme_results.py").read_text(encoding="utf-8")
    assert '/ "challengers"' not in src and "challenger-gbm" not in src


@pytest.mark.realdata
def test_verify_readme_numbers_finds_no_mismatch_and_does_not_crash_on_the_chunk_l_reports():
    import subprocess
    import sys

    env = dict(__import__("os").environ, MOOTCOURT_DATA_ROOT=str(real_paths().root))
    cmd = [sys.executable, str(ROOT / "scripts" / "verify_readme_numbers.py")]
    done = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)
    assert done.returncode == 0, done.stdout[-1500:] + done.stderr[-1500:]
    assert re.search(r"total checked \d+, mismatches 0", done.stdout)
    assert "not checked (no table handler)" not in done.stdout


@pytest.mark.realdata
def test_render_readme_results_check_passes_for_the_page_and_the_headline():
    import subprocess
    import sys

    env = dict(__import__("os").environ, MOOTCOURT_DATA_ROOT=str(real_paths().root))
    cmd = [sys.executable, str(ROOT / "scripts" / "render_readme_results.py"), "--check"]
    done = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_renderer_checks_every_marker_before_it_writes_anything(tmp_path):
    page, front = tmp_path / "page.md", tmp_path / "front.md"
    page.write_text("x\n" + START + "\nold\n" + END + "\n", encoding="utf-8")
    front.write_text("no markers here\n", encoding="utf-8")
    import subprocess
    import sys

    cmd = [sys.executable, str(ROOT / "scripts" / "render_readme_results.py"), "--write", "--page", str(page), "--front", str(front),
           "--reports-dir", str(tmp_path / "no-reports")]
    done = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 2 and "lacks the" in done.stderr
    assert "old" in page.read_text(encoding="utf-8"), "the page was rewritten although the other file lacks its markers"
