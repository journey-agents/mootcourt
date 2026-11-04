# Troubleshooting

Start with `moot doctor`. It names most of what can be wrong, and its exit code (0 healthy, 1 warnings, 2 failures) tells a scheduled job whether to stop. This page goes through what it reports and the other things that surprise people, in the order they tend to come up.

## Doctor reports something

| Line | Meaning | Fix |
|---|---|---|
| `FAIL python` or `FAIL package ...` | A version is below the minimum, or a package is missing. | Reinstall in an environment with Python 3.11 or newer: `pip install -e .` |
| `FAIL data root: ... does not exist` | The folder named by `MOOTCOURT_DATA_ROOT` or `[storage] data_root` is not there. | Create it, or run `moot init`, or correct the path. |
| `WARN data root: ... free space ... (under 10 GB ...)` | Little room for reports, models and caches. | Point the data root at a larger volume. |
| `WARN ledger: no ledger at ...` | Nothing has been imported. | `moot ingest`, see [tutorial 2](tutorials/02-your-own-archive.md). |
| `FAIL environment: N sidecar files ...` | The Python environment sits on an exFAT volume and holds macOS `._` sidecar files; `moot backtest` would fail on them. Make the environment on the internal disk, see [working from a clone on an exFAT volume](#working-from-a-clone-on-an-exfat-volume). A `WARN environment` says the environment is on an external volume. |
| `WARN cards SOURCE: ... post-hoc cards ...` | Cards of this source were issued after their test started (or after its result). They are recorded and never scored, so they cannot raise the record; a reissue for a row that already has a scored card is counted here too. Issue cards before the test starts. The line is absent until outcome records exist. |
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

External drives are often formatted as exFAT. A data root works on them (the repository and its environment do not, see the next section): it needs no symlinks, no hard links and no permission changes, and a permission change that the volume refuses is skipped quietly. On macOS an exFAT volume gets a binary companion file called `._NAME` next to many files. The package ignores every dot file when it lists a folder, so these do not confuse it. If a script of your own globs a folder under the data root, skip names that start with a dot. Do not copy a data root between volumes with a tool that follows symlinks into it, and do not put a symlink inside it.

## Working from a clone on an exFAT volume

Keep the clone and its environment on the internal disk. If the repository or its environment sits on an exFAT drive, macOS writes a `._NAME` sidecar file next to every file it creates there (19,356 of them under a fresh `.venv`), and several things break. The data root can stay on the drive; see the last point for what that costs.

- **`moot backtest` fails after a `pip install -e .` that succeeded.** The install, `moot init`, `moot ingest` and `moot fit` all work, then `moot backtest` exits 2 with this text (the path is that of your environment):

  ```text
  Cannot decode configuration file PosixPath('.../.venv/lib/python3.11/site-packages/matplotlib/mpl-data/stylelib/.__classic_test_patch.mplstyle') as utf-8. error: 'utf-8' codec can't decode byte 0xb0 in position 37
  ```

  The plotting library globs the sidecar of one of its own style files, and the message names a style file and not the drive. `moot backtest` now stops on this with one line that says what it is ("the Python environment holds macOS `._` sidecar files ...") and `moot doctor` reports it on its second line: `FAIL environment: N sidecar files (`._name`) under ...` (and `WARN environment: ... lives on an external volume` before any sidecar appears). Cure: make the environment on the internal disk and install into that, then run again.

  ```bash
  python3 -m venv ~/.venvs/mootcourt
  source ~/.venvs/mootcourt/bin/activate
  pip install -e /path/to/clone
  ```

  Delete the damaged `.venv` inside the clone, and the sidecars (below).

- **`uv sync` fails with a RECORD mismatch.** In a clone on the drive, `uv sync --all-extras` exits 2 with the lines below (the first warning appears too; the paths are those of your clone), after it has already removed two packages from an existing `.venv`:

  ```text
  warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
           If the cache and target directories are on different filesystems, hardlinking may not be supported.
           If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
  error: Failed to install: ruff-0.17.3-py3-none-macosx_11_0_arm64.whl (ruff==0.17.3)
    Caused by: RECORD file doesn't match wheel contents: Could not find entry for ruff-0.17.3.data/scripts/._ruff (/Volumes/Crucial X10/mootcourt-data/round01-r4-clone/.venv/lib/python3.13/site-packages/ruff-0.17.3.data/scripts/._ruff)
  ```

  An older uv fails with `failed to copy ... ._ttx.1` instead; the cause is the same, a `._` file in a wheel. Cure: point uv at an environment on the internal disk, and leave the clone and the data root where they are.

  ```bash
  export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/mootcourt"
  uv sync --all-extras
  uv run pytest -q
  ```

  The environment takes a few hundred megabytes of the internal disk. Keep the variable set in every shell that runs `uv run` in that clone.  `--all-extras` also installs the packages that build the manual.

- **Sidecar files fail tests.** Several tests read the docs, reports and source folders as text, and stop with `UnicodeDecodeError: ... byte 0xb0` when they reach a sidecar, so a fresh clone or copy shows about twenty failures that have nothing to do with the code. Delete the sidecar files before you run the tests, and again after anything that copies files onto the drive. The command reaches `.git` as well:

  ```bash
  find . -name '._*' -type f -delete
  ```

- **Two harmless messages.** `git status` in a fresh clone prints `error: non-monotonic index .git/objects/pack/._pack-....idx` twice, and `pip install -e .` prints about ten lines of `WARNING: Ignoring invalid distribution -httpx2 ...` (pip reads each `._NAME` sidecar as a package named `-NAME`). The `find` command above cures both.
- **A data root on the drive is slower.** Sample-sized commands take several times longer there than on the internal disk, because they write many small files: one measurement gave `moot init` 90 s and `moot backtest` 97 s on exFAT against 24 s and 12 s on the internal disk, with the backtest printing 11 s for its own run. `moot init` and `moot backtest` print progress lines to standard error after 10 seconds (`--progress-after`), and the backtest's last line reports "the whole run N s". Keep the data root on the drive for large runs, where the space matters more than the small-file cost.

## A card abstains

An abstained card is the intended answer when the ledger has no standing to give an opinion. It lists every reason that fired. There are four triggers.

| Reason on the card | Meaning | What to do |
|---|---|---|
| `support` | Fewer than 30 admitted rows of this cell are visible at the card's origin. | Import more history, or check that the cell name is right (see below). |
| `novelty` | The proposal is unlike every precedent in the cell. | Nothing is wrong: the ledger has nothing to say about a change this unusual. Run the test and add it to the ledger. |
| `reliability` | The cell's reliability report is missing, more than 14 days older than the card's issue time, or marks the cell drifted. | Run `moot backtest` once to seed it, and `moot join` weekly to keep it current; the join scores abstained cards too, so a stale cell recovers as its outcomes arrive. For a static archive, pass `--now` at the end of its history (the service has no `--now`: it uses its own clock). A drifted cell clears at the first join that is not below threshold. |
| `instability` | Dismissing a few precedents would move the forecast across the action threshold. | The evidence is thin or split. Report the card as undecided, and run the test. |

A backtest reports the abstention rate and the share by trigger, so you know how often to expect each.

**`moot card` says `this ledger's cells are ...; the card needs --cell`.** The ledger's cells are metrics, and you did not name one. The command stops with one line that lists the cells; pass `--cell NAME` with one of them (the names are also in `[cells]` and in the ingest summary). The check is in the card builder, so `POST /card` and the MCP tool apply it too; there the cell is the `cell` field.

## Ids differ between machines

A card carries three ids: the card id, the model id and a feature hash. They are digests of content that includes the fitted parameters, and the model id also covers the snapshot id, whose first part is the date of the import, so the same fit on another day has another model id. The same fit on another operating system or linear algebra build can differ in the last bits of its parameters (about 1e-15) and so produce a different model id and feature hash, while every score agrees to about eleven digits. Two consequences:

- Compare cards, models and snapshots **by their stored ids**, never by refitting and recomputing. A card file stores the ids of the snapshot and the model it used.
- Do not expect the model id in a tutorial to match yours on another day or platform. Compare the scores, which are the substance. The snapshot id has a date prefix and a digest of the ledger rows; the digest part is a function of the rows alone.

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

## Backtest says the ledger is too small

A backtest scores a quarter only when at least 20 admitted rows are usable before it starts. A ledger with fewer admitted rows than that cannot be back-tested, and `moot backtest` ends in one line that names the minimum:

```text
Invalid value: the ledger is too small to backtest: 18 admitted rows, and a quarter is scored only when at least 20 admitted rows are usable before it starts
```

Earlier releases ended in a Python traceback that finished with `KeyError: 'cell'` instead; if you see that, you are running an old version. The cure is more history: a few dozen experiments per metric make a first backtest possible, and the gates in its report say how many are needed for a comparison to mean anything. A model can still be fitted, and a card issued, on such a ledger; only the backtest, and so the reliability record that it seeds, is missing.

## The service and the MCP server

- **`address already in use` in the service log.** Another process has the port. Choose another with `--port`.
- **HTTP 400 on every request.** On a loopback bind the service accepts only loopback names in the `Host` header (a defense against DNS rebinding). Call it as `127.0.0.1` or `localhost`.
- **HTTP 404 `no model is registered for source ...`.** The source has no fitted model, or you fitted after starting the service, which reads models at start. Fit and restart.
- **HTTP 422.** A required field is missing: `source` and `impressions`.
- **A card from the service abstains although the CLI card did not.** The card abstains for `reliability` when the cell's report is more than 14 days older than the card's issue time, or is dated after it. The command line issues cards as of `--now` (the machine's clock by default). The service always uses its own clock, and a request has no `now` field. An `origin` in the request does not help: it chooses which ledger rows the forecaster may see and leaves the clock alone. A static ledger such as the sample has an old report, so the service's card abstains. For a live ledger, run `moot join` on fresh results, which refreshes the report (abstained cards are scored by the join too, so a stale cell collects the evidence to recover). To see a full card from a static archive, use `moot card --now` at the end of its history.
- **An MCP client says the tool failed.** The server refuses a bad request as a tool error, and the message is one line that names the cause. The usual cause is an `origin` earlier than the date the model was fitted on, because the parameters were fitted on rows that origin should not see.
- **The client says the server exited.** `moot mcp` must run from the project folder, or with `MOOTCOURT_DATA_ROOT` set, to find its models.

## My numbers differ from the published ones

For the two public archives, the backtest report matches the published one to every printed digit, apart from timing lines, when the data, the seed (`--seed 0` is the default), the bootstrap count (500) and the gates file are the same. If they differ, check that the downloaded files verify (`python scripts/download_data.py --verify-only`), the number of admitted rows, and the gates file: the first backtest simulates one if none exists, and the simulation is seeded, so it reproduces. A model id that differs on another platform is not a failure; see [ids differ between machines](#ids-differ-between-machines).
