# Command line

Every command is `moot <command>`. This page is generated from the command definitions by `scripts/gen_cli_docs.py`; run
`make docs` to refresh it. `moot <command> --help` prints the same text.

## `moot backtest`

Rolling-origin backtest at calendar quarter starts; writes the report, figures and score table.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str |  | Data source: upworthy, asos or synthetic. |
| `--origins` | str | `quarterly` | Only quarterly is supported. |
| `--challenger` | str |  | Challenger rungs: gbm, local_eb, text_lr. |
| `--seed` | int | `0` |  |
| `--second-opinion` | path |  | Records file from `moot simulators run`: adds the agent and stacked rungs. |
| `--bootstrap` | int | `500` | Bootstrap resamples (by test) for every interval. |
| `--features` | str | `both` | Ablation: text, structured or both. |
| `--bandwidth-mult` | float |  | Ablation: fix the P2 bandwidth multiplier. |
| `--lambda` | float |  | Ablation: fix the P2 weight on precedents. |
| `--kappa` | float |  | Ablation: P1 pooling strength. |
| `--prior` | str | `t` | Ablation: P1 prior family, t or normal. |
| `--p2-selection` | str |  | How P2 chooses lambda and bandwidth: loto or forward. |
| `--recency` | str |  | Time kernel for P2: select, or a half-life in days. |
| `--p2-guard` | str |  | Ablation: P2 admission guard multiplier, or off. |
| `--effect-scale` | str | `absolute` | absolute (default) or relative: the cautionary first run (Upworthy only). |
| `--drop-trigger` | str |  | Ablation: switch an abstention trigger off (support, novelty, reliability or instability); repeatable. |
| `--s-star` | str | `prelaunch` | prelaunch (default) or realized: feed the realized standard error (cautionary run). |
| `--local-k` | int | `50` | Neighbors used by the local_eb challenger. |
| `--primary-metric` | str |  | Multi-metric ledgers: the metric the decision value uses. |
| `--baselines`, `--no-baselines` | flag | `True` | Score the always_reference and always_variant baselines. |
| `--learning-curve` | str |  | Comma-separated history fractions, for example 0.1,0.25,0.5,1. |
| `--seeds` | int | `3` | Random history subsamples per fraction in the learning curve. |
| `--ledger` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |
| `--models-dir` | path |  | Default: the storage root. |
| `--verbose` | flag |  | Print one line per origin to standard error. |

## `moot benchmark`

Scale benchmark (--scale N) or the organization report card (--ledger FILE); exactly one of the two.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--scale` | int |  | Generate a synthetic ledger of this many contrasts; time the fit, a backtest and cards. |
| `--ledger` | path |  | Run the standard protocol on this ledger and write the one-page report card. |
| `--source` | str |  | With --ledger: the source to score when the ledger holds several. |
| `--bootstrap` | int | `200` | With --ledger: bootstrap resamples for the intervals. |
| `--cards` | int | `1000` | With --scale: how many cards to issue and time. |
| `--origins` | int | `2` | With --scale: how many of the last quarterly origins the small backtest scores. |
| `--scored-per-origin` | int | `2000` | With --scale: rows scored at each origin (a seeded random sample). |
| `--seed` | int | `20261103` | Random seed. |
| `--reports-dir` | path |  | Default: the storage root. |
| `--experiments-dir` | path |  | With --scale: default the storage root. |

## `moot card`

Issue a card for a proposed experiment and freeze it under the cards directory.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str |  | Data source: upworthy, asos or synthetic. |
| `--headline` | str | `` | Proposed headline (text sources; leave out for ledgers without headline text). |
| `--image-changed` | str | `false` | true or false. |
| `--impressions` | int |  | Planned exposures (units) per arm. |
| `--origin` | str |  | ISO-8601 time with offset; default now. |
| `--models-dir` | path |  | Default: the storage root. |
| `--cards-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |
| `--now` | str |  | Issue time (ISO-8601 with offset); default now. |
| `--model-id` | str |  | Model to use; default the registry champion. |
| `--cell` | str |  | Primary metric's cell (needed for metric-keyed sources). |
| `--guardrail` | str |  | Guardrail as CELL:DELTA (harm margin above zero); repeat. |
| `--headline-changed` | str | `true` | true or false. |
| `--json` | flag |  | Print the card as JSON instead of Markdown. |
| `--verbose` | flag |  | Print timings to standard error. |
| `--simulator` | str |  | Attach a response simulator (see `moot simulators list`) as a second opinion. |
| `--reference-headline` | str | `` | Reference headline passed to the simulator, if known. |
| `--sim-config` | path |  | Config file with [simulators.*] tables; default mootcourt.toml. |
| `--allow-remote` | flag |  | Allow an http simulator on a non-loopback host. |

## `moot doctor`

Check versions, data root and space, ledger, model freshness, reliability age and the service; write reports/doctor.json.

Exit code 0 healthy, 1 warnings, 2 failures.

## `moot earn-weight`

Fit the second-opinion weight; it stays 0 until a provider earns it (the default provider has no opinion).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str |  | Source whose backtest scores at the current ledger snapshot are used. |
| `--second-opinion` | path |  | Records file from `moot simulators run`. |
| `--include-contaminated` | flag |  | Also use contaminated origins; the stored weight is then marked contaminated. |
| `--ledger` | path |  | Default: the storage root. |
| `--models-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |

## `moot fit`

Fit P0, P1 and P2 at the current ledger snapshot, save the bundle and register it.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str |  | Data source: upworthy, asos or synthetic. |
| `--ledger` | path |  | Default: the storage root. |
| `--models-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |

## `moot ingest`

Build the shared ledger from the downloaded files, or import a results export. Idempotent: rows already present are unchanged.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str | `all` | upworthy, asos, synthetic or all. |
| `--raw-dir` | path |  | Where scripts/download_data.py put the files; default: the storage root. |
| `--ledger` | path |  | Default: the storage root. |
| `--synthetic`, `--no-synthetic` | flag | `True` | With --source all, also add the synthetic ledger. |
| `--n-tests` | int | `1000` | Synthetic tests. |
| `--seed` | int | `0` | Synthetic seed. |
| `--format` | str |  | Import a results export instead: see `moot ledger formats`. Needs --input. |
| `--input` | path |  | The export file (CSV, Parquet or JSON) for --format. |
| `--source-name` | str | `ledger` | Source name given to imported rows. |
| `--mapping` | path |  | TOML mapping file (columns, constants, options) for generic and template formats. |
| `--dry-run` | flag |  | Print the admission summary of an import and write nothing. |
| `--experiment-id` | str |  | Experiment id for exports that carry none. |
| `--ci-level` | float |  | Confidence level of the exported intervals when the format does not state it. |
| `--effect-scale-import` | str |  | absolute or relative, for formats that export both. |
| `--started-at` | str |  | Start time for exports without dates (ISO-8601). |
| `--ended-at` | str |  | End time for exports without dates (ISO-8601). |
| `--n-baseline` | int |  | Baseline units for exports without counts. |
| `--n-variant` | int |  | Variant units for exports without counts. |
| `--engine` | str |  | Analysis engine to read when an export holds several: frequentist or bayesian. |
| `--analysis-basis` | str |  | Jetstream tables: enrollments (default) or exposures. |
| `--min-exposure` | int | `100` | Imports: fewer units than this in an arm makes the row low_exposure. |
| `--usable-delay-days` | float | `0.0` | Imports: days after the end before a row may be used. |

## `moot init`

Create mootcourt.toml, the data root layout, a sample ledger and quick gates; print the three commands that follow.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--dir` | path | `.` | Project folder; mootcourt.toml is written here. |
| `--data-root` | path |  | Where data, models, reports and cards live; default <dir>/mootcourt-data. |
| `--cells` | str |  | Comma-separated cell names the program forecasts; default the sample ledger's metrics. |
| `--name` | str |  | Project name; default the folder name. |
| `--force` | flag |  | Overwrite an existing mootcourt.toml. |

## `moot join`

Weekly loop: append new rows, join outcomes to issued cards, type misses, rewrite reliability.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str |  |  |
| `--ledger` | path |  | Default: the storage root. |
| `--cards-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |
| `--new-rows` | path |  | Ledger parquet of newly concluded rows to append. |
| `--now` | str |  | Join time (ISO-8601 with offset); default now. |

## `moot ledger`

The vendor-neutral ledger exchange format: formats and conformance check.

### `moot ledger check`

Report schema violations, duplicate ids, impossible values, horizon violations and missing provenance. Exit code 1 on any.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `FILE` | argument | required | |

### `moot ledger formats`

List the import formats and whether the export is documented publicly or needs an editable mapping template.

## `moot mcp`

Start the read-only MCP server on stdio (get_card, list_precedents, reliability_report).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--models-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |

## `moot promote`

Promote the challenger to champion only if it beats the champion by the margin at the gate's n.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--source` | str |  |  |
| `--models-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |
| `--margin` | float | `0.02` | Required Brier skill gain over the champion. |

## `moot serve`

Start the read-only HTTP service (POST /card, GET /reliability/{source}, GET /health).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--host` | str | `127.0.0.1` | Bind address; loopback by default, no authentication is provided. |
| `--port` | int | `8000` |  |
| `--models-dir` | path |  | Default: the storage root. |
| `--cards-dir` | path |  | Default: the storage root. |
| `--reports-dir` | path |  | Default: the storage root. |

## `moot simulate`

Synthetic data and gate power. Everything here is synthetic.

### `moot simulate ledger`

Write a synthetic ledger with known truth (source synthetic).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--out` | path |  | Where to write the synthetic ledger (parquet). |
| `--seed` | int | `0` |  |
| `--n-tests` | int | `1000` |  |

### `moot simulate power`

Simulate the release gates and write reports/gates.json (synthetic data only).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--out` | path |  | Default: gates.json under the reports directory. |
| `--reps` | int | `1000` | Simulated gates per point; lower is faster and noisier. |
| `--bootstrap` | int | `500` | Bootstrap resamples per simulated gate. |
| `--seed` | int | `20261102` |  |
| `--base-rate` | float | `0.3` |  |
| `--target` | float |  | Power of the release gate; default gate.target_power in mootcourt.toml, else 0.90. |

## `moot simulators`

Response simulators: attach an outside agent as a second opinion.

### `moot simulators list`

List providers with version, knowledge cutoff and the earned weight per source.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--config` | path |  | Config file; default mootcourt.toml in the working directory. |
| `--models-dir` | path |  | Default: the storage root. |

### `moot simulators run`

Run a provider once over the rolling-origin request set and write one record per request.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--provider` | str |  | Provider name (see `moot simulators list`). |
| `--source` | str |  | Data source: upworthy, asos or synthetic. |
| `--origins` | str | `quarterly` | Only quarterly is supported. |
| `--out` | path |  | Records file to write (JSONL). |
| `--config` | path |  | Config file; default mootcourt.toml in the working directory. |
| `--allow-remote` | flag |  | Allow an http provider on a non-loopback host. |
| `--limit` | int |  | Only the first N requests (a trial run). |
| `--max-respondents` | int | `100` | Budget passed to the agent. |
| `--max-seconds` | float | `30.0` | Time cap passed to the agent and enforced by the adapters. |
| `--cache`, `--no-cache` | flag | `True` | Reuse results under the cache folder. |
| `--ledger` | path |  | Default: the storage root. |

## `moot storage`

Show where the heavy directories live, their sizes and the free space of their volumes.
