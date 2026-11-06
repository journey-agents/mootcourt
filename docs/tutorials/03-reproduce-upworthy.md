# Tutorial 3: reproduce the Upworthy study

**You will:** download the Upworthy Research Archive, build its ledger, fit the forecaster, run the full backtest and compare your tables with the published ones in [Results](../results.md).

**Prerequisites:** a clone of this repository with the package installed (this tutorial uses the scripts in `scripts/`), Python 3.11 or newer and a network connection for the download. About 15 MB of disk for the archives and a few hundred MB for everything that grows from them.

**Time:** about 10 minutes of compute: 5 seconds to build the ledger, 15 to 30 seconds to fit, and 5 to 7 minutes for the backtest, of which about a minute is the quick gate simulation the first time. The download takes as long as your connection needs for 15 MB.

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
python3 scripts/download_data.py
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
upworthy: 17793 contrasts, 10903 admitted, 4873 tests (3.6 s)
snapshot 20261106-2dc461f52ea4 for upworthy
ledger ~/mootcourt-data/data/ledger/ledger.parquet: 17793 rows in 3.9 s
```

The importer reads twelve named columns of the archive and builds one row per contrast: one variant of a test against the earliest-created arm of the same test, with the effect measured as the click-through difference in percentage points. 17,793 contrasts come from 4,873 tests. **13,453 are admitted** and can teach a model; the rest are kept, with the reason, and never used. The archive records neither when a test was read nor the planned exposure of an arm, so two **modeling choices** stand in: a test is treated as final 7 days after its latest arm was created, and the arm's realized impressions stand in for planned exposure. Both are stated as limits in [Limitations](../limitations.md) and in the [method page](../method.md).

## 3. Fit

```bash run needs=archives
moot fit --source upworthy
```

```text output
fitted model 938be3f002b0 at snapshot 20261106-2dc461f52ea4 on 10903 rows usable at 2026-11-06T12:03:15.519027+00:00 in 11.8 s; it is the champion for upworthy
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
```

The model id is a digest of the snapshot id and the fitted parameters. The snapshot id begins with the date of the import, so the model id you get on another day differs from the one in the header of the published backtest report, and the last digits of the parameters can differ on another platform (see [troubleshooting](../troubleshooting.md#ids-differ-between-machines)). The card id in step 6 is a digest of the card's content, which includes the model id and the snapshot id, so it differs for the same reason. It also covers the gates file in force, which the skill line of the card (below the lines shown) reads: a card made after the quick gates of the first backtest and a card made after `moot simulate gate-power` have different ids even when every prediction number is equal. A different id is not a failure. The scores below are the check.

## 4. Back-test

```bash run needs=archives slow
moot backtest --source upworthy
```

```text output
~/mootcourt-data/reports/gates.json is missing; running the quick gate simulation first, the one `moot init` runs (synthetic data, by test, at the simulated base rate nearest this ledger's 0.092); run `moot simulate gate-power` for the full gates. The adjusted bounds of the report do not read the gates: they depend on the family of intervals, 20 intervals for the ladder alone and 52 with the challengers
gates read from ~/mootcourt-data/reports/gates.json: {"base_rate": 0.09, "by_target": {"0.80": {"n_200": 125, "n_400": 200}, "0.90": {"n_200": 175, "n_400": 250}}, "decision_target": 0.9, "icc": 0.13, "interval": {"by": "test", "dependence": "per base rate in by_base_rate: rows per test and the binary within-test correlation measured on the archive of that rate (docs/method.md call 170)", "icc": 0.13, "level": 0.9, "rows_per_test": 3.5}, "n_200": 175, "n_400": 250, "rows_per_test": 3.5}
gate sizes by base rate (tests): 0.09: n_200 175, n_400 250
backtest of upworthy: still running, 10 s elapsed
progress: origin 2013-10-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 2158 rows, scoring 1096
backtest of upworthy: still running, 20 s elapsed
progress: origin 2014-01-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 3335 rows, scoring 1315
backtest of upworthy: still running, 30 s elapsed
progress: origin 2014-04-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 4534 rows, scoring 1907
backtest of upworthy: still running, 40 s elapsed
backtest of upworthy: still running, 50 s elapsed
progress: origin 2014-07-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 6413 rows, scoring 2822
backtest of upworthy: still running, 60 s elapsed
backtest of upworthy: still running, 70 s elapsed
backtest of upworthy: still running, 80 s elapsed
backtest of upworthy: still running, 90 s elapsed
backtest of upworthy: still running, 100 s elapsed
progress: origin 2014-10-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 9139 rows, scoring 2640
backtest of upworthy: still running, 110 s elapsed
backtest of upworthy: still running, 120 s elapsed
backtest of upworthy: still running, 130 s elapsed
backtest of upworthy: still running, 140 s elapsed
progress: origin 2015-01-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 11997 rows, scoring 1143
backtest of upworthy: still running, 150 s elapsed
backtest of upworthy: still running, 160 s elapsed
backtest of upworthy: still running, 170 s elapsed
progress: origin 2015-04-01: fitted ['P0', 'P1', 'P2', 'always_reference', 'always_variant'] on 13132 rows, scoring 270
backtest of upworthy: still running, 180 s elapsed
filled the backtest summary of model 25cd2b6c38d9
scored 13247 rows over 9 origins in 207.3 s (report writing 39.1 s; the whole run 246.5 s)
wrote ~/mootcourt-data/reports/backtest-upworthy-20261105-4bfb354b87e3.md
wrote ~/mootcourt-data/reports/backtest-upworthy-20261105-4bfb354b87e3.json
wrote ~/mootcourt-data/reports/scores-upworthy-20261105-4bfb354b87e3.parquet
```

The first time, there is no gates file, so the command first runs a quick gate simulation (about a minute, synthetic data) and writes `reports/gates.json`, then the backtest itself (about five minutes, of which about one is writing the report). That quick file is sized by test at the simulated base rate nearest the archive's own (0.09, the rate the published gates read too), so the decidability columns already match the published ones. The Bonferroni-adjusted bounds of the pooled table differ in the fourth decimal until the challengers are in the table (`make challengers`, about 6 minutes), because the family of intervals then grows from 20 to 52, the number the results page prints as "intervals in the family". The scores do not depend on the gates file. It scores 13,247 rows over 9 quarterly origins. Each row is forecast by models fitted on rows that were final before the row's origin.

## 5. Compare with the published tables

Open `reports/backtest-upworthy-<snapshot>.md` under your data root and compare its tables with the Upworthy tables in [Results](../results.md). With the same data and the same seed (`--seed 0` is the default), the scores of the report match the published ones to every printed digit, apart from timing lines. The decidability columns match too. The adjusted bounds of the pooled table match once the challengers are in the table (`make challengers`), because the Bonferroni family of 52 intervals of the published report counts them and the family of 20 of a ladder-only run does not. The rows to compare:

| Rung | What it is | Brier skill on all rows (90% interval) |
|---|---|---|
| P0 | the empirical base-rate forecaster | 0.0000, by construction |
| P1 | pooled empirical-Bayes shrinkage | 0.0015 (-0.0018 to 0.0048) |
| P2 | weighted precedents under an admission guard | 0.0019 (-0.0018 to 0.0054) |

**What these numbers say, and what they do not.** Brier skill is one minus the rung's Brier score over the Brier score of a constant base rate. Zero means no better than the base rate. P0 is that base rate, as a forecaster, so its skill is zero by construction and its interval has no width. The intervals of P1 and P2 contain zero: pooled shrinkage and weighted precedents are no better than the base rate on this archive, and no worse. Look at the log score for the difference between the two: P2 minus P1 is about plus 0.0004 nats, which is level with the prior within the interval, so the precedents added nothing measurable out of time, even though the admission guard let them in for some cells (the report says for how many). The guard limits how much noise the selection fits. It does not promise that P2 beats P1 on later tests, and here it shows no measurable gain.

That is the finding, and it is a modest one: on this archive no rung of the ladder is distinguishable from the base rate in Brier skill, and the extra machinery of P2 does not pay. Nothing here says it would be the same for product experiments: the archive is headline and image tests from one publisher. The README's list of what the project does not show applies in full.

The report has more to read: calibration, coverage of the intervals (near 0.80 and 0.90 is calibrated), abstention by trigger, decision value and calibration by precision. [Tutorial 2](02-your-own-archive.md#7-read-the-report-card) explains each section. The tables of [Results](../results.md) include the cautionary first run, which scored a relative lift against a noisy reference arm and found negative skill everywhere, because of a design defect and not a finding about the archive, and the coverage by decile of the realized over the planned standard error, which shows where the intervals cover less than they say.

## 6. A card as of the end of the archive

The archive ends in 2015, so its reliability report is dated 2015. With today's clock a card abstains because that report is older than 14 days. To see a card issued as of the end of the archive, pass the time of the archive's last day:

```bash run needs=archives slow
moot card --source upworthy --headline "A simple fact about your mornings" --image-changed false --impressions 20000 --origin 2015-05-07T00:00:00+00:00 --now 2015-05-07T00:00:00+00:00
```

```text output
# Moot Court card

- Card id: 9809c988fce99cd9
- Source: upworthy
- Cell: headline_only
- Origin: 2015-05-07T00:00:00+00:00
- Ledger snapshot: 20261105-4bfb354b87e3
- Model: 25cd2b6c38d9
- Feature hash: b4b031b2f77e
- Issued at: 2015-05-07T00:00:00+00:00
- Request: headline "A simple fact about your mornings", image changed: no, planned units per arm: 20000, standard error of the future estimate: 0.110 percentage points
- Reference headline: not supplied; the pair features use the fit-set mean reference vector (the center of the pairwise space), not a real pair

## Evidence

- Admitted rows in the cell visible at the origin: 7593
- Effective number of precedents: 1393.2
- Base rate of significant positive results in the cell (P0): 0.101

## Prediction

- P(significant and positive): 0.154
- Point estimate: -0.09 percentage points
- 80 percent interval for the true effect: -0.47 to 0.28 percentage points
- 80 percent interval for the result of the test at the planned standard error: -0.50 to 0.31 percentage points
- P(true effect above 0): 0.357
- Rung: P2, weight on precedents 0.6

## Team forecast

- None provided.

## Robustness

- Top precedents considered (k = round of the effective number): 1393
- Precedents to dismiss, highest weight first, to move p_sig across 0.35: more than 1393
- Share of 200 resamples by test with p_sig on the same side of 0.35: 1.00

## Skill at this n

- Latest gated backtest for this cell (headline_only), rung P2: Brier skill -0.004 (90 percent interval -0.008 to 0.001) over 2280 tests, decidable at skill 0.20 and 0.10; the interval includes zero
- Brier skill against the cell base rate, trailing 8 weeks: 0.094 (90 percent interval 0.038 to 0.180, by test), measured on 265 rows from 93 tests, as of 2015-05-06T22:46:43.618000+00:00, descriptive, one window of many
- Gate at this n: 93 tests: undecidable at this n (the gate needs 250 tests for a skill of 0.10 and 175 for 0.20 at the nearest simulated base rate, 0.09 (this cell's own rate is 0.101)), and its interval is above zero

## Abstention

- Status: issue
- Reasons: none

---

The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.
```

The card ends with the **Skill at this n** section, which reads the backtest you just ran: it gives the cell's own gated skill when the cell is decidable at its number of tests and otherwise the pooled figure, labelled, and the gate it was read against comes from the gates file, so it changes with the file (step 4). This card is for a headline-only change: the headline is the proposed variant and `--image-changed false` says the image stays. The cell is derived from that (headline only, image only, or both). Read the card as in [tutorial 1](01-first-card.md#5-ask-for-a-card).

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

`make ablations` and `make challengers` write gigabytes: keep the data root on a volume with room. Then `python3 scripts/render_readme_results.py --write` rewrites the results page from the reports, and `--check` fails if it is stale.

## What you have

The ledger of the archive, a model, the backtest report and a card, and a direct comparison with the published numbers. If your numbers differ, check the snapshot id first (its digest part must match the published one), then the number of admitted rows (13,453), and then open an issue with the report attached.
