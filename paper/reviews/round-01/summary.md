# Round 01 summary

Paper and code version under review: 85ae973. Reviews received: R1 (statistician), R2 (experimentation platform engineer), R3 (machine learning reviewer), R4 (reproducibility chair, added in part 2a), R5 (area chair), R6 (practitioner and documentation reviewer). Written 4 November 2026 by the launching team.

## Scores and recommendations

| Reviewer | Novelty | Correctness | Rigor | Clarity | Reproducibility | Code | Recommendation |
|---|---|---|---|---|---|---|---|
| R1 statistician | 3 | 3 | 3 | 3 | 4 | 4 | major revision |
| R2 platform engineer | 3 | 3 | 4 | 4 | 4 | 3 | major revision |
| R3 machine learning | 3 | 3 | 3 | 3 | 4 | 4 | major revision |
| R4 reproducibility chair | 3 | 4 | 4 | 4 | 4 | 4 | minor revision |
| R5 area chair | 3 | 4 | 4 | 3 | 4 | 4 | major revision |
| R6 practitioner | 3 | 4 | 4 | 3 | 4 | 4 | major revision |

Five reviewers recommend major revision and the reproducibility chair minor revision; none recommends reject. Every round-00 blocking and major finding is recorded by its reviewer as holding at this commit, with the residues listed below (R1 on the decision-value table's adjusted bounds, R2 on the promotion comparison and the doctor counts, R3 on the realized gain of the positive control and the text classifier's decisive-row accuracy, R5 on the cross-platform number and the abstract's length).

## Findings by severity

| Reviewer | Blocking | Major | Minor | Nit | Findings | Questions |
|---|---|---|---|---|---|---|
| R1 | 2 | 2 | 5 | 2 | 11 | 5 |
| R2 | 1 | 5 | 6 | 3 | 15 | 5 |
| R3 | 0 | 6 | 7 | 2 | 15 | 6 |
| R4 | 0 | 1 | 5 | 7 | 13 | 4 |
| R5 | 0 | 4 | 5 | 5 | 14 | 6 |
| R6 | 0 | 3 | 12 | 5 | 20 | 5 |
| Total | 3 | 21 | 40 | 24 | 88 | 31 |

### Blocking

1. R1 B1. The decision-value comparison is dominated by the number of arms per test, a pre-launch field, and its random baseline does not control for it; against an arm-count-matched baseline the text classifier keeps about four points and the precedent rung keeps nothing. Task T-061 (arm-count policy as a named baseline row, matched baseline with by-test intervals and adjusted bounds, text rewritten to the rungs that clear it).
2. R1 B2. The learning curve's Brier skill is measured against a base rate re-estimated from each subsample, so the curve reads backwards; against the full-history base rate P1's skill rises with history and plateaus between 1,200 and 3,000 rows. Task T-062 (rescore every fraction against the full-history base rate, 500 resamples, seed spread beside the by-test interval, paragraph rewritten).
3. R2 B1. The weekly join's only time check is that the row's usable time has passed at the join clock, so a card issued after the result is in the ledger is joined and enters the reliability report as evidence. Task T-063 (refuse an outcome when the card's origin or issue time is at or after the row's usable time, mark a card issued after launch as in flight, exclude both from the reliability row, count both in the doctor).

### Major, grouped by theme, with the overlaps

1. Stale ablation captions (R1 M4, R3 M6, R5 M1). The captions of the two ablation tables carried P1 log scores from the truncated-grid run of round 00. Fixed in this pass: every caption number is read from the run5 files and carries a source comment, and every caption in the paper with a digit was swept (the two year tables' Bonferroni family sizes were also stale, 132 for 156 and 90 for 110).
2. Learning curve (R1 B2, R1 M3, R3 M5, R5 m5). Besides the moving baseline, the gates were read against the fit-history size, which is not what they measure, and the paragraph's "challengers keep their pooled order" does not match the file. Task T-062; the paragraph now states the subsampled-P0 baseline, drops the gate comparison and the order claim, and is marked for rewriting when the rerun lands.
3. The positive control measured admission, not recovery (R3 M4, R1 m9). Done as task T-066 before this pass: the sensitivity rows carry the rung's held-out gain, the oracle's gain and the recovered fraction, and two backtests of the planted ledger run every rung including the text classifier. At the size of the headline-only cell the rung recovers 0.197 (0.180 to 0.215) of the planted information; the text classifier scores below the base rate on the planted ledger. The abstract, Section 6.8, Appendix B and the limitations are rewritten in this pass.
4. Decision value (R1 B1, R5 M3, R1 m6). The adjusted bounds for the decision table (task T-060) are already in the working tree's report and table (family of six at each budget); the paper now reads the fifth hypothesis as confirmed for the text classifier and the boosted model and unresolved for the precedent rung and the local set, pending the arm-count-matched baseline of T-061.
5. "Pre-registered" (R5 M2). The plan entered the repository in commit 145eaf7 with the first run2 reports. Fixed in this pass: the paper says the hypotheses were fixed in writing before the final runs and are unchanged since, names the commit, and never uses the word.
6. Matched splits and the text ceiling (R5 M4, R3 m2, R3 m6). Only in-house re-implementations of the simplest members of each family ran on the matched splits. Fixed in wording in this pass (Section 2, the introduction, the abstract and Section 6.2 now say TF-IDF, and the decisive-row accuracy 0.601 is in the paper). A single-headline run of the challengers and a stronger text representation as a fourth challenger have no task yet.
7. The precedent negative is not isolated (R3 M1, R3 M2, R3 M3). Forward-chaining selection reverses the sign of the pooled difference (task T-064, the default re-tested under call 66 with a paired interval); the loss sits on the typical row of the admitted pairs and points at the scale term (task T-067, location against scale decomposition); the pooled AUC and resolution credit between-cell movement (task T-065, within-stratum discrimination).
8. The released loop (R2 B1, M2, M3, M4, M5, M6 and minors m7 to m12). An origin after the issue time is accepted; two cards for one row are both scored; the nightly fit takes every admitted row rather than the rows usable at the fit clock; the promotion of a different method compares unpaired summaries against a fixed margin no rung reaches; the card prints the pooled backtest line rather than its own cell's. Task T-063 covers all of them; the paper's Section 4.3 and 6.6 are marked and describe the loop as released.
9. Onboarding (R6 M1, M2, M3 and minors). The pip and uv install paths both break on a clone kept on an exFAT drive, the README's `uv run moot` fails outside the clone, the gate sizes are stated differently on three pages, the gate-power defaults come from a public archive, the card's request line shows headline fields on a ledger without text, and the reliability report needs a Python snippet to read. Tasks T-068 (command-line items: a reliability command, the doctor checks, the card's request line and base-rate wording, the verify script's flag, the timing line) and M4 (documentation).
10. Gates (R1 m5; R6 m6, m7, m8). The smallest cell has 2.1 rows per test against the 3.5 the gate simulation draws; the paper now says its label overstates it and no cell-level claim rests on it. The gate numbers across the documentation and the card's "base rate 0.30" line are documentation items (M4, T-068).
11. Reproduction (R4). From a clean clone, a fresh download and an empty data root, every number regenerated except one stale deployment-shaped guard-off ablation written by the run-4 bundle (two printed digits move); run 6 regenerates every number from one code state in one run folder with the leakage audit and the run log inside it (PENDING-T076). The minors (the cross-platform number, the leakage audit's source, the mixed code states of the timed run, the dated model ids, the absolute table headers) are answered by call 239, run 6, an Appendix E sentence and call 240; the nits by calls 241 to 243, dated corrections in the round-00 letter, and the wording "one command per table".
12. Process and venue (R5 m6, m7, m8, m9 and nits). The abstract is cut from 434 to about 370 words with fewer stacked numbers; the cross-platform claim no longer carries a number (a per-platform report from the continuous-integration job has no task yet); Section 10 gains a benchmark-artifact paragraph; the two uncited bibliography entries are removed; the title is kept as the benchmark's name. The two incorrect lines of the round-00 letter are answered in the round-01 letter and listed for correction.

### Items with no task yet (as written in part 1; the list at the end of the response letter is current as of part 2a, where calls 205, 235 to 240 and the public registration closed most of these)

- The event rate by year as a column of the year table, and a sentence on what the drift rule cannot see (R1 m8; the sentence is in, the column is not).
- The pooled paired P2 minus P1 interval over all rows in Table 1 or Section 6.2 (R1 m7; the admitted-pairs interval is quoted instead).
- A per-platform score report written by the continuous-integration job (R5 m8).
- The cautionary run at 500 resamples (R3 m7; the learning curve's 500 is in T-062).
- A single-headline run of the challengers (R3 m6) and a stronger text representation as a fourth challenger (R5 M4, optional).
- The module docstring of the precedent rung (R3 nit 2).
- The round-00 letter's two lines (R5 m7), outside the files of this pass.
- The single-column style, checklist and artifact statement of the target track (R5 m9); the artifact paragraph is in.

## What every reviewer asked to keep

The per-row score file and the source comments (R1, R3), one code path for the join and the replay and the withheld block (R2), the guard-pairs table and the guard-off variants of every ablation (R3, R5), the cautionary run as a named contribution (R5), the honest treatment of the deployment-shaped archive and of the four flagged weeks (R2, R5), the executable tutorials and the report card that carries no ledger content (R6), and the boundary sentence (R5).

## Part 2b (run 6)

Every number of the paper now comes from `paper/data/run6-forward-chaining`, one code state under the forward-chaining default (call 206), the timed run at the final commit included (2,052 seconds in all, an upper bound measured under load; Appendix E quotes it). P0, P1 and the challengers are unchanged to the last digit; the precedent rung equals the prior on skill and on the log score within the interval (plus 0.0004 nats, minus 0.0003 to 0.0012), the eight admitted pairs' realized difference is plus 0.0010 (minus 0.0007 to 0.0025) with a location part of plus 0.0036 and a scale part of minus 0.0026, decision value is read against the arm-count-matched random order (the text classifier plus 0.040 and the boosted model plus 0.028 confirmed; the precedent rung plus 0.014 and the local set plus 0.015 unresolved), the learning curve is scored against the full-history base rate (P2 above P1 from 2,991 rows), the positive control admits a one-percent lift in 97 percent of cells at the size of the real cell and the rung recovers 0.18 of the oracle's gain, and the deployment-shaped guard-off ablation is regenerated (4.7172). No marker remains in the paper.
