# Concepts

Each term below is used the same way in the commands, the reports and the card. Read the flow first, then use the glossary as a lookup. The [method page](method.md) says how each quantity is computed.

## The flow

Moot Court has one input, one forecast and one feedback loop.

```mermaid
flowchart LR
    X["Concluded experiments<br/>(platform export or warehouse query)"] -->|moot ingest| L[("Ledger<br/>and its snapshots")]
    L -->|moot fit| M["Models<br/>P0, P1, P2<br/>champion and challenger"]
    L -->|moot backtest| B["Backtest report<br/>skill, calibration, gates"]
    B -->|seeds| R["Reliability report<br/>per cell"]
    M --> C["moot card<br/>HTTP service<br/>MCP tool"]
    R --> C
    C --> K["Frozen card<br/>forecast or abstention"]
    K --> T(["The live experiment runs<br/>and concludes"])
    T -->|new rows| J["moot join"]
    J --> O["Outcome files<br/>typed hits and misses"]
    O --> R
    J -->|appends| L
    A["Outside simulation agent<br/>(optional)"] -.->|second opinion| C
```

Read it from the left. Concluded experiments become the **ledger**. The ledger trains **models** and is replayed by the **backtest**, which says whether the models can be trusted and how many experiments it takes to tell. A **card** combines a model with the reliability report and either gives a forecast or abstains. The card is frozen. When the live experiment ends, `moot join` attaches its result to the card as an **outcome**, and the outcomes become the reliability report that the next card reads. The loop is how the forecaster earns and loses trust.

Nothing in the flow decides anything about the experiment. The card prioritizes and sizes the test. The live test decides.

## Glossary

| Term | In one line | Section |
|---|---|---|
| Ledger | the table of concluded experiments that teaches the models | [Ledger](#ledger) |
| Contrast | one row of the ledger: one variant against its baseline on one metric | [Ledger](#ledger) |
| Cell | a group of alike experiments sharing a base rate | [Cell](#cell) |
| Origin | a point in time; a model sees only rows usable by then | [Origin](#origin) |
| `usable_after` | the first instant a row may be used for a forecast | [Origin](#origin) |
| Rung (P0, P1, P2, P3) | one predictor of the ladder | [Ladder](#ladder) |
| Second opinion | an outside agent's probability, held at weight zero until it earns more | [Second opinion](#second-opinion) |
| Abstention triggers | the four reasons a card declines: support, novelty, reliability, instability | [Abstention](#abstention) |
| Card | the frozen forecast for one proposed experiment | [Card](#card) |
| Frozen ids | content digests that make a card, a model and a snapshot tamper-evident | [Frozen ids](#frozen-ids) |
| Harness | the rolling-origin backtest | [Harness](#harness) |
| Gate | the number of scored experiments below which a difference cannot be told from zero | [Gates](#gates) |
| Decision value | how much lift a policy that follows the forecast would have captured | [Decision value](#decision-value) |
| Report card | the one-page, shareable summary of a backtest | [Report card](#report-card) |
| Reliability report | the recent hit record per cell that cards read | [Reliability report](#reliability-report) |

## Ledger

The ledger is the record of concluded experiments, one row per **contrast**: one variant against its baseline on one metric at the final read. A row holds the estimated effect `y`, its standard error `s`, the planned exposure per arm, the time the test started, the time its result became final and the time it may be used (`usable_after`). Rows carry a status. Only admitted rows may teach a model; the others (an arm with too few units, a sample ratio mismatch, a duplicate arm) are kept and counted, never dropped. Snapshots of the ledger are immutable and named by a digest of their content. The file format is in [Ledger format](ledger-format.md).

## Cell

A cell is a group of experiments that are alike enough to share a base rate and a spread of true effects, for example headline-only changes or checkout conversion. By default the cell is the metric. Every prediction is made inside a cell, and every score is reported by cell and pooled. A cell with fewer than 30 admitted rows visible at the origin makes a card abstain.

## Origin

An origin is a point in time. A model at an origin sees only rows whose `usable_after` is not later than the origin. A card is issued at an origin, and a backtest steps through quarterly origins so that each row is forecast by models that could not have seen it.

`usable_after` is the first instant a forecaster may use a row. It defaults to the end of the analysis window plus the delay you give at import (`--usable-delay-days`). It exists because a result is often not final, or not available to the team, the moment a window closes. Using a row before it is usable is the leak that makes backtests look better than they are, so every command respects it, and `moot ledger check` reports a row whose dates break it.

## Ladder

The ladder is a sequence of predictors, called **rungs**, each admitted only if it beats the one below out of time:

- **P0** predicts the cell base rate: what the cell's experiments did on average.
- **P1** pools the cells and shrinks each toward the whole, weighing every row by its own standard error. A noisy experiment counts for less.
- **P2** weighs precedents that resemble the proposal (a kernel regression on the proposal's features), shrunk toward P1, with a weight on precedents chosen per cell and a guard against fitting noise: the weight is above zero only when it beats zero out of sample by more than two standard errors. With the weight at zero, P2 equals P1 exactly.
- **P3** is the team's own forecast, when one is supplied with the request, frozen at issue. No public archive holds one, so it is exercised on synthetic data only.

Challengers (gradient boosting, local empirical Bayes, a text-only classifier) run beside the ladder on the same rows and never replace it without winning on the promotion rule.

### Second opinion

An outside agent that gives a probability for the same event, attached without a code change. It is scored on the backtest beside the model and held at weight zero until it beats the model on origins it was not tuned on. See [Simulators](simulators.md) and [tutorial 6](tutorials/06-simulation-agent.md).

## Abstention

Abstention is the court declining to rule. A card abstains when any one of four **triggers** fires:

| Trigger | Fires when |
|---|---|
| support | the cell has fewer than 30 admitted rows visible at the origin |
| novelty | the proposal is unlike every precedent: its similarity to the cell's rows is below the 5th percentile of what the cell's own rows have to each other |
| reliability | the cell's reliability report is missing, more than 14 days old, or marks the cell drifted (two joins in a row with forecasts worse than the base rate) |
| instability | resampling the precedents by experiment keeps the forecast on the same side of the action threshold in 80 percent or fewer of the resamples |

An abstained card says which reasons fired and shows the base-rate forecast only. The abstention rate is reported with every score, so a forecaster cannot look good by declining everything without that showing.

## Card

A card is a pre-trial opinion for one proposed test: the probability that it ends significant and positive, an interval for the true effect, the precedents that carry the forecast, how far the answer is from changing a decision, how well forecasts like it did in the backtest, and the abstention status. A card never contains a ship, rollout or stopping recommendation. Cards are frozen as content-addressed files, so a card cannot be edited after the outcome is known.

## Frozen ids

Three ids are content digests, written as hexadecimal strings: the **card id** (a digest of the card's content), the **model id** (of the fitted parameters) and the **snapshot id** (of the ledger rows, prefixed with the date). A card stores the ids of the snapshot and the model it used. If the content changes, the id changes, and a card whose id clashes with different content under the same id is refused. The consequence for users: compare a card by its stored ids, never by refitting and recomputing them. A fit repeated on another operating system or linear algebra build can differ in the last bits of its parameters and so in its model id and feature hash, while scores agree to about eleven digits. See [troubleshooting](troubleshooting.md#ids-differ-between-machines).

## Harness

The harness is the rolling-origin backtest. It scores every admitted row once per rung with models fitted only on earlier rows, then reports log score, CRPS, Brier skill against the base rate, calibration, coverage, abstention and decision value, with intervals bootstrapped by test.

## Gates

A gate is a number of scored tests below which a difference in skill cannot be told from zero. Gates come from a power simulation and are read at two power targets: 0.90 for release decisions and 0.80 as a research screen. A comparison below its gate is reported as undecidable at this n. The gate counts tests, not rows, because contrasts of one test share a baseline and are not independent. The gates file is `reports/gates.json`; `moot init` writes a quick one and `moot simulate power` the full one.

## Decision value

Decision value asks a different question from calibration: if a team had chosen the top quarter of its tests by a rung's forecast, how much of the total positive lift would it have captured, compared with choosing at random and with an oracle? It is reported apart from the scores and never folded into them.

## Report card

The report card is the one-page summary that `moot benchmark --ledger` writes: ledger size, gates, the ladder's skill and coverage, decision value and calibration by precision. It holds aggregates only, so an organization can keep its ledger private and publish the card. See [the benchmark page](benchmark.md).

## Reliability report

The reliability report holds, per cell, the rolling log score and Brier skill of recently issued cards over the trailing eight weeks, and whether the cell has drifted. The backtest seeds it, and `moot join` keeps it current. A card reads it, which is how the record of past cards changes what the next card does. See [tutorial 4](tutorials/04-weekly-loop.md).
