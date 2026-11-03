# Concepts

Each term below is used the same way in the commands, the reports and the card. The method page says how each is computed.

## Ledger

The ledger is the record of concluded experiments, one row per contrast: one variant against its baseline on one metric at the
final read. A row holds the estimated effect `y`, its standard error `s`, the planned exposure per arm, the time the test
started, the time its result became final and the time it may be used (`usable_after`). Rows carry a status. Only admitted
rows may teach a model; the others (low exposure, low clicks and so on) are kept and counted. Snapshots of the ledger are
immutable and named by a digest of their content. The file format is in [Ledger format](ledger-format.md).

## Cell

A cell is a group of experiments that are alike enough to share a base rate and a spread of true effects, for example
headline-only changes or checkout conversion. Every prediction is made inside a cell, and every score is reported by cell and
pooled.

## Origin

An origin is a point in time. A model at an origin sees only rows whose `usable_after` is not later than the origin. A card is
issued at an origin, and a backtest steps through quarterly origins so that each row is forecast by models that could not have
seen it.

## Ladder

The ladder is a sequence of predictors, each admitted only if it beats the one below out of time:

- P0 predicts the cell base rate.
- P1 pools the cells and shrinks each toward the whole.
- P2 weighs precedents that resemble the proposal, shrunk toward P1, with a guard against fitting noise.
- P3 is the team's own forecast, when the ledger carries one.

Challengers (gradient boosting, local empirical Bayes, a text-only classifier) run beside the ladder on the same rows and never
replace it without winning on the promotion rule.

## Abstention

Abstention is the court declining to rule. A card abstains when the cell has too little support, the proposal is unlike every
precedent, the reliability report is missing or stale or shows drift, or the forecast is unstable under a small change in the
precedents. An abstained card says which reason fired. The abstention rate is reported with every score.

## Card

A card is a pre-trial opinion for one proposed test: the probability that it ends significant and positive, an interval for the
true effect, the precedents that carry the forecast, how far the answer is from changing a decision, and the abstention status.
Cards are frozen as content-addressed files, so a card cannot be edited after the outcome is known.

## Harness

The harness is the rolling-origin backtest. It scores every admitted row once per rung with models fitted only on earlier
rows, then reports log score, CRPS, Brier skill against the base rate, calibration, coverage, abstention and decision value,
with intervals bootstrapped by test.

## Gates

A gate is a number of scored tests below which a difference in skill cannot be told from zero. Gates come from a power
simulation and are read at two power targets: 0.90 for release decisions and 0.80 as a research screen. A comparison below its
gate is reported as undecidable at this n.

## Decision value

Decision value asks a different question from calibration: if a team had chosen the top quarter of its tests by a rung's
forecast, how much of the total positive lift would it have captured, compared with choosing at random and with an oracle?
It is reported apart from the scores and never folded into them.
