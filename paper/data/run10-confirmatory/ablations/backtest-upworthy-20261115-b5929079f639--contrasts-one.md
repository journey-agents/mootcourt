# Backtest report: upworthy

> The card is advice before launch. The live test decides. Moot Court never changes the decision to launch, the traffic split or when a test stops.

## Header

- Source: upworthy
- Ledger snapshot: 20261115-b5929079f639
- Model: 6f58c709374c
- Feature hash: 0ee77c981273
- Command: `moot backtest --source upworthy --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr --contrasts one --seed 0`
- Seed: 0, bootstrap resamples: 500
- Variant (an ablation, not the main run): {"contrasts": "one"}
- Gate sizes from the power simulation at the release gate (power 0.90): n_200 = 175 (skill 0.20), n_400 = 250 (skill 0.10)
- At power 0.80: n_200 = 125 (skill 0.20), n_400 = 200 (skill 0.10) (research screen)
- At power 0.90: n_200 = 175 (skill 0.20), n_400 = 250 (skill 0.10) (release gate)
- Rungs: GBM, GBM+cal, P0, P1, P2, always_reference, always_variant, local_eb, local_eb+cal, text_lr, text_lr+cal; primary rung for decisions and plots: P2
- Origins scored: 7 from 2013-04-01T00:00:00+00:00 to 2015-04-01T00:00:00+00:00
- Origins with fewer than 20 visible rows (nothing fitted): 2013-01-01T00:00:00+00:00
- Ledger rows: 45810, admitted: 14151, scored: 13822, admitted but never scored (before the first fit): 329
- Tests: 22743 in the ledger, 14151 admitted, 13822 scored. Tests in the ledger are the distinct test ids of every row of the source whatever its status. Tests admitted are the distinct test ids with at least one admitted contrast. Tests scored are the admitted tests with at least one contrast scored by the primary rung. The difference between admitted and scored is the contrasts of the first quarters, before the first origin with enough visible rows to fit (they are history only), plus any test whose contrasts all fall there.
- P2 admission guard: 2.0
- P2 selection rule: forward
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

### Rows, tests, gates and abstention (the gates count tests, so decidability is read by tests)

| cell | rung | kind | n | n_tests | n_nonabstained | abstention_rate | gate_base_rate | decidable_by_tests | decidable_research_by_tests |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | challenger | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | GBM+cal | challenger | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P0 | ladder | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P1 | ladder | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | P2 | ladder | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | always_reference | baseline | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | always_variant | baseline | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb | challenger | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb+cal | challenger | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr | challenger | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr+cal | challenger | 13822 | 13822 | 10496 | 0.2406 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | GBM | challenger | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | GBM+cal | challenger | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P0 | ladder | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P1 | ladder | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | P2 | ladder | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | always_reference | baseline | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | always_variant | baseline | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | local_eb | challenger | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | local_eb+cal | challenger | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | text_lr | challenger | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| both | text_lr+cal | challenger | 407 | 407 | 286 | 0.2973 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM | challenger | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM+cal | challenger | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P0 | ladder | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P1 | ladder | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | P2 | ladder | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | always_reference | baseline | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | always_variant | baseline | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb | challenger | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb+cal | challenger | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr | challenger | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr+cal | challenger | 8259 | 8259 | 6262 | 0.2418 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | GBM | challenger | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | GBM+cal | challenger | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P0 | ladder | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P1 | ladder | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | P2 | ladder | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | always_reference | baseline | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | always_variant | baseline | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb | challenger | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb+cal | challenger | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr | challenger | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr+cal | challenger | 5156 | 5156 | 3948 | 0.2343 | 0.0900 | decidable at skill 0.20 and 0.10 | decidable at skill 0.20 and 0.10 |

### Log score and CRPS, all predicted rows (higher log score is better, lower CRPS is better)

| cell | rung | logscore | logscore_lo | logscore_hi | crps | crps_lo | crps_hi |
|---|---|---|---|---|---|---|---|
| ALL | GBM | -0.8906 | -0.9026 | -0.8795 | 0.3121 | 0.3086 | 0.3159 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | -0.8076 | -0.8189 | -0.7963 | 0.3126 | 0.3091 | 0.3165 |
| ALL | P1 | -0.8049 | -0.8182 | -0.7921 | 0.3021 | 0.2981 | 0.3063 |
| ALL | P2 | -0.8054 | -0.8189 | -0.7926 | 0.3020 | 0.2980 | 0.3062 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | -0.9116 | -0.9392 | -0.8888 | 0.3042 | 0.3002 | 0.3086 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | -1.0061 | -1.1117 | -0.9105 | 0.3456 | 0.3170 | 0.3758 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | -0.9157 | -0.9913 | -0.8491 | 0.3630 | 0.3361 | 0.3926 |
| both | P1 | -0.9038 | -0.9848 | -0.8314 | 0.3397 | 0.3099 | 0.3715 |
| both | P2 | -0.9035 | -0.9845 | -0.8312 | 0.3397 | 0.3099 | 0.3715 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | -1.0491 | -1.2563 | -0.8813 | 0.3401 | 0.3087 | 0.3737 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | -0.8895 | -0.9066 | -0.8739 | 0.3127 | 0.3076 | 0.3178 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | -0.8113 | -0.8260 | -0.7967 | 0.3168 | 0.3117 | 0.3217 |
| headline_only | P1 | -0.7979 | -0.8148 | -0.7813 | 0.3028 | 0.2971 | 0.3083 |
| headline_only | P2 | -0.7986 | -0.8159 | -0.7817 | 0.3025 | 0.2969 | 0.3082 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | -0.8902 | -0.9287 | -0.8571 | 0.3039 | 0.2981 | 0.3096 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | -0.8832 | -0.8996 | -0.8661 | 0.3085 | 0.3030 | 0.3139 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | -0.7932 | -0.8143 | -0.7737 | 0.3020 | 0.2960 | 0.3081 |
| image_only | P1 | -0.8082 | -0.8324 | -0.7863 | 0.2980 | 0.2916 | 0.3048 |
| image_only | P2 | -0.8087 | -0.8328 | -0.7870 | 0.2980 | 0.2916 | 0.3048 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | -0.9352 | -0.9729 | -0.8979 | 0.3019 | 0.2954 | 0.3083 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a |

### Brier score of p_sig against the significant-positive event, with skill against the base rate

| cell | rung | brier | brier_lo | brier_hi | brier_base | brier_skill | brier_skill_lo | brier_skill_hi | brier_floor |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.0926 | 0.0899 | 0.0952 | 0.0878 | -0.0540 | -0.0615 | -0.0470 | 0.0576 |
| ALL | GBM+cal | 0.0881 | 0.0850 | 0.0911 | 0.0878 | -0.0025 | -0.0057 | 0.0003 | 0.0576 |
| ALL | P0 | 0.0878 | 0.0847 | 0.0911 | 0.0878 | 0.0000 | 0.0000 | 0.0000 | 0.0576 |
| ALL | P1 | 0.0875 | 0.0843 | 0.0909 | 0.0878 | 0.0035 | 0.0016 | 0.0053 | 0.0576 |
| ALL | P2 | 0.0875 | 0.0842 | 0.0908 | 0.0878 | 0.0044 | 0.0022 | 0.0066 | 0.0576 |
| ALL | always_reference | n/a | n/a | n/a | 0.0878 | n/a | n/a | n/a | 0.0576 |
| ALL | always_variant | n/a | n/a | n/a | 0.0878 | n/a | n/a | n/a | 0.0576 |
| ALL | local_eb | 0.0882 | 0.0849 | 0.0914 | 0.0878 | -0.0039 | -0.0078 | 0.0005 | 0.0576 |
| ALL | local_eb+cal | 0.0878 | 0.0847 | 0.0910 | 0.0878 | 0.0002 | -0.0015 | 0.0020 | 0.0576 |
| ALL | text_lr | 0.0880 | 0.0849 | 0.0913 | 0.0878 | -0.0019 | -0.0075 | 0.0030 | 0.0576 |
| ALL | text_lr+cal | 0.0875 | 0.0844 | 0.0906 | 0.0878 | 0.0042 | 0.0014 | 0.0066 | 0.0576 |
| both | GBM | 0.0857 | 0.0722 | 0.1024 | 0.0803 | -0.0673 | -0.1197 | -0.0254 | 0.0561 |
| both | GBM+cal | 0.0797 | 0.0646 | 0.0986 | 0.0803 | 0.0072 | -0.0116 | 0.0268 | 0.0561 |
| both | P0 | 0.0803 | 0.0653 | 0.0995 | 0.0803 | 0.0000 | 0.0000 | 0.0000 | 0.0561 |
| both | P1 | 0.0806 | 0.0658 | 0.0994 | 0.0803 | -0.0046 | -0.0104 | 0.0000 | 0.0561 |
| both | P2 | 0.0806 | 0.0657 | 0.0993 | 0.0803 | -0.0039 | -0.0095 | 0.0006 | 0.0561 |
| both | always_reference | n/a | n/a | n/a | 0.0803 | n/a | n/a | n/a | 0.0561 |
| both | always_variant | n/a | n/a | n/a | 0.0803 | n/a | n/a | n/a | 0.0561 |
| both | local_eb | 0.0801 | 0.0643 | 0.1004 | 0.0803 | 0.0018 | -0.0172 | 0.0242 | 0.0561 |
| both | local_eb+cal | 0.0803 | 0.0651 | 0.0994 | 0.0803 | 0.0002 | -0.0094 | 0.0104 | 0.0561 |
| both | text_lr | 0.0795 | 0.0637 | 0.0984 | 0.0803 | 0.0091 | -0.0250 | 0.0433 | 0.0561 |
| both | text_lr+cal | 0.0792 | 0.0637 | 0.0979 | 0.0803 | 0.0137 | -0.0050 | 0.0315 | 0.0561 |
| headline_only | GBM | 0.0958 | 0.0924 | 0.0995 | 0.0921 | -0.0410 | -0.0497 | -0.0340 | 0.0580 |
| headline_only | GBM+cal | 0.0917 | 0.0877 | 0.0959 | 0.0921 | 0.0041 | 0.0012 | 0.0067 | 0.0580 |
| headline_only | P0 | 0.0921 | 0.0880 | 0.0962 | 0.0921 | 0.0000 | 0.0000 | 0.0000 | 0.0580 |
| headline_only | P1 | 0.0913 | 0.0871 | 0.0956 | 0.0921 | 0.0087 | 0.0062 | 0.0112 | 0.0580 |
| headline_only | P2 | 0.0912 | 0.0869 | 0.0955 | 0.0921 | 0.0098 | 0.0067 | 0.0132 | 0.0580 |
| headline_only | always_reference | n/a | n/a | n/a | 0.0921 | n/a | n/a | n/a | 0.0580 |
| headline_only | always_variant | n/a | n/a | n/a | 0.0921 | n/a | n/a | n/a | 0.0580 |
| headline_only | local_eb | 0.0914 | 0.0871 | 0.0959 | 0.0921 | 0.0071 | 0.0016 | 0.0132 | 0.0580 |
| headline_only | local_eb+cal | 0.0916 | 0.0876 | 0.0958 | 0.0921 | 0.0048 | 0.0031 | 0.0066 | 0.0580 |
| headline_only | text_lr | 0.0921 | 0.0881 | 0.0961 | 0.0921 | 0.0001 | -0.0083 | 0.0084 | 0.0580 |
| headline_only | text_lr+cal | 0.0911 | 0.0871 | 0.0952 | 0.0921 | 0.0104 | 0.0065 | 0.0142 | 0.0580 |
| image_only | GBM | 0.0879 | 0.0835 | 0.0920 | 0.0817 | -0.0764 | -0.0951 | -0.0619 | 0.0571 |
| image_only | GBM+cal | 0.0829 | 0.0779 | 0.0875 | 0.0817 | -0.0152 | -0.0231 | -0.0083 | 0.0571 |
| image_only | P0 | 0.0817 | 0.0763 | 0.0866 | 0.0817 | 0.0000 | 0.0000 | 0.0000 | 0.0571 |
| image_only | P1 | 0.0821 | 0.0766 | 0.0872 | 0.0817 | -0.0053 | -0.0081 | -0.0024 | 0.0571 |
| image_only | P2 | 0.0820 | 0.0766 | 0.0872 | 0.0817 | -0.0047 | -0.0075 | -0.0018 | 0.0571 |
| image_only | always_reference | n/a | n/a | n/a | 0.0817 | n/a | n/a | n/a | 0.0571 |
| image_only | always_variant | n/a | n/a | n/a | 0.0817 | n/a | n/a | n/a | 0.0571 |
| image_only | local_eb | 0.0836 | 0.0784 | 0.0884 | 0.0817 | -0.0242 | -0.0310 | -0.0169 | 0.0571 |
| image_only | local_eb+cal | 0.0823 | 0.0772 | 0.0870 | 0.0817 | -0.0081 | -0.0130 | -0.0042 | 0.0571 |
| image_only | text_lr | 0.0822 | 0.0769 | 0.0871 | 0.0817 | -0.0063 | -0.0102 | -0.0020 | 0.0571 |
| image_only | text_lr+cal | 0.0823 | 0.0772 | 0.0870 | 0.0817 | -0.0077 | -0.0121 | -0.0034 | 0.0571 |

### Calibration of p_sig against the perfect-calibration null, clustered by test

| cell | rung | ece | ece_percentile | ece_percentile_independent | ece_equal_mass | ece_equal_mass_percentile | design_effect | icc |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.0752 | 100.0000 | 100.0000 | 0.0752 | 100.0000 | 0.6560 | 0.0000 |
| ALL | GBM+cal | 0.0324 | 100.0000 | 100.0000 | 0.0324 | 100.0000 | 0.7916 | 0.0000 |
| ALL | P0 | 0.0270 | 100.0000 | 100.0000 | 0.0271 | 100.0000 | 0.8287 | 0.0000 |
| ALL | P1 | 0.0180 | 100.0000 | 100.0000 | 0.0186 | 100.0000 | 0.9249 | 0.0000 |
| ALL | P2 | 0.0185 | 100.0000 | 100.0000 | 0.0175 | 100.0000 | 0.9394 | 0.0000 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.0275 | 100.0000 | 100.0000 | 0.0284 | 100.0000 | 0.9623 | 0.0000 |
| ALL | local_eb+cal | 0.0275 | 100.0000 | 100.0000 | 0.0275 | 100.0000 | 0.8152 | 0.0000 |
| ALL | text_lr | 0.0293 | 100.0000 | 100.0000 | 0.0313 | 100.0000 | 0.8873 | 0.0000 |
| ALL | text_lr+cal | 0.0287 | 100.0000 | 100.0000 | 0.0287 | 100.0000 | 0.8088 | 0.0000 |
| both | GBM | 0.0908 | 100.0000 | 100.0000 | 0.0908 | 99.8000 | 0.5948 | 0.0000 |
| both | GBM+cal | 0.0519 | 99.5000 | 99.5000 | 0.0647 | 98.0000 | 0.6986 | 0.0000 |
| both | P0 | 0.0492 | 99.6000 | 99.6000 | 0.0492 | 93.6000 | 0.6902 | 0.0000 |
| both | P1 | 0.0529 | 100.0000 | 100.0000 | 0.0529 | 96.6000 | 0.6789 | 0.0000 |
| both | P2 | 0.0526 | 100.0000 | 100.0000 | 0.0526 | 96.0000 | 0.6798 | 0.0000 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.0314 | 86.0000 | 86.0000 | 0.0516 | 92.8000 | 0.7943 | 0.0000 |
| both | local_eb+cal | 0.0477 | 99.2000 | 99.2000 | 0.0506 | 89.0000 | 0.6994 | 0.0000 |
| both | text_lr | 0.0339 | 85.1000 | 85.1000 | 0.0460 | 78.4000 | 0.7811 | 0.0000 |
| both | text_lr+cal | 0.0447 | 97.8000 | 97.8000 | 0.0476 | 74.4000 | 0.7061 | 0.0000 |
| headline_only | GBM | 0.0712 | 100.0000 | 100.0000 | 0.0712 | 100.0000 | 0.6764 | 0.0000 |
| headline_only | GBM+cal | 0.0282 | 100.0000 | 100.0000 | 0.0282 | 100.0000 | 0.8196 | 0.0000 |
| headline_only | P0 | 0.0327 | 100.0000 | 100.0000 | 0.0327 | 100.0000 | 0.7982 | 0.0000 |
| headline_only | P1 | 0.0155 | 100.0000 | 100.0000 | 0.0174 | 100.0000 | 0.8925 | 0.0000 |
| headline_only | P2 | 0.0143 | 100.0000 | 100.0000 | 0.0153 | 100.0000 | 0.9205 | 0.0000 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.0185 | 100.0000 | 100.0000 | 0.0218 | 100.0000 | 1.0236 | 0.0000 |
| headline_only | local_eb+cal | 0.0249 | 100.0000 | 100.0000 | 0.0251 | 100.0000 | 0.8367 | 0.0000 |
| headline_only | text_lr | 0.0313 | 100.0000 | 100.0000 | 0.0344 | 100.0000 | 0.8687 | 0.0000 |
| headline_only | text_lr+cal | 0.0287 | 100.0000 | 100.0000 | 0.0287 | 100.0000 | 0.8166 | 0.0000 |
| image_only | GBM | 0.0808 | 100.0000 | 100.0000 | 0.0805 | 100.0000 | 0.6278 | 0.0000 |
| image_only | GBM+cal | 0.0379 | 100.0000 | 100.0000 | 0.0380 | 100.0000 | 0.7538 | 0.0000 |
| image_only | P0 | 0.0164 | 100.0000 | 100.0000 | 0.0296 | 100.0000 | 0.9053 | 0.0000 |
| image_only | P1 | 0.0242 | 100.0000 | 100.0000 | 0.0275 | 100.0000 | 1.0196 | 0.0000 |
| image_only | P2 | 0.0229 | 100.0000 | 100.0000 | 0.0219 | 100.0000 | 1.0060 | 0.0000 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.0416 | 100.0000 | 100.0000 | 0.0423 | 100.0000 | 0.8837 | 0.0000 |
| image_only | local_eb+cal | 0.0300 | 100.0000 | 100.0000 | 0.0314 | 100.0000 | 0.7890 | 0.0000 |
| image_only | text_lr | 0.0273 | 100.0000 | 100.0000 | 0.0296 | 100.0000 | 0.9328 | 0.0000 |
| image_only | text_lr+cal | 0.0276 | 100.0000 | 100.0000 | 0.0276 | 100.0000 | 0.8042 | 0.0000 |

### Bonferroni-adjusted bounds for the family of intervals of this table (descriptive intervals are the unadjusted ones above)

| cell | rung | family_size | brier_skill | adjusted_lo | adjusted_hi | logscore | logscore_adjusted_lo | logscore_adjusted_hi |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 52 | -0.0540 | -0.0682 | -0.0398 | -0.8906 | -0.9125 | -0.8687 |
| ALL | GBM+cal | 52 | -0.0025 | -0.0081 | 0.0031 | n/a | n/a | n/a |
| ALL | P0 | 52 | 0.0000 | n/a | n/a | -0.8076 | -0.8294 | -0.7859 |
| ALL | P1 | 52 | 0.0035 | -0.0001 | 0.0070 | -0.8049 | -0.8299 | -0.7798 |
| ALL | P2 | 52 | 0.0044 | 0.0003 | 0.0086 | -0.8054 | -0.8308 | -0.7801 |
| ALL | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 52 | -0.0039 | -0.0118 | 0.0040 | -0.9116 | -0.9599 | -0.8633 |
| ALL | local_eb+cal | 52 | 0.0002 | -0.0029 | 0.0034 | n/a | n/a | n/a |
| ALL | text_lr | 52 | -0.0019 | -0.0120 | 0.0083 | n/a | n/a | n/a |
| ALL | text_lr+cal | 52 | 0.0042 | -0.0010 | 0.0094 | n/a | n/a | n/a |
| both | GBM | 52 | -0.0673 | -0.1524 | 0.0177 | -1.0061 | -1.2068 | -0.8054 |
| both | GBM+cal | 52 | 0.0072 | -0.0303 | 0.0447 | n/a | n/a | n/a |
| both | P0 | 52 | 0.0000 | n/a | n/a | -0.9157 | -1.0478 | -0.7836 |
| both | P1 | 52 | -0.0046 | -0.0145 | 0.0053 | -0.9038 | -1.0495 | -0.7580 |
| both | P2 | 52 | -0.0039 | -0.0135 | 0.0058 | -0.9035 | -1.0493 | -0.7577 |
| both | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 52 | 0.0018 | -0.0371 | 0.0408 | -1.0491 | -1.4160 | -0.6822 |
| both | local_eb+cal | 52 | 0.0002 | -0.0194 | 0.0198 | n/a | n/a | n/a |
| both | text_lr | 52 | 0.0091 | -0.0578 | 0.0760 | n/a | n/a | n/a |
| both | text_lr+cal | 52 | 0.0137 | -0.0212 | 0.0485 | n/a | n/a | n/a |
| headline_only | GBM | 52 | -0.0410 | -0.0554 | -0.0266 | -0.8895 | -0.9197 | -0.8592 |
| headline_only | GBM+cal | 52 | 0.0041 | -0.0011 | 0.0093 | n/a | n/a | n/a |
| headline_only | P0 | 52 | 0.0000 | n/a | n/a | -0.8113 | -0.8389 | -0.7837 |
| headline_only | P1 | 52 | 0.0087 | 0.0040 | 0.0134 | -0.7979 | -0.8292 | -0.7667 |
| headline_only | P2 | 52 | 0.0098 | 0.0040 | 0.0156 | -0.7986 | -0.8308 | -0.7664 |
| headline_only | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 52 | 0.0071 | -0.0042 | 0.0184 | -0.8902 | -0.9561 | -0.8242 |
| headline_only | local_eb+cal | 52 | 0.0048 | 0.0015 | 0.0081 | n/a | n/a | n/a |
| headline_only | text_lr | 52 | 0.0001 | -0.0153 | 0.0155 | n/a | n/a | n/a |
| headline_only | text_lr+cal | 52 | 0.0104 | 0.0031 | 0.0176 | n/a | n/a | n/a |
| image_only | GBM | 52 | -0.0764 | -0.1092 | -0.0436 | -0.8832 | -0.9144 | -0.8520 |
| image_only | GBM+cal | 52 | -0.0152 | -0.0293 | -0.0011 | n/a | n/a | n/a |
| image_only | P0 | 52 | 0.0000 | n/a | n/a | -0.7932 | -0.8313 | -0.7551 |
| image_only | P1 | 52 | -0.0053 | -0.0105 | -0.0001 | -0.8082 | -0.8521 | -0.7643 |
| image_only | P2 | 52 | -0.0047 | -0.0098 | 0.0005 | -0.8087 | -0.8524 | -0.7650 |
| image_only | always_reference | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | 52 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 52 | -0.0242 | -0.0375 | -0.0108 | -0.9352 | -1.0092 | -0.8612 |
| image_only | local_eb+cal | 52 | -0.0081 | -0.0164 | 0.0002 | n/a | n/a | n/a |
| image_only | text_lr | 52 | -0.0063 | -0.0142 | 0.0015 | n/a | n/a | n/a |
| image_only | text_lr+cal | 52 | -0.0077 | -0.0161 | 0.0007 | n/a | n/a | n/a |

### Discrimination apart from skill: AUC of p_sig for the event and of the direction probability for y > 0, and the Murphy resolution term (equal-mass forecast bins: how far the observed frequency of each bin lies from the event rate; zero for a forecast that does not separate outcomes, however spread it is)

| cell | rung | auc_event | auc_event_lo | auc_event_hi | resolution_event | resolution_event_lo | resolution_event_hi | auc_direction | auc_direction_lo | auc_direction_hi | resolution_direction | resolution_direction_lo | resolution_direction_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.5565 | 0.5445 | 0.5697 | 0.0003 | 0.0003 | 0.0006 | 0.5218 | 0.5141 | 0.5296 | 0.0008 | 0.0006 | 0.0014 |
| ALL | GBM+cal | 0.5524 | 0.5405 | 0.5655 | 0.0003 | 0.0002 | 0.0005 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.5313 | 0.5164 | 0.5464 | 0.0003 | 0.0002 | 0.0005 | 0.5015 | 0.4935 | 0.5090 | 0.0010 | 0.0008 | 0.0017 |
| ALL | P1 | 0.5327 | 0.5179 | 0.5477 | 0.0002 | 0.0001 | 0.0004 | 0.5018 | 0.4946 | 0.5097 | 0.0012 | 0.0009 | 0.0019 |
| ALL | P2 | 0.5356 | 0.5214 | 0.5504 | 0.0002 | 0.0001 | 0.0004 | 0.5104 | 0.5034 | 0.5186 | 0.0008 | 0.0006 | 0.0014 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.5290 | 0.5156 | 0.5439 | 0.0002 | 0.0001 | 0.0003 | 0.5240 | 0.5154 | 0.5321 | 0.0005 | 0.0004 | 0.0011 |
| ALL | local_eb+cal | 0.5419 | 0.5284 | 0.5566 | 0.0002 | 0.0002 | 0.0004 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.5590 | 0.5455 | 0.5726 | 0.0005 | 0.0004 | 0.0008 | 0.5394 | 0.5308 | 0.5476 | 0.0013 | 0.0010 | 0.0020 |
| ALL | text_lr+cal | 0.5640 | 0.5513 | 0.5775 | 0.0005 | 0.0003 | 0.0007 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | 0.6026 | 0.5204 | 0.6942 | 0.0031 | 0.0020 | 0.0087 | 0.5570 | 0.5116 | 0.6053 | 0.0067 | 0.0057 | 0.0200 |
| both | GBM+cal | 0.6030 | 0.5175 | 0.6946 | 0.0042 | 0.0027 | 0.0105 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | 0.5966 | 0.5194 | 0.6761 | 0.0009 | 0.0005 | 0.0042 | 0.5400 | 0.4976 | 0.5849 | 0.0035 | 0.0020 | 0.0138 |
| both | P1 | 0.5944 | 0.5131 | 0.6767 | 0.0009 | 0.0006 | 0.0042 | 0.5241 | 0.4814 | 0.5717 | 0.0035 | 0.0024 | 0.0143 |
| both | P2 | 0.5966 | 0.5194 | 0.6761 | 0.0009 | 0.0005 | 0.0042 | 0.5255 | 0.4835 | 0.5727 | 0.0035 | 0.0020 | 0.0138 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5382 | 0.4492 | 0.6249 | 0.0023 | 0.0017 | 0.0065 | 0.4949 | 0.4486 | 0.5426 | 0.0087 | 0.0065 | 0.0212 |
| both | local_eb+cal | 0.5879 | 0.4994 | 0.6706 | 0.0013 | 0.0012 | 0.0050 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | 0.6223 | 0.5415 | 0.7036 | 0.0020 | 0.0017 | 0.0068 | 0.5479 | 0.5011 | 0.5925 | 0.0047 | 0.0040 | 0.0168 |
| both | text_lr+cal | 0.6243 | 0.5403 | 0.7102 | 0.0030 | 0.0018 | 0.0088 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.5702 | 0.5540 | 0.5865 | 0.0007 | 0.0005 | 0.0011 | 0.5332 | 0.5230 | 0.5451 | 0.0012 | 0.0009 | 0.0021 |
| headline_only | GBM+cal | 0.5604 | 0.5434 | 0.5758 | 0.0005 | 0.0003 | 0.0008 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.5522 | 0.5367 | 0.5676 | 0.0004 | 0.0002 | 0.0007 | 0.5025 | 0.4922 | 0.5121 | 0.0006 | 0.0004 | 0.0013 |
| headline_only | P1 | 0.5506 | 0.5351 | 0.5665 | 0.0004 | 0.0002 | 0.0007 | 0.5022 | 0.4924 | 0.5118 | 0.0004 | 0.0002 | 0.0009 |
| headline_only | P2 | 0.5565 | 0.5412 | 0.5719 | 0.0005 | 0.0004 | 0.0009 | 0.5208 | 0.5097 | 0.5316 | 0.0005 | 0.0004 | 0.0013 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5539 | 0.5365 | 0.5710 | 0.0004 | 0.0003 | 0.0008 | 0.5319 | 0.5206 | 0.5407 | 0.0008 | 0.0006 | 0.0016 |
| headline_only | local_eb+cal | 0.5558 | 0.5390 | 0.5731 | 0.0004 | 0.0003 | 0.0008 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5856 | 0.5682 | 0.6041 | 0.0010 | 0.0007 | 0.0014 | 0.5605 | 0.5496 | 0.5715 | 0.0028 | 0.0021 | 0.0041 |
| headline_only | text_lr+cal | 0.5897 | 0.5731 | 0.6074 | 0.0010 | 0.0008 | 0.0015 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.5344 | 0.5128 | 0.5578 | 0.0005 | 0.0003 | 0.0010 | 0.4912 | 0.4786 | 0.5047 | 0.0007 | 0.0005 | 0.0018 |
| image_only | GBM+cal | 0.5329 | 0.5114 | 0.5566 | 0.0003 | 0.0002 | 0.0008 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.4842 | 0.4614 | 0.5059 | 0.0004 | 0.0002 | 0.0008 | 0.4832 | 0.4699 | 0.4972 | 0.0023 | 0.0015 | 0.0038 |
| image_only | P1 | 0.4777 | 0.4545 | 0.4996 | 0.0005 | 0.0003 | 0.0009 | 0.4891 | 0.4769 | 0.5033 | 0.0023 | 0.0015 | 0.0038 |
| image_only | P2 | 0.4807 | 0.4571 | 0.5030 | 0.0004 | 0.0002 | 0.0007 | 0.4890 | 0.4761 | 0.5031 | 0.0014 | 0.0008 | 0.0027 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.4925 | 0.4691 | 0.5170 | 0.0002 | 0.0001 | 0.0006 | 0.5101 | 0.4982 | 0.5236 | 0.0011 | 0.0008 | 0.0024 |
| image_only | local_eb+cal | 0.5095 | 0.4867 | 0.5335 | 0.0002 | 0.0002 | 0.0006 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.4924 | 0.4699 | 0.5157 | 0.0001 | 0.0001 | 0.0005 | 0.4960 | 0.4830 | 0.5098 | 0.0004 | 0.0003 | 0.0014 |
| image_only | text_lr+cal | 0.5045 | 0.4826 | 0.5275 | 0.0002 | 0.0001 | 0.0006 | n/a | n/a | n/a | n/a | n/a | n/a |

### Discrimination within strata (an origin and a cell scored on its own, averaged with weights by stratum size): the pooled AUC above also credits a rung with the movement of the base rate between cells and origins, which P0 has by construction

| cell | rung | auc_event_within | auc_event_within_lo | auc_event_within_hi | resolution_event_within | resolution_event_within_lo | resolution_event_within_hi | auc_direction_within | auc_direction_within_lo | auc_direction_within_hi | resolution_direction_within |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.5491 | 0.5359 | 0.5625 | 0.0012 | 0.0017 | 0.0025 | 0.5263 | 0.5186 | 0.5334 | 0.0035 |
| ALL | GBM+cal | 0.5491 | 0.5359 | 0.5625 | 0.0012 | 0.0017 | 0.0025 | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| ALL | P1 | 0.4959 | 0.4913 | 0.5004 | 0.0000 | 0.0000 | 0.0001 | 0.5012 | 0.4982 | 0.5039 | 0.0001 |
| ALL | P2 | 0.5228 | 0.5130 | 0.5317 | 0.0004 | 0.0006 | 0.0010 | 0.5201 | 0.5145 | 0.5250 | 0.0019 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.5255 | 0.5124 | 0.5390 | 0.0013 | 0.0018 | 0.0025 | 0.5203 | 0.5118 | 0.5283 | 0.0035 |
| ALL | local_eb+cal | 0.5057 | 0.4902 | 0.5202 | 0.0013 | 0.0018 | 0.0025 | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.5553 | 0.5412 | 0.5691 | 0.0016 | 0.0021 | 0.0030 | 0.5385 | 0.5300 | 0.5465 | 0.0049 |
| ALL | text_lr+cal | 0.5553 | 0.5412 | 0.5691 | 0.0016 | 0.0021 | 0.0030 | n/a | n/a | n/a | n/a |
| both | GBM | 0.5144 | 0.4349 | 0.6124 | 0.0111 | 0.0128 | 0.0297 | 0.5322 | 0.4859 | 0.5840 | 0.0310 |
| both | GBM+cal | 0.5144 | 0.4349 | 0.6124 | 0.0111 | 0.0128 | 0.0297 | n/a | n/a | n/a | n/a |
| both | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| both | P1 | 0.4839 | 0.4283 | 0.5426 | 0.0000 | 0.0000 | 0.0010 | 0.4887 | 0.4676 | 0.5083 | 0.0012 |
| both | P2 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.4903 | 0.4816 | 0.4993 | 0.0072 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.4290 | 0.3474 | 0.5166 | 0.0111 | 0.0095 | 0.0262 | 0.4783 | 0.4349 | 0.5237 | 0.0340 |
| both | local_eb+cal | 0.5274 | 0.4387 | 0.6143 | 0.0104 | 0.0092 | 0.0258 | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5774 | 0.4850 | 0.6709 | 0.0101 | 0.0120 | 0.0278 | 0.5407 | 0.4944 | 0.5873 | 0.0358 |
| both | text_lr+cal | 0.5774 | 0.4850 | 0.6709 | 0.0101 | 0.0120 | 0.0278 | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.5654 | 0.5476 | 0.5817 | 0.0012 | 0.0014 | 0.0023 | 0.5369 | 0.5266 | 0.5482 | 0.0030 |
| headline_only | GBM+cal | 0.5654 | 0.5476 | 0.5817 | 0.0012 | 0.0014 | 0.0023 | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| headline_only | P1 | 0.4976 | 0.4922 | 0.5029 | 0.0000 | 0.0000 | 0.0001 | 0.5000 | 0.4969 | 0.5033 | 0.0001 |
| headline_only | P2 | 0.5337 | 0.5209 | 0.5467 | 0.0006 | 0.0007 | 0.0013 | 0.5325 | 0.5251 | 0.5404 | 0.0026 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5314 | 0.5132 | 0.5501 | 0.0009 | 0.0012 | 0.0021 | 0.5322 | 0.5208 | 0.5417 | 0.0019 |
| headline_only | local_eb+cal | 0.5045 | 0.4862 | 0.5231 | 0.0009 | 0.0012 | 0.0021 | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5772 | 0.5597 | 0.5962 | 0.0014 | 0.0016 | 0.0026 | 0.5608 | 0.5499 | 0.5716 | 0.0048 |
| headline_only | text_lr+cal | 0.5772 | 0.5597 | 0.5962 | 0.0014 | 0.0016 | 0.0026 | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.5255 | 0.5047 | 0.5442 | 0.0006 | 0.0008 | 0.0016 | 0.5088 | 0.4970 | 0.5191 | 0.0020 |
| image_only | GBM+cal | 0.5255 | 0.5047 | 0.5442 | 0.0006 | 0.0008 | 0.0016 | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| image_only | P1 | 0.4939 | 0.4860 | 0.5028 | 0.0001 | 0.0000 | 0.0003 | 0.5041 | 0.4993 | 0.5092 | 0.0001 |
| image_only | P2 | 0.5069 | 0.4967 | 0.5150 | 0.0002 | 0.0002 | 0.0006 | 0.5027 | 0.4973 | 0.5085 | 0.0004 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.5236 | 0.5017 | 0.5480 | 0.0011 | 0.0014 | 0.0025 | 0.5047 | 0.4915 | 0.5188 | 0.0037 |
| image_only | local_eb+cal | 0.5060 | 0.4829 | 0.5304 | 0.0011 | 0.0014 | 0.0025 | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.5187 | 0.4977 | 0.5417 | 0.0012 | 0.0015 | 0.0028 | 0.5024 | 0.4895 | 0.5162 | 0.0028 |
| image_only | text_lr+cal | 0.5187 | 0.4977 | 0.5417 | 0.0012 | 0.0015 | 0.0028 | n/a | n/a | n/a | n/a |

### Sensitivity of the event definition: the same forecasts scored against y > z s_star on the planned standard error (the headline uses the realized one)

| cell | rung | event_rate_planned | p_sig_mean | brier_planned | brier_base_planned | brier_skill_planned | brier_skill_planned_lo | brier_skill_planned_hi |
|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.0817 | 0.1714 | 0.0835 | 0.0769 | -0.0860 | -0.0956 | -0.0769 |
| ALL | GBM+cal | 0.0817 | 0.1286 | 0.0776 | 0.0769 | -0.0096 | -0.0135 | -0.0062 |
| ALL | P0 | 0.0817 | 0.1166 | 0.0769 | 0.0769 | 0.0000 | 0.0000 | 0.0000 |
| ALL | P1 | 0.0817 | 0.1072 | 0.0767 | 0.0769 | 0.0020 | 0.0003 | 0.0037 |
| ALL | P2 | 0.0817 | 0.1052 | 0.0767 | 0.0769 | 0.0025 | 0.0006 | 0.0044 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.0817 | 0.1044 | 0.0771 | 0.0769 | -0.0026 | -0.0067 | 0.0019 |
| ALL | local_eb+cal | 0.0817 | 0.1237 | 0.0772 | 0.0769 | -0.0040 | -0.0061 | -0.0021 |
| ALL | text_lr | 0.0817 | 0.1158 | 0.0776 | 0.0769 | -0.0089 | -0.0149 | -0.0036 |
| ALL | text_lr+cal | 0.0817 | 0.1249 | 0.0770 | 0.0769 | -0.0011 | -0.0044 | 0.0020 |
| both | GBM | 0.0737 | 0.1767 | 0.0787 | 0.0705 | -0.1166 | -0.1996 | -0.0568 |
| both | GBM+cal | 0.0737 | 0.1334 | 0.0713 | 0.0705 | -0.0116 | -0.0456 | 0.0202 |
| both | P0 | 0.0737 | 0.1199 | 0.0705 | 0.0705 | 0.0000 | 0.0000 | 0.0000 |
| both | P1 | 0.0737 | 0.1389 | 0.0724 | 0.0705 | -0.0264 | -0.0515 | -0.0082 |
| both | P2 | 0.0737 | 0.1386 | 0.0723 | 0.0705 | -0.0256 | -0.0508 | -0.0074 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.0737 | 0.1166 | 0.0705 | 0.0705 | 0.0001 | -0.0205 | 0.0184 |
| both | local_eb+cal | 0.0737 | 0.1337 | 0.0710 | 0.0705 | -0.0071 | -0.0311 | 0.0123 |
| both | text_lr | 0.0737 | 0.1199 | 0.0723 | 0.0705 | -0.0256 | -0.0683 | 0.0129 |
| both | text_lr+cal | 0.0737 | 0.1307 | 0.0711 | 0.0705 | -0.0078 | -0.0363 | 0.0173 |
| headline_only | GBM | 0.0835 | 0.1725 | 0.0847 | 0.0785 | -0.0791 | -0.0901 | -0.0685 |
| headline_only | GBM+cal | 0.0835 | 0.1296 | 0.0789 | 0.0785 | -0.0051 | -0.0085 | -0.0019 |
| headline_only | P0 | 0.0835 | 0.1258 | 0.0785 | 0.0785 | 0.0000 | 0.0000 | 0.0000 |
| headline_only | P1 | 0.0835 | 0.1168 | 0.0781 | 0.0785 | 0.0046 | 0.0030 | 0.0064 |
| headline_only | P2 | 0.0835 | 0.1128 | 0.0781 | 0.0785 | 0.0054 | 0.0030 | 0.0079 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.0835 | 0.1012 | 0.0777 | 0.0785 | 0.0106 | 0.0049 | 0.0162 |
| headline_only | local_eb+cal | 0.0835 | 0.1263 | 0.0786 | 0.0785 | -0.0016 | -0.0031 | 0.0000 |
| headline_only | text_lr | 0.0835 | 0.1262 | 0.0795 | 0.0785 | -0.0132 | -0.0219 | -0.0045 |
| headline_only | text_lr+cal | 0.0835 | 0.1300 | 0.0784 | 0.0785 | 0.0013 | -0.0030 | 0.0056 |
| image_only | GBM | 0.0793 | 0.1693 | 0.0819 | 0.0748 | -0.0955 | -0.1164 | -0.0789 |
| image_only | GBM+cal | 0.0793 | 0.1267 | 0.0761 | 0.0748 | -0.0171 | -0.0257 | -0.0099 |
| image_only | P0 | 0.0793 | 0.1017 | 0.0748 | 0.0748 | 0.0000 | 0.0000 | 0.0000 |
| image_only | P1 | 0.0793 | 0.0892 | 0.0748 | 0.0748 | -0.0004 | -0.0034 | 0.0030 |
| image_only | P2 | 0.0793 | 0.0905 | 0.0748 | 0.0748 | -0.0003 | -0.0031 | 0.0029 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.0793 | 0.1086 | 0.0767 | 0.0748 | -0.0250 | -0.0321 | -0.0180 |
| image_only | local_eb+cal | 0.0793 | 0.1189 | 0.0754 | 0.0748 | -0.0078 | -0.0128 | -0.0037 |
| image_only | text_lr | 0.0793 | 0.0989 | 0.0748 | 0.0748 | -0.0005 | -0.0046 | 0.0036 |
| image_only | text_lr+cal | 0.0793 | 0.1164 | 0.0751 | 0.0748 | -0.0046 | -0.0093 | -0.0001 |

### Paired log score difference from P1 on the same rows (nats per row, 90 percent by-test interval; negative means the rung scores below P1)

| cell | rung | logscore_vs_p1 | logscore_vs_p1_lo | logscore_vs_p1_hi | logscore_vs_p1_adjusted_lo | logscore_vs_p1_adjusted_hi | n_paired |
|---|---|---|---|---|---|---|---|
| ALL | GBM | -0.0857 | -0.0929 | -0.0790 | -0.0986 | -0.0727 | 13822 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | P0 | -0.0028 | -0.0049 | -0.0004 | -0.0071 | 0.0016 | 13822 |
| ALL | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 13822 |
| ALL | P2 | -0.0006 | -0.0011 | 0.0000 | -0.0015 | 0.0004 | 13822 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | local_eb | -0.1068 | -0.1242 | -0.0917 | -0.1383 | -0.0752 | 13822 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | GBM | -0.1023 | -0.1582 | -0.0561 | -0.2009 | -0.0037 | 407 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | P0 | -0.0119 | -0.0210 | -0.0014 | -0.0303 | 0.0064 | 407 |
| both | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 407 |
| both | P2 | 0.0003 | -0.0001 | 0.0007 | -0.0005 | 0.0011 | 407 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| both | local_eb | -0.1453 | -0.2962 | -0.0316 | -0.4031 | 0.1124 | 407 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | GBM | -0.0915 | -0.0997 | -0.0839 | -0.1065 | -0.0766 | 8259 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | P0 | -0.0134 | -0.0159 | -0.0108 | -0.0181 | -0.0087 | 8259 |
| headline_only | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 8259 |
| headline_only | P2 | -0.0007 | -0.0015 | 0.0002 | -0.0023 | 0.0009 | 8259 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | local_eb | -0.0922 | -0.1168 | -0.0690 | -0.1369 | -0.0476 | 8259 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | GBM | -0.0750 | -0.0854 | -0.0627 | -0.0961 | -0.0539 | 5156 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | P0 | 0.0150 | 0.0108 | 0.0193 | 0.0072 | 0.0228 | 5156 |
| image_only | P1 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 5156 |
| image_only | P2 | -0.0005 | -0.0008 | -0.0001 | -0.0011 | 0.0001 | 5156 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | local_eb | -0.1270 | -0.1496 | -0.1059 | -0.1694 | -0.0845 | 5156 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | 0 |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | 0 |

### The gate read with the group's own dependence: rows per test and within-test correlation of the group against those the nearest simulated gate assumed, and the gate sizes scaled to first order by the information per test (an approximation; docs/method.md call 205)

| cell | rung | event_rate | gate_cell_rows_per_test | gate_cell_icc | gate_assumed_rows_per_test | gate_assumed_icc | gate_cell_n_200 | gate_cell_n_400 | decidable_by_tests_cell |
|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | GBM+cal | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | P0 | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | P1 | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | P2 | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | always_reference | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | always_variant | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | local_eb+cal | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| ALL | text_lr+cal | 0.0962 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| both | GBM | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | GBM+cal | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | P0 | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | P1 | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | P2 | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | always_reference | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | always_variant | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | local_eb | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | local_eb+cal | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | text_lr | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| both | text_lr+cal | 0.0860 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | undecidable at this n |
| headline_only | GBM | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | GBM+cal | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | P0 | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | P1 | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | P2 | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | always_reference | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | always_variant | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | local_eb+cal | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| headline_only | text_lr+cal | 0.1013 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | GBM | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | GBM+cal | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | P0 | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | P1 | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | P2 | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | always_reference | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | always_variant | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | local_eb+cal | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |
| image_only | text_lr+cal | 0.0888 | 1.0000 | 0.0000 | 3.5000 | 0.1300 | 463 | 661 | decidable at skill 0.20 and 0.10 |

### Direction accuracy and coverage of the intervals for y

| cell | rung | direction_accuracy | direction_accuracy_lo | direction_accuracy_hi | n_decisive | direction_accuracy_decisive | direction_ceiling | coverage_80 | coverage_80_lo | coverage_80_hi | coverage_90 | coverage_90_lo | coverage_90_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | 0.5521 | 0.5456 | 0.5592 | 3586 | 0.6168 | 0.8195 | 0.9004 | 0.8960 | 0.9050 | 0.9475 | 0.9444 | 0.9504 |
| ALL | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8195 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | P0 | 0.5591 | 0.5522 | 0.5662 | 3586 | 0.6291 | 0.8195 | 0.8602 | 0.8553 | 0.8653 | 0.9381 | 0.9345 | 0.9415 |
| ALL | P1 | 0.5460 | 0.5393 | 0.5530 | 3586 | 0.6037 | 0.8195 | 0.8214 | 0.8157 | 0.8271 | 0.9002 | 0.8957 | 0.9046 |
| ALL | P2 | 0.5459 | 0.5394 | 0.5530 | 3586 | 0.6035 | 0.8195 | 0.8195 | 0.8136 | 0.8252 | 0.8982 | 0.8937 | 0.9027 |
| ALL | always_reference | 0.5591 | 0.5522 | 0.5662 | 3586 | 0.6291 | 0.8195 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | always_variant | 0.4409 | 0.4338 | 0.4478 | 3586 | 0.3709 | 0.8195 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | local_eb | 0.5406 | 0.5341 | 0.5479 | 3586 | 0.5767 | 0.8195 | 0.8116 | 0.8060 | 0.8171 | 0.8801 | 0.8753 | 0.8848 |
| ALL | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8195 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr | 0.5389 | 0.5315 | 0.5461 | 3586 | 0.5856 | 0.8195 | n/a | n/a | n/a | n/a | n/a | n/a |
| ALL | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8195 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | GBM | 0.5700 | 0.5307 | 0.6093 | 116 | 0.6983 | 0.8400 | 0.8943 | 0.8673 | 0.9189 | 0.9361 | 0.9165 | 0.9558 |
| both | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8400 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | P0 | 0.5725 | 0.5306 | 0.6143 | 116 | 0.6983 | 0.8400 | 0.8943 | 0.8673 | 0.9189 | 0.9484 | 0.9312 | 0.9656 |
| both | P1 | 0.5725 | 0.5306 | 0.6143 | 116 | 0.6983 | 0.8400 | 0.8600 | 0.8303 | 0.8870 | 0.9263 | 0.9042 | 0.9459 |
| both | P2 | 0.5725 | 0.5306 | 0.6143 | 116 | 0.6983 | 0.8400 | 0.8600 | 0.8303 | 0.8870 | 0.9263 | 0.9042 | 0.9459 |
| both | always_reference | 0.5725 | 0.5306 | 0.6143 | 116 | 0.6983 | 0.8400 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | always_variant | 0.4275 | 0.3857 | 0.4694 | 116 | 0.3017 | 0.8400 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | local_eb | 0.5553 | 0.5111 | 0.5946 | 116 | 0.6552 | 0.8400 | 0.8428 | 0.8084 | 0.8722 | 0.9017 | 0.8746 | 0.9238 |
| both | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8400 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr | 0.5577 | 0.5184 | 0.5971 | 116 | 0.6638 | 0.8400 | n/a | n/a | n/a | n/a | n/a | n/a |
| both | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8400 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | GBM | 0.5600 | 0.5511 | 0.5695 | 2248 | 0.6237 | 0.8301 | 0.9014 | 0.8960 | 0.9069 | 0.9477 | 0.9437 | 0.9519 |
| headline_only | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8301 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | P0 | 0.5623 | 0.5534 | 0.5711 | 2248 | 0.6277 | 0.8301 | 0.8755 | 0.8692 | 0.8815 | 0.9488 | 0.9452 | 0.9529 |
| headline_only | P1 | 0.5623 | 0.5534 | 0.5711 | 2248 | 0.6277 | 0.8301 | 0.8356 | 0.8286 | 0.8430 | 0.9134 | 0.9083 | 0.9184 |
| headline_only | P2 | 0.5622 | 0.5534 | 0.5711 | 2248 | 0.6272 | 0.8301 | 0.8311 | 0.8243 | 0.8385 | 0.9093 | 0.9039 | 0.9144 |
| headline_only | always_reference | 0.5623 | 0.5534 | 0.5711 | 2248 | 0.6277 | 0.8301 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | always_variant | 0.4377 | 0.4289 | 0.4466 | 2248 | 0.3723 | 0.8301 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | local_eb | 0.5486 | 0.5393 | 0.5571 | 2248 | 0.5939 | 0.8301 | 0.8094 | 0.8028 | 0.8166 | 0.8789 | 0.8727 | 0.8849 |
| headline_only | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8301 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr | 0.5545 | 0.5453 | 0.5642 | 2248 | 0.6019 | 0.8301 | n/a | n/a | n/a | n/a | n/a | n/a |
| headline_only | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8301 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | GBM | 0.5380 | 0.5268 | 0.5497 | 1222 | 0.5966 | 0.8008 | 0.8991 | 0.8924 | 0.9052 | 0.9482 | 0.9432 | 0.9525 |
| image_only | GBM+cal | n/a | n/a | n/a | 0 | n/a | 0.8008 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | P0 | 0.5529 | 0.5425 | 0.5640 | 1222 | 0.6252 | 0.8008 | 0.8330 | 0.8243 | 0.8414 | 0.9201 | 0.9141 | 0.9253 |
| image_only | P1 | 0.5178 | 0.5068 | 0.5304 | 1222 | 0.5507 | 0.8008 | 0.7958 | 0.7861 | 0.8047 | 0.8768 | 0.8695 | 0.8840 |
| image_only | P2 | 0.5178 | 0.5068 | 0.5304 | 1222 | 0.5507 | 0.8008 | 0.7977 | 0.7882 | 0.8064 | 0.8782 | 0.8710 | 0.8854 |
| image_only | always_reference | 0.5529 | 0.5425 | 0.5640 | 1222 | 0.6252 | 0.8008 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | always_variant | 0.4471 | 0.4360 | 0.4575 | 1222 | 0.3748 | 0.8008 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | local_eb | 0.5266 | 0.5157 | 0.5386 | 1222 | 0.5376 | 0.8008 | 0.8126 | 0.8031 | 0.8218 | 0.8803 | 0.8735 | 0.8873 |
| image_only | local_eb+cal | n/a | n/a | n/a | 0 | n/a | 0.8008 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr | 0.5124 | 0.5015 | 0.5248 | 1222 | 0.5483 | 0.8008 | n/a | n/a | n/a | n/a | n/a | n/a |
| image_only | text_lr+cal | n/a | n/a | n/a | 0 | n/a | 0.8008 | n/a | n/a | n/a | n/a | n/a | n/a |

### The same scores on non-abstained rows only

| cell | rung | logscore_nonabstained | logscore_nonabstained_lo | logscore_nonabstained_hi | crps_nonabstained | crps_nonabstained_lo | crps_nonabstained_hi | brier_nonabstained | brier_nonabstained_lo | brier_nonabstained_hi | direction_accuracy_nonabstained | direction_accuracy_nonabstained_lo | direction_accuracy_nonabstained_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | GBM | -0.8185 | -0.8309 | -0.8081 | 0.2875 | 0.2841 | 0.2911 | 0.0885 | 0.0852 | 0.0914 | 0.5547 | 0.5472 | 0.5632 |
| ALL | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0841 | 0.0804 | 0.0873 | n/a | n/a | n/a |
| ALL | P0 | -0.7332 | -0.7451 | -0.7211 | 0.2890 | 0.2855 | 0.2926 | 0.0840 | 0.0802 | 0.0873 | 0.5609 | 0.5531 | 0.5691 |
| ALL | P1 | -0.7204 | -0.7343 | -0.7065 | 0.2769 | 0.2728 | 0.2809 | 0.0835 | 0.0795 | 0.0870 | 0.5443 | 0.5367 | 0.5524 |
| ALL | P2 | -0.7213 | -0.7355 | -0.7071 | 0.2768 | 0.2727 | 0.2809 | 0.0835 | 0.0795 | 0.0869 | 0.5443 | 0.5367 | 0.5525 |
| ALL | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5609 | 0.5531 | 0.5691 |
| ALL | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4391 | 0.4309 | 0.4469 |
| ALL | local_eb | -0.7869 | -0.8119 | -0.7652 | 0.2790 | 0.2751 | 0.2832 | 0.0846 | 0.0806 | 0.0880 | 0.5397 | 0.5317 | 0.5472 |
| ALL | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0840 | 0.0801 | 0.0873 | n/a | n/a | n/a |
| ALL | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.0844 | 0.0806 | 0.0877 | 0.5372 | 0.5289 | 0.5455 |
| ALL | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0838 | 0.0799 | 0.0870 | n/a | n/a | n/a |
| both | GBM | -0.9420 | -1.0937 | -0.8172 | 0.3157 | 0.2832 | 0.3495 | 0.0760 | 0.0601 | 0.0933 | 0.5664 | 0.5209 | 0.6160 |
| both | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0702 | 0.0520 | 0.0899 | n/a | n/a | n/a |
| both | P0 | -0.8210 | -0.9067 | -0.7385 | 0.3295 | 0.2998 | 0.3614 | 0.0703 | 0.0529 | 0.0895 | 0.5944 | 0.5448 | 0.6461 |
| both | P1 | -0.8142 | -0.9103 | -0.7211 | 0.3082 | 0.2743 | 0.3432 | 0.0705 | 0.0535 | 0.0895 | 0.5944 | 0.5448 | 0.6461 |
| both | P2 | -0.8138 | -0.9098 | -0.7205 | 0.3082 | 0.2743 | 0.3431 | 0.0704 | 0.0534 | 0.0895 | 0.5944 | 0.5448 | 0.6461 |
| both | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5944 | 0.5448 | 0.6461 |
| both | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4056 | 0.3539 | 0.4552 |
| both | local_eb | -1.0054 | -1.2995 | -0.7731 | 0.3058 | 0.2719 | 0.3427 | 0.0695 | 0.0509 | 0.0899 | 0.5874 | 0.5387 | 0.6396 |
| both | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0696 | 0.0514 | 0.0890 | n/a | n/a | n/a |
| both | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.0700 | 0.0513 | 0.0899 | 0.5629 | 0.5177 | 0.6127 |
| both | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0693 | 0.0514 | 0.0888 | n/a | n/a | n/a |
| headline_only | GBM | -0.8104 | -0.8258 | -0.7961 | 0.2860 | 0.2809 | 0.2911 | 0.0919 | 0.0877 | 0.0960 | 0.5607 | 0.5502 | 0.5711 |
| headline_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0878 | 0.0831 | 0.0924 | n/a | n/a | n/a |
| headline_only | P0 | -0.7352 | -0.7502 | -0.7198 | 0.2912 | 0.2863 | 0.2961 | 0.0880 | 0.0833 | 0.0926 | 0.5616 | 0.5517 | 0.5716 |
| headline_only | P1 | -0.7182 | -0.7351 | -0.7012 | 0.2761 | 0.2706 | 0.2815 | 0.0875 | 0.0825 | 0.0923 | 0.5616 | 0.5517 | 0.5716 |
| headline_only | P2 | -0.7193 | -0.7367 | -0.7015 | 0.2759 | 0.2704 | 0.2815 | 0.0874 | 0.0824 | 0.0923 | 0.5616 | 0.5517 | 0.5718 |
| headline_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5616 | 0.5517 | 0.5716 |
| headline_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4384 | 0.4284 | 0.4483 |
| headline_only | local_eb | -0.7800 | -0.8137 | -0.7472 | 0.2770 | 0.2713 | 0.2825 | 0.0881 | 0.0829 | 0.0931 | 0.5487 | 0.5385 | 0.5589 |
| headline_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0877 | 0.0828 | 0.0924 | n/a | n/a | n/a |
| headline_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.0884 | 0.0839 | 0.0930 | 0.5522 | 0.5412 | 0.5631 |
| headline_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0874 | 0.0827 | 0.0920 | n/a | n/a | n/a |
| image_only | GBM | -0.8224 | -0.8414 | -0.8037 | 0.2879 | 0.2820 | 0.2941 | 0.0840 | 0.0794 | 0.0889 | 0.5443 | 0.5315 | 0.5577 |
| image_only | GBM+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0793 | 0.0741 | 0.0847 | n/a | n/a | n/a |
| image_only | P0 | -0.7237 | -0.7451 | -0.7031 | 0.2826 | 0.2762 | 0.2892 | 0.0785 | 0.0731 | 0.0844 | 0.5572 | 0.5449 | 0.5703 |
| image_only | P1 | -0.7170 | -0.7417 | -0.6936 | 0.2758 | 0.2690 | 0.2830 | 0.0783 | 0.0727 | 0.0842 | 0.5132 | 0.5005 | 0.5265 |
| image_only | P2 | -0.7177 | -0.7422 | -0.6944 | 0.2758 | 0.2690 | 0.2830 | 0.0782 | 0.0727 | 0.0842 | 0.5132 | 0.5005 | 0.5265 |
| image_only | always_reference | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.5572 | 0.5449 | 0.5703 |
| image_only | always_variant | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.4428 | 0.4297 | 0.4551 |
| image_only | local_eb | -0.7821 | -0.8146 | -0.7487 | 0.2804 | 0.2736 | 0.2870 | 0.0801 | 0.0745 | 0.0855 | 0.5220 | 0.5099 | 0.5355 |
| image_only | local_eb+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0792 | 0.0740 | 0.0847 | n/a | n/a | n/a |
| image_only | text_lr | n/a | n/a | n/a | n/a | n/a | n/a | 0.0791 | 0.0736 | 0.0849 | 0.5114 | 0.4988 | 0.5256 |
| image_only | text_lr+cal | n/a | n/a | n/a | n/a | n/a | n/a | 0.0791 | 0.0738 | 0.0847 | n/a | n/a | n/a |

### Other columns

| cell | rung | resolution_direction_within_lo | resolution_direction_within_hi | latent_rho | gate_cell_scale |
|---|---|---|---|---|---|
| ALL | GBM | 0.0051 | 0.0068 | 0.0000 | 2.6415 |
| ALL | GBM+cal | n/a | n/a | 0.0000 | 2.6415 |
| ALL | P0 | 0.0000 | 0.0000 | 0.0000 | 2.6415 |
| ALL | P1 | 0.0001 | 0.0005 | 0.0000 | 2.6415 |
| ALL | P2 | 0.0022 | 0.0035 | 0.0000 | 2.6415 |
| ALL | always_reference | n/a | n/a | n/a | 2.6415 |
| ALL | always_variant | n/a | n/a | n/a | 2.6415 |
| ALL | local_eb | 0.0054 | 0.0071 | 0.0000 | 2.6415 |
| ALL | local_eb+cal | n/a | n/a | 0.0000 | 2.6415 |
| ALL | text_lr | 0.0069 | 0.0089 | 0.0000 | 2.6415 |
| ALL | text_lr+cal | n/a | n/a | 0.0000 | 2.6415 |
| both | GBM | 0.0429 | 0.0682 | 0.0000 | 2.6415 |
| both | GBM+cal | n/a | n/a | 0.0000 | 2.6415 |
| both | P0 | 0.0000 | 0.0000 | 0.0000 | 2.6415 |
| both | P1 | 0.0004 | 0.0071 | 0.0000 | 2.6415 |
| both | P2 | 0.0029 | 0.0105 | 0.0000 | 2.6415 |
| both | always_reference | n/a | n/a | n/a | 2.6415 |
| both | always_variant | n/a | n/a | n/a | 2.6415 |
| both | local_eb | 0.0433 | 0.0674 | 0.0000 | 2.6415 |
| both | local_eb+cal | n/a | n/a | 0.0000 | 2.6415 |
| both | text_lr | 0.0502 | 0.0766 | 0.0000 | 2.6415 |
| both | text_lr+cal | n/a | n/a | 0.0000 | 2.6415 |
| headline_only | GBM | 0.0037 | 0.0058 | 0.0000 | 2.6415 |
| headline_only | GBM+cal | n/a | n/a | 0.0000 | 2.6415 |
| headline_only | P0 | 0.0000 | 0.0000 | 0.0000 | 2.6415 |
| headline_only | P1 | 0.0000 | 0.0003 | 0.0000 | 2.6415 |
| headline_only | P2 | 0.0029 | 0.0049 | 0.0000 | 2.6415 |
| headline_only | always_reference | n/a | n/a | n/a | 2.6415 |
| headline_only | always_variant | n/a | n/a | n/a | 2.6415 |
| headline_only | local_eb | 0.0028 | 0.0047 | 0.9950 | 2.6415 |
| headline_only | local_eb+cal | n/a | n/a | 0.0000 | 2.6415 |
| headline_only | text_lr | 0.0053 | 0.0079 | 0.0000 | 2.6415 |
| headline_only | text_lr+cal | n/a | n/a | 0.0000 | 2.6415 |
| image_only | GBM | 0.0030 | 0.0052 | 0.0000 | 2.6415 |
| image_only | GBM+cal | n/a | n/a | 0.0000 | 2.6415 |
| image_only | P0 | 0.0000 | 0.0000 | 0.0000 | 2.6415 |
| image_only | P1 | 0.0000 | 0.0005 | 0.9950 | 2.6415 |
| image_only | P2 | 0.0004 | 0.0014 | 0.9950 | 2.6415 |
| image_only | always_reference | n/a | n/a | n/a | 2.6415 |
| image_only | always_variant | n/a | n/a | n/a | 2.6415 |
| image_only | local_eb | 0.0047 | 0.0076 | 0.0000 | 2.6415 |
| image_only | local_eb+cal | n/a | n/a | 0.0000 | 2.6415 |
| image_only | text_lr | 0.0042 | 0.0071 | 0.0000 | 2.6415 |
| image_only | text_lr+cal | n/a | n/a | 0.0000 | 2.6415 |

## P2 selection by cell

How lam (the weight on precedents), the bandwidth multiplier and the recency half-life were chosen, summarised over the origins. `share_lambda_zero` is the share of origins where the selection gave up on precedents and P2 equalled P1 in that cell. `guard` is the admission guard multiplier: lam above zero is used only when its out-of-sample log-score gain over lam 0 minus that many standard errors (across tests) is above zero, the ladder admission rule made operational. `share_guard_held` is the share of origins where the guard forced lam to 0 although the earlier rule would have used the precedents; `gain_mean` and `gain_se_mean` are the gain of the best candidate and its standard error, averaged over origins. The per-origin values are in the JSON under `p2_selection`.

| rung | cell | selection | origins | lambda_mean | lambda_min | lambda_max | share_lambda_zero | guard | share_guard_held | lambda_unguarded_mean | gain_mean | gain_se_mean | bandwidth_mult_mean | share_no_decay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | both | forward | 7 | 0.1286 | 0.0000 | 0.9000 | 0.8571 | 2.0000 | 0.7143 | 0.3571 | 0.0081 | 0.0129 | 0.6429 | 1.0000 |
| P2 | headline_only | forward | 7 | 0.3429 | 0.0000 | 0.8000 | 0.2857 | 2.0000 | 0.1429 | 0.4714 | 0.0045 | 0.0013 | 0.4286 | 1.0000 |
| P2 | image_only | forward | 7 | 0.0429 | 0.0000 | 0.3000 | 0.8571 | 2.0000 | 0.1429 | 0.1714 | 0.0009 | 0.0020 | 1.0000 | 1.0000 |

Columns not computed (null on every row) and left out: half_life_days_median.

## Abstention by trigger

Counts of rows that fired each trigger (a row can fire several).

| cell | n | rate | support | novelty | reliability | instability |
|---|---|---|---|---|---|---|
| ALL | 13822 | 0.2406 | 425 | 1293 | 2811 | 1 |
| both | 407 | 0.2973 | 79 | 13 | 109 | 0 |
| headline_only | 8259 | 0.2418 | 0 | 414 | 1676 | 1 |
| image_only | 5156 | 0.2343 | 346 | 866 | 1026 | 0 |

All four triggers fired at least once. After the burn-in origin the reliability trigger fired on 1636 rows.

## Origins

The first scored origin is the burn-in origin.

| origin | n_scored | n_tests | abstention_rate | logscore | burn_in |
|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | 1175 | 1175 | 1.0000 | -1.0343 | yes |
| 2014-01-01T00:00:00+00:00 | 1636 | 1636 | 1.0000 | -1.2109 | no |
| 2014-04-01T00:00:00+00:00 | 2372 | 2372 | 0.0249 | -0.9063 | no |
| 2014-07-01T00:00:00+00:00 | 3468 | 3468 | 0.0557 | -0.6135 | no |
| 2014-10-01T00:00:00+00:00 | 3229 | 3229 | 0.0505 | -0.6746 | no |
| 2015-01-01T00:00:00+00:00 | 1570 | 1570 | 0.0529 | -0.7945 | no |
| 2015-04-01T00:00:00+00:00 | 372 | 372 | 0.0457 | -0.6271 | no |

### Log score by origin with 90 percent intervals

| origin | rung | n | logscore | logscore_lo | logscore_hi |
|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | GBM | 1175 | -1.1574 | -1.1849 | -1.1374 |
| 2013-04-01T00:00:00+00:00 | P0 | 1175 | -1.0164 | -1.0486 | -0.9855 |
| 2013-04-01T00:00:00+00:00 | P1 | 1175 | -1.0378 | -1.0710 | -1.0111 |
| 2013-04-01T00:00:00+00:00 | P2 | 1175 | -1.0343 | -1.0680 | -1.0071 |
| 2013-04-01T00:00:00+00:00 | local_eb | 1175 | -1.0474 | -1.0965 | -1.0106 |
| 2014-01-01T00:00:00+00:00 | GBM | 1636 | -1.1900 | -1.2429 | -1.1397 |
| 2014-01-01T00:00:00+00:00 | P0 | 1636 | -1.1639 | -1.2095 | -1.1183 |
| 2014-01-01T00:00:00+00:00 | P1 | 1636 | -1.2094 | -1.2630 | -1.1574 |
| 2014-01-01T00:00:00+00:00 | P2 | 1636 | -1.2109 | -1.2653 | -1.1583 |
| 2014-01-01T00:00:00+00:00 | local_eb | 1636 | -1.6649 | -1.8148 | -1.5322 |
| 2014-04-01T00:00:00+00:00 | GBM | 2372 | -0.9890 | -1.0119 | -0.9651 |
| 2014-04-01T00:00:00+00:00 | P0 | 2372 | -0.9105 | -0.9347 | -0.8853 |
| 2014-04-01T00:00:00+00:00 | P1 | 2372 | -0.9052 | -0.9310 | -0.8790 |
| 2014-04-01T00:00:00+00:00 | P2 | 2372 | -0.9063 | -0.9316 | -0.8804 |
| 2014-04-01T00:00:00+00:00 | local_eb | 2372 | -0.9629 | -1.0141 | -0.9185 |
| 2014-07-01T00:00:00+00:00 | GBM | 3468 | -0.7566 | -0.7681 | -0.7461 |
| 2014-07-01T00:00:00+00:00 | P0 | 3468 | -0.6423 | -0.6570 | -0.6269 |
| 2014-07-01T00:00:00+00:00 | P1 | 3468 | -0.6135 | -0.6301 | -0.5962 |
| 2014-07-01T00:00:00+00:00 | P2 | 3468 | -0.6135 | -0.6301 | -0.5962 |
| 2014-07-01T00:00:00+00:00 | local_eb | 3468 | -0.6308 | -0.6539 | -0.6113 |
| 2014-10-01T00:00:00+00:00 | GBM | 3229 | -0.7670 | -0.7898 | -0.7418 |
| 2014-10-01T00:00:00+00:00 | P0 | 3229 | -0.6889 | -0.7079 | -0.6637 |
| 2014-10-01T00:00:00+00:00 | P1 | 3229 | -0.6765 | -0.6997 | -0.6450 |
| 2014-10-01T00:00:00+00:00 | P2 | 3229 | -0.6746 | -0.6983 | -0.6433 |
| 2014-10-01T00:00:00+00:00 | local_eb | 3229 | -0.7615 | -0.8125 | -0.7055 |
| 2015-01-01T00:00:00+00:00 | GBM | 1570 | -0.8189 | -0.8588 | -0.7841 |
| 2015-01-01T00:00:00+00:00 | P0 | 1570 | -0.7766 | -0.8175 | -0.7403 |
| 2015-01-01T00:00:00+00:00 | P1 | 1570 | -0.7860 | -0.8328 | -0.7429 |
| 2015-01-01T00:00:00+00:00 | P2 | 1570 | -0.7945 | -0.8449 | -0.7502 |
| 2015-01-01T00:00:00+00:00 | local_eb | 1570 | -0.9142 | -0.9892 | -0.8480 |
| 2015-04-01T00:00:00+00:00 | GBM | 372 | -0.7268 | -0.8084 | -0.6538 |
| 2015-04-01T00:00:00+00:00 | P0 | 372 | -0.6284 | -0.6974 | -0.5563 |
| 2015-04-01T00:00:00+00:00 | P1 | 372 | -0.6278 | -0.7083 | -0.5491 |
| 2015-04-01T00:00:00+00:00 | P2 | 372 | -0.6271 | -0.7090 | -0.5408 |
| 2015-04-01T00:00:00+00:00 | local_eb | 372 | -0.7538 | -0.9002 | -0.6091 |

### Scores by calendar year of the test start

Each scored row belongs to the year in which its test started; the years partition the scored rows. Brier skill and log score carry 90 percent by-test intervals.

| year | cell | rung | n | n_tests | logscore | logscore_lo | logscore_hi | brier_skill | brier_skill_lo | brier_skill_hi | direction_accuracy | abstention_rate | event_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | ALL | GBM | 1175 | 1175 | -1.1574 | -1.1848 | -1.1347 | -0.1010 | -0.1292 | -0.0750 | 0.5243 | 1.0000 | 0.1157 |
| 2013 | ALL | GBM+cal | 1175 | 1175 | n/a | n/a | n/a | -0.0399 | -0.0606 | -0.0203 | n/a | 1.0000 | 0.1157 |
| 2013 | ALL | P0 | 1175 | 1175 | -1.0164 | -1.0488 | -0.9867 | 0.0000 | 0.0000 | 0.0000 | 0.5430 | 1.0000 | 0.1157 |
| 2013 | ALL | P1 | 1175 | 1175 | -1.0378 | -1.0698 | -1.0093 | -0.0137 | -0.0204 | -0.0073 | 0.5430 | 1.0000 | 0.1157 |
| 2013 | ALL | P2 | 1175 | 1175 | -1.0343 | -1.0667 | -1.0054 | -0.0100 | -0.0168 | -0.0029 | 0.5430 | 1.0000 | 0.1157 |
| 2013 | ALL | always_reference | 1175 | 1175 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5430 | 1.0000 | 0.1157 |
| 2013 | ALL | always_variant | 1175 | 1175 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4570 | 1.0000 | 0.1157 |
| 2013 | ALL | local_eb | 1175 | 1175 | -1.0474 | -1.0926 | -1.0069 | 0.0004 | -0.0169 | 0.0183 | 0.5421 | 1.0000 | 0.1157 |
| 2013 | ALL | local_eb+cal | 1175 | 1175 | n/a | n/a | n/a | -0.0251 | -0.0341 | -0.0162 | n/a | 1.0000 | 0.1157 |
| 2013 | ALL | text_lr | 1175 | 1175 | n/a | n/a | n/a | -0.0101 | -0.0314 | 0.0104 | 0.5345 | 1.0000 | 0.1157 |
| 2013 | ALL | text_lr+cal | 1175 | 1175 | n/a | n/a | n/a | -0.0163 | -0.0293 | -0.0047 | n/a | 1.0000 | 0.1157 |
| 2013 | both | GBM | 79 | 79 | -1.3028 | -1.4804 | -1.1648 | -0.0315 | -0.1915 | 0.0476 | 0.5823 | 1.0000 | 0.1266 |
| 2013 | both | GBM+cal | 79 | 79 | n/a | n/a | n/a | 0.0247 | -0.0550 | 0.0817 | n/a | 1.0000 | 0.1266 |
| 2013 | both | P0 | 79 | 79 | -1.2726 | -1.4213 | -1.1493 | 0.0000 | 0.0000 | 0.0000 | 0.5063 | 1.0000 | 0.1266 |
| 2013 | both | P1 | 79 | 79 | -1.2549 | -1.4183 | -1.1240 | -0.0080 | -0.0287 | 0.0015 | 0.5063 | 1.0000 | 0.1266 |
| 2013 | both | P2 | 79 | 79 | -1.2549 | -1.4183 | -1.1240 | -0.0080 | -0.0287 | 0.0015 | 0.5063 | 1.0000 | 0.1266 |
| 2013 | both | always_reference | 79 | 79 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5063 | 1.0000 | 0.1266 |
| 2013 | both | always_variant | 79 | 79 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4937 | 1.0000 | 0.1266 |
| 2013 | both | local_eb | 79 | 79 | -1.3186 | -1.5389 | -1.1513 | 0.0013 | -0.0004 | 0.0049 | 0.5063 | 1.0000 | 0.1266 |
| 2013 | both | local_eb+cal | 79 | 79 | n/a | n/a | n/a | -0.0146 | -0.0503 | 0.0019 | n/a | 1.0000 | 0.1266 |
| 2013 | both | text_lr | 79 | 79 | n/a | n/a | n/a | 0.0517 | -0.0035 | 0.1229 | 0.6203 | 1.0000 | 0.1266 |
| 2013 | both | text_lr+cal | 79 | 79 | n/a | n/a | n/a | 0.0259 | -0.0160 | 0.0564 | n/a | 1.0000 | 0.1266 |
| 2013 | headline_only | GBM | 750 | 750 | -1.1822 | -1.2154 | -1.1508 | -0.0378 | -0.0578 | -0.0194 | 0.5307 | 1.0000 | 0.1387 |
| 2013 | headline_only | GBM+cal | 750 | 750 | n/a | n/a | n/a | -0.0020 | -0.0214 | 0.0181 | n/a | 1.0000 | 0.1387 |
| 2013 | headline_only | P0 | 750 | 750 | -1.0840 | -1.1240 | -1.0407 | 0.0000 | 0.0000 | 0.0000 | 0.5440 | 1.0000 | 0.1387 |
| 2013 | headline_only | P1 | 750 | 750 | -1.0740 | -1.1159 | -1.0310 | 0.0126 | 0.0077 | 0.0182 | 0.5440 | 1.0000 | 0.1387 |
| 2013 | headline_only | P2 | 750 | 750 | -1.0685 | -1.1111 | -1.0242 | 0.0176 | 0.0104 | 0.0256 | 0.5440 | 1.0000 | 0.1387 |
| 2013 | headline_only | always_reference | 750 | 750 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5440 | 1.0000 | 0.1387 |
| 2013 | headline_only | always_variant | 750 | 750 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4560 | 1.0000 | 0.1387 |
| 2013 | headline_only | local_eb | 750 | 750 | -1.0934 | -1.1569 | -1.0356 | 0.0331 | 0.0090 | 0.0607 | 0.5427 | 1.0000 | 0.1387 |
| 2013 | headline_only | local_eb+cal | 750 | 750 | n/a | n/a | n/a | -0.0010 | -0.0076 | 0.0057 | n/a | 1.0000 | 0.1387 |
| 2013 | headline_only | text_lr | 750 | 750 | n/a | n/a | n/a | -0.0153 | -0.0447 | 0.0152 | 0.5360 | 1.0000 | 0.1387 |
| 2013 | headline_only | text_lr+cal | 750 | 750 | n/a | n/a | n/a | 0.0047 | -0.0082 | 0.0181 | n/a | 1.0000 | 0.1387 |
| 2013 | image_only | GBM | 346 | 346 | -1.0704 | -1.0932 | -1.0488 | -0.3919 | -0.5904 | -0.2535 | 0.4971 | 1.0000 | 0.0636 |
| 2013 | image_only | GBM+cal | 346 | 346 | n/a | n/a | n/a | -0.2232 | -0.3554 | -0.1320 | n/a | 1.0000 | 0.0636 |
| 2013 | image_only | P0 | 346 | 346 | -0.8115 | -0.8612 | -0.7673 | 0.0000 | 0.0000 | 0.0000 | 0.5491 | 1.0000 | 0.0636 |
| 2013 | image_only | P1 | 346 | 346 | -0.9098 | -0.9466 | -0.8765 | -0.1254 | -0.1843 | -0.0752 | 0.5491 | 1.0000 | 0.0636 |
| 2013 | image_only | P2 | 346 | 346 | -0.9098 | -0.9466 | -0.8765 | -0.1254 | -0.1843 | -0.0752 | 0.5491 | 1.0000 | 0.0636 |
| 2013 | image_only | always_reference | 346 | 346 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5491 | 1.0000 | 0.0636 |
| 2013 | image_only | always_variant | 346 | 346 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4509 | 1.0000 | 0.0636 |
| 2013 | image_only | local_eb | 346 | 346 | -0.8858 | -0.9239 | -0.8504 | -0.1356 | -0.1988 | -0.0817 | 0.5491 | 1.0000 | 0.0636 |
| 2013 | image_only | local_eb+cal | 346 | 346 | n/a | n/a | n/a | -0.1292 | -0.1897 | -0.0776 | n/a | 1.0000 | 0.0636 |
| 2013 | image_only | text_lr | 346 | 346 | n/a | n/a | n/a | -0.0128 | -0.0383 | 0.0120 | 0.5116 | 1.0000 | 0.0636 |
| 2013 | image_only | text_lr+cal | 346 | 346 | n/a | n/a | n/a | -0.1201 | -0.1918 | -0.0709 | n/a | 1.0000 | 0.0636 |
| 2014 | ALL | GBM | 10705 | 10705 | -0.8775 | -0.8908 | -0.8654 | -0.0481 | -0.0565 | -0.0398 | 0.5480 | 0.1916 | 0.0984 |
| 2014 | ALL | GBM+cal | 10705 | 10705 | n/a | n/a | n/a | 0.0006 | -0.0020 | 0.0033 | n/a | 0.1916 | 0.0984 |
| 2014 | ALL | P0 | 10705 | 10705 | -0.7955 | -0.8076 | -0.7836 | 0.0000 | 0.0000 | 0.0000 | 0.5548 | 0.1916 | 0.0984 |
| 2014 | ALL | P1 | 10705 | 10705 | -0.7882 | -0.8023 | -0.7741 | 0.0049 | 0.0030 | 0.0068 | 0.5379 | 0.1916 | 0.0984 |
| 2014 | ALL | P2 | 10705 | 10705 | -0.7881 | -0.8021 | -0.7741 | 0.0055 | 0.0035 | 0.0076 | 0.5380 | 0.1916 | 0.0984 |
| 2014 | ALL | always_reference | 10705 | 10705 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5548 | 0.1916 | 0.0984 |
| 2014 | ALL | always_variant | 10705 | 10705 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4452 | 0.1916 | 0.0984 |
| 2014 | ALL | local_eb | 10705 | 10705 | -0.9018 | -0.9350 | -0.8730 | -0.0044 | -0.0090 | 0.0004 | 0.5338 | 0.1916 | 0.0984 |
| 2014 | ALL | local_eb+cal | 10705 | 10705 | n/a | n/a | n/a | 0.0040 | 0.0021 | 0.0057 | n/a | 0.1916 | 0.0984 |
| 2014 | ALL | text_lr | 10705 | 10705 | n/a | n/a | n/a | -0.0025 | -0.0080 | 0.0030 | 0.5325 | 0.1916 | 0.0984 |
| 2014 | ALL | text_lr+cal | 10705 | 10705 | n/a | n/a | n/a | 0.0064 | 0.0035 | 0.0091 | n/a | 0.1916 | 0.0984 |
| 2014 | both | GBM | 242 | 242 | -0.9738 | -1.1472 | -0.8461 | -0.0625 | -0.1159 | -0.0227 | 0.5620 | 0.1653 | 0.0826 |
| 2014 | both | GBM+cal | 242 | 242 | n/a | n/a | n/a | 0.0098 | -0.0015 | 0.0256 | n/a | 0.1653 | 0.0826 |
| 2014 | both | P0 | 242 | 242 | -0.8582 | -0.9452 | -0.7824 | 0.0000 | 0.0000 | 0.0000 | 0.5661 | 0.1653 | 0.0826 |
| 2014 | both | P1 | 242 | 242 | -0.8477 | -0.9449 | -0.7633 | -0.0033 | -0.0105 | 0.0031 | 0.5661 | 0.1653 | 0.0826 |
| 2014 | both | P2 | 242 | 242 | -0.8477 | -0.9449 | -0.7633 | -0.0033 | -0.0105 | 0.0031 | 0.5661 | 0.1653 | 0.0826 |
| 2014 | both | always_reference | 242 | 242 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5661 | 0.1653 | 0.0826 |
| 2014 | both | always_variant | 242 | 242 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4339 | 0.1653 | 0.0826 |
| 2014 | both | local_eb | 242 | 242 | -1.0077 | -1.3225 | -0.7747 | -0.0032 | -0.0364 | 0.0371 | 0.5248 | 0.1653 | 0.0826 |
| 2014 | both | local_eb+cal | 242 | 242 | n/a | n/a | n/a | 0.0077 | -0.0074 | 0.0274 | n/a | 0.1653 | 0.0826 |
| 2014 | both | text_lr | 242 | 242 | n/a | n/a | n/a | -0.0181 | -0.0740 | 0.0365 | 0.5537 | 0.1653 | 0.0826 |
| 2014 | both | text_lr+cal | 242 | 242 | n/a | n/a | n/a | 0.0062 | -0.0189 | 0.0327 | n/a | 0.1653 | 0.0826 |
| 2014 | headline_only | GBM | 6401 | 6401 | -0.8722 | -0.8904 | -0.8545 | -0.0430 | -0.0513 | -0.0354 | 0.5588 | 0.1861 | 0.1006 |
| 2014 | headline_only | GBM+cal | 6401 | 6401 | n/a | n/a | n/a | 0.0028 | 0.0008 | 0.0047 | n/a | 0.1861 | 0.1006 |
| 2014 | headline_only | P0 | 6401 | 6401 | -0.7884 | -0.8030 | -0.7739 | 0.0000 | 0.0000 | 0.0000 | 0.5608 | 0.1861 | 0.1006 |
| 2014 | headline_only | P1 | 6401 | 6401 | -0.7706 | -0.7870 | -0.7541 | 0.0081 | 0.0055 | 0.0105 | 0.5608 | 0.1861 | 0.1006 |
| 2014 | headline_only | P2 | 6401 | 6401 | -0.7701 | -0.7864 | -0.7531 | 0.0087 | 0.0058 | 0.0117 | 0.5610 | 0.1861 | 0.1006 |
| 2014 | headline_only | always_reference | 6401 | 6401 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5608 | 0.1861 | 0.1006 |
| 2014 | headline_only | always_variant | 6401 | 6401 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4392 | 0.1861 | 0.1006 |
| 2014 | headline_only | local_eb | 6401 | 6401 | -0.8648 | -0.9029 | -0.8255 | 0.0036 | -0.0026 | 0.0098 | 0.5454 | 0.1861 | 0.1006 |
| 2014 | headline_only | local_eb+cal | 6401 | 6401 | n/a | n/a | n/a | 0.0059 | 0.0040 | 0.0078 | n/a | 0.1861 | 0.1006 |
| 2014 | headline_only | text_lr | 6401 | 6401 | n/a | n/a | n/a | -0.0002 | -0.0084 | 0.0085 | 0.5490 | 0.1861 | 0.1006 |
| 2014 | headline_only | text_lr+cal | 6401 | 6401 | n/a | n/a | n/a | 0.0100 | 0.0061 | 0.0142 | n/a | 0.1861 | 0.1006 |
| 2014 | image_only | GBM | 4062 | 4062 | -0.8801 | -0.9008 | -0.8617 | -0.0556 | -0.0741 | -0.0388 | 0.5300 | 0.2019 | 0.0958 |
| 2014 | image_only | GBM+cal | 4062 | 4062 | n/a | n/a | n/a | -0.0034 | -0.0102 | 0.0035 | n/a | 0.2019 | 0.0958 |
| 2014 | image_only | P0 | 4062 | 4062 | -0.8029 | -0.8288 | -0.7788 | 0.0000 | 0.0000 | 0.0000 | 0.5446 | 0.2019 | 0.0958 |
| 2014 | image_only | P1 | 4062 | 4062 | -0.8124 | -0.8441 | -0.7845 | 0.0000 | -0.0026 | 0.0030 | 0.5000 | 0.2019 | 0.0958 |
| 2014 | image_only | P2 | 4062 | 4062 | -0.8131 | -0.8446 | -0.7852 | 0.0007 | -0.0017 | 0.0036 | 0.5000 | 0.2019 | 0.0958 |
| 2014 | image_only | always_reference | 4062 | 4062 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5446 | 0.2019 | 0.0958 |
| 2014 | image_only | always_variant | 4062 | 4062 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4554 | 0.2019 | 0.0958 |
| 2014 | image_only | local_eb | 4062 | 4062 | -0.9539 | -1.0119 | -0.9028 | -0.0177 | -0.0254 | -0.0097 | 0.5160 | 0.2019 | 0.0958 |
| 2014 | image_only | local_eb+cal | 4062 | 4062 | n/a | n/a | n/a | 0.0005 | -0.0036 | 0.0045 | n/a | 0.2019 | 0.0958 |
| 2014 | image_only | text_lr | 4062 | 4062 | n/a | n/a | n/a | -0.0053 | -0.0100 | -0.0009 | 0.5052 | 0.2019 | 0.0958 |
| 2014 | image_only | text_lr+cal | 4062 | 4062 | n/a | n/a | n/a | 0.0006 | -0.0034 | 0.0046 | n/a | 0.2019 | 0.0958 |
| 2015 | ALL | GBM | 1942 | 1942 | -0.8013 | -0.8403 | -0.7661 | -0.0524 | -0.0764 | -0.0338 | 0.5917 | 0.0515 | 0.0726 |
| 2015 | ALL | GBM+cal | 1942 | 1942 | n/a | n/a | n/a | 0.0099 | 0.0049 | 0.0146 | n/a | 0.0515 | 0.0726 |
| 2015 | ALL | P0 | 1942 | 1942 | -0.7482 | -0.7839 | -0.7148 | 0.0000 | 0.0000 | 0.0000 | 0.5927 | 0.0515 | 0.0726 |
| 2015 | ALL | P1 | 1942 | 1942 | -0.7557 | -0.7967 | -0.7174 | 0.0095 | 0.0031 | 0.0173 | 0.5927 | 0.0515 | 0.0726 |
| 2015 | ALL | P2 | 1942 | 1942 | -0.7624 | -0.8068 | -0.7217 | 0.0099 | 0.0015 | 0.0204 | 0.5917 | 0.0515 | 0.0726 |
| 2015 | ALL | always_reference | 1942 | 1942 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5927 | 0.0515 | 0.0726 |
| 2015 | ALL | always_variant | 1942 | 1942 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4073 | 0.0515 | 0.0726 |
| 2015 | ALL | local_eb | 1942 | 1942 | -0.8835 | -0.9601 | -0.8205 | -0.0043 | -0.0156 | 0.0078 | 0.5772 | 0.0515 | 0.0726 |
| 2015 | ALL | local_eb+cal | 1942 | 1942 | n/a | n/a | n/a | -0.0030 | -0.0064 | -0.0003 | n/a | 0.0515 | 0.0726 |
| 2015 | ALL | text_lr | 1942 | 1942 | n/a | n/a | n/a | 0.0098 | -0.0078 | 0.0233 | 0.5772 | 0.0515 | 0.0726 |
| 2015 | ALL | text_lr+cal | 1942 | 1942 | n/a | n/a | n/a | 0.0071 | -0.0029 | 0.0152 | n/a | 0.0515 | 0.0726 |
| 2015 | both | GBM | 86 | 86 | -0.8244 | -1.0225 | -0.6614 | -0.1518 | -0.3987 | -0.0578 | 0.5814 | 0.0233 | 0.0581 |
| 2015 | both | GBM+cal | 86 | 86 | n/a | n/a | n/a | -0.0348 | -0.0651 | -0.0114 | n/a | 0.0233 | 0.0581 |
| 2015 | both | P0 | 86 | 86 | -0.7497 | -0.9042 | -0.6167 | 0.0000 | 0.0000 | 0.0000 | 0.6512 | 0.0233 | 0.0581 |
| 2015 | both | P1 | 86 | 86 | -0.7392 | -0.9074 | -0.5940 | -0.0033 | -0.0092 | -0.0011 | 0.6512 | 0.0233 | 0.0581 |
| 2015 | both | P2 | 86 | 86 | -0.7378 | -0.9049 | -0.5925 | 0.0014 | -0.0003 | 0.0027 | 0.6512 | 0.0233 | 0.0581 |
| 2015 | both | always_reference | 86 | 86 | n/a | n/a | n/a | n/a | n/a | n/a | 0.6512 | 0.0233 | 0.0581 |
| 2015 | both | always_variant | 86 | 86 | n/a | n/a | n/a | n/a | n/a | n/a | 0.3488 | 0.0233 | 0.0581 |
| 2015 | both | local_eb | 86 | 86 | -0.9181 | -1.3573 | -0.5643 | 0.0223 | -0.0231 | 0.1348 | 0.6860 | 0.0233 | 0.0581 |
| 2015 | both | local_eb+cal | 86 | 86 | n/a | n/a | n/a | -0.0019 | -0.0117 | 0.0021 | n/a | 0.0233 | 0.0581 |
| 2015 | both | text_lr | 86 | 86 | n/a | n/a | n/a | 0.0370 | -0.0310 | 0.0915 | 0.5116 | 0.0233 | 0.0581 |
| 2015 | both | text_lr+cal | 86 | 86 | n/a | n/a | n/a | 0.0204 | -0.0287 | 0.0483 | n/a | 0.0233 | 0.0581 |
| 2015 | headline_only | GBM | 1108 | 1108 | -0.7912 | -0.8338 | -0.7524 | -0.0304 | -0.0594 | -0.0086 | 0.5866 | 0.0505 | 0.0803 |
| 2015 | headline_only | GBM+cal | 1108 | 1108 | n/a | n/a | n/a | 0.0201 | 0.0132 | 0.0278 | n/a | 0.0505 | 0.0803 |
| 2015 | headline_only | P0 | 1108 | 1108 | -0.7590 | -0.8041 | -0.7148 | 0.0000 | 0.0000 | 0.0000 | 0.5830 | 0.0505 | 0.0803 |
| 2015 | headline_only | P1 | 1108 | 1108 | -0.7688 | -0.8245 | -0.7178 | 0.0084 | 0.0003 | 0.0193 | 0.5830 | 0.0505 | 0.0803 |
| 2015 | headline_only | P2 | 1108 | 1108 | -0.7807 | -0.8422 | -0.7252 | 0.0088 | -0.0040 | 0.0261 | 0.5812 | 0.0505 | 0.0803 |
| 2015 | headline_only | always_reference | 1108 | 1108 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5830 | 0.0505 | 0.0803 |
| 2015 | headline_only | always_variant | 1108 | 1108 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4170 | 0.0505 | 0.0803 |
| 2015 | headline_only | local_eb | 1108 | 1108 | -0.8992 | -0.9831 | -0.8176 | 0.0022 | -0.0126 | 0.0211 | 0.5713 | 0.0505 | 0.0803 |
| 2015 | headline_only | local_eb+cal | 1108 | 1108 | n/a | n/a | n/a | 0.0038 | 0.0017 | 0.0064 | n/a | 0.0505 | 0.0803 |
| 2015 | headline_only | text_lr | 1108 | 1108 | n/a | n/a | n/a | 0.0196 | -0.0060 | 0.0425 | 0.5993 | 0.0505 | 0.0803 |
| 2015 | headline_only | text_lr+cal | 1108 | 1108 | n/a | n/a | n/a | 0.0194 | 0.0058 | 0.0314 | n/a | 0.0505 | 0.0803 |
| 2015 | image_only | GBM | 748 | 748 | -0.8134 | -0.8775 | -0.7507 | -0.0823 | -0.1294 | -0.0514 | 0.6003 | 0.0561 | 0.0628 |
| 2015 | image_only | GBM+cal | 748 | 748 | n/a | n/a | n/a | -0.0042 | -0.0077 | -0.0013 | n/a | 0.0561 | 0.0628 |
| 2015 | image_only | P0 | 748 | 748 | -0.7319 | -0.7864 | -0.6759 | 0.0000 | 0.0000 | 0.0000 | 0.6003 | 0.0561 | 0.0628 |
| 2015 | image_only | P1 | 748 | 748 | -0.7382 | -0.8014 | -0.6723 | 0.0128 | 0.0032 | 0.0275 | 0.6003 | 0.0561 | 0.0628 |
| 2015 | image_only | P2 | 748 | 748 | -0.7382 | -0.8014 | -0.6723 | 0.0128 | 0.0032 | 0.0275 | 0.6003 | 0.0561 | 0.0628 |
| 2015 | image_only | always_reference | 748 | 748 | n/a | n/a | n/a | n/a | n/a | n/a | 0.6003 | 0.0561 | 0.0628 |
| 2015 | image_only | always_variant | 748 | 748 | n/a | n/a | n/a | n/a | n/a | n/a | 0.3997 | 0.0561 | 0.0628 |
| 2015 | image_only | local_eb | 748 | 748 | -0.8562 | -0.9679 | -0.7563 | -0.0191 | -0.0382 | -0.0001 | 0.5735 | 0.0561 | 0.0628 |
| 2015 | image_only | local_eb+cal | 748 | 748 | n/a | n/a | n/a | -0.0157 | -0.0271 | -0.0079 | n/a | 0.0561 | 0.0628 |
| 2015 | image_only | text_lr | 748 | 748 | n/a | n/a | n/a | -0.0111 | -0.0234 | 0.0019 | 0.5521 | 0.0561 | 0.0628 |
| 2015 | image_only | text_lr+cal | 748 | 748 | n/a | n/a | n/a | -0.0171 | -0.0304 | -0.0068 | n/a | 0.0561 | 0.0628 |

## Coverage of the intervals for y (primary rung)

| cell | n | coverage_80 | coverage_90 |
|---|---|---|---|
| ALL | 13822 | 0.8195 | 0.8982 |
| both | 407 | 0.8600 | 0.9263 |
| headline_only | 8259 | 0.8311 | 0.9093 |
| image_only | 5156 | 0.7977 | 0.8782 |

## Coverage by realized over planned standard error

Rows grouped in deciles of the ratio of the realized to the planned standard error (an evaluation-time stratifier: the realized standard error is never a forecast input). The forecaster fixes the click-through level at the cell median, so the ratio varies with the realized level; `coverage_80` and `coverage_90` should be near 0.80 and 0.90 in every decile. A rung that is not in range here is not calibrated within strata, whatever its pooled coverage.

| rung | decile | ratio_lo | ratio_hi | n | mean_ratio | coverage_80 | coverage_90 | event_rate | mean_p_sig |
|---|---|---|---|---|---|---|---|---|---|
| GBM | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | 1.0000 | 1.0000 | 0.0824 | 0.1720 |
| GBM | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | 0.9899 | 0.9978 | 0.0912 | 0.1739 |
| GBM | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | 0.9812 | 0.9928 | 0.0803 | 0.1731 |
| GBM | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | 0.9609 | 0.9855 | 0.0897 | 0.1730 |
| GBM | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | 0.9414 | 0.9790 | 0.0832 | 0.1701 |
| GBM | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | 0.9023 | 0.9660 | 0.1122 | 0.1705 |
| GBM | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | 0.9045 | 0.9530 | 0.1035 | 0.1713 |
| GBM | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | 0.8517 | 0.9269 | 0.1020 | 0.1693 |
| GBM | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | 0.7996 | 0.8821 | 0.1049 | 0.1710 |
| GBM | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | 0.6725 | 0.7925 | 0.1128 | 0.1704 |
| GBM+cal | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | n/a | n/a | 0.0824 | 0.1280 |
| GBM+cal | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | n/a | n/a | 0.0912 | 0.1300 |
| GBM+cal | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | n/a | n/a | 0.0803 | 0.1301 |
| GBM+cal | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | n/a | n/a | 0.0897 | 0.1299 |
| GBM+cal | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | n/a | n/a | 0.0832 | 0.1276 |
| GBM+cal | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | n/a | n/a | 0.1122 | 0.1277 |
| GBM+cal | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | n/a | n/a | 0.1035 | 0.1288 |
| GBM+cal | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | n/a | n/a | 0.1020 | 0.1274 |
| GBM+cal | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | n/a | n/a | 0.1049 | 0.1287 |
| GBM+cal | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | n/a | n/a | 0.1128 | 0.1280 |
| P0 | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | 0.9978 | 1.0000 | 0.0824 | 0.1258 |
| P0 | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | 0.9805 | 0.9971 | 0.0912 | 0.1249 |
| P0 | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | 0.9696 | 0.9928 | 0.0803 | 0.1233 |
| P0 | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | 0.9320 | 0.9819 | 0.0897 | 0.1227 |
| P0 | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | 0.9067 | 0.9725 | 0.0832 | 0.1209 |
| P0 | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | 0.8538 | 0.9580 | 0.1122 | 0.1207 |
| P0 | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | 0.8350 | 0.9407 | 0.1035 | 0.1214 |
| P0 | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | 0.7923 | 0.9117 | 0.1020 | 0.1207 |
| P0 | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | 0.7366 | 0.8654 | 0.1049 | 0.1201 |
| P0 | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | 0.5980 | 0.7607 | 0.1128 | 0.1153 |
| P1 | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | 0.9928 | 1.0000 | 0.0824 | 0.1141 |
| P1 | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | 0.9703 | 0.9906 | 0.0912 | 0.1124 |
| P1 | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | 0.9407 | 0.9834 | 0.0803 | 0.1097 |
| P1 | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | 0.8980 | 0.9674 | 0.0897 | 0.1090 |
| P1 | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | 0.8546 | 0.9385 | 0.0832 | 0.1060 |
| P1 | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | 0.8017 | 0.9045 | 0.1122 | 0.1049 |
| P1 | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | 0.7822 | 0.8951 | 0.1035 | 0.1065 |
| P1 | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | 0.7431 | 0.8517 | 0.1020 | 0.1048 |
| P1 | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | 0.6896 | 0.8010 | 0.1049 | 0.1050 |
| P1 | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | 0.5416 | 0.6696 | 0.1128 | 0.0993 |
| P2 | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | 0.9928 | 1.0000 | 0.0824 | 0.1136 |
| P2 | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | 0.9711 | 0.9906 | 0.0912 | 0.1113 |
| P2 | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | 0.9414 | 0.9834 | 0.0803 | 0.1086 |
| P2 | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | 0.8980 | 0.9674 | 0.0897 | 0.1075 |
| P2 | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | 0.8538 | 0.9385 | 0.0832 | 0.1045 |
| P2 | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | 0.8003 | 0.8987 | 0.1122 | 0.1027 |
| P2 | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | 0.7779 | 0.8929 | 0.1035 | 0.1043 |
| P2 | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | 0.7388 | 0.8473 | 0.1020 | 0.1021 |
| P2 | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | 0.6867 | 0.7981 | 0.1049 | 0.1021 |
| P2 | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | 0.5343 | 0.6652 | 0.1128 | 0.0956 |
| always_reference | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | n/a | n/a | 0.0824 | n/a |
| always_reference | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | n/a | n/a | 0.0912 | n/a |
| always_reference | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | n/a | n/a | 0.0803 | n/a |
| always_reference | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | n/a | n/a | 0.0897 | n/a |
| always_reference | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | n/a | n/a | 0.0832 | n/a |
| always_reference | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | n/a | n/a | 0.1122 | n/a |
| always_reference | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | n/a | n/a | 0.1035 | n/a |
| always_reference | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | n/a | n/a | 0.1020 | n/a |
| always_reference | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | n/a | n/a | 0.1049 | n/a |
| always_reference | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | n/a | n/a | 0.1128 | n/a |
| always_variant | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | n/a | n/a | 0.0824 | n/a |
| always_variant | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | n/a | n/a | 0.0912 | n/a |
| always_variant | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | n/a | n/a | 0.0803 | n/a |
| always_variant | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | n/a | n/a | 0.0897 | n/a |
| always_variant | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | n/a | n/a | 0.0832 | n/a |
| always_variant | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | n/a | n/a | 0.1122 | n/a |
| always_variant | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | n/a | n/a | 0.1035 | n/a |
| always_variant | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | n/a | n/a | 0.1020 | n/a |
| always_variant | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | n/a | n/a | 0.1049 | n/a |
| always_variant | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | n/a | n/a | 0.1128 | n/a |
| local_eb | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | 0.9848 | 0.9971 | 0.0824 | 0.1068 |
| local_eb | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | 0.9559 | 0.9863 | 0.0912 | 0.1075 |
| local_eb | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | 0.9385 | 0.9732 | 0.0803 | 0.1072 |
| local_eb | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | 0.8835 | 0.9479 | 0.0897 | 0.1072 |
| local_eb | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | 0.8517 | 0.9269 | 0.0832 | 0.1046 |
| local_eb | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | 0.7988 | 0.8857 | 0.1122 | 0.1040 |
| local_eb | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | 0.7764 | 0.8712 | 0.1035 | 0.1070 |
| local_eb | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | 0.7337 | 0.8198 | 0.1020 | 0.1031 |
| local_eb | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | 0.6708 | 0.7699 | 0.1049 | 0.1008 |
| local_eb | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | 0.5221 | 0.6233 | 0.1128 | 0.0958 |
| local_eb+cal | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | n/a | n/a | 0.0824 | 0.1237 |
| local_eb+cal | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | n/a | n/a | 0.0912 | 0.1254 |
| local_eb+cal | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | n/a | n/a | 0.0803 | 0.1252 |
| local_eb+cal | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | n/a | n/a | 0.0897 | 0.1255 |
| local_eb+cal | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | n/a | n/a | 0.0832 | 0.1234 |
| local_eb+cal | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | n/a | n/a | 0.1122 | 0.1232 |
| local_eb+cal | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | n/a | n/a | 0.1035 | 0.1245 |
| local_eb+cal | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | n/a | n/a | 0.1020 | 0.1239 |
| local_eb+cal | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | n/a | n/a | 0.1049 | 0.1232 |
| local_eb+cal | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | n/a | n/a | 0.1128 | 0.1194 |
| text_lr | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | n/a | n/a | 0.0824 | 0.1170 |
| text_lr | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | n/a | n/a | 0.0912 | 0.1167 |
| text_lr | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | n/a | n/a | 0.0803 | 0.1173 |
| text_lr | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | n/a | n/a | 0.0897 | 0.1166 |
| text_lr | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | n/a | n/a | 0.0832 | 0.1138 |
| text_lr | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | n/a | n/a | 0.1122 | 0.1167 |
| text_lr | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | n/a | n/a | 0.1035 | 0.1159 |
| text_lr | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | n/a | n/a | 0.1020 | 0.1128 |
| text_lr | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | n/a | n/a | 0.1049 | 0.1163 |
| text_lr | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | n/a | n/a | 0.1128 | 0.1147 |
| text_lr+cal | 1 | 0.2005 | 0.5281 | 1383 | 0.4325 | n/a | n/a | 0.0824 | 0.1238 |
| text_lr+cal | 2 | 0.5283 | 0.6299 | 1382 | 0.5828 | n/a | n/a | 0.0912 | 0.1251 |
| text_lr+cal | 3 | 0.6299 | 0.7151 | 1382 | 0.6730 | n/a | n/a | 0.0803 | 0.1258 |
| text_lr+cal | 4 | 0.7152 | 0.7904 | 1382 | 0.7527 | n/a | n/a | 0.0897 | 0.1257 |
| text_lr+cal | 5 | 0.7905 | 0.8676 | 1382 | 0.8295 | n/a | n/a | 0.0832 | 0.1234 |
| text_lr+cal | 6 | 0.8677 | 0.9502 | 1382 | 0.9082 | n/a | n/a | 0.1122 | 0.1253 |
| text_lr+cal | 7 | 0.9503 | 1.0448 | 1382 | 0.9952 | n/a | n/a | 0.1035 | 0.1253 |
| text_lr+cal | 8 | 1.0449 | 1.1647 | 1382 | 1.1013 | n/a | n/a | 0.1020 | 0.1239 |
| text_lr+cal | 9 | 1.1651 | 1.3580 | 1382 | 1.2512 | n/a | n/a | 0.1049 | 0.1265 |
| text_lr+cal | 10 | 1.3581 | 3.3635 | 1383 | 1.6041 | n/a | n/a | 0.1128 | 0.1248 |

## Calibration by precision

Rows grouped in deciles of the planned exposures per arm (fewer groups when exposures tie). A forecaster that is calibrated overall but not within these groups is not calibrated. `mean_p_sig` should match `event_rate`, and `coverage_90` should be near 0.90, in every group.

| rung | decile | exposure_lo | exposure_hi | n | mean_s_star | mean_p_sig | event_rate | coverage_90 |
|---|---|---|---|---|---|---|---|---|
| GBM | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.2265 | 0.1151 | 0.9653 |
| GBM | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1678 | 0.1290 | 0.9391 |
| GBM | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1781 | 0.1028 | 0.9012 |
| GBM | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1666 | 0.0974 | 0.9717 |
| GBM | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1733 | 0.0771 | 0.9748 |
| GBM | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.1483 | 0.0803 | 0.9233 |
| GBM | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.1408 | 0.0694 | 0.9240 |
| GBM | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.1677 | 0.0912 | 0.9376 |
| GBM+cal | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1887 | 0.1151 | n/a |
| GBM+cal | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1239 | 0.1290 | n/a |
| GBM+cal | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1369 | 0.1028 | n/a |
| GBM+cal | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1235 | 0.0974 | n/a |
| GBM+cal | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1257 | 0.0771 | n/a |
| GBM+cal | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.1030 | 0.0803 | n/a |
| GBM+cal | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.0948 | 0.0694 | n/a |
| GBM+cal | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.1263 | 0.0912 | n/a |
| P0 | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1825 | 0.1151 | 0.9543 |
| P0 | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1328 | 0.1290 | 0.9304 |
| P0 | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1526 | 0.1028 | 0.9150 |
| P0 | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1212 | 0.0974 | 0.9704 |
| P0 | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1074 | 0.0771 | 0.9618 |
| P0 | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.1075 | 0.0803 | 0.9188 |
| P0 | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.0940 | 0.0694 | 0.9124 |
| P0 | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.1031 | 0.0912 | 0.9155 |
| P1 | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1881 | 0.1151 | 0.9535 |
| P1 | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1225 | 0.1290 | 0.9188 |
| P1 | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1308 | 0.1028 | 0.8636 |
| P1 | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1108 | 0.0974 | 0.9477 |
| P1 | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.0981 | 0.0771 | 0.9359 |
| P1 | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.0871 | 0.0803 | 0.8574 |
| P1 | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.0739 | 0.0694 | 0.8562 |
| P1 | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.0800 | 0.0912 | 0.8521 |
| P2 | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1849 | 0.1151 | 0.9535 |
| P2 | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1225 | 0.1290 | 0.9188 |
| P2 | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1258 | 0.1028 | 0.8587 |
| P2 | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1129 | 0.0974 | 0.9499 |
| P2 | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.0981 | 0.0771 | 0.9359 |
| P2 | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.0740 | 0.0803 | 0.8348 |
| P2 | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.0739 | 0.0694 | 0.8562 |
| P2 | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.0775 | 0.0912 | 0.8511 |
| always_reference | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | n/a | 0.1151 | n/a |
| always_reference | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | n/a | 0.1290 | n/a |
| always_reference | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | n/a | 0.1028 | n/a |
| always_reference | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | n/a | 0.0974 | n/a |
| always_reference | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | n/a | 0.0771 | n/a |
| always_reference | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | n/a | 0.0803 | n/a |
| always_reference | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | n/a | 0.0694 | n/a |
| always_reference | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | n/a | 0.0912 | n/a |
| always_variant | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | n/a | 0.1151 | n/a |
| always_variant | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | n/a | 0.1290 | n/a |
| always_variant | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | n/a | 0.1028 | n/a |
| always_variant | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | n/a | 0.0974 | n/a |
| always_variant | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | n/a | 0.0771 | n/a |
| always_variant | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | n/a | 0.0803 | n/a |
| always_variant | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | n/a | 0.0694 | n/a |
| always_variant | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | n/a | 0.0912 | n/a |
| local_eb | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1593 | 0.1151 | 0.9338 |
| local_eb | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1016 | 0.1290 | 0.8674 |
| local_eb | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1113 | 0.1028 | 0.7875 |
| local_eb | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1052 | 0.0974 | 0.9328 |
| local_eb | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1212 | 0.0771 | 0.9431 |
| local_eb | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.0778 | 0.0803 | 0.8195 |
| local_eb | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.0927 | 0.0694 | 0.8529 |
| local_eb | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.0883 | 0.0912 | 0.8464 |
| local_eb+cal | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1930 | 0.1151 | n/a |
| local_eb+cal | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1228 | 0.1290 | n/a |
| local_eb+cal | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1366 | 0.1028 | n/a |
| local_eb+cal | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1203 | 0.0974 | n/a |
| local_eb+cal | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1207 | 0.0771 | n/a |
| local_eb+cal | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.1046 | 0.0803 | n/a |
| local_eb+cal | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.1088 | 0.0694 | n/a |
| local_eb+cal | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.1097 | 0.0912 | n/a |
| text_lr | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1736 | 0.1151 | n/a |
| text_lr | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1216 | 0.1290 | n/a |
| text_lr | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1429 | 0.1028 | n/a |
| text_lr | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1145 | 0.0974 | n/a |
| text_lr | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1055 | 0.0771 | n/a |
| text_lr | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.1022 | 0.0803 | n/a |
| text_lr | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.0919 | 0.0694 | n/a |
| text_lr | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.0999 | 0.0912 | n/a |
| text_lr+cal | 1 | 2731.0000 | 2826.0000 | 1269 | 0.3425 | 0.1902 | 0.1151 | n/a |
| text_lr+cal | 2 | 2878.0000 | 2878.0000 | 1380 | 0.3347 | 0.1274 | 0.1290 | n/a |
| text_lr+cal | 3 | 2897.0000 | 2924.0000 | 1012 | 0.3205 | 0.1430 | 0.1028 | n/a |
| text_lr+cal | 4 | 3030.0000 | 3104.0000 | 3213 | 0.3239 | 0.1209 | 0.0974 | n/a |
| text_lr+cal | 5 | 3111.0000 | 3188.0000 | 1388 | 0.3266 | 0.1154 | 0.0771 | n/a |
| text_lr+cal | 6 | 3190.0000 | 3316.0000 | 1108 | 0.2631 | 0.1088 | 0.0803 | n/a |
| text_lr+cal | 7 | 3328.0000 | 3328.0000 | 605 | 0.2879 | 0.1074 | 0.0694 | n/a |
| text_lr+cal | 8 | 3348.0000 | 3385.0000 | 3847 | 0.2859 | 0.1120 | 0.0912 | n/a |

## Reliability bins of p_sig

| rung | bin | lo | hi | n | mean_p | freq |
|---|---|---|---|---|---|---|
| GBM | 0 | 0.0000 | 0.1000 | 70 | 0.0869 | 0.0857 |
| GBM | 1 | 0.1000 | 0.2000 | 12404 | 0.1647 | 0.0927 |
| GBM | 2 | 0.2000 | 0.3000 | 1240 | 0.2302 | 0.1266 |
| GBM | 3 | 0.3000 | 0.4000 | 105 | 0.3250 | 0.1619 |
| GBM | 4 | 0.4000 | 0.5000 | 3 | 0.4159 | 0.0000 |
| GBM | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| GBM | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| GBM | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| GBM | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| GBM | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| GBM+cal | 0 | 0.0000 | 0.1000 | 1187 | 0.0912 | 0.0623 |
| GBM+cal | 1 | 0.1000 | 0.2000 | 12265 | 0.1284 | 0.0985 |
| GBM+cal | 2 | 0.2000 | 0.3000 | 324 | 0.2454 | 0.1265 |
| GBM+cal | 3 | 0.3000 | 0.4000 | 43 | 0.3353 | 0.1628 |
| GBM+cal | 4 | 0.4000 | 0.5000 | 3 | 0.4281 | 0.0000 |
| GBM+cal | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| GBM+cal | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| GBM+cal | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| GBM+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| GBM+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P0 | 0 | 0.0000 | 0.1000 | 1440 | 0.0819 | 0.0896 |
| P0 | 1 | 0.1000 | 0.2000 | 11632 | 0.1208 | 0.0943 |
| P0 | 2 | 0.2000 | 0.3000 | 750 | 0.2093 | 0.1387 |
| P0 | 3 | 0.3000 | 0.4000 | 0 | n/a | n/a |
| P0 | 4 | 0.4000 | 0.5000 | 0 | n/a | n/a |
| P0 | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| P0 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P0 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P0 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P0 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P1 | 0 | 0.0000 | 0.1000 | 6631 | 0.0823 | 0.0896 |
| P1 | 1 | 0.1000 | 0.2000 | 7191 | 0.1301 | 0.1024 |
| P1 | 2 | 0.2000 | 0.3000 | 0 | n/a | n/a |
| P1 | 3 | 0.3000 | 0.4000 | 0 | n/a | n/a |
| P1 | 4 | 0.4000 | 0.5000 | 0 | n/a | n/a |
| P1 | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| P1 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P1 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P1 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P1 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| P2 | 0 | 0.0000 | 0.1000 | 6633 | 0.0796 | 0.0894 |
| P2 | 1 | 0.1000 | 0.2000 | 7188 | 0.1289 | 0.1025 |
| P2 | 2 | 0.2000 | 0.3000 | 1 | 0.2511 | 0.0000 |
| P2 | 3 | 0.3000 | 0.4000 | 0 | n/a | n/a |
| P2 | 4 | 0.4000 | 0.5000 | 0 | n/a | n/a |
| P2 | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| P2 | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| P2 | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| P2 | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| P2 | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| local_eb | 0 | 0.0000 | 0.1000 | 7006 | 0.0699 | 0.0889 |
| local_eb | 1 | 0.1000 | 0.2000 | 6588 | 0.1371 | 0.1037 |
| local_eb | 2 | 0.2000 | 0.3000 | 228 | 0.2202 | 0.1053 |
| local_eb | 3 | 0.3000 | 0.4000 | 0 | n/a | n/a |
| local_eb | 4 | 0.4000 | 0.5000 | 0 | n/a | n/a |
| local_eb | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| local_eb | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| local_eb | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| local_eb | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| local_eb | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| local_eb+cal | 0 | 0.0000 | 0.1000 | 795 | 0.0899 | 0.0654 |
| local_eb+cal | 1 | 0.1000 | 0.2000 | 12584 | 0.1225 | 0.0965 |
| local_eb+cal | 2 | 0.2000 | 0.3000 | 443 | 0.2200 | 0.1445 |
| local_eb+cal | 3 | 0.3000 | 0.4000 | 0 | n/a | n/a |
| local_eb+cal | 4 | 0.4000 | 0.5000 | 0 | n/a | n/a |
| local_eb+cal | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| local_eb+cal | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| local_eb+cal | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| local_eb+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| local_eb+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| text_lr | 0 | 0.0000 | 0.1000 | 6491 | 0.0742 | 0.0846 |
| text_lr | 1 | 0.1000 | 0.2000 | 6238 | 0.1345 | 0.0963 |
| text_lr | 2 | 0.2000 | 0.3000 | 903 | 0.2360 | 0.1595 |
| text_lr | 3 | 0.3000 | 0.4000 | 162 | 0.3364 | 0.1975 |
| text_lr | 4 | 0.4000 | 0.5000 | 26 | 0.4326 | 0.1538 |
| text_lr | 5 | 0.5000 | 0.6000 | 2 | 0.5284 | 0.0000 |
| text_lr | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| text_lr | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| text_lr | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| text_lr | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |
| text_lr+cal | 0 | 0.0000 | 0.1000 | 2872 | 0.0882 | 0.0735 |
| text_lr+cal | 1 | 0.1000 | 0.2000 | 10378 | 0.1295 | 0.0989 |
| text_lr+cal | 2 | 0.2000 | 0.3000 | 561 | 0.2252 | 0.1658 |
| text_lr+cal | 3 | 0.3000 | 0.4000 | 11 | 0.3164 | 0.0000 |
| text_lr+cal | 4 | 0.4000 | 0.5000 | 0 | n/a | n/a |
| text_lr+cal | 5 | 0.5000 | 0.6000 | 0 | n/a | n/a |
| text_lr+cal | 6 | 0.6000 | 0.7000 | 0 | n/a | n/a |
| text_lr+cal | 7 | 0.7000 | 0.8000 | 0 | n/a | n/a |
| text_lr+cal | 8 | 0.8000 | 0.9000 | 0 | n/a | n/a |
| text_lr+cal | 9 | 0.9000 | 1.0000 | 0 | n/a | n/a |

## Split-half check of the prior

P1 fit on odd tests and on even tests; the gap in the cell mean and spread.

| cell | mu_odd | mu_even | mu_gap | tau_odd | tau_even | tau_gap | n_odd | n_even |
|---|---|---|---|---|---|---|---|---|
| both | -0.0902 | -0.0979 | 0.0077 | 0.3126 | 0.3708 | 0.0582 | 221 | 199 |
| headline_only | -0.0727 | -0.0545 | 0.0182 | 0.2808 | 0.2678 | 0.0129 | 4105 | 4151 |
| image_only | -0.0576 | -0.0562 | 0.0014 | 0.2479 | 0.2564 | 0.0085 | 2514 | 2490 |

## Decision value

Reported separately from calibration and never combined with it. Each origin picks K tests (10, 25 and 50 percent of the period's tests, rounded, at least one) at random, by p_win, or by an oracle that knows y. Captured is the lift won in the units of y, the fraction is of the period's total positive observed lift, and regret is the oracle's capture minus the policy's. Random order captures K over n of the total by linearity, so it is exact, not a draw. A rung whose p_win is constant within a cell chooses by cell and then at random; its capture differs from random order only through between-cell differences. Intervals resample whole tests within each origin. The adjusted bounds are Bonferroni bounds for the family of rungs compared with random order in the pooled rows (family_size, the decision-value call of docs/method.md). diff_matched is the difference from random order matched to the arm-count composition of the chosen set, the baseline a rung must beat (the number of contrasts is known before launch).

| origin | policy | rung | budget | K | n_tests | total | captured | captured_fraction | captured_fraction_lo | captured_fraction_hi | captured_fraction_adjusted_lo | captured_fraction_adjusted_hi | regret | regret_lo | regret_hi | regret_adjusted_lo | regret_adjusted_hi | random_fraction | diff_random | diff_random_lo | diff_random_hi | diff_random_adjusted_lo | diff_random_adjusted_hi | matched_fraction | diff_matched | diff_matched_lo | diff_matched_hi | diff_matched_adjusted_lo | diff_matched_adjusted_hi | family_size | constant_within_cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013-04-01T00:00:00+00:00 | random | all | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 294 | 1175 | 242.1116 | 60.5794 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 0.2502 | 148.7122 | 137.0697 | 159.7959 | 131.6581 | 165.7664 | 0.2502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 294 | 1175 | 242.1116 | 59.8698 | 0.2473 | 0.2128 | 0.2877 | 0.1935 | 0.3011 | 149.4218 | 132.8550 | 164.5304 | 125.5119 | 173.3317 | 0.2502 | -0.0029 | -0.0374 | 0.0375 | -0.0567 | 0.0509 | 0.2502 | -0.0029 | -0.0374 | 0.0375 | -0.0567 | 0.0509 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 294 | 1175 | 242.1116 | 47.2829 | 0.1953 | 0.1679 | 0.2246 | 0.1536 | 0.2370 | 162.0088 | 146.3685 | 176.7263 | 138.9818 | 185.0358 | 0.2502 | -0.0549 | -0.0823 | -0.0256 | -0.0966 | -0.0133 | 0.2502 | -0.0549 | -0.0823 | -0.0256 | -0.0966 | -0.0133 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 294 | 1175 | 242.1116 | 64.8396 | 0.2678 | 0.2504 | 0.2835 | 0.2445 | 0.2911 | 144.4520 | 132.8406 | 155.6104 | 127.2327 | 161.6714 | 0.2502 | 0.0176 | 0.0002 | 0.0333 | -0.0057 | 0.0409 | 0.2502 | 0.0176 | 0.0002 | 0.0333 | -0.0057 | 0.0409 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 294 | 1175 | 242.1116 | 76.0953 | 0.3143 | 0.2733 | 0.3558 | 0.2544 | 0.3742 | 133.1963 | 118.3856 | 147.7045 | 111.8145 | 154.5782 | 0.2502 | 0.0641 | 0.0231 | 0.1056 | 0.0041 | 0.1240 | 0.2502 | 0.0641 | 0.0231 | 0.1056 | 0.0041 | 0.1240 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 294 | 1175 | 242.1116 | 51.8758 | 0.2143 | 0.1861 | 0.2433 | 0.1712 | 0.2573 | 157.4158 | 142.1682 | 171.9375 | 134.7779 | 180.0537 | 0.2502 | -0.0359 | -0.0642 | -0.0070 | -0.0790 | 0.0071 | 0.2502 | -0.0359 | -0.0642 | -0.0070 | -0.0790 | 0.0071 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 294 | 1175 | 242.1116 | 70.9960 | 0.2932 | 0.2556 | 0.3346 | 0.2349 | 0.3515 | 138.2957 | 123.4644 | 152.3167 | 116.7162 | 159.8751 | 0.2502 | 0.0430 | 0.0054 | 0.0844 | -0.0153 | 0.1013 | 0.2502 | 0.0430 | 0.0054 | 0.0844 | -0.0153 | 0.1013 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 294 | 1175 | 242.1116 | 209.2916 | 0.8644 | 0.8413 | 0.8880 | 0.8309 | 0.8980 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2502 | 0.6142 | 0.5911 | 0.6378 | 0.5807 | 0.6478 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random | all | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 118 | 1175 | 242.1116 | 24.3142 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 0.1004 | 107.5245 | 96.6890 | 117.6098 | 92.6537 | 122.3952 | 0.1004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 118 | 1175 | 242.1116 | 23.8027 | 0.0983 | 0.0746 | 0.1211 | 0.0632 | 0.1334 | 108.0360 | 95.0724 | 120.7604 | 89.1539 | 126.9181 | 0.1004 | -0.0021 | -0.0259 | 0.0206 | -0.0372 | 0.0330 | 0.1004 | -0.0021 | -0.0259 | 0.0206 | -0.0372 | 0.0330 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 118 | 1175 | 242.1116 | 18.9775 | 0.0784 | 0.0673 | 0.0900 | 0.0618 | 0.0950 | 112.8612 | 100.7377 | 123.6813 | 95.7229 | 129.9995 | 0.1004 | -0.0220 | -0.0331 | -0.0104 | -0.0387 | -0.0054 | 0.1004 | -0.0220 | -0.0331 | -0.0104 | -0.0387 | -0.0054 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 118 | 1175 | 242.1116 | 26.0241 | 0.1075 | 0.1010 | 0.1136 | 0.0982 | 0.1168 | 105.8146 | 94.9899 | 115.5974 | 91.1021 | 120.5271 | 0.1004 | 0.0071 | 0.0005 | 0.0131 | -0.0022 | 0.0163 | 0.1004 | 0.0071 | 0.0005 | 0.0131 | -0.0022 | 0.0163 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 118 | 1175 | 242.1116 | 25.7369 | 0.1063 | 0.0854 | 0.1353 | 0.0711 | 0.1415 | 106.1018 | 93.0290 | 117.2192 | 88.3574 | 123.8462 | 0.1004 | 0.0059 | -0.0150 | 0.0349 | -0.0293 | 0.0410 | 0.1004 | 0.0059 | -0.0150 | 0.0349 | -0.0293 | 0.0410 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 118 | 1175 | 242.1116 | 23.5705 | 0.0974 | 0.0763 | 0.1181 | 0.0672 | 0.1275 | 108.2682 | 97.0269 | 120.0588 | 91.3059 | 125.2305 | 0.1004 | -0.0031 | -0.0241 | 0.0177 | -0.0332 | 0.0271 | 0.1004 | -0.0031 | -0.0241 | 0.0177 | -0.0332 | 0.0271 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 118 | 1175 | 242.1116 | 32.4893 | 0.1342 | 0.1076 | 0.1637 | 0.0929 | 0.1755 | 99.3494 | 87.9745 | 110.9615 | 81.6325 | 117.0662 | 0.1004 | 0.0338 | 0.0072 | 0.0633 | -0.0075 | 0.0750 | 0.1004 | 0.0338 | 0.0072 | 0.0633 | -0.0075 | 0.0750 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 118 | 1175 | 242.1116 | 131.8387 | 0.5445 | 0.5168 | 0.5748 | 0.5046 | 0.5845 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1004 | 0.4441 | 0.4164 | 0.4744 | 0.4042 | 0.4840 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random | all | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 588 | 1175 | 242.1116 | 121.1588 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 0.5004 | 120.9528 | 110.1211 | 131.7459 | 105.0338 | 136.8718 | 0.5004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2013-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 588 | 1175 | 242.1116 | 117.4318 | 0.4850 | 0.4395 | 0.5272 | 0.4195 | 0.5506 | 124.6798 | 110.7325 | 140.3810 | 101.9968 | 147.3629 | 0.5004 | -0.0154 | -0.0609 | 0.0267 | -0.0809 | 0.0501 | 0.5004 | -0.0154 | -0.0609 | 0.0267 | -0.0809 | 0.0501 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 588 | 1175 | 242.1116 | 112.6529 | 0.4653 | 0.4359 | 0.4978 | 0.4185 | 0.5121 | 129.4587 | 116.2719 | 143.1818 | 108.9948 | 149.9225 | 0.5004 | -0.0351 | -0.0645 | -0.0026 | -0.0819 | 0.0117 | 0.5004 | -0.0351 | -0.0645 | -0.0026 | -0.0819 | 0.0117 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 588 | 1175 | 242.1116 | 129.6792 | 0.5356 | 0.5031 | 0.5651 | 0.4887 | 0.5825 | 112.4323 | 100.1852 | 125.2976 | 93.8153 | 131.0494 | 0.5004 | 0.0352 | 0.0026 | 0.0646 | -0.0117 | 0.0821 | 0.5004 | 0.0352 | 0.0026 | 0.0646 | -0.0117 | 0.0821 | 6 | yes |
| 2013-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 588 | 1175 | 242.1116 | 135.5940 | 0.5600 | 0.5173 | 0.6028 | 0.4962 | 0.6239 | 106.5176 | 91.6242 | 121.9407 | 85.2633 | 127.7719 | 0.5004 | 0.0596 | 0.0168 | 0.1023 | -0.0042 | 0.1234 | 0.5004 | 0.0596 | 0.0168 | 0.1023 | -0.0042 | 0.1234 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 588 | 1175 | 242.1116 | 112.5171 | 0.4647 | 0.4216 | 0.5185 | 0.3956 | 0.5339 | 129.5945 | 112.6805 | 145.9116 | 104.6519 | 154.5370 | 0.5004 | -0.0357 | -0.0788 | 0.0180 | -0.1048 | 0.0335 | 0.5004 | -0.0357 | -0.0788 | 0.0180 | -0.1048 | 0.0335 | 6 | no |
| 2013-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 588 | 1175 | 242.1116 | 135.2901 | 0.5588 | 0.5191 | 0.6049 | 0.4947 | 0.6229 | 106.8215 | 92.1627 | 120.4798 | 85.9247 | 127.7183 | 0.5004 | 0.0584 | 0.0187 | 0.1044 | -0.0058 | 0.1225 | 0.5004 | 0.0584 | 0.0187 | 0.1044 | -0.0058 | 0.1225 | 6 | no |
| 2013-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 588 | 1175 | 242.1116 | 242.1116 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5004 | 0.4996 | 0.4996 | 0.4996 | 0.4996 | 0.4996 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.2500 | 409 | 1636 | 374.6958 | 93.6739 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 234.4327 | 219.9381 | 250.0377 | 211.6494 | 257.2161 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 409 | 1636 | 374.6958 | 104.1462 | 0.2779 | 0.2504 | 0.3074 | 0.2363 | 0.3196 | 223.9605 | 206.3313 | 241.9922 | 197.1164 | 250.8045 | 0.2500 | 0.0279 | 0.0004 | 0.0574 | -0.0137 | 0.0696 | 0.2500 | 0.0279 | 0.0004 | 0.0574 | -0.0137 | 0.0696 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 409 | 1636 | 374.6958 | 85.6650 | 0.2286 | 0.2133 | 0.2443 | 0.2057 | 0.2515 | 242.4417 | 224.8146 | 260.5010 | 216.6529 | 268.2305 | 0.2500 | -0.0214 | -0.0367 | -0.0057 | -0.0443 | 0.0015 | 0.2500 | -0.0214 | -0.0367 | -0.0057 | -0.0443 | 0.0015 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 409 | 1636 | 374.6958 | 85.3546 | 0.2278 | 0.2104 | 0.2437 | 0.2035 | 0.2521 | 242.7521 | 225.6102 | 260.3028 | 216.9694 | 268.5347 | 0.2500 | -0.0222 | -0.0396 | -0.0063 | -0.0465 | 0.0021 | 0.2500 | -0.0222 | -0.0396 | -0.0063 | -0.0465 | 0.0021 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 409 | 1636 | 374.6958 | 99.9181 | 0.2667 | 0.2326 | 0.3013 | 0.2173 | 0.3160 | 228.1886 | 209.6022 | 248.8654 | 199.3468 | 257.0304 | 0.2500 | 0.0167 | -0.0174 | 0.0513 | -0.0327 | 0.0660 | 0.2500 | 0.0167 | -0.0174 | 0.0513 | -0.0327 | 0.0660 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 409 | 1636 | 374.6958 | 116.9673 | 0.3122 | 0.2742 | 0.3433 | 0.2625 | 0.3618 | 211.1394 | 195.1710 | 229.6592 | 185.6255 | 236.6533 | 0.2500 | 0.0622 | 0.0242 | 0.0933 | 0.0125 | 0.1118 | 0.2500 | 0.0622 | 0.0242 | 0.0933 | 0.0125 | 0.1118 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 409 | 1636 | 374.6958 | 107.0318 | 0.2856 | 0.2522 | 0.3201 | 0.2369 | 0.3344 | 221.0749 | 202.5115 | 240.1204 | 192.9524 | 249.1973 | 0.2500 | 0.0356 | 0.0022 | 0.0701 | -0.0131 | 0.0844 | 0.2500 | 0.0356 | 0.0022 | 0.0701 | -0.0131 | 0.0844 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.2500 | 409 | 1636 | 374.6958 | 328.1067 | 0.8757 | 0.8597 | 0.8914 | 0.8522 | 0.8991 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.6257 | 0.6097 | 0.6414 | 0.6022 | 0.6491 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.1000 | 164 | 1636 | 374.6958 | 37.5612 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 0.1002 | 169.5417 | 157.3630 | 182.2835 | 151.2407 | 187.8427 | 0.1002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 164 | 1636 | 374.6958 | 42.2781 | 0.1128 | 0.0924 | 0.1385 | 0.0781 | 0.1476 | 164.8247 | 149.7862 | 178.7399 | 143.7478 | 185.9016 | 0.1002 | 0.0126 | -0.0078 | 0.0383 | -0.0221 | 0.0473 | 0.1002 | 0.0126 | -0.0078 | 0.0383 | -0.0221 | 0.0473 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 164 | 1636 | 374.6958 | 34.5357 | 0.0922 | 0.0836 | 0.1009 | 0.0795 | 0.1048 | 172.5672 | 158.8411 | 185.4064 | 152.6960 | 192.4383 | 0.1002 | -0.0081 | -0.0167 | 0.0007 | -0.0207 | 0.0046 | 0.1002 | -0.0081 | -0.0167 | 0.0007 | -0.0207 | 0.0046 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 164 | 1636 | 374.6958 | 34.2253 | 0.0913 | 0.0849 | 0.0978 | 0.0818 | 0.1009 | 172.8775 | 159.8398 | 185.8807 | 153.7020 | 192.0531 | 0.1002 | -0.0089 | -0.0154 | -0.0024 | -0.0184 | 0.0006 | 0.1002 | -0.0089 | -0.0154 | -0.0024 | -0.0184 | 0.0006 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 164 | 1636 | 374.6958 | 42.8934 | 0.1145 | 0.0872 | 0.1413 | 0.0757 | 0.1533 | 164.2095 | 149.8447 | 179.4378 | 142.6970 | 185.7219 | 0.1002 | 0.0142 | -0.0130 | 0.0411 | -0.0246 | 0.0530 | 0.1002 | 0.0142 | -0.0130 | 0.0411 | -0.0246 | 0.0530 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 164 | 1636 | 374.6958 | 42.5697 | 0.1136 | 0.0872 | 0.1415 | 0.0748 | 0.1524 | 164.5331 | 149.0908 | 177.8516 | 143.8836 | 185.1827 | 0.1002 | 0.0134 | -0.0131 | 0.0412 | -0.0254 | 0.0522 | 0.1002 | 0.0134 | -0.0131 | 0.0412 | -0.0254 | 0.0522 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 164 | 1636 | 374.6958 | 49.0158 | 0.1308 | 0.1094 | 0.1579 | 0.0948 | 0.1669 | 158.0871 | 142.5001 | 173.2866 | 135.1185 | 181.0557 | 0.1002 | 0.0306 | 0.0092 | 0.0577 | -0.0055 | 0.0666 | 0.1002 | 0.0306 | 0.0092 | 0.0577 | -0.0055 | 0.0666 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.1000 | 164 | 1636 | 374.6958 | 207.1029 | 0.5527 | 0.5299 | 0.5783 | 0.5188 | 0.5867 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1002 | 0.4525 | 0.4296 | 0.4780 | 0.4185 | 0.4864 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random | all | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | arm_count | all | 0.5000 | 818 | 1636 | 374.6958 | 187.3479 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 187.3479 | 173.7872 | 201.2737 | 167.3117 | 207.3841 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-01-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 818 | 1636 | 374.6958 | 204.2336 | 0.5451 | 0.5103 | 0.5781 | 0.4953 | 0.5948 | 170.4622 | 152.7675 | 188.0214 | 144.4500 | 196.4744 | 0.5000 | 0.0451 | 0.0103 | 0.0781 | -0.0047 | 0.0948 | 0.5000 | 0.0451 | 0.0103 | 0.0781 | -0.0047 | 0.0948 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 818 | 1636 | 374.6958 | 171.0196 | 0.4564 | 0.4229 | 0.4894 | 0.4085 | 0.5044 | 203.6762 | 184.4018 | 225.0247 | 173.7861 | 233.5663 | 0.5000 | -0.0436 | -0.0771 | -0.0106 | -0.0915 | 0.0044 | 0.5000 | -0.0436 | -0.0771 | -0.0106 | -0.0915 | 0.0044 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 818 | 1636 | 374.6958 | 170.7092 | 0.4556 | 0.4212 | 0.4889 | 0.4063 | 0.5049 | 203.9866 | 184.7402 | 225.8636 | 173.8902 | 234.0829 | 0.5000 | -0.0444 | -0.0788 | -0.0111 | -0.0937 | 0.0049 | 0.5000 | -0.0444 | -0.0788 | -0.0111 | -0.0937 | 0.0049 | 6 | yes |
| 2014-01-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 818 | 1636 | 374.6958 | 174.8396 | 0.4666 | 0.4284 | 0.5008 | 0.4118 | 0.5214 | 199.8561 | 180.7319 | 222.5852 | 168.2059 | 231.5064 | 0.5000 | -0.0334 | -0.0716 | 0.0008 | -0.0882 | 0.0214 | 0.5000 | -0.0334 | -0.0716 | 0.0008 | -0.0882 | 0.0214 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 818 | 1636 | 374.6958 | 197.9089 | 0.5282 | 0.4965 | 0.5698 | 0.4726 | 0.5838 | 176.7869 | 155.5549 | 194.9178 | 147.5959 | 205.9778 | 0.5000 | 0.0282 | -0.0035 | 0.0698 | -0.0274 | 0.0838 | 0.5000 | 0.0282 | -0.0035 | 0.0698 | -0.0274 | 0.0838 | 6 | no |
| 2014-01-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 818 | 1636 | 374.6958 | 205.4135 | 0.5482 | 0.5082 | 0.5826 | 0.4934 | 0.6031 | 169.2822 | 152.0643 | 190.3275 | 141.1263 | 197.4382 | 0.5000 | 0.0482 | 0.0082 | 0.0826 | -0.0066 | 0.1031 | 0.5000 | 0.0482 | 0.0082 | 0.0826 | -0.0066 | 0.1031 | 6 | no |
| 2014-01-01T00:00:00+00:00 | oracle | all | 0.5000 | 818 | 1636 | 374.6958 | 374.6958 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 593 | 2372 | 522.7343 | 130.6836 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 302.7496 | 286.9237 | 319.6851 | 279.0821 | 326.4171 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 593 | 2372 | 522.7343 | 149.2966 | 0.2856 | 0.2608 | 0.3130 | 0.2480 | 0.3232 | 284.1365 | 265.4374 | 302.7392 | 255.9121 | 312.3610 | 0.2500 | 0.0356 | 0.0108 | 0.0630 | -0.0020 | 0.0732 | 0.2500 | 0.0356 | 0.0108 | 0.0630 | -0.0020 | 0.0732 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 593 | 2372 | 522.7343 | 127.6350 | 0.2442 | 0.2273 | 0.2608 | 0.2193 | 0.2690 | 305.7982 | 287.5720 | 327.7289 | 276.7538 | 334.8425 | 0.2500 | -0.0058 | -0.0227 | 0.0108 | -0.0307 | 0.0190 | 0.2500 | -0.0058 | -0.0227 | 0.0108 | -0.0307 | 0.0190 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 593 | 2372 | 522.7343 | 127.6350 | 0.2442 | 0.2273 | 0.2608 | 0.2193 | 0.2690 | 305.7982 | 287.5720 | 327.7289 | 276.7538 | 334.8425 | 0.2500 | -0.0058 | -0.0227 | 0.0108 | -0.0307 | 0.0190 | 0.2500 | -0.0058 | -0.0227 | 0.0108 | -0.0307 | 0.0190 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 593 | 2372 | 522.7343 | 130.1776 | 0.2490 | 0.2260 | 0.2726 | 0.2143 | 0.2838 | 303.2556 | 283.1381 | 325.6602 | 271.8313 | 334.6798 | 0.2500 | -0.0010 | -0.0240 | 0.0226 | -0.0357 | 0.0338 | 0.2500 | -0.0010 | -0.0240 | 0.0226 | -0.0357 | 0.0338 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 593 | 2372 | 522.7343 | 133.2423 | 0.2549 | 0.2320 | 0.2850 | 0.2171 | 0.2927 | 300.1909 | 278.2968 | 320.8571 | 269.1736 | 331.2082 | 0.2500 | 0.0049 | -0.0180 | 0.0350 | -0.0329 | 0.0427 | 0.2500 | 0.0049 | -0.0180 | 0.0350 | -0.0329 | 0.0427 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 593 | 2372 | 522.7343 | 156.3374 | 0.2991 | 0.2748 | 0.3290 | 0.2604 | 0.3378 | 277.0958 | 258.5884 | 297.4166 | 249.1396 | 305.0519 | 0.2500 | 0.0491 | 0.0248 | 0.0790 | 0.0104 | 0.0878 | 0.2500 | 0.0491 | 0.0248 | 0.0790 | 0.0104 | 0.0878 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 593 | 2372 | 522.7343 | 433.4331 | 0.8292 | 0.8146 | 0.8434 | 0.8082 | 0.8502 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.5792 | 0.5646 | 0.5934 | 0.5582 | 0.6002 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 237 | 2372 | 522.7343 | 52.2294 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 0.0999 | 214.0609 | 198.8928 | 229.1773 | 192.8138 | 235.3080 | 0.0999 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 237 | 2372 | 522.7343 | 55.7471 | 0.1066 | 0.0888 | 0.1268 | 0.0793 | 0.1340 | 210.5431 | 192.3931 | 227.8331 | 186.0729 | 235.0134 | 0.0999 | 0.0067 | -0.0111 | 0.0269 | -0.0206 | 0.0340 | 0.0999 | 0.0067 | -0.0111 | 0.0269 | -0.0206 | 0.0340 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 237 | 2372 | 522.7343 | 49.4796 | 0.0947 | 0.0862 | 0.1046 | 0.0809 | 0.1084 | 216.8106 | 199.0579 | 232.4992 | 193.3821 | 240.2391 | 0.0999 | -0.0053 | -0.0137 | 0.0047 | -0.0190 | 0.0085 | 0.0999 | -0.0053 | -0.0137 | 0.0047 | -0.0190 | 0.0085 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 237 | 2372 | 522.7343 | 49.4796 | 0.0947 | 0.0862 | 0.1046 | 0.0809 | 0.1084 | 216.8106 | 199.0579 | 232.4992 | 193.3821 | 240.2391 | 0.0999 | -0.0053 | -0.0137 | 0.0047 | -0.0190 | 0.0085 | 0.0999 | -0.0053 | -0.0137 | 0.0047 | -0.0190 | 0.0085 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 237 | 2372 | 522.7343 | 54.8886 | 0.1050 | 0.0857 | 0.1193 | 0.0797 | 0.1303 | 211.4016 | 196.7461 | 228.7865 | 186.8374 | 235.9659 | 0.0999 | 0.0051 | -0.0142 | 0.0194 | -0.0202 | 0.0303 | 0.0999 | 0.0051 | -0.0142 | 0.0194 | -0.0202 | 0.0303 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 237 | 2372 | 522.7343 | 61.9157 | 0.1184 | 0.0973 | 0.1390 | 0.0878 | 0.1490 | 204.3745 | 188.2358 | 221.9828 | 180.2033 | 228.5458 | 0.0999 | 0.0185 | -0.0026 | 0.0391 | -0.0121 | 0.0491 | 0.0999 | 0.0185 | -0.0026 | 0.0391 | -0.0121 | 0.0491 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 237 | 2372 | 522.7343 | 63.8119 | 0.1221 | 0.0999 | 0.1419 | 0.0917 | 0.1525 | 202.4783 | 185.9009 | 219.6238 | 177.7531 | 227.2035 | 0.0999 | 0.0222 | -0.0001 | 0.0420 | -0.0083 | 0.0526 | 0.0999 | 0.0222 | -0.0001 | 0.0420 | -0.0083 | 0.0526 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 237 | 2372 | 522.7343 | 266.2902 | 0.5094 | 0.4918 | 0.5284 | 0.4830 | 0.5358 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0999 | 0.4095 | 0.3919 | 0.4285 | 0.3831 | 0.4359 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random | all | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 1186 | 2372 | 522.7343 | 261.3671 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 261.3599 | 245.5579 | 276.2029 | 238.6903 | 284.0296 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 1186 | 2372 | 522.7343 | 278.5246 | 0.5328 | 0.5061 | 0.5610 | 0.4941 | 0.5715 | 244.2024 | 223.8910 | 263.6547 | 216.3464 | 272.0584 | 0.5000 | 0.0328 | 0.0061 | 0.0610 | -0.0059 | 0.0715 | 0.5000 | 0.0328 | 0.0061 | 0.0610 | -0.0059 | 0.0715 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 1186 | 2372 | 522.7343 | 258.4592 | 0.4944 | 0.4700 | 0.5193 | 0.4592 | 0.5296 | 264.2678 | 243.2334 | 284.8099 | 233.4430 | 295.0926 | 0.5000 | -0.0056 | -0.0300 | 0.0193 | -0.0408 | 0.0296 | 0.5000 | -0.0056 | -0.0300 | 0.0193 | -0.0408 | 0.0296 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 1186 | 2372 | 522.7343 | 258.4592 | 0.4944 | 0.4700 | 0.5193 | 0.4592 | 0.5296 | 264.2678 | 243.2334 | 284.8099 | 233.4430 | 295.0926 | 0.5000 | -0.0056 | -0.0300 | 0.0193 | -0.0408 | 0.0296 | 0.5000 | -0.0056 | -0.0300 | 0.0193 | -0.0408 | 0.0296 | 6 | yes |
| 2014-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 1186 | 2372 | 522.7343 | 258.4592 | 0.4944 | 0.4700 | 0.5193 | 0.4592 | 0.5296 | 264.2678 | 243.2334 | 284.8099 | 233.4430 | 295.0926 | 0.5000 | -0.0056 | -0.0300 | 0.0193 | -0.0408 | 0.0296 | 0.5000 | -0.0056 | -0.0300 | 0.0193 | -0.0408 | 0.0296 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 1186 | 2372 | 522.7343 | 272.8560 | 0.5220 | 0.4941 | 0.5524 | 0.4788 | 0.5652 | 249.8710 | 227.7930 | 270.2863 | 218.2336 | 281.5085 | 0.5000 | 0.0220 | -0.0059 | 0.0524 | -0.0212 | 0.0652 | 0.5000 | 0.0220 | -0.0059 | 0.0524 | -0.0212 | 0.0652 | 6 | no |
| 2014-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 1186 | 2372 | 522.7343 | 292.9074 | 0.5603 | 0.5328 | 0.5881 | 0.5188 | 0.6019 | 229.8196 | 209.9542 | 249.5514 | 200.8329 | 258.8063 | 0.5000 | 0.0603 | 0.0328 | 0.0881 | 0.0188 | 0.1019 | 0.5000 | 0.0603 | 0.0328 | 0.0881 | 0.0188 | 0.1019 | 6 | no |
| 2014-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 1186 | 2372 | 522.7343 | 522.7271 | 1.0000 | 0.9992 | 1.0000 | 0.9992 | 1.0008 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.4992 | 0.5000 | 0.4992 | 0.5008 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.2500 | 867 | 3468 | 429.6886 | 107.4222 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 272.3548 | 260.3036 | 284.2716 | 254.8406 | 289.8690 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 867 | 3468 | 429.6886 | 117.1783 | 0.2727 | 0.2501 | 0.2988 | 0.2375 | 0.3079 | 262.5987 | 247.1379 | 275.1157 | 241.7547 | 283.4426 | 0.2500 | 0.0227 | 0.0001 | 0.0488 | -0.0125 | 0.0579 | 0.2500 | 0.0227 | 0.0001 | 0.0488 | -0.0125 | 0.0579 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 867 | 3468 | 429.6886 | 111.7107 | 0.2600 | 0.2416 | 0.2771 | 0.2331 | 0.2869 | 268.0663 | 253.5725 | 281.1641 | 247.8483 | 288.2842 | 0.2500 | 0.0100 | -0.0084 | 0.0271 | -0.0169 | 0.0369 | 0.2500 | 0.0100 | -0.0084 | 0.0271 | -0.0169 | 0.0369 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 867 | 3468 | 429.6886 | 111.7107 | 0.2600 | 0.2416 | 0.2771 | 0.2331 | 0.2869 | 268.0663 | 253.5725 | 281.1641 | 247.8483 | 288.2842 | 0.2500 | 0.0100 | -0.0084 | 0.0271 | -0.0169 | 0.0369 | 0.2500 | 0.0100 | -0.0084 | 0.0271 | -0.0169 | 0.0369 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 867 | 3468 | 429.6886 | 111.7107 | 0.2600 | 0.2416 | 0.2771 | 0.2331 | 0.2869 | 268.0663 | 253.5725 | 281.1641 | 247.8483 | 288.2842 | 0.2500 | 0.0100 | -0.0084 | 0.0271 | -0.0169 | 0.0369 | 0.2500 | 0.0100 | -0.0084 | 0.0271 | -0.0169 | 0.0369 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 867 | 3468 | 429.6886 | 108.6451 | 0.2528 | 0.2283 | 0.2780 | 0.2167 | 0.2890 | 271.1318 | 254.2551 | 286.3258 | 247.2231 | 295.0406 | 0.2500 | 0.0028 | -0.0217 | 0.0280 | -0.0333 | 0.0390 | 0.2500 | 0.0028 | -0.0217 | 0.0280 | -0.0333 | 0.0390 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 867 | 3468 | 429.6886 | 125.7626 | 0.2927 | 0.2694 | 0.3182 | 0.2567 | 0.3287 | 254.0144 | 239.8255 | 268.6401 | 233.1048 | 274.9240 | 0.2500 | 0.0427 | 0.0194 | 0.0682 | 0.0067 | 0.0787 | 0.2500 | 0.0427 | 0.0194 | 0.0682 | 0.0067 | 0.0787 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.2500 | 867 | 3468 | 429.6886 | 379.7769 | 0.8838 | 0.8719 | 0.8953 | 0.8666 | 0.9011 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.6338 | 0.6219 | 0.6453 | 0.6166 | 0.6511 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.1000 | 347 | 3468 | 429.6886 | 42.9936 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 196.5530 | 185.5390 | 207.5595 | 180.5295 | 212.5766 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 347 | 3468 | 429.6886 | 45.9794 | 0.1070 | 0.0954 | 0.1249 | 0.0852 | 0.1288 | 193.5673 | 179.8892 | 205.8340 | 174.4532 | 212.6813 | 0.1001 | 0.0069 | -0.0046 | 0.0249 | -0.0148 | 0.0287 | 0.1001 | 0.0069 | -0.0046 | 0.0249 | -0.0148 | 0.0287 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 347 | 3468 | 429.6886 | 44.7100 | 0.1041 | 0.0973 | 0.1117 | 0.0933 | 0.1148 | 194.8366 | 183.5753 | 205.9438 | 178.9290 | 210.7443 | 0.1001 | 0.0040 | -0.0028 | 0.0117 | -0.0067 | 0.0147 | 0.1001 | 0.0040 | -0.0028 | 0.0117 | -0.0067 | 0.0147 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 347 | 3468 | 429.6886 | 44.7100 | 0.1041 | 0.0973 | 0.1117 | 0.0933 | 0.1148 | 194.8366 | 183.5753 | 205.9438 | 178.9290 | 210.7443 | 0.1001 | 0.0040 | -0.0028 | 0.0117 | -0.0067 | 0.0147 | 0.1001 | 0.0040 | -0.0028 | 0.0117 | -0.0067 | 0.0147 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 347 | 3468 | 429.6886 | 44.7100 | 0.1041 | 0.0973 | 0.1117 | 0.0933 | 0.1148 | 194.8366 | 183.5753 | 205.9438 | 178.9290 | 210.7443 | 0.1001 | 0.0040 | -0.0028 | 0.0117 | -0.0067 | 0.0147 | 0.1001 | 0.0040 | -0.0028 | 0.0117 | -0.0067 | 0.0147 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 347 | 3468 | 429.6886 | 43.2607 | 0.1007 | 0.0867 | 0.1228 | 0.0737 | 0.1277 | 196.2860 | 183.6257 | 206.9202 | 178.5247 | 214.0473 | 0.1001 | 0.0006 | -0.0133 | 0.0227 | -0.0264 | 0.0276 | 0.1001 | 0.0006 | -0.0133 | 0.0227 | -0.0264 | 0.0276 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 347 | 3468 | 429.6886 | 51.7864 | 0.1205 | 0.1024 | 0.1363 | 0.0964 | 0.1447 | 187.7603 | 175.1198 | 200.8121 | 169.5630 | 205.9576 | 0.1001 | 0.0205 | 0.0024 | 0.0362 | -0.0037 | 0.0446 | 0.1001 | 0.0205 | 0.0024 | 0.0362 | -0.0037 | 0.0446 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.1000 | 347 | 3468 | 429.6886 | 239.5467 | 0.5575 | 0.5409 | 0.5740 | 0.5341 | 0.5809 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1001 | 0.4574 | 0.4408 | 0.4739 | 0.4340 | 0.4808 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random | all | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | arm_count | all | 0.5000 | 1734 | 3468 | 429.6886 | 214.8443 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 214.8443 | 204.3910 | 226.6028 | 198.3750 | 231.3136 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-07-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 1734 | 3468 | 429.6886 | 227.6324 | 0.5298 | 0.5039 | 0.5560 | 0.4916 | 0.5679 | 202.0562 | 188.1760 | 220.2593 | 179.6838 | 224.4287 | 0.5000 | 0.0298 | 0.0039 | 0.0560 | -0.0084 | 0.0679 | 0.5000 | 0.0298 | 0.0039 | 0.0560 | -0.0084 | 0.0679 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 1734 | 3468 | 429.6886 | 218.8793 | 0.5094 | 0.4870 | 0.5280 | 0.4799 | 0.5389 | 210.8093 | 198.0004 | 225.7838 | 190.6981 | 230.9205 | 0.5000 | 0.0094 | -0.0130 | 0.0280 | -0.0201 | 0.0389 | 0.5000 | 0.0094 | -0.0130 | 0.0280 | -0.0201 | 0.0389 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 1734 | 3468 | 429.6886 | 218.8793 | 0.5094 | 0.4870 | 0.5280 | 0.4799 | 0.5389 | 210.8093 | 198.0004 | 225.7838 | 190.6981 | 230.9205 | 0.5000 | 0.0094 | -0.0130 | 0.0280 | -0.0201 | 0.0389 | 0.5000 | 0.0094 | -0.0130 | 0.0280 | -0.0201 | 0.0389 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 1734 | 3468 | 429.6886 | 218.8793 | 0.5094 | 0.4870 | 0.5280 | 0.4799 | 0.5389 | 210.8093 | 198.0004 | 225.7838 | 190.6981 | 230.9205 | 0.5000 | 0.0094 | -0.0130 | 0.0280 | -0.0201 | 0.0389 | 0.5000 | 0.0094 | -0.0130 | 0.0280 | -0.0201 | 0.0389 | 6 | yes |
| 2014-07-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 1734 | 3468 | 429.6886 | 212.5803 | 0.4947 | 0.4730 | 0.5224 | 0.4578 | 0.5317 | 217.1083 | 200.5639 | 233.6847 | 193.2857 | 240.9310 | 0.5000 | -0.0053 | -0.0270 | 0.0224 | -0.0422 | 0.0317 | 0.5000 | -0.0053 | -0.0270 | 0.0224 | -0.0422 | 0.0317 | 6 | no |
| 2014-07-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 1734 | 3468 | 429.6886 | 244.1544 | 0.5682 | 0.5419 | 0.5925 | 0.5303 | 0.6061 | 185.5343 | 172.4914 | 202.4331 | 164.1042 | 206.9643 | 0.5000 | 0.0682 | 0.0419 | 0.0925 | 0.0303 | 0.1061 | 0.5000 | 0.0682 | 0.0419 | 0.0925 | 0.0303 | 0.1061 | 6 | no |
| 2014-07-01T00:00:00+00:00 | oracle | all | 0.5000 | 1734 | 3468 | 429.6886 | 429.6886 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.2500 | 807 | 3229 | 426.0653 | 106.4833 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 0.2499 | 277.8624 | 263.2799 | 292.9979 | 256.6879 | 299.0370 | 0.2499 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 807 | 3229 | 426.0653 | 121.1147 | 0.2843 | 0.2626 | 0.3069 | 0.2525 | 0.3160 | 263.2311 | 246.3939 | 279.3449 | 238.8569 | 287.6053 | 0.2499 | 0.0343 | 0.0126 | 0.0569 | 0.0026 | 0.0661 | 0.2499 | 0.0343 | 0.0126 | 0.0569 | 0.0026 | 0.0661 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 807 | 3229 | 426.0653 | 110.3328 | 0.2590 | 0.2378 | 0.2783 | 0.2292 | 0.2887 | 274.0130 | 257.1996 | 291.2772 | 250.1471 | 297.8789 | 0.2499 | 0.0090 | -0.0121 | 0.0284 | -0.0208 | 0.0388 | 0.2499 | 0.0090 | -0.0121 | 0.0284 | -0.0208 | 0.0388 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 807 | 3229 | 426.0653 | 110.3328 | 0.2590 | 0.2378 | 0.2783 | 0.2292 | 0.2887 | 274.0130 | 257.1996 | 291.2772 | 250.1471 | 297.8789 | 0.2499 | 0.0090 | -0.0121 | 0.0284 | -0.0208 | 0.0388 | 0.2499 | 0.0090 | -0.0121 | 0.0284 | -0.0208 | 0.0388 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 807 | 3229 | 426.0653 | 110.9409 | 0.2604 | 0.2388 | 0.2785 | 0.2305 | 0.2903 | 273.4049 | 256.8343 | 289.7303 | 249.3753 | 297.4345 | 0.2499 | 0.0105 | -0.0111 | 0.0286 | -0.0194 | 0.0403 | 0.2499 | 0.0105 | -0.0111 | 0.0286 | -0.0194 | 0.0403 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 807 | 3229 | 426.0653 | 116.4023 | 0.2732 | 0.2466 | 0.3017 | 0.2336 | 0.3128 | 267.9434 | 250.8951 | 284.4012 | 243.7906 | 292.0963 | 0.2499 | 0.0233 | -0.0033 | 0.0517 | -0.0163 | 0.0629 | 0.2499 | 0.0233 | -0.0033 | 0.0517 | -0.0163 | 0.0629 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 807 | 3229 | 426.0653 | 124.1552 | 0.2914 | 0.2629 | 0.3187 | 0.2510 | 0.3318 | 260.1906 | 242.4751 | 279.6655 | 232.1404 | 288.2408 | 0.2499 | 0.0415 | 0.0129 | 0.0688 | 0.0010 | 0.0819 | 0.2499 | 0.0415 | 0.0129 | 0.0688 | 0.0010 | 0.0819 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.2500 | 807 | 3229 | 426.0653 | 384.3458 | 0.9021 | 0.8893 | 0.9145 | 0.8838 | 0.9204 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2499 | 0.6522 | 0.6394 | 0.6646 | 0.6339 | 0.6704 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.1000 | 323 | 3229 | 426.0653 | 42.6197 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 206.2630 | 192.4215 | 218.0559 | 187.1165 | 225.4094 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 323 | 3229 | 426.0653 | 55.8282 | 0.1310 | 0.1114 | 0.1514 | 0.1027 | 0.1593 | 193.0545 | 178.4262 | 207.9717 | 171.2724 | 214.8366 | 0.1000 | 0.0310 | 0.0114 | 0.0514 | 0.0027 | 0.0593 | 0.1000 | 0.0310 | 0.0114 | 0.0514 | 0.0027 | 0.0593 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 323 | 3229 | 426.0653 | 44.1605 | 0.1036 | 0.0968 | 0.1119 | 0.0926 | 0.1147 | 204.7222 | 189.7571 | 216.7850 | 185.5091 | 223.9353 | 0.1000 | 0.0036 | -0.0032 | 0.0118 | -0.0074 | 0.0146 | 0.1000 | 0.0036 | -0.0032 | 0.0118 | -0.0074 | 0.0146 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 323 | 3229 | 426.0653 | 44.1605 | 0.1036 | 0.0968 | 0.1119 | 0.0926 | 0.1147 | 204.7222 | 189.7571 | 216.7850 | 185.5091 | 223.9353 | 0.1000 | 0.0036 | -0.0032 | 0.0118 | -0.0074 | 0.0146 | 0.1000 | 0.0036 | -0.0032 | 0.0118 | -0.0074 | 0.0146 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 323 | 3229 | 426.0653 | 44.7686 | 0.1051 | 0.0978 | 0.1135 | 0.0933 | 0.1168 | 204.1141 | 189.3151 | 216.4680 | 184.6108 | 223.6175 | 0.1000 | 0.0050 | -0.0022 | 0.0135 | -0.0067 | 0.0168 | 0.1000 | 0.0050 | -0.0022 | 0.0135 | -0.0067 | 0.0168 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 323 | 3229 | 426.0653 | 40.2119 | 0.0944 | 0.0789 | 0.1117 | 0.0707 | 0.1181 | 208.6707 | 192.4224 | 223.4526 | 186.1347 | 231.2068 | 0.1000 | -0.0057 | -0.0212 | 0.0117 | -0.0293 | 0.0180 | 0.1000 | -0.0057 | -0.0212 | 0.0117 | -0.0293 | 0.0180 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 323 | 3229 | 426.0653 | 56.6141 | 0.1329 | 0.1128 | 0.1512 | 0.1035 | 0.1622 | 192.2686 | 176.3652 | 208.0002 | 169.5273 | 215.0098 | 0.1000 | 0.0328 | 0.0128 | 0.0512 | 0.0035 | 0.0622 | 0.1000 | 0.0328 | 0.0128 | 0.0512 | 0.0035 | 0.0622 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.1000 | 323 | 3229 | 426.0653 | 248.8827 | 0.5841 | 0.5669 | 0.6021 | 0.5587 | 0.6096 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 | 0.4841 | 0.4669 | 0.5021 | 0.4586 | 0.5096 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random | all | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | arm_count | all | 0.5000 | 1615 | 3229 | 426.0653 | 213.0986 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 0.5002 | 212.9667 | 201.2384 | 226.0195 | 194.7191 | 231.2143 | 0.5002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2014-10-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 1615 | 3229 | 426.0653 | 225.3364 | 0.5289 | 0.5113 | 0.5481 | 0.5017 | 0.5561 | 200.7289 | 187.1584 | 214.9075 | 180.0577 | 221.4001 | 0.5002 | 0.0287 | 0.0112 | 0.0479 | 0.0015 | 0.0559 | 0.5002 | 0.0287 | 0.0112 | 0.0479 | 0.0015 | 0.0559 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 1615 | 3229 | 426.0653 | 218.7130 | 0.5133 | 0.4907 | 0.5365 | 0.4803 | 0.5463 | 207.3523 | 193.4946 | 223.0732 | 185.6243 | 229.0804 | 0.5002 | 0.0132 | -0.0095 | 0.0363 | -0.0198 | 0.0462 | 0.5002 | 0.0132 | -0.0095 | 0.0363 | -0.0198 | 0.0462 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 1615 | 3229 | 426.0653 | 218.7130 | 0.5133 | 0.4907 | 0.5365 | 0.4803 | 0.5463 | 207.3523 | 193.4946 | 223.0732 | 185.6243 | 229.0804 | 0.5002 | 0.0132 | -0.0095 | 0.0363 | -0.0198 | 0.0462 | 0.5002 | 0.0132 | -0.0095 | 0.0363 | -0.0198 | 0.0462 | 6 | yes |
| 2014-10-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 1615 | 3229 | 426.0653 | 232.6074 | 0.5459 | 0.5171 | 0.5742 | 0.5054 | 0.5865 | 193.4580 | 177.8115 | 210.2675 | 170.0054 | 216.9106 | 0.5002 | 0.0458 | 0.0169 | 0.0741 | 0.0052 | 0.0864 | 0.5002 | 0.0458 | 0.0169 | 0.0741 | 0.0052 | 0.0864 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 1615 | 3229 | 426.0653 | 223.3953 | 0.5243 | 0.4947 | 0.5488 | 0.4830 | 0.5656 | 202.6700 | 187.5031 | 220.2793 | 178.3056 | 227.0345 | 0.5002 | 0.0242 | -0.0055 | 0.0487 | -0.0172 | 0.0655 | 0.5002 | 0.0242 | -0.0055 | 0.0487 | -0.0172 | 0.0655 | 6 | no |
| 2014-10-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 1615 | 3229 | 426.0653 | 227.8633 | 0.5348 | 0.5009 | 0.5611 | 0.4906 | 0.5790 | 198.2021 | 182.1888 | 216.9973 | 173.3916 | 223.0125 | 0.5002 | 0.0347 | 0.0007 | 0.0609 | -0.0095 | 0.0788 | 0.5002 | 0.0347 | 0.0007 | 0.0609 | -0.0095 | 0.0788 | 6 | no |
| 2014-10-01T00:00:00+00:00 | oracle | all | 0.5000 | 1615 | 3229 | 426.0653 | 426.0653 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5002 | 0.4998 | 0.4998 | 0.4998 | 0.4998 | 0.4998 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.2500 | 393 | 1570 | 238.9403 | 59.8112 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 0.2503 | 156.4829 | 145.7181 | 166.8784 | 141.0881 | 171.8777 | 0.2503 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 393 | 1570 | 238.9403 | 80.5035 | 0.3369 | 0.2970 | 0.3739 | 0.2794 | 0.3944 | 135.7906 | 123.5047 | 149.0411 | 117.7654 | 153.8158 | 0.2503 | 0.0866 | 0.0467 | 0.1236 | 0.0291 | 0.1441 | 0.2503 | 0.0866 | 0.0467 | 0.1236 | 0.0291 | 0.1441 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 393 | 1570 | 238.9403 | 58.2173 | 0.2436 | 0.2206 | 0.2694 | 0.2076 | 0.2797 | 158.0768 | 145.5010 | 170.2686 | 140.0481 | 176.1054 | 0.2503 | -0.0067 | -0.0297 | 0.0191 | -0.0427 | 0.0294 | 0.2503 | -0.0067 | -0.0297 | 0.0191 | -0.0427 | 0.0294 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 393 | 1570 | 238.9403 | 56.4386 | 0.2362 | 0.2129 | 0.2607 | 0.2013 | 0.2711 | 159.8555 | 147.0982 | 172.1454 | 141.6363 | 178.0747 | 0.2503 | -0.0141 | -0.0374 | 0.0104 | -0.0490 | 0.0208 | 0.2503 | -0.0141 | -0.0374 | 0.0104 | -0.0490 | 0.0208 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 393 | 1570 | 238.9403 | 63.2150 | 0.2646 | 0.2397 | 0.2910 | 0.2275 | 0.3017 | 153.0791 | 140.7307 | 164.6100 | 135.5541 | 170.6041 | 0.2503 | 0.0142 | -0.0106 | 0.0407 | -0.0229 | 0.0513 | 0.2503 | 0.0142 | -0.0106 | 0.0407 | -0.0229 | 0.0513 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 393 | 1570 | 238.9403 | 66.0739 | 0.2765 | 0.2438 | 0.3162 | 0.2234 | 0.3296 | 150.2202 | 137.5111 | 162.2127 | 131.2567 | 169.1837 | 0.2503 | 0.0262 | -0.0065 | 0.0659 | -0.0269 | 0.0793 | 0.2503 | 0.0262 | -0.0065 | 0.0659 | -0.0269 | 0.0793 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 393 | 1570 | 238.9403 | 74.8589 | 0.3133 | 0.2794 | 0.3483 | 0.2630 | 0.3636 | 141.4352 | 128.2879 | 154.2053 | 122.4608 | 160.4096 | 0.2503 | 0.0630 | 0.0291 | 0.0979 | 0.0127 | 0.1133 | 0.2503 | 0.0630 | 0.0291 | 0.0979 | 0.0127 | 0.1133 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.2500 | 393 | 1570 | 238.9403 | 216.2941 | 0.9052 | 0.8872 | 0.9218 | 0.8805 | 0.9299 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2503 | 0.6549 | 0.6369 | 0.6715 | 0.6302 | 0.6796 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.1000 | 157 | 1570 | 238.9403 | 23.8940 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 113.0998 | 104.3278 | 121.3364 | 100.7591 | 125.4405 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 157 | 1570 | 238.9403 | 39.6015 | 0.1657 | 0.1356 | 0.1987 | 0.1190 | 0.2124 | 97.3924 | 86.9880 | 107.7957 | 82.2634 | 112.5213 | 0.1000 | 0.0657 | 0.0356 | 0.0987 | 0.0190 | 0.1124 | 0.1000 | 0.0657 | 0.0356 | 0.0987 | 0.0190 | 0.1124 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 157 | 1570 | 238.9403 | 23.2573 | 0.0973 | 0.0876 | 0.1078 | 0.0825 | 0.1122 | 113.7365 | 104.8804 | 122.2287 | 101.1416 | 126.3315 | 0.1000 | -0.0027 | -0.0124 | 0.0078 | -0.0175 | 0.0122 | 0.1000 | -0.0027 | -0.0124 | 0.0078 | -0.0175 | 0.0122 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 157 | 1570 | 238.9403 | 21.4786 | 0.0899 | 0.0751 | 0.1069 | 0.0654 | 0.1143 | 115.5153 | 105.9731 | 124.6187 | 101.9317 | 129.0989 | 0.1000 | -0.0101 | -0.0249 | 0.0069 | -0.0346 | 0.0143 | 0.1000 | -0.0101 | -0.0249 | 0.0069 | -0.0346 | 0.0143 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 157 | 1570 | 238.9403 | 28.9685 | 0.1212 | 0.0937 | 0.1478 | 0.0834 | 0.1590 | 108.0253 | 97.9421 | 117.7400 | 93.5069 | 122.5437 | 0.1000 | 0.0212 | -0.0063 | 0.0478 | -0.0166 | 0.0590 | 0.1000 | 0.0212 | -0.0063 | 0.0478 | -0.0166 | 0.0590 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 157 | 1570 | 238.9403 | 25.3440 | 0.1061 | 0.0866 | 0.1362 | 0.0700 | 0.1422 | 111.6498 | 100.5657 | 121.1829 | 95.8917 | 127.4079 | 0.1000 | 0.0061 | -0.0134 | 0.0362 | -0.0300 | 0.0422 | 0.1000 | 0.0061 | -0.0134 | 0.0362 | -0.0300 | 0.0422 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 157 | 1570 | 238.9403 | 37.0430 | 0.1550 | 0.1280 | 0.1862 | 0.1118 | 0.1983 | 99.9508 | 89.0447 | 109.6934 | 84.8195 | 115.0822 | 0.1000 | 0.0550 | 0.0280 | 0.0862 | 0.0118 | 0.0983 | 0.1000 | 0.0550 | 0.0280 | 0.0862 | 0.0118 | 0.0983 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.1000 | 157 | 1570 | 238.9403 | 136.9938 | 0.5733 | 0.5491 | 0.5979 | 0.5372 | 0.6095 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 | 0.4733 | 0.4491 | 0.4979 | 0.4372 | 0.5095 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random | all | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | arm_count | all | 0.5000 | 785 | 1570 | 238.9403 | 119.4701 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 119.4701 | 110.5847 | 130.0382 | 105.2162 | 133.7241 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-01-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 785 | 1570 | 238.9403 | 133.5992 | 0.5591 | 0.5181 | 0.6025 | 0.4990 | 0.6193 | 105.3411 | 93.3186 | 118.2443 | 87.6346 | 123.0475 | 0.5000 | 0.0591 | 0.0181 | 0.1025 | -0.0010 | 0.1193 | 0.5000 | 0.0591 | 0.0181 | 0.1025 | -0.0010 | 0.1193 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 785 | 1570 | 238.9403 | 115.4768 | 0.4833 | 0.4478 | 0.5188 | 0.4301 | 0.5365 | 123.4634 | 110.5884 | 135.6750 | 105.2386 | 141.6883 | 0.5000 | -0.0167 | -0.0522 | 0.0188 | -0.0699 | 0.0365 | 0.5000 | -0.0167 | -0.0522 | 0.0188 | -0.0699 | 0.0365 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 785 | 1570 | 238.9403 | 115.4768 | 0.4833 | 0.4478 | 0.5188 | 0.4301 | 0.5365 | 123.4634 | 110.5884 | 135.6750 | 105.2386 | 141.6883 | 0.5000 | -0.0167 | -0.0522 | 0.0188 | -0.0699 | 0.0365 | 0.5000 | -0.0167 | -0.0522 | 0.0188 | -0.0699 | 0.0365 | 6 | yes |
| 2015-01-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 785 | 1570 | 238.9403 | 123.3752 | 0.5163 | 0.4720 | 0.5534 | 0.4567 | 0.5760 | 115.5651 | 102.8202 | 130.2067 | 96.7117 | 134.4185 | 0.5000 | 0.0163 | -0.0280 | 0.0534 | -0.0433 | 0.0760 | 0.5000 | 0.0163 | -0.0280 | 0.0534 | -0.0433 | 0.0760 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 785 | 1570 | 238.9403 | 127.2539 | 0.5326 | 0.4972 | 0.5764 | 0.4759 | 0.5893 | 111.6864 | 99.0532 | 123.4620 | 93.9586 | 129.4142 | 0.5000 | 0.0326 | -0.0028 | 0.0764 | -0.0241 | 0.0893 | 0.5000 | 0.0326 | -0.0028 | 0.0764 | -0.0241 | 0.0893 | 6 | no |
| 2015-01-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 785 | 1570 | 238.9403 | 139.4363 | 0.5836 | 0.5350 | 0.6192 | 0.5231 | 0.6440 | 99.5040 | 88.4135 | 114.8273 | 80.2392 | 118.7688 | 0.5000 | 0.0836 | 0.0350 | 0.1192 | 0.0231 | 0.1440 | 0.5000 | 0.0836 | 0.0350 | 0.1192 | 0.0231 | 0.1440 | 6 | no |
| 2015-01-01T00:00:00+00:00 | oracle | all | 0.5000 | 785 | 1570 | 238.9403 | 238.9403 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random | all | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | GBM | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P0 | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P1 | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P2 | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | local_eb | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | text_lr | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | arm_count | all | 0.2500 | 93 | 372 | 49.9236 | 12.4809 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 33.4134 | 28.0513 | 39.5028 | 25.1504 | 41.6764 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | p_win | GBM | 0.2500 | 93 | 372 | 49.9236 | 15.0018 | 0.3005 | 0.2358 | 0.4086 | 0.1743 | 0.4267 | 30.8925 | 23.8409 | 36.3806 | 21.9807 | 39.8043 | 0.2500 | 0.0505 | -0.0142 | 0.1586 | -0.0757 | 0.1767 | 0.2500 | 0.0505 | -0.0142 | 0.1586 | -0.0757 | 0.1767 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | P0 | 0.2500 | 93 | 372 | 49.9236 | 12.4154 | 0.2487 | 0.1867 | 0.3129 | 0.1572 | 0.3402 | 33.4789 | 27.8523 | 39.2018 | 25.1135 | 41.8442 | 0.2500 | -0.0013 | -0.0633 | 0.0629 | -0.0928 | 0.0902 | 0.2500 | -0.0013 | -0.0633 | 0.0629 | -0.0928 | 0.0902 | 6 | yes |
| 2015-04-01T00:00:00+00:00 | p_win | P1 | 0.2500 | 93 | 372 | 49.9236 | 12.4154 | 0.2487 | 0.1867 | 0.3129 | 0.1572 | 0.3402 | 33.4789 | 27.8523 | 39.2018 | 25.1135 | 41.8442 | 0.2500 | -0.0013 | -0.0633 | 0.0629 | -0.0928 | 0.0902 | 0.2500 | -0.0013 | -0.0633 | 0.0629 | -0.0928 | 0.0902 | 6 | yes |
| 2015-04-01T00:00:00+00:00 | p_win | P2 | 0.2500 | 93 | 372 | 49.9236 | 11.7535 | 0.2354 | 0.1870 | 0.2838 | 0.1656 | 0.3053 | 34.1408 | 28.3439 | 39.9328 | 25.3471 | 42.9344 | 0.2500 | -0.0146 | -0.0630 | 0.0338 | -0.0844 | 0.0553 | 0.2500 | -0.0146 | -0.0630 | 0.0338 | -0.0844 | 0.0553 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | local_eb | 0.2500 | 93 | 372 | 49.9236 | 12.5619 | 0.2516 | 0.1739 | 0.3252 | 0.1410 | 0.3622 | 33.3325 | 26.8244 | 40.6481 | 22.9458 | 43.7191 | 0.2500 | 0.0016 | -0.0761 | 0.0752 | -0.1090 | 0.1122 | 0.2500 | 0.0016 | -0.0761 | 0.0752 | -0.1090 | 0.1122 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | text_lr | 0.2500 | 93 | 372 | 49.9236 | 16.4097 | 0.3287 | 0.2464 | 0.4307 | 0.1924 | 0.4650 | 29.4846 | 22.3660 | 35.2117 | 19.9628 | 39.0064 | 0.2500 | 0.0787 | -0.0036 | 0.1807 | -0.0576 | 0.2150 | 0.2500 | 0.0787 | -0.0036 | 0.1807 | -0.0576 | 0.2150 | 6 | no |
| 2015-04-01T00:00:00+00:00 | oracle | all | 0.2500 | 93 | 372 | 49.9236 | 45.8943 | 0.9193 | 0.8856 | 0.9523 | 0.8697 | 0.9689 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.6693 | 0.6356 | 0.7023 | 0.6197 | 0.7189 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random | all | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | GBM | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P0 | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P1 | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P2 | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | local_eb | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | text_lr | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | arm_count | all | 0.1000 | 37 | 372 | 49.9236 | 4.9655 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 0.0995 | 25.5860 | 20.5435 | 31.1003 | 17.6672 | 33.5048 | 0.0995 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | p_win | GBM | 0.1000 | 37 | 372 | 49.9236 | 9.4798 | 0.1899 | 0.1122 | 0.2697 | 0.0760 | 0.3037 | 21.0718 | 15.8774 | 27.7893 | 12.5073 | 29.6362 | 0.0995 | 0.0904 | 0.0128 | 0.1703 | -0.0234 | 0.2043 | 0.0995 | 0.0904 | 0.0128 | 0.1703 | -0.0234 | 0.2043 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | P0 | 0.1000 | 37 | 372 | 49.9236 | 4.9395 | 0.0989 | 0.0740 | 0.1251 | 0.0629 | 0.1350 | 25.6121 | 20.6993 | 30.5027 | 18.1752 | 33.0490 | 0.0995 | -0.0005 | -0.0254 | 0.0257 | -0.0365 | 0.0355 | 0.0995 | -0.0005 | -0.0254 | 0.0257 | -0.0365 | 0.0355 | 6 | yes |
| 2015-04-01T00:00:00+00:00 | p_win | P1 | 0.1000 | 37 | 372 | 49.9236 | 4.9395 | 0.0989 | 0.0740 | 0.1251 | 0.0629 | 0.1350 | 25.6121 | 20.6993 | 30.5027 | 18.1752 | 33.0490 | 0.0995 | -0.0005 | -0.0254 | 0.0257 | -0.0365 | 0.0355 | 0.0995 | -0.0005 | -0.0254 | 0.0257 | -0.0365 | 0.0355 | 6 | yes |
| 2015-04-01T00:00:00+00:00 | p_win | P2 | 0.1000 | 37 | 372 | 49.9236 | 4.2776 | 0.0857 | 0.0622 | 0.1109 | 0.0515 | 0.1199 | 26.2740 | 20.6494 | 32.2367 | 17.6733 | 34.8747 | 0.0995 | -0.0138 | -0.0373 | 0.0114 | -0.0480 | 0.0205 | 0.0995 | -0.0138 | -0.0373 | 0.0114 | -0.0480 | 0.0205 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | local_eb | 0.1000 | 37 | 372 | 49.9236 | 3.8734 | 0.0776 | 0.0245 | 0.1530 | -0.0182 | 0.1734 | 26.6781 | 21.1505 | 32.6249 | 18.3909 | 34.9653 | 0.0995 | -0.0219 | -0.0750 | 0.0536 | -0.1177 | 0.0739 | 0.0995 | -0.0219 | -0.0750 | 0.0536 | -0.1177 | 0.0739 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | text_lr | 0.1000 | 37 | 372 | 49.9236 | 9.4863 | 0.1900 | 0.1173 | 0.2745 | 0.0803 | 0.2997 | 21.0653 | 15.6387 | 27.8350 | 11.9946 | 30.1359 | 0.0995 | 0.0906 | 0.0179 | 0.1750 | -0.0192 | 0.2003 | 0.0995 | 0.0906 | 0.0179 | 0.1750 | -0.0192 | 0.2003 | 6 | no |
| 2015-04-01T00:00:00+00:00 | oracle | all | 0.1000 | 37 | 372 | 49.9236 | 30.5515 | 0.6120 | 0.5528 | 0.6711 | 0.5283 | 0.6957 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0995 | 0.5125 | 0.4534 | 0.5716 | 0.4288 | 0.5962 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random | all | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | GBM | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P0 | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P1 | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | P2 | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | local_eb | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | random_matched | text_lr | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | arm_count | all | 0.5000 | 186 | 372 | 49.9236 | 24.9618 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 24.9618 | 20.3604 | 29.7579 | 17.8774 | 32.0463 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| 2015-04-01T00:00:00+00:00 | p_win | GBM | 0.5000 | 186 | 372 | 49.9236 | 29.3911 | 0.5887 | 0.5001 | 0.6760 | 0.4595 | 0.7180 | 20.5326 | 15.7697 | 25.4138 | 13.6201 | 27.4450 | 0.5000 | 0.0887 | 0.0001 | 0.1760 | -0.0405 | 0.2180 | 0.5000 | 0.0887 | 0.0001 | 0.1760 | -0.0405 | 0.2180 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | P0 | 0.5000 | 186 | 372 | 49.9236 | 24.9725 | 0.5002 | 0.4134 | 0.5716 | 0.3846 | 0.6159 | 24.9512 | 19.5860 | 30.7334 | 16.8936 | 33.0088 | 0.5000 | 0.0002 | -0.0866 | 0.0716 | -0.1154 | 0.1159 | 0.5000 | 0.0002 | -0.0866 | 0.0716 | -0.1154 | 0.1159 | 6 | yes |
| 2015-04-01T00:00:00+00:00 | p_win | P1 | 0.5000 | 186 | 372 | 49.9236 | 24.9725 | 0.5002 | 0.4134 | 0.5716 | 0.3846 | 0.6159 | 24.9512 | 19.5860 | 30.7334 | 16.8936 | 33.0088 | 0.5000 | 0.0002 | -0.0866 | 0.0716 | -0.1154 | 0.1159 | 0.5000 | 0.0002 | -0.0866 | 0.0716 | -0.1154 | 0.1159 | 6 | yes |
| 2015-04-01T00:00:00+00:00 | p_win | P2 | 0.5000 | 186 | 372 | 49.9236 | 27.1750 | 0.5443 | 0.4246 | 0.6197 | 0.4022 | 0.6865 | 22.7486 | 17.5555 | 29.7093 | 13.9128 | 31.5845 | 0.5000 | 0.0443 | -0.0754 | 0.1197 | -0.0978 | 0.1865 | 0.5000 | 0.0443 | -0.0754 | 0.1197 | -0.0978 | 0.1865 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | local_eb | 0.5000 | 186 | 372 | 49.9236 | 24.9162 | 0.4991 | 0.4064 | 0.5974 | 0.3579 | 0.6402 | 25.0074 | 19.1177 | 30.8045 | 16.3290 | 33.6859 | 0.5000 | -0.0009 | -0.0936 | 0.0974 | -0.1421 | 0.1402 | 0.5000 | -0.0009 | -0.0936 | 0.0974 | -0.1421 | 0.1402 | 6 | no |
| 2015-04-01T00:00:00+00:00 | p_win | text_lr | 0.5000 | 186 | 372 | 49.9236 | 30.4043 | 0.6090 | 0.5130 | 0.7107 | 0.4658 | 0.7522 | 19.5193 | 13.8723 | 26.2307 | 10.3522 | 28.6864 | 0.5000 | 0.1090 | 0.0130 | 0.2107 | -0.0342 | 0.2522 | 0.5000 | 0.1090 | 0.0130 | 0.2107 | -0.0342 | 0.2522 | 6 | no |
| 2015-04-01T00:00:00+00:00 | oracle | all | 0.5000 | 186 | 372 | 49.9236 | 49.9236 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.2500 | 3456 | 13822 | 2284.1595 | 571.1345 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 1426.0081 | 1390.6169 | 1460.5705 | 1376.5582 | 1475.4580 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.2500 | 3456 | 13822 | 2284.1595 | 647.1109 | 0.2833 | 0.2724 | 0.2964 | 0.2657 | 0.3009 | 1350.0317 | 1303.1235 | 1386.7837 | 1290.2811 | 1409.7822 | 0.2500 | 0.0333 | 0.0223 | 0.0463 | 0.0157 | 0.0509 | 0.2500 | 0.0333 | 0.0223 | 0.0463 | 0.0157 | 0.0509 | 6 | no |
| ALL | p_win | P0 | 0.2500 | 3456 | 13822 | 2284.1595 | 553.2590 | 0.2422 | 0.2341 | 0.2505 | 0.2303 | 0.2541 | 1443.8836 | 1400.2097 | 1484.2846 | 1385.0585 | 1502.7087 | 0.2500 | -0.0078 | -0.0159 | 0.0005 | -0.0197 | 0.0041 | 0.2500 | -0.0078 | -0.0159 | 0.0005 | -0.0197 | 0.0041 | 6 | yes |
| ALL | p_win | P1 | 0.2500 | 3456 | 13822 | 2284.1595 | 568.7266 | 0.2490 | 0.2408 | 0.2568 | 0.2376 | 0.2604 | 1428.4159 | 1390.1345 | 1467.5219 | 1371.8370 | 1484.9949 | 0.2500 | -0.0011 | -0.0092 | 0.0068 | -0.0125 | 0.0104 | 0.2500 | -0.0011 | -0.0092 | 0.0068 | -0.0125 | 0.0104 | 6 | yes |
| ALL | p_win | P2 | 0.2500 | 3456 | 13822 | 2284.1595 | 603.8111 | 0.2643 | 0.2531 | 0.2750 | 0.2486 | 0.2801 | 1393.3315 | 1351.2026 | 1434.6029 | 1331.9701 | 1454.6929 | 0.2500 | 0.0143 | 0.0031 | 0.0250 | -0.0014 | 0.0300 | 0.2500 | 0.0143 | 0.0031 | 0.0250 | -0.0014 | 0.0300 | 6 | no |
| ALL | p_win | local_eb | 0.2500 | 3456 | 13822 | 2284.1595 | 605.7686 | 0.2652 | 0.2533 | 0.2781 | 0.2479 | 0.2825 | 1391.3740 | 1344.9083 | 1431.3264 | 1328.4534 | 1454.2945 | 0.2500 | 0.0152 | 0.0033 | 0.0280 | -0.0021 | 0.0325 | 0.2500 | 0.0152 | 0.0033 | 0.0280 | -0.0021 | 0.0325 | 6 | no |
| ALL | p_win | text_lr | 0.2500 | 3456 | 13822 | 2284.1595 | 675.5516 | 0.2958 | 0.2854 | 0.3079 | 0.2786 | 0.3129 | 1321.5910 | 1279.1583 | 1361.3073 | 1260.4933 | 1382.6887 | 0.2500 | 0.0457 | 0.0353 | 0.0578 | 0.0286 | 0.0629 | 0.2500 | 0.0457 | 0.0353 | 0.0578 | 0.0286 | 0.0629 | 6 | no |
| ALL | oracle | all | 0.2500 | 3456 | 13822 | 2284.1595 | 1997.1426 | 0.8743 | 0.8678 | 0.8804 | 0.8653 | 0.8834 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | 0.6243 | 0.6177 | 0.6303 | 0.6153 | 0.6333 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.1000 | 1383 | 13822 | 2284.1595 | 228.5776 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1032.6288 | 1001.5028 | 1058.4277 | 990.3102 | 1074.9475 | 0.1001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.1000 | 1383 | 13822 | 2284.1595 | 272.7167 | 0.1194 | 0.1112 | 0.1286 | 0.1066 | 0.1322 | 988.4898 | 950.3862 | 1018.4591 | 938.3205 | 1038.6590 | 0.1001 | 0.0193 | 0.0111 | 0.0286 | 0.0065 | 0.0321 | 0.1001 | 0.0193 | 0.0111 | 0.0286 | 0.0065 | 0.0321 | 6 | no |
| ALL | p_win | P0 | 0.1000 | 1383 | 13822 | 2284.1595 | 220.0600 | 0.0963 | 0.0930 | 0.1002 | 0.0913 | 0.1014 | 1041.1464 | 1007.3737 | 1068.3835 | 996.0319 | 1086.2609 | 0.1001 | -0.0037 | -0.0071 | 0.0002 | -0.0088 | 0.0013 | 0.1001 | -0.0037 | -0.0071 | 0.0002 | -0.0088 | 0.0013 | 6 | yes |
| ALL | p_win | P1 | 0.1000 | 1383 | 13822 | 2284.1595 | 225.0175 | 0.0985 | 0.0951 | 0.1024 | 0.0931 | 0.1039 | 1036.1889 | 1002.8938 | 1064.1661 | 991.4451 | 1080.9328 | 0.1001 | -0.0016 | -0.0049 | 0.0023 | -0.0070 | 0.0039 | 0.1001 | -0.0016 | -0.0049 | 0.0023 | -0.0070 | 0.0039 | 6 | yes |
| ALL | p_win | P2 | 0.1000 | 1383 | 13822 | 2284.1595 | 246.2436 | 0.1078 | 0.1002 | 0.1144 | 0.0976 | 0.1180 | 1014.9629 | 984.1156 | 1048.0025 | 966.6144 | 1063.3114 | 0.1001 | 0.0077 | 0.0002 | 0.0143 | -0.0025 | 0.0180 | 0.1001 | 0.0077 | 0.0002 | 0.0143 | -0.0025 | 0.0180 | 6 | no |
| ALL | p_win | local_eb | 0.1000 | 1383 | 13822 | 2284.1595 | 240.7459 | 0.1054 | 0.0978 | 0.1156 | 0.0924 | 0.1184 | 1020.4605 | 984.5177 | 1048.5366 | 972.3176 | 1068.6034 | 0.1001 | 0.0053 | -0.0023 | 0.0155 | -0.0076 | 0.0183 | 0.1001 | 0.0053 | -0.0023 | 0.0155 | -0.0076 | 0.0183 | 6 | no |
| ALL | p_win | text_lr | 0.1000 | 1383 | 13822 | 2284.1595 | 300.2467 | 0.1314 | 0.1228 | 0.1404 | 0.1185 | 0.1444 | 960.9597 | 926.2448 | 995.0486 | 911.4212 | 1010.4983 | 0.1001 | 0.0314 | 0.0228 | 0.0403 | 0.0185 | 0.0443 | 0.1001 | 0.0314 | 0.0228 | 0.0403 | 0.0185 | 0.0443 | 6 | no |
| ALL | oracle | all | 0.1000 | 1383 | 13822 | 2284.1595 | 1261.2065 | 0.5522 | 0.5440 | 0.5606 | 0.5397 | 0.5646 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1001 | 0.4521 | 0.4439 | 0.4606 | 0.4397 | 0.4645 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random | all | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | GBM | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P0 | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P1 | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | P2 | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | local_eb | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | random_matched | text_lr | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | arm_count | all | 0.5000 | 6912 | 13822 | 2284.1595 | 1142.2487 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 0.5001 | 1141.9035 | 1109.3057 | 1172.1837 | 1097.0230 | 1186.7841 | 0.5001 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |
| ALL | p_win | GBM | 0.5000 | 6912 | 13822 | 2284.1595 | 1216.1491 | 0.5324 | 0.5204 | 0.5440 | 0.5144 | 0.5504 | 1068.0032 | 1027.6823 | 1107.9879 | 1010.0589 | 1125.9474 | 0.5001 | 0.0324 | 0.0203 | 0.0439 | 0.0144 | 0.0504 | 0.5001 | 0.0324 | 0.0203 | 0.0439 | 0.0144 | 0.0504 | 6 | no |
| ALL | p_win | P0 | 0.5000 | 6912 | 13822 | 2284.1595 | 1120.1733 | 0.4904 | 0.4796 | 0.5006 | 0.4750 | 0.5058 | 1163.9790 | 1124.2207 | 1206.7078 | 1104.6081 | 1223.3498 | 0.5001 | -0.0097 | -0.0205 | 0.0006 | -0.0251 | 0.0057 | 0.5001 | -0.0097 | -0.0205 | 0.0006 | -0.0251 | 0.0057 | 6 | yes |
| ALL | p_win | P1 | 0.5000 | 6912 | 13822 | 2284.1595 | 1136.8893 | 0.4977 | 0.4862 | 0.5087 | 0.4816 | 0.5139 | 1147.2630 | 1108.1567 | 1192.4619 | 1086.9010 | 1207.6250 | 0.5001 | -0.0023 | -0.0138 | 0.0086 | -0.0185 | 0.0138 | 0.5001 | -0.0023 | -0.0138 | 0.0086 | -0.0185 | 0.0138 | 6 | yes |
| ALL | p_win | P2 | 0.5000 | 6912 | 13822 | 2284.1595 | 1170.9297 | 0.5126 | 0.4997 | 0.5246 | 0.4947 | 0.5306 | 1113.2226 | 1070.7347 | 1161.7044 | 1050.8081 | 1175.6370 | 0.5001 | 0.0126 | -0.0004 | 0.0245 | -0.0054 | 0.0305 | 0.5001 | 0.0126 | -0.0004 | 0.0245 | -0.0054 | 0.0305 | 6 | no |
| ALL | p_win | local_eb | 0.5000 | 6912 | 13822 | 2284.1595 | 1171.4277 | 0.5128 | 0.5015 | 0.5283 | 0.4930 | 0.5327 | 1112.7246 | 1067.0788 | 1154.0058 | 1048.7275 | 1176.7217 | 0.5001 | 0.0128 | 0.0014 | 0.0282 | -0.0071 | 0.0326 | 0.5001 | 0.0128 | 0.0014 | 0.0282 | -0.0071 | 0.0326 | 6 | no |
| ALL | p_win | text_lr | 0.5000 | 6912 | 13822 | 2284.1595 | 1275.4693 | 0.5584 | 0.5431 | 0.5698 | 0.5389 | 0.5779 | 1008.6830 | 973.1676 | 1055.3254 | 949.8594 | 1067.5066 | 0.5001 | 0.0583 | 0.0430 | 0.0697 | 0.0388 | 0.0779 | 0.5001 | 0.0583 | 0.0430 | 0.0697 | 0.0388 | 0.0779 | 6 | no |
| ALL | oracle | all | 0.5000 | 6912 | 13822 | 2284.1595 | 2284.1523 | 1.0000 | 0.9998 | 1.0000 | 0.9998 | 1.0002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5001 | 0.4999 | 0.4998 | 0.4999 | 0.4997 | 0.5001 | n/a | n/a | n/a | n/a | n/a | n/a | 6 | n/a |

## Figures

- figures/reliability-upworthy.png
- figures/score_by_origin-upworthy.png
- figures/coverage-upworthy.png
- figures/decision_value-upworthy.png
