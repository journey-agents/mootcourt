# Tutorial 4: operate the weekly loop

**You will:** issue cards before experiments launch, join the outcomes to those cards as the experiments conclude, read the reliability report that results, and promote a newly fitted model only if it earns it.

**Prerequisites:** [tutorial 1](01-first-card.md) done (the steps below repeat its setup so that this page runs by itself).

**Time:** about 20 minutes. The commands run in about a minute. The one thing that takes weeks in real life, waiting for experiments to conclude, is compressed here by feeding the sample ledger's later experiments in monthly batches.

## Why there is a loop

A card is an opinion, and an opinion is worth what its record is worth. The loop keeps the record. Every card is **frozen** when it is issued, under a content digest, so nobody can adjust it after the result is known. When the experiment concludes, its result is joined to the card as a separate **outcome** file. The outcome says whether the card hit or missed, and how. The recent record of hits and misses is the **reliability report**, and it feeds back into the next card: a card **abstains** when its cell has no recent record, or when the cell has drifted (the forecasts have been worse than the plain base rate for two joins in a row).

| Step | Cadence | Command | Writes |
|---|---|---|---|
| Ingest the week's results | weekly | `moot ingest --format generic --input new-results.csv --source-name NAME --ledger incoming/ledger.parquet` | a staging ledger of the new rows |
| Join | weekly | `moot join --source NAME --new-rows incoming/ledger.parquet` | appended rows, outcome files, the reliability report |
| Refit | nightly, or after a join | `moot fit --source NAME` | a new model, registered as the challenger |
| Backtest | after a refit | `moot backtest --source NAME` | the challenger's report |
| Promote | after the backtest | `moot promote --source NAME` | the registry, if the challenger earned it |
| Issue | whenever a test is proposed | `moot card --source NAME --cell CELL --impressions N` | a frozen card |

`NAME` is the source name you gave at import. Schedule ingest, join, refit and backtest from cron or your scheduler. `moot doctor` exits non-zero when something has gone stale, which makes it a good last line of the job.

## 1. Set up a ledger with history only

A stand-in for your situation: the ledger holds experiments that concluded up to July 2025, and the experiments that conclude after that have not happened yet. The first 100 experiments of the sample become the history, the remaining 20 the "future".

```bash run
mkdir moot-weekly && cd moot-weekly
moot init > /dev/null
python - <<'PY'
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
300 rows from 100 experiments
  admitted: 300
admitted by cell: checkout_conversion 100, pages_per_session 100, revenue_per_user 100
final reads from 2023-01-23 to 2025-07-02
snapshot 20261103-12617dfc4337 for sample
ledger ~/moot-weekly/mootcourt-data/data/ledger/ledger.parquet: 300 rows
fitted model ea8db7bd4a5c at snapshot 20261103-12617dfc4337 in 1.4 s; it is the champion for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
scored 270 rows over 9 origins in 3.3 s (report writing 2.2 s)
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261103-12617dfc4337.md
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261103-12617dfc4337.json
wrote ~/moot-weekly/mootcourt-data/reports/scores-sample-20261103-12617dfc4337.parquet
```

The backtest also **seeds the reliability report**: it records how the cards would have done on past experiments, so that the first live cards have a record to stand on.

## 2. Issue cards before the experiments launch

Twelve experiments are about to launch. For each, we issue a card. A card must know which ledger row will hold its outcome, so that the join can find it. The row id of a ledger row is `source:experiment_id:variant_id::metric_id`: the source name you gave at import, the experiment id and variant id from your export, and the metric id joined to the variant with `::`. You know every part of it before launch.

`moot card` does not take a row id yet, so this step calls the package's own card functions from a short Python script. They are the same code that `moot card` runs, but they are not a stable public interface, so keep the script in your repository and expect to revisit it after an upgrade. Until a `--row-id` option exists on `moot card`, this script is the way to issue a card that the join can find. (If your cards are issued over HTTP or the MCP tool, the same limit applies. Cards issued without a row id are frozen and valid, but `moot join` cannot attach an outcome to them.)

```bash run
cat > issue_cards.py <<'PY'
import datetime as dt

from mootcourt import card
from mootcourt.bundle import load_bundle
from mootcourt.cli import resolve_model_id
from mootcourt.settings import abstain_config
from mootcourt.storage import storage_paths

paths = storage_paths()                                                                # where the data root's folders are
bundle = load_bundle(resolve_model_id(paths.models, "sample"), paths.models)           # the champion model of the source "sample"
reliability = card.load_reliability_report(paths.reports, "sample")                    # the recent record that the card checks
now = dt.datetime(2025, 7, 3, tzinfo=dt.timezone.utc)                                  # the issue time: just after the history ends

for n in range(101, 113):                      # the twelve experiments that are about to launch
    request = card.CardRequest(source="sample", headline="", image_changed=False, impressions=20000, origin=now,
                               cell="checkout_conversion", row_id=f"sample:exp-{n:03d}:treatment::checkout_conversion")
    issued, _ = card.time_issue(bundle, request, reliability, now, config=abstain_config())     # build the card; nothing is written yet
    frozen = card.freeze_or_load(issued, paths.cards)                                           # freeze it as a file under cards/
    print(frozen["card_id"], frozen["abstention"]["status"], f"p_sig {frozen['prediction']['p_sig']:.3f}", frozen["request"]["row_id"])
PY
python issue_cards.py
```

```text output
e46545e44bbd58c1 issue p_sig 0.209 sample:exp-101:treatment::checkout_conversion
0af31d37ddad841e issue p_sig 0.209 sample:exp-102:treatment::checkout_conversion
a981e990eb074688 issue p_sig 0.209 sample:exp-103:treatment::checkout_conversion
467eef59ad6f832b issue p_sig 0.209 sample:exp-104:treatment::checkout_conversion
38a275af4702b31e issue p_sig 0.209 sample:exp-105:treatment::checkout_conversion
76c61dafe3818f27 issue p_sig 0.209 sample:exp-106:treatment::checkout_conversion
e0d93c8d43113c7a issue p_sig 0.209 sample:exp-107:treatment::checkout_conversion
b38e480eecd78c43 issue p_sig 0.209 sample:exp-108:treatment::checkout_conversion
a5b007c3747c2182 issue p_sig 0.209 sample:exp-109:treatment::checkout_conversion
d54205f0fe871d55 issue p_sig 0.209 sample:exp-110:treatment::checkout_conversion
4058a1090f19d1dd issue p_sig 0.209 sample:exp-111:treatment::checkout_conversion
8689afafdee13d42 issue p_sig 0.209 sample:exp-112:treatment::checkout_conversion
```

To adapt the script to your own archive, change the source name (`"sample"`), the cell, `impressions` (the planned units per arm), `now` (the issue time) and the row id (your experiment and variant ids), and issue one card for each experiment you are about to launch.

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
snapshot 20261103-5f0e42252332 for sample
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
appended 60 rows, snapshot 20261103-80131c793938; attached 3 outcomes {"direction_miss": 2, "magnitude_miss": 1}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 3 outcomes {"direction_miss": 3}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 4 outcomes {"hit": 4}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 2 outcomes {"direction_miss": 2}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 0 outcomes {}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
appended 0 rows; attached 0 outcomes {}; reliability in ~/moot-weekly/mootcourt-data/reports/reliability-sample.json
```

Each line says how many rows were appended, how many outcomes were attached and the **miss type** of each. Only experiments that had a card get an outcome: 12 of the 20 new experiments here, so the totals are 3, 3, 4 and 2. An outcome exists only once the experiment's result was usable at the time of the join, so the first join attaches only the outcomes of experiments that had concluded by 1 August, and later joins attach the rest. The five miss types, in the order they are checked (the first that applies is recorded):

| Type | Meaning |
|---|---|
| `abstained_but_clear` | the card declined, and the result was clearly significant after all |
| `confident_but_wrong` | the card gave 0.6 or more for a significant positive result and it did not happen, or gave 0.1 or less and it did |
| `direction_miss` | the sign of the card's point estimate differs from the sign of the result, and the result is more than one standard error from zero |
| `magnitude_miss` | the direction was right but the result fell outside the card's 90 percent interval |
| `hit` | none of the above |

A card file is never changed by a join. The outcome is a separate, read-only file under `cards/outcomes/`.

## 4. Read the reliability report

```bash run
python - <<'PY'
import json

report = json.load(open("mootcourt-data/reports/reliability-sample.json"))
print("report as of", report["as_of"])
print(f"{'cell':22} {'as of':12} {'n':>3} {'brier skill':>12} {'log score':>10} {'P0 log score':>13} {'below':>6} drifted")
for cell, e in report["cells"].items():
    print(f"{cell:22} {e['as_of'][:10]:12} {e['n']:>3} {e['brier_skill']:>12.3f} {e['rolling_logscore']:>10.3f} "
          f"{e['p0_rolling_logscore']:>13.3f} {e['consecutive_below']:>6} {e['drifted']}")
PY
```

```text output
report as of 2025-12-30T00:00:00+00:00
cell                   as of          n  brier skill  log score  P0 log score  below drifted
checkout_conversion    2025-12-01     5       -0.087      1.984         1.983      0 False
pages_per_session      2025-07-02     7       -0.086      2.200         2.281      0 False
revenue_per_user       2025-07-02     7        0.033      1.921         1.870      0 False
```

What to look at:

- **as of, per cell.** Only the checkout cell has a recent date: it is the only cell that received outcomes. "Recent" here is relative to the join clock we set; `moot doctor`, below, compares with today's real date, which is why it still calls every entry stale. The other two carry the date of the backtest that seeded them, and a card for them abstains once that date is more than 14 days old. This is the intended behavior: a cell with no recent record has no standing.
- **n.** The outcomes inside the rolling window, the trailing eight weeks before the join. A cell's counters, n included, are computed at a join that brings it outcomes, and a later join with none only refreshes the **as of** date (that is why the checkout cell reads 2025-12-01 and not 2025-11-01). For the checkout cell the last such join was on 1 November, so the window runs from 6 September. The twelve experiments concluded on 11 July, 20 July, 29 July, 7 August, 16 August, 25 August, 3 September, 12 September, 21 September, 30 September, 9 October and 18 October (the `ended_at` dates in `future.csv`), and five of them, 12 September to 18 October, fall inside the window: that is the 5. The other two cells still show the 7 outcomes that the backtest seeded them with.
- **log score and P0 log score.** The rolling log score of the cards and of the plain base-rate predictor (P0) on the same rows; higher is better. A cell is below threshold at a join when the model is more than 0.10 nats (the unit of the natural-log score) under the base rate with at least ten outcomes in the window. After two joins in a row below threshold, the cell is marked **drifted** and every card for it abstains until a join that is not below clears the mark. Here no cell has ten outcomes in its window, so none can drift, and `below` is zero.
- **brier skill.** Negative means the recent forecasts did worse than the base rate. With five outcomes, it says nothing yet.

`moot doctor` summarizes the same facts:

```bash run
moot doctor > doctor.txt; echo "exit code: $?"
tail -n 4 doctor.txt
```

```text output
exit code: 1
WARN  model sample: champion ea8db7bd4a5c was fit on snapshot 20261103-12617dfc4337, which no longer matches the ledger; run `moot fit`
WARN  reliability sample: 3 of 3 entries are stale (limit 14 days, oldest 489 days old): checkout_conversion, pages_per_session, revenue_per_user; those cells abstain until new outcomes for the cell are joined
OK    cells: 3 configured cells, each with 20 or more admitted rows
status: warn
```

## 5. Refit, back-test and promote

New rows came in, so the model is out of date ("fit on a snapshot that no longer matches the ledger"). Refit. The new model is registered as the **challenger**; the old one stays the **champion** until the challenger earns the place.

```bash run
moot fit --source sample
moot backtest --source sample | tail -n 3
moot promote --source sample
```

```text output
fitted model 57a727de0c15 at snapshot 20261103-80131c793938 in 1.7 s; it is the challenger for sample
no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261103-80131c793938.md
wrote ~/moot-weekly/mootcourt-data/reports/backtest-sample-20261103-80131c793938.json
wrote ~/moot-weekly/mootcourt-data/reports/scores-sample-20261103-80131c793938.parquet
not promoted: Brier skill gain 0.0075 is short by 0.0125 of the margin 0.0200; the challenger's backtest has 110 tests, below gate n = 400 tests for its skill
```

`moot promote` promotes the challenger only when two conditions hold. Its Brier skill must beat the champion's by a margin (0.02 by default, `--margin`), and the challenger's backtest must rest on at least as many distinct experiments as the gate for that skill. Otherwise it says which condition failed, as above: the gain is short of the margin, and the backtest of 110 experiments is below the gate of 400. That is the usual outcome with small ledgers and means the champion stays. The project is then left as it was: the champion is the old model, the challenger stays registered, and `moot doctor` keeps warning that the champion was fit on an older snapshot until a later fit and backtest earn the promotion. Nothing is broken.

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
