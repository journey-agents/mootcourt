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
registered for a source is its champion. Later models are challengers, except a refit of the same method on newer data, which refreshes the champion
(see "Champion refresh" below).

## Weekly join

The join reads new concluded rows, appends them to the ledger, and attaches an outcome to every card whose row is now
in the ledger, issued or abstained (see "Abstained cards and the convention of the join" below). Two rules protect the record.

- Card files are never changed. An outcome is a separate file, written once and made read-only.
- An outcome exists only once its registered horizon has passed. A join at time `now` skips any row whose `usable_after` is
  after `now`. The first later join attaches it. The reliability window also ignores outcomes dated after `now`.

Each outcome carries a typed miss: `abstained_but_clear`, `confident_but_wrong`, `direction_miss`, `magnitude_miss`, or a hit.

## Drift

The reliability report holds, per cell, the rolling log score and Brier skill over the trailing eight weeks. A cell is below
threshold at a join when its rolling log score is more than 0.10 nats under the base-rate predictor on the same rows, with at
least ten outcomes in the window. After two such joins in a row the cell is marked drifted and every card for that cell
abstains until a join that is not below threshold clears the mark. A join that brought no new outcomes carries every counter
unchanged and refreshes a cell's date only while the cell's window still holds outcomes, so a cell that stops receiving outcomes ages.

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

## Research reports

Three reports are for study of the method, not for the weekly cycle. All are files under the reports folder of the data root, and none writes to the ledger, the cards or the models.

- **The weekly replay.** `python scripts/replay_weekly.py --source NAME` replays an archive as if `moot join` had run every week, and writes `reports/replay-<source>-<snapshot>.json`. Each entry of `weeks` has `cards_issued`, `abstained`, `abstention_rate`, `outcomes_joined`, `miss_counts`, `coverage_90` and the reliability state of the week. `weeks[].abstained_by_trigger` counts the cards of the week that carried each of the four triggers as a reason. A card can carry several, so the counts can add up to more than `abstained`. `totals.abstained_by_trigger` sums the weeks. Read it to see which trigger holds a source back, and when.
- **The trigger removal run.** `moot backtest --source NAME --drop-trigger support` (repeatable) switches a trigger off for that run and writes its own report under `reports/ablations`. When the main run's scores exist for the same snapshot, the report also holds `tables.released_rows`, shown as the section "Released rows": the scores of the rows that the main run abstained on and this run issued. It answers what the dropped trigger was holding back, and whether those rows were forecast well. Without the main run's scores the report says so and prints no such table.
- **`scripts/refresh_discrimination.py`.** `python scripts/refresh_discrimination.py REPORTS_DIR [--check]` recomputes the discrimination columns (AUC and the Murphy resolution) of existing backtest reports from their stored score tables, when the definition of those columns changes, without rerunning a backtest; `--check` only compares.
- **`scripts/paper_extras.py`.** `python scripts/paper_extras.py --source NAME` writes `reports/paper-extras-<source>-<snapshot>.json`, the numbers that no backtest report holds, each with the inputs it came from. For every source it computes the correlation of the log planned exposure per arm with the absolute standardized effect and with the significant-positive event (the stand-in check in [Limitations](limitations.md)). For the synthetic source it also computes how often the P2 admission guard still admits a positive precedent weight when the data carry no text signal, and the share of neighbor weight that lies beyond the top M neighbors. It collects the released rows of every trigger removal run of the snapshot.

## Abstained cards and the convention of the join

The join and the replay of an archive (`scripts/replay_weekly.py`) share one code path, so a team gets what the replay reports. An abstained card is scored on the forecast it withheld: a frozen card
of an abstained cell keeps that forecast in a sealed `withheld` block of its file (rung, weight on precedents, `p_sig`, point, intervals and the predictive), and the join scores it exactly as it scores an issued card,
flagged `abstained: true` and `scored_forecast: withheld`, never dropped. The reliability report is built from every outcome that has a forecast, so a cell whose entry is older than 14 days, or is marked drifted,
collects evidence while it abstains and recovers: after the first ten outcomes in the trailing window the entry is dated at the join, and one join that is not below threshold clears a drift mark. No screen, no HTTP response and no
tool shows the sealed block; an abstained card still shows P0 only, labelled as the base rate the card declined to improve on. A card with no forecast at all (no visible row in its cell) has nothing to score.

An outcome is scored with the predictive the card stored (family, degrees of freedom, location, scale and grid, and the planned standard error `s_star`), so the log score and the coverage match the backtest's for the same row. Coverage is
that of the 90 percent interval for the observed estimate at the planned standard error (`interval_90_y`), the interval the backtest's coverage is measured against; the card also carries the narrower interval for the true effect,
which is what a team reads. A card issued before schema version 2 has no predictive and is scored by the Normal its point and interval imply, and its outcome says `legacy_normal: true`.

## Attaching a card to its outcome

A card can only be scored once its ledger row is known. `moot card --row-id source:test_id:variant_id` (or `--test-id` with `--variant-id`), the `row_id` field of `POST /card` (or `test_id` and `variant_id`) and the `row_id`
argument of the MCP tool name that row. The tool never freezes a card, so it only echoes the key; freeze through the command or the service. The planned exposures of the two arms can differ (`--impressions` and
`--impressions-variant`), and a ledger that has reference headlines takes `--reference-headline`.

## Champion refresh

Each fit records its `method_id`, a hash of the method version, the fixed hyperparameters and the kind and size of the feature space (never of the data), and `data_through`, the latest result it saw. A fit with the champion's `method_id` on strictly newer data is the same method on newer data: it becomes the champion
without the challenger margin, unless its backtest Brier skill interval lies entirely below the champion's. The fit time only breaks a tie between equal data, and a refit of an older snapshot never takes the champion back, whatever its fit time.
A same-method fit that has no backtest yet (the usual state right after new rows arrive) is held as the challenger and marked pending; `moot fit` says so, and `moot backtest` decides it by attaching the summary (no second `moot fit`): the champion is refreshed or the history records `refresh_refused`. A registry written before `data_through` existed gets the champion's value derived from its bundle's fit cutoff (the history logs `data_through_derived`).
Every route to the challenger writes its reason in the history. A fit with another `method_id` is a different method and needs the margin and the gate (`moot promote`).

## The skill line on a card

The card prints the trailing eight-week Brier skill of the cell against its base rate with its 90 percent by-test interval, the rows and tests in the window, the gate verdict at that many tests (read at the base rate nearest the cell's own
in `gates.json`) and the latest gated figure of the champion's backtest. A reliability report written before the interval was stored prints "no interval is recorded". Run `moot simulate gate-power` to size the gates by test at the base rate
of your archive; `moot simulate power` is the earlier per-row simulation at one base rate.
