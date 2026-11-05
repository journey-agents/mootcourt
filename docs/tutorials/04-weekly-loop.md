# Tutorial 4: operate the weekly loop

**You will:** issue cards before experiments launch, each naming the ledger row that will hold its outcome, join the outcomes to those cards as the experiments conclude, read the reliability report that results, and promote a newly fitted model only if it earns it.

**Prerequisites:** [tutorial 1](01-first-card.md) done (the steps below repeat its setup so that this page runs by itself).

**Time:** about 20 minutes. The commands run in about a minute. The one thing that takes weeks in real life, waiting for experiments to conclude, is compressed here by feeding the sample ledger's later experiments in monthly batches.

## Why there is a loop

A card is an opinion, and an opinion is worth what its record is worth. The loop keeps the record. Every card is **frozen** when it is issued, under a content digest, so nobody can adjust it after the result is known. When the experiment concludes, its result is joined to the card as a separate **outcome** file. The outcome says whether the card hit or missed, and how. The recent record of hits and misses is the **reliability report**, and it feeds back into the next card: a card **abstains** when its cell has no recent record, or when the cell has drifted (at two joins in a row, with at least ten outcomes in the window, the rolling log score of the cards was more than 0.10 nats under the plain base rate).

| Step | Cadence | Command | Writes |
|---|---|---|---|
| Ingest the week's results | weekly | `moot ingest --format generic --input new-results.csv --source-name NAME --ledger incoming/ledger.parquet` | a staging ledger of the new rows |
| Join | weekly | `moot join --source NAME --new-rows incoming/ledger.parquet` | appended rows, outcome files, the reliability report |
| Refit | nightly, or after a join | `moot fit --source NAME` | a new model, on the rows usable now: a champion refresh when it is the same method on newer data, otherwise a challenger |
| Backtest | after a refit | `moot backtest --source NAME` | the new model's report, which also decides a pending refresh |
| Promote | after the backtest | `moot promote --source NAME` | the registry, if a challenger beat the champion on the paired comparison |
| Issue | whenever a test is proposed | `moot card --source NAME --cell CELL --impressions N --test-id T --variant-id V` | a frozen card that names its ledger row |

`NAME` is the source name you gave at import. Schedule ingest, join, refit and backtest from cron or your scheduler. `moot doctor` exits non-zero when something has gone stale, which makes it a good last line of the job.

## 1. Set up a ledger with history only

A stand-in for your situation: the ledger holds experiments that concluded up to July 2025, and the experiments that conclude after that have not happened yet. The first 100 experiments of the sample become the history, the remaining 20 the "future".

```bash run
mkdir moot-weekly && cd moot-weekly
moot init > /dev/null
python3 - <<'PY'
import pandas as pd

d = pd.read_csv("mootcourt-data/data/sample-ledger.csv")
ids = sorted(d.experiment_id.unique())
d[d.experiment_id.isin(ids[:100])].to_csv("history.csv", index=False)
d[d.experiment_id.isin(ids[100:])].to_csv("future.csv", index=False)
PY
moot ingest --format generic --input history.csv --source-name sample
moot fit --source sample
moot backtest --source sample | tail -n 4
```

```text output
the quick gates simulation (synthetic data): still running, 10 s elapsed
progress: base rate 0.09, power 0.80, skill 0.20: n = 125 (11 s elapsed)
the quick gates simulation (synthetic data): still running, 20 s elapsed
progress: base rate 0.09, power 0.80, skill 0.10: n = 200 (22 s elapsed)
progress: base rate 0.09, power 0.90, skill 0.20: n = 175 (24 s elapsed)
progress: base rate 0.09, power 0.90, skill 0.10: n = 250 (29 s elapsed)
300 rows from 100 experiments
  admitted: 300
admitted by cell: checkout_conversion 100, pages_per_session 100, revenue_per_user 100
final reads from 2023-01-23 to 2025-07-02
snapshot 20261105-c14e001659bc for sample
ledger ~/moot-weekly/mootcourt-data/data/ledger/ledger.parquet: 300 rows
fitted model dbecf0d65cbf at snapshot 20261105-c14e001659bc on 300 rows usable at 2026-11-05T11:11:31.864823+00:00 in 1.4 s; it is the champion for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
scored 270 rows over 9 origins in 3.4 s (report writing 13.2 s; the whole run 16.6 s)
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261105-c14e001659bc.md
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261105-c14e001659bc.json
wrote ~/moot-weekly/mootcourt-data/reports/scores-sample-20261105-c14e001659bc.parquet
```

The backtest also **seeds the reliability report**: it records how the cards would have done on past experiments, so that the first live cards have a record to stand on.

## 2. Issue cards before the experiments launch

Twelve experiments are about to launch: 103 to 114, which start between 15 July and 22 October. For each, we issue a card on 3 July, before any of them starts. The timing matters: the join counts a card as evidence only when its origin and its issue time are at or before the start of its test, and a card issued while the test is running or after its result is recorded as post-hoc and never scored (a card for experiment 101, which started on 27 June, issued on 3 July would be one). A card must know which ledger row will hold its outcome, so that the join can find it. The row id of a ledger row is `source:test_id:variant_id`: the source name you gave at import, the experiment id from your export, and the variant id. In this sample ledger every row is one variant on one metric, and the variant id is the variant joined to the metric id with `::`, so the row of experiment 103 on the checkout metric is `sample:exp-103:treatment::checkout_conversion`. You know every part of it before launch. Give it to `moot card` as `--row-id`, or as `--test-id` with `--variant-id`, which build the same id. The HTTP service takes the same field as `row_id` and the MCP tool as its `row_id` argument ([tutorial 5](05-serve-http-and-mcp.md)).

```bash run
for n in $(seq 103 114); do
  moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-07-03T00:00:00+00:00 \
    --test-id exp-$n --variant-id treatment::checkout_conversion --json \
    | python3 -c "import json, sys; c = json.load(sys.stdin); print(c['card_id'], c['abstention']['status'], 'p_sig', round(c['prediction']['p_sig'], 3), c['request']['row_id'])"
done
```

```text output
7b5db4126832ff0e issue p_sig 0.041 sample:exp-103:treatment::checkout_conversion
2d1fd20f8284ef21 issue p_sig 0.041 sample:exp-104:treatment::checkout_conversion
a6f47ecf121acf34 issue p_sig 0.041 sample:exp-105:treatment::checkout_conversion
f675081c13407169 issue p_sig 0.041 sample:exp-106:treatment::checkout_conversion
fd7fcd8e8fa0f4be issue p_sig 0.041 sample:exp-107:treatment::checkout_conversion
dd91cce272238f50 issue p_sig 0.041 sample:exp-108:treatment::checkout_conversion
9a93d41a26447060 issue p_sig 0.041 sample:exp-109:treatment::checkout_conversion
05689c8d90d012f6 issue p_sig 0.041 sample:exp-110:treatment::checkout_conversion
098b92000cc04f8a issue p_sig 0.041 sample:exp-111:treatment::checkout_conversion
2c9eaedd3a9df2c8 issue p_sig 0.041 sample:exp-112:treatment::checkout_conversion
2af878e7002088f5 issue p_sig 0.041 sample:exp-113:treatment::checkout_conversion
615e2b9794f91414 issue p_sig 0.041 sample:exp-114:treatment::checkout_conversion
```

Each card is frozen under `cards/` with its row id inside. A card is also refused if its origin is after its issue time (`--origin` later than `--now`), because it would stand on rows that were not yet usable. `--now` is the issue time: just after the history ends. To adapt the loop to your own archive, change the source name, the cell, `--impressions` (the planned units per arm), the issue time and the experiment and variant ids, and issue one card for each experiment you are about to launch. A card without a row id is frozen and valid, but `moot join` cannot attach an outcome to it. A card requested through the MCP tool is never frozen, so freeze through `moot card` or `POST /card`.

All twelve cards issued an opinion and gave the same probability, because the twelve requests are identical: same cell, same planned exposure, no features that tell them apart. That is faithful to this ledger, which has no headline text. On a ledger with features, the cards differ.

## 3. Join the outcomes as experiments conclude

The new results arrive as a file. Import them into a **staging ledger**, a separate ledger file next to the main one. `moot join` then appends the staged rows to the main ledger and attaches outcomes. The staging ledger accumulates: each import adds to it, and `moot join` appends only the rows that the main ledger does not have yet, so a row staged last week is never added twice:

```bash run
mkdir incoming
moot ingest --format generic --input future.csv --source-name sample --ledger incoming/ledger.parquet
```

```text output
60 rows from 20 experiments
  admitted: 60
admitted by cell: checkout_conversion 20, pages_per_session 20, revenue_per_user 20
final reads from 2025-07-11 to 2025-12-29
snapshot 20261105-f10730f0adba for sample
ledger incoming/ledger.parquet: 60 rows
```

Now the join. In production you run `moot join --source sample --new-rows incoming/ledger.parquet` once a week and `--now` is the clock. Here we set the clock ourselves, one join per month from August to December 2025.

```bash run
moot join --source sample --new-rows incoming/ledger.parquet --now 2025-08-01T00:00:00+00:00
for day in 2025-09-01 2025-10-01 2025-11-01 2025-12-01 2025-12-30; do
  moot join --source sample --now ${day}T00:00:00+00:00
done
```

```text output
appended 60 rows, snapshot 20261105-b04b5b1dd18c; attached 1 outcomes {"confident_but_wrong": 1}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 3 outcomes {"hit": 3}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 4 outcomes {"hit": 4}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 3 outcomes {"hit": 3}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 1 outcomes {"hit": 1}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 0 outcomes {}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
```

Each line says how many rows were appended, how many outcomes were attached and the **miss type** of each. Only experiments that had a card get an outcome: 12 of the 20 new experiments here (103 to 114), so the totals are 1, 3, 4, 3 and 1, and 0 on the last join. An outcome exists only once the experiment's result was usable at the time of the join, so the first join attaches only the outcome of the experiment that had concluded by 1 August (103, on 29 July), and later joins attach the rest. Two more rules protect the record, and nothing in this run triggers them: a card issued after its test started is recorded as post-hoc and never scored, and when several cards name one row only the earliest pre-launch card is scored and the others are recorded as reissues. When a join records any, its line says how many (`; N post-hoc cards recorded, not scored`, `; N reissues recorded, not scored`), and `moot doctor` has a `cards sample` line that warns when post-hoc cards exist. The five miss types, in the order they are checked (the first that applies is recorded):

| Type | Meaning |
|---|---|
| `abstained_but_clear` | the card declined, and the result was clearly significant after all |
| `confident_but_wrong` | the card gave 0.6 or more for a significant positive result and it did not happen, or gave 0.1 or less and it did |
| `direction_miss` | the sign of the card's point estimate differs from the sign of the result, and the result is more than one standard error from zero |
| `magnitude_miss` | the direction was right but the result fell outside the card's 90 percent interval |
| `hit` | none of the above |

A card that abstained is joined too. It keeps the forecast it withheld in the frozen file, which the join scores and no interface shows. The join scores that forecast like an issued card's, flags the outcome as abstained and adds it to the reliability report. That is how a cell with a stale record recovers: its abstained cards still bring evidence. A card file is never changed by a join. The outcome is a separate, read-only file under `cards/outcomes/`.

## 4. Read the reliability report

`moot reliability` prints the reliability report of a source, the record every card of the source reads, one line per cell:

```bash run
moot reliability --source sample
```

```text output
report as of 2025-12-30T00:00:00+00:00
cell                   as of         rows tests  brier skill           interval  log score  P0 log score  below drifted
checkout_conversion    2025-12-30       4     4       -0.894   -0.894 to -0.894      1.747         1.768      0 False
pages_per_session      2025-07-02       7     7       -0.011    -0.025 to 0.612      2.166         2.268      0 False
revenue_per_user       2025-07-02       7     7        0.497     0.384 to 0.618      1.922         1.910      0 False
```

(`--json` prints the same report as JSON, which is also what `GET /reliability/sample` of the service returns.)

What to look at:

- **as of, per cell.** Only the checkout cell has a recent date: it is the only cell that received outcomes. "Recent" here is relative to the join clock we set; `moot doctor`, below, compares with today's real date, which is why it still calls every entry stale. The other two carry the date of the backtest that seeded them, and a card for them abstains once that date is more than 14 days old. This is the intended behavior: a cell with no recent record has no standing.
- **rows and tests.** The outcomes inside the rolling window, the trailing eight weeks before the join, and the distinct experiments they come from. A cell's counters are computed at a join that brings it outcomes. For the checkout cell the last such join was on 1 December, so the window runs from 6 October. The twelve experiments concluded on 29 July, 7 August, 16 August, 25 August, 3 September, 12 September, 21 September, 30 September, 9 October, 18 October, 27 October and 5 November (the `ended_at` dates of 103 to 114 in `future.csv`), and four of them, 9 October to 5 November, fall inside the window: that is the 4. The other two cells still show the 7 outcomes that the backtest seeded them with.
- **Why the checkout cell reads 2025-12-30.** A join that brings a cell no outcomes carries its counters unchanged, and refreshes its **as of** date only while the cell's window still holds outcomes. The 30 December join looked back to 4 November, where the experiment that concluded on 5 November still counted, so the date moved to 30 December. Had that experiment ended a few days earlier, the date would have stayed at 1 December, and a cell that stops receiving outcomes ages: its cards abstain once the date is more than 14 days old.
- **log score and P0 log score.** The rolling log score of the cards and of the plain base-rate predictor (P0) on the same rows; higher is better. A cell is below threshold at a join when the model is more than 0.10 nats (the unit of the natural-log score) under the base rate with at least ten outcomes in the window. After two joins in a row below threshold, the cell is marked **drifted** and every card for it abstains until a join that is not below clears the mark. Here no cell has ten outcomes in its window, so none can drift, and `below` is zero.
- **brier skill and interval.** Negative means the recent forecasts did worse than the base rate. With four outcomes from four tests the checkout interval collapses to the single value minus 0.894 and says nothing yet (the first join even recorded a `confident_but_wrong`, the miss type for a card that gave 0.6 or more, or 0.1 or less, against the event); the interval is by test, so repeated rows of one test do not narrow it.

`moot doctor` summarizes the same facts, and once outcome records exist it adds a `cards sample` line that counts the scored outcomes, the post-hoc cards and the reissues (here 12, 0 and 0):

```bash run
moot doctor > doctor.txt; echo "exit code: $?"
tail -n 4 doctor.txt
```

```text output
exit code: 1
WARN  reliability sample: 3 of 3 entries are stale (limit 14 days, oldest 491 days old): checkout_conversion, pages_per_session, revenue_per_user; those cells abstain until new outcomes for the cell are joined
OK    cells: 3 configured cells, each with 20 or more admitted rows
OK    cards sample: 12 scored outcomes, 0 post-hoc cards (issued after their test started: recorded, never scored), 0 reissues (a later card for a row another card scores)
status: warn
```

## 5. Refit, back-test and promote

New rows came in, so the model is out of date ("fit on a snapshot that no longer matches the ledger"). Refit. A fit at a date inside a quarter takes the period level from the last complete quarter, so a refit after a few new rows moves a card only slightly. A fit records the method it was made with (`method_id`, a hash of the method version and its fixed hyperparameters, never of the data) and the date of the latest result it saw (`data_through`). A fit with the champion's method on strictly newer data is a **champion refresh**: it takes the champion's place without the promotion margin, after a check that its backtest did not regress. Until its backtest summary is attached, the refresh is pending and the new model is listed as the challenger, which is why the backtest follows the fit. The registry history states the reason either way (`champion_refreshed` or `refresh_refused`). Any other later fit is registered as the **challenger**.

```bash run
moot fit --source sample
moot backtest --source sample | tail -n 3
moot promote --source sample
```

```text output
fitted model 6b43ae900d91 at snapshot 20261105-b04b5b1dd18c on 360 rows usable at 2026-11-05T11:12:22.733396+00:00 in 1.5 s; it is the challenger for sample
a refresh of the champion is pending: same method, newer data; `moot backtest` decides it (no further `moot fit`)
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261105-b04b5b1dd18c.md
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261105-b04b5b1dd18c.json
wrote ~/moot-weekly/mootcourt-data/reports/scores-sample-20261105-b04b5b1dd18c.parquet
not promoted: no challenger is registered, nothing to promote
```

Read the first line of the fit output: it says which role the new model took when it was fitted. Here it says challenger and the next line announces that a refresh of the champion is pending (same method, newer data), which `moot backtest` decides; after the backtest the refresh is decided and goes through, which is why `promote` then finds no challenger. The backtest then attaches the summary and decides a pending refresh. `moot promote` looks at a challenger, and promotes it only when two conditions hold. It pairs the rows both models scored and bootstraps the difference of their Brier skills by test (500 resamples by default, `--bootstrap`), and the lower end of the 90 percent interval must clear the margin, which is zero by default (`--margin`), so the interval decides. The common tests must also reach the gate for that skill. Otherwise it says which condition failed, for example that the interval does not clear zero or that the backtest has too few tests. When the refresh went through there is no challenger, and `promote` says so. `moot doctor` warns that the champion was fit on an older snapshot whenever the champion is not a model fitted on the current ledger; once the refresh has gone through it reads OK for the model. Nothing is broken. The backtest after the fit also fills the new model's backtest summary, which the skill line of a card reads (its first line is cut off here by `tail`).

## 6. What the weekly job looks like

```bash
moot ingest --format generic --input new-results.csv --source-name mine --ledger incoming/ledger.parquet   # the week's concluded experiments
moot join --source mine --new-rows incoming/ledger.parquet
moot fit --source mine                                   # nightly is fine
moot backtest --source mine
moot promote --source mine
moot doctor                                              # exit 0 healthy, 1 warnings, 2 failures
```

Replace `mine` with your source name. The first line is step 3 again: it puts the week's results, in the exchange format, in a separate ledger file that `moot join` appends. Keep the cards your tools issue under `cards/`; they are the record the next join reads.

The service and the MCP tool read models and reports once started. After `moot promote` changes the champion, restart them.

## What you have

Twelve frozen cards with outcomes, a reliability report that tells the next card whether its cell has standing, and a promotion rule that stops a model from replacing the champion on noise. For the replay of this loop over a whole archive, see [the method page](../method.md).
