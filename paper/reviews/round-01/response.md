# Round 01 response letter (parts 1 and 2a)

Paper version under review: 85ae973. Code version under review: 85ae973. Part 1 of this letter was written on 4 November 2026 against the working tree before the round-01 code tasks landed; part 2a, the same day, added the section for R4, the design-call numbers of the code that had landed (`docs/method.md` calls 199 to 247), the released loop in Section 4.3 and the public registration of the plan; part 2b (4 November 2026, evening) switches every number of the paper to run 6, `paper/data/run6-forward-chaining`, in which every experiment downstream of the precedent rung was rerun from one code state under the forward-chaining default of call 206, with the three leakage audits inside the folder. Every answer below carries its run 6 number where a number was pending; no marker remains in the paper, the timed run at the final commit being in the run folder as `run-log.json` (2,052 seconds in all, measured under load). Pass 9 (4 November 2026, late evening): every path of the paper and the register names `paper/data/run7-tie-rank`, run 6 repeated on commit 82ba862 under the mid-rank tie rule of the calibration percentile (call 255); no number quoted in this letter moved except the gate simulation's seconds, the card latency and the timed run's seconds, file count, tree digest and data stage (corrected in the R4 answers on 5 November 2026), which are timings and identifiers, and the positive control's snapshot date and model ids, noted in place; the timed run of run 7 is in the folder as `run-log.json` and Appendix E quotes it (2,024 seconds in all, 1,264 for the main pipeline, 837 the gate simulation, 706 the boosted challenger; the archives copied from the data root in 0.2 seconds, nothing downloaded; a one-minute load average of 7.2 at the start and 92.0 at the end; 748 files, tree digest 00b348180c492b75).

We are the launching team. Every finding of the five reviews is answered below in the reviewers' order, with one of three marks. Fixed: a change of code or data, with the task that holds it (or "done" with the design call when it has landed). Paper: a change of text only, with the section it now lives in. Argued: no change, with the reason. Numbers are quoted from the report files under `paper/data/run5-period-rule/` by file and key; the positive control's new keys are `positive_control_sensitivity` (now with `realized_gain`, `oracle_gain` and `recovered_fraction` beside `share_admitted`) and `positive_control_rungs`, both in `paper-extras-synthetic-20261103-bf4fd286e2b2.json` (task T-066, design calls 230 to 232, done before this letter).

Tasks named in this letter: T-060 adjusted bounds for the remaining tables of intervals; T-061 a random baseline matched on each test's number of arms for decision value; T-062 the learning curve against the full-history base rate with 500 resamples; T-063 the released loop (every R2 finding); T-064 re-application of the default rule for the precedent selection (design call 66); T-065 discrimination within each origin and cell stratum; T-066 the positive control's realized gain (done); T-067 the per-row distribution of the admitted pairs' realized difference; T-068 command-line items (R6); M4 documentation items (R6). Items that no task holds yet are marked "new item" and listed at the end.

Section numbers refer to the paper at this commit: 1 Introduction, 2 Related Work, 3 Problem Setting and Data, 4 Method, 5 Evaluation Protocol, 6 Results (6.1 cautionary run, 6.2 skill ladder, 6.3 calibration and coverage, 6.4 decision value, 6.5 abstention, 6.6 drift and replay, 6.7 the deployment-shaped archive, 6.8 synthetic truth and the positive control), 7 Ablations and Learning Curve, 8 Discussion, 9 Hypotheses, Limitations and Ethics, 10 Reproducibility, Appendices A to F.

## Reviewer R1, statistician

**[blocking] The decision-value comparison is dominated by the number of arms per test, a pre-launch field, and its random baseline does not control for it; against an arm-count-matched baseline the text classifier keeps about four points and the precedent rung keeps nothing.**
Fixed (call 201, run 6). The arm-count policy is a named row of the decision table and every rung's difference is read against a random order matched on the arm-count composition of the set it chooses, with by-test intervals and Bonferroni-adjusted bounds over the six rungs of each budget. At the quarter budget the arm-count policy captures 0.3026 of the lift (plus 0.0524 over random order, 0.0400 to 0.0640), and against the matched baseline the text classifier captures plus 0.0395 (0.0217 to 0.0541; adjusted 0.0158 to 0.0632), the boosted model plus 0.0276 (0.0154 to 0.0397; adjusted 0.0093 to 0.0459), the local set plus 0.0150 (minus 0.0014 to 0.0312) and the precedent rung plus 0.0139 (0.0023 to 0.0264; adjusted minus 0.0038 to 0.0316), P1 minus 0.0043 (`backtest-upworthy tables.decision_value` origin ALL budget 0.25, `diff_matched` and `diff_matched_adjusted_lo`). Paper: the abstract, the introduction, Section 6.4 and the fifth hypothesis read against the matched baseline; the text classifier keeps about four points, the boosted model clears zero, and the precedent rung and the local set are unresolved after adjustment, as the review predicted. Question 1 (budgets of a tenth and a half): the text classifier captures plus 0.0322 (0.0211 to 0.0451) and plus 0.0362 (0.0167 to 0.0509) over the matched baseline; whether the one-contrast tests are a different kind of test is not analysed, but the `contrasts-one` ablation of Section 7 scores one contrast per test, the earliest, and leaves P2 at the prior (minus 0.870 against minus 0.871).

**[blocking] The learning curve's Brier skill is measured against a base rate re-estimated from each subsample, so the baseline worsens as the history shrinks and the curve reads backwards.**
Fixed (call 204, run 6). Every fraction is scored against the base rate of the full visible history at the final origin, with 500 resamples, the seed spread and each subsample's own base rate beside it: P1's skill rises 0.0007 (minus 0.0169 to 0.0235), 0.0191, 0.0229, 0.0273, 0.0286, 0.0288, 0.0295 (0.0140 to 0.0510) over the seven histories (seed spread 0.0359 at 123 rows, 0.0031 at 2,991), P2 0.0035, 0.0164, 0.0231, 0.0275, 0.0299, 0.0317, 0.0353 and above P1 from 2,991 rows on, the local set 0.0366 only at the full history, the text classifier minus 0.0243 to 0.0104 (`learning-curve-upworthy rows`). Paper: Section 7 and Figure 6 are rewritten to the fixed-baseline curve and say that the own-base reading (0.0679 at 123 rows) is the base rate's noise; Section 8 says a prior arrives within a few hundred rows, and the precedents add nothing the curve can measure (unpaired points whose intervals overlap at every fraction; corrected 4 November 2026 after the claims audit). Question 2: P1's Brier score comes within 0.0005 of its full-history value from 2,991 history rows on (0.0539 against 0.0538).

**[major] The gates are read against the size of the fit history, which is not what they measure.**
Paper: the sentence is gone from Section 7, which says that the 318 held-out tests clear both gates at every point and that how much history the prior needs is a different question; the run 6 figure draws no gate line.

**[major] Eight P1 log scores in the two ablation captions come from an earlier run and do not trace to any run5 report.**
Paper: both captions carry the run5 values with a source comment naming each file: minus 0.857 in every unchanged row (`ablations/backtest-upworthy-20261103-4bfb354b87e3--lambda-0.0.json` tables.aggregate cell ALL rung P1 logscore minus 0.8566), prior-normal minus 0.957, admission-prelaunch minus 0.832 on 14,235 rows, the kappa rows minus 0.860, minus 0.859 and minus 0.855; on the deployment-shaped archive 4.709, 4.332 and 4.693, 4.701, 4.716 (`ablations/backtest-asos-20261103-6bb5a15c5ff0--*.json`). Every caption in the paper that carries a digit was swept against its source: the two year tables' Bonferroni family sizes were stale as well (132 where `tables.score_by_year family_size` is 156; 90 where the deployment-shaped file says 110) and are fixed, and every caption with a number now has a source comment. Fixed (call 235): `tests/test_paper_sources.py` requires a source for every float whose caption carries a digit.

**[minor] The smallest cell's label is read at 3.5 rows per test, which it does not have (2.09).**
Fixed (call 205, run 6): the aggregate rows record the gate's assumed rows per test and correlation beside the group's own and a first-order verdict at the cell's own sizes (`gate_cell_rows_per_test`, `gate_cell_icc`, `gate_cell_n_200`, `gate_cell_n_400`, `decidable_by_tests_cell`). Paper: Section 6.2 says the smallest cell has 2.1 rows per test and a within-test correlation of 0.40 against the 3.5 and 0.13 the simulation draws, that its gates scale to 318 and 454 tests, and that it is undecidable at both skills (the pooled table's own dependence gives 199 and 284, still cleared). Question 5: the gate read carries them.

**[minor] "Every table of intervals also carries Bonferroni-adjusted bounds" is true of the aggregate, year and ECE tables and not of the others.**
Paper: Section 5 and Section 9 name the tables that carry them (aggregate, year, calibration and decision value) and say that the ablation, learning-curve, released-rows, guard and positive-control tables do not yet. Argued: the ablation, learning-curve, released-rows, guard and positive-control tables carry no adjusted bounds, and Section 5 says which tables do (aggregate, year, calibration, decision value); every claim that rests on an interval is read from those four, and the remaining tables are descriptive.

**[minor] The pooled paired P2 minus P1 difference has a by-test interval of minus 0.0052 to minus 0.0027; "less than the noise of selecting them" understates a measurable loss.**
Fixed (call 205, run 6): the aggregate rows carry `logscore_vs_p1`, the all-rows paired log-score difference from P1 with a by-test interval and adjusted bounds, and Table 1 prints it. Under forward chaining the pooled P2 minus P1 is plus 0.0004 (minus 0.0003 to 0.0012; adjusted minus 0.0010 to 0.0019), so the sentence the review asked for reads the other way: Section 6.2 says "the admitted precedents move the out-of-time log score by less than the noise of selecting them (plus 0.0010 nats on their rows, minus 0.0007 to 0.0025; plus 0.0004 pooled over all rows)". The run 5 figure the review recomputed, minus 0.0040 (minus 0.0054 to minus 0.0026), was a property of the leave-one-test-out default, which is now the ablation `p2-selection-loto` (minus 0.8606, 0.004 nats below the prior, Section 7).

**[minor] The significant-positive rate falls by half over the archive (0.118 to 0.057 by origin year) and the paper does not say so; "nothing declines with time" is true of the skill only; the drift rule cannot see a drift the two rungs share.**
Fixed (call 205, run 6): `tables.score_by_year` and the aggregate rows carry `event_rate`; Section 6.6 says the significant-positive rate falls from 0.117 in 2013 to 0.087 in 2014 and 0.057 in 2015, a shift P0's trailing base rate lags and the drift rule, which watches the log score against P0 alone, cannot see, and Section 6.3 reads P0's ECE at the 100th percentile the same way. Question 3 (whether the publisher's effects shrank, and whether P1's 2015 skill comes from its prior scale tracking a falling rate): the rate falls while the planned exposure does not, so the effects did shrink in the sense that fewer tests cleared significance at the same precision; the rerun learning curve holds out exactly the 2015 quarter and P1's skill there is the highest of any quarter at every history size, which is consistent with the review's reading and does not prove it.

**[minor] The positive control shows that the guard admits, not that the rung gains; say the ceiling and the realized gain beside the admission rate.**
Fixed, done (T-066, calls 230 and 231; run 6 numbers): every row of `positive_control_sensitivity` carries the rung's held-out gain over P1, the oracle's gain (P1 refit with the planted term removed and shifted back row by row) and the recovered fraction, on a random 15 percent of each ledger's tests held out by test. At 11,100 tests and a planted lift of 1 percent the guard admits a weight in 0.972 of cells, the realized gain is 0.00369 nats (0.00334 to 0.00401) against an oracle gain of 0.0204, recovered 0.180 (0.164 to 0.197); in the headline-only cell, where the lift is a third of a prior standard deviation, 0.099; at 300 and 1,000 tests the rung recovers at most 0.016 of the oracle's gain at lifts of 1 percent and below. The closed-form ceiling of the review agrees with the refit oracle at the second digit per cell (call 230). Paper: the abstract reads "the guard admits a planted lift at the size of the largest cell and the rung recovers about a fifth of it"; Section 6.8, Appendix B and the limitations say the ceiling, the realized gain and the admission rate side by side, and Table positive-control-gain carries all three. At the published control's own size (4,000 contrasts, about 1,200 rows per cell) the guard under forward chaining admits no weight in the planted cell, which Section 6.8 now says.

**[nit] "At an event rate of 0.0847 against 0.0832" labels the base Brier score as an event rate.**
Paper: Section 7 reads "at a base Brier score of 0.0847 against 0.0832".

**[nit] The round-00 letter reads the headline-only interval as slight miscalibration; the text reads it as one of two null excursions.**
Paper: Section 6.2 gives both readings in one sentence: two excursions among the table's 52 intervals are what the null predicts, and the headline-only cell's expected calibration error at the 100th percentile (`tables.aggregate` cell headline_only rung P1 ece 0.0172, ece_percentile 100.0) reads its negative interval as slight miscalibration on the largest cell as well. The round-00 letter carries a dated correction (part 2a).

Questions. (1) and (2) above. (3) Above; the planned-exposure trend by year is read with the event-rate column when it exists. (4) The two largest in-selection gains (July and October 2014, headline only) with the two most negative realized differences are the pairs that T-067 decomposes into a location and a scale part, and the forward-chaining rule is re-tested against leave-one-test-out with a paired by-test interval under call 66 (T-064); leave-one-test-out was the default because it uses every visible row at an origin for both fitting and validation, which the forward rule cannot at the early origins, and the default changes if the forward rule's advantage clears zero. (5) Above: the gate table says which cells it applies to; the per-cell read is a new item.

## Reviewer R2, experimentation platform engineer

The trace of one card from issue to outcome is acknowledged with thanks; it reproduces the join's scores from the frozen file alone and found the four gaps below by pushing the loop one step further than the replay does.

**[blocking] The join's only time check is that the row's usable time has passed at the join clock; a card issued after the result is in the ledger is joined and enters the reliability report as evidence.**
Fixed (call 220): `loop.card_timing` classifies every card against its row, pre-launch when the later of its origin and issue time is at or before the row's start (inclusive; at the start instant the test has produced nothing, and the inclusive rule keeps every replay card pre-launch), in flight between the start and the result, after the result otherwise; only a pre-launch card is scored, a post-hoc card is recorded with every score null and never reaches the reliability report, `moot join` counts it apart and `moot doctor` reports it; three tests hold it, one of them R2's exp-120 case through `moot card`, `moot join` and the doctor. Paper: Section 4.3 states the rule (part 2a), and Section 6.6 reports the run 6 replay under the loop's own rules: 13,247 cards over 111 weeks, 1,457 abstained (0.110), 89.5 percent of 11,790 joined outcomes covered by the card's 90 percent interval, four flagged weeks, all in the smallest cell from 20 April 2015. Question 1: a card issued during a test is not scored as a pre-launch one; it is marked in flight and reported apart, and the tutorial's example moves to a test that launches after the clock (M4).

**[major] A card may stand at an origin later than its issue time, and the issue time is caller-supplied on every interface.**
Fixed (call 221): an origin after the issue time is refused on the command, the service and the tool. Argued: the wall-clock stamp inside the content id is not added, because it is the caller's clock too and a stamp that changes on every call would defeat the idempotent freeze and manufacture the duplicates of the next finding; the registered times stay the team's statements and the join's guard of call 220 enforces them. Paper: Section 4.3 says so (part 2a).

**[major] Every frozen card with a row id is scored, so two cards for one row give two outcomes and the row counts twice.**
Fixed (call 222): one card per row is scored, the earliest pre-launch one in issue order; every other pre-launch card for the row is recorded as a reissue with `superseded_by`, a row an earlier join scored keeps its card, `moot join` prints the reissue count and `moot doctor` counts them. Paper: Sections 4.3 and 6.6 say so (part 2a).

**[major] The nightly fit takes every admitted row of the snapshot, not the rows usable at the fit time.**
Fixed (call 223): `moot fit` takes the fit clock (`--now`, default the wall clock), fits on the rows usable at it, records `fit_as_of` in the manifest and registers `data_through` as the latest usable time the fit saw. Paper: Section 4.3 reads "a nightly fit on the rows usable at its clock" (part 2a). Question 4: it was not deliberate; on a ledger with a usable delay `data_through` meant the latest usable time of the fit rows, which can lie in the future, and the loud refusal of `check_origin` is what made it visible, as the review says.

**[major] The promotion of a different method compares two unpaired backtest summaries against a fixed margin of 0.02; the Discussion calls the comparison paired; no rung reaches the margin here.**
Fixed (call 224): `registry.paired_comparison` scores the two methods on common rows, the paired Brier skill difference (challenger over champion) with a 90 percent interval by test (500 resamples), and `Registry.promote` promotes only when the interval's lower bound clears the margin at the gate for the challenger's skill; the margin is zero by default (`config.PROMOTION_MARGIN` 0.0), because the gates size a skill and not a difference and the fixed 0.02 was reached by nothing on these archives; two models scored by one table have no paired evidence and the command refuses with what to run. Paper: Section 4.3 describes that comparison and Section 8 reads "a paired, gated comparison" (part 2a). Question 5: with the margin at zero and the interval deciding, `moot promote` promotes a challenger whose paired interval clears zero at the gate; the margin is a team's own choice (`--margin`).

**[major] The "Latest gated backtest" line prints the pooled summary on a card that is issued per cell; a launching team never sees the decidable negative for its own cell.**
Fixed (call 225): the backtest summary stores every cell of the card rung with its skill, interval, rows, tests and gate verdict, and the card prints its own cell's figure with its decidability when the backtest finds the cell decidable, otherwise the pooled figure labelled as pooled and why; the window line keeps its interval, test count and verdict. Paper: Section 4.3 says so (part 2a). The figures the review quotes for the headline-only cell (rung P2 brier_skill minus 0.0048, minus 0.0085 to minus 0.0016, decidable at both skills) are the ones the card will print.

**[minor] "Sealed" overstates what the code does.**
Paper: Section 4.3 reads "kept in the frozen file, where the weekly join scores it and no interface shows it"; the operations manual and tutorial 4 follow (M4).

**[minor] The entry is dated at the first outcome in the window, not the tenth; a one-test window prints "no interval is recorded" when the interval was not computable.**
Fixed, pending: M4 corrects both sentences; the "fewer than two tests in the window" line is not in calls 207 to 229 and stays listed.

**[minor] The seed is dated at the last usable time of the scored rows, so every first live card abstains for one horizon.**
Pending, listed: dating the seed at the fit clock when the ledger's last result is within the staleness limit is not in calls 220 to 225; call 223 gives the fit its clock, which is the precondition.

**[minor] Three conventions of the replay are not enforced by the loop.**
Paper: Section 6.6 names the three (one card per admitted row, issued at the week start before the test starts, from a bundle refit at every quarterly origin). The first two become guards of the loop (T-063).

**[minor] A card without a row id, or with a row id in no ledger, is frozen and never scored; the doctor count listed for this round is not there.**
Fixed in part (calls 220 and 222): `moot doctor` counts post-hoc cards and reissues per source; cards with no row id, with a row id absent from the ledger, and with a passed horizon and no outcome are not yet counted and stay listed.

**[minor] Only admitted rows receive outcomes, so the live record is conditioned on admission.**
Fixed, pending: M4 says so in the operations manual; counting such cards and writing an admission rule that depends on realized counts into the ledger's provenance are not in calls 207 to 229 and stay listed.

**[nit] The outcome records the card's snapshot and not the ledger snapshot that holds the outcome row; two post-launch quantities sit at the top level of the deployment-shaped features.**
Pending, listed: not in calls 220 to 225.

**[nit] The tutorial's cards for exp-101 are issued six days after launch under a heading that says before launch.**
Fixed, pending: M4; the example moves to a test that launches after the clock.

**[nit] A cell whose outcomes all fall outside the trailing eight weeks keeps its old date.**
Pending, listed: not in calls 220 to 225.

Questions. (1), (4) and (5) above. (2) As call 187 states, a request without a reference headline takes the fit-mean reference vector, so it sits nearer the centre of the pairwise space than a real pair; whether that lowers the novelty rate for a team that omits the reference is not measured, and the card now says when the reference was defaulted (call 238, `reference_defaulted`). (3) The `consecutive_below` of 1 for the smallest cell is the state in which the archive ends, kept as the seed deliberately; a first live join that is also below the margin marks the cell, which is the rule's intent, and the operations manual will say so (M4).

## Reviewer R3, machine learning reviewer

**[major] The headline negative is a property of the leave-one-test-out selection rule; the forward-chaining ablation reverses its sign, and Section 7 reads the swing as noise while Section 6.2 reads a 0.0067 loss as a finding.**
Fixed (calls 202 and 206, run 6). Call 66's rule, re-applied to the run 5 numbers with 2,000 by-test resamples, selected forward chaining (pooled advantage plus 0.0044, 0.0030 to 0.0057, with the guard on; plus 0.0024, 0.0007 to 0.0041, with it off), so forward chaining is the default selection of run 6 and leave-one-test-out the ablation `p2-selection-loto`. Under it the precedent rung is level with P1: pooled P2 minus P1 plus 0.0004 (minus 0.0003 to 0.0012), minus 0.016 at October 2013, where the forward validation blocks are smallest, plus 0.010 at April 2014 and within 0.003 of zero at the other seven origins; the guard admits 8 of 27 pairs and their realized difference is plus 0.0010 (minus 0.0007 to 0.0025). Paper: the abstract, the introduction, Sections 4.2, 6.2 and 7 and the hypotheses say so; the headline negative is now "precedents equal the prior on skill and on the log score within the interval", and Section 7 reports leave-one-test-out as the counterfactual (minus 0.8606, 0.004 nats below the prior and below forward chaining). The two readings the review found incompatible are gone with the 0.0067 loss. Question 1: the paired interval clears zero (above), and the default changed.

**[major] The realized loss in the admitted pairs sits on the typical row, not on a few, and points at the scale term rather than the precedent mean.**
Fixed (call 233, run 6). `guard_pairs_rows` decomposes the realized difference on the admitted pairs' rows into a location part and a scale part (the two one-parameter-at-a-time paths averaged, which sum to the difference row by row), with the shares of rows P2 scores better on, the decisive and non-decisive splits and the scale ratio; Table guard-pairs-rows prints it. Under forward chaining the eight admitted pairs' realized difference is plus 0.0010 (minus 0.0007 to 0.0025): location part plus 0.0036 (0.0025 to 0.0046), positive in seven of the eight pairs; scale part minus 0.0026 (minus 0.0040 to minus 0.0010); P2 better than P1 on 47 percent of the rows and wider on 61 percent; plus 0.0031 on the 4,468 non-decisive rows and minus 0.0049 on the 1,646 decisive ones (location plus 0.0144, scale minus 0.0193 there). Paper: Section 6.2 reads "the precedent mean carrying a little and the scale term giving most of it back". Question 2 (the two largest pairs, July and October 2014): location plus 0.0024 and plus 0.0018, scale minus 0.0022 and minus 0.0012, the pairs' realized differences plus 0.0002 and plus 0.0006; under leave-one-test-out (run 5) the same pairs lost 0.0267 and 0.0153 with scale parts of minus 0.0299 and minus 0.0179. Question 4 (a marginal-likelihood estimate of the residual variance): not tested; Section 9 names a held-out choice of P2's scale term as the top candidate for future work.

**[major] The pooled AUC and Murphy resolution credit every rung with between-cell and between-origin movement of the base rate.**
Fixed (call 203, run 6). The aggregate rows carry the AUC and the resolution within each origin-and-cell stratum, row-weighted, with intervals by test, and Table discrimination-within prints them: within strata the event AUC is 0.500 for P0, 0.530 (0.512 to 0.547) for P1, 0.548 for P2, 0.538 for the local set and 0.564 (0.547 to 0.582) for the text classifier, and within the origins of the headline-only cell 0.502 (0.477 to 0.525) for P1, 0.533 for P2 and 0.575 (0.554 to 0.598) for the recalibrated text classifier, the review's numbers. Paper: Section 6.2 gives the pooled and the within-stratum figures and says that inside the largest cell the prior ranks tests at chance for the significance event and the text models a little above it. Question 5: the paper claims no within-cell discrimination for the prior.

**[major] The positive control shows the guard admits; it does not show the rung recovers the signal, the realized gain at each strength and size is not reported, and the text classifier is absent from the control.**
Fixed, done (T-066, calls 230 to 232; run 6 numbers). For every row of the sensitivity the realized out-of-time P2 minus P1 and the gain of the oracle are reported (`positive_control_sensitivity.rows realized_gain`, `oracle_gain`, `recovered_fraction`), and two backtests of the planted ledger with every rung including the text classifier exist, at 2,000 tests (the published control's own ledger, snapshot 20261104-8cc34d3af720; 20261105-8cc34d3af720 in run 7) and at 11,100 tests (snapshot 20261104-c7ca82ca15a6, 20261105-c7ca82ca15a6 in run 7; `positive_control_rungs`). Question 3: at 7,400 rows per cell and a planted lift of 1 percent the realized held-out P2 minus P1 is 0.00369 nats (0.00334 to 0.00401), 0.180 (0.164 to 0.197) of the oracle's 0.0204; in the rolling-origin backtest at 11,100 tests it is 0.0018 (0.0014 to 0.0023), 0.092 of the oracle's 0.0197, less because the early origins fit on short histories, and at 2,000 tests P2 equals P1 (0.0000, minus 0.0002 to 0.0003; the guard admits 2 of 24 pairs); the text classifier on the same ledgers scores below the base rate (`positive_control_rungs` n_tests 11100 cell ALL rung text_lr brier_skill minus 0.0168, minus 0.0222 to minus 0.0114; recalibrated minus 0.0134), and its event AUC in the headline-only cell is 0.526 against P1's 0.591. The boosted model's Brier gain in the headline-only cell at 2,000 tests (minus 0.0044 against the oracle's minus 0.0026, the number the review quoted) is 1.7 times the oracle's on intervals that overlap, and the model falls below P1 in that cell and pooled at 11,100 tests. Paper: Section 6.8, Appendix B, the abstract, contribution 3 and the limitations carry these numbers; Tables positive-control-gain and positive-control-rungs carry them all.

**[major] The learning curve's skill is measured against a P0 refit on the same subsample; "the challengers keep their pooled order" and "the curve crosses both gates" do not match the file.**
Fixed (call 204, run 6), as for R1's second blocking finding; both sentences are gone and the paragraph reads the fixed-baseline curve.

**[major] Two table captions carry log scores from a superseded run.**
Paper: as for R1's fourth finding. Question 6: the captions were written from the round-00 run and left when the scoring changed; the sweep of every caption found the two year tables' family sizes stale as well; every other number in the paper is generated by `build_tables.py`, drawn by the figure script, or sourced by a comment that the mechanical audit checks against the comment, the named table and the named report file (662 numbers at this pass, none unmatched).

**[minor] "The only direction signal this ledger carries is that the earliest-created arm tends to win" is contradicted by the text classifier's direction AUC and the decision value.**
Paper: Section 6.2 reads that the ladder's direction accuracy is no better than always_reference, the creation-order effect P1 learns through the cell mean, and that the text models carry a little direction signal apart from it (`tables.aggregate` cell ALL auc_direction rung text_lr 0.5410, rung P2 0.5202, rung P1 0.5010).

**[minor] "Highest on every measure" holds only for the four columns of the discrimination table; the text classifier's decisive-row accuracy is in the file and not in the paper.**
Paper: Section 6.2 says "highest on the four measures of that table" and gives the text classifier's direction accuracy on all rows and on the decisive rows (`tables.aggregate` cell ALL rung text_lr direction_accuracy 0.5548, direction_accuracy_decisive 0.6010) beside P1's 0.632 and always_reference's 0.658; Section 2 quotes the 0.601 where the pairwise classifier is placed against the winner predictors.

**[minor] 0.049 of the 0.149 nats is the fitted prior and 0.100 is the Student-t family.**
Paper: Section 6.2 says so where the 0.149 is quoted (`ablations/...--prior-normal.json` rung P1 logscore minus 0.9566 against P0 minus 1.0059).

**[minor] The boosted model and the local set carry a normal predictive, so their raw log scores mix the family with the model.**
Paper: Section 4.2 states that the two challengers' log scores carry the normal-family penalty the prior-normal ablation prices at 0.100 nats, and that the recalibrated rows settle the probability and nothing settles the log score. Argued: a t predictive of the same degrees of freedom for the challengers is not built in this round; the statement beside the table is what the review asked for as the alternative.

**[minor] Only the boosted model is searched; the text classifier's regularization and the local set's neighbour count are fixed by hand.**
Paper: Section 4.2 states it and reads the text result as a lower bound for its family.

**[minor] No single-headline run of the text classifier exists, so the paper cannot say what the reference headline bought the baseline.**
New item: `--pairwise off` with the challengers, reporting the text classifier's skill, AUC and decision value under both spaces.

**[minor] The cautionary run and the learning curve used 200 resamples while Appendix E says every backtest used 500.**
Paper: Section 6.1, Section 7, Appendix E and the two captions state the 200; the learning curve reruns at 500 under T-062; the cautionary run at 500 is a new item.

**[nit] The decision table's 3,799 tests against 3,797 scored.**
Paper: the caption says that the pooled rows count 3,799 test-origin pairs from 3,797 tests, two tests having contrasts that started in two quarters.

**[nit] The module docstring of `p2.py` still says "beats the rung below out of sample".**
Fixed (call 236): the docstring says what the rung is and that a candidate is admitted when it beats weight zero on the validation rows of the fit; a test pins the phrases.

Questions. (1) to (6) above.

## Reviewer R5, area chair

**[major] The two ablation captions state P1 scores that do not trace to any run5 report.**
Paper: as for R1's fourth finding; every caption with a number now has a source comment and the sweep is recorded in this letter.

**[major] "Pre-registered" is not supported by the record: the plan entered the repository in commit 145eaf7 with the first run2 reports.**
Paper: the word is gone from the paper. Section 9 opens with "Six hypotheses were fixed in writing in the plan before the final runs and are unchanged since; the repository's record is commit 145eaf7 of 3 November 2026, which holds the plan beside the first run's reports, so it shows the order within our own history and not a public timestamp"; the introduction says "fixed in writing before the final runs and unchanged since"; Section 5 and Section 9 read "the pooled interval is the primary claim"; the two archive-norm sentences in Sections 3 and 9 now say "registered confirmatory analyses" so that neither sense of the word remains. Question 3: there is no record older than 145eaf7. A byte-identical copy of the plan was registered publicly on 4 November 2026, after round 01 and before run 6 (repository journey-agents/mootcourt-plan, tag plan-registered-2026-11-04, commit f0b088c794dcea1a1eac9872cd15aeb1c2412976, pushed 2026-11-04T17:19:12Z, plan.md sha256 e6dab9062fd1dc59734e5e4374ba429d3edc06efe681f68bb81424d88f45b613); the paper cites it in Sections 5, 9 and 10 and says when it was posted, and never calls the plan pre-registered.

**[major] The decision table is the one table of intervals without adjusted bounds, and the verdict on the fifth hypothesis for the precedent rung rests on the unadjusted interval.**
Fixed: the decision table carries the adjusted columns (family of six at each budget; `tables.decision_value diff_random_adjusted_lo`, `_hi`, and under run 6 `diff_matched_adjusted_lo`, `_hi`): against the arm-count-matched random order the text classifier's bounds are 0.0158 to 0.0632 and the boosted model's 0.0093 to 0.0459, the precedent rung's minus 0.0038 to 0.0316 and the local set's minus 0.0086 to 0.0386, which is the review's reading. Paper: Section 6.4 and Section 9 read the hypothesis under the table-wide rule, confirmed for the text classifier and the boosted model and unresolved for the precedent rung and the local set; the abstract drops "the precedent rung by 1.5". Question 2: the table-wide rule; the columns are in the build (call 200); the remaining tables of intervals carry none, which Section 5 says; the arm-count-matched baseline of call 201 is what Section 6.4 and the hypothesis read.

**[major] What was compared on the matched splits are in-house re-implementations of the simplest member of each family; none of the published models was run.**
Paper: Section 2 reads "our pairwise TF-IDF classifier re-implements the simplest member of that family on matched splits and reaches 0.601 on the decisive rows; the published models were not rerun" and "the nearest neighbours are represented on the matched splits by in-house re-implementations of their simplest members, not by the published systems, so the negative on text is a statement about the TF-IDF and SVD feature space"; the abstract and the introduction say TF-IDF where they summarize the text result; Section 8 says "TF-IDF features of the two headlines". Question 4: no published ranker was run; a released fine-tune or a sentence-embedding kernel as a fourth challenger on the same origins and rows is a new item, and the paper says the ceiling tried here is the TF-IDF one.

**[minor] The rise of P1's skill at the smallest history is the baseline degrading, not P1 improving.**
Fixed (call 204, run 6): Section 7 reads the curve against the full-history base rate (P1 0.0007 at 123 rows rising to 0.0295) and gives the own-base reading beside it as the base rate's noise. Question 5: against the P0 fit on the same subsample in the reviewed version; the run 6 table shows the full-history base and Table learning-upworthy's P0 row is the subsampled base rate scored against the full one.

**[minor] The abstract is 434 words and reads as a second results section; the body stacks numbers.**
Paper: the abstract is about 370 words, keeps the four claims, and its second paragraph carries the powered negative with its one interval, the positive control in words, the text classifier's one interval, the leakage finding and the undecidable verdict; Section 6.4's three-budget sentence is cut to one clause with a table reference. The cut to about 200 words comes with the move to the single-column style, when the body is cut as well.

**[minor] Two statements of the round-00 letter do not match the artifacts.**
Paper: this letter quotes `gates.json` by key: `by_base_rate 0.09 by_target 0.90 n_200 175, n_400 250` (the release gate) and `by_target 0.80 n_200 125, n_400 200` (the research screen); by count the smallest cell exceeds the gate of 175 only, and Section 6.2 now says that even that label overstates it at 2.1 rows per test. The abstract was 434 words and is now about 370. The two lines of the round-00 letter carry dated corrections (part 2a).

**[minor] "Scores reproduce across operating systems to one part in 10^11" is sourced to no report.**
Paper: the number is removed. Fixed (call 239): `scripts/ci_score_report.py` runs the sample backtest on every Python version of the continuous-integration job and uploads `score-report-<python>.json` (P0, P1 and P2 log score and Brier skill to six decimals, with the platform and library versions) as an artifact; Section 10 names the artifact and says that agreement across platforms is read from the job rather than claimed.

**[minor] Venue fit: the document is not yet the artifact a datasets and benchmarks track evaluates.**
Paper: Section 10 gains a paragraph "Benchmark artifact" that lists what is released (the ledger schema, the snapshot digests and admission rules, the quarterly origins, the names of the refused files, the harness and the report card under MIT, the report files behind the paper), where the raw files live and under what terms (the publishers' repositories, CC BY 4.0, pinned checksums, nothing redistributed), how a new result enters (the same backtest on the same snapshot and a published report card with the gate verdict beside every skill), and who maintains the benchmark and how versions are named (we do; semantic versioning; a schema change is a minor version before 1.0; the snapshot digest names the data). Question 6 is answered there. The single-column style, its page limit and the checklist come at submission; the body is expected to need cutting then.

**[nit] "A few dozen live directions" describes the simulation framework, not one of the three screening systems.**
Paper: the introduction reads "each validated on private data by offline ranking or replay".

**[nit] "The only rung whose pooled interval excludes zero" ignores the two raw rungs that exclude it from below.**
Paper: "the only rung whose pooled interval lies above zero (the raw local set and boosted model lie below it)".

**[nit] Appendix tables 16, 19 and 22 are set at scriptsize inside a column-width resizebox and are not legible.**
Paper: the ablation table of the headline archive, the held-out selection-bias table and the three decision-value tables (whose new adjusted column had made them narrower still) are two-column floats; the sensitivity table is replaced by the positive-control gain table, a two-column float that carries the admission column beside the gains.

**[nit] Two bibliography entries are cited nowhere.**
Paper: `kohavi2017surprising` and `kaufman2011leakage` are removed; 77 entries remain, each cited; `paper/related-work.md` records the removal.

**[nit] The title names the system whose precedents never earn weight out of time.**
Argued: the title is kept as the benchmark's name, as in round 00; the negative is the first sentence of the abstract's second paragraph, and the positive control now bounds what precedents could have shown.

Questions. (1) The two measures do not contradict each other: the kernel moves the location often enough in the right direction to rank tests above random order on the unadjusted interval (and to a direction AUC of 0.520 against P1's 0.501), while the realized log-score loss sits on the bulk of the admitted pairs' rows, which points at the scale term (R3's second major finding); after adjustment the precedent rung's decision value is unresolved, and T-067 says which term carries the loss, after which the discussion gets the one sentence. (2) to (6) above.

## Reviewer R6, practitioner and documentation reviewer

The walkthrough is acknowledged with thanks; every output of tutorials 1, 2, 4, 5 and 6 matched to the character, and the three major findings are onboarding defects a newcomer meets before the first card.

**[major] The pip install path on a clone kept on an exFAT drive breaks `moot backtest` through the plotting library's sidecar files, and `moot doctor` reports OK in that state.**
Fixed, pending: M4 (one sentence at the README install step and in tutorial 1 that the environment must live on the internal disk; a troubleshooting entry quoting this exact error text) and call 226 (`moot doctor` fails with the count of sidecar files under site-packages and the cure, and `moot backtest` prints one line naming the cause and the doctor instead of the traceback). Question 4: yes.

**[major] `uv sync` on such a clone fails with an error the troubleshooting page does not quote, and damages an existing environment.**
Fixed, pending: M4 (the README install block says where the environment must live and links the entry; the entry quotes both error texts; the extras flag on the page matches the Makefile and CI, or the difference is stated).

**[major] `uv run moot` fails from the project folder the README tells the reader to create.**
Fixed, pending: M4 (`uv run --project ../mootcourt moot ...`, or activating the environment and calling `moot` directly; the docs test runs one block through uv from outside the clone).

**[minor] `moot init` and `moot backtest` are several times slower with the data root on an exFAT volume, with no progress line and a timing line that does not cover the run.**
Fixed, pending: M4 (a timing caveat beside "exFAT is fine") and call 207 (a heartbeat line from `moot init`, `moot backtest` and `moot simulate gate-power`, and a backtest timing line that covers the whole run). Question 3: where the extra seconds go is not yet measured and stays listed.

**[minor] Two more things a newcomer meets on such a clone are not on the troubleshooting page.**
Fixed, pending: M4 (two lines; the cleanup command's scope includes the git folder).

**[minor] The gate sizes are stated differently on every page.**
Fixed, pending: M4 (one sentence, repeated verbatim on the three pages, that the gate is a number of tests that depends on the base rate, with the three simulated rates and their sizes; the stale "400" removed from tutorial 6). Question 5: the quick gates of `moot init` are simulated at base rate 0.30 (75 and 150 tests) and the paper's at 0.09 (175 and 250); the sample ledger's base rate is now the headline archive's 0.09 and `moot init` simulates its quick gates at it, 175 and 250 tests (call 237); the tutorial outputs that print sample numbers are regenerated by the documentation builder (M4).

**[minor] `moot simulate gate-power` sizes a user's gates with the within-test dependence of a public archive nearest their rate, and the page does not say so.**
Fixed, pending: M4 (the page says the two dependence settings default to a public archive's values and where to read the ledger's own; the timing says ten to fifteen minutes) and call 207 (the command prints its assumptions and their source before it runs and measures them from the ledger with `--source`).

**[minor] The card's gate line reads "at base rate 0.30" beside a cell base rate of 0.117 or 0.275.**
Fixed (call 227): the gate line reads "at the nearest simulated base rate, 0.30 (this cell's own rate is 0.117)"; M4 for the card reference.

**[minor] A card for a ledger with no text features prints headline fields and stores `headline_changed` true for an empty headline.**
Fixed (call 228): the request line prints the text fields only when the request has a headline or a reference headline, and an empty headline stores `headline_changed` false. Question 2: yes.

**[minor] The first table of the backtest report carries two repeated and two "not computed" columns.**
Fixed (call 210): the decidable columns give the verdict in the unit of the gates and the README sentence that told the reader to ignore two columns goes (M4).

**[minor] The report card's gates heading says rows where the gates count tests.**
Fixed (call 229): "Tests needed".

**[minor] `P(true effect above 0)` is not explained in the tutorial or the glossary.**
Fixed, pending: M4 (one sentence in tutorial 1 and a glossary row).

**[minor] Reading the reliability report requires a Python snippet; there is no `moot reliability` command.**
Fixed (call 208): `moot reliability --source NAME` prints the table the snippet printed, or the JSON; tutorial 4 uses it (M4). Question 1: yes.

**[minor] The README's verification script needs a flag the sentence does not give, and ends in a traceback without it.**
Fixed, pending: M4 (the README sentence gives the flag); the script's one-line message is not in calls 207 to 229 and stays listed.

**[minor] One quantity has three names across the flag, the card and the prose.**
Fixed (call 228): the card and the help text say "planned units per arm" and `--impressions` keeps its name; M4 for the prose.

**[nit] A signed zero on the card.**
Fixed (call 209).

**[nit] Install wording differs across three pages.**
Fixed, pending: M4.

**[nit] `python` against `python3`.**
Fixed, pending: M4.

**[nit] The fit timing on tutorial 3.**
Fixed, pending: M4 ("15 to 30 seconds").

**[nit] The card id of tutorial 3 differs for a reason the page does not give.**
Fixed, pending: M4 (the card id also covers the gates in force; the page shows the skill section of the card).

Questions. (1) to (5) above.

## Reviewer R4, reproducibility chair (part 2a)

The clean-clone reproduction is acknowledged with thanks: from a fresh download and an empty data root every backtest, the positive control, the gates, both replays, both learning curves, the cautionary run, the three extras files and 45 of the 46 ablations regenerated with zero differing numbers, and 53 of 55 tables built from that run are byte-identical to the committed ones.

**[major] The shipped deployment-shaped guard-off ablation was written by the run-4 bundle and the reviewed code does not reproduce it: the unguarded P2 at origin 2020-07-01 scores 4.9161 against the shipped 4.9143, 554 entries move and two printed digits change.**
Fixed (run 6; since pass 9, run 7): every number of the paper is regenerated from one code state in one run folder, `paper/data/run7-tie-rank` (run 6, `paper/data/run6-forward-chaining`, repeated on commit 82ba862 under the tie rule of call 255; the three backtests, every ablation and both guard comparisons, the replays, the learning curves, the positive control and its two rung backtests, the extras, the gates, the card latency), with the three leakage audit JSONs inside it; the README lists which files are new, changed, removed and identical. The deployment-shaped guard-off ablation reads 4.7172 from the final code, so Appendix A says the rung gains 0.008 nats without the guard (guarded minus unguarded minus 0.0083, minus 0.0233 to 0.0029) and the table row follows. The timed run at the final commit is in the folder too (`run-log.json`: 2,052 seconds in all, 1,431 for the main pipeline, 964 the gate simulation, 585 the boosted challenger, the fetch of 15,470,807 bytes in 15.6 seconds; an upper bound measured under a load average of 13 to 16 at the start and 7.6 at the end, which Appendix E says). [Correction, 5 November 2026, after round 02 (R4-F3): those are run 6's figures; the run 7 folder's `run-log.json` reads 2,024.2 seconds in all, 1,263.9 for the main pipeline, 836.7 the gate simulation, 706.1 the boosted challenger, nothing downloaded (the three archives copied from the data root in 0.2 seconds, the data stage 41.9), a one-minute load average of 7.2 at the start and 92.0 at the end.] Question 1 (what moved the unguarded P2 at that origin between the run-4 bundle and the reviewed code) is answered in the run 6 README beside the rerun.

**[minor] "Scores reproduce across operating systems to one part in 10^11" traces to no artifact; the workflow runs on one image and no backtest.**
Paper: the number was removed in part 1. Fixed (call 239): `scripts/ci_score_report.py` backtests the bundled sample ledger on every Python version of the continuous-integration job and uploads `score-report-<python>.json` (P0, P1 and P2 log score and Brier skill to six decimals, with the platform and library versions) as an artifact; Section 10 names the artifact and says that agreement across platforms is read from the job rather than claimed. Question 2: yes, as above; a second runner image is a matter of the workflow matrix and is listed.

**[minor] The leakage audit's source is three text files on the launching team's data root, not in the package.**
Fixed (run 6): `leakage-audit-upworthy.json`, `-asos.json` and `-synthetic.json` sit in the run folder, every rung with zero rows both fit and scored, zero fit rows usable after their origin, zero rows outside their window and zero standard-error mismatches, and the source comment of Section 10 names them.

**[minor] The run folder mixes code states (the timed run, the gates file and the scale measurements predate the period rule) and the paper does not say so.**
Fixed (run 6): the timed run was repeated at the final commit and its `run-log.json` is in the folder (2,052 seconds in all against 1,469 before, the main pipeline 1,431, the gate simulation 964; a clean copy of the 656 files git would commit, tree digest 8b7092bb04f4d961), the gates file is regenerated in the same run (870 seconds; 794 in run 7), and the scale measurements are carried from run 5. [Correction, 5 November 2026, after round 02 (R4-F3): the run 7 timed run, the one Appendix E quotes, is 2,024.2 seconds in all, 1,263.9 for the main pipeline, 836.7 the gate simulation, from a clean copy of the 748 files git would commit at commit 82ba862, tree digest 00b348180c492b75.] Paper: Appendix E quotes the run 6 timed run, says that its wall time is an upper bound measured under load (a one-minute load average of 13 to 16 at the start and 7.6 at the end, from the run folder's README), and says that only the scale measurements predate the period rule, which moves no backtest number. Question 4: yes, both.

**[minor] The model ids are dated identifiers a reader cannot regenerate.**
Paper: Appendix E says that the model ids are dated identifiers of our artifacts, because the bundle hashes the snapshot id and the snapshot id carries the ingest date, and that the content digests and every score are what a reader matches (part 2a). Argued: the id is not made date-free in this round; the content digest identifies the data and the scores identify the fit. Question 3: the latter.

**[minor] Every committed table names the launching team's absolute data-root path as its source, and `make paper` rebuilds the figures but not the tables.**
Fixed (call 240): `build_tables.py` writes each header relative to the run folder, a test holds that no committed table names an absolute path, the Makefile gains `tables` and `paper` depends on `paper-figures` and `tables`, none of which reads the data root; the tables were rebuilt from the run folder in place and run 6 rebuilds them again. Paper: the commands table reads `make tables` (part 2a).

**[nit] 37 en dashes in the built PDF, from the citation-range compression of the class and the page ranges of the bibliography style.**
Argued: the writing rule covers the committed text, which the test checks; the class compresses citation ranges and the bibliography style sets page ranges, and the paper overrides neither. Listed for the lead's decision.

**[nit] The troubleshooting page quotes a different uv error and recommends a different sync command.**
Fixed, pending: M4 (call 243 hands the verbatim messages and the one-command ask to the documentation builder).

**[nit] The sdist holds 48 MB of paper data.**
Fixed (call 241): the sdist holds the package, its tests and its examples only (516,974 bytes against 10,208,715); the wheel is unchanged.

**[nit] `-q` twice hides the test count.**
Fixed (call 242): the workflow and the Makefile pass no `-q` beyond `addopts`; the count line is printed.

**[nit] The round-00 letter lists run-5 paths with run-4 model ids.**
Fixed: the letter's re-run section carries a dated correction with the run-5 ids (`c6d5d2c6950c`, `bbafeb17d444`, `f00625996a1c`), and Appendix E of the paper now carries run 6's ids (`dd73c75e92bd`, `d3e813b146ce`, `6377324df73a`); the round-00 letter is left as corrected in part 2a.

**[nit] "Reproduces every table with one command" in the abstract and contribution 4 against "one command per table" in Section 10.**
Paper: both read "regenerates every table from the report files, one command per table" (part 2a).

**[nit] The run-5 README's sentence on the ablations is contradicted by the major finding.**
Fixed: the run 6 README states which files were regenerated, which are new, which were removed and which is identical, and that every file came from one code state (call 243).

Questions. (1) to (4) above.

## Items with no task yet (updated in part 2a)

Done since part 1 by the design calls named above: the caption test (call 235), the per-cell gate read (205), the all-rows paired interval (205), the event rate by year (205), the docstring of the precedent rung (236), the public registration of the plan, the continuous-integration score report (239), the round-00 letter's lines (part 2a), the sample ledger's base rate (237), the card's note on a defaulted reference headline (238), relative table headers and `make tables` (240), the sdist (241) and the pytest flag (242).

Still open:

1. The cautionary run at 500 resamples (R3 minor 7), unless run 6 reruns it.
2. A single-headline run of the challengers (R3 minor 6).
3. A stronger text representation as a fourth challenger (R5 major 4, optional).
4. Dating the seed at the fit clock when the ledger's last result is within the staleness limit (R2 minor 9).
5. The outcome's ledger snapshot id and the two post-launch fields at the top level of the deployment-shaped features (R2 nit 1).
6. A join that brings outcomes older than the trailing window says so (R2 nit 3).
7. An admission rule that depends on realized counts, written into the ledger's provenance; the doctor's counts of cards with no row id, an unknown row id, a passed horizon without an outcome, or an unadmitted test; the "fewer than two tests in the window" line; the verify script's one-line message; where the extra seconds of a backtest on an exFAT data root go (R2 minors 8, 10 and 11; R6 minors 4 and 13).
8. The single-column style and the checklist of the target track at submission (R5 minor 9).
9. En dashes in the rendered PDF from the class and the bibliography style (R4 nit); a second runner image in the continuous-integration matrix (R4 question 2).


## Diff of the paper's claims between round 00 and this letter (parts 1, 2a and 2b)

Changed.
- The precedent rung: "loses 0.004 nats" (round 00 and part 1, the leave-one-test-out default) becomes "equals the prior on skill and on the log score within the interval (plus 0.0004 nats, minus 0.0003 to 0.0012)" under the forward-chaining default of call 206 (run 6); the admitted pairs' realized difference becomes plus 0.0010 (minus 0.0007 to 0.0025) on 8 of 27 pairs, with a location part of plus 0.0036 and a scale part of minus 0.0026; "the precedents move the forecast by less than the noise of selecting them" returns as the negative result, with the decomposition behind it; leave-one-test-out is the ablation (minus 0.8606). Claims C10, C22, C54, C60; pass 10 reads "no better than" and the pooled figure as a cancellation (C55).
- Decision value: read against a random order matched on the number of arms; the text classifier keeps plus 0.039 (2.2 to 5.4 points), the boosted model plus 0.028, the precedent rung plus 0.014 and the local set plus 0.015 are unresolved after adjustment; the fifth hypothesis is confirmed for the first two, unresolved for the other two, failed by construction for the prior; the verdict counts read one confirmed, four in part and one refuted under the rule Section 5 now states (a hypothesis is read part by part; the first is held in part because its base-rate and image-only parts hold; corrected 4 November 2026 after the claims audit). Claims C34, C36, C37, C38; pass 10 adds the registered-baseline reading (C123, C124).
- Learning curve: scored against the full-history base rate; P1 rises from 0.001 at 123 rows to 0.030 at the full history, P2 sits above P1 from 2,991 rows on; "crosses both gates" and "more history does not add discrimination" withdrawn. Claims C105, C121.
- Positive control: "the guard responds to a planted lift" becomes "admits a planted lift at the size of the largest cell (97 percent of cells) and the rung recovers about a fifth of it (0.18, 0.16 to 0.20)"; the 4,000-contrast control admits no weight in the planted cell under forward chaining; the text classifier fails the control; P2 is the only rung above P1 at 11,100 tests. Claims C12, C24, C97, C119, C122.
- Discrimination: pooled AUCs are kept and read beside the within-stratum ones (P1 0.530 pooled over strata, 0.502 within the headline-only cell; the text classifier 0.564 and 0.575). Claims C51, C52.
- Abstention 14.1 percent (was 13.2); the replay abstains on 1,457 cards and covers 89.5 percent of 11,790 outcomes (was 1,361 and 90.1 of 11,886); four flagged weeks as before. Claims C80, C85, C86.
- The smallest cell: "decidable at a skill of 0.20 alone" becomes "undecidable at both skills at its own dependence (318 and 454 tests)". Claim C63.
- Kernel weight beyond the listed precedents: 0.52 to 0.65 of the total at ten thousand to three hundred thousand contrasts (was 0.15 to 0.65). Section 9, no claim id (the register covers the abstract, the hypotheses, Section 6 and the conclusion).
- "Pre-registered" becomes "fixed in writing before the final runs and unchanged since", with the commit named and the public registration of 4 November 2026 cited; "compared on matched splits" becomes "re-implementations of the simplest members on matched splits; the published models were not rerun"; the cross-platform number is withdrawn and the continuous-integration artifact named; the captions carry run 6 values; Section 4.3 describes the loop as it runs (calls 220 to 225); Section 8 reads "a paired, gated comparison". Claims C26 (the record of the hypotheses), C106 (the paired, gated comparison); the related-work sentence and the continuous-integration artifact carry no claim id.

Unchanged. The headline numbers: 0.149 nats over the base rate (0.100 of them the Student-t family); Brier skill 0.0015 (minus 0.0018 to 0.0048) on 3,797 tests against a release gate of 250; the 100th percentile of the clustered null; coverage 1.000 to 0.655 across the deciles; the cautionary run's minus 0.1074; the deployment-shaped archive undecidable at every gate and overconfident on calibration and coverage (its skill interval spans zero after adjustment); the challengers' pooled skills; the gates; P0, P1 and the challengers equal to run 5 to the last digit.

## Corrections of 4 November 2026, after the claims audit

The statistician's audit of the claims register (`paper/reviews/claims-audit.md`, convergence plan Task 3 step 6) weakened 22 of 106 rows and the paper was corrected in pass 8; every answer above that quoted an old sentence is corrected in place and marked. The changes, by claim id: C14, C34, C71, C102 and C107 print 3.9 points and plus 0.039 (`diff_matched` 0.039459, rounded once); C80 prints 14.1 percent (`abstention.rate` 0.141466); C50 prints 0.012 (`adjusted_hi` 0.012489); C51 prints 0.564 (`auc_event_within` 0.564487); C84 prints 0.117 (`event_rate` 0.117460); C27 and C46 name January 2015 as the narrowest P1 over P0 margin (0.068 nats, minus 0.731 against minus 0.799), not July 2013, which is the lowest pair of scores; C26 and C28 follow the verdict rule Section 5 now states (one confirmed, four in part, one refuted; the first hypothesis is held in part, with the headline-only paired difference plus 0.0008, minus 0.0007 to 0.0020); C12, C24, C119 and C122 say "about a fifth" (0.180, 0.164 to 0.197); C23 names the fixed weight of one (minus 0.869) as the largest departure beside leave-one-test-out (minus 0.861); C78 says the top rung and the prior keep their places at a tenth and a half while the middle rungs reorder; C89 reads the deployment-shaped overconfidence from calibration and coverage, its skill interval spanning zero after adjustment; C92 reads the synthetic ECE at percentile 95.2 as just past the rejection line; C99 shows the text classifier's intervals at both sizes; C101 and C102 qualify "nothing" by the gate and by adjustment; C105 and C121 read the learning curve as unpaired with overlapping intervals; C112 says the text classifier's raw skill sits above the prior's; C113 says the resolution term does not order the rungs as the AUC does (P0 above P1 and P2); C116 attributes the abstention reading to the novelty trigger; C118 limits the boosted model's win to the Brier score. Three digits outside the audit's scope were corrected the same way (Section 7: minus 0.010 and 0.002; Appendix B: 0.026), and every `% src:` comment touched now carries the report's own digits.

## Corrections of 5 November 2026, after round 02 (R5-F5 under rubric item R5.9; R2 question 4)

Statements above that the artifacts have overtaken since this letter was written, corrected here and not in place.

- "Still open" items 4 to 7 were closed after the letter by `docs/method.md` calls 248 to 254: call 248 dates the seed at the fit clock when the ledger's last result is within the staleness limit (item 4; the R2 minor answered "Pending, listed: dating the seed at the fit clock ... is not in calls 220 to 225"); call 249 writes the ledger snapshot id on every outcome record and leaves the two run-length fields at the top level by decision (item 5; the R2 nit answered "Pending, listed: not in calls 220 to 225"); call 250 makes a join that brings outcomes older than the trailing window say so (item 6; the R2 nit answered "Pending, listed"); call 251 prints "fewer than two tests in the window" and dates the entry at the first outcome in the window (item 7, first part; the R2 minor answered "Fixed, pending: M4 corrects both sentences; the 'fewer than two tests in the window' line ... stays listed"); call 252 counts the cards no join will score, including a card with no row id, an unknown row id, a passed horizon without an outcome and an unadmitted test (item 7; the R2 minor answered "Fixed in part (calls 220 and 222)"); call 253 makes the verify script name what is missing in one line (item 7; R6 minor 13); call 254 leaves the admission rule's place in the provenance to the operations manual, not built (item 7, R2 minor 8, which round 02 raises again as R2-F4). Where the extra seconds of a backtest on an exFAT data root go (item 7, R6 minor 4) is still unmeasured.
- "The abstract is about 370 words" (R5 minor 6): the abstract was 405 words at round 02's commit 9f725b1, and pass 10 (5 November 2026) cut it to 250 under decision 3 of round 02 (at most 250 words, counted as the whitespace-separated words of the abstract's text lines with the source comment lines removed; no venue named, a datasets and benchmarks track stated in Section 10).
- "77 entries remain, each cited" (R5 nit 13): 81 entries since pass 8, which added three fetch-verified sources for the challengers and one for the registered plan, recorded in `paper/related-work.md`.
- The R2 answer to round 01 finding 6 (the card's own-cell figure) quoted the run 5 headline-only figures (minus 0.0048, minus 0.0085 to minus 0.0016, below zero) as the ones the card will print; under run 7 the card prints P2's headline-only Brier skill minus 0.0036 (minus 0.0084 to 0.0007, including zero; `tables.aggregate[cell=headline_only,rung=P2] brier_skill`), and P1's is the one below zero (minus 0.0043, minus 0.0085 to minus 0.0006).
- The four marks beside the protocol's three ("Paper:", "Fixed, pending:", "Pending, listed:", "New item:") are read as follows: "Paper:" is a fix made in the paper's text; "Fixed, pending:" and "Pending, listed:" are fixes assigned to a task that was open when the letter was written (closed or not as recorded above); "New item:" is a fix adopted as a task. The round 02 letter uses the three marks only.
- The claim ids of the between-rounds diff are now written beside each line of the diff section above (pass 10).
