# Round 03 response letter

Paper version under review: a839b2c. Code version under review: a839b2c. Written 5 November 2026 by the launching team against the working tree that holds the round 03 fixes, which release 1.0.0 carries (the package version is 1.0.0 and the CHANGELOG is dated today); "release 1.0.0" below names that commit. Round 03 is the cap round of `paper/reviews/protocol.md`: the last planned round under the convergence plan, after which the open minors are listed here and in Section 9 and the paper is released. Every finding of the six reviews in hand (R1, R2, R3, R5, R6 and R7, the fresh area chair the protocol adds in round 03) is answered in the reviewers' order with one of the protocol's three marks, Fixed (what changed, with the design call or the pass that holds it), Argued (no change, with the reason) or Suggestion (no change in the round). Numbers are quoted from the report files under `paper/data/run7-tie-rank` by file and key. Finding ids follow `.claude/fleet/round03-triage.md`: `Rk-Fn` is the nth bullet of reviewer k's Findings section. The decisions of the launching team that bind the answers are numbered as in `.claude/fleet/round03-decisions.md`.

Section numbers refer to the paper at release 1.0.0: 1 Introduction, 2 Related Work, 3 Problem Setting and Data, 4 Method (4.2 the ladder and the challengers, 4.3 abstention, the card and the loop), 5 Evaluation Protocol, 6 Results (6.1 to 6.8 as before), 7 Ablations and Learning Curve, 8 Discussion, 9 Hypotheses, Limitations and Ethics, 10 Reproducibility, Appendices A to F.

## Re-run experiments

One Tier C stage ran once in this round, `scripts/run_experiments.sh --only extras-upworthy` (call 271, decision 24), on a copy of run 7's inputs at the round's commit with the round 03 change to `scripts/paper_extras.py`; the only file replaced is `paper/data/run7-tie-rank/paper-extras-upworthy-20261103-4bfb354b87e3.json` (through `scripts/assemble_run_folder.py --update`, a checksum over every other file unchanged, a dated README line). It adds two keys and moves no existing number: `p1_minus_p0_by_origin` (the paired P1 minus P0 log-score difference by origin with by-test intervals at 500 resamples: pooled 0.1493, clear of zero at all nine origins, narrowest January 2015 0.0681, 0.0384 to 0.0972) and `issued_ece_by_origin` (the ECE of the issued cards with the null clustered at each origin's own design effect, 500 draws: pooled 0.01508 at percentile 100.0, inside the central 90 percent at 4 of the 8 origins that issue cards; on all rows 4 of 9). Every other change of this round is Tier A (text) or a small Tier B (code that moves no number, calls 268 to 273, with `make quick-check` passed and the sample fixture unchanged).

## Reviewer R1, statistician

**[minor] [R1.15] Four hypothesis parts are not read by name with the measure the hypothesis names, its number and its interval: H1 part 1 on points, H3 part 1 on the pooled ECE of all rows, H3 part 2 without the shipped coverage intervals, H4 part 3 on the pooled abstention rate.** (R1-F1)
Fixed (decision 5; call 271; pass 12): Section 9 reads each part by name with its measure and interval. H1 part 1: P1 is above P0 on the log score at every origin after burn-in, and paired by test the difference at the narrowest origin, January 2015, is plus 0.068 (0.038 to 0.097) and clear of zero at all nine origins (`p1_minus_p0_by_origin.by_origin[origin=2015-01-01]`, `by_origin_clear_of_zero` 9). H3 part 1: the ECE of issued cards falls inside the central 90 percent of the null at 4 of the 8 origins that issue cards, not at most of them, and pooled sits at the 100th percentile, so the part fails (`issued_ece_by_origin.issued`). H3 part 2: coverage holds pooled at 81 percent (80 to 82) and 89 percent (89 to 90), within 5 points of nominal (`coverage_80_lo`, `_hi`, `coverage_90_lo`, `_hi`). H4 part 3: abstention is 14 percent pooled and 8.8 percent after the burn-in origin, below 30 (`tables.abstention[cell=ALL].rate` 0.141466 of 13,247 rows, `tables.origins[origin=2013-04-01]` 781 rows at `abstention_rate` 1.0, so 1,093 of 12,466 rows after it). No verdict changes. Register C27, C30 and C33 requoted; C130, C131, C133 and C134 added.

**[minor] [C105] "Precedents that add nothing measurable on this archive" is unqualified while Section 6.2 reads the admitted pairs as a cancellation of two measurable movements.** (R1-F2)
Fixed (pass 12): Section 8 reads "precedents that add nothing measurable pooled on this archive"; C105 requoted.

**[minor] [R5.7] The seed-spread column of Table learning-detail is blank in the 1.00 row because the full history is one fit, and the caption does not say so.** (R1-F3)
Fixed (decision 7; pass 12): the caption reads "the spread of that skill over the 20 seeds (blank at the full history, which is one fit)".

**[nit] [R5.12] The Section 5 paragraph "One reading rule changed after the data were seen" appears twice in a row, and both copies render.** (R1-F4)
Fixed (decision 3; pass 12): one copy is kept; `grep -c` of the paragraph's first words in `paper/main.tex` is 1, and the PDF built from release 1.0.0 carries one copy.

**[nit] [R1.14] [C15] "The prior equals it by construction" names the arm-count-matched order; by construction the prior equals a random order within cell, and its difference from the matched order is a measurement within noise.** (R1-F5)
Fixed (decision 2; pass 12): the abstract reads "the prior, one number per cell, sits at it (minus 0.004, within noise)" (`tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung=P1].diff_matched` minus 0.004270, minus 0.012137 to 0.005350; `constant_within_cell` true), and the H5 verdict of Section 9 reads "failed for the prior, which ranks by cell only (its win probability is one number per cell and origin) and sits at the matched order within noise (minus 0.004, minus 0.012 to 0.005)". C15 re-keyed to the matched difference, C38 requoted, C129 added.

**[nit] [R1.14] [R5.12] "The one Brier skill interval that clears zero" means the one above zero (prior-normal and the cautionary run clear it below), "the two whose intervals clear zero" holds in the rung's favour only, and the paired column prints two lower bounds of minus 0.00002 as 0.0000.** (R1-F6)
Fixed (decisions 28 and 29; call 272; pass 12): Section 7 reads "the one Brier skill interval above zero ... (the two below zero, the prior-shape and the cautionary rows, are read in their own places)" and "whose intervals clear zero in the rung's favour", contribution 3 reads "the two paired intervals in the rung's favour", and the paired column of Table ablations-upworthy prints five decimals, so the two kappa rows' lower bounds, minus 0.00002, are seen below zero; the caption says so.

Suggestions (R1-s1 to R1-s3): recorded under Suggestions below.

Questions. (1) The run folder's file is the record (the second rerun of round 02 and now the third of this round); the data root's copy was replaced by the run folder's before the documentation was rendered, so a regeneration from the data root finds every key. (2) Yes: `issued_ece_by_origin` ships the per-origin percentile of the issued cards, and Section 9 says the registered "at most origins" part fails at 4 of 8 origins inside while the pooled reading is unambiguous (100 on all rows and on the issued rows); that two of the four outside are within four draws of the line is R1's reading of the file and is not claimed in the paper. (3) Yes: `p1_minus_p0_by_origin`, 500 resamples, the count stated in the key and in the src; Section 9 quotes January 2015 and says the difference is clear of zero at every origin. (4) A fifth decimal in the paired column (call 272).

## Reviewer R2, experimentation platform engineer

**[minor] [R2.15] (a) A card for a row the ledger already holds, with its result, is accepted at issue on the command, the service and the tool, and `--now` is the path by which a backdated card enters the scored record; (b) the timing rule names no start, so a card for a late-added arm counts as pre-launch for the contrast while the test's data had been accruing.** (R2-F1)
Fixed (decision 13, call 268; pass 12): `ledger.check_row_cell` refuses any row the ledger holds (the row's own cell raises `RowHeldError`, "row id X is in the ledger with its result; a card for it would not be pre-launch evidence") on the command (exit 2), the service (422) and the tool, with three tests and the manual's and the card page's sentences; Section 4.3 reads that the join's guard reads the contrast's own start (on the headline archive the later of its two arms' creation times), so that a card for a variant added to a running test is pre-launch evidence for that contrast and not for the test, and the card page says the same for the headline archive. Tutorial 5's example moved to a row the sample ledger does not hold.

**[minor] [R6.10] The cell-mismatch refusal exits 1 where the three sibling refusals at issue exit 2, and the commands page documents the 1.** (R2-F2)
Fixed (decision 14, release 1.0.0): the explicit handler is removed so the wrapper maps the refusal to exit 2; the commands page and the operations manual read "(exit 2; the service answers 422)" and state the convention (exit 1 for a clash with the store, exit 2 for an input error).

**[minor] [C86] "Covered 89.5 percent of 11,790 joined outcomes" names the larger set: the replay joins an outcome to all 13,247 cards and measures coverage over the 11,790 outcomes of issued cards.** (R2-F3)
Fixed (decision 8; pass 12): Section 6.6 reads "joined an outcome to every card (13,247), covered 89.5 percent of the 11,790 outcomes of issued cards with the card's 90 percent interval (an abstained card shows no interval)" (`totals.outcomes_joined` 13247, `coverage_90_all_n` 11790), and the replay caption reads the coverage as the issued cards'; C86 requoted, C132 added.

**[nit] [R2.14] The two post-launch display fields of the deployment-shaped loader stay at the top level of its features, outside the post-launch block, by decision 6.** (R2-F4)
Argued (decision 19, from round 02's decision 6): nothing changes in the code this round, as R2's own words say; the rubric item is amended with a dated clause (the ledger-format page names the fields as post-launch display fields kept outside the block for the run folders' identifiers, with the release at which they move), and Section 9's list of argued items now carries the fields with the reason, the release and the reading side closed by the allow-list.

Suggestions (R2-s1 to R2-s5): recorded under Suggestions below.

Questions. (1) The amendment, dated 5 November 2026, under decision 6; the move itself is scheduled for the release that changes snapshot ids, at or after version 1.0.0. (2) "The ledger holds the row": the refusal reads the ledger's row ids at the moment of issue, and on this ledger format, which holds concluded rows, that is the row with its result; the manual and the card page say which the check reads, so a ledger that ingests rows at launch would refuse at ingest, which the manual states as the convention. (3) The contrast's own start, the rule the code reads, kept; Section 4.3 and the card page say so, and the replay's numbers do not depend on it. (4) Yes: exit 1 is reserved for a clash with the store (a frozen card with different content) and exit 2 for input errors, the cell-mismatch refusal now among them; the commands page states the convention in one line. (5) The registry history does not record the summary refresh of decision 10; the run 7 README and the round 02 letter record it, and a history entry for a summary refresh is a suggestion for the release after 1.0.0.

## Reviewer R3, machine learning reviewer

**[blocking] [R3.3] [C121] Section 7 prints P1's full-history raw Brier score as 0.0539 where the key holds 0.053846 and Table learning-detail prints 0.0538: a double rounding of the source comment's five-decimal figure.** (R3-F1)
Fixed (decisions 22 and 30; call 273; pass 12): Section 7 prints 0.0538 and its source comment carries the leaves (0.053896, 0.053887, 0.053846); the round 02 letter carries a dated correction of its R3-F6 answer; the number audit now matches a printed number against the named key's leaf first and treats a match against the comment's digits alone as a failure when the comment is itself a rounding of a leaf (three tests, red on the double-rounded 0.0539), and under that rule it reports every number of the paper matched (769 checked, 0 unmatched) with no further digit flagged. The reading does not move: P2's 0.0535 stays below P1's 0.0538.

**[minor] [R3.9] [R1.3] The pooled realized P2 minus P1 difference prints with two intervals, a second bootstrap draw of the same statistic in Table guard-pairs-rows beside Table guard-pairs's, and neither caption says so.** (R3-F2)
Fixed (decision 29; call 272; pass 12): both tables print the one interval of `guard_pairs.summary` (0.0010, minus 0.0007 to 0.0025) on their pooled lines, and the caption of Table guard-pairs-rows says the pooled line's mean difference and its interval are those of Table guard-pairs, one draw for both tables, the location and scale parts being its own.

**[minor] [C23] "The one Brier skill interval that clears zero ... is one of 33" is right about what is not read as a finding and wrong in its count: three intervals exclude zero, one above and two below.** (R3-F3)
Fixed (decision 29; pass 12): "the one Brier skill interval above zero ..., is one of 33 in the table and is not read as a finding (the two below zero, the prior-shape and the cautionary rows, are read in their own places)".

Suggestions (R3-s1 to R3-s5): recorded under Suggestions below; R3-s3 (the zero-rounded bounds) and R3-s4 (the empty seed-spread cell) are done with R1-F6 and R1-F3.

Questions. (1) Yes (call 273): the first tier is the leaf of the key the source comment names, a match against the comment's own digits alone fails when the comment is a rounding of a leaf, a derived number that no leaf carries still passes on its comment, and the audit prints the tier of every match. (2) The pooled line of Table guard-pairs-rows is read for the mean difference only through Table guard-pairs's interval, which it now prints; it keeps the location and scale parts, which are its own. (3) Adopted as rubric item R3.15, dated 5 November 2026, applying to any later round. (4) Adopted as rubric item R3.16, dated the same day. (5) Done in the code and the extras (the header field `p2_selection` written by reports from round 02 on, the comparison shipped as `p2_selection_comparison`); it is recorded under R3.9's reading rather than as a separate item, since the two adopted items cover the audit and the intervals and the comparison behind the one change of default is in the folder.

## Reviewer R4, reproducibility chair

R4 recommends accept: 6 of 6 round 02 findings closed, 14 of 14 rubric items passed, one new minor, two suggestions. From a clean clone of a839b2c: the suite 1,354 passed, 1 skipped (pdflatex absent), 0 failed; the timed run from an empty data root with a real download exits 0 at every stage in 2,283.1 s; its seven reports against the run folder, 55,940 numbers, 0 differ at 1e-9; the extras file regenerated from scratch; the leakage audits zero on all 31 rungs and identical to the shipped files; `make tables` leaves the tree clean at three hash seeds; `make arxiv-check` exits 0.

**[minor] [R5.9] Two clauses of the round 02 letter do not match the artifacts: the sample fixture "unchanged", and the source of R4's 22,311 s and 3 h 49 min.**
Fixed (release 1.0.0): both corrected with dated lines at the end of `paper/reviews/round-02/response.md`. Nothing in the paper changes. The second error was the launching team's: the figures came from the run 7 driver's stages file and logs, as R4's round 02 review said.

Questions. (1) Yes, as above. (2) No full driver rerun at the release commit: the release changes no scoring code after a839b2c, whose reports R4 found equal to the run folder, and item R4.5 passes under the reading R4 gave it. In its place the release check repeats the timed run on the release commit and compares its reports with the run folder at 1e-9 (`.claude/fleet/verification-s.md`). `run-log.json` in the folder keeps naming 82ba862, as the run 7 README says. (3) Not for 1.0.0: `scripts/compare_runs.py` stays a suggestion.

## Reviewer R5, area chair

**[minor] [C3, R5.1] The 250-word abstract lost the stand-in exception that qualified its leakage sentence: realized impressions, measured during the test, stand in for the unrecorded plan and enter the planned standard error, and Section 9 measures the leak.** (R5-F1)
Fixed (decision 1; pass 12): the abstract reads "in which no in-test outcome reaches a pre-launch forecast (one stand-in, realized exposure, its leak measured)" and contribution 1 reads "a planned-exposure standard error (from realized exposure where the archive records no plan, a stand-in whose leak Section 9 measures)"; C3 and C19 requoted from the paper as printed, the abstract's src naming the leak's key (0.0994).

**[minor] [C15, R5.1] "The prior equals it by construction" is not what the paper measures or argues; the H5 verdict's by-cell wording is the exact one, and C15 quotes a sentence the abstract no longer prints.** (R5-F2)
Fixed (decision 2; pass 12): as for R1-F5; C15 re-keyed to the measured difference and requoted from the abstract as printed.

**[minor] [R5.2, R5.7] The Section 5 disclosure paragraph and its source comment are present twice in a row and the built page prints both.** (R5-F3)
Fixed (decision 3; pass 12): one copy; the PDF built from release 1.0.0 carries one.

**[minor] [R5.5] The limitations list omits the one argued finding of the round 02 letter (the two post-launch display fields) and the two not-done items (the within-origin-and-cell comparison of issued against withheld rows; the one-runner-image job).** (R5-F4)
Fixed (decision 10; pass 12): the argued list carries the two display fields with the reason, the release at which they move and the reading side closed by the allow-list; the future-work list carries the within-origin-and-cell comparison; the one-runner-image job stays stated in Section 10, where R5 read it.

**[minor] [R5.9] Two statements of the round 02 letter do not match the artifacts: the first-reference order it reports omits three numbers, and it says 250 abstract words where the register and the round 01 correction block say 249.** (R5-F5)
Fixed (decision 11; pass 12): the round 02 letter carries a dated correction block (after round 03) with the order as built at a839b2c (2, 3, 4, 1, 5, 6, 7, 8, 39, 9, 10, 11, 12, 40) and one counting rule for the abstract (the whitespace-separated words of its text lines with the source comment lines removed: 250 at a839b2c and 250 after this round), applied in the register's pass 10 note and the round 01 block as well; this letter uses the protocol's three marks only.

Suggestions (R5-s1 to R5-s3): recorded under Suggestions below.

Questions. (1) Yes, both. (2) Yes, both (the measured minus 0.004 with its interval; C15 re-keyed and requoted). (3) Deleted; the PDF built from release 1.0.0 carries one copy (the duplicate entered between the launching team's build of 06:14 and the commit of 06:35, by a resumed edit script that did not recognise an insertion whose new text contained its anchor; the same class of slip recurred and was caught in this round's pass, which now greps the count). (4) Yes, with the release (at or after version 1.0.0). (5) 250, by the whitespace rule stated in the register's note and in both letters.

## Reviewer R6, practitioner and documentation reviewer

**[minor] [R6.4] [R6.11] Three sentences of tutorial 3's reproduction narrative contradict the run they describe (the quick file's rate, the decidability columns, the adjusted bounds), and call 258's diagnosis names the gates file where the cause is the Bonferroni family.** (R6-F1)
Fixed (decision 16, release 1.0.0): the backtest's note line reads that the adjusted bounds do not read the gates but depend on the family of intervals (20 for the ladder alone, 52 with the challengers), with a dated correction under call 258 and the test extended; tutorial 3 sections 4 and 5 say that the quick file is sized by test at 0.09, that the decidability columns match from the first run, and that reproducing the adjusted bounds needs `make challengers`; its blocks were regenerated.

**[minor] [R6.6] The README and tutorial 1 tell the reader to look at the columns `decidable` and `decidable_research`, which round 02 removed, and the concepts page says the backtest keeps the 0.30 base rate beside it as a second verdict.** (R6-F2)
Fixed (decision 17, release 1.0.0): the sentence is deleted from both pages, and the concepts page says the 0.30 verdict lives in the JSON and on the results page; the round 02 letter's "the README sentence is gone" is corrected by this answer.

**[minor] [R6.6] The column `half_life_days_median` of the report table "P2 selection by cell" reads n/a on every row: the round 02 "not computed" column under another word.** (R6-F3)
Fixed (call 270, release 1.0.0): the report renderer leaves out a column that is null on every row and ends the table with "Columns not computed (null on every row) and left out: ..."; two tests; the JSON is unchanged.

**[minor] [R6.3] Three timing sentences contradict their pages' own output blocks (the command guide, tutorial 2, tutorial 1's init).** (R6-F4)
Fixed (release 1.0.0, documentation): the command guide, tutorial 2 and tutorial 1 carry the timings R6 wrote from the blocks ("about 20 to 25 seconds for a few hundred rows, most of it writing the report, and about 5 minutes for 18,000 rows"; "about twenty seconds here" and "about a minute and a half"; "about 30 seconds" for the init with "can take a minute" kept).

**[minor] [R6.4] The quick gates of `moot init` are simulated at 0.09 while the sample ledger's own rate is 0.067, so the item's last clause does not hold; the report card and the card now say so in words.** (R6-F5)
Argued (decision 12, from R6's question 2): the sample is not redrawn (a redraw moves the sample fixture, the quick-check reference and every tutorial output, which is not a cap-round change); the last clause of R6.4 is reworded, dated 5 November 2026, to the behaviour the pages document (the quick gates sized at the nearest simulated base rate, with the card and the report card saying which rate was used and the cell's own rate), and the redraw stays suggestion R6-s4 of round 02 for the release after 1.0.0.

**[minor] [R6.5] The two JSON keys that make the card's Team forecast line say anything but "None provided" are named on no page a user reads.** (R6-F6)
Fixed (release 1.0.0, documentation): the `team_forecast` row of the card page names `p_win_team` and `point_team` with an example, and tutorial 5 carries a request that sets them.

**[nit] [R6.11] One `python scripts/download_data.py --verify-only` remains where every other page says `python3`.** (R6-F7)
Fixed (release 1.0.0, documentation): `python3`.

**[nit] [R6.13] No page states when the printed outputs were last regenerated, although the ids agree across the pages.** (R6-F8)
Argued (release 1.0.0's documentation): CONTRIBUTING names the one-pass regeneration of the README, the command guide and the tutorials with `python3 scripts/render_tutorial_outputs.py --write` and says that the snapshot ids on those pages carry its date (20261105 after this round's pass); a separate date line would drift from the ids at the next regeneration, so the ids are the dated statement, printed on every page that shows them, and the release checklist regenerates the pages in one pass before the tag.

Suggestions (R6-s1 to R6-s4): recorded under Suggestions below.

Questions. (1) Yes, the published pooled table's Bonferroni family of 52 includes the challengers by design, so P1's adjusted bounds are read in the family of every rung of the table; tutorial 3 says that reproducing them needs `make challengers`, and a ladder-only run's family of 20 is named there and in the backtest's note line. (2) No redraw; the clause reworded, dated (R6-F5). (3) Adopted as rubric item R6.14, dated 5 November 2026, applying to any later round.

## Reviewer R7, fresh area chair

**[minor] [C3] "No in-test measurement reaches a pre-launch forecast" needs one qualifier, since realized impressions stand in for the planned exposure and Section 9 measures that leak; contribution 1 takes the same clause.** (R7-F1)
Fixed (decision 1; pass 12): as for R5-F1, with R7's clause in the abstract ("one stand-in, realized exposure, its leak measured") and in contribution 1.

**[minor] [C15, C38] "The prior equals it by construction" and "failed by construction for the prior": the key gives that P1 cannot rank within a cell, not equality with the matched order; write what the number shows.** (R7-F2)
Fixed (decision 2; pass 12): "the prior, one number per cell, sits at it (minus 0.004, within noise)" in the abstract and "fails for the prior, which ranks by cell only ... and sits at the matched order within noise (minus 0.004, minus 0.012 to 0.005)" in the verdict, with "fails for the prior, which ranks by cell only" in Section 6.4; the adjusted bounds R7 quotes (minus 0.018 to 0.009) are in Table decision-intervals-upworthy.

**[minor] [C12, C24, C119, C122] "Recovers a fifth of it pooled" for a key of 0.180 whose interval lies wholly below a fifth.** (R7-F3)
Fixed (decision 6; pass 12): "about a fifth" in the abstract, contribution 3, Section 6.8 and Section 9, with 0.18 (0.16 to 0.20) printed where the number is read (Section 6.8); the tenth stays as printed; the four rows requoted.

**[minor] [R5.2] The plan fixes the six hypotheses and no reading rule; the pooled rule was written after the data, H2 and H3 are read pooled under it, and the shipped reports carried no per-origin calibration percentile.** (R7-F4)
Fixed (decisions 4 and 24; call 271; pass 12): Section 5 says that the plan fixed the hypotheses and no reading rule, that the pooled-interval rule was fixed in the paper after the data were seen, that H2's final-origin part and H3's most-origins part are read pooled under it, and that Section 9 reads H3's first part by origin as well, which it now does from the shipped `issued_ece_by_origin` (4 of 8 origins inside the central 90 percent, so the part fails); C26 stands, C30 and C134 carry the by-origin read.

**[minor] [R5.2] "Fixed in writing before the final runs ... the record is commit 145eaf7" lets a reader infer the hypotheses predate every run, while the commit holds the pre-launch-clean run's reports and the plan's section 1a reads the first run.** (R7-F5)
Fixed (decision 25; pass 12): Section 5 and Section 9 state the history as it was: the plan was written after the first two runs on the headline archive (the leaky relative-lift run of Section 6.1, which its section 1a reads, and the pre-launch-clean run), fixed in commit 145eaf7 beside the second run's reports, not changed afterwards, and before every run the paper reads; the reading rule was stated in the paper, not in the plan; the public copy was registered on 4 November 2026 after round 01; the plan's own status line is corrected in the paper and the register note, never in the registered file, and no sentence of the paper claims a prior registration ("the registered plan" and "the random order the plan registered" now read "the plan").

**[minor] [R5.7] The disclosure paragraph of Section 5 is printed twice.** (R7-F6)
Fixed (decision 3; pass 12): one copy.

**[minor] [R5.7] CRPS is used in Section 2 and defined in Section 5; SVD is used in Section 2 and defined in Section 4.2.** (R7-F7)
Fixed (decision 9; pass 12): each is defined at its first use in Section 2 and used as the acronym afterwards.

**[minor] [R5.7] Numbers the tables hold are stacked in four passages: contribution 3, Section 6.2's discrimination paragraph, Section 6.4's rung list and Section 7's second paragraph.** (R7-F8)
Fixed (decision 26; pass 12): contribution 3 reads as a contribution with no numbers, its sections named (C21, C22 and C23 requoted without numbers, the numbers registered where they are printed); Section 7's weight sentence reads the range with the table named and its contrasts-one numbers go to the table; Section 6.2's pooled AUC list reads the range from P0 to the recalibrated text classifier with the table named; Section 6.4 keeps the intervals for the text classifier, whose claim rests on them, and the point values for the other rungs; the intervals a claim rests on stay in prose under the rule of decision 26.

**[minor] [R5.7] One measured thing carries several names: the local empirical-Bayes challenger five, the significant-positive event two, the boosted model three.** (R7-F9)
Fixed (decision 9; pass 12): one name each, fixed at the definition in Section 4.2 and used in every sentence: "the local comparison set" (`local_eb` in the tables), "the significant-positive event" and "the boosted model" (GBM in the tables); no generated table label changed.

**[minor] [R5.7] Figures 1 and 2 are drawn at column width with 6 and 6.5 pt type and included at 0.62 of the column, so their labels print at about 4 pt.** (R7-F10)
Fixed (decision 15, call 269, release 1.0.0): the figure script draws both at 0.62 of the column with 8 pt type (the coverage panels stacked, the decision legend below), `make paper-figures` regenerated them with `figures.json` unchanged, and a test holds the size; the captions are unchanged. The taller figures and this round's added text move the end of the body from the foot of page 10 to the top of page 12 (30 pages in all).

**[nit] [R5.12] Figures are cited in the order 5, 4, 1, 2 and Tables 46 and 47 before 45; the two table groups are accepted from round 02.** (R7-F11)
Argued (decision 18): the appendix tables stay in two ordered groups (single-column, then two-column), each in reading order, and the appendix figures stay at the head of the appendix, because one exact reading order cost five pages in round 02; Section 9's argued list now carries the sentence "the numbering of the appendix tables in two ordered groups (single-column, then two-column) rather than one exact reading order, with the appendix figures cited from the body before its own two, kept because one exact order cost five pages".

**[minor] [R5.3] The Platt recalibration map and the median heuristic are borrowed ideas without a citation and without an entry in the related-work record.** (R7-F12)
Fixed (decision 9; pass 12): Section 4.2 cites the Platt chapter (`platt2000probabilities`: "Probabilities for SV Machines", in Advances in Large-Margin Classifiers, The MIT Press, 2000, pages 61 to 74, DOI 10.7551/mitpress/1113.003.0008, the 1999 preprint's title in the note) and the median heuristic's source (`garreau2017large`, arXiv 1707.07269), both fetch-verified on 5 November 2026 through Crossref by DOI and the arXiv page and recorded with their URLs in `paper/related-work.md` (83 entries, all cited).

**[minor] [R5.5] The argued list omits the two display fields and the deferral of the within-origin-and-cell comparison on which H4's "partly by composition" rests.** (R7-F13)
Fixed (decision 10; pass 12): as for R5-F4.

Suggestions (R7-s1 to R7-s3): recorded under Suggestions below.

Questions. (1) Yes, it was cheap and it is shipped: `issued_ece_by_origin` (call 271), and Section 9 reads H3's first part from it. (2) The history as decision 25 states it and Section 5 now says: the hypotheses were written after the first two runs on the headline archive (the leaky relative-lift run and the pre-launch-clean run), fixed in commit 145eaf7 beside the second run's reports, with the plan's section 1a reading the first run; they were not changed afterwards; the reading rule (the pooled interval as primary) was stated in the paper and not in the plan; the public copy was registered on 4 November 2026, after round 01; the paper claims no prior registration. (3) Adopted as rubric item R5.13, dated 5 November 2026, applying to any later round; the versioned entry-rules file it names is R7-s2 for the release. (4) A decidable deployment-shaped archive is the gap that matters most: the headline archive already shows what a second headline archive would test (transfer of a prior and of text features), while no public archive of deployment-shaped experiments is large enough for any gate, which is why Section 9 says "one archive of each kind"; the discussion is unchanged.

## Open items at the cap

The protocol's cap rule lists the open minors here and in Section 9 and releases the paper. After this round's fixes the items that stay open are:

- The numbering of the appendix tables and figures in one exact reading order (R7-F11, a nit under R5.12; decision 18). Section 9 carries: "the numbering of the appendix tables in two ordered groups (single-column, then two-column) rather than one exact reading order, with the appendix figures cited from the body before its own two, kept because one exact order cost five pages".
- Rubric item R2.14 read literally (R2-F4, a nit; decision 19), the two post-launch display fields of the deployment-shaped loader outside the post-launch block until the release that changes snapshot ids. Section 9 carries: "the two post-launch display fields of the deployment-shaped archive (the checkpoint count and the final offset in days), kept at the top level of its features outside the post-launch block until the next snapshot-changing release, because moving them rewrites every snapshot id the run folders cite, with the reading side closed by the feature allow-list and its test"; the item is amended, dated, so that it passes by the ledger-format page's naming.
- The sample ledger's own base rate against the quick gates' simulated rate (R6-F5): closed by the reworded clause of R6.4, with the redraw kept as R6-s4 for the release after 1.0.0; no sentence of the paper rests on it.
- R4's review needs no rerun beyond the extras stage (decision 20): its one finding was a correction to the round 02 letter, now made.

Not open: the two per-origin keys (R1-F1, R7-F4) were shipped (decision 24), the held-row refusal (R2-F1a) was built (decision 13), and the one blocking digit (R3-F1) was fixed with the audit changed to catch its class.

## Suggestions (recorded, not fixed in the round)

- R1-s1: print the closed form of the positive control's ceiling per cell beside the refit oracle and call it the normal approximation, since the refit Student-t oracle exceeds it in every cell (a new extras key).
- R1-s2: carried from round 02 unchanged: the first-order scaling sentence for a cell's gates; the gate lines of the package's learning-curve figure; the equal-mass ECE columns of Table ece-upworthy; the by-origin table's 200 resamples.
- R1-s3: the data root's copy of the extras file lagged the run folder's; settled by the copy made before the documentation was rendered (R1's question 1).
- R2-s1: two module docstrings keep "sealed" (`loop.py`, `mcp_server.py`); the paper's wording fits both.
- R2-s2: `moot card` has no `--ledger` option, so the check at issue reads the storage root's ledger; add the option or say so on the commands page.
- R2-s3: Section 4.3's "read-only service" against `POST /card`, which freezes the card it issues.
- R2-s4: `docs/method.md` calls 16 and 74 still call the earn-weight margin the promotion margin; a dated note at call 16.
- R2-s5: quote the card latency table in one sentence of Section 4.3 or the manual.
- R3-s1: the single-headline run of the challengers (carried; Section 9 lists it as not run).
- R3-s2: a held-out or marginal-likelihood estimate of P2's scale term (carried; Section 9 names it as future work).
- R3-s3 and R3-s4: done with R1-F6 and R1-F3.
- R3-s5: a clause in the caption of Table learning-upworthy that the curve's full-history point is the main backtest's final-origin fit to the last digit.
- R5-s1: a test that every register sentence of the abstract, the contributions and the Section 9 verdicts appears verbatim in the source.
- R5-s2: a build check that no paragraph of the LaTeX sources is repeated verbatim.
- R5-s3: carried from rounds 01 and 02: a stronger text representation as a fourth challenger; the cross-platform number once a second runner image runs.
- R6-s1: the backtest's note line could say what the quick simulation costs.
- R6-s2: the boxed panel of `moot backtest --source nosuch` and `moot reliability --source nosuch`; the one-exit-code convention settled in part by R2-F2.
- R6-s3: one line on the report card saying why the `random_matched` rows equal the `random` row on a ledger without features.
- R6-s4: the results page naming which rungs the interval family counts.
- R7-s1: the abstract's first sentence and the introduction's "almost never before one" are empirical claims about practice without a citation; cite a survey or soften them.
- R7-s2: a versioned `BENCHMARK.md` fixing the entry rules an entrant must follow (rubric item R5.13 from the next round).
- R7-s3: one sentence in Section 2 saying which single element of the protocol is new and which are assembled from cited parts.
- R4-s3: `docs/results.md` says `make ablations` and `make learning-curve` run the full sets, while the shipped curves come from the driver's `lc-S` stage with 20 seeds and seven fractions; the sentence could name the driver stage.
- R4-s4: the source comment of Appendix E's one-code-state sentence read "73 stages"; taken outside the round's count and corrected to 71.

## Diff of the paper's claims between the round 02 letter and this one, by claim id

Changed.
- The abstract (250 words, unchanged in count): the stand-in qualifier restored (C3, C19 for contribution 1); the prior at the matched order as a measurement (C15, re-keyed to `diff_matched`; C129 added); "about a fifth" (C12, C24, C119, C122); C10, C14 and C17 requoted after the cuts that kept the count.
- The hypothesis parts read by name with their measure and interval: C27 and C133 (H1 part 1, paired by origin), C30 and C134 (H3 part 1, the issued cards by origin, the part now read as failing), C130 (H3 part 2, the coverage intervals), C33 and C131 (H4 part 3, after burn-in); C38 (the prior ranks by cell only); C26 unchanged (the hypotheses fixed in writing before the final runs and unchanged since, with Section 5 now stating what the plan fixed and what it did not).
- "Nothing measurable pooled": C105. The replay's two counts: C86, C132.
- Contribution 3 without numbers: C21, C22, C23 (report, key and value none; the numbers registered where printed). Section 6.2's and 6.4's prose: C113, C72, C73, C74. One name per measured thing: no printed value moved.
- The digit of C121's clause: P1's raw Brier at the full history prints 0.0538 (the leaf 0.053846); C121's sentence unchanged.

Unchanged. The headline numbers: 0.149 nats over the base rate; Brier skill 0.0015 (minus 0.0018 to 0.0048) on 3,797 tests against a release gate of 250; the 100th percentile of the clustered null; coverage 1.000 to 0.655 across the deciles; the paired P2 minus P1 0.000447 (minus 0.000297 to 0.001191); the admitted pairs' pooled 0.00097 (minus 0.00073 to 0.00245, now the one interval of both tables); the decision values against the matched order; the positive control's admission 0.972 and pooled recovery 0.180 (0.164 to 0.197) with the tenth in the cell shaped like the real one; the cautionary run's minus 0.1074; the deployment-shaped archive undecidable at every gate; every percentile the paper prints. The register holds 134 rows (128 at the round's commit), 127 keyed, every keyed row resolving under `paper/data/run7-tie-rank` (`scripts/claims_audit.py` exit 0).
