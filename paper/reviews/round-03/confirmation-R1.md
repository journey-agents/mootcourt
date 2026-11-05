# Confirmation pass on release 1.0.0, Reviewer R1

Reviewer: R1
Role: statistician
Commit: c7dbfd0 (release 1.0.0 is tag v1.0.0 at d9d06ed; c7dbfd0 adds the Zenodo DOI line)
Date: 5 November 2026

No new blocking or major finding.

## 1. Round 03 findings at c7dbfd0

R1-F1 [minor, R1.15], marked Fixed. Closed. Section 9 (`paper/sections/limitations.tex:9`) reads H1 part 1 with the paired difference, "plus 0.068, 0.038 to 0.097, and clear of zero at all nine origins"; H3 part 1 as "the ECE of issued cards falls inside the central 90 percent of the null at 4 of the 8 origins that issue cards, not at most of them, and pooled it sits at the 100th percentile of the clustered null, so the first part fails"; H3 part 2 with the coverage intervals, "81 percent, 80 to 82, and 89 percent, 89 to 90, within 5 points of nominal"; and H4 part 3 as "14 percent pooled and 8.8 percent after the burn-in origin". The two shipped keys in `paper/data/run7-tie-rank/paper-extras-upworthy-20261103-4bfb354b87e3.json` hold them: `p1_minus_p0_by_origin` (`bootstrap_resamples` 500, `by_origin_clear_of_zero` 9, `by_origin[origin=2015-01-01].difference` 0.068106, lo 0.038382, hi 0.097183) and `issued_ece_by_origin` (`null_draws` 500; `issued.pooled.ece` 0.015076 at `ece_percentile` 100.0; `issued.origins_inside_central_90` 4 of 8; `all_rows` 4 of 9). Every value equals my own round 03 recomputation to the digits I printed (narrowest origin plus 0.0681, 0.0384 to 0.0972; issued percentiles 92.2, 100.0, 27.4, 92.9, 100.0, 95.8, 99.6 and 79.3; pooled issued ECE 0.01508). A key-by-key diff of the extras file against a839b2c shows only the two new keys and the header changed. Register rows C27, C30 and C33 requoted, C130, C131, C133 and C134 added. The sentences are in the released PDF.

R1-F2 [minor, C105], Fixed. Closed. `paper/sections/discussion.tex:4` reads "precedents that add nothing measurable pooled on this archive"; C105 requoted with the two measurable pairs named.

R1-F3 [minor, R5.7], Fixed. Closed. The caption at `paper/sections/appendix.tex:427` reads "the spread of that skill over the 20 seeds (blank at the full history, which is one fit)"; in the PDF.

R1-F4 [nit, R5.12], Fixed. Closed. The paragraph "One reading rule changed after the data were seen" occurs once in `paper/main.tex` and once in the PDF text extracted in reading order; a second sentence now states that the plan fixed the hypotheses and no reading rule.

R1-F5 [nit, R1.14, C15], Fixed. Closed. The abstract (`paper/main.tex:31`) reads "the prior, one number per cell, sits at it (minus 0.004, within noise)"; the H5 verdict reads "failed for the prior, which ranks by cell only ... and sits at the matched order within noise (minus 0.004, minus 0.012 to 0.005)"; the key `tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung=P1].diff_matched` is minus 0.004270 (minus 0.012137, 0.005350); C15 re-keyed to it, C38 requoted, C129 added.

R1-F6 [nit, R1.14, R5.12], Fixed. Closed. `paper/sections/ablations.tex:11` reads "the one Brier skill interval above zero ... (the two below zero, the prior-shape and the cautionary rows, are read in their own places)" and "whose intervals clear zero in the rung's favour"; contribution 3 (`paper/main.tex:49`) reads "the two paired intervals in the rung's favour read as descriptive"; `paper/tables/ablations-upworthy.tex` prints the paired column to five decimals, the kappa rows reading 0.00069 (minus 0.00002, 0.00138) and 0.00069 (minus 0.00002, 0.00137), which the PDF carries; the caption (`paper/sections/appendix.tex:411`) says why.

Six of six closed; nothing argued.

## 2. Rubric R1.1 to R1.15 at c7dbfd0

- R1.1 Pass. The headline report is unchanged (sha256 prefix 9e7e6e28deafb7a1, as at a839b2c); the only run-folder files changed are the extras file (two new keys) and one README line; every existing extras key is byte-identical to a839b2c, so my round 03 recomputations stand, and the two new keys match my independent numbers. Table guard-pairs-rows now prints the pooled interval from `guard_pairs.summary` (minus 0.0007, 0.0025) in place of its own resampling (minus 0.0007, 0.0027), so both tables carry one interval.
- R1.2 Pass. `scripts/claims_audit.py` exits 0 on 135 rows (127 keyed; C135, a design claim without a key, came with the one Discussion sentence of d9d06ed); `scripts/paper_audit.py --run paper/data/run7-tie-rank` reports 771 numbers checked, 0 unmatched, 107 sources resolved, 0 unresolved. Contribution 3's rows C21 to C23 carry no number, and the numbers they summarize are registered where printed.
- R1.3 Pass. Both new keys state 500 resamples, and the admitted pairs' pooled interval is one draw for both tables.
- R1.4 to R1.13 Pass, unchanged since round 03; no number or table they read moved.
- R1.14 Pass. The two wordings of my nits are gone; "equals" remains only where the weight is zero everywhere.
- R1.15 Pass. Each part of H1, H3 and H4 that I named is read by name with its measure, number and interval; Section 5 now states that H2's final-origin part and H3's most-origins part are read pooled under the paper's rule, and Section 9 reads H3's first part by origin as well.

No item fails.

## 3. Open items at the cap

None of the four open items touches my role: the appendix numbering (R5.12), the two post-launch display fields (R2.14), the sample ledger's base rate (R6.4) and the round 02 letter correction (R4). The two items of mine the triage classed as open, the per-origin keys for H1 part 1 and H3 part 1, were shipped and are not open. The argued list of Section 9 (`paper/sections/limitations.tex:28`) may stay as written for publication. My remaining suggestions (the closed form of the positive control's ceiling per cell, the first-order scaling of a cell's gates, the equal-mass ECE columns, the by-origin table's 200 resamples) are suggestions and need no listing.

## 4. Verdict

Recommendation: accept
Scores (1 to 5): novelty 3, correctness 4, rigor 4, clarity 4, reproducibility 5, code 4
High-quality paper worth publishing at a top venue: yes. A datasets-and-benchmarks track is the venue I have in mind: every number traces to a shipped report and recomputes from the per-row score table, every hypothesis part is read in the measure it registered with its interval, and the headline negative is stated at the size the data support with its intervals, families and floors beside it.
High-quality code package worth publishing: yes. The package regenerates every table from the reports with one command per table, ships the per-row scores, the leakage audits, the claims register and two audits that catch a moved digit, and reproduced to every printed decimal in two rounds of independent recomputation.
Remaining concerns: [suggestion] print the closed form of the positive control's ceiling per cell and call it the normal approximation, since the refit oracle exceeds it in every cell; [suggestion] say in Section 6.2 that a cell's gates are a first-order scaling of the simulated ones; [suggestion] the by-origin table of the report uses 200 resamples where everything printed uses 500.
