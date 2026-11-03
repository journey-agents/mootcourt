# Round 00 summary (preliminary round, 3 Nov 2026)

Paper version f3c8718, code version f3c8718. Four of six reviewers (R1, R2, R3, R5); R4 and R6 wait for the traceability and documentation chunks. All four recommend major revision.

| Reviewer | novelty | correctness | rigor | clarity | reproducibility | code | recommendation |
|---|---|---|---|---|---|---|---|
| R1 statistician | 3 | 2 | 3 | 3 | 4 | 4 | major revision |
| R2 platform engineer | 3 | 3 | 3 | 4 | 4 | 3 | major revision |
| R3 ML reviewer | 3 | 3 | 3 | 4 | 4 | 4 | major revision |
| R5 area chair | 3 | 4 | 4 | 3 | 4 | 4 | major revision |

## Blocking findings

1. R1: coverage runs from 1.00 to 0.66 across deciles of realized over planned standard error; the pooled coverage hides a gradient the protocol forbids.
2. R1: the precedent rung's loss against P1 is confounded with a change of predictive family (Student-t at lambda 0, Normal above), about 0.076 of the 0.085 nats lost at lambda 0.2.
3. R2: the live join scores issued cards only while the replay scores every card, so a stale or drifted cell never recovers in the released loop; the paper does not state the difference.
4. R3: the challengers' decision value is computed but omitted; text_lr (0.286) and local_eb (0.280) capture more lift than random (0.251), so the flat refutation of H5 does not stand.
5. R5: the scored P0 is not the base rate the skill numbers are measured against, so P0's skill of minus 0.124 is unexplained and the strict-nesting claim fails at P0 to P1.

## Major findings (grouped)

- Gates simulated at base rate 0.3 against an archive rate near 0.09 (R1, R5).
- Decision value without intervals; random order is K over n by construction; P1's p_win is constant within a cell (R1, R3, R5).
- Calibration: the ECE null ignores clustering by test (R1); "calibrated" in the title and abstract against an ECE null rejected at the 100th percentile (R5).
- The abstract's absolute no-leakage sentence against the disclosed stand-ins; the exposure proxy correlation is 0.215 on ASOS against 0.099 on Upworthy; admission on realized clicks conditions the scored set on the outcome (R2, R5).
- Replay scores a Normal rebuilt from the card interval; card intervals are theta intervals while the backtest covers the observed estimate; no released interface takes a row id, so the join cannot close; a same-method refit is never promoted; the card skill line prints a bare number (R1, R2).
- Ablations run behind the guard so the ablated setting rarely reaches a forecast; the feature space never reads the reference headline; the GBM is untuned and uncalibrated while challengers get no fallback; no positive control (R3).
- More than forty unadjusted intervals read with the excursions singled out (R1).
- Three 2026 pre-launch screening systems from the landscape survey uncited against the novelty claim (R5).

## Disposition

Every blocking and major finding with a code component is a criterion of task T-054 (chunk L), followed by a full rerun. The paper-only findings (framing, title, abstract, citations, figures, test counts, venue) go to the paper's third pass, which also writes the response letter for this round. Venue decision: reframe as a benchmark and protocol paper for the NeurIPS Datasets and Benchmarks track, with CODE@MIT for the talk, as R5 recommends.
