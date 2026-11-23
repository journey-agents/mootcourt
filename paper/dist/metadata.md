# arXiv metadata, ready to paste

Everything is as it should be pasted. The abstract below is the abstract of `paper/main.tex` since 22 November 2026: it is organized around one question, whether a test can be predicted from its history and what that buys compared with running the test. The anonymous abstract in `paper/sections/abstract-tmlr.tex` is the same text as one paragraph of at most 300 words; keep the three in agreement on every number and verdict. arXiv's field holds 1,920 characters and counts each line break as two. arXiv joins the lines of the abstract into one paragraph unless a line starts with a space, so paste every line after the first with one leading space, which keeps the breaks and stays inside the limit.

## Title

Can Past Experiments Predict the Next One? A Scoring Protocol for Pre-Launch Forecasts of A/B Tests, Applied to a Public Archive of Headline Tests

## Authors

Yingjie Li (Independent researcher)

## Abstract

Can a team predict an A/B test from its history before running it, and what does that buy compared with running the test? We replay a public archive: 2,949 headline and image tests, each forecast over seven quarters by models fitted only on earlier tests. No plan is recorded, so a forecast gets the median traffic of earlier tests like it.
What the predictor gives:
- A realistic expectation of the result. A heavy-tailed base rate forecasts it nearly as well as a fitted prior, whose lead of 0.007 nats is not told apart from zero with quarters as units.
- A yardstick. A new method should first beat the base rate and a trivial rule: rank tests by their number of variants.
What it did not give:
- Which test will be significant. The prior's skill is small and fragile, and its probabilities fail a calibration test.
- Which tests to run. A text classifier orders tests better than chance, but no model we ran is shown to beat the variant-count rule.
- Which headline wins. Language models playing readers (they may have seen the archive) are not shown to beat always picking the earliest; nor is an open model asked directly. An embedding classifier beats the earliest pick, but not once variation between quarters is counted.
- A gain from weighting similar past tests, in a replay that recovers under a tenth of a planted signal.
So the predictor says what to expect from a test like this one, not whether to ship it, and it does not replace the test. The evidence is one publisher's archive and simple models, so a better predictor is not ruled out; this protocol can test one. Findings are exploratory, except that on a confirmatory split of 13,822 tests, opened once under rules fixed before in our dated record (no registry then), three verdicts recur: by quarter the prior's lead and its skill against a smoothed base rate are not shown, nor is a ranking better than the variant-count rule.

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
