# Troubleshooting

Start with `moot doctor`. It names most of what can be wrong, and its exit code (0 healthy, 1 warnings, 2 failures) tells a scheduled job whether to stop. This page goes through what it reports and the other things that surprise people, in the order they tend to come up.

## Doctor reports something

| Line | Meaning | Fix |
|---|---|---|
| `FAIL python` or `FAIL package ...` | A version is below the minimum, or a package is missing. | Reinstall in an environment with Python 3.11 or newer: `pip install -e .` |
| `FAIL data root: ... does not exist` | The folder named by `MOOTCOURT_DATA_ROOT` or `[storage] data_root` is not there. | Create it, or run `moot init`, or correct the path. |
| `WARN data root: ... free space ... (under 10 GB ...)` | Little room for reports, models and caches. | Point the data root at a larger volume. |
| `WARN ledger: no ledger at ...` | Nothing has been imported. | `moot ingest`, see [tutorial 2](tutorials/02-your-own-archive.md). |
| `FAIL ledger` with violations | The ledger does not conform to the schema (duplicate row ids, a standard error of zero, a row used before it was final, mixed units in a cell). | Run `moot ledger check` on the ledger for the rows, fix the export and import again. |
| `WARN models: no registry` | No model has been fitted. | `moot fit --source NAME`. |
| `WARN model ...: champion ... was fit on snapshot ..., which no longer matches the ledger` | The ledger grew after the last fit. | `moot fit`, then `moot backtest`. |
| `WARN reliability ...: ... entries are stale` | The recent record of a cell is older than 14 days, or absent. Cards for those cells abstain. | Join new results with `moot join`, or run `moot backtest` to seed the record. For a static archive this warning is correct. See [a card abstains](#a-card-abstains). |
| `WARN cells: cells with fewer than 20 admitted rows: ...` | A configured cell has too little history to back-test. | Import more history, or remove the cell from `[cells]`. |
| `FAIL service ...: ... is not reachable` | `[service] url` is set and nothing answers. Only loopback addresses are contacted. | Start `moot serve`, or remove the key. |

## The data root

Everything heavy lives under one folder, the **data root**. These are the questions that come up.

- **Where is it?** `moot storage` prints the resolved folders. The order of precedence is the environment variable `MOOTCOURT_DATA_ROOT`, then `data_root` under `[storage]` in `mootcourt.toml` in the working directory, then folders inside the working directory.
- **Commands cannot find my ledger or models.** You are probably in another folder, so the other `mootcourt.toml` is read, or the environment variable is set in one shell and not in the other. Run `moot storage` in the shell where it fails. A process manager that starts `moot serve` needs the variable in its own environment.
- **I set the variable and the file says something else.** The variable wins. That is by design, so that one command can be pointed elsewhere without editing the file.
- **A command wrote into the repository.** With no data root set, the folders are created in the working directory. Set a data root, and keep large files out of the repository.

## exFAT volumes and `._` files

External drives are often formatted as exFAT. Moot Court works on them: it needs no symlinks, no hard links and no permission changes, and a permission change that the volume refuses is skipped quietly. On macOS an exFAT volume gets a binary companion file called `._NAME` next to many files. The package ignores every dot file when it lists a folder, so these do not confuse it. If a script of your own globs a folder under the data root, skip names that start with a dot. Do not copy a data root between volumes with a tool that follows symlinks into it, and do not put a symlink inside it.

## A card abstains

An abstained card is the intended answer when the ledger has no standing to give an opinion. It lists every reason that fired. There are four triggers.

| Reason on the card | Meaning | What to do |
|---|---|---|
| `support` | Fewer than 30 admitted rows of this cell are visible at the card's origin. | Import more history, or check that the cell name is right (see below). |
| `novelty` | The proposal is unlike every precedent in the cell. | Nothing is wrong: the ledger has nothing to say about a change this unusual. Run the test and add it to the ledger. |
| `reliability` | The cell's reliability report is missing, more than 14 days old, or marks the cell drifted. | Run `moot backtest` once to seed it, and `moot join` weekly to keep it current. For a static archive, pass `--now` at the end of its history. A drifted cell clears at the first join that is not below threshold. |
| `instability` | Dismissing a few precedents would move the forecast across the action threshold. | The evidence is thin or split. Report the card as undecided, and run the test. |

A backtest reports the abstention rate and the share by trigger, so you know how often to expect each.

**The card says `Cell: headline_only` and `no admitted rows in cell headline_only`.** The ledger's cells are metrics, and you did not name one. Pass `--cell NAME` (the names are in `[cells]` and in the ingest summary). Today the command does not stop and ask; it forecasts a cell that the ledger does not have and abstains for lack of support.

## Ids differ between machines

A card carries three ids: the card id, the model id and a feature hash. They are digests of content that includes the fitted parameters. The same fit on another operating system or linear algebra build can differ in the last bits of its parameters (about 1e-15) and so produce a different model id and feature hash, while every score agrees to about eleven digits. Two consequences:

- Compare cards, models and snapshots **by their stored ids**, never by refitting and recomputing. A card file stores the ids of the snapshot and the model it used.
- Do not expect the model id in a tutorial to match yours on another platform. Compare the scores, which are the substance. The snapshot id has a date prefix and a digest of the ledger rows; the digest part is a function of the rows alone.

## Rows are missing from the ledger, or not used

Admission is a status, never a filter, so a row you expected is kept with a reason and can be listed. Three rules explain most cases.

- **Admission statuses.** `low_exposure`: an arm has fewer than 100 units (`--min-exposure`) or the standard error is missing. `imbalance_flag`: your export flagged a sample ratio mismatch. `duplicate_arm`: the variant equals the baseline. Only `admitted` rows teach a model. A status you give in the file is kept, and a stated `admitted` cannot lift an exclusion.
- **The horizon, `usable_after`.** A row is visible to a forecast only when its `usable_after` is not later than the forecast's origin. By default `usable_after` is the end of the analysis window plus `--usable-delay-days`. A backtest therefore scores a row only at origins after it became usable. For the Upworthy archive, which does not record when a test was read, a test is treated as final seven days after its latest arm was created, for every contrast of that test: that is a modeling choice, and it moves rows to later origins.
- **No fit at the first origins.** A model is fitted at an origin only when at least 20 admitted rows are visible. Earlier rows are used as history but never scored: the backtest header lists them as "admitted but never scored (before the first fit)". On the sample ledger that is 30 of 360 rows.

If the numbers still do not add up, compare the ingest summary, the "Header" of the backtest report and the status counts in `moot ledger check`.

## Rebuilding a ledger after an upgrade

The ledger is a Parquet file with a schema version. A new release can tighten a rule (for example, that the rows of one cell share one effect unit). A ledger built before that is reported by `moot ledger check` and `moot doctor`, and the fix is to rebuild it from the exchange files, not to edit it.

1. Keep your exchange files or exports. They are the source of truth, and the ledger is derived from them.
2. Move the old ledger folder aside: `mv mootcourt-data/data/ledger mootcourt-data/data/ledger-old`.
3. Import again with the same `moot ingest` command or commands you used before.
4. Refit and back-test: `moot fit --source NAME`, `moot backtest --source NAME`. Cards issued earlier are frozen files under `cards/` and stay valid records. They name the snapshot and model they used.

An unfamiliar error that mentions `schema_version` after an upgrade means the same thing.

## Backtest stops with `KeyError: 'cell'`

A ledger with fewer than about 20 admitted rows before its first quarterly origin cannot be back-tested. Today the command stops with a Python traceback that ends in `KeyError: 'cell'` instead of a sentence. The cure is more history: a few dozen experiments per metric make a first backtest possible, and the gates in its report say how many are needed for a comparison to mean anything.

## The service and the MCP server

- **`address already in use` in the service log.** Another process has the port. Choose another with `--port`.
- **HTTP 400 on every request.** On a loopback bind the service accepts only loopback names in the `Host` header (a defense against DNS rebinding). Call it as `127.0.0.1` or `localhost`.
- **HTTP 404 `no model is registered for source ...`.** The source has no fitted model, or you fitted after starting the service, which reads models at start. Fit and restart.
- **HTTP 422.** A required field is missing: `source` and `impressions`.
- **A card from the service abstains although the CLI card did not.** The service issues cards as of its machine's clock, and a static ledger's reliability report is old. Pass an `origin` in the request, or join fresh results.
- **An MCP client says `Error executing tool get_card`.** The server refused the request, and the reason is in the server's log, not in the client's message. The usual cause is an `origin` earlier than the date the model was fitted on, because the parameters were fitted on rows that origin should not see.
- **The client says the server exited.** `moot mcp` must run from the project folder, or with `MOOTCOURT_DATA_ROOT` set, to find its models.

## My numbers differ from the published ones

For the two public archives, the backtest report matches the published one to every printed digit, apart from timing lines, when the data, the seed (`--seed 0` is the default), the bootstrap count (500) and the gates file are the same. If they differ, check that the downloaded files verify (`python scripts/download_data.py --verify-only`), the number of admitted rows, and the gates file: the first backtest simulates one if none exists, and the simulation is seeded, so it reproduces. A model id that differs on another platform is not a failure; see [ids differ between machines](#ids-differ-between-machines).
