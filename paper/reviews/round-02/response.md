# Round 02 response letter

Paper version under review: 9f725b1. Code version under review: 9f725b1. Written 5 November 2026 by the launching team against the working tree that holds the round 02 fixes, before the commit that carries them; "this commit" below names that commit. Every finding of the six reviews is answered in the reviewers' order with one of the protocol's three marks: Fixed (what changed, and the design call or the pass that holds it), Argued (no change, with the reason), Suggestion (no change in the round). Numbers are quoted from the report files under `paper/data/run7-tie-rank` by file and key. Finding ids follow `.claude/fleet/round02-triage.md`: `Rk-Fn` is the nth bullet of reviewer k's Findings section.

Section numbers refer to the paper at this commit: 1 Introduction, 2 Related Work, 3 Problem Setting and Data, 4 Method (4.2 the ladder and the challengers, 4.3 abstention, the card and the loop), 5 Evaluation Protocol, 6 Results (6.1 to 6.8 as in round 01), 7 Ablations and Learning Curve, 8 Discussion, 9 Hypotheses, Limitations and Ethics, 10 Reproducibility, Appendices A to F.

Decisions of the launching team that bind the answers below are numbered as in `.claude/fleet/round02-decisions.md` (decision 1, the H5 disclosure; 2, the H4 reading and the extras rerun; 3, the abstract and the track; 4, the artifact paragraph; 5, the single-headline run not run; 6, the two post-launch fields; 7, three rubric items for round 03; 8, the card's team-forecast options; 9, the guard-pairs resample count; 10, the card's cell verdict; 11, two one-line suggestions taken outside the count).

## Re-run experiments

One Tier C stage ran twice, `scripts/run_experiments.sh --only extras-upworthy`, on a copy of run 7's ledger, models and reports at commit 9f725b1 with the round 02 changes to `scripts/paper_extras.py`; the only file replaced is `paper/data/run7-tie-rank/paper-extras-upworthy-20261103-4bfb354b87e3.json` (through `scripts/assemble_run_folder.py --update`, a checksum over every other file unchanged). First rerun (125 s): the guard-pairs bootstrap at 500 resamples in place of 1,000 (`guard_pairs.summary.bootstrap_resamples` 500; the pooled interval minus 0.00073 to 0.00245, from minus 0.00071 to 0.00253; the point value 0.00097 unchanged) and the new key `issued_row_brier_skill` (P1 and P2 on the issued rows, the abstained rows scored on the withheld forecast, and all rows, with by-test intervals). Second rerun (84 s): the new key `p2_selection_comparison` (P2's log score under forward chaining minus under leave-one-test-out, per row, pooled and by origin, with the guard on and off, 500 resamples). The run folder also gained `stages.txt` (every stage of the driver with its exit code and seconds) and the README's lists of files against run 6. No other report moved. Every other change of this round is Tier A (text) or Tier B (code that moves no number; `make quick-check` passed after the batch, the sample fixture unchanged).

## Reviewer R1, statistician

**[major] [R1.8] The learning-curve tables print neither P1's raw Brier score, nor the subsample's own base rate, nor the seed spread, and the own-base column of Table learning-detail is a skill while the sentence introducing it says base rate.** (R1-F1)
Fixed (call 262, this commit): Table learning-detail now carries P1's raw Brier score, the base Brier score of the full history and of the subsample, P1's skill against the full-history base rate with its seed spread, P1's skill against the own base rate and the local set (`learning-curve-upworthy-20261103-4bfb354b87e3.json rows[rung=P1]` `brier` 0.05544 to 0.05385, `base_brier_own` 0.06020 to 0.05548 against `base_brier_full` 0.05548, `skill_seed_sd` 0.0359 to 0.0019); Section 7 reads "gives each subsample's own base rate and P1's raw Brier score beside it, with the seed spread", and the caption describes the columns. No rerun; the experiment stands.

**[minor] [C23] [R1.9] "No setting of the rung beats the prior" is flat, but two ablations clear zero on the paired log score and the table prints unpaired scores only.** (R1-F2)
Fixed (call 262; pass 10): Table ablations-upworthy prints the paired P2 minus P1 difference with its interval beside the unpaired scores (`tables.aggregate[cell=ALL,rung=P2].logscore_vs_p1` of each file); contribution 3 reads "no setting moves the paired log score in the rung's favour by more than a thousandth of a nat, and the two whose intervals clear zero, admission on exposure alone and one contrast per test, are read as the Brier excursion is, one of 33", and Section 7 reads the two intervals under that rule (admission on exposure alone plus 0.0009, 0.0003 to 0.0016, on 14,235 rows; one contrast per test plus 0.0005, 0.0004 to 0.0007), each under a thousandth of a nat, neither clear of zero on the Brier skill. Register C23 weakened.

**[minor] [C33] [R1.14] H4 names skill, Section 6.5 reads the issued rows on the log score, and on the Brier skill the sign reverses; the paper does not say so.** (R1-F3)
Fixed (decision 2, call 263, the extras rerun): `issued_row_brier_skill.rungs.P2` reads `issued` minus 0.001781 (minus 0.005599 to 0.002112) on 11,373 rows, `all` 0.001898, `abstained` 0.019853 (0.007824 to 0.033540) on 1,874 rows, with the event rates 0.0878 and 0.1105 and the base Brier 0.0804 and 0.1000 beside them; Section 6.5 compares the skill and names the composition, and Section 9 reads the first two parts of H4 as refuted and the third as holding, so H4 stays held in part. Register C33 and C80 rewritten, C125 and C126 added. Table trigger-ablation still prints the raw issued Brier score; the issued-row skill is in the text and the extras.

**[minor] [R1.3] The pooled interval of the eight admitted pairs rests on 1,000 resamples while every other interval uses 500, and neither the caption nor Section 6.2 states the count.** (R1-F4)
Fixed (decision 9, call 263): the extras rerun put the guard-pairs bootstrap at 500 (`guard_pairs.summary.bootstrap_resamples` 500; the printed interval minus 0.0007 to 0.0025 unchanged at four decimals); the caption of Table guard-pairs and the generated table's header state 500, and Appendix E's sentence that every interval uses 500 now holds.

**[minor] [R1.9] [C57] [C60] The tables without adjusted bounds are not labelled descriptive, and Section 6.2 reads two of their intervals as the result.** (R1-F5)
Fixed (pass 10): Section 5 reads "the remaining tables of intervals do not yet and are read as descriptive, as are the per-cell and per-year intervals; the pooled interval is the primary claim", Section 9 "the remaining tables carry none yet and are read as descriptive"; Section 6.2 reads "which is how the pooled difference decomposes" in place of "which is the negative result", and the guard comparison's interval is labelled "(0.0002 to 0.0017, descriptive)". Register C57 and C59 updated.

**[minor] [C55] [C60] The two origin differences print without intervals; both are clear of zero with opposite signs, so the pooled plus 0.0004 is a cancellation.** (R1-F6)
Fixed (pass 10): Section 6.2 adds "pooled" before "move", says that two admitted pairs move the score measurably in opposite directions, and quotes the two shipped intervals of Table guard-pairs-rows (`guard_pairs_rows.rows` origin 2013-10-01 `mean_diff` minus 0.0276, minus 0.0341 to minus 0.0206; origin 2014-04-01 plus 0.0184, 0.0129 to 0.0234), so the pooled figure is read as a cancellation of two measurable movements, not an absence of movement; R1's by-origin recomputation is not quoted, since no shipped key holds a by-origin interval of the difference. Register C55 re-keyed to the October 2013 pair and C60 rewritten.

**[minor] [R1.11] The floor reads each row's realized estimate and is not named an in-hindsight bound.** (R1-F7)
Fixed (pass 10): Section 5 reads "the floor is an in-hindsight bound, since it reads the realized estimate the forecast could not".

**[minor] [R1.13] Table positive-control-gain prints no interval for the oracle gain, and the closed-form ceiling is not stated beside the refit oracle.** (R1-F8)
Fixed (call 262; pass 10): the table prints the oracle's interval (`positive_control_sensitivity.rows[n_tests=11100,text_effect_strength=1.0].oracle_gain` 0.02042, 0.01890 to 0.02209), Section 6.8 quotes it, and Appendix B states the closed-form ceiling in words (half the log of one plus the planted variance over the predictive variance, the normal known-parameter version of the same quantity, agreeing with the refit oracle at the second digit in every cell) and why the refit oracle is the one reported. A printed ceiling number is not added (it would need a new extras key).

**[nit] [R1.14] "Equal the prior on skill" for 0.0019 against 0.0015, and "P2 equals P1 at 2,000 tests" for a paired 0.0000 with 2 of 24 pairs admitted.** (R1-F9)
Fixed (pass 10): "no better than the prior on skill" in the abstract, the introduction and contribution 3, "within the interval of P1 at 2,000 tests (0.0000, minus 0.0002 to 0.0003)" in Section 6.8; "equals" stays where the weight is zero everywhere (the deployment-shaped archive, the 4,000-contrast control, the synthetic archive without a signal). Register C10, C21, C22, C100 and C110 updated.

Suggestions (R1-s1 to R1-s5): recorded under Suggestions below.

Questions. (1) Yes: the two paired intervals that clear zero are read under the rule of Section 5 as descriptive, one of 33, and contribution 3 and Section 7 say so; the paired column is printed. (2) The reversal is read as composition in part (the abstained rows carry the burn-in origin and an event rate of 0.11 against 0.09), and the paper names it; the within-origin-and-cell comparison of issued against withheld rows is not built this round (decision 2 chose the pooled issued-row skill with the composition named). (3) The random-matched rows stay in Table decision-intervals-upworthy, since they carry the baseline's own captured fraction that the matched difference is read against; the columns that went are the two "minus random" columns (R5-F8), the matched difference and its adjusted bounds being the ones read. (4) Adopted as rubric item R1.15, dated 5 November 2026, applying from round 03 (decision 7). (5) 500: the extras rerun of decision 9.

## Reviewer R2, experimentation platform engineer

**[minor] [R2.13, R2.12] The join matches a card to its row by row id alone and never compares cells, so a card issued for one cell is scored against another metric's result.** (R2-F1)
Fixed (call 256, this commit): `attach_outcomes` writes a record with `scored` false and `cell_mismatch` true when the card's cell is not the row's, before any timing logic; `moot join` prints the count, `moot doctor` lists "cards for a row of another cell"; `moot card`, `POST /card` and the tool refuse a row id whose ledger row exists with another cell (`ledger.check_row_cell`, one filtered read of two columns); the operations manual's Weekly join section carries the sentence. Tests: five in `tests/test_round02_b.py`.

**[minor] [R2.10] The card prints the trailing-window line before the cell's backtest figure, and `backtest_summary` copies `decidable_by_tests` rather than `decidable_by_tests_cell`.** (R2-F2)
Fixed (calls 257 and 264, decision 10): the summary stores `decidable_by_tests_cell`, `gate_cell_n_200` and `gate_cell_n_400`; the card reads the cell's own verdict first, prints the backtest line before the window line, and ends the window line with "descriptive, one window of many"; the released headline bundle's stored summary was refreshed by `attach_backtest` on the existing report (no report file touched), so a both-cell card now reads "undecidable at this n" (318 and 454 tests needed, 225 available), which Section 6.2 reports for that cell. Tests: four in `tests/test_round02_b.py`.

**[minor] [R2.9] Tutorial 4 still describes the unpaired promotion rule with a 0.02 default, and the commands page calls the earn-weight margin "the promotion margin".** (R2-F3)
Fixed (this commit, documentation): tutorial 4's promotion paragraph is the paired rule (the 90 percent by-test interval of the paired Brier skill difference clears a margin of 0 by default at the gate in tests; 500 resamples); the earn-weight margin is named by its own name in `docs/commands.md`, `docs/simulators.md` and tutorial 6.

**[minor] [R2.6] The operations manual does not say that only admitted rows receive outcomes nor that an admission rule reading realized counts belongs in the registered plan, and the loop paragraph lacks the clause.** (R2-F4)
Fixed (this commit): two bullets in the manual's Weekly join section (only admitted rows are scored, so the live record is conditioned on admission as the backtest is; the doctor's count of cards on an unadmitted test; a rule that reads realized counts belongs in the registered analysis plan, as Sections 3 and 7 treat the clicks rule), and Section 4.3 reads "a card whose test is not admitted is never scored".

**[minor] [R2.11] Section 4.3's loop paragraph omits the 14-day staleness limit, where the seed is dated, the cold start that remains, and the sentence the round 01 letter promised.** (R2-F5)
Fixed (pass 10): Section 4.3 reads "the registered times are the team's statements, and the join's guard is what enforces them" and "The reliability trigger also reads a staleness limit of 14 days: the backtest seeds each cell's report dated at the ledger's last result, moved to the fit clock when that result is within the limit, so a ledger whose last result is older than 14 days at the fit clock issues no card until the first join brings outcomes, the cold start that remains" (`config.RELIABILITY_MAX_AGE_DAYS` 14, call 248); the manual's Abstained cards section carries the same, with the released seed's `consecutive_below` 1 for the both cell.

**[nit] [R2.14] `n_checkpoints` and `final_offset_days` sit at the top level of the deployment-shaped archive's features outside the post_launch block.** (R2-F6)
Argued (decision 6, call 249): moving the two fields rewrites `features_json` and changes every snapshot id and content digest of that archive the run folders cite, a change of the ledger format that belongs to the tier that moves numbers; the reading side is closed by the allow-list and its test. The settlement R2 offered is taken: `docs/ledger-format.md` names the two fields as post-launch display fields kept at the top level for the run folders' identifiers, to move at the next snapshot-changing release.

**[minor, carried] "Sealed" overstates what the code does; the paper's wording did not reach the documentation in five places.** (R2-V7, round 01 finding 7)
Fixed (this commit, documentation): the paper's wording ("the withheld forecast kept in the frozen file, which the join scores and no interface shows") replaces "sealed" in `docs/operations.md` (two places), tutorial 4, `docs/concepts.md` (heading and body) and `docs/reference/card.md`; the renderer string behind `docs/results.md` changed and the page was regenerated, so the word is gone from the documentation.

Suggestions (R2-s1, R2-s2, R2-s4): recorded under Suggestions below; R2-s3 (print 0.152 beside 0.215 in the deployment-shaped appendix) was merged into R5-F2 and is done.

Questions. (1) The two items are adopted as rubric item R2.15, dated 5 November 2026, applying from round 03 (decision 7); refusing a card for a row the ledger holds at issue is R2-s1 this round. (2) The cell's own-dependence verdict, `decidable_by_tests_cell` (decision 10; call 257), and the stored summary of the released bundle now carries it. (3) It was not; the sentence (the released seed starts at `consecutive_below` 1 for the both cell, and a first live join below the margin marks it) is now in the manual's Abstained cards section. (4) Yes: the round 01 letter carries a dated correction block (5 November 2026) with the run 7 headline-only figures (`tables.aggregate[cell=headline_only,rung=P2]` `brier_skill` minus 0.0036, minus 0.0084 to 0.0007, including zero; P1's minus 0.0043, minus 0.0085 to minus 0.0006, the one below zero), as R4.12 asks. (5) No: `make quick-check` covers the sample bundle's backtest (the report regenerated and diffed against the committed fixture), not a normal-limit bundle's card scoring; R2's closed-form check is the test for that, and the card's scoring is covered by the join tests.

## Reviewer R3, machine learning reviewer

**[minor] [C23] "No setting of the rung beats the prior" is read from the rows' own log scores; two settings have P2 above P1 with a descriptive paired interval clear of zero; "each run with the guard on and again with it off" holds for 7 of 16 settings.** (R3-F1)
Fixed (call 262; passes 10 and 11): as for R1-F2 (contribution 3 and Section 7 read the two intervals as descriptive and not findings, the paired column is printed); Section 7's opening sentence now reads "each run with the guard on and, where the guard can hold the setting back, again with it off", the caption's wording.

**[minor] [C12, C24, C119, C122] "The rung recovers about a fifth of it" is the pooled recovered fraction; in the cell shaped like the real headline-only cell it is a tenth, and the abstract, the contribution and Section 9 do not say so.** (R3-F2)
Fixed (pass 11): the abstract reads "the rung recovers a fifth of it pooled, a tenth in the cell shaped like the real one"; contribution 3, the end of Section 6.8 and Section 9 read the fifth as pooled over the generator's cells and name the tenth in the cell shaped like the real headline-only cell (`positive_control_sensitivity.rows[n_tests=11100,text_effect_strength=1.0].by_cell[cell=headline_only].recovered_fraction` 0.0995, 0.0764 to 0.1314, `strength_over_prior_sd` 0.333). Register C12, C24, C119 and C122 requoted; C127 keys the tenth.

**[minor] [R3.8] The within-stratum Murphy resolution column carries the per-stratum bias unstated, and the column orders P1 above the text classifier while the within-stratum AUC orders them the other way.** (R3-F3)
Fixed (pass 11): the caption of Table discrimination-within states the bias where the column is introduced: about nine over the stratum's rows times the event rate times one minus it in every stratum, which weighted by rows over the 27 strata is about 0.0015 at the pooled rate (9 by 27 by 0.0910 by 0.9090 over 13,247 rows), of the size of the printed values (`resolution_event_within` P1 0.00229, text_lr 0.00217), so the column ranks rungs on the same rows and nothing more, and P0's zero is by construction rather than a bias reference. The column stays; Section 6.2 does not read it.

**[minor] [R3.9] The paired comparison that changed the default is not a key in any shipped run 7 report, no header records the selection rule, and the Section 6.2 source comment names `header.p2_selection`, which does not exist.** (R3-F4)
Fixed (the second extras rerun; pass 11): the extras key `p2_selection_comparison` ships the comparison (`guard_on.pooled` `difference` 0.004403, 0.003085 to 0.005704; `guard_off.pooled` 0.002425, 0.000644 to 0.003927; by origin under both; 500 resamples), Section 7 quotes it ("paired by test, forward chaining beats it by plus 0.0044 nats, 0.0031 to 0.0057, with the guard on and plus 0.0024, 0.0006 to 0.0039, with it off") as the comparison by which the rule fixed before the data made forward chaining the default, and the Section 6.2 source comment names `tables.p2_selection[].selection` (forward in every row), call 206 and `config.P2_SELECTION_DEFAULT`. The header field: reports written from this commit on carry `p2_selection` beside `p2_guard`; the run 7 reports keep their headers, which the README says. The report takes the shape of an extras key rather than a file beside `ablations/p2-guard-upworthy.json`; the content is the one R3 asked for. Register C128 keys the pooled difference.

**[minor] [R3.10] The normal-family penalty is stated in Section 4.2 and nowhere beside Table 1.** (R3-F5)
Fixed (pass 11): the caption of Table 1 reads "The boosted model and the local set issue a normal predictive, so their log scores carry the 0.100-nat family penalty of Section 4.2" (`ablations/...--prior-normal.json` P1 `logscore` minus 0.9566 against minus 0.8566).

**[minor] [C121] "P2 sits above it from 2,991 rows on" is a statement about Brier differences of 0.00007 to 0.00033 on a base of 0.05548, and the raw Brier is in the file and not in the tables.** (R3-F6)
Fixed (call 262; pass 11): Table learning-detail prints P1's raw Brier score and both base Brier scores; Section 7 quotes the raw gap beside the skills ("raw Brier scores of 0.0538, 0.0537 and 0.0535 against 0.0539, 0.0539 and 0.0539 on a base of 0.0555", `rows[rung=P2].brier` 0.05383, 0.05373, 0.05352 against `rows[rung=P1].brier` 0.05390, 0.05389, 0.05385). P2's raw Brier is quoted in the text from the file and is not a column of the table.

Suggestions (R3-s1, R3-s2): recorded under Suggestions below; R3-s1 is the single-headline run of the challengers, not run this round by decision 5 and listed in Section 9 as not done; R3-s2 is the held-out scale term, named in Section 9 as future work.

Questions. (1) Yes, and contribution 3 says so. (2) The pooled generator; the paper now says both, the fifth pooled and the tenth in the cell shaped like the real one. (3) It stays; the bias per stratum is computable from the stratum's scored rows and event rate (the per-row score table carries both; the report carries the pooled rate and the cell sizes), and the caption states the row-weighted figure at the pooled rate, about 0.0015. (4) The family is six per budget, the rungs compared at one budget (Section 5 and the table's m = 6); the plan fixed a quarter and the verdict reads it there; the tenth-budget bound (`tables.decision_value[origin=ALL,budget=0.1,policy=p_win,rung=P2]` `diff_matched_adjusted_lo` 0.003) is in Table decision-intervals-upworthy and is not read for the verdict, and no clause is added, under decision 3's rule that prose keeps one number per claim. (5) Recorded for the launching team's decision between rounds; the shipped comparison exists (R3-F4), and the header field is written by reports from this commit on.

## Reviewer R4, reproducibility chair

**[minor] [R4.6] The paper says what the timed run covers and nowhere says what the stages outside it cost; the driver's stages file is not shipped.** (R4-F1)
Fixed (this commit; pass 11): `paper/data/run7-tie-rank/stages.txt` ships (every stage of the driver with its exit code and seconds); Appendix E reads: 71 stages, every exit code zero, 24,466 seconds of stage time in all, of which 23,088 fall outside the stages the timed run covers (the 36 headline-archive ablations 11,201, the three extras files 4,872, the two learning curves 3,943, the planted ledgers 1,413, the refresh check 646, the two replays 510, the ten deployment-shaped ablations 261, the cautionary run 239), run four stages at a time over 3 hours 15 minutes of wall time from the first stage to the last (the README: 18:11 to 21:26 PT). R4's 22,311 s of stage time and 3 h 49 min of wall time are from its own regeneration run in its clone (three jobs; 22,725 s of stage time over 11,925 s of wall time in its own account), not from the run 7 folder; the folder's `stages.txt` and README are the record of the shipped run.

**[minor] [R4.5] The README does not say which files are new, changed, removed and identical against run 6, and "73 stages" counts two marker lines.** (R4-F2)
Fixed (this commit): the README lists the assembler's four lists (5 new, 57 changed, 6 removed, 9 identical, each file named: the five positive-control files renamed by their snapshot date, run 6's `run-log.json` removed and replaced by the run 7 timed run's, the learning curves, the replays, the three leakage audits and the two guard comparisons identical) and reads "All 71 stages exited 0".

**[minor] [R4.12] The round 01 letter's R4 answer quotes run 6's timed run beside the run 7 folder name.** (R4-F3)
Fixed (pass 11): both R4 answers of the round 01 letter carry a dated correction (5 November 2026) quoting the run 7 file (`run-log.json` `total_seconds` 2,024.2, `main_pipeline_seconds` 1,263.9, power 836.7, challenger-gbm 706.1, nothing downloaded, `meta.files` 748, `meta.tree_sha256_16` 00b348180c492b75), and the pass 9 note at the head of that letter now lists the timed run's seconds, file count, tree digest and data stage among the numbers that moved.

**[nit] [R4.14] The commands table names targets whose flags are not the ones that produced the shipped files.** (R4-F4)
Fixed in part (pass 11): every build line of Table commands now carries the flags that produced the shipped files, in the driver's form (`scripts/run_experiments.sh --only lc-S` with `--learning-curve 0.01,0.02,0.05,0.1,0.25,0.5,1 --seeds 20 --no-recalibrate --bootstrap 500`; `--only 'ablation-S-*'` at `--bootstrap 500`; the cautionary and admission runs with `--origins quarterly --bootstrap 500`; `compare_guard.py --source S`; `paper_extras.py --source S`, the synthetic one with `--positive-control-runs`; `leakage_audit.py ... --json-out`; `card_latency.py ... --json-out`), and the caption says that `--list` names the stages. The Makefile's `learning-curve`, `ablations` and `audit` targets keep their quick flags (`--seeds 3`, the `.txt` audit); the table no longer names them for the shipped files. `docs/results.md`'s `--seeds 3` is the documentation agent's line.

**[nit] [R4.13] "Agreement across platforms is read from the job" rests on one runner image; the cross-platform reading is `tests/test_quick_check.py` against the Mac-built fixture, which the paper does not name.** (R4-F5)
Fixed (pass 11): Section 10 reads that the job runs three Python versions on one runner image (ubuntu), that the artifact shows agreement across Python versions, and that the cross-platform reading is `tests/test_quick_check.py` in the same job, which regenerates the sample backtest on the runner and compares it with the fixture built on macOS at a relative 1e-9 (2 points on the percentile fields). A second runner image is not added this round.

**[nit] [R6.11] Table decision-intervals-asos prints signed zeros that a fresh run prints the other way.** (R4-F6)
Fixed (call 262, this commit): the table formatter prints a value that rounds to zero as an unsigned zero, so no table holds "-0.000"; `make tables` regenerated the table.

Suggestions (R4-s1, R4-s2): recorded under Suggestions below; the timed run at the tagged release commit is on the release checklist.

Questions. (1) `stages.txt` ships and the README carries the four lists. (2) The commands table names the driver's stages and flags; the Makefile targets keep their quick form, so that `make learning-curve` stays a few minutes; the regeneration of the shipped files as written is `scripts/run_experiments.sh --only STAGE`. (3) Section 10 names the quick-check fixture as the macOS reference the ubuntu job is compared with; a second runner image is a suggestion for the release (R5-s2 asks for the number it would give).

## Reviewer R5, area chair

**[minor] [R5.2, C34, C36] H5's registered wording reads "more positive lift than random"; the verdict reads the arm-count-matched order adopted after the runs, and Section 5 does not say so.** (R5-F1)
Fixed (decision 1; pass 10): Section 5 states that the registered plan names random order as the fifth hypothesis's baseline and that since round 01 the verdict reads the arm-count-matched order, the stricter baseline, because the arm-count policy captures 0.303 against 0.250 for random order, more than any rung (call 201); Section 9 gives both readings (under the registered baseline the precedent rung is confirmed, `diff_random_adjusted_lo` 0.001053 to 0.039233, and the local set stays unresolved, minus 0.000797 to 0.048406; under the matched baseline both are unresolved) and says the verdict rests on the later, stricter baseline; Section 6.4 adds the clause; the limitations list the deviation; the verdict count stays one confirmed, four in part, one refuted. Register C34, C36, C37 updated, C123 and C124 added.

**[minor] [R5.5] The limitations list omits the two argued nits of the round 01 letter, the open single-headline run, and the run-length stand-in's leak.** (R5-F2)
Fixed (decision 5; pass 10): the list names the en dashes of the rendered PDF (the class and the bibliography style), the title kept as the benchmark's name, and the single-headline run of the challengers as not run; 0.152 (`paper-extras-asos ... corr_log_run_length_abs_z` 0.1522) is printed beside 0.215 in Section 9 and in the deployment-shaped appendix.

**[minor] [R5.7] The abstract is 405 words with no venue named, and Sections 6.2 and 6.4 stack numbers the tables hold.** (R5-F3)
Fixed (decision 3; passes 10 and 11): the abstract is 250 words, keeping the four claims and the three intervals (the Brier skill, the paired log score, the text classifier's decision value); no venue is named and Section 10 says the paper is written for a datasets and benchmarks track, with style, page limit and checklist handled at submission; Section 6.2's discrimination paragraph keeps the point AUCs and the two headline-only intervals the chance claim rests on, the admitted-pairs paragraph keeps the pooled interval and the location and scale parts and sends the row shares and the decisive split to the table, and Section 6.4's second paragraph keeps the text classifier's two matched gains and names the table; the cut keeps what R1-F2 and R1-F6 add. The two carried items of R5's round 01 review are done: the abstract (250 words) and the three decision-interval tables, now eight columns at their natural width (R5-F8).

**[minor] [R5.8] The artifact paragraph does not say who maintains the benchmark, where a submitted report card goes, or the pre-1.0 versioning rule.** (R5-F4)
Fixed (decision 4; pass 10): the author maintains the benchmark through the repository (issues and pull requests); a report card from a new archive is a pull request that adds a run folder under `paper/data` with its README, as the contributing page's new section describes; the released snapshot digests are named by version 1.0.0, and a schema change is a minor version before it.

**[minor] [R5.9] The round 01 letter carries statements overtaken since.** (R5-F5)
Fixed (pass 10): a dated correction block (5 November 2026) at the end of the round 01 letter names calls 248 to 254 against the findings they close, the two counts (405 then 250 words; 81 entries), the run 5 headline-only card figures against run 7's, and the four marks; the claim ids stand beside every line of the between-rounds diff.

**[nit] [R5.12] Tables are not numbered in reading order.** (R5-F6)
Fixed in part (pass 10): the appendix tables are ordered by their first reference in the body, in two groups, the single-column tables and then the two-column tables, each in reading order (the first references now run 2, 3, 4, 1, 7, 8, 39, 9, 10, 11, 40, ...; Table 1 is the body's main table); interleaving the two kinds in one exact reading order cost six pages, because a deferred two-column float holds the single-column floats behind it, so the two groups are kept.

**[nit] [R5.12] "logarithmic score" and "log score" name one measured thing.** (R5-F7)
Fixed (pass 10): "log score" throughout, defined once at its first body use in Section 2.

**[nit] [R5.12] The three decision-value interval tables render below legibility.** (R5-F8)
Fixed (call 262; pass 10): the two "minus random" columns are dropped (the matched difference and its adjusted bounds are the ones read; the difference from random order is the captured fraction minus the random row), and the three tables, now eight columns, are set at their natural width in scriptsize with no scaled box.

Suggestions (R5-s1, R5-s2): recorded under Suggestions below.

Questions. (1) Yes, both: Section 5 discloses the change and Section 9 gives the registered-baseline reading beside the matched one. (2) The author, through the repository; a pull request adding a run folder under `paper/data`; version 1.0.0 names the released snapshot digests (decision 4). (3) No track is named; the paper is written for a datasets and benchmarks track and the abstract is 250 words (decision 3). (4) Listed in Section 9 as not done (decision 5). (5) Yes, the dated block of 5 November 2026 at the end of the round 01 letter.

## Reviewer R6, practitioner and documentation reviewer

**[minor] [R6.6] The backtest report's first table repeats two columns, prints a fixed-rate column as n/a, and its heading says "the by-row columns are beside it".** (R6-F1)
Fixed (call 260, this commit): the two repeated columns and the fixed-rate column go when the gates file counts tests; the heading is reworded; the README sentence is gone; a renderer test holds it. The JSON does not change.

**[minor] [R6.4] Tutorial 6 reads "below the gate of 150 tests" under its own output "below the gate of 250 tests".** (R6-F2)
Fixed (this commit, documentation): "250 tests" (the quick gate at a skill of 0.10 and base rate 0.09, which earn-weight reads). The documentation test R6 proposed (every gate size quoted beside an output block appears in that block) is Tier B and not taken this round.

**[minor] [R6.4] The report card's Gates section gives 175 and 250 tests with no base rate while its Ledger section prints 0.067.** (R6-F3)
Fixed (call 259, this commit): the report card reads the gate sizes at the simulated rate nearest the ledger's and says so on the Gates heading line ("simulated at base rate 0.09, the nearest simulated rate to this ledger's 0.067"); tutorial 2 and `docs/benchmark.md` carry the same words.

**[minor] [R6.4] Without a gates file `moot backtest` runs a different quick simulation from `moot init`, so tutorial 3's first card counts rows and the report's adjusted bounds differ from the published ones.** (R6-F4)
Fixed (call 258, this commit): `onboarding.write_quick_gates` is shared by `moot init` and the backtest fallback (by test, at the simulated rate nearest the ledger's, level 0.90); `moot init` writes the same file as before, so the sample fixture did not move; tutorial 3 says that the adjusted bounds depend on the gates file until `moot simulate gate-power` has run, and its blocks were regenerated.

**[minor] [R6.5] Every card prints "Team forecast: None provided" and no page explains it; the help of `--impressions-variant` says "exposures".** (R6-F5)
Fixed (call 261 and this commit's documentation): tutorial 1 has a Team forecast bullet (the team's probability and point estimate, frozen with the card when given through `POST /card`; the command line has no option); the card reference row names the two fields; the help reads "planned units". Whether `moot card` takes `--team-p-win` and `--team-point` is a suggestion this round (decision 8).

**[minor] [R6.7] `moot join --new-rows` with a missing file prints "error: /nonexistent.parquet".** (R6-F6)
Fixed (call 261): the message names the problem and the cure ("new rows file not found: <path>; stage the week's results with moot ingest --ledger incoming/ledger.parquet first"); the manual and the commands page carry the join's messages.

**[minor] [R6.2] No test runs a documentation block through `uv run --project <clone>` from outside the clone.** (R6-F7)
Fixed (this commit): `tests/test_docs_run.py::test_the_readmes_uv_run_project_form_runs_moot_from_a_folder_outside_the_clone`, skipped when uv is not on the path.

**[minor] [R6.3] Two timings contradict the pages' own output.** (R6-F8)
Fixed (this commit, documentation): tutorial 1 reads "about twenty seconds, most of it writing the report" and the README "about 20 seconds"; tutorial 3's Time line and step 4 read "5 to 7 minutes, of which about a minute is the quick gate simulation" and "about five minutes, of which about one is writing the report".

**[minor] [C103] The conclusion's "the card prints the cell's latest gated skill beside every forecast" holds for the archive's cells and not for a ledger below the gate.** (R6-F9)
Fixed (pass 10): Section 8 reads "the card prints beside every forecast the latest gated skill of its cell, or the pooled figure, labelled, when the cell is undecidable". Register C103 updated.

**[nit] [R6.11] `python scripts/...` remains in tutorial 3 and the operations manual, and the README and tutorial 1 print different ids for the same commands.** (R6-F10)
Fixed (this commit, documentation): `python3` on those lines; one regeneration pass over the README, the commands page and tutorials 1, 2, 3, 4 and 6 after the code settled, so the ids agree; rubric item R6.13 adopted for round 03 (decision 7).

**[nit] [R6.12] Tutorial 1 and the README do not say that the model id and the card id change with the snapshot date, and tutorial 3 shows only the first 26 lines of its card.** (R6-F11)
Fixed (this commit, documentation): one sentence after tutorial 1's fit output and in the README (the model id covers the snapshot id, so it differs on another day; compare the numbers); tutorial 3's card block is no longer cut at 26 lines and a sentence names the Skill section.

**[nit] [R6.8] The troubleshooting page says `moot doctor` reports the sidecar on its second line.** (R6-F12)
Fixed (this commit, documentation): "on its `environment` line".

Suggestions (R6-s1 to R6-s5): recorded under Suggestions below; R6-s2 (the "(call 208)" help text) and R6-s3 (the reviewer's absolute clone path on the troubleshooting page) were taken outside the round's count as one-line changes (decision 11; call 261 and the documentation).

Questions. (1) Yes: the fallback is the quick simulation `moot init` runs, by test at the rate nearest the ledger's (call 258), so a reader who starts from tutorial 3 sees gates in tests from the first report. (2) Through `POST /card` (`team_forecast` with `p_win_team` and `point_team`), frozen with the card; the command-line options are a suggestion, not this round (decision 8). (3) Adopted as rubric item R6.13, dated 5 November 2026, applying from round 03 (decision 7).

## Suggestions (recorded, not fixed in the round)

- R1-s1: say in Section 6.2 that a cell's gates are a first-order scaling of the simulated ones, not a simulation; R1's simulation at the smallest cell's dependence (power 0.910 at 318 tests for a skill of 0.20, 0.870 at 454 for 0.10) is the check.
- R1-s2: the package's learning-curve figure still draws the gate sizes as vertical lines on the history axis.
- R1-s3: the equal-mass ECE and its percentile as columns of Table ece-upworthy.
- R1-s4: the by-origin table uses 200 resamples; nothing printed depends on it.
- R1-s5: H1 read on the paired P1 minus P0 difference by origin (narrowest January 2015, 0.0681, 0.0384 to 0.0972) in place of the point comparison.
- R2-s1: refuse at issue a card for a row the ledger already holds (rubric item R2.15 from round 03 asks for it).
- R2-s2: the timing rule reads the contrast's start; on the headline archive 34 tests have packages created up to 14.9 days after the reference arm.
- R2-s4: name the backtest's simulated rate on the card's backtest line.
- R3-s1: the single-headline run of the challengers (not run, decision 5; Section 9 lists it as not done).
- R3-s2: a held-out or marginal-likelihood estimate of P2's scale term (Section 9 names it as future work).
- R4-s1: a `scripts/compare_runs.py` that diffs a fresh reports folder against a run folder leaf by leaf.
- R4-s2: repeat the timed run at the tagged release commit (on the release checklist).
- R5-s1: a stronger text representation as a fourth challenger.
- R5-s2: once a second runner image runs, quote the maximum relative difference of the per-platform score reports.
- R6-s1: one exit-code convention for input errors.
- R6-s2 and R6-s3: taken outside the count (decision 11).
- R6-s4: draw the sample ledger at base rate 0.09.
- R6-s5: keep `moot init` quoting a path that contains a space.

## Diff of the paper's claims between the round 01 letter and this one, by claim id

Changed.
- The abstract (250 words, from 405): C1, C3, C4, C6, C7, C8, C10, C11, C12, C14, C16, C17, C18 requoted; C5 (pooled coverage) and C13 (the period-level defect) left the abstract and are kept in the register as removed, their claims standing in Sections 6.2, 6.8 and 9 (C30, C44, C95).
- "Equal the prior" to "no better than the prior" and "within the interval of": C10, C21, C22, C100, C110.
- Contribution 3's ablation sentence weakened to the two paired intervals that clear zero, read as descriptive: C23.
- H4 read on the Brier skill, the first two parts refuted and the third holding: C33, C80, C125, C126 (`issued_row_brier_skill`).
- H5 under both baselines, the verdict on the later, stricter one: C34, C36, C37, C123, C124.
- The admitted pairs: the pooled difference read as a cancellation of two measurable movements, with the two pairs' intervals: C55 (re-keyed), C60; the location and scale parts and the guard comparison labelled descriptive: C57, C59; the row shares and the decisive split sent to the table: C58 removed.
- Fewer numbers in prose: C51, C78, C113 (re-keyed to P0's pooled AUC).
- The oracle's interval: C96. The card's pooled fallback: C103. "Log score": C4, C43, C46, C108.
- The recovered fraction read as a fifth pooled and a tenth in the cell shaped like the real one: C12, C24, C119, C122, C127.
- The shipped selection comparison behind the forward-chaining default: C128.

Unchanged. The headline numbers: 0.149 nats over the base rate (0.100 of them the Student-t family); Brier skill 0.0015 (minus 0.0018 to 0.0048) on 3,797 tests against a release gate of 250; the 100th percentile of the clustered null; coverage 1.000 to 0.655 across the deciles; the paired P2 minus P1 0.000447 (minus 0.000297 to 0.001191); the admitted pairs' pooled 0.00097 (its interval now at 500 resamples, minus 0.00073 to 0.00245, the printed digits unchanged); the decision values against the matched order; the positive control's admission and pooled recovery; the cautionary run's minus 0.1074; the deployment-shaped archive undecidable at every gate; every percentile the paper prints (the tie rule of call 255 moved per-cell fields only, none printed). The claims register holds 128 rows (122 at the round's commit), every keyed row resolving under `paper/data/run7-tie-rank` (`scripts/claims_audit.py` exit 0).
