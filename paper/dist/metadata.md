# arXiv metadata, ready to paste

Everything is as it should be pasted. The abstract is the one in `paper/main.tex` as plain text.

## Title

Arguing from Precedent: A Benchmark and Protocol for Scored, Gated Pre-Launch Forecasts of A/B Test Outcomes with Abstention

## Authors

Yingjie Li (Independent researcher)

## Abstract

Problem. A team must choose which A/B tests to run before any result exists. Its record of past experiments could inform that choice but is usually read only afterwards. Industrial systems forecast tests on private data; no public benchmark shows whether such forecasts can be trusted, or when the record has too little to say.
Method. We replay two public archives in time order: 3,797 headline tests from an online publisher (Upworthy) and 78 experiments from a fashion retailer (ASOS). Each test is forecast only from results final before it started (realized exposure stands in for planned exposure; we measure that leak).
Findings.
- Can past experiments predict new ones? Partly. On the publisher's tests, a fitted model forecasts the range of a new effect better than a historical baseline (0.149 nats), but not which test wins: pooled skill 0.001, interval spanning zero on 3,797 tests, and its probabilities are miscalibrated. The retailer's 68 scored tests are too few to decide (400 needed).
- How? Fit a prior per group of tests, allowing for measurement error. Weighting similar past tests leaves log score and skill unchanged and ranks tests slightly better, but this backtest is weak here: on synthetic tests it recovers about 0.09 of the gain an oracle gets from a planted effect. To choose tests, a text classifier's top quarter captures 3.9 points more lift than a matched random choice, though it fails that same control. Abstention did not improve what was issued.
- What improves prediction? A heavy-tailed forecast gained most (0.100 nats over a normal one); bandwidth, features and pooling barely mattered. Planned exposure, stronger text models and frozen team forecasts are untested.
Tools. A base rate, a fitted prior, similarity weighting, three learned challengers.
Release. A benchmark (protocol, schema, baselines, run reports) and Moot Court, an MIT-licensed Python package that regenerates every results table and runs privately on a company's own aggregate records.

(Check the abstract against `paper/main.tex` at upload: the text above is the structured abstract of the format pass of 5 November 2026, on the run 7 sources.)

## Categories

- Primary: **cs.AI** (Artificial Intelligence). The work asks how well an AI system's forecasts of experiment outcomes hold up, and how a team should
  gate and audit them; the endorsement is for this category.
- Cross-list: **stat.ML** (Machine Learning, Statistics). A benchmark and a scoring protocol for probabilistic forecasts (proper scores, calibration
  under a clustered null, coverage by precision, sample-size gates), with empirical-Bayes and kernel estimators as the baselines.
- Cross-list: **cs.LG** (Machine Learning). The benchmark, the challenger models (a boosted model, a text classifier), the leakage audit
  and the reproducibility packaging are the computer-science side of the same work, and the readers who run experimentation platforms
  are there.
- Cross-list: **stat.ME** (Methodology). The rolling-origin design with versioned snapshots, admission as a status, the planned standard
  error, the decision-value measure against random order and the gates in tests are methodological contributions to the analysis of
  online experiments.

## Comments line

30 pages including the appendix, 6 figures, 56 tables. Code, the data pipeline and the run folders behind every table:
https://github.com/journey-agents/mootcourt (MIT). The analysis plan was fixed in writing before the final runs:
https://github.com/journey-agents/mootcourt-plan. (Recount the pages from the final `make arxiv-check` before pasting.)

## License

**CC BY 4.0** (Creative Commons Attribution). Both public archives the paper is built on are released under CC BY 4.0, the code is MIT,
and the benchmark is meant to be reused, extended and re-reported by other teams with attribution; the attribution license is the most
permissive of arXiv's choices that keeps the authors named, and it does not restrict a later journal version.

## Ancillary files

None proposed. The tables and figures are regenerated from the repository's run folder (`make tables`, `make paper-figures`), and the
provenance index `figures.json` lives there; if arXiv's ancillary slot is wanted, `paper/figures/figures.json` (the list of every plotted
value with its report path) is the one file worth attaching.

## Other fields

- Report number: none. Journal reference: none. DOI field: leave empty (it is for the paper's own DOI); the software release's Zenodo DOI 10.5281/zenodo.23988587 is cited in Section 10 and the README.
- ACM class (optional): G.3 Probability and Statistics; I.2.6 Learning.
