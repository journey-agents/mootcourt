# Command guide

Every command is `moot <command>`. This page says, for each command, what it is for, what it reads, what it writes, one example with its real output, and the errors you are most likely to meet. The [command reference](reference/cli.md) lists every option and is generated from the code. `moot <command> --help` prints the same.

The examples run in order in one project folder, the way you would type them, and a test runs them on every change: the output shown is what the command printed. Durations are from a laptop. Exit codes: `0` success, `1` a handled problem (a warning from `doctor`, a refused import, a card that cannot be frozen), `2` a bad argument or a failed check.

Output paths are shown under `~/moot-commands`. Ids (a hexadecimal string such as a model id) and timings differ on your machine.

```bash run quiet
mkdir moot-commands && cd moot-commands
```

## Setting up and checking

### `moot init`

**Purpose.** Create a project folder: `mootcourt.toml`, the data root with its folders, a synthetic sample ledger and a quick gates file.

**Reads.** Nothing. **Writes.** `mootcourt.toml`, `mootcourt-data/` (or the folder you name with `--data-root`), `data/sample-ledger.csv`, `reports/gates.json`. It refuses to overwrite an existing `mootcourt.toml` unless you pass `--force`. About 3 seconds.

**Options you will use.** `--cells a,b` the cells you forecast, `--name`, `--data-root PATH` to put everything on another volume, `--dir` for another project folder.

```bash run
moot init
```

```text output
wrote ~/moot-commands/mootcourt.toml
data root ~/moot-commands/mootcourt-data (layout created)
sample ledger ~/moot-commands/mootcourt-data/data/sample-ledger.csv (synthetic)
quick gates ~/moot-commands/mootcourt-data/reports/gates.json (400 replicates; run `moot simulate power` for the full simulation)
Next, from the project folder:
  1. moot ingest --format generic --input ~/moot-commands/mootcourt-data/data/sample-ledger.csv --source-name sample
  2. moot fit --source sample && moot backtest --source sample
  3. moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

**Common errors.**

| Message | Cause and fix |
|---|---|
| `error: ... mootcourt.toml already exists; pass --force to overwrite it` (exit 1) | The folder is already a project. Use `--force` to start again, or `--dir` for a new folder. |

```bash run exit=1 quiet expect="already exists; pass --force to overwrite it"
moot init
```

### `moot doctor`

**Purpose.** Check that the setup is healthy before you rely on a card: Python and package versions, the data root and its free space, the ledger, whether each fitted model is fresh, how old each reliability report is, the configured cells and the service if you set one.

**Reads** the settings, the data root, the ledger and the reports. **Writes** `reports/doctor.json`. Under 3 seconds. **Exit code** 0 healthy, 1 warnings, 2 failures, so it can end a scheduled job.

```bash run
moot doctor > doctor.txt; echo "exit code: $?"
tail -n 5 doctor.txt
```

```text output
exit code: 1
OK    data root: ~/moot-commands/mootcourt-data; free space 12.5 GB
WARN  ledger: no ledger at ~/moot-commands/mootcourt-data/data/ledger/ledger.parquet; import results with `moot ingest`
WARN  models: no registry; run `moot fit --source NAME`
WARN  reliability: no reliability report; `moot backtest` seeds one and `moot join` keeps it current
status: warn
```

Right after `init` there is no ledger and no model yet, which is why these are warnings and not failures.

**Common errors.**

| Line | Cause and fix |
|---|---|
| `FAIL python: ... (needs 3.11 or newer)` | An older interpreter. Make an environment with Python 3.11 or newer. |
| `WARN model ...: champion ... was fit on snapshot ..., which no longer matches the ledger` | The ledger grew after the last fit. Run `moot fit`. |
| `WARN reliability ...: ... entries are stale` | Cards for those cells abstain until a join or a backtest refreshes the report. |
| `FAIL service ...: ... is not reachable` | `[service] url` is set and nothing answers. Start `moot serve` or remove the key. |
| `WARN data root: free space ...` | Move the data root to a larger volume. See [Configuration](reference/config.md). |

### `moot storage`

**Purpose.** Show where the heavy folders live, their sizes and the free space of their volumes. It warns below 10 GB.

**Reads** the folder sizes. **Writes** nothing. Under a second.

```bash run
moot storage
```

```text output
data root: ~/moot-commands/mootcourt-data  [set MOOTCOURT_DATA_ROOT or storage.data_root in mootcourt.toml]
raw         ~/moot-commands/mootcourt-data/data/raw  size 0 B  free 12.5 GB
ledger      ~/moot-commands/mootcourt-data/data/ledger  size 0 B  free 12.5 GB
reports     ~/moot-commands/mootcourt-data/reports  size 2.5 KB  free 12.5 GB
models      ~/moot-commands/mootcourt-data/models  size 0 B  free 12.5 GB
cards       ~/moot-commands/mootcourt-data/cards  size 0 B  free 12.5 GB
cache       ~/moot-commands/mootcourt-data/cache  size 0 B  free 12.5 GB
experiments ~/moot-commands/mootcourt-data/experiments  size 0 B  free 12.5 GB
```

## Bringing results in

### `moot ingest`

**Purpose.** Import concluded experiments into the ledger. It is idempotent: rows already present are unchanged, and importing the same file twice adds nothing.

**Reads** a file in the [exchange format](ledger-format.md), or a vendor export with `--format`, or any CSV or Parquet file with `--mapping`. **Writes** the ledger (`data/ledger/ledger.parquet`) and an immutable snapshot named by a digest of its content. **Time** about a second per few thousand rows.

**Options you will use.** `--format` (`generic` for the exchange format; `moot ledger formats` lists the rest), `--input`, `--source-name` (the name of this set of experiments in every later command), `--mapping`, `--dry-run` (print the admission summary, write nothing), `--usable-delay-days`, `--min-exposure`, and `--ledger` to write to a ledger file other than the default. Without `--format`, it builds the ledger of the two public archives from files that `scripts/download_data.py` fetched; see [tutorial 3](tutorials/03-reproduce-upworthy.md).

```bash run
moot ingest --format generic --input mootcourt-data/data/sample-ledger.csv --source-name sample
```

```text output
360 rows from 120 experiments
  admitted: 360
admitted by cell: checkout_conversion 120, pages_per_session 120, revenue_per_user 120
final reads from 2023-01-23 to 2025-12-29
snapshot 20261103-80131c793938 for sample
ledger ~/moot-commands/mootcourt-data/data/ledger/ledger.parquet: 360 rows
```

**What to look at.** The number of rows against the number of experiments; the **admitted** count (rows that failed an admission rule are kept and counted by reason, but do not teach the models); the date range of the final reads.

**Common errors.**

| Message | Cause and fix |
|---|---|
| `error: file not found: ...` (exit 1) | The path is wrong. Paths are relative to the folder you run from. |
| `error: row 5, column se: must be greater than zero` (exit 1) | The data row (counting from 1) and the column are named. Fix the export. Nothing was imported. |
| `Invalid value: unknown format 'x'; the formats are ...` (exit 2) | Use one of the listed formats, or `generic` with a mapping. |
| `unit 'relative' differs from 'absolute' used by row 3 in cell ...` | Rows pooled in one cell must share an effect unit (`absolute`, `relative`, `standardized`, `as_exported`). Convert, or give the metrics different cells. |

```bash run exit=1 quiet expect="file not found: missing.csv"
moot ingest --format generic --input missing.csv --source-name x
```

```bash run exit=2 quiet expect="unknown format 'nosuch'"
moot ingest --format nosuch --input x --source-name y
```

### `moot ledger check`

**Purpose.** Test a file against the exchange format: columns, types, duplicate row ids, impossible values, horizon violations (a row usable before it was final), missing provenance and mixed units. It takes an exchange file (CSV or Parquet) or a ledger Parquet file.

**Reads** the file. **Writes** nothing. **Exit code** 1 on any error or warning, so it can gate a pipeline. Each message names the column and, for rows, the row.

```bash run
moot ledger check mootcourt-data/data/ledger/ledger.parquet
```

```text output
ok: the file conforms to the ledger exchange format
```

**Common errors.** `error: column effect: required column is missing` (the file is a raw export: use `moot ingest --mapping` to turn it into a ledger, then check the ledger); `error: file not found: ...`.

```bash run exit=1 quiet expect="file not found: nope.csv"
moot ledger check nope.csv
```

### `moot ledger formats`

**Purpose.** List the export formats that have an importer, and say for each whether the export is documented by its vendor (the mapping follows the documentation) or is a template that you edit.

**Reads** nothing. **Writes** nothing.

```bash run head=1
moot ledger formats
```

```text output
generic: exchange columns, or any file through --mapping
```

Only the first line is shown; the list continues with the vendor formats, one per line. `generic` is the exchange format itself, and the only one you need when you write the file yourself.

## Fitting and scoring

### `moot fit`

**Purpose.** Fit P0, P1 and P2 on the current ledger snapshot, save the bundle and register it. The first model for a source is its champion, later ones are challengers.

**Reads** the ledger. **Writes** `models/<model id>/` with a manifest, and the registry. **Time** 1 to 2 seconds for a few hundred rows, about 15 seconds for 18,000 rows.

```bash run
moot fit --source sample
```

```text output
fitted model 57a727de0c15 at snapshot 20261103-80131c793938 in 1.4 s; it is the champion for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
```

**Common errors.**

| Message | Cause and fix |
|---|---|
| `Invalid value: the ledger ... has no rows for source nope` (exit 2) | No rows were imported under that `--source-name`. Check `moot ingest` ran, and the spelling. |

```bash run exit=2 quiet expect="has no rows for source nope"
moot fit --source nope
```

### `moot backtest`

**Purpose.** Replay the history quarter by quarter and score every rung on rows it could not have seen. This tells you whether the cards can be trusted, and it seeds the reliability report that cards check.

**Reads** the ledger and `reports/gates.json`. When the gates file is missing it runs a gate simulation first, which takes about a minute. **Writes** `reports/backtest-<source>-<snapshot>.md` and `.json`, the score table (`scores-...parquet`) and figures. **Time** about 10 seconds for a few hundred rows and about 3 minutes for 18,000 rows.

**Options you will use.** `--challenger gbm` (also `local_eb`, `text_lr`) to compare with another model; `--second-opinion FILE` ([tutorial 6](tutorials/06-simulation-agent.md)); `--bootstrap N` for the interval resamples; `--primary-metric` for a ledger with several metrics; the ablation flags (`--features`, `--lambda`, `--kappa`, `--drop-trigger`) in the [method page](method.md).

```bash run
moot backtest --source sample
```

```text output
gates read from ~/moot-commands/mootcourt-data/reports/gates.json: {"by_target": {"0.80": {"n_200": 125, "n_400": 275}, "0.90": {"n_200": 175, "n_400": 400}}, "decision_target": 0.9, "n_200": 175, "n_400": 400}
filled the backtest summary of model 57a727de0c15
scored 330 rows over 11 origins in 4.1 s (report writing 2.4 s)
wrote ~/moot-commands/mootcourt-data/reports/backtest-sample-20261103-80131c793938.md
wrote ~/moot-commands/mootcourt-data/reports/backtest-sample-20261103-80131c793938.json
wrote ~/moot-commands/mootcourt-data/reports/scores-sample-20261103-80131c793938.parquet
```

**What to look at.** Open the Markdown report. Read the Brier skill with its interval, the coverage, the abstention rate and the gates, as in [tutorial 1](tutorials/01-first-card.md#4-fit-the-models-and-back-test-them). The one-page version is `moot benchmark --ledger`.

**Common errors.** The same `has no rows for source` as `fit`. A ledger with fewer than about 20 admitted rows before its first quarterly origin cannot be back-tested: today it stops with a Python traceback that ends in `KeyError: 'cell'` and not with a sentence. Import more history. See [troubleshooting](troubleshooting.md#backtest-stops-with-keyerror-cell).

## Issuing cards

### `moot card`

**Purpose.** Issue a card for a proposed experiment and freeze it under `cards/`.

**Reads** the champion model (or `--model-id`), the reliability report and the settings. **Writes** `cards/<card id>.json`. **Prints** the card as Markdown, or as JSON with `--json`. About a second, most of it loading the model.

**Options you will use.** `--source` and `--impressions` (planned units per arm) always. `--cell` for a ledger with several metrics, where the cell is the metric. `--headline`, `--image-changed` and `--headline-changed` for a ledger with text features. `--guardrail CELL:DELTA` (repeatable) to add a guardrail metric, shown with `p_harm`. `--now` (the issue time, which sets what "recent" means for the reliability check) and `--origin` (the time whose rows the forecaster may see, default `--now`) to issue as of a past time, which a static ledger needs. `--simulator NAME` to add a second opinion.

```bash run head=24
moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: a96d585026449f64
- Source: sample
- Cell: checkout_conversion
- Origin: 2025-12-30T00:00:00+00:00
- Ledger snapshot: 20261103-80131c793938
- Model: 57a727de0c15
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
- P(true effect above 0): 0.551
```

A ledger can carry several metrics per experiment. Each metric is its own cell, scored in its own block of the backtest report, and a card names a primary metric with `--cell` and any number of guardrails with `--guardrail CELL:DELTA`. A guardrail shows `p_harm`, the probability that the true effect is worse than minus the margin `DELTA`, from the same ladder, and abstains on its own when its evidence is thin.

**What to look at.** `Abstention: Status` first. Then the probability against the cell's base rate, the interval, the rung and the weight on precedents, the robustness lines and the skill with the number of rows behind it. [Tutorial 1](tutorials/01-first-card.md#5-ask-for-a-card) goes through each line.

**Common errors.**

| Message | Cause and fix |
|---|---|
| `Invalid value: no fitted model for source nope in ...; run moot fit first` (exit 2) | Fit first, or fix the source name. |
| `Invalid value: --now 'yesterday' is not an ISO-8601 time` (exit 2) | Use a full time with an offset, such as `2025-12-30T00:00:00+00:00`. |
| `Invalid value: --image-changed must be true or false, got ...` (exit 2) | Pass `true` or `false`. |
| `error: card ... is frozen with different content` (exit 1) | The card id covers the content; a clash fails loudly instead of replacing a record. |
| a card with `Reason reliability: reliability report is older than 14 days` | Not an error: the cell has no recent record. See [troubleshooting](troubleshooting.md#a-card-abstains). |

```bash run exit=2 quiet expect="no fitted model for source nope"
moot card --source nope --impressions 100
```

## Running the loop

### `moot join`

**Purpose.** The weekly step: append newly concluded rows to the ledger, attach an outcome to every issued card whose row is now final, type each miss, and rewrite the reliability report.

**Reads** the ledger, the cards and, with `--new-rows`, a ledger Parquet file of new rows. **Writes** the appended ledger and a snapshot, `cards/outcomes/<card id>.json` (once, read-only) and `reports/reliability-<source>.json`. Seconds.

An outcome is attached only to a card that names its ledger row when issued, and only once the row's `usable_after` has passed at the join time (`--now`). See [tutorial 4](tutorials/04-weekly-loop.md) for the full cycle.

```bash run
moot join --source sample --now 2025-12-30T00:00:00+00:00
```

```text output
appended 0 rows; attached 0 outcomes {}; reliability in ~/moot-commands/mootcourt-data/reports/reliability-sample.json
```

With no cards that name a row there is nothing to attach, but the report's date moves, and the line says so.

**Common errors.** `Missing option '--source'` (exit 2); `error: P0 needs at least one admitted row` (exit 2), when the source has no admitted rows in the ledger.

```bash run exit=2 quiet expect="Missing option '--source'"
moot join
```

### `moot promote`

**Purpose.** Promote the challenger to champion only if it beats the champion by a margin at the gate's n.

**Reads** the registry and both models' backtest summaries. **Writes** the registry, only if the challenger earns the place. It prints each condition that failed. Under a second.

```bash run
moot promote --source sample
```

```text output
not promoted: no challenger is registered, nothing to promote
```

There is no challenger yet: every fit after the first one makes one. See [tutorial 4](tutorials/04-weekly-loop.md#5-refit-back-test-and-promote) for a promotion attempt with the reasons it fails.

**Common errors.** `not promoted: no challenger is registered` (fit again after new rows, then back-test the new model first); `not promoted: Brier skill gain ... is short of the margin` and `the challenger's backtest has N tests, below gate n` are the rule working, not errors: the champion stays.

## Second opinions

### `moot simulators list`

**Purpose.** List the providers you can attach: the two built-ins, the tables in `mootcourt.toml` and any registered entry points, with version, knowledge cutoff and the weight each has earned.

**Reads** the settings and the registry. **Writes** nothing.

```bash run
moot simulators list
```

```text output
name              adapter      version  knowledge cutoff  cost      weight earned
heuristic         builtin      1        none              free      0 (not earned)
null              builtin      1        none              free      0 (not earned)
```

### `moot simulators run`

**Purpose.** Run one provider once over the rolling-origin request set of a source and write one record per request. Results are cached by provider, version and request digest, so a second run calls the agent zero times.

**Reads** the ledger and the provider's table. **Writes** the records file (JSONL) and the cache. **Time** the agent's latency times the number of rows. Use `--limit N` for a trial. A provider with a network call costs money: read the cost on the last line.

```bash run
moot simulators run --provider heuristic --source sample --limit 60 --out heuristic.jsonl
```

```text output
heuristic 1: 60 requests, 60 called, 0 from the cache, 0 declined, 0 failed (recorded, not cached); cost 0.0000 dollars, agent latency 0.0 s, wall 0.0 s
wrote heuristic.jsonl
```

**Common errors.** `Invalid value: unknown provider 'nope'; known: ...` (exit 2); `provider X: knowledge_cutoff is required` (add the key to the table); a failure line in the summary, such as a timeout or a non-zero exit of the agent (the run still finishes, the failures are recorded and not cached).

```bash run exit=2 quiet expect="unknown provider 'nope'"
moot simulators run --provider nope --source sample --out x.jsonl
```

### `moot earn-weight`

**Purpose.** Decide whether the provider's opinion earns a weight in the stacked probability. The weight stays zero until the provider beats the model on later origins by the promotion margin with enough distinct experiments.

**Reads** the records file and the backtest scores of the current snapshot. **Writes** the registry when a weight is earned or reset. Seconds.

```bash run
moot earn-weight --source sample --second-opinion heuristic.jsonl
```

```text output
heuristic 1 on all origins, scores scores-sample-20261103-80131c793938.parquet, 30 judged rows (10 tests) with an opinion: 30 judged rows with an opinion from 10 tests is below the gate of 400 tests; weight stays 0
```

**Common errors.** `error: ...: No such file or directory` (exit 2) for a wrong records path; `no backtest scores for SOURCE at snapshot ...; run moot backtest` means the ledger changed since the last backtest: run it again.

## Reporting and planning

### `moot benchmark`

**Purpose.** Two modes, exactly one at a time. `--ledger FILE` runs the standard protocol and writes the one-page report card, which holds aggregates only and can be shared. `--scale N` times the tool on a synthetic ledger of N contrasts ([Scale](scale.md)).

**Reads** a ledger. **Writes** `reports/benchmark/<ledger stem>-<snapshot>.md` and `.json`. About 7 seconds for 360 contrasts.

```bash run
moot benchmark --ledger mootcourt-data/data/ledger/ledger.parquet
```

```text output
scoring 360 contrasts of source sample
wrote ~/moot-commands/mootcourt-data/reports/benchmark/ledger-20261103-80131c793938.md
wrote ~/moot-commands/mootcourt-data/reports/benchmark/ledger-20261103-80131c793938.json
```

**What to look at.** [Tutorial 2](tutorials/02-your-own-archive.md#7-read-the-report-card) reads each section.

**Common errors.** `Invalid value: give exactly one of --scale N and --ledger FILE` (exit 2). A ledger that holds several sources needs `--source NAME` to choose one.

```bash run exit=2 quiet expect="give exactly one of --scale N and --ledger FILE"
moot benchmark
```

### `moot simulate ledger`

**Purpose.** Write a synthetic ledger with known truth, labeled synthetic. Use it to try commands or to test a pipeline.

**Writes** the Parquet file named by `--out`. **Options** `--n-tests`, `--seed`.

```bash run
moot simulate ledger --out synthetic.parquet --n-tests 40
```

```text output
wrote 80 synthetic rows to synthetic.parquet (label: synthetic)
```

### `moot simulate power`

**Purpose.** Simulate the release gates (how many scored experiments a skill difference needs before it can be told from zero) and write `reports/gates.json`. Everything here is synthetic.

**Writes** the gates file (or the path in `--out`). The default of 1,000 simulated gates per point takes about a minute; `moot init` writes a quick version. The example uses a small run and writes to a separate file so that it does not replace your gates.

```bash run
moot simulate power --reps 40 --bootstrap 50 --out gates-small.json
```

```text output
Gate power (synthetic data only), share of simulated gates whose 95 percent interval clears zero
skill \ n       100     125     150     250     400     500    1000    2000
0.05           0.25    0.33    0.38    0.47    0.70    0.90    1.00    1.00
0.10           0.53    0.55    0.62    0.82    1.00    1.00    1.00    1.00
0.20           0.78    0.82    0.93    0.97    1.00    1.00    1.00    1.00
0.30           0.93    0.97    0.95    1.00    1.00    1.00    1.00    1.00
power 0.80: n_200 = 125 (skill 0.20), n_400 = 250 (skill 0.10)
power 0.90: n_200 = 150 (skill 0.20), n_400 = 400 (skill 0.10)
release gate = power 0.90; reps 40, bootstrap 50, 0.3 s. Synthetic data. Wrote gates-small.json
```

The two lines to read are the gates, `n_200` (the number of scored experiments at which a Brier skill difference of 0.20 is decidable) and `n_400` (for 0.10), at power 0.90 and 0.80. A small run is noisy; use the default for a decision.

## Serving

### `moot serve`

**Purpose.** Start the HTTP service: `POST /card`, `GET /reliability/{source}`, `GET /health`. It binds to `127.0.0.1:8000` by default and has no authentication.

**Reads** models, reports and the settings once at start. **Writes** only the card that `POST /card` freezes. It runs until you stop it. [Tutorial 5](tutorials/05-serve-http-and-mcp.md) goes through it.

```bash run
moot serve --port 8731 > serve.log 2>&1 &
SERVER=$!
until curl -sf http://127.0.0.1:8731/health > /dev/null; do sleep 0.5; done
curl -s http://127.0.0.1:8731/health | head -c 60
echo
kill $SERVER
wait $SERVER 2> /dev/null || true
```

```text output
{"status":"ok","sources":["sample"],"boundary":"The card pri
```

**Common errors.** `address already in use` in the log: pick another `--port`. A card request for a source that has no model returns 404 and lists the sources that do.

### `moot mcp`

**Purpose.** Start the read-only MCP server on standard input and output, with the tools `get_card`, `list_precedents` and `reliability_report`. An MCP client starts it as a child process.

**Reads** models and reports. **Writes** nothing. The example sends one protocol message and reads the reply.

```bash run
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"doc","version":"0"}}}' | moot mcp | python -c "import json, sys; r = json.loads(sys.stdin.readline())['result']; print(r['serverInfo']['name'], r['protocolVersion']); print(r['instructions'])"
```

```text output
mootcourt 2025-06-18
The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.
```

**Common errors.** A client that reports the server "exited" usually ran `moot mcp` outside the project folder, or without the data root set: give it `MOOTCOURT_DATA_ROOT` and the folder with `mootcourt.toml`.
