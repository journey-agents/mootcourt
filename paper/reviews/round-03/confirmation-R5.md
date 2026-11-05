# Confirmation pass, Reviewer R5

Reviewer: R5
Role: area chair
Commit: c7dbfd0 (release 1.0.0 plus the Zenodo DOI line; tag v1.0.0 is d9d06ed)
Date: 5 November 2026

No new blocking or major finding.

## 1. The round 03 findings at c7dbfd0

- R5-F1 [C3, R5.1], letter mark Fixed. Closed. The abstract (paper/main.tex line 29) reads "in which no in-test outcome reaches a pre-launch forecast (one stand-in, realized exposure, its leak measured)", contribution 1 (line 45) reads "a planned-exposure standard error (from realized exposure where the archive records no plan, a stand-in whose leak Section 9 measures)", and rows C3 and C19 of paper/reviews/claims.md quote both as printed; PDF page 1.
- R5-F2 [C15, R5.1], Fixed. Closed. The abstract (line 31) reads "the prior, one number per cell, sits at it (minus 0.004, within noise)"; C15 is re-keyed to tables.decision_value[origin=ALL,budget=0.25,policy=p_win,rung=P1].diff_matched (minus 0.004270, minus 0.012137 to 0.005350) and requoted, C38 reads "failed for the prior, which ranks by cell only ... and sits at the matched order within noise (minus 0.004, minus 0.012 to 0.005)", C129 keys the interval; Section 9 (sections/limitations.tex line 9) carries the same wording.
- R5-F3 [R5.2, R5.7], Fixed. Closed. The paragraph "One reading rule changed after the data were seen" occurs once in paper/main.tex (line 126; grep count 1) and once on page 5 of the PDF built at c7dbfd0.
- R5-F4 [R5.5], Fixed. Closed. sections/limitations.tex line 28 lists among the argued items "the two post-launch display fields of the deployment-shaped archive (the checkpoint count and the final offset in days), kept at the top level of its features outside the post-launch block until the next snapshot-changing release, because moving them rewrites every snapshot id the run folders cite, with the reading side closed by the feature allow-list and its test", and the future-work sentence names "the within-origin-and-cell comparison of issued against withheld rows, on which the reading of the fourth hypothesis's reversal as composition in part rests"; the one-runner-image job stays in Section 10, which I accept.
- R5-F5 [R5.9], Fixed. Closed. paper/reviews/round-02/response.md line 230 opens "Corrections of 5 November 2026, after round 03 (R5-F5 under R5.9; R3-F1 under R3.3)" and gives the built order (2, 3, 4, 1, 5, 6, 7, 8, 39, 9, 10, 11, 12, 40) and one counting rule (whitespace-separated words of the abstract's text lines, comment lines removed: 250 at a839b2c and after pass 12); the register's pass 10 note (claims.md line 151) states the rule. My count at c7dbfd0 is 250.

Closed 5, not closed 0, argued 0.

## 2. Rubric R5.1 to R5.13 at c7dbfd0

- R5.1 pass: scripts/claims_audit.py exits 0 (135 rows, 127 keyed; C135, the Discussion sentence on the monitor benchmark, was added by d9d06ed after the letter's count of 134, keyed none with a source comment naming the cited paper's Section 5 and Table 3); scripts/paper_audit.py reports 771 numbers, 0 unmatched, 107 sources resolved, 0 unresolved (the letter's 769 predates the DOI line's two numbers). The abstract, the four contributions (contribution 3 now carries no numbers), the six verdicts and the conclusion read against their rows say no more than their keys hold.
- R5.2 pass: hypotheses stated once and verbatim, the disclosure once, verdict counts one confirmed, four in part, one refuted; the record sentence now also says the pooled-interval reading rule was fixed in the paper after the data were seen because the plan fixes none.
- R5.3 pass: 84 bibliography entries, 84 cited, none dangling; the three entries added since a839b2c carry fetch records (paper/related-work.md lines 365 to 367).
- R5.4 pass: sections/related-work.tex lines 10 and 20 unchanged in substance; no further challenger promised.
- R5.5 pass: the argued list carries every argued item of the three letters, the two open items at the cap, the stand-ins with 0.099, 0.215 and 0.152, what is not built and what was not run.
- R5.6 pass: sections/limitations.tex line 34 unchanged.
- R5.7 pass: 250 words, three intervals, 62 labels all referenced, acronyms defined at first use, "log score" throughout.
- R5.8 pass: the artifact paragraph (sections/reproducibility.tex line 12) now also names the release DOI 10.5281/zenodo.23988587 and the concept DOI.
- R5.9 pass: the round 03 letter answers 40 findings in the reviewers' order with the three marks only (no "Fixed in part"), quotes keys that resolve, and ends with the claims diff by id.
- R5.10 pass: the verdict below rests on no open finding of mine.
- R5.11 pass: title and the negative-first abstract unchanged.
- R5.12 fails as a nit, argued under decision 18 and accepted: the appendix tables run in two ordered groups rather than one exact order, stated in Section 9 with the five-page cost.
- R5.13 (added after round 03, applying to any later round): not yet met and not required at this release; no versioned entry-rules file exists and the artifact paragraph names none. A suggestion below.

## 3. The open items at the cap

They may stay listed in Section 9 for publication. The two paper-facing items are a numbering order kept in two reading-ordered groups and two display fields outside the post-launch block with the reading side closed by the allow-list and its test and the move scheduled for the next snapshot-changing release; neither touches a number, a claim, a verdict or a reader's ability to regenerate the paper, and Section 9 states each with its reason. The other two (the sample ledger's rate against the quick gates' simulated rate; no rerun needed for R4) are documentation and process items that no sentence of the paper rests on.

## 4. Final verdict

Recommendation: accept
Scores (1 to 5): novelty 3, correctness 4, rigor 4, clarity 4, reproducibility 5, code 4
High-quality paper worth publishing at a top venue: yes. For a datasets-and-benchmarks track: it releases a public benchmark with a leakage-audited protocol, a pre-fixed hypothesis set read back part by part against a claims register a script checks, and a powered negative that is itself the finding; it is not a main machine-learning track paper, since the method result is a negative with no new model.
High-quality code package worth publishing: yes. One command regenerates each table from shipped report files, the leakage audit ships as JSON with every count zero, the register and number audits trace 771 printed numbers to report keys, a clean clone built the paper and passed the paper suites at a839b2c, and the release is archived under a DOI.
Remaining concerns: [suggestion] fix the benchmark's entry rules (budget, baseline, gate target, reading rule, snapshot digest) in one versioned file named by the artifact paragraph before the first external result enters, which is what R5.13 will ask; [suggestion] the Discussion sentence on the monitor benchmark entered at release after the reviews and rests on the maintainers' reading of that paper's Table 3; keep its source comment and register row as they are, and reread it against the cited paper's next version before any later revision.
