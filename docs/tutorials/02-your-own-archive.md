# Tutorial 2: your own experiment archive, end to end

**You will:** turn an export of your concluded A/B tests into a ledger, check it, fit the forecaster, back-test it, read the report card and issue a card.

**Prerequisites:** [tutorial 1](01-first-card.md) done, or at least `moot` installed. An export of concluded tests from your experimentation platform or warehouse. If you have none yet, this tutorial makes a stand-in export in step 1, so that you can follow every command.

**Time:** about 20 minutes with a stand-in export. Preparing a real export is the part that takes the time, and it depends on your platform. The commands themselves run in under a minute on a few hundred experiments, and in minutes on tens of thousands.

## What you need from your archive

The ledger holds **aggregates only**: no user-level data, no event streams. For every concluded experiment, for every variant and every metric you care about, you need one row (the package calls it a **contrast**: one variant against its baseline on one metric) with:

| What | Why |
|---|---|
| the experiment, variant and metric names | the row's identity; rows of one experiment share a baseline |
| the effect (treatment minus baseline) and its standard error | what the experiment found and how noisy it was |
| the units in each arm | the forecaster scales the noise of a future test with them |
| the start and the end of the analysis window | the end is when the result became final; no forecast may use the row before that |

A standard error is not always exported. An interval, a half-width or a p-value is enough: the importer recovers the standard error from it and writes how it did so into the row. You do not need a baseline name (default `control`), a cell (default the metric) or any headline text.

**How many experiments?** The gates in the backtest report say it. As a rule of thumb, a few dozen experiments per metric make a card possible, and somewhere between 75 and 400 scored experiments in total are needed before a difference in skill between two forecasters can be told from zero, fewer when your experiments often end significant and positive and more when they rarely do (`moot simulate gate-power` sizes the gate at the rate of your archive). With fewer, you still get cards and reports, and the reports say "undecidable at this n" instead of a verdict.

### If the archive lives in a warehouse

One query gives every metric, one row per variant per metric per experiment. For a difference in means the standard error is the two-sample one:

```sql
SELECT e.experiment_id,
       v.arm                                       AS variant_id,
       'control'                                   AS baseline_id,
       v.metric_id,
       v.mean_value - c.mean_value                 AS effect,
       SQRT(v.var_value / v.n + c.var_value / c.n) AS se,
       c.n                                         AS n_baseline,
       v.n                                         AS n_variant,
       e.analysis_start                            AS started_at,
       e.analysis_end                              AS ended_at
FROM   experiments e
JOIN   experiment_results v ON v.experiment_id = e.experiment_id AND v.arm <> 'control'
JOIN   experiment_results c ON c.experiment_id = e.experiment_id AND c.metric_id = v.metric_id AND c.arm = 'control'
WHERE  e.status = 'concluded'
```

The table and column names are placeholders for yours. The query returns one row per variant per metric per experiment.

For a ratio metric whose unit differs from the unit of randomization (revenue per session with users randomized), use the delta method or import the standard error your platform already reports. [Ledger format](../ledger-format.md) has the formula and every column.

### If you have a platform export

Run `moot ledger formats` to list the exports that have an importer. A label "documented mapping" means that `--format NAME` reads that platform's export as the platform documents it, and you run `moot ingest --format NAME --input FILE --source-name mine`. A label "mapping template to edit" means the platform does not document its export: copy the template from `examples/mappings/` in the repository, edit the column names and pass it with `--mapping`. For an export with no importer at all, write a mapping file as in step 2.

## 1. A stand-in export

Skip this step if you have a real export. The script needs pandas, which is installed with `moot`. `moot init` takes a project name (`--name`, shown by `moot doctor`) and the cells you forecast (`--cells`, checked by `moot doctor`). The sample ledger it writes is then turned into a file that looks like a platform export: other column names, effects in percent instead of fractions, and a 95 percent interval instead of a standard error.

```bash run
mkdir moot-mine && cd moot-mine
moot init --name mine --cells checkout_conversion,pages_per_session,revenue_per_user > /dev/null
python - <<'PY'
import pandas as pd

d = pd.read_csv("mootcourt-data/data/sample-ledger.csv")
z = 1.96
export = pd.DataFrame({
    "experiment": d.experiment_id, "variant": d.variant_id, "control": d.baseline_id, "metric": d.metric_id,
    "delta": d.effect * 100, "delta_low": (d.effect - z * d.se) * 100, "delta_high": (d.effect + z * d.se) * 100,
    "control_units": d.n_baseline, "variant_units": d.n_variant, "start": d.started_at, "end": d.ended_at,
})
export.to_csv("my-export.csv", index=False)
PY
head -3 my-export.csv
```

```text output
experiment,variant,control,metric,delta,delta_low,delta_high,control_units,variant_units,start,end
exp-001,treatment,control,checkout_conversion,1.6528999999999998,-0.08659999999999987,3.3923999999999994,57135,57135,2023-01-09T00:00:00Z,2023-01-23T00:00:00Z
exp-001,treatment,control,pages_per_session,-2.0502,-3.209736,-0.8906639999999999,57135,57135,2023-01-09T00:00:00Z,2023-01-23T00:00:00Z
```

## 2. Write a mapping

A mapping file tells the importer which of your columns is which. It has three tables. `[columns]` maps an exchange column name (left) to a column of your file (right). `ci_low` and `ci_high` stand for interval bounds from which the standard error is derived. `[constants]` fills a column with one value for every row, and `[options]` holds the interval level and a scale factor.

```bash run
cat > mapping.toml <<'EOF'
[columns]
experiment_id = "experiment"
variant_id = "variant"
baseline_id = "control"
metric_id = "metric"
effect = "delta"
ci_low = "delta_low"
ci_high = "delta_high"
n_baseline = "control_units"
n_variant = "variant_units"
started_at = "start"
ended_at = "end"

[constants]
source_system = "my_platform_export"
variance_method = "95 percent interval bounds, normal approximation"
effect_unit = "relative"

[options]
ci_level = 0.95    # the level of the exported interval
scale = 0.01       # the export is in percent; multiply effect and standard error by 0.01
EOF
```

Three decisions in this file matter, and each is a place where an archive goes wrong:

- **The interval level and shape.** If your platform exports a 90 percent interval, say `ci_level = 0.90`. If it exports a sequential or Bayesian interval, the derived standard error is not a fixed-horizon one; say so in `variance_method`.
- **The unit.** `effect_unit` is one of `absolute`, `relative`, `standardized` or `as_exported`. All rows of one cell must share a unit, and the importer refuses to mix them. Do not pool a percent lift from one platform with an absolute difference from another.
- **The scale.** The forecaster's numbers are in the units of your effects. After the import, a value of `0.0165` for a relative lift means 1.65 percent.

`variance_method` and `source_system` are not decoration: a standard error cannot be interpreted without knowing how it was made, and `moot ledger check` flags a ledger that lacks them.

## 3. Preview the import

`--dry-run` shows what would be admitted and writes nothing. It takes a second.

```bash run
moot ingest --format generic --input my-export.csv --mapping mapping.toml --source-name mine --dry-run
```

```text output
360 rows from 120 experiments
  admitted: 360
admitted by cell: checkout_conversion 120, pages_per_session 120, revenue_per_user 120
final reads from 2023-01-23 to 2025-12-29
dry run: nothing written
```

What to look at: the row count (does it equal experiments times variants times metrics?), the **admitted** line, and the dates. A row is not admitted when an arm has fewer than 100 units (`--min-exposure`), when a standard error is missing, when the baseline equals the variant, or when your export flags a sample ratio mismatch. Excluded rows are kept and listed by reason, so a large number of exclusions tells you something about the export, not about the forecaster. The date range shows the history the backtest will replay.

If your platform makes results available only some days after an experiment ends, add `--usable-delay-days N`. A row is then usable for a forecast N days after its end, and never before.

## 4. Import it

```bash run
moot ingest --format generic --input my-export.csv --mapping mapping.toml --source-name mine
```

```text output
360 rows from 120 experiments
  admitted: 360
admitted by cell: checkout_conversion 120, pages_per_session 120, revenue_per_user 120
final reads from 2023-01-23 to 2025-12-29
snapshot 20261104-4a80e5b241d7 for mine
ledger ~/moot-mine/mootcourt-data/data/ledger/ledger.parquet: 360 rows
```

The ledger gained 360 rows and a snapshot was written. Running the same command again leaves the ledger at 360 rows and the snapshot unchanged: an import never duplicates a row. You can append later batches the same way.

## 5. Check the ledger

```bash run
moot ledger check mootcourt-data/data/ledger/ledger.parquet
```

```text output
ok: the file conforms to the ledger exchange format
```

This checks the ledger against the format: columns, types, duplicate row ids, impossible values (a standard error of zero or below), horizon violations (a row used before it was final) and missing provenance. It exits 1 on any error or warning and names the row and the column. It also accepts a file that already uses the exchange column names (one you wrote by hand), so you can check it before importing. A platform export that still needs a mapping, such as `my-export.csv` here, fails that check until it is imported through its mapping, which is why this step checks the ledger after the import.

## 6. Fit and back-test

```bash run
moot fit --source mine
moot backtest --source mine
```

```text output
fitted model adf46433a35f at snapshot 20261104-4a80e5b241d7 in 1.7 s; it is the champion for mine
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
gates read from ~/moot-mine/mootcourt-data/reports/gates.json: {"base_rate": 0.3, "by_target": {"0.80": {"n_200": 50, "n_400": 100}, "0.90": {"n_200": 75, "n_400": 150}}, "decision_target": 0.9, "interval": {"by": "test", "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive of that rate (docs/method.md call 170)", "icc": 0.13, "level": 0.9, "rows_per_test": 3.5}, "n_200": 75, "n_400": 150}
gate sizes by base rate (tests): 0.30: n_200 75, n_400 150
filled the backtest summary of model adf46433a35f
scored 330 rows over 11 origins in 4.2 s (report writing 5.0 s)
wrote ~/moot-mine/mootcourt-data/reports/backtest-mine-20261104-4a80e5b241d7.md
wrote ~/moot-mine/mootcourt-data/reports/backtest-mine-20261104-4a80e5b241d7.json
wrote ~/moot-mine/mootcourt-data/reports/scores-mine-20261104-4a80e5b241d7.parquet
```

Time: about ten seconds here. It grows roughly with the number of rows times the number of origins; a ledger of a million contrasts is measured in [Scale](../scale.md).

The gates came from `reports/gates.json`, which `moot init` wrote with a quick simulation at one base rate (0.3), in tests; the backtest prints the sizes after the gates line. Run `moot simulate gate-power --base-rate R`, with `R` the share of your experiments that end significant and positive (the report card's Ledger section gives it), to size the gates by experiment at your own rate; it takes a few minutes, and the next backtest reads the result.

## 7. Read the report card

The backtest report is long. For a first read, use the one-page report card instead:

```bash run
moot benchmark --ledger mootcourt-data/data/ledger/ledger.parquet
```

```text output
scoring 360 contrasts of source mine
wrote ~/moot-mine/mootcourt-data/reports/benchmark/ledger-20261104-4a80e5b241d7.md
wrote ~/moot-mine/mootcourt-data/reports/benchmark/ledger-20261104-4a80e5b241d7.json
```

It writes `reports/benchmark/ledger-<snapshot>.md`. Read its sections in this order:

1. **Ledger.** Admitted contrasts, the number of distinct experiments scored (the unit that matters, because the rows of one experiment are not independent), the number of cells and the base rate of significant positive results. A low base rate makes every probability score harder to move.
2. **Gates.** How many scored experiments a skill difference of 0.20 and 0.10 needs, at two power targets (0.90 for decisions, 0.80 as a screen). They come from a simulation on synthetic data and say nothing about your ledger except how large it must be.
3. **Ladder.** One row per **rung**, a predictor of the ladder, and each rung adds one thing to the one below. P0 is the empirical base-rate forecaster of each cell, so its Brier skill is zero by construction. P1 adds a fitted partially pooled prior that accounts for measurement error: it pools the cells and shrinks each toward the whole. P2 adds the precedents that resemble the proposal, under an **admission guard**: its weight on precedents is above zero only when it beats zero on validation rows inside the fit by more than two standard errors, and at zero P2 equals P1. The guard limits how much noise the selection fits. It does not promise that P2 beats P1 out of time, so compare the P2 row with the P1 row on the score, and do not assume the richer rung is the better one. The columns to read:
   - **Brier skill** with its 90 percent interval. Zero means no better than the base rate. An interval that contains zero means the data cannot tell the rung from the base rate. P0's skill is zero by construction.
   - The two **coverage** columns. Near 0.80 and 0.90 is calibrated, and well below means overconfident. [Tutorial 1](01-first-card.md#4-fit-the-models-and-back-test-them) shows how to judge "near" with the interval in the backtest report.
   - **Abstention**: the share of rows on which a card would have declined.
   - **Decidable**: whether the number of experiments reaches the gate.
4. **Decision value.** If the top quarter of experiments had been chosen by a rung's forecast, what share of the total positive lift would have been captured, against random choice (the floor, computed exactly) and an oracle that knows the outcomes (the ceiling). Each policy has an interval and a difference from random order; a difference whose interval contains zero is no edge. It is a different question from calibration, and it is never mixed into the scores.
5. **Calibration by precision.** The scored rows in ten bands of planned exposure. In each band the mean forecast should be near the event rate. A forecaster that is right only for the most precise experiments shows here.
6. **Limitations.** Three standing sentences: a forecast is only as good as its ledger, the gates say what is decidable and not whether the tool is useful, and a precedent forecast never replaces running the experiment.

On the stand-in data every interval contains zero, which is the correct reading of synthetic noise, and the decidable column says only that a skill difference of 0.20 could be told from zero at this number of experiments, not that there is one. On your own archive, the first thing to look at is whether P1 or P2 has a positive skill with an interval above zero, and whether that comparison is decidable.

The card holds counts, rates and scores only. It has no row id, no experiment name, no headline and no cell name, so an organization can publish it and keep its ledger private. See [the benchmark page](../benchmark.md).

## 8. Issue a card

Name the cell you want to forecast and the planned number of units per arm. The `--now` option is needed only because this stand-in ledger is static. When you will join the outcome later, also name the ledger row the card is for with `--row-id source:test_id:variant_id` (or `--test-id` with `--variant-id`); [tutorial 4](04-weekly-loop.md) shows the loop.

```bash run head=26
moot card --source mine --cell revenue_per_user --impressions 50000 --now 2025-12-30T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: 78d1c35a26f41151
- Source: mine
- Cell: revenue_per_user
- Origin: 2025-12-30T00:00:00+00:00
- Ledger snapshot: 20261104-4a80e5b241d7
- Model: adf46433a35f
- Feature hash: e7ee5b832720
- Issued at: 2025-12-30T00:00:00+00:00
- Request: headline "", image changed: no, exposures per arm: 50000, standard error of the future estimate: 0.019 units of the ledger's effect

## Evidence

- Admitted rows in the cell visible at the origin: 120
- Effective number of precedents: 116.9
- Base rate of significant positive results in the cell (P0): 0.117

## Prediction

- P(significant and positive): 0.151
- Point estimate: -0.00 units of the ledger's effect
- 80 percent interval for the true effect: -0.05 to 0.04 units of the ledger's effect
- 80 percent interval for the result of the test at the planned standard error: -0.05 to 0.05 units of the ledger's effect
- P(true effect above 0): 0.457
- Rung: P2, weight on precedents 0.0
```

The first lines are shown. The full card is the one explained in [tutorial 1](01-first-card.md#5-ask-for-a-card).

Add `--json` to print the same card as a machine-readable document, which is what other tools read. The same request through HTTP or the MCP tool is [tutorial 5](05-serve-http-and-mcp.md).

## What you have

A ledger of your own archive, a fitted model, a backtest, a one-page report card and a card.

## What to do next

Keep the ledger current and let the cards earn trust: [tutorial 4](04-weekly-loop.md). If your archive has headline or other text features, add them as `headline` and `feature_*` columns; the forecaster then also weighs precedents by similarity of text.
