# Paper version 2: plan, fixed before the new results exist

Written 6 November 2026, before any run below. Inputs: the logic review (`.claude/fleet/logic-review.md`), the fidelity check (`format-pass-g.md`), the outside review excerpts (`.claude/fleet/muse-review/`) and the archive's June 2024 notice. There is no date target: the paper ships when it is right.

## Why

1. **The archive's 2024 randomization notice is not handled.** The archive's maintainers report evidence of randomization problems in about 22 percent of tests and discourage causal or confirmatory use of tests from 25 June 2013 to 10 January 2014. The OSF file we read dates from 2021 and has no flag column, so the loader's `imbalance_flag` never fires. 1,050 of the 4,873 exploratory tests (21.5 percent) started in that window, and the paper does not say so.
2. **The argument overreaches** in the ways the logic review lists.

## Decisions fixed now, before seeing any new number

- D1. The main analysis excludes the window: a test started from 2013-06-25 to 2014-01-10 inclusive gets admission status `imbalance_flag` (rows kept and counted, not scored). Run 7's configuration stays as an ablation, `include-randomization-window`, and must reproduce run 7's numbers.
- D2. Whatever the result, the paper reports both, main first. D1 does not change after the numbers are seen.
- D3. All nine origins stay on the calendar. An origin with too few tests is reported as such; no origin is dropped by hand.
- D4. The existing rung definitions, guard and settings do not change in this plan. A method change found useful here goes to a later version.

## Experiments on the exploratory split (run 8, one code state)

| id | experiment | answers |
|---|---|---|
| X1 | The whole pipeline under D1; run 7's configuration as the ablation | the notice |
| X2 | Two single-change runs: relative lift at planned precision; absolute effect at realized precision | which choice makes the reversal (review G9) |
| X3 | Exposure fixed at the cell median | what the realized-exposure stand-in does to each score, and whether P1's within-cell AUC rests on it (G8) |
| X4 | The prior's family on the standardized effect | whether the Student-t gain is heavy-tailed effects or a mixture over the click-through level (E8) |
| X5 | Paired P2 minus P1 and text classifier minus P1 in captured lift at each budget, by test, with adjusted bounds; P2 rows in the decision tables; an exposure-only (s*) policy beside the arm-count policy; decision value on the planted ledgers | ranking (E11, G5, G11) |
| X6 | Abstention: abstained against issued excluding burn-in, and within origin-and-cell strata; skill read against one common baseline | composition claim (G7, outside review) |
| X7 | Gates at each stratum's own dependence; adjusted intervals for each cell; one gate rule throughout | outside review |
| X8 | A calibration null whose event rates follow the trailing window (drift matched), beside the current null, for P0, P1 and P2 | whether the rejection is calibration or drift (outside review) |
| X9 | Paired P2 minus P1 on the learning curve; within-origin AUC for the 2015 skill; the lowest reliability bin | G10, G14, G15 |
| X10 | Sizing evaluation: does the predicted distribution improve test size choice? Design in X10's own note below, reviewed before running | G1 |

### X10 design requirements

Sizing cannot be replayed on concluded tests, because each ran once at one size. The builder writes a short design note first, for the lead's review, covering at least: (a) out-of-time assurance, that is whether the forecast probability of significance at the planned size matches the realized rate across exposure bins; (b) test-and-roll sample sizes (Feige and McDowell) computed from each origin's out-of-time prior, compared by simulation with sizes from the base rate and with a fixed power rule, with regret measured under a data-generating distribution that does not equal the prior being tested. If the design cannot give a fair answer the paper says sizing is not evaluated and drops the claim.

## Confirmatory split

Not opened by this plan. The archive routes it through Registered Reports reviewed by a journal. Opening it is a separate decision recorded here when made, after this plan's analysis is frozen and registered publicly.

## Text

After run 8: every ERROR, GAP, CUT and UNCLEAR of the logic review, the remaining findings of the fidelity check, the outside review's findings and the reordering (verdicts before discussion; a conclusion at the end); three research questions lead the introduction and discussion. Every number traces to a report key; a source line is checked against the claim it documents, because the digit audit can pass on a wrong source.

## Review

Fresh independent readers with no rubric read the result sentence by sentence; the outside reviewer reads it again. No verdict from before this plan carries over.
