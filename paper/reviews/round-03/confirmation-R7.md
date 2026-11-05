# Confirmation pass, release 1.0.0

Reviewer: R7
Role: fresh area chair (round 03, under rubric items R5.1 to R5.13)
Commit: c7dbfd0 (tag v1.0.0 is d9d06ed; c7dbfd0 adds the Zenodo DOI line)
Date: 5 November 2026

No new blocking or major finding. Checks at c7dbfd0: `scripts/claims_audit.py` exit 0 (134 rows, 127 keyed); `scripts/paper_audit.py` 771 numbers, 0 unmatched, 107 sources resolved; PDF 30 pages, references on page 12, abstract 250 words; sources diffed against a839b2c.

## 1. My round 03 findings at c7dbfd0

- R7-F1 (C3), Fixed: closed. Abstract: "no in-test outcome reaches a pre-launch forecast (one stand-in, realized exposure, its leak measured)"; contribution 1 (`paper/main.tex` line 45) carries "from realized exposure where the archive records no plan, a stand-in whose leak Section 9 measures". Register C3 requoted.
- R7-F2 (C15, C38), Fixed: closed. Abstract: "the prior, one number per cell, sits at it (minus 0.004, within noise)"; Section 9 H5: "failed for the prior, which ranks by cell only ... sits at the matched order within noise (minus 0.004, minus 0.012 to 0.005)"; Section 6.4 line 70: "fails for the prior, which ranks by cell only". C15 re-keyed to `diff_matched`; C129 added.
- R7-F3 (C12, C24, C119, C122), Fixed: closed. "About a fifth" in the abstract, contribution 3, Section 9 (line 28 of `limitations.tex`); Section 6.8 line 109 prints "0.18 (0.16 to 0.20)" where the number is read.
- R7-F4 (R5.2), Fixed: closed. Section 5, third paragraph after the hypotheses: the plan fixed no reading rule, the pooled rule was fixed in the paper after the data were seen, H2's final-origin part and H3's most-origins part are read pooled, and Section 9 reads H3's first part by origin. The shipped key `issued_ece_by_origin.issued.origins_inside_central_90` is 4 of 8 origins (500 null draws, clustered by test), and the verdict reads the part as failing (C134).
- R7-F5 (R5.2), Fixed: closed. Section 9, first paragraph: the commit "holds the plan beside the reports of the second run on the same archive while the plan's own section 1a reads the first, so the hypotheses postdate those two runs ... and precede every run the paper reads"; "registered plan" and "the plan registered" no longer appear (0 hits in the sources).
- R7-F6 (R5.7), Fixed: closed. The disclosure paragraph appears once in `paper/main.tex` and once in the PDF.
- R7-F7 (R5.7), Fixed: closed. Section 2 defines "continuous ranked probability score (CRPS)" and "singular value decomposition (SVD)" at first use (PDF text order checked).
- R7-F8 (R5.7), Fixed: closed. Contribution 3 (`main.tex` line 49) carries no numbers; Section 6.2 line 29 reads the pooled AUC as a range; Section 6.4 line 68 keeps intervals for the text classifier only; Section 7 line 9 reads the weight range with the table named. The intervals a claim rests on stay, which is the right rule.
- R7-F9 (R5.7), Fixed: closed. Counts over the sources: "local comparison set" 15, the four other names 0; "boosted model" 17 with one "gradient-boosted regressor" at its definition; "significant-positive event" 7 with one leftover "significance event" in Section 9 (`limitations.tex` line 16, "The headline significance event and the floor ingredients"), a one-word edit I list below and do not count against the mark.
- R7-F10 (R5.7), Fixed: closed. `scripts/paper_figures.py` draws both figures at 0.62 of the column (151.8 pt wide) with 8 pt type and 7.5 pt ticks; PDF pages 7 and 8 rendered at 110 dpi are legible, with the coverage panels stacked and the decision legend below.
- R7-F11 (R5.12), Argued: argued and accepted. First references at c7dbfd0 still run Table 2, 3, 4, Figure 5, Table 1, 5, 7, 8, 39, 9, 12, Figure 2, Table 10, Figure 4, Figure 1. Section 9's argued list carries the two-group numbering and the figure order with the five-page cost. A nit that touches no number and is disclosed with its reason is what the cap rule provides for; I accept it.
- R7-F12 (R5.3), Fixed: closed. Section 4.2 cites `garreau2017large` for the median heuristic (line 93) and `platt2000probabilities` for the map (line 97); both are in the bibliography (84 entries, all cited, none missing) and in `paper/related-work.md` (pass 12 entry, fetch-verified 5 November 2026).
- R7-F13 (R5.5), Fixed: closed. Section 9's argued list names the two post-launch display fields with the reason and the reading side closed by the allow-list; "Future work, named and not done" names the within-origin-and-cell comparison of issued against withheld rows and what rests on it.


## 2. Rubric items R5.1 to R5.13 at c7dbfd0

Pass: R5.1 (both audits clean; the three requoted abstract rows read as their keys hold), R5.2 (the rule's history stated in Sections 5 and 9; H3 part 1 read by origin from a shipped key; counts match), R5.3, R5.4, R5.5, R5.6, R5.7 (250 words; acronyms at first use; figures at 8 pt; no repeated paragraph; one name per thing but for the one leftover word under R7-F9), R5.8 (the artifact paragraph now also names the release DOI and the concept DOI), R5.9 (the round 03 letter answers R7-F1 to F13 in order with report keys; five of its statements checked and holding), R5.10, R5.11.

Still failing:
- R5.12, nit: the exact numbering order (R7-F11), argued and accepted, listed in Section 9.
- R5.13, minor if read now: no versioned file fixes the entry rules (budget, baseline, gate target, reading rule, snapshot digest); `docs/benchmark.md` exists and the artifact paragraph names no such file. The rubric dates the item to apply from the next round, so it does not bind release 1.0.0; it should ship before the first external report card is compared (R7-s2).

## 3. The open items at the cap

They may stay listed in Section 9 for publication. The four items are a numbering order, a field placement held for identifier stability with its reading side closed by a test, a documentation wording settled by a dated rubric amendment, and a review that needed no rerun. None moves a number, a claim or a verdict, each carries its reason in the paper, and the protocol's cap rule provides this disposition.

## 4. Final verdict

Recommendation: accept
Scores (1 to 5): novelty 3, correctness 4, rigor 4, clarity 4, reproducibility 5, code 4
High-quality paper worth publishing at a top venue: yes. For a datasets-and-benchmarks track it is a complete benchmark and protocol with a leakage audit, a claims register that ties 134 sentences to report keys, a powered negative read against a derived gate, and an honest read-back of registered hypotheses; the narrow novelty and the single decidable archive are why it belongs there rather than in a main machine-learning track.
High-quality code package worth publishing: yes. Every table and figure regenerates by one command, the number and claims audits run in the test suite, the per-row score table reproduces every headline number I recomputed (the decision-value policy included), and the modules I read document their design calls.
Remaining concerns: [R7-F9, R5.7] one leftover "significance event" in Section 9 line 16, a one-word edit at nit level; [R5.13] the versioned entry-rules file, due before the first external report card is compared, not before publication; [suggestion] R7-s1, the abstract's first sentence states a practice claim without a citation.
