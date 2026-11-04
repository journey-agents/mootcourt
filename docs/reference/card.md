# Card reference

A card is one JSON file under `cards/`, named by its card id. The same content is printed as Markdown by `moot card`, and as JSON by `moot card --json`, by `POST /card` and by the MCP tool `get_card`. This page lists the fields of schema version 2. [Concepts](../concepts.md#card) says what the parts are for.

## Top level

| Field | Meaning |
|---|---|
| `schema_version` | `2`. A card from before version 2 has no predictive and is scored by the Normal its point and interval imply. |
| `card_id` | A digest of the card's content. Frozen: the same content gives the same id. |
| `source`, `cell` | The ledger source and the cell the forecast was made in. |
| `snapshot_id`, `model_id`, `feature_hash` | The ledger snapshot, the model and the feature space the card used. All three are digests. |
| `origin` | The time the forecast is made as of: it sees only rows usable by then. |
| `issued_at` | The issue time. The reliability report's age is measured against it. |
| `request` | What was asked: `headline`, `reference_headline`, `headline_changed`, `image_changed`, `impressions`, `impressions_variant`, the planned standard error `s_star`, and `row_id`. |
| `evidence` | `n_cell` (admitted rows visible), `n_eff` (effective number of precedents) and `base_rate_sig_pos` (the cell's rate of significant positive results). |
| `prediction` | The forecast, below. On an abstained card it holds only the base rate (`p0`). |
| `robustness` | Whether the forecast survives dismissing precedents: `applicable`, `k` (the precedents it leans on), `dismissals_needed`, `resamples`, `bootstrap_same_side` and `action_threshold`. Not applicable where the weight on precedents is zero. |
| `skill` | The skill line: `available` (false, with a `reason`, when the reliability record has nothing to report), `brier_skill`, `brier_skill_lo`, `brier_skill_hi`, `n`, `n_tests`, `window_weeks`, `as_of`, `verdict`, and `backtest` (the latest gated backtest: `rung`, `brier_skill` with its interval, `n`, `n_tests`, `snapshot_id`). |
| `abstention` | `status` (`issue` or `abstain`), `reasons` (the triggers that fired) and `details`. |
| `team_forecast` | The team's own forecast when one was given, otherwise null. |
| `withheld` | Only on an abstained card: the forecast that was withheld, sealed. It has the same fields as `prediction`. No renderer, HTTP response or tool shows it; the weekly join scores it. |
| `footer` | The boundary sentence: the card prioritizes and sizes the test, the live test decides. |

## `prediction`

| Field | Meaning |
|---|---|
| `rung` | The rung that produced the forecast. |
| `lambda` | The weight on precedents. Zero means the forecast is P1's. |
| `p_sig` | The probability that the observed estimate of the live test is significant and positive. |
| `p_win` | The probability that the true effect is above zero. |
| `point` | The point estimate of the true effect. |
| `interval_80`, `interval_90` | The central intervals for the **true effect**. These are what the team reads. |
| `interval_80_y`, `interval_90_y` | The central intervals for the **observed estimate** at the planned standard error. They add the noise the test will have, so they are wider. A result is compared with these, and the backtest's coverage is measured against them. |
| `predictive` | The forecast distribution itself, so that a joined outcome can be scored without refitting: `family` (`t`, or `normal` when the cell has no degrees of freedom), `df`, `location`, `scale`, the grid it was computed on (`grid_lo`, `grid_hi`, `grid_n`) and the planned standard error `s_star`. |
| `p0` | The base-rate forecaster of the cell: `p_sig`, `mean` and `var`, the variance of the visible estimates. |

## Giving a card its row id

The weekly join finds a card by `request.row_id`, the ledger row (`source:test_id:variant_id`) that will hold its result.

| Interface | How |
|---|---|
| `moot card` | `--row-id source:test_id:variant_id`, or `--test-id` with `--variant-id` |
| `POST /card` | the `row_id` field, or `test_id` with `variant_id` |
| MCP `get_card` | the `row_id` argument, or `test_id` with `variant_id` |

Giving both forms is an error. A card without a row id is valid, but no outcome can be attached to it. The MCP tool never freezes a card, so it only echoes the key.
