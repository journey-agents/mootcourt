# Quickstart: from install to a first card in ten minutes

This takes a fresh folder to a card on a small synthetic ledger. It needs no network after the install and no data of your own. A test runs the commands below in a temporary folder. [Tutorial 1](tutorials/01-first-card.md) walks through the same steps with every output shown and explained, and is the better first read.

## 1. Install

```
pip install -e .
```

(or `uv sync`). The command `moot` is then on your path. Python 3.11 or newer.

## 2. Create the project

```
moot init
```

The command takes about 20 seconds, because it also simulates the quick gates file. It writes `mootcourt.toml` (data root, the cells to forecast, the action threshold, the gate target and a place for simulators), creates the data root `mootcourt-data/` with its folders, writes a synthetic sample ledger and a quick gate file, and prints the three commands that follow.

## 3. Import the sample ledger

```
moot ingest --format generic --input mootcourt-data/data/sample-ledger.csv --source-name sample
```

The ledger holds 120 synthetic experiments with three metrics each. `--dry-run` shows the admission summary without writing. Your own results come in the same way, from a file in the exchange format or from a vendor export; see `docs/ledger-format.md`.

## 4. Fit the models and back-test them

**Options.** `--challenger gbm` adds a gradient-boosted comparison; `--seed` and `--bootstrap` fix the random draws and the interval resamples. See the [command guide](commands.md#moot-backtest).

```
moot fit --source sample
moot backtest --source sample
```

The backtest replays the history one quarter at a time, scores every rung of the ladder on rows it could not have seen, and seeds the reliability report that cards check. It writes a report under `mootcourt-data/reports/`; open the Markdown file first and read the skill and the calibration before you trust any card.

## 5. Ask for a card

**Options.** `--row-id` names the ledger row the weekly join will attach the outcome to; `--cell` is needed for a ledger of metrics. See the [command guide](commands.md#moot-card).

```
moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

The sample ledger is static, so the card is issued as of the end of its history (`--now`); with your own live ledger leave `--now` out. The card shows the chance that the test ends significant and positive, an interval for the true effect, how fragile the opinion is, the skill measured at this n, and whether the model abstains and why. It prioritizes and sizes the test; the live test decides.

## 6. Check health

**What to look at.** The last line, `status:`, and the exit code. The README and [tutorial 1](tutorials/01-first-card.md) explain each line of the output.

```
moot doctor
```

It checks versions, the data root and its free space, the ledger, whether the model is fresh, how old the reliability report is, and the service if you set one. Exit code 0 is healthy, 1 means warnings and 2 means failures. On the static sample it warns that the reliability report is old, which is correct: nobody has joined new results since 2025.

## Next

- Bring your own results: [Ledger format](ledger-format.md).
- Keep it current: `moot join` attaches new results to the issued cards that name their ledger row (`moot card --row-id`) and refreshes reliability (see [Operations](operations.md) and [tutorial 4](tutorials/04-weekly-loop.md)).
- Serve it: `moot serve` (HTTP) or `moot mcp`.
