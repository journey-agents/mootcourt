# Convergence Plan: from round 01 to a paper and package worth submitting

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reach the review protocol's stop condition in at most two more rounds, with every change verified at the cheapest level that proves it, and the arXiv tarball ready the day the stop condition is met.

**Architecture:** Three mechanisms make the loop converge instead of wander. A claims register turns the paper into a finite list of claims with evidence paths, so a review finding must name the claim it weakens or the rubric item it fails. A closed rubric per reviewer role fixes what can count as blocking or major, and the same six reviewers continue across rounds, verifying their own previous findings before raising new ones. A tiered verification ladder (text, number-neutral code, number-changing code) replaces the full rerun per change, with the full suite only at pull-request time and the clean clone only before a round.

**Tech Stack:** Python 3.11+ with uv, pytest, the `moot` CLI, tectonic for the paper, `scripts/run_experiments.sh` and `scripts/assemble_run_folder.py` for experiment stages, the fleet registry in `.claude/fleet/tasks.json`.

**Spec:** `paper/reviews/protocol.md` (the review protocol, amended by Task 2), `paper/reviews/round-01/response.md` (the inventory of open items), `.claude/fleet/release-checklist.md` (the release steps after the stop condition).

## Global Constraints

- The repository never names the employer, team, person or purpose it was built for; write "the launching team".
- No em dash and no en dash in any file; never the role noun spelled o-w-n-e-r; the tier 1 digests in `tests/forbidden_terms.sha256` never anywhere, the tier 2 digests in `tests/restricted_terms.sha256` only in allow-listed files.
- Agents never commit; the lead commits and pushes. Commit messages end with the attribution lines of the session.
- No LLM calls in the package's default path. No downloads except the clone, `uv sync`, and the archives fetched by a timed run the user has approved.
- Every number in the paper carries a `% src:` comment naming a report JSON under the current run folder, and `make tables` regenerates `paper/tables` byte-identical to the committed files.
- `export MOOTCOURT_DATA_ROOT="/Volumes/Crucial X10/mootcourt-data"` before anything that reads the data root; large data stays on the external drive.
- The deadline is Sunday 8 November 2026: the stop condition or the capped release decision by Saturday evening.

## Review Focus

- A finding that names no claim and no rubric item: the protocol must record it as a suggestion, never as a major, or the loop reopens. Task 2 tests that the rubric states this rule.
- A fix that moves a number no one expected: Tier B's sample-ledger diff must catch any change to the committed sample report. Task 5 tests the diff on a deliberately altered report.
- A stage rerun that leaves a stale sibling file in the run folder: `assemble_run_folder.py --update` must refuse a file whose header model id is older than the stage it depends on. Task 5 tests the refusal.
- A claim whose evidence path exists but whose key no longer holds the quoted value: the claims audit must compare the value, not only the path. Task 3 tests the mismatch.
- A round dispatched while a PENDING marker or a failing self-check item remains: `make selfcheck` must exit non-zero on either. Task 4 tests both.

---

## Why the loop has not converged, in one paragraph

Round 00 had four reviewers and found five blocking and twenty-one major findings; round 01 had six reviewers, two of them new roles, and found three blocking and twenty-one major, seventeen of them from the four returning roles. Every blocking finding was a real defect and every one is now closed in run 6. The count of majors fell slowly for three reasons: each round brought fresh reviewers with their own taste; "missing experiment" was an open-ended severity, so any suggested analysis could be a major; and every analysis added in answer to one round invited new questions in the next. The three mechanisms above remove each cause. The expected trajectory is round 02 with no blocking and a handful of majors, and round 03 at the stop condition.

## Verification tiers (used by every task below)

| Tier | What changed | What proves it | Cost |
|---|---|---|---|
| A | Paper text, docs, README, review files | `make paper` exit 0 and the page count; number audit 0 unmatched; `tests/test_writing_rules.py`; docs `--check` scripts | minutes |
| B | Code that must not move a number (CLI messages, doctor, join bookkeeping, tests, tooling) | The touched module's tests; `make quick-check` (Task 5): the sample ledger's backtest regenerated and diffed against the committed sample report apart from timestamps and model ids | under 10 minutes |
| C | Code that moves numbers | Only the stages the change touches, by `scripts/run_experiments.sh --only`; `assemble_run_folder.py --update`; `make tables`; the paper's `% src:` lines for the changed files; a full rerun only if P0, P1, the ledger format or the backtest harness changed | the stages' own wall time |
| PR | Any commit series | The full suite once, locally or in CI; ruff; `make selfcheck` | once per pull request |
| Round | Before a review round | A clean clone by the tester, every task's acceptance criteria, `make selfcheck` green | once per round |

---

### Task 1: Land the in-flight work (Phase 0, Wednesday evening)

**Files:**
- Modify: `paper/sections/appendix.tex` (the one `% PENDING-T076` line, wall time from builder-l)
- Modify: `.claude/fleet/tasks.json` (T-076, T-079 marked done by builder-l)
- Create: `.claude/fleet/verification-p.md` (tester)

**Interfaces:**
- Consumes: builder-l's run-log.json, the paper writer's part 2b summary, builder-m's phase B2b summary.
- Produces: commit on `chunk-l`, pull request 7, main fast-forwarded; the commit every later task builds on.

- [ ] **Step 1: Collect the three reports** (wall time, fetch time, diff result, suite counts; page count, audit counts, marker count; docs test counts).
- [ ] **Step 2: Fill the wall-time line.** Replace the `% PENDING-T076` line with the number and its `% src: paper/data/run6-forward-chaining/run-log.json`.
- [ ] **Step 3: Tier A plus the rules.** Run: `make paper && .venv/bin/python -m pytest -q tests/test_writing_rules.py tests/test_paper_sources.py tests/test_review_f.py -p no:cacheprovider`. Expected: exit 0, no PENDING marker in `paper/`.
- [ ] **Step 4: Commit and open the pull request** with the drafted message and body in the scratchpad (`commit-msg-p.txt`, `pr-body-p.md`, slots filled). Run: `git add -A && git commit -F <msg> && git push -u origin chunk-l && gh pr create ...`.
- [ ] **Step 5: Dispatch the tester** with `verify-p-brief.md` (COMMIT filled) and watch CI. Expected: CI green on all eight jobs; the tester reports every task of T-060 to T-080 passing.
- [ ] **Step 6: Fast-forward main.** Run: `git push origin <sha>:main`.

### Task 2: The rubric and the amended protocol

**Files:**
- Create: `paper/reviews/rubric.md`
- Modify: `paper/reviews/protocol.md` (Stop condition section; Reviewers section)
- Test: `tests/test_review_protocol.py`

**Interfaces:**
- Produces: rubric item ids `R1.1` to `R6.n` that reviews, the response letter and the claims register cite.

- [ ] **Step 1: Write the failing test.**

```python
def test_rubric_has_six_roles_with_at_least_eight_items_each():
    text = Path("paper/reviews/rubric.md").read_text()
    for k in range(1, 7):
        ids = re.findall(rf"^- \[R{k}\.(\d+)\]", text, flags=re.M)
        assert len(ids) >= 8, k

def test_protocol_states_the_three_convergence_rules():
    text = Path("paper/reviews/protocol.md").read_text()
    assert "names the claim it weakens or the rubric item it fails" in text
    assert "The same six reviewers continue" in text
    assert "at most two further rounds" in text
```

- [ ] **Step 2: Run it to verify it fails.** Run: `.venv/bin/python -m pytest -q tests/test_review_protocol.py`. Expected: FAIL, file not found.
- [ ] **Step 3: Write `paper/reviews/rubric.md`.** One section per role; each item one line `- [Rk.n] <check> <severity if it fails: blocking | major | minor>`. Derive the items from the two rounds' findings and the mandatory checks already in the protocol. The fixed severities: blocking only for leakage, a number that does not reproduce, or a claim the evidence does not support; major only for an experiment the rubric names (baselines on matched splits, the positive control, the leakage audit, an ablation of each design choice, the learning curve, decision value against random and matched order, the clean-clone run, the tutorials from a clean clone); everything else minor or nit. The last section states the rule: a finding that names no claim id and no rubric id is a suggestion, recorded in the letter under "Suggestions", never fixed in the round, never counted toward the stop condition.
- [ ] **Step 4: Amend `paper/reviews/protocol.md`.** Reviewers: "The same six reviewers continue across rounds; each receives its own previous review and the response letter, verifies each of its previous findings first (closed or not closed, with the evidence), then runs its rubric section, then may add findings that name a claim or a rubric item." Stop condition: add "every rubric item passes for every role", "a finding ... names the claim it weakens or the rubric item it fails", and "at most two further rounds after round 01; at the cap, open minors are listed in the letter and in the limitations section and the paper is released; an open major at the cap is a decision for the launching team".
- [ ] **Step 5: Run the test to verify it passes.** Expected: PASS. Then Tier A: `tests/test_writing_rules.py` on the two files.

### Task 3: The claims register and its audit

**Files:**
- Create: `paper/reviews/claims.md`
- Create: `scripts/claims_audit.py`
- Test: `tests/test_claims_register.py`

**Interfaces:**
- Consumes: the `% src:` convention and `paper/data/run6-forward-chaining/*.json`.
- Produces: `claims_audit(register_path: Path, run_dir: Path) -> list[ClaimResult]` where `ClaimResult(id: str, ok: bool, reason: str)`; claim ids `C1` to `Cn` cited by reviews and the letter.

- [ ] **Step 1: Write the failing tests.**

```python
def test_every_claim_resolves_to_a_value_in_a_report(tmp_path):
    results = claims_audit(Path("paper/reviews/claims.md"), Path("paper/data/run6-forward-chaining"))
    assert [r.id for r in results if not r.ok] == []

def test_a_value_that_moved_is_reported(tmp_path):
    # register row: C9 | <sentence> | report.json | tables.aggregate[predictor=p2].logscore_vs_p1 | 0.0004 | adjusted
    write_register(tmp_path, value="0.0040")
    results = claims_audit(tmp_path / "claims.md", Path("paper/data/run6-forward-chaining"))
    assert results[0].ok is False and "0.0004" in results[0].reason
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL, module not found.
- [ ] **Step 3: Write the register.** The paper writer lists every claim sentence of the abstract, the introduction's contributions, the six hypotheses, Section 6's headline sentences and the conclusion: a table with columns id, section, sentence, report path, key path, printed value, interval kind (adjusted, plain, none), status (supported, weakened, removed). Keys use the dotted form `tables.<name>[<col>=<value>].<field>`.
- [ ] **Step 4: Implement `claims_audit`** in `scripts/claims_audit.py`: parse the table, load each report, resolve the key path, compare the printed value at the printed precision, return one `ClaimResult` per row; exit 1 from `main()` if any row fails.
- [ ] **Step 5: Run the tests to verify they pass.** Expected: PASS.
- [ ] **Step 6: The audit pass.** A statistician agent (not a reviewer of any round) reads the register against the tables and writes `paper/reviews/claims-audit.md`: for each claim, supported as written, or the sentence it should become, or removed. The paper writer applies every line (Tier A). The letter's final section cites the register.

### Task 4: The self-check gate

**Files:**
- Create: `scripts/review_selfcheck.py`
- Modify: `Makefile` (target `selfcheck`)
- Test: `tests/test_review_selfcheck.py`

**Interfaces:**
- Consumes: `claims_audit` (Task 3), the existing `scripts/release_check.py`, `scripts/gen_cli_docs.py --check`, `scripts/render_tutorial_outputs.py --check`, `scripts/render_readme_results.py --check`, the number audit and source resolution scripts of the paper writer (move them from the scratchpad into `scripts/paper_audit.py` as part of this task).
- Produces: `run_selfcheck(repo: Path) -> SelfCheckReport` with `items: list[tuple[str, bool, str]]` and `ok: bool`; the file `.claude/fleet/selfcheck-<date>.md`.

- [ ] **Step 1: Write the failing tests.**

```python
def test_a_pending_marker_fails_the_selfcheck(tmp_repo):
    (tmp_repo / "paper/sections/x.tex").write_text("% PENDING-T999\n")
    assert run_selfcheck(tmp_repo).ok is False

def test_report_lists_every_item_with_its_status(tmp_repo):
    report = run_selfcheck(tmp_repo)
    names = [name for name, _, _ in report.items]
    assert {"pending-markers", "number-audit", "source-resolution", "writing-rules", "forbidden-terms", "paper-builds", "tables-byte-identical", "docs-current", "claims-audit", "release-check"} <= set(names)
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Implement `run_selfcheck`** as a list of named checks, each a function returning `(ok, detail)`, run in order, never short-circuiting, writing the Markdown report.
- [ ] **Step 4: Run the tests to verify they pass; run `make selfcheck` on the tree.** Expected: tests PASS; the tree's report lists every item green before Task 8 dispatches a round.

### Task 5: Tiered verification tooling

**Files:**
- Modify: `scripts/run_experiments.sh` (flags `--only <stage>[,<stage>]` and `--list`)
- Modify: `scripts/assemble_run_folder.py` (flag `--update <report>...`)
- Modify: `Makefile` (target `quick-check`)
- Create: `scripts/quick_check.py`
- Test: `tests/test_quick_check.py`, `tests/test_run_experiments_only.py`

**Interfaces:**
- Produces: `make quick-check` (Tier B), `scripts/run_experiments.sh --only main-synthetic` (Tier C), `assemble_run_folder.py --update <files>` which copies only the named reports into the run folder and refuses a file whose header model id is older than the newest file it depends on.

- [ ] **Step 1: Write the failing tests.**

```python
def test_quick_check_passes_on_the_committed_sample_report(tmp_path):
    assert quick_check(sample_root(tmp_path)).ok

def test_quick_check_fails_when_a_number_moved(tmp_path):
    root = sample_root(tmp_path); bump_one_value(root / "reports/backtest-sample.json")
    assert quick_check(root).ok is False

def test_list_prints_every_stage_and_only_runs_the_named_one():
    out = run(["bash", "scripts/run_experiments.sh", "--list"])
    assert "main-synthetic" in out and "lc-upworthy" in out
    out = run(["bash", "scripts/run_experiments.sh", "--only", "fit-synthetic", "--dry-run"])
    assert out.strip().splitlines() == ["fit-synthetic"]

def test_update_refuses_a_stale_dependent(tmp_run_dir):
    with pytest.raises(SystemExit):
        update(tmp_run_dir, [older_report_than_its_gates])
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** `--list` prints the stage names in order; `--only` runs the named stages through the existing `step` function; `--dry-run` prints what would run. `quick_check(root: Path) -> QuickCheckResult` regenerates the sample ledger's backtest into a temporary data root and diffs the report against the committed one with the header fields `model_id`, `created_at` and any `*_seconds` field ignored. `--update` copies the named files and checks model-id order against the folder's dependency list (gates before backtests, backtests before extras).
- [ ] **Step 4: Run the tests to verify they pass.** Expected: PASS; `make quick-check` under 10 minutes on this machine (record the time in the summary).

### Task 6: Close the open items from round 01

**Files:** per item below.

**Interfaces:**
- Consumes: Task 5's tiers.
- Produces: every "Pending, listed" and "Still open" line of the round 01 letter closed or argued, with its tier's evidence.

| Item (letter section) | Decision | Tier | Evidence |
|---|---|---|---|
| Cautionary run at 500 resamples (R3 minor 7) | Done in run 6; the letter says so | A | run 6 README |
| Single-headline run of the challengers (R3 minor 6) | Check whether the `contrasts_one` ablation covers the challengers; if not, one Tier C stage | C | the ablation report |
| A stronger text challenger (R5 major 4, optional) | Argued: future work; the rubric names the three challengers as the fixed set | A | letter and limitations |
| Seed dated at the fit clock within the staleness limit (R2 minor 9) | Fix in `src/mootcourt/registry.py` fit path with a unit test | B | module test and `make quick-check` |
| Outcome record's ledger snapshot id and post-launch fields (R2 nit 1) | Fix in `card.py` outcome record; unit test | B | module test |
| Join older than the trailing window says so (R2 nit 3) | One message line in the join; unit test | B | module test |
| Doctor counts (no row id, unknown row id, passed horizon, unadmitted), provenance admission rule, "fewer than two tests" line, verify script message (R2 minors 8, 10, 11; R6 minors 4, 13) | Doctor counts and the two messages fixed; the provenance admission rule argued (a policy, not a defect) | B | `tests/test_doctor.py` additions |
| exFAT backtest seconds (R6 minor 4) | Measure once with `time` on both roots; one sentence in troubleshooting | A | the two timings in the summary |
| Single-column style and track checklist (R5 minor 9) | At submission; argued | A | letter |
| En dashes in the rendered PDF from class and bibliography (R4 nit) | Argued: typeset page ranges from the style; sources carry none | A | letter |
| Second runner image in CI (R4 question 2) | Add `ubuntu-latest` plus `macos-latest` for the test job at one Python version | PR | CI green on both |

- [ ] **Step 1: For each B row, write the failing unit test, run it, implement, run it.**
- [ ] **Step 2: Run `make quick-check` once after all B rows.** Expected: sample report unchanged.
- [ ] **Step 3: The paper writer updates the letter's status lines** (Tier A).

### Task 7: The editorial quality pass on the paper

**Files:**
- Modify: `paper/main.tex`, `paper/sections/*.tex` (paper writer only)
- Test: the existing `tests/test_writing_rules.py` plus `tests/test_paper_captions.py` (call 235) and the claims audit of Task 3.

- [ ] **Step 1: Run the checklist, each item yes or no, recorded in `.claude/fleet/editorial-pass.md`:** every caption self-contained (what, where from, how to read the interval); every table and figure referenced from the text; every acronym defined at first use; the abstract's numbers equal the tables' at the printed precision; the limitations section lists every argued item of the letters and every rubric item answered "not done"; the six hypotheses stated once, in Section 5, and read back once, in Section 9, with the same wording; no sentence claims more than its claim id supports; the related-work section cites every baseline's source.
- [ ] **Step 2: Fix every "no".** Tier A after each batch of fixes.
- [ ] **Step 3: `make selfcheck` green.** Expected: every item green, body on page 9 or 10.

### Task 8: Round 02, the fix batch, round 03 (Thursday evening to Saturday)

**Files:**
- Create: `paper/reviews/round-02/R1..R6-*.md`, `summary.md`, `response.md`; later `round-03/`.
- Modify: the brief template in the scratchpad (`round01-brief-template.md` becomes `round-brief-template.md` with ROUND, COMMIT, ROLE, the rubric, the claims register and the reviewer's previous review).

**Interfaces:**
- Consumes: Tasks 2 to 7 complete, `make selfcheck` green, the tester's clean clone of the round's commit.
- Produces: the convergence table in each round's summary: open findings by severity, rubric items passed per role, claims supported, numbers changed since the previous round.

- [ ] **Step 1: Dispatch round 02 to the six continuing reviewers** with the amended brief. Expected: six review files citing claim and rubric ids; summary with the convergence table.
- [ ] **Step 2: Triage every finding into a tier** in the response letter draft; batch the fixes; one Tier C run for all number-moving fixes together; `make quick-check` after the B batch; Tier A for the rest.
- [ ] **Step 3: PR tier:** full suite, ruff, `make selfcheck`, commit, pull request, CI, the tester's clean clone, fast-forward.
- [ ] **Step 4: Round 03** with the same six, plus one fresh area chair bounded by the rubric as the independent check. Expected: the stop condition, or the cap outcome recorded in the summary.
- [ ] **Step 5: At the cap:** minors listed in the letter and the limitations; a major, if any, written up for the launching team's decision with the options (fix and run round 04; or argue and release).

### Task 9: Release on the stop condition

- [ ] **Step 1: Follow `.claude/fleet/release-checklist.md`** in order: version 1.0.0, CHANGELOG, `make arxiv`, `make arxiv-check`, tag, GitHub release, the metadata file reread against `main.tex`.
- [ ] **Step 2: Hand the launching team the four account steps:** arXiv endorsement and upload, Zenodo integration before the tag, repository visibility, the author line.

## Schedule

| When | What |
|---|---|
| Wed 4 Nov, evening | Task 1 (land run 6, PR 7, CI, clean clone, fast-forward); Tasks 2 and 5 start in parallel |
| Thu 5 Nov | Tasks 2 to 7 complete; `make selfcheck` green; PR 8 |
| Thu evening | Round 02 dispatched |
| Fri 6 Nov | Round 02 fixes in tiers; PR 9; clean clone |
| Sat 7 Nov | Round 03; stop condition or cap decision; Task 9 |
| Sun 8 Nov | Buffer; the launching team uploads to arXiv |

## How to read progress

After every round, the summary's convergence table must show each of these moving the right way, or the plan is revised rather than another round run: open blocking (must be 0), open major (falling), rubric items passed per role (rising to all), claims supported as written (rising to all), numbers changed since the previous round (falling to 0 apart from an intended Tier C stage).
