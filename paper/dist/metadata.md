# arXiv metadata, ready to paste

Fill in the author line; everything else is as it should be pasted. The abstract is the one in `paper/main.tex` as plain text.

## Title

Arguing from Precedent: A Benchmark and Protocol for Scored, Gated Pre-Launch Forecasts of A/B Test Outcomes with Abstention

## Authors

<author line: fill in at upload; the paper's author block is in paper/main.tex>

## Abstract

Teams that run many online controlled experiments accumulate a ledger of concluded tests, yet rarely consult it before the next test launches. We release a benchmark and protocol for asking what the ledger says about a proposed test: a ledger format with admission as a status, a rolling-origin backtest over versioned snapshots in which nothing measured during a test reaches a forecast made before it (two stated stand-ins excepted, their leak measured), proper scores with floors and ceilings, calibration against a clustered null and within strata of precision, sample-size gates at the archive's own base rate, a leakage audit, and decision value against random order. It runs on the Upworthy Research Archive (3,797 scored headline tests), the ASOS Digital Experiments Dataset (78 experiments) and a synthetic generator with known truth, with a baseline ladder (base rate, empirical-Bayes Student-t prior, kernel-weighted precedents behind an admission guard, abstention triggers and a frozen card) and three recalibrated challengers on matched splits. The first finding is a powered negative. On the headline archive the prior improves the logarithmic score of the next result by 0.149 nats over the base rate and covers at nominal rates on average, yet its Brier skill against the base rate is 0.001 (90 percent interval minus 0.002 to 0.005) on 3,797 tests against a release gate of 250, its probabilities sit at the 100th percentile of the calibration null, and its coverage runs from 1.00 to 0.66 across deciles of realized over planned standard error. Precedents, held in the prior's own predictive family, equal the prior on skill and on the log score within the interval (plus 0.0004 nats, minus 0.0003 to 0.0012); in a positive control the guard admits a planted lift at the size of the largest cell and the rung recovers a fifth of it, after exposing a defect in the prior's period level, now fixed. Ranking tests by predicted win probability captures more positive lift than a random order matched on the number of arms for a TF-IDF text classifier (4.0 points, interval 2.2 to 5.4), while the prior equals random order by construction. A first run that scored relative lift at realized precision reported a reversed calibration gradient; we show it was leakage. The deployment-shaped archive returns undecidable at every gate, as designed. Moot Court, the open-source system, regenerates every table and figure from the report files, one command per table.

(Check the abstract against `paper/main.tex` at upload: the text above is that of the run 6 sources of 4 November 2026.)

## Categories

- Primary: **stat.ML** (Machine Learning, Statistics). The contribution is a benchmark and a scoring protocol for probabilistic forecasts
  (proper scores, calibration under a clustered null, coverage by precision, sample-size gates), with empirical-Bayes and kernel
  estimators as the baselines; that is statistical machine learning rather than a learning algorithm.
- Cross-list: **cs.LG** (Machine Learning). The benchmark, the challenger models (a boosted model, a text classifier), the leakage audit
  and the reproducibility packaging are the computer-science side of the same work, and the readers who run experimentation platforms
  are there.
- Cross-list: **stat.ME** (Methodology). The rolling-origin design with versioned snapshots, admission as a status, the planned standard
  error, the decision-value measure against random order and the gates in tests are methodological contributions to the analysis of
  online experiments.

## Comments line

27 pages including the appendix, 6 figures, 53 tables. Code, the data pipeline and the run folders behind every table:
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

- Report number: none. Journal reference: none. DOI: the Zenodo DOI of the software release, once minted (see the release checklist).
- ACM class (optional): G.3 Probability and Statistics; I.2.6 Learning.
