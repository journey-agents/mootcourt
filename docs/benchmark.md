# The benchmark report card

One command turns a ledger of concluded tests into a one-page card. The card holds aggregate numbers only, so an
organization can run it on its own machine, keep the ledger private and publish the card. Two organizations' cards have the
same sections, the same tables and the same columns, so they can be read side by side.

## Run it privately

```
moot benchmark --ledger my-ledger.parquet
```

The ledger is a file in the format of `docs/ledger-format.md`, written by `moot ingest`. If it holds several sources, choose
one with `--source`. The command runs the standard protocol and nothing else:

- rolling quarterly origins, so every row is scored by models fitted only on rows that were final before its origin;
- the ladder: P0 (the empirical base-rate forecaster, whose Brier skill is zero by construction), P1 (pooled shrinkage that accounts for measurement error) and P2 (weighted precedents under an admission guard), plus P3 when the ledger carries a
  team forecast;
- gates at both power targets, read from `reports/gates.json`; when that file is missing, a quick simulation writes `reports/benchmark/gates-quick.json` instead and the card says so (the shared gates file is never created by this command);
- calibration by precision, abstention and decision value.

It writes `reports/benchmark/<ledger-stem>-<snapshot>.md` and `.json` under the data root. Nothing leaves the machine. The
JSON carries `report_card_schema_version`, which changes whenever a field is added, renamed or removed.

## What to publish

Publish the Markdown or the JSON. Both hold counts, rates, scores with intervals and decile summaries. Neither holds a row
id, a test id, a headline or a cell name. Before you publish, check two things yourself: that the number of tests and the
base rate are not themselves confidential, and that the ledger name (the file stem) is one you are willing to show.

## How to read each line

**Ledger.** Admitted contrasts are the rows the models may learn from. Tests with a scored contrast counts distinct tests,
the unit that matters for uncertainty, because contrasts of one test share a reference arm. Scored rows are the rows
forecast out of time at the quarterly origins. The base rate is the share of scored rows that ended significant and
positive. A small base rate makes every probability score harder to move.

**Gates.** For each power target, the number of scored tests at which a Brier skill difference of 0.20 (n at skill 0.20) or
0.10 (n at skill 0.10) can be told from zero. They come from a simulation on synthetic data with a known base rate and say
nothing about your ledger beyond its size. The section is headed "Tests needed" when the gates count tests (the report records the unit as `gates_unit`) and "Rows needed" when the gates are per row: a per-row gates file, or the quick fallback the report card simulates when `reports/gates.json` does not exist.

**Ladder.** One row per rung over all cells.

- Brier skill is one minus the rung's Brier score over the Brier score of the constant base rate, with a 90 percent
  interval bootstrapped by test (the level is `LEVEL` in `harness_stats`, and the card prints it). Zero means no better than the base rate. An interval that contains zero means the data
  cannot tell the rung from the base rate.
- Coverage 80 and coverage 90 are the shares of outcomes inside the central 80 and 90 percent intervals. Near 0.80 and 0.90
  is calibrated; well below means overconfident.
- Abstention is the share of rows on which the card would have declined to issue a forecast. It is the same for every rung.
- Decidable says whether the number of scored tests reaches the gate. The two columns are headed with the power targets read from the gates file (by default 0.90, the release gate, and 0.80, the research
  screen); a gates file with one target gives one column. "Undecidable at this n" means a difference in skill between this rung and another cannot be established with the
  rows you have, whatever its size.

**Decision value.** If the top quarter of tests had been chosen by a policy, the share of the total positive lift that policy
would have captured. Random is the floor, the oracle (which knows the outcomes) is the ceiling, and each rung sits between.
This is reported apart from calibration and is never folded into it.

**Calibration by precision.** The scored rows in ten bands of planned exposure, from the least to the most precise. In each
band the mean forecast probability should be close to the event rate. A forecast that is right only for precise tests shows
here.

**Limitations.** The same three sentences on every card: the forecast is only as good as the ledger it was fit on; the gates
say whether a skill difference is decidable at this n, not whether the tool is useful; and a precedent forecast never
replaces running the experiment.

## Scale

`moot benchmark --scale N` is a different mode: it times the tool on a synthetic ledger of N contrasts. See `docs/scale.md`.
