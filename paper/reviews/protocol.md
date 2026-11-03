# Simulated red-team review protocol

Each round reviews two artifacts together: the paper (paper/main.pdf built from paper/main.tex) and the code package (the repository at the commit named in the round file). Five reviewers read independently, with fresh context, and never see each other's reviews before writing their own. A round is stored in paper/reviews/round-NN/ as five review files, one summary file, and one response letter.

## Reviewers

R1 Statistician. Empirical Bayes, proper scoring rules, calibration, multiple comparisons, bootstrap validity with clustered contrasts, the floors and ceilings, the circularity concession. Must recompute at least one headline number from the report JSON.
R2 Experimentation platform engineer. Operational realism, leakage, admission, horizon discipline, drift, registry, freeze at issue, latency, what a launching team would misuse. Must trace one card from issue to outcome in the code.
R3 Machine learning reviewer. Baselines and challengers on matched splits, ablations, learning curves, feature leakage, fairness of the comparison with prior text-based predictors, the ladder claim that each rung is a strict generalization.
R4 Reproducibility chair. Clean clone, environment, `make data fit backtest`, every table and figure regenerated from a report JSON, checksums, licenses, data norms (the archive splits deliberately not used), writing rules, test suite, wall time within the stated budget.
R5 Area chair. Significance of the contribution, honesty of the claims against the results, fit to the venue, clarity, related work coverage and credit, limitations, ethics.

## Scores

Each reviewer scores six dimensions from 1 to 5: novelty, technical correctness, experimental rigor, clarity, reproducibility, code quality. Each reviewer gives a recommendation: reject, major revision, minor revision, accept. Each finding carries a severity: blocking (a correctness, leakage or reproducibility defect, or a claim the results do not support), major (a missing experiment, baseline or analysis the conclusions need), minor (presentation, wording, structure), nit.

## Stop condition

The loop stops when, in one round, all five reviewers recommend accept or minor revision, no blocking or major finding remains, R4 reports a clean-clone run that regenerates every number in the paper, and every number in the paper traces to a report JSON path. If any reviewer disagrees, the round's response letter answers every finding (fixed, with the commit; or argued, with the reason), the affected experiments are re-run, and a new round begins. The log of rounds is part of the paper's supplementary material.

## Review file format (one per reviewer)

```
# Round NN, Reviewer Rk: <role>
Paper version: <git commit>   Code version: <git commit>
Scores: novelty n/5, correctness n/5, rigor n/5, clarity n/5, reproducibility n/5, code n/5
Recommendation: <reject | major revision | minor revision | accept>
## Summary (five sentences, in the reviewer's own words, of what the paper claims and shows)
## Findings
- [blocking|major|minor|nit] <where: section, table, file:line> <what is wrong> <what would fix it>
## Questions for the authors
## What is good (so it is not removed in revision)
```

## Response letter format

For every finding, in the reviewers' order: the finding quoted in one line, then "Fixed:" with the change and commit, or "Argued:" with the reason and, where possible, the number that settles it. Re-run experiments are listed with their new report JSON paths. The letter ends with the diff of the paper's claims between rounds.

## Writing rules (also enforced on the reviews)

No em dash or en dash. The role noun spelled o-w-n-e-r never appears. No company, team or person is named as the intended reader. Reviews quote numbers from the report JSON, not from memory.
