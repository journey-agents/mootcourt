# Tutorial 3: reproduce the Upworthy study

**You will:** download the Upworthy Research Archive, build its ledger, fit the forecaster, run the full backtest and compare your tables with the published ones in [Results](../results.md).

**Prerequisites:** a clone of this repository with the package installed (this tutorial uses the scripts in `scripts/`), Python 3.11 or newer and a network connection for the download. About 15 MB of disk for the archives and a few hundred MB for everything that grows from them.

**Time:** about 10 minutes of compute: 5 seconds to build the ledger, 15 seconds to fit, a minute to simulate the gates the first time, and 3 to 4 minutes for the backtest. The download takes as long as your connection needs for 15 MB.

**Why do this.** The reference results of the project are produced by exactly these commands on two public archives. Running them yourself shows that the numbers are not a one-off, and it is the best preparation for running the same commands on your own archive ([tutorial 2](02-your-own-archive.md)). The Upworthy archive is a set of headline and image tests run by one publisher (Matias et al., Scientific Data 8, 195, 2021, CC BY 4.0).

## 0. Choose where the data goes

Everything heavy (the downloads, the ledger, models, reports, cards) goes under one folder, the **data root**. Pick a folder on a volume with a few hundred MB free and export it for this shell. The variable wins over any file setting.

```bash run quiet
export MOOTCOURT_DATA_ROOT="$HOME/mootcourt-data"
mkdir -p "$MOOTCOURT_DATA_ROOT"
```

## 1. Download the archive and verify it

From the clone:

```bash
python scripts/download_data.py
```

The script lists the files through the Open Science Framework API at run time, streams each to a `.part` file, renames it only when complete and records the SHA-256 digest and size of every file in `data/CHECKSUMS.json` under the data root. Every later run verifies the files against that record and stops on any mismatch. It downloads about 15 MB. `--verify-only` checks the files on disk without any network access:

```text
verified  raw/upworthy/upworthy-archive-exploratory-packages-03.12.2020.csv
verified  raw/asos/Datasheet - ASOS Digital Experiments Dataset.pdf
verified  raw/asos/asos_digital_experiments_dataset.parquet
ok: 0 downloaded (0 bytes), 3 verified, 0.0 s
```

(That is the output of `--verify-only` after a download. The same script also fetches the second public archive, the ASOS Digital Experiments Dataset, CC BY 4.0, which the project uses as a deployment-shaped check. This tutorial uses Upworthy only.)

**What the script refuses.** The Upworthy archive also holds a holdout file, a confirmatory file and an undeployed-packages file. The archive asks researchers to pre-register an analysis before using the first two. This project did not, and the script refuses to download any file whose name contains `holdout`, `confirmatory` or `undeployed`. Only the exploratory file is used. `DATA.md` in the repository root has the full account.

## 2. Build the ledger

```bash run needs=archives
moot ingest --source upworthy
```

```text output
upworthy: 17793 contrasts, 13453 admitted, 4873 tests (4.3 s)
snapshot 20261104-4bfb354b87e3 for upworthy
ledger ~/mootcourt-data/data/ledger/ledger.parquet: 17793 rows in 4.7 s
```

The importer reads twelve named columns of the archive and builds one row per contrast: one variant of a test against the earliest-created arm of the same test, with the effect measured as the click-through difference in percentage points. 17,793 contrasts come from 4,873 tests. **13,453 are admitted** and can teach a model; the rest are kept, with the reason, and never used. The archive records neither when a test was read nor the planned exposure of an arm, so two **modeling choices** stand in: a test is treated as final 7 days after its latest arm was created, and the arm's realized impressions stand in for planned exposure. Both are stated as limits in [Limitations](../limitations.md) and in the [method page](../method.md).

## 3. Fit

```bash run needs=archives
moot fit --source upworthy
```

```text output
fitted model 3834241d2b4a at snapshot 20261104-4bfb354b87e3 in 16.0 s; it is the champion for upworthy
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
```

The model id is a digest of the snapshot id and the fitted parameters. The snapshot id begins with the date of the import, so the model id you get on another day differs from the one in the header of the published backtest report, and the last digits of the parameters can differ on another platform (see [troubleshooting](../troubleshooting.md#ids-differ-between-machines)). The card id in step 6 is a digest of the card's content, which includes the model id and the snapshot id, so it differs for the same reason. A different id is not a failure. The scores below are the check.

## 4. Back-test

```bash run needs=archives slow
moot backtest --source upworthy
```

```text output
~/mootcourt-data/reports/gates.json is missing; running the gate power simulation first (synthetic data, same as `moot simulate power`)
gates read from ~/mootcourt-data/reports/gates.json: {"base_rate": 0.3, "by_target": {"0.80": {"n_200": 125, "n_400": 300}, "0.90": {"n_200": 175, "n_400": 375}}, "decision_target": 0.9, "interval": {"by": "row", "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive of that rate (docs/method.md call 170)", "icc": 0.0, "level": 0.95, "rows_per_test": 1.0}, "n_200": 175, "n_400": 375}
note: these gates were simulated at one base rate (0.3); run `moot simulate gate-power` to size them by test at the base rate of your archive
filled the backtest summary of model 3834241d2b4a
scored 13247 rows over 9 origins in 217.4 s (report writing 23.7 s)
wrote ~/mootcourt-data/reports/backtest-upworthy-20261104-4bfb354b87e3.md
wrote ~/mootcourt-data/reports/backtest-upworthy-20261104-4bfb354b87e3.json
wrote ~/mootcourt-data/reports/scores-upworthy-20261104-4bfb354b87e3.parquet
```

The first time, there is no gates file, so the command first runs a quick gate simulation (about a minute, synthetic data) and writes `reports/gates.json`, then the backtest itself (about 3 and a half minutes). That quick file sizes the gate at one base rate (0.3), so the backtest ends with a note, and the decidability columns of your report will differ from the published ones. The published tables read gates sized by test at the base rate of each cell: run `moot simulate gate-power` (`make power`, about ten minutes) and then the backtest again to get the same columns. The scores do not depend on the gates file. It scores 13,247 rows over 9 quarterly origins. Each row is forecast by models fitted on rows that were final before the row's origin.

## 5. Compare with the published tables

Open `reports/backtest-upworthy-<snapshot>.md` under your data root and compare its tables with the Upworthy tables in [Results](../results.md). With the same data and the same seed (`--seed 0` is the default), the scores of the report match the published ones to every printed digit, apart from timing lines. The decidability columns match too once the gates come from `moot simulate gate-power`. The rows to compare:

| Rung | What it is | Brier skill on all rows (90% interval) |
|---|---|---|
| P0 | the empirical base-rate forecaster | 0.0000, by construction |
| P1 | pooled empirical-Bayes shrinkage | 0.0015 (-0.0018 to 0.0048) |
| P2 | weighted precedents under an admission guard | 0.0015 (-0.0017 to 0.0047) |

**What these numbers say, and what they do not.** Brier skill is one minus the rung's Brier score over the Brier score of a constant base rate. Zero means no better than the base rate. P0 is that base rate, as a forecaster, so its skill is zero by construction and its interval has no width. The intervals of P1 and P2 contain zero: pooled shrinkage and weighted precedents are no better than the base rate on this archive, and no worse. Look at the log score for the difference between the two: P2 minus P1 is about minus 0.004 nats, so the precedents did not add anything out of time, even though the admission guard let them in for some cells (the report says for how many). The guard limits how much noise the selection fits. It does not promise that P2 beats P1 on later tests, and here it does not.

That is the finding, and it is a modest one: on this archive no rung of the ladder is distinguishable from the base rate in Brier skill, and the extra machinery of P2 does not pay. Nothing here says it would be the same for product experiments: the archive is headline and image tests from one publisher. The README's list of what the project does not show applies in full.

The report has more to read: calibration, coverage of the intervals (near 0.80 and 0.90 is calibrated), abstention by trigger, decision value and calibration by precision. [Tutorial 2](02-your-own-archive.md#7-read-the-report-card) explains each section. The tables of [Results](../results.md) include the cautionary first run, which scored a relative lift against a noisy reference arm and found negative skill everywhere, because of a design defect and not a finding about the archive, and the coverage by decile of the realized over the planned standard error, which shows where the intervals cover less than they say.

## 6. A card as of the end of the archive

The archive ends in 2015, so its reliability report is dated 2015. With today's clock a card abstains because that report is older than 14 days. To see a card issued as of the end of the archive, pass the time of the archive's last day:

```bash run needs=archives slow head=26
moot card --source upworthy --headline "A simple fact about your mornings" --image-changed false --impressions 20000 --origin 2015-05-07T00:00:00+00:00 --now 2015-05-07T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: 1c3190f7e3731062
- Source: upworthy
- Cell: headline_only
- Origin: 2015-05-07T00:00:00+00:00
- Ledger snapshot: 20261104-4bfb354b87e3
- Model: 3834241d2b4a
- Feature hash: b4b031b2f77e
- Issued at: 2015-05-07T00:00:00+00:00
- Request: headline "A simple fact about your mornings", image changed: no, exposures per arm: 20000, standard error of the future estimate: 0.110 percentage points

## Evidence

- Admitted rows in the cell visible at the origin: 7593
- Effective number of precedents: 1393.2
- Base rate of significant positive results in the cell (P0): 0.101

## Prediction

- P(significant and positive): 0.195
- Point estimate: -0.09 percentage points
- 80 percent interval for the true effect: -0.55 to 0.37 percentage points
- 80 percent interval for the result of the test at the planned standard error: -0.57 to 0.40 percentage points
- P(true effect above 0): 0.388
- Rung: P2, weight on precedents 0.4
```

This card is for a headline-only change: the headline is the proposed variant and `--image-changed false` says the image stays. The cell is derived from that (headline only, image only, or both). Read the card as in [tutorial 1](01-first-card.md#5-ask-for-a-card).

## 7. The rest of the study

These commands produce the remaining tables of [Results](../results.md). They are long runs, and they write under the data root.

| Command | Produces |
|---|---|
| `make challengers` | the gradient-boosted, local and text-only comparisons, each with a recalibrated row (about 6 minutes) |
| `make ablations` | one-setting-at-a-time changes, each also with the admission guard off, and the abstention triggers (the longest run) |
| `make learning-curve` | skill against the amount of history used |
| `make replay` | the weekly replay of the archive |
| `make audit` | a post-hoc leakage audit of a backtest |
| `make power` | `moot simulate gate-power`: the gates sized by test at three base rates (about ten minutes) |

The run-time table at the end of [Results](../results.md) has the measured times of the stages.

`make ablations` and `make challengers` write gigabytes: keep the data root on a volume with room. Then `python scripts/render_readme_results.py --write` rewrites the results page from the reports, and `--check` fails if it is stale.

## What you have

The ledger of the archive, a model, the backtest report and a card, and a direct comparison with the published numbers. If your numbers differ, check the snapshot id first (its digest part must match the published one), then the number of admitted rows (13,453), and then open an issue with the report attached.
