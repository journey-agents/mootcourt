# Round 03 confirmation pass on release 1.0.0

Paper and code version read: c7dbfd0 (release 1.0.0 is tag v1.0.0 at d9d06ed; c7dbfd0 adds the Zenodo DOI line). Written 5 November 2026 by the launching team from the seven files `confirmation-R1.md` to `confirmation-R7.md`. The round 03 summary recorded that no reviewer had read the fix commit; in this pass each reviewer verified its own round 03 findings at the released commit, re-read its rubric section, and answered two questions in fixed words: whether this is a high-quality paper worth publishing at a top venue, and whether this is a high-quality code package worth publishing. No experiment was rerun; R4 ran the test suite in a clean clone of the tag.

## Verdicts

| Reviewer | Recommendation | Novelty | Correctness | Rigor | Clarity | Reproducibility | Code | Paper worth a top venue | Code package worth publishing |
|---|---|---|---|---|---|---|---|---|---|
| R1 statistician | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |
| R2 experimentation platform engineer | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |
| R3 machine learning reviewer | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |
| R4 reproducibility chair | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |
| R5 area chair | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |
| R6 practitioner and documentation reviewer | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |
| R7 fresh area chair | accept | 3 | 4 | 4 | 4 | 5 | 4 | yes | yes |

7 of 7 recommend accept and 0 recommend minor revision; 7 of 7 answer yes to the paper question and 7 of 7 to the code question.

## Remaining concerns, as each reviewer classified them

- R1: [suggestion] print the closed form of the positive control's ceiling per cell and call it the normal approximation, since the refit oracle exceeds it in every cell; [suggestion] say in Section 6.2 that a cell's gates are a first-order scaling of the simulated ones; [suggestion] the by-origin table of the report uses 200 resamples where everything printed uses 500.
- R2: [suggestion] R2-s1 to R2-s5 as recorded in the letter; [suggestion] the three held-row tests and the exit-code test carry the prefix test_r3 while they close R2 items, a naming matter for the next release.
- R3: none as findings. [suggestion] R3-s1, the single-headline run of the challengers (Section 9 lists it as not run). [suggestion] R3-s2, a held-out or marginal-likelihood estimate of P2's scale term (Section 9 names it as future work). [suggestion] R3-s5, a clause in the caption of Table learning-upworthy that the curve's full-history point equals the main backtest's final-origin fit to the last digit.
- R4: [finding, R4.7] at c7dbfd0 the README is one line past the limit of `tests/test_docs_run.py` (226 newline-split pieces against 225), so that test, `make release-check` and `make selfcheck` fail at the DOI commit while the tag passes; fix with one line fewer in the Citing paragraph, or a limit of about 230 with the test's sentence updated, and say in the changelog which commit the release check last passed on. [suggestion] `docs/results.md` line 844 still says the quick Makefile targets run the full sets (R4-s3). [suggestion] the release notes could say that running the suite needs the dev extra, since a plain `uv sync` installs no pytest.
- R5: [suggestion] fix the benchmark's entry rules (budget, baseline, gate target, reading rule, snapshot digest) in one versioned file named by the artifact paragraph before the first external result enters, which is what R5.13 will ask; [suggestion] the Discussion sentence on the monitor benchmark entered at release after the reviews and rests on the maintainers' reading of that paper's Table 3; keep its source comment and register row as they are, and reread it against the cited paper's next version before any later revision.
- R6: [R6.11, nit: `moot init` timing reads 20 seconds on the quickstart and the command guide and 30 seconds in tutorial 1 against blocks of 26 to 28 s]; [suggestion: the 1.0.0 entry of CHANGELOG.md could name the regeneration pass that CONTRIBUTING line 49 says the release notes carry]; [suggestion: the R6.14 documentation test, so that a duration or base rate quoted in prose is checked against its block the way gate sizes are].
- R7: [R7-F9, R5.7] one leftover "significance event" in Section 9 line 16, a one-word edit at nit level; [R5.13] the versioned entry-rules file, due before the first external report card is compared, not before publication; [suggestion] R7-s1, the abstract's first sentence states a practice claim without a citation.

## The launching team's answer (5 November 2026)

Three items named by the reviewers are fixed in the commit that adds these files: the README's length (R4.7, one joined line in the Citing section; the test, the release check and the self-check pass again), the `moot init` timing on the quickstart and the command guide (R6.11, about 30 seconds), and the one leftover "significance event" in Section 9 with register row C52 requoted (R7-F9). The versioned entry-rules file (R5.13) is scheduled for the release after 1.0.0, before the first external result is compared. The suggestions stay recorded in the letter. The audits pass after the edits: claims audit 135 rows, 0 failing; number audit 771 numbers, 0 unmatched; writing rules clean. The PDF and the arXiv tarball were rebuilt at 30 pages.
