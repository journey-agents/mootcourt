# arXiv metadata, ready to paste

Fill in the author line; everything else is as it should be pasted. The abstract is the one in `paper/main.tex` as plain text.

## Title

Arguing from Precedent: A Benchmark and Protocol for Scored, Gated Pre-Launch Forecasts of A/B Test Outcomes with Abstention

## Authors

<author line: fill in at upload; the paper's author block is in paper/main.tex>

## Abstract

Teams rarely consult their ledger of concluded experiments before the next launch. We release a benchmark and protocol that ask it about a proposed test: a rolling-origin backtest over versioned snapshots in which no in-test measurement reaches a pre-launch forecast, proper scores, a clustered calibration null, gates and decision value against random order, on the Upworthy Research Archive (3,797 headline tests) and the ASOS Digital Experiments Dataset (78 experiments).

The first finding is a powered negative. On the headline archive an empirical-Bayes prior gains 0.149 nats of log score over the base rate, yet its Brier skill is 0.001 (minus 0.002 to 0.005) on 3,797 tests against a gate of 250, its probabilities sit at the null's 100th percentile, and its coverage runs from 1.00 to 0.66 across deciles of realized over planned standard error. Guarded precedents in the prior's family are no better than it (plus 0.0004 nats of log score, minus 0.0003 to 0.0012); in a positive control the guard admits a planted lift at the largest cell's size and the rung recovers a fifth of it pooled, a tenth in the cell shaped like the real one. Ranking by win probability beats an arm-count-matched random order for a TF-IDF text classifier (3.9 points, 2.2 to 5.4); the prior equals it by construction. A first run scoring relative lift at realized precision reversed the calibration gradient: leakage. The deployment-shaped archive is undecidable at every gate, by design. Moot Court, the open-source system, regenerates every table from the reports.

(Check the abstract against `paper/main.tex` at upload: the text above is the 250-word abstract of pass 11, 5 November 2026, on the run 7 sources.)

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

29 pages including the appendix, 6 figures, 53 tables. Code, the data pipeline and the run folders behind every table:
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
