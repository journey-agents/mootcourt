# Round 02 summary

Paper and code version under review: 9f725b1. Reviews received: R1 (statistician), R2 (experimentation platform engineer), R3 (machine learning reviewer), R4 (reproducibility chair), R5 (area chair), R6 (practitioner and documentation reviewer), the same six as round 01, each verifying its own round 01 findings before its rubric section. Written 5 November 2026 by the launching team, with the response letter `response.md` beside it. Finding ids follow `.claude/fleet/round02-triage.md`.

## Scores and recommendations

| Reviewer | Novelty | Correctness | Rigor | Clarity | Reproducibility | Code | Recommendation |
|---|---|---|---|---|---|---|---|
| R1 statistician | 3 | 4 | 4 | 3 | 5 | 4 | minor revision |
| R2 platform engineer | 3 | 4 | 4 | 4 | 5 | 4 | minor revision |
| R3 machine learning | 3 | 4 | 4 | 4 | 5 | 4 | minor revision |
| R4 reproducibility chair | 3 | 4 | 4 | 4 | 5 | 4 | minor revision |
| R5 area chair | 3 | 4 | 4 | 3 | 4 | 4 | minor revision |
| R6 practitioner | 3 | 4 | 4 | 4 | 4 | 4 | minor revision |

All six recommend minor revision (round 01: five major revision, one minor). No reviewer recommends reject.

## Convergence table (plan Task 8)

| Reviewer | Recommendation | Round 01 findings closed / not closed | Rubric items passed of total | New findings: blocking / major / minor / nit | Suggestions |
|---|---|---|---|---|---|
| R1 | minor revision | 11 / 0 | 8 of 14 (fails R1.8 major; R1.3, R1.9, R1.11, R1.13 minor; R1.14 nit) | 0 / 1 / 7 / 1 | 5 |
| R2 | minor revision | 12 / 3 (items 7, 12, 13; 12 and 13 re-raised as R2-F4 and R2-F6, item 7 carried as R2-V7) | 8 of 14 (fails R2.6, R2.9, R2.10, R2.11, R2.13 minor; R2.14 nit) | 0 / 0 / 6 / 1 | 4 |
| R3 | minor revision | 14 / 1 (minor 6, the single-headline run, carried as a suggestion) | 14 of 14 | 0 / 0 / 6 / 0 | 2 |
| R4 | minor revision | 13 / 0 | 9 of 14 (fails R4.5, R4.6, R4.12 minor; R4.13, R4.14 nit) | 0 / 0 / 3 / 3 | 2 |
| R5 | minor revision | 12 / 2 (items 6 and 12, re-raised as R5-F3 and R5-F8) | 6 of 12 (fails R5.2, R5.5, R5.7, R5.8, R5.9 minor; R5.12 nit) | 0 / 0 / 5 / 3 | 2 |
| R6 | minor revision | 16 / 4 (items 6, 10, 18, 20, re-raised as R6-F2, R6-F1, R6-F10, R6-F11) | 4 of 12 (fails R6.2, R6.3, R6.4, R6.5, R6.6, R6.7 minor; R6.11, R6.12 nit) | 0 / 0 / 9 / 3 | 5 |
| Total | 6 of 6 minor revision | 78 / 10 | 49 of 80 | 0 / 1 / 36 / 11 (48 findings) | 20 |

The rubric totals are the counts at the round's commit (14, 14, 14, 14, 12, 12); three items were added for round 03 after this round (R1.15, R2.15, R6.13; decision 7). Of the 10 round 01 findings not closed, every one was re-raised as a round 02 finding or carried as a suggestion, and each is answered in the letter.

## Findings by severity and their disposition

| Reviewer | Blocking | Major | Minor | Nit | Findings | Fixed | Fixed in part | Argued | Questions |
|---|---|---|---|---|---|---|---|---|---|
| R1 | 0 | 1 | 7 | 1 | 9 | 9 | 0 | 0 | 5 |
| R2 | 0 | 0 | 6 | 1 | 7 (R2-V7 carried) | 6 | 0 | 1 (R2-F6, decision 6) | 5 |
| R3 | 0 | 0 | 6 | 0 | 6 | 6 | 0 | 0 | 5 |
| R4 | 0 | 0 | 3 | 3 | 6 | 5 | 1 (R4-F4) | 0 | 3 |
| R5 | 0 | 0 | 5 | 3 | 8 | 7 | 1 (R5-F6) | 0 | 5 |
| R6 | 0 | 0 | 9 | 3 | 12 | 12 | 0 | 0 | 3 |
| Total | 0 | 1 | 36 | 11 | 48 | 45 | 2 | 1 | 26 |

The one major (R1-F1, the learning-curve tables) is a regenerated table and one sentence; no experiment was defective. The two fixed in part: R4-F4 (the commands table carries the driver's flags; the Makefile's quick targets keep theirs) and R5-F6 (the appendix tables are in reading order within two groups, single-column then two-column, since one exact order costs six pages). The one argued: R2-F6, the two post-launch fields of the deployment-shaped features, kept at the top level until the next snapshot-changing release (decision 6) with the sentence on the ledger-format page. Suggestions: 20 recorded in the letter, two of them (R6-s2, R6-s3) taken outside the count as one-line changes (decision 11), none counted toward the stop condition.

## Tiers of the fixes

- Tier C (one stage): `scripts/run_experiments.sh --only extras-upworthy`, twice, replacing `paper/data/run7-tie-rank/paper-extras-upworthy-20261103-4bfb354b87e3.json` (the guard-pairs bootstrap at 500, the keys `issued_row_brier_skill` and `p2_selection_comparison`). No other report moved; the run folder gained `stages.txt` and the README's file lists.
- Tier B (code that moves no number): calls 256 to 264 (the cell-mismatch guard, the card's cell verdict and line order, the stored summary, the fallback gates, the report card's base rate, the report's first table, the join's messages, the help texts, the table builder's columns and unsigned zeros); `make quick-check` passed with the sample fixture unchanged.
- Tier A (text): the paper (passes 10 and 11), the documentation (the round 02 docs pass and the regeneration after the code settled), the round 01 letter's dated corrections, the rubric's three items, and this round's letter and summary.

## Claims supported as written

The register `paper/reviews/claims.md` holds 128 rows after this round (122 at the commit under review; C123 to C128 added, C5, C13 and C58 kept with status removed after their clauses left the abstract and Section 6.2); 124 rows carry a key, and `scripts/claims_audit.py paper/reviews/claims.md paper/data/run7-tie-rank` exits 0 with no failing row. The number audit reads 776 numbers checked and 0 unmatched, 108 source paths resolved and 0 unresolved. Every caption with a digit carries a source (`tests/test_paper_sources.py`), and the writing rules pass on the paper, the register, the rubric, both letters and the six reviews.

## Numbers changed since round 01

- The calibration percentiles: run 7 repeated run 6 under the mid-rank tie rule of call 255; the per-cell percentile fields moved in 9, 91 and 26 leaves of the three main reports (by at most 0.6, 3.0 and 3.9 points), none of them printed; every printed percentile is unchanged (the pooled headline cell 100.0, the deployment-shaped archive 98.8, the synthetic archive 95.2 and 97.8).
- The extras rerun: the admitted pairs' pooled interval at 500 resamples, minus 0.00073 to 0.00245 (from minus 0.00071 to 0.00253; printed minus 0.0007 to 0.0025, unchanged); the new keys `issued_row_brier_skill` (P2 issued minus 0.0018, abstained 0.0199) and `p2_selection_comparison` (forward minus leave-one-test-out, plus 0.0044 pooled with the guard on, plus 0.0024 with it off).
- Timings and identifiers only: the run 7 timed run (2,024.2 s against run 6's 2,052.0; 748 files; tree digest 00b348180c492b75), the gate simulation's seconds (794 against 870), the card latency, the positive control's snapshot date and model ids.
- No headline number of the paper moved: the skills, the log scores, the coverage, the decision values, the positive control's admission and pooled recovery and the learning curve are those of the round 01 letter's part 2b.

## Stop condition

Not met at the round's commit: five reviewers reported failing rubric items (R1 six, R2 six, R4 five, R5 six, R6 eight; R3 none), 47 of the 48 findings name a rubric item or a claim id and are fixed or argued above, and one item, R1-F1, carried the rubric's major severity. All six recommend minor revision, no blocking finding was raised, R4 regenerated every number of the run folder from a clean clone (609,116 numbers of 69 files at 1e-9, zero differing), every number traces to a report path, and every register row is supported as written. Round 03 is the second of the two further rounds the protocol allows: the same six reviewers verify this round's fixes, with one fresh area chair bounded by the rubric as the independent check; the three rubric items added after this round apply there.
