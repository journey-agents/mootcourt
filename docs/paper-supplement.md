# Paper supplement: four parts that left the paper

On 21 November 2026 four appendix parts left the paper, at the author's decision after two reviews, because no claim of the
paper rests on them. Their text is kept here so that nothing is lost. The parts are the timed run with latency and scale, the
tooling landscape, the detail of the weekly replay, and the check of the mechanics on a second archive.

Every figure on this page comes from run 9, the main run of the paper. Its reports are in `paper/data/run9-visible-exposure/`,
written `RUN/` below. A table file named here is written by `make tables` into `paper/tables/`. This page prints few numbers:
it names the table file and the report key that hold each one. Nothing here is a finding of the paper.

## Wall time, latency and scale

### The timed run

The table `paper/tables/walltime.tex` lists the stages of one timed run, with the seconds each took on the wall clock. It is
built from `RUN/run-log.json` (keys `stages[].stage`, `stages[].seconds`, `main_pipeline_seconds`, `total_seconds`).

- The wall times come from an earlier run (run 7) and were not repeated on the main analysis. They time the pipeline as it was
  before the date rule and before exposure was fixed.
- That pipeline scored 13,247 rows of the headline archive (`RUN/include-randomization-window/backtest-upworthy-20261114-4bfb354b87e3.json`,
  `header.scored_rows`). The main analysis scores 10,697 (`RUN/backtest-upworthy-20261106-2dc461f52ea4.json`, `header.scored_rows`).
- The power stage is the gate simulation by test at three base rates, with dependence within a test. The stage of the boosted
  model runs from a folder of its own.
- The machine ran other jobs the whole time, so each wall time is an upper bound and not a quiet timing. The run log records
  the load, the environment and a digest of the files that ran.
- In the data stage the three archive files were copied from a local store already in place and their checksums were checked.
  Nothing was downloaded.
- The command is `scripts/timed_run.sh`.

### The stages of the main run

The full driver (`scripts/run_experiments.sh`) covers the main analysis, the ablations and the experiments. It worked through
83 stages, and a second script (`scripts/run_run9_extras.sh`) added 24. The stage lines are in `RUN/stages.txt` and
`RUN/stages-additions.txt`. Every exit code was zero but one: the leakage audit of the headline archive failed inside the run.
The paper's appendix on code states, seeds and snapshots says why it failed and how it was rerun.

### Card latency

The report is `RUN/card-latency.json`, written by `python3 scripts/card_latency.py --source upworthy --json-out card-latency.json`.

- One card was timed 30 times in process, for a headline test at 20,000 impressions per arm, with the bundle already loaded
  (`impressions`, `in_process_ms.n`).
- The median is 18 milliseconds (`in_process_ms.p50`). With the precedent weight forced to one half it is 32 milliseconds
  (`in_process_lambda_0.5_ms.p50`).
- In a fresh process the median of three runs is 1,455 milliseconds (`cli_fresh_process_ms.p50`, `cli_fresh_process_ms.n`).

### Scale

The reports are `RUN/scale/scale-100000.json` and `RUN/scale/scale-1000000.json`, written by `moot benchmark --scale N`. The
page [Scale](scale.md) describes the benchmark.

- Fitting a synthetic ledger of one million contrasts took 22 minutes and 5.0 GiB of memory (`stages.fit.seconds`,
  `peak_rss_gb`).
- Beside the run on a tenth of the rows, the time grows a little faster than the rows and the memory grows more slowly.
- The scale measurements come from an earlier configuration (`RUN/scale/README.md`). They were taken before the rule on which
  quarter's level the prior adds, a rule that changes no backtest figure, and before the date rule, which leaves a synthetic
  ledger alone.

### How the cell columns were found

One early rerun left the challengers unable to see the cell, while the ladder fits each cell on its own. On the synthetic
archive, where the cell means sit three points apart, the recalibrated challengers reached a Brier skill of about minus 0.10.
That number belongs to the method notes (`docs/method.md`) and appears in no report of run 9. The boosted model and the text
classifier now each receive one indicator column per cell, and every stage that scores a challenger was rerun. The columns did
not remove the deficit: on the synthetic archive the recalibrated boosted model stays below the base rate, with an interval
below zero (`RUN/backtest-synthetic-20261103-bf4fd286e2b2.json`, `tables.aggregate[cell=ALL,rung=GBM+cal].brier_skill` and its
bounds; table file `paper/tables/main-synthetic.tex`).

## Tooling landscape

The survey is the page [Landscape](landscape.md). Each entry was checked against the tool's own public pages. It spans
thirteen commercial experimentation platforms, seventeen open-source projects, sixteen internal platforms set out in public
papers, and the wave of simulation and language-model tools from 2023 to 2026.

No product found by the survey does all four of these things: it puts out a pre-launch outcome distribution or win probability
for a proposed experiment, it abstains, it scores its own forecasts against how real tests turned out, live or concluded, and
it backtests over an archive. What exists is the parts: power calculators that draw on historical variance, priors typed in by
hand, experiment knowledge bases, one learned prior across a platform, ranking scores trained on archives of ideas and
creatives, the three screening systems of 2026 that the paper's related work cites, and simulation agents validated only
through directional backtests over a few dozen tests.

The table below condenses the gap table of the survey (section 6 of the landscape page). It leaves out the column for a
backtest over an archive, which the full table carries. Y is yes, P is partial and N is no. An entry records that a capability
exists, as documented or, for this work, as built. It does not record that anyone has shown the capability to work. The
screening row holds the three systems of 2026.

| | outcome distribution before launch | calibrated win probability | abstention | precedent retrieval | forecasts scored against real tests | learned prior from the organization's archive | experiment memory | open source |
|---|---|---|---|---|---|---|---|---|
| Commercial platforms (13) | N | N | N | P | N | P | P | N |
| Open-source platforms and libraries | N | N | N | P | N | P | P | Y |
| Internal platforms (public papers) | N | N | N | P | P | P | Y | N |
| Screening systems before launch (2026) | N | N | N | P | P | Y | P | N |
| Simulation and language-model agents | P | N | P | N | P | N | N | P |
| Archive priors (research) | N | N | N | N | N | Y | N | N |
| This work | Y | P | Y | Y | Y | Y | Y | Y |

## Weekly replay detail

The paper keeps the weekly replay of the headline archive in its section on drift, with the table
`paper/tables/replay-upworthy.tex`. The report is `RUN/replay-upworthy-20261106-2dc461f52ea4.json`, written by
`python3 scripts/replay_weekly.py --source upworthy`. The replay shows that the loop runs end to end. It gives no evidence on
forecast skill. The detail below left the paper.

- The drift rule marks only the smallest cell, the one that changed both headline and image (`drift_onsets`, `weeks[].flagged`).
- It marks the two weeks that start on 31 March 2014 and the four weeks from 20 April 2015 to the end of the archive
  (`totals.n_flagged_weeks`).
- Rolling coverage at 90 percent is measured against the card's interval around the observed estimate. Its lowest value is
  0.625, in the week of 26 August 2013 (`weeks[week_start=2013-08-26].coverage_90`, `coverage_90_n`). That week is the last one
  before the gap left by the date rule, and its rolling window holds eight joined outcomes.
- The next lowest value is 0.78, on 17 February 2014, on 198 joined outcomes. The highest is 0.96, on 13 October 2014.
- The novelty trigger abstains on 1,526 cards, the reliability trigger on 271 and the support trigger on 280. The instability
  trigger abstains on none (`totals.abstained_by_trigger`). A card counts under every trigger that fired on it.
- The reliability trigger fires when the report of a cell is missing or stale, or when the cell is marked drifted
  (`src/mootcourt/abstain.py`, `reliability_reason`; `header.rule.reliability_max_age_days`). In the replay that happens in the
  first two weeks, in the three weeks of January 2014 that follow the gap left by the date rule, and on a few cards in the
  flagged weeks (`weeks[].abstained_by_trigger.reliability`).

## A check of the mechanics on a second archive

The paper keeps a short summary of this check in its appendix, with the table `paper/tables/fmt-asos.tex`, because the sixth
hypothesis of the plan is read on it. The full account follows.

### What the archive is and what the check shows

The second archive is the ASOS Digital Experiments Dataset, the product experiments of an online fashion retailer. The pipeline
runs on it unchanged: the command is that of the headline archive with the source changed (`moot backtest --source asos`). The
reports are `RUN/backtest-asos-20261103-6bb5a15c5ff0.json` and `RUN/paper-extras-asos-20261103-6bb5a15c5ff0.json`. The pooled
table is `paper/tables/main-asos.tex` and the decision value is in `paper/tables/decision-intervals-asos.tex`. Neither is
printed in the paper.

- The archive holds 78 experiments and scores 68 (`header.tests_in_ledger`, `header.tests_scored`). That is too few to decide
  any claim. The check shows only that the mechanics run on other data.
- The metric serves as the cell. A gate is the number of tests that a stratum, a cell or the pooled archive, needs before a
  claim about skill there can be decided. No cell reaches its gate, and neither does the pooled archive. The smallest gate asks
  for 175 tests at a skill of 0.20 (`gates_by_stratum.strata.ALL.own_gate.n_200`).
- The count of tests alone settles that outcome. The archive gives no basis for judging whether the findings on the headline
  archive carry over to product experiments.
- The archive has no dates, so its calendar is nominal: the loader lays the tests out on it in an arbitrary order. The figures
  by year and the weekly replay therefore show no more than that the loop runs. They say nothing about when these experiments
  drifted, or whether they drifted.

### Abstention

The abstention rate is high mostly because of the support trigger, which withholds a card when its cell holds fewer than 30
visible rows. The trigger fires at each of the first three origins and at no later origin, and it accounts for most of the
abstained rows (`tables.abstention[cell=ALL]`, `tables.origins`).

With one trigger switched off at a time (the reports `RUN/ablations/backtest-asos-20261103-6bb5a15c5ff0--drop-trigger-*.json`,
key `tables.released_rows[cell=ALL]`):

- The support trigger withholds the most: switched off, it releases 81 rows in 19 tests.
- The novelty trigger releases 25 rows in 2 tests. The reliability trigger releases 11 rows in 8 tests. The instability trigger
  releases none.
- The rows that the support trigger releases reach 5.25 on the log score, against 4.67 for the issued rows. A higher score is
  better here.
- For direction the released rows score 0.63, and the interval around that value contains the 0.52 of the issued rows. The
  interval for their Brier skill spans zero.
- The two sets hold different tests, so these gaps do not show that the trigger withheld forecasts that were better or worse.
  At 19 tests the threshold of 30 rows remains a convention, and the archive is too small to check it.

### The prior

The figures for the prior are descriptive, because the tests are too few to treat them as a finding (table file
`paper/tables/fmt-asos.tex`; key `tables.aggregate[cell=ALL,rung=P1]`).

- Before adjustment the interval of the prior's Brier skill sits below zero. After adjustment for the 55 intervals of the
  pooled table it spans zero.
- The expected calibration error of the prior lies beyond the rejection line of the clustered null (`ece_percentile`). That of
  the base rate does not. This is the one calibration figure that sets the two apart here.
- The coverage of the 80 and 90 percent intervals falls slightly short of the nominal levels, but the bootstrap interval
  around each coverage figure includes the nominal level, so no shortfall in coverage is shown.
- On average the prior forecasts a significant positive result at a rate above the realized rate (`p_sig_mean`, `event_rate`).
  The base rate does the same, so the gap is not peculiar to the prior.
- As on the headline archive, a normal prior gives up log score and Brier skill, and the pooling strength shifts the score by
  less than 0.03 nats (the reports `--prior-normal`, `--kappa-0.0` and `--kappa-80.0` under `RUN/ablations/`).

### The precedent rung and the challengers

- P2 equals P1 on every row, because the guard gives precedents no weight in any cell at any origin
  (`tables.p2_selection_by_cell`, `share_lambda_zero`).
- The feature space does not force that. On this archive the features are the metric and the number of variants only. With the
  guard off, precedents get a weight in 13 of the 28 pairs of origin and cell (`RUN/ablations/p2-guard-asos.json`,
  `unguarded.share_lambda_zero`).
- Without the guard the rung gains 0.008 nats, on an interval that spans zero (`difference.logscore`).
- Two challengers run here, the boosted model and the local comparison set. The text classifier needs headlines, and this
  archive has none.
- In raw form the Brier skill of each challenger falls far below zero. The intervals lie below zero before adjustment and span
  zero after it. Once the challengers are recalibrated, both intervals span zero. None of this is treated as a finding.
- Against random order the lift that the challengers capture spans zero. Against the order matched on arms it is exactly zero:
  at every origin all tests with the same number of contrasts get the same score, so within those groups a random order
  captures just what the model captures (`tables.decision_value`, `diff_random`, `diff_matched`).

### Exposure and the learning curve

- The stand-in for exposure is the count of users at the final checkpoint. Its correlation with the absolute standardized
  effect is stronger than on the headline archive (`impressions_effect_correlation`). A second correlation uses the run length,
  which no feature reads. These are associations and not effects on a score. Exposure is fixed in the main run on the headline
  archive only, and the rows of this archive keep their own user counts.
- The learning curve is scored on 9 held-out tests (`RUN/learning-curve-asos-20261103-6bb5a15c5ff0.json`,
  `rows[rung=P1,fraction=0.05].n_scored_tests`). At the smallest fraction a fit was impossible for 17 of the 20 subsamples. The
  intervals it prints sit below zero and run wide, and with so few tests neither is treated as a finding.

### The comparison table

The paper once printed a table that set this archive beside the headline archive, one figure per row. The function `app_asos`
in `paper/summary_tables/appendix.py` still builds it, but it is no longer in the list of tables that the build writes. Its
rows read the two main backtests, the guard reports `p2-guard-asos.json` and `p2-guard-upworthy.json`, the reports with one
trigger off, the reports on the prior, the extras, the replays and the two learning curves, all under `RUN/`.
