# Paper Red-Team Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find every error of argument, truth and clarity that remains in paper version 2 after the paragraph review, and say what a named venue's reviewers would object to, using reviewers who have seen none of the earlier work.

**Architecture:** A venue scout first recommends a venue from the paper's topic and the submission dates now open, and the user picks one. Then eleven fresh reviewers work in three stages. Stage 1 has two cold readers and one venue reviewer, who see only the built PDF. Stage 2 has six checkers, who each read one slice as a reader and then test it against the run 8 reports and the code. Stage 3 has two adversarial verifiers, who try to refute every finding. The lead then checks each surviving fix against its report and brings it to the user, who accepts or rejects each one.

**Tech Stack:** The Agent tool with fresh general-purpose agents; web search and fetch for the venue scout only; `paper/main.pdf` built by `make paper`; the reports under `paper/data/run8-randomization-window`; the `paper-check` skill after any accepted edit.

**Spec:** `.claude/skills/paper-review/SKILL.md` (local), the team structure the user was shown on 10 November 2026, and the user's two instructions of that day: add a reviewer for a specific venue's requirements, and choose the venue from a search of topic fit, timing and the submission dates now open.

## Global Constraints

- The paper under review is branch `paper-v2` at commit 9f9f338 or later. Record the commit in the run folder before the first reviewer starts.
- No reviewer is given, or may open, `paper/reviews/`, `.claude/fleet/` (other than its own output file and the files its brief names), `.claude/skills/`, `docs/superpowers/`, or any part of the lead's conversation.
- No reviewer may open an Upworthy file named holdout, confirmatory or undeployed.
- Reviewers read only. They edit no file except their own output file.
- Only the venue scout uses the network. Its searches and fetches carry general topic words and venue names only: never the paper's title, its text, the author's name, the repository's name or an email address.
- No other download and no other call to an outside service. The Muse is not used unless the user says yes; the default is no.
- A venue fact (a date, a page limit, a policy) is stated only with the URL of the venue's own page and the date it was fetched. A fact found only on a third-party list is marked unconfirmed.
- Every finding quotes the paper's words with file and line (or page for a reader of the PDF), proposes replacement text, and is marked `checked` (with the report path and key) or `inferred`.
- A number a reviewer computes does not enter the paper unless a report key holds it.
- Replacement text follows the repository's writing rules: no dash of any kind, complete sentences, at most two numbers in a sentence, terms defined before use.
- Nothing in the paper changes in this plan until the user accepts a finding. Nothing is committed or pushed unless the user asks.
- Cutting the paper to a venue's page limit is not part of this plan. The venue reviewer says what would have to move; the cut itself is a separate plan the user must ask for.

## Review Focus

The failure modes of the review itself, most likely first. Each is pinned by a step named beside it.

1. A reviewer reads an earlier review and repeats its verdicts. Pinned by the forbidden paths in every brief (Task 1) and the opening statement each reviewer must write (Tasks 3 and 4).
2. A reviewer reports a mistake of its own in the same confident tone as a real finding. Pinned by the verifiers (Task 5) and the lead's own check against the report (Task 6).
3. The venue's rules are taken from memory or from last year's call. Pinned by Task 2, step 2: every rule carries a URL, a fetch date and the year of the call it comes from.
4. A cold reader's confusion is dismissed because the lead knows the answer. Pinned by Task 6, step 2: every confusion is kept unless the paper's own text, quoted, already answers it before that point.
5. Sentence fixes are applied to text that the venue's page limit would remove. Pinned by Task 6, step 5: the venue report is presented first, and the user decides whether to cut before deciding on sentences.

---

## File Structure

All outputs go under `.claude/fleet/red-team-2026-11-10/`, which is local and not in git.

| File | Written by | Holds |
|---|---|---|
| `commit.txt` | lead | the commit and the PDF's page count |
| `brief-common.md` | lead | the rules every brief starts with |
| `venues.md` | venue scout | the candidate venues, their facts with URLs, and a recommendation |
| `venue-requirements.md` | lead | the chosen venue's rules and review criteria, copied from `venues.md` after the user's choice |
| `r1-newcomer.md`, `r2-referee.md` | cold readers | their reports |
| `v1-venue.md` | venue reviewer | the review as that venue would write it |
| `c1-frontmatter.md` to `c6-consistency.md` | checkers | their findings |
| `verified-a.md`, `verified-b.md` | verifiers | each finding with a verdict |
| `findings.md` | lead | the merged list presented to the user, with the user's decision on each |

Finding format, used by every reviewer:

```text
### <id> <severity: broken | weak | unclear | minor>
Where: <file>:<line> (or PDF page and paragraph)
Quote: "<the paper's words>"
Problem: <one or two sentences>
Proposed: "<replacement text>"
Basis: checked <report path> <key> = <value> | inferred
```

Ids are the file's prefix and a number: `R1-3`, `C4-12`, `V1-2`.

---

### Task 1: Prepare the run folder and the briefs

**Files:**
- Create: `.claude/fleet/red-team-2026-11-10/commit.txt`
- Create: `.claude/fleet/red-team-2026-11-10/brief-common.md`

**Interfaces:**
- Produces: the common brief text that Tasks 3 to 5 prepend to each reviewer's prompt, and a PDF known to match the committed sources.

- [ ] **Step 1: Confirm the tree is clean and build the PDF**

Run: `git status --short && MOOTCOURT_DATA_ROOT="/Volumes/Crucial X10/mootcourt-data" make paper && pdfinfo paper/main.pdf | grep Pages`
Expected: no modified file under `paper/`, and `Pages: 45`.

- [ ] **Step 2: Write `commit.txt`** with the output of `git rev-parse HEAD` and the page count.

- [ ] **Step 3: Write `brief-common.md`** with exactly these rules:

```text
You are reviewing a research paper you have never seen. You do not edit the paper.
Do not open: paper/reviews/, .claude/ (except the files this brief names), docs/superpowers/, or any Upworthy file whose name contains holdout, confirmatory or undeployed.
Do not use the network.
Begin your report with one line: "I opened none of the forbidden paths." If that is not true, say which you opened and stop.
Write findings in the format below and save them to your output file. Quote the paper's words exactly. Propose replacement text for each finding. The replacement uses no dash of any kind, complete sentences, at most two numbers in a sentence, and no term before its definition.
Mark each finding "checked" with the report path and key, or "inferred". Do not put a number you computed into replacement text unless a report key holds it.
Severity: broken (the claim is false or does not follow), weak (the claim is stronger than its evidence), unclear (a careful reader cannot tell what is meant), minor.
Report what you find. Do not pad: a slice with three real findings gets three.
```

followed by the finding format from the File Structure section.

- [ ] **Step 4: Verify** that `brief-common.md` names no file under `paper/reviews/` and holds none of the lead's conclusions about the paper.

### Task 2: Scout the venues and let the user choose

**Files:**
- Create: `.claude/fleet/red-team-2026-11-10/venues.md`
- Create: `.claude/fleet/red-team-2026-11-10/venue-requirements.md`

**Interfaces:**
- Produces: `venue-requirements.md`, which the venue reviewer of Task 3 reads.

- [ ] **Step 1: Launch one fresh general-purpose agent, the venue scout**, with web search and fetch and this brief. It does not read the paper; the description below is all it gets.

```text
Today is 10 November 2026. Find the best place to submit a research paper, and report facts only from each venue's own website.
The paper, described without its title: a public benchmark and an open-source tool that test whether an organization's past online controlled experiments (A/B tests) can forecast the outcome of the next one. It uses two public archives of concluded A/B tests, a rolling backtest with proper scoring rules, calibration checks, an abstention rule and sample-size gates. Its findings are mostly negative or modest and are declared exploratory. One author, no affiliation with a university or company lab. A public code repository and a preprint are planned. In its current form the body is 28 pages in the ACM two-column format, with a 15 page appendix.
Do not search for or mention any title, author name, repository name or email address.
Consider at least: the KDD research track and its datasets and benchmarks track, the NeurIPS track for datasets, benchmarks or evaluations, ICML, The Web Conference, AISTATS, UAI, CODE@MIT and other venues on online experimentation, relevant workshops, and the journals TMLR, DMLR and the Journal of Machine Learning Research. Add any venue you find that fits better.
For each venue report, each with the URL of the venue's own page and today's date as the fetch date:
1. the next submission deadline after today, and the abstract deadline if separate; say which year's call the page belongs to, and say "not yet announced" when the next call is not posted, giving last cycle's date as an estimate marked as such;
2. page limit for the body, what counts toward it, and whether appendices or supplements are unlimited;
3. template and format;
4. anonymity rule, and whether a public preprint and a public code repository are allowed before and during review;
5. required parts: checklist, ethics or limitations statement, dataset documentation, artifact or reproducibility rules, license rules;
6. the review criteria in the venue's own words, and whether negative results, benchmarks and tools are in scope;
7. dual submission policy;
8. the most recent acceptance rate the venue itself published, or "not published".
Then rank the three best fits for this paper, weighing topic fit, how the venue treats modest or negative results, how much the paper would have to be cut, and whether the next deadline can be met. State what is uncertain. A fact found only on a third-party site is marked unconfirmed.
Save the report to .claude/fleet/red-team-2026-11-10/venues.md.
```

- [ ] **Step 2: Check the scout's report.** Every date and page limit has a URL on the venue's own domain and names the year of its call. Fetch the pages behind the top three venues' deadlines and page limits again and confirm them. Mark anything that cannot be confirmed.

- [ ] **Step 3: Present the ranking to the user** as a table of venue, next deadline, page limit, what the paper would need to change, and the uncertainty. Recommend one. Ask the user to choose. The plan stops here until the user answers.

- [ ] **Step 4: Write `venue-requirements.md`** for the chosen venue: its items 2 to 7 from `venues.md`, with URLs, and the venue's reviewer form or review criteria quoted in full where the venue publishes them.

### Task 3: Stage 1, two cold readers and the venue reviewer

**Files:**
- Create: `.claude/fleet/red-team-2026-11-10/r1-newcomer.md`
- Create: `.claude/fleet/red-team-2026-11-10/r2-referee.md`
- Create: `.claude/fleet/red-team-2026-11-10/v1-venue.md`

**Interfaces:**
- Consumes: `brief-common.md`; `paper/main.pdf`; for V1, `venue-requirements.md`.
- Produces: three reports with page references.

- [ ] **Step 1: Launch all three in one message**, each a fresh general-purpose agent, each told to read only `paper/main.pdf` (in page ranges of at most 20) and to open no other file in the repository, except that V1 also reads `venue-requirements.md`. Tasks 3 and 4 do not depend on each other, so their nine agents may run at the same time.

R1, the newcomer, adds to the common brief:

```text
You are an experimentation practitioner. You know what an A/B test is and basic statistics. You know neither archive and none of this project's terms.
Read pages 1 to 28, the body, once, front to back. Open the appendix only where the body sends you.
Report: (a) in your own words, what the paper claims, in five sentences; (b) every term used before it is defined or never defined; (c) every sentence you had to read twice, and the question it left; (d) every place where a result is stated without saying what to conclude from it; (e) whether the abstract's claims match what the body delivered.
```

R2, the referee, adds:

```text
You are a statistician refereeing for a venue that values honest negative results. Read the whole paper.
Report: (a) the argument as a numbered chain from the research questions to the conclusion, each link marked sound, weak or broken, with the page that carries it; (b) every claim stronger than the evidence shown for it; (c) every analysis choice that could have been made after seeing results and is not declared as such; (d) every comparison whose baseline or unit is unstated; (e) what a reader would need, and is not given, to reproduce the headline numbers; (f) the three objections you would raise first.
```

V1, the venue reviewer, adds:

```text
You are an experienced reviewer for the venue described in .claude/fleet/red-team-2026-11-10/venue-requirements.md. Read that file first, then the whole paper. Judge the paper only by that file's rules and criteria, not by rules you remember.
Report:
(a) Compliance: one line per rule in the requirements file (page limit, format, anonymity, required statements and checklists, dataset and artifact rules), marked met, not met or cannot tell, with the page that shows it.
(b) The review this venue would write: summary, strengths, weaknesses, questions to the authors, and a score on each of the venue's criteria using its own scale where the file gives one. Say which weaknesses would lead a reviewer to reject.
(c) The reasons for a desk rejection, if any.
(d) Fit: what this venue's readers would value in the paper, and what they would see as out of scope or too long.
(e) If the body exceeds the page limit: which sections, tables and figures carry the argument and must stay, and which could move to the appendix, with an estimate of pages saved by each move. Do not rewrite anything.
(f) The ten changes most likely to move a reject to an accept, most valuable first, each a finding in the format below. Do not propose a claim the paper's evidence does not support: a change that makes the paper more attractive and less true is not a finding.
```

The body ends with the conclusion on page 28 of the 45 page build. Confirm that page before launch and correct the range if the build has changed.

- [ ] **Step 2: Verify each report** starts with the required opening line. R1 and R2 must hold part (a); V1 must hold one compliance line for every rule in `venue-requirements.md`. A report that fails this is rerun with a fresh agent, not continued.

### Task 4: Stage 2, six checkers

**Files:**
- Create: `.claude/fleet/red-team-2026-11-10/c1-frontmatter.md` to `c6-consistency.md`

**Interfaces:**
- Consumes: `brief-common.md`. The checkers do not see the Stage 1 reports or the venue files.
- Produces: six finding files with `file:line` references.

- [ ] **Step 1: Launch all six in one message**, each a fresh general-purpose agent, each writing only to its own output file. Each brief adds:

```text
Read your slice first as a reader, start to finish, and note what does not follow or is unclear. Only then open reports and code to test what the text says.
Work at four levels: sentence (true, follows from what it cites, needed), paragraph (one job, finished), section (delivers what it promises), and your slice's part in the paper's argument.
Sources of truth: the reports under paper/data/run8-randomization-window (read with `uv run python`), the code under src/mootcourt and scripts, DATA.md and docs/method.md. A `% src:` comment above a sentence names where its numbers should come from: open the key and confirm it is the quantity the sentence claims, not only that the digits match.
Generated tables under paper/tables are never edited by hand; if a table is wrong, name the spec under paper/summary_tables.
```

and its slice:

| Checker | Slice |
|---|---|
| C1 | `paper/main.tex` from the abstract through the end of Section 3 (problem setting and data), with `paper/sections/related-work.tex` and `paper/sections/landscape.tex` |
| C2 | `paper/main.tex` Section 4 (method) and Section 5 (evaluation protocol) |
| C3 | `paper/sections/results.tex` |
| C4 | `paper/sections/results-b.tex` and `paper/sections/ablations.tex` |
| C5 | `paper/sections/hypotheses.tex`, `discussion.tex`, `limitations.tex`, `reproducibility.tex`, `conclusion.tex` |
| C6 | The whole paper including `paper/sections/appendix.tex`, every caption and `paper/dist/metadata.md`, for one thing only: the same number, term, count or claim stated differently in two places, and a claim in the abstract, introduction or conclusion that the body does not carry |

- [ ] **Step 2: Verify each file** starts with the opening line and that every finding has all six fields. Send a checker back once for missing fields; rerun it fresh if the second file still lacks them.

### Task 5: Stage 3, two adversarial verifiers

**Files:**
- Create: `.claude/fleet/red-team-2026-11-10/verified-a.md`
- Create: `.claude/fleet/red-team-2026-11-10/verified-b.md`

**Interfaces:**
- Consumes: the nine files of Tasks 3 and 4.
- Produces: every finding id with a verdict `confirmed`, `refuted` or `unresolved`, and the evidence.

- [ ] **Step 1: Launch two fresh general-purpose agents in one message.** Verifier A takes `r1`, `r2`, `v1` part (f) and `c6`. Verifier B takes `c1` to `c5`. Each gets the common brief and this addition:

```text
Your job is to refute findings, not to add them. For each finding, open the quoted location and the report or code it names, and try to show the paper is right and the reviewer wrong.
Verdicts: confirmed (you tried and could not refute it; give the report path, key and value, or the quoted text, that settles it), refuted (give the evidence), unresolved (say what would settle it).
For a reader's "unclear" finding, the only refutation is a quotation from the paper, earlier than the point of confusion, that answers the question.
Also check each proposed replacement: does it state anything no report holds, or break a writing rule? Record that beside the verdict.
```

- [ ] **Step 2: Verify** that the number of verdicts equals the number of findings in the files each verifier was given. V1's compliance lines, review and scores are not findings and get no verdict; the lead checks its compliance lines against the PDF in Task 6.

### Task 6: Merge, check and present

**Files:**
- Create: `.claude/fleet/red-team-2026-11-10/findings.md`

**Interfaces:**
- Consumes: the two verifier files and the nine report files.
- Produces: the list the user decides on.

- [ ] **Step 1: Merge by location.** Group confirmed and unresolved findings that touch the same sentence or paragraph. Where two proposed fixes conflict, keep both and say so.
- [ ] **Step 2: Keep every reader confusion** unless a verifier refutes it with an earlier quotation from the paper.
- [ ] **Step 3: Check each proposed fix against its report** by opening the key. Drop any number no key holds, and say that the fix was changed. Check each "not met" line of V1's compliance list against the PDF and the requirements file.
- [ ] **Step 4: Report the counts to the user**: findings raised, refuted, unresolved and confirmed, by severity, and which reviewer raised each.
- [ ] **Step 5: Present the venue report first**: the compliance list, the predicted review and scores, and what would have to move to meet the page limit. Ask the user whether to plan a cut before deciding on sentences. If the user wants a cut, findings in text that would move to the appendix are set aside, not discarded.
- [ ] **Step 6: Present the remaining findings** in the order broken, weak, unclear, minor, in the format of the paragraph review: the quoted words, what was checked, the problem, the proposed text, and "Do you accept this?". Present the chain from R2 before any sentence, since a broken link outranks one.
- [ ] **Step 7: Record each decision** in `findings.md`.

### Task 7: Apply what the user accepts

**Files:**
- Modify: the paper sources named by each accepted finding
- Modify: `paper/reviews/claims.md`

- [ ] **Step 1: Apply only accepted findings**, adding a `% src:` line above every prose line that carries a number and a row in `paper/reviews/claims.md` for every new or changed claim.
- [ ] **Step 2: Run the `paper-check` skill.**

Expected: `make tables` changes no table that was not meant to change; `make paper` builds with no undefined reference and no overfull box; `scripts/paper_audit.py` reports 0 unmatched and 0 unresolved; `scripts/claims_audit.py` exits 0; the six paper test files pass.

- [ ] **Step 3: Recheck the abstract** in `paper/dist/metadata.md`: under 1,920 plain-text characters and in agreement with the PDF's abstract.
- [ ] **Step 4: Commit only when the user asks.**
