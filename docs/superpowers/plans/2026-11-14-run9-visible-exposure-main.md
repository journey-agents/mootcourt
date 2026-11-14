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

(To be written after the run and before the paper text changes.)
