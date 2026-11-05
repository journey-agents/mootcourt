# Round 03 summary

Paper and code version under review: a839b2c. Reviews received: R1 (statistician), R2 (experimentation platform engineer), R3 (machine learning reviewer), R4 (reproducibility chair), R5 (area chair), R6 (practitioner and documentation reviewer), the same six as rounds 01 and 02, and R7, the fresh area chair the protocol adds in round 03, bounded by the rubric. Written 5 November 2026 by the launching team, with the response letter `response.md` beside it. Finding ids follow `.claude/fleet/round03-triage.md`.

## Scores and recommendations

| Reviewer | Novelty | Correctness | Rigor | Clarity | Reproducibility | Code | Recommendation |
|---|---|---|---|---|---|---|---|
| R1 statistician | 3 | 4 | 4 | 4 | 5 | 4 | minor revision |
| R2 platform engineer | 3 | 4 | 4 | 4 | 5 | 4 | minor revision |
| R3 machine learning | 3 | 4 | 4 | 4 | 4 | 4 | minor revision |
| R4 reproducibility chair | 3 | 4 | 4 | 4 | 5 | 4 | accept |
| R5 area chair | 3 | 4 | 4 | 4 | 4 | 4 | minor revision |
| R6 practitioner | 3 | 4 | 4 | 4 | 4 | 4 | minor revision |
| R7 fresh area chair | 3 | 4 | 4 | 3 | 5 | 4 | minor revision |

One recommends accept and six recommend minor revision; none recommends major revision or reject.

## Convergence table for round 03 (plan Task 8)

| Reviewer | Recommendation | Round 02 findings closed / not closed | Rubric items passed of total | New findings: blocking / major / minor / nit | Suggestions |
|---|---|---|---|---|---|
| R1 | minor revision | 9 / 0 | 13 of 15 (fails R1.15 minor; R1.14 nit) | 0 / 0 / 3 / 3 | 3 |
| R2 | minor revision | 7 / 0 (six findings and the carried R2-V7) | 13 of 15 (fails R2.15 minor; R2.14 nit, argued and accepted) | 0 / 0 / 3 / 1 | 5 |
| R3 | minor revision | 6 / 0 | 12 of 14 (fails R3.3 blocking; R3.9 minor) | 1 / 0 / 2 / 0 | 5 |
| R4 | accept | 6 / 0 | 14 of 14 | 0 / 0 / 1 / 0 | 2 |
| R5 | minor revision | 8 / 0 | 9 of 12 (fails R5.2, R5.5, R5.9 minor) | 0 / 0 / 5 / 0 | 3 |
| R6 | minor revision | 12 / 0 | 7 of 13 (fails R6.3, R6.4, R6.5, R6.6 minor; R6.11, R6.13 nit) | 0 / 0 / 6 / 2 | 4 |
| R7 | minor revision | none (first round) | 7 of 12 (fails R5.2, R5.3, R5.5, R5.7 minor; R5.12 nit) | 0 / 0 / 12 / 1 | 3 |
| Total, seven reviews | 1 accept, 6 minor revision | 48 / 0 | 75 of 95 | 1 / 0 / 32 / 7 (40 findings; 35 rows after merging and splitting) | 25 (two merged into findings) |

The rubric totals are the counts at the round's commit (15, 15, 14, 14, 12, 13 and 12 for R7 under R5's items); the items added after this round (R3.15, R3.16, R5.13, R6.14) and the dated amendments of R2.14 and R6.4 apply to any later round. Of the 40 findings, 36 are fixed, 4 are argued (R2-F4 under decision 6, R6-F5 by the reworded clause of R6.4, R6-F8 by the dated ids the pages print, R7-F11 by the page cost), none is a suggestion mis-filed as a finding, and every one names a rubric item or a claim id.

## Across the rounds

| Round | Commit | Reviewers | Recommendations | Findings: blocking / major / minor / nit | Previous findings closed / not closed | Rubric items passed of total | Suggestions |
|---|---|---|---|---|---|---|---|
| 01 | 85ae973 | R1 to R6 | 5 major revision, 1 minor | 3 / 21 / 40 / 24 (88) | round 00's five blocking and twenty-one major all closed | no rubric yet (Task 2 wrote it after round 01) | recorded in the letter |
| 02 | 9f725b1 | R1 to R6 | 6 minor revision | 0 / 1 / 36 / 11 (48) | 78 / 10 | 49 of 80 | 20 |
| 03 | a839b2c | R1 to R6, R7 | 1 accept, 6 minor revision | 1 / 0 / 32 / 7 (40) | 48 / 0 | 75 of 95 | 25 |

The one blocking of round 03 is a single printed digit (0.0539 for a leaf of 0.053846), fixed in one line with the number audit changed to match the report leaf before the source comment (call 273, three tests), so that the class cannot recur unseen. The majors went from 21 to 1 to 0; the open findings of the previous round not closed went from 10 to 0.

## Findings by severity and their disposition

| Reviewer | Blocking | Major | Minor | Nit | Findings | Fixed | Argued | Questions |
|---|---|---|---|---|---|---|---|---|
| R1 | 0 | 0 | 3 | 3 | 6 | 6 | 0 | 4 |
| R2 | 0 | 0 | 3 | 1 | 4 | 3 | 1 (R2-F4, decision 19) | 5 |
| R3 | 1 | 0 | 2 | 0 | 3 | 3 | 0 | 5 |
| R4 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 3 |
| R5 | 0 | 0 | 5 | 0 | 5 | 5 | 0 | 5 |
| R6 | 0 | 0 | 6 | 2 | 8 | 6 | 2 (R6-F5 by the reworded clause; R6-F8 by the dated ids) | 3 |
| R7 | 0 | 0 | 12 | 1 | 13 | 12 | 1 (R7-F11, decision 18) | 4 |
| Total | 1 | 0 | 32 | 7 | 40 | 36 | 4 | 29 |

## Tiers of the fixes

- Tier C (one stage): `scripts/run_experiments.sh --only extras-upworthy` (call 271), adding `p1_minus_p0_by_origin` and `issued_ece_by_origin` to `paper/data/run7-tie-rank/paper-extras-upworthy-20261103-4bfb354b87e3.json`; no existing number moved.
- Tier B (code that moves no number): calls 268 to 273 (the held-row refusal, the exit code, the figures at the included width, call 258's corrected note line, the all-null report column, the paired column at five decimals and the one pooled interval, the leaf-first number audit); `make quick-check` passed with the sample fixture unchanged; the figures test holds `figures.json` unchanged.
- Tier A (text): the paper (pass 12: decisions 1 to 12 and 22, 25, 26, 29), the documentation (decision 17 and the R6 rows, one regeneration pass over the pages), the rubric's dated items and amendments, the round 02 letter's dated corrections, and this round's letter and summary.

## Claims supported as written

The register `paper/reviews/claims.md` holds 134 rows after this round (128 at the commit under review; C129 to C134 added; C21, C22 and C23 requoted without numbers after contribution 3 was rewritten as a contribution); 127 rows carry a key, and `scripts/claims_audit.py paper/reviews/claims.md paper/data/run7-tie-rank` exits 0 with no failing row. The number audit, now matching the report leaf first, reads 769 numbers checked and 0 unmatched, 107 source paths resolved and 0 unresolved. Every caption with a digit carries a source, and the writing rules pass on the paper, the register, the rubric, the three letters and the reviews of the three rounds.

## Numbers changed since round 02

Only the extras file moved, in three reruns of one stage, `extras-upworthy`: the first two in the round 02 fix batch (the guard-pairs bootstrap at 500 resamples, the interval minus 0.00073 to 0.00245 from minus 0.00071 to 0.00253 with the printed digits unchanged; the keys `issued_row_brier_skill` and `p2_selection_comparison`), the third in this round (the keys `p1_minus_p0_by_origin` and `issued_ece_by_origin`, call 271). No other report, table value, figure value or headline number changed; one printed digit of the paper was corrected to its leaf (0.0538), and the figures were redrawn at the included width with every plotted value unchanged.

## The cap

This was the last planned round under the convergence plan: the protocol allows at most two further rounds after round 01, and round 03 is the second. No round 04 is run; the fix commit, release 1.0.0, is verified by the audits, `make selfcheck` and the tester's clean clone, and the paper is released with the open items listed in the letter and in Section 9.

The stop condition, part by part. Met by the round: all seven reviewers recommend accept or minor revision; no major finding was raised; every finding names the claim it weakens or the rubric item it fails; every number of the paper traces to a report key; every register row is supported as written; the one blocking finding is fixed and its class is now caught by the audit. Met by listing, as the cap rule provides: the rubric items that failed at the commit are fixed in this round except two that pass by dated amendment (R2.14, R6.4) and one nit that stays argued (R5.12's exact numbering order), each carried in Section 9's argued list; R2.15 was built. Met by R4 at a839b2c: a clean clone with a fresh download reproduces the timed run's seven reports, 55,940 numbers with 0 differing at 1e-9 and the extras file regenerated, on top of its round 02 regeneration of all 69 report files at 9f725b1 (609,116 numbers, 0 differing). Not met in the protocol's first form: no reviewer has read the fix commit, so "every rubric item passes" rests on the fixes and the audits, not on a further round; that is what the cap rule provides, and the release check verifies the fix commit mechanically.
