# Tutorial 1: your first card in five minutes

**You will:** install the package, create a project folder with a synthetic sample ledger, back-test the forecaster on it and issue one forecast card.

**Prerequisites:** Python 3.11 or newer and a terminal. No network after the install, no data of your own, no account.

**Time:** about five minutes, of which the commands take about a minute. The times below are from a laptop. (These are the same commands as the README quickstart, with every output explained. Use a new folder, as below, if you already ran that.)

## Words you will meet

You will see these in every output. The [glossary](../concepts.md#glossary) has the full definitions.

- A **ledger** is the table of concluded experiments the forecaster learns from: one row per variant, per metric, per experiment, with the measured effect and its standard error.
- A **cell** is a group of alike experiments that share a base rate, for example "checkout conversion". Every forecast is made inside one cell.
- A **precedent** is a past experiment in the same cell that is similar to the proposal. A forecast weighs precedents by how similar and how precise each was.
- A **rung** is one predictor in the ladder. P0 forecasts the cell's base rate, P1 adds a prior that pools the cells and shrinks each toward the whole while it accounts for measurement error, and P2 adds a weighing of the precedents under an admission guard. A card says which rung produced its forecast and the weight it put on precedents. A weight of 0.0 means that similar experiments did not help, so P2 gave the same answer as P1.
- A **card** is the forecast for one proposed experiment: the chance that it ends significant and positive, an interval for the true effect, and how fragile that opinion is. A card can also decline to give an opinion, which is called an **abstention**.
- The **action threshold** is the probability above which your team would act (0.35 by default, set in `mootcourt.toml`). The card asks how easily its forecast could fall on the other side of it.
- A **backtest** replays the ledger quarter by quarter. Each past experiment is forecast using only the rows that were already final before it, then scored against what it showed. This tells you whether the cards can be trusted.
- An **origin** is a point in time. A card issued at an origin sees only rows that were usable at that time.
- A **snapshot**, a **model id** and a **feature hash** are short ids on every card: they name the exact version of the ledger, of the fitted model and of the features the card was made from.

## 1. Install

From a clone of the repository, make and activate an environment of your own and install the package into it:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

With `uv`, `uv sync` does the same and `uv run moot ...` replaces `moot ...` below. Check it worked:

```bash run
moot --version
```

```text output
0.1.0
```

## 2. Create a project folder

Make an empty folder and let `moot init` fill it. It takes about 20 seconds on a laptop, because it also simulates the quick gates file (on a very first run, with cold caches, or on a loaded machine it can take a minute).

```bash run
mkdir moot-first && cd moot-first
moot init
```

```text output
wrote ~/moot-first/mootcourt.toml
data root ~/moot-first/mootcourt-data (layout created)
sample ledger ~/moot-first/mootcourt-data/data/sample-ledger.csv (synthetic)
quick gates ~/moot-first/mootcourt-data/reports/gates.json (400 replicates; run `moot simulate gate-power` for the full simulation)
Next, from the project folder:
  1. moot ingest --format generic --input ~/moot-first/mootcourt-data/data/sample-ledger.csv --source-name sample
  2. moot fit --source sample && moot backtest --source sample
  3. moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

Three things were created. `mootcourt.toml` holds the settings (see the [configuration reference](../reference/config.md)). The **data root** `mootcourt-data/` holds everything that grows: the ledger, fitted models, reports and cards. The sample ledger is synthetic, made by a generator, and exists only so that you can run every command. The quick gates file says how many scored experiments a comparison needs before it means anything. `init` prints the three commands that come next, and this tutorial runs them.

## 3. Import the sample ledger

```bash run
moot ingest --format generic --input mootcourt-data/data/sample-ledger.csv --source-name sample
```

```text output
360 rows from 120 experiments
  admitted: 360
admitted by cell: checkout_conversion 120, pages_per_session 120, revenue_per_user 120
final reads from 2023-01-23 to 2025-12-29
snapshot 20261104-80131c793938 for sample
ledger ~/moot-first/mootcourt-data/data/ledger/ledger.parquet: 360 rows
```

What to look at: **admitted** must equal the row count unless you expect exclusions. Admission is a status, never a filter: a row that fails a rule (too few units in an arm, a sample ratio mismatch) is kept and counted, and only admitted rows teach a model. The **snapshot** is a name made from the date and a digest of the ledger content. Importing the same file again changes nothing and gives the same digest.

## 4. Fit the models and back-test them

```bash run
moot fit --source sample
moot backtest --source sample
```

```text output
fitted model 097a3bd3b39b at snapshot 20261104-80131c793938 in 1.6 s; it is the champion for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
gates read from ~/moot-first/mootcourt-data/reports/gates.json: {"base_rate": 0.3, "by_target": {"0.80": {"n_200": 50, "n_400": 100}, "0.90": {"n_200": 75, "n_400": 150}}, "decision_target": 0.9, "interval": {"by": "test", "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive of that rate (docs/method.md call 170)", "icc": 0.13, "level": 0.9, "rows_per_test": 3.5}, "n_200": 75, "n_400": 150}
gate sizes by base rate (tests): 0.30: n_200 75, n_400 150
filled the backtest summary of model 097a3bd3b39b
scored 330 rows over 11 origins in 4.0 s (report writing 4.7 s)
wrote ~/moot-first/mootcourt-data/reports/backtest-sample-20261104-80131c793938.md
wrote ~/moot-first/mootcourt-data/reports/backtest-sample-20261104-80131c793938.json
wrote ~/moot-first/mootcourt-data/reports/scores-sample-20261104-80131c793938.parquet
```

`fit` makes the forecaster from the ledger. The first model for a source becomes its **champion**. The line "no backtest exists" is expected the first time: the backtest then fills that slot, as the next lines say. The backtest takes about ten seconds here and minutes on a ledger with tens of thousands of rows.

The backtest scored 330 rows over 11 quarterly origins. Open the Markdown report named in the last lines, `reports/backtest-sample-....md`, and read three things before you trust any card:

1. **Brier skill** (section "Brier score of p_sig against the significant-positive event"): one minus the forecaster's Brier score over the Brier score of a constant base rate. Zero means no better than always forecasting the base rate. Look at the 90 percent bootstrap interval beside it (the columns `brier_skill_lo` and `brier_skill_hi`). In the row `ALL`, rung `P2`, the skill is about 0.02 and the interval contains zero. The sample ledger was generated without any real structure, so that is the right answer. The report says it in the first table: the column `decidable_by_tests` reads "decidable at skill 0.20 only" for every comparison: 110 tests reach the gate of 75 for a skill difference of 0.20 but not the gate of 150 for 0.10. Ignore the columns `decidable` and `decidable_research` beside it, which read "not computed" when the gates count tests, because they would compare a number of rows with a number of tests.
2. **Coverage** (section "Direction accuracy and coverage of the intervals for y"): the share of outcomes inside the central 80 and 90 percent intervals should be near 0.80 and 0.90. Judge it by the bootstrap interval printed beside it: if the interval contains 0.80 (or 0.90), the intervals are calibrated at this n; if it lies below, they are overconfident. On this sample P2's 80 percent coverage is 0.73 with an interval of 0.69 to 0.77, so the intervals are a little overconfident.
3. **Gates**: the header gives two numbers of scored experiments, one for a skill difference of 0.20 and one for 0.10: 75 and 150 at the release gate. The release gate is the power 0.90 line of the header; the power 0.80 line below it is a research screen. A difference of that size cannot be told from zero with fewer experiments. The report scored 110 experiments (the `n_tests` column of the first table), which is above the first and below the second, so the table says "decidable at skill 0.20 only" (and "decidable at skill 0.20 and 0.10" at the power 0.80 screen, whose gates are 50 and 100). These numbers come from the quick gates file that `moot init` wrote: it sizes the gate in tests at one base rate (0.3), and the line after the "gates read" line lists the sizes. For your own archive, `moot simulate gate-power` sizes the gate in tests at your base rate ([tutorial 2](02-your-own-archive.md)).

## 5. Ask for a card

```bash run
moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: 8f5b904729f2bbd2
- Source: sample
- Cell: checkout_conversion
- Origin: 2025-12-30T00:00:00+00:00
- Ledger snapshot: 20261104-80131c793938
- Model: 097a3bd3b39b
- Feature hash: e7ee5b832720
- Issued at: 2025-12-30T00:00:00+00:00
- Request: headline "", image changed: no, exposures per arm: 20000, standard error of the future estimate: 0.015 units of the ledger's effect

## Evidence

- Admitted rows in the cell visible at the origin: 120
- Effective number of precedents: 119.2
- Base rate of significant positive results in the cell (P0): 0.275

## Prediction

- P(significant and positive): 0.220
- Point estimate: 0.00 units of the ledger's effect
- 80 percent interval for the true effect: -0.03 to 0.04 units of the ledger's effect
- 80 percent interval for the result of the test at the planned standard error: -0.04 to 0.05 units of the ledger's effect
- P(true effect above 0): 0.551
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

The sample ledger holds history only up to the end of 2025 and is never updated, so the card is issued as of the end of that history with `--now`. `--now` is the issue time: it sets what "recent" means for the reliability check. `--origin` is the time whose rows the forecaster may see, and it defaults to `--now`. With your own live ledger you leave both out and the card is issued as of today.

How to read the card, top to bottom:

- **Request**: what you asked about. The "standard error of the future estimate" is how noisy the planned test will be at 20,000 units per arm. More units make it smaller, and a smaller one makes a significant result more likely.
- **Evidence**: how many admitted rows of this cell the forecaster could see at the origin. The effective number of precedents counts how many of them carry weight. The base rate is the share of past tests in this cell that ended significant and positive.
- **Prediction**: `P(significant and positive)` is the headline number, to be compared with the base rate 0.275. Here it is 0.220: slightly below the base rate. The first interval is for the true effect, which is what you read. The second, "for the result of the test at the planned standard error", is wider because it adds the noise the test will have: it is the interval a measured result is compared with, and the one the backtest's coverage is checked against. `Rung: P2, weight on precedents 0.0` means the weighted-precedent rung found no benefit in similar experiments for this cell and fell back to the pooled prior, which is what the guard against fitting noise should do on a ledger with no structure.
- **Robustness**: how easily the forecast could flip to the other side of the action threshold, by dismissing precedents. Here the weight on precedents is 0.0, so the forecast does not depend on any particular precedent and the section says "Not applicable". With a weight above zero it counts the precedents the forecast leans on, asks how many of them, heaviest first, you would have to dismiss to push the probability across 0.35, and resamples the precedents to report the share of resamples that stay on the same side.
- **Skill at this n** (the skill line): the card's record, in three lines. The first is the Brier skill of this cell's most recent forecasts, from its reliability record, over the trailing eight weeks, with a 90 percent interval by test and the rows and tests it rests on. Seven rows from seven tests is very little, and the interval (minus 0.227 to 0.221) says so. The second is the gate verdict at that many tests: "undecidable at this n", with the sizes the gate needs. A gates file written by the older per-row simulation (`moot simulate power`) would give a count of rows instead, and the line would say rows. The third is the latest gated backtest of the model, with its interval and the number of tests: 0.020 here, a different measurement from the first line, because it covers the whole history. Treat the first line as no evidence.
- **Abstention**: `issue` means the card gives an opinion. When a card declines it says `abstain` and lists the reasons. See [troubleshooting](../troubleshooting.md#a-card-abstains).

The card is also saved, frozen, under `mootcourt-data/cards/`. Its id is a digest of its content, so it cannot be edited after the outcome is known.

## 6. Check the setup

```bash run exit=1
moot doctor
```

```text output
OK    python: 3.11.14 (needs 3.11 or newer)
OK    package numpy: 2.4.6 (needs 1.26 or newer)
OK    package scipy: 1.17.1 (needs 1.11 or newer)
OK    package pandas: 3.1.0 (needs 2.1 or newer)
OK    package pyarrow: 26.0.0 (needs 14 or newer)
OK    package scikit-learn: 1.9.1 (needs 1.4 or newer)
OK    package joblib: 1.6.0 (needs 1.3 or newer)
OK    package typer: 0.27.3 (needs 0.12 or newer)
OK    package fastapi: 0.162.0 (needs 0.110 or newer)
OK    package uvicorn: 0.54.0 (needs 0.29 or newer)
OK    package mcp: 2.3.0 (needs 1.2 or newer)
OK    package matplotlib: 3.11.2 (needs 3.8 or newer)
OK    data root: ~/moot-first/mootcourt-data; free space 11.7 GB
OK    ledger: ~/moot-first/mootcourt-data/data/ledger/ledger.parquet conforms
OK    model sample: champion 097a3bd3b39b on snapshot 20261104-80131c793938
WARN  reliability sample: 3 of 3 entries are stale (limit 14 days, oldest 310 days old): checkout_conversion, pages_per_session, revenue_per_user; those cells abstain until new outcomes for the cell are joined
OK    cells: 3 configured cells, each with 20 or more admitted rows
status: warn
```

The exit code is 0 when everything is healthy, 1 with warnings and 2 with failures. Here it is 1, and the one warning is correct: the **reliability report** (the record of how well issued cards have done lately, seeded by the backtest) is dated at the end of the sample history, which is long before today. Cards for a live ledger abstain when that report is older than 14 days. You will refresh it in [tutorial 4](04-weekly-loop.md).

## What you have

A project folder with a ledger, a fitted model, a backtest report, one frozen card and a health check. The same six commands work on your own results: [tutorial 2](02-your-own-archive.md) shows how to bring them.
