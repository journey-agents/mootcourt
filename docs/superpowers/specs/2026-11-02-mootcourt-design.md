# Moot Court: argue the next experiment from precedent before the trial

Status: approved scope (full end to end), 2 Nov 2026. This document is the single source of truth for the first release. A builder should be able to plan from it without going back to the author.

## 1. Intent

Teams that run many online experiments accumulate a ledger of concluded tests: what was changed, what was measured, what the effect and its standard error were. Almost nobody uses that ledger to say anything about the next test before it runs. Moot Court (package mootcourt, command moot) is a small open-source reference implementation of one idea: before a test launches, issue a card that states what the ledger implies about its result, score every card against the live result once it lands, and abstain when the ledger has nothing to say.

The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule. That sentence is the boundary and it appears in the README, the card footer and the service response.

The name is a metaphor the code follows: the ledger is the case law, the predictor weighs precedents, the card is a pre-trial opinion, abstention is the court declining to rule, and the robustness check counts how many precedents must be dismissed to change the opinion. The live experiment is the trial, and only the trial decides. The name sits in the author's Moot family of projects. Package name mootcourt, import name mootcourt, command line entry point moot.

The repo is written for a general audience of experimentation engineers. It does not name any company, team or person as its target reader, and it does not mention any job application or hiring conversation. The author is Yingjie Li; the license is MIT.

## 2. Goals

1. Run end to end on two public archives of real experiments, with a one-command download and a one-command backtest.
2. Implement the full predictor ladder (P0 base rate, P1 empirical-Bayes prior, P2 weighted precedents, P3 team forecast field, second opinion at weight zero) behind one interface.
3. Implement the four abstention triggers and show them firing on real data.
4. Implement the rolling-origin backtest harness with the three scores, the calibration null, interval coverage, the gates with their sample sizes, and the decision-value measurement.
5. Implement the operational loop: versioned ledger snapshots, champion/challenger registry, freeze at issue, weekly join with typed misses, drift to abstain, reliability report.
6. Serve the card three ways: CLI (Markdown and JSON), a thin HTTP service, and a read-only MCP tool.
7. Report the backtest results in the README exactly as they come out, including nulls and abstention rates.

## 3. Non-goals

- No decision automation of any kind: no ship, rollout, allocation, ramp or stopping recommendation.
- No user-level data. Both archives are aggregates; Moot Court never ingests anything finer.
- No LLM calls in the default path. The second-opinion provider interface exists; the default provider returns nothing and the weight is zero.
- No claim that skill on headline tests transfers to product deployments. The README says this in its first screen.
- No dashboard or web UI beyond the JSON service.

## 4. Anti-goals (what would make this a failure even if it runs)

- A README that overstates results, hides the null, or omits the abstention rate.
- Scoring a predictor against labels that were built from the same rows it was fit on. Every score is out-of-origin.
- A card without version ids. Every card carries ledger snapshot id, model id and feature hash.
- Any text that names the intended reader, employer or hiring process.
- The role noun spelled o-w-n-e-r in docs or card text. Use "the launching team". No em dashes or en dashes anywhere in docs, card text or README; use commas, periods or the word "to".

## 5. Data

### 5.1 Upworthy Research Archive (main cell group)

Source: https://osf.io/jd64p/ , exploratory split only (4,873 tests, 22,666 packages, Jan 2013 to Apr 2015). License CC BY 4.0, Cornell University. Cite: Matias et al., Scientific Data 2021, doi 10.1038/s41597-021-00934-7. The confirmatory split is not public and is never used.

Columns used: created_at, test_week, clickability_test_id, impressions, clicks, headline, eyecatcher_id, problem (randomization imbalance flag), excerpt, lede, slug, share_text. Former-staff columns (square, significance, first_place, winner, updated_at) are never used as inputs or labels.

Contrast definition: within a test, the reference arm is the package with the earliest created_at (ties: lowest package id). Every other package is one variant contrast. Effect y is the absolute difference in click-through rate in percentage points, 100 * (ctr_v - ctr_r), with standard error s = 100 * sqrt(ctr_v (1 - ctr_v) / n_v + ctr_r (1 - ctr_r) / n_r) from two independent binomials. The relative lift against the reference is stored in the row's post-launch block for display only and is never a label or an input: a ratio against a noisy reference arm couples the effect to its own standard error (see docs/method.md). One ledger row per contrast. Contrasts in one test share a reference arm; the harness resamples by test, never by row.

Kind of change (the cell key): compare variant to reference. headline_only if headline differs and eyecatcher_id is equal; image_only if eyecatcher_id differs and headline is equal; both if both differ; identical rows are excluded with status duplicate_arm. Product area is a single value, "upworthy", so the Upworthy cell is kind of change crossed with calendar quarter for partial pooling.

Admission (status recorded, rows never deleted): admitted when impressions >= 1000 and clicks >= 10 in both arms, problem flag is clear, both headlines non-empty, test has >= 2 packages. Otherwise status is one of low_exposure, low_clicks, imbalance_flag, missing_text, single_arm, duplicate_arm. Admitted rows get usable_after = the creation time of the latest arm of the test + 7 days, the same instant for every contrast of the test, so a row is never visible before its variant existed and no sibling row exposes the shared reference arm before the test has ended (the registered horizon for this archive, documented as a modeling choice). started_at stays per contrast: the later created_at of the two arms of the contrast.

### 5.2 ASOS Digital Experiments Dataset (deployment-shaped cell group)

Source: https://osf.io/64jsb/ , Liu, Cardoso, Couturier, McCoy, "Datasets for Online Controlled Experiments", NeurIPS 2021 Datasets and Benchmarks, arXiv 2111.10198. 78 experiments, two to five variants, four decision metrics (binary, count, real-valued), daily or 12-hourly cumulative checkpoints. License: read the datasheet on OSF after download and record it in DATA.md before using the data; if the license does not permit redistribution of derived aggregates, the loader still runs locally but the README publishes only summary statistics.

Contrast: each treatment variant against control, per metric, at the final checkpoint. Effect in the metric's own units as given (mean difference) plus standardized effect; the harness uses the standardized one for cross-metric pooling. Cell key = metric id (experiment content is anonymized, so kind of change is unknown). The daily checkpoints demonstrate two design rules: final read at the registered horizon (the last checkpoint is the only one admitted as the outcome) and usable_after (a row is invisible to any origin before its final checkpoint date). 78 experiments give at most a few hundred contrasts, so the gate sections of the report will mostly say "undecidable at this n" for ASOS. That is the honest result and it is kept.

### 5.3 Synthetic deployment-shaped cell

`moot simulate` generates a ledger with known true effects for calibration tests and the gate-power simulation (how many concluded contrasts are needed to detect a Brier skill of 0.20 or 0.10 against the base rate; expected: about 200 and about 400 at base rate near 0.3). It also hosts the only P3 demonstration (a synthetic noisy forecaster), clearly labeled synthetic in every output.

### 5.4 Handling of downloaded files

Downloads are untrusted data. They go to data/raw/<source>/ (gitignored), scripts live in src/ and scripts/, and loaders take the file path as an argument. `scripts/download_data.py` records sha256 and byte size of every file into data/CHECKSUMS.json on first download and verifies on later runs. Nothing under data/raw is ever committed.

## 6. Ledger

Parquet file data/ledger/ledger.parquet plus data/ledger/snapshots/<snapshot_id>/ (immutable copies). snapshot_id = first 12 hex chars of sha256 over the canonical row contents (sorted row ids with every column value) and the schema version, prefixed with the UTC date; a ledger with the same ids but different values gets a new snapshot id.

Row schema (one row per concluded variant contrast):

| column | type | meaning |
|---|---|---|
| row_id | str | stable id: source, test id, variant id |
| source | str | upworthy, asos, synthetic |
| test_id | str | the experiment |
| variant_id | str | the arm compared with the reference |
| cell | str | kind of change or metric id |
| period | str | calendar quarter of the final read |
| started_at | timestamp | test start |
| final_read_at | timestamp | registered horizon |
| usable_after | timestamp | first instant a predictor may see this row |
| y | float | observed effect |
| s | float | standard error of y |
| n_ref, n_var | int | exposures per arm |
| status | str | admitted or an exclusion reason |
| features_json | str | raw text and structured features for retrieval |
| schema_version | int | 1 |

Admission is a status, not a filter. Every query takes an origin timestamp and returns rows with status admitted and usable_after <= origin.

## 7. Features and retrieval

Pre-launch rule. A feature may use only what the launching team knows before the test runs: the headline, the reference headline, whether the headline or the image changed, the number of variants, the planned exposures per arm, the cell and the period. The feature builder enforces this allow-list and raises on a post-launch field (reference click-through rate, clicks, realized standard error); the leakage audit reports any such field as a violation. Cell-level statistics of earlier, concluded tests (for example the median reference click-through rate of the cell among rows visible at the origin) are history and are allowed.

Default features for P2: TF-IDF (1 to 2 grams, min_df 3) on headline text, reduced with TruncatedSVD to 64 dimensions, concatenated with structured features (headline length in words, has question mark, has number, has quote marks, starts with pronoun, image changed flag, log of the planned exposures per arm). Standardize per fit. Kernel k(x, x_i) = exp(-d^2 / (2 h^2)) with d Euclidean on standardized features and h set by the median heuristic on the fit set. An optional sentence-embedding backend is behind a flag and off by default (no model download in the default path). For ASOS, features are the metric id and the number of variants only; P2 degenerates to P1 there, and the report says so.

The retrieval index is rebuilt at every fit and stored with the model; it is never updated incrementally.

## 8. Predictor ladder

Common interface: `predict(x, s_star, cell, origin) -> Predictive`, where Predictive is a probability mass function over a fixed theta grid (801 points spanning the fitted cell's mean plus or minus 8 tau, at least the range of observed y). Every downstream quantity is computed from the grid:

- p_win = P(theta > delta), delta configurable, default 0.
- Predictive for the observed estimate y* = theta + noise with sd s_star: the grid convolved with Normal(0, s_star^2).
- p_sig = P(y* > z * s_star), z = 1.96 by default (significant and positive).
- Point estimate = grid mean; 80 and 90 percent intervals from grid quantiles.

P0 base rate. Per cell, Normal(mean(y), var(y)) of admitted rows up to the origin. Deliberately ignores measurement error. Also exposes the empirical frequency of significant-positive outcomes in the cell.

P1 empirical-Bayes prior. Per cell, Student-t(mu_c, tau_c, nu_c) prior on theta, fit by maximizing the marginal likelihood sum_i log integral Normal(y_i | theta, s_i^2) t(theta | mu_c, tau_c, nu_c) dtheta, integral on the theta grid, nu_c on a small grid {3, 5, 10, 30, inf}. Partial pooling: cell parameters (mu_c, log tau_c) are shrunk toward the global fit with weight n_c / (n_c + kappa), kappa = 20, applied to both the kind-of-change dimension and the period dimension (crossed: fit kind-level and period-level parameters, combine by averaging the shrunk values). This is a simplification of a full crossed random-effects fit and is documented as such.

P2 weighted precedents. With weights w_i = k(x, x_i) / (s_i^2 + tau_c^2) over admitted rows visible at the origin:
- m(x) = sum w_i y_i / sum w_i
- v_m(x) = sum w_i^2 (s_i^2 + tau_c^2) / (sum w_i)^2
- n_eff(x) = (sum w_i)^2 / sum w_i^2
- theta_hat(x) = lambda m(x) + (1 - lambda) mu_c
- v(x) = lambda (v_m(x) + tau_res_c^2) + (1 - lambda) tau_c^2, where tau_res_c^2 is the residual between-test variance after kernel regression in the cell, method of moments on out-of-origin residuals r_i = y_i - m_{-i}(x_i): tau_res^2 = max(0, mean(r_i^2) - mean(s_i^2) - mean(v_m)).
- lambda in {0, 0.1, ..., 1} chosen per cell by out-of-origin log score. lambda = 0 recovers P1 exactly (the grid is then P1's).
- Working predictive theta ~ Normal(theta_hat, v), placed on the grid.

P3 team forecast. A field on the setup card: p_win_team and point_team, frozen at issue with a timestamp, never editable. Scored alongside the predictors when present. No archive has historical forecasts, so the only populated P3 appears in the synthetic cell with a labeled synthetic forecaster.

Second opinion. p_stack = (1 - w) p_sig + w p_AI. Provider interface with one method returning p_AI or None. Default provider returns None and w = 0. `moot earn-weight` fits w on a grid by out-of-origin Brier and only writes w > 0 if the stacked Brier beats p_sig at the gate's n with the gate's margin. The README explains the weight stays zero until earned.

Why not a gradient-boosted regressor: with tens to a few hundred rows per cell, a boosted model on raw features cannot be checked for calibration per cell and gives no principled abstention. The ladder is interpretable at every rung and each rung is a strict generalization of the one below. The README states this and the harness includes a `--challenger gbm` option so the claim can be tested rather than asserted.

## 8a. Response simulators: plugging in developed agents (added 2 Nov 2026, evening)

The second opinion in section 8 is generalized into a plugin system so that agents developed outside this repo, including LLM-based synthetic-user or persona-pool simulators, can be attached without changing Moot Court's code. The rules of section 8 still hold: the agent's output enters the card as p_AI, the stacking weight w starts at zero and is earned only on the out-of-time backtest, and nothing the agent says can touch a ship, allocation or stopping rule.

Interface (Python protocol `ResponseSimulator` in `src/mootcourt/simulators/base.py`):
- `describe() -> SimulatorInfo` with provider_id, version, knowledge_cutoff (ISO date or None), cost_model (free, per_call, per_token), and a plain-language description.
- `simulate(request: SimulationRequest) -> SimulationResult`. The request carries only aggregate, non-personal inputs: source, cell, origin, the contrast's text and structured features (for Upworthy: reference headline, variant headline, image_changed), the planned exposures per arm, s_star, the action threshold, and a budget (max simulated respondents, max seconds). The result carries p_win_ai in [0, 1], optional point_ai and interval_ai in the effect's units, n_simulated, optional raw_votes, provider_id, version, latency_s, cost_usd, and notes. A result may be `None` when the agent declines; then w is irrelevant and the card says the second opinion abstained.

Adapters, so that "developed agents" need no Python change:
- `stdio` adapter: runs a command, writes the request as one JSON line on stdin, reads one JSON line result from stdout; a time cap kills the process and records a decline.
- `http` adapter: POSTs the request JSON to a URL and reads the result JSON; loopback only by default, other hosts require an explicit allow flag.
- `recorded` adapter: replays results from a JSONL file keyed by request hash. This is how an expensive agent is backtested: `moot simulators run --provider X --source upworthy --origins quarterly --out agent.jsonl` runs the agent once over the rolling-origin request set and writes the file; `moot backtest --second-opinion agent.jsonl` scores it out of time without re-running the agent.
- `heuristic` built-in provider: deterministic, uses structured headline features only; exists for tests and as the example of the protocol. `null` is the default provider and returns None.

Registration: Python entry points under the group `mootcourt.simulators`, plus a repo-level `mootcourt.toml` that lists enabled providers with their adapter settings. `moot simulators list` prints what is installed and whether each has an earned weight; `moot card --simulator NAME` attaches one provider to a card.

Scoring and weight: the harness treats the second opinion as its own rung (reported alone as "agent" and stacked as "P2 + agent" at the earned w). `moot earn-weight --second-opinion agent.jsonl` fits w on a grid by out-of-time Brier and writes w > 0 to the registry only if the stacked Brier beats p_sig at the gate's n by the promotion margin. The card shows p_AI, the provider id and version, and the weight in force, side by side with p_sig; the Markdown card says in words when w is zero.

Contamination guard: an LLM-based agent may have seen the archive in pretraining. Every recorded result carries the provider's knowledge_cutoff; the harness marks any scored origin that is earlier than the cutoff as possibly contaminated and reports contaminated and clean scores separately. The README and the paper state this limitation whenever an agent rung appears.

Caching and cost: results are cached under `cache/simulators/<provider_id>/<version>/<request_hash>.json`; a re-run with the same request and version never calls the agent again. Cost and latency are summed into the report.

Privacy and safety: requests never contain user-level data; adapters refuse to send anything other than the request schema; the stdio adapter runs with the repo's environment minus any variable whose name contains KEY, TOKEN or SECRET unless the provider declares it needs one by name.

Documentation: `docs/simulators.md` shows how to attach an existing agent in under thirty lines (one stdio example in Python, one HTTP example), how to run the recorded backtest, and how the weight is earned. `examples/simulators/` holds the stdio example and a persona-pool template whose LLM call is a clearly marked stub.

## 9. Abstention

The card abstains (status abstain, with every triggered reason listed) when any of the four triggers fires:

1. Support: n_c < 30 admitted rows visible at the origin after pooling.
2. Novelty: nearest-neighbor kernel density of x among the cell's visible rows below the 5th percentile of the same density computed leave-one-out over those rows.
3. Reliability: the reliability report for the cell is missing, older than 14 days, or its latest rolling log score is below the drift threshold for two consecutive weekly joins.
4. Decision instability: bootstrap resampling of precedents by test (200 resamples) puts p_sig on the same side of the action threshold a (default 0.35) in 80 percent or fewer of resamples.

An abstained card still shows P0 and the reasons; it never shows a point estimate as if it were usable.

## 10. The card

Issued by `moot card` (CLI), `POST /card` (service) and the MCP tool `get_card`. Contents, in order:

1. Header: source, cell, origin timestamp, ledger snapshot id, model id, feature hash, issued_at.
2. Evidence: n_c admitted rows in cell, n_eff precedents, base rate of significant-positive results in the cell.
3. Prediction: p_sig, point estimate, 80 percent interval (90 percent in JSON), p_win.
4. Team forecast if provided (frozen), side by side.
5. Robustness: how many of the top-k precedents (k = round(n_eff)) must be dismissed to move p_sig across the action threshold; the fraction of bootstrap resamples on the same side of the threshold.
6. Skill at this n: the cell's latest Brier skill against P0 and the n it was measured on, from the reliability report.
7. Abstention status and reasons.
8. Footer: the boundary sentence.

Markdown and JSON renderers share one data class. Latency of the online path is measured and printed in verbose mode; target under one second on a laptop with the index preloaded.

## 11. Backtest harness

`moot backtest --source upworthy --origins quarterly` and the same for asos and synthetic.

- Rolling origin: for each origin t_k (calendar quarter starts), fit on rows with usable_after <= t_k, predict every admitted row with started_at in [t_k, t_{k+1}) with a pre-launch s_star, score once its y is known. s_star comes from the planned exposures per arm and, for Upworthy, the median reference click-through rate c of the row's cell among rows visible at the origin: s_star = 100 * sqrt(2 c (1 - c) / n_arm) (with unequal arms, 100 * sqrt(c (1 - c) (1 / n_ref + 1 / n_var))). For ASOS s_star = sqrt(1 / n_ref + 1 / n_var); for the synthetic source the standard error is fixed by the generator before the test and is used as given. The realized s defines only the event y > 1.96 s and the floor ingredients; it is never an input to any predictor, and the predictive of y* is scored with s_star. Nothing is ever scored by a model that saw it.
- Scores, each with a bootstrap-by-test 90 percent interval:
  - log score and CRPS of the y* predictive at the observed y
  - Brier of p_sig against the significant-positive event, with the irreducible floor E[p_theta (1 - p_theta)] estimated from the shrunken posterior per row, and Brier skill = 1 - Brier / Brier_P0
  - direction accuracy against its ceiling E[Phi(|theta| / s)]
- Calibration: reliability bins of p_sig, ECE, compared with the distribution of ECE under the perfect-calibration null (resample outcomes from the predicted probabilities, 500 draws); report the percentile.
- Coverage of 80 and 90 percent intervals for y.
- Calibration by precision: rows binned in deciles of planned exposures per arm (fewer bins when exposures tie); per rung, the mean p_sig, the event rate, coverage of the 90 percent interval and the count in each bin. A forecaster that is calibrated overall but not within precision strata is not calibrated.
- Split-half check of the prior: fit P1 on odd tests and even tests at the final origin; report the gap in (mu, tau).
- Gates: a predictor is decidable at skill 0.20 when n >= n_200 and at 0.10 when n >= n_400, where the n values come from the simulate command's power run; the report prints decidable or undecidable at the realized n for every cell and rung.
- Circularity: the report states, in its header, that the scores are against the observed estimate with known standard error, not against the unknown true effect, and that this is the only option when no ground truth exists.
- Decision value: for each origin, a budget of K tests (K = 25 percent of the period's tests) is chosen three ways: random, by p_win, by an oracle that knows y. Report the fraction of the period's total positive observed lift captured by each policy, and test-and-roll regret relative to the oracle. This is reported separately from calibration and never folded into one number.

Output: reports/backtest-<source>-<snapshot_id>.md and .json plus figures (reliability diagram, score by origin, coverage, decision value). Figures are PNG via matplotlib; no interactive dependencies.

## 12. Operations

- `moot fit` (the nightly batch): fits P0, P1, P2 per cell at the current snapshot, rebuilds the retrieval index, writes models/<model_id>/ with manifest.json (snapshot_id, feature hash, parameters, fit time, backtest summary).
- Registry: models/registry.json names champion and challenger per source. `moot promote` replaces the champion only when the challenger's backtest Brier skill beats the champion's by the gate margin at the gate's n; otherwise it prints why not.
- Freeze at issue: every card is written to cards/<card_id>.json with the ids above and is never modified. A later join attaches the outcome in a separate file cards/outcomes/<card_id>.json.
- `moot join` (the weekly loop): reads new rows from the sources, appends to the ledger with usable_after, joins outcomes to issued cards, types each miss (direction_miss, magnitude_miss, abstained_but_clear, confident_but_wrong), and rewrites reports/reliability-<source>.json with per-cell rolling log score and Brier skill over the trailing 8 weeks.
- Drift: if a cell's trailing log score is below the drift threshold for two consecutive joins, the reliability report marks the cell drifted and the card abstains for that cell until a join clears it.
- Privacy and cost: aggregates only; everything runs on CPU in minutes; no network calls after download.
- Service: FastAPI app with POST /card (same payload as the CLI), GET /reliability/{source}, GET /health. Read-only.
- MCP tool: a stdio server exposing get_card, list_precedents (top-k precedents with weights for a given x), reliability_report. Read-and-propose only; no tool mutates state.

## 13. Repository layout

```
mootcourt/
  README.md            results first screen, boundary sentence, how to run, what it does not show
  DATA.md              sources, licenses, contrast definitions, admission rules, checksums policy
  LICENSE              MIT
  pyproject.toml       python >= 3.11; numpy, scipy, pandas, pyarrow, scikit-learn, typer, fastapi, uvicorn, mcp, matplotlib, pytest, ruff
  Makefile             data, fit, backtest, card, serve, test
  scripts/download_data.py
  src/mootcourt/
    ledger.py          schema, admission, snapshots, origin queries
    sources/upworthy.py, sources/asos.py, sources/synthetic.py
    features.py        tfidf+svd, structured features, kernel, density
    predictors/base.py, p0.py, p1.py, p2.py, p3.py, second_opinion.py
    abstain.py
    card.py            data class, markdown and json renderers
    harness.py         rolling origin, scores, calibration, coverage, gates, decision value
    registry.py        models, champion/challenger, promote
    loop.py            join, misses, reliability, drift
    service.py         FastAPI
    mcp_server.py
    simulate.py        synthetic ledger, gate power
    cli.py             typer app
  tests/               pytest; synthetic fixtures; no network
  reports/, models/, cards/   generated, gitignored except .gitkeep and the README figures
  docs/superpowers/specs/     this file
```

## 14. Definition of done for the first release

1. `make data && make fit && make backtest` completes on a laptop from a clean clone in under 30 minutes.
2. `moot card --source upworthy --headline "..." --image-changed false --impressions 20000` returns a card in under one second with the index preloaded, or an abstention with reasons.
3. `pytest` passes with no network; tests cover admission statuses, origin visibility, every predictor on synthetic data with known truth (P1 recovers mu and tau within tolerance, P2 with lambda 0 equals P1), abstention triggers, calibration null, gate arithmetic, registry promotion rule, join miss typing, card renderers, service and MCP tool responses.
4. README shows the Upworthy backtest table (per cell and rung: n, log score, Brier skill, decidable or not, coverage, abstention rate), the ASOS table (expected mostly undecidable), the synthetic power table, the reliability diagram, and the decision-value figure, with the exact numbers the run produced.
5. No occurrence of em dash, en dash, the role noun spelled o-w-n-e-r, or any employer, team or person name as target reader in any committed file (a test enforces the character and word rules on docs and card text).

## 15. Left to the builder

- Exact structured-feature list beyond the six named.
- Grid resolution and integration details, as long as tests on synthetic truth pass.
- Package manager (uv or pip) and Makefile details.
- Figure styling.
- The ASOS loader's column mapping, after reading the datasheet.
