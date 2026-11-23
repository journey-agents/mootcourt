# arXiv metadata, ready to paste

Everything is as it should be pasted. The abstract below is the abstract of `paper/main.tex` shortened to fit arXiv's field: it asks whether a test can be predicted from its history and what the forecast can be used for, then lists what history gives and what we could not show. It leaves out the sentence on traffic, the yardstick and several second sentences of the findings, which the PDF's abstract keeps. The anonymous abstract in `paper/sections/abstract-tmlr.tex` is one paragraph with the same content; keep the three in agreement on every number and verdict. arXiv's field holds 1,920 characters and counts each line break as two. arXiv joins the lines of the abstract into one paragraph unless a line starts with a space, so paste every line after the first with one leading space, which keeps the breaks and stays inside the limit.

## Title

Can Past Experiments Predict the Next One? A Scoring Protocol for Pre-Launch Forecasts of A/B Tests, Applied to a Public Archive of Headline Tests

## Authors

Yingjie Li (Independent researcher)

## Abstract

Can a team predict an A/B test from its history before running it, and what can it use that forecast for? We replay a public archive: 2,949 headline and image tests in seven quarters, each forecast once by models fitted only on earlier tests.
What history gives: a forecast of how the next result will be distributed, better than one reading no history. A heavy-tailed base rate forecasts it nearly as well as a fitted prior, whose pooled lead of 0.007 nats is not shown once quarters, not tests, are units.
What we could not show:
- Which test will be significant. The prior gives all tests of one kind and quarter one probability, so its small, fragile skill is a better level, not a ranking; its probabilities fail a calibration test.
- Which tests to run. A text classifier orders tests better than a random order matched on arm count, but no model we ran is shown to beat the arm-count rule: rank tests by number of variants.
- Which headline drew more clicks. Language models playing readers are not shown to beat always picking the earliest headline; nor is an open model asked directly. An embedding classifier is above that rule with tests resampled, not with quarters as units. All may have seen the archive.
- A gain from weighting similar past tests, a method that recovers under a tenth of a planted gain on synthetic data.
History says what to expect from a test of its kind and little about which test will succeed. We do not compare a forecast with a live test; the test still decides what a change did. The evidence is one publisher's archive and untuned models, so a better predictor is not ruled out. Findings are exploratory, except three verdicts that recur on a confirmatory split of 13,822 tests, opened once under rules fixed beforehand in our dated record (no registry then): by quarter the prior's lead and its skill are not shown, nor is the classifier above the arm-count rule.

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

78 pages including the appendix, 6 figures. Code, the data pipeline and the run folders behind every table:
https://github.com/journey-agents/mootcourt (MIT). The plan with the six hypotheses, written after two earlier runs on the same split:
https://github.com/journey-agents/mootcourt-plan

(The page count is the one arXiv's own compile reported on 22 November 2026; the local build has 79. Recount after any new upload.)

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
