# Paper plan: Moot Court

Working title: Arguing from precedent: calibrated pre-launch forecasts of A/B test outcomes with abstention, evaluated on two public experiment archives

Status: plan written 2 Nov 2026, before the real-data runs. Numbers in this file are targets and hypotheses, not results. Every number in the paper comes from a report JSON produced by the released code.

## 1. Research questions

RQ1 (skill). Does the ledger of concluded experiments carry out-of-time predictive skill about the next experiment's result, and how does skill grow along the ladder P0 (base rate), P1 (empirical-Bayes prior), P2 (weighted precedents)?

RQ2 (calibration). Are the issued probabilities calibrated against a perfect-calibration null, and do the 80 and 90 percent intervals cover the observed estimates at their nominal rates?

RQ3 (abstention). Does abstaining on the four triggers (support, novelty, reliability, decision instability) improve the quality of what is issued, and at what abstention rate?

RQ4 (decision value). If the launching team can run only a fraction of its candidate tests, how much of the realized positive lift is captured by prioritizing on the predicted win probability, compared with random order and with an oracle, and what is the regret?

RQ5 (data efficiency). How many concluded contrasts are needed before a skill claim is decidable, and does the empirical learning curve match the power simulation's gate sizes?

RQ6 (transfer). Does the method behave honestly on a deployment-shaped archive with few experiments (ASOS): undecidable gates, abstention, no false skill claims?

## 1a. Methodological finding from the first real run (3 Nov 2026), to be a contribution of the paper

On the first Upworthy run the effect was relative lift against the earliest-created reference arm and the harness used each row's realized standard error as s_star. By decile of that standard error the mean effect ran from minus 41 percent (most precise) to plus 104 percent (least precise), the significant-positive rate from 0.4 to 16 percent, and the empirical-Bayes rung predicted the opposite gradient (p_sig 0.16 down to 0.02), so its Brier skill against the base rate was negative. The cause is mechanical: a ratio against a noisy reference couples the effect with its own standard error through the reference's realized click-through rate, and realized precision is in-test information that no pre-launch forecaster may consume. The paper states this as a result: pre-launch forecasts must be scored with a planned-exposure standard error and a pre-launch level estimate, on an effect scale whose noise does not depend on the realized reference, and every report must show calibration by precision. The second run (task T-032) implements that design. Both runs are reported, the first as the cautionary case.

## 2. Hypotheses to be confirmed or refuted by the runs

H1. P1 beats P0 on log score at every origin after burn-in on Upworthy; P2 beats P1 on the headline_only cell where text features carry signal, and does not beat P1 on image_only.
H2. Brier skill of P2 against the base rate is positive and its 90 percent bootstrap interval clears zero at the final origin on Upworthy; the released gate (power 0.90) is decidable there.
H3. ECE of issued cards falls inside the central 90 percent of the perfect-calibration null at most origins; 80 and 90 percent coverage are within 5 points of nominal.
H4. Issued cards have higher skill than the full set; abstained rows have lower skill when forced; abstention rate is below 30 percent after burn-in.
H5. Prioritizing by p_win captures more positive lift than random at K = 25 percent of tests, with regret against the oracle reported as is.
H6. On ASOS every gate is undecidable and P2 equals P1 (cell-only features); the paper reports this as the expected outcome.

If a hypothesis fails, the paper reports the failure and the reason found; no hypothesis is dropped from the paper after the runs.

## 3. Experiments (each is one command of the released code, logged to reports/)

E1 Skill ladder: rolling-origin backtest on Upworthy, quarterly origins, all rungs, per cell. Outputs: log score, CRPS, Brier skill with floor, direction accuracy with ceiling, bootstrap-by-test intervals.
E2 Calibration and coverage: reliability diagrams per rung at the final origin, ECE and its null percentile, coverage of 80 and 90 percent intervals by origin.
E3 Abstention analysis: skill on issued vs forced-on-abstained rows; trigger frequency table; abstention rate by origin and cell; ablation that removes one trigger at a time.
E4 Decision value: lift captured and test-and-roll regret for random, p_win and oracle policies at K in {10, 25, 50} percent, by origin.
E5 Learning curve: skill as a function of ledger size at the final origin, by subsampling the visible ledger at fixed fractions with 20 seeds, overlaid with gate sizes from the power simulation at both targets.
E6 Ablations: (a) features: text only, structured only, both; (b) kernel bandwidth multiplier fixed at each grid value vs selected; (c) lambda fixed at 0, 0.5, 1 vs selected; (d) pooling kappa in {0, 20, 100}; (e) Student-t vs Normal prior; (f) gradient-boosted challenger (the `--challenger gbm` path) against the ladder.
E7 Drift: skill by calendar year; what the weekly loop would have flagged in a replay of the archive at weekly joins.
E8 ASOS: the full harness on the deployment-shaped archive; expected undecidable; report the direction accuracy and coverage anyway.
E9 Synthetic truth: calibration and recovery of mu, tau on simulated ledgers; gate power at both targets; the P3 forecaster demonstration (labelled synthetic).
E11 Second opinion from a response-simulation agent (optional, only if an agent is attached): recorded run over the rolling-origin request set, scored alone and stacked at the earned weight, with scores split into origins before and after the agent's knowledge cutoff (contamination). Reported only with that split and the limitation sentence; never folded into the main skill table.
E10 Cost: wall time per stage, card latency with a preloaded bundle and through the service.

E12 Head-to-head baselines demanded by the novelty check (paper/related-work.md): (a) comparison-set empirical Bayes, a prior fit only on the k nearest past experiments in feature space without the kernel shrinkage to the cell prior (the local empirical Bayes line of work); (b) a text-only winner classifier, TF-IDF plus logistic regression trained on visible rows to predict P(variant beats reference), the shape used by prior text-based Upworthy winner prediction; (c) the gradient-boosted challenger already in the harness. All three run on the same rolling-origin splits as the ladder and are scored with the same scores on the direction and significant-positive events, so the comparison is on matched splits. The paper credits the base-rate-as-prior idea to its origin.

## 3a. Adoption workstream (goal extension, 2 Nov 2026)

The paper gains a short practitioner section and the repository gains the adoption layer: a vendor-neutral ledger exchange format with importers for the exports of the platforms organizations already use, an init and doctor command for a one-day pilot, a standardized benchmark report card any organization can run privately on its own ledger and publish without data, packaging with CI and Docker, a documentation site, multi-metric guardrails, and a scale benchmark at 1e5 and 1e6 contrasts. The landscape survey (docs/landscape.md) feeds both the related-work positioning and the gap table in the paper.

## 4. Paper structure (target: 9 pages plus references and appendix, two-column)

1. Introduction: the ledger nobody reads before the next test; the card; the boundary (prioritize and size, never decide).
2. Problem setting and data: contrast, cell, origin, admission, the two archives and why they are complementary.
3. Method: ledger and snapshots; the ladder with each rung a strict generalization; abstention; the card.
4. Evaluation protocol: rolling origin, scores, floors and ceilings, calibration null, gates from power, circularity concession, decision value.
5. Results: E1 to E8 with figures.
6. Ablations and learning curve: E5, E6.
7. Discussion: what headline tests can and cannot say about product deployments; when to abstain; operational loop.
8. Limitations and ethics: aggregate data only, archive norms respected (no confirmatory or holdout data), no decision automation.
9. Reproducibility: one command per table; checksums; versions.

## 5. Review protocol (simulated red team)

Five reviewer personas, each producing a scored review on a 1 to 5 scale for novelty, technical correctness, experimental rigor, clarity, reproducibility and code quality, with a recommendation in {reject, major revision, minor revision, accept}:
R1 statistician (empirical Bayes, scoring rules, calibration, multiple comparisons);
R2 experimentation platform engineer (operational realism, leakage, admission, drift, latency);
R3 machine learning reviewer (baselines, ablations, learning curves, fair challengers);
R4 reproducibility chair (runs the code from a clean clone, checks every number against the report JSON, license and data norms);
R5 area chair for the venue (significance, fit, writing, honesty of claims).
Loop: write or revise, run all five, collect findings, fix code and text, re-run the affected experiments, repeat. Stop condition: every reviewer recommends accept or minor revision with no remaining correctness or reproducibility finding, and the code package passes R4's clean-clone run. Each round is logged in paper/reviews/round-NN/ with the five reviews and the response letter.

## 6. Venue candidates (decide after results)

Primary: KDD applied data science track or the Web Conference (industry and applied tracks value measured decision value on real archives). Also: CODE@MIT (Conference on Digital Experimentation) for the experimentation audience; the NeurIPS Datasets and Benchmarks track if the benchmark framing (public archives, rolling-origin protocol, gates) is the main contribution. Format follows the chosen venue's template.

## 7. Writing rules

No em dash or en dash anywhere. The role noun spelled o-w-n-e-r never appears; use "the launching team". No company, team or person is named as the intended reader. Every number traces to a report JSON path. Every citation is fetch-verified (paper/related-work.md). Claims about product deployments are limited to what the ASOS archive supports.
