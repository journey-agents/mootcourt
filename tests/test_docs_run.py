"""T-053 contracts: the documentation runs. Every command in README.md, docs/commands.md and docs/tutorials/*.md is executed
against a temporary folder, the output the pages show is the output the commands print, and the manual stays in step with the CLI
and with mootcourt.settings.

The runner is scripts/run_doc_snippets.py (which documents the tags) and the page writer and checker is
scripts/render_tutorial_outputs.py. The tutorial that needs the two public archives is skipped without them; its slow blocks run
only with MOOT_DOCS_SLOW=1.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rds = _load("run_doc_snippets")
rto = _load("render_tutorial_outputs")

TUTORIALS = sorted((ROOT / "docs" / "tutorials").glob("[0-9]*.md"))
RUN_PAGES = [ROOT / "README.md", ROOT / "docs" / "commands.md", *TUTORIALS]
ALLOWED_OPTIONS = {"exit", "needs", "slow", "quiet", "head", "expect"}
ALLOWED_LANGS = {"bash", "text", "toml", "json", "python", "sql", "mermaid", "", "bibtex", "yaml"}


def _page(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "page.md"
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------------------------------- the runner itself
def test_only_blocks_tagged_bash_run_are_executed_and_options_are_read(tmp_path):
    p = _page(tmp_path, "intro\n\n```bash\nexit 9\n```\n\n"
                        "```bash run exit=3 head=1 expect=\"a b\"\necho 'a b'; (exit 3)\n```\n\n```text output\nold\n```\n")
    blocks = rds.parse_blocks(p.read_text(encoding="utf-8"))
    assert [b.is_run for b in blocks] == [False, True, False] and blocks[2].is_output
    run = blocks[1]
    assert run.option("exit") == "3" and run.option("head") == "1" and run.options("expect") == ["a b"] and run.option("slow") is None
    fr = rds.run_file(p)
    assert [r.status for r in fr.results] == ["ok"]                      # the untagged block, which would exit 9, never ran


def test_a_block_with_the_wrong_exit_code_or_a_missing_expected_text_fails(tmp_path):
    p = _page(tmp_path, "```bash run\n(exit 4)\n```\n\n```bash run expect=\"zebra\"\necho horse\n```\n\n```bash run exit=1\necho fine; false\n```\n")
    fr = rds.run_file(p)
    assert [r.status for r in fr.results] == ["failed", "failed", "ok"]
    assert "zebra" in fr.results[1].note and "wanted 0" in fr.results[0].note


def test_the_blocks_of_a_page_share_one_session_that_starts_in_a_clean_home(tmp_path):
    p = _page(tmp_path, "```bash run\nmkdir work && cd work && export LEDGER=here && pwd | sed 's#.*/##'\n```\n\n"
                        "```bash run\necho $LEDGER $(basename $PWD) ${MOOTCOURT_DATA_ROOT:-unset}; ls ~ | tr '\\n' ' '\n```\n")
    fr = rds.run_file(p)
    assert [r.status for r in fr.results] == ["ok", "ok"]
    assert fr.results[1].output.split("\n")[0] == "here work unset" and "work" in fr.results[1].output


def test_a_command_that_reads_standard_input_does_not_swallow_the_next_block(tmp_path):
    p = _page(tmp_path, "```bash run\ncat\n```\n\n```bash run\necho second\n```\n")
    fr = rds.run_file(p)
    assert [r.status for r in fr.results] == ["ok", "ok"] and fr.results[1].output.strip() == "second"


def test_slow_and_archive_blocks_are_skipped_and_say_so(tmp_path, monkeypatch):
    monkeypatch.setattr(rds, "archives_present", lambda root=None: None)
    p = _page(tmp_path, "```bash run slow\nexit 7\n```\n\n```bash run needs=archives\nexit 7\n```\n\n```bash run\necho ok\n```\n")
    fr = rds.run_file(p)
    assert [r.status for r in fr.results] == ["skipped", "skipped", "ok"]
    assert "slow" in fr.results[0].note and "archives" in fr.results[1].note


def test_a_server_port_in_a_page_is_replaced_by_a_free_port_and_shown_as_the_documented_one(tmp_path):
    p = _page(tmp_path, "```bash run\necho listening on 127.0.0.1:8731\n```\n")
    fr = rds.run_file(p)
    assert fr.port and fr.port != "8731" and fr.results[0].output.strip() == f"listening on 127.0.0.1:{fr.port}"
    assert rds.shown_lines(fr.results[0], fr.results[0].block, fr.home, fr.port) == "listening on 127.0.0.1:8731"


def test_the_mask_hides_what_changes_between_machines_and_nothing_else():
    a = "model 57a727de0c15 snapshot 20261103-80131c793938 in 1.4 s on numpy 2.4.6; free space 13.9 GB; 309 days old; p 0.220; n 330"
    b = "model aaaaaaaaaaaa snapshot 20270101-bbbbbbbbbbbb in 9.0 s on numpy 2.5.0; free space 7.2 GB; 12 days old; p 0.220; n 330"
    assert rds.mask(a) == rds.mask(b)
    assert rds.mask("p 0.220") != rds.mask("p 0.221") and rds.mask("n 330") != rds.mask("n 331")


def test_write_then_check_agree_and_a_changed_command_makes_the_page_stale(tmp_path):
    p = _page(tmp_path, "```bash run\necho hello\n```\n\n```bash run quiet\necho unseen\n```\n\n```bash run\ntrue\n```\n")
    assert rto.compare(rds.run_file(p))[0].endswith("the page shows no output for this block (run --write)")
    fr = rds.run_file(p)
    p.write_text(rto.render(fr), encoding="utf-8")
    text = p.read_text(encoding="utf-8")
    assert "```text output\nhello\n```" in text and text.count("```text output") == 1      # the quiet and the silent block get no output block
    assert rto.compare(rds.run_file(p)) == []
    p.write_text(text.replace("echo hello", "echo goodbye"), encoding="utf-8")
    stale = rto.compare(rds.run_file(p))
    assert len(stale) == 1 and "stale" in stale[0] and "hello" in stale[0] and "goodbye" in stale[0]


# ------------------------------------------------------------------------------------------------ the pages themselves
def _tags(page: Path):
    return [b for b in rds.parse_blocks(page.read_text(encoding="utf-8"))]


@pytest.mark.parametrize("page", [ROOT / "README.md", ROOT / "docs" / "commands.md", ROOT / "docs" / "troubleshooting.md", *TUTORIALS,
                                  *sorted((ROOT / "docs").glob("*.md"))], ids=lambda p: p.name)
def test_every_fenced_block_has_a_known_language_and_known_run_options(page):
    for b in _tags(page):
        words = b.words
        lang = words[0] if words else ""
        assert lang in ALLOWED_LANGS, f"{page.name}:{b.start}: unknown block language {lang!r}"
        if b.is_run:
            opts = {w.split("=", 1)[0] for w in words[2:]}
            assert opts <= ALLOWED_OPTIONS, f"{page.name}:{b.start}: unknown run option {opts - ALLOWED_OPTIONS}"
        if len(words) > 1 and not b.is_run and not b.is_output:
            assert lang == "bash" and words[1] != "run", f"{page.name}:{b.start}: a second word is only allowed after bash run or text output"


@pytest.mark.parametrize("page", TUTORIALS, ids=lambda p: p.name)
def test_every_tutorial_states_prerequisites_time_and_what_you_have(page):
    text = page.read_text(encoding="utf-8")
    assert text.startswith("# Tutorial "), page.name
    assert re.search(r"\*\*Prerequisites:?\*\*", text), f"{page.name}: no prerequisites"
    assert re.search(r"\*\*Time:?\*\*", text), f"{page.name}: no time"
    assert "## What you have" in text, f"{page.name}: no closing section"
    assert sum(b.is_run for b in rds.parse_blocks(text)) >= 3, f"{page.name}: a tutorial runs at least three commands"


def test_there_are_six_tutorials_and_the_nav_lists_them_in_order():
    names = [t.name for t in TUTORIALS]
    assert names == ["01-first-card.md", "02-your-own-archive.md", "03-reproduce-upworthy.md", "04-weekly-loop.md",
                     "05-serve-http-and-mcp.md", "06-simulation-agent.md"]
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8").split("\nnav:\n", 1)[1]
    pos = [nav.index(f"tutorials/{n}") for n in names]
    assert pos == sorted(pos)
    for page in ("commands.md", "results.md", "troubleshooting.md", "faq.md", "concepts.md"):
        assert re.search(rf":\s+{re.escape(page)}\s*$", nav, re.M), page


def test_the_upworthy_tutorial_needs_the_archives_and_the_others_do_not():
    for t in TUTORIALS:
        needs = [b for b in rds.parse_blocks(t.read_text(encoding="utf-8")) if b.is_run and b.option("needs") == "archives"]
        assert bool(needs) == (t.name == "03-reproduce-upworthy.md"), t.name


def test_every_output_block_follows_a_run_block():
    for page in RUN_PAGES:
        text = page.read_text(encoding="utf-8")
        blocks = rds.parse_blocks(text)
        for i, b in enumerate(blocks):
            if b.is_output:
                follows = i > 0 and blocks[i - 1].is_run and rds.output_block_of(blocks, i - 1, text) is b
                assert follows, f"{page.name}:{b.start}: an output block must follow its run block"


def _needs_archives(page: Path) -> bool:
    return any(b.is_run and b.option("needs") == "archives" for b in rds.parse_blocks(page.read_text(encoding="utf-8")))


@pytest.mark.parametrize("page", RUN_PAGES, ids=lambda p: p.name)
def test_the_commands_in_the_page_run_and_the_output_shown_is_current(page, monkeypatch):
    if not page.exists():
        pytest.skip("page not written yet")
    from conftest import AMBIENT_ROOT

    if AMBIENT_ROOT:
        monkeypatch.setenv("MOOTCOURT_DATA_ROOT", AMBIENT_ROOT)    # lets the archive tutorial find the downloads; the page's shell never sees it
    if _needs_archives(page) and rds.archives_present() is None:
        pytest.skip("this page needs the two public archives (python scripts/download_data.py)")
    fr = rds.run_file(page, slow=os.environ.get("MOOT_DOCS_SLOW") == "1")
    assert fr.results, f"{page.name} has no runnable block"
    problems = rto.compare(fr)
    fix = f"python scripts/render_tutorial_outputs.py --write {page.relative_to(ROOT)}"
    assert not problems, f"{page.name}: run `{fix}` if the change is intended\n" + "\n".join(problems)


def test_the_readme_and_every_tutorial_have_blocks_that_run():
    for page in (ROOT / "README.md", *TUTORIALS):
        assert any(b.is_run for b in rds.parse_blocks(page.read_text(encoding="utf-8"))), f"{page.name} has no runnable block"


# ------------------------------------------------------------------------------------------------------- the manual
def test_the_configuration_reference_lists_every_key_the_code_reads_with_its_default():
    text = (ROOT / "docs" / "reference" / "config.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `\[([\w.]+)\]` \| `(\w+)` \| ([^|]*) \| ([^|]*) \| ", text, re.M)
    documented = {(t, k): (typ.strip(), dflt.strip()) for t, k, typ, dflt in rows}
    sim_keys = set(re.findall(r'table(?:\.get\(|\[)"(\w+)"', (ROOT / "src/mootcourt/simulators/loader.py").read_text(encoding="utf-8")))
    sim_keys |= {"enabled", "adapter"}
    expected = {("project", "name"), ("storage", "data_root"), ("cells", "names"), ("decision", "action_threshold"), ("gate", "target_power"),
                ("service", "url")} | {("simulators.NAME", k) for k in sim_keys}
    assert set(documented) == expected, (set(documented) ^ expected)
    # every non-simulator key is read in the settings code or the modules it names
    code = "".join((ROOT / "src/mootcourt" / f).read_text(encoding="utf-8") for f in ("settings.py", "storage.py", "onboarding.py"))
    for table, key in expected:
        if not table.startswith("simulators"):
            assert f'"{key}"' in code or f"{key} =" in code, (table, key)
    from mootcourt.config import ACTION_THRESHOLD
    from mootcourt.settings import load_settings
    from mootcourt.simulate import DEFAULT_TARGET

    s = load_settings(ROOT / "docs")                                  # no file in docs/: every key at its default
    assert documented[("decision", "action_threshold")][1] == f"{s['decision']['action_threshold']}" == f"{ACTION_THRESHOLD}"
    assert documented[("gate", "target_power")][1] == f"{s['gate']['target_power']:.2f}" == f"{DEFAULT_TARGET:.2f}"
    assert documented[("simulators.NAME", "time_cap_s")][1] == "30" and documented[("simulators.NAME", "version")][1] == "`0`"
    assert documented[("simulators.NAME", "cost_model")][1] == "`free`"
    assert re.search(r"\| `MOOTCOURT_DATA_ROOT` \|", text)


def _commands():
    import typer

    from mootcourt.cli import app

    root = typer.main.get_command(app)
    out = []
    for name, sub in sorted(root.commands.items()):
        subs = getattr(sub, "commands", None)
        out += [f"{name} {s}" for s in sorted(subs)] if subs else [name]
    return out


def test_the_command_guide_covers_every_command_with_purpose_example_and_reads_and_writes():
    text = (ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
    sections = re.split(r"^### ", text, flags=re.M)[1:]
    by_name = {s.split("\n", 1)[0].strip().removeprefix("`moot ").removesuffix("`"): s for s in sections}
    assert set(by_name) == set(_commands()), set(by_name) ^ set(_commands())
    for name, body in by_name.items():
        assert "**Purpose.**" in body, name
        assert "**Reads" in body or "**Writes" in body, name
        assert "```bash run" in body, f"{name}: no example that runs"
        assert "**Common errors" in body, f"{name}: no common errors"      # every command, with a real error or a sentence saying there is none


def test_the_command_guide_runs_each_command_it_documents():
    text = (ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
    ran = "\n".join(b.body for b in rds.parse_blocks(text) if b.is_run)
    for name in _commands():
        assert f"moot {name}" in ran, f"commands.md never runs `moot {name}`"


def test_the_concepts_page_has_the_diagram_and_defines_every_required_term():
    text = (ROOT / "docs" / "concepts.md").read_text(encoding="utf-8")
    mer = [b for b in rds.parse_blocks(text) if b.words == ["mermaid"]]
    assert len(mer) == 1 and "flowchart" in mer[0].body and "moot join" in mer[0].body and "moot card" in mer[0].body
    cfg = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "custom_fences" in cfg and "name: mermaid" in cfg and "fence_code_format" in cfg
    assert "## Glossary" in text
    glossary = text.split("## Glossary", 1)[1].split("\n## ", 1)[0].lower()
    for term in ("ledger", "contrast", "cell", "origin", "usable_after", "p0, p1, p2, p3", "second opinion",
                 "support, novelty, reliability, instability", "card", "frozen ids", "gate", "decision value", "report card"):
        assert term in glossary, term
    for heading in ("Ledger", "Cell", "Origin", "Ladder", "Abstention", "Card", "Frozen ids", "Harness", "Gates", "Decision value", "Report card",
                    "Second opinion", "Reliability report"):
        assert f"## {heading}" in text, heading
    for trig in ("support", "novelty", "reliability", "instability"):
        assert f"| {trig} |" in text, trig


def test_the_troubleshooting_page_covers_its_required_topics_and_the_anchors_other_pages_link_to():
    text = (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8").lower()
    for topic in ("## doctor reports something", "## the data root", "## exfat volumes", "## a card abstains", "## ids differ between machines",
                  "## rows are missing from the ledger", "## rebuilding a ledger after an upgrade", "usable_after", "--min-exposure", "keyerror"):
        assert topic in text, topic
    for page in ROOT.glob("docs/**/*.md"):
        if "superpowers" in page.parts or page.name.startswith("._"):
            continue
        for anchor in re.findall(r"troubleshooting\.md#([\w-]+)", page.read_text(encoding="utf-8")):
            plain = text.replace("`", "")
            headings = re.findall(r"^#+ (.+)$", plain, re.M)
            slugs = {re.sub(r"[^\w\s-]", "", h).strip().replace(" ", "-") for h in headings}      # how mkdocs names a heading
            assert anchor in slugs, f"{page.name} links to troubleshooting.md#{anchor}; the headings give {sorted(slugs)}"


def test_the_faq_answers_the_questions_a_new_reader_asks():
    text = (ROOT / "docs" / "faq.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^\*\*.+\?\*\*", text, re.M)) >= 25
    for q in ("How many tests do I need?", "Do I need user-level data?", "Why does the card often abstain?", "Does anything leave my machine?"):
        assert q in text, q


def test_the_results_page_holds_the_generated_block_and_the_readme_links_to_it():
    results = (ROOT / "docs" / "results.md").read_text(encoding="utf-8")
    if "<!-- moot-results:start -->" not in results:
        pytest.skip("results page not written yet")
    assert results.count("<!-- moot-results:start -->") == 1 and results.count("<!-- moot-results:end -->") == 1
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "moot-results:start" not in readme and "docs/results.md" in readme
    assert len(readme.split("\n")) <= 225, "the README is a reader's entry point of about 220 lines"


# ------------------------------------------------------------------------------------------- T-055: the documentation pass after chunk L
def _doc(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_every_command_has_exactly_one_common_errors_entry_and_the_five_named_by_the_verification_have_theirs():
    text = _doc("docs/commands.md")
    sections = {s.split("\n", 1)[0].strip().removeprefix("`moot ").removesuffix("`"): s for s in re.split(r"^### ", text, flags=re.M)[1:]}
    assert len(re.findall(r"^\*\*Common errors", text, re.M)) == len(_commands()) == len(sections)
    for name in ("storage", "ledger formats", "simulators list", "simulate ledger", "simulate power"):
        assert sections[name].count("**Common errors") == 1, name
        entry = sections[name].split("**Common errors", 1)[1]
        assert len(entry.strip()) > 60, f"{name}: the common errors entry is empty"


def test_the_troubleshooting_page_covers_a_clone_on_an_exfat_volume():
    text = _doc("docs/troubleshooting.md")
    low = text.lower()
    assert "## working from a clone on an exfat volume" in low
    section = low.split("## working from a clone on an exfat volume", 1)[1].split("\n## ", 1)[0]
    assert "._" in section and "sidecar" in section and "find . -name" in section and "-delete" in section       # the cleanup command
    assert "uv_project_environment" in section and "internal disk" in section                                    # the virtualenv elsewhere
    assert "test" in section and "unicodedecodeerror" in section                                                  # what the sidecars break


def test_the_troubleshooting_page_explains_the_service_clock_and_no_longer_says_an_origin_cures_staleness():
    text = _doc("docs/troubleshooting.md")
    line = next(ln for ln in text.splitlines() if ln.startswith("- **A card from the service abstains"))
    assert "Pass an `origin` in the request, or join fresh results" not in text
    low = line.lower()
    assert "clock" in low and "14 days" in low and "origin" in low and "does not" in low        # the staleness rule and why an origin does not help
    assert "moot join" in low or "join fresh" in low


def test_the_weekly_join_pages_describe_the_row_id_the_three_interfaces_take_and_tutorial_four_has_no_python_workaround():
    t4 = _doc("docs/tutorials/04-weekly-loop.md")
    assert "--row-id" in t4 or "--test-id" in t4
    assert "does not take a row id yet" not in t4 and "Until a `--row-id` option exists" not in t4
    assert "from mootcourt import card" not in t4 and "issue_cards.py" not in t4 and "```python" not in t4
    for rel in ("README.md", "docs/concepts.md"):
        text = _doc(rel)
        assert "row id" in text.lower() and "--row-id" in text, rel
    for iface in ("`POST /card`", "MCP"):
        assert iface in _doc("docs/concepts.md") or iface in _doc("docs/tutorials/05-serve-http-and-mcp.md")
    t5 = _doc("docs/tutorials/05-serve-http-and-mcp.md")
    assert "row_id" in t5


def test_the_rung_wording_states_what_the_guard_does_and_does_not_claim_a_rung_must_beat_the_one_below():
    forbidden = re.compile(r"(used|admitted)[^.]{0,40}only (if|when)[^.]{0,30}beats? the (rung|one) below", re.I)
    for rel in ("README.md", "docs/concepts.md", "docs/faq.md", "docs/tutorials/02-your-own-archive.md", "docs/results.md"):
        assert not forbidden.search(_doc(rel)), f"{rel}: a rung is used only if it beats the one below"
    concepts = _doc("docs/concepts.md")
    assert "P2 equals P1 exactly at a weight of zero" in concepts or "reduces to P1" in concepts
    assert "does not promise" in concepts or "not a promise" in concepts
    faq = _doc("docs/faq.md")
    assert "P2 can score below P1" in faq or "P2 can score worse than P1" in faq
    t2 = _doc("docs/tutorials/02-your-own-archive.md")
    assert "admission guard" in t2 and "out of time" in t2


def test_the_serve_readiness_loops_have_a_time_limit():
    for rel in ("docs/commands.md", "docs/tutorials/05-serve-http-and-mcp.md"):
        text = _doc(rel)
        waits = [b.body for b in rds.parse_blocks(text) if b.is_run and "/health" in b.body and "moot serve" in b.body]
        assert waits, rel
        for body in waits:
            assert not re.search(r"\b(until|while)\b", body), f"{rel}: an unbounded readiness loop"
            assert re.search(r"for \w+ in \$\(seq 1 \d+\)", body) and "break" in body, f"{rel}: the readiness wait has no time limit"


def test_a_block_that_times_out_ends_the_page_and_stops_everything_it_started(tmp_path, monkeypatch):
    monkeypatch.setattr(rds, "BLOCK_TIMEOUT_S", 2)
    pidfile = tmp_path / "bg.pid"
    p = _page(tmp_path, f"```bash run\nsleep 300 &\necho $! > {pidfile}\nuntil false; do sleep 1; done\n```\n\n```bash run\necho never\n```\n")
    fr = rds.run_file(p)
    assert [r.status for r in fr.results] == ["timeout", "skipped"] and "timed out" in fr.results[1].note
    pid = int(pidfile.read_text().strip())
    import time as _time

    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        _time.sleep(0.1)
    else:
        raise AssertionError("the background process of the page survived the timeout")


def test_the_output_mask_hides_how_many_days_old_but_not_the_staleness_limit():
    assert rds.mask("reliability: 3 entries are stale (limit 14 days, oldest 489 days old)") == rds.mask(
        "reliability: 3 entries are stale (limit 14 days, oldest 12 days old)")
    assert rds.mask("stale (limit 14 days, oldest 5 days old)") != rds.mask("stale (limit 30 days, oldest 5 days old)")


def test_the_drift_definition_carries_its_margin_and_minimum_wherever_it_is_defined():
    for rel in ("docs/concepts.md", "docs/tutorials/04-weekly-loop.md"):
        text = _doc(rel)
        drift = [ln for ln in text.splitlines() if "drift" in ln.lower() and ("two joins" in ln or "two in a row" in ln or "two consecutive" in ln)]
        assert drift, rel
        assert all("0.10" in ln and "ten outcomes" in ln for ln in drift), f"{rel}: drift without the 0.10-nat margin and the ten-outcome minimum"


def test_the_p0_wording_calls_it_the_base_rate_forecaster_with_zero_skill_by_construction():
    for rel in ("docs/concepts.md", "docs/results.md"):
        text = _doc(rel)
        assert "base-rate forecaster" in text and "zero by construction" in text, rel
        assert "P0 predicts the cell base rate" not in text, rel
    assert "Normal distribution of the cell's observed effects" not in _doc("docs/concepts.md")


# What a user meets, where. Each pair is (page, a phrase that page must carry) for one behaviour change of chunk L.
CHUNK_L_BEHAVIOURS = {
    "P0 as the base-rate forecaster": ("docs/concepts.md", "empirical base-rate forecaster"),
    "the P2 Student-t predictive": ("docs/concepts.md", "Student-t"),
    "card fields for the predictive and both intervals": ("docs/concepts.md", "interval for the observed estimate"),
    "card schema version 2": ("docs/reference/card.md", "schema_version"),
    "the card skill line with interval and gate verdict": ("docs/concepts.md", "skill line"),
    "the row id on the three interfaces": ("docs/commands.md", "--row-id"),
    "the row id on POST /card": ("docs/tutorials/05-serve-http-and-mcp.md", "row_id"),
    "the live join recording abstained cards": ("docs/concepts.md", "sealed"),
    "the champion-refresh rule": ("docs/concepts.md", "method_id"),
    "the gates file with two base rates": ("docs/concepts.md", "base rate"),
    "the decision table columns": ("docs/concepts.md", "difference from random order"),
    "coverage by precision decile": ("docs/concepts.md", "realized over the planned standard error"),
    "the guard-off ablations": ("docs/results.md", "+p2-guard-off"),
    "the prelaunch admission option": ("docs/commands.md", "--admission prelaunch"),
    "the positive-control synthetic archive": ("docs/commands.md", "--text-effect"),
    "the adjusted intervals": ("docs/concepts.md", "Bonferroni"),
    "the gate-power command": ("docs/commands.md", "moot simulate gate-power"),
}


@pytest.mark.parametrize("what", sorted(CHUNK_L_BEHAVIOURS))
def test_every_behaviour_change_of_chunk_l_is_documented_where_a_user_meets_it(what):
    rel, phrase = CHUNK_L_BEHAVIOURS[what]
    page = ROOT / rel
    assert page.exists(), f"{what}: {rel} does not exist"
    assert phrase in page.read_text(encoding="utf-8"), f"{what}: {rel} lacks {phrase!r}"


def test_the_card_reference_page_exists_is_in_the_nav_and_lists_the_prediction_fields():
    text = _doc("docs/reference/card.md")
    for field in ("family", "df", "location", "scale", "s_star", "interval_80", "interval_90", "interval_80_y", "interval_90_y", "withheld",
                  "row_id", "schema_version"):
        assert f"`{field}`" in text, field
    assert "reference/card.md" in _doc("mkdocs.yml")
