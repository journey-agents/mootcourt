# History-amount comparison: design and decisions

Written 10 November 2026, before the result it describes exists. It follows a review of paper version 2.

## Why

The paper reads "the fitted prior (P1) beats the base rate (P0) by 0.120 nats on the log score" as evidence that past experiments predict the distribution of the next result. A review found that this does not follow. P0 and P1 are both fitted to the same visible history, so their difference measures one way of using history against another. It does not measure what history adds.

The learning curve already varies the amount of history. At the final origin with enough held-out tests it refits every rung on a random fraction of the history's tests and scores the same held-out rows. Its report holds each rung's mean log score at each fraction, and the paired difference of each rung from P1 at the same fraction. It holds no paired comparison of one rung with itself across fractions, so the paper cannot say with an interval whether more history gives a better forecast.

## What was seen before this was written

The point estimates of the mean log score by fraction in `paper/data/run8-randomization-window/learning-curve-upworthy-20261106-2dc461f52ea4.json` were read on 10 November 2026, before this design. For P1 they run from minus 0.812 at a fraction of 0.01 (26 history tests) to minus 0.730 at the full history (2,608 history tests). For P0 they run from minus 0.884 to minus 0.761. No interval for a difference between fractions has been computed or seen. The paper will say that this comparison was added after a review and after those point estimates were read.

## What is added

One additive key in the learning-curve report, `paired_vs_full`, with a note. For each fraction below 1 and each rung that has a log score or a Brier score:

- the paired difference on the held-out rows both runs scored, the rung fitted on the subsample minus the same rung fitted on the full history: `logscore_minus_full` (nats per row, below zero means the smaller history is worse) and `brier_gain_over_full` (the full-history Brier score minus the subsample's, below zero means the smaller history is worse);
- the mean of that difference over the subsample seeds;
- a 90 percent interval by test: the percentile interval of the seed-averaged by-test resample draws, with the same resamples and seed as the report's existing paired key, so the interval is of the same kind as `paired_vs_p1`;
- the standard deviation of the difference over seeds, and the number of paired rows and seeds.

No existing key changes. The fractions, seeds, resamples, origin and rungs are those of the existing stage: `scripts/run_experiments.sh --only lc-upworthy` (fractions 0.01, 0.02, 0.05, 0.1, 0.25, 0.5 and 1; 20 seeds; 500 resamples). The retailer's curve is rerun too (`lc-asos`), for the record; the paper reads only the headline archive's.

## Decisions fixed now

1. **Primary reading.** P1, log score, the smallest fraction against the full history. It is the nearest the design comes to "little history against all of it". The other fractions and P0 are printed beside it and are descriptive.
2. **Level and kind of interval.** 90 percent, by test, unadjusted, as for every pooled primary interval in the paper. The table says so.
3. **Words.** "Shown" needs the primary interval to lie wholly below zero. An interval that contains zero is "not shown".
4. **What a null means.** If the primary interval contains zero, the backtest cannot show, at this origin and on these held-out tests, that P1 fitted on about 26 tests forecasts worse than P1 fitted on about 2,600. The paper would then say that neither the 0.120 nats nor the learning curve shows what history adds, and the answer to the first research question would lose "the prior predicts the distribution of the next result" as a claim about history.
5. **What a result below zero means, and does not.** It shows that more of this archive's history gives a better distribution forecast at one origin, on 318 held-out tests, for a random subsample of tests. It does not compare history with no history: the smallest fraction still has about 26 tests. The subsample is random by test and is not the earliest tests, so it does not replay a team early in its life. It is one origin, the one the learning curve already uses, and the base rate there is known to lag the event rate.
6. **No change to the method follows from the result.** If a number is surprising it is reported as it is.

## Code state and run

- Code: `src/mootcourt/learning_curve.py` (the new key), with a test in `tests/`. Existing numbers of the report must not change: the diff of the new report against run 8's is additive, and the build stops otherwise.
- The stage is rerun at a later commit than the rest of run 8 (5e4fedf). The run folder's README and the paper's Versions list will name that commit and say which report it wrote.
- A table from the new key is built by `paper/summary_tables/`, not typed.
