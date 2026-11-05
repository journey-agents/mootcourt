# Simulated red-team review protocol

Each round reviews two artifacts together: the paper (paper/main.pdf built from paper/main.tex) and the code package (the repository at the commit named in the round file). Six reviewers read independently, with fresh context, and never see each other's reviews before writing their own. A round is stored in paper/reviews/round-NN/ as six review files, one summary file, and one response letter.

## Reviewers

R1 Statistician. Empirical Bayes, proper scoring rules, calibration, multiple comparisons, bootstrap validity with clustered contrasts, the floors and ceilings, the circularity concession. Must recompute at least one headline number from the report JSON.
R2 Experimentation platform engineer. Operational realism, leakage, admission, horizon discipline, drift, registry, freeze at issue, latency, what a launching team would misuse. Must trace one card from issue to outcome in the code.
R3 Machine learning reviewer. Baselines and challengers on matched splits, ablations, learning curves, feature leakage, fairness of the comparison with prior text-based predictors, the ladder claim that each rung is a strict generalization.
R4 Reproducibility chair. Clean clone, environment, `make data fit backtest`, every table and figure regenerated from a report JSON, checksums, licenses, data norms (the archive splits deliberately not used), writing rules, test suite, wall time within the stated budget.
R5 Area chair. Significance of the contribution, honesty of the claims against the results, fit to the venue, clarity, related work coverage and credit, limitations, ethics.
R6 Practitioner and documentation reviewer. A data scientist at a company with an experiment archive who has never seen the project. Follows README and the tutorials from a clean clone with no other context: the five-minute quickstart, the bring-your-own-archive tutorial, the weekly loop and the service. Judges whether a new user understands what the package does and can run it on their own results within an hour, whether the manual answers the questions that come up, and whether the outputs are understandable without reading the paper. A tutorial step that fails or an output a reader cannot interpret is a major finding. Scores clarity and code quality; reports the wall time of the walkthrough.

The same six reviewers continue across rounds; each receives its own previous review and the response letter, verifies each of its previous findings first (closed or not closed, with the evidence), then runs its rubric section of paper/reviews/rubric.md, then may add findings that name a claim or a rubric item. Round 03 adds one fresh area chair, bounded by the rubric, as the independent check.

## Scores

Each reviewer scores six dimensions from 1 to 5: novelty, technical correctness, experimental rigor, clarity, reproducibility, code quality. Each reviewer gives a recommendation: reject, major revision, minor revision, accept. Each finding carries a severity fixed by paper/reviews/rubric.md: blocking only for leakage, a number that does not reproduce, or a claim the evidence does not support; major only for an experiment the rubric names that is missing or defective; minor for presentation, wording, structure and the other items the rubric names; nit for naming and formatting. Every finding cites the claim id (paper/reviews/claims.md) or the rubric item id it rests on; a finding that cites neither is a suggestion, recorded in the letter under "Suggestions", never fixed in the round and never counted toward the stop condition.

## Stop condition

The loop stops when, in one round, all six reviewers recommend accept or minor revision, no blocking or major finding remains, every rubric item passes for every role, every finding of the round names the claim it weakens or the rubric item it fails (a finding that names neither is a suggestion and does not count), R4 reports a clean-clone run that regenerates every number in the paper, every number in the paper traces to a report JSON path, and every claim in paper/reviews/claims.md is supported as written. If any reviewer disagrees, the round's response letter answers every finding (fixed, with the commit; or argued, with the reason; or suggestion, with no change in the round), the affected experiments are re-run at the cheapest verification tier that proves the change, and a new round begins. The loop runs at most two further rounds after round 01; at the cap, open minors are listed in the letter and in the limitations section and the paper is released; an open major at the cap is a decision for the launching team, written up with the options (fix and run one more round, or argue and release). The log of rounds is part of the paper's supplementary material. After the cap round's fixes are released, each reviewer reads the released commit once more, verifies its own findings there and records a final verdict with two fixed questions (a high-quality paper worth a top venue; a high-quality code package worth publishing); this confirmation pass raises no new round, and a finding it raises is fixed in the commit that records the pass or listed with the open minors.

## Review file format (one per reviewer)

```
# Round NN, Reviewer Rk: <role>
Paper version: <git commit>   Code version: <git commit>
Scores: novelty n/5, correctness n/5, rigor n/5, clarity n/5, reproducibility n/5, code n/5
Recommendation: <reject | major revision | minor revision | accept>
## Summary (five sentences, in the reviewer's own words, of what the paper claims and shows)
## Verification of previous findings (from round 02 on: each of this reviewer's previous findings, closed or not closed, with the evidence)
## Findings
- [blocking|major|minor|nit] [Rk.n and/or Cj] <where: section, table, file:line> <what is wrong> <what would fix it>
## Suggestions (what names no claim id and no rubric id; not fixed in the round)
## Questions for the authors
## What is good (so it is not removed in revision)
```

## Response letter format

For every finding, in the reviewers' order: the finding quoted in one line with its claim or rubric id, then "Fixed:" with the change and commit, or "Argued:" with the reason and, where possible, the number that settles it, or "Suggestion:" with no change in the round. Re-run experiments are listed with their new report JSON paths. The letter ends with the diff of the paper's claims between rounds, by claim id. The round's summary file carries the convergence table: open findings by severity, rubric items passed per role, claims supported as written, and numbers changed since the previous round.

## Writing rules (also enforced on the reviews)

No em dash or en dash. The role noun spelled o-w-n-e-r never appears. No company, team or person is named as the intended reader. Reviews quote numbers from the report JSON, not from memory.
