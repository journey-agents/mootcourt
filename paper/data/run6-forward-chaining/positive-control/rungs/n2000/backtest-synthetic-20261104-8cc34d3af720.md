# Backtest report: synthetic

**Synthetic data.** Every number below comes from simulated tests with known truth. It shows the method works, not what any real archive says.

> The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.

## Header

- Source: synthetic
- Ledger snapshot: 20261104-8cc34d3af720
- Model: 5cb5a874bbab
- Feature hash: 098b16a276fd
- Command: `moot backtest --source synthetic --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr --seed 0`
- Seed: 0, bootstrap resamples: 500
- Gate sizes from the power simulation at the release gate (power 0.90): n_200 = 175 (skill 0.20), n_400 = 250 (skill 0.10)
- At power 0.80: n_200 = 125 (skill 0.20), n_400 = 200 (skill 0.10) (research screen)
- At power 0.90: n_200 = 175 (skill 0.20), n_400 = 250 (skill 0.10) (release gate)
- Rungs: GBM, GBM+cal, P0, P1, P2, always_reference, always_variant, local_eb, local_eb+cal, text_lr, text_lr+cal; primary rung for decisions and plots: P2
- Origins scored: 8 from 2013-04-01T00:00:00+00:00 to 2015-01-01T00:00:00+00:00
- Origins with fewer than 20 visible rows (nothing fitted): 2013-01-01T00:00:00+00:00
- Ledger rows: 4000, admitted: 4000, scored: 3576, admitted but never scored (before the first fit): 424
- Tests: 2000 in the ledger, 2000 admitted, 1788 scored. Tests in the ledger are the distinct test ids of every row of the source whatever its status. Tests admitted are the distinct test ids with at least one admitted contrast. Tests scored are the admitted tests with at least one contrast scored by the primary rung. The difference between admitted and scored is the contrasts of the first quarters, before the first origin with enough visible rows to fit (they are history only), plus any test whose contrasts all fall there.
- P2 admission guard: 2.0
- Gate sizes by base rate (tests): 0.09: n_200 175, n_400 250; 0.14: n_200 200, n_400 400; 0.30: n_200 75, n_400 150

## How to read the scores

Scores are computed against the observed estimate with known standard error, not against the unknown true effect. This is the only option when no ground truth exists: the true effect of a past test is never observed, so a predictor can only be asked about the estimate the test produced.

Burn-in: the first scored origin has no earlier origin to build a reliability report from, so every row there abstains for 'reliability report is missing'. Abstention-adjusted figures for that origin are not comparable with later origins.

Intervals are 90 percent bootstrap intervals that resample whole tests. Scores are given on all predicted rows (so rungs are comparable) and, separately, on rows where the card would not have abstained.

P0 is the empirical base-rate forecaster: its significant-positive probability is the visible event rate of its cell, the same quantity the Brier skill is measured against, so its Brier skill is zero by construction and its calibration is a real out-of-time check of the base rate. A rung's Brier skill is always against that cell base rate, never against another rung.

Three interval conventions are used. Every score interval is a 90 percent percentile bootstrap that resamples whole tests. The ECE percentile is read in a perfect-calibration null whose outcomes are drawn by test (contrasts of one test move together, with the within-test correlation estimated from the rows); 500 draws resolve percentiles up to 99.8, so 100 means above every draw. The gate simulation bootstraps by test and uses a 90 percent interval. Columns named adjusted_lo and adjusted_hi, and those ending in _adjusted_lo and _adjusted_hi, are Bonferroni-adjusted bounds for the family of intervals the table shows (the bootstrap standard error times the Bonferroni normal quantile); the per-cell and per-year intervals are descriptive.

design_effect is the variance of the total residual with whole tests as the units over its independent-rows value; icc is the within-test correlation of the standardized residuals it implies and drives the clustered null. ece_percentile_independent is the percentile in the earlier null that draws every row independently, kept for comparison.

Rungs:

- GBM: gradient-boosted challenger on the same features, precision weighted with a time-ordered search, spread from out-of-fold residuals
- GBM+cal: the GBM's p_sig through a Platt map fit on out-of-fold predictions of the visible rows only; probabilities only
- P0: empirical base-rate forecaster of the visible ledger per cell: p_sig is the visible event rate, so its Brier skill is zero by construction
- P1: empirical-Bayes prior per cell, pooled over kind of change and period
- P2: weighted precedents (kernel regression on headline features) shrunk toward P1
- always_reference: direction baseline: the reference arm wins (creation-order effect); direction accuracy only
- always_variant: direction baseline: the variant wins; direction accuracy only
- local_eb: challenger: empirical-Bayes prior fit on the k nearest visible rows in feature space, no shrinkage to the cell prior
- local_eb+cal: local_eb's p_sig through a Platt map fit on out-of-fold predictions of the visible rows only; probabilities only
- text_lr: challenger: TF-IDF and logistic regression on the headline text (the difference of the two headlines where present), probabilities used directly (no density)
- text_lr+cal: text_lr's p_sig through a Platt map fit on out-of-fold predictions of the visible rows only; probabilities only

## Scores by cell and rung

### Rows, tests, gates and abstention (the headline decidability is by tests; the by-row columns are beside it)

| cell | rung | kind | n | n_tests | n_nonabstained | abstention_rate | gate_base_rate | decidable_by_tests | decidable_by_tests_base_0.3 | decidable_research_by_tests | decidable | decidable_research |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | challenger | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | GBM+cal | challenger | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P0 | ladder | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P1 | ladder | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P2 | ladder | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | always_reference | baseline | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | always_variant | baseline | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb | challenger | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb+cal | challenger | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr | challenger | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr+cal | challenger | 3576 | 1788 | 2752 | 0.2304 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | GBM | challenger | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | GBM+cal | challenger | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P0 | ladder | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P1 | ladder | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P2 | ladder | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | always_reference | baseline | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | always_variant | baseline | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | local_eb | challenger | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | local_eb+cal | challenger | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | text_lr | challenger | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | text_lr+cal | challenger | 1216 | 608 | 939 | 0.2278 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM | challenger | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM+cal | challenger | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P0 | ladder | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P1 | ladder | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P2 | ladder | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | always_reference | baseline | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | always_variant | baseline | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb | challenger | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb+cal | challenger | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr | challenger | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr+cal | challenger | 1216 | 608 | 943 | 0.2245 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | GBM | challenger | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | GBM+cal | challenger | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P0 | ladder | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P1 | ladder | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P2 | ladder | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | always_reference | baseline | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | always_variant | baseline | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb | challenger | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb+cal | challenger | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr | challenger | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr+cal | challenger | 1144 | 572 | 870 | 0.2395 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |

### Log score and CRPS, all predicted rows (higher log score is better, lower CRPS is better)

| cell | rung | logscore | logscore_lo | logscore_hi | crps | crps_lo | crps_hi |
|---|---|---|---|---|---|---|---|
| ALL | GBM | -2.4519 | -2.4721 | -2.4303 | 1.5769 | 1.5436 | 1.6097 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | -2.4352 | -2.4557 | -2.4133 | 1.5708 | 1.5363 | 1.6015 |
| ALL | P1 | -2.4268 | -2.4457 | -2.4048 | 1.5687 | 1.5350 | 1.5999 |
| ALL | P2 | -2.4268 | -2.4458 | -2.4048 | 1.5687 | 1.5357 | 1.5999 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | -2.4403 | -2.4601 | -2.4164 | 1.5760 | 1.5409 | 1.6064 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | -2.4072 | -2.4419 | -2.3768 | 1.5074 | 1.4556 | 1.5605 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | -2.4096 | -2.4486 | -2.3763 | 1.5105 | 1.4608 | 1.5664 |
| both | P1 | -2.4079 | -2.4460 | -2.3742 | 1.5104 | 1.4601 | 1.5668 |
| both | P2 | -2.4080 | -2.4463 | -2.3746 | 1.5107 | 1.4606 | 1.5675 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | -2.4204 | -2.4592 | -2.3860 | 1.5145 | 1.4623 | 1.5704 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | -2.6547 | -2.7016 | -2.6100 | 1.8979 | 1.8308 | 1.9691 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | -2.6380 | -2.6690 | -2.6056 | 1.9098 | 1.8453 | 1.9743 |
| headline_only | P1 | -2.6348 | -2.6678 | -2.6023 | 1.9041 | 1.8406 | 1.9684 |
| headline_only | P2 | -2.6348 | -2.6678 | -2.6023 | 1.9041 | 1.8406 | 1.9684 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | -2.6529 | -2.6862 | -2.6204 | 1.9239 | 1.8619 | 1.9863 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | -2.2837 | -2.3104 | -2.2584 | 1.3097 | 1.2641 | 1.3576 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | -2.2468 | -2.2921 | -2.2015 | 1.2744 | 1.2186 | 1.3277 |
| image_only | P1 | -2.2258 | -2.2669 | -2.1860 | 1.2741 | 1.2209 | 1.3262 |
| image_only | P2 | -2.2257 | -2.2668 | -2.1860 | 1.2739 | 1.2207 | 1.3264 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | -2.2356 | -2.2767 | -2.1949 | 1.2715 | 1.2190 | 1.3240 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |

### Brier score of p_sig against the significant-positive event, with skill against the base rate

| cell | rung | brier | brier_lo | brier_hi | brier_base | brier_skill | brier_skill_lo | brier_skill_hi | brier_floor |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.1392 | 0.1334 | 0.1449 | 0.1423 | 0.0217 | 0.0058 | 0.0359 | 0.0688 |
| ALL | GBM+cal | 0.1386 | 0.1326 | 0.1446 | 0.1423 | 0.0260 | 0.0073 | 0.0426 | 0.0688 |
| ALL | P0 | 0.1423 | 0.1362 | 0.1478 | 0.1423 | 0.0000 | 0.0000 | 0.0000 | 0.0688 |
| ALL | P1 | 0.1389 | 0.1330 | 0.1448 | 0.1423 | 0.0239 | 0.0145 | 0.0332 | 0.0688 |
| ALL | P2 | 0.1389 | 0.1330 | 0.1448 | 0.1423 | 0.0237 | 0.0145 | 0.0332 | 0.0688 |
| ALL | always_reference | n/a | n/a | n/a | 0.1423 | n/a | n/a | n/a | 0.0688 |
| ALL | always_variant | n/a | n/a | n/a | 0.1423 | n/a | n/a | n/a | 0.0688 |
| ALL | local_eb | 0.1398 | 0.1339 | 0.1458 | 0.1423 | 0.0174 | 0.0055 | 0.0303 | 0.0688 |
| ALL | local_eb+cal | 0.1393 | 0.1334 | 0.1452 | 0.1423 | 0.0204 | 0.0095 | 0.0324 | 0.0688 |
| ALL | text_lr | 0.1442 | 0.1378 | 0.1503 | 0.1423 | -0.0137 | -0.0273 | 0.0009 | 0.0688 |
| ALL | text_lr+cal | 0.1434 | 0.1371 | 0.1493 | 0.1423 | -0.0079 | -0.0205 | 0.0045 | 0.0688 |
| both | GBM | 0.1433 | 0.1333 | 0.1540 | 0.1472 | 0.0265 | 0.0080 | 0.0455 | 0.0821 |
| both | GBM+cal | 0.1430 | 0.1326 | 0.1544 | 0.1472 | 0.0291 | 0.0069 | 0.0522 | 0.0821 |
| both | P0 | 0.1472 | 0.1370 | 0.1588 | 0.1472 | 0.0000 | 0.0000 | 0.0000 | 0.0821 |
| both | P1 | 0.1430 | 0.1324 | 0.1550 | 0.1472 | 0.0291 | 0.0155 | 0.0425 | 0.0821 |
| both | P2 | 0.1430 | 0.1324 | 0.1551 | 0.1472 | 0.0286 | 0.0146 | 0.0420 | 0.0821 |
| both | always_reference | n/a | n/a | n/a | 0.1472 | n/a | n/a | n/a | 0.0821 |
| both | always_variant | n/a | n/a | n/a | 0.1472 | n/a | n/a | n/a | 0.0821 |
| both | local_eb | 0.1443 | 0.1334 | 0.1564 | 0.1472 | 0.0203 | 0.0025 | 0.0382 | 0.0821 |
| both | local_eb+cal | 0.1440 | 0.1332 | 0.1560 | 0.1472 | 0.0221 | 0.0047 | 0.0388 | 0.0821 |
| both | text_lr | 0.1481 | 0.1374 | 0.1592 | 0.1472 | -0.0056 | -0.0237 | 0.0133 | 0.0821 |
| both | text_lr+cal | 0.1477 | 0.1374 | 0.1585 | 0.1472 | -0.0032 | -0.0194 | 0.0130 | 0.0821 |
| headline_only | GBM | 0.2274 | 0.2196 | 0.2350 | 0.2377 | 0.0435 | 0.0216 | 0.0650 | 0.0963 |
| headline_only | GBM+cal | 0.2285 | 0.2206 | 0.2367 | 0.2377 | 0.0389 | 0.0120 | 0.0639 | 0.0963 |
| headline_only | P0 | 0.2377 | 0.2332 | 0.2424 | 0.2377 | 0.0000 | 0.0000 | 0.0000 | 0.0963 |
| headline_only | P1 | 0.2318 | 0.2255 | 0.2378 | 0.2377 | 0.0251 | 0.0108 | 0.0379 | 0.0963 |
| headline_only | P2 | 0.2318 | 0.2255 | 0.2378 | 0.2377 | 0.0251 | 0.0108 | 0.0379 | 0.0963 |
| headline_only | always_reference | n/a | n/a | n/a | 0.2377 | n/a | n/a | n/a | 0.0963 |
| headline_only | always_variant | n/a | n/a | n/a | 0.2377 | n/a | n/a | n/a | 0.0963 |
| headline_only | local_eb | 0.2331 | 0.2272 | 0.2391 | 0.2377 | 0.0197 | 0.0010 | 0.0357 | 0.0963 |
| headline_only | local_eb+cal | 0.2319 | 0.2256 | 0.2380 | 0.2377 | 0.0247 | 0.0067 | 0.0401 | 0.0963 |
| headline_only | text_lr | 0.2421 | 0.2352 | 0.2495 | 0.2377 | -0.0185 | -0.0393 | -0.0003 | 0.0963 |
| headline_only | text_lr+cal | 0.2396 | 0.2325 | 0.2470 | 0.2377 | -0.0078 | -0.0274 | 0.0096 | 0.0963 |
| image_only | GBM | 0.0409 | 0.0341 | 0.0492 | 0.0354 | -0.1547 | -0.2406 | -0.0939 | 0.0255 |
| image_only | GBM+cal | 0.0383 | 0.0309 | 0.0472 | 0.0354 | -0.0804 | -0.1314 | -0.0442 | 0.0255 |
| image_only | P0 | 0.0354 | 0.0274 | 0.0445 | 0.0354 | 0.0000 | 0.0000 | 0.0000 | 0.0255 |
| image_only | P1 | 0.0357 | 0.0278 | 0.0449 | 0.0354 | -0.0078 | -0.0162 | -0.0001 | 0.0255 |
| image_only | P2 | 0.0357 | 0.0278 | 0.0449 | 0.0354 | -0.0080 | -0.0163 | -0.0002 | 0.0255 |
| image_only | always_reference | n/a | n/a | n/a | 0.0354 | n/a | n/a | n/a | 0.0255 |
| image_only | always_variant | n/a | n/a | n/a | 0.0354 | n/a | n/a | n/a | 0.0255 |
| image_only | local_eb | 0.0359 | 0.0279 | 0.0452 | 0.0354 | -0.0122 | -0.0238 | -0.0018 | 0.0255 |
| image_only | local_eb+cal | 0.0361 | 0.0282 | 0.0454 | 0.0354 | -0.0175 | -0.0311 | -0.0060 | 0.0255 |
| image_only | text_lr | 0.0360 | 0.0280 | 0.0451 | 0.0354 | -0.0149 | -0.0244 | -0.0055 | 0.0255 |
| image_only | text_lr+cal | 0.0365 | 0.0288 | 0.0454 | 0.0354 | -0.0290 | -0.0499 | -0.0124 | 0.0255 |

### Calibration of p_sig against the perfect-calibration null, clustered by test

| cell | rung | ece | ece_percentile | ece_percentile_independent | ece_equal_mass | ece_equal_mass_percentile | design_effect | icc |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.0341 | 100.0000 | 100.0000 | 0.0378 | 100.0000 | 0.9308 | 0.0000 |
| ALL | GBM+cal | 0.0176 | 87.2000 | 84.2000 | 0.0201 | 88.8000 | 1.0066 | 0.0066 |
| ALL | P0 | 0.0137 | 86.2000 | 86.6000 | 0.0166 | 69.4000 | 1.0232 | 0.0232 |
| ALL | P1 | 0.0108 | 44.4000 | 37.4000 | 0.0176 | 76.8000 | 1.0213 | 0.0213 |
| ALL | P2 | 0.0107 | 43.2000 | 36.0000 | 0.0161 | 65.2000 | 1.0223 | 0.0223 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.0158 | 79.8000 | 79.2000 | 0.0202 | 91.0000 | 1.0346 | 0.0346 |
| ALL | local_eb+cal | 0.0142 | 67.4000 | 72.4000 | 0.0148 | 47.6000 | 1.0253 | 0.0253 |
| ALL | text_lr | 0.0268 | 100.0000 | 100.0000 | 0.0328 | 100.0000 | 1.0883 | 0.0883 |
| ALL | text_lr+cal | 0.0298 | 100.0000 | 100.0000 | 0.0290 | 99.8000 | 1.0340 | 0.0340 |
| both | GBM | 0.0263 | 88.2000 | 88.2000 | 0.0304 | 58.0000 | 0.8937 | 0.0000 |
| both | GBM+cal | 0.0184 | 53.2000 | 53.2000 | 0.0267 | 50.2000 | 0.9769 | 0.0000 |
| both | P0 | 0.0053 | 32.6000 | 32.6000 | 0.0182 | 15.4000 | 0.9625 | 0.0000 |
| both | P1 | 0.0174 | 66.2000 | 66.2000 | 0.0305 | 67.6000 | 0.9574 | 0.0000 |
| both | P2 | 0.0169 | 63.2000 | 63.2000 | 0.0305 | 68.8000 | 0.9604 | 0.0000 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.0306 | 97.0000 | 97.0000 | 0.0326 | 77.2000 | 0.9771 | 0.0000 |
| both | local_eb+cal | 0.0287 | 96.2000 | 96.2000 | 0.0206 | 13.6000 | 0.9712 | 0.0000 |
| both | text_lr | 0.0338 | 98.6000 | 99.0000 | 0.0373 | 92.4000 | 1.0660 | 0.0660 |
| both | text_lr+cal | 0.0327 | 98.8000 | 98.6000 | 0.0360 | 89.6000 | 1.0024 | 0.0024 |
| headline_only | GBM | 0.0323 | 83.6000 | 82.4000 | 0.0470 | 94.4000 | 1.1115 | 0.1115 |
| headline_only | GBM+cal | 0.0395 | 93.0000 | 92.8000 | 0.0450 | 90.2000 | 1.1290 | 0.1290 |
| headline_only | P0 | 0.0348 | 98.0000 | 97.2000 | 0.0466 | 96.0000 | 1.0628 | 0.0628 |
| headline_only | P1 | 0.0111 | 10.4000 | 9.2000 | 0.0228 | 6.2000 | 1.0727 | 0.0727 |
| headline_only | P2 | 0.0111 | 10.4000 | 9.2000 | 0.0228 | 6.2000 | 1.0727 | 0.0727 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.0382 | 94.8000 | 93.6000 | 0.0472 | 92.0000 | 1.0812 | 0.0812 |
| headline_only | local_eb+cal | 0.0374 | 94.0000 | 92.8000 | 0.0467 | 90.4000 | 1.0777 | 0.0777 |
| headline_only | text_lr | 0.0650 | 100.0000 | 100.0000 | 0.0818 | 100.0000 | 1.1205 | 0.1205 |
| headline_only | text_lr+cal | 0.0700 | 100.0000 | 100.0000 | 0.0664 | 99.8000 | 1.1127 | 0.1127 |
| image_only | GBM | 0.0632 | 100.0000 | 100.0000 | 0.0632 | 100.0000 | 0.5245 | 0.0000 |
| image_only | GBM+cal | 0.0343 | 100.0000 | 100.0000 | 0.0401 | 100.0000 | 0.6401 | 0.0000 |
| image_only | P0 | 0.0002 | 7.4000 | 8.4000 | 0.0109 | 31.8000 | 1.0109 | 0.0109 |
| image_only | P1 | 0.0035 | 37.4000 | 37.4000 | 0.0163 | 74.4000 | 0.9488 | 0.0000 |
| image_only | P2 | 0.0036 | 38.7000 | 38.7000 | 0.0170 | 79.6000 | 0.9479 | 0.0000 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.0028 | 33.0000 | 33.0000 | 0.0206 | 96.8000 | 0.9624 | 0.0000 |
| image_only | local_eb+cal | 0.0056 | 58.3000 | 58.3000 | 0.0237 | 99.0000 | 0.9116 | 0.0000 |
| image_only | text_lr | 0.0034 | 36.6000 | 36.6000 | 0.0190 | 90.6000 | 0.9707 | 0.0000 |
| image_only | text_lr+cal | 0.0171 | 99.2000 | 99.2000 | 0.0291 | 99.8000 | 0.7544 | 0.0000 |

### Bonferroni-adjusted bounds for the family of intervals of this table (descriptive intervals are the unadjusted ones above)

| cell | rung | family_size | brier_skill | adjusted_lo | adjusted_hi | logscore | logscore_adjusted_lo | logscore_adjusted_hi |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 52 | 0.0217 | -0.0063 | 0.0498 | -2.4519 | -2.4914 | -2.4124 |
| ALL | GBM+cal | 52 | 0.0260 | -0.0068 | 0.0587 | n/a | n/a | n/a |
| ALL | P0 | 52 | 0.0000 | n/a | n/a | -2.4352 | -2.4772 | -2.3932 |
| ALL | P1 | 52 | 0.0239 | 0.0059 | 0.0419 | -2.4268 | -2.4673 | -2.3863 |
| ALL | P2 | 52 | 0.0237 | 0.0058 | 0.0417 | -2.4268 | -2.4674 | -2.3862 |
| ALL | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 52 | 0.0174 | -0.0047 | 0.0394 | -2.4403 | -2.4823 | -2.3984 |
| ALL | local_eb+cal | 52 | 0.0204 | -0.0006 | 0.0415 | n/a | n/a | n/a |
| ALL | text_lr | 52 | -0.0137 | -0.0401 | 0.0127 | n/a | n/a | n/a |
| ALL | text_lr+cal | 52 | -0.0079 | -0.0310 | 0.0153 | n/a | n/a | n/a |
| both | GBM | 52 | 0.0265 | -0.0102 | 0.0633 | -2.4072 | -2.4661 | -2.3484 |
| both | GBM+cal | 52 | 0.0291 | -0.0135 | 0.0717 | n/a | n/a | n/a |
| both | P0 | 52 | 0.0000 | n/a | n/a | -2.4096 | -2.4773 | -2.3418 |
| both | P1 | 52 | 0.0291 | 0.0021 | 0.0560 | -2.4079 | -2.4747 | -2.3410 |
| both | P2 | 52 | 0.0286 | 0.0016 | 0.0556 | -2.4080 | -2.4750 | -2.3409 |
| both | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 52 | 0.0203 | -0.0140 | 0.0546 | -2.4204 | -2.4900 | -2.3509 |
| both | local_eb+cal | 52 | 0.0221 | -0.0100 | 0.0542 | n/a | n/a | n/a |
| both | text_lr | 52 | -0.0056 | -0.0402 | 0.0289 | n/a | n/a | n/a |
| both | text_lr+cal | 52 | -0.0032 | -0.0344 | 0.0281 | n/a | n/a | n/a |
| headline_only | GBM | 52 | 0.0435 | 0.0025 | 0.0845 | -2.6547 | -2.7420 | -2.5675 |
| headline_only | GBM+cal | 52 | 0.0389 | -0.0100 | 0.0878 | n/a | n/a | n/a |
| headline_only | P0 | 52 | 0.0000 | n/a | n/a | -2.6380 | -2.6977 | -2.5784 |
| headline_only | P1 | 52 | 0.0251 | -0.0022 | 0.0525 | -2.6348 | -2.6968 | -2.5728 |
| headline_only | P2 | 52 | 0.0251 | -0.0022 | 0.0525 | -2.6348 | -2.6968 | -2.5728 |
| headline_only | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 52 | 0.0197 | -0.0121 | 0.0515 | -2.6529 | -2.7166 | -2.5892 |
| headline_only | local_eb+cal | 52 | 0.0247 | -0.0063 | 0.0557 | n/a | n/a | n/a |
| headline_only | text_lr | 52 | -0.0185 | -0.0572 | 0.0202 | n/a | n/a | n/a |
| headline_only | text_lr+cal | 52 | -0.0078 | -0.0424 | 0.0268 | n/a | n/a | n/a |
| image_only | GBM | 52 | -0.1547 | -0.2973 | -0.0121 | -2.2837 | -2.3329 | -2.2346 |
| image_only | GBM+cal | 52 | -0.0804 | -0.1625 | 0.0016 | n/a | n/a | n/a |
| image_only | P0 | 52 | 0.0000 | n/a | n/a | -2.2468 | -2.3328 | -2.1607 |
| image_only | P1 | 52 | -0.0078 | -0.0230 | 0.0073 | -2.2258 | -2.3024 | -2.1492 |
| image_only | P2 | 52 | -0.0080 | -0.0232 | 0.0072 | -2.2257 | -2.3023 | -2.1491 |
| image_only | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 52 | -0.0122 | -0.0332 | 0.0089 | -2.2356 | -2.3143 | -2.1568 |
| image_only | local_eb+cal | 52 | -0.0175 | -0.0411 | 0.0062 | n/a | n/a | n/a |
| image_only | text_lr | 52 | -0.0149 | -0.0331 | 0.0033 | n/a | n/a | n/a |
| image_only | text_lr+cal | 52 | -0.0290 | -0.0644 | 0.0064 | n/a | n/a | n/a |

### Discrimination apart from skill: AUC of p_sig for the event and of the direction probability for y > 0, and the Murphy resolution term (equal-mass forecast bins: how far the observed frequency of each bin lies from the event rate; zero for a forecast that does not separate outcomes, however spread it is)

| cell | rung | auc_event | auc_event_lo | auc_event_hi | resolution_event | resolution_event_lo | resolution_event_hi | auc_direction | auc_direction_lo | auc_direction_hi | resolution_direction | resolution_direction_lo | resolution_direction_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.7674 | 0.7511 | 0.7831 | 0.0243 | 0.0213 | 0.0283 | 0.7037 | 0.6895 | 0.7191 | 0.0322 | 0.0282 | 0.0371 |
| ALL | GBM+cal | 0.7667 | 0.7503 | 0.7821 | 0.0236 | 0.0205 | 0.0277 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.7336 | 0.7177 | 0.7498 | 0.0191 | 0.0166 | 0.0226 | 0.6917 | 0.6773 | 0.7065 | 0.0323 | 0.0284 | 0.0372 |
| ALL | P1 | 0.7646 | 0.7475 | 0.7801 | 0.0238 | 0.0208 | 0.0281 | 0.6941 | 0.6794 | 0.7093 | 0.0316 | 0.0278 | 0.0370 |
| ALL | P2 | 0.7644 | 0.7473 | 0.7802 | 0.0237 | 0.0207 | 0.0278 | 0.6943 | 0.6802 | 0.7091 | 0.0315 | 0.0276 | 0.0366 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.7620 | 0.7462 | 0.7784 | 0.0225 | 0.0198 | 0.0265 | 0.7010 | 0.6863 | 0.7159 | 0.0324 | 0.0282 | 0.0376 |
| ALL | local_eb+cal | 0.7626 | 0.7465 | 0.7788 | 0.0226 | 0.0198 | 0.0270 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.7458 | 0.7296 | 0.7635 | 0.0209 | 0.0180 | 0.0249 | 0.6913 | 0.6781 | 0.7072 | 0.0279 | 0.0245 | 0.0332 |
| ALL | text_lr+cal | 0.7453 | 0.7290 | 0.7632 | 0.0209 | 0.0179 | 0.0249 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | 0.6239 | 0.5855 | 0.6588 | 0.0051 | 0.0034 | 0.0091 | 0.5564 | 0.5279 | 0.5819 | 0.0032 | 0.0024 | 0.0085 |
| both | GBM+cal | 0.6239 | 0.5867 | 0.6592 | 0.0054 | 0.0037 | 0.0097 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | 0.4964 | 0.4629 | 0.5308 | 0.0004 | 0.0004 | 0.0022 | 0.5091 | 0.4832 | 0.5345 | 0.0001 | 0.0005 | 0.0028 |
| both | P1 | 0.6131 | 0.5743 | 0.6519 | 0.0048 | 0.0034 | 0.0091 | 0.5017 | 0.4753 | 0.5246 | 0.0016 | 0.0015 | 0.0062 |
| both | P2 | 0.6124 | 0.5739 | 0.6511 | 0.0046 | 0.0033 | 0.0089 | 0.5037 | 0.4768 | 0.5291 | 0.0018 | 0.0016 | 0.0062 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5909 | 0.5543 | 0.6279 | 0.0040 | 0.0029 | 0.0078 | 0.5456 | 0.5156 | 0.5715 | 0.0029 | 0.0023 | 0.0077 |
| both | local_eb+cal | 0.5937 | 0.5572 | 0.6300 | 0.0030 | 0.0022 | 0.0065 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5496 | 0.5163 | 0.5843 | 0.0020 | 0.0014 | 0.0052 | 0.5380 | 0.5118 | 0.5661 | 0.0032 | 0.0021 | 0.0083 |
| both | text_lr+cal | 0.5492 | 0.5164 | 0.5842 | 0.0024 | 0.0017 | 0.0056 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.6197 | 0.5926 | 0.6443 | 0.0126 | 0.0091 | 0.0192 | 0.5547 | 0.5249 | 0.5842 | 0.0034 | 0.0024 | 0.0077 |
| headline_only | GBM+cal | 0.6202 | 0.5927 | 0.6460 | 0.0114 | 0.0083 | 0.0176 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.4842 | 0.4595 | 0.5133 | 0.0020 | 0.0012 | 0.0059 | 0.4993 | 0.4735 | 0.5296 | 0.0007 | 0.0007 | 0.0036 |
| headline_only | P1 | 0.5858 | 0.5564 | 0.6095 | 0.0064 | 0.0046 | 0.0120 | 0.5138 | 0.4859 | 0.5440 | 0.0009 | 0.0011 | 0.0046 |
| headline_only | P2 | 0.5858 | 0.5564 | 0.6095 | 0.0064 | 0.0046 | 0.0120 | 0.5138 | 0.4859 | 0.5440 | 0.0009 | 0.0011 | 0.0046 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5851 | 0.5549 | 0.6089 | 0.0067 | 0.0047 | 0.0124 | 0.5165 | 0.4855 | 0.5464 | 0.0017 | 0.0014 | 0.0055 |
| headline_only | local_eb+cal | 0.5893 | 0.5583 | 0.6136 | 0.0085 | 0.0059 | 0.0149 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5366 | 0.5089 | 0.5610 | 0.0037 | 0.0028 | 0.0082 | 0.5520 | 0.5221 | 0.5802 | 0.0024 | 0.0018 | 0.0064 |
| headline_only | text_lr+cal | 0.5370 | 0.5094 | 0.5610 | 0.0030 | 0.0023 | 0.0076 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.5087 | 0.4367 | 0.5791 | 0.0004 | 0.0003 | 0.0013 | 0.5204 | 0.4864 | 0.5514 | 0.0026 | 0.0019 | 0.0070 |
| image_only | GBM+cal | 0.5020 | 0.4312 | 0.5695 | 0.0003 | 0.0002 | 0.0011 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.4429 | 0.3636 | 0.5185 | 0.0001 | 0.0001 | 0.0007 | 0.4854 | 0.4505 | 0.5156 | 0.0029 | 0.0021 | 0.0070 |
| image_only | P1 | 0.4791 | 0.4068 | 0.5603 | 0.0001 | 0.0001 | 0.0007 | 0.5078 | 0.4719 | 0.5378 | 0.0010 | 0.0010 | 0.0047 |
| image_only | P2 | 0.4760 | 0.4031 | 0.5573 | 0.0001 | 0.0002 | 0.0008 | 0.5079 | 0.4728 | 0.5382 | 0.0013 | 0.0011 | 0.0049 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.4962 | 0.4183 | 0.5696 | 0.0004 | 0.0003 | 0.0011 | 0.5382 | 0.5049 | 0.5666 | 0.0028 | 0.0022 | 0.0071 |
| image_only | local_eb+cal | 0.4768 | 0.4030 | 0.5498 | 0.0003 | 0.0003 | 0.0011 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.4652 | 0.3915 | 0.5386 | 0.0002 | 0.0002 | 0.0009 | 0.5256 | 0.4942 | 0.5552 | 0.0007 | 0.0009 | 0.0042 |
| image_only | text_lr+cal | 0.4508 | 0.3742 | 0.5250 | 0.0006 | 0.0004 | 0.0015 | n/a | n/a | n/a | n/a | n/a | n/a |

### Discrimination within strata (an origin and a cell scored on its own, averaged with weights by stratum size): the pooled AUC above also credits a rung with the movement of the base rate between cells and origins, which P0 has by construction

| cell | rung | auc_event_within | auc_event_within_lo | auc_event_within_hi | resolution_event_within | resolution_event_within_lo | resolution_event_within_hi | auc_direction_within | auc_direction_within_lo | auc_direction_within_hi | resolution_direction_within |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.5942 | 0.5677 | 0.6217 | 0.0137 | 0.0181 | 0.0244 | 0.5523 | 0.5335 | 0.5684 | 0.0148 |
| ALL | GBM+cal | 0.5942 | 0.5677 | 0.6217 | 0.0137 | 0.0181 | 0.0244 | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| ALL | P1 | 0.5765 | 0.5472 | 0.6050 | 0.0109 | 0.0159 | 0.0213 | 0.5279 | 0.5085 | 0.5454 | 0.0137 |
| ALL | P2 | 0.5745 | 0.5450 | 0.6026 | 0.0110 | 0.0161 | 0.0216 | 0.5263 | 0.5075 | 0.5441 | 0.0137 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.5579 | 0.5247 | 0.5917 | 0.0125 | 0.0174 | 0.0227 | 0.5367 | 0.5188 | 0.5534 | 0.0125 |
| ALL | local_eb+cal | 0.5579 | 0.5247 | 0.5917 | 0.0125 | 0.0174 | 0.0227 | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.5230 | 0.4928 | 0.5509 | 0.0074 | 0.0129 | 0.0178 | 0.5421 | 0.5250 | 0.5589 | 0.0121 |
| ALL | text_lr+cal | 0.5230 | 0.4928 | 0.5509 | 0.0074 | 0.0129 | 0.0178 | n/a | n/a | n/a | n/a |
| both | GBM | 0.6215 | 0.5853 | 0.6585 | 0.0141 | 0.0170 | 0.0278 | 0.5565 | 0.5271 | 0.5835 | 0.0154 |
| both | GBM+cal | 0.6215 | 0.5853 | 0.6585 | 0.0141 | 0.0170 | 0.0278 | n/a | n/a | n/a | n/a |
| both | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| both | P1 | 0.6209 | 0.5827 | 0.6584 | 0.0130 | 0.0160 | 0.0259 | 0.5101 | 0.4825 | 0.5372 | 0.0176 |
| both | P2 | 0.6183 | 0.5790 | 0.6556 | 0.0134 | 0.0165 | 0.0265 | 0.5054 | 0.4799 | 0.5341 | 0.0161 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5954 | 0.5582 | 0.6315 | 0.0131 | 0.0163 | 0.0261 | 0.5503 | 0.5209 | 0.5754 | 0.0161 |
| both | local_eb+cal | 0.5954 | 0.5582 | 0.6315 | 0.0131 | 0.0163 | 0.0261 | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5478 | 0.5123 | 0.5850 | 0.0086 | 0.0124 | 0.0209 | 0.5352 | 0.5082 | 0.5633 | 0.0167 |
| both | text_lr+cal | 0.5478 | 0.5123 | 0.5850 | 0.0086 | 0.0124 | 0.0209 | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.6204 | 0.5940 | 0.6453 | 0.0248 | 0.0298 | 0.0440 | 0.5568 | 0.5255 | 0.5877 | 0.0156 |
| headline_only | GBM+cal | 0.6204 | 0.5940 | 0.6453 | 0.0248 | 0.0298 | 0.0440 | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| headline_only | P1 | 0.5884 | 0.5589 | 0.6129 | 0.0173 | 0.0240 | 0.0366 | 0.5244 | 0.4923 | 0.5568 | 0.0139 |
| headline_only | P2 | 0.5884 | 0.5589 | 0.6129 | 0.0173 | 0.0240 | 0.0366 | 0.5244 | 0.4923 | 0.5568 | 0.0139 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5937 | 0.5631 | 0.6192 | 0.0208 | 0.0271 | 0.0398 | 0.5230 | 0.4881 | 0.5549 | 0.0118 |
| headline_only | local_eb+cal | 0.5937 | 0.5631 | 0.6192 | 0.0208 | 0.0271 | 0.0398 | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5408 | 0.5109 | 0.5646 | 0.0109 | 0.0185 | 0.0297 | 0.5567 | 0.5265 | 0.5855 | 0.0101 |
| headline_only | text_lr+cal | 0.5408 | 0.5109 | 0.5646 | 0.0109 | 0.0185 | 0.0297 | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.5374 | 0.4606 | 0.6066 | 0.0016 | 0.0024 | 0.0054 | 0.5431 | 0.5122 | 0.5745 | 0.0135 |
| image_only | GBM+cal | 0.5374 | 0.4606 | 0.6066 | 0.0016 | 0.0024 | 0.0054 | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| image_only | P1 | 0.5166 | 0.4455 | 0.5913 | 0.0017 | 0.0025 | 0.0056 | 0.5506 | 0.5203 | 0.5799 | 0.0093 |
| image_only | P2 | 0.5132 | 0.4421 | 0.5879 | 0.0017 | 0.0025 | 0.0056 | 0.5507 | 0.5201 | 0.5801 | 0.0110 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.4801 | 0.3902 | 0.5850 | 0.0030 | 0.0031 | 0.0076 | 0.5367 | 0.5054 | 0.5688 | 0.0096 |
| image_only | local_eb+cal | 0.4801 | 0.3902 | 0.5850 | 0.0030 | 0.0031 | 0.0076 | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.4779 | 0.4076 | 0.5507 | 0.0025 | 0.0029 | 0.0066 | 0.5338 | 0.5033 | 0.5648 | 0.0094 |
| image_only | text_lr+cal | 0.4779 | 0.4076 | 0.5507 | 0.0025 | 0.0029 | 0.0066 | n/a | n/a | n/a | n/a |

### Sensitivity of the event definition: the same forecasts scored against y > z s_star on the planned standard error (the headline uses the realized one)

| cell | rung | event_rate_planned | p_sig_mean | brier_planned | brier_base_planned | brier_skill_planned | brier_skill_planned_lo | brier_skill_planned_hi |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.2036 | 0.2259 | 0.1392 | 0.1423 | 0.0217 | 0.0058 | 0.0359 |
| ALL | GBM+cal | 0.2036 | 0.2143 | 0.1386 | 0.1423 | 0.0260 | 0.0073 | 0.0426 |
| ALL | P0 | 0.2036 | 0.2135 | 0.1423 | 0.1423 | 0.0000 | 0.0000 | 0.0000 |
| ALL | P1 | 0.2036 | 0.2091 | 0.1389 | 0.1423 | 0.0239 | 0.0145 | 0.0332 |
| ALL | P2 | 0.2036 | 0.2090 | 0.1389 | 0.1423 | 0.0237 | 0.0145 | 0.0332 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.2036 | 0.2144 | 0.1398 | 0.1423 | 0.0174 | 0.0055 | 0.0303 |
| ALL | local_eb+cal | 0.2036 | 0.2111 | 0.1393 | 0.1423 | 0.0204 | 0.0095 | 0.0324 |
| ALL | text_lr | 0.2036 | 0.2106 | 0.1442 | 0.1423 | -0.0137 | -0.0273 | 0.0009 |
| ALL | text_lr+cal | 0.2036 | 0.2123 | 0.1434 | 0.1423 | -0.0079 | -0.0205 | 0.0045 |
| both | GBM | 0.1793 | 0.2049 | 0.1433 | 0.1472 | 0.0265 | 0.0080 | 0.0455 |
| both | GBM+cal | 0.1793 | 0.1836 | 0.1430 | 0.1472 | 0.0291 | 0.0069 | 0.0522 |
| both | P0 | 0.1793 | 0.1846 | 0.1472 | 0.1472 | 0.0000 | 0.0000 | 0.0000 |
| both | P1 | 0.1793 | 0.1825 | 0.1430 | 0.1472 | 0.0291 | 0.0155 | 0.0425 |
| both | P2 | 0.1793 | 0.1820 | 0.1430 | 0.1472 | 0.0286 | 0.0146 | 0.0420 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.1793 | 0.1828 | 0.1443 | 0.1472 | 0.0203 | 0.0025 | 0.0382 |
| both | local_eb+cal | 0.1793 | 0.1826 | 0.1440 | 0.1472 | 0.0221 | 0.0047 | 0.0388 |
| both | text_lr | 0.1793 | 0.1771 | 0.1481 | 0.1472 | -0.0056 | -0.0237 | 0.0133 |
| both | text_lr+cal | 0.1793 | 0.1882 | 0.1477 | 0.1472 | -0.0032 | -0.0194 | 0.0130 |
| headline_only | GBM | 0.3849 | 0.3655 | 0.2274 | 0.2377 | 0.0435 | 0.0216 | 0.0650 |
| headline_only | GBM+cal | 0.3849 | 0.3798 | 0.2285 | 0.2377 | 0.0389 | 0.0120 | 0.0639 |
| headline_only | P0 | 0.3849 | 0.4086 | 0.2377 | 0.2377 | 0.0000 | 0.0000 | 0.0000 |
| headline_only | P1 | 0.3849 | 0.3946 | 0.2318 | 0.2377 | 0.0251 | 0.0108 | 0.0379 |
| headline_only | P2 | 0.3849 | 0.3946 | 0.2318 | 0.2377 | 0.0251 | 0.0108 | 0.0379 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.3849 | 0.4106 | 0.2331 | 0.2377 | 0.0197 | 0.0010 | 0.0357 |
| headline_only | local_eb+cal | 0.3849 | 0.3984 | 0.2319 | 0.2377 | 0.0247 | 0.0067 | 0.0401 |
| headline_only | text_lr | 0.3849 | 0.4045 | 0.2421 | 0.2377 | -0.0185 | -0.0393 | -0.0003 |
| headline_only | text_lr+cal | 0.3849 | 0.3855 | 0.2396 | 0.2377 | -0.0078 | -0.0274 | 0.0096 |
| image_only | GBM | 0.0367 | 0.0999 | 0.0409 | 0.0354 | -0.1547 | -0.2406 | -0.0939 |
| image_only | GBM+cal | 0.0367 | 0.0710 | 0.0383 | 0.0354 | -0.0804 | -0.1314 | -0.0442 |
| image_only | P0 | 0.0367 | 0.0369 | 0.0354 | 0.0354 | 0.0000 | 0.0000 | 0.0000 |
| image_only | P1 | 0.0367 | 0.0402 | 0.0357 | 0.0354 | -0.0078 | -0.0162 | -0.0001 |
| image_only | P2 | 0.0367 | 0.0403 | 0.0357 | 0.0354 | -0.0080 | -0.0163 | -0.0002 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.0367 | 0.0395 | 0.0359 | 0.0354 | -0.0122 | -0.0238 | -0.0018 |
| image_only | local_eb+cal | 0.0367 | 0.0423 | 0.0361 | 0.0354 | -0.0175 | -0.0311 | -0.0060 |
| image_only | text_lr | 0.0367 | 0.0401 | 0.0360 | 0.0354 | -0.0149 | -0.0244 | -0.0055 |
| image_only | text_lr+cal | 0.0367 | 0.0538 | 0.0365 | 0.0354 | -0.0290 | -0.0499 | -0.0124 |

### Paired log score difference from P1 on the same rows (nats per row, 90 percent by-test interval; negative means the rung scores below P1)

| cell | rung | logscore_vs_p1 | logscore_vs_p1_lo | logscore_vs_p1_hi | logscore_vs_p1_adjusted_lo | logscore_vs_p1_adjusted_hi | n_paired |
|---|---|---|---|---|---|---|---|
| ALL | GBM | -0.0251 | -0.0337 | -0.0166 | -0.0413 | -0.0089 | 3576 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | P0 | -0.0084 | -0.0133 | -0.0037 | -0.0177 | 0.0009 | 3576 |
| ALL | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 3576 |
| ALL | P2 | 0.0000 | -0.0002 | 0.0003 | -0.0005 | 0.0005 | 3576 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | local_eb | -0.0136 | -0.0190 | -0.0078 | -0.0242 | -0.0029 | 3576 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | GBM | 0.0006 | -0.0078 | 0.0093 | -0.0155 | 0.0167 | 1216 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | P0 | -0.0017 | -0.0086 | 0.0051 | -0.0147 | 0.0113 | 1216 |
| both | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1216 |
| both | P2 | -0.0001 | -0.0008 | 0.0006 | -0.0014 | 0.0012 | 1216 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| both | local_eb | -0.0126 | -0.0225 | -0.0032 | -0.0310 | 0.0058 | 1216 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | GBM | -0.0199 | -0.0392 | -0.0037 | -0.0534 | 0.0136 | 1216 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | P0 | -0.0032 | -0.0079 | 0.0012 | -0.0118 | 0.0053 | 1216 |
| headline_only | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1216 |
| headline_only | P2 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1216 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | local_eb | -0.0181 | -0.0290 | -0.0082 | -0.0386 | 0.0024 | 1216 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | GBM | -0.0579 | -0.0729 | -0.0418 | -0.0879 | -0.0280 | 1144 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | P0 | -0.0209 | -0.0337 | -0.0103 | -0.0429 | 0.0010 | 1144 |
| image_only | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1144 |
| image_only | P2 | 0.0001 | -0.0001 | 0.0005 | -0.0004 | 0.0007 | 1144 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | local_eb | -0.0098 | -0.0192 | -0.0001 | -0.0272 | 0.0077 | 1144 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |

### The gate read with the group's own dependence: rows per test and within-test correlation of the group against those the nearest simulated gate assumed, and the gate sizes scaled to first order by the information per test (an approximation; docs/method.md call 205)

| cell | rung | event_rate | gate_cell_rows_per_test | gate_cell_icc | gate_assumed_rows_per_test | gate_assumed_icc | gate_cell_n_200 | gate_cell_n_400 | decidable_by_tests_cell |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | GBM+cal | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | P0 | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | P1 | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | P2 | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | always_reference | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | always_variant | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb+cal | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr+cal | 0.2036 | 2.0000 | 0.1583 | 5.0000 | 0.6700 | 158 | 315 | decidable at skill 0.20 and 0.10 |
| both | GBM | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | GBM+cal | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | P0 | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | P1 | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | P2 | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | always_reference | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | always_variant | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | local_eb | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | local_eb+cal | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | text_lr | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| both | text_lr+cal | 0.1793 | 2.0000 | 0.0000 | 5.0000 | 0.6700 | 136 | 272 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM+cal | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | P0 | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | P1 | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | P2 | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | always_reference | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | always_variant | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb+cal | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr+cal | 0.3849 | 2.0000 | 0.0760 | 3.5000 | 0.1300 | 107 | 214 | decidable at skill 0.20 and 0.10 |
| image_only | GBM | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | GBM+cal | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | P0 | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | P1 | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | P2 | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | always_reference | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | always_variant | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb+cal | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr+cal | 0.0367 | 2.0000 | 0.0113 | 3.5000 | 0.1300 | 234 | 334 | decidable at skill 0.20 and 0.10 |

### Direction accuracy and coverage of the intervals for y

| cell | rung | direction_accuracy | direction_accuracy_lo | direction_accuracy_hi | n_decisive | direction_accuracy_decisive | direction_ceiling | coverage_80 | coverage_80_lo | coverage_80_hi | coverage_90 | coverage_90_lo | coverage_90_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.6641 | 0.6513 | 0.6773 | 1169 | 0.7819 | 0.8254 | 0.8157 | 0.8045 | 0.8263 | 0.9044 | 0.8968 | 0.9122 |
| ALL | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8254 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.6723 | 0.6599 | 0.6843 | 1169 | 0.7973 | 0.8254 | 0.7931 | 0.7827 | 0.8048 | 0.8949 | 0.8865 | 0.9038 |
| ALL | P1 | 0.6723 | 0.6599 | 0.6843 | 1169 | 0.7973 | 0.8254 | 0.7984 | 0.7878 | 0.8098 | 0.8957 | 0.8870 | 0.9047 |
| ALL | P2 | 0.6723 | 0.6599 | 0.6843 | 1169 | 0.7973 | 0.8254 | 0.7984 | 0.7880 | 0.8096 | 0.8954 | 0.8867 | 0.9044 |
| ALL | always_reference | 0.4636 | 0.4488 | 0.4771 | 1169 | 0.3772 | 0.8254 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | 0.5364 | 0.5229 | 0.5512 | 1169 | 0.6228 | 0.8254 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.6711 | 0.6582 | 0.6832 | 1169 | 0.7956 | 0.8254 | 0.7970 | 0.7849 | 0.8082 | 0.8921 | 0.8834 | 0.9010 |
| ALL | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8254 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.6566 | 0.6437 | 0.6698 | 1169 | 0.7648 | 0.8254 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8254 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | 0.5789 | 0.5559 | 0.6012 | 330 | 0.6455 | 0.8087 | 0.8322 | 0.8157 | 0.8479 | 0.9194 | 0.9071 | 0.9310 |
| both | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8087 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | 0.5847 | 0.5609 | 0.6061 | 330 | 0.6606 | 0.8087 | 0.7961 | 0.7771 | 0.8141 | 0.9021 | 0.8890 | 0.9153 |
| both | P1 | 0.5847 | 0.5609 | 0.6061 | 330 | 0.6606 | 0.8087 | 0.8035 | 0.7861 | 0.8215 | 0.9013 | 0.8882 | 0.9153 |
| both | P2 | 0.5847 | 0.5609 | 0.6061 | 330 | 0.6606 | 0.8087 | 0.8035 | 0.7862 | 0.8207 | 0.9005 | 0.8873 | 0.9145 |
| both | always_reference | 0.4153 | 0.3939 | 0.4391 | 330 | 0.3394 | 0.8087 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | 0.5847 | 0.5609 | 0.6061 | 330 | 0.6606 | 0.8087 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5814 | 0.5551 | 0.6036 | 330 | 0.6545 | 0.8087 | 0.8059 | 0.7870 | 0.8224 | 0.9005 | 0.8865 | 0.9137 |
| both | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8087 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5633 | 0.5386 | 0.5856 | 330 | 0.6212 | 0.8087 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8087 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.7204 | 0.6982 | 0.7410 | 551 | 0.8512 | 0.8765 | 0.7319 | 0.7113 | 0.7533 | 0.8438 | 0.8273 | 0.8610 |
| headline_only | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8765 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.7220 | 0.6998 | 0.7434 | 551 | 0.8494 | 0.8765 | 0.7944 | 0.7746 | 0.8133 | 0.9005 | 0.8865 | 0.9145 |
| headline_only | P1 | 0.7220 | 0.6998 | 0.7434 | 551 | 0.8494 | 0.8765 | 0.8059 | 0.7870 | 0.8240 | 0.8980 | 0.8832 | 0.9120 |
| headline_only | P2 | 0.7220 | 0.6998 | 0.7434 | 551 | 0.8494 | 0.8765 | 0.8059 | 0.7870 | 0.8240 | 0.8980 | 0.8832 | 0.9120 |
| headline_only | always_reference | 0.2780 | 0.2566 | 0.3002 | 551 | 0.1506 | 0.8765 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | 0.7220 | 0.6998 | 0.7434 | 551 | 0.8494 | 0.8765 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.7220 | 0.6998 | 0.7434 | 551 | 0.8494 | 0.8765 | 0.7985 | 0.7788 | 0.8158 | 0.8914 | 0.8766 | 0.9054 |
| headline_only | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8765 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.7196 | 0.6965 | 0.7410 | 551 | 0.8403 | 0.8765 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8765 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.6949 | 0.6730 | 0.7159 | 288 | 0.8056 | 0.7886 | 0.8872 | 0.8706 | 0.9039 | 0.9528 | 0.9414 | 0.9633 |
| image_only | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.7886 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.7124 | 0.6897 | 0.7334 | 288 | 0.8542 | 0.7886 | 0.7885 | 0.7666 | 0.8086 | 0.8811 | 0.8628 | 0.8977 |
| image_only | P1 | 0.7124 | 0.6897 | 0.7334 | 288 | 0.8542 | 0.7886 | 0.7850 | 0.7631 | 0.8068 | 0.8872 | 0.8715 | 0.9030 |
| image_only | P2 | 0.7124 | 0.6897 | 0.7334 | 288 | 0.8542 | 0.7886 | 0.7850 | 0.7631 | 0.8068 | 0.8872 | 0.8715 | 0.9030 |
| image_only | always_reference | 0.7124 | 0.6897 | 0.7334 | 288 | 0.8542 | 0.7886 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | 0.2876 | 0.2666 | 0.3103 | 288 | 0.1458 | 0.7886 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.7124 | 0.6897 | 0.7334 | 288 | 0.8542 | 0.7886 | 0.7858 | 0.7648 | 0.8068 | 0.8837 | 0.8663 | 0.8995 |
| image_only | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.7886 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.6888 | 0.6660 | 0.7133 | 288 | 0.7847 | 0.7886 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.7886 | n/a | n/a | n/a | n/a | n/a | n/a |

### The same scores on non-abstained rows only

| cell | rung | logscore_nonabstained | logscore_nonabstained_lo | logscore_nonabstained_hi | crps_nonabstained | crps_nonabstained_lo | crps_nonabstained_hi | brier_nonabstained | brier_nonabstained_lo | brier_nonabstained_hi | direction_accuracy_nonabstained | direction_accuracy_nonabstained_lo | direction_accuracy_nonabstained_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | -2.4472 | -2.4717 | -2.4236 | 1.5678 | 1.5315 | 1.6073 | 0.1409 | 0.1347 | 0.1474 | 0.6664 | 0.6524 | 0.6811 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1404 | 0.1338 | 0.1471 | n/a | n/a | n/a |
| ALL | P0 | -2.4264 | -2.4490 | -2.4023 | 1.5606 | 1.5237 | 1.5952 | 0.1443 | 0.1375 | 0.1505 | 0.6715 | 0.6572 | 0.6861 |
| ALL | P1 | -2.4181 | -2.4395 | -2.3935 | 1.5580 | 1.5206 | 1.5938 | 0.1406 | 0.1342 | 0.1472 | 0.6715 | 0.6572 | 0.6861 |
| ALL | P2 | -2.4183 | -2.4395 | -2.3937 | 1.5584 | 1.5212 | 1.5942 | 0.1407 | 0.1342 | 0.1472 | 0.6715 | 0.6572 | 0.6861 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4578 | 0.4417 | 0.4743 |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5422 | 0.5257 | 0.5583 |
| ALL | local_eb | -2.4309 | -2.4544 | -2.4061 | 1.5655 | 1.5268 | 1.6026 | 0.1414 | 0.1346 | 0.1478 | 0.6672 | 0.6530 | 0.6820 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1411 | 0.1343 | 0.1476 | n/a | n/a | n/a |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.1463 | 0.1393 | 0.1530 | 0.6544 | 0.6395 | 0.6698 |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1456 | 0.1387 | 0.1521 | n/a | n/a | n/a |
| both | GBM | -2.3903 | -2.4299 | -2.3558 | 1.4798 | 1.4258 | 1.5447 | 0.1444 | 0.1335 | 0.1556 | 0.5836 | 0.5562 | 0.6084 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1442 | 0.1324 | 0.1561 | n/a | n/a | n/a |
| both | P0 | -2.3926 | -2.4362 | -2.3547 | 1.4816 | 1.4272 | 1.5460 | 0.1490 | 0.1366 | 0.1617 | 0.5942 | 0.5693 | 0.6191 |
| both | P1 | -2.3881 | -2.4311 | -2.3506 | 1.4805 | 1.4252 | 1.5462 | 0.1436 | 0.1316 | 0.1555 | 0.5942 | 0.5693 | 0.6191 |
| both | P2 | -2.3888 | -2.4319 | -2.3515 | 1.4819 | 1.4260 | 1.5475 | 0.1437 | 0.1317 | 0.1556 | 0.5942 | 0.5693 | 0.6191 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4058 | 0.3809 | 0.4307 |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5942 | 0.5693 | 0.6191 |
| both | local_eb | -2.3989 | -2.4413 | -2.3628 | 1.4889 | 1.4356 | 1.5543 | 0.1456 | 0.1338 | 0.1578 | 0.5815 | 0.5537 | 0.6067 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1455 | 0.1337 | 0.1577 | n/a | n/a | n/a |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.1501 | 0.1380 | 0.1624 | 0.5698 | 0.5449 | 0.5958 |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1497 | 0.1379 | 0.1616 | n/a | n/a | n/a |
| headline_only | GBM | -2.6698 | -2.7320 | -2.6184 | 1.9183 | 1.8454 | 2.0060 | 0.2303 | 0.2218 | 0.2394 | 0.7158 | 0.6890 | 0.7412 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.2314 | 0.2231 | 0.2407 | n/a | n/a | n/a |
| headline_only | P0 | -2.6397 | -2.6798 | -2.6046 | 1.9186 | 1.8512 | 1.9979 | 0.2391 | 0.2338 | 0.2445 | 0.7179 | 0.6925 | 0.7439 |
| headline_only | P1 | -2.6393 | -2.6788 | -2.6024 | 1.9170 | 1.8480 | 1.9950 | 0.2337 | 0.2268 | 0.2408 | 0.7179 | 0.6925 | 0.7439 |
| headline_only | P2 | -2.6393 | -2.6788 | -2.6024 | 1.9170 | 1.8480 | 1.9950 | 0.2337 | 0.2268 | 0.2408 | 0.7179 | 0.6925 | 0.7439 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2821 | 0.2561 | 0.3075 |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.7179 | 0.6925 | 0.7439 |
| headline_only | local_eb | -2.6571 | -2.6989 | -2.6203 | 1.9319 | 1.8643 | 2.0081 | 0.2337 | 0.2273 | 0.2411 | 0.7179 | 0.6925 | 0.7439 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.2330 | 0.2260 | 0.2407 | n/a | n/a | n/a |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.2434 | 0.2360 | 0.2521 | 0.7137 | 0.6863 | 0.7388 |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.2415 | 0.2334 | 0.2503 | n/a | n/a | n/a |
| image_only | GBM | -2.2673 | -2.2953 | -2.2394 | 1.2828 | 1.2326 | 1.3328 | 0.0402 | 0.0331 | 0.0497 | 0.7023 | 0.6751 | 0.7270 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0376 | 0.0300 | 0.0480 | n/a | n/a | n/a |
| image_only | P0 | -2.2317 | -2.2785 | -2.1852 | 1.2579 | 1.1996 | 1.3134 | 0.0365 | 0.0283 | 0.0473 | 0.7046 | 0.6778 | 0.7294 |
| image_only | P1 | -2.2107 | -2.2537 | -2.1657 | 1.2523 | 1.1927 | 1.3063 | 0.0366 | 0.0284 | 0.0474 | 0.7046 | 0.6778 | 0.7294 |
| image_only | P2 | -2.2106 | -2.2536 | -2.1657 | 1.2521 | 1.1924 | 1.3061 | 0.0366 | 0.0284 | 0.0474 | 0.7046 | 0.6778 | 0.7294 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.7046 | 0.6778 | 0.7294 |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2954 | 0.2706 | 0.3222 |
| image_only | local_eb | -2.2202 | -2.2628 | -2.1735 | 1.2512 | 1.1952 | 1.3056 | 0.0368 | 0.0288 | 0.0475 | 0.7046 | 0.6778 | 0.7294 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0368 | 0.0288 | 0.0475 | n/a | n/a | n/a |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.0370 | 0.0290 | 0.0478 | 0.6816 | 0.6548 | 0.7077 |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0373 | 0.0295 | 0.0478 | n/a | n/a | n/a |

### Other columns

| cell | rung | resolution_direction_within_lo | resolution_direction_within_hi | latent_rho | gate_cell_scale |
|---|---|---|---|---|---|
| ALL | GBM | 0.0232 | 0.0307 | 0.0000 | 0.7869 |
| ALL | GBM+cal | n/a | n/a | 0.0122 | 0.7869 |
| ALL | P0 | 0.0000 | 0.0000 | 0.0479 | 0.7869 |
| ALL | P1 | 0.0221 | 0.0292 | 0.0427 | 0.7869 |
| ALL | P2 | 0.0223 | 0.0294 | 0.0447 | 0.7869 |
| ALL | always_reference | n/a | n/a | n/a | 0.7869 |
| ALL | always_variant | n/a | n/a | n/a | 0.7869 |
| ALL | local_eb | 0.0213 | 0.0278 | 0.0687 | 0.7869 |
| ALL | local_eb+cal | n/a | n/a | 0.0541 | 0.7869 |
| ALL | text_lr | 0.0210 | 0.0274 | 0.1675 | 0.7869 |
| ALL | text_lr+cal | n/a | n/a | 0.0693 | 0.7869 |
| both | GBM | 0.0228 | 0.0356 | 0.0000 | 0.6793 |
| both | GBM+cal | n/a | n/a | 0.0000 | 0.6793 |
| both | P0 | 0.0000 | 0.0000 | 0.0000 | 0.6793 |
| both | P1 | 0.0248 | 0.0374 | 0.0000 | 0.6793 |
| both | P2 | 0.0239 | 0.0356 | 0.0000 | 0.6793 |
| both | always_reference | n/a | n/a | n/a | 0.6793 |
| both | always_variant | n/a | n/a | n/a | 0.6793 |
| both | local_eb | 0.0227 | 0.0360 | 0.0000 | 0.6793 |
| both | local_eb+cal | n/a | n/a | 0.0000 | 0.6793 |
| both | text_lr | 0.0240 | 0.0364 | 0.1379 | 0.6793 |
| both | text_lr+cal | n/a | n/a | 0.0035 | 0.6793 |
| headline_only | GBM | 0.0206 | 0.0318 | 0.1825 | 1.4211 |
| headline_only | GBM+cal | n/a | n/a | 0.2239 | 1.4211 |
| headline_only | P0 | 0.0000 | 0.0000 | 0.0964 | 1.4211 |
| headline_only | P1 | 0.0192 | 0.0312 | 0.1100 | 1.4211 |
| headline_only | P2 | 0.0192 | 0.0312 | 0.1100 | 1.4211 |
| headline_only | always_reference | n/a | n/a | n/a | 1.4211 |
| headline_only | always_variant | n/a | n/a | n/a | 1.4211 |
| headline_only | local_eb | 0.0179 | 0.0276 | 0.1206 | 1.4211 |
| headline_only | local_eb+cal | n/a | n/a | 0.1182 | 1.4211 |
| headline_only | text_lr | 0.0157 | 0.0264 | 0.1900 | 1.4211 |
| headline_only | text_lr+cal | n/a | n/a | 0.1800 | 1.4211 |
| image_only | GBM | 0.0200 | 0.0315 | 0.0000 | 1.3357 |
| image_only | GBM+cal | n/a | n/a | 0.0000 | 1.3357 |
| image_only | P0 | 0.0000 | 0.0000 | 0.0000 | 1.3357 |
| image_only | P1 | 0.0166 | 0.0273 | 0.0000 | 1.3357 |
| image_only | P2 | 0.0182 | 0.0285 | 0.0000 | 1.3357 |
| image_only | always_reference | n/a | n/a | n/a | 1.3357 |
| image_only | always_variant | n/a | n/a | n/a | 1.3357 |
| image_only | local_eb | 0.0171 | 0.0271 | 0.0000 | 1.3357 |
| image_only | local_eb+cal | n/a | n/a | 0.0000 | 1.3357 |
| image_only | text_lr | 0.0163 | 0.0269 | 0.0000 | 1.3357 |
| image_only | text_lr+cal | n/a | n/a | 0.0000 | 1.3357 |

## P2 selection by cell

How lam (the weight on precedents), the bandwidth multiplier and the recency half-life were chosen, summarised over the origins. `share_lambda_zero` is the share of origins where the selection gave up on precedents and P2 equalled P1 in that cell. `guard` is the admission guard multiplier: lam above zero is used only when its out-of-sample log-score gain over lam 0 minus that many standard errors (across tests) is above zero, the ladder admission rule made operational. `share_guard_held` is the share of origins where the guard forced lam to 0 although the earlier rule would have used the precedents; `gain_mean` and `gain_se_mean` are the gain of the best candidate and its standard error, averaged over origins. The per-origin values are in the JSON under `p2_selection`.

| rung | cell | selection | origins | lambda_mean | lambda_min | lambda_max | share_lambda_zero | guard | share_guard_held | lambda_unguarded_mean | gain_mean | gain_se_mean | bandwidth_mult_mean | half_life_days_median | share_no_decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | both | forward | 8 | 0.0375 | 0.0000 | 0.3000 | 0.8750 | 2.0000 | 0.6250 | 0.2750 | 0.0027 | 0.0034 | 0.5312 | n/a | 1.0000 |
| P2 | headline_only | forward | 8 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 2.0000 | 0.6250 | 0.2000 | 0.0021 | 0.0027 | 0.4375 | n/a | 1.0000 |
| P2 | image_only | forward | 8 | 0.0125 | 0.0000 | 0.1000 | 0.8750 | 2.0000 | 0.1250 | 0.0875 | 0.0003 | 0.0019 | 0.6875 | n/a | 1.0000 |

## Abstention by trigger

Counts of rows that fired each trigger (a row can fire several).

| cell | n | rate | support | novelty | reliability | instability |
|---|---|---|---|---|---|---|
| ALL | 3576 | 0.2304 | 0 | 394 | 448 | 1 |
| both | 1216 | 0.2278 | 0 | 135 | 150 | 1 |
| headline_only | 1216 | 0.2245 | 0 | 117 | 162 | 0 |
| image_only | 1144 | 0.2395 | 0 | 142 | 136 | 0 |

Never fired in this backtest: support. After the burn-in origin the reliability trigger fired on 0 rows, so no cell was marked drifted and every reliability abstention is the missing report at the burn-in origin.

## Origins

The first scored origin is the burn-in origin.

| origin | n_scored | n_tests | abstention_rate | logscore | burn_in |
|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | 448 | 224 | 1.0000 | -2.4972 | yes |
| 2013-07-01T00:00:00+00:00 | 480 | 240 | 0.0771 | -2.3800 | no |
| 2013-10-01T00:00:00+00:00 | 434 | 217 | 0.0438 | -2.4362 | no |
| 2014-01-01T00:00:00+00:00 | 464 | 232 | 0.1013 | -2.3932 | no |
| 2014-04-01T00:00:00+00:00 | 412 | 206 | 0.1214 | -2.3872 | no |
| 2014-07-01T00:00:00+00:00 | 450 | 225 | 0.1689 | -2.4157 | no |
| 2014-10-01T00:00:00+00:00 | 454 | 227 | 0.1630 | -2.4558 | no |
| 2015-01-01T00:00:00+00:00 | 434 | 217 | 0.1682 | -2.4511 | no |

### Log score by origin with 90 percent intervals

| origin | rung | n | logscore | logscore_lo | logscore_hi |
|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | GBM | 448 | -2.5061 | -2.5674 | -2.4458 |
| 2013-04-01T00:00:00+00:00 | P0 | 448 | -2.5045 | -2.5831 | -2.4336 |
| 2013-04-01T00:00:00+00:00 | P1 | 448 | -2.4972 | -2.5634 | -2.4281 |
| 2013-04-01T00:00:00+00:00 | P2 | 448 | -2.4972 | -2.5634 | -2.4281 |
| 2013-04-01T00:00:00+00:00 | local_eb | 448 | -2.5063 | -2.5812 | -2.4391 |
| 2013-07-01T00:00:00+00:00 | GBM | 480 | -2.4179 | -2.4699 | -2.3694 |
| 2013-07-01T00:00:00+00:00 | P0 | 480 | -2.3760 | -2.4311 | -2.3218 |
| 2013-07-01T00:00:00+00:00 | P1 | 480 | -2.3800 | -2.4396 | -2.3243 |
| 2013-07-01T00:00:00+00:00 | P2 | 480 | -2.3800 | -2.4396 | -2.3243 |
| 2013-07-01T00:00:00+00:00 | local_eb | 480 | -2.3860 | -2.4386 | -2.3319 |
| 2013-10-01T00:00:00+00:00 | GBM | 434 | -2.4323 | -2.4887 | -2.3793 |
| 2013-10-01T00:00:00+00:00 | P0 | 434 | -2.4392 | -2.4934 | -2.3799 |
| 2013-10-01T00:00:00+00:00 | P1 | 434 | -2.4362 | -2.4961 | -2.3790 |
| 2013-10-01T00:00:00+00:00 | P2 | 434 | -2.4362 | -2.4961 | -2.3790 |
| 2013-10-01T00:00:00+00:00 | local_eb | 434 | -2.4538 | -2.5242 | -2.3948 |
| 2014-01-01T00:00:00+00:00 | GBM | 464 | -2.4160 | -2.4730 | -2.3604 |
| 2014-01-01T00:00:00+00:00 | P0 | 464 | -2.4025 | -2.4644 | -2.3391 |
| 2014-01-01T00:00:00+00:00 | P1 | 464 | -2.3929 | -2.4463 | -2.3345 |
| 2014-01-01T00:00:00+00:00 | P2 | 464 | -2.3932 | -2.4465 | -2.3347 |
| 2014-01-01T00:00:00+00:00 | local_eb | 464 | -2.3974 | -2.4529 | -2.3399 |
| 2014-04-01T00:00:00+00:00 | GBM | 412 | -2.4387 | -2.5136 | -2.3766 |
| 2014-04-01T00:00:00+00:00 | P0 | 412 | -2.3961 | -2.4607 | -2.3423 |
| 2014-04-01T00:00:00+00:00 | P1 | 412 | -2.3872 | -2.4493 | -2.3344 |
| 2014-04-01T00:00:00+00:00 | P2 | 412 | -2.3872 | -2.4493 | -2.3344 |
| 2014-04-01T00:00:00+00:00 | local_eb | 412 | -2.3975 | -2.4612 | -2.3408 |
| 2014-07-01T00:00:00+00:00 | GBM | 450 | -2.4491 | -2.5107 | -2.3988 |
| 2014-07-01T00:00:00+00:00 | P0 | 450 | -2.4288 | -2.4995 | -2.3685 |
| 2014-07-01T00:00:00+00:00 | P1 | 450 | -2.4157 | -2.4794 | -2.3630 |
| 2014-07-01T00:00:00+00:00 | P2 | 450 | -2.4157 | -2.4794 | -2.3630 |
| 2014-07-01T00:00:00+00:00 | local_eb | 450 | -2.4370 | -2.5039 | -2.3830 |
| 2014-10-01T00:00:00+00:00 | GBM | 454 | -2.4780 | -2.5375 | -2.4180 |
| 2014-10-01T00:00:00+00:00 | P0 | 454 | -2.4650 | -2.5208 | -2.4050 |
| 2014-10-01T00:00:00+00:00 | P1 | 454 | -2.4558 | -2.5078 | -2.3983 |
| 2014-10-01T00:00:00+00:00 | P2 | 454 | -2.4558 | -2.5078 | -2.3983 |
| 2014-10-01T00:00:00+00:00 | local_eb | 454 | -2.4841 | -2.5369 | -2.4259 |
| 2015-01-01T00:00:00+00:00 | GBM | 434 | -2.4796 | -2.5560 | -2.4087 |
| 2015-01-01T00:00:00+00:00 | P0 | 434 | -2.4723 | -2.5426 | -2.4048 |
| 2015-01-01T00:00:00+00:00 | P1 | 434 | -2.4514 | -2.5214 | -2.3862 |
| 2015-01-01T00:00:00+00:00 | P2 | 434 | -2.4511 | -2.5213 | -2.3855 |
| 2015-01-01T00:00:00+00:00 | local_eb | 434 | -2.4633 | -2.5371 | -2.3903 |

### Scores by calendar year of the test start

Each scored row belongs to the year in which its test started; the years partition the scored rows. Brier skill and log score carry 90 percent by-test intervals.

| year | cell | rung | n | n_tests | logscore | logscore_lo | logscore_hi | brier_skill | brier_skill_lo | brier_skill_hi | direction_accuracy | abstention_rate | event_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | ALL | GBM | 1362 | 681 | -2.4515 | -2.4830 | -2.4242 | 0.0367 | 0.0129 | 0.0590 | 0.6535 | 0.3700 | 0.2085 |
| 2013 | ALL | GBM+cal | 1362 | 681 | n/a | n/a | n/a | 0.0481 | 0.0216 | 0.0733 | n/a | 0.3700 | 0.2085 |
| 2013 | ALL | P0 | 1362 | 681 | -2.4384 | -2.4750 | -2.4073 | 0.0000 | 0.0000 | 0.0000 | 0.6703 | 0.3700 | 0.2085 |
| 2013 | ALL | P1 | 1362 | 681 | -2.4365 | -2.4709 | -2.4061 | 0.0276 | 0.0127 | 0.0429 | 0.6703 | 0.3700 | 0.2085 |
| 2013 | ALL | P2 | 1362 | 681 | -2.4365 | -2.4709 | -2.4061 | 0.0276 | 0.0127 | 0.0429 | 0.6703 | 0.3700 | 0.2085 |
| 2013 | ALL | always_reference | 1362 | 681 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4515 | 0.3700 | 0.2085 |
| 2013 | ALL | always_variant | 1362 | 681 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5485 | 0.3700 | 0.2085 |
| 2013 | ALL | local_eb | 1362 | 681 | -2.4472 | -2.4851 | -2.4148 | 0.0234 | 0.0060 | 0.0397 | 0.6711 | 0.3700 | 0.2085 |
| 2013 | ALL | local_eb+cal | 1362 | 681 | n/a | n/a | n/a | 0.0269 | 0.0117 | 0.0423 | n/a | 0.3700 | 0.2085 |
| 2013 | ALL | text_lr | 1362 | 681 | n/a | n/a | n/a | -0.0060 | -0.0307 | 0.0172 | 0.6593 | 0.3700 | 0.2085 |
| 2013 | ALL | text_lr+cal | 1362 | 681 | n/a | n/a | n/a | -0.0014 | -0.0231 | 0.0191 | n/a | 0.3700 | 0.2085 |
| 2013 | both | GBM | 488 | 244 | -2.4307 | -2.4782 | -2.3795 | 0.0459 | 0.0133 | 0.0740 | 0.5840 | 0.3422 | 0.1865 |
| 2013 | both | GBM+cal | 488 | 244 | n/a | n/a | n/a | 0.0529 | 0.0214 | 0.0831 | n/a | 0.3422 | 0.1865 |
| 2013 | both | P0 | 488 | 244 | -2.4340 | -2.4911 | -2.3764 | 0.0000 | 0.0000 | 0.0000 | 0.5881 | 0.3422 | 0.1865 |
| 2013 | both | P1 | 488 | 244 | -2.4377 | -2.4935 | -2.3734 | 0.0331 | 0.0139 | 0.0536 | 0.5881 | 0.3422 | 0.1865 |
| 2013 | both | P2 | 488 | 244 | -2.4377 | -2.4935 | -2.3734 | 0.0331 | 0.0139 | 0.0536 | 0.5881 | 0.3422 | 0.1865 |
| 2013 | both | always_reference | 488 | 244 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4119 | 0.3422 | 0.1865 |
| 2013 | both | always_variant | 488 | 244 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5881 | 0.3422 | 0.1865 |
| 2013 | both | local_eb | 488 | 244 | -2.4460 | -2.5052 | -2.3816 | 0.0314 | 0.0071 | 0.0592 | 0.5902 | 0.3422 | 0.1865 |
| 2013 | both | local_eb+cal | 488 | 244 | n/a | n/a | n/a | 0.0335 | 0.0116 | 0.0575 | n/a | 0.3422 | 0.1865 |
| 2013 | both | text_lr | 488 | 244 | n/a | n/a | n/a | 0.0030 | -0.0271 | 0.0335 | 0.5840 | 0.3422 | 0.1865 |
| 2013 | both | text_lr+cal | 488 | 244 | n/a | n/a | n/a | 0.0047 | -0.0223 | 0.0314 | n/a | 0.3422 | 0.1865 |
| 2013 | headline_only | GBM | 460 | 230 | -2.6156 | -2.6862 | -2.5474 | 0.0722 | 0.0354 | 0.1076 | 0.7261 | 0.3696 | 0.3913 |
| 2013 | headline_only | GBM+cal | 460 | 230 | n/a | n/a | n/a | 0.0742 | 0.0310 | 0.1120 | n/a | 0.3696 | 0.3913 |
| 2013 | headline_only | P0 | 460 | 230 | -2.6337 | -2.6835 | -2.5844 | 0.0000 | 0.0000 | 0.0000 | 0.7304 | 0.3696 | 0.3913 |
| 2013 | headline_only | P1 | 460 | 230 | -2.6314 | -2.6851 | -2.5780 | 0.0296 | 0.0078 | 0.0515 | 0.7304 | 0.3696 | 0.3913 |
| 2013 | headline_only | P2 | 460 | 230 | -2.6314 | -2.6851 | -2.5780 | 0.0296 | 0.0078 | 0.0515 | 0.7304 | 0.3696 | 0.3913 |
| 2013 | headline_only | always_reference | 460 | 230 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2696 | 0.3696 | 0.3913 |
| 2013 | headline_only | always_variant | 460 | 230 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7304 | 0.3696 | 0.3913 |
| 2013 | headline_only | local_eb | 460 | 230 | -2.6432 | -2.6951 | -2.5917 | 0.0230 | -0.0019 | 0.0482 | 0.7304 | 0.3696 | 0.3913 |
| 2013 | headline_only | local_eb+cal | 460 | 230 | n/a | n/a | n/a | 0.0298 | 0.0069 | 0.0538 | n/a | 0.3696 | 0.3913 |
| 2013 | headline_only | text_lr | 460 | 230 | n/a | n/a | n/a | -0.0103 | -0.0461 | 0.0224 | 0.7261 | 0.3696 | 0.3913 |
| 2013 | headline_only | text_lr+cal | 460 | 230 | n/a | n/a | n/a | 0.0003 | -0.0322 | 0.0309 | n/a | 0.3696 | 0.3913 |
| 2013 | image_only | GBM | 414 | 207 | -2.2937 | -2.3339 | -2.2560 | -0.3257 | -0.6517 | -0.1618 | 0.6546 | 0.4034 | 0.0314 |
| 2013 | image_only | GBM+cal | 414 | 207 | n/a | n/a | n/a | -0.2079 | -0.4250 | -0.0946 | n/a | 0.4034 | 0.0314 |
| 2013 | image_only | P0 | 414 | 207 | -2.2267 | -2.3072 | -2.1548 | 0.0000 | 0.0000 | 0.0000 | 0.7005 | 0.4034 | 0.0314 |
| 2013 | image_only | P1 | 414 | 207 | -2.2186 | -2.2843 | -2.1565 | -0.0214 | -0.0520 | -0.0039 | 0.7005 | 0.4034 | 0.0314 |
| 2013 | image_only | P2 | 414 | 207 | -2.2186 | -2.2843 | -2.1565 | -0.0214 | -0.0520 | -0.0039 | 0.7005 | 0.4034 | 0.0314 |
| 2013 | image_only | always_reference | 414 | 207 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7005 | 0.4034 | 0.0314 |
| 2013 | image_only | always_variant | 414 | 207 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2995 | 0.4034 | 0.0314 |
| 2013 | image_only | local_eb | 414 | 207 | -2.2307 | -2.3041 | -2.1672 | -0.0198 | -0.0440 | -0.0018 | 0.7005 | 0.4034 | 0.0314 |
| 2013 | image_only | local_eb+cal | 414 | 207 | n/a | n/a | n/a | -0.0361 | -0.0715 | -0.0146 | n/a | 0.4034 | 0.0314 |
| 2013 | image_only | text_lr | 414 | 207 | n/a | n/a | n/a | -0.0202 | -0.0479 | 0.0026 | 0.6739 | 0.4034 | 0.0314 |
| 2013 | image_only | text_lr+cal | 414 | 207 | n/a | n/a | n/a | -0.0524 | -0.1186 | -0.0139 | n/a | 0.4034 | 0.0314 |
| 2014 | ALL | GBM | 1780 | 890 | -2.4454 | -2.4762 | -2.4182 | 0.0047 | -0.0172 | 0.0251 | 0.6702 | 0.1388 | 0.2056 |
| 2014 | ALL | GBM+cal | 1780 | 890 | n/a | n/a | n/a | 0.0049 | -0.0214 | 0.0289 | n/a | 0.1388 | 0.2056 |
| 2014 | ALL | P0 | 1780 | 890 | -2.4236 | -2.4548 | -2.3948 | 0.0000 | 0.0000 | 0.0000 | 0.6736 | 0.1388 | 0.2056 |
| 2014 | ALL | P1 | 1780 | 890 | -2.4134 | -2.4421 | -2.3853 | 0.0211 | 0.0079 | 0.0350 | 0.6736 | 0.1388 | 0.2056 |
| 2014 | ALL | P2 | 1780 | 890 | -2.4135 | -2.4422 | -2.3854 | 0.0207 | 0.0076 | 0.0344 | 0.6736 | 0.1388 | 0.2056 |
| 2014 | ALL | always_reference | 1780 | 890 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4657 | 0.1388 | 0.2056 |
| 2014 | ALL | always_variant | 1780 | 890 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5343 | 0.1388 | 0.2056 |
| 2014 | ALL | local_eb | 1780 | 890 | -2.4295 | -2.4584 | -2.3994 | 0.0084 | -0.0082 | 0.0267 | 0.6697 | 0.1388 | 0.2056 |
| 2014 | ALL | local_eb+cal | 1780 | 890 | n/a | n/a | n/a | 0.0105 | -0.0052 | 0.0279 | n/a | 0.1388 | 0.2056 |
| 2014 | ALL | text_lr | 1780 | 890 | n/a | n/a | n/a | -0.0174 | -0.0375 | 0.0013 | 0.6579 | 0.1388 | 0.2056 |
| 2014 | ALL | text_lr+cal | 1780 | 890 | n/a | n/a | n/a | -0.0123 | -0.0304 | 0.0044 | n/a | 0.1388 | 0.2056 |
| 2014 | both | GBM | 592 | 296 | -2.3812 | -2.4247 | -2.3400 | 0.0065 | -0.0246 | 0.0347 | 0.5726 | 0.1419 | 0.1689 |
| 2014 | both | GBM+cal | 592 | 296 | n/a | n/a | n/a | 0.0064 | -0.0287 | 0.0395 | n/a | 0.1419 | 0.1689 |
| 2014 | both | P0 | 592 | 296 | -2.3783 | -2.4287 | -2.3326 | 0.0000 | 0.0000 | 0.0000 | 0.5828 | 0.1419 | 0.1689 |
| 2014 | both | P1 | 592 | 296 | -2.3760 | -2.4216 | -2.3317 | 0.0251 | 0.0061 | 0.0433 | 0.5828 | 0.1419 | 0.1689 |
| 2014 | both | P2 | 592 | 296 | -2.3762 | -2.4225 | -2.3320 | 0.0241 | 0.0046 | 0.0424 | 0.5828 | 0.1419 | 0.1689 |
| 2014 | both | always_reference | 592 | 296 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4172 | 0.1419 | 0.1689 |
| 2014 | both | always_variant | 592 | 296 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5828 | 0.1419 | 0.1689 |
| 2014 | both | local_eb | 592 | 296 | -2.3874 | -2.4342 | -2.3446 | 0.0036 | -0.0246 | 0.0279 | 0.5709 | 0.1419 | 0.1689 |
| 2014 | both | local_eb+cal | 592 | 296 | n/a | n/a | n/a | 0.0062 | -0.0214 | 0.0300 | n/a | 0.1419 | 0.1689 |
| 2014 | both | text_lr | 592 | 296 | n/a | n/a | n/a | -0.0164 | -0.0445 | 0.0087 | 0.5574 | 0.1419 | 0.1689 |
| 2014 | both | text_lr+cal | 592 | 296 | n/a | n/a | n/a | -0.0135 | -0.0401 | 0.0091 | n/a | 0.1419 | 0.1689 |
| 2014 | headline_only | GBM | 612 | 306 | -2.6637 | -2.7271 | -2.6053 | 0.0158 | -0.0164 | 0.0474 | 0.7222 | 0.1373 | 0.3971 |
| 2014 | headline_only | GBM+cal | 612 | 306 | n/a | n/a | n/a | 0.0079 | -0.0318 | 0.0521 | n/a | 0.1373 | 0.3971 |
| 2014 | headline_only | P0 | 612 | 306 | -2.6254 | -2.6661 | -2.5868 | 0.0000 | 0.0000 | 0.0000 | 0.7222 | 0.1373 | 0.3971 |
| 2014 | headline_only | P1 | 612 | 306 | -2.6229 | -2.6634 | -2.5821 | 0.0219 | 0.0002 | 0.0433 | 0.7222 | 0.1373 | 0.3971 |
| 2014 | headline_only | P2 | 612 | 306 | -2.6229 | -2.6634 | -2.5821 | 0.0219 | 0.0002 | 0.0433 | 0.7222 | 0.1373 | 0.3971 |
| 2014 | headline_only | always_reference | 612 | 306 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2778 | 0.1373 | 0.3971 |
| 2014 | headline_only | always_variant | 612 | 306 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7222 | 0.1373 | 0.3971 |
| 2014 | headline_only | local_eb | 612 | 306 | -2.6476 | -2.6950 | -2.6064 | 0.0134 | -0.0124 | 0.0369 | 0.7222 | 0.1373 | 0.3971 |
| 2014 | headline_only | local_eb+cal | 612 | 306 | n/a | n/a | n/a | 0.0156 | -0.0090 | 0.0397 | n/a | 0.1373 | 0.3971 |
| 2014 | headline_only | text_lr | 612 | 306 | n/a | n/a | n/a | -0.0186 | -0.0484 | 0.0109 | 0.7206 | 0.1373 | 0.3971 |
| 2014 | headline_only | text_lr+cal | 612 | 306 | n/a | n/a | n/a | -0.0104 | -0.0369 | 0.0156 | n/a | 0.1373 | 0.3971 |
| 2014 | image_only | GBM | 576 | 288 | -2.2795 | -2.3145 | -2.2463 | -0.0762 | -0.1637 | -0.0254 | 0.7153 | 0.1372 | 0.0399 |
| 2014 | image_only | GBM+cal | 576 | 288 | n/a | n/a | n/a | -0.0207 | -0.0570 | 0.0036 | n/a | 0.1372 | 0.0399 |
| 2014 | image_only | P0 | 576 | 288 | -2.2559 | -2.3152 | -2.1988 | 0.0000 | 0.0000 | 0.0000 | 0.7153 | 0.1372 | 0.0399 |
| 2014 | image_only | P1 | 576 | 288 | -2.2292 | -2.2848 | -2.1774 | 0.0002 | -0.0077 | 0.0083 | 0.7153 | 0.1372 | 0.0399 |
| 2014 | image_only | P2 | 576 | 288 | -2.2292 | -2.2848 | -2.1774 | 0.0002 | -0.0077 | 0.0083 | 0.7153 | 0.1372 | 0.0399 |
| 2014 | image_only | always_reference | 576 | 288 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7153 | 0.1372 | 0.0399 |
| 2014 | image_only | always_variant | 576 | 288 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2847 | 0.1372 | 0.0399 |
| 2014 | image_only | local_eb | 576 | 288 | -2.2411 | -2.2961 | -2.1889 | -0.0068 | -0.0236 | 0.0082 | 0.7153 | 0.1372 | 0.0399 |
| 2014 | image_only | local_eb+cal | 576 | 288 | n/a | n/a | n/a | -0.0072 | -0.0242 | 0.0078 | n/a | 0.1372 | 0.0399 |
| 2014 | image_only | text_lr | 576 | 288 | n/a | n/a | n/a | -0.0132 | -0.0245 | -0.0047 | 0.6944 | 0.1372 | 0.0399 |
| 2014 | image_only | text_lr+cal | 576 | 288 | n/a | n/a | n/a | -0.0201 | -0.0439 | -0.0053 | n/a | 0.1372 | 0.0399 |
| 2015 | ALL | GBM | 434 | 217 | -2.4796 | -2.5550 | -2.4115 | 0.0445 | 0.0067 | 0.0807 | 0.6728 | 0.1682 | 0.1797 |
| 2015 | ALL | GBM+cal | 434 | 217 | n/a | n/a | n/a | 0.0422 | -0.0006 | 0.0847 | n/a | 0.1682 | 0.1797 |
| 2015 | ALL | P0 | 434 | 217 | -2.4723 | -2.5425 | -2.4010 | 0.0000 | 0.0000 | 0.0000 | 0.6728 | 0.1682 | 0.1797 |
| 2015 | ALL | P1 | 434 | 217 | -2.4514 | -2.5205 | -2.3819 | 0.0236 | -0.0049 | 0.0525 | 0.6728 | 0.1682 | 0.1797 |
| 2015 | ALL | P2 | 434 | 217 | -2.4511 | -2.5208 | -2.3819 | 0.0235 | -0.0051 | 0.0524 | 0.6728 | 0.1682 | 0.1797 |
| 2015 | ALL | always_reference | 434 | 217 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4931 | 0.1682 | 0.1797 |
| 2015 | ALL | always_variant | 434 | 217 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5069 | 0.1682 | 0.1797 |
| 2015 | ALL | local_eb | 434 | 217 | -2.4633 | -2.5370 | -2.3888 | 0.0351 | 0.0015 | 0.0663 | 0.6774 | 0.1682 | 0.1797 |
| 2015 | ALL | local_eb+cal | 434 | 217 | n/a | n/a | n/a | 0.0411 | 0.0087 | 0.0720 | n/a | 0.1682 | 0.1797 |
| 2015 | ALL | text_lr | 434 | 217 | n/a | n/a | n/a | -0.0237 | -0.0577 | 0.0092 | 0.6429 | 0.1682 | 0.1797 |
| 2015 | ALL | text_lr+cal | 434 | 217 | n/a | n/a | n/a | -0.0104 | -0.0417 | 0.0195 | n/a | 0.1682 | 0.1797 |
| 2015 | both | GBM | 136 | 68 | -2.4362 | -2.5403 | -2.3504 | 0.0373 | -0.0136 | 0.0834 | 0.5882 | 0.1912 | 0.1985 |
| 2015 | both | GBM+cal | 136 | 68 | n/a | n/a | n/a | 0.0352 | -0.0201 | 0.0911 | n/a | 0.1912 | 0.1985 |
| 2015 | both | P0 | 136 | 68 | -2.4581 | -2.5878 | -2.3495 | 0.0000 | 0.0000 | 0.0000 | 0.5809 | 0.1912 | 0.1985 |
| 2015 | both | P1 | 136 | 68 | -2.4395 | -2.5496 | -2.3445 | 0.0307 | -0.0085 | 0.0724 | 0.5809 | 0.1912 | 0.1985 |
| 2015 | both | P2 | 136 | 68 | -2.4395 | -2.5496 | -2.3445 | 0.0307 | -0.0085 | 0.0724 | 0.5809 | 0.1912 | 0.1985 |
| 2015 | both | always_reference | 136 | 68 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4191 | 0.1912 | 0.1985 |
| 2015 | both | always_variant | 136 | 68 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5809 | 0.1912 | 0.1985 |
| 2015 | both | local_eb | 136 | 68 | -2.4726 | -2.6057 | -2.3638 | 0.0461 | -0.0069 | 0.0993 | 0.5956 | 0.1912 | 0.1985 |
| 2015 | both | local_eb+cal | 136 | 68 | n/a | n/a | n/a | 0.0442 | -0.0053 | 0.0938 | n/a | 0.1912 | 0.1985 |
| 2015 | both | text_lr | 136 | 68 | n/a | n/a | n/a | 0.0061 | -0.0327 | 0.0486 | 0.5147 | 0.1912 | 0.1985 |
| 2015 | both | text_lr+cal | 136 | 68 | n/a | n/a | n/a | 0.0098 | -0.0260 | 0.0473 | n/a | 0.1912 | 0.1985 |
| 2015 | headline_only | GBM | 144 | 72 | -2.7416 | -2.9162 | -2.5847 | 0.0717 | 0.0126 | 0.1348 | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | GBM+cal | 144 | 72 | n/a | n/a | n/a | 0.0597 | -0.0066 | 0.1254 | n/a | 0.1319 | 0.3125 |
| 2015 | headline_only | P0 | 144 | 72 | -2.7057 | -2.8270 | -2.5917 | 0.0000 | 0.0000 | 0.0000 | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | P1 | 144 | 72 | -2.6965 | -2.8154 | -2.5851 | 0.0246 | -0.0162 | 0.0686 | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | P2 | 144 | 72 | -2.6965 | -2.8154 | -2.5851 | 0.0246 | -0.0162 | 0.0686 | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | always_reference | 144 | 72 | n/a | n/a | n/a | n/a | n/a | n/a | 0.3056 | 0.1319 | 0.3125 |
| 2015 | headline_only | always_variant | 144 | 72 | n/a | n/a | n/a | n/a | n/a | n/a | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | local_eb | 144 | 72 | -2.7063 | -2.8267 | -2.6040 | 0.0369 | -0.0037 | 0.0831 | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | local_eb+cal | 144 | 72 | n/a | n/a | n/a | 0.0493 | 0.0038 | 0.0976 | n/a | 0.1319 | 0.3125 |
| 2015 | headline_only | text_lr | 144 | 72 | n/a | n/a | n/a | -0.0463 | -0.1029 | 0.0110 | 0.6944 | 0.1319 | 0.3125 |
| 2015 | headline_only | text_lr+cal | 144 | 72 | n/a | n/a | n/a | -0.0237 | -0.0742 | 0.0270 | n/a | 0.1319 | 0.3125 |
| 2015 | image_only | GBM | 154 | 77 | -2.2729 | -2.3510 | -2.1982 | -0.0799 | -0.3959 | -0.0050 | 0.7273 | 0.1818 | 0.0390 |
| 2015 | image_only | GBM+cal | 154 | 77 | n/a | n/a | n/a | -0.0294 | -0.1397 | -0.0027 | n/a | 0.1818 | 0.0390 |
| 2015 | image_only | P0 | 154 | 77 | -2.2665 | -2.4057 | -2.1440 | 0.0000 | 0.0000 | 0.0000 | 0.7338 | 0.1818 | 0.0390 |
| 2015 | image_only | P1 | 154 | 77 | -2.2327 | -2.3729 | -2.1128 | -0.0085 | -0.0153 | 0.0125 | 0.7338 | 0.1818 | 0.0390 |
| 2015 | image_only | P2 | 154 | 77 | -2.2317 | -2.3703 | -2.1129 | -0.0099 | -0.0163 | 0.0098 | 0.7338 | 0.1818 | 0.0390 |
| 2015 | image_only | always_reference | 154 | 77 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7338 | 0.1818 | 0.0390 |
| 2015 | image_only | always_variant | 154 | 77 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2662 | 0.1818 | 0.0390 |
| 2015 | image_only | local_eb | 154 | 77 | -2.2279 | -2.3706 | -2.1021 | -0.0161 | -0.0390 | 0.0085 | 0.7338 | 0.1818 | 0.0390 |
| 2015 | image_only | local_eb+cal | 154 | 77 | n/a | n/a | n/a | -0.0160 | -0.0448 | 0.0075 | n/a | 0.1818 | 0.0390 |
| 2015 | image_only | text_lr | 154 | 77 | n/a | n/a | n/a | -0.0097 | -0.0310 | -0.0010 | 0.7078 | 0.1818 | 0.0390 |
| 2015 | image_only | text_lr+cal | 154 | 77 | n/a | n/a | n/a | -0.0119 | -0.0674 | 0.0042 | n/a | 0.1818 | 0.0390 |

## Coverage of the intervals for y (primary rung)

| cell | n | coverage_80 | coverage_90 |
|---|---|---|---|
| ALL | 3576 | 0.7984 | 0.8954 |
| both | 1216 | 0.8035 | 0.9005 |
| headline_only | 1216 | 0.8059 | 0.8980 |
| image_only | 1144 | 0.7850 | 0.8872 |

## Coverage by realized over planned standard error

Rows grouped in deciles of the ratio of the realized to the planned standard error (an evaluation-time stratifier: the realized standard error is never a forecast input). The forecaster fixes the click-through level at the cell median, so the ratio varies with the realized level; `coverage_80` and `coverage_90` should be near 0.80 and 0.90 in every decile. A rung that is not in range here is not calibrated within strata, whatever its pooled coverage.

| rung | decile | ratio_lo | ratio_hi | n | mean_ratio | coverage_80 | coverage_90 | event_rate | mean_p_sig |
|---|---|---|---|---|---|---|---|---|---|
| GBM | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | 0.8157 | 0.9044 | 0.2036 | 0.2259 |
| GBM+cal | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | n/a | n/a | 0.2036 | 0.2143 |
| P0 | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | 0.7931 | 0.8949 | 0.2036 | 0.2135 |
| P1 | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | 0.7984 | 0.8957 | 0.2036 | 0.2091 |
| P2 | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | 0.7984 | 0.8954 | 0.2036 | 0.2090 |
| always_reference | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | n/a | n/a | 0.2036 | n/a |
| always_variant | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | n/a | n/a | 0.2036 | n/a |
| local_eb | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | 0.7970 | 0.8921 | 0.2036 | 0.2144 |
| local_eb+cal | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | n/a | n/a | 0.2036 | 0.2111 |
| text_lr | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | n/a | n/a | 0.2036 | 0.2106 |
| text_lr+cal | 1 | 1.0000 | 1.0000 | 3576 | 1.0000 | n/a | n/a | 0.2036 | 0.2123 |

## Calibration by precision

Rows grouped in deciles of the planned exposures per arm (fewer groups when exposures tie). A forecaster that is calibrated overall but not within these groups is not calibrated. `mean_p_sig` should match `event_rate`, and `coverage_90` should be near 0.90, in every group.

| rung | decile | exposure_lo | exposure_hi | n | mean_s_star | mean_p_sig | event_rate | coverage_90 |
|---|---|---|---|---|---|---|---|---|
| GBM | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2313 | 0.2067 | 0.8911 |
| GBM | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2212 | 0.1961 | 0.9076 |
| GBM | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2261 | 0.2151 | 0.9106 |
| GBM | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2315 | 0.2360 | 0.8933 |
| GBM | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2185 | 0.1811 | 0.9276 |
| GBM | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2242 | 0.2011 | 0.8743 |
| GBM | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2254 | 0.2045 | 0.9048 |
| GBM | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2273 | 0.1821 | 0.8964 |
| GBM | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2285 | 0.2095 | 0.9134 |
| GBM | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2251 | 0.2039 | 0.9246 |
| GBM+cal | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2218 | 0.2067 | n/a |
| GBM+cal | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2099 | 0.1961 | n/a |
| GBM+cal | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2141 | 0.2151 | n/a |
| GBM+cal | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2211 | 0.2360 | n/a |
| GBM+cal | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2056 | 0.1811 | n/a |
| GBM+cal | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2122 | 0.2011 | n/a |
| GBM+cal | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2139 | 0.2045 | n/a |
| GBM+cal | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2147 | 0.1821 | n/a |
| GBM+cal | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2174 | 0.2095 | n/a |
| GBM+cal | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2122 | 0.2039 | n/a |
| P0 | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2128 | 0.2067 | 0.8827 |
| P0 | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2011 | 0.1961 | 0.8880 |
| P0 | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2079 | 0.2151 | 0.8799 |
| P0 | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2288 | 0.2360 | 0.8961 |
| P0 | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2090 | 0.1811 | 0.9192 |
| P0 | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2148 | 0.2011 | 0.8799 |
| P0 | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2028 | 0.2045 | 0.8768 |
| P0 | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2243 | 0.1821 | 0.9076 |
| P0 | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2158 | 0.2095 | 0.9022 |
| P0 | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2178 | 0.2039 | 0.9162 |
| P1 | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2106 | 0.2067 | 0.8799 |
| P1 | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.1970 | 0.1961 | 0.8908 |
| P1 | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.1999 | 0.2151 | 0.8715 |
| P1 | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2209 | 0.2360 | 0.9017 |
| P1 | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2064 | 0.1811 | 0.9164 |
| P1 | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2102 | 0.2011 | 0.8743 |
| P1 | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2007 | 0.2045 | 0.8852 |
| P1 | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2169 | 0.1821 | 0.9020 |
| P1 | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2132 | 0.2095 | 0.9106 |
| P1 | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2155 | 0.2039 | 0.9246 |
| P2 | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2103 | 0.2067 | 0.8799 |
| P2 | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.1970 | 0.1961 | 0.8908 |
| P2 | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.1998 | 0.2151 | 0.8687 |
| P2 | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2207 | 0.2360 | 0.9017 |
| P2 | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2063 | 0.1811 | 0.9164 |
| P2 | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2102 | 0.2011 | 0.8743 |
| P2 | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2004 | 0.2045 | 0.8852 |
| P2 | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2167 | 0.1821 | 0.9020 |
| P2 | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2131 | 0.2095 | 0.9106 |
| P2 | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2154 | 0.2039 | 0.9246 |
| always_reference | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | n/a | 0.2067 | n/a |
| always_reference | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | n/a | 0.1961 | n/a |
| always_reference | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | n/a | 0.2151 | n/a |
| always_reference | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | n/a | 0.2360 | n/a |
| always_reference | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | n/a | 0.1811 | n/a |
| always_reference | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | n/a | 0.2011 | n/a |
| always_reference | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | n/a | 0.2045 | n/a |
| always_reference | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | n/a | 0.1821 | n/a |
| always_reference | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | n/a | 0.2095 | n/a |
| always_reference | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | n/a | 0.2039 | n/a |
| always_variant | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | n/a | 0.2067 | n/a |
| always_variant | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | n/a | 0.1961 | n/a |
| always_variant | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | n/a | 0.2151 | n/a |
| always_variant | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | n/a | 0.2360 | n/a |
| always_variant | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | n/a | 0.1811 | n/a |
| always_variant | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | n/a | 0.2011 | n/a |
| always_variant | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | n/a | 0.2045 | n/a |
| always_variant | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | n/a | 0.1821 | n/a |
| always_variant | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | n/a | 0.2095 | n/a |
| always_variant | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | n/a | 0.2039 | n/a |
| local_eb | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2158 | 0.2067 | 0.8715 |
| local_eb | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2032 | 0.1961 | 0.8852 |
| local_eb | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2048 | 0.2151 | 0.8827 |
| local_eb | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2287 | 0.2360 | 0.8848 |
| local_eb | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2106 | 0.1811 | 0.9136 |
| local_eb | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2176 | 0.2011 | 0.8687 |
| local_eb | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2043 | 0.2045 | 0.8739 |
| local_eb | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2228 | 0.1821 | 0.9048 |
| local_eb | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2170 | 0.2095 | 0.9078 |
| local_eb | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2193 | 0.2039 | 0.9274 |
| local_eb+cal | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2125 | 0.2067 | n/a |
| local_eb+cal | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2006 | 0.1961 | n/a |
| local_eb+cal | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2027 | 0.2151 | n/a |
| local_eb+cal | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2247 | 0.2360 | n/a |
| local_eb+cal | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2076 | 0.1811 | n/a |
| local_eb+cal | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2140 | 0.2011 | n/a |
| local_eb+cal | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2008 | 0.2045 | n/a |
| local_eb+cal | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2193 | 0.1821 | n/a |
| local_eb+cal | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2136 | 0.2095 | n/a |
| local_eb+cal | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2154 | 0.2039 | n/a |
| text_lr | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2106 | 0.2067 | n/a |
| text_lr | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2088 | 0.1961 | n/a |
| text_lr | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2064 | 0.2151 | n/a |
| text_lr | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2240 | 0.2360 | n/a |
| text_lr | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2011 | 0.1811 | n/a |
| text_lr | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2107 | 0.2011 | n/a |
| text_lr | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2011 | 0.2045 | n/a |
| text_lr | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2224 | 0.1821 | n/a |
| text_lr | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2149 | 0.2095 | n/a |
| text_lr | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2061 | 0.2039 | n/a |
| text_lr+cal | 1 | 2001.0000 | 6125.0000 | 358 | 1.5376 | 0.2123 | 0.2067 | n/a |
| text_lr+cal | 2 | 6162.0000 | 10056.0000 | 357 | 1.5695 | 0.2101 | 0.1961 | n/a |
| text_lr+cal | 3 | 10074.0000 | 13665.0000 | 358 | 1.5651 | 0.2092 | 0.2151 | n/a |
| text_lr+cal | 4 | 13666.0000 | 17608.0000 | 356 | 1.5749 | 0.2246 | 0.2360 | n/a |
| text_lr+cal | 5 | 17647.0000 | 21424.0000 | 359 | 1.5456 | 0.2044 | 0.1811 | n/a |
| text_lr+cal | 6 | 21434.0000 | 25534.0000 | 358 | 1.5597 | 0.2122 | 0.2011 | n/a |
| text_lr+cal | 7 | 25544.0000 | 29217.0000 | 357 | 1.5437 | 0.2040 | 0.2045 | n/a |
| text_lr+cal | 8 | 29225.0000 | 32807.0000 | 357 | 1.5534 | 0.2228 | 0.1821 | n/a |
| text_lr+cal | 9 | 32811.0000 | 36505.0000 | 358 | 1.5392 | 0.2161 | 0.2095 | n/a |
| text_lr+cal | 10 | 36506.0000 | 39984.0000 | 358 | 1.5361 | 0.2078 | 0.2039 | n/a |

## Reliability bins of p_sig

| rung | bin | lo | hi | n | mean_p | freq |
|---|---|---|---|---|---|---|
| GBM | 0 | 0.0000 | 0.1000 | 718 | 0.0756 | 0.0390 |
| GBM | 1 | 0.1000 | 0.2000 | 1107 | 0.1463 | 0.1003 |
| GBM | 2 | 0.2000 | 0.3000 | 785 | 0.2474 | 0.2280 |
| GBM | 3 | 0.3000 | 0.4000 | 504 | 0.3470 | 0.3829 |
| GBM | 4 | 0.4000 | 0.5000 | 317 | 0.4464 | 0.4227 |
| GBM | 5 | 0.5000 | 0.6000 | 124 | 0.5424 | 0.5645 |
| GBM | 6 | 0.6000 | 0.7000 | 17 | 0.6416 | 0.5882 |
| GBM | 7 | 0.7000 | 0.8000 | 4 | 0.7168 | 0.7500 |
| GBM | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| GBM | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| GBM+cal | 0 | 0.0000 | 0.1000 | 1112 | 0.0592 | 0.0486 |
| GBM+cal | 1 | 0.1000 | 0.2000 | 894 | 0.1464 | 0.1398 |
| GBM+cal | 2 | 0.2000 | 0.3000 | 637 | 0.2464 | 0.2323 |
| GBM+cal | 3 | 0.3000 | 0.4000 | 392 | 0.3489 | 0.3801 |
| GBM+cal | 4 | 0.4000 | 0.5000 | 272 | 0.4446 | 0.4081 |
| GBM+cal | 5 | 0.5000 | 0.6000 | 182 | 0.5388 | 0.5000 |
| GBM+cal | 6 | 0.6000 | 0.7000 | 73 | 0.6373 | 0.5753 |
| GBM+cal | 7 | 0.7000 | 0.8000 | 12 | 0.7323 | 0.6667 |
| GBM+cal | 8 | 0.8000 | 0.9000 | 2 | 0.8139 | 0.0000 |
| GBM+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P0 | 0 | 0.0000 | 0.1000 | 1144 | 0.0369 | 0.0367 |
| P0 | 1 | 0.1000 | 0.2000 | 1216 | 0.1846 | 0.1793 |
| P0 | 2 | 0.2000 | 0.3000 | 0 | n/a | n/a |
| P0 | 3 | 0.3000 | 0.4000 | 144 | 0.3978 | 0.4444 |
| P0 | 4 | 0.4000 | 0.5000 | 1072 | 0.4101 | 0.3769 |
| P0 | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| P0 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P0 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P0 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P0 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P1 | 0 | 0.0000 | 0.1000 | 1181 | 0.0415 | 0.0381 |
| P1 | 1 | 0.1000 | 0.2000 | 762 | 0.1556 | 0.1509 |
| P1 | 2 | 0.2000 | 0.3000 | 534 | 0.2432 | 0.2228 |
| P1 | 3 | 0.3000 | 0.4000 | 514 | 0.3556 | 0.3735 |
| P1 | 4 | 0.4000 | 0.5000 | 495 | 0.4441 | 0.4222 |
| P1 | 5 | 0.5000 | 0.6000 | 90 | 0.5316 | 0.5333 |
| P1 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P1 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P1 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P1 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P2 | 0 | 0.0000 | 0.1000 | 1183 | 0.0416 | 0.0380 |
| P2 | 1 | 0.1000 | 0.2000 | 766 | 0.1556 | 0.1527 |
| P2 | 2 | 0.2000 | 0.3000 | 528 | 0.2433 | 0.2216 |
| P2 | 3 | 0.3000 | 0.4000 | 514 | 0.3555 | 0.3735 |
| P2 | 4 | 0.4000 | 0.5000 | 495 | 0.4441 | 0.4222 |
| P2 | 5 | 0.5000 | 0.6000 | 90 | 0.5316 | 0.5333 |
| P2 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P2 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P2 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P2 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| local_eb | 0 | 0.0000 | 0.1000 | 1243 | 0.0424 | 0.0426 |
| local_eb | 1 | 0.1000 | 0.2000 | 691 | 0.1512 | 0.1635 |
| local_eb | 2 | 0.2000 | 0.3000 | 503 | 0.2488 | 0.2207 |
| local_eb | 3 | 0.3000 | 0.4000 | 473 | 0.3516 | 0.3404 |
| local_eb | 4 | 0.4000 | 0.5000 | 470 | 0.4472 | 0.3957 |
| local_eb | 5 | 0.5000 | 0.6000 | 170 | 0.5373 | 0.5294 |
| local_eb | 6 | 0.6000 | 0.7000 | 24 | 0.6303 | 0.5833 |
| local_eb | 7 | 0.7000 | 0.8000 | 2 | 0.7412 | 0.0000 |
| local_eb | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| local_eb | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| local_eb+cal | 0 | 0.0000 | 0.1000 | 1202 | 0.0435 | 0.0399 |
| local_eb+cal | 1 | 0.1000 | 0.2000 | 735 | 0.1501 | 0.1605 |
| local_eb+cal | 2 | 0.2000 | 0.3000 | 528 | 0.2478 | 0.2311 |
| local_eb+cal | 3 | 0.3000 | 0.4000 | 498 | 0.3513 | 0.3434 |
| local_eb+cal | 4 | 0.4000 | 0.5000 | 470 | 0.4434 | 0.4043 |
| local_eb+cal | 5 | 0.5000 | 0.6000 | 125 | 0.5335 | 0.5680 |
| local_eb+cal | 6 | 0.6000 | 0.7000 | 17 | 0.6280 | 0.4706 |
| local_eb+cal | 7 | 0.7000 | 0.8000 | 1 | 0.7662 | 0.0000 |
| local_eb+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| local_eb+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| text_lr | 0 | 0.0000 | 0.1000 | 1262 | 0.0438 | 0.0531 |
| text_lr | 1 | 0.1000 | 0.2000 | 753 | 0.1487 | 0.1580 |
| text_lr | 2 | 0.2000 | 0.3000 | 499 | 0.2513 | 0.2365 |
| text_lr | 3 | 0.3000 | 0.4000 | 441 | 0.3520 | 0.3900 |
| text_lr | 4 | 0.4000 | 0.5000 | 390 | 0.4447 | 0.4051 |
| text_lr | 5 | 0.5000 | 0.6000 | 167 | 0.5414 | 0.4012 |
| text_lr | 6 | 0.6000 | 0.7000 | 57 | 0.6357 | 0.4211 |
| text_lr | 7 | 0.7000 | 0.8000 | 7 | 0.7253 | 0.4286 |
| text_lr | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| text_lr | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| text_lr+cal | 0 | 0.0000 | 0.1000 | 1143 | 0.0524 | 0.0446 |
| text_lr+cal | 1 | 0.1000 | 0.2000 | 799 | 0.1515 | 0.1564 |
| text_lr+cal | 2 | 0.2000 | 0.3000 | 580 | 0.2498 | 0.2224 |
| text_lr+cal | 3 | 0.3000 | 0.4000 | 540 | 0.3515 | 0.4130 |
| text_lr+cal | 4 | 0.4000 | 0.5000 | 371 | 0.4421 | 0.3774 |
| text_lr+cal | 5 | 0.5000 | 0.6000 | 122 | 0.5420 | 0.4262 |
| text_lr+cal | 6 | 0.6000 | 0.7000 | 19 | 0.6317 | 0.3158 |
| text_lr+cal | 7 | 0.7000 | 0.8000 | 2 | 0.7144 | 1.0000 |
| text_lr+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| text_lr+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |

## Split-half check of the prior

P1 fit on odd tests and on even tests; the gap in the cell mean and spread.

| cell | mu_odd | mu_even | mu_gap | tau_odd | tau_even | tau_gap | n_odd | n_even |
|---|---|---|---|---|---|---|---|---|
| both | 0.5552 | 0.5699 | 0.0147 | 2.1555 | 2.0040 | 0.1515 | 616 | 562 |
| headline_only | 2.2388 | 2.0016 | 0.2372 | 2.9080 | 2.9356 | 0.0275 | 566 | 626 |
| image_only | -1.0243 | -1.1212 | 0.0969 | 1.5514 | 1.3454 | 0.2059 | 562 | 558 |

## Decision value

Reported separately from calibration and never combined with it. Each origin picks K tests (10, 25 and 50 percent of the period's tests, rounded, at least one) at random, by p_win, or by an oracle that knows y. Captured is the lift won in the units of y, the fraction is of the period's total positive observed lift, and regret is the oracle's capture minus the policy's. Random order captures K over n of the total by linearity, so it is exact, not a draw. A rung whose p_win is constant within a cell chooses by cell and then at random; its capture differs from random order only through between-cell differences. Intervals resample whole tests within each origin. The adjusted bounds are Bonferroni bounds for the family of rungs compared with random order in the pooled rows (family_size, the decision-value call of docs/method.md). diff_matched is the difference from random order matched to the arm-count composition of the chosen set, the baseline a rung must beat (the number of contrasts is known before launch).

| origin | policy | rung | budget | K | n_tests | total | captured | captured_fraction | captured_fraction_lo | captured_fraction_hi | captured_fraction_adjusted_lo | captured_fraction_adjusted_hi | regret | regret_lo | regret_hi | regret_adjusted_lo | regret_adjusted_hi | random_fraction | diff_random | diff_random_lo | diff_random_hi | diff_random_adjusted_lo | diff_random_adjusted_hi | matched_fraction | diff_matched | diff_matched_lo | diff_matched_hi | diff_matched_adjusted_lo | diff_matched_adjusted_hi | family_size | constant_within_cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | random | all | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 56 | 224 | 524.6907 | 131.1727 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 189.3085 | 170.3100 | 205.9810 | 162.6917 | 215.9253 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 56 | 224 | 524.6907 | 213.8855 | 0.4076 | 0.3607 | 0.4793 | 0.3251 | 0.4902 | 106.5957 | 71.2021 | 130.5962 | 64.6349 | 148.5565 | 0.2500 | 0.1576 | 0.1107 | 0.2293 | 0.0751 | 0.2402 | 0.2500 | 0.1576 | 0.1107 | 0.2293 | 0.0751 | 0.2402 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 56 | 224 | 524.6907 | 215.7487 | 0.4112 | 0.3714 | 0.4575 | 0.3509 | 0.4715 | 104.7324 | 83.1904 | 123.2577 | 74.7612 | 134.7037 | 0.2500 | 0.1612 | 0.1214 | 0.2075 | 0.1009 | 0.2215 | 0.2500 | 0.1612 | 0.1214 | 0.2075 | 0.1009 | 0.2215 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 56 | 224 | 524.6907 | 215.7487 | 0.4112 | 0.3714 | 0.4575 | 0.3509 | 0.4715 | 104.7324 | 83.1904 | 123.2577 | 74.7612 | 134.7037 | 0.2500 | 0.1612 | 0.1214 | 0.2075 | 0.1009 | 0.2215 | 0.2500 | 0.1612 | 0.1214 | 0.2075 | 0.1009 | 0.2215 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 56 | 224 | 524.6907 | 215.7487 | 0.4112 | 0.3714 | 0.4575 | 0.3509 | 0.4715 | 104.7324 | 83.1904 | 123.2577 | 74.7612 | 134.7037 | 0.2500 | 0.1612 | 0.1214 | 0.2075 | 0.1009 | 0.2215 | 0.2500 | 0.1612 | 0.1214 | 0.2075 | 0.1009 | 0.2215 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 56 | 224 | 524.6907 | 219.8523 | 0.4190 | 0.3749 | 0.4855 | 0.3375 | 0.5005 | 100.6289 | 69.9326 | 120.4782 | 61.9543 | 139.3035 | 0.2500 | 0.1690 | 0.1249 | 0.2355 | 0.0875 | 0.2505 | 0.2500 | 0.1690 | 0.1249 | 0.2355 | 0.0875 | 0.2505 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 56 | 224 | 524.6907 | 217.6600 | 0.4148 | 0.3640 | 0.4671 | 0.3382 | 0.4914 | 102.8212 | 76.2379 | 125.5070 | 65.7483 | 139.8940 | 0.2500 | 0.1648 | 0.1140 | 0.2171 | 0.0882 | 0.2414 | 0.2500 | 0.1648 | 0.1140 | 0.2171 | 0.0882 | 0.2414 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 56 | 224 | 524.6907 | 320.4812 | 0.6108 | 0.5725 | 0.6477 | 0.5575 | 0.6641 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3608 | 0.3225 | 0.3977 | 0.3075 | 0.4141 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random | all | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 22 | 224 | 524.6907 | 51.5321 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 0.0982 | 111.6847 | 101.1440 | 120.6616 | 97.4889 | 125.8804 | 0.0982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 22 | 224 | 524.6907 | 78.6226 | 0.1498 | 0.1271 | 0.1983 | 0.0978 | 0.2019 | 84.5942 | 59.2076 | 99.2893 | 55.8670 | 113.3215 | 0.0982 | 0.0516 | 0.0289 | 0.1001 | -0.0004 | 0.1037 | 0.0982 | 0.0516 | 0.0289 | 0.1001 | -0.0004 | 0.1037 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 22 | 224 | 524.6907 | 84.7584 | 0.1615 | 0.1470 | 0.1786 | 0.1383 | 0.1848 | 78.4584 | 68.2290 | 87.0551 | 64.5048 | 92.4119 | 0.0982 | 0.0633 | 0.0488 | 0.0804 | 0.0400 | 0.0866 | 0.0982 | 0.0633 | 0.0488 | 0.0804 | 0.0400 | 0.0866 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 22 | 224 | 524.6907 | 84.7584 | 0.1615 | 0.1470 | 0.1786 | 0.1383 | 0.1848 | 78.4584 | 68.2290 | 87.0551 | 64.5048 | 92.4119 | 0.0982 | 0.0633 | 0.0488 | 0.0804 | 0.0400 | 0.0866 | 0.0982 | 0.0633 | 0.0488 | 0.0804 | 0.0400 | 0.0866 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 22 | 224 | 524.6907 | 84.7584 | 0.1615 | 0.1470 | 0.1786 | 0.1383 | 0.1848 | 78.4584 | 68.2290 | 87.0551 | 64.5048 | 92.4119 | 0.0982 | 0.0633 | 0.0488 | 0.0804 | 0.0400 | 0.0866 | 0.0982 | 0.0633 | 0.0488 | 0.0804 | 0.0400 | 0.0866 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 22 | 224 | 524.6907 | 100.5926 | 0.1917 | 0.1496 | 0.2196 | 0.1392 | 0.2442 | 62.6242 | 50.0691 | 83.0152 | 38.0114 | 87.2371 | 0.0982 | 0.0935 | 0.0514 | 0.1213 | 0.0410 | 0.1460 | 0.0982 | 0.0935 | 0.0514 | 0.1213 | 0.0410 | 0.1460 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 22 | 224 | 524.6907 | 98.0162 | 0.1868 | 0.1445 | 0.2200 | 0.1309 | 0.2427 | 65.2006 | 47.3781 | 86.7039 | 34.5999 | 95.8014 | 0.0982 | 0.0886 | 0.0462 | 0.1218 | 0.0327 | 0.1445 | 0.0982 | 0.0886 | 0.0462 | 0.1218 | 0.0327 | 0.1445 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 22 | 224 | 524.6907 | 163.2168 | 0.3111 | 0.2851 | 0.3408 | 0.2718 | 0.3503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0982 | 0.2129 | 0.1869 | 0.2426 | 0.1736 | 0.2521 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random | all | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 112 | 224 | 524.6907 | 262.3453 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2668 | 192.1027 | 226.3653 | 183.6595 | 236.8742 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 112 | 224 | 524.6907 | 389.0382 | 0.7415 | 0.6826 | 0.7792 | 0.6716 | 0.8114 | 83.5740 | 66.1282 | 111.5152 | 50.0076 | 117.1404 | 0.5000 | 0.2415 | 0.1826 | 0.2792 | 0.1716 | 0.3114 | 0.5000 | 0.2415 | 0.1826 | 0.2792 | 0.1716 | 0.3114 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 112 | 224 | 524.6907 | 379.9424 | 0.7241 | 0.6887 | 0.7634 | 0.6696 | 0.7786 | 92.6697 | 75.9197 | 109.2002 | 67.9913 | 117.3482 | 0.5000 | 0.2241 | 0.1887 | 0.2634 | 0.1696 | 0.2786 | 0.5000 | 0.2241 | 0.1887 | 0.2634 | 0.1696 | 0.2786 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 112 | 224 | 524.6907 | 379.9424 | 0.7241 | 0.6887 | 0.7634 | 0.6696 | 0.7786 | 92.6697 | 75.9197 | 109.2002 | 67.9913 | 117.3482 | 0.5000 | 0.2241 | 0.1887 | 0.2634 | 0.1696 | 0.2786 | 0.5000 | 0.2241 | 0.1887 | 0.2634 | 0.1696 | 0.2786 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 112 | 224 | 524.6907 | 379.9424 | 0.7241 | 0.6887 | 0.7634 | 0.6696 | 0.7786 | 92.6697 | 75.9197 | 109.2002 | 67.9913 | 117.3482 | 0.5000 | 0.2241 | 0.1887 | 0.2634 | 0.1696 | 0.2786 | 0.5000 | 0.2241 | 0.1887 | 0.2634 | 0.1696 | 0.2786 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 112 | 224 | 524.6907 | 397.2305 | 0.7571 | 0.7152 | 0.8003 | 0.6933 | 0.8208 | 75.3817 | 55.4496 | 94.3961 | 46.5918 | 104.1715 | 0.5000 | 0.2571 | 0.2152 | 0.3003 | 0.1933 | 0.3208 | 0.5000 | 0.2571 | 0.2152 | 0.3003 | 0.1933 | 0.3208 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 112 | 224 | 524.6907 | 397.8980 | 0.7583 | 0.7074 | 0.7948 | 0.6934 | 0.8233 | 74.7141 | 57.5878 | 98.2057 | 45.5924 | 103.8359 | 0.5000 | 0.2583 | 0.2074 | 0.2948 | 0.1934 | 0.3233 | 0.5000 | 0.2583 | 0.2074 | 0.2948 | 0.1934 | 0.3233 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 112 | 224 | 524.6907 | 472.6122 | 0.9007 | 0.8676 | 0.9296 | 0.8579 | 0.9435 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.4007 | 0.3676 | 0.4296 | 0.3579 | 0.4435 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random | all | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | arm_count | all | 0.2500 | 60 | 240 | 530.2397 | 132.5599 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 194.7757 | 177.9551 | 208.8851 | 172.0328 | 217.5186 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 60 | 240 | 530.2397 | 240.0350 | 0.4527 | 0.4043 | 0.5081 | 0.3789 | 0.5265 | 87.3006 | 63.6262 | 108.1510 | 54.5204 | 120.0809 | 0.2500 | 0.2027 | 0.1543 | 0.2581 | 0.1289 | 0.2765 | 0.2500 | 0.2027 | 0.1543 | 0.2581 | 0.1289 | 0.2765 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 60 | 240 | 530.2397 | 228.7282 | 0.4314 | 0.3917 | 0.4841 | 0.3672 | 0.4955 | 98.6074 | 76.3886 | 116.0386 | 68.2541 | 128.9607 | 0.2500 | 0.1814 | 0.1417 | 0.2341 | 0.1172 | 0.2455 | 0.2500 | 0.1814 | 0.1417 | 0.2341 | 0.1172 | 0.2455 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 60 | 240 | 530.2397 | 228.7282 | 0.4314 | 0.3917 | 0.4841 | 0.3672 | 0.4955 | 98.6074 | 76.3886 | 116.0386 | 68.2541 | 128.9607 | 0.2500 | 0.1814 | 0.1417 | 0.2341 | 0.1172 | 0.2455 | 0.2500 | 0.1814 | 0.1417 | 0.2341 | 0.1172 | 0.2455 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 60 | 240 | 530.2397 | 228.7282 | 0.4314 | 0.3917 | 0.4841 | 0.3672 | 0.4955 | 98.6074 | 76.3886 | 116.0386 | 68.2541 | 128.9607 | 0.2500 | 0.1814 | 0.1417 | 0.2341 | 0.1172 | 0.2455 | 0.2500 | 0.1814 | 0.1417 | 0.2341 | 0.1172 | 0.2455 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 60 | 240 | 530.2397 | 223.3629 | 0.4212 | 0.3750 | 0.4866 | 0.3411 | 0.5014 | 103.9727 | 74.0494 | 128.2550 | 64.9463 | 142.9991 | 0.2500 | 0.1712 | 0.1250 | 0.2366 | 0.0911 | 0.2514 | 0.2500 | 0.1712 | 0.1250 | 0.2366 | 0.0911 | 0.2514 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 60 | 240 | 530.2397 | 205.7120 | 0.3880 | 0.3492 | 0.4472 | 0.3200 | 0.4559 | 121.6236 | 93.1452 | 144.6013 | 84.2841 | 158.9631 | 0.2500 | 0.1380 | 0.0992 | 0.1972 | 0.0700 | 0.2059 | 0.2500 | 0.1380 | 0.0992 | 0.1972 | 0.0700 | 0.2059 | 6 | no |
| 2013-07-01T00:00:00+00:00 | oracle | all | 0.2500 | 60 | 240 | 530.2397 | 327.3356 | 0.6173 | 0.5796 | 0.6547 | 0.5612 | 0.6735 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3673 | 0.3296 | 0.4047 | 0.3112 | 0.4235 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random | all | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | arm_count | all | 0.1000 | 24 | 240 | 530.2397 | 53.0240 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 108.7663 | 99.3487 | 117.9560 | 94.9279 | 122.6047 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 24 | 240 | 530.2397 | 101.6614 | 0.1917 | 0.1634 | 0.2265 | 0.1453 | 0.2381 | 60.1289 | 43.0235 | 75.4420 | 36.3515 | 83.9063 | 0.1000 | 0.0917 | 0.0634 | 0.1265 | 0.0453 | 0.1381 | 0.1000 | 0.0917 | 0.0634 | 0.1265 | 0.0453 | 0.1381 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 24 | 240 | 530.2397 | 91.4913 | 0.1725 | 0.1565 | 0.1932 | 0.1468 | 0.1983 | 70.2990 | 58.3354 | 81.1998 | 54.2482 | 86.3498 | 0.1000 | 0.0725 | 0.0565 | 0.0932 | 0.0468 | 0.0983 | 0.1000 | 0.0725 | 0.0565 | 0.0932 | 0.0468 | 0.0983 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 24 | 240 | 530.2397 | 91.4913 | 0.1725 | 0.1565 | 0.1932 | 0.1468 | 0.1983 | 70.2990 | 58.3354 | 81.1998 | 54.2482 | 86.3498 | 0.1000 | 0.0725 | 0.0565 | 0.0932 | 0.0468 | 0.0983 | 0.1000 | 0.0725 | 0.0565 | 0.0932 | 0.0468 | 0.0983 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 24 | 240 | 530.2397 | 91.4913 | 0.1725 | 0.1565 | 0.1932 | 0.1468 | 0.1983 | 70.2990 | 58.3354 | 81.1998 | 54.2482 | 86.3498 | 0.1000 | 0.0725 | 0.0565 | 0.0932 | 0.0468 | 0.0983 | 0.1000 | 0.0725 | 0.0565 | 0.0932 | 0.0468 | 0.0983 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 24 | 240 | 530.2397 | 98.3933 | 0.1856 | 0.1544 | 0.2137 | 0.1409 | 0.2302 | 63.3970 | 46.5880 | 82.5070 | 36.6207 | 90.1733 | 0.1000 | 0.0856 | 0.0544 | 0.1137 | 0.0409 | 0.1302 | 0.1000 | 0.0856 | 0.0544 | 0.1137 | 0.0409 | 0.1302 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 24 | 240 | 530.2397 | 105.0389 | 0.1981 | 0.1595 | 0.2272 | 0.1488 | 0.2474 | 56.7514 | 41.4445 | 77.4767 | 29.6289 | 83.8739 | 0.1000 | 0.0981 | 0.0595 | 0.1272 | 0.0488 | 0.1474 | 0.1000 | 0.0981 | 0.0595 | 0.1272 | 0.0488 | 0.1474 | 6 | no |
| 2013-07-01T00:00:00+00:00 | oracle | all | 0.1000 | 24 | 240 | 530.2397 | 161.7903 | 0.3051 | 0.2785 | 0.3295 | 0.2686 | 0.3417 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 | 0.2051 | 0.1785 | 0.2295 | 0.1686 | 0.2417 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random | all | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | arm_count | all | 0.5000 | 120 | 240 | 530.2397 | 265.1199 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 219.8844 | 199.6901 | 238.4410 | 191.7584 | 248.0105 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 120 | 240 | 530.2397 | 403.9392 | 0.7618 | 0.7108 | 0.8015 | 0.6977 | 0.8259 | 81.0650 | 63.7233 | 103.4781 | 51.5978 | 110.5323 | 0.5000 | 0.2618 | 0.2108 | 0.3015 | 0.1977 | 0.3259 | 0.5000 | 0.2618 | 0.2108 | 0.3015 | 0.1977 | 0.3259 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 120 | 240 | 530.2397 | 392.4822 | 0.7402 | 0.6985 | 0.7794 | 0.6815 | 0.7989 | 92.5221 | 74.2357 | 110.4144 | 65.9303 | 119.1139 | 0.5000 | 0.2402 | 0.1985 | 0.2794 | 0.1815 | 0.2989 | 0.5000 | 0.2402 | 0.1985 | 0.2794 | 0.1815 | 0.2989 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 120 | 240 | 530.2397 | 392.4822 | 0.7402 | 0.6985 | 0.7794 | 0.6815 | 0.7989 | 92.5221 | 74.2357 | 110.4144 | 65.9303 | 119.1139 | 0.5000 | 0.2402 | 0.1985 | 0.2794 | 0.1815 | 0.2989 | 0.5000 | 0.2402 | 0.1985 | 0.2794 | 0.1815 | 0.2989 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 120 | 240 | 530.2397 | 392.4822 | 0.7402 | 0.6985 | 0.7794 | 0.6815 | 0.7989 | 92.5221 | 74.2357 | 110.4144 | 65.9303 | 119.1139 | 0.5000 | 0.2402 | 0.1985 | 0.2794 | 0.1815 | 0.2989 | 0.5000 | 0.2402 | 0.1985 | 0.2794 | 0.1815 | 0.2989 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 120 | 240 | 530.2397 | 402.4332 | 0.7590 | 0.7126 | 0.8055 | 0.6913 | 0.8266 | 82.5711 | 59.8348 | 102.6063 | 50.7986 | 114.3436 | 0.5000 | 0.2590 | 0.2126 | 0.3055 | 0.1913 | 0.3266 | 0.5000 | 0.2590 | 0.2126 | 0.3055 | 0.1913 | 0.3266 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 120 | 240 | 530.2397 | 374.7358 | 0.7067 | 0.6488 | 0.7500 | 0.6307 | 0.7828 | 110.2684 | 87.2681 | 141.2018 | 70.9265 | 149.6104 | 0.5000 | 0.2067 | 0.1488 | 0.2500 | 0.1307 | 0.2828 | 0.5000 | 0.2067 | 0.1488 | 0.2500 | 0.1307 | 0.2828 | 6 | no |
| 2013-07-01T00:00:00+00:00 | oracle | all | 0.5000 | 120 | 240 | 530.2397 | 485.0043 | 0.9147 | 0.8834 | 0.9400 | 0.8737 | 0.9557 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.4147 | 0.3834 | 0.4400 | 0.3737 | 0.4557 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random | all | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | arm_count | all | 0.2500 | 54 | 217 | 587.5764 | 146.2172 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 176.9599 | 160.5652 | 191.2841 | 154.2869 | 199.6328 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 54 | 217 | 587.5764 | 255.1295 | 0.4342 | 0.3741 | 0.4734 | 0.3635 | 0.5049 | 68.0476 | 50.8668 | 99.3927 | 32.7957 | 103.2994 | 0.2488 | 0.1854 | 0.1252 | 0.2245 | 0.1147 | 0.2561 | 0.2488 | 0.1854 | 0.1252 | 0.2245 | 0.1147 | 0.2561 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 54 | 217 | 587.5764 | 233.9500 | 0.3982 | 0.3592 | 0.4397 | 0.3415 | 0.4548 | 89.2270 | 68.9666 | 107.2733 | 60.7389 | 117.7152 | 0.2488 | 0.1493 | 0.1104 | 0.1909 | 0.0926 | 0.2060 | 0.2488 | 0.1493 | 0.1104 | 0.1909 | 0.0926 | 0.2060 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 54 | 217 | 587.5764 | 233.9500 | 0.3982 | 0.3592 | 0.4397 | 0.3415 | 0.4548 | 89.2270 | 68.9666 | 107.2733 | 60.7389 | 117.7152 | 0.2488 | 0.1493 | 0.1104 | 0.1909 | 0.0926 | 0.2060 | 0.2488 | 0.1493 | 0.1104 | 0.1909 | 0.0926 | 0.2060 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 54 | 217 | 587.5764 | 233.9500 | 0.3982 | 0.3592 | 0.4397 | 0.3415 | 0.4548 | 89.2270 | 68.9666 | 107.2733 | 60.7389 | 117.7152 | 0.2488 | 0.1493 | 0.1104 | 0.1909 | 0.0926 | 0.2060 | 0.2488 | 0.1493 | 0.1104 | 0.1909 | 0.0926 | 0.2060 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 54 | 217 | 587.5764 | 219.3530 | 0.3733 | 0.3254 | 0.4279 | 0.3032 | 0.4434 | 103.8240 | 75.7561 | 128.1101 | 66.5043 | 141.1437 | 0.2488 | 0.1245 | 0.0766 | 0.1791 | 0.0544 | 0.1945 | 0.2488 | 0.1245 | 0.0766 | 0.1791 | 0.0544 | 0.1945 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 54 | 217 | 587.5764 | 223.7036 | 0.3807 | 0.3313 | 0.4315 | 0.3040 | 0.4574 | 99.4734 | 71.8908 | 127.5840 | 58.8619 | 140.0850 | 0.2488 | 0.1319 | 0.0824 | 0.1826 | 0.0552 | 0.2086 | 0.2488 | 0.1319 | 0.0824 | 0.1826 | 0.0552 | 0.2086 | 6 | no |
| 2013-10-01T00:00:00+00:00 | oracle | all | 0.2500 | 54 | 217 | 587.5764 | 323.1770 | 0.5500 | 0.5148 | 0.5847 | 0.5000 | 0.6000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2488 | 0.3012 | 0.2659 | 0.3358 | 0.2512 | 0.3512 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random | all | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | arm_count | all | 0.1000 | 22 | 217 | 587.5764 | 59.5700 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 100.5698 | 88.8918 | 111.0718 | 84.2240 | 116.9155 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 22 | 217 | 587.5764 | 107.2155 | 0.1825 | 0.1445 | 0.2157 | 0.1323 | 0.2326 | 52.9242 | 35.2410 | 72.3725 | 26.1513 | 79.6971 | 0.1014 | 0.0811 | 0.0431 | 0.1144 | 0.0309 | 0.1312 | 0.1014 | 0.0811 | 0.0431 | 0.1144 | 0.0309 | 0.1312 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 22 | 217 | 587.5764 | 95.3130 | 0.1622 | 0.1479 | 0.1776 | 0.1401 | 0.1844 | 64.8267 | 53.7986 | 75.0749 | 49.8482 | 79.8053 | 0.1014 | 0.0608 | 0.0465 | 0.0762 | 0.0387 | 0.0830 | 0.1014 | 0.0608 | 0.0465 | 0.0762 | 0.0387 | 0.0830 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 22 | 217 | 587.5764 | 95.3130 | 0.1622 | 0.1479 | 0.1776 | 0.1401 | 0.1844 | 64.8267 | 53.7986 | 75.0749 | 49.8482 | 79.8053 | 0.1014 | 0.0608 | 0.0465 | 0.0762 | 0.0387 | 0.0830 | 0.1014 | 0.0608 | 0.0465 | 0.0762 | 0.0387 | 0.0830 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 22 | 217 | 587.5764 | 95.3130 | 0.1622 | 0.1479 | 0.1776 | 0.1401 | 0.1844 | 64.8267 | 53.7986 | 75.0749 | 49.8482 | 79.8053 | 0.1014 | 0.0608 | 0.0465 | 0.0762 | 0.0387 | 0.0830 | 0.1014 | 0.0608 | 0.0465 | 0.0762 | 0.0387 | 0.0830 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 22 | 217 | 587.5764 | 109.1671 | 0.1858 | 0.1507 | 0.2189 | 0.1353 | 0.2363 | 50.9726 | 32.8473 | 67.2169 | 26.0734 | 75.8718 | 0.1014 | 0.0844 | 0.0494 | 0.1175 | 0.0339 | 0.1349 | 0.1014 | 0.0844 | 0.0494 | 0.1175 | 0.0339 | 0.1349 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 22 | 217 | 587.5764 | 105.3603 | 0.1793 | 0.1373 | 0.2096 | 0.1254 | 0.2332 | 54.7794 | 38.5833 | 75.0970 | 28.3479 | 81.2110 | 0.1014 | 0.0779 | 0.0359 | 0.1083 | 0.0240 | 0.1318 | 0.1014 | 0.0779 | 0.0359 | 0.1083 | 0.0240 | 0.1318 | 6 | no |
| 2013-10-01T00:00:00+00:00 | oracle | all | 0.1000 | 22 | 217 | 587.5764 | 160.1397 | 0.2725 | 0.2472 | 0.2946 | 0.2382 | 0.3069 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1014 | 0.1712 | 0.1458 | 0.1932 | 0.1368 | 0.2055 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random | all | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | arm_count | all | 0.5000 | 109 | 217 | 587.5764 | 295.1421 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 210.2139 | 193.1711 | 225.8239 | 186.5003 | 233.9274 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 109 | 217 | 587.5764 | 415.6499 | 0.7074 | 0.6637 | 0.7433 | 0.6473 | 0.7675 | 89.7060 | 68.2943 | 113.6247 | 57.1077 | 122.3043 | 0.5023 | 0.2051 | 0.1614 | 0.2410 | 0.1450 | 0.2652 | 0.5023 | 0.2051 | 0.1614 | 0.2410 | 0.1450 | 0.2652 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 109 | 217 | 587.5764 | 406.2192 | 0.6913 | 0.6584 | 0.7231 | 0.6429 | 0.7398 | 99.1367 | 83.5022 | 115.4065 | 75.2448 | 123.0286 | 0.5023 | 0.1890 | 0.1561 | 0.2208 | 0.1406 | 0.2375 | 0.5023 | 0.1890 | 0.1561 | 0.2208 | 0.1406 | 0.2375 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 109 | 217 | 587.5764 | 406.2192 | 0.6913 | 0.6584 | 0.7231 | 0.6429 | 0.7398 | 99.1367 | 83.5022 | 115.4065 | 75.2448 | 123.0286 | 0.5023 | 0.1890 | 0.1561 | 0.2208 | 0.1406 | 0.2375 | 0.5023 | 0.1890 | 0.1561 | 0.2208 | 0.1406 | 0.2375 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 109 | 217 | 587.5764 | 406.2192 | 0.6913 | 0.6584 | 0.7231 | 0.6429 | 0.7398 | 99.1367 | 83.5022 | 115.4065 | 75.2448 | 123.0286 | 0.5023 | 0.1890 | 0.1561 | 0.2208 | 0.1406 | 0.2375 | 0.5023 | 0.1890 | 0.1561 | 0.2208 | 0.1406 | 0.2375 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 109 | 217 | 587.5764 | 420.8268 | 0.7162 | 0.6796 | 0.7551 | 0.6611 | 0.7713 | 84.5291 | 62.2519 | 100.3449 | 56.7774 | 112.2807 | 0.5023 | 0.2139 | 0.1773 | 0.2528 | 0.1588 | 0.2690 | 0.5023 | 0.2139 | 0.1773 | 0.2528 | 0.1588 | 0.2690 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 109 | 217 | 587.5764 | 410.6866 | 0.6990 | 0.6556 | 0.7393 | 0.6376 | 0.7603 | 94.6693 | 71.5115 | 117.3413 | 62.9821 | 126.3565 | 0.5023 | 0.1966 | 0.1533 | 0.2370 | 0.1353 | 0.2580 | 0.5023 | 0.1966 | 0.1533 | 0.2370 | 0.1353 | 0.2580 | 6 | no |
| 2013-10-01T00:00:00+00:00 | oracle | all | 0.5000 | 109 | 217 | 587.5764 | 505.3559 | 0.8601 | 0.8269 | 0.8897 | 0.8145 | 0.9057 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5023 | 0.3578 | 0.3245 | 0.3874 | 0.3122 | 0.4034 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.2500 | 58 | 232 | 552.4782 | 138.1195 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 180.9882 | 164.6547 | 197.6804 | 157.1001 | 204.8763 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 58 | 232 | 552.4782 | 235.5999 | 0.4264 | 0.3864 | 0.4793 | 0.3603 | 0.4926 | 83.5079 | 59.6949 | 100.0101 | 53.8399 | 113.1758 | 0.2500 | 0.1764 | 0.1364 | 0.2293 | 0.1103 | 0.2426 | 0.2500 | 0.1764 | 0.1364 | 0.2293 | 0.1103 | 0.2426 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 58 | 232 | 552.4782 | 225.1724 | 0.4076 | 0.3688 | 0.4507 | 0.3501 | 0.4651 | 93.9353 | 74.5767 | 112.1042 | 66.9766 | 120.8939 | 0.2500 | 0.1576 | 0.1188 | 0.2007 | 0.1001 | 0.2151 | 0.2500 | 0.1576 | 0.1188 | 0.2007 | 0.1001 | 0.2151 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 58 | 232 | 552.4782 | 225.1724 | 0.4076 | 0.3688 | 0.4507 | 0.3501 | 0.4651 | 93.9353 | 74.5767 | 112.1042 | 66.9766 | 120.8939 | 0.2500 | 0.1576 | 0.1188 | 0.2007 | 0.1001 | 0.2151 | 0.2500 | 0.1576 | 0.1188 | 0.2007 | 0.1001 | 0.2151 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 58 | 232 | 552.4782 | 225.1724 | 0.4076 | 0.3688 | 0.4507 | 0.3501 | 0.4650 | 93.9353 | 74.5767 | 112.1042 | 67.0460 | 120.8245 | 0.2500 | 0.1576 | 0.1188 | 0.2007 | 0.1001 | 0.2150 | 0.2500 | 0.1576 | 0.1188 | 0.2007 | 0.1001 | 0.2150 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 58 | 232 | 552.4782 | 237.7964 | 0.4304 | 0.3885 | 0.4755 | 0.3662 | 0.4946 | 81.3113 | 58.7737 | 99.5031 | 51.6206 | 111.0021 | 0.2500 | 0.1804 | 0.1385 | 0.2255 | 0.1162 | 0.2446 | 0.2500 | 0.1804 | 0.1385 | 0.2255 | 0.1162 | 0.2446 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 58 | 232 | 552.4782 | 222.9261 | 0.4035 | 0.3558 | 0.4475 | 0.3392 | 0.4678 | 96.1817 | 72.5885 | 123.1012 | 58.9239 | 133.4394 | 0.2500 | 0.1535 | 0.1058 | 0.1975 | 0.0892 | 0.2178 | 0.2500 | 0.1535 | 0.1058 | 0.1975 | 0.0892 | 0.2178 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.2500 | 58 | 232 | 552.4782 | 319.1077 | 0.5776 | 0.5430 | 0.6117 | 0.5266 | 0.6286 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3276 | 0.2930 | 0.3617 | 0.2766 | 0.3786 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.1000 | 23 | 232 | 552.4782 | 54.7715 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 0.0991 | 104.3349 | 91.9419 | 114.5670 | 87.3406 | 121.3292 | 0.0991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 23 | 232 | 552.4782 | 112.0618 | 0.2028 | 0.1621 | 0.2393 | 0.1482 | 0.2575 | 47.0446 | 30.9023 | 66.8492 | 21.7756 | 72.3137 | 0.0991 | 0.1037 | 0.0629 | 0.1401 | 0.0490 | 0.1584 | 0.0991 | 0.1037 | 0.0629 | 0.1401 | 0.0490 | 0.1584 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 23 | 232 | 552.4782 | 89.2925 | 0.1616 | 0.1467 | 0.1794 | 0.1379 | 0.1853 | 69.8139 | 59.6025 | 79.0332 | 55.0555 | 84.5724 | 0.0991 | 0.0625 | 0.0475 | 0.0802 | 0.0388 | 0.0862 | 0.0991 | 0.0625 | 0.0475 | 0.0802 | 0.0388 | 0.0862 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 23 | 232 | 552.4782 | 89.2925 | 0.1616 | 0.1467 | 0.1794 | 0.1379 | 0.1853 | 69.8139 | 59.6025 | 79.0332 | 55.0555 | 84.5724 | 0.0991 | 0.0625 | 0.0475 | 0.0802 | 0.0388 | 0.0862 | 0.0991 | 0.0625 | 0.0475 | 0.0802 | 0.0388 | 0.0862 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 23 | 232 | 552.4782 | 89.2925 | 0.1616 | 0.1467 | 0.1794 | 0.1379 | 0.1853 | 69.8139 | 59.6025 | 79.0332 | 55.0555 | 84.5724 | 0.0991 | 0.0625 | 0.0475 | 0.0802 | 0.0388 | 0.0862 | 0.0991 | 0.0625 | 0.0475 | 0.0802 | 0.0388 | 0.0862 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 23 | 232 | 552.4782 | 110.1104 | 0.1993 | 0.1564 | 0.2288 | 0.1465 | 0.2522 | 48.9961 | 35.1394 | 69.3228 | 23.2892 | 74.7029 | 0.0991 | 0.1002 | 0.0573 | 0.1297 | 0.0473 | 0.1530 | 0.0991 | 0.1002 | 0.0573 | 0.1297 | 0.0473 | 0.1530 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 23 | 232 | 552.4782 | 103.3462 | 0.1871 | 0.1588 | 0.2217 | 0.1397 | 0.2344 | 55.7603 | 34.8522 | 72.8306 | 27.6651 | 83.8555 | 0.0991 | 0.0879 | 0.0597 | 0.1225 | 0.0406 | 0.1353 | 0.0991 | 0.0879 | 0.0597 | 0.1225 | 0.0406 | 0.1353 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.1000 | 23 | 232 | 552.4782 | 159.1065 | 0.2880 | 0.2644 | 0.3138 | 0.2506 | 0.3253 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0991 | 0.1888 | 0.1652 | 0.2146 | 0.1515 | 0.2262 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.5000 | 116 | 232 | 552.4782 | 276.2391 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 216.2423 | 199.1071 | 230.4847 | 192.7387 | 239.7459 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 116 | 232 | 552.4782 | 393.4638 | 0.7122 | 0.6670 | 0.7564 | 0.6456 | 0.7787 | 99.0176 | 76.6693 | 122.1595 | 66.1478 | 131.8873 | 0.5000 | 0.2122 | 0.1670 | 0.2564 | 0.1456 | 0.2787 | 0.5000 | 0.2122 | 0.1670 | 0.2564 | 0.1456 | 0.2787 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 116 | 232 | 552.4782 | 385.8683 | 0.6984 | 0.6618 | 0.7394 | 0.6439 | 0.7529 | 106.6131 | 88.2051 | 121.5527 | 82.9305 | 130.2957 | 0.5000 | 0.1984 | 0.1618 | 0.2394 | 0.1439 | 0.2529 | 0.5000 | 0.1984 | 0.1618 | 0.2394 | 0.1439 | 0.2529 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 116 | 232 | 552.4782 | 385.8683 | 0.6984 | 0.6618 | 0.7394 | 0.6439 | 0.7529 | 106.6131 | 88.2051 | 121.5527 | 82.9305 | 130.2957 | 0.5000 | 0.1984 | 0.1618 | 0.2394 | 0.1439 | 0.2529 | 0.5000 | 0.1984 | 0.1618 | 0.2394 | 0.1439 | 0.2529 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 116 | 232 | 552.4782 | 375.9994 | 0.6806 | 0.6360 | 0.7281 | 0.6116 | 0.7495 | 116.4819 | 92.6621 | 139.5700 | 82.0800 | 150.8838 | 0.5000 | 0.1806 | 0.1360 | 0.2281 | 0.1116 | 0.2495 | 0.5000 | 0.1806 | 0.1360 | 0.2281 | 0.1116 | 0.2495 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 116 | 232 | 552.4782 | 367.6702 | 0.6655 | 0.6173 | 0.7141 | 0.5954 | 0.7356 | 124.8112 | 99.8815 | 148.0939 | 89.4017 | 160.2207 | 0.5000 | 0.1655 | 0.1173 | 0.2141 | 0.0954 | 0.2356 | 0.5000 | 0.1655 | 0.1173 | 0.2141 | 0.0954 | 0.2356 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 116 | 232 | 552.4782 | 383.3222 | 0.6938 | 0.6501 | 0.7503 | 0.6191 | 0.7685 | 109.1591 | 82.2468 | 129.1602 | 72.8727 | 145.4456 | 0.5000 | 0.1938 | 0.1501 | 0.2503 | 0.1191 | 0.2685 | 0.5000 | 0.1938 | 0.1501 | 0.2503 | 0.1191 | 0.2685 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.5000 | 116 | 232 | 552.4782 | 492.4814 | 0.8914 | 0.8570 | 0.9243 | 0.8413 | 0.9415 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.3914 | 0.3570 | 0.4243 | 0.3413 | 0.4415 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 52 | 206 | 494.0927 | 124.7224 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 0.2524 | 189.9585 | 167.9677 | 210.7288 | 157.8959 | 222.0211 | 0.2524 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 52 | 206 | 494.0927 | 238.1854 | 0.4821 | 0.4200 | 0.5349 | 0.3976 | 0.5666 | 76.4956 | 54.4509 | 102.2919 | 41.0127 | 111.9784 | 0.2524 | 0.2296 | 0.1676 | 0.2825 | 0.1451 | 0.3141 | 0.2524 | 0.2296 | 0.1676 | 0.2825 | 0.1451 | 0.3141 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 52 | 206 | 494.0927 | 232.2454 | 0.4700 | 0.4216 | 0.5267 | 0.3924 | 0.5477 | 82.4356 | 59.6197 | 103.2643 | 50.5439 | 114.3272 | 0.2524 | 0.2176 | 0.1691 | 0.2743 | 0.1399 | 0.2953 | 0.2524 | 0.2176 | 0.1691 | 0.2743 | 0.1399 | 0.2953 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 52 | 206 | 494.0927 | 232.2454 | 0.4700 | 0.4216 | 0.5267 | 0.3924 | 0.5477 | 82.4356 | 59.6197 | 103.2643 | 50.5439 | 114.3272 | 0.2524 | 0.2176 | 0.1691 | 0.2743 | 0.1399 | 0.2953 | 0.2524 | 0.2176 | 0.1691 | 0.2743 | 0.1399 | 0.2953 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 52 | 206 | 494.0927 | 232.2454 | 0.4700 | 0.4216 | 0.5267 | 0.3924 | 0.5477 | 82.4356 | 59.6197 | 103.2643 | 50.5439 | 114.3272 | 0.2524 | 0.2176 | 0.1691 | 0.2743 | 0.1399 | 0.2953 | 0.2524 | 0.2176 | 0.1691 | 0.2743 | 0.1399 | 0.2953 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 52 | 206 | 494.0927 | 230.5651 | 0.4666 | 0.4210 | 0.5401 | 0.3815 | 0.5517 | 84.1159 | 54.2302 | 101.6083 | 49.7565 | 118.4753 | 0.2524 | 0.2142 | 0.1685 | 0.2877 | 0.1291 | 0.2993 | 0.2524 | 0.2142 | 0.1685 | 0.2877 | 0.1291 | 0.2993 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 52 | 206 | 494.0927 | 210.5852 | 0.4262 | 0.3657 | 0.4784 | 0.3403 | 0.5122 | 104.0958 | 77.5233 | 129.5848 | 65.4500 | 142.7415 | 0.2524 | 0.1738 | 0.1133 | 0.2260 | 0.0878 | 0.2597 | 0.2524 | 0.1738 | 0.1133 | 0.2260 | 0.0878 | 0.2597 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 52 | 206 | 494.0927 | 314.6810 | 0.6369 | 0.5930 | 0.6769 | 0.5756 | 0.6982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2524 | 0.3845 | 0.3406 | 0.4244 | 0.3232 | 0.4458 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 21 | 206 | 494.0927 | 50.3687 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 0.1019 | 120.6805 | 101.3328 | 135.7171 | 95.6020 | 145.7591 | 0.1019 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 21 | 206 | 494.0927 | 100.4498 | 0.2033 | 0.1555 | 0.2497 | 0.1346 | 0.2720 | 70.5994 | 47.2690 | 91.9410 | 36.5813 | 104.6176 | 0.1019 | 0.1014 | 0.0535 | 0.1478 | 0.0327 | 0.1700 | 0.1019 | 0.1014 | 0.0535 | 0.1478 | 0.0327 | 0.1700 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 21 | 206 | 494.0927 | 93.7914 | 0.1898 | 0.1702 | 0.2150 | 0.1564 | 0.2233 | 77.2578 | 59.6463 | 89.2057 | 55.9195 | 98.5961 | 0.1019 | 0.0879 | 0.0683 | 0.1130 | 0.0544 | 0.1213 | 0.1019 | 0.0879 | 0.0683 | 0.1130 | 0.0544 | 0.1213 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 21 | 206 | 494.0927 | 93.7914 | 0.1898 | 0.1702 | 0.2150 | 0.1564 | 0.2233 | 77.2578 | 59.6463 | 89.2057 | 55.9195 | 98.5961 | 0.1019 | 0.0879 | 0.0683 | 0.1130 | 0.0544 | 0.1213 | 0.1019 | 0.0879 | 0.0683 | 0.1130 | 0.0544 | 0.1213 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 21 | 206 | 494.0927 | 93.7914 | 0.1898 | 0.1702 | 0.2150 | 0.1564 | 0.2233 | 77.2578 | 59.6463 | 89.2057 | 55.9195 | 98.5961 | 0.1019 | 0.0879 | 0.0683 | 0.1130 | 0.0544 | 0.1213 | 0.1019 | 0.0879 | 0.0683 | 0.1130 | 0.0544 | 0.1213 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 21 | 206 | 494.0927 | 93.5751 | 0.1894 | 0.1479 | 0.2313 | 0.1273 | 0.2514 | 77.4741 | 52.7785 | 101.0541 | 41.9318 | 113.0165 | 0.1019 | 0.0874 | 0.0460 | 0.1294 | 0.0254 | 0.1495 | 0.1019 | 0.0874 | 0.0460 | 0.1294 | 0.0254 | 0.1495 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 21 | 206 | 494.0927 | 110.9071 | 0.2245 | 0.1678 | 0.2619 | 0.1545 | 0.2944 | 60.1421 | 43.2096 | 85.6456 | 29.8982 | 90.3859 | 0.1019 | 0.1225 | 0.0659 | 0.1599 | 0.0525 | 0.1925 | 0.1019 | 0.1225 | 0.0659 | 0.1599 | 0.0525 | 0.1925 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 21 | 206 | 494.0927 | 171.0492 | 0.3462 | 0.3092 | 0.3806 | 0.2953 | 0.3971 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1019 | 0.2442 | 0.2073 | 0.2786 | 0.1933 | 0.2952 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 103 | 206 | 494.0927 | 247.0464 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 210.2842 | 189.0110 | 230.4182 | 178.6456 | 241.9228 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 103 | 206 | 494.0927 | 369.0699 | 0.7470 | 0.6892 | 0.8015 | 0.6694 | 0.8245 | 88.2607 | 64.7915 | 112.5921 | 52.2351 | 124.2863 | 0.5000 | 0.2470 | 0.1892 | 0.3015 | 0.1694 | 0.3245 | 0.5000 | 0.2470 | 0.1892 | 0.3015 | 0.1694 | 0.3245 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 103 | 206 | 494.0927 | 375.7471 | 0.7605 | 0.7204 | 0.8010 | 0.6992 | 0.8218 | 81.5835 | 63.5458 | 97.1043 | 56.9905 | 106.1764 | 0.5000 | 0.2605 | 0.2204 | 0.3010 | 0.1992 | 0.3218 | 0.5000 | 0.2605 | 0.2204 | 0.3010 | 0.1992 | 0.3218 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 103 | 206 | 494.0927 | 375.7471 | 0.7605 | 0.7204 | 0.8010 | 0.6992 | 0.8218 | 81.5835 | 63.5458 | 97.1043 | 56.9905 | 106.1764 | 0.5000 | 0.2605 | 0.2204 | 0.3010 | 0.1992 | 0.3218 | 0.5000 | 0.2605 | 0.2204 | 0.3010 | 0.1992 | 0.3218 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 103 | 206 | 494.0927 | 375.7471 | 0.7605 | 0.7204 | 0.8010 | 0.6992 | 0.8218 | 81.5835 | 63.5458 | 97.1043 | 56.9905 | 106.1764 | 0.5000 | 0.2605 | 0.2204 | 0.3010 | 0.1992 | 0.3218 | 0.5000 | 0.2605 | 0.2204 | 0.3010 | 0.1992 | 0.3218 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 103 | 206 | 494.0927 | 373.1261 | 0.7552 | 0.7082 | 0.8087 | 0.6798 | 0.8305 | 84.2044 | 60.2843 | 105.3585 | 50.0882 | 118.3207 | 0.5000 | 0.2552 | 0.2082 | 0.3087 | 0.1798 | 0.3305 | 0.5000 | 0.2552 | 0.2082 | 0.3087 | 0.1798 | 0.3305 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 103 | 206 | 494.0927 | 368.3506 | 0.7455 | 0.7052 | 0.8016 | 0.6715 | 0.8196 | 88.9800 | 63.6604 | 108.7196 | 55.0437 | 122.9162 | 0.5000 | 0.2455 | 0.2052 | 0.3016 | 0.1715 | 0.3196 | 0.5000 | 0.2455 | 0.2052 | 0.3016 | 0.1715 | 0.3196 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 103 | 206 | 494.0927 | 457.3306 | 0.9256 | 0.8934 | 0.9555 | 0.8801 | 0.9711 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.4256 | 0.3934 | 0.4555 | 0.3801 | 0.4711 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.2500 | 56 | 225 | 544.5977 | 135.5443 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 0.2489 | 187.1124 | 169.1645 | 204.0596 | 162.0338 | 212.1910 | 0.2489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 56 | 225 | 544.5977 | 234.4871 | 0.4306 | 0.3726 | 0.4694 | 0.3609 | 0.5003 | 88.1696 | 69.5412 | 116.2481 | 54.8355 | 121.5038 | 0.2489 | 0.1817 | 0.1237 | 0.2205 | 0.1120 | 0.2514 | 0.2489 | 0.1817 | 0.1237 | 0.2205 | 0.1120 | 0.2514 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 56 | 225 | 544.5977 | 224.9955 | 0.4131 | 0.3775 | 0.4584 | 0.3534 | 0.4729 | 97.6613 | 76.2734 | 116.4776 | 68.4290 | 126.8936 | 0.2489 | 0.1643 | 0.1286 | 0.2096 | 0.1045 | 0.2240 | 0.2489 | 0.1643 | 0.1286 | 0.2096 | 0.1045 | 0.2240 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 56 | 225 | 544.5977 | 224.9955 | 0.4131 | 0.3775 | 0.4584 | 0.3534 | 0.4729 | 97.6613 | 76.2734 | 116.4776 | 68.4290 | 126.8936 | 0.2489 | 0.1643 | 0.1286 | 0.2096 | 0.1045 | 0.2240 | 0.2489 | 0.1643 | 0.1286 | 0.2096 | 0.1045 | 0.2240 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 56 | 225 | 544.5977 | 224.9955 | 0.4131 | 0.3775 | 0.4584 | 0.3534 | 0.4729 | 97.6613 | 76.2734 | 116.4776 | 68.4290 | 126.8936 | 0.2489 | 0.1643 | 0.1286 | 0.2096 | 0.1045 | 0.2240 | 0.2489 | 0.1643 | 0.1286 | 0.2096 | 0.1045 | 0.2240 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 56 | 225 | 544.5977 | 220.7326 | 0.4053 | 0.3576 | 0.4493 | 0.3378 | 0.4728 | 101.9241 | 78.8658 | 128.2811 | 65.3896 | 138.4587 | 0.2489 | 0.1564 | 0.1087 | 0.2004 | 0.0889 | 0.2240 | 0.2489 | 0.1564 | 0.1087 | 0.2004 | 0.0889 | 0.2240 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 56 | 225 | 544.5977 | 210.0750 | 0.3857 | 0.3489 | 0.4468 | 0.3127 | 0.4588 | 112.5817 | 78.8441 | 131.6043 | 73.3530 | 151.8104 | 0.2489 | 0.1369 | 0.1000 | 0.1979 | 0.0638 | 0.2099 | 0.2489 | 0.1369 | 0.1000 | 0.1979 | 0.0638 | 0.2099 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.2500 | 56 | 225 | 544.5977 | 322.6567 | 0.5925 | 0.5544 | 0.6278 | 0.5404 | 0.6445 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2489 | 0.3436 | 0.3055 | 0.3789 | 0.2915 | 0.3956 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.1000 | 23 | 225 | 544.5977 | 55.6700 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 0.1022 | 114.2377 | 101.3020 | 125.2596 | 96.5148 | 131.9607 | 0.1022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 23 | 225 | 544.5977 | 112.2150 | 0.2061 | 0.1667 | 0.2448 | 0.1481 | 0.2640 | 57.6927 | 38.6803 | 74.6395 | 31.0267 | 84.3587 | 0.1022 | 0.1038 | 0.0644 | 0.1426 | 0.0459 | 0.1617 | 0.1022 | 0.1038 | 0.0644 | 0.1426 | 0.0459 | 0.1617 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 23 | 225 | 544.5977 | 92.4089 | 0.1697 | 0.1547 | 0.1863 | 0.1459 | 0.1935 | 77.4989 | 66.0256 | 88.2899 | 61.7105 | 93.2872 | 0.1022 | 0.0675 | 0.0524 | 0.0840 | 0.0437 | 0.0913 | 0.1022 | 0.0675 | 0.0524 | 0.0840 | 0.0437 | 0.0913 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 23 | 225 | 544.5977 | 92.4089 | 0.1697 | 0.1547 | 0.1863 | 0.1459 | 0.1935 | 77.4989 | 66.0256 | 88.2899 | 61.7105 | 93.2872 | 0.1022 | 0.0675 | 0.0524 | 0.0840 | 0.0437 | 0.0913 | 0.1022 | 0.0675 | 0.0524 | 0.0840 | 0.0437 | 0.0913 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 23 | 225 | 544.5977 | 92.4089 | 0.1697 | 0.1547 | 0.1863 | 0.1459 | 0.1935 | 77.4989 | 66.0256 | 88.2899 | 61.7105 | 93.2872 | 0.1022 | 0.0675 | 0.0524 | 0.0840 | 0.0437 | 0.0913 | 0.1022 | 0.0675 | 0.0524 | 0.0840 | 0.0437 | 0.0913 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 23 | 225 | 544.5977 | 89.2510 | 0.1639 | 0.1265 | 0.2059 | 0.1074 | 0.2204 | 80.6567 | 60.1922 | 102.5741 | 49.1360 | 112.1774 | 0.1022 | 0.0617 | 0.0243 | 0.1037 | 0.0051 | 0.1182 | 0.1022 | 0.0617 | 0.0243 | 0.1037 | 0.0051 | 0.1182 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 23 | 225 | 544.5977 | 76.9528 | 0.1413 | 0.1051 | 0.1897 | 0.0781 | 0.2045 | 92.9549 | 65.0976 | 112.2910 | 58.3297 | 127.5802 | 0.1022 | 0.0391 | 0.0029 | 0.0875 | -0.0241 | 0.1023 | 0.1022 | 0.0391 | 0.0029 | 0.0875 | -0.0241 | 0.1023 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.1000 | 23 | 225 | 544.5977 | 169.9077 | 0.3120 | 0.2857 | 0.3361 | 0.2751 | 0.3489 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1022 | 0.2098 | 0.1834 | 0.2339 | 0.1729 | 0.2467 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.5000 | 113 | 225 | 544.5977 | 273.5091 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 208.1350 | 188.0029 | 225.6173 | 180.6429 | 235.6272 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 113 | 225 | 544.5977 | 397.1588 | 0.7293 | 0.6737 | 0.7647 | 0.6624 | 0.7961 | 84.4853 | 68.0643 | 110.4560 | 54.2069 | 114.7638 | 0.5022 | 0.2270 | 0.1715 | 0.2625 | 0.1602 | 0.2939 | 0.5022 | 0.2270 | 0.1715 | 0.2625 | 0.1602 | 0.2939 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 113 | 225 | 544.5977 | 388.0149 | 0.7125 | 0.6779 | 0.7517 | 0.6588 | 0.7662 | 93.6292 | 76.3511 | 109.0916 | 70.6708 | 116.5876 | 0.5022 | 0.2103 | 0.1756 | 0.2495 | 0.1565 | 0.2640 | 0.5022 | 0.2103 | 0.1756 | 0.2495 | 0.1565 | 0.2640 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 113 | 225 | 544.5977 | 388.0149 | 0.7125 | 0.6779 | 0.7517 | 0.6588 | 0.7662 | 93.6292 | 76.3511 | 109.0916 | 70.6708 | 116.5876 | 0.5022 | 0.2103 | 0.1756 | 0.2495 | 0.1565 | 0.2640 | 0.5022 | 0.2103 | 0.1756 | 0.2495 | 0.1565 | 0.2640 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 113 | 225 | 544.5977 | 388.0149 | 0.7125 | 0.6779 | 0.7517 | 0.6588 | 0.7662 | 93.6292 | 76.3511 | 109.0916 | 70.6708 | 116.5876 | 0.5022 | 0.2103 | 0.1756 | 0.2495 | 0.1565 | 0.2640 | 0.5022 | 0.2103 | 0.1756 | 0.2495 | 0.1565 | 0.2640 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 113 | 225 | 544.5977 | 389.3555 | 0.7149 | 0.6763 | 0.7655 | 0.6504 | 0.7795 | 92.2886 | 68.4189 | 109.0140 | 62.2415 | 122.3357 | 0.5022 | 0.2127 | 0.1741 | 0.2633 | 0.1482 | 0.2772 | 0.5022 | 0.2127 | 0.1741 | 0.2633 | 0.1482 | 0.2772 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 113 | 225 | 544.5977 | 406.4870 | 0.7464 | 0.7047 | 0.7853 | 0.6866 | 0.8062 | 75.1571 | 59.1098 | 92.6416 | 49.3819 | 100.9323 | 0.5022 | 0.2442 | 0.2025 | 0.2831 | 0.1843 | 0.3040 | 0.5022 | 0.2442 | 0.2025 | 0.2831 | 0.1843 | 0.3040 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.5000 | 113 | 225 | 544.5977 | 481.6441 | 0.8844 | 0.8565 | 0.9137 | 0.8417 | 0.9271 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5022 | 0.3822 | 0.3543 | 0.4114 | 0.3395 | 0.4249 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.2500 | 57 | 227 | 521.2246 | 130.8802 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 0.2511 | 201.1242 | 182.1282 | 218.4858 | 173.7719 | 228.4764 | 0.2511 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 57 | 227 | 521.2246 | 226.4856 | 0.4345 | 0.3729 | 0.4794 | 0.3551 | 0.5140 | 105.5188 | 80.7064 | 135.9960 | 64.9165 | 146.1211 | 0.2511 | 0.1834 | 0.1218 | 0.2283 | 0.1040 | 0.2629 | 0.2511 | 0.1834 | 0.1218 | 0.2283 | 0.1040 | 0.2629 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 57 | 227 | 521.2246 | 214.8336 | 0.4122 | 0.3735 | 0.4530 | 0.3537 | 0.4707 | 117.1707 | 97.2541 | 136.4058 | 88.5973 | 145.7442 | 0.2511 | 0.1611 | 0.1224 | 0.2019 | 0.1026 | 0.2196 | 0.2511 | 0.1611 | 0.1224 | 0.2019 | 0.1026 | 0.2196 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 57 | 227 | 521.2246 | 214.8336 | 0.4122 | 0.3735 | 0.4530 | 0.3537 | 0.4707 | 117.1707 | 97.2541 | 136.4058 | 88.5973 | 145.7442 | 0.2511 | 0.1611 | 0.1224 | 0.2019 | 0.1026 | 0.2196 | 0.2511 | 0.1611 | 0.1224 | 0.2019 | 0.1026 | 0.2196 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 57 | 227 | 521.2246 | 214.8336 | 0.4122 | 0.3735 | 0.4530 | 0.3537 | 0.4707 | 117.1707 | 97.2541 | 136.4058 | 88.5973 | 145.7442 | 0.2511 | 0.1611 | 0.1224 | 0.2019 | 0.1026 | 0.2196 | 0.2511 | 0.1611 | 0.1224 | 0.2019 | 0.1026 | 0.2196 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 57 | 227 | 521.2246 | 225.2021 | 0.4321 | 0.3666 | 0.4777 | 0.3531 | 0.5111 | 106.8023 | 84.0047 | 137.8201 | 66.1738 | 147.4307 | 0.2511 | 0.1810 | 0.1155 | 0.2266 | 0.1020 | 0.2600 | 0.2511 | 0.1810 | 0.1155 | 0.2266 | 0.1020 | 0.2600 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 57 | 227 | 521.2246 | 207.3839 | 0.3979 | 0.3480 | 0.4572 | 0.3172 | 0.4785 | 124.6205 | 93.5920 | 151.2627 | 83.0777 | 166.1633 | 0.2511 | 0.1468 | 0.0969 | 0.2061 | 0.0661 | 0.2274 | 0.2511 | 0.1468 | 0.0969 | 0.2061 | 0.0661 | 0.2274 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.2500 | 57 | 227 | 521.2246 | 332.0044 | 0.6370 | 0.5964 | 0.6745 | 0.5801 | 0.6938 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2511 | 0.3859 | 0.3453 | 0.4234 | 0.3290 | 0.4427 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.1000 | 23 | 227 | 521.2246 | 52.8113 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 0.1013 | 119.5188 | 106.9055 | 127.8717 | 103.7796 | 135.2579 | 0.1013 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 23 | 227 | 521.2246 | 83.7268 | 0.1606 | 0.1191 | 0.1983 | 0.1015 | 0.2198 | 88.6033 | 70.2567 | 108.5839 | 60.3280 | 116.8785 | 0.1013 | 0.0593 | 0.0177 | 0.0970 | 0.0002 | 0.1185 | 0.1013 | 0.0593 | 0.0177 | 0.0970 | 0.0002 | 0.1185 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 23 | 227 | 521.2246 | 86.6873 | 0.1663 | 0.1514 | 0.1815 | 0.1437 | 0.1889 | 85.6428 | 74.6512 | 95.0172 | 71.1580 | 100.1277 | 0.1013 | 0.0650 | 0.0501 | 0.0802 | 0.0424 | 0.0876 | 0.1013 | 0.0650 | 0.0501 | 0.0802 | 0.0424 | 0.0876 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 23 | 227 | 521.2246 | 86.6873 | 0.1663 | 0.1514 | 0.1815 | 0.1437 | 0.1889 | 85.6428 | 74.6512 | 95.0172 | 71.1580 | 100.1277 | 0.1013 | 0.0650 | 0.0501 | 0.0802 | 0.0424 | 0.0876 | 0.1013 | 0.0650 | 0.0501 | 0.0802 | 0.0424 | 0.0876 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 23 | 227 | 521.2246 | 86.6873 | 0.1663 | 0.1514 | 0.1815 | 0.1437 | 0.1889 | 85.6428 | 74.6512 | 95.0172 | 71.1580 | 100.1277 | 0.1013 | 0.0650 | 0.0501 | 0.0802 | 0.0424 | 0.0876 | 0.1013 | 0.0650 | 0.0501 | 0.0802 | 0.0424 | 0.0876 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 23 | 227 | 521.2246 | 79.7726 | 0.1530 | 0.1076 | 0.1891 | 0.0922 | 0.2139 | 92.5575 | 70.3879 | 114.7680 | 59.4249 | 125.6902 | 0.1013 | 0.0517 | 0.0063 | 0.0877 | -0.0091 | 0.1125 | 0.1013 | 0.0517 | 0.0063 | 0.0877 | -0.0091 | 0.1125 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 23 | 227 | 521.2246 | 89.8810 | 0.1724 | 0.1284 | 0.2108 | 0.1108 | 0.2341 | 82.4490 | 59.2393 | 103.1595 | 50.5664 | 114.3317 | 0.1013 | 0.0711 | 0.0271 | 0.1094 | 0.0094 | 0.1328 | 0.1013 | 0.0711 | 0.0271 | 0.1094 | 0.0094 | 0.1328 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.1000 | 23 | 227 | 521.2246 | 172.3301 | 0.3306 | 0.2990 | 0.3566 | 0.2902 | 0.3710 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1013 | 0.2293 | 0.1977 | 0.2552 | 0.1889 | 0.2697 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.5000 | 114 | 227 | 521.2246 | 261.7604 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 0.5022 | 216.2121 | 193.6798 | 235.5061 | 187.4666 | 244.9577 | 0.5022 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 114 | 227 | 521.2246 | 383.6529 | 0.7361 | 0.6992 | 0.7951 | 0.6621 | 0.8100 | 94.3196 | 65.0031 | 112.3036 | 59.5542 | 129.0851 | 0.5022 | 0.2339 | 0.1970 | 0.2929 | 0.1599 | 0.3078 | 0.5022 | 0.2339 | 0.1970 | 0.2929 | 0.1599 | 0.3078 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 114 | 227 | 521.2246 | 388.2492 | 0.7449 | 0.7019 | 0.7878 | 0.6816 | 0.8081 | 89.7233 | 70.4827 | 109.1303 | 61.4048 | 118.0419 | 0.5022 | 0.2427 | 0.1997 | 0.2856 | 0.1794 | 0.3059 | 0.5022 | 0.2427 | 0.1997 | 0.2856 | 0.1794 | 0.3059 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 114 | 227 | 521.2246 | 388.2492 | 0.7449 | 0.7019 | 0.7878 | 0.6816 | 0.8081 | 89.7233 | 70.4827 | 109.1303 | 61.4048 | 118.0419 | 0.5022 | 0.2427 | 0.1997 | 0.2856 | 0.1794 | 0.3059 | 0.5022 | 0.2427 | 0.1997 | 0.2856 | 0.1794 | 0.3059 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 114 | 227 | 521.2246 | 388.2492 | 0.7449 | 0.7019 | 0.7878 | 0.6816 | 0.8081 | 89.7233 | 70.4827 | 109.1303 | 61.4048 | 118.0419 | 0.5022 | 0.2427 | 0.1997 | 0.2856 | 0.1794 | 0.3059 | 0.5022 | 0.2427 | 0.1997 | 0.2856 | 0.1794 | 0.3059 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 114 | 227 | 521.2246 | 398.1715 | 0.7639 | 0.7022 | 0.8152 | 0.6840 | 0.8438 | 79.8010 | 57.4742 | 110.4392 | 42.8263 | 116.7758 | 0.5022 | 0.2617 | 0.2000 | 0.3130 | 0.1818 | 0.3416 | 0.5022 | 0.2617 | 0.2000 | 0.3130 | 0.1818 | 0.3416 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 114 | 227 | 521.2246 | 391.4985 | 0.7511 | 0.6948 | 0.7926 | 0.6796 | 0.8226 | 86.4740 | 65.4164 | 111.8683 | 52.9500 | 119.9981 | 0.5022 | 0.2489 | 0.1926 | 0.2904 | 0.1774 | 0.3204 | 0.5022 | 0.2489 | 0.1926 | 0.2904 | 0.1774 | 0.3204 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.5000 | 114 | 227 | 521.2246 | 477.9725 | 0.9170 | 0.8898 | 0.9416 | 0.8785 | 0.9555 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5022 | 0.4148 | 0.3876 | 0.4394 | 0.3763 | 0.4533 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.2500 | 54 | 217 | 476.2898 | 118.5237 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 0.2488 | 187.0780 | 165.6227 | 210.0745 | 154.1613 | 219.9948 | 0.2488 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 54 | 217 | 476.2898 | 224.9524 | 0.4723 | 0.4070 | 0.5275 | 0.3871 | 0.5575 | 80.6494 | 62.3999 | 102.3401 | 50.9421 | 110.3566 | 0.2488 | 0.2235 | 0.1582 | 0.2787 | 0.1383 | 0.3086 | 0.2488 | 0.2235 | 0.1582 | 0.2787 | 0.1383 | 0.3086 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 54 | 217 | 476.2898 | 203.4276 | 0.4271 | 0.3783 | 0.4836 | 0.3534 | 0.5008 | 102.1741 | 81.2708 | 120.8034 | 72.0712 | 132.2770 | 0.2488 | 0.1783 | 0.1295 | 0.2347 | 0.1046 | 0.2519 | 0.2488 | 0.1783 | 0.1295 | 0.2347 | 0.1046 | 0.2519 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 54 | 217 | 476.2898 | 203.4276 | 0.4271 | 0.3783 | 0.4836 | 0.3534 | 0.5008 | 102.1741 | 81.2708 | 120.8034 | 72.0712 | 132.2770 | 0.2488 | 0.1783 | 0.1295 | 0.2347 | 0.1046 | 0.2519 | 0.2488 | 0.1783 | 0.1295 | 0.2347 | 0.1046 | 0.2519 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 54 | 217 | 476.2898 | 203.4276 | 0.4271 | 0.3783 | 0.4836 | 0.3534 | 0.5008 | 102.1741 | 81.2708 | 120.8034 | 72.0712 | 132.2770 | 0.2488 | 0.1783 | 0.1295 | 0.2347 | 0.1046 | 0.2519 | 0.2488 | 0.1783 | 0.1295 | 0.2347 | 0.1046 | 0.2519 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 54 | 217 | 476.2898 | 203.3086 | 0.4269 | 0.3764 | 0.4981 | 0.3373 | 0.5164 | 102.2931 | 73.7991 | 121.1977 | 66.8345 | 137.7518 | 0.2488 | 0.1780 | 0.1276 | 0.2492 | 0.0885 | 0.2675 | 0.2488 | 0.1780 | 0.1276 | 0.2492 | 0.0885 | 0.2675 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 54 | 217 | 476.2898 | 196.9714 | 0.4136 | 0.3626 | 0.4790 | 0.3269 | 0.5002 | 108.6303 | 81.6610 | 129.1304 | 73.8449 | 143.4157 | 0.2488 | 0.1647 | 0.1137 | 0.2302 | 0.0781 | 0.2513 | 0.2488 | 0.1647 | 0.1137 | 0.2302 | 0.0781 | 0.2513 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.2500 | 54 | 217 | 476.2898 | 305.6018 | 0.6416 | 0.6000 | 0.6783 | 0.5847 | 0.6986 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2488 | 0.3928 | 0.3512 | 0.4294 | 0.3358 | 0.4497 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.1000 | 22 | 217 | 476.2898 | 48.2874 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 0.1014 | 117.8278 | 101.9953 | 135.3610 | 93.1022 | 142.5533 | 0.1014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 22 | 217 | 476.2898 | 109.2436 | 0.2294 | 0.1843 | 0.2869 | 0.1535 | 0.3052 | 56.8716 | 36.9249 | 73.7871 | 30.4739 | 83.2693 | 0.1014 | 0.1280 | 0.0829 | 0.1855 | 0.0521 | 0.2038 | 0.1014 | 0.1280 | 0.0829 | 0.1855 | 0.0521 | 0.2038 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 22 | 217 | 476.2898 | 82.8779 | 0.1740 | 0.1529 | 0.1951 | 0.1440 | 0.2040 | 83.2373 | 69.0409 | 96.1772 | 62.9036 | 103.5710 | 0.1014 | 0.0726 | 0.0515 | 0.0937 | 0.0427 | 0.1026 | 0.1014 | 0.0726 | 0.0515 | 0.0937 | 0.0427 | 0.1026 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 22 | 217 | 476.2898 | 82.8779 | 0.1740 | 0.1529 | 0.1951 | 0.1440 | 0.2040 | 83.2373 | 69.0409 | 96.1772 | 62.9036 | 103.5710 | 0.1014 | 0.0726 | 0.0515 | 0.0937 | 0.0427 | 0.1026 | 0.1014 | 0.0726 | 0.0515 | 0.0937 | 0.0427 | 0.1026 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 22 | 217 | 476.2898 | 82.8779 | 0.1740 | 0.1529 | 0.1951 | 0.1440 | 0.2040 | 83.2373 | 69.0409 | 96.1772 | 62.9036 | 103.5710 | 0.1014 | 0.0726 | 0.0515 | 0.0937 | 0.0427 | 0.1026 | 0.1014 | 0.0726 | 0.0515 | 0.0937 | 0.0427 | 0.1026 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 22 | 217 | 476.2898 | 102.9688 | 0.2162 | 0.1623 | 0.2585 | 0.1439 | 0.2884 | 63.1464 | 45.8508 | 88.5675 | 32.5792 | 93.7136 | 0.1014 | 0.1148 | 0.0609 | 0.1571 | 0.0426 | 0.1871 | 0.1014 | 0.1148 | 0.0609 | 0.1571 | 0.0426 | 0.1871 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 22 | 217 | 476.2898 | 115.9230 | 0.2434 | 0.1885 | 0.2890 | 0.1696 | 0.3172 | 50.1922 | 33.3021 | 69.4055 | 23.8510 | 76.5334 | 0.1014 | 0.1420 | 0.0872 | 0.1877 | 0.0682 | 0.2158 | 0.1014 | 0.1420 | 0.0872 | 0.1877 | 0.0682 | 0.2158 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.1000 | 22 | 217 | 476.2898 | 166.1152 | 0.3488 | 0.3175 | 0.3831 | 0.2982 | 0.3994 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1014 | 0.2474 | 0.2162 | 0.2817 | 0.1968 | 0.2980 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.5000 | 109 | 217 | 476.2898 | 239.2423 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 0.5023 | 203.1564 | 183.4723 | 220.6524 | 175.3175 | 230.9952 | 0.5023 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 109 | 217 | 476.2898 | 353.1861 | 0.7415 | 0.6894 | 0.7822 | 0.6718 | 0.8112 | 89.2125 | 70.2618 | 112.6554 | 58.8481 | 119.5770 | 0.5023 | 0.2392 | 0.1871 | 0.2799 | 0.1695 | 0.3089 | 0.5023 | 0.2392 | 0.1871 | 0.2799 | 0.1695 | 0.3089 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 109 | 217 | 476.2898 | 351.0927 | 0.7371 | 0.6946 | 0.7771 | 0.6778 | 0.7965 | 91.3060 | 74.0686 | 106.1268 | 67.0515 | 115.5605 | 0.5023 | 0.2348 | 0.1923 | 0.2748 | 0.1755 | 0.2942 | 0.5023 | 0.2348 | 0.1923 | 0.2748 | 0.1755 | 0.2942 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 109 | 217 | 476.2898 | 351.0927 | 0.7371 | 0.6946 | 0.7771 | 0.6778 | 0.7965 | 91.3060 | 74.0686 | 106.1268 | 67.0515 | 115.5605 | 0.5023 | 0.2348 | 0.1923 | 0.2748 | 0.1755 | 0.2942 | 0.5023 | 0.2348 | 0.1923 | 0.2748 | 0.1755 | 0.2942 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 109 | 217 | 476.2898 | 351.0927 | 0.7371 | 0.6946 | 0.7771 | 0.6778 | 0.7965 | 91.3060 | 74.0686 | 106.1268 | 67.0515 | 115.5605 | 0.5023 | 0.2348 | 0.1923 | 0.2748 | 0.1755 | 0.2942 | 0.5023 | 0.2348 | 0.1923 | 0.2748 | 0.1755 | 0.2942 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 109 | 217 | 476.2898 | 350.1608 | 0.7352 | 0.6834 | 0.7850 | 0.6586 | 0.8118 | 92.2379 | 70.5052 | 116.9002 | 58.4794 | 125.9964 | 0.5023 | 0.2329 | 0.1811 | 0.2827 | 0.1563 | 0.3095 | 0.5023 | 0.2329 | 0.1811 | 0.2827 | 0.1563 | 0.3095 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 109 | 217 | 476.2898 | 345.9675 | 0.7264 | 0.6777 | 0.7821 | 0.6515 | 0.8013 | 96.4312 | 71.7535 | 119.2224 | 62.9062 | 129.9562 | 0.5023 | 0.2241 | 0.1754 | 0.2798 | 0.1492 | 0.2990 | 0.5023 | 0.2241 | 0.1754 | 0.2798 | 0.1492 | 0.2990 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.5000 | 109 | 217 | 476.2898 | 442.3987 | 0.9288 | 0.8980 | 0.9548 | 0.8878 | 0.9699 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5023 | 0.4265 | 0.3957 | 0.4525 | 0.3855 | 0.4676 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.2500 | 447 | 1788 | 4231.1899 | 1057.7400 | 0.2500 | 0.2499 | 0.2500 | 0.2499 | 0.2501 | 1507.3054 | 1445.8141 | 1555.0927 | 1426.1280 | 1588.4828 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.2500 | 447 | 1788 | 4231.1899 | 1868.7603 | 0.4417 | 0.4213 | 0.4574 | 0.4146 | 0.4687 | 696.2851 | 628.4783 | 762.9010 | 597.5537 | 795.0165 | 0.2500 | 0.1917 | 0.1713 | 0.2074 | 0.1647 | 0.2187 | 0.2500 | 0.1917 | 0.1713 | 0.2074 | 0.1647 | 0.2187 | 6 | no |
| ALL | p_win | P0 | 0.2500 | 447 | 1788 | 4231.1899 | 1779.1016 | 0.4205 | 0.4065 | 0.4357 | 0.3988 | 0.4422 | 785.9438 | 723.8900 | 835.6442 | 703.8205 | 868.0672 | 0.2500 | 0.1705 | 0.1565 | 0.1856 | 0.1488 | 0.1922 | 0.2500 | 0.1705 | 0.1565 | 0.1856 | 0.1488 | 0.1922 | 6 | yes |
| ALL | p_win | P1 | 0.2500 | 447 | 1788 | 4231.1899 | 1779.1016 | 0.4205 | 0.4065 | 0.4357 | 0.3988 | 0.4422 | 785.9438 | 723.8900 | 835.6442 | 703.8205 | 868.0672 | 0.2500 | 0.1705 | 0.1565 | 0.1856 | 0.1488 | 0.1922 | 0.2500 | 0.1705 | 0.1565 | 0.1856 | 0.1488 | 0.1922 | 6 | yes |
| ALL | p_win | P2 | 0.2500 | 447 | 1788 | 4231.1899 | 1779.1016 | 0.4205 | 0.4065 | 0.4354 | 0.3988 | 0.4422 | 785.9438 | 723.8900 | 835.6442 | 703.8658 | 868.0218 | 0.2500 | 0.1705 | 0.1565 | 0.1855 | 0.1488 | 0.1922 | 0.2500 | 0.1705 | 0.1565 | 0.1855 | 0.1488 | 0.1922 | 6 | no |
| ALL | p_win | local_eb | 0.2500 | 447 | 1788 | 4231.1899 | 1780.1731 | 0.4207 | 0.4038 | 0.4416 | 0.3936 | 0.4479 | 784.8723 | 694.7919 | 838.6528 | 683.0938 | 886.6508 | 0.2500 | 0.1707 | 0.1537 | 0.1916 | 0.1436 | 0.1979 | 0.2500 | 0.1707 | 0.1537 | 0.1916 | 0.1436 | 0.1979 | 6 | no |
| ALL | p_win | text_lr | 0.2500 | 447 | 1788 | 4231.1899 | 1695.0172 | 0.4006 | 0.3848 | 0.4219 | 0.3729 | 0.4283 | 870.0282 | 776.7983 | 924.9401 | 761.6713 | 978.3851 | 0.2500 | 0.1506 | 0.1348 | 0.1719 | 0.1229 | 0.1783 | 0.2500 | 0.1506 | 0.1348 | 0.1719 | 0.1229 | 0.1783 | 6 | no |
| ALL | oracle | all | 0.2500 | 447 | 1788 | 4231.1899 | 2565.0454 | 0.6062 | 0.5916 | 0.6173 | 0.5874 | 0.6250 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3562 | 0.3416 | 0.3673 | 0.3374 | 0.3750 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.1000 | 180 | 1788 | 4231.1899 | 426.0350 | 0.1007 | 0.1006 | 0.1007 | 0.1006 | 0.1008 | 897.6205 | 852.7525 | 927.0111 | 844.2010 | 951.0400 | 0.1007 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.1000 | 180 | 1788 | 4231.1899 | 805.1965 | 0.1903 | 0.1766 | 0.2062 | 0.1687 | 0.2119 | 518.4590 | 457.0847 | 560.9404 | 441.8257 | 595.0923 | 0.1007 | 0.0896 | 0.0759 | 0.1054 | 0.0681 | 0.1112 | 0.1007 | 0.0896 | 0.0759 | 0.1054 | 0.0681 | 0.1112 | 6 | no |
| ALL | p_win | P0 | 0.1000 | 180 | 1788 | 4231.1899 | 716.6207 | 0.1694 | 0.1635 | 0.1757 | 0.1604 | 0.1783 | 607.0348 | 566.8854 | 630.4466 | 561.1828 | 652.8869 | 0.1007 | 0.0687 | 0.0627 | 0.0750 | 0.0597 | 0.0776 | 0.1007 | 0.0687 | 0.0627 | 0.0750 | 0.0597 | 0.0776 | 6 | yes |
| ALL | p_win | P1 | 0.1000 | 180 | 1788 | 4231.1899 | 716.6207 | 0.1694 | 0.1635 | 0.1757 | 0.1604 | 0.1783 | 607.0348 | 566.8854 | 630.4466 | 561.1828 | 652.8869 | 0.1007 | 0.0687 | 0.0627 | 0.0750 | 0.0597 | 0.0776 | 0.1007 | 0.0687 | 0.0627 | 0.0750 | 0.0597 | 0.0776 | 6 | yes |
| ALL | p_win | P2 | 0.1000 | 180 | 1788 | 4231.1899 | 716.6207 | 0.1694 | 0.1635 | 0.1757 | 0.1604 | 0.1783 | 607.0348 | 566.8854 | 630.4466 | 561.1828 | 652.8869 | 0.1007 | 0.0687 | 0.0627 | 0.0750 | 0.0597 | 0.0776 | 0.1007 | 0.0687 | 0.0627 | 0.0750 | 0.0597 | 0.0776 | 6 | no |
| ALL | p_win | local_eb | 0.1000 | 180 | 1788 | 4231.1899 | 783.8308 | 0.1853 | 0.1664 | 0.1954 | 0.1649 | 0.2056 | 539.8247 | 491.9544 | 611.3007 | 453.7676 | 625.8818 | 0.1007 | 0.0846 | 0.0657 | 0.0947 | 0.0642 | 0.1049 | 0.1007 | 0.0846 | 0.0657 | 0.0947 | 0.0642 | 0.1049 | 6 | no |
| ALL | p_win | text_lr | 0.1000 | 180 | 1788 | 4231.1899 | 805.4254 | 0.1904 | 0.1736 | 0.2016 | 0.1693 | 0.2114 | 518.2301 | 467.1322 | 579.2825 | 435.4495 | 601.0107 | 0.1007 | 0.0897 | 0.0729 | 0.1009 | 0.0686 | 0.1107 | 0.1007 | 0.0897 | 0.0729 | 0.1009 | 0.0686 | 0.1107 | 6 | no |
| ALL | oracle | all | 0.1000 | 180 | 1788 | 4231.1899 | 1323.6555 | 0.3128 | 0.3014 | 0.3213 | 0.2980 | 0.3277 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1007 | 0.2121 | 0.2007 | 0.2206 | 0.1973 | 0.2270 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.5000 | 896 | 1788 | 4231.1899 | 2120.4045 | 0.5011 | 0.5011 | 0.5012 | 0.5011 | 0.5012 | 1694.3951 | 1633.3164 | 1736.7606 | 1616.0592 | 1772.7311 | 0.5011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.5000 | 896 | 1788 | 4231.1899 | 3105.1588 | 0.7339 | 0.7130 | 0.7480 | 0.7081 | 0.7596 | 709.6408 | 650.8977 | 780.6466 | 617.7249 | 801.5567 | 0.5011 | 0.2327 | 0.2119 | 0.2468 | 0.2070 | 0.2585 | 0.5011 | 0.2327 | 0.2119 | 0.2468 | 0.2070 | 0.2585 | 6 | no |
| ALL | p_win | P0 | 0.5000 | 896 | 1788 | 4231.1899 | 3067.6159 | 0.7250 | 0.7101 | 0.7383 | 0.7033 | 0.7467 | 747.1837 | 690.2649 | 791.2997 | 673.3088 | 821.0586 | 0.5011 | 0.2239 | 0.2090 | 0.2372 | 0.2022 | 0.2455 | 0.5011 | 0.2239 | 0.2090 | 0.2372 | 0.2022 | 0.2455 | 6 | yes |
| ALL | p_win | P1 | 0.5000 | 896 | 1788 | 4231.1899 | 3067.6159 | 0.7250 | 0.7101 | 0.7383 | 0.7033 | 0.7467 | 747.1837 | 690.2649 | 791.2997 | 673.3088 | 821.0586 | 0.5011 | 0.2239 | 0.2090 | 0.2372 | 0.2022 | 0.2455 | 0.5011 | 0.2239 | 0.2090 | 0.2372 | 0.2022 | 0.2455 | 6 | yes |
| ALL | p_win | P2 | 0.5000 | 896 | 1788 | 4231.1899 | 3057.7471 | 0.7227 | 0.7074 | 0.7371 | 0.7005 | 0.7448 | 757.0525 | 697.0351 | 800.7208 | 679.9868 | 834.1183 | 0.5011 | 0.2215 | 0.2063 | 0.2360 | 0.1994 | 0.2437 | 0.5011 | 0.2215 | 0.2063 | 0.2360 | 0.1994 | 0.2437 | 6 | no |
| ALL | p_win | local_eb | 0.5000 | 896 | 1788 | 4231.1899 | 3098.9746 | 0.7324 | 0.7170 | 0.7518 | 0.7065 | 0.7583 | 715.8250 | 634.0728 | 768.1724 | 620.2850 | 811.3650 | 0.5011 | 0.2313 | 0.2158 | 0.2506 | 0.2053 | 0.2572 | 0.5011 | 0.2313 | 0.2158 | 0.2506 | 0.2053 | 0.2572 | 6 | no |
| ALL | p_win | text_lr | 0.5000 | 896 | 1788 | 4231.1899 | 3078.9464 | 0.7277 | 0.7095 | 0.7434 | 0.7020 | 0.7534 | 735.8533 | 665.7156 | 797.5667 | 641.6828 | 830.0238 | 0.5011 | 0.2265 | 0.2084 | 0.2423 | 0.2008 | 0.2522 | 0.5011 | 0.2265 | 0.2084 | 0.2423 | 0.2008 | 0.2522 | 6 | no |
| ALL | oracle | all | 0.5000 | 896 | 1788 | 4231.1899 | 3814.7996 | 0.9016 | 0.8888 | 0.9109 | 0.8854 | 0.9178 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5011 | 0.4005 | 0.3877 | 0.4098 | 0.3843 | 0.4166 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |

## Figures

- figures/reliability-synthetic.png
- figures/score_by_origin-synthetic.png
- figures/coverage-synthetic.png
- figures/decision_value-synthetic.png
