# arXiv metadata, ready to paste

Everything is as it should be pasted. The abstract below is condensed from the one in `paper/main.tex` to fit arXiv's field of 1,920 characters: the five exploratory findings and the registered confirmatory one are kept; Tools is left to the PDF; and Problem, Method and Release are shorter.

## Title

Can Past Experiments Predict the Next One? A Scoring Protocol for Pre-Launch Forecasts of A/B Tests, Applied to a Public Archive of Headline Tests

## Authors

Yingjie Li (Independent researcher)

## Abstract

Problem. Before a launch, a team wants to know what its experiment will show. Industrial screeners are evaluated privately; public work scores winner predictors. We found no public evaluation that scores a forecast distribution and a probability of a significant result against concluded tests under a fixed rule for what a forecast may see.
Method. We replay one public archive: 2,949 headline and image tests of a publisher, scored over seven quarters by models fitted on earlier tests. The archive records realized, not planned, traffic, so each forecast gets the median traffic of earlier tests of its kind. All findings but the last are exploratory: one split, read many times.
Findings.
- A heavy-tailed base rate forecasts the next result's distribution nearly as well as a fitted prior. The prior leads by 0.007 nats on the log score; with the seven quarters as units the lead cannot be told apart from zero.
- The prior's skill on which test will be significant is small and fragile; within a kind of test and quarter every test gets the same probability: a better level, not a ranking.
- In the main run the probabilities fail a calibration test: the level is off in both directions.
- No model we ran, all simple stand-ins, ranks tests detectably better than counting arms, on a target that grows with arm count.
- On the exploratory split, weighting similar past tests does not beat the prior; it recovers under a tenth of a planted signal, so the tie cannot rule one out.
- Confirmatory split, opened once under rules fixed beforehand in our own dated record (no registry): on 13,822 tests of the same quarters the verdicts recur. By quarter the prior's lead and skill are not shown, though clear by test; ranking above arm count is not shown. Weighting past tests leads slightly there, signs differing by kind of test (no verdict).
Release. Protocol and Moot Court (MIT), which rebuilds every table.

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

71 pages including the appendix, 6 figures, 99 tables. Code, the data pipeline and the run folders behind every table:
https://github.com/journey-agents/mootcourt (MIT). The plan with the six hypotheses, written after two earlier runs on the same split:
https://github.com/journey-agents/mootcourt-plan. (Recount the pages from the final `make arxiv-check` before pasting.)

## License

**CC BY 4.0** (Creative Commons Attribution). The public archives the paper is built on are released under CC BY 4.0, the code is MIT,
and the protocol is meant to be reused, extended and re-reported by other teams with attribution; the attribution license is the most
permissive of arXiv's choices that keeps the authors named, and it does not restrict a later journal version.

## Ancillary files

None proposed. The tables and figures are regenerated from the repository's run folder (`make tables`, `make paper-figures`), and the
provenance index `figures.json` lives there; if arXiv's ancillary slot is wanted, `paper/figures/figures.json` (the list of every plotted
value with its report path) is the one file worth attaching.

## Other fields

- Report number: none. Journal reference: none. DOI field: leave empty (it is for the paper's own DOI); the software release's Zenodo DOI 10.5281/zenodo.23988587 is cited in Section 11 and the README.
- ACM class (optional): G.3 Probability and Statistics; I.2.6 Learning.
