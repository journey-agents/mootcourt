# A base rate with the prior's recency, and the headline by origin: design and decisions

Written 12 November 2026, before the results it describes exist.

## Why

A panel of reviewers read the paper paragraph by paragraph on 12 November 2026. Two of its points need new numbers.

1. **Recency.** The prior (P1) moves each cell's parameters half way toward the level of the last complete quarter. The base rate (P0)
   pools every visible row and has no such term. Every Brier skill in the paper is measured against P0's probability, so a skill above
   zero can come from recency alone. The paper already shows the base rate standing above a falling event rate. No run gives the base
   rate the same period rule.
2. **Origins.** The prior's lead over the Student-t base rate (0.020 nats, and 0.009 with exposure fixed) carries an interval that
   resamples tests and holds the seven origins fixed. The lead is not present at every origin, and one origin holds most of the rows.
   No report gives a paired interval at each origin or the pooled lead with one origin left out.

## What was seen before this was written

- The main run and its ablations, as the paper reports them. In particular the mean log scores by origin of the two Student-t ablations:
  the prior leads on the mean at 4 of 7 origins, and at 5 of 7 with exposure fixed. A reviewer added up those rounded means and
  judged that the July 2014 origin supplies most of both pooled leads.
- The paper's own tables that show the base rate above the realized event rate late in the archive.
- Nothing from a base rate with a period term has been computed or seen. No paired interval by origin for either Student-t comparison
  and no leave-one-origin-out figure has been computed or seen.

## Part A: a base rate with a period term

### What is added

One setting of the backtest, `--base-recency` (default `none`, which changes nothing), with two rules.

- `quarter` (the primary rule, the mirror of the prior's). The prior's cell parameter in a period is the cell's value plus half the
  deviation of the last complete quarter's level from the global level, where the quarter's level is fitted over all cells and a quarter
  needs at least 30 rows to count. The base rate's probability of the event becomes: the cell's visible share, plus half of (the share
  over all visible rows of the last complete quarter with at least 30 visible rows, minus the share over all visible rows), clipped to
  the unit interval. With no such quarter the probability is unchanged. A quarter is complete under the prior's own test (its last day
  is on or before the origin's day).
- `cell-quarter` (the secondary rule, the one a reviewer worded). The base rate's probability is the cell's own share in the last
  complete quarter that holds at least 30 visible rows of that cell. With no such quarter it is the cell's visible share, as now.

The same rule is applied to the base probability of the event at planned precision, which the harness computes separately. Nothing else
about the base rate changes: its density for the log score, its intervals and its direction probability stay as they are. So the log
score of every rung is unchanged, and the Brier score of every rung other than the base rate is unchanged. Only the Brier skill, which
is measured against the base rate, moves. The reports must show the first two as equalities.

Three ablations of the headline archive, each on the ledger, origins, rows and seed of run 8, each with 500 resamples:

1. `--base-recency quarter`
2. `--base-recency quarter --exposure cell-median`
3. `--base-recency cell-quarter`

### Decisions fixed now

1. **Primary reading.** P1's pooled Brier skill against the base rate with the `quarter` rule, on the event as defined in the main run
   (significant at the realized standard error), with the report's 90 percent interval by test. Secondary, in the same report: the same
   skill on the event at planned precision. Secondary, from run 2: both with exposure fixed. Run 3 is a robustness check of the rule.
2. **Words.** An interval wholly above zero: "the skill survives a base rate with the same recency". An interval containing zero: "not
   shown to survive". An interval wholly below zero: "the base rate with recency beats the prior on this event".
3. **What each outcome means for the paper.** The paper prints the skills of all three runs beside the main run's in one table. Each
   place that reads a Brier skill above zero (the event at planned precision, exposure fixed, the last year) gains one clause that says
   whether it survives. If the base rate with recency has a lower Brier score than the plain base rate, the paper says the plain base
   rate was a weak opponent on this event. If it has a higher one, the paper says recency does not help the base rate and the
   asymmetry did not favour the prior.
4. **What it does not show.** It is one archive. The rule is one of many ways to give a frequency a recency term; the two rules bracket
   a mild and a strong version. The prior also shrinks the quarter's level by its row count, and the base rate's rule does not.
5. **No change to the method follows.** P0 in the main run, the card and the package's default stay as they are. A surprising number
   is reported as it is.

## Part B: the two Student-t comparisons by origin

### What is added

No model is run. A script reads the saved scores of the two existing ablations (`--base-density t`, and the same with
`--exposure cell-median`) and writes one report per ablation with, for the log score of P1 minus P0 per row:

- the pooled difference and its interval by test (which must reproduce the ablation report's);
- the difference at each origin with a 90 percent interval that resamples the tests of that origin;
- the pooled difference with each origin left out in turn, each with its interval by test;
- the mean over the seven origins weighted equally, with an interval that resamples tests within each origin.

Seed and resample count are the ablation report's (0 and 500).

### Decisions fixed now

1. **Primary reading.** The leave-one-origin-out figures: "the lead does not rest on one origin" needs all seven intervals wholly above
   zero. If any contains zero or lies below it, the paper names the origin and says the pooled lead rests on it.
2. **Secondary.** The count of origins whose own interval lies above zero, the count below zero, and the equal-weighted mean with its
   interval. The paper prints the by-origin table in the appendix and reads it in one or two sentences beside the pooled figure.
3. **Either way** the sentence that says the pooled interval holds the origins fixed stays, because these intervals still do not
   resample origins: seven origins are too few for that.
4. Nothing in the method changes because of the result.

## Code state and run

- Part A code: `src/mootcourt/predictors/p0.py` (the rule), `src/mootcourt/harness.py` (the planned event's base, the setting),
  `src/mootcourt/cli.py` (the option), tests in `tests/test_p0.py`. The default path must give the same numbers as before. The three
  settings join `scripts/run_ablations.sh`.
- Part B code: `scripts/by_origin_difference.py`, with a test on a small frame.
- Both are committed before anything runs. The run folder's README names the commit, and the paper's Versions list does too.
- Tables come from the reports through `paper/summary_tables/`.
