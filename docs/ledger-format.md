# Ledger exchange format

A vendor-neutral file format for the results of concluded experiments, and the importers that read vendor exports into it. It holds aggregates only: one row per variant, per metric, per experiment. No unit-level data is needed or accepted. The executable specification is `src/mootcourt/importers/exchange.py`; `moot ledger check FILE` tests a file against it.

A worked example with 360 rows is `examples/ledgers/sample.csv` (synthetic). Import it with `moot ingest --format generic --input examples/ledgers/sample.csv --source-name sample`.

## One row, one contrast

A row compares one variant with one baseline on one metric at the final read of one experiment. CSV and Parquet carry the same columns. Timestamps are ISO-8601; a value without an offset is read as UTC.

### Required columns

| column | type | meaning |
|---|---|---|
| `experiment_id` | text | the experiment; rows with the same id share a baseline and are resampled together |
| `variant_id` | text | the treatment arm; it must not contain `::` (the ledger joins variant and metric with it) |
| `metric_id` | text | the metric; with the experiment and variant it is the row key, so one experiment can carry several metrics |
| `effect` | number | treatment minus baseline, in `effect_unit` |
| `se` | number, above zero | standard error of `effect`, same unit |
| `n_baseline`, `n_variant` | whole numbers, finite and at most 2**53 | randomization units (or exposures) per arm; they scale the standard error of a future test |
| `started_at`, `ended_at` | timestamps | when the analysis window began and when the result was final |

### Optional columns

| column | meaning |
|---|---|
| `baseline_id` | the baseline arm, default `control`; equal to `variant_id` marks the row `duplicate_arm` |
| `effect_unit` | one of `absolute` (the metric's own units), `relative` (a fractional change), `standardized` (standard deviations) or `as_exported` (an export that does not state its unit, kept as exported), default `absolute`. Any other value is an error. Rows pooled in one cell must share a unit: the check names the rows that differ, and an import is refused when a cell would gain a second unit. `as_exported` is compared together with the row's `source_system`, because two vendors' unstated scales need not agree: an `as_exported` cell that gains rows from a second vendor is refused like any other unit clash. `moot ledger check` on a ledger Parquet file applies the same rules per source and cell, reading the unit and the vendor from the row's features; a ledger built before the rule existed is reported, and it is rebuilt from the exchange files rather than edited |
| `cell` | the grouping for partial pooling, default the metric id |
| `status` | an admission status (below); computed when absent. A stated exclusion is kept; a stated `admitted` is checked against the derived rules and cannot lift an exclusion |
| `usable_after` | the first instant a forecaster may use the row; default `ended_at` plus `--usable-delay-days` |
| `decision`, `decision_threshold` | what the team decided and the rule behind it. Vendors define a decision differently (a shipped arm, a significance flag, a probability crossing a threshold), so the rule travels with the label |
| `srm_flag` | true when a sample ratio mismatch check failed; the row becomes `imbalance_flag` |
| `headline` and `feature_*` | pre-launch features, kept for forecasting (the `feature_` prefix is dropped) |

### Provenance columns

| column | meaning |
|---|---|
| `source_system` | where the numbers came from, for example the platform and the export |
| `variance_method` | how `se` was obtained: the estimator, the interval level, any assumption |
| `cuped`, `sequential`, `winsorized` | true when variance reduction, a sequential correction or outlier clipping changed the estimate or interval |
| `multiple_comparison` | the correction applied, if any |
| `numerator`, `denominator` | for a ratio metric, what the two parts are |

`moot ledger check` reports a missing `source_system` or `variance_method` as a violation: an interval cannot be interpreted without knowing how it was made.

## Metrics and the variance estimator

`effect` and `se` must be on one scale. For a difference in means, `se` is the usual two-sample standard error. For a ratio metric whose unit of analysis differs from the unit of randomization (revenue per session, with users randomized), the delta method gives the variance of each arm's ratio `R = mean_num / mean_den`:

`Var(R) = ( var_num / mean_den^2  -  2 mean_num cov / mean_den^3  +  mean_num^2 var_den / mean_den^4 ) / n`

with per-unit variances and covariance, and `se = sqrt(Var(R_variant) + Var(R_baseline))`. `mootcourt.importers.delta_method_ratio_se` computes it; it is a library helper that no reader calls, for preparing the `effect` and `se` columns yourself. A vendor that already reports a standard error or an interval for a ratio metric has done this; import its number and say so in `variance_method`. When only an interval is available, `se` is taken from a symmetric normal interval as `(upper - lower) / (2 z)`, from a half-width as `half / z`, or from a two-sided p-value as `|effect| / z`, where `z` is the normal quantile of the stated level. Sequential intervals are wider than fixed-horizon ones, so a `se` derived from them is inflated; set `sequential` to true.

## Admission statuses

Admission is a status, never a filter. Importers set one of: `admitted`; `low_exposure` (fewer than `--min-exposure` units in an arm, default 100, or a missing standard error, recorded as `exclusion_detail` `missing_variance`); `imbalance_flag` (`srm_flag`); `duplicate_arm` (variant equals baseline). A given `status` is kept. Only `admitted` rows with `usable_after` at or before a forecast's origin are used.

## Importing

```
moot ingest --format FORMAT --input FILE --source-name NAME [--mapping MAP.toml] [--dry-run]
moot ledger formats
moot ledger check FILE
```

`--dry-run` prints an admission summary and writes nothing. Errors name the data row (counting from 1) and the column, for example `error: row 5, column se: must be greater than zero`, and `moot ingest` exits 1. Warnings are printed and do not stop the import. `moot ledger check` exits 1 on any error or warning and accepts an exchange file or a ledger Parquet file.

### Formats

Where the vendor documents its export, the mapping follows the documentation (cited in the importer's docstring); where the documentation is silent on something, the importer takes an option with a stated default and records the assumption in `variance_method`. Confirm each assumption against your own export before you rely on the intervals.

| format | export | status | documentation | assumptions to confirm |
|---|---|---|---|---|
| `generic` | a file in the exchange columns, or any file through `--mapping` | specified here | this document, template `examples/mappings/generic.toml` | none |
| `statsig` | Warehouse Native results view `statsig_daily_results`, as a CSV or Parquet extract | documented mapping | https://docs.statsig.com/experiments/interpreting-results/access-whn, decisions at https://docs.statsig.com/console-api/experiments | the page does not say whether `absoluteDeltaCI` is a half-width or a bound, or its level: the importer takes a half-width at `--ci-level` (default 0.95) |
| `statsig` with `--mapping` | the console CSV download | not documented publicly (the export page lists no fields), so a template to edit | `examples/mappings/statsig-csv.toml` | all of it |
| `optimizely` | the CSV export of an experiment, 20 columns | documented mapping | https://docs.optimizely.com/web-experimentation/docs/D9uo-reference-for-columns-in-csv-export-files-for-campaigns-and-experiments | the unit of `Improvement Value from Baseline`, the interval scale and its level (the importer assumes symmetric bounds at 0.90); the export has no experiment id, pass `--experiment-id` |
| `harness` | the "Share results" download, CSV or JSON | documented mapping | https://developer.harness.io/feature-management-experimentation/use-fme/experimentation/experiment-results/sharing-experiment-results/index | the interval is on the scale of `Impact`; the level is one minus the exported significance threshold, and when the export has none the row says that 0.95 was assumed; CSV needs `--experiment-id` |
| `growthbook` | experiment results API, or bulk-results snapshots, saved as JSON | documented mapping | https://docs.growthbook.io/api/experiments/operation/getExperimentResults | `percentChange` is read as a relative change with `effectStandardError` as its standard error; the latest snapshot is the final read; a bulk snapshot has no start date, so pass `--started-at`; without `effectStandardError` the standard error comes from `ciLow` and `ciHigh` as symmetric bounds at `--ci-level` (default 0.95, written into the row); `--engine` picks frequentist or bayesian |
| `jetstream` | Mozilla Jetstream statistics tables exported to CSV or Parquet | documented mapping | https://docs.telemetry.mozilla.org/datasets/jetstream | the table has no experiment slug, dates or client counts: pass `--experiment-id`, `--started-at`, `--ended-at`, `--n-baseline`, `--n-variant`; a table with both analysis bases keeps `--analysis-basis` (default `enrollments`, or `exposures`) |
| `eppo` | results export | not documented publicly (the documentation defers the schema to its API reference), so a template to edit | `examples/mappings/eppo.toml` | all of it |

A mapping file has three tables: `[columns]` maps an exchange column (or `ci_low`, `ci_high`, `ci_halfwidth`, `p_value`, from which `se` is derived) to a column of your file, `[constants]` fills a column with one value, and `[options]` holds `ci_level` and a `scale` factor. A standard error derived from an interval or a p-value is recorded in `variance_method` with its level. The templates carry `EDIT` markers where your column names go.

## What the importers do not do

They do not read unit-level data, call a vendor API or hold credentials. Save an API response to a file, or extract a warehouse view to CSV or Parquet, and point the importer at the file. They do not decide what a metric means: a metric id is a label, and two platforms' metrics with the same name are pooled only if you give them the same `cell`.
