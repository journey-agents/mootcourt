# Tutorial 1: your first card in five minutes

**You will:** install the package, create a project folder with a synthetic sample ledger, back-test the forecaster on it and issue one forecast card.

**Prerequisites:** Python 3.11 or newer and a terminal. No network after the install, no data of your own, no account.

**Time:** about five minutes once the package is installed (the install adds a few more), of which the commands take about a minute on the internal disk (several times longer with the data root on exFAT). The times below are from a laptop. (These are the same commands as the README quickstart, with every output explained. Use a new folder, as below, if you already ran that.)

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

From a clone of the repository, make and activate an environment of your own and install the package into it. Keep the clone and its environment on your **internal disk**. On an exFAT or other external volume macOS writes `._` sidecar files into the environment, and both install paths break: `pip install -e .` succeeds but `moot backtest` later fails with `Cannot decode configuration file ... .__classic_test_patch.mplstyle ... utf-8`, and `uv sync` fails with `RECORD file doesn't match wheel contents ... ._ruff`. The [troubleshooting page](../troubleshooting.md#working-from-a-clone-on-an-exfat-volume) has both error texts and the cure. The data root may live on an external drive, but sample-sized commands are several times slower there (one measurement: `moot init` 90 s and `moot backtest` 97 s, against 24 s and 12 s on the internal disk).


```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

With `uv`, run `uv sync --all-extras` in the clone instead (on an external volume, first set `UV_PROJECT_ENVIRONMENT` to a path on the internal disk). `uv run moot ...` finds the package only from inside the clone, and the project folder of step 2 is outside it. So either activate the environment (`source /path/to/clone/.venv/bin/activate`, or the folder named by `UV_PROJECT_ENVIRONMENT`) and call `moot` as below, or write `uv run --project /path/to/clone moot ...` wherever the page says `moot ...`. Check it worked:

```bash run
moot --version
```

```text output
0.1.0
```

## 2. Create a project folder

Make an empty folder and let `moot init` fill it. It takes about 20 seconds on a laptop with the data root on the internal disk, because it also simulates the quick gates file (on a very first run, with cold caches, or on a loaded machine it can take a minute). On an exFAT volume it can take 90 seconds, with no progress line.

```bash run
mkdir moot-first && cd moot-first
moot init
```

```text output
the quick gates simulation (synthetic data): still running, 10 s elapsed
progress: base rate 0.09, power 0.80, skill 0.20: n = 125 (12 s elapsed)
the quick gates simulation (synthetic data): still running, 20 s elapsed
progress: base rate 0.09, power 0.80, skill 0.10: n = 200 (25 s elapsed)
progress: base rate 0.09, power 0.90, skill 0.20: n = 175 (26 s elapsed)
the quick gates simulation (synthetic data): still running, 30 s elapsed
progress: base rate 0.09, power 0.90, skill 0.10: n = 250 (32 s elapsed)
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
snapshot 20261105-b04b5b1dd18c for sample
ledger ~/moot-first/mootcourt-data/data/ledger/ledger.parquet: 360 rows
```

What to look at: **admitted** must equal the row count unless you expect exclusions. Admission is a status, never a filter: a row that fails a rule (too few units in an arm, a sample ratio mismatch) is kept and counted, and only admitted rows teach a model. The **snapshot** is a name made from the date and a digest of the ledger content. Importing the same file again changes nothing and gives the same digest.

## 4. Fit the models and back-test them

```bash run
moot fit --source sample
moot backtest --source sample
```

```text output
fitted model 6b43ae900d91 at snapshot 20261105-b04b5b1dd18c on 360 rows usable at 2026-11-05T11:03:41.846471+00:00 in 1.7 s; it is the champion for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
gates read from ~/moot-first/mootcourt-data/reports/gates.json: {"base_rate": 0.09, "by_target": {"0.80": {"n_200": 125, "n_400": 200}, "0.90": {"n_200": 175, "n_400": 250}}, "decision_target": 0.9, "icc": 0.13, "interval": {"by": "test", "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive of that rate (docs/method.md call 170)", "icc": 0.13, "level": 0.9, "rows_per_test": 3.5}, "n_200": 175, "n_400": 250, "rows_per_test": 3.5}
gate sizes by base rate (tests): 0.09: n_200 175, n_400 250
filled the backtest summary of model 6b43ae900d91
scored 330 rows over 11 origins in 5.0 s (report writing 18.7 s; the whole run 23.7 s)
wrote ~/moot-first/mootcourt-data/reports/backtest-sample-20261105-b04b5b1dd18c.md
wrote ~/moot-first/mootcourt-data/reports/backtest-sample-20261105-b04b5b1dd18c.json
wrote ~/moot-first/mootcourt-data/reports/scores-sample-20261105-b04b5b1dd18c.parquet
```

`fit` makes the forecaster from the ledger. The level of each period (quarter) in the fit is taken from the last complete quarter, because the latest quarter of a ledger is usually thin; the backtest, which fits at quarter starts, is unaffected. The first model for a source becomes its **champion**. The model id covers the snapshot id, which begins with the date of the import, so your model id and card id differ from the ones printed here on another day; compare the numbers, not the ids. The line "no backtest exists" is expected the first time: the backtest then fills that slot, as the next lines say. The backtest takes about twenty seconds here, most of it writing the report, and minutes on a ledger with tens of thousands of rows.

The backtest scored 330 rows over 11 quarterly origins. Open the Markdown report named in the last lines, `reports/backtest-sample-....md`, and read three things before you trust any card:

1. **Brier skill** (section "Brier score of p_sig against the significant-positive event"): one minus the forecaster's Brier score over the Brier score of a constant base rate. Zero means no better than always forecasting the base rate. Look at the 90 percent bootstrap interval beside it (the columns `brier_skill_lo` and `brier_skill_hi`). In the row `ALL`, rung `P2`, the skill is about 0.02 and the interval (about 0.00 to 0.04, its lower end a hair below zero) does not clear zero. The sample ledger was generated with only a faint structure, so a skill that is barely distinguishable from nothing is the right answer. The report says it in the first table: the column `decidable_by_tests` reads "undecidable at this n" for every comparison, because 110 tests are below the gate of 175 for a skill difference of 0.20. The columns `decidable` and `decidable_research` beside it carry the same verdict in the unit of the gates (by tests, when the gates count tests).
2. **Coverage** (section "Direction accuracy and coverage of the intervals for y"): the share of outcomes inside the central 80 and 90 percent intervals should be near 0.80 and 0.90. Judge it by the bootstrap interval printed beside it: if the interval contains 0.80 (or 0.90), the intervals are calibrated at this n; if it lies below, they are overconfident. On this sample P2's 80 percent coverage is 0.72 with an interval of 0.68 to 0.76, so the intervals are a little overconfident.
3. **Gates**: the header gives two numbers of scored experiments, one for a skill difference of 0.20 and one for 0.10: 175 and 250 at the release gate. The release gate is the power 0.90 line of the header; the power 0.80 line below it is a research screen. A difference of that size cannot be told from zero with fewer experiments. The report scored 110 experiments (the `n_tests` column of the first table), which is below both, so the table says "undecidable at this n" (and the same at the power 0.80 screen, whose gates are 125 and 200). These numbers come from the quick gates file that `moot init` wrote: it sizes the gate in tests at one base rate (0.09, the base rate of the Upworthy archive, which the sample ledger is drawn to resemble), and the line after the "gates read" line lists the sizes. For your own archive, `moot simulate gate-power` sizes the gate in tests at your base rate ([tutorial 2](02-your-own-archive.md)).

## 5. Ask for a card

```bash run
moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: 75e9856f63b7e30a
- Source: sample
- Cell: checkout_conversion
- Origin: 2025-12-30T00:00:00+00:00
- Ledger snapshot: 20261105-b04b5b1dd18c
- Model: 6b43ae900d91
- Feature hash: e7ee5b832720
- Issued at: 2025-12-30T00:00:00+00:00
- Request: planned units per arm: 20000, standard error of the future estimate: 0.015 units of the ledger's effect

## Evidence

- Admitted rows in the cell visible at the origin: 120
- Effective number of precedents: 119.3
- Base rate of significant positive results in the cell (P0): 0.042

## Prediction

- P(significant and positive): 0.052
- Point estimate: -0.03 units of the ledger's effect
- 80 percent interval for the true effect: -0.06 to 0.01 units of the ledger's effect
- 80 percent interval for the result of the test at the planned standard error: -0.07 to 0.02 units of the ledger's effect
- P(true effect above 0): 0.200
- Rung: P2, weight on precedents 0.0

## Team forecast

- None provided.

## Robustness

- Not applicable: the weight on precedents is zero, so the card uses the cell prior and no precedent can change it.

## Skill at this n

- Latest gated backtest, pooled over all cells because this cell's own figure is undecidable at this n (at this cell's own dependence the gate needs 463 tests for a skill of 0.20 and 661 for 0.10; it has 110), rung P2: Brier skill 0.020 (90 percent interval 0.000 to 0.038) over 110 tests
- Brier skill against the cell base rate, trailing 8 weeks: 0.100 (90 percent interval -5.280 to 0.123, by test), measured on 7 rows from 7 tests, as of 2025-12-29T00:00:00+00:00, descriptive, one window of many
- Gate at this n: 7 tests: undecidable at this n (the gate needs 250 tests for a skill of 0.10 and 175 for 0.20 at the nearest simulated base rate, 0.09 (this cell's own rate is 0.042)), and its interval includes zero

## Abstention

- Status: issue
- Reasons: none

---

The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.
```

The sample ledger holds history only up to the end of 2025 and is never updated, so the card is issued as of the end of that history with `--now`. `--now` is the issue time: it sets what "recent" means for the reliability check. `--origin` is the time whose rows the forecaster may see, and it defaults to `--now`. With your own live ledger you leave both out and the card is issued as of today.

How to read the card, top to bottom:

- **Request**: what you asked about, in planned units per arm (the `--impressions` option keeps its name for compatibility). On a ledger without headline text, as here, the line carries no headline or image fields; a ledger with text shows the headline and whether the image changed. The "standard error of the future estimate" is how noisy the planned test will be at 20,000 units per arm. More units make it smaller, and a smaller one makes a significant result more likely.
- **Evidence**: how many admitted rows of this cell the forecaster could see at the origin. The effective number of precedents counts how many of them carry weight. The base rate is the share of past tests in this cell that ended significant and positive.
- **Prediction**: `P(significant and positive)` is the headline number, to be compared with the base rate 0.042 (about one in twenty-four tests in this cell ended significant and positive). Here it is 0.052: slightly above the base rate. The line `P(true effect above 0)` is a different probability: the chance that the true effect is positive, whatever the test will show, as opposed to the chance that the test will show a significant positive estimate. The first interval is for the true effect, which is what you read. The second, "for the result of the test at the planned standard error", is wider because it adds the noise the test will have: it is the interval a measured result is compared with, and the one the backtest's coverage is checked against. `Rung: P2, weight on precedents 0.0` means the weighted-precedent rung found no benefit in similar experiments for this cell and fell back to the pooled prior, which is what the guard against fitting noise should do on a ledger with no structure.
- **Team forecast**: your own probability of a significant positive result and your own point estimate, when you supply them. They are frozen with the card, so the weekly join can score them beside the model's. Here it says "None provided", because `moot card` has no option for them; only the HTTP service takes them, in the `team_forecast` field of `POST /card` (see the [card reference](../reference/card.md)).
- **Robustness**: how easily the forecast could flip to the other side of the action threshold, by dismissing precedents. Here the weight on precedents is 0.0, so the forecast does not depend on any particular precedent and the section says "Not applicable". With a weight above zero it counts the precedents the forecast leans on, asks how many of them, heaviest first, you would have to dismiss to push the probability across 0.35, and resamples the precedents to report the share of resamples that stay on the same side.
- **Skill at this n** (the skill line): the card's record, in three lines. The first is the Brier skill of this cell's most recent forecasts, from its reliability record, over the trailing eight weeks, with a 90 percent interval by test and the rows and tests it rests on. Seven rows from seven tests is very little, and the interval (minus 5.280 to 0.123, a lower end far below zero) says so. The second is the gate verdict at that many tests: "undecidable at this n", with the sizes the gate needs. The line says it in full: "at the nearest simulated base rate, 0.09 (this cell's own rate is 0.042)". The 0.09 is the simulated base rate of the gates file nearest the cell's own, not another measurement of the cell. A gates file written by the older per-row simulation (`moot simulate power`) would give a count of rows instead, and the line would say rows. The third is the latest gated backtest of the model, with its interval and the number of tests: 0.020 here, pooled over all cells because this cell's own figure is undecidable at this n (the line says so), a different measurement from the first line, because it covers the whole history. Treat the first line as no evidence.
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
OK    environment: no sidecar files under <env>/lib/python3.11/site-packages
OK    data root: ~/moot-first/mootcourt-data; free space 13.4 GB
OK    ledger: ~/moot-first/mootcourt-data/data/ledger/ledger.parquet conforms
OK    model sample: champion 6b43ae900d91 on snapshot 20261105-b04b5b1dd18c
WARN  reliability sample: 3 of 3 entries are stale (limit 14 days, oldest 311 days old): checkout_conversion, pages_per_session, revenue_per_user; those cells abstain until new outcomes for the cell are joined
OK    cells: 3 configured cells, each with 20 or more admitted rows
WARN  cards sample: 0 scored outcomes, 0 post-hoc cards (issued after their test started: recorded, never scored), 0 reissues (a later card for a row another card scores); no join scores these as they stand, cards with no row id: 1
status: warn
```

The exit code is 0 when everything is healthy, 1 with warnings and 2 with failures. The `python` and `package` lines show the versions installed in your environment, and the `environment` line its path (shown here as `<env>`), so yours will differ. Here the exit code is 1. The first warning is correct: the **reliability report** (the record of how well issued cards have done lately, seeded by the backtest) is dated at the end of the sample history, which is long before today. Cards for a live ledger abstain when that report is older than 14 days. You will refresh it in [tutorial 4](04-weekly-loop.md). The second, on `cards sample`, counts the card you issued in step 5, which names no ledger row (`cards with no row id: 1`), so no join could score it; tutorial 4 issues cards that name their row.

## What you have

A project folder with a ledger, a fitted model, a backtest report, one frozen card and a health check. The same six commands work on your own results: [tutorial 2](02-your-own-archive.md) shows how to bring them.
