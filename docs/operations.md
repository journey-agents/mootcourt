# Operations

How Moot Court is meant to run once a ledger exists. Every step is a command, every step writes a file, and no step
makes a decision about a test.

## The cycle

| Step | Cadence | Command | What it writes |
|---|---|---|---|
| Ingest | when new concluded tests arrive | `moot ingest` | appends contrasts to `data/ledger/ledger.parquet` and writes an immutable snapshot |
| Fit | nightly batch | `moot fit --source <source>` | `models/<model_id>/` with a manifest and an updated registry |
| Backtest | after a fit, or when the method changes | `moot backtest --source <source>` | `reports/backtest-<source>-<snapshot>.md`, `.json`, figures |
| Issue | whenever a test is proposed | `moot card`, `POST /card`, or the MCP tool | `cards/<card_id>.json`, frozen |
| Join | weekly | `moot join --source <source>` | `cards/outcomes/<card_id>.json` and `reports/reliability-<source>.json` |
| Promote | when a challenger has a backtest | `moot promote --source <source>` | the registry, only if the challenger earns it |

## Nightly fit

The fit rebuilds the retrieval index from scratch for the current ledger snapshot. It never updates an index in place.
A fit stores the snapshot id, the feature hash, the parameters and the fit time in the model's manifest. The first model
registered for a source is its champion. Later models are challengers.

## Weekly join

The join reads new concluded rows, appends them to the ledger, and attaches an outcome to every issued card whose row is now
in the ledger. Two rules protect the record.

- Card files are never changed. An outcome is a separate file, written once and made read-only.
- An outcome exists only once its registered horizon has passed. A join at time `now` skips any row whose `usable_after` is
  after `now`. The first later join attaches it. The reliability window also ignores outcomes dated after `now`.

Each outcome carries a typed miss: `abstained_but_clear`, `confident_but_wrong`, `direction_miss`, `magnitude_miss`, or a hit.

## Drift

The reliability report holds, per cell, the rolling log score and Brier skill over the trailing eight weeks. A cell is below
threshold at a join when its rolling log score is more than 0.10 nats under the base-rate predictor on the same rows, with at
least ten outcomes in the window. After two such joins in a row the cell is marked drifted and every card for that cell
abstains until a join that is not below threshold clears the mark. A join that brought no new outcomes only moves the
report's date.

A card also abstains when the cell's reliability report is missing or more than 14 days old.

## Promotion

`moot promote` compares the challenger's backtest Brier skill with the champion's. It promotes only when the gain reaches the
margin and the challenger's backtest test count reaches the gate size for its own skill (the gate counts tests, not rows). Otherwise it prints each condition that failed.

## What the service does not do

The HTTP service and the MCP server read models and reports. `POST /card` freezes the card it issues, which is the only write.
The service has no authentication and binds to the loopback address by default, so put it behind your own access control before
exposing it. When it binds to loopback it accepts only loopback names in the Host header, so a web page cannot reach it through a DNS name that
resolves to 127.0.0.1. The service and the MCP server read the `[decision] action_threshold` of `mootcourt.toml` once at startup (restart to change it),
the same value `moot card` reads, so one request gives one card id on every path. `headline` and `image_changed` are optional in `POST /card` and in the
MCP tools, as on the command line: a ledger without headline text is served by naming the cell. Neither the service nor the card touches a ship,
allocation or stopping rule.
