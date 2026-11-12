# arXiv metadata, ready to paste

Everything is as it should be pasted. The abstract below is condensed from the one in `paper/main.tex` to fit arXiv's field of 1,920 characters: the main findings are kept; the learning curve, the diagnostic of the prior's shape, the question labels and Tools are left to the PDF; and Problem, Method and Release are shorter.

## Title

Can Past Experiments Predict the Next One? A Scoring Protocol for Pre-Launch Forecasts of A/B Tests, Applied to Two Public Archives

## Authors

Yingjie Li (Independent researcher)

## Abstract

Problem. Before launching a change, a team wants to know what result to expect, whether the test is worth running and how large to make it. Industrial screening systems are evaluated on private data. We found no public evaluation showing whether forecasts from past experiments can be trusted, or when they say too little.
Method. We simulate how a team would have forecast each test, on two public archives: 2,949 scored headline and image tests from a publisher (Upworthy), leaving out a period flagged for randomization problems, and 68 scored experiments from a retailer (ASOS; no dates). We fit on earlier tests only. Forecasts use actual traffic, unknown to a real forecast. All results are exploratory: we reused the data and changed the method after seeing results.
Findings.
- For the publisher, a fitted prior forecasts the next result's distribution better than a base rate scored with a normal density (0.120 nats). Most of that is the density's shape: against a heavy-tailed base rate the gain is 0.020, above zero pooled. It does not say which test will succeed. Its skill on which test will be significant is at most small: its interval spans zero, or just clears it, unadjusted, at planned precision and only without the flagged period. Its probabilities fail a calibration test. The retailer's tests are too few to decide on skill.
- Weighting similar past tests matches the prior on score and skill. It ranks tests better, but worse than arm count alone at a quarter or half of the tests, and no better than traffic alone. With a planted signal it recovers 0.09 of the gain of a model told the signal. A text classifier's top quarter captures 4.6 points more lift than a matched random choice, no more than arm count alone, and fails that control. Abstaining is not shown to help.
- Sizing tests from the forecast shows no consistent gain over the base rate.
Release. Protocol and Moot Court (MIT).

## Categories

- Primary: **cs.AI** (Artificial Intelligence). The work asks how well an AI system's forecasts of experiment outcomes hold up, and how a team should
  gate and audit them; the endorsement is for this category.
- Cross-list: **stat.ML** (Machine Learning, Statistics). A scoring protocol for probabilistic forecasts (proper scores, calibration
  under a clustered null, coverage by precision, sample-size gates), with empirical-Bayes and kernel estimators as the baselines.
- Cross-list: **cs.LG** (Machine Learning). The protocol, the challenger models (a boosted model, a text classifier), the leakage audit
  and the reproducibility packaging are the computer-science side of the same work, and the readers who run experimentation platforms
  are there.
- Cross-list: **stat.ME** (Methodology). The rolling-origin design with versioned snapshots, admission as a status, the planned standard
  error, the decision-value measure against random order and the gates in tests are methodological contributions to the analysis of
  online experiments.

## Comments line

51 pages including the appendix, 6 figures, 88 tables. Code, the data pipeline and the run folders behind every table:
https://github.com/journey-agents/mootcourt (MIT). The plan with the six hypotheses, written after two earlier runs on the same split:
https://github.com/journey-agents/mootcourt-plan. (Recount the pages from the final `make arxiv-check` before pasting.)

## License

**CC BY 4.0** (Creative Commons Attribution). Both public archives the paper is built on are released under CC BY 4.0, the code is MIT,
and the protocol is meant to be reused, extended and re-reported by other teams with attribution; the attribution license is the most
permissive of arXiv's choices that keeps the authors named, and it does not restrict a later journal version.

## Ancillary files

None proposed. The tables and figures are regenerated from the repository's run folder (`make tables`, `make paper-figures`), and the
provenance index `figures.json` lives there; if arXiv's ancillary slot is wanted, `paper/figures/figures.json` (the list of every plotted
value with its report path) is the one file worth attaching.

## Other fields

- Report number: none. Journal reference: none. DOI field: leave empty (it is for the paper's own DOI); the software release's Zenodo DOI 10.5281/zenodo.23988587 is cited in Section 11 and the README.
- ACM class (optional): G.3 Probability and Statistics; I.2.6 Learning.
