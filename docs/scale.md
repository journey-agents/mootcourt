# Scale

How the fit, a backtest and the card behave on ledgers of 100 thousand and one million contrasts. The two runs below are real:
they ran on one laptop, wrote their files to an external drive and are reproducible with one command.

```
moot benchmark --scale 100000
moot benchmark --scale 1000000
```

Each run generates a synthetic ledger of N contrasts (two variants per test, a text signal in the headlines, 3 cells), fits a
bundle, scores a seeded sample of rows at the last two quarterly origins with the full history before each origin, issues 1000
cards against the fitted bundle and times every card. The report goes to `reports/scale-N.json` and the ledger to
`experiments/scale/` under the data root. The synthetic source has a known truth, so these numbers say how fast the tool is, not
how good its forecasts are.

## What was measured

Machine: Apple silicon laptop, 8 cores, 16 GB of memory, macOS, Python 3.11. The fit is single threaded. The test suite ran at the same time for part of
each run, so the times include some contention and are an upper bound on an idle machine.

| | 100 thousand | 1 million |
|---|---|---|
| Wall time, whole run | 331 s | 3082 s (51 minutes) |
| Fit (P0, P1, P2 with its selection) | 93 s | 1209 s (20 minutes) |
| Backtest, 2 origins, 4000 rows scored | 213 s | 1826 s (30 minutes) |
| 1000 cards, one after another | 24 s | 35 s |
| Card latency, median | 23.7 ms | 35.1 ms |
| Card latency, 95th percentile | 24.7 ms | 36.8 ms |
| Card latency, slowest | 38.4 ms | 77.3 ms |
| Peak resident memory (also what `/usr/bin/time -l` reports) | 1.48 GiB | 6.54 GiB |
| Peak memory footprint reported by the operating system | not captured | 8.2 GiB |
| Ledger file on disk | 7 MB | 60 MB |
| Free space, internal disk, before and after | 13.28 and 12.80 GB | 12.63 and 12.32 GB |
| Free space, external drive, before and after | 1346.23 and 1346.22 GB | 1346.22 and 1346.17 GB |

The internal disk lost 0.5 and 0.3 GB during the runs. The benchmark writes nothing there, and the likely cause is swap and other
work on the machine. On both runs the card was issued in well under the one second the design asks for, and the largest fit took
a third of the hour it was allowed. No change to the code was needed to meet either target, so none was made.

## Where the time goes

- **The fit grows in proportion to the number of rows.** 1e4 rows took 10 s, 1e5 took 93 to 109 s, 3e5 took 338 s and 1e6 took
  1209 s: about one millisecond per row.
- **Most of it is P1.** A profile of a 200 thousand row fit put 85 percent of the time in the hyperparameter search of the
  pooled model, which evaluates a quadrature grid likelihood over every row of a cell at each of about seventy optimizer steps.
  P2 took 12 percent: its selection uses at most 3000 query rows per cell against all rows, so it also grows in proportion to
  the rows, and it never forms an n by n matrix.
- **A backtest costs about one fit per origin plus the scoring.** The scale backtest scores 2000 rows at each of two origins
  rather than every row. Scoring every row at a million contrasts would need about nine origin fits and roughly eight
  milliseconds per scored row, an estimate of three to four hours that was not measured. The sample is seeded and its size
  is in the report.
- **A card costs almost the same at any size.** It compares one query with the cell's visible rows, lists the top 1000 and
  sums the rest, so 1e5 and 1e6 rows differ by only about 12 ms. In a separate check at 20 thousand rows, issued and
  abstained cards took the same time within a millisecond.
- **Memory** is the feature matrix (64 text dimensions plus the structured ones, in 64-bit numbers), the retrieval index
  and a block of 256 query rows against all rows during selection. The block is what makes the peak 6.5 GiB at a million rows.
  A ledger ten times larger would not fit in 16 GB of memory without a smaller block or 32-bit numbers.

## Limit: top-M truncation

A query lists its 1000 highest-weight neighbors (top M) and keeps the sums of the rest as a tail. The forecast `p_sig` uses the
moments of all precedents, so the truncation does not bias it. Two things use only the listed neighbors: the bootstrap interval
(it resamples the listed precedents and holds the tail fixed) and the list of precedents to dismiss. When many precedents carry
a little weight each, the tail holds most of the weight and these two understate what a different set of precedents would do.

Measured on the synthetic ledger, for 60 headline-only queries, the share of the total kernel weight beyond the top 1000:

| Contrasts | Share of weight in the tail, mean (10th to 90th percentile) |
|---|---|
| 10 thousand | 0.15 (0.07 to 0.21) |
| 100 thousand | 0.53 (0.32 to 0.67) |
| 300 thousand | 0.66 (0.51 to 0.79) |

The share was not measured at a million contrasts and is expected to be higher. The limit is stated, not removed: a larger M
costs memory and time in every card, and a tail-aware bootstrap would change the interval's definition. Until one of those is
chosen, read the interval of a card from a large ledger as a lower bound on its uncertainty.

## If the fit becomes too slow

In order of cost: estimate the pooled model's hyperparameters on a seeded subsample of each cell's rows (the likelihood is the
slow part, and the estimates stabilize long before a million rows); fit the quarterly origins of a backtest in parallel
processes; use 32-bit numbers for the feature matrix. None of these is needed at a million contrasts on this machine.
