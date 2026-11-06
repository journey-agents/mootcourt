# Data

Moot Court uses two public archives of concluded online experiments and one simulator. Nothing is bundled in
this repository. `make data` downloads the files, and every later run checks them against recorded checksums.

## Sources and licenses

### Upworthy Research Archive (exploratory split only)

- Where: Open Science Framework node `jd64p`, https://osf.io/jd64p/
- License: CC BY 4.0, held by Cornell University.
- Cite: J. Nathan Matias, Kevin Munger, Marianne Aubin Le Quere and Charles Ebersole, "The Upworthy Research
  Archive, a time series of 32,487 experiments in U.S. media", Scientific Data 8, 195 (2021),
  doi 10.1038/s41597-021-00934-7.
- File used: `upworthy-archive-exploratory-packages-03.12.2020.csv`, 14,260,949 bytes, 22,666 packages in
  4,873 tests, created from 26 Jan 2013 to 29 Apr 2015. Both counts were confirmed on the real file.
- **Files deliberately not used.** The same OSF folder holds a holdout file, a confirmatory file and an
  undeployed-packages file. The archive asks researchers to pre-register an analysis before touching the
  holdout and confirmatory data. This project did not pre-register and did not download, open or score any of the
  three. The download script refuses any file whose name contains `holdout`, `confirmatory` or `undeployed`.
- Former-staff columns (`square`, `significance`, `first_place`, `winner`, `updated_at`) are never read, as
  inputs or as labels. The loader reads an explicit list of twelve columns and the inventory lists those five by
  name only.
- **The archive's 2024 randomization notice.** In June 2024 the archive's maintainers reported evidence of randomization
  problems in about 22 percent of tests and discourage causal or confirmatory use of tests from 25 June 2013 to 10 January
  2014 (https://upworthy.natematias.com/about-the-archive). The 2021 file used here has no flag column, so the loader applies
  the date rule itself: a test that started from 2013-06-25 to 2014-01-10 inclusive (UTC, the earliest `created_at` of its
  packages) gets the status `imbalance_flag` on every contrast, by default (docs/method.md call 275). On the exploratory file
  1,050 of the 4,873 tests (21.5 percent) started in the window. Their rows are kept and counted, not scored: 2,587 contrasts
  of 857 tests change status, 2,550 of them (848 tests) from `admitted`, which leaves 3,022 admitted tests and 10,903 admitted
  contrasts. The earlier runs (run 7 and before) did not apply the rule; `include-randomization-window` is that configuration
  and is kept as an ablation.
- Discrepancies with the design spec, recorded as found on the real file:
  - The file has no `problem` (randomization imbalance) column. The `imbalance_flag` status therefore fires only through the
    date rule above, never through a flag in the file. That is a property of the file, not a result.
  - The file has no named package id. Its unnamed first column is a unique, increasing integer index of the full
    archive. It is used as the package id for tie-breaking and for variant ids.
  - `created_at` has mixed precision (some values with milliseconds, some without) and no time zone. It is read as UTC.

### ASOS Digital Experiments Dataset

- Where: Open Science Framework node `64jsb`, https://osf.io/64jsb/ , DOI 10.17605/OSF.IO/64JSB.
- License, from the datasheet (page 5): "the dataset is distributed under a CC-By Attribution 4.0 International
  (CC BY 4.0) License." It is also stated as "The dataset is open-sourced under a CC-By Attribution 4.0
  International (CC BY 4.0) License." Decision: CC BY 4.0 permits sharing and adapting with attribution, so derived
  aggregates (the tables and figures in the README) may be published with this citation. This was read before the
  data was used.
- Cite: C. H. Bryan Liu, Ângelo Cardoso, Paul Couturier and Emma J. McCoy, "Datasets for Online Controlled
  Experiments", NeurIPS 2021 Datasets and Benchmarks Track, arXiv 2111.10198.
- Files used: `asos_digital_experiments_dataset.parquet` (1,003,239 bytes) and the datasheet PDF
  (206,619 bytes). The CSV copy and `metadata.html` are not downloaded.
- Layout: 24,153 rows, 78 experiments, 99 treatment variants, four decision metrics (ids 1 to 4). One row per
  experiment, treatment, metric and checkpoint with `time_since_start` in days, the control group's count, mean and
  variance, and the treatment group's count, mean and variance. Five treatments lack the variance entries for metrics
  2, 3 and 4 (15 contrasts), as the datasheet says.
- There is no calendar date and no experiment content. See the nominal calendar below.

### Synthetic

`moot simulate` writes a ledger with known true effects. It is used for calibration tests, the gate power
simulation and the only demonstration of a team forecast rung. Every output that uses it is labelled synthetic.

## Contrast definitions

### Upworthy

Within a test the reference arm is the package with the earliest `created_at`; ties go to the lowest package id.
Every other package is one contrast. The effect `y` is the absolute difference in click-through rate in percentage points,
`100 * (ctr_v - ctr_r)`. Its standard error `s` is the binomial value for two independent proportions,
`100 * sqrt(ctr_v (1 - ctr_v) / n_v + ctr_r (1 - ctr_r) / n_r)`, where `ctr` is clicks over impressions and `n` is impressions.
The relative lift against the reference is kept for display in the row's `post_launch` block and is never a label or an input,
because a ratio against a noisy reference arm couples the effect to its own standard error (see `docs/method.md`, call 52).
Contrasts of one test share a reference arm, so the harness resamples whole tests.

Fields known only after a test runs (the two click-through rates, the clicks, the relative lift) sit in the nested `post_launch`
block of the row's feature record. The feature builder reads only the pre-launch fields: headline, reference headline, whether the
headline or the image changed, number of variants and planned exposures per arm.

The cell is the kind of change: `headline_only`, `image_only` or `both`, from comparing the headline and the
`eyecatcher_id` of the variant with the reference. Identical arms carry the cell `unclassified` and are never admitted.

Time: `started_at` of a contrast is the later `created_at` of the two arms, the first instant at which both existed (34 tests have packages created
up to 14.9 days after the reference). The final read and `usable_after` are test level: 7 days after the creation of the latest arm of the test, one instant for every contrast of that test, because the shared reference arm keeps accruing until the last arm ends and no row may expose it earlier. No row is visible before its variant existed. Seven days is a modeling choice, not a fact recorded in the archive. The period is the calendar quarter of the final read.

Impressions: the archive records the impressions each arm realized, not the exposure that was planned. The feature builder and the forecaster's scale use the realized impressions as a stand-in for the planned exposure. That stand-in can leak, because a test that shows a large effect may be given more traffic: log impressions correlate +0.087 with the absolute standardized effect on the admitted rows of run 8 (+0.099 with the window included) (`docs/method.md`, call 53). It is a stated limitation, not a fixed one.

### ASOS

For each treatment variant and each metric, only the last checkpoint becomes a ledger row. Earlier checkpoints are
never admitted as outcomes. The effect `y` is the standardized effect (treatment mean minus control mean, over the pooled
standard deviation) and `s` its large-sample standard error. The effect in the metric's own units and its standard
error are kept in the `post_launch` block of the row's feature record. The cell is the metric (`metric_1` to `metric_4`). The feature space is
cell only (metric and number of variants), so the second rung of the ladder is expected to be close to the first there. The README says
whether it was.

The file gives offsets in days, not dates. **The calendar is nominal.** Experiments are sorted by the sha256 of their id and
spread evenly from 1 Jan 2019 over 730 days. The order is arbitrary and not real. The ASOS backtest therefore tests
prediction across an arbitrary order and says nothing about drift over time. `usable_after` is the nominal start
plus the experiment's last checkpoint offset.

## Admission rules

Admission is a status. Rows are never deleted.

### Upworthy statuses, in the order they are checked

1. `single_arm`: the test has fewer than two packages.
2. `missing_text`: a headline is empty in either arm.
3. `duplicate_arm`: same headline and same `eyecatcher_id` as the reference. The packages may differ in excerpt or lede, which are not the
   kind of change this project models.
4. `imbalance_flag`: the problem flag is set in either arm (the file has no such column), or the test started from 2013-06-25 to
   2014-01-10 inclusive, the window of the archive's June 2024 notice (see above and docs/method.md call 275). The date rule is on by default.
5. `low_exposure`: fewer than 1000 impressions in either arm.
6. `low_clicks`: fewer than 10 clicks in either arm, where the rate and its binomial standard error are unreliable.
7. Otherwise `admitted`.

### ASOS statuses

`admitted` when both arms hold at least 1000 users and the effect and its standard error are finite with `s > 0`.
Otherwise `low_exposure`, the closest status in the fixed vocabulary, with the real reason (`missing_variance`)
recorded in the row's feature record.

## Counts produced by the loaders on the real files

Upworthy: 4,873 tests and 17,793 contrasts (22,666 packages minus one reference per test).

| status | rows, date rule on (run 8) | rows, rule off (run 7) |
|---|---|---|
| admitted | 10,903 | 13,453 |
| duplicate_arm | 3,321 | 3,321 |
| imbalance_flag | 2,587 | 0 |
| low_clicks | 975 | 991 |
| low_exposure | 7 | 28 |
| single_arm, missing_text | 0 | 0 |

Admitted by cell, rule on: headline_only 6,142; image_only 4,371; both 390 (rule off: 7,593; 5,369; 491).
The 2,587 flagged contrasts belong to 857 tests; 1,050 tests in all started in the window, and the others have only contrasts that
`duplicate_arm` already excludes or a single package.

The `low_clicks` status is new. Seven of the 35 rows that were `low_exposure` in the first run (a zero-click arm with at least 1000
impressions) moved to it, and 984 rows that were admitted in the first run have an arm with fewer than 10 clicks.

ASOS: 78 experiments, 99 treatments, 396 contrasts.

| status | rows |
|---|---|
| admitted | 381 |
| low_exposure (missing variance) | 15 |

Admitted by cell: metric_1 99; metric_2 94; metric_3 94; metric_4 94.

The full column inventories are written by `python scripts/data_inventory.py` to `reports/data-inventory-upworthy.txt` and
`reports/data-inventory-asos.txt`.

## Checksums policy

`scripts/download_data.py` lists the files through the OSF API at run time. No file id is written in the script.
It streams each file to a `.part` name and renames it only when the download is complete. On first download it
records the sha256 and byte size of every file in `data/CHECKSUMS.json`, which is committed. On later runs it checks
every file against that record and exits with a non-zero code naming the file on any mismatch. `--refresh` is the only way
to re-record. `--verify-only` checks files on disk without any network access.

Downloaded files are untrusted data. They live only under `data/raw/<source>/`, which is not tracked by git. Loaders
take the file path as an argument, nothing is imported or executed from that directory, and zip archives (none are used today)
are checked for path traversal, absolute names and total size before extraction.
