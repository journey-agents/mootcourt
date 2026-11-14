# Run 9: exposure fixed on visible rows as the main run, and one confirmatory reading

Written 14 November 2026, before any result of run 9 exists. It follows a review of the paper by four fresh readers and four decisions of the user, recorded below.

## The user's decisions (14 November 2026, recorded here as the rule on the confirmatory file requires)

1. The run with exposure fixed on visible rows becomes the main run. The run that reads realized traffic becomes a labelled diagnostic.
2. The precedent rung (P2) is cut down in the paper to one paragraph of the body plus the appendix, and the abstract says the paper cannot test whether similar past tests help.
3. The paper is retitled to one public archive of headline tests. The retailer's archive leaves the glance table and becomes an appendix check of the mechanics.
4. The Upworthy confirmatory split is opened once, after the code is frozen at a commit and the readings in Part C are registered. No other use of that file is authorized. The file is not on this machine; fetching it is a download and needs the user's approval when the time comes.

## What was seen before this was written

Every report of run 8, including the ablations that already hold the new main setting for the ladder: `--exposure cell-median-visible`, `--exposure cell-median-visible+base-density-t` and `--exposure cell-median-visible+base-recency-quarter`, their by-origin readings, and the reviewer runs of 13 November. So the ladder's numbers under the new main setting are known (P1 minus the Student-t base rate 0.007 nats, interval 0.003 to 0.011; without July 2014 about 0.001; P1 Brier skill 0.0069). Not seen: the challengers, the decision value, the learning curve, the sizing simulation, the calibration size check, the gates by stratum and the window ablation under exposure fixed on visible rows; any run with another assumed end of a test; anything from the confirmatory file.

## Part A: the new defaults

- `moot backtest --exposure` defaults to `cell-median-visible`. The value `planned` (each row's own realized traffic, the stand-in) stays and is the diagnostic. `--base-density` defaults to `t`; `normal` stays as an ablation. Nothing else about the method changes.
- The setting touches Upworthy rows only, as before. The retailer and synthetic ledgers are untouched by `--exposure`; their base rate's log score changes with the density default.
- The weekly replay issues cards through the production path and keeps the exposure a request states. It is labelled so in the paper and is not a main result.
- Ablations of run 9 are all relative to the new main. Dropped: the three `exposure-cell-median-visible*` variants (now the main) and the whole-ledger variants `exposure-cell-median*` (the diagnostic that reads later rows leaves the paper; run 8 keeps its reports). Added: `--exposure planned`, `--exposure planned --base-density normal` (run 8's main setting), `--base-density normal`. Kept: every other variant of `scripts/run_ablations.sh`, including `--base-recency quarter`, `--base-recency cell-quarter` and `--recalibrate-ladder on`.
- The cautionary run keeps its own setup and adds `--exposure planned --base-density normal`, so it is still the first specification.
- The reviewer runs are repeated at the run's commit: the calibration size check on the new main scores, the planted control at seeds 7 to 11, the learning curve at all seven origins, the split-half spread.

### Decisions fixed before results (Part A)

- The headline is P1 minus P0 on the log score in the main run, pooled, with the interval by test (quarters fixed), the interval with quarters as units, and both with each origin left out. Wording by rule: "shown" only if the interval with quarters as units lies above zero; otherwise "not shown", with the pooled interval described as a statement about these rows. The known ablation values put this at "not shown"; the run 9 main report must reproduce the ablation's ladder numbers to rounding (same code path), and a difference above 1e-6 in P1 minus P0 is a defect to find before anything is written.
- Brier skill of each rung on the realized event and on the planned event, with the family adjustment as before. With exposure fixed the planned standard error is one value per cell and origin, so the two events differ less; both are printed and the text says which is which.
- Challengers: the same three, raw and recalibrated, same reading rules as run 8 (an interval that spans zero is "not shown").
- Decision value: the paper's sentence becomes "no model is shown to rank tests better than counting arms" unless the text classifier's paired difference against the arm-count rule has an interval above zero at a quarter budget.
- The realized-traffic diagnostic is reported in one table: the same headline rows under `--exposure planned`, so a reader sees what the stand-in adds.
- If a table of run 8 has no counterpart in run 9 because its ablation was dropped, the table leaves the paper.

## Part B: the assumed end of a test

- Why: each test's end is assumed to fall seven days after its last arm was created, and the visibility rule rests on it. It was never varied.
- `scripts/rebuild_upworthy_ledger.py` gets `--horizon-days N` (default: the configured seven). Two ledgers, 14 and 28 days, each fitted and back-tested with the ladder only (no challengers), like the window ablation, into `reports/horizon-14` and `reports/horizon-28`.
- Reported: scored tests and rows, P1 minus P0 on the log score with its interval, P1 Brier skill with its interval, for 7, 14 and 28 days.
- Reading, fixed now: the assumption "does not move the reading" if at 14 and at 28 days the sign of P1 minus P0 and whether its interval excludes zero match the main run, and the same for Brier skill. Otherwise the paper says which reading depends on the assumed end.

## Part C: the confirmatory reading (registered before the file is fetched)

- Code state: the commit of run 9's paper text, tagged before the file is fetched. No change to `src/` after the tag except the one loader change below, which is made and tested on the exploratory file before the tag.
- Loader: `scripts/` and the loader refuse a file named confirmatory. One explicit option, `--confirmatory-decision 2026-11-14`, lets `moot ingest` read the confirmatory packages file into its own ledger and reports directory (`reports/confirmatory`). Nothing else reads it.
- Procedure: fit and back-test the confirmatory ledger with the run 9 main settings and the three challengers, quarterly origins, seed 0, 500 resamples; then the by-origin script and the decision-value table. Models are fit on the confirmatory ledger's own earlier tests (the same rolling design); nothing is tuned on it. One run; a crash is fixed only if the fix cannot change a number, and is reported.
- Primary readings, three, with their rules:
  1. P1 minus P0 on the log score, pooled, interval by test with quarters fixed, and the Student-t interval with quarters as units. "Confirmed lead" needs the interval with quarters as units above zero. "Not shown" otherwise. "Base rate ahead" if that interval lies below zero.
  2. P1 Brier skill on the realized event, 90 percent interval by test. Skill is "shown" only if the interval lies above zero; with three primary readings the bound printed beside it is Bonferroni-adjusted for three.
  3. The text classifier's captured positive lift at a quarter budget minus the arm-count rule's, paired by test. "Ranks better than counting arms" only if the interval lies above zero.
- Secondary, reported without verdict words: calibration percentile of P1 with both binnings, coverage of the 80 and 90 percent intervals, P2 minus P1, the same three readings with the date rule applied as in the exploratory split (the window is in both splits) and with it off.
- The exploratory numbers stay in the paper as they are. A confirmatory section reports the three readings and says, for each, whether it agrees with the exploratory reading.
- A null on all three is a result and is reported as the paper's main finding: on fresh data the fitted prior is not shown to beat a heavy-tailed base rate, has no shown skill on significance, and no model ranks better than arm count.

## Part D: the paper

- Title names one archive. Structured abstract in five parts, about 250 words, four findings: the heavy-tailed base rate nearly matches the fitted prior; no skill shown on which test is significant; calibration fails mostly through level; ranking no better than counting arms. Plus the exploratory statement and, once run, the confirmatory reading.
- The glance table has one archive column and the synthetic check; notes cut to the four that change how a row is read.
- Section 6 reports the new main run. One table gives the realized-traffic diagnostic. The whole-ledger diagnostic and every sentence comparing two fixings leave.
- P2: one paragraph in the body (what it is, that the guard admits it rarely, that it is not shown to help, that the control recovers under a tenth of a planted signal so the paper cannot test the question) and the existing appendix material.
- The retailer: one appendix section, "a check of the mechanics on a second archive".
- One appendix table lists each analysis, whether its reading was fixed before or after results, and what changed; inline history leaves.
- Limits named by the reviewers and not addressed by a run are stated once each: challengers keep a normal predictive; the decision value's target (the largest observed lift) rewards noise; gates are sized for skills far above those measured; only two recency rules for the base rate were tried.

## Tasks

1. Defaults and names (Part A): tests first in `tests/test_challengers_ablations.py` and `tests/test_review_n.py` for the variant names under the new defaults (`exposure-planned`, `base-density-normal`, empty for the main), then `cli.py` and `harness.py`; `scripts/run_ablations.sh`, `scripts/run_experiments.sh` (cautionary flags); fix the tests that assumed the old defaults.
2. `--horizon-days` (Part B): test on a small frame that usable_after moves by the given days; stages `horizon-14`, `horizon-28` in a driver `scripts/run_run9_extras.sh` together with the repeated reviewer runs.
3. `--confirmatory-decision` (Part C): test that ingest refuses the name without the option and accepts it with the exact date; no file is fetched in tests.
4. Full suite green, commit, run 9 (`scripts/run_experiments.sh` then the extras driver), assemble `paper/data/run9-visible-exposure`, README with what changed against run 8.
5. Table builders and paper (Part D), claims register, paper-check.
6. Fresh review round (four readers). Fix. Repeat until each says the paper is good.
7. Tag, ask the user to approve the download, fetch, run Part C once, add the confirmatory section, final review.

## Post-run notes

Written 14 November 2026 after run 9 finished and before any paper text that depends on its results. Run 9 ran at commit b2e3713 (the same `src/` and `scripts/` as 85f2bb4), started 11:30 UTC, was suspended from 11:35 to 12:31 UTC at the request of another session on the machine, and ended about 17:40 UTC. Numbers below are read from the reports in `paper/data/run9-visible-exposure`.

### What happened in the run

- One stage failed: the leakage audit of the Upworthy scores reported every `s_star` as a mismatch. The cause is the audit, which recomputed `s_star` from each row's own exposure, the default before run 9. The audit now takes `--exposure cell-median-visible` and recomputes the fixed exposure itself from the rows visible at each origin, without the package's view. It was rerun after the run, at a later commit, on the unchanged scores: zero violations. The scores and every other report are from the run's commit.
- Defect check of Part A: the main report's ladder rows equal run 8's ablation with the same setting to 1e-9 (P1 minus P0 0.006875). No defect.
- The planted ledgers and the ledger with the date rule off were rebuilt on 14 November, so their snapshot ids carry that date; their content hashes are those of run 8.

### Each rule of Part A and its branch

- Headline. P1 minus P0 on the log score, pooled: 0.0069 nats, interval by test 0.0030 to 0.0106. With quarters as units: 0.0036, interval minus 0.012 to 0.019. The rule's branch is "not shown". Leaving one origin out, the interval by test stays above zero for 6 of 7 origins (not without July 2014: 0.0008, minus 0.0044 to 0.0060), and the interval with quarters as units lies above zero for 1 of 7 (only without January 2014).
- Brier skill, realized event. P1 0.0069 (0.0041 to 0.0100), family-adjusted 0.0013 to 0.0125; P2 0.0081, adjusted 0.0021 to 0.0141. By the rule both are shown, pooled, and they are under one percent of the base rate's Brier score. By cell the adjusted intervals of P1 span zero in all three cells. Part D of this plan listed "no skill shown on which test is significant" as a finding; that phrase was written from the realized-traffic run and is wrong for the new main run by this plan's own rule. The paper will say: a skill under one percent, pooled, not shown in any single cell, and none within a cell and quarter, where P0 and P1 give every test the same probability (exact-tie AUC 0.5 by construction).
- Brier skill, planned event: P1 0.0127 (0.0096 to 0.0155). Printed beside the realized one, as the rule says.
- Challengers (realized event). Raw GBM minus 0.068 and raw local_eb minus 0.009, both intervals below zero: worse than the base rate. Recalibrated GBM, recalibrated local_eb, the text classifier raw (0.0070, minus 0.0005 to 0.0140) and recalibrated (0.0045, minus 0.0003 to 0.0100) all span zero: not shown.
- Decision value. The text classifier minus the arm-count rule at a quarter budget: minus 0.002 (minus 0.027 to 0.022). Branch: "no model is shown to rank tests better than counting arms". P0, P1, P2, GBM and local_eb are below the arm-count rule at that budget with intervals below zero.
- Realized-traffic diagnostic (`--exposure planned`): P1 minus P0 0.0196 (0.0155 to 0.0232); with quarters as units 0.012 (minus 0.006 to 0.030); P1 Brier skill 0.0023, adjusted interval spans zero. One table, as planned.
- Run 8's main setting (`--exposure planned --base-density normal`): P1 minus P0 0.120, as in run 8. Kept as the first specification in the cautionary account only.

### Part B: the assumed end of a test

- 14 days: P1 minus P0 0.0077 (0.0039 to 0.0115), P1 Brier skill 0.0065 (0.0035 to 0.0097). 28 days: P1 minus P0 0.119 (0.096 to 0.143), P1 Brier skill 0.0071 (0.0044 to 0.0102). Scored rows and tests are the same at all three values (10,697 and 2,949).
- By the rule fixed before the run (sign, and whether the interval excludes zero) the assumption "does not move the reading" at either value, for both metrics.
- The rule is too coarse for what the 28-day run shows, and the paper will say so. The gap at 28 days is 17 times the main run's and comes from one cell of the first origin: at April 2013 the image-only cell has two visible rows under a 28-day end (ten under seven days), the base rate fitted on two rows scores minus 6.7 nats per row on that cell's 213 rows, and P1 does not degrade there. This was found after the result. To put it on record with report keys, the by-origin script was run on the two horizon ledgers after the result (not planned): at 28 days, leaving the first origin out gives 0.0029 (minus 0.0012 to 0.0066), an interval that spans zero; at 14 days every leave-one-out interval but July 2014's stays above zero, as in the main run. So the paper's reading: the Brier reading does not depend on the assumed end; the log-score lead of P1 at 28 days is a failure of the base rate on a cell with two rows of history, not evidence for the prior, and without that origin the lead is not shown.

### The reviewer runs, repeated at the run's commit

- Calibration size: the rejection share of calibrated forecasts at the observed correlation is 0.037 to 0.077 over the 12 rung and stratum pairs with equal-width bins (image-only P0 highest). Verdicts are read against the simulated critical value as before.
- Planted control, five seeds: the share of the oracle's gain that P2 recovers, pooled, is 0.076 to 0.092. P2 minus P1 in the headline-only cell falls inside the real archive's interval at 4 of 5 seeds (run 8: 5 of 5, against run 8's interval); seed 11 lies above it. The paper's sentence stays that the control recovers under a tenth of a planted signal, and the count is reported as 4 of 5.
- Learning curve by origin: a quarter of the history is worse at 7 of 7 origins, a half at 5 of 7, as in run 8.

### Changes to Part D that follow

- Finding 2 of the abstract is reworded as above (a small pooled skill, none within a cell and quarter).
- The horizon table reports 7, 14 and 28 days with the leave-first-origin-out reading at 28 days, labelled as added after the result.

## Addendum: the Brier skill by origin (written 14 November 2026, after a review of the rewritten paper, before the script below has run)

A statistics reviewer of the rewritten paper pointed out that the paper reads the prior's lead on the log score with the quarters as units and reads its Brier skill only with tests resampled, although it says the skill is a level per cell and quarter. The reviewer computed, from the saved scores, the skill by origin and a Student-t interval on the seven origin skills, and found that one stratum of the first origin (image-only, April 2013), where the base rate's probability is exactly zero, carries a large share of the pooled gain.

What was seen before this was written: the reviewer's own figures (P1 on the main event about 0.010 with an interval just above zero with quarters as units; on the planned event an interval that contains zero; P2 about 0.014 with an interval above zero; the pooled skill without the zero-rate stratum about 0.004 with an interval above zero). No report key holds them, so none of them may enter the paper.

What is added: `scripts/by_origin_skill.py`, which reads the saved scores of the main run and writes, for P1 and P2 and for the event at realized and at planned precision: the pooled skill with its interval by test (it must reproduce the report's value); the skill at each origin with an interval that resamples that origin's tests; the pooled skill with each origin left out; a Student-t interval on the origin skills with the origins as units, and that interval with each origin left out; and every stratum of origin and cell in which the base rate's probability is zero, with its rows, its visible rows, its event rate, its share of the pooled Brier gain and the pooled skill without it.

Reading, fixed now: the skill is "shown with the quarters as units" only if the Student-t interval on the seven origin skills lies above zero. The paper prints both intervals side by side for the main event and for the planned event, says which strata have a base rate of zero, and gives the pooled skill without them. The verdict of the second hypothesis, read pooled, is worded with both units. Given what was seen, the expected branch is: shown with quarters as units on the main event, narrowly; not shown on the planned event.

Result (14 November 2026, script at commit e903ef9). The pooled skills reproduce the report's. With the quarters as units, P1 on the main event is 0.0099 (0.0013 to 0.0185) and P2 is 0.0137 (0.0031 to 0.0243): shown, narrowly. With each origin left out in turn, P1's interval with quarters as units lies above zero in 4 of 7 cases and P2's in 5 of 7. On the planned event both intervals contain zero (P1 minus 0.0008 to 0.0264): not shown. One stratum has a base rate of zero, image-only at April 2013 (213 rows, 10 visible rows, event rate 0.113); it carries 0.42 of P1's pooled Brier gain, and without it the pooled skill is 0.0041 (0.0020 to 0.0062). The branch is the expected one.
