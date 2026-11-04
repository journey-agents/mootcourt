# Moot Court

Moot Court is a Python package and command line for the people who plan A/B tests. It reads the record of your concluded experiments, forecasts what that record implies about a proposed experiment, scores every forecast against what the live test later showed, and declines to rule when the record has nothing to say. It is for a data scientist or an experimentation team with an archive of concluded tests, and it needs only aggregates: the effect, its standard error, the units per arm and the dates of each experiment, not user-level data.

The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.

Skill on headline tests does not transfer to product deployments, and nothing here shows that it does.

## How it works

The ideas, in the order you meet them:

- **The ledger** is the table of your concluded experiments: one row per variant, per metric, per experiment. Importing results is one command, and rows that fail an admission rule are kept and counted, never dropped.
- **A card** is the forecast for one proposed experiment: the chance that it ends significant and positive, an interval for the true effect and how fragile that opinion is. A card can also abstain, and then it says why. Cards are frozen under a digest of their content, so nobody can edit one after the result is known.
- **Cells and rungs.** Experiments are grouped into **cells** (by default one per metric), and every forecast is made inside one cell. A **rung** is one predictor in a ladder from simple to richer, and each adds one thing to the one below it: P0 is the empirical base-rate forecaster of the cell, P1 adds a fitted partially pooled Student-t prior that accounts for measurement error, and P2 adds kernel-weighted precedents under an admission guard. At a weight of zero on precedents P2 reduces to P1 exactly; the guard allows a weight above zero only when it beats zero on validation rows by more than two standard errors. That is a guard against fitting noise, not a promise that P2 beats P1 on later tests, and on Upworthy the weights it admitted lost out of time (the results page has the guard pairs and the positive-control sensitivity table, which says how often the guard admits a weight at each ledger size and strength of a planted text signal, and shows guarded and unguarded selection side by side). A card says which rung produced it (the [concepts page](docs/concepts.md#ladder) explains each).
- **The backtest** replays the ledger quarter by quarter, forecasts every past experiment using only what was final before it, and scores the forecast. It tells you whether the cards can be trusted, and how many experiments it takes to tell.

A weekly step joins each concluded experiment to the card that forecast it, and the record of hits and misses decides whether the next card may speak. The join finds a card by the ledger row it names: give `moot card` a row id with `--row-id` (or `--test-id` with `--variant-id`), and give `POST /card` and the MCP tool `get_card` the same `row_id`. A card without a row id is valid, but no outcome can be attached to it. The [concepts page](docs/concepts.md) has the diagram and the glossary.

## Quickstart

You need Python 3.11 or newer. In the root of your clone of this repository, make and activate an environment and install the package (`uv sync` works too, and then `uv run moot ...` replaces `moot ...`):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Leave the clone (`cd ..`) and make a project folder next to it, not inside it. `moot init` writes the settings, the data folders, a synthetic sample ledger and a quick gates file:

```bash run
mkdir moot-demo && cd moot-demo
moot init
```

```text output
wrote ~/moot-demo/mootcourt.toml
data root ~/moot-demo/mootcourt-data (layout created)
sample ledger ~/moot-demo/mootcourt-data/data/sample-ledger.csv (synthetic)
quick gates ~/moot-demo/mootcourt-data/reports/gates.json (400 replicates; run `moot simulate gate-power` for the full simulation)
Next, from the project folder:
  1. moot ingest --format generic --input ~/moot-demo/mootcourt-data/data/sample-ledger.csv --source-name sample
  2. moot fit --source sample && moot backtest --source sample
  3. moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

Import the sample ledger and fit the forecaster (about 5 to 15 seconds). `ingest` reports how many rows were admitted to teach the models:

```bash run
moot ingest --format generic --input mootcourt-data/data/sample-ledger.csv --source-name sample
moot fit --source sample
```

```text output
360 rows from 120 experiments
  admitted: 360
admitted by cell: checkout_conversion 120, pages_per_session 120, revenue_per_user 120
final reads from 2023-01-23 to 2025-12-29
snapshot 20261104-80131c793938 for sample
ledger ~/moot-demo/mootcourt-data/data/ledger/ledger.parquet: 360 rows
fitted model 6e5029e03c73 at snapshot 20261104-80131c793938 in 1.4 s; it is the champion for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
```

The last line of the `fit` output is expected: the new model has no backtest yet, and the backtest below fills that slot. You do not need to run `fit` again. Now back-test it (about 10 seconds). This is the step that says whether to trust a card:

```bash run
moot backtest --source sample
```

```text output
gates read from ~/moot-demo/mootcourt-data/reports/gates.json: {"base_rate": 0.3, "by_target": {"0.80": {"n_200": 50, "n_400": 100}, "0.90": {"n_200": 75, "n_400": 150}}, "decision_target": 0.9, "interval": {"by": "test", "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive of that rate (docs/method.md call 170)", "icc": 0.13, "level": 0.9, "rows_per_test": 3.5}, "n_200": 75, "n_400": 150}
gate sizes by base rate (tests): 0.30: n_200 75, n_400 150
filled the backtest summary of model 6e5029e03c73
scored 330 rows over 11 origins in 3.5 s (report writing 4.1 s)
wrote ~/moot-demo/mootcourt-data/reports/backtest-sample-20261104-80131c793938.md
wrote ~/moot-demo/mootcourt-data/reports/backtest-sample-20261104-80131c793938.json
wrote ~/moot-demo/mootcourt-data/reports/scores-sample-20261104-80131c793938.parquet
```

The first two lines say which gates the backtest read. `moot init` wrote them with a quick simulation, in tests, at one base rate (0.3). `moot simulate gate-power` sizes the gates at the base rate of your own archive; for this walk-through you can ignore it. Open the report it names, `mootcourt-data/reports/backtest-sample-....md`. The Brier skill (how much better than always forecasting the base rate) is in the section whose heading starts "Brier score of p_sig" (search the report for it), in the row `ALL`, rung `P2`. On this synthetic sample its interval contains zero. In the first table, read the column `decidable_by_tests`: it says "decidable at skill 0.20 only", meaning that the 110 scored tests reach the gate for a skill difference of 0.20 and not the one for 0.10. `decidable_research_by_tests` is the same reading at the power 0.80 screen. Ignore the columns `decidable` and `decidable_research`, which read "not computed" when the gates count tests, because they would compare a number of rows with a number of tests. That is the right reading of a sample with no structure, and it is what the report is for.

Ask for a card (about a second). The sample is static, so `--now` issues it as of the end of its history; on a live ledger you leave `--now` out:

```bash run
moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: 1705a34c4ed02a00
- Source: sample
- Cell: checkout_conversion
- Origin: 2025-12-30T00:00:00+00:00
- Ledger snapshot: 20261104-80131c793938
- Model: 6e5029e03c73
- Feature hash: e7ee5b832720
- Issued at: 2025-12-30T00:00:00+00:00
- Request: headline "", image changed: no, exposures per arm: 20000, standard error of the future estimate: 0.015 units of the ledger's effect

## Evidence

- Admitted rows in the cell visible at the origin: 120
- Effective number of precedents: 119.3
- Base rate of significant positive results in the cell (P0): 0.275

## Prediction

- P(significant and positive): 0.249
- Point estimate: 0.01 units of the ledger's effect
- 80 percent interval for the true effect: -0.03 to 0.05 units of the ledger's effect
- 80 percent interval for the result of the test at the planned standard error: -0.04 to 0.05 units of the ledger's effect
- P(true effect above 0): 0.585
- Rung: P2, weight on precedents 0.0

## Team forecast

- None provided.

## Robustness

- Not applicable: the weight on precedents is zero, so the card uses the cell prior and no precedent can change it.

## Skill at this n

- Brier skill against the cell base rate, trailing 8 weeks: 0.093 (90 percent interval -0.227 to 0.221, by test), measured on 7 rows from 7 tests, as of 2025-12-29T00:00:00+00:00
- Gate at this n: 7 tests: undecidable at this n (the gate needs 150 tests for a skill of 0.10 and 75 for 0.20 at base rate 0.30), and its interval includes zero
- Latest gated backtest, rung P2: Brier skill 0.020 (90 percent interval -0.007 to 0.046) over 110 tests

## Abstention

- Status: issue
- Reasons: none

---

The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.
```

Read `Abstention` first, then the probability against the base rate, then the interval. The section `Skill at this n` is the card's own record, the skill line: how forecasts like it did recently and in the backtest, with intervals and the gate verdict. [Tutorial 1](docs/tutorials/01-first-card.md) explains each line.

Check the setup. The output goes to a file so that the exit code can be printed; piping it into `tail` would hide the code:

```bash run head=6
moot doctor > doctor.txt; echo "exit code: $?"
tail -n 5 doctor.txt
```

```text output
exit code: 1
OK    ledger: ~/moot-demo/mootcourt-data/data/ledger/ledger.parquet conforms
OK    model sample: champion 6e5029e03c73 on snapshot 20261104-80131c793938
WARN  reliability sample: 3 of 3 entries are stale (limit 14 days, oldest 310 days old): checkout_conversion, pages_per_session, revenue_per_user; those cells abstain until new outcomes for the cell are joined
OK    cells: 3 configured cells, each with 20 or more admitted rows
status: warn
```

The exit code printed on the first line is 0 when healthy, 1 with warnings and 2 with failures. The warning here is correct: the sample ledger ends in 2025, so its reliability report is old, and cards for a live ledger abstain when that report is older than 14 days.

## What the results show, and what the project does not show

- **Headline-test skill is not deployment skill.** The main archive is headline and image tests from one publisher. Nothing here measures whether a forecaster that predicts them predicts product experiments.
- **The headline result is modest.** On the Upworthy archive no rung of the ladder is distinguishable from always forecasting the base rate, and weighing similar headlines does not improve on the pooled prior out of time. Nulls are reported as nulls.
- **ASOS is undecidable at its n.** The deployment-shaped archive has a few hundred contrasts in under a hundred tests, and the results mark each cell as decidable or undecidable at the release gate, sized at the archive's own base rate; every ASOS cell is undecidable. That file has no dates, so its calendar is nominal and says nothing about drift.
- **Scores are against the observed estimate, not the unknown true effect.** A predictor is judged on the estimate a test produced, noise included.
- **Two stand-ins on Upworthy.** The archive does not record when a test was read, so a test is treated as final seven days after its latest arm was created. It does not record planned exposure either, so realized impressions stand in, and that stand-in can leak: log impressions correlate +0.099 with the absolute standardized effect on the admitted rows (`DATA.md`, `docs/method.md`).
- **Not every rung is exercised on real data.** The team-forecast rung needs a forecast frozen before the test, and no archive holds one. It runs on synthetic data only.
- **It is not a decision tool.** No ship, rollout, allocation, ramp or stopping recommendation comes out of it.

## Headline results

<!-- moot-headline:start -->
- Upworthy, 13247 scored rows: Brier skill against the base rate on all rows is 0.0015 (-0.0018 to 0.0048) for P1 (not distinguishable from the constant base rate) and 0.0015 (-0.0017 to 0.0047) for P2 (not distinguishable from the constant base rate); 0 of 3 cells are undecidable at this n at the release gate.
- ASOS, 337 scored rows: Brier skill against the base rate on all rows is -0.1073 (-0.2366 to -0.0020) for P1 (worse than the constant base rate) and -0.1073 (-0.2366 to -0.0020) for P2 (worse than the constant base rate); 4 of 4 cells are undecidable at this n at the release gate.
<!-- moot-headline:end -->

The full tables (calibration, abstention, decision value, challengers, ablations, the cautionary first run and run times) are in [docs/results.md](docs/results.md). They are generated from the report files, and `scripts/verify_readme_numbers.py` re-derives every number independently.

## Learn more

| You want to | Read |
|---|---|
| Walk through a first card with every output explained | [Tutorial 1](docs/tutorials/01-first-card.md) |
| Bring your own archive | [Tutorial 2](docs/tutorials/02-your-own-archive.md) |
| Reproduce the Upworthy study | [Tutorial 3](docs/tutorials/03-reproduce-upworthy.md) |
| Run the weekly loop | [Tutorial 4](docs/tutorials/04-weekly-loop.md) |
| Serve cards over HTTP or MCP | [Tutorial 5](docs/tutorials/05-serve-http-and-mcp.md) |
| Attach a response-simulation agent | [Tutorial 6](docs/tutorials/06-simulation-agent.md) |
| Look up a term | [Concepts and glossary](docs/concepts.md) |
| Look up a command or a setting | [Command guide](docs/commands.md), [configuration](docs/reference/config.md) |
| Fix a problem | [Troubleshooting](docs/troubleshooting.md), [FAQ](docs/faq.md) |
| Know what was decided and why | [Method](docs/method.md), [Limitations](docs/limitations.md), [Data](DATA.md) |

`make docs` builds the manual as a site. Every command in this README, in the command guide and in the tutorials is run by the test suite against a temporary folder, and the output shown is what it printed.

## More you can do

```bash
moot serve      # HTTP: POST /card, GET /reliability/{source}, GET /health on 127.0.0.1:8000
moot mcp        # Model Context Protocol server over stdio: get_card, list_precedents, reliability_report
moot backtest --source sample --challenger gbm     # add a gradient-boosted regressor as one more rung
```

The service has no authentication and binds to the loopback address by default: put your own access control in front of it before exposing it. Models are loaded only from local artifacts that `moot fit` wrote, checked by a digest, and never from downloads. A card's three ids are content digests and are platform-specific: compare a card by its stored ids, never by recomputing them (see [troubleshooting](docs/troubleshooting.md#ids-differ-between-machines)).

To reproduce the published study on the two public archives, `make setup`, `make data`, `make fit` and `make backtest` run it end to end, as [tutorial 3](docs/tutorials/03-reproduce-upworthy.md) describes. Everything heavy goes under one data root: set `MOOTCOURT_DATA_ROOT` or `[storage] data_root` in `mootcourt.toml`, for example to an external volume (exFAT is fine) for large runs.

## License and citations

MIT. Data: Matias et al., Scientific Data 8, 195 (2021), doi 10.1038/s41597-021-00934-7 (Upworthy Research Archive, CC BY 4.0, Cornell University). Liu, Cardoso, Couturier and McCoy, NeurIPS 2021 Datasets and Benchmarks, arXiv 2111.10198 (ASOS Digital Experiments Dataset, CC BY 4.0, DOI 10.17605/OSF.IO/64JSB).
