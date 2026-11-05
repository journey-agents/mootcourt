# Round 03 confirmation pass, Reviewer R6

Reviewer: R6
Role: practitioner and documentation reviewer
Commit: c7dbfd0 (release 1.0.0; tag v1.0.0 is d9d06ed, c7dbfd0 adds the Zenodo DOI line)
Date: 5 November 2026

No new blocking or major finding. Checks run: file reads and `git diff a839b2c..c7dbfd0`, `uv run pytest tests/test_round02_b.py` (25 passed), `uv run ruff check` (clean), `pytest --collect-only` (1369 tests), `scripts/verify_readme_numbers.py --reports paper/data/run7-tie-rank` (3224 checked, 0 mismatches), and the README's six sample commands in a scratch project folder under `~/.cache` with the gates file removed before the backtest (deleted afterwards). The page runner and the test suite were not rerun, as instructed; the pages' regenerated blocks (all 17 snapshot ids on the README, the command guide and the tutorials read 20261105) are the evidence that the outputs shown are current.

## 1. Round 03 findings at c7dbfd0

- R6-F1 (minor, R6.4 and R6.11; letter: Fixed). Closed. docs/tutorials/03-reproduce-upworthy.md line 110 reads "That quick file is sized by test at the simulated base rate nearest the archive's own (0.09, the rate the published gates read too), so the decidability columns already match the published ones. The Bonferroni-adjusted bounds of the pooled table differ in the fourth decimal until the challengers are in the table (`make challengers`, about 6 minutes), because the family of intervals then grows from 20 to 52"; line 114 says the same for the comparison step. The note line in src/mootcourt/cli.py lines 525 to 529 ends "The adjusted bounds of the report do not read the gates: they depend on the family of intervals, 20 intervals for the ladder alone and 52 with the challengers", and my sample backtest with the gates file removed printed exactly that line. docs/method.md call 258 carries "Correction, 5 November 2026 (round 03, R6)" naming the family as the measured cause.
- R6-F2 (minor, R6.6; Fixed). Closed. `grep` finds no "The columns `decidable` and `decidable_research`" sentence in README.md or docs/tutorials/01-first-card.md; docs/concepts.md line 128 reads "keeps the earlier base rate of 0.30 in the JSON and on the results page as a second verdict".
- R6-F3 (minor, R6.6; Fixed). Closed. src/mootcourt/report.py lines 404 to 410 leave out a column that is null on every row and print "Columns not computed (null on every row) and left out: ..."; my sample report's "P2 selection by cell" table has no `half_life_days_median` column and line 384 reads "Columns not computed (null on every row) and left out: half_life_days_median."; `test_r3_the_report_tables_omit_a_column_that_is_null_on_every_row_and_say_so` and `test_r3_the_p2_selection_table_of_the_sample_report_drops_its_all_null_half_life_column` (tests/test_round02_b.py lines 442 and 453) passed.
- R6-F4 (minor, R6.3; Fixed). Closed. docs/commands.md line 234: "about 20 to 25 seconds for a few hundred rows, most of it writing the report, and about 5 minutes for 18,000 rows" (its block: `the whole run 19.8 s`; tutorial 3's block: `246.5 s`); docs/tutorials/02-your-own-archive.md line 7 "about a minute and a half" and line 193 "about twenty seconds here" (its block: `18.6 s`); docs/tutorials/01-first-card.md line 45 "about 30 seconds ... can take a minute" (its block's last gate at `28 s elapsed`).
- R6-F5 (minor, R6.4; Argued). Argued and accepted. paper/reviews/rubric.md line 106 rewords the last clause, dated 5 November 2026 (decision 12), to "sized at the nearest simulated base rate, with the card and the report card saying which rate was used and the cell's own rate", which is what the pages now document; the redraw stays suggestion R6-s4; no sentence of the paper rests on the sample's rate. I accept: the mitigation I called the right one is in place, and a redraw would move the sample fixture and every tutorial output at the cap.
- R6-F6 (minor, R6.5; Fixed). Closed. docs/reference/card.md line 21 names the keys with an example, `{"p_win_team": 0.4, "point_team": 0.02}`; docs/tutorials/05-serve-http-and-mcp.md line 50: "To record your own forecast with the card, add `"team_forecast": {"p_win_team": 0.4, "point_team": 0.02}` to the request body".
- R6-F7 (nit, R6.11; Fixed). Closed. `grep -rn "python scripts/" README.md docs/` finds no line that is not `python3`.
- R6-F8 (nit, R6.13; Argued). Argued and accepted. CONTRIBUTING.md line 49: "The outputs shown in the README, the command guide and the tutorials are regenerated in one pass with `python3 scripts/render_tutorial_outputs.py --write --slow`, so their snapshot ids carry one date. Re-run it before a release and put its date in the release notes."; every snapshot id on those pages reads 20261105 and CHANGELOG.md line 7 reads "## [1.0.0] - 2026-11-05". I accept that the ids are the dated statement and that a separate line would drift. One suggestion below.

Closed: 6. Argued and accepted: 2. Not closed: 0.

## 2. Rubric items R6.1 to R6.14 at c7dbfd0

R6.1, R6.2, R6.3, R6.4 (under the amended clause), R6.5, R6.6, R6.7, R6.8, R6.9, R6.10, R6.12 and R6.13 pass on the evidence above and on the unchanged pages (the gate sentence is still one 527-character string on the FAQ, tutorial 2 and tutorial 6; the install and troubleshooting pages are unchanged apart from F7). R6.14 applies to later rounds only; no test for it exists yet (tests/test_docs_run.py still checks gate sizes only).

One item still fails. R6.11 (nit): the timings for `moot init` disagree across pages. docs/tutorials/01-first-card.md line 45 now says "about 30 seconds", while docs/quickstart.md line 21 ("takes about 20 seconds") and docs/commands.md line 19 ("About 20 seconds on the internal disk") were not changed, and the regenerated blocks on all four pages show the last gate at 26 to 28 s elapsed. Fix: "about 30 seconds" on the two pages.

## 3. Open items at the cap

R6-F5 may stay listed in Section 9 for publication. The listing is accurate as the letter words it: closed by the reworded clause of R6.4, the redraw kept as R6-s4 for the release after 1.0.0, and no sentence of the paper rests on the sample ledger's rate. The sentence a reader needs is on the report card and the card themselves.

## 4. Final verdict

Recommendation: accept
Scores (1 to 5): novelty 3, correctness 4, rigor 4, clarity 4, reproducibility 5, code 4
High-quality paper worth publishing at a top venue: yes. For a datasets-and-benchmarks track: a powered negative stated first, every printed number traced to a report key, and a tutorial that reproduces every score and decidability column of the headline table from a clean clone, with the one remaining fourth-decimal difference now explained correctly.
High-quality code package worth publishing: yes. The tutorials are executable documents whose outputs match the pages, the card and the report explain themselves without the paper, and a new user runs the package on their own archive within an hour.
Remaining concerns: [R6.11, nit: `moot init` timing reads 20 seconds on the quickstart and the command guide and 30 seconds in tutorial 1 against blocks of 26 to 28 s]; [suggestion: the 1.0.0 entry of CHANGELOG.md could name the regeneration pass that CONTRIBUTING line 49 says the release notes carry]; [suggestion: the R6.14 documentation test, so that a duration or base rate quoted in prose is checked against its block the way gate sizes are].
