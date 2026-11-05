# Backtest report: synthetic

**Synthetic data.** Every number below comes from simulated tests with known truth. It shows the method works, not what any real archive says.

> The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.

## Header

- Source: synthetic
- Ledger snapshot: 20261105-c7ca82ca15a6
- Model: e4f97a83999d
- Feature hash: 160f62eb0d63
- Command: `moot backtest --source synthetic --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr --seed 0`
- Seed: 0, bootstrap resamples: 500
- Gate sizes from the power simulation at the release gate (power 0.90): n_200 = 175 (skill 0.20), n_400 = 250 (skill 0.10)
- At power 0.80: n_200 = 125 (skill 0.20), n_400 = 200 (skill 0.10) (research screen)
- At power 0.90: n_200 = 175 (skill 0.20), n_400 = 250 (skill 0.10) (release gate)
- Rungs: GBM, GBM+cal, P0, P1, P2, always_reference, always_variant, local_eb, local_eb+cal, text_lr, text_lr+cal; primary rung for decisions and plots: P2
- Origins scored: 8 from 2013-04-01T00:00:00+00:00 to 2015-01-01T00:00:00+00:00
- Origins with fewer than 20 visible rows (nothing fitted): 2013-01-01T00:00:00+00:00
- Ledger rows: 22200, admitted: 22200, scored: 19766, admitted but never scored (before the first fit): 2434
- Tests: 11100 in the ledger, 11100 admitted, 9883 scored. Tests in the ledger are the distinct test ids of every row of the source whatever its status. Tests admitted are the distinct test ids with at least one admitted contrast. Tests scored are the admitted tests with at least one contrast scored by the primary rung. The difference between admitted and scored is the contrasts of the first quarters, before the first origin with enough visible rows to fit (they are history only), plus any test whose contrasts all fall there.
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
| ALL | GBM | challenger | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | GBM+cal | challenger | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P0 | ladder | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P1 | ladder | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P2 | ladder | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | always_reference | baseline | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | always_variant | baseline | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb | challenger | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb+cal | challenger | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr | challenger | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr+cal | challenger | 19766 | 9883 | 16212 | 0.1798 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | GBM | challenger | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | GBM+cal | challenger | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P0 | ladder | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P1 | ladder | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P2 | ladder | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | always_reference | baseline | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | always_variant | baseline | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | local_eb | challenger | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | local_eb+cal | challenger | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | text_lr | challenger | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | text_lr+cal | challenger | 6788 | 3394 | 5562 | 0.1806 | 0.1400 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM | challenger | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM+cal | challenger | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P0 | ladder | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P1 | ladder | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P2 | ladder | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | always_reference | baseline | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | always_variant | baseline | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb | challenger | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb+cal | challenger | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr | challenger | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr+cal | challenger | 6354 | 3177 | 5169 | 0.1865 | 0.3000 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | GBM | challenger | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | GBM+cal | challenger | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P0 | ladder | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P1 | ladder | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P2 | ladder | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | always_reference | baseline | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | always_variant | baseline | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb | challenger | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb+cal | challenger | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr | challenger | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr+cal | challenger | 6624 | 3312 | 5481 | 0.1726 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |

### Log score and CRPS, all predicted rows (higher log score is better, lower CRPS is better)

| cell | rung | logscore | logscore_lo | logscore_hi | crps | crps_lo | crps_hi |
|---|---|---|---|---|---|---|---|
| ALL | GBM | -2.4424 | -2.4530 | -2.4337 | 1.5625 | 1.5494 | 1.5783 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | -2.4276 | -2.4377 | -2.4200 | 1.5651 | 1.5522 | 1.5812 |
| ALL | P1 | -2.4181 | -2.4284 | -2.4105 | 1.5616 | 1.5488 | 1.5781 |
| ALL | P2 | -2.4163 | -2.4264 | -2.4088 | 1.5591 | 1.5462 | 1.5751 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | -2.4301 | -2.4409 | -2.4215 | 1.5666 | 1.5537 | 1.5824 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | -2.3766 | -2.3893 | -2.3626 | 1.4716 | 1.4483 | 1.4935 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | -2.3908 | -2.4058 | -2.3743 | 1.4875 | 1.4636 | 1.5099 |
| both | P1 | -2.3808 | -2.3950 | -2.3650 | 1.4843 | 1.4602 | 1.5069 |
| both | P2 | -2.3793 | -2.3934 | -2.3637 | 1.4821 | 1.4577 | 1.5044 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | -2.3933 | -2.4073 | -2.3763 | 1.4920 | 1.4669 | 1.5148 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | -2.6979 | -2.7216 | -2.6757 | 1.9513 | 1.9197 | 1.9832 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | -2.6550 | -2.6694 | -2.6401 | 1.9380 | 1.9087 | 1.9672 |
| headline_only | P1 | -2.6507 | -2.6649 | -2.6357 | 1.9355 | 1.9060 | 1.9649 |
| headline_only | P2 | -2.6504 | -2.6646 | -2.6355 | 1.9348 | 1.9050 | 1.9642 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | -2.6683 | -2.6844 | -2.6527 | 1.9481 | 1.9202 | 1.9781 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | -2.2647 | -2.2732 | -2.2557 | 1.2827 | 1.2670 | 1.2979 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | -2.2472 | -2.2607 | -2.2326 | 1.2869 | 1.2675 | 1.3041 |
| image_only | P1 | -2.2333 | -2.2469 | -2.2188 | 1.2822 | 1.2633 | 1.2992 |
| image_only | P2 | -2.2298 | -2.2433 | -2.2151 | 1.2776 | 1.2588 | 1.2944 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | -2.2391 | -2.2533 | -2.2236 | 1.2769 | 1.2582 | 1.2940 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |

### Brier score of p_sig against the significant-positive event, with skill against the base rate

| cell | rung | brier | brier_lo | brier_hi | brier_base | brier_skill | brier_skill_lo | brier_skill_hi | brier_floor |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.1384 | 0.1356 | 0.1408 | 0.1408 | 0.0177 | 0.0116 | 0.0236 | 0.0686 |
| ALL | GBM+cal | 0.1383 | 0.1355 | 0.1408 | 0.1408 | 0.0177 | 0.0109 | 0.0248 | 0.0686 |
| ALL | P0 | 0.1408 | 0.1383 | 0.1436 | 0.1408 | 0.0000 | 0.0000 | 0.0000 | 0.0686 |
| ALL | P1 | 0.1378 | 0.1351 | 0.1404 | 0.1408 | 0.0215 | 0.0177 | 0.0251 | 0.0686 |
| ALL | P2 | 0.1377 | 0.1350 | 0.1403 | 0.1408 | 0.0224 | 0.0186 | 0.0262 | 0.0686 |
| ALL | always_reference | n/a | n/a | n/a | 0.1408 | n/a | n/a | n/a | 0.0686 |
| ALL | always_variant | n/a | n/a | n/a | 0.1408 | n/a | n/a | n/a | 0.0686 |
| ALL | local_eb | 0.1383 | 0.1356 | 0.1409 | 0.1408 | 0.0179 | 0.0126 | 0.0232 | 0.0686 |
| ALL | local_eb+cal | 0.1384 | 0.1357 | 0.1409 | 0.1408 | 0.0176 | 0.0123 | 0.0229 | 0.0686 |
| ALL | text_lr | 0.1432 | 0.1406 | 0.1460 | 0.1408 | -0.0168 | -0.0222 | -0.0114 | 0.0686 |
| ALL | text_lr+cal | 0.1427 | 0.1401 | 0.1455 | 0.1408 | -0.0134 | -0.0184 | -0.0085 | 0.0686 |
| both | GBM | 0.1428 | 0.1381 | 0.1476 | 0.1473 | 0.0303 | 0.0228 | 0.0371 | 0.0812 |
| both | GBM+cal | 0.1427 | 0.1376 | 0.1478 | 0.1473 | 0.0310 | 0.0227 | 0.0389 | 0.0812 |
| both | P0 | 0.1473 | 0.1418 | 0.1525 | 0.1473 | 0.0000 | 0.0000 | 0.0000 | 0.0812 |
| both | P1 | 0.1442 | 0.1390 | 0.1493 | 0.1473 | 0.0211 | 0.0155 | 0.0260 | 0.0812 |
| both | P2 | 0.1439 | 0.1389 | 0.1490 | 0.1473 | 0.0227 | 0.0171 | 0.0280 | 0.0812 |
| both | always_reference | n/a | n/a | n/a | 0.1473 | n/a | n/a | n/a | 0.0812 |
| both | always_variant | n/a | n/a | n/a | 0.1473 | n/a | n/a | n/a | 0.0812 |
| both | local_eb | 0.1445 | 0.1395 | 0.1495 | 0.1473 | 0.0189 | 0.0118 | 0.0259 | 0.0812 |
| both | local_eb+cal | 0.1446 | 0.1396 | 0.1494 | 0.1473 | 0.0185 | 0.0111 | 0.0259 | 0.0812 |
| both | text_lr | 0.1489 | 0.1435 | 0.1541 | 0.1473 | -0.0113 | -0.0175 | -0.0046 | 0.0812 |
| both | text_lr+cal | 0.1486 | 0.1434 | 0.1537 | 0.1473 | -0.0091 | -0.0154 | -0.0027 | 0.0812 |
| headline_only | GBM | 0.2345 | 0.2312 | 0.2376 | 0.2394 | 0.0206 | 0.0117 | 0.0296 | 0.0962 |
| headline_only | GBM+cal | 0.2363 | 0.2331 | 0.2394 | 0.2394 | 0.0128 | 0.0013 | 0.0238 | 0.0962 |
| headline_only | P0 | 0.2394 | 0.2373 | 0.2415 | 0.2394 | 0.0000 | 0.0000 | 0.0000 | 0.0962 |
| headline_only | P1 | 0.2335 | 0.2310 | 0.2359 | 0.2394 | 0.0247 | 0.0187 | 0.0310 | 0.0962 |
| headline_only | P2 | 0.2334 | 0.2309 | 0.2357 | 0.2394 | 0.0252 | 0.0190 | 0.0314 | 0.0962 |
| headline_only | always_reference | n/a | n/a | n/a | 0.2394 | n/a | n/a | n/a | 0.0962 |
| headline_only | always_variant | n/a | n/a | n/a | 0.2394 | n/a | n/a | n/a | 0.0962 |
| headline_only | local_eb | 0.2346 | 0.2317 | 0.2372 | 0.2394 | 0.0201 | 0.0111 | 0.0284 | 0.0962 |
| headline_only | local_eb+cal | 0.2346 | 0.2319 | 0.2372 | 0.2394 | 0.0201 | 0.0112 | 0.0281 | 0.0962 |
| headline_only | text_lr | 0.2450 | 0.2423 | 0.2478 | 0.2394 | -0.0234 | -0.0323 | -0.0155 | 0.0962 |
| headline_only | text_lr+cal | 0.2437 | 0.2408 | 0.2467 | 0.2394 | -0.0177 | -0.0253 | -0.0105 | 0.0962 |
| image_only | GBM | 0.0416 | 0.0386 | 0.0448 | 0.0397 | -0.0470 | -0.0663 | -0.0307 | 0.0291 |
| image_only | GBM+cal | 0.0399 | 0.0367 | 0.0434 | 0.0397 | -0.0045 | -0.0139 | 0.0044 | 0.0291 |
| image_only | P0 | 0.0397 | 0.0364 | 0.0433 | 0.0397 | 0.0000 | 0.0000 | 0.0000 | 0.0291 |
| image_only | P1 | 0.0395 | 0.0362 | 0.0432 | 0.0397 | 0.0039 | 0.0015 | 0.0062 | 0.0291 |
| image_only | P2 | 0.0395 | 0.0361 | 0.0432 | 0.0397 | 0.0048 | 0.0024 | 0.0070 | 0.0291 |
| image_only | always_reference | n/a | n/a | n/a | 0.0397 | n/a | n/a | n/a | 0.0291 |
| image_only | always_variant | n/a | n/a | n/a | 0.0397 | n/a | n/a | n/a | 0.0291 |
| image_only | local_eb | 0.0396 | 0.0363 | 0.0433 | 0.0397 | 0.0012 | -0.0045 | 0.0070 | 0.0291 |
| image_only | local_eb+cal | 0.0397 | 0.0364 | 0.0433 | 0.0397 | -0.0002 | -0.0067 | 0.0060 | 0.0291 |
| image_only | text_lr | 0.0397 | 0.0364 | 0.0433 | 0.0397 | 0.0002 | -0.0037 | 0.0040 | 0.0291 |
| image_only | text_lr+cal | 0.0399 | 0.0366 | 0.0434 | 0.0397 | -0.0042 | -0.0096 | 0.0008 | 0.0291 |

### Calibration of p_sig against the perfect-calibration null, clustered by test

| cell | rung | ece | ece_percentile | ece_percentile_independent | ece_equal_mass | ece_equal_mass_percentile | design_effect | icc |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.0266 | 100.0000 | 100.0000 | 0.0234 | 100.0000 | 0.9412 | 0.0000 |
| ALL | GBM+cal | 0.0157 | 100.0000 | 100.0000 | 0.0177 | 100.0000 | 1.0192 | 0.0192 |
| ALL | P0 | 0.0041 | 52.0000 | 55.7000 | 0.0062 | 44.6000 | 1.0143 | 0.0143 |
| ALL | P1 | 0.0020 | 1.6000 | 0.6000 | 0.0046 | 15.6000 | 1.0172 | 0.0172 |
| ALL | P2 | 0.0020 | 1.8000 | 1.0000 | 0.0062 | 51.0000 | 1.0193 | 0.0193 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.0089 | 99.0000 | 98.0000 | 0.0071 | 73.4000 | 1.0436 | 0.0436 |
| ALL | local_eb+cal | 0.0047 | 37.7000 | 40.8000 | 0.0081 | 87.6000 | 1.0131 | 0.0131 |
| ALL | text_lr | 0.0201 | 100.0000 | 100.0000 | 0.0211 | 100.0000 | 1.0696 | 0.0696 |
| ALL | text_lr+cal | 0.0178 | 100.0000 | 100.0000 | 0.0172 | 100.0000 | 1.0269 | 0.0269 |
| both | GBM | 0.0152 | 99.0000 | 99.0000 | 0.0181 | 96.6000 | 0.9477 | 0.0000 |
| both | GBM+cal | 0.0104 | 87.6000 | 87.2000 | 0.0095 | 25.2000 | 1.0342 | 0.0342 |
| both | P0 | 0.0038 | 62.0000 | 57.7000 | 0.0086 | 30.2000 | 1.0291 | 0.0291 |
| both | P1 | 0.0036 | 17.1000 | 20.4000 | 0.0072 | 4.6000 | 1.0177 | 0.0177 |
| both | P2 | 0.0028 | 9.0000 | 9.9000 | 0.0090 | 17.2000 | 1.0166 | 0.0166 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.0137 | 97.8000 | 97.2000 | 0.0174 | 96.6000 | 1.0385 | 0.0385 |
| both | local_eb+cal | 0.0116 | 93.6000 | 93.6000 | 0.0187 | 99.4000 | 0.9953 | 0.0000 |
| both | text_lr | 0.0350 | 100.0000 | 100.0000 | 0.0369 | 100.0000 | 1.0718 | 0.0718 |
| both | text_lr+cal | 0.0265 | 100.0000 | 100.0000 | 0.0330 | 100.0000 | 1.0205 | 0.0205 |
| headline_only | GBM | 0.0375 | 100.0000 | 100.0000 | 0.0364 | 100.0000 | 1.0713 | 0.0713 |
| headline_only | GBM+cal | 0.0430 | 100.0000 | 100.0000 | 0.0443 | 100.0000 | 1.0775 | 0.0775 |
| headline_only | P0 | 0.0082 | 68.7000 | 69.6000 | 0.0135 | 47.2000 | 1.0045 | 0.0045 |
| headline_only | P1 | 0.0024 | 0.2000 | 0.6000 | 0.0119 | 16.6000 | 1.0125 | 0.0125 |
| headline_only | P2 | 0.0027 | 1.0000 | 1.2000 | 0.0123 | 17.4000 | 1.0119 | 0.0119 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.0213 | 99.4000 | 99.6000 | 0.0252 | 99.4000 | 1.0377 | 0.0377 |
| headline_only | local_eb+cal | 0.0167 | 95.4000 | 94.4000 | 0.0241 | 98.8000 | 1.0283 | 0.0283 |
| headline_only | text_lr | 0.0584 | 100.0000 | 100.0000 | 0.0624 | 100.0000 | 1.0788 | 0.0788 |
| headline_only | text_lr+cal | 0.0552 | 100.0000 | 100.0000 | 0.0578 | 100.0000 | 1.0749 | 0.0749 |
| image_only | GBM | 0.0448 | 100.0000 | 100.0000 | 0.0448 | 100.0000 | 0.5730 | 0.0000 |
| image_only | GBM+cal | 0.0177 | 100.0000 | 100.0000 | 0.0177 | 100.0000 | 0.7537 | 0.0000 |
| image_only | P0 | 0.0005 | 14.1000 | 14.7000 | 0.0071 | 82.6000 | 1.0154 | 0.0154 |
| image_only | P1 | 0.0007 | 23.1000 | 23.3000 | 0.0060 | 48.4000 | 1.0423 | 0.0423 |
| image_only | P2 | 0.0020 | 61.6000 | 58.6000 | 0.0060 | 52.0000 | 1.0743 | 0.0743 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.0047 | 88.3000 | 91.9000 | 0.0110 | 100.0000 | 1.0986 | 0.0986 |
| image_only | local_eb+cal | 0.0022 | 47.3000 | 47.3000 | 0.0113 | 100.0000 | 0.9964 | 0.0000 |
| image_only | text_lr | 0.0011 | 23.9000 | 21.2000 | 0.0101 | 99.6000 | 1.0119 | 0.0119 |
| image_only | text_lr+cal | 0.0112 | 100.0000 | 100.0000 | 0.0144 | 100.0000 | 0.8321 | 0.0000 |

### Bonferroni-adjusted bounds for the family of intervals of this table (descriptive intervals are the unadjusted ones above)

| cell | rung | family_size | brier_skill | adjusted_lo | adjusted_hi | logscore | logscore_adjusted_lo | logscore_adjusted_hi |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 52 | 0.0177 | 0.0066 | 0.0288 | -2.4424 | -2.4602 | -2.4246 |
| ALL | GBM+cal | 52 | 0.0177 | 0.0047 | 0.0308 | n/a | n/a | n/a |
| ALL | P0 | 52 | 0.0000 | n/a | n/a | -2.4276 | -2.4447 | -2.4105 |
| ALL | P1 | 52 | 0.0215 | 0.0143 | 0.0286 | -2.4181 | -2.4351 | -2.4012 |
| ALL | P2 | 52 | 0.0224 | 0.0152 | 0.0296 | -2.4163 | -2.4333 | -2.3994 |
| ALL | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 52 | 0.0179 | 0.0080 | 0.0277 | -2.4301 | -2.4481 | -2.4120 |
| ALL | local_eb+cal | 52 | 0.0176 | 0.0077 | 0.0275 | n/a | n/a | n/a |
| ALL | text_lr | 52 | -0.0168 | -0.0267 | -0.0070 | n/a | n/a | n/a |
| ALL | text_lr+cal | 52 | -0.0134 | -0.0225 | -0.0042 | n/a | n/a | n/a |
| both | GBM | 52 | 0.0303 | 0.0168 | 0.0437 | -2.3766 | -2.4015 | -2.3518 |
| both | GBM+cal | 52 | 0.0310 | 0.0156 | 0.0465 | n/a | n/a | n/a |
| both | P0 | 52 | 0.0000 | n/a | n/a | -2.3908 | -2.4204 | -2.3612 |
| both | P1 | 52 | 0.0211 | 0.0108 | 0.0314 | -2.3808 | -2.4089 | -2.3526 |
| both | P2 | 52 | 0.0227 | 0.0123 | 0.0331 | -2.3793 | -2.4072 | -2.3514 |
| both | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 52 | 0.0189 | 0.0053 | 0.0324 | -2.3933 | -2.4223 | -2.3644 |
| both | local_eb+cal | 52 | 0.0185 | 0.0045 | 0.0325 | n/a | n/a | n/a |
| both | text_lr | 52 | -0.0113 | -0.0237 | 0.0012 | n/a | n/a | n/a |
| both | text_lr+cal | 52 | -0.0091 | -0.0211 | 0.0029 | n/a | n/a | n/a |
| headline_only | GBM | 52 | 0.0206 | 0.0037 | 0.0374 | -2.6979 | -2.7402 | -2.6556 |
| headline_only | GBM+cal | 52 | 0.0128 | -0.0087 | 0.0344 | n/a | n/a | n/a |
| headline_only | P0 | 52 | 0.0000 | n/a | n/a | -2.6550 | -2.6828 | -2.6272 |
| headline_only | P1 | 52 | 0.0247 | 0.0132 | 0.0363 | -2.6507 | -2.6787 | -2.6228 |
| headline_only | P2 | 52 | 0.0252 | 0.0137 | 0.0368 | -2.6504 | -2.6783 | -2.6224 |
| headline_only | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 52 | 0.0201 | 0.0047 | 0.0356 | -2.6683 | -2.6990 | -2.6377 |
| headline_only | local_eb+cal | 52 | 0.0201 | 0.0046 | 0.0355 | n/a | n/a | n/a |
| headline_only | text_lr | 52 | -0.0234 | -0.0390 | -0.0078 | n/a | n/a | n/a |
| headline_only | text_lr+cal | 52 | -0.0177 | -0.0319 | -0.0036 | n/a | n/a | n/a |
| image_only | GBM | 52 | -0.0470 | -0.0798 | -0.0143 | -2.2647 | -2.2818 | -2.2475 |
| image_only | GBM+cal | 52 | -0.0045 | -0.0224 | 0.0134 | n/a | n/a | n/a |
| image_only | P0 | 52 | 0.0000 | n/a | n/a | -2.2472 | -2.2739 | -2.2205 |
| image_only | P1 | 52 | 0.0039 | -0.0006 | 0.0083 | -2.2333 | -2.2602 | -2.2064 |
| image_only | P2 | 52 | 0.0048 | 0.0004 | 0.0092 | -2.2298 | -2.2568 | -2.2028 |
| image_only | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 52 | 0.0012 | -0.0093 | 0.0117 | -2.2391 | -2.2684 | -2.2098 |
| image_only | local_eb+cal | 52 | -0.0002 | -0.0121 | 0.0117 | n/a | n/a | n/a |
| image_only | text_lr | 52 | 0.0002 | -0.0071 | 0.0075 | n/a | n/a | n/a |
| image_only | text_lr+cal | 52 | -0.0042 | -0.0142 | 0.0057 | n/a | n/a | n/a |

### Discrimination apart from skill: AUC of p_sig for the event and of the direction probability for y > 0, and the Murphy resolution term (equal-mass forecast bins: how far the observed frequency of each bin lies from the event rate; zero for a forecast that does not separate outcomes, however spread it is)

| cell | rung | auc_event | auc_event_lo | auc_event_hi | resolution_event | resolution_event_lo | resolution_event_hi | auc_direction | auc_direction_lo | auc_direction_hi | resolution_direction | resolution_direction_lo | resolution_direction_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.7717 | 0.7661 | 0.7781 | 0.0240 | 0.0227 | 0.0255 | 0.6993 | 0.6932 | 0.7057 | 0.0297 | 0.0280 | 0.0317 |
| ALL | GBM+cal | 0.7715 | 0.7658 | 0.7779 | 0.0240 | 0.0227 | 0.0256 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.7405 | 0.7334 | 0.7472 | 0.0201 | 0.0188 | 0.0215 | 0.6765 | 0.6702 | 0.6827 | 0.0263 | 0.0246 | 0.0282 |
| ALL | P1 | 0.7694 | 0.7634 | 0.7759 | 0.0238 | 0.0224 | 0.0252 | 0.6838 | 0.6773 | 0.6899 | 0.0261 | 0.0245 | 0.0280 |
| ALL | P2 | 0.7705 | 0.7647 | 0.7771 | 0.0240 | 0.0226 | 0.0255 | 0.6903 | 0.6841 | 0.6965 | 0.0273 | 0.0257 | 0.0293 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.7674 | 0.7614 | 0.7741 | 0.0234 | 0.0221 | 0.0248 | 0.6888 | 0.6823 | 0.6951 | 0.0271 | 0.0254 | 0.0290 |
| ALL | local_eb+cal | 0.7671 | 0.7614 | 0.7739 | 0.0232 | 0.0220 | 0.0247 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.7485 | 0.7420 | 0.7553 | 0.0198 | 0.0186 | 0.0211 | 0.6837 | 0.6775 | 0.6901 | 0.0258 | 0.0241 | 0.0276 |
| ALL | text_lr+cal | 0.7482 | 0.7417 | 0.7550 | 0.0198 | 0.0186 | 0.0212 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | 0.6308 | 0.6167 | 0.6444 | 0.0045 | 0.0037 | 0.0058 | 0.5693 | 0.5585 | 0.5805 | 0.0036 | 0.0029 | 0.0051 |
| both | GBM+cal | 0.6307 | 0.6166 | 0.6440 | 0.0045 | 0.0037 | 0.0058 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | 0.4930 | 0.4778 | 0.5065 | 0.0000 | 0.0001 | 0.0004 | 0.4922 | 0.4814 | 0.5046 | 0.0001 | 0.0001 | 0.0007 |
| both | P1 | 0.6075 | 0.5927 | 0.6223 | 0.0030 | 0.0024 | 0.0040 | 0.5056 | 0.4946 | 0.5167 | 0.0003 | 0.0002 | 0.0011 |
| both | P2 | 0.6115 | 0.5972 | 0.6258 | 0.0033 | 0.0026 | 0.0044 | 0.5331 | 0.5211 | 0.5456 | 0.0010 | 0.0007 | 0.0020 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5989 | 0.5853 | 0.6127 | 0.0028 | 0.0023 | 0.0039 | 0.5259 | 0.5148 | 0.5372 | 0.0008 | 0.0006 | 0.0017 |
| both | local_eb+cal | 0.5989 | 0.5855 | 0.6127 | 0.0029 | 0.0024 | 0.0040 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5384 | 0.5241 | 0.5526 | 0.0007 | 0.0005 | 0.0012 | 0.5517 | 0.5404 | 0.5630 | 0.0021 | 0.0016 | 0.0034 |
| both | text_lr+cal | 0.5381 | 0.5239 | 0.5519 | 0.0008 | 0.0006 | 0.0015 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.5983 | 0.5863 | 0.6102 | 0.0068 | 0.0056 | 0.0087 | 0.5548 | 0.5420 | 0.5686 | 0.0017 | 0.0013 | 0.0028 |
| headline_only | GBM+cal | 0.5977 | 0.5858 | 0.6097 | 0.0068 | 0.0056 | 0.0088 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.5047 | 0.4925 | 0.5170 | 0.0002 | 0.0002 | 0.0009 | 0.4956 | 0.4821 | 0.5098 | 0.0001 | 0.0001 | 0.0007 |
| headline_only | P1 | 0.5912 | 0.5801 | 0.6028 | 0.0057 | 0.0046 | 0.0076 | 0.5258 | 0.5126 | 0.5395 | 0.0007 | 0.0005 | 0.0016 |
| headline_only | P2 | 0.5922 | 0.5807 | 0.6043 | 0.0058 | 0.0047 | 0.0077 | 0.5328 | 0.5203 | 0.5467 | 0.0006 | 0.0004 | 0.0014 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5899 | 0.5767 | 0.6026 | 0.0058 | 0.0045 | 0.0078 | 0.5350 | 0.5222 | 0.5479 | 0.0011 | 0.0008 | 0.0022 |
| headline_only | local_eb+cal | 0.5892 | 0.5756 | 0.6015 | 0.0058 | 0.0046 | 0.0077 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5259 | 0.5134 | 0.5372 | 0.0007 | 0.0005 | 0.0017 | 0.5280 | 0.5149 | 0.5410 | 0.0006 | 0.0004 | 0.0014 |
| headline_only | text_lr+cal | 0.5251 | 0.5126 | 0.5361 | 0.0007 | 0.0005 | 0.0016 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.6326 | 0.6057 | 0.6579 | 0.0004 | 0.0003 | 0.0007 | 0.5824 | 0.5705 | 0.5944 | 0.0046 | 0.0036 | 0.0063 |
| image_only | GBM+cal | 0.6301 | 0.6029 | 0.6556 | 0.0003 | 0.0002 | 0.0006 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.4604 | 0.4307 | 0.4873 | 0.0000 | 0.0000 | 0.0002 | 0.4913 | 0.4793 | 0.5035 | 0.0002 | 0.0002 | 0.0008 |
| image_only | P1 | 0.5754 | 0.5488 | 0.6010 | 0.0002 | 0.0001 | 0.0003 | 0.5246 | 0.5129 | 0.5379 | 0.0007 | 0.0005 | 0.0017 |
| image_only | P2 | 0.5949 | 0.5680 | 0.6190 | 0.0002 | 0.0001 | 0.0004 | 0.5520 | 0.5410 | 0.5647 | 0.0020 | 0.0015 | 0.0032 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.5777 | 0.5465 | 0.6064 | 0.0002 | 0.0001 | 0.0004 | 0.5645 | 0.5528 | 0.5757 | 0.0026 | 0.0020 | 0.0040 |
| image_only | local_eb+cal | 0.5748 | 0.5429 | 0.6041 | 0.0002 | 0.0001 | 0.0004 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.5650 | 0.5369 | 0.5920 | 0.0002 | 0.0001 | 0.0003 | 0.5660 | 0.5544 | 0.5773 | 0.0027 | 0.0021 | 0.0041 |
| image_only | text_lr+cal | 0.5611 | 0.5330 | 0.5879 | 0.0002 | 0.0001 | 0.0003 | n/a | n/a | n/a | n/a | n/a | n/a |

### Discrimination within strata (an origin and a cell scored on its own, averaged with weights by stratum size): the pooled AUC above also credits a rung with the movement of the base rate between cells and origins, which P0 has by construction

| cell | rung | auc_event_within | auc_event_within_lo | auc_event_within_hi | resolution_event_within | resolution_event_within_lo | resolution_event_within_hi | auc_direction_within | auc_direction_within_lo | auc_direction_within_hi | resolution_direction_within |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.6216 | 0.6105 | 0.6325 | 0.0053 | 0.0060 | 0.0077 | 0.5704 | 0.5631 | 0.5776 | 0.0057 |
| ALL | GBM+cal | 0.6216 | 0.6105 | 0.6325 | 0.0053 | 0.0060 | 0.0077 | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| ALL | P1 | 0.5939 | 0.5825 | 0.6047 | 0.0043 | 0.0051 | 0.0065 | 0.5221 | 0.5152 | 0.5294 | 0.0028 |
| ALL | P2 | 0.6019 | 0.5911 | 0.6132 | 0.0044 | 0.0052 | 0.0066 | 0.5404 | 0.5336 | 0.5473 | 0.0034 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.5887 | 0.5766 | 0.6003 | 0.0043 | 0.0050 | 0.0066 | 0.5419 | 0.5351 | 0.5496 | 0.0036 |
| ALL | local_eb+cal | 0.5887 | 0.5766 | 0.6003 | 0.0043 | 0.0050 | 0.0066 | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.5467 | 0.5357 | 0.5579 | 0.0020 | 0.0030 | 0.0041 | 0.5492 | 0.5425 | 0.5565 | 0.0040 |
| ALL | text_lr+cal | 0.5467 | 0.5357 | 0.5579 | 0.0020 | 0.0030 | 0.0041 | n/a | n/a | n/a | n/a |
| both | GBM | 0.6308 | 0.6174 | 0.6442 | 0.0062 | 0.0065 | 0.0089 | 0.5714 | 0.5603 | 0.5829 | 0.0062 |
| both | GBM+cal | 0.6308 | 0.6174 | 0.6442 | 0.0062 | 0.0065 | 0.0089 | n/a | n/a | n/a | n/a |
| both | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| both | P1 | 0.6085 | 0.5937 | 0.6240 | 0.0047 | 0.0051 | 0.0074 | 0.5104 | 0.4987 | 0.5227 | 0.0034 |
| both | P2 | 0.6128 | 0.5979 | 0.6276 | 0.0050 | 0.0053 | 0.0077 | 0.5341 | 0.5213 | 0.5460 | 0.0038 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5997 | 0.5862 | 0.6132 | 0.0043 | 0.0048 | 0.0069 | 0.5253 | 0.5146 | 0.5367 | 0.0030 |
| both | local_eb+cal | 0.5997 | 0.5862 | 0.6132 | 0.0043 | 0.0048 | 0.0069 | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5383 | 0.5238 | 0.5523 | 0.0022 | 0.0030 | 0.0046 | 0.5522 | 0.5406 | 0.5638 | 0.0045 |
| both | text_lr+cal | 0.5383 | 0.5238 | 0.5523 | 0.0022 | 0.0030 | 0.0046 | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.5976 | 0.5859 | 0.6093 | 0.0092 | 0.0100 | 0.0139 | 0.5557 | 0.5429 | 0.5699 | 0.0033 |
| headline_only | GBM+cal | 0.5976 | 0.5859 | 0.6093 | 0.0092 | 0.0100 | 0.0139 | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| headline_only | P1 | 0.5902 | 0.5791 | 0.6017 | 0.0079 | 0.0087 | 0.0124 | 0.5278 | 0.5153 | 0.5415 | 0.0022 |
| headline_only | P2 | 0.5914 | 0.5800 | 0.6034 | 0.0076 | 0.0085 | 0.0120 | 0.5358 | 0.5236 | 0.5490 | 0.0020 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5890 | 0.5759 | 0.6023 | 0.0082 | 0.0088 | 0.0128 | 0.5361 | 0.5234 | 0.5492 | 0.0026 |
| headline_only | local_eb+cal | 0.5890 | 0.5759 | 0.6023 | 0.0082 | 0.0088 | 0.0128 | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5258 | 0.5131 | 0.5369 | 0.0033 | 0.0046 | 0.0072 | 0.5288 | 0.5155 | 0.5422 | 0.0022 |
| headline_only | text_lr+cal | 0.5258 | 0.5131 | 0.5369 | 0.0033 | 0.0046 | 0.0072 | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.6352 | 0.6086 | 0.6613 | 0.0007 | 0.0008 | 0.0014 | 0.5834 | 0.5718 | 0.5952 | 0.0076 |
| image_only | GBM+cal | 0.6352 | 0.6086 | 0.6613 | 0.0007 | 0.0008 | 0.0014 | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| image_only | P1 | 0.5824 | 0.5538 | 0.6101 | 0.0006 | 0.0007 | 0.0012 | 0.5286 | 0.5159 | 0.5412 | 0.0026 |
| image_only | P2 | 0.6008 | 0.5728 | 0.6275 | 0.0007 | 0.0008 | 0.0014 | 0.5513 | 0.5402 | 0.5638 | 0.0043 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.5771 | 0.5466 | 0.6074 | 0.0007 | 0.0008 | 0.0014 | 0.5645 | 0.5528 | 0.5759 | 0.0050 |
| image_only | local_eb+cal | 0.5771 | 0.5466 | 0.6074 | 0.0007 | 0.0008 | 0.0014 | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.5755 | 0.5475 | 0.6040 | 0.0005 | 0.0007 | 0.0012 | 0.5659 | 0.5544 | 0.5773 | 0.0051 |
| image_only | text_lr+cal | 0.5755 | 0.5475 | 0.6040 | 0.0005 | 0.0007 | 0.0012 | n/a | n/a | n/a | n/a |

### Sensitivity of the event definition: the same forecasts scored against y > z s_star on the planned standard error (the headline uses the realized one)

| cell | rung | event_rate_planned | p_sig_mean | brier_planned | brier_base_planned | brier_skill_planned | brier_skill_planned_lo | brier_skill_planned_hi |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.2031 | 0.2131 | 0.1384 | 0.1408 | 0.0177 | 0.0116 | 0.0236 |
| ALL | GBM+cal | 0.2031 | 0.2083 | 0.1383 | 0.1408 | 0.0177 | 0.0109 | 0.0248 |
| ALL | P0 | 0.2031 | 0.2042 | 0.1408 | 0.1408 | 0.0000 | 0.0000 | 0.0000 |
| ALL | P1 | 0.2031 | 0.2016 | 0.1378 | 0.1408 | 0.0215 | 0.0177 | 0.0251 |
| ALL | P2 | 0.2031 | 0.2010 | 0.1377 | 0.1408 | 0.0224 | 0.0186 | 0.0262 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.2031 | 0.1983 | 0.1383 | 0.1408 | 0.0179 | 0.0126 | 0.0232 |
| ALL | local_eb+cal | 0.2031 | 0.2062 | 0.1384 | 0.1408 | 0.0176 | 0.0123 | 0.0229 |
| ALL | text_lr | 0.2031 | 0.2040 | 0.1432 | 0.1408 | -0.0168 | -0.0222 | -0.0114 |
| ALL | text_lr+cal | 0.2031 | 0.2072 | 0.1427 | 0.1408 | -0.0134 | -0.0184 | -0.0085 |
| both | GBM | 0.1794 | 0.1940 | 0.1428 | 0.1473 | 0.0303 | 0.0228 | 0.0371 |
| both | GBM+cal | 0.1794 | 0.1763 | 0.1427 | 0.1473 | 0.0310 | 0.0227 | 0.0389 |
| both | P0 | 0.1794 | 0.1757 | 0.1473 | 0.1473 | 0.0000 | 0.0000 | 0.0000 |
| both | P1 | 0.1794 | 0.1780 | 0.1442 | 0.1473 | 0.0211 | 0.0155 | 0.0260 |
| both | P2 | 0.1794 | 0.1778 | 0.1439 | 0.1473 | 0.0227 | 0.0171 | 0.0280 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.1794 | 0.1755 | 0.1445 | 0.1473 | 0.0189 | 0.0118 | 0.0259 |
| both | local_eb+cal | 0.1794 | 0.1854 | 0.1446 | 0.1473 | 0.0185 | 0.0111 | 0.0259 |
| both | text_lr | 0.1794 | 0.1749 | 0.1489 | 0.1473 | -0.0113 | -0.0175 | -0.0046 |
| both | text_lr+cal | 0.1794 | 0.1847 | 0.1486 | 0.1473 | -0.0091 | -0.0154 | -0.0027 |
| headline_only | GBM | 0.3969 | 0.3659 | 0.2345 | 0.2394 | 0.0206 | 0.0117 | 0.0296 |
| headline_only | GBM+cal | 0.3969 | 0.3982 | 0.2363 | 0.2394 | 0.0128 | 0.0013 | 0.0238 |
| headline_only | P0 | 0.3969 | 0.4038 | 0.2394 | 0.2394 | 0.0000 | 0.0000 | 0.0000 |
| headline_only | P1 | 0.3969 | 0.3947 | 0.2335 | 0.2394 | 0.0247 | 0.0187 | 0.0310 |
| headline_only | P2 | 0.3969 | 0.3943 | 0.2334 | 0.2394 | 0.0252 | 0.0190 | 0.0314 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.3969 | 0.3887 | 0.2346 | 0.2394 | 0.0201 | 0.0111 | 0.0284 |
| headline_only | local_eb+cal | 0.3969 | 0.3982 | 0.2346 | 0.2394 | 0.0201 | 0.0112 | 0.0281 |
| headline_only | text_lr | 0.3969 | 0.4036 | 0.2450 | 0.2394 | -0.0234 | -0.0323 | -0.0155 |
| headline_only | text_lr+cal | 0.3969 | 0.3926 | 0.2437 | 0.2394 | -0.0177 | -0.0253 | -0.0105 |
| image_only | GBM | 0.0414 | 0.0861 | 0.0416 | 0.0397 | -0.0470 | -0.0663 | -0.0307 |
| image_only | GBM+cal | 0.0414 | 0.0590 | 0.0399 | 0.0397 | -0.0045 | -0.0139 | 0.0044 |
| image_only | P0 | 0.0414 | 0.0419 | 0.0397 | 0.0397 | 0.0000 | 0.0000 | 0.0000 |
| image_only | P1 | 0.0414 | 0.0407 | 0.0395 | 0.0397 | 0.0039 | 0.0015 | 0.0062 |
| image_only | P2 | 0.0414 | 0.0394 | 0.0395 | 0.0397 | 0.0048 | 0.0024 | 0.0070 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.0414 | 0.0392 | 0.0396 | 0.0397 | 0.0012 | -0.0045 | 0.0070 |
| image_only | local_eb+cal | 0.0414 | 0.0435 | 0.0397 | 0.0397 | -0.0002 | -0.0067 | 0.0060 |
| image_only | text_lr | 0.0414 | 0.0424 | 0.0397 | 0.0397 | 0.0002 | -0.0037 | 0.0040 |
| image_only | text_lr+cal | 0.0414 | 0.0526 | 0.0399 | 0.0397 | -0.0042 | -0.0096 | 0.0008 |

### Paired log score difference from P1 on the same rows (nats per row, 90 percent by-test interval; negative means the rung scores below P1)

| cell | rung | logscore_vs_p1 | logscore_vs_p1_lo | logscore_vs_p1_hi | logscore_vs_p1_adjusted_lo | logscore_vs_p1_adjusted_hi | n_paired |
|---|---|---|---|---|---|---|---|
| ALL | GBM | -0.0243 | -0.0281 | -0.0206 | -0.0313 | -0.0172 | 19766 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | P0 | -0.0094 | -0.0109 | -0.0078 | -0.0124 | -0.0065 | 19766 |
| ALL | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 19766 |
| ALL | P2 | 0.0018 | 0.0014 | 0.0023 | 0.0010 | 0.0026 | 19766 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | local_eb | -0.0119 | -0.0146 | -0.0089 | -0.0173 | -0.0065 | 19766 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | GBM | 0.0041 | 0.0010 | 0.0072 | -0.0017 | 0.0100 | 6788 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | P0 | -0.0100 | -0.0127 | -0.0070 | -0.0153 | -0.0047 | 6788 |
| both | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 6788 |
| both | P2 | 0.0015 | 0.0007 | 0.0023 | 0.0000 | 0.0029 | 6788 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| both | local_eb | -0.0126 | -0.0163 | -0.0083 | -0.0203 | -0.0049 | 6788 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | GBM | -0.0472 | -0.0561 | -0.0385 | -0.0631 | -0.0313 | 6354 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | P0 | -0.0043 | -0.0062 | -0.0024 | -0.0077 | -0.0008 | 6354 |
| headline_only | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 6354 |
| headline_only | P2 | 0.0004 | 0.0001 | 0.0007 | -0.0001 | 0.0009 | 6354 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | local_eb | -0.0176 | -0.0227 | -0.0124 | -0.0272 | -0.0081 | 6354 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | GBM | -0.0313 | -0.0373 | -0.0260 | -0.0424 | -0.0202 | 6624 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | P0 | -0.0138 | -0.0175 | -0.0101 | -0.0208 | -0.0069 | 6624 |
| image_only | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 6624 |
| image_only | P2 | 0.0035 | 0.0025 | 0.0044 | 0.0017 | 0.0054 | 6624 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | local_eb | -0.0058 | -0.0108 | -0.0012 | -0.0153 | 0.0037 | 6624 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |

### The gate read with the group's own dependence: rows per test and within-test correlation of the group against those the nearest simulated gate assumed, and the gate sizes scaled to first order by the information per test (an approximation; docs/method.md call 205)

| cell | rung | event_rate | gate_cell_rows_per_test | gate_cell_icc | gate_assumed_rows_per_test | gate_assumed_icc | gate_cell_n_200 | gate_cell_n_400 | decidable_by_tests_cell |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | GBM+cal | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | P0 | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | P1 | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | P2 | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | always_reference | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | always_variant | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb+cal | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr+cal | 0.2031 | 2.0000 | 0.1403 | 5.0000 | 0.6700 | 155 | 310 | decidable at skill 0.20 and 0.10 |
| both | GBM | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | GBM+cal | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | P0 | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | P1 | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | P2 | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | always_reference | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | always_variant | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | local_eb | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | local_eb+cal | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | text_lr | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| both | text_lr+cal | 0.1794 | 2.0000 | 0.0115 | 5.0000 | 0.6700 | 138 | 275 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM+cal | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | P0 | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | P1 | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | P2 | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | always_reference | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | always_variant | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb+cal | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr+cal | 0.3969 | 2.0000 | 0.0098 | 3.5000 | 0.1300 | 101 | 201 | decidable at skill 0.20 and 0.10 |
| image_only | GBM | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | GBM+cal | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | P0 | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | P1 | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | P2 | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | always_reference | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | always_variant | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb+cal | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr+cal | 0.0414 | 2.0000 | 0.0254 | 3.5000 | 0.1300 | 237 | 339 | decidable at skill 0.20 and 0.10 |

### Direction accuracy and coverage of the intervals for y

| cell | rung | direction_accuracy | direction_accuracy_lo | direction_accuracy_hi | n_decisive | direction_accuracy_decisive | direction_ceiling | coverage_80 | coverage_80_lo | coverage_80_hi | coverage_90 | coverage_90_lo | coverage_90_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.6585 | 0.6526 | 0.6641 | 6423 | 0.7825 | 0.8240 | 0.8126 | 0.8075 | 0.8168 | 0.9008 | 0.8969 | 0.9041 |
| ALL | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8240 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.6593 | 0.6532 | 0.6649 | 6423 | 0.7834 | 0.8240 | 0.7983 | 0.7933 | 0.8025 | 0.9026 | 0.8991 | 0.9057 |
| ALL | P1 | 0.6593 | 0.6532 | 0.6649 | 6423 | 0.7834 | 0.8240 | 0.8004 | 0.7955 | 0.8048 | 0.9002 | 0.8965 | 0.9035 |
| ALL | P2 | 0.6593 | 0.6531 | 0.6648 | 6423 | 0.7834 | 0.8240 | 0.8016 | 0.7969 | 0.8057 | 0.9008 | 0.8970 | 0.9040 |
| ALL | always_reference | 0.4526 | 0.4465 | 0.4591 | 6423 | 0.3751 | 0.8240 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | 0.5474 | 0.5409 | 0.5535 | 6423 | 0.6249 | 0.8240 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.6564 | 0.6509 | 0.6623 | 6423 | 0.7820 | 0.8240 | 0.7924 | 0.7874 | 0.7971 | 0.8921 | 0.8884 | 0.8955 |
| ALL | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8240 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.6490 | 0.6433 | 0.6549 | 6423 | 0.7648 | 0.8240 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8240 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | 0.5807 | 0.5710 | 0.5914 | 1864 | 0.6518 | 0.8064 | 0.8324 | 0.8241 | 0.8407 | 0.9241 | 0.9191 | 0.9297 |
| both | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8064 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | 0.5824 | 0.5722 | 0.5927 | 1864 | 0.6534 | 0.8064 | 0.8024 | 0.7943 | 0.8105 | 0.9056 | 0.9004 | 0.9118 |
| both | P1 | 0.5824 | 0.5722 | 0.5927 | 1864 | 0.6534 | 0.8064 | 0.8027 | 0.7945 | 0.8114 | 0.9025 | 0.8967 | 0.9090 |
| both | P2 | 0.5825 | 0.5726 | 0.5933 | 1864 | 0.6534 | 0.8064 | 0.8038 | 0.7957 | 0.8126 | 0.9041 | 0.8982 | 0.9103 |
| both | always_reference | 0.4176 | 0.4073 | 0.4278 | 1864 | 0.3466 | 0.8064 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | 0.5824 | 0.5722 | 0.5927 | 1864 | 0.6534 | 0.8064 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5742 | 0.5645 | 0.5844 | 1864 | 0.6486 | 0.8064 | 0.7963 | 0.7878 | 0.8045 | 0.8935 | 0.8873 | 0.8997 |
| both | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8064 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5701 | 0.5601 | 0.5800 | 1864 | 0.6202 | 0.8064 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8064 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.7332 | 0.7235 | 0.7425 | 2993 | 0.8423 | 0.8787 | 0.7077 | 0.6988 | 0.7172 | 0.8160 | 0.8078 | 0.8237 |
| headline_only | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8787 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.7334 | 0.7236 | 0.7428 | 2993 | 0.8426 | 0.8787 | 0.7945 | 0.7856 | 0.8028 | 0.8996 | 0.8930 | 0.9056 |
| headline_only | P1 | 0.7334 | 0.7236 | 0.7428 | 2993 | 0.8426 | 0.8787 | 0.7986 | 0.7902 | 0.8067 | 0.8996 | 0.8933 | 0.9059 |
| headline_only | P2 | 0.7334 | 0.7236 | 0.7428 | 2993 | 0.8426 | 0.8787 | 0.7989 | 0.7907 | 0.8071 | 0.8990 | 0.8924 | 0.9056 |
| headline_only | always_reference | 0.2666 | 0.2572 | 0.2764 | 2993 | 0.1574 | 0.8787 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | 0.7334 | 0.7236 | 0.7428 | 2993 | 0.8426 | 0.8787 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.7334 | 0.7236 | 0.7428 | 2993 | 0.8426 | 0.8787 | 0.7882 | 0.7792 | 0.7962 | 0.8906 | 0.8835 | 0.8969 |
| headline_only | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8787 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.7277 | 0.7183 | 0.7373 | 2993 | 0.8343 | 0.8787 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8787 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.6665 | 0.6567 | 0.6756 | 1566 | 0.8238 | 0.7897 | 0.8928 | 0.8871 | 0.8990 | 0.9582 | 0.9543 | 0.9621 |
| image_only | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.7897 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.6670 | 0.6571 | 0.6759 | 1566 | 0.8250 | 0.7897 | 0.7977 | 0.7897 | 0.8060 | 0.9023 | 0.8972 | 0.9078 |
| image_only | P1 | 0.6670 | 0.6571 | 0.6759 | 1566 | 0.8250 | 0.7897 | 0.7997 | 0.7921 | 0.8080 | 0.8984 | 0.8934 | 0.9044 |
| image_only | P2 | 0.6670 | 0.6571 | 0.6759 | 1566 | 0.8250 | 0.7897 | 0.8019 | 0.7945 | 0.8102 | 0.8993 | 0.8942 | 0.9050 |
| image_only | always_reference | 0.6670 | 0.6571 | 0.6759 | 1566 | 0.8250 | 0.7897 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | 0.3330 | 0.3241 | 0.3429 | 1566 | 0.1750 | 0.7897 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.6668 | 0.6570 | 0.6757 | 1566 | 0.8250 | 0.7897 | 0.7926 | 0.7852 | 0.8012 | 0.8922 | 0.8869 | 0.8980 |
| image_only | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.7897 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.6543 | 0.6442 | 0.6641 | 1566 | 0.8040 | 0.7897 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.7897 | n/a | n/a | n/a | n/a | n/a | n/a |

### The same scores on non-abstained rows only

| cell | rung | logscore_nonabstained | logscore_nonabstained_lo | logscore_nonabstained_hi | crps_nonabstained | crps_nonabstained_lo | crps_nonabstained_hi | brier_nonabstained | brier_nonabstained_lo | brier_nonabstained_hi | direction_accuracy_nonabstained | direction_accuracy_nonabstained_lo | direction_accuracy_nonabstained_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | -2.4414 | -2.4524 | -2.4319 | 1.5599 | 1.5440 | 1.5768 | 0.1382 | 0.1353 | 0.1410 | 0.6575 | 0.6514 | 0.6639 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1382 | 0.1351 | 0.1412 | n/a | n/a | n/a |
| ALL | P0 | -2.4289 | -2.4394 | -2.4194 | 1.5658 | 1.5508 | 1.5818 | 0.1412 | 0.1382 | 0.1442 | 0.6590 | 0.6527 | 0.6655 |
| ALL | P1 | -2.4191 | -2.4295 | -2.4096 | 1.5621 | 1.5473 | 1.5784 | 0.1381 | 0.1351 | 0.1411 | 0.6590 | 0.6527 | 0.6655 |
| ALL | P2 | -2.4169 | -2.4275 | -2.4075 | 1.5590 | 1.5443 | 1.5755 | 0.1380 | 0.1350 | 0.1410 | 0.6590 | 0.6528 | 0.6654 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4501 | 0.4431 | 0.4569 |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5499 | 0.5431 | 0.5569 |
| ALL | local_eb | -2.4299 | -2.4409 | -2.4200 | 1.5653 | 1.5498 | 1.5821 | 0.1383 | 0.1352 | 0.1413 | 0.6560 | 0.6498 | 0.6623 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1384 | 0.1353 | 0.1413 | n/a | n/a | n/a |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.1432 | 0.1402 | 0.1463 | 0.6500 | 0.6442 | 0.6562 |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1428 | 0.1398 | 0.1458 | n/a | n/a | n/a |
| both | GBM | -2.3746 | -2.3877 | -2.3589 | 1.4686 | 1.4420 | 1.4914 | 0.1431 | 0.1382 | 0.1478 | 0.5827 | 0.5723 | 0.5944 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1430 | 0.1379 | 0.1481 | n/a | n/a | n/a |
| both | P0 | -2.3901 | -2.4065 | -2.3716 | 1.4854 | 1.4574 | 1.5097 | 0.1474 | 0.1419 | 0.1527 | 0.5865 | 0.5756 | 0.5982 |
| both | P1 | -2.3797 | -2.3949 | -2.3626 | 1.4819 | 1.4548 | 1.5064 | 0.1445 | 0.1394 | 0.1497 | 0.5865 | 0.5756 | 0.5982 |
| both | P2 | -2.3779 | -2.3929 | -2.3611 | 1.4794 | 1.4526 | 1.5038 | 0.1443 | 0.1392 | 0.1495 | 0.5865 | 0.5757 | 0.5982 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4135 | 0.4018 | 0.4244 |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5865 | 0.5756 | 0.5982 |
| both | local_eb | -2.3924 | -2.4073 | -2.3744 | 1.4898 | 1.4635 | 1.5132 | 0.1449 | 0.1397 | 0.1501 | 0.5780 | 0.5671 | 0.5893 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1450 | 0.1399 | 0.1500 | n/a | n/a | n/a |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.1494 | 0.1437 | 0.1549 | 0.5766 | 0.5660 | 0.5875 |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.1491 | 0.1435 | 0.1543 | n/a | n/a | n/a |
| headline_only | GBM | -2.7012 | -2.7277 | -2.6758 | 1.9507 | 1.9150 | 1.9873 | 0.2334 | 0.2297 | 0.2367 | 0.7346 | 0.7232 | 0.7453 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.2352 | 0.2315 | 0.2386 | n/a | n/a | n/a |
| headline_only | P0 | -2.6575 | -2.6748 | -2.6420 | 1.9409 | 1.9102 | 1.9738 | 0.2396 | 0.2373 | 0.2416 | 0.7346 | 0.7232 | 0.7453 |
| headline_only | P1 | -2.6533 | -2.6698 | -2.6377 | 1.9385 | 1.9076 | 1.9723 | 0.2332 | 0.2302 | 0.2357 | 0.7346 | 0.7232 | 0.7453 |
| headline_only | P2 | -2.6528 | -2.6692 | -2.6373 | 1.9376 | 1.9066 | 1.9708 | 0.2331 | 0.2301 | 0.2356 | 0.7346 | 0.7232 | 0.7453 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2654 | 0.2547 | 0.2768 |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.7346 | 0.7232 | 0.7453 |
| headline_only | local_eb | -2.6685 | -2.6867 | -2.6510 | 1.9467 | 1.9141 | 1.9810 | 0.2334 | 0.2301 | 0.2364 | 0.7346 | 0.7232 | 0.7453 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.2335 | 0.2303 | 0.2363 | n/a | n/a | n/a |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.2439 | 0.2410 | 0.2470 | 0.7301 | 0.7194 | 0.7404 |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.2427 | 0.2396 | 0.2457 | n/a | n/a | n/a |
| image_only | GBM | -2.2642 | -2.2743 | -2.2538 | 1.2841 | 1.2660 | 1.3016 | 0.0436 | 0.0400 | 0.0472 | 0.6608 | 0.6490 | 0.6708 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0420 | 0.0383 | 0.0460 | n/a | n/a | n/a |
| image_only | P0 | -2.2526 | -2.2687 | -2.2371 | 1.2935 | 1.2736 | 1.3137 | 0.0421 | 0.0381 | 0.0461 | 0.6614 | 0.6497 | 0.6711 |
| image_only | P1 | -2.2383 | -2.2536 | -2.2225 | 1.2886 | 1.2688 | 1.3086 | 0.0419 | 0.0380 | 0.0459 | 0.6614 | 0.6497 | 0.6711 |
| image_only | P2 | -2.2339 | -2.2492 | -2.2176 | 1.2828 | 1.2618 | 1.3030 | 0.0419 | 0.0380 | 0.0458 | 0.6614 | 0.6497 | 0.6711 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.6614 | 0.6497 | 0.6711 |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.3386 | 0.3289 | 0.3503 |
| image_only | local_eb | -2.2428 | -2.2599 | -2.2253 | 1.2823 | 1.2610 | 1.3025 | 0.0420 | 0.0382 | 0.0460 | 0.6610 | 0.6493 | 0.6711 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0420 | 0.0382 | 0.0460 | n/a | n/a | n/a |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.0420 | 0.0382 | 0.0461 | 0.6488 | 0.6374 | 0.6590 |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0421 | 0.0383 | 0.0460 | n/a | n/a | n/a |

### Other columns

| cell | rung | resolution_direction_within_lo | resolution_direction_within_hi | latent_rho | gate_cell_scale |
|---|---|---|---|---|---|
| ALL | GBM | 0.0072 | 0.0090 | 0.0000 | 0.7747 |
| ALL | GBM+cal | n/a | n/a | 0.0420 | 0.7747 |
| ALL | P0 | 0.0000 | 0.0000 | 0.0297 | 0.7747 |
| ALL | P1 | 0.0044 | 0.0057 | 0.0393 | 0.7747 |
| ALL | P2 | 0.0050 | 0.0065 | 0.0438 | 0.7747 |
| ALL | always_reference | n/a | n/a | n/a | 0.7747 |
| ALL | always_variant | n/a | n/a | n/a | 0.7747 |
| ALL | local_eb | 0.0052 | 0.0067 | 0.0849 | 0.7747 |
| ALL | local_eb+cal | n/a | n/a | 0.0253 | 0.7747 |
| ALL | text_lr | 0.0056 | 0.0071 | 0.1333 | 0.7747 |
| ALL | text_lr+cal | n/a | n/a | 0.0552 | 0.7747 |
| both | GBM | 0.0070 | 0.0102 | 0.0000 | 0.6871 |
| both | GBM+cal | n/a | n/a | 0.0747 | 0.6871 |
| both | P0 | 0.0000 | 0.0000 | 0.0701 | 0.6871 |
| both | P1 | 0.0046 | 0.0072 | 0.0433 | 0.6871 |
| both | P2 | 0.0050 | 0.0079 | 0.0432 | 0.6871 |
| both | always_reference | n/a | n/a | n/a | 0.6871 |
| both | always_variant | n/a | n/a | n/a | 0.6871 |
| both | local_eb | 0.0043 | 0.0068 | 0.0858 | 0.6871 |
| both | local_eb+cal | n/a | n/a | 0.0000 | 0.6871 |
| both | text_lr | 0.0056 | 0.0086 | 0.1576 | 0.6871 |
| both | text_lr+cal | n/a | n/a | 0.0501 | 0.6871 |
| headline_only | GBM | 0.0043 | 0.0067 | 0.1263 | 1.3338 |
| headline_only | GBM+cal | n/a | n/a | 0.1378 | 1.3338 |
| headline_only | P0 | 0.0000 | 0.0000 | 0.0121 | 1.3338 |
| headline_only | P1 | 0.0035 | 0.0055 | 0.0289 | 1.3338 |
| headline_only | P2 | 0.0033 | 0.0052 | 0.0280 | 1.3338 |
| headline_only | always_reference | n/a | n/a | n/a | 1.3338 |
| headline_only | always_variant | n/a | n/a | n/a | 1.3338 |
| headline_only | local_eb | 0.0037 | 0.0058 | 0.0662 | 1.3338 |
| headline_only | local_eb+cal | n/a | n/a | 0.0524 | 1.3338 |
| headline_only | text_lr | 0.0034 | 0.0054 | 0.1328 | 1.3338 |
| headline_only | text_lr+cal | n/a | n/a | 0.1267 | 1.3338 |
| image_only | GBM | 0.0082 | 0.0116 | 0.0000 | 1.3543 |
| image_only | GBM+cal | n/a | n/a | 0.0000 | 1.3543 |
| image_only | P0 | 0.0000 | 0.0000 | 0.1141 | 1.3543 |
| image_only | P1 | 0.0039 | 0.0062 | 0.2209 | 1.3543 |
| image_only | P2 | 0.0054 | 0.0081 | 0.3030 | 1.3543 |
| image_only | always_reference | n/a | n/a | n/a | 1.3543 |
| image_only | always_variant | n/a | n/a | n/a | 1.3543 |
| image_only | local_eb | 0.0060 | 0.0089 | 0.3858 | 1.3543 |
| image_only | local_eb+cal | n/a | n/a | 0.0000 | 1.3543 |
| image_only | text_lr | 0.0062 | 0.0089 | 0.0984 | 1.3543 |
| image_only | text_lr+cal | n/a | n/a | 0.0000 | 1.3543 |

## P2 selection by cell

How lam (the weight on precedents), the bandwidth multiplier and the recency half-life were chosen, summarised over the origins. `share_lambda_zero` is the share of origins where the selection gave up on precedents and P2 equalled P1 in that cell. `guard` is the admission guard multiplier: lam above zero is used only when its out-of-sample log-score gain over lam 0 minus that many standard errors (across tests) is above zero, the ladder admission rule made operational. `share_guard_held` is the share of origins where the guard forced lam to 0 although the earlier rule would have used the precedents; `gain_mean` and `gain_se_mean` are the gain of the best candidate and its standard error, averaged over origins. The per-origin values are in the JSON under `p2_selection`.

| rung | cell | selection | origins | lambda_mean | lambda_min | lambda_max | share_lambda_zero | guard | share_guard_held | lambda_unguarded_mean | gain_mean | gain_se_mean | bandwidth_mult_mean | half_life_days_median | share_no_decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | both | forward | 8 | 0.4000 | 0.0000 | 0.7000 | 0.2500 | 2.0000 | 0.1250 | 0.4375 | 0.0027 | 0.0011 | 0.3438 | n/a | 1.0000 |
| P2 | headline_only | forward | 8 | 0.1125 | 0.0000 | 0.3000 | 0.6250 | 2.0000 | 0.3750 | 0.1750 | 0.0012 | 0.0010 | 0.3125 | n/a | 1.0000 |
| P2 | image_only | forward | 8 | 0.4250 | 0.0000 | 0.9000 | 0.3750 | 2.0000 | 0.3750 | 0.5125 | 0.0046 | 0.0019 | 0.2500 | n/a | 1.0000 |

## Abstention by trigger

Counts of rows that fired each trigger (a row can fire several).

| cell | n | rate | support | novelty | reliability | instability |
|---|---|---|---|---|---|---|
| ALL | 19766 | 0.1798 | 0 | 1257 | 2482 | 102 |
| both | 6788 | 0.1806 | 0 | 443 | 894 | 16 |
| headline_only | 6354 | 0.1865 | 0 | 381 | 776 | 86 |
| image_only | 6624 | 0.1726 | 0 | 433 | 812 | 0 |

Never fired in this backtest: support. After the burn-in origin the reliability trigger fired on 0 rows, so no cell was marked drifted and every reliability abstention is the missing report at the burn-in origin.

## Origins

The first scored origin is the burn-in origin.

| origin | n_scored | n_tests | abstention_rate | logscore | burn_in |
|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | 2482 | 1241 | 1.0000 | -2.3968 | yes |
| 2013-07-01T00:00:00+00:00 | 2528 | 1264 | 0.1388 | -2.4349 | no |
| 2013-10-01T00:00:00+00:00 | 2512 | 1256 | 0.0788 | -2.4240 | no |
| 2014-01-01T00:00:00+00:00 | 2248 | 1124 | 0.0516 | -2.4131 | no |
| 2014-04-01T00:00:00+00:00 | 2454 | 1227 | 0.0355 | -2.4152 | no |
| 2014-07-01T00:00:00+00:00 | 2526 | 1263 | 0.0487 | -2.4112 | no |
| 2014-10-01T00:00:00+00:00 | 2470 | 1235 | 0.0441 | -2.4230 | no |
| 2015-01-01T00:00:00+00:00 | 2546 | 1273 | 0.0346 | -2.4120 | no |

### Log score by origin with 90 percent intervals

| origin | rung | n | logscore | logscore_lo | logscore_hi |
|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | GBM | 2482 | -2.4276 | -2.4537 | -2.4054 |
| 2013-04-01T00:00:00+00:00 | P0 | 2482 | -2.4043 | -2.4271 | -2.3820 |
| 2013-04-01T00:00:00+00:00 | P1 | 2482 | -2.3968 | -2.4198 | -2.3749 |
| 2013-04-01T00:00:00+00:00 | P2 | 2482 | -2.3968 | -2.4198 | -2.3749 |
| 2013-04-01T00:00:00+00:00 | local_eb | 2482 | -2.4130 | -2.4354 | -2.3897 |
| 2013-07-01T00:00:00+00:00 | GBM | 2528 | -2.4548 | -2.4821 | -2.4318 |
| 2013-07-01T00:00:00+00:00 | P0 | 2528 | -2.4424 | -2.4676 | -2.4232 |
| 2013-07-01T00:00:00+00:00 | P1 | 2528 | -2.4349 | -2.4613 | -2.4141 |
| 2013-07-01T00:00:00+00:00 | P2 | 2528 | -2.4349 | -2.4613 | -2.4141 |
| 2013-07-01T00:00:00+00:00 | local_eb | 2528 | -2.4501 | -2.4750 | -2.4284 |
| 2013-10-01T00:00:00+00:00 | GBM | 2512 | -2.4417 | -2.4680 | -2.4165 |
| 2013-10-01T00:00:00+00:00 | P0 | 2512 | -2.4396 | -2.4675 | -2.4136 |
| 2013-10-01T00:00:00+00:00 | P1 | 2512 | -2.4253 | -2.4511 | -2.4009 |
| 2013-10-01T00:00:00+00:00 | P2 | 2512 | -2.4240 | -2.4505 | -2.3994 |
| 2013-10-01T00:00:00+00:00 | local_eb | 2512 | -2.4345 | -2.4618 | -2.4080 |
| 2014-01-01T00:00:00+00:00 | GBM | 2248 | -2.4498 | -2.4836 | -2.4139 |
| 2014-01-01T00:00:00+00:00 | P0 | 2248 | -2.4248 | -2.4544 | -2.3898 |
| 2014-01-01T00:00:00+00:00 | P1 | 2248 | -2.4147 | -2.4425 | -2.3790 |
| 2014-01-01T00:00:00+00:00 | P2 | 2248 | -2.4131 | -2.4409 | -2.3769 |
| 2014-01-01T00:00:00+00:00 | local_eb | 2248 | -2.4216 | -2.4522 | -2.3843 |
| 2014-04-01T00:00:00+00:00 | GBM | 2454 | -2.4349 | -2.4647 | -2.4116 |
| 2014-04-01T00:00:00+00:00 | P0 | 2454 | -2.4283 | -2.4527 | -2.4047 |
| 2014-04-01T00:00:00+00:00 | P1 | 2454 | -2.4176 | -2.4439 | -2.3948 |
| 2014-04-01T00:00:00+00:00 | P2 | 2454 | -2.4152 | -2.4403 | -2.3924 |
| 2014-04-01T00:00:00+00:00 | local_eb | 2454 | -2.4287 | -2.4584 | -2.4035 |
| 2014-07-01T00:00:00+00:00 | GBM | 2526 | -2.4419 | -2.4724 | -2.4174 |
| 2014-07-01T00:00:00+00:00 | P0 | 2526 | -2.4217 | -2.4471 | -2.3996 |
| 2014-07-01T00:00:00+00:00 | P1 | 2526 | -2.4146 | -2.4401 | -2.3939 |
| 2014-07-01T00:00:00+00:00 | P2 | 2526 | -2.4112 | -2.4376 | -2.3899 |
| 2014-07-01T00:00:00+00:00 | local_eb | 2526 | -2.4275 | -2.4535 | -2.4072 |
| 2014-10-01T00:00:00+00:00 | GBM | 2470 | -2.4546 | -2.4819 | -2.4272 |
| 2014-10-01T00:00:00+00:00 | P0 | 2470 | -2.4377 | -2.4615 | -2.4115 |
| 2014-10-01T00:00:00+00:00 | P1 | 2470 | -2.4264 | -2.4499 | -2.4005 |
| 2014-10-01T00:00:00+00:00 | P2 | 2470 | -2.4230 | -2.4467 | -2.3962 |
| 2014-10-01T00:00:00+00:00 | local_eb | 2470 | -2.4381 | -2.4662 | -2.4121 |
| 2015-01-01T00:00:00+00:00 | GBM | 2546 | -2.4345 | -2.4594 | -2.4082 |
| 2015-01-01T00:00:00+00:00 | P0 | 2546 | -2.4215 | -2.4483 | -2.3972 |
| 2015-01-01T00:00:00+00:00 | P1 | 2546 | -2.4144 | -2.4394 | -2.3914 |
| 2015-01-01T00:00:00+00:00 | P2 | 2546 | -2.4120 | -2.4375 | -2.3891 |
| 2015-01-01T00:00:00+00:00 | local_eb | 2546 | -2.4258 | -2.4559 | -2.3988 |

### Scores by calendar year of the test start

Each scored row belongs to the year in which its test started; the years partition the scored rows. Brier skill and log score carry 90 percent by-test intervals.

| year | cell | rung | n | n_tests | logscore | logscore_lo | logscore_hi | brier_skill | brier_skill_lo | brier_skill_hi | direction_accuracy | abstention_rate | event_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | ALL | GBM | 7522 | 3761 | -2.4414 | -2.4571 | -2.4262 | 0.0213 | 0.0120 | 0.0309 | 0.6611 | 0.4030 | 0.2031 |
| 2013 | ALL | GBM+cal | 7522 | 3761 | n/a | n/a | n/a | 0.0238 | 0.0121 | 0.0368 | n/a | 0.4030 | 0.2031 |
| 2013 | ALL | P0 | 7522 | 3761 | -2.4289 | -2.4449 | -2.4132 | 0.0000 | 0.0000 | 0.0000 | 0.6578 | 0.4030 | 0.2031 |
| 2013 | ALL | P1 | 7522 | 3761 | -2.4191 | -2.4346 | -2.4038 | 0.0260 | 0.0204 | 0.0325 | 0.6578 | 0.4030 | 0.2031 |
| 2013 | ALL | P2 | 7522 | 3761 | -2.4187 | -2.4342 | -2.4033 | 0.0266 | 0.0211 | 0.0330 | 0.6581 | 0.4030 | 0.2031 |
| 2013 | ALL | always_reference | 7522 | 3761 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4475 | 0.4030 | 0.2031 |
| 2013 | ALL | always_variant | 7522 | 3761 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5525 | 0.4030 | 0.2031 |
| 2013 | ALL | local_eb | 7522 | 3761 | -2.4327 | -2.4485 | -2.4174 | 0.0179 | 0.0099 | 0.0264 | 0.6571 | 0.4030 | 0.2031 |
| 2013 | ALL | local_eb+cal | 7522 | 3761 | n/a | n/a | n/a | 0.0180 | 0.0101 | 0.0268 | n/a | 0.4030 | 0.2031 |
| 2013 | ALL | text_lr | 7522 | 3761 | n/a | n/a | n/a | -0.0132 | -0.0213 | -0.0051 | 0.6477 | 0.4030 | 0.2031 |
| 2013 | ALL | text_lr+cal | 7522 | 3761 | n/a | n/a | n/a | -0.0100 | -0.0175 | -0.0028 | n/a | 0.4030 | 0.2031 |
| 2013 | both | GBM | 2686 | 1343 | -2.3875 | -2.4071 | -2.3681 | 0.0353 | 0.0246 | 0.0462 | 0.5964 | 0.4021 | 0.1776 |
| 2013 | both | GBM+cal | 2686 | 1343 | n/a | n/a | n/a | 0.0376 | 0.0259 | 0.0496 | n/a | 0.4021 | 0.1776 |
| 2013 | both | P0 | 2686 | 1343 | -2.4028 | -2.4260 | -2.3800 | 0.0000 | 0.0000 | 0.0000 | 0.5901 | 0.4021 | 0.1776 |
| 2013 | both | P1 | 2686 | 1343 | -2.3929 | -2.4158 | -2.3708 | 0.0258 | 0.0174 | 0.0339 | 0.5901 | 0.4021 | 0.1776 |
| 2013 | both | P2 | 2686 | 1343 | -2.3916 | -2.4143 | -2.3696 | 0.0274 | 0.0187 | 0.0355 | 0.5908 | 0.4021 | 0.1776 |
| 2013 | both | always_reference | 2686 | 1343 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4099 | 0.4021 | 0.1776 |
| 2013 | both | always_variant | 2686 | 1343 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5901 | 0.4021 | 0.1776 |
| 2013 | both | local_eb | 2686 | 1343 | -2.4089 | -2.4319 | -2.3833 | 0.0235 | 0.0121 | 0.0352 | 0.5879 | 0.4021 | 0.1776 |
| 2013 | both | local_eb+cal | 2686 | 1343 | n/a | n/a | n/a | 0.0233 | 0.0116 | 0.0353 | n/a | 0.4021 | 0.1776 |
| 2013 | both | text_lr | 2686 | 1343 | n/a | n/a | n/a | -0.0073 | -0.0170 | 0.0027 | 0.5707 | 0.4021 | 0.1776 |
| 2013 | both | text_lr+cal | 2686 | 1343 | n/a | n/a | n/a | -0.0043 | -0.0134 | 0.0051 | n/a | 0.4021 | 0.1776 |
| 2013 | headline_only | GBM | 2370 | 1185 | -2.6851 | -2.7167 | -2.6514 | 0.0247 | 0.0086 | 0.0408 | 0.7312 | 0.4021 | 0.4025 |
| 2013 | headline_only | GBM+cal | 2370 | 1185 | n/a | n/a | n/a | 0.0198 | -0.0006 | 0.0400 | n/a | 0.4021 | 0.4025 |
| 2013 | headline_only | P0 | 2370 | 1185 | -2.6496 | -2.6714 | -2.6262 | 0.0000 | 0.0000 | 0.0000 | 0.7316 | 0.4021 | 0.4025 |
| 2013 | headline_only | P1 | 2370 | 1185 | -2.6456 | -2.6677 | -2.6221 | 0.0297 | 0.0208 | 0.0402 | 0.7316 | 0.4021 | 0.4025 |
| 2013 | headline_only | P2 | 2370 | 1185 | -2.6456 | -2.6677 | -2.6221 | 0.0297 | 0.0208 | 0.0402 | 0.7316 | 0.4021 | 0.4025 |
| 2013 | headline_only | always_reference | 2370 | 1185 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2684 | 0.4021 | 0.4025 |
| 2013 | headline_only | always_variant | 2370 | 1185 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7316 | 0.4021 | 0.4025 |
| 2013 | headline_only | local_eb | 2370 | 1185 | -2.6677 | -2.6915 | -2.6417 | 0.0161 | 0.0038 | 0.0284 | 0.7316 | 0.4021 | 0.4025 |
| 2013 | headline_only | local_eb+cal | 2370 | 1185 | n/a | n/a | n/a | 0.0167 | 0.0047 | 0.0285 | n/a | 0.4021 | 0.4025 |
| 2013 | headline_only | text_lr | 2370 | 1185 | n/a | n/a | n/a | -0.0191 | -0.0323 | -0.0051 | 0.7266 | 0.4021 | 0.4025 |
| 2013 | headline_only | text_lr+cal | 2370 | 1185 | n/a | n/a | n/a | -0.0140 | -0.0254 | -0.0018 | n/a | 0.4021 | 0.4025 |
| 2013 | image_only | GBM | 2466 | 1233 | -2.2661 | -2.2830 | -2.2532 | -0.0589 | -0.0921 | -0.0299 | 0.6642 | 0.4047 | 0.0393 |
| 2013 | image_only | GBM+cal | 2466 | 1233 | n/a | n/a | n/a | -0.0101 | -0.0286 | 0.0074 | n/a | 0.4047 | 0.0393 |
| 2013 | image_only | P0 | 2466 | 1233 | -2.2452 | -2.2722 | -2.2226 | 0.0000 | 0.0000 | 0.0000 | 0.6606 | 0.4047 | 0.0393 |
| 2013 | image_only | P1 | 2466 | 1233 | -2.2300 | -2.2573 | -2.2077 | 0.0046 | 0.0010 | 0.0088 | 0.6606 | 0.4047 | 0.0393 |
| 2013 | image_only | P2 | 2466 | 1233 | -2.2300 | -2.2573 | -2.2077 | 0.0046 | 0.0010 | 0.0088 | 0.6606 | 0.4047 | 0.0393 |
| 2013 | image_only | always_reference | 2466 | 1233 | n/a | n/a | n/a | n/a | n/a | n/a | 0.6606 | 0.4047 | 0.0393 |
| 2013 | image_only | always_variant | 2466 | 1233 | n/a | n/a | n/a | n/a | n/a | n/a | 0.3394 | 0.4047 | 0.0393 |
| 2013 | image_only | local_eb | 2466 | 1233 | -2.2327 | -2.2598 | -2.2093 | 0.0054 | -0.0037 | 0.0142 | 0.6610 | 0.4047 | 0.0393 |
| 2013 | image_only | local_eb+cal | 2466 | 1233 | n/a | n/a | n/a | 0.0032 | -0.0065 | 0.0123 | n/a | 0.4047 | 0.0393 |
| 2013 | image_only | text_lr | 2466 | 1233 | n/a | n/a | n/a | -0.0014 | -0.0078 | 0.0046 | 0.6557 | 0.4047 | 0.0393 |
| 2013 | image_only | text_lr+cal | 2466 | 1233 | n/a | n/a | n/a | -0.0093 | -0.0200 | 0.0000 | n/a | 0.4047 | 0.0393 |
| 2014 | ALL | GBM | 9698 | 4849 | -2.4452 | -2.4603 | -2.4298 | 0.0137 | 0.0059 | 0.0209 | 0.6583 | 0.0449 | 0.2031 |
| 2014 | ALL | GBM+cal | 9698 | 4849 | n/a | n/a | n/a | 0.0128 | 0.0022 | 0.0220 | n/a | 0.0449 | 0.2031 |
| 2014 | ALL | P0 | 9698 | 4849 | -2.4282 | -2.4422 | -2.4135 | 0.0000 | 0.0000 | 0.0000 | 0.6624 | 0.0449 | 0.2031 |
| 2014 | ALL | P1 | 9698 | 4849 | -2.4184 | -2.4322 | -2.4037 | 0.0196 | 0.0139 | 0.0247 | 0.6624 | 0.0449 | 0.2031 |
| 2014 | ALL | P2 | 9698 | 4849 | -2.4157 | -2.4295 | -2.4011 | 0.0206 | 0.0149 | 0.0258 | 0.6622 | 0.0449 | 0.2031 |
| 2014 | ALL | always_reference | 9698 | 4849 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4562 | 0.0449 | 0.2031 |
| 2014 | ALL | always_variant | 9698 | 4849 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5438 | 0.0449 | 0.2031 |
| 2014 | ALL | local_eb | 9698 | 4849 | -2.4291 | -2.4442 | -2.4139 | 0.0184 | 0.0113 | 0.0256 | 0.6593 | 0.0449 | 0.2031 |
| 2014 | ALL | local_eb+cal | 9698 | 4849 | n/a | n/a | n/a | 0.0184 | 0.0109 | 0.0254 | n/a | 0.0449 | 0.2031 |
| 2014 | ALL | text_lr | 9698 | 4849 | n/a | n/a | n/a | -0.0184 | -0.0263 | -0.0110 | 0.6551 | 0.0449 | 0.2031 |
| 2014 | ALL | text_lr+cal | 9698 | 4849 | n/a | n/a | n/a | -0.0140 | -0.0213 | -0.0073 | n/a | 0.0449 | 0.2031 |
| 2014 | both | GBM | 3212 | 1606 | -2.3700 | -2.3892 | -2.3522 | 0.0236 | 0.0139 | 0.0347 | 0.5688 | 0.0380 | 0.1821 |
| 2014 | both | GBM+cal | 3212 | 1606 | n/a | n/a | n/a | 0.0228 | 0.0113 | 0.0352 | n/a | 0.0380 | 0.1821 |
| 2014 | both | P0 | 3212 | 1606 | -2.3843 | -2.4068 | -2.3637 | 0.0000 | 0.0000 | 0.0000 | 0.5772 | 0.0380 | 0.1821 |
| 2014 | both | P1 | 3212 | 1606 | -2.3732 | -2.3955 | -2.3536 | 0.0165 | 0.0087 | 0.0237 | 0.5772 | 0.0380 | 0.1821 |
| 2014 | both | P2 | 3212 | 1606 | -2.3716 | -2.3930 | -2.3520 | 0.0179 | 0.0100 | 0.0257 | 0.5766 | 0.0380 | 0.1821 |
| 2014 | both | always_reference | 3212 | 1606 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4228 | 0.0380 | 0.1821 |
| 2014 | both | always_variant | 3212 | 1606 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5772 | 0.0380 | 0.1821 |
| 2014 | both | local_eb | 3212 | 1606 | -2.3852 | -2.4075 | -2.3649 | 0.0127 | 0.0030 | 0.0229 | 0.5688 | 0.0380 | 0.1821 |
| 2014 | both | local_eb+cal | 3212 | 1606 | n/a | n/a | n/a | 0.0127 | 0.0026 | 0.0229 | n/a | 0.0380 | 0.1821 |
| 2014 | both | text_lr | 3212 | 1606 | n/a | n/a | n/a | -0.0091 | -0.0184 | 0.0004 | 0.5788 | 0.0380 | 0.1821 |
| 2014 | both | text_lr+cal | 3212 | 1606 | n/a | n/a | n/a | -0.0064 | -0.0157 | 0.0023 | n/a | 0.0380 | 0.1821 |
| 2014 | headline_only | GBM | 3154 | 1577 | -2.7130 | -2.7457 | -2.6788 | 0.0175 | 0.0046 | 0.0313 | 0.7384 | 0.0580 | 0.3951 |
| 2014 | headline_only | GBM+cal | 3154 | 1577 | n/a | n/a | n/a | 0.0090 | -0.0083 | 0.0266 | n/a | 0.0580 | 0.3951 |
| 2014 | headline_only | P0 | 3154 | 1577 | -2.6628 | -2.6853 | -2.6396 | 0.0000 | 0.0000 | 0.0000 | 0.7384 | 0.0580 | 0.3951 |
| 2014 | headline_only | P1 | 3154 | 1577 | -2.6571 | -2.6790 | -2.6348 | 0.0244 | 0.0156 | 0.0338 | 0.7384 | 0.0580 | 0.3951 |
| 2014 | headline_only | P2 | 3154 | 1577 | -2.6566 | -2.6786 | -2.6346 | 0.0251 | 0.0161 | 0.0345 | 0.7384 | 0.0580 | 0.3951 |
| 2014 | headline_only | always_reference | 3154 | 1577 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2616 | 0.0580 | 0.3951 |
| 2014 | headline_only | always_variant | 3154 | 1577 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7384 | 0.0580 | 0.3951 |
| 2014 | headline_only | local_eb | 3154 | 1577 | -2.6723 | -2.6970 | -2.6482 | 0.0251 | 0.0134 | 0.0366 | 0.7384 | 0.0580 | 0.3951 |
| 2014 | headline_only | local_eb+cal | 3154 | 1577 | n/a | n/a | n/a | 0.0252 | 0.0135 | 0.0363 | n/a | 0.0580 | 0.3951 |
| 2014 | headline_only | text_lr | 3154 | 1577 | n/a | n/a | n/a | -0.0276 | -0.0396 | -0.0161 | 0.7334 | 0.0580 | 0.3951 |
| 2014 | headline_only | text_lr+cal | 3154 | 1577 | n/a | n/a | n/a | -0.0207 | -0.0316 | -0.0102 | n/a | 0.0580 | 0.3951 |
| 2014 | image_only | GBM | 3332 | 1666 | -2.2642 | -2.2775 | -2.2506 | -0.0428 | -0.0697 | -0.0201 | 0.6687 | 0.0390 | 0.0417 |
| 2014 | image_only | GBM+cal | 3332 | 1666 | n/a | n/a | n/a | -0.0009 | -0.0139 | 0.0113 | n/a | 0.0390 | 0.0417 |
| 2014 | image_only | P0 | 3332 | 1666 | -2.2484 | -2.2702 | -2.2268 | 0.0000 | 0.0000 | 0.0000 | 0.6726 | 0.0390 | 0.0417 |
| 2014 | image_only | P1 | 3332 | 1666 | -2.2360 | -2.2570 | -2.2158 | 0.0038 | 0.0001 | 0.0074 | 0.6726 | 0.0390 | 0.0417 |
| 2014 | image_only | P2 | 3332 | 1666 | -2.2300 | -2.2512 | -2.2089 | 0.0053 | 0.0015 | 0.0089 | 0.6726 | 0.0390 | 0.0417 |
| 2014 | image_only | always_reference | 3332 | 1666 | n/a | n/a | n/a | n/a | n/a | n/a | 0.6726 | 0.0390 | 0.0417 |
| 2014 | image_only | always_variant | 3332 | 1666 | n/a | n/a | n/a | n/a | n/a | n/a | 0.3274 | 0.0390 | 0.0417 |
| 2014 | image_only | local_eb | 3332 | 1666 | -2.2413 | -2.2649 | -2.2186 | 0.0007 | -0.0084 | 0.0093 | 0.6717 | 0.0390 | 0.0417 |
| 2014 | image_only | local_eb+cal | 3332 | 1666 | n/a | n/a | n/a | -0.0001 | -0.0099 | 0.0095 | n/a | 0.0390 | 0.0417 |
| 2014 | image_only | text_lr | 3332 | 1666 | n/a | n/a | n/a | -0.0002 | -0.0051 | 0.0053 | 0.6546 | 0.0390 | 0.0417 |
| 2014 | image_only | text_lr+cal | 3332 | 1666 | n/a | n/a | n/a | -0.0036 | -0.0107 | 0.0037 | n/a | 0.0390 | 0.0417 |
| 2015 | ALL | GBM | 2546 | 1273 | -2.4345 | -2.4610 | -2.4095 | 0.0219 | 0.0071 | 0.0353 | 0.6516 | 0.0346 | 0.2027 |
| 2015 | ALL | GBM+cal | 2546 | 1273 | n/a | n/a | n/a | 0.0186 | -0.0003 | 0.0369 | n/a | 0.0346 | 0.2027 |
| 2015 | ALL | P0 | 2546 | 1273 | -2.4215 | -2.4483 | -2.3992 | 0.0000 | 0.0000 | 0.0000 | 0.6516 | 0.0346 | 0.2027 |
| 2015 | ALL | P1 | 2546 | 1273 | -2.4144 | -2.4393 | -2.3924 | 0.0152 | 0.0053 | 0.0254 | 0.6516 | 0.0346 | 0.2027 |
| 2015 | ALL | P2 | 2546 | 1273 | -2.4120 | -2.4374 | -2.3894 | 0.0166 | 0.0071 | 0.0266 | 0.6520 | 0.0346 | 0.2027 |
| 2015 | ALL | always_reference | 2546 | 1273 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4544 | 0.0346 | 0.2027 |
| 2015 | ALL | always_variant | 2546 | 1273 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5456 | 0.0346 | 0.2027 |
| 2015 | ALL | local_eb | 2546 | 1273 | -2.4258 | -2.4537 | -2.4002 | 0.0159 | 0.0028 | 0.0289 | 0.6434 | 0.0346 | 0.2027 |
| 2015 | ALL | local_eb+cal | 2546 | 1273 | n/a | n/a | n/a | 0.0137 | -0.0005 | 0.0280 | n/a | 0.0346 | 0.2027 |
| 2015 | ALL | text_lr | 2546 | 1273 | n/a | n/a | n/a | -0.0214 | -0.0357 | -0.0048 | 0.6296 | 0.0346 | 0.2027 |
| 2015 | ALL | text_lr+cal | 2546 | 1273 | n/a | n/a | n/a | -0.0207 | -0.0351 | -0.0037 | n/a | 0.0346 | 0.2027 |
| 2015 | both | GBM | 890 | 445 | -2.3679 | -2.4014 | -2.3352 | 0.0396 | 0.0185 | 0.0599 | 0.5764 | 0.0270 | 0.1753 |
| 2015 | both | GBM+cal | 890 | 445 | n/a | n/a | n/a | 0.0416 | 0.0161 | 0.0665 | n/a | 0.0270 | 0.1753 |
| 2015 | both | P0 | 890 | 445 | -2.3779 | -2.4175 | -2.3394 | 0.0000 | 0.0000 | 0.0000 | 0.5775 | 0.0270 | 0.1753 |
| 2015 | both | P1 | 890 | 445 | -2.3715 | -2.4095 | -2.3344 | 0.0241 | 0.0095 | 0.0383 | 0.5775 | 0.0270 | 0.1753 |
| 2015 | both | P2 | 890 | 445 | -2.3699 | -2.4095 | -2.3329 | 0.0263 | 0.0119 | 0.0406 | 0.5787 | 0.0270 | 0.1753 |
| 2015 | both | always_reference | 890 | 445 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4225 | 0.0270 | 0.1753 |
| 2015 | both | always_variant | 890 | 445 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5775 | 0.0270 | 0.1753 |
| 2015 | both | local_eb | 890 | 445 | -2.3758 | -2.4155 | -2.3374 | 0.0274 | 0.0060 | 0.0477 | 0.5528 | 0.0270 | 0.1753 |
| 2015 | both | local_eb+cal | 890 | 445 | n/a | n/a | n/a | 0.0255 | 0.0007 | 0.0475 | n/a | 0.0270 | 0.1753 |
| 2015 | both | text_lr | 890 | 445 | n/a | n/a | n/a | -0.0314 | -0.0533 | -0.0117 | 0.5371 | 0.0270 | 0.1753 |
| 2015 | both | text_lr+cal | 890 | 445 | n/a | n/a | n/a | -0.0334 | -0.0564 | -0.0134 | n/a | 0.0270 | 0.1753 |
| 2015 | headline_only | GBM | 830 | 415 | -2.6775 | -2.7363 | -2.6188 | 0.0203 | -0.0014 | 0.0417 | 0.7193 | 0.0590 | 0.3880 |
| 2015 | headline_only | GBM+cal | 830 | 415 | n/a | n/a | n/a | 0.0076 | -0.0218 | 0.0363 | n/a | 0.0590 | 0.3880 |
| 2015 | headline_only | P0 | 830 | 415 | -2.6405 | -2.6757 | -2.6031 | 0.0000 | 0.0000 | 0.0000 | 0.7193 | 0.0590 | 0.3880 |
| 2015 | headline_only | P1 | 830 | 415 | -2.6412 | -2.6773 | -2.6020 | 0.0117 | -0.0027 | 0.0272 | 0.7193 | 0.0590 | 0.3880 |
| 2015 | headline_only | P2 | 830 | 415 | -2.6400 | -2.6757 | -2.6009 | 0.0127 | -0.0012 | 0.0283 | 0.7193 | 0.0590 | 0.3880 |
| 2015 | headline_only | always_reference | 830 | 415 | n/a | n/a | n/a | n/a | n/a | n/a | 0.2807 | 0.0590 | 0.3880 |
| 2015 | headline_only | always_variant | 830 | 415 | n/a | n/a | n/a | n/a | n/a | n/a | 0.7193 | 0.0590 | 0.3880 |
| 2015 | headline_only | local_eb | 830 | 415 | -2.6550 | -2.6936 | -2.6175 | 0.0128 | -0.0077 | 0.0316 | 0.7193 | 0.0590 | 0.3880 |
| 2015 | headline_only | local_eb+cal | 830 | 415 | n/a | n/a | n/a | 0.0102 | -0.0117 | 0.0295 | n/a | 0.0590 | 0.3880 |
| 2015 | headline_only | text_lr | 830 | 415 | n/a | n/a | n/a | -0.0200 | -0.0467 | 0.0041 | 0.7096 | 0.0590 | 0.3880 |
| 2015 | headline_only | text_lr+cal | 830 | 415 | n/a | n/a | n/a | -0.0173 | -0.0427 | 0.0065 | n/a | 0.0590 | 0.3880 |
| 2015 | image_only | GBM | 826 | 413 | -2.2622 | -2.2871 | -2.2366 | -0.0320 | -0.0829 | 0.0056 | 0.6646 | 0.0182 | 0.0460 |
| 2015 | image_only | GBM+cal | 826 | 413 | n/a | n/a | n/a | -0.0033 | -0.0291 | 0.0181 | n/a | 0.0182 | 0.0460 |
| 2015 | image_only | P0 | 826 | 413 | -2.2483 | -2.2874 | -2.2082 | 0.0000 | 0.0000 | 0.0000 | 0.6634 | 0.0182 | 0.0460 |
| 2015 | image_only | P1 | 826 | 413 | -2.2326 | -2.2725 | -2.1918 | 0.0022 | -0.0043 | 0.0095 | 0.6634 | 0.0182 | 0.0460 |
| 2015 | image_only | P2 | 826 | 413 | -2.2282 | -2.2691 | -2.1866 | 0.0034 | -0.0025 | 0.0099 | 0.6634 | 0.0182 | 0.0460 |
| 2015 | image_only | always_reference | 826 | 413 | n/a | n/a | n/a | n/a | n/a | n/a | 0.6634 | 0.0182 | 0.0460 |
| 2015 | image_only | always_variant | 826 | 413 | n/a | n/a | n/a | n/a | n/a | n/a | 0.3366 | 0.0182 | 0.0460 |
| 2015 | image_only | local_eb | 826 | 413 | -2.2495 | -2.2980 | -2.2021 | -0.0077 | -0.0216 | 0.0073 | 0.6646 | 0.0182 | 0.0460 |
| 2015 | image_only | local_eb+cal | 826 | 413 | n/a | n/a | n/a | -0.0091 | -0.0273 | 0.0085 | n/a | 0.0182 | 0.0460 |
| 2015 | image_only | text_lr | 826 | 413 | n/a | n/a | n/a | 0.0058 | -0.0057 | 0.0175 | 0.6489 | 0.0182 | 0.0460 |
| 2015 | image_only | text_lr+cal | 826 | 413 | n/a | n/a | n/a | 0.0063 | -0.0084 | 0.0202 | n/a | 0.0182 | 0.0460 |

## Coverage of the intervals for y (primary rung)

| cell | n | coverage_80 | coverage_90 |
|---|---|---|---|
| ALL | 19766 | 0.8016 | 0.9008 |
| both | 6788 | 0.8038 | 0.9041 |
| headline_only | 6354 | 0.7989 | 0.8990 |
| image_only | 6624 | 0.8019 | 0.8993 |

## Coverage by realized over planned standard error

Rows grouped in deciles of the ratio of the realized to the planned standard error (an evaluation-time stratifier: the realized standard error is never a forecast input). The forecaster fixes the click-through level at the cell median, so the ratio varies with the realized level; `coverage_80` and `coverage_90` should be near 0.80 and 0.90 in every decile. A rung that is not in range here is not calibrated within strata, whatever its pooled coverage.

| rung | decile | ratio_lo | ratio_hi | n | mean_ratio | coverage_80 | coverage_90 | event_rate | mean_p_sig |
|---|---|---|---|---|---|---|---|---|---|
| GBM | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | 0.8126 | 0.9008 | 0.2031 | 0.2131 |
| GBM+cal | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | n/a | n/a | 0.2031 | 0.2083 |
| P0 | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | 0.7983 | 0.9026 | 0.2031 | 0.2042 |
| P1 | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | 0.8004 | 0.9002 | 0.2031 | 0.2016 |
| P2 | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | 0.8016 | 0.9008 | 0.2031 | 0.2010 |
| always_reference | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | n/a | n/a | 0.2031 | n/a |
| always_variant | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | n/a | n/a | 0.2031 | n/a |
| local_eb | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | 0.7924 | 0.8921 | 0.2031 | 0.1983 |
| local_eb+cal | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | n/a | n/a | 0.2031 | 0.2062 |
| text_lr | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | n/a | n/a | 0.2031 | 0.2040 |
| text_lr+cal | 1 | 1.0000 | 1.0000 | 19766 | 1.0000 | n/a | n/a | 0.2031 | 0.2072 |

## Calibration by precision

Rows grouped in deciles of the planned exposures per arm (fewer groups when exposures tie). A forecaster that is calibrated overall but not within these groups is not calibrated. `mean_p_sig` should match `event_rate`, and `coverage_90` should be near 0.90, in every group.

| rung | decile | exposure_lo | exposure_hi | n | mean_s_star | mean_p_sig | event_rate | coverage_90 |
|---|---|---|---|---|---|---|---|---|
| GBM | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2150 | 0.2135 | 0.8933 |
| GBM | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2157 | 0.2039 | 0.8993 |
| GBM | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2161 | 0.2205 | 0.9064 |
| GBM | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2167 | 0.2061 | 0.8962 |
| GBM | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2146 | 0.1926 | 0.9034 |
| GBM | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2175 | 0.2055 | 0.8882 |
| GBM | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.2096 | 0.1947 | 0.9029 |
| GBM | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.2058 | 0.1994 | 0.9124 |
| GBM | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.2114 | 0.2028 | 0.8953 |
| GBM | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.2086 | 0.1917 | 0.9105 |
| GBM+cal | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2109 | 0.2135 | n/a |
| GBM+cal | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2117 | 0.2039 | n/a |
| GBM+cal | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2124 | 0.2205 | n/a |
| GBM+cal | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2125 | 0.2061 | n/a |
| GBM+cal | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2103 | 0.1926 | n/a |
| GBM+cal | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2138 | 0.2055 | n/a |
| GBM+cal | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.2035 | 0.1947 | n/a |
| GBM+cal | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.1994 | 0.1994 | n/a |
| GBM+cal | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.2061 | 0.2028 | n/a |
| GBM+cal | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.2028 | 0.1917 | n/a |
| P0 | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2011 | 0.2135 | 0.8928 |
| P0 | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2038 | 0.2039 | 0.9069 |
| P0 | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2069 | 0.2205 | 0.8973 |
| P0 | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2072 | 0.2061 | 0.9013 |
| P0 | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2040 | 0.1926 | 0.9029 |
| P0 | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2107 | 0.2055 | 0.8983 |
| P0 | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.2020 | 0.1947 | 0.8993 |
| P0 | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.2015 | 0.1994 | 0.9099 |
| P0 | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.2029 | 0.2028 | 0.9039 |
| P0 | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.2013 | 0.1917 | 0.9130 |
| P1 | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2009 | 0.2135 | 0.8918 |
| P1 | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2027 | 0.2039 | 0.9044 |
| P1 | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2044 | 0.2205 | 0.8918 |
| P1 | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2049 | 0.2061 | 0.9008 |
| P1 | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2024 | 0.1926 | 0.9024 |
| P1 | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2077 | 0.2055 | 0.8947 |
| P1 | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.1987 | 0.1947 | 0.8923 |
| P1 | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.1968 | 0.1994 | 0.9094 |
| P1 | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.1995 | 0.2028 | 0.9039 |
| P1 | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.1981 | 0.1917 | 0.9105 |
| P2 | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2007 | 0.2135 | 0.8923 |
| P2 | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2023 | 0.2039 | 0.9064 |
| P2 | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2035 | 0.2205 | 0.8943 |
| P2 | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2043 | 0.2061 | 0.8987 |
| P2 | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2018 | 0.1926 | 0.9029 |
| P2 | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2072 | 0.2055 | 0.8947 |
| P2 | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.1983 | 0.1947 | 0.8923 |
| P2 | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.1962 | 0.1994 | 0.9119 |
| P2 | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.1988 | 0.2028 | 0.9049 |
| P2 | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.1972 | 0.1917 | 0.9100 |
| always_reference | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | n/a | 0.2135 | n/a |
| always_reference | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | n/a | 0.2039 | n/a |
| always_reference | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | n/a | 0.2205 | n/a |
| always_reference | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | n/a | 0.2061 | n/a |
| always_reference | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | n/a | 0.1926 | n/a |
| always_reference | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | n/a | 0.2055 | n/a |
| always_reference | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | n/a | 0.1947 | n/a |
| always_reference | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | n/a | 0.1994 | n/a |
| always_reference | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | n/a | 0.2028 | n/a |
| always_reference | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | n/a | 0.1917 | n/a |
| always_variant | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | n/a | 0.2135 | n/a |
| always_variant | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | n/a | 0.2039 | n/a |
| always_variant | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | n/a | 0.2205 | n/a |
| always_variant | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | n/a | 0.2061 | n/a |
| always_variant | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | n/a | 0.1926 | n/a |
| always_variant | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | n/a | 0.2055 | n/a |
| always_variant | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | n/a | 0.1947 | n/a |
| always_variant | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | n/a | 0.1994 | n/a |
| always_variant | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | n/a | 0.2028 | n/a |
| always_variant | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | n/a | 0.1917 | n/a |
| local_eb | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.1999 | 0.2135 | 0.8816 |
| local_eb | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2007 | 0.2039 | 0.8978 |
| local_eb | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2009 | 0.2205 | 0.8872 |
| local_eb | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2009 | 0.2061 | 0.8886 |
| local_eb | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.1993 | 0.1926 | 0.8999 |
| local_eb | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2059 | 0.2055 | 0.8882 |
| local_eb | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.1947 | 0.1947 | 0.8781 |
| local_eb | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.1924 | 0.1994 | 0.9038 |
| local_eb | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.1958 | 0.2028 | 0.8943 |
| local_eb | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.1930 | 0.1917 | 0.9019 |
| local_eb+cal | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2079 | 0.2135 | n/a |
| local_eb+cal | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2086 | 0.2039 | n/a |
| local_eb+cal | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2088 | 0.2205 | n/a |
| local_eb+cal | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2084 | 0.2061 | n/a |
| local_eb+cal | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2071 | 0.1926 | n/a |
| local_eb+cal | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2140 | 0.2055 | n/a |
| local_eb+cal | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.2025 | 0.1947 | n/a |
| local_eb+cal | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.2002 | 0.1994 | n/a |
| local_eb+cal | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.2039 | 0.2028 | n/a |
| local_eb+cal | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.2009 | 0.1917 | n/a |
| text_lr | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2008 | 0.2135 | n/a |
| text_lr | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2033 | 0.2039 | n/a |
| text_lr | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2049 | 0.2205 | n/a |
| text_lr | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2052 | 0.2061 | n/a |
| text_lr | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2046 | 0.1926 | n/a |
| text_lr | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2122 | 0.2055 | n/a |
| text_lr | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.2042 | 0.1947 | n/a |
| text_lr | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.2015 | 0.1994 | n/a |
| text_lr | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.2044 | 0.2028 | n/a |
| text_lr | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.1994 | 0.1917 | n/a |
| text_lr+cal | 1 | 2002.0000 | 5857.0000 | 1977 | 1.5315 | 0.2044 | 0.2135 | n/a |
| text_lr+cal | 2 | 5861.0000 | 9739.0000 | 1976 | 1.5374 | 0.2066 | 0.2039 | n/a |
| text_lr+cal | 3 | 9741.0000 | 13471.0000 | 1977 | 1.5536 | 0.2081 | 0.2205 | n/a |
| text_lr+cal | 4 | 13477.0000 | 17405.0000 | 1975 | 1.5523 | 0.2081 | 0.2061 | n/a |
| text_lr+cal | 5 | 17409.0000 | 21200.0000 | 1978 | 1.5343 | 0.2076 | 0.1926 | n/a |
| text_lr+cal | 6 | 21201.0000 | 25007.0000 | 1976 | 1.5503 | 0.2150 | 0.2055 | n/a |
| text_lr+cal | 7 | 25010.0000 | 28729.0000 | 1977 | 1.5517 | 0.2070 | 0.1947 | n/a |
| text_lr+cal | 8 | 28730.0000 | 32454.0000 | 1976 | 1.5596 | 0.2049 | 0.1994 | n/a |
| text_lr+cal | 9 | 32461.0000 | 36141.0000 | 1977 | 1.5517 | 0.2077 | 0.2028 | n/a |
| text_lr+cal | 10 | 36143.0000 | 39999.0000 | 1977 | 1.5525 | 0.2030 | 0.1917 | n/a |

## Reliability bins of p_sig

| rung | bin | lo | hi | n | mean_p | freq |
|---|---|---|---|---|---|---|
| GBM | 0 | 0.0000 | 0.1000 | 5033 | 0.0705 | 0.0324 |
| GBM | 1 | 0.1000 | 0.2000 | 5791 | 0.1471 | 0.1212 |
| GBM | 2 | 0.2000 | 0.3000 | 3942 | 0.2459 | 0.2598 |
| GBM | 3 | 0.3000 | 0.4000 | 2642 | 0.3458 | 0.3683 |
| GBM | 4 | 0.4000 | 0.5000 | 1698 | 0.4449 | 0.4741 |
| GBM | 5 | 0.5000 | 0.6000 | 546 | 0.5394 | 0.5183 |
| GBM | 6 | 0.6000 | 0.7000 | 104 | 0.6321 | 0.5769 |
| GBM | 7 | 0.7000 | 0.8000 | 9 | 0.7305 | 0.4444 |
| GBM | 8 | 0.8000 | 0.9000 | 1 | 0.8052 | 0.0000 |
| GBM | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| GBM+cal | 0 | 0.0000 | 0.1000 | 7017 | 0.0554 | 0.0459 |
| GBM+cal | 1 | 0.1000 | 0.2000 | 4594 | 0.1468 | 0.1554 |
| GBM+cal | 2 | 0.2000 | 0.3000 | 2933 | 0.2458 | 0.2666 |
| GBM+cal | 3 | 0.3000 | 0.4000 | 2115 | 0.3461 | 0.3470 |
| GBM+cal | 4 | 0.4000 | 0.5000 | 1553 | 0.4471 | 0.4398 |
| GBM+cal | 5 | 0.5000 | 0.6000 | 1032 | 0.5443 | 0.4787 |
| GBM+cal | 6 | 0.6000 | 0.7000 | 407 | 0.6405 | 0.5405 |
| GBM+cal | 7 | 0.7000 | 0.8000 | 102 | 0.7342 | 0.5882 |
| GBM+cal | 8 | 0.8000 | 0.9000 | 13 | 0.8321 | 0.3846 |
| GBM+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P0 | 0 | 0.0000 | 0.1000 | 6624 | 0.0419 | 0.0414 |
| P0 | 1 | 0.1000 | 0.2000 | 6788 | 0.1757 | 0.1794 |
| P0 | 2 | 0.2000 | 0.3000 | 0 | n/a | n/a |
| P0 | 3 | 0.3000 | 0.4000 | 1674 | 0.3994 | 0.4020 |
| P0 | 4 | 0.4000 | 0.5000 | 4680 | 0.4053 | 0.3951 |
| P0 | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| P0 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P0 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P0 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P0 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P1 | 0 | 0.0000 | 0.1000 | 6933 | 0.0428 | 0.0438 |
| P1 | 1 | 0.1000 | 0.2000 | 4378 | 0.1551 | 0.1540 |
| P1 | 2 | 0.2000 | 0.3000 | 2708 | 0.2414 | 0.2445 |
| P1 | 3 | 0.3000 | 0.4000 | 2658 | 0.3548 | 0.3570 |
| P1 | 4 | 0.4000 | 0.5000 | 2595 | 0.4442 | 0.4478 |
| P1 | 5 | 0.5000 | 0.6000 | 491 | 0.5264 | 0.5316 |
| P1 | 6 | 0.6000 | 0.7000 | 3 | 0.6085 | 0.6667 |
| P1 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P1 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P1 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P2 | 0 | 0.0000 | 0.1000 | 6952 | 0.0417 | 0.0430 |
| P2 | 1 | 0.1000 | 0.2000 | 4353 | 0.1545 | 0.1553 |
| P2 | 2 | 0.2000 | 0.3000 | 2730 | 0.2420 | 0.2462 |
| P2 | 3 | 0.3000 | 0.4000 | 2654 | 0.3553 | 0.3561 |
| P2 | 4 | 0.4000 | 0.5000 | 2588 | 0.4442 | 0.4490 |
| P2 | 5 | 0.5000 | 0.6000 | 485 | 0.5265 | 0.5299 |
| P2 | 6 | 0.6000 | 0.7000 | 4 | 0.6087 | 0.7500 |
| P2 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P2 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P2 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| local_eb | 0 | 0.0000 | 0.1000 | 7256 | 0.0417 | 0.0493 |
| local_eb | 1 | 0.1000 | 0.2000 | 4090 | 0.1491 | 0.1565 |
| local_eb | 2 | 0.2000 | 0.3000 | 2854 | 0.2464 | 0.2505 |
| local_eb | 3 | 0.3000 | 0.4000 | 2675 | 0.3501 | 0.3507 |
| local_eb | 4 | 0.4000 | 0.5000 | 2073 | 0.4444 | 0.4616 |
| local_eb | 5 | 0.5000 | 0.6000 | 736 | 0.5374 | 0.4810 |
| local_eb | 6 | 0.6000 | 0.7000 | 79 | 0.6229 | 0.6329 |
| local_eb | 7 | 0.7000 | 0.8000 | 3 | 0.7262 | 0.6667 |
| local_eb | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| local_eb | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| local_eb+cal | 0 | 0.0000 | 0.1000 | 6974 | 0.0439 | 0.0459 |
| local_eb+cal | 1 | 0.1000 | 0.2000 | 4006 | 0.1507 | 0.1510 |
| local_eb+cal | 2 | 0.2000 | 0.3000 | 2961 | 0.2467 | 0.2428 |
| local_eb+cal | 3 | 0.3000 | 0.4000 | 2684 | 0.3509 | 0.3443 |
| local_eb+cal | 4 | 0.4000 | 0.5000 | 2201 | 0.4450 | 0.4384 |
| local_eb+cal | 5 | 0.5000 | 0.6000 | 834 | 0.5373 | 0.5024 |
| local_eb+cal | 6 | 0.6000 | 0.7000 | 104 | 0.6268 | 0.5769 |
| local_eb+cal | 7 | 0.7000 | 0.8000 | 2 | 0.7500 | 1.0000 |
| local_eb+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| local_eb+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| text_lr | 0 | 0.0000 | 0.1000 | 7112 | 0.0452 | 0.0508 |
| text_lr | 1 | 0.1000 | 0.2000 | 4299 | 0.1489 | 0.1707 |
| text_lr | 2 | 0.2000 | 0.3000 | 2707 | 0.2466 | 0.2604 |
| text_lr | 3 | 0.3000 | 0.4000 | 2511 | 0.3506 | 0.3576 |
| text_lr | 4 | 0.4000 | 0.5000 | 2024 | 0.4464 | 0.4130 |
| text_lr | 5 | 0.5000 | 0.6000 | 921 | 0.5403 | 0.4224 |
| text_lr | 6 | 0.6000 | 0.7000 | 179 | 0.6338 | 0.4525 |
| text_lr | 7 | 0.7000 | 0.8000 | 13 | 0.7257 | 0.7692 |
| text_lr | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| text_lr | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| text_lr+cal | 0 | 0.0000 | 0.1000 | 6694 | 0.0523 | 0.0442 |
| text_lr+cal | 1 | 0.1000 | 0.2000 | 4352 | 0.1519 | 0.1645 |
| text_lr+cal | 2 | 0.2000 | 0.3000 | 3087 | 0.2462 | 0.2582 |
| text_lr+cal | 3 | 0.3000 | 0.4000 | 2811 | 0.3506 | 0.3657 |
| text_lr+cal | 4 | 0.4000 | 0.5000 | 2026 | 0.4452 | 0.4126 |
| text_lr+cal | 5 | 0.5000 | 0.6000 | 699 | 0.5383 | 0.4163 |
| text_lr+cal | 6 | 0.6000 | 0.7000 | 91 | 0.6288 | 0.5055 |
| text_lr+cal | 7 | 0.7000 | 0.8000 | 6 | 0.7213 | 0.6667 |
| text_lr+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| text_lr+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |

## Split-half check of the prior

P1 fit on odd tests and on even tests; the gap in the cell mean and spread.

| cell | mu_odd | mu_even | mu_gap | tau_odd | tau_even | tau_gap | n_odd | n_even |
|---|---|---|---|---|---|---|---|---|
| both | 0.5132 | 0.5193 | 0.0060 | 2.0238 | 2.1715 | 0.1476 | 3276 | 3340 |
| headline_only | 2.0681 | 2.0837 | 0.0157 | 3.0042 | 3.1008 | 0.0966 | 3124 | 3056 |
| image_only | -1.0408 | -0.9481 | 0.0927 | 1.6682 | 1.5920 | 0.0762 | 3234 | 3238 |

## Decision value

Reported separately from calibration and never combined with it. Each origin picks K tests (10, 25 and 50 percent of the period's tests, rounded, at least one) at random, by p_win, or by an oracle that knows y. Captured is the lift won in the units of y, the fraction is of the period's total positive observed lift, and regret is the oracle's capture minus the policy's. Random order captures K over n of the total by linearity, so it is exact, not a draw. A rung whose p_win is constant within a cell chooses by cell and then at random; its capture differs from random order only through between-cell differences. Intervals resample whole tests within each origin. The adjusted bounds are Bonferroni bounds for the family of rungs compared with random order in the pooled rows (family_size, the decision-value call of docs/method.md). diff_matched is the difference from random order matched to the arm-count composition of the chosen set, the baseline a rung must beat (the number of contrasts is known before launch).

| origin | policy | rung | budget | K | n_tests | total | captured | captured_fraction | captured_fraction_lo | captured_fraction_hi | captured_fraction_adjusted_lo | captured_fraction_adjusted_hi | regret | regret_lo | regret_hi | regret_adjusted_lo | regret_adjusted_hi | random_fraction | diff_random | diff_random_lo | diff_random_hi | diff_random_adjusted_lo | diff_random_adjusted_hi | matched_fraction | diff_matched | diff_matched_lo | diff_matched_hi | diff_matched_adjusted_lo | diff_matched_adjusted_hi | family_size | constant_within_cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | random | all | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 310 | 1241 | 2864.9101 | 715.6504 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1031.7038 | 989.2153 | 1069.8477 | 972.9954 | 1090.4122 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 310 | 1241 | 2864.9101 | 1224.7058 | 0.4275 | 0.4044 | 0.4511 | 0.3930 | 0.4620 | 522.6484 | 461.7753 | 585.0467 | 432.4465 | 612.8502 | 0.2498 | 0.1777 | 0.1546 | 0.2013 | 0.1432 | 0.2122 | 0.2498 | 0.1777 | 0.1546 | 0.2013 | 0.1432 | 0.2122 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 310 | 1241 | 2864.9101 | 1244.1501 | 0.4343 | 0.4153 | 0.4551 | 0.4066 | 0.4620 | 503.2040 | 456.7051 | 547.6548 | 435.9448 | 570.4633 | 0.2498 | 0.1845 | 0.1655 | 0.2053 | 0.1568 | 0.2122 | 0.2498 | 0.1845 | 0.1655 | 0.2053 | 0.1568 | 0.2122 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 310 | 1241 | 2864.9101 | 1244.1501 | 0.4343 | 0.4153 | 0.4551 | 0.4066 | 0.4620 | 503.2040 | 456.7051 | 547.6548 | 435.9448 | 570.4633 | 0.2498 | 0.1845 | 0.1655 | 0.2053 | 0.1568 | 0.2122 | 0.2498 | 0.1845 | 0.1655 | 0.2053 | 0.1568 | 0.2122 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 310 | 1241 | 2864.9101 | 1244.1501 | 0.4343 | 0.4153 | 0.4551 | 0.4066 | 0.4620 | 503.2040 | 456.7051 | 547.6548 | 435.9448 | 570.4633 | 0.2498 | 0.1845 | 0.1655 | 0.2053 | 0.1568 | 0.2122 | 0.2498 | 0.1845 | 0.1655 | 0.2053 | 0.1568 | 0.2122 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 310 | 1241 | 2864.9101 | 1230.0761 | 0.4294 | 0.4107 | 0.4537 | 0.3975 | 0.4612 | 517.2781 | 450.3648 | 569.0883 | 434.9538 | 599.6023 | 0.2498 | 0.1796 | 0.1609 | 0.2039 | 0.1477 | 0.2115 | 0.2498 | 0.1796 | 0.1609 | 0.2039 | 0.1477 | 0.2115 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 310 | 1241 | 2864.9101 | 1182.2219 | 0.4127 | 0.3941 | 0.4328 | 0.3829 | 0.4424 | 565.1323 | 508.9456 | 620.2759 | 485.0948 | 645.1698 | 0.2498 | 0.1629 | 0.1443 | 0.1830 | 0.1331 | 0.1926 | 0.2498 | 0.1629 | 0.1443 | 0.1830 | 0.1331 | 0.1926 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 310 | 1241 | 2864.9101 | 1747.3542 | 0.6099 | 0.5947 | 0.6274 | 0.5856 | 0.6343 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2498 | 0.3601 | 0.3449 | 0.3776 | 0.3358 | 0.3845 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random | all | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 124 | 1241 | 2864.9101 | 286.2602 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 597.0433 | 567.5055 | 622.1313 | 556.8457 | 637.2409 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 124 | 1241 | 2864.9101 | 503.0053 | 0.1756 | 0.1612 | 0.1908 | 0.1535 | 0.1977 | 380.2982 | 330.3173 | 425.0389 | 309.4358 | 451.1606 | 0.0999 | 0.0757 | 0.0613 | 0.0909 | 0.0536 | 0.0978 | 0.0999 | 0.0757 | 0.0613 | 0.0909 | 0.0536 | 0.0978 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 124 | 1241 | 2864.9101 | 497.6600 | 0.1737 | 0.1670 | 0.1807 | 0.1635 | 0.1839 | 385.6434 | 357.4319 | 410.2882 | 347.8866 | 423.4003 | 0.0999 | 0.0738 | 0.0671 | 0.0808 | 0.0636 | 0.0840 | 0.0999 | 0.0738 | 0.0671 | 0.0808 | 0.0636 | 0.0840 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 124 | 1241 | 2864.9101 | 497.6600 | 0.1737 | 0.1670 | 0.1807 | 0.1635 | 0.1839 | 385.6434 | 357.4319 | 410.2882 | 347.8866 | 423.4003 | 0.0999 | 0.0738 | 0.0671 | 0.0808 | 0.0636 | 0.0840 | 0.0999 | 0.0738 | 0.0671 | 0.0808 | 0.0636 | 0.0840 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 124 | 1241 | 2864.9101 | 497.6600 | 0.1737 | 0.1670 | 0.1807 | 0.1635 | 0.1839 | 385.6434 | 357.4319 | 410.2882 | 347.8866 | 423.4003 | 0.0999 | 0.0738 | 0.0671 | 0.0808 | 0.0636 | 0.0840 | 0.0999 | 0.0738 | 0.0671 | 0.0808 | 0.0636 | 0.0840 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 124 | 1241 | 2864.9101 | 483.6594 | 0.1688 | 0.1510 | 0.1828 | 0.1460 | 0.1917 | 399.6440 | 356.3427 | 449.4979 | 334.2013 | 465.0868 | 0.0999 | 0.0689 | 0.0511 | 0.0829 | 0.0460 | 0.0918 | 0.0999 | 0.0689 | 0.0511 | 0.0829 | 0.0460 | 0.0918 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 124 | 1241 | 2864.9101 | 480.0951 | 0.1676 | 0.1533 | 0.1830 | 0.1457 | 0.1895 | 403.2084 | 350.2967 | 447.2887 | 331.7570 | 474.6597 | 0.0999 | 0.0677 | 0.0534 | 0.0831 | 0.0458 | 0.0896 | 0.0999 | 0.0677 | 0.0534 | 0.0831 | 0.0458 | 0.0896 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 124 | 1241 | 2864.9101 | 883.3035 | 0.3083 | 0.2970 | 0.3192 | 0.2924 | 0.3243 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0999 | 0.2084 | 0.1971 | 0.2193 | 0.1925 | 0.2243 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random | all | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 621 | 1241 | 2864.9101 | 1433.6093 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1141.6534 | 1097.7766 | 1185.5983 | 1075.4265 | 1207.8803 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 621 | 1241 | 2864.9101 | 2109.1929 | 0.7362 | 0.7188 | 0.7549 | 0.7099 | 0.7625 | 466.0699 | 416.1463 | 507.0197 | 397.4492 | 534.6905 | 0.5004 | 0.2358 | 0.2184 | 0.2545 | 0.2095 | 0.2621 | 0.5004 | 0.2358 | 0.2184 | 0.2545 | 0.2095 | 0.2621 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 621 | 1241 | 2864.9101 | 2066.5652 | 0.7213 | 0.7050 | 0.7359 | 0.6995 | 0.7432 | 508.6975 | 472.1080 | 542.4247 | 457.0970 | 560.2981 | 0.5004 | 0.2209 | 0.2046 | 0.2355 | 0.1991 | 0.2428 | 0.5004 | 0.2209 | 0.2046 | 0.2355 | 0.1991 | 0.2428 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 621 | 1241 | 2864.9101 | 2066.5652 | 0.7213 | 0.7050 | 0.7359 | 0.6995 | 0.7432 | 508.6975 | 472.1080 | 542.4247 | 457.0970 | 560.2981 | 0.5004 | 0.2209 | 0.2046 | 0.2355 | 0.1991 | 0.2428 | 0.5004 | 0.2209 | 0.2046 | 0.2355 | 0.1991 | 0.2428 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 621 | 1241 | 2864.9101 | 2066.5652 | 0.7213 | 0.7050 | 0.7359 | 0.6995 | 0.7432 | 508.6975 | 472.1080 | 542.4247 | 457.0970 | 560.2981 | 0.5004 | 0.2209 | 0.2046 | 0.2355 | 0.1991 | 0.2428 | 0.5004 | 0.2209 | 0.2046 | 0.2355 | 0.1991 | 0.2428 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 621 | 1241 | 2864.9101 | 2108.6694 | 0.7360 | 0.7137 | 0.7504 | 0.7099 | 0.7621 | 466.5933 | 431.8325 | 519.3513 | 400.9636 | 532.2230 | 0.5004 | 0.2356 | 0.2133 | 0.2500 | 0.2095 | 0.2617 | 0.5004 | 0.2356 | 0.2133 | 0.2500 | 0.2095 | 0.2617 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 621 | 1241 | 2864.9101 | 2068.9403 | 0.7222 | 0.7001 | 0.7409 | 0.6926 | 0.7518 | 506.3224 | 455.0435 | 566.2604 | 429.9730 | 582.6718 | 0.5004 | 0.2218 | 0.1997 | 0.2405 | 0.1922 | 0.2514 | 0.5004 | 0.2218 | 0.1997 | 0.2405 | 0.1922 | 0.2514 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 621 | 1241 | 2864.9101 | 2575.2627 | 0.8989 | 0.8875 | 0.9102 | 0.8815 | 0.9163 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5004 | 0.3985 | 0.3871 | 0.4098 | 0.3811 | 0.4159 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random | all | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | arm_count | all | 0.2500 | 316 | 1264 | 2997.2473 | 749.3118 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1058.9849 | 1011.6441 | 1111.5583 | 986.8061 | 1131.1636 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 316 | 1264 | 2997.2473 | 1277.7871 | 0.4263 | 0.4050 | 0.4496 | 0.3941 | 0.4585 | 530.5096 | 469.1989 | 595.3843 | 442.0149 | 619.0043 | 0.2500 | 0.1763 | 0.1550 | 0.1996 | 0.1441 | 0.2085 | 0.2500 | 0.1763 | 0.1550 | 0.1996 | 0.1441 | 0.2085 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 316 | 1264 | 2997.2473 | 1274.7657 | 0.4253 | 0.4065 | 0.4447 | 0.3969 | 0.4538 | 533.5310 | 487.4086 | 587.4652 | 459.9573 | 607.1046 | 0.2500 | 0.1753 | 0.1565 | 0.1947 | 0.1469 | 0.2038 | 0.2500 | 0.1753 | 0.1565 | 0.1947 | 0.1469 | 0.2038 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 316 | 1264 | 2997.2473 | 1274.7657 | 0.4253 | 0.4065 | 0.4447 | 0.3969 | 0.4538 | 533.5310 | 487.4086 | 587.4652 | 459.9573 | 607.1046 | 0.2500 | 0.1753 | 0.1565 | 0.1947 | 0.1469 | 0.2038 | 0.2500 | 0.1753 | 0.1565 | 0.1947 | 0.1469 | 0.2038 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 316 | 1264 | 2997.2473 | 1274.7657 | 0.4253 | 0.4065 | 0.4447 | 0.3969 | 0.4538 | 533.5310 | 487.4086 | 587.4652 | 459.9573 | 607.1046 | 0.2500 | 0.1753 | 0.1565 | 0.1947 | 0.1469 | 0.2038 | 0.2500 | 0.1753 | 0.1565 | 0.1947 | 0.1469 | 0.2038 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 316 | 1264 | 2997.2473 | 1268.3708 | 0.4232 | 0.3930 | 0.4382 | 0.3902 | 0.4561 | 539.9259 | 496.0715 | 621.5678 | 446.8035 | 633.0483 | 0.2500 | 0.1732 | 0.1430 | 0.1882 | 0.1402 | 0.2061 | 0.2500 | 0.1732 | 0.1430 | 0.1882 | 0.1402 | 0.2061 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 316 | 1264 | 2997.2473 | 1228.3910 | 0.4098 | 0.3866 | 0.4323 | 0.3776 | 0.4421 | 579.9057 | 523.3947 | 637.2927 | 495.9516 | 663.8598 | 0.2500 | 0.1598 | 0.1366 | 0.1823 | 0.1276 | 0.1921 | 0.2500 | 0.1598 | 0.1366 | 0.1823 | 0.1276 | 0.1921 | 6 | no |
| 2013-07-01T00:00:00+00:00 | oracle | all | 0.2500 | 316 | 1264 | 2997.2473 | 1808.2967 | 0.6033 | 0.5873 | 0.6184 | 0.5794 | 0.6273 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3533 | 0.3373 | 0.3684 | 0.3294 | 0.3773 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random | all | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | arm_count | all | 0.1000 | 126 | 1264 | 2997.2473 | 298.7762 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 0.0997 | 635.0571 | 601.7338 | 669.0851 | 585.7847 | 684.3295 | 0.0997 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 126 | 1264 | 2997.2473 | 550.2911 | 0.1836 | 0.1655 | 0.1996 | 0.1593 | 0.2079 | 383.5422 | 337.4764 | 437.2812 | 312.4024 | 454.6821 | 0.0997 | 0.0839 | 0.0658 | 0.0999 | 0.0596 | 0.1082 | 0.0997 | 0.0839 | 0.0658 | 0.0999 | 0.0596 | 0.1082 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 126 | 1264 | 2997.2473 | 508.2927 | 0.1696 | 0.1621 | 0.1776 | 0.1586 | 0.1805 | 425.5407 | 397.3954 | 457.3141 | 382.0985 | 468.9828 | 0.0997 | 0.0699 | 0.0624 | 0.0779 | 0.0590 | 0.0808 | 0.0997 | 0.0699 | 0.0624 | 0.0779 | 0.0590 | 0.0808 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 126 | 1264 | 2997.2473 | 508.2927 | 0.1696 | 0.1621 | 0.1776 | 0.1586 | 0.1805 | 425.5407 | 397.3954 | 457.3141 | 382.0985 | 468.9828 | 0.0997 | 0.0699 | 0.0624 | 0.0779 | 0.0590 | 0.0808 | 0.0997 | 0.0699 | 0.0624 | 0.0779 | 0.0590 | 0.0808 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 126 | 1264 | 2997.2473 | 508.2927 | 0.1696 | 0.1621 | 0.1776 | 0.1586 | 0.1805 | 425.5407 | 397.3954 | 457.3141 | 382.0985 | 468.9828 | 0.0997 | 0.0699 | 0.0624 | 0.0779 | 0.0590 | 0.0808 | 0.0997 | 0.0699 | 0.0624 | 0.0779 | 0.0590 | 0.0808 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 126 | 1264 | 2997.2473 | 471.7409 | 0.1574 | 0.1410 | 0.1726 | 0.1338 | 0.1810 | 462.0924 | 414.4922 | 519.6723 | 383.3176 | 540.8673 | 0.0997 | 0.0577 | 0.0414 | 0.0729 | 0.0341 | 0.0813 | 0.0997 | 0.0577 | 0.0414 | 0.0729 | 0.0341 | 0.0813 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 126 | 1264 | 2997.2473 | 533.0670 | 0.1779 | 0.1609 | 0.1909 | 0.1549 | 0.2008 | 400.7663 | 359.0492 | 456.4131 | 330.0271 | 471.5054 | 0.0997 | 0.0782 | 0.0612 | 0.0913 | 0.0552 | 0.1011 | 0.0997 | 0.0782 | 0.0612 | 0.0913 | 0.0552 | 0.1011 | 6 | no |
| 2013-07-01T00:00:00+00:00 | oracle | all | 0.1000 | 126 | 1264 | 2997.2473 | 933.8333 | 0.3116 | 0.3006 | 0.3228 | 0.2955 | 0.3276 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0997 | 0.2119 | 0.2009 | 0.2231 | 0.1958 | 0.2279 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random | all | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | arm_count | all | 0.5000 | 632 | 1264 | 2997.2473 | 1498.6237 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1179.1498 | 1132.7033 | 1223.0200 | 1113.3184 | 1244.9813 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-07-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 632 | 1264 | 2997.2473 | 2150.4018 | 0.7175 | 0.6944 | 0.7335 | 0.6894 | 0.7455 | 527.3717 | 484.1279 | 590.8046 | 451.5406 | 603.2028 | 0.5000 | 0.2175 | 0.1944 | 0.2335 | 0.1894 | 0.2455 | 0.5000 | 0.2175 | 0.1944 | 0.2335 | 0.1894 | 0.2455 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 632 | 1264 | 2997.2473 | 2113.1570 | 0.7050 | 0.6889 | 0.7210 | 0.6819 | 0.7282 | 564.6164 | 524.5914 | 604.0130 | 507.9890 | 621.2439 | 0.5000 | 0.2050 | 0.1889 | 0.2210 | 0.1819 | 0.2282 | 0.5000 | 0.2050 | 0.1889 | 0.2210 | 0.1819 | 0.2282 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 632 | 1264 | 2997.2473 | 2113.1570 | 0.7050 | 0.6889 | 0.7210 | 0.6819 | 0.7282 | 564.6164 | 524.5914 | 604.0130 | 507.9890 | 621.2439 | 0.5000 | 0.2050 | 0.1889 | 0.2210 | 0.1819 | 0.2282 | 0.5000 | 0.2050 | 0.1889 | 0.2210 | 0.1819 | 0.2282 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 632 | 1264 | 2997.2473 | 2113.1570 | 0.7050 | 0.6889 | 0.7210 | 0.6819 | 0.7282 | 564.6164 | 524.5914 | 604.0130 | 507.9890 | 621.2439 | 0.5000 | 0.2050 | 0.1889 | 0.2210 | 0.1819 | 0.2282 | 0.5000 | 0.2050 | 0.1889 | 0.2210 | 0.1819 | 0.2282 | 6 | yes |
| 2013-07-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 632 | 1264 | 2997.2473 | 2110.2706 | 0.7041 | 0.6848 | 0.7241 | 0.6752 | 0.7330 | 567.5029 | 519.1637 | 623.1492 | 491.3909 | 643.6149 | 0.5000 | 0.2041 | 0.1848 | 0.2241 | 0.1752 | 0.2330 | 0.5000 | 0.2041 | 0.1848 | 0.2241 | 0.1752 | 0.2330 | 6 | no |
| 2013-07-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 632 | 1264 | 2997.2473 | 2119.6509 | 0.7072 | 0.6878 | 0.7264 | 0.6795 | 0.7349 | 558.1226 | 509.0364 | 612.0733 | 485.4965 | 630.7488 | 0.5000 | 0.2072 | 0.1878 | 0.2264 | 0.1795 | 0.2349 | 0.5000 | 0.2072 | 0.1878 | 0.2264 | 0.1795 | 0.2349 | 6 | no |
| 2013-07-01T00:00:00+00:00 | oracle | all | 0.5000 | 632 | 1264 | 2997.2473 | 2677.7735 | 0.8934 | 0.8822 | 0.9060 | 0.8758 | 0.9110 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.3934 | 0.3822 | 0.4060 | 0.3758 | 0.4110 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random | all | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | arm_count | all | 0.2500 | 314 | 1256 | 3096.1220 | 774.0305 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1063.3074 | 1021.7353 | 1108.6409 | 997.7192 | 1128.8955 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 314 | 1256 | 3096.1220 | 1345.6409 | 0.4346 | 0.4138 | 0.4567 | 0.4037 | 0.4655 | 491.6970 | 431.8166 | 558.1361 | 399.7138 | 583.6802 | 0.2500 | 0.1846 | 0.1638 | 0.2067 | 0.1537 | 0.2155 | 0.2500 | 0.1846 | 0.1638 | 0.2067 | 0.1537 | 0.2155 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 314 | 1256 | 3096.1220 | 1296.3180 | 0.4187 | 0.4022 | 0.4362 | 0.3933 | 0.4441 | 541.0198 | 489.9482 | 590.8356 | 465.3364 | 616.7032 | 0.2500 | 0.1687 | 0.1522 | 0.1862 | 0.1433 | 0.1941 | 0.2500 | 0.1687 | 0.1522 | 0.1862 | 0.1433 | 0.1941 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 314 | 1256 | 3096.1220 | 1296.3180 | 0.4187 | 0.4022 | 0.4362 | 0.3933 | 0.4441 | 541.0198 | 489.9482 | 590.8356 | 465.3364 | 616.7032 | 0.2500 | 0.1687 | 0.1522 | 0.1862 | 0.1433 | 0.1941 | 0.2500 | 0.1687 | 0.1522 | 0.1862 | 0.1433 | 0.1941 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 314 | 1256 | 3096.1220 | 1296.3180 | 0.4187 | 0.4022 | 0.4362 | 0.3933 | 0.4441 | 541.0198 | 489.9482 | 590.8356 | 465.3364 | 616.7032 | 0.2500 | 0.1687 | 0.1522 | 0.1862 | 0.1433 | 0.1941 | 0.2500 | 0.1687 | 0.1522 | 0.1862 | 0.1433 | 0.1941 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 314 | 1256 | 3096.1220 | 1361.7466 | 0.4398 | 0.4185 | 0.4591 | 0.4100 | 0.4697 | 475.5912 | 422.3181 | 543.7716 | 389.2981 | 561.8843 | 0.2500 | 0.1898 | 0.1685 | 0.2091 | 0.1600 | 0.2197 | 0.2500 | 0.1898 | 0.1685 | 0.2091 | 0.1600 | 0.2197 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 314 | 1256 | 3096.1220 | 1332.1443 | 0.4303 | 0.4097 | 0.4486 | 0.4022 | 0.4583 | 505.1935 | 455.8795 | 570.1332 | 423.0802 | 587.3068 | 0.2500 | 0.1803 | 0.1597 | 0.1986 | 0.1522 | 0.2083 | 0.2500 | 0.1803 | 0.1597 | 0.1986 | 0.1522 | 0.2083 | 6 | no |
| 2013-10-01T00:00:00+00:00 | oracle | all | 0.2500 | 314 | 1256 | 3096.1220 | 1837.3379 | 0.5934 | 0.5781 | 0.6080 | 0.5718 | 0.6151 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3434 | 0.3281 | 0.3580 | 0.3218 | 0.3651 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random | all | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | arm_count | all | 0.1000 | 126 | 1256 | 3096.1220 | 310.5982 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 0.1003 | 629.8123 | 598.8975 | 662.2828 | 582.8365 | 676.7881 | 0.1003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 126 | 1256 | 3096.1220 | 536.4179 | 0.1733 | 0.1577 | 0.1890 | 0.1503 | 0.1962 | 403.9927 | 352.4668 | 463.0886 | 323.6149 | 484.3704 | 0.1003 | 0.0729 | 0.0574 | 0.0887 | 0.0500 | 0.0959 | 0.1003 | 0.0729 | 0.0574 | 0.0887 | 0.0500 | 0.0959 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 126 | 1256 | 3096.1220 | 520.1786 | 0.1680 | 0.1608 | 0.1759 | 0.1571 | 0.1789 | 420.2320 | 391.0495 | 448.8334 | 377.4805 | 462.9834 | 0.1003 | 0.0677 | 0.0605 | 0.0756 | 0.0568 | 0.0786 | 0.1003 | 0.0677 | 0.0605 | 0.0756 | 0.0568 | 0.0786 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 126 | 1256 | 3096.1220 | 520.1786 | 0.1680 | 0.1608 | 0.1759 | 0.1571 | 0.1789 | 420.2320 | 391.0495 | 448.8334 | 377.4805 | 462.9834 | 0.1003 | 0.0677 | 0.0605 | 0.0756 | 0.0568 | 0.0786 | 0.1003 | 0.0677 | 0.0605 | 0.0756 | 0.0568 | 0.0786 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 126 | 1256 | 3096.1220 | 520.1786 | 0.1680 | 0.1608 | 0.1759 | 0.1571 | 0.1789 | 420.2320 | 391.0495 | 448.8334 | 377.4805 | 462.9834 | 0.1003 | 0.0677 | 0.0605 | 0.0756 | 0.0568 | 0.0786 | 0.1003 | 0.0677 | 0.0605 | 0.0756 | 0.0568 | 0.0786 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 126 | 1256 | 3096.1220 | 568.4413 | 0.1836 | 0.1666 | 0.1978 | 0.1612 | 0.2060 | 371.9692 | 322.4590 | 427.7943 | 296.3599 | 447.5785 | 0.1003 | 0.0833 | 0.0663 | 0.0975 | 0.0609 | 0.1057 | 0.1003 | 0.0833 | 0.0663 | 0.0975 | 0.0609 | 0.1057 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 126 | 1256 | 3096.1220 | 522.2794 | 0.1687 | 0.1549 | 0.1828 | 0.1484 | 0.1890 | 418.1311 | 371.2926 | 467.3240 | 346.4131 | 489.8491 | 0.1003 | 0.0684 | 0.0546 | 0.0825 | 0.0481 | 0.0886 | 0.1003 | 0.0684 | 0.0546 | 0.0825 | 0.0481 | 0.0886 | 6 | no |
| 2013-10-01T00:00:00+00:00 | oracle | all | 0.1000 | 126 | 1256 | 3096.1220 | 940.4105 | 0.3037 | 0.2925 | 0.3166 | 0.2866 | 0.3208 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1003 | 0.2034 | 0.1922 | 0.2163 | 0.1863 | 0.2205 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random | all | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | arm_count | all | 0.5000 | 628 | 1256 | 3096.1220 | 1548.0610 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1186.4020 | 1139.3133 | 1230.5801 | 1120.7204 | 1252.0836 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-10-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 628 | 1256 | 3096.1220 | 2235.7722 | 0.7221 | 0.7056 | 0.7425 | 0.6959 | 0.7484 | 498.6908 | 440.3565 | 545.6536 | 421.5084 | 575.8731 | 0.5000 | 0.2221 | 0.2056 | 0.2425 | 0.1959 | 0.2484 | 0.5000 | 0.2221 | 0.2056 | 0.2425 | 0.1959 | 0.2484 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 628 | 1256 | 3096.1220 | 2189.4551 | 0.7072 | 0.6930 | 0.7222 | 0.6864 | 0.7280 | 545.0079 | 505.3361 | 586.4613 | 487.5464 | 602.4694 | 0.5000 | 0.2072 | 0.1930 | 0.2222 | 0.1864 | 0.2280 | 0.5000 | 0.2072 | 0.1930 | 0.2222 | 0.1864 | 0.2280 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 628 | 1256 | 3096.1220 | 2189.4551 | 0.7072 | 0.6930 | 0.7222 | 0.6864 | 0.7280 | 545.0079 | 505.3361 | 586.4613 | 487.5464 | 602.4694 | 0.5000 | 0.2072 | 0.1930 | 0.2222 | 0.1864 | 0.2280 | 0.5000 | 0.2072 | 0.1930 | 0.2222 | 0.1864 | 0.2280 | 6 | yes |
| 2013-10-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 628 | 1256 | 3096.1220 | 2224.6503 | 0.7185 | 0.7026 | 0.7390 | 0.6919 | 0.7452 | 509.8127 | 453.4156 | 553.3987 | 434.9720 | 584.6534 | 0.5000 | 0.2185 | 0.2026 | 0.2390 | 0.1919 | 0.2452 | 0.5000 | 0.2185 | 0.2026 | 0.2390 | 0.1919 | 0.2452 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 628 | 1256 | 3096.1220 | 2223.7006 | 0.7182 | 0.7031 | 0.7378 | 0.6922 | 0.7442 | 510.7624 | 456.5476 | 555.6068 | 435.7921 | 585.7326 | 0.5000 | 0.2182 | 0.2031 | 0.2378 | 0.1922 | 0.2442 | 0.5000 | 0.2182 | 0.2031 | 0.2378 | 0.1922 | 0.2442 | 6 | no |
| 2013-10-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 628 | 1256 | 3096.1220 | 2237.2428 | 0.7226 | 0.7041 | 0.7390 | 0.6966 | 0.7486 | 497.2202 | 454.4349 | 548.4342 | 428.0281 | 566.4123 | 0.5000 | 0.2226 | 0.2041 | 0.2390 | 0.1966 | 0.2486 | 0.5000 | 0.2226 | 0.2041 | 0.2390 | 0.1966 | 0.2486 | 6 | no |
| 2013-10-01T00:00:00+00:00 | oracle | all | 0.5000 | 628 | 1256 | 3096.1220 | 2734.4630 | 0.8832 | 0.8718 | 0.8950 | 0.8656 | 0.9008 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.3832 | 0.3718 | 0.3950 | 0.3656 | 0.4008 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.2500 | 281 | 1124 | 2612.0813 | 653.0203 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 973.7184 | 929.2481 | 1020.9810 | 908.3372 | 1039.0997 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 281 | 1124 | 2612.0813 | 1155.9777 | 0.4426 | 0.4172 | 0.4632 | 0.4074 | 0.4777 | 470.7611 | 417.7794 | 532.8814 | 386.6786 | 554.8437 | 0.2500 | 0.1926 | 0.1672 | 0.2132 | 0.1574 | 0.2277 | 0.2500 | 0.1926 | 0.1672 | 0.2132 | 0.1574 | 0.2277 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 281 | 1124 | 2612.0813 | 1132.0975 | 0.4334 | 0.4142 | 0.4545 | 0.4049 | 0.4619 | 494.6413 | 443.5545 | 538.6612 | 423.9332 | 565.3494 | 0.2500 | 0.1834 | 0.1642 | 0.2045 | 0.1549 | 0.2119 | 0.2500 | 0.1834 | 0.1642 | 0.2045 | 0.1549 | 0.2119 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 281 | 1124 | 2612.0813 | 1132.0975 | 0.4334 | 0.4142 | 0.4545 | 0.4049 | 0.4619 | 494.6413 | 443.5545 | 538.6612 | 423.9332 | 565.3494 | 0.2500 | 0.1834 | 0.1642 | 0.2045 | 0.1549 | 0.2119 | 0.2500 | 0.1834 | 0.1642 | 0.2045 | 0.1549 | 0.2119 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 281 | 1124 | 2612.0813 | 1128.0687 | 0.4319 | 0.4125 | 0.4525 | 0.4033 | 0.4604 | 498.6701 | 445.3207 | 542.3220 | 427.6518 | 569.6884 | 0.2500 | 0.1819 | 0.1625 | 0.2025 | 0.1533 | 0.2104 | 0.2500 | 0.1819 | 0.1625 | 0.2025 | 0.1533 | 0.2104 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 281 | 1124 | 2612.0813 | 1125.1575 | 0.4308 | 0.4081 | 0.4512 | 0.3985 | 0.4630 | 501.5813 | 448.0989 | 558.3102 | 422.3464 | 580.8161 | 0.2500 | 0.1808 | 0.1581 | 0.2012 | 0.1485 | 0.2130 | 0.2500 | 0.1808 | 0.1581 | 0.2012 | 0.1485 | 0.2130 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 281 | 1124 | 2612.0813 | 1033.9908 | 0.3958 | 0.3730 | 0.4202 | 0.3619 | 0.4298 | 592.7479 | 527.6195 | 652.0728 | 503.4709 | 682.0250 | 0.2500 | 0.1458 | 0.1230 | 0.1702 | 0.1119 | 0.1798 | 0.2500 | 0.1458 | 0.1230 | 0.1702 | 0.1119 | 0.1798 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.2500 | 281 | 1124 | 2612.0813 | 1626.7388 | 0.6228 | 0.6043 | 0.6383 | 0.5973 | 0.6482 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3728 | 0.3543 | 0.3883 | 0.3473 | 0.3982 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.1000 | 112 | 1124 | 2612.0813 | 260.2786 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 0.0996 | 578.5504 | 547.2464 | 609.7729 | 532.5839 | 624.5170 | 0.0996 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 112 | 1124 | 2612.0813 | 432.9272 | 0.1657 | 0.1492 | 0.1835 | 0.1411 | 0.1903 | 405.9018 | 354.6488 | 456.9876 | 331.4951 | 480.3085 | 0.0996 | 0.0661 | 0.0495 | 0.0838 | 0.0415 | 0.0907 | 0.0996 | 0.0661 | 0.0495 | 0.0838 | 0.0415 | 0.0907 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 112 | 1124 | 2612.0813 | 451.2275 | 0.1727 | 0.1644 | 0.1808 | 0.1609 | 0.1846 | 387.6015 | 358.6130 | 417.8859 | 345.0913 | 430.1117 | 0.0996 | 0.0731 | 0.0647 | 0.0812 | 0.0613 | 0.0849 | 0.0996 | 0.0731 | 0.0647 | 0.0812 | 0.0613 | 0.0849 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 112 | 1124 | 2612.0813 | 451.2275 | 0.1727 | 0.1644 | 0.1808 | 0.1609 | 0.1846 | 387.6015 | 358.6130 | 417.8859 | 345.0913 | 430.1117 | 0.0996 | 0.0731 | 0.0647 | 0.0812 | 0.0613 | 0.0849 | 0.0996 | 0.0731 | 0.0647 | 0.0812 | 0.0613 | 0.0849 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 112 | 1124 | 2612.0813 | 447.1987 | 0.1712 | 0.1624 | 0.1792 | 0.1588 | 0.1836 | 391.6304 | 362.7199 | 423.3721 | 348.0891 | 435.1716 | 0.0996 | 0.0716 | 0.0627 | 0.0796 | 0.0592 | 0.0840 | 0.0996 | 0.0716 | 0.0627 | 0.0796 | 0.0592 | 0.0840 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 112 | 1124 | 2612.0813 | 462.6904 | 0.1771 | 0.1593 | 0.1933 | 0.1520 | 0.2022 | 376.1386 | 330.6514 | 424.4380 | 304.4357 | 447.8416 | 0.0996 | 0.0775 | 0.0596 | 0.0937 | 0.0524 | 0.1026 | 0.0996 | 0.0775 | 0.0596 | 0.0937 | 0.0524 | 0.1026 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 112 | 1124 | 2612.0813 | 410.3985 | 0.1571 | 0.1387 | 0.1718 | 0.1330 | 0.1812 | 428.4305 | 389.3708 | 484.1137 | 355.8871 | 500.9739 | 0.0996 | 0.0575 | 0.0390 | 0.0721 | 0.0334 | 0.0815 | 0.0996 | 0.0575 | 0.0390 | 0.0721 | 0.0334 | 0.0815 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.1000 | 112 | 1124 | 2612.0813 | 838.8290 | 0.3211 | 0.3080 | 0.3339 | 0.3025 | 0.3398 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0996 | 0.2215 | 0.2083 | 0.2343 | 0.2028 | 0.2401 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.5000 | 562 | 1124 | 2612.0813 | 1306.0407 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 1058.2150 | 1011.3017 | 1102.7175 | 993.1246 | 1123.3055 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 562 | 1124 | 2612.0813 | 1926.2079 | 0.7374 | 0.7151 | 0.7567 | 0.7078 | 0.7670 | 438.0478 | 391.2782 | 484.6300 | 369.2501 | 506.8455 | 0.5000 | 0.2374 | 0.2151 | 0.2567 | 0.2078 | 0.2670 | 0.5000 | 0.2374 | 0.2151 | 0.2567 | 0.2078 | 0.2670 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 562 | 1124 | 2612.0813 | 1901.5660 | 0.7280 | 0.7113 | 0.7448 | 0.7041 | 0.7519 | 462.6897 | 426.6114 | 498.9761 | 410.1091 | 515.2703 | 0.5000 | 0.2280 | 0.2113 | 0.2448 | 0.2041 | 0.2519 | 0.5000 | 0.2280 | 0.2113 | 0.2448 | 0.2041 | 0.2519 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 562 | 1124 | 2612.0813 | 1901.5660 | 0.7280 | 0.7113 | 0.7448 | 0.7041 | 0.7519 | 462.6897 | 426.6114 | 498.9761 | 410.1091 | 515.2703 | 0.5000 | 0.2280 | 0.2113 | 0.2448 | 0.2041 | 0.2519 | 0.5000 | 0.2280 | 0.2113 | 0.2448 | 0.2041 | 0.2519 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 562 | 1124 | 2612.0813 | 1948.9785 | 0.7461 | 0.7236 | 0.7608 | 0.7184 | 0.7739 | 415.2771 | 383.5079 | 466.0165 | 352.0813 | 478.4730 | 0.5000 | 0.2461 | 0.2236 | 0.2608 | 0.2184 | 0.2739 | 0.5000 | 0.2461 | 0.2236 | 0.2608 | 0.2184 | 0.2739 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 562 | 1124 | 2612.0813 | 1895.9726 | 0.7258 | 0.7061 | 0.7462 | 0.6966 | 0.7551 | 468.2831 | 418.8618 | 511.6935 | 399.5329 | 537.0333 | 0.5000 | 0.2258 | 0.2061 | 0.2462 | 0.1966 | 0.2551 | 0.5000 | 0.2258 | 0.2061 | 0.2462 | 0.1966 | 0.2551 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 562 | 1124 | 2612.0813 | 1908.0713 | 0.7305 | 0.7092 | 0.7523 | 0.6988 | 0.7622 | 456.1844 | 401.6360 | 505.1368 | 379.4613 | 532.9075 | 0.5000 | 0.2305 | 0.2092 | 0.2523 | 0.1988 | 0.2622 | 0.5000 | 0.2305 | 0.2092 | 0.2523 | 0.1988 | 0.2622 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.5000 | 562 | 1124 | 2612.0813 | 2364.2557 | 0.9051 | 0.8926 | 0.9156 | 0.8877 | 0.9226 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.4051 | 0.3926 | 0.4156 | 0.3877 | 0.4226 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 307 | 1227 | 2833.4339 | 708.9358 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1034.0145 | 986.4274 | 1079.2310 | 963.2680 | 1104.7610 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 307 | 1227 | 2833.4339 | 1263.9592 | 0.4461 | 0.4228 | 0.4678 | 0.4135 | 0.4787 | 478.9911 | 426.9151 | 541.9093 | 395.3578 | 562.6244 | 0.2502 | 0.1959 | 0.1726 | 0.2176 | 0.1633 | 0.2285 | 0.2502 | 0.1959 | 0.1726 | 0.2176 | 0.1633 | 0.2285 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 307 | 1227 | 2833.4339 | 1252.7107 | 0.4421 | 0.4240 | 0.4624 | 0.4136 | 0.4707 | 490.2395 | 443.6841 | 541.4664 | 417.9424 | 562.5366 | 0.2502 | 0.1919 | 0.1738 | 0.2122 | 0.1633 | 0.2205 | 0.2502 | 0.1919 | 0.1738 | 0.2122 | 0.1633 | 0.2205 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 307 | 1227 | 2833.4339 | 1252.7107 | 0.4421 | 0.4240 | 0.4624 | 0.4136 | 0.4707 | 490.2395 | 443.6841 | 541.4664 | 417.9424 | 562.5366 | 0.2502 | 0.1919 | 0.1738 | 0.2122 | 0.1633 | 0.2205 | 0.2502 | 0.1919 | 0.1738 | 0.2122 | 0.1633 | 0.2205 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 307 | 1227 | 2833.4339 | 1252.7107 | 0.4421 | 0.4240 | 0.4624 | 0.4136 | 0.4707 | 490.2395 | 443.6841 | 541.4664 | 417.9424 | 562.5366 | 0.2502 | 0.1919 | 0.1738 | 0.2122 | 0.1633 | 0.2205 | 0.2502 | 0.1919 | 0.1738 | 0.2122 | 0.1633 | 0.2205 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 307 | 1227 | 2833.4339 | 1219.9098 | 0.4305 | 0.4131 | 0.4588 | 0.3968 | 0.4643 | 523.0405 | 451.9741 | 569.6171 | 435.5800 | 610.5010 | 0.2502 | 0.1803 | 0.1629 | 0.2086 | 0.1466 | 0.2141 | 0.2502 | 0.1803 | 0.1629 | 0.2086 | 0.1466 | 0.2141 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 307 | 1227 | 2833.4339 | 1218.3782 | 0.4300 | 0.4089 | 0.4517 | 0.3980 | 0.4620 | 524.5721 | 466.6104 | 581.7911 | 442.4187 | 606.7255 | 0.2502 | 0.1798 | 0.1587 | 0.2015 | 0.1478 | 0.2118 | 0.2502 | 0.1798 | 0.1587 | 0.2015 | 0.1478 | 0.2118 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 307 | 1227 | 2833.4339 | 1742.9503 | 0.6151 | 0.5986 | 0.6305 | 0.5915 | 0.6388 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2502 | 0.3649 | 0.3484 | 0.3803 | 0.3413 | 0.3885 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 123 | 1227 | 2833.4339 | 284.0362 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 627.4028 | 589.8231 | 663.7580 | 573.8042 | 681.0013 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 123 | 1227 | 2833.4339 | 540.7131 | 0.1908 | 0.1761 | 0.2102 | 0.1658 | 0.2159 | 370.7258 | 316.0715 | 413.5823 | 293.1859 | 448.2657 | 0.1002 | 0.0906 | 0.0758 | 0.1100 | 0.0656 | 0.1156 | 0.1002 | 0.0906 | 0.0758 | 0.1100 | 0.0656 | 0.1156 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 123 | 1227 | 2833.4339 | 501.9004 | 0.1771 | 0.1699 | 0.1857 | 0.1660 | 0.1883 | 409.5385 | 377.1274 | 439.4476 | 363.8972 | 455.1799 | 0.1002 | 0.0769 | 0.0697 | 0.0855 | 0.0657 | 0.0881 | 0.1002 | 0.0769 | 0.0697 | 0.0855 | 0.0657 | 0.0881 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 123 | 1227 | 2833.4339 | 501.9004 | 0.1771 | 0.1699 | 0.1857 | 0.1660 | 0.1883 | 409.5385 | 377.1274 | 439.4476 | 363.8972 | 455.1799 | 0.1002 | 0.0769 | 0.0697 | 0.0855 | 0.0657 | 0.0881 | 0.1002 | 0.0769 | 0.0697 | 0.0855 | 0.0657 | 0.0881 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 123 | 1227 | 2833.4339 | 501.9004 | 0.1771 | 0.1699 | 0.1857 | 0.1660 | 0.1883 | 409.5385 | 377.1274 | 439.4476 | 363.8972 | 455.1799 | 0.1002 | 0.0769 | 0.0697 | 0.0855 | 0.0657 | 0.0881 | 0.1002 | 0.0769 | 0.0697 | 0.0855 | 0.0657 | 0.0881 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 123 | 1227 | 2833.4339 | 522.6715 | 0.1845 | 0.1660 | 0.1990 | 0.1603 | 0.2086 | 388.7675 | 342.2672 | 443.7826 | 315.9240 | 461.6109 | 0.1002 | 0.0842 | 0.0658 | 0.0988 | 0.0601 | 0.1084 | 0.1002 | 0.0842 | 0.0658 | 0.0988 | 0.0601 | 0.1084 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 123 | 1227 | 2833.4339 | 497.7188 | 0.1757 | 0.1590 | 0.1884 | 0.1540 | 0.1973 | 413.7201 | 367.3538 | 470.0567 | 338.6896 | 488.7506 | 0.1002 | 0.0754 | 0.0588 | 0.0882 | 0.0538 | 0.0970 | 0.1002 | 0.0754 | 0.0588 | 0.0882 | 0.0538 | 0.0970 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 123 | 1227 | 2833.4339 | 911.4389 | 0.3217 | 0.3094 | 0.3340 | 0.3032 | 0.3401 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1002 | 0.2214 | 0.2092 | 0.2337 | 0.2030 | 0.2399 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 614 | 1227 | 2833.4339 | 1417.8716 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1148.9605 | 1106.1977 | 1191.6943 | 1084.9781 | 1212.9428 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 614 | 1227 | 2833.4339 | 2082.9153 | 0.7351 | 0.7161 | 0.7521 | 0.7081 | 0.7622 | 483.9167 | 444.8346 | 529.0766 | 419.2677 | 548.5657 | 0.5004 | 0.2347 | 0.2156 | 0.2517 | 0.2077 | 0.2618 | 0.5004 | 0.2347 | 0.2156 | 0.2517 | 0.2077 | 0.2618 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 614 | 1227 | 2833.4339 | 2056.1068 | 0.7257 | 0.7085 | 0.7416 | 0.7019 | 0.7494 | 510.7252 | 473.6400 | 547.4220 | 456.8272 | 564.6233 | 0.5004 | 0.2253 | 0.2081 | 0.2412 | 0.2015 | 0.2490 | 0.5004 | 0.2253 | 0.2081 | 0.2412 | 0.2015 | 0.2490 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 614 | 1227 | 2833.4339 | 2056.1068 | 0.7257 | 0.7085 | 0.7416 | 0.7019 | 0.7494 | 510.7252 | 473.6400 | 547.4220 | 456.8272 | 564.6233 | 0.5004 | 0.2253 | 0.2081 | 0.2412 | 0.2015 | 0.2490 | 0.5004 | 0.2253 | 0.2081 | 0.2412 | 0.2015 | 0.2490 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 614 | 1227 | 2833.4339 | 2079.5595 | 0.7339 | 0.7139 | 0.7509 | 0.7060 | 0.7618 | 487.2726 | 444.1259 | 536.3667 | 419.6805 | 554.8647 | 0.5004 | 0.2335 | 0.2135 | 0.2505 | 0.2056 | 0.2614 | 0.5004 | 0.2335 | 0.2135 | 0.2505 | 0.2056 | 0.2614 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 614 | 1227 | 2833.4339 | 2053.4960 | 0.7247 | 0.7076 | 0.7463 | 0.6954 | 0.7541 | 513.3360 | 460.0282 | 558.1648 | 442.2510 | 584.4211 | 0.5004 | 0.2243 | 0.2072 | 0.2459 | 0.1950 | 0.2536 | 0.5004 | 0.2243 | 0.2072 | 0.2459 | 0.1950 | 0.2536 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 614 | 1227 | 2833.4339 | 2042.5028 | 0.7209 | 0.6977 | 0.7394 | 0.6904 | 0.7514 | 524.3293 | 477.4744 | 581.7022 | 449.0878 | 599.5707 | 0.5004 | 0.2205 | 0.1973 | 0.2390 | 0.1899 | 0.2510 | 0.5004 | 0.2205 | 0.1973 | 0.2390 | 0.1899 | 0.2510 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 614 | 1227 | 2833.4339 | 2566.8321 | 0.9059 | 0.8924 | 0.9180 | 0.8881 | 0.9238 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5004 | 0.4055 | 0.3920 | 0.4176 | 0.3876 | 0.4234 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.2500 | 316 | 1263 | 2989.7208 | 748.0220 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1069.4009 | 1023.0394 | 1116.0010 | 999.7284 | 1139.0734 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 316 | 1263 | 2989.7208 | 1271.6791 | 0.4254 | 0.4017 | 0.4458 | 0.3940 | 0.4567 | 545.7438 | 497.5485 | 617.8988 | 455.4245 | 636.0630 | 0.2502 | 0.1752 | 0.1515 | 0.1956 | 0.1438 | 0.2065 | 0.2502 | 0.1752 | 0.1515 | 0.1956 | 0.1438 | 0.2065 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 316 | 1263 | 2989.7208 | 1272.5732 | 0.4256 | 0.4087 | 0.4453 | 0.3993 | 0.4520 | 544.8497 | 496.9701 | 595.2360 | 473.0934 | 616.6060 | 0.2502 | 0.1755 | 0.1585 | 0.1951 | 0.1491 | 0.2018 | 0.2502 | 0.1755 | 0.1585 | 0.1951 | 0.1491 | 0.2018 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 316 | 1263 | 2989.7208 | 1272.5732 | 0.4256 | 0.4087 | 0.4453 | 0.3993 | 0.4520 | 544.8497 | 496.9701 | 595.2360 | 473.0934 | 616.6060 | 0.2502 | 0.1755 | 0.1585 | 0.1951 | 0.1491 | 0.2018 | 0.2502 | 0.1755 | 0.1585 | 0.1951 | 0.1491 | 0.2018 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 316 | 1263 | 2989.7208 | 1289.1983 | 0.4312 | 0.4101 | 0.4547 | 0.3988 | 0.4636 | 528.2246 | 466.7862 | 589.8506 | 440.1272 | 616.3219 | 0.2502 | 0.1810 | 0.1599 | 0.2045 | 0.1486 | 0.2134 | 0.2502 | 0.1810 | 0.1599 | 0.2045 | 0.1486 | 0.2134 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 316 | 1263 | 2989.7208 | 1223.7010 | 0.4093 | 0.3844 | 0.4309 | 0.3755 | 0.4431 | 593.7219 | 537.3005 | 672.5331 | 495.9462 | 691.4976 | 0.2502 | 0.1591 | 0.1342 | 0.1807 | 0.1253 | 0.1929 | 0.2502 | 0.1591 | 0.1342 | 0.1807 | 0.1253 | 0.1929 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 316 | 1263 | 2989.7208 | 1268.5950 | 0.4243 | 0.3990 | 0.4427 | 0.3928 | 0.4559 | 548.8279 | 498.6878 | 622.8481 | 456.7883 | 640.8674 | 0.2502 | 0.1741 | 0.1488 | 0.1925 | 0.1426 | 0.2057 | 0.2502 | 0.1741 | 0.1488 | 0.1925 | 0.1426 | 0.2057 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.2500 | 316 | 1263 | 2989.7208 | 1817.4229 | 0.6079 | 0.5929 | 0.6234 | 0.5857 | 0.6301 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2502 | 0.3577 | 0.3427 | 0.3732 | 0.3355 | 0.3799 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.1000 | 126 | 1263 | 2989.7208 | 298.2619 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 651.6025 | 618.9442 | 688.7610 | 601.5604 | 701.6445 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 126 | 1263 | 2989.7208 | 542.7678 | 0.1815 | 0.1650 | 0.1964 | 0.1584 | 0.2047 | 407.0966 | 361.0416 | 461.5041 | 334.2901 | 479.9031 | 0.0998 | 0.0818 | 0.0652 | 0.0967 | 0.0586 | 0.1050 | 0.0998 | 0.0818 | 0.0652 | 0.0967 | 0.0586 | 0.1050 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 126 | 1263 | 2989.7208 | 507.4184 | 0.1697 | 0.1625 | 0.1775 | 0.1586 | 0.1808 | 442.4460 | 414.9921 | 470.8607 | 399.8813 | 485.0107 | 0.0998 | 0.0700 | 0.0628 | 0.0777 | 0.0588 | 0.0811 | 0.0998 | 0.0700 | 0.0628 | 0.0777 | 0.0588 | 0.0811 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 126 | 1263 | 2989.7208 | 507.4184 | 0.1697 | 0.1625 | 0.1775 | 0.1586 | 0.1808 | 442.4460 | 414.9921 | 470.8607 | 399.8813 | 485.0107 | 0.0998 | 0.0700 | 0.0628 | 0.0777 | 0.0588 | 0.0811 | 0.0998 | 0.0700 | 0.0628 | 0.0777 | 0.0588 | 0.0811 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 126 | 1263 | 2989.7208 | 530.2908 | 0.1774 | 0.1611 | 0.1965 | 0.1513 | 0.2034 | 419.5737 | 363.2428 | 469.6036 | 345.3798 | 493.7675 | 0.0998 | 0.0776 | 0.0613 | 0.0967 | 0.0515 | 0.1037 | 0.0998 | 0.0776 | 0.0613 | 0.0967 | 0.0515 | 0.1037 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 126 | 1263 | 2989.7208 | 459.8325 | 0.1538 | 0.1391 | 0.1734 | 0.1286 | 0.1790 | 490.0319 | 431.8585 | 540.5670 | 412.3281 | 567.7357 | 0.0998 | 0.0540 | 0.0393 | 0.0736 | 0.0289 | 0.0792 | 0.0998 | 0.0540 | 0.0393 | 0.0736 | 0.0289 | 0.0792 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 126 | 1263 | 2989.7208 | 512.3083 | 0.1714 | 0.1552 | 0.1880 | 0.1475 | 0.1952 | 437.5561 | 386.9979 | 489.7580 | 361.5105 | 513.6017 | 0.0998 | 0.0716 | 0.0555 | 0.0883 | 0.0477 | 0.0955 | 0.0998 | 0.0716 | 0.0555 | 0.0883 | 0.0477 | 0.0955 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.1000 | 126 | 1263 | 2989.7208 | 949.8644 | 0.3177 | 0.3067 | 0.3302 | 0.3003 | 0.3351 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0998 | 0.2179 | 0.2069 | 0.2304 | 0.2006 | 0.2353 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.5000 | 632 | 1263 | 2989.7208 | 1496.0440 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1186.4429 | 1144.7873 | 1228.5056 | 1122.9105 | 1249.9752 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 632 | 1263 | 2989.7208 | 2175.7621 | 0.7277 | 0.7080 | 0.7475 | 0.6983 | 0.7572 | 506.7247 | 454.1783 | 556.1874 | 430.5182 | 582.9311 | 0.5004 | 0.2274 | 0.2076 | 0.2471 | 0.1979 | 0.2568 | 0.5004 | 0.2274 | 0.2076 | 0.2471 | 0.1979 | 0.2568 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 632 | 1263 | 2989.7208 | 2141.0220 | 0.7161 | 0.6999 | 0.7320 | 0.6925 | 0.7398 | 541.4648 | 504.8990 | 580.0706 | 485.3454 | 597.5842 | 0.5004 | 0.2157 | 0.1995 | 0.2316 | 0.1921 | 0.2394 | 0.5004 | 0.2157 | 0.1995 | 0.2316 | 0.1921 | 0.2394 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 632 | 1263 | 2989.7208 | 2141.0220 | 0.7161 | 0.6999 | 0.7320 | 0.6925 | 0.7398 | 541.4648 | 504.8990 | 580.0706 | 485.3454 | 597.5842 | 0.5004 | 0.2157 | 0.1995 | 0.2316 | 0.1921 | 0.2394 | 0.5004 | 0.2157 | 0.1995 | 0.2316 | 0.1921 | 0.2394 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 632 | 1263 | 2989.7208 | 2167.8809 | 0.7251 | 0.7056 | 0.7440 | 0.6971 | 0.7531 | 514.6059 | 464.1427 | 562.4380 | 441.0636 | 588.1483 | 0.5004 | 0.2247 | 0.2052 | 0.2436 | 0.1967 | 0.2527 | 0.5004 | 0.2247 | 0.2052 | 0.2436 | 0.1967 | 0.2527 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 632 | 1263 | 2989.7208 | 2161.9759 | 0.7231 | 0.7032 | 0.7429 | 0.6943 | 0.7520 | 520.5110 | 468.6556 | 571.3720 | 445.5934 | 595.4286 | 0.5004 | 0.2227 | 0.2028 | 0.2425 | 0.1939 | 0.2516 | 0.5004 | 0.2227 | 0.2028 | 0.2425 | 0.1939 | 0.2516 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 632 | 1263 | 2989.7208 | 2178.4487 | 0.7286 | 0.7093 | 0.7478 | 0.7006 | 0.7567 | 504.0381 | 453.0168 | 556.4783 | 429.7664 | 578.3098 | 0.5004 | 0.2283 | 0.2089 | 0.2474 | 0.2002 | 0.2563 | 0.5004 | 0.2283 | 0.2089 | 0.2474 | 0.2002 | 0.2563 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.5000 | 632 | 1263 | 2989.7208 | 2682.4868 | 0.8972 | 0.8846 | 0.9086 | 0.8793 | 0.9152 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5004 | 0.3968 | 0.3842 | 0.4082 | 0.3789 | 0.4148 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.2500 | 309 | 1235 | 3025.0340 | 756.8709 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 1085.3814 | 1034.9819 | 1132.9861 | 1012.5142 | 1158.2487 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 309 | 1235 | 3025.0340 | 1367.4405 | 0.4520 | 0.4273 | 0.4733 | 0.4183 | 0.4858 | 474.8118 | 418.7620 | 545.5466 | 384.0389 | 565.5848 | 0.2502 | 0.2018 | 0.1771 | 0.2231 | 0.1681 | 0.2356 | 0.2502 | 0.2018 | 0.1771 | 0.2231 | 0.1681 | 0.2356 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 309 | 1235 | 3025.0340 | 1340.5792 | 0.4432 | 0.4251 | 0.4624 | 0.4165 | 0.4698 | 501.6731 | 454.8202 | 549.0763 | 433.3000 | 570.0462 | 0.2502 | 0.1930 | 0.1749 | 0.2122 | 0.1663 | 0.2196 | 0.2502 | 0.1930 | 0.1749 | 0.2122 | 0.1663 | 0.2196 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 309 | 1235 | 3025.0340 | 1340.5792 | 0.4432 | 0.4251 | 0.4624 | 0.4165 | 0.4698 | 501.6731 | 454.8202 | 549.0763 | 433.3000 | 570.0462 | 0.2502 | 0.1930 | 0.1749 | 0.2122 | 0.1663 | 0.2196 | 0.2502 | 0.1930 | 0.1749 | 0.2122 | 0.1663 | 0.2196 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 309 | 1235 | 3025.0340 | 1338.5153 | 0.4425 | 0.4264 | 0.4649 | 0.4128 | 0.4722 | 503.7370 | 439.6406 | 549.1357 | 422.4009 | 585.0731 | 0.2502 | 0.1923 | 0.1762 | 0.2147 | 0.1625 | 0.2220 | 0.2502 | 0.1923 | 0.1762 | 0.2147 | 0.1625 | 0.2220 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 309 | 1235 | 3025.0340 | 1313.4947 | 0.4342 | 0.4095 | 0.4515 | 0.4035 | 0.4649 | 528.7576 | 476.2807 | 600.1745 | 440.0983 | 617.4169 | 0.2502 | 0.1840 | 0.1593 | 0.2013 | 0.1533 | 0.2147 | 0.2502 | 0.1840 | 0.1593 | 0.2013 | 0.1533 | 0.2147 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 309 | 1235 | 3025.0340 | 1300.4417 | 0.4299 | 0.4080 | 0.4476 | 0.4002 | 0.4595 | 541.8106 | 486.5499 | 608.1375 | 455.6505 | 627.9706 | 0.2502 | 0.1797 | 0.1578 | 0.1974 | 0.1500 | 0.2093 | 0.2502 | 0.1797 | 0.1578 | 0.1974 | 0.1500 | 0.2093 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.2500 | 309 | 1235 | 3025.0340 | 1842.2523 | 0.6090 | 0.5932 | 0.6240 | 0.5865 | 0.6315 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2502 | 0.3588 | 0.3430 | 0.3738 | 0.3363 | 0.3813 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.1000 | 124 | 1235 | 3025.0340 | 303.7281 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 666.1970 | 625.8592 | 706.3294 | 609.5270 | 722.8670 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 124 | 1235 | 3025.0340 | 549.8608 | 0.1818 | 0.1693 | 0.2011 | 0.1579 | 0.2056 | 420.0644 | 353.8812 | 458.8303 | 343.2237 | 496.9050 | 0.1004 | 0.0814 | 0.0689 | 0.1007 | 0.0575 | 0.1052 | 0.1004 | 0.0814 | 0.0689 | 0.1007 | 0.0575 | 0.1052 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 124 | 1235 | 3025.0340 | 537.9670 | 0.1778 | 0.1704 | 0.1858 | 0.1668 | 0.1889 | 431.9581 | 400.1314 | 461.9462 | 384.0196 | 479.8966 | 0.1004 | 0.0774 | 0.0700 | 0.0854 | 0.0664 | 0.0885 | 0.1004 | 0.0774 | 0.0700 | 0.0854 | 0.0664 | 0.0885 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 124 | 1235 | 3025.0340 | 537.9670 | 0.1778 | 0.1704 | 0.1858 | 0.1668 | 0.1889 | 431.9581 | 400.1314 | 461.9462 | 384.0196 | 479.8966 | 0.1004 | 0.0774 | 0.0700 | 0.0854 | 0.0664 | 0.0885 | 0.1004 | 0.0774 | 0.0700 | 0.0854 | 0.0664 | 0.0885 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 124 | 1235 | 3025.0340 | 573.5354 | 0.1896 | 0.1719 | 0.2050 | 0.1654 | 0.2138 | 396.3897 | 349.1408 | 452.6583 | 319.6042 | 473.1753 | 0.1004 | 0.0892 | 0.0715 | 0.1045 | 0.0650 | 0.1134 | 0.1004 | 0.0892 | 0.0715 | 0.1045 | 0.0650 | 0.1134 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 124 | 1235 | 3025.0340 | 519.4106 | 0.1717 | 0.1562 | 0.1860 | 0.1492 | 0.1942 | 450.5145 | 399.4515 | 507.7049 | 370.7046 | 530.3245 | 0.1004 | 0.0713 | 0.0558 | 0.0856 | 0.0488 | 0.0938 | 0.1004 | 0.0713 | 0.0558 | 0.0856 | 0.0488 | 0.0938 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 124 | 1235 | 3025.0340 | 548.6756 | 0.1814 | 0.1631 | 0.1959 | 0.1581 | 0.2046 | 421.2495 | 374.4535 | 480.6921 | 341.8371 | 500.6619 | 0.1004 | 0.0810 | 0.0627 | 0.0955 | 0.0577 | 0.1042 | 0.1004 | 0.0810 | 0.0627 | 0.0955 | 0.0577 | 0.1042 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.1000 | 124 | 1235 | 3025.0340 | 969.9251 | 0.3206 | 0.3072 | 0.3323 | 0.3027 | 0.3386 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1004 | 0.2202 | 0.2068 | 0.2319 | 0.2023 | 0.2382 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.5000 | 618 | 1235 | 3025.0340 | 1513.7417 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1194.2944 | 1147.1284 | 1240.4044 | 1123.8385 | 1264.7503 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 618 | 1235 | 3025.0340 | 2277.3855 | 0.7528 | 0.7318 | 0.7723 | 0.7247 | 0.7810 | 430.6506 | 385.3252 | 480.8790 | 362.9647 | 498.3365 | 0.5004 | 0.2524 | 0.2314 | 0.2719 | 0.2243 | 0.2806 | 0.5004 | 0.2524 | 0.2314 | 0.2719 | 0.2243 | 0.2806 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 618 | 1235 | 3025.0340 | 2246.9756 | 0.7428 | 0.7258 | 0.7582 | 0.7192 | 0.7663 | 461.0605 | 424.7272 | 496.0600 | 409.6234 | 512.4976 | 0.5004 | 0.2424 | 0.2254 | 0.2578 | 0.2188 | 0.2659 | 0.5004 | 0.2424 | 0.2254 | 0.2578 | 0.2188 | 0.2659 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 618 | 1235 | 3025.0340 | 2246.9756 | 0.7428 | 0.7258 | 0.7582 | 0.7192 | 0.7663 | 461.0605 | 424.7272 | 496.0600 | 409.6234 | 512.4976 | 0.5004 | 0.2424 | 0.2254 | 0.2578 | 0.2188 | 0.2659 | 0.5004 | 0.2424 | 0.2254 | 0.2578 | 0.2188 | 0.2659 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 618 | 1235 | 3025.0340 | 2241.5933 | 0.7410 | 0.7229 | 0.7612 | 0.7131 | 0.7689 | 466.4428 | 412.2604 | 509.9356 | 396.2394 | 536.6462 | 0.5004 | 0.2406 | 0.2225 | 0.2608 | 0.2127 | 0.2685 | 0.5004 | 0.2406 | 0.2225 | 0.2608 | 0.2127 | 0.2685 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 618 | 1235 | 3025.0340 | 2241.3452 | 0.7409 | 0.7217 | 0.7610 | 0.7122 | 0.7696 | 466.6909 | 415.4847 | 511.7402 | 395.6545 | 537.7273 | 0.5004 | 0.2405 | 0.2212 | 0.2605 | 0.2118 | 0.2692 | 0.5004 | 0.2405 | 0.2212 | 0.2605 | 0.2118 | 0.2692 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 618 | 1235 | 3025.0340 | 2243.4793 | 0.7416 | 0.7228 | 0.7623 | 0.7127 | 0.7706 | 464.5568 | 409.9327 | 510.6314 | 393.7577 | 535.3560 | 0.5004 | 0.2412 | 0.2224 | 0.2619 | 0.2123 | 0.2702 | 0.5004 | 0.2412 | 0.2224 | 0.2619 | 0.2123 | 0.2702 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.5000 | 618 | 1235 | 3025.0340 | 2708.0361 | 0.8952 | 0.8824 | 0.9084 | 0.8767 | 0.9137 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5004 | 0.3948 | 0.3820 | 0.4080 | 0.3763 | 0.4133 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.2500 | 318 | 1273 | 3025.8441 | 755.8668 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 0.2498 | 1069.3386 | 1028.4279 | 1112.7365 | 1006.2335 | 1132.4437 | 0.2498 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 318 | 1273 | 3025.8441 | 1334.3452 | 0.4410 | 0.4253 | 0.4641 | 0.4105 | 0.4714 | 490.8602 | 423.8227 | 532.2718 | 409.1010 | 572.6194 | 0.2498 | 0.1912 | 0.1754 | 0.2143 | 0.1607 | 0.2216 | 0.2498 | 0.1912 | 0.1754 | 0.2143 | 0.1607 | 0.2216 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 318 | 1273 | 3025.8441 | 1292.5258 | 0.4272 | 0.4097 | 0.4455 | 0.4011 | 0.4532 | 532.6796 | 484.4737 | 581.5355 | 457.8345 | 607.5247 | 0.2498 | 0.1774 | 0.1599 | 0.1957 | 0.1513 | 0.2034 | 0.2498 | 0.1774 | 0.1599 | 0.1957 | 0.1513 | 0.2034 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 318 | 1273 | 3025.8441 | 1292.5258 | 0.4272 | 0.4097 | 0.4455 | 0.4011 | 0.4532 | 532.6796 | 484.4737 | 581.5355 | 457.8345 | 607.5247 | 0.2498 | 0.1774 | 0.1599 | 0.1957 | 0.1513 | 0.2034 | 0.2498 | 0.1774 | 0.1599 | 0.1957 | 0.1513 | 0.2034 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 318 | 1273 | 3025.8441 | 1348.9424 | 0.4458 | 0.4257 | 0.4655 | 0.4166 | 0.4750 | 476.2630 | 421.9161 | 531.8987 | 396.9320 | 555.5939 | 0.2498 | 0.1960 | 0.1759 | 0.2157 | 0.1668 | 0.2252 | 0.2498 | 0.1960 | 0.1759 | 0.2157 | 0.1668 | 0.2252 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 318 | 1273 | 3025.8441 | 1311.8152 | 0.4335 | 0.4113 | 0.4514 | 0.4032 | 0.4639 | 513.3902 | 467.5772 | 577.1308 | 431.9314 | 594.8490 | 0.2498 | 0.1837 | 0.1615 | 0.2015 | 0.1534 | 0.2141 | 0.2498 | 0.1837 | 0.1615 | 0.2015 | 0.1534 | 0.2141 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 318 | 1273 | 3025.8441 | 1262.8172 | 0.4173 | 0.3975 | 0.4366 | 0.3890 | 0.4457 | 562.3882 | 505.8818 | 621.0603 | 478.0291 | 646.7474 | 0.2498 | 0.1675 | 0.1477 | 0.1868 | 0.1392 | 0.1959 | 0.2498 | 0.1675 | 0.1477 | 0.1868 | 0.1392 | 0.1959 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.2500 | 318 | 1273 | 3025.8441 | 1825.2054 | 0.6032 | 0.5877 | 0.6173 | 0.5803 | 0.6261 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2498 | 0.3534 | 0.3379 | 0.3675 | 0.3305 | 0.3763 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.1000 | 127 | 1273 | 3025.8441 | 301.8713 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 0.0998 | 645.8611 | 610.3821 | 677.5632 | 596.6393 | 695.0829 | 0.0998 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 127 | 1273 | 3025.8441 | 572.8986 | 0.1893 | 0.1719 | 0.2008 | 0.1675 | 0.2112 | 374.8339 | 335.1203 | 431.3763 | 304.4295 | 445.2383 | 0.0998 | 0.0896 | 0.0721 | 0.1011 | 0.0677 | 0.1114 | 0.0998 | 0.0896 | 0.0721 | 0.1011 | 0.0677 | 0.1114 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 127 | 1273 | 3025.8441 | 516.1974 | 0.1706 | 0.1641 | 0.1780 | 0.1605 | 0.1807 | 431.5350 | 399.4923 | 461.6327 | 385.3243 | 477.7458 | 0.0998 | 0.0708 | 0.0643 | 0.0782 | 0.0607 | 0.0810 | 0.0998 | 0.0708 | 0.0643 | 0.0782 | 0.0607 | 0.0810 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 127 | 1273 | 3025.8441 | 516.1974 | 0.1706 | 0.1641 | 0.1780 | 0.1605 | 0.1807 | 431.5350 | 399.4923 | 461.6327 | 385.3243 | 477.7458 | 0.0998 | 0.0708 | 0.0643 | 0.0782 | 0.0607 | 0.0810 | 0.0998 | 0.0708 | 0.0643 | 0.0782 | 0.0607 | 0.0810 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 127 | 1273 | 3025.8441 | 535.8002 | 0.1771 | 0.1589 | 0.1914 | 0.1534 | 0.2008 | 411.9322 | 364.8989 | 470.1101 | 334.6794 | 489.1850 | 0.0998 | 0.0773 | 0.0591 | 0.0917 | 0.0536 | 0.1010 | 0.0998 | 0.0773 | 0.0591 | 0.0917 | 0.0536 | 0.1010 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 127 | 1273 | 3025.8441 | 534.7704 | 0.1767 | 0.1619 | 0.1955 | 0.1523 | 0.2011 | 412.9620 | 354.8261 | 456.4058 | 339.1228 | 486.8012 | 0.0998 | 0.0770 | 0.0621 | 0.0958 | 0.0526 | 0.1014 | 0.0998 | 0.0770 | 0.0621 | 0.0958 | 0.0526 | 0.1014 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 127 | 1273 | 3025.8441 | 549.3954 | 0.1816 | 0.1648 | 0.1948 | 0.1587 | 0.2044 | 398.3371 | 358.1639 | 451.6189 | 330.5601 | 466.1140 | 0.0998 | 0.0818 | 0.0650 | 0.0950 | 0.0589 | 0.1047 | 0.0998 | 0.0818 | 0.0650 | 0.0950 | 0.0589 | 0.1047 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.1000 | 127 | 1273 | 3025.8441 | 947.7324 | 0.3132 | 0.3015 | 0.3227 | 0.2972 | 0.3292 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0998 | 0.2134 | 0.2017 | 0.2229 | 0.1975 | 0.2294 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.5000 | 637 | 1273 | 3025.8441 | 1514.1105 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 1201.3107 | 1153.3894 | 1244.3264 | 1136.5797 | 1266.0417 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 637 | 1273 | 3025.8441 | 2183.1769 | 0.7215 | 0.7023 | 0.7391 | 0.6946 | 0.7484 | 532.2444 | 480.6213 | 582.2734 | 457.9019 | 606.5868 | 0.5004 | 0.2211 | 0.2019 | 0.2387 | 0.1942 | 0.2480 | 0.5004 | 0.2211 | 0.2019 | 0.2387 | 0.1942 | 0.2480 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 637 | 1273 | 3025.8441 | 2155.2379 | 0.7123 | 0.6983 | 0.7275 | 0.6903 | 0.7343 | 560.1833 | 519.9570 | 596.0027 | 503.9417 | 616.4249 | 0.5004 | 0.2119 | 0.1979 | 0.2271 | 0.1899 | 0.2339 | 0.5004 | 0.2119 | 0.1979 | 0.2271 | 0.1899 | 0.2339 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 637 | 1273 | 3025.8441 | 2155.2379 | 0.7123 | 0.6983 | 0.7275 | 0.6903 | 0.7343 | 560.1833 | 519.9570 | 596.0027 | 503.9417 | 616.4249 | 0.5004 | 0.2119 | 0.1979 | 0.2271 | 0.1899 | 0.2339 | 0.5004 | 0.2119 | 0.1979 | 0.2271 | 0.1899 | 0.2339 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 637 | 1273 | 3025.8441 | 2166.1663 | 0.7159 | 0.6979 | 0.7345 | 0.6894 | 0.7424 | 549.2550 | 501.5955 | 598.3914 | 478.7364 | 619.7735 | 0.5004 | 0.2155 | 0.1975 | 0.2341 | 0.1890 | 0.2420 | 0.5004 | 0.2155 | 0.1975 | 0.2341 | 0.1890 | 0.2420 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 637 | 1273 | 3025.8441 | 2170.7088 | 0.7174 | 0.7007 | 0.7366 | 0.6903 | 0.7445 | 544.7125 | 489.8051 | 592.1103 | 469.5453 | 619.8797 | 0.5004 | 0.2170 | 0.2004 | 0.2362 | 0.1899 | 0.2441 | 0.5004 | 0.2170 | 0.2004 | 0.2362 | 0.1899 | 0.2441 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 637 | 1273 | 3025.8441 | 2138.7965 | 0.7068 | 0.6873 | 0.7250 | 0.6784 | 0.7353 | 576.6247 | 526.5871 | 629.4562 | 498.2501 | 654.9994 | 0.5004 | 0.2065 | 0.1869 | 0.2246 | 0.1780 | 0.2349 | 0.5004 | 0.2065 | 0.1869 | 0.2246 | 0.1780 | 0.2349 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.5000 | 637 | 1273 | 3025.8441 | 2715.4212 | 0.8974 | 0.8855 | 0.9087 | 0.8800 | 0.9148 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5004 | 0.3970 | 0.3851 | 0.4083 | 0.3796 | 0.4144 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.2500 | 2471 | 9883 | 23444.3936 | 5861.7085 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 8385.8498 | 8241.0058 | 8515.4119 | 8186.8977 | 8584.8020 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.2500 | 2471 | 9883 | 23444.3936 | 10241.5353 | 0.4368 | 0.4285 | 0.4440 | 0.4256 | 0.4481 | 4006.0230 | 3839.7177 | 4171.8644 | 3764.9373 | 4247.1087 | 0.2500 | 0.1868 | 0.1785 | 0.1939 | 0.1756 | 0.1981 | 0.2500 | 0.1868 | 0.1785 | 0.1939 | 0.1756 | 0.1981 | 6 | no |
| ALL | p_win | P0 | 0.2500 | 2471 | 9883 | 23444.3936 | 10105.7202 | 0.4311 | 0.4246 | 0.4372 | 0.4219 | 0.4402 | 4141.8381 | 4002.7662 | 4280.7835 | 3945.5804 | 4338.0958 | 0.2500 | 0.1810 | 0.1746 | 0.1872 | 0.1718 | 0.1902 | 0.2500 | 0.1810 | 0.1746 | 0.1872 | 0.1718 | 0.1902 | 6 | yes |
| ALL | p_win | P1 | 0.2500 | 2471 | 9883 | 23444.3936 | 10105.7202 | 0.4311 | 0.4246 | 0.4372 | 0.4219 | 0.4402 | 4141.8381 | 4002.7662 | 4280.7835 | 3945.5804 | 4338.0958 | 0.2500 | 0.1810 | 0.1746 | 0.1872 | 0.1718 | 0.1902 | 0.2500 | 0.1810 | 0.1746 | 0.1872 | 0.1718 | 0.1902 | 6 | yes |
| ALL | p_win | P2 | 0.2500 | 2471 | 9883 | 23444.3936 | 10172.6693 | 0.4339 | 0.4276 | 0.4410 | 0.4240 | 0.4438 | 4074.8890 | 3907.4893 | 4212.1480 | 3860.2978 | 4289.4802 | 0.2500 | 0.1839 | 0.1776 | 0.1910 | 0.1739 | 0.1938 | 0.2500 | 0.1839 | 0.1776 | 0.1910 | 0.1739 | 0.1938 | 6 | no |
| ALL | p_win | local_eb | 0.2500 | 2471 | 9883 | 23444.3936 | 10054.2716 | 0.4289 | 0.4199 | 0.4349 | 0.4180 | 0.4397 | 4193.2867 | 4057.7187 | 4394.3238 | 3953.7970 | 4432.7764 | 0.2500 | 0.1788 | 0.1699 | 0.1849 | 0.1680 | 0.1896 | 0.2500 | 0.1788 | 0.1699 | 0.1849 | 0.1680 | 0.1896 | 6 | no |
| ALL | p_win | text_lr | 0.2500 | 2471 | 9883 | 23444.3936 | 9826.9801 | 0.4192 | 0.4111 | 0.4252 | 0.4087 | 0.4296 | 4420.5782 | 4254.3348 | 4585.1120 | 4185.4971 | 4655.6594 | 0.2500 | 0.1691 | 0.1610 | 0.1752 | 0.1587 | 0.1795 | 0.2500 | 0.1691 | 0.1610 | 0.1752 | 0.1587 | 0.1795 | 6 | no |
| ALL | oracle | all | 0.2500 | 2471 | 9883 | 23444.3936 | 14247.5583 | 0.6077 | 0.6022 | 0.6128 | 0.5999 | 0.6156 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.3577 | 0.3522 | 0.3628 | 0.3498 | 0.3656 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.1000 | 988 | 9883 | 23444.3936 | 2343.8107 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 5031.5265 | 4933.2099 | 5116.2493 | 4891.1331 | 5171.9199 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.1000 | 988 | 9883 | 23444.3936 | 4228.8817 | 0.1804 | 0.1746 | 0.1860 | 0.1722 | 0.1886 | 3146.4555 | 2997.5790 | 3280.7073 | 2940.5468 | 3352.3642 | 0.1000 | 0.0804 | 0.0746 | 0.0860 | 0.0722 | 0.0886 | 0.1000 | 0.0804 | 0.0746 | 0.0860 | 0.0722 | 0.0886 | 6 | no |
| ALL | p_win | P0 | 0.1000 | 988 | 9883 | 23444.3936 | 4040.8420 | 0.1724 | 0.1697 | 0.1749 | 0.1685 | 0.1762 | 3334.4952 | 3249.2656 | 3410.1020 | 3209.9984 | 3458.9921 | 0.1000 | 0.0724 | 0.0697 | 0.0749 | 0.0685 | 0.0762 | 0.1000 | 0.0724 | 0.0697 | 0.0749 | 0.0685 | 0.0762 | 6 | yes |
| ALL | p_win | P1 | 0.1000 | 988 | 9883 | 23444.3936 | 4040.8420 | 0.1724 | 0.1697 | 0.1749 | 0.1685 | 0.1762 | 3334.4952 | 3249.2656 | 3410.1020 | 3209.9984 | 3458.9921 | 0.1000 | 0.0724 | 0.0697 | 0.0749 | 0.0685 | 0.0762 | 0.1000 | 0.0724 | 0.0697 | 0.0749 | 0.0685 | 0.0762 | 6 | yes |
| ALL | p_win | P2 | 0.1000 | 988 | 9883 | 23444.3936 | 4114.8567 | 0.1755 | 0.1706 | 0.1793 | 0.1691 | 0.1819 | 3260.4805 | 3158.0805 | 3371.3336 | 3095.0181 | 3425.9429 | 0.1000 | 0.0755 | 0.0707 | 0.0794 | 0.0691 | 0.0819 | 0.1000 | 0.0755 | 0.0707 | 0.0794 | 0.0691 | 0.0819 | 6 | no |
| ALL | p_win | local_eb | 0.1000 | 988 | 9883 | 23444.3936 | 4023.2170 | 0.1716 | 0.1653 | 0.1768 | 0.1631 | 0.1801 | 3352.1202 | 3207.9665 | 3512.0832 | 3133.4687 | 3570.7717 | 0.1000 | 0.0716 | 0.0653 | 0.0768 | 0.0631 | 0.0802 | 0.1000 | 0.0716 | 0.0653 | 0.0768 | 0.0631 | 0.0802 | 6 | no |
| ALL | p_win | text_lr | 0.1000 | 988 | 9883 | 23444.3936 | 4053.9382 | 0.1729 | 0.1667 | 0.1773 | 0.1649 | 0.1809 | 3321.3991 | 3198.6588 | 3484.2053 | 3109.3053 | 3533.4928 | 0.1000 | 0.0729 | 0.0667 | 0.0774 | 0.0649 | 0.0810 | 0.1000 | 0.0729 | 0.0667 | 0.0774 | 0.0649 | 0.0810 | 6 | no |
| ALL | oracle | all | 0.1000 | 988 | 9883 | 23444.3936 | 7375.3372 | 0.3146 | 0.3099 | 0.3188 | 0.3084 | 0.3208 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 | 0.2146 | 0.2099 | 0.2188 | 0.2084 | 0.2208 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.5000 | 4944 | 9883 | 23444.3936 | 11728.1025 | 0.5003 | 0.5002 | 0.5003 | 0.5002 | 0.5003 | 9296.4287 | 9168.8574 | 9413.8539 | 9118.1447 | 9474.7127 | 0.5003 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.5000 | 4944 | 9883 | 23444.3936 | 17140.8146 | 0.7311 | 0.7247 | 0.7373 | 0.7215 | 0.7407 | 3883.7165 | 3750.5342 | 4026.9810 | 3679.1829 | 4088.2502 | 0.5003 | 0.2309 | 0.2245 | 0.2370 | 0.2213 | 0.2405 | 0.5003 | 0.2309 | 0.2245 | 0.2370 | 0.2213 | 0.2405 | 6 | no |
| ALL | p_win | P0 | 0.5000 | 4944 | 9883 | 23444.3936 | 16870.0857 | 0.7196 | 0.7145 | 0.7251 | 0.7119 | 0.7273 | 4154.4454 | 4038.0719 | 4252.4536 | 3996.1957 | 4312.6951 | 0.5003 | 0.2193 | 0.2143 | 0.2248 | 0.2116 | 0.2271 | 0.5003 | 0.2193 | 0.2143 | 0.2248 | 0.2116 | 0.2271 | 6 | yes |
| ALL | p_win | P1 | 0.5000 | 4944 | 9883 | 23444.3936 | 16870.0857 | 0.7196 | 0.7145 | 0.7251 | 0.7119 | 0.7273 | 4154.4454 | 4038.0719 | 4252.4536 | 3996.1957 | 4312.6951 | 0.5003 | 0.2193 | 0.2143 | 0.2248 | 0.2116 | 0.2271 | 0.5003 | 0.2193 | 0.2143 | 0.2248 | 0.2116 | 0.2271 | 6 | yes |
| ALL | p_win | P2 | 0.5000 | 4944 | 9883 | 23444.3936 | 17008.5511 | 0.7255 | 0.7186 | 0.7314 | 0.7163 | 0.7346 | 4015.9801 | 3888.1701 | 4153.9714 | 3818.0960 | 4213.8642 | 0.5003 | 0.2252 | 0.2184 | 0.2312 | 0.2161 | 0.2344 | 0.5003 | 0.2252 | 0.2184 | 0.2312 | 0.2161 | 0.2344 | 6 | no |
| ALL | p_win | local_eb | 0.5000 | 4944 | 9883 | 23444.3936 | 16966.1391 | 0.7237 | 0.7171 | 0.7300 | 0.7141 | 0.7332 | 4058.3921 | 3906.7480 | 4191.4014 | 3849.6785 | 4267.1056 | 0.5003 | 0.2234 | 0.2169 | 0.2297 | 0.2139 | 0.2330 | 0.5003 | 0.2234 | 0.2169 | 0.2297 | 0.2139 | 0.2330 | 6 | no |
| ALL | p_win | text_lr | 0.5000 | 4944 | 9883 | 23444.3936 | 16937.1325 | 0.7224 | 0.7147 | 0.7283 | 0.7123 | 0.7326 | 4087.3986 | 3936.7563 | 4239.7347 | 3870.0832 | 4304.7140 | 0.5003 | 0.2222 | 0.2145 | 0.2281 | 0.2120 | 0.2323 | 0.5003 | 0.2222 | 0.2145 | 0.2281 | 0.2120 | 0.2323 | 6 | no |
| ALL | oracle | all | 0.5000 | 4944 | 9883 | 23444.3936 | 21024.5311 | 0.8968 | 0.8925 | 0.9006 | 0.8906 | 0.9029 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5003 | 0.3965 | 0.3922 | 0.4004 | 0.3904 | 0.4027 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |

## Figures

- figures/reliability-synthetic.png
- figures/score_by_origin-synthetic.png
- figures/coverage-synthetic.png
- figures/decision_value-synthetic.png
