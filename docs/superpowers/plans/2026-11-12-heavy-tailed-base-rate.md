# A base rate with a heavy-tailed density: design and decisions

Written 12 November 2026, before the result it describes exists.

## Why

The headline of the paper is that the fitted prior (P1) beats the base rate (P0) by 0.120 nats on the log score. P0 is scored with a
normal density and P1 with a Student-t. An existing ablation gives P1 a normal prior and finds a gain of 0.045 nats, so 0.075 nats of
the headline is the shape of the density. Every review round asked for the comparison the other way round: a base rate that is allowed
heavy tails. The method section says such a base rate "might be a harder baseline, and we did not run it". This run does it.

## What was seen before this was written

- The main run: P1 minus P0 is 0.120 nats (0.106 to 0.136).
- The ablation with a normal prior: P1 minus P0 is 0.045 nats (0.034 to 0.055).
- Nothing about a heavy-tailed base rate has been computed or seen.

## What is added

One setting of the backtest, `--base-density t` (default `normal`, which changes nothing). With it, P0's density for the log score is a
Student-t in place of the normal:

- per cell and origin, a location, a scale and the degrees of freedom are fitted by maximum likelihood to the visible observed
  estimates `y` of that cell, the same rows the normal base rate reads;
- the degrees of freedom are chosen from the grid the prior uses (3, 5, 10, 30 and the normal limit), by the likelihood;
- the scale has the same floor as the normal base rate's variance, the median squared standard error of the visible rows, so two visible
  rows cannot give a near-zero spread;
- a cell with fewer than two visible rows falls back to the global fit, as now.

Nothing else about P0 changes. Its probability of a significant positive result is still the visible share of such rows, so the Brier
skill of every rung, which is measured against that probability, is unchanged, and the report must show that. Its intervals are still
the empirical quantiles. Its CRPS stays the normal one and is not read from this run. Like the normal base rate, this one reads no
standard error of the scored row and does not model measurement error: `y` already contains it.

The run is one ablation of the headline archive, `moot backtest --source upworthy --bootstrap 500 --base-density t`, on the ledger,
origins, rows and seed of run 8. Its report is `ablations/backtest-upworthy-<snapshot>--base-density-t.json`.

## Decisions fixed now

1. **Primary reading.** P1 minus the heavy-tailed base rate on the pooled log score, with the report's 90 percent bootstrap interval by
   test, unadjusted (`tables.aggregate[cell=ALL,rung=P0].logscore_vs_p1`, negated).
2. **Words.** "The prior beats a heavy-tailed base rate" needs that interval to lie wholly above zero. An interval that contains zero is
   "not shown". An interval wholly below zero is "the heavy-tailed base rate beats the prior".
3. **What each outcome means for the paper.**
   - Above zero: the prior's use of history (pooling across cells and periods, and the planned standard error of the row) adds to the
     distribution forecast beyond the shape of the density. The paper reports the size next to the 0.120 and the 0.045.
   - Contains zero or below it: the paper says the prior is not shown to beat a base rate of the same family on the log score, and the
     headline becomes a statement about the density family. The first hypothesis's first part, written against the normal base rate, keeps
     its verdict as written, and the paper says the verdict does not carry over to a heavy-tailed base rate.
4. **What it does not show either way.** It is one archive, pooled over seven origins. The heavy-tailed base rate is fitted without
   measurement error, so its tails absorb both the spread of effects and the noise of small tests; it is a harder baseline than the
   normal one and not a model of the effects.
5. **No change to the method follows from the result.** P0 in the main run, the card and the package's default stay the normal base
   rate, which is what the Brier skill and every other table are measured against. A surprising number is reported as it is.

## Code state and run

- Code: `src/mootcourt/predictors/p0.py` (the density), `src/mootcourt/harness.py` and `src/mootcourt/cli.py` (the setting), with tests.
  The default path must give the same numbers as before: a test compares the log scores of the default with the normal formula.
- The setting joins the ablation list of the headline archive in `scripts/run_ablations.sh`.
- The run is made at a later commit than run 8 (5e4fedf). The run folder's README and the paper's Versions list name that commit.
- A table row comes from the report through `paper/summary_tables/`, not typed.

## Notes added after the run (12 November 2026)

- The code gives a cell with fewer than five visible rows the normal density (`_MIN_ROWS_T` in `p0.py`). This rule was in the committed code before the run and is missing from the list above. Every scored cell and origin of run 8 has far more visible rows, so it did not act.
- A review of the result pointed out that the gain against the heavy-tailed base rate is not separated from the traffic stand-in: the prior reads the row's standard error and the base rate does not. The paper says so and prints no number for the part that would survive a fixed exposure, since no run combines the two settings.

## A second run: the same comparison with exposure fixed (written 12 November 2026, before its result exists)

Why. The prior reads each row's standard error, which the archive supplies from realized traffic, and the base rate reads none. Two
reviewers of the first result asked how much of the 0.020 nats survives when that stand-in is removed. The existing ablation
`--exposure cell-median` gives every row of a cell the cell's median exposure. No run combines it with the Student-t base rate, so the
paper could only set two pooled means side by side.

What was seen before this was written. From two separate reports, P1's pooled log score with exposure fixed is minus 0.7676 and the
Student-t base rate's is minus 0.7761, a difference of about 0.009 with no interval. Nothing from a run with both settings has been seen.

What is added. One more ablation of the headline archive, with both settings and nothing else changed:
`moot backtest --source upworthy --bootstrap 500 --base-density t --exposure cell-median`. No code changes; the setting joins the list in
`scripts/run_ablations.sh`.

Decisions fixed now.

1. Primary reading: P1 minus the Student-t base rate on the pooled log score with exposure fixed, with the report's unadjusted 90 percent
   interval by test.
2. Words: above zero wholly, "the prior's lead over a heavy-tailed base rate survives a fixed exposure"; containing zero, "not shown to
   survive"; below zero wholly, "the heavy-tailed base rate is ahead once exposure is fixed".
3. Either way the paper prints the number beside the 0.020 and replaces the sentence that says no run combines the two settings.
4. It does not show what a true planned exposure would give: fixing exposure at the cell median removes all variation in the row's
   standard error within a cell, which is more than removing the realized part of it.
