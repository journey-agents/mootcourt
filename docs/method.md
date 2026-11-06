# Method notes

This file documents every design call in plain words. The calls are numbered in the order they were made. Calls 1 to
19 were made when the work was planned, 20 to 40 while the code was built, 41 to 51 when the real data was run, and 52 onward
after the first full run showed a design defect in the scale of the Upworthy effect.
Where a call replaced an earlier plan, the call says so.

## What is built

A ledger holds one row per concluded variant contrast: the observed effect `y`, its standard error `s`, the cell
(the kind of change, or the metric) and the time the row became usable. A ladder of predictors answers one question
for a proposed test: what does the ledger imply about the result? The rungs are not nested in a chain (call 160): P1 adds a fitted partially
pooled Student-t prior that accounts for measurement error to what P0 is, and P2 adds kernel-weighted precedents under an admission guard to what P1 is.

- **P0**, the empirical base-rate forecaster of the visible ledger, per cell and origin. Its significant-positive probability is the
  visible event rate of the cell, the same quantity the Brier skill is measured against, so its Brier skill is zero by construction;
  its sign probability is the visible share of positive estimates and its intervals are the empirical quantiles of the visible
  estimates (call 160). It never models measurement error: the estimates it summarizes already contain it.
- **P1**, an empirical-Bayes prior. Per cell, a Student-t prior on the true effect, fitted by marginal likelihood so
  that each row counts according to its own standard error. Parameters are partially pooled toward the global fit. P1 adds a fitted
  partially pooled Student-t prior that accounts for measurement error.
- **P2**, weighted precedents. A kernel-weighted average of earlier effects with weights that favour similar
  headlines and precise rows, mixed with the P1 mean by a weight chosen per cell, and a predictive of the SAME family as P1 (a
  Student-t with the cell's degrees of freedom, moment matched, call 161). P2 adds kernel-weighted precedents under an admission guard.
  P2 nests P1 exactly at lambda zero.
- **P3**, a team forecast field that is frozen at issue. No archive holds historical forecasts, so it appears only in
  the synthetic source.
- **Second opinion**, an optional stack weight that stays at zero until a provider earns it.

Everything downstream comes from a probability mass function over a fixed grid of true effects: the probability the
true effect is positive, the probability that the observed estimate is significant and positive (`p_sig`), the point
estimate and the intervals.

## Simplifications to read before trusting a number

- **Partial pooling is not a full crossed random-effects fit.** The cell parameters are shrunk toward the global fit by
  weight `n / (n + 20)`, once along the kind-of-change dimension and once along the period dimension, and the two
  shrunk values are averaged. A full crossed random-effects model would estimate both dimensions jointly.
- **Top-M truncation.** The kernel average uses the 1000 nearest precedents per query. Weight beyond that is kept as
  aggregate sums so `p_sig` is not truncated, but the bootstrap resamples only the stored top-M and holds the tail fixed.
- **The 7-day horizon is a modeling choice.** The Upworthy archive does not record when a test was read. A result is
  treated as final seven days after the latest arm of its test was created, one instant for every contrast of the test (on the real file 34 tests
  have packages created up to 14.9 days after the reference, calls 70 and 75). A different horizon would change which rows are visible at each origin.
- **The scores are circular in one specific way.** They are computed against the observed estimate with its known
  standard error, never against the unknown true effect. That is the only option when no ground truth exists, and it means a
  predictor is judged on the estimate a test produced, noise included. The synthetic source, where truth is known, is
  the check that the method itself works.
- **The ASOS calendar is nominal** (call 45), so that backtest cannot speak about drift over time.
- **Headline-test skill is not deployment skill.** Nothing here measures whether skill on headline tests transfers to
  product deployments.

## Calls made when the work was planned

1. The Brier skill baseline is the empirical frequency of significant-positive results in the cell (the base rate), not a
   P0 Normal pushed through the significance rule.
2. Scores are computed on all predicted rows for every rung, so rungs are comparable, and separately on rows where the card
   would not have abstained. The abstention rate is printed next to both.
3. The reliability trigger inside the backtest uses only earlier origins. The first scored origin has no report and abstains
   for that reason; it is labelled the burn-in origin. `moot backtest` also writes the reliability report for the source.
4. Drift threshold: the trailing 8-week log score is more than 0.10 nats below P0 on the same rows, at two joins in a row. Both
   numbers are configuration.
5. A period the model has no history for (the quarter being predicted never has any) uses the most recent visible period's
   parameters.
6. The support trigger counts visible admitted rows at the kind-of-change level, pooled over periods.
7. The choice of the mixing weight and of the residual variance is by leave-one-test-out, not leave-one-row-out, because
   contrasts of one test share a reference arm and are not independent.
8. P2 keeps the top 1000 neighbours by kernel weight, so no matrix with one row and one column per training row is ever formed. It was
   tested against the exact computation on 2000 rows.
9. The log score is the exact mixture density. The CRPS comes from a cumulative distribution on a grid of observed values built by
   fast convolution or chunked normal distribution functions, never from a double sum over the grid for every row.
10. The team forecast `p_win_team` is scored by Brier against the event that the observed effect is positive, beside each rung's
    probability that the observed estimate is positive. It is approximate, synthetic only, and labelled so.
11. A zero-click reference arm was first `low_exposure`; call 54 replaces that with the `low_clicks` status. The final read and `usable_after`
    are the later `created_at` of the two arms of the contrast plus seven days (call 70).
12. Card inputs: the cell is `headline_only` when the image is unchanged, `both` when the image and the headline changed and
    `image_only` when only the image changed. The standard error `s_star` comes from the planned impressions per arm and the cell's
    median reference click-through rate of the rows visible at the origin; call 53 gives the current formula (the first version used the
    delta method for a relative lift).
13. Decision value works at the level of a test. A test's score under the `p_win` policy is the largest `p_win` among its contrasts; its
    value is the best positive observed lift among them. The budget K is 25 percent of the period's tests.
14. Typed misses, in this precedence: `abstained_but_clear`, `confident_but_wrong` (`p_sig` at least 0.6 and no event, or at most 0.1
    and an event), `direction_miss`, `magnitude_miss`, otherwise a hit.
15. The gate sizes come from `moot simulate power`, read from `reports/gates.json`. Nothing hardcodes a sample size.
16. The promotion margin is 0.02 Brier skill, a configuration constant.
17. A `bundle` module was added to the file tree of the spec so the card, the registry and the harness share one fit and one load path. Bundles
    are checked by sha256 before they are loaded.
18. The download script uses only the standard library and lists files through the OSF API at run time. No file id is hardcoded.
19. A writing-rule test blocks a private list of names, stored only as sha256 digests, so the list is not itself in the repository. Pages do not name private parties; a company name appears only where a surveyed product or an export format is documented.

## Calls made while the code was built

20. The P2 bandwidth is the median heuristic times a multiplier from 1, 1/2, 1/4 and 1/8, chosen per cell together with the mixing weight by
    out-of-origin log score. At multiplier 1 the kernel is nearly flat in 72 dimensions.
21. Scores within 0.001 nats resolve to the smaller mixing weight.
22. Neighbours beyond the top 1000 are kept as aggregate sums, so `p_sig` is not truncated.
23. P1 pooling: the scale is pooled as a standard deviation, the period part enters as half a deviation from the global fit, and a period with fewer than 30
    rows carries no period information.
24. The neighbour state carries an extra `tail` field with the aggregate sums.
25. Measured: a P2 fit on 15000 rows across 3 cells takes about 11 seconds, a 20000-row bundle about 17 seconds, and a card with a preloaded bundle about 3 milliseconds.
26. Gate power simulation. Calibrated probabilities come from a Beta distribution whose mean is the base rate and whose variance is `skill * base * (1 - base)`,
    which gives Brier skill `skill` exactly against the constant base rate. The per-row Brier difference is bootstrapped per row, and a replicate
    passes when the lower end of the 95 percent interval is above zero. The sample size is the smallest value on a fixed grid that meets the target power.
27. One reliability module serves the backtest, the report and `moot join`. A cell is below threshold when its rolling log score is more than
    0.10 nats under P0 on the same rows and it has at least 10 outcomes; with fewer, the drift counters are carried unchanged. One join that is not below threshold clears the drift mark.
28. Leakage audit. Besides checking the frames, the `fit` methods of P0, P1, P2 and the feature space are wrapped during factory calls and raise an
    error if a frame with a not-yet-usable row reaches them, so a factory that ignores its `rows` argument is caught.
29. Origins with fewer than 20 visible rows in total are skipped and listed in the report header. Rows are counted as admitted but never scored.
30. Abstention inside the backtest. One decision per scored row is made by the P2 model and copied to every rung's row. The reliability report at an
    origin is built from rows of earlier origins whose `usable_after` is not after that origin. The first scored origin has no report (burn-in).
31. Floor ingredients. For each scored row the shrunken posterior of the true effect given the row's own `y` and `s` under the pooled P1 prior is integrated by
    24-point Gauss-Hermite quadrature, giving the Brier floor and the direction ceiling.
32. The 80 and 90 percent intervals of the observed estimate come from one cumulative distribution evaluation per row on 201 points, inverted by linear interpolation.
33. `decidable_by_tests` applies the gates to the number of tests and is the headline; `decidable` applies per-row gates to the number of scored rows and is shown beside it as the by-row figure (call 70); when the gates file counts tests (`moot simulate gate-power`) the by-row column reads "not computed: the gates count tests", because a row count against a number of tests is not a decision (call 180). All intervals are
    90 percent percentile bootstrap intervals that resample whole tests.
34. Registry. The first registered model is the champion. Promotion needs a Brier skill gain of at least the margin at the gate size for the challenger's own skill, and it reports every failed condition.
35. Decision value. A test's value is `max(0, best y)`. Ties at the cut are averaged. Random order is exact, K over n of the total (call 173). Regret is the oracle's capture minus the policy's.
36. The report is built as JSON first and the Markdown is a pure function of it, with every float printed to four decimals, so any printed number is in the JSON.
37. Outcome files are written once per issued or abstained card whose row is admitted. The model log score is the analytic marginal of the predictive the card stored (calls 162 and 180); only a card of schema 1 is scored by the Normal its point and interval imply, and the baseline log score is the P0 the card itself stored (call 188). A join advances the drift counters only when it attached new outcomes.
38. The service preloads the champion of every registered source at startup. `POST /card` freezes the card it issues, which is the only write. The service has no authentication and binds to the loopback address by default.
39. Test edits in the second build chunk: a report-test helper builds its command from the source, and the MCP test reads `isError` or `is_error` for the SDK rename. No assertion was weakened.
40. The task registry dashboard writes a data file inside the repository. It is ignored by git, and the style test scans only files git would commit.

## Gates

### Call 41: the release gate is power 0.90, the research screen is power 0.80

A rung in a cell is called decidable when its number of scored rows reaches the size at which a simulated
gate has enough power to resolve a Brier skill of 0.20 (or 0.10). The power simulation draws calibrated
probabilities with a known Brier skill against the base rate and asks how often the 95 percent bootstrap
interval of the per-row Brier gain clears zero.

Two power targets are written to `reports/gates.json`, under `by_target`. The release gate is power 0.90.
The research screen is power 0.80. The release gate is stricter because a claim that a model beats the base
rate should be missed rarely before it is trusted, whereas a research screen only asks whether a question is
worth pursuing. The two targets read the same power curve at different levels: one simulated curve of power
against sample size, cut at 0.80 and at 0.90. The top-level `n_200` and `n_400` in the file are the values at the
release gate, and every report prints the research screen beside them. No code holds a gate size; the sizes
come from the file the power run produced.

## Outcomes and time

### Call 42: an outcome exists only once its registered horizon has passed

Every test has a registered horizon, the moment its result is final (`usable_after` in the ledger). A row
whose horizon is after the time of a join gets no outcome at that join. The first later join, with a time at or
after the horizon, attaches it. The reliability window looks at outcomes dated within the trailing eight weeks and
not after the time of the join, so a result dated in the future can neither enter the rolling score nor move the
drift counters. Before this rule a replayed join could count a result before its horizon.

## Calls made when the real data was run

### Call 43: Upworthy admission precedence

Each contrast gets exactly one status, checked in this order: `single_arm`, `missing_text`, `duplicate_arm`, `imbalance_flag`,
`low_exposure`, then `admitted`. At the first run a variant or reference arm with zero clicks was `low_exposure`; call 54 adds the
`low_clicks` status after `low_exposure`.

### Call 44: what the real Upworthy file contains

The exploratory file has no `problem` column and no named package id. The loader reads the `problem` flag when a file has it and
treats its absence as a clear flag, so `imbalance_flag` cannot fire here. The unnamed first column is a unique increasing integer
index, and it serves as the package id for tie-breaking and for variant ids. Timestamps have mixed precision and are parsed as ISO-8601 in UTC.

### Call 45: the ASOS calendar is nominal

The ASOS file gives each checkpoint as days since the start of its experiment and carries no dates. To give every row a
`usable_after`, experiments are sorted by the sha256 of their anonymized id and spread evenly over 730 days from 1 January 2019. The order
does not depend on any value in the data and it is not the real order. The rolling-origin backtest on ASOS therefore predicts across an arbitrary order. The
final checkpoint of an experiment is its largest offset, and that is the only row that becomes an outcome for each treatment and metric.

### Call 46: ASOS standardized effect

The effect is the treatment mean minus the control mean over the pooled standard deviation (Cohen's d), with the large-sample standard error
`sqrt((n_t + n_c) / (n_t n_c) + d^2 / (2 (n_t + n_c)))`. The difference in the metric's own units and its standard error stay in the row's feature record. Fifteen
contrasts lack variance entries in the file and get `low_exposure`, the closest status in the fixed vocabulary, with the true reason recorded.

### Call 47: building the ledger from downloads

`moot ingest` reads `data/raw` and appends the contrasts of each source to the shared ledger. It is idempotent: rows that already exist must be
identical. `make data` runs the download and then the ingest, so `make fit` and `make backtest` find a ledger.

### Call 48: which files the download script fetches

The script refuses any file named for the holdout, confirmatory or undeployed Upworthy data. When the listing holds the preferred files of a
source it fetches only those; otherwise it fetches every file that is not refused. A file larger than 100 MB is refused unless the cap is raised.

### Call 49: the report says which abstention triggers never fired

Each backtest report states, in words, which of the four abstention triggers never fired and whether the reliability trigger fired after the
burn-in origin. A trigger that never fires on real data is a finding, not a detail, so the README repeats it from the report.

### Call 50: ingest must be repeatable

Running the ingest a second time appends nothing, and that must leave the ledger valid. An earlier version turned the timestamp columns into
generic objects when every incoming row was already known and the two frames differed in time resolution and in the time-zone object. The ledger now
returns the original frame when nothing is new and settles the time dtype after any append. A regression test pins this.

### Call 51: results are never tuned after they are seen

The only changes made after the first full run were to the report text (the abstention note), the run scripts, and the repeatability bug in call 50.
No model setting, threshold or grid was changed after seeing a result. Null and negative results stay in the README as the run produced them.
The one exception is a design change, not a tuning step: the first full run gave negative skill on Upworthy, a diagnosis showed that the
label and the scale it was scored on were built wrongly, and calls 52 to 55 replace them. Nothing was tuned against the new numbers, and the
first run's numbers are described in call 52.

## Calls made after the first full run (3 Nov 2026)

### Call 52: relative lift against a noisy reference is not a label

The first full run scored Upworthy with the relative lift in click-through rate as the effect and the delta-method standard error of that
lift as the scale. Brier skill against the base rate came out negative for every rung (P1 -0.107, P2 -0.108). A calibrated forecaster that
uses the base rate as its floor cannot have negative skill, so the cause was in the design, not in the data.

The relative lift divides by the reference arm's own click-through rate, which is itself a noisy measurement. A reference that happened to
read low inflates the lift and, at the same moment, its standard error. Effect and standard error therefore move together. Grouping the
first run's P1 rows into deciles of the realized standard error of the lift, the observed mean effect ran from -41 percent in the most precise decile to
+104 percent in the least precise. The rate of significant positive results ran from 0.004 to 0.160. The P1 probability of a significant positive result
fell from 0.161 to 0.024 over the same deciles, which is the opposite direction, and the 90 percent interval covered the observed estimate only 0.65
and 0.72 of the time at the two extremes. The harness also fed the forecaster the realized standard error of each row as its scale, which is
information that does not exist before a test runs.

Two changes follow, and neither was tuned against a result. First, the Upworthy effect is the absolute difference in click-through rate in percentage
points, `100 * (ctr_v - ctr_r)`, with the binomial standard error of the two proportions. The relative lift is kept in the row's `post_launch` block for display
only. Second, the forecaster's scale comes from what is known at launch (call 53).

After the change, at the run of 3 Nov 2026, the P1 Brier skill against the base rate on all rows is +0.0015 (90 percent interval -0.0019 to +0.0053), which is
not distinguishable from zero, and P2 is -0.0312 (-0.0385 to -0.0233). The result is a null for the prior and a small negative for the precedent rung. It is reported as
produced.

### Call 53: the scale and the features are pre-launch

A forecast is made before the test runs, so every input must exist before it. `s_star`, the standard error of the future estimate, is computed from the
planned exposures per arm and, for Upworthy, the median reference click-through rate `c` of the row's cell among the rows visible at the origin:
`s_star = 100 * sqrt(c (1 - c) (1 / n_ref + 1 / n_var))`, which is `100 * sqrt(2 c (1 - c) / n_arm)` when the two arms are equal. The archive does not say that
impressions were fixed in advance, so the realized impressions serve as the planned-exposure proxy in the backtest. They are the one realized quantity used as a
pre-launch stand-in. On the 13,453 admitted rows the natural log of the impressions per arm correlates +0.10 with the absolute observed effect `|y / s|` and
+0.03 with the significant-positive event. That is small but not zero, and it is a limitation: if editors stopped tests adaptively, part of the realized exposure
is post-launch information. A live card uses the exposure the launching team plans. For ASOS `s_star = sqrt(1 / n_ref + 1 / n_var)`. For the
synthetic source the generator fixes the standard error before the test and it is used as given. The realized standard error defines only the event (the
observed estimate exceeds 1.96 times the realized standard error) and the floor ingredients. The predictive for the observed estimate, its log score,
its intervals and its p_sig all use `s_star`. The join of a live outcome follows the same rule, using the `s_star` frozen on the card.

The feature builder reads an allow-list: the headline, the reference headline, whether the headline or the image changed, the number of variants, the
planned exposure per arm (as its natural log, appended to the structured features), the cell and the period. A post-launch field (reference click-through
rate, clicks, realized standard error) at the top level of a row's features raises an error. Ledger rows keep such fields in a nested `post_launch` block
that no feature reads; only cell statistics of concluded tests, such as the median reference rate, read it, and only for rows visible at the origin.
The leakage audit reports any top-level post-launch field as a violation and recomputes `s_star` for Upworthy and ASOS from the ledger to confirm that no
realized value reached it. The relative lift and the original-unit ASOS effect moved into the same block.

### Call 54: the `low_clicks` status

An arm with fewer than 10 clicks has a click-through rate and a binomial standard error too unreliable to use, so the contrast gets `low_clicks`. The status
is checked after `low_exposure`, so an arm with fewer than 1000 impressions is still `low_exposure`. Counts are in DATA.md and in the data inventory.

### Call 55: calibration by precision

Calibration is checked within strata of precision as well as overall. Every backtest report has a table with deciles of the planned exposures per arm and,
per rung, the mean p_sig, the rate of the event, the coverage of the 90 percent interval and the number of rows. Decile edges come from the distinct scored
rows, so each rung is cut the same way; tied exposures give fewer groups. The README renders the table for P1 and P2. A forecaster that looks calibrated overall but is wrong inside a stratum
is not calibrated, and the first run's defect would have shown here at once.

### Call 56: provenance and integrity fixes from the code review

The review of the first two build chunks led to these changes, each with a test. A bundle loads only when its manifest lists exactly the files in its folder and
the five required artifacts; each file is read once and loaded from the bytes that were hashed; the manifest must name the folder's own model id. A bundle
records the latest `usable_after` it was fit on and refuses a card or prediction at an earlier origin, so parameters never use rows from after the origin. The
snapshot id hashes the canonical content of every row, so a changed value gives a new snapshot. The card id hashes the whole card minus the id, and a second
card with the same id but different content fails instead of being shown. A reliability report dated after the issue time counts as not fresh. A card with no visible
rows lists the reliability reason beside the support reason. The share of each precedent now counts the weight beyond the top 1000. The second-opinion margin is in
Brier skill units, like the promotion margin, and the gate counts only tests with a row on which the provider gave an opinion (call 76: tests, not rows). The reference marginal likelihood in the
tests widens its grid to cover the data. Not changed: the lambda selection scores the zero-weight case with a Normal approximation of the prior, which the module
documents as a working score.

### Call 57: one storage root

The heavy folders (`data/raw`, `data/ledger`, `reports`, `models`, `cards`, `cache`, `experiments`) are resolved by one function in `mootcourt.storage`. The order is
the environment variable `MOOTCOURT_DATA_ROOT`, then `data_root` in the `[storage]` table of `mootcourt.toml` in the working directory, then the repo-local relative
paths. Every command option that names one of these folders now defaults to the resolved path, and explicit options still win. External volumes are often exFAT, which
has no symlinks, no hard links and no permission bits, so a permission change is best effort and never required, and a frozen card falls back from a hard link to an
exclusive create when the volume refuses links. The figures that the README links stay in the repository (`reports/figures`); `scripts/render_readme_results.py --write`
copies them there from the reports folder. `moot storage` prints each folder, its size and the free space of its volume, and warns below 10 GB.

### Call 58: response simulators attach outside agents without a code change

An agent built elsewhere gives a second opinion through a small protocol: `describe()` and `simulate(request)`. The request holds aggregate inputs only (source, cell,
origin, the two headlines, change flags, planned exposures per arm, the standard error known before launch, the action threshold and a budget) and refuses any other
key, so no user-level field can travel. The result is `p_win_ai`, defined as the probability that the live test ends significant and positive, the event `p_sig`
forecasts, plus optional point and interval, aggregate votes, latency and cost. Adapters run a command over stdio (no shell, a time cap that kills the whole process group, every variable whose name
looks like a credential removed unless declared), call an HTTP endpoint (loopback only unless allowed, redirects not followed), or replay a recorded file keyed by
a hash of the request. Providers register through the entry point group `mootcourt.simulators` or the `[simulators.*]` tables of `mootcourt.toml`. Results are cached
by provider, version and request hash, explicit declines included, so an agent is never asked the same thing twice. A timeout, a failed start, a connection error or an
output that is not a valid result is a failure, not a decline: it is recorded with its reason and never cached. Details and two short examples are in `docs/simulators.md`.

### Call 59: the second opinion is a rung, and its weight starts at zero

`moot simulators run` writes one record per scored row of the rolling-origin backtest, with the same standard error the backtest uses, so a recorded run can be replayed
without the agent. `moot backtest --second-opinion` adds two probability-only rungs to a separate report: `agent` (its probability alone; rows it declined or that are
absent from the file are left out and counted) and `P2+agent` (`p_sig` stacked at the weight in force). Density, intervals and CRPS are not available for these rungs and
are left empty, not zero. `moot earn-weight --second-opinion` fits the weight on a grid by Brier score on the origins before an inner cut and judges it on the origins from the cut on
(call 74); it writes a positive weight to the registry only when the stacked score beats `p_sig` on the judged rows by the promotion margin and the judged rows with an
opinion come from at least as many distinct tests as the gate size (call 76). A weight that later stops passing is reset to zero.

Contamination. An agent built on a language model may have seen a public archive in pretraining. Every record carries the knowledge cutoff, origins earlier than the
cutoff are flagged (every origin, when a provider declares no cutoff), the report shows contaminated and clean scores separately, and the weight is earned on clean
origins unless `--include-contaminated` is passed, in which case the stored weight carries a contaminated flag that the card and the report repeat. On
archives that end in 2015 no current language-model agent has a clean origin, so none can earn weight from them. That is the honest result.

### Call 60: challengers on the same rows

Three challengers run beside the ladder on exactly its origins and rows. `GBM` is a gradient-boosted regression whose predictive spread comes from out-of-fold residuals:
the visible rows are put in time order, cut into five contiguous folds, each fold is predicted by a model fit on the others, and the variance of those residuals minus the
mean squared standard error is the spread of the true effect; the model that predicts is refit on all visible rows. Its `p_sig` goes through the same reliability bins
as every other rung. `local_eb` fits a Normal prior on the k nearest visible rows of the cell in feature space (k is 50 by default, `--local-k`) with the DerSimonian-Laird
moment estimate and no shrinkage toward the cell prior; its predictive for the true effect is that prior. `text_lr` is a TF-IDF logistic regression on the variant headline
that predicts the direction event, plus a second regression on the same text for the significant-positive event, with the probabilities used as they come (no Platt
step). It ignores the precision of the future test, which is part of what the comparison shows, and it has no density, so it is scored with Brier and direction
accuracy only. It needs text and is refused for ASOS.

### Call 61: direction baselines

`always_reference` predicts that the earliest-created arm wins and `always_variant` that it loses. They carry only a direction, so they are scored on direction accuracy
against the same ceiling as every rung and have no probability, density or interval. Because the reference is the earliest-created arm, `always_reference` measures the
creation-order effect that the archive's authors credit it with. A rung that cannot beat it at predicting direction has learned nothing that creation order does not already say.

### Call 62: ablation switches and where their reports go

`--features {text,structured,both}` keeps the text columns, the structured columns or both. `--bandwidth-mult` and `--lambda` fix P2's bandwidth multiplier and its weight
on precedents. `--kappa` sets the P1 pooling strength and `--prior normal` restricts P1 to a Normal prior. `--p2-selection` and `--recency` are described in calls 63 and
64. Any setting that differs from the default writes a report named for it under `reports/ablations` (for example `backtest-upworthy-<snapshot>--features-text.json`),
draws no figures and does not touch the reliability seed or the registry, so an ablation can never replace the main report. The report header records the variant.

### Call 63: forward-chaining selection of the P2 hyperparameters

Leave-one-test-out selection, the original rule, removes a test's own contrasts and nothing else, so a validation row may borrow precedents that were created after it.
Forward chaining respects time. Inside the fit set, three inner cuts sit at the 50th, 67th and 83rd percentiles of start times; a row after the cut at block b is
predicted using only rows usable at that cut, which is what a fit at that cut would have had; rows before the first cut are never validated. Weight on precedents, bandwidth
multiplier and (with `--recency select`) the half-life are chosen jointly by the mean log score of those predictions, with the same tie rule as before (the smaller
lambda within 0.001 nats). The estimates of the prior itself (P1) still use all fit rows. Both rules are backtested on the same origins and the per-cell selections (lambda,
bandwidth, half-life, share of origins where lambda was zero) are in every report.

### Call 64: recency kernel

`--recency select` multiplies each precedent's kernel weight by `2 ** (-age / half_life)` with age in days from the origin to the precedent's `usable_after`, and chooses
the half-life per cell from infinity (no decay), 365, 180 and 90 days with the other hyperparameters. `--recency DAYS` fixes it. Under leave-one-test-out the age is
measured from the validation row's start, which is only a rough stand-in; the rule is meaningful under forward chaining, where the age is measured from the inner cut as it
is at a real origin. A synthetic test with a flip in the headline effect confirms that forward chaining stops trusting precedents and that recency finds a short half-life,
and that neither happens on a stable archive.

### Call 65: learning curve

`moot backtest --learning-curve FRACTIONS --seeds N` takes the latest quarter start with at least 500 admitted rows as the final origin (the quarter with the most rows when none reaches that) and scores the rows that start in
that quarter, the same rows in every run. The history (rows usable at the origin) is subsampled by whole tests at each fraction, N times (fraction 1 once), every rung is
refit and scored. Per fraction and rung it reports the mean history size, the Brier skill against the base rate averaged over seeds with a 90 percent bootstrap interval by
held-out test (the draws of the seeds are averaged, so the interval describes the seed-averaged skill on this held-out set), the spread across seeds, and log score and
direction accuracy where the rung has them. The figure overlays the gate sizes at both power targets on the history axis. A subsample with too few rows to fit is left out
and the report says so.

### Call 66: which selection rule is the default

Figures in this call were measured before the review fixes of call 70 and the admission guard of call 71, with the earlier unguarded selection. With the guard on, P2 is 0.0145 nats
below P1 in log score under leave-one-test-out and 0.0096 under forward chaining; the difference between the rules was not re-tested with an interval after the guard, so the default stays `loto`.

Both rules were backtested on the same nine Upworthy origins and 13,247 rows. The paired difference forward chaining minus leave-one-test-out on the P2 rung, with 90 percent
intervals from resampling tests, is: log score +0.0051 (-0.0014 to +0.0111), CRPS -0.0024 percentage points (-0.0029 to -0.0019, an improvement), Brier score -0.0004 (-0.0008 to
+0.00001), direction accuracy +0.0042. Forward chaining is worse at the three earliest origins, where its validation blocks are small, and better at four of the last six. The selection
optimizes the log score, and on the log score the two rules cannot be told apart, so the default stays `loto` (`config.P2_SELECTION_DEFAULT`). Forward chaining is the principled rule, since it
never lets a validation row use a precedent that did not exist yet, and it stays one flag away (`--p2-selection forward`). The rule for changing the default is that the better rule's
advantage on the log score must clear zero in its 90 percent interval.

Neither rule recovers P1, and P2 does not beat P1 under either. Per cell, averaged over origins, leave-one-test-out selects a weight on precedents of 0.20 (both), 0.14
(headline only) and 0.03 (image only), with lambda equal to zero at 11, 33 and 78 percent of origins; forward chaining selects more weight, not less: 0.44, 0.56 and 0.26, with lambda equal
to zero at 33, 22 and 44 percent of origins. P2 stays 0.055 nats (leave-one-test-out) and 0.050 nats (forward chaining) below P1 in log score.

Why the selection does not protect P2. At the last two origins checked by hand, the in-selection gain of the chosen setting over lambda 0 was between 0.002 and 0.027 nats per row, while the
out-of-origin loss was 0.025 to 0.11 nats at the same origins. A gain that small is inside the noise of choosing the best of 44 combinations (11 lambdas by 4 bandwidths), and the tie rule
(0.001 nats) is far below that noise. This is a hypothesis for the next session, not a result of this one: require the chosen setting to beat lambda 0 by more than the standard error of the
paired by-test difference before using it.

### Call 67: what the ablations show on Upworthy

Figures in this call were measured before the guard of call 71. With the guard on (the current ablation table in the README), the reading changes as follows: the main run is 0.0145 nats below P1
(it was 0.0547), the unguarded run (`--p2-guard off`) is 0.0536 below and a guard of one standard error is 0.0480 below; the fixed-lambda rows are unchanged; the best bandwidth in hindsight (multiplier 0.125, -0.0080) is still better than the
selected one (-0.0145), so the bandwidth choice still costs about 0.0065 nats; structured features alone, text alone and both are within 0.0004 of each other (-0.0152, -0.0148 and -0.0145).
The text below is the earlier reading.

All other rows of the ablation table are in the README; the reading is short. Every P2 variant is below P1, by 0.019 to 0.111 nats. Fixing lambda makes it monotonic: 0.2, 0.5 and 1.0 give P2 minus P1
of -0.085, -0.091 and -0.111, and lambda 0 reproduces P1 exactly. The best bandwidth in hindsight (multiplier 0.5 or 1) is better than the selected one (-0.019 against -0.055), so the selection
also overfits the bandwidth. Structured features alone give the least bad P2 (-0.044), text alone -0.054 and both -0.055: the text precedents add nothing to the structured ones. The recency kernel
selects a half-life of 90 to 135 days in the origins where it uses one and moves the P2 log score by +0.0010 under leave-one-test-out, which is nothing. The P1 pooling strength kappa barely matters (P1 log score -0.8817, -0.8803,
-0.8814 and -0.8789 for kappa 0, 5, 20 and 80), and a Normal prior in place of the Student-t is 0.076 nats worse, so the heavy tails of the effects are real.

### Call 68: what the learning curve shows

With the guard on, P2 equals P1 at every fraction (the guard holds lambda at zero in nearly every cell and origin), so the P2 rows repeat the P1 rows: a Brier skill between 0.027 and 0.032 at every history size.
The figures that follow were measured before the guard.

On Upworthy the final origin is 1 January 2015 (the latest quarter with at least 500 rows), with 1,143 held-out rows in 318 tests and between 601 and 11,997 history rows. P1 sits at a Brier skill of
about 0.03 at every history size (0.027 at 5 percent of the tests, 0.030 at all of them), so twenty times more history adds nothing measurable. P2 is below P1 at five of the five fractions
(0.014 against 0.027 at 5 percent, 0.006 against 0.030 at 100 percent). The gradient-boosted challenger improves with history (-0.28 to -0.12) and never reaches zero; `local_eb` and `text_lr` stay at
zero within their intervals. In this quarter the ladder rungs predict the reference arm at nearly every setting, so their direction accuracy is 0.573 or within 0.005 of it, the accuracy of `always_reference`. The 90 percent intervals are
bootstrap intervals over the 318 held-out tests; they do not include the noise of choosing one quarter, and a different final origin would move the levels. On ASOS the final origin is the quarter
with the most rows and holds 56 rows in 9 tests, so every interval is wide and nothing there is decidable; the curve is produced for completeness and says so.

### Call 69: the cautionary run is reproducible

`moot backtest --source upworthy --effect-scale relative --s-star realized` rebuilds the first run: `y` is the relative lift in percent and `s` its standard error (both read from
the `post_launch` block of each row), and the forecaster is given each row's realized standard error instead of the one known before launch. It is a view of the ledger made after the
snapshot id is taken, so no ledger or snapshot changes, and its report goes to `reports/ablations` under the name `--effect-scale-relative+s-star-realized`. Defaults are unchanged.
On the same 13,247 rows P0 has a Brier skill of -0.99, P1 -0.107 and P2 -0.107 (the guard holds P2 at P1 here; the unguarded run gave -0.112), and p_sig is above the event rate in all ten deciles of planned exposure. The report JSON is copied to
`paper/data/run1-relative-lift/`; the absolute-difference run with a pre-launch standard error is the released protocol.

## Calls made after the code review of the first two runs (3 Nov 2026)

### Call 70: review fixes that change what the reports say

- **Visibility of Upworthy rows.** A contrast starts when both of its arms exist: `started_at` is the later of the two `created_at` values, and the final read and
  `usable_after` are seven days after it (call 75 later made the final read test level). Before this change the horizon was keyed on the reference arm alone, and 15 admitted rows were visible before their variant
  existed. The status counts and the cells are unchanged (13,453 admitted rows); only the times moved.
- **Reliability entries age.** A cell with no outcome in the trailing window keeps its old entry and its old `as_of`; only the report-level `as_of` moves. The 14-day
  staleness trigger therefore fires for a cell that stopped receiving outcomes, in `moot join` and in the backtest replay, which call the same function. A join that
  attached no new outcomes carries the counters and refreshes the `as_of` of the cells whose window still holds outcomes, and of no others.
- **Decidability is counted in tests.** The power simulation resamples independent rows, while the contrasts of one test share a reference arm. The report and the README
  therefore headline the by-test count and print the by-row count beside it, labelled. At the same gate the two can disagree, for example 337 ASOS rows from 68 experiments.
- **Realized impressions.** See call 53: they are a proxy for the planned exposure, and the measured correlation with the absolute observed effect is a stated limitation.
- **Downloads.** The download script fetches only files matching an approved name and stops with exit code 4 when none matches. The run log separates a checksum
  verification from a download; a download time is quoted only from a clean copy with an empty data root.

### Call 71: the P2 admission guard

The ladder's rule is that a rung is used only when it beats the rung below out of sample by more than noise. Until now the P2 selection step ignored the second half of that
sentence: it scored about forty candidates (eleven values of the precedent weight lambda times four bandwidths) on the same validation rows and took the best, and the best of forty
noisy gains is biased upward. At two origins checked by hand the gain over lambda 0 inside the selection was 0.002 to 0.027 nats while the loss at the next origin was 0.025 to 0.11 nats.

The admission guard makes the rule operational. For every candidate with lambda above zero the selection computes the per-row log-score gain over lambda 0 on the validation rows
(leave-one-test-out or forward chaining, whichever is in force) and its standard error clustered by test, because contrasts of one test share a reference arm. A candidate is
admissible when its gain exceeds the tie tolerance of 0.001 nats and the gain minus the guard multiplier times the standard error is above zero. Among admissible candidates the best gain
wins and gains within the tie tolerance resolve to the smaller lambda. With no admissible candidate lambda is 0 and P2 equals P1 for that cell and origin; the bandwidth is then the one the
earlier rule would have used, which only sets the novelty threshold. A fixed `--lambda` bypasses the guard.

The multiplier is the constant `P2_GUARD_MULT`. The task asked for 1.0. On synthetic data with no precedent signal (24 seeds, 72 cell fits) one standard error still admitted a
positive lambda in 28 cells (39 percent), because the maximum over many correlated candidates clears one standard error by chance; 1.5 admitted 10 cells (14 percent) and 2.0
admitted 6 cells (8 percent), while the earlier unguarded rule used a positive lambda in 44 cells (61 percent). The requirement is that at least 90 percent of such cells stay at lambda 0, so the default is 2.0 and 1.0 stays available as `--p2-guard 1.0`. With a planted strong
text signal every cell admits a positive lambda. The report stores per cell and origin the selected lambda, the earlier rule's lambda, the gain, its standard error and whether the guard
held it at zero (`tables.p2_selection`), summarises them per cell, and `scripts/compare_guard.py` writes the guarded-against-unguarded comparison (paired by test) that the README prints.

### Call 72: imported ledgers

An imported source (any source other than the three built in) is forecast without looking at its own result. The standard error used for forecasting is the cell's median of `s sqrt(n)` over the rows visible at the origin divided by the square root of the row's planned exposure, the same rule a card uses, so a backtest and a card agree. The feature space is the cell one-hot plus the number of variants whenever no row carries headline text. Rows are keyed by experiment, variant and metric; the metric id is part of the variant id and of the row id, and the cell defaults to the metric id. Importers set the standard error from what the export carries and record in `variance_method` every assumption they made (the interval level, whether a single interval number is a half-width), because some exports do not say. Statuses use the existing vocabulary: a missing standard error is `low_exposure` with `exclusion_detail` `missing_variance`.

### Call 73: several metrics per contrast and guardrails

A ledger with two or more metrics gets a `metric` column in the score table and one report block per metric under `tables.by_metric`; the pooled `ALL` rows mix scales and the report says so. The decision value uses the primary metric only (the metric with the most scored rows unless `--primary-metric` says otherwise), because a policy that ranks tests by one metric's win probability has no meaning on another metric's lift. A single-metric source gets exactly the report it always had.

On a card, the primary metric is the cell. Each guardrail is another cell of the same source with a harm margin `delta`, and its `p_harm` is the probability that the true effect is below minus `delta`, read from the same P2 predictive as the primary metric. A guardrail has its own abstention (support, novelty, reliability, instability), evaluated on its own cell, and when it abstains the card shows its reasons and no number. The primary metric abstaining does not hide a guardrail that has evidence, and the other way round. Guardrails are part of the card id.

### Call 74: the earned weight is out of time, per version, and tied to the champion

Review of the second-opinion code found that the weight had been chosen and judged on the same rows. It is now chosen on the origins before an inner cut and judged on
the origins from the cut on. The rows with an opinion are put in time order and the cut falls between origins, at the first origin where at least half of the rows lie
before it. The grid value with the best Brier score before the cut is the candidate. It is kept only when, from the cut on, the stacked Brier score beats plain `p_sig`
by the promotion margin (relative to the constant base rate of those later rows) and at least the gate's number of later rows carry an opinion. The gate therefore counts
judged rows, so a provider needs roughly twice the rows it needed under the old rule. Rows from a single origin cannot be split and earn nothing.

A weight belongs to one provider version and to the champion it was stacked on. A new version of an agent starts at zero, and a promotion of a new champion changes `p_sig`,
so the weight lapses until it is earned again (the record is kept for the audit trail). A provider that declares no knowledge cutoff, other than the two built-ins, is
treated as unknown: every origin is possibly contaminated, the config loader refuses such a table, and a weight earned only with `--include-contaminated` is stored with
`contaminated: true`. Scores for earning are found by the current snapshot id, never by modification time. The agent rung is scored on the rows where the agent gave an
opinion, so the report adds the base rung on exactly those rows and the agent is compared with it.

### Call 75: the Upworthy horizon is test level

The first horizon rule (call 70) keyed each contrast on the later of its two arms. A review showed that this still lets a sibling row expose the shared reference arm early:
the reference arm of a test keeps accruing impressions and clicks until the test's last arm ends, so a contrast whose own variant was created early had a final read before
the reference arm's counts stopped changing. The final read and `usable_after` of every contrast are now seven days after the creation of the latest arm of the test, one instant for
all contrasts of that test. `started_at` stays per contrast (the later of its two arms), so the origin at which a row is predicted is unchanged. Single-arm tests are unchanged.
Seven days remains a modeling choice. The status counts do not change, because admission does not use time. Rows move to later `usable_after` values, so some history is
visible at fewer origins; the experiments were rerun and the README and paper numbers regenerated from the new snapshot.

### Call 76: gates count tests

The earn-weight gate and the registry promotion gate compare the number of distinct tests with the gate's n, not the number of rows. Rows of one test share their reference arm,
so they are not independent draws, and the by-test count of decidable cells is already the headline (call 70). `earn_weight` counts the distinct `test_id` of the judged
rows with an opinion (a frame without that column counts each row as a test), and `backtest_summary` stores `n_tests` beside `n`. A summary written before this change has no test
count and the promotion gate falls back to its row count, saying so in the refusal message.

### Call 77: units are checked, and bad input ends in one line

`effect_unit` is one of `absolute`, `relative`, `standardized` or `as_exported` (an export that does not state its unit). Any other value is an error, rows pooled in one
cell must share a unit within a file and across imports, and the check names the rows that differ. Pooling a relative and a standardized effect would have corrupted P0 to
P2 without a sign. A derived standard error always says in `variance_method` how it was derived and at what assumed level. Counts must be finite whole numbers no larger than
2**53. An input error (a bad value, a missing file, a conflicting row) ends in one line on standard error and exit code 2; `MOOTCOURT_DEBUG=1` shows the traceback.

## Calls made for the abstention and drift experiments (3 Nov 2026)

### Call 78: dropping a trigger, the year of a row, and the weekly replay

`moot backtest --drop-trigger NAME` (repeatable; support, novelty, reliability or instability) switches an abstention trigger off for the run. A dropped trigger is never evaluated: it adds no reason and cannot make a row
abstain, and the other triggers are computed exactly as before, so the reasons of a row are the main run's minus the dropped name. Predictions, scores and the reliability report do not depend on abstention, so only the abstention
columns, the abstention table and the non-abstained columns of the aggregate change. The report is written under `reports/ablations` with the suffix `drop-trigger-<names>` and its header records the dropped names. A trigger can
be redundant: when every row it flags is also flagged by another trigger, dropping it leaves the abstention rate unchanged.

`tables.score_by_year` groups the scored rows by the calendar year (UTC) in which the row's test started, read from the ledger's `started_at`. Each row is scored once, at the origin of the quarter it starts in, so the year is also
the year of its origin; the years partition the scored rows of every rung. Each year is scored with the same definitions, bootstrap and seed as the main aggregate on its own rows, so the table adds to the report and changes none of its
other tables. A year with a few tests has a wide interval; read the interval before the point.

`scripts/replay_weekly.py` replays an archive at weekly joins using only what was visible at each week. A week starts seven days after the last, from the first quarterly origin at which a champion can be fitted. One card is issued per
admitted row at the start of the week in which its test starts, from the champion bundle fitted at the latest quarterly origin on or before that week. At each week it first joins the outcomes whose `usable_after` has passed
(typed by the weekly join's own rule), then rewrites the reliability report by the weekly join's rule, then issues the week's cards against that report. The report is built from the forecast every card made, abstained or not, as the backtest
does, because a loop that counted only issued cards could not leave an all-abstaining start; the typed misses follow the card as issued. A week is flagged when the report written at its join marks a cell drifted: two joins in a row, each with at
least ten outcomes in the trailing eight weeks and a rolling log score more than 0.10 nats under the baseline. The replay writes `reports/replay-<source>-<snapshot>.json` with per-week counts and nothing else.


## Calls made after the round 00 red-team review (3 Nov 2026)

Four reviewers read the first paper draft and the code at commit f3c8718 and found five blocking problems and about twenty major ones in the
method's implementation (paper/reviews/round-00). Chunk L fixed every one that has a code component, or argued against it in plan-notes, and
reran every experiment. Every number of the earlier runs is superseded; the earlier reports are kept under `archive-pre-l` on the data root.

### Call 160: P0 is the empirical base-rate forecaster, and what each rung adds

The scored P0 used to be a Normal of the visible effects pushed through the significance rule, which counted the measurement noise twice
and had a Brier skill of minus 0.124 against a base rate it was not. P0 is now the forecaster the Brier skill is measured against. At each
origin and in each cell (the global rows when a cell has fewer than two) it forecasts the observed estimate from the visible history alone:
`p_sig` is the visible event rate of `y > 1.96 s`, `p_dir` (also `p_win`) the visible share of `y > 0`, the 80 and 90 percent intervals the
empirical quantiles of the visible `y`, the point estimate their mean, and the log score and CRPS those of a Normal with the visible mean
and variance of `y` (a density family used for scoring only; the intervals are empirical). Because `p_sig` equals `p_base` row by row, P0's
Brier skill is zero by construction; the report says so beside the P0 row and a test pins the identity. P0's calibration and coverage are
therefore real out-of-time checks of the base rate. The statement that each rung is a strict generalization of the one below is dropped. What
each rung adds is: P1 adds a fitted partially pooled Student-t prior that accounts for measurement error; P2 adds kernel-weighted precedents
under an admission guard. P2 nests P1 exactly at lambda zero (call 161). There is no admission guard between P0 and P1 and none is claimed:
the by-origin table of log scores is where a reader sees a quarter in which P1 was below P0.

### Call 161: the P2 predictive is a Student-t of P1's family at every lambda

At lambda above zero P2 used to return a Normal whose variance mixed the precedent variance with P1's, while P1 is a Student-t with three
degrees of freedom in every cell, so about 0.076 of the 0.085 nats P2 lost at lambda 0.2 was the change of family and the lambda ablation did
not isolate the precedents. The P2 predictive is now `t(theta_hat, scale, nu)` with `nu` the cell's own degrees of freedom from P1 and
`scale = sqrt(v (nu - 2) / nu)`, where `theta_hat` and `v` are the precedent mixture's mean and variance exactly as before. The variance of
the t is therefore `v`, lambda zero gives P1's scale and location (the predictive is P1's object, equal to the last bit), and a
lambda above zero changes the location and the scale but not the family. The selection of lambda scores every candidate, the lambda 0
baseline included, with the marginal density of `y` under that t and the row's own standard error, computed by the same scale-mixture
integral the P1 likelihood uses, so the guard compares candidates with the predictive P1 would have issued and not with a Normal stand-in.
The probability of a significant positive estimate, the dismissal walk and the instability bootstrap use the same mixture form, which agrees
with the grid computation to about 1e-3. The grid reaches 8 scales around the location, so for three degrees of freedom the variance of the
gridded t is below `v` by the mass in the far tail; P1 has the same truncation, so the two stay comparable.

Review L amended the scoring: the log score of y is the analytic marginal of this t, not the grid (call 180).

### Call 162: what a card stores, and how the loop and the replay score it

Card schema version 2. The prediction block carries the predictive itself (`family`, `df`, `location`, `scale`, the grid bounds and number of points,
and the planned standard error `s_star`), the 80 and 90 percent intervals for the true effect (what the team reads) and the 80 and 90
percent intervals for the observed estimate at `s_star` (`interval_80_y`, `interval_90_y`; the quantity the backtest's coverage is measured
against). The weekly join and the replay score an outcome with the stored predictive, rebuilt on the stored grid, so the log score of a joined
card is the backtest's log score of the same row to the last digits, and they cover with `interval_90_y`, not with the narrower interval for
the true effect (which under-covers an observed estimate by construction). A card from before schema 2 has no predictive; it is scored by the
Normal its point and interval imply and the outcome says so (`legacy_normal`). The typed miss `magnitude_miss` compares the result with the
interval for the observed estimate.

### Call 163: abstained cards are recorded by the live join

The live join used to build the reliability report from issued cards only, while the replay scored every card's hidden forecast, so in the
released loop abstention was absorbing: a stale cell abstained every card, abstained cards added no evidence and the entry never refreshed; a
drift mark could never clear. One convention now serves both paths. An abstained card keeps the forecast it withheld in a sealed `withheld`
block of its frozen file (rung, lambda, `p_sig`, point, intervals and predictive). The join scores it exactly as it scores an issued card,
flagged `abstained: true` with `scored_forecast: withheld`, and `loop.reliability_row` turns every outcome with a forecast into reliability
evidence; the replay calls the same two functions and passes nothing of its own. No renderer, no HTTP response and no tool shows the sealed
block (`card.public_json` drops it), so an abstained card still shows only P0. A card with no forecast at all (no visible row in the cell) has
nothing to score and is the only kind left out. Recovery needs outcomes: a cell that abstains for staleness recovers at the first join
that brings an outcome inside the trailing window, and a drift mark clears after ten outcomes in the window and one join that is not below
threshold (corrected in call 251).

### Call 164: the row id on the three interfaces

`moot card --row-id`, the `row_id` field of `POST /card` and the `row_id` argument of the MCP tool `get_card` carry the ledger row the card will be
joined to (`source:test_id:variant_id`). The ledger row key can be given instead as `--test-id` with `--variant-id` (or `test_id` and `variant_id`), which
compose the same id; giving both forms is an error. The tool never freezes, so it only echoes the key. The request also takes the planned exposures of the two
arms separately (`--impressions` for the reference arm and `--impressions-variant`, default equal), which the Upworthy and ASOS standard errors use, and
the reference headline (`--reference-headline`) that a pairwise feature space reads (call 167).

### Call 165: the champion-refresh rule (tightened in call 185)

A fit records the METHOD it was made with, `method_id`: a hash of the method version and the fixed hyperparameters, never of the data. A
bundle with the champion's `method_id` and a later fit time is the same method on newer data. `register_model` makes it the champion without the
challenger margin, after a no-regression check: it is refused and kept as a challenger (with the reason in the history) only when its backtest Brier
skill interval lies entirely below the champion's. A bundle with another `method_id` is a different method and stays a challenger that
needs the margin and the gate (`moot promote`). The champion changes only through these two paths and the history records which. Without the split a
method with skill near zero could never replace a champion that was merely older.

### Call 166: the card's skill line

The line prints the trailing eight-week Brier skill against the cell base rate with its 90 percent by-test bootstrap interval, the rows and the
tests in the window, the gate verdict at that many tests (read at the base rate nearest the cell's own, call 170) and the latest gated figure of the
bundle's backtest with its interval and test count. The reliability report stores the interval and the test count per cell (`brier_skill_lo`,
`brier_skill_hi`, `n_tests`, `window_weeks`), so a report from before this change prints "no interval is recorded" and a verdict that says so,
never a bare number. The precedent robustness lines say "not applicable" where the weight on precedents is zero (the closed-form `p_sig` then
does not depend on the precedents, and the instability check is switched off by construction in those cells, so its "never fires" is not an
empirical finding there) and are omitted on an abstained card.

### Call 167: the feature space reads the reference headline

A contrast is a pair, and a kernel on the variant text alone cannot represent what changed. Where the rows carry a reference headline (Upworthy),
the text part of the feature space is three blocks of 32 SVD columns from one TF-IDF and SVD fit on the distinct variant and reference headlines
together: the variant vector, the reference vector and their difference; the word-count difference, the character-count difference and the share of
words the two headlines have in common are appended after the structured features. The GBM, `local_eb` and `text_lr` read the same space; `text_lr`
uses the difference of the two TF-IDF vectors beside the variant's own. A card request without a reference headline gets the fit-set mean reference
vector. Ledgers without a reference headline keep the single-headline space and its feature hash. `--pairwise off` restores the earlier space for the
ablation. The challengers report the direction accuracy on decisive rows (`|y| > 1.96 s`) beside the all-rows figure, which is the quantity the winner
prediction literature reports.

### Call 168: the challengers are recalibrated on visible rows only

Every challenger also gets a recalibrated rung (`GBM+cal`, `local_eb+cal`, `text_lr+cal`): its `p_sig` goes through a Platt map (logistic regression on the
logit; isotonic is available) fit on the out-of-fold predictions of the rows visible at the origin against the events those rows had. The folds are
contiguous in start-time order, a row's neighbors or training rows come from the other folds only, and a fixed subsample of 3000 rows keeps the cost
bounded. Nothing from the origin's own scored rows reaches the map, which a test pins with a spy on the fit and with flipped outcomes. With fewer than five
events or non-events the map is the visible base rate, and with no signal the slope goes to zero, which is the fallback the ladder's rungs have. The report carries
the raw and the recalibrated row of each challenger; the recalibrated row carries a probability only.

### Call 169: the GBM is weighted and tuned inside the origin

The GBM is weighted by `1 / (s^2 + tau^2)` (`tau` the DerSimonian-Laird between-test spread of the visible rows) and chooses its learning rate, leaf count and
number of rounds from a small grid by weighted squared error: the earliest 80 percent of the visible rows in start-time order fit each configuration
and the latest 20 percent score every boosting round, so the stopping point never looks past a validation row. The chosen configuration is refit
on all visible rows, and the spread still comes from five contiguous out-of-fold folds. `tuned=False` restores the untuned model. Fits use one thread
(a thread pool of eight is slower on these row counts). The columns are quantized once to at most 63 levels (scikit-learn searches histogram bins by a weighted
percentile on every fit when a sample weight is given, which cost seven seconds a fit). The GBM and `text_lr` also see the cell, one 0/1 column per cell: the ladder fits each cell apart, so a
model of all cells that cannot see the cell is handicapped by construction. The first rerun showed it: on the synthetic archive (cell means 2.0, minus 1.0 and 0.5) the recalibrated
challengers sat at about minus 0.10 Brier skill, and `local_eb`, which searches within the query's cell, did not.

### Call 170: gates by test, at the base rate of the archive

The earlier gates were simulated at a base rate of 0.30 with rows resampled one by one and a 95 percent interval, while the Upworthy event rate is about
0.09 and every reported interval is a 90 percent interval that resamples tests. `moot simulate gate-power` now draws tests of 3.5 rows on average
with one forecast per test, bootstraps by test, and passes the gate when the lower end of the 90 percent interval is above zero, so the sizes are numbers of tests,
the unit the harness counts decidability in, at each `--base-rate` (default 0.09, 0.14 and 0.30). `gates.json` keeps the top level of the first base rate
(old readers still read `n_200` and `n_400`) and adds `by_base_rate` and the `interval` convention. The harness reads a group's gate at the simulated base rate
nearest to the group's own event rate (`gate_base_rate` in the aggregate) and keeps the earlier 0.30 gate as the column `decidable_by_tests_base_0.3`. The per-row `moot simulate
power` command is kept for comparison.

Review L amended the gates: the rows of a test are dependent in the simulation, with the measured correlation of each source (call 183), and the by-row `decidable` column is not computed against gates that count tests (call 180's neighbor, item 33).

### Call 171: coverage by decile of the realized over the planned standard error

The pooled coverage of 0.89 hid a gradient from 1.00 to 0.66 across deciles of the ratio of the realized to the planned standard error: the forecaster fixes the click-through
level at the cell median, and the realized standard error depends on the realized level. `tables.coverage_by_se_ratio` gives the 80 and 90 percent coverage, the event rate and
the mean `p_sig` per rung and decile of that ratio (an evaluation-time stratifier; the realized standard error is never a forecast input). A scale mixture over the cell's
reference rates, which would widen the predictive for the uncertain level, is not built: it changes the object being forecast (the planned standard error is the quantity
a team knows before launch) and the table is what lets a reader see the gradient; the abstract and the discussion must say that coverage holds on average and not within strata of the realized level.

### Call 172: the calibration null is clustered by test, and the percentile is stated with its resolution

The perfect-calibration null drew every outcome independently, while contrasts of one test share a reference arm. The null now draws contrasts of one test together: a one-factor Gaussian
copula keeps every marginal at its `p` and gives the outcomes of a test a common latent, with the within-test correlation estimated from the rows (`icc`, from the design effect, the
variance of the total residual with whole tests as units over its independent-rows value). The report records `design_effect`, `icc`, the clustered percentile (`ece_percentile`), the independent percentile for
comparison (`ece_percentile_independent`) and the ECE over ten equal-mass bins with its percentile. Five hundred null draws resolve percentiles up to 99.8, so 100 means above every draw. A bootstrap of the
observed rows would not be a null, so the clustered null is a draw from a calibrated world with the observed dependence, not a resample of the data.

Review L amended the null: its latent correlation is solved to reproduce the observed design effect (call 182).

### Call 173: decision value with intervals and budgets

Random order captures `K / n` of the total by linearity, so it is computed exactly and the 200 seeded draws are gone. Each policy row carries a 90 percent bootstrap interval that resamples whole tests within each origin (the
pooled `ALL` row resamples within every origin and pools them) for the captured fraction, the regret and the difference from random order, at budgets of 10, 25 and 50 percent of the period's tests (the 25 percent rows come first). Every
rung of the run that has a win probability is a row, the challengers included. A rung whose `p_win` is constant within a cell (P0, and P1 and P2 wherever lambda is zero) chooses by cell and then at random, so its capture
differs from random order only through between-cell differences; `constant_within_cell` and `note` say so on the row.

### Call 174: Bonferroni-adjusted bounds

Every aggregate and year row carries Bonferroni-adjusted bounds beside the percentile intervals, for the Brier skill (`adjusted_lo`, `adjusted_hi`) and for the log score (`logscore_adjusted_lo`, `logscore_adjusted_hi`), with the
family size. The bound is the estimate plus or minus the bootstrap standard error times the normal quantile of `1 - 0.05 / m`, where `m` is the number of intervals the table shows (every cell and rung for the aggregate table, every
year, cell and rung for the year table); the normal approximation is used so that the correction works for any family size with 500 draws. The per-cell and per-year intervals are descriptive; the pooled interval is the pre-registered claim.

Review L amended the family: the intervals actually reported (call 186).

### Call 175: the counts of tests

The header gives the tests in the ledger (every distinct test id of the source), the tests admitted (at least one admitted contrast) and the tests scored (at least one contrast scored by the primary rung), and says why they differ: the first
quarters before the first origin with enough visible rows to fit are history only, and a test whose contrasts all fall there is not scored.

### Call 176: guard-off ablation names

The feature, bandwidth, selection, recency and pairwise ablations run twice, with the guard on and with `--p2-guard off`; a run with the guard off is named after its ablation and `p2-guard-off`, for example
`features-text+p2-guard-off`, and its header records the guard setting (`p2_guard` is the multiplier, or `off`). Fixed-lambda runs bypass the guard by construction and are not repeated.

### Call 177: the positive control

The synthetic archive with no text signal shows that the guard holds lambda at zero when there is nothing to learn. The positive control plants a text signal of 1.0 percent lift between headlines with and without a signal word (0.33 to 0.67 prior standard
deviations in the three default cells, which is the order of the text effects the Upworthy split-half fits suggest) and runs the whole protocol on it with `moot simulate ledger --text-effect 1.0` and `moot backtest`; the report shows
whether the guard admits lambda above zero and whether P2 beats P1 where the signal is planted. The detectable strength at the sizes of the Upworthy cells is read from the paper-extras table of admission rates by strength.

### Call 178: admission and the exposure proxy

The minimum-clicks rule (10 clicks in each arm) is decided on realized clicks, an outcome a launching team cannot know, so it conditions the scored set on a post-launch quantity and trims both tails of the effect distribution. `moot backtest --admission prelaunch`
admits on exposure only: every `low_clicks` contrast with a finite estimate and standard error is scored, as an ablation next to the main run (the main run keeps the ledger's statuses). The correlation of the log planned exposure with the absolute
standardized effect is computed for every source in the paper-extras report, so the ASOS value (where the proxy is the user count at the final checkpoint of a run whose length varies) stands beside the Upworthy one, with the correlation of the log run length where the rows record it.

### Call 179: findings answered without a code change

The findings of round 00 that have no code component or are answered by a stated reason are listed in `.claude/fleet/plan-notes.md` (calls 160 to 179 and the finding-to-test map). The ones argued against here: a scale mixture for the
uncertain click-through level (call 171); extending the grid of degrees of freedom below three (the pooling of the scale needs `nu` above two and the fit on the boundary is reported, not hidden); seeding the reliability report with the join clock
(a cold-start product item, listed for the lead); the sensitivity that defines the significant-positive event on the planned standard error as well (R5; built after the review of chunk L as a scoring sensitivity, call 190; the base rate of the planned event is redefined, the floor and the history of the challengers are not); the Brier floor and the direction ceiling, which replace the t prior by the Normal with the same standard deviation before computing the posterior (a stated approximation, not changed); and the novelty rate on held-out text (the backtest's novelty trigger already queries rows that did not build the index, so its 2.9 percent is the held-out rate).


## Calls made after the review of chunk L (3 Nov 2026)

A fresh review of chunk L (REV-L-001 to REV-L-028) found two high and six medium problems. Chunk N fixed them and reran every experiment (run4).

### Call 180: the log score of y is the analytic t marginal, everywhere

Call 161 says the lambda selection, P1's likelihood and the backtest score the same object. They did not: the backtest, the card, the join and the replay scored y on
the GRID, which drops every bit of t mass beyond its edge and then scores a far y with the Gaussian decay of the edge, while the selection and the P1 likelihood use the
untruncated marginal. At three degrees of freedom the gap was 0.025 nats on Upworthy and 0.099 on ASOS, several times the P2 minus P1 difference and a quarter of the 0.10
nat drift margin; P0, an untruncated Normal, was not subject to it. `Predictive.logscore` now evaluates `theta + Normal(0, s*^2)` with `theta ~ t(location, scale, df)`
from the stored spec by the scale-mixture integral of `marginal_logpdf_rows` (the Normal when `df` is None), so one function serves the backtest, the card, the join,
the replay and the drift flag, and a test asserts it equals `marginal_logpdf_rows` on random rows including rows far beyond the old grid edge. The grid still serves
the intervals, `p_sig`, `p_win` and the CRPS, which depend on the mass near the bulk. A predictive without a spec keeps its exact grid mixture. Every number of run3
that is a log score of P1, P2, a challenger or the drift flag moved; run4 replaces them.

### Call 181: outcome files without a test id

The skill interval of a cell resamples tests. Outcomes written before test ids were stored, or whose row had none, are left out of the resampling; `n_tests` counts only
the outcomes that have an id, and is None when none has one, so the card says "no interval is recorded" instead of crashing the join or printing "0 tests".

### Call 182: the clustered null reproduces the observed design effect

Thresholding a latent Gaussian at `Phi^-1(p)` attenuates its correlation sharply at a low `p`; using the observed binary correlation as the latent one gave null draws with a
design effect of 1.14 against 1.39 in the data. The latent correlation is now solved (`latent_rho_for_design_effect`, bisection on the design effect of 60 null draws with
common random numbers) so the null draws reproduce the observed design effect, whatever the spread of `p`; the aggregate reports it as `latent_rho` beside the binary `icc`.
The design effect is measured on residuals that include the miscalibration under test, which raises it a little with no clustering and widens the null: the clustered
percentile is therefore conservative (it leans toward not rejecting), and a rejection under it is the stronger statement. The independent percentile is reported beside it.

### Call 183: the gate simulation has dependence within a test

Rows of one test shared a forecast but their outcomes were independent given it, so the simulated design effect was 1 and power at a given number of tests was overstated
(0.94 against 0.77 at 175 tests, base rate 0.09, skill 0.10). The simulation now draws the rows of a test with a latent Gaussian factor whose correlation is chosen so that the
binary correlation of two events of a test equals the source's measured value (`latent_rho_for_icc`), at the source's rows per test: Upworthy 3.5 rows and binary correlation
0.13 at base rate 0.09; ASOS 5 rows and 0.67 at 0.14; the Upworthy values at 0.30, where no archive exists. The values are measured on the backtests (design effect 1.4 on
Upworthy, 3.8 on ASOS) and are in `simulate.SOURCE_DEPENDENCE`; `gates.json` records the values each entry used. The gates are larger than run3's.

### Call 184: the leakage spies cover every challenger

`_audit_fits` wraps the construction of `GBMChallenger`, `LocalEB` and `TextLR` as it wraps the fits of the predictors, so a factory that hands one a row that is not yet usable raises
`LeakageError`. The recalibration spy runs for all three challengers, and the outcome-flip check flips the outcomes of the last quarter's rows before `rolling_origin` and asserts
that the recalibrated probabilities of every origin are unchanged.

### Call 185: the champion refresh needs strictly newer data and a backtest

A same-method fit is a refresh only when the data it saw (`data_through`, the latest result in its fit set) is strictly newer than the champion's; the fit time only breaks a tie
between equal data, and unknown recency is not newer (a refit of an old snapshot has a new fit time and must not take the champion back). A same-method fit with no backtest summary
is held as the challenger and marked pending; `attach_summary` decides it when the summary arrives (refresh, or `refresh_refused`). Every route to the challenger writes its reason in
the history (a different method, older data, the same data and not later, unknown recency, pending, clearly worse).

### Call 186: the Bonferroni family

The family is the number of intervals the table reports: one per row with a Brier skill interval of positive width and one per row with a log score interval. Rows without an interval
(the direction baselines) and P0's zero-width skill interval are not counted. The year table is one family over every year, cell and rung.

### Call 187: the lows

The planned exposure is bounded (at most 1e12; a larger value is a one-line error on the command, 422 on the service). The MCP tool turns a refusal into its one-line message. The
simulator request carries the variant arm's exposure. Without a reference headline the pair features are the fit-set means, as the reference vector is. The learning curve runs on
the admission it records. A row id must start with the card's source and carry no control character. P0's variance is floored at the median squared standard error of the visible
rows. A query whose kernel underflows to exactly zero for every precedent gets P1's predictive (an empty state with a weight of zero) because the fit-time validation never saw such
a query; a query whose peak is merely tiny keeps the relative-kernel path. `method_id` covers the kind and size of the feature space, the top-M and the half-lives. The GBM's
calibration set is the same fixed subsample of 3,000 rows as the other challengers'. The robustness count is relative to the weight the state started with. A guardrail margin must be finite. Review nit REV-L-024: the far-query change
is exact to rounding (4e-16), not bit-identical.

### Call 188: the baseline of the join is the card's own P0

The card stores P0's mean and variance of y beside its probability, and the join's baseline log score is that Normal, so the drift flag compares the model with a baseline that has
the information the model had (the replay used a P0 fit on the whole current ledger, up to twelve weeks ahead of the bundle). A card without them falls back to the refit.

### Call 189: discrimination is reported apart from skill

The aggregate table carries, per cell and rung, the AUC of `p_sig` for the significant-positive event and of the direction probability for `y > 0` (`auc_event`, `auc_direction`, each with a 90
percent interval from the same by-test resamples as the other columns), and the Murphy resolution term of the Brier score (`resolution_event`, `resolution_direction`, with intervals). The
resolution is computed over ten equal-mass bins of the forecast (the bins the equal-mass ECE uses): the bin-weighted mean of the squared difference between the bin's observed frequency and the
overall event rate. It is zero for a forecast whose bins all show the base rate, however spread the forecast is, so it measures separation and not sharpness. (An earlier version of this call
reported the spread of the forecast around the base rate under the name resolution; that quantity is sharpness plus miscalibration, put GBM first while its skill was negative, and was replaced in
the review of chunk N, REV-N-001.) The estimate is biased upward by about `(10 - 1) / N * rate * (1 - rate)` from the sampling noise of the bin frequencies (for independent rows; larger by about the design effect when the rows of a test are correlated, as on the archives), and a percentile interval of a biased
statistic can leave the estimate near its lower end; read the column as a ranking of rungs on the same rows, not as an absolute amount. The AUC is the rank statistic with ties counting one half
and is None where the group has only one class. Skill (Brier against the base rate) mixes discrimination with calibration and with the base rate; an AUC above 0.5 or a resolution above what a
noise forecast gives shows that a rung ranks rows better than chance when its skill is zero or negative. P0's `p_sig` is constant within a cell and origin, so its AUC and resolution measure only
the movement of the base rate across cells and origins.

### Call 190: the event defined on the planned standard error is a scoring sensitivity

The headline event is `y > z s` with the realized standard error `s`, the quantity an experimenter's own significance test uses. The forecast is made before launch from the planned
standard error `s_star`, so a row whose realized standard error differs from the plan is scored against an event the forecast did not describe. The sensitivity scores the same forecast
against `y > z s_star` (`event_planned`, `brier_planned`, `brier_base_planned`; aggregate columns `event_rate_planned`, `p_sig_mean`, `brier_planned`, `brier_base_planned`,
`brier_skill_planned` with its interval). The base rate for this event is the visible share of rows of the cell with `y > z s_star`, each visible row's `s_star` computed from its planned
exposure as for scored rows; P0's forecast for this event is that base rate, so its skill is zero by construction here as well. The challengers were trained on the realized event and are
scored against the planned one unchanged; the sensitivity changes the scoring, not any fit. The headline stays on the realized standard error because it is the event the
user acts on and the one every earlier number used; the sensitivity is a table beside it (report group "Sensitivity of the event definition"). On ASOS the planned and realized standard error
coincide in this archive, so the two events agree row by row.

### Call 191: the guard pairs are a table

`scripts/paper_extras.py` writes `guard_pairs`: for every (origin, cell) pair of the main run in which the guard admitted a positive precedent weight, the in-selection gain (mean per-row log
score gain over lambda 0 on the leave-one-test-out validation rows, nats), its standard error, the chosen and the unguarded lambda, the rows and tests scored in the pair and the realized
out-of-time P2 minus P1 log score on them, then the pooled realized difference over the admitted pairs with a 90 percent interval that resamples tests. The claim that in-selection gains
do not transfer out of time is a column of this table and a pooled line, not a sentence.

### Call 192: the positive control reaches the per-cell size of the cell it is used on

The guard works per cell, and the synthetic generator spreads tests over three cells, so a ledger of `n` tests with two variants has about `2n / 3` rows in each cell. The sensitivity of the guard
to a planted text effect adds a ledger of 11,100 tests (about 7,400 rows in each cell, the size of Upworthy's headline-only cell) beside 300 and 1,000, so the paper can state the guard's power at the
size of the cell the guard works in. (The first version added 3,700 tests, which is 2,440 rows per cell: a third of the size it claimed, REV-N-002.) At that size the guard admits a weight in 39 percent of cells with no planted signal; call 198 examines why.

### Call 193: review of chunk N

A registry written before `data_through` existed has none for its champion; `decide_refresh` is then given the value derived from the champion bundle's fit cutoff, and the history logs a `data_through_derived`
event, so a same-method refit on newer data is a refresh and not a permanent challenger (REV-N-003). `moot fit` says a pending refresh is waiting for `moot backtest`, which decides it (REV-N-004). The P2
neighbor search returns P1's predictive when the kernel peak is below the float32 range the fit-time validation used, not only when it is exactly zero (REV-N-005). A missing exposure in a pairwise feature space is
filled with the exposure column's mean (REV-N-006); `list_precedents` takes an optional exposure. `moot init` writes quick gates by test at the 90 percent level with the rows per test and within-test correlation
of base rate 0.30 (`SOURCE_DEPENDENCE`), and `gate_verdict` compares the row count, not the test count, with a per-row gates file (REV-N-007).

### Call 198: why the guard admitted weights on data with no planted signal as the cells grew

The guard admits a weight when the candidate's in-selection gain over lambda 0 exceeds the tie tolerance and two standard errors. On synthetic ledgers with no planted text effect (12 seeds, three cells each,
36 cells per size) the run4 share of cells that admitted a weight was 0.03 at 300 and at 1,000 tests, 0.67 at 3,700 and 0.39 at 11,100, and it swung from 0.03 to 0.92 with the fit set at one size (first 85, 90,
95 and 100 percent of the rows: 0.03, 0.42, 0.00, 0.67). Two earlier readings of this are withdrawn: a fixed selection bias that passes a growing significance test, and structure of the generator that the
precedents capture (the guard's power). The cause is in P1, not in P2 and not in the generator (review N2, REV-N2-001 and 003).

The mechanism. P1 adds half of the shrunken deviation of the latest period (the most recent quarter with at least 30 rows) to every cell's prior mean. A synthetic ledger ends on a fixed date, so its latest quarter
is a tail of the next one: 58 to 70 rows at 3,700 tests (the week after the ledger's end), 176 to 216 at 11,100, 216 to 252 at 1,000. The tail's mean is noise, mixed over the cells, and it moves every cell's mu by up
to 0.29 percent lift away from the cell's own fit. P2, which weights precedents of the same cell, undoes that error, so its in-selection gain over lambda 0 is real out of sample against this P1 and the guard admits.
The size of the tail explains the size pattern and the fit-fraction swing. The control in `guard_period_control` (synthetic paper extras, table `guard-period-control.tex`) at planted lift zero, 12 seeds, 36 cells per size:

| tests | P1 period level | mean gain | mean s.e. | share admitted | rows in the level |
|---|---|---|---|---|---|
| 3,700 | old rule | 0.00274 | 0.00085 | 0.67 | 62 |
| 3,700 | old rule, every period set to the global fit | 0.00010 | 0.00019 | 0.00 | none |
| 3,700 | new rule (call 199) | 0.00020 | 0.00027 | 0.06 | 799 |
| 11,100 | old rule | 0.00121 | 0.00059 | 0.39 | 183 |
| 11,100 | old rule, every period set to the global fit | 0.00012 | 0.00021 | 0.00 | none |
| 11,100 | new rule (call 199) | 0.00024 | 0.00030 | 0.00 | 2,441 |

With the period deviation removed, or with the level taken from the last complete period, the gains fall to 0.0001 to 0.0002 nats and the share admitted at lift zero is 0.00 to 0.06. Under the new rule the share
admitted at lift zero is 0.03, 0.03, 0.06 and 0.00 at 300, 1,000, 3,700 and 11,100 tests, and over the fit fractions at 3,700 tests 0.06, 0.06, 0.03 and 0.06 (random 85 percent: 0.00): the instability is gone.

What the held-out diagnostics show after the correction (`guard_held_out_gain`, a random 15 percent of the tests held out, never rows): the in-selection gain of the best positive-weight candidate minus the held-out
gain of the same candidate (the bias of the selection) is 0.00629 nats over all 36 cells at 300 tests, 0.00277 at 1,000, 0.00036 at 3,700 and 0.00016 at 11,100, with held-out standard errors of the candidate
gain of 0.0028, 0.0009, 0.0002 and 0.0001. The selection bias is large in small cells and negligible in large ones, and the gain of the weight the guard chose is held-out zero where it chose none. So the
guard behaves as built: it holds the weight at zero when nothing transfers, and it admitted weights before the rule only because P1 was wrong. The first positive-control row (planted lift zero) is a share of cells
admitted with no text signal and now reads near the 0.03 of the small sizes at every size. Remedies named in review N (a held-out split for the gain, a size-aware threshold) are not needed for this and stay future work.
The first version of `guard_held_out_gain` compared the best candidate's in-selection gain with a held-out gain fixed at zero wherever the guard held, which is not a bias estimate; it is replaced.

### Call 199: the period level comes from the last complete period

`P1Predictor.fit(rows, data_end=None)` takes the instant up to which the fit's data reach: the origin of a backtest fit, the `as_of` of a bundle, otherwise the newest `usable_after` among the rows. A calendar quarter
whose last day is after the calendar day of that instant is incomplete (a quarter whose last day is the data end's day is kept): its rows still enter the global and the cell fits, but it sets no period level and a request for it (a card at a date inside it) takes the
level of the last complete period. `MIN_PERIOD_ROWS` (30) stays as the second condition. If no period is complete the period deviation is zero (the global fit). Why: a fit made a few days into a quarter otherwise
forecasts every cell with the noise of those few days, which no cell can correct and which the guard then reads as a gain for the precedents (call 198).

Effect. At the quarterly origins of the backtest the data end is the origin, which is a quarter start, so the latest visible quarter is complete and the parameters are those of the old rule to the last digit (pinned in a
test); all three main backtests were rerun and every score is identical to run4 (only the model id, which depends on the fitted bundle, differs, together with two reporting corrections that run4 had not applied: P0's planned-event mean in the Upworthy report, and the 288 resolution values of the ASOS `by_metric` blocks, which still held the forecast spread). Fits at other dates change: the bundles of
`moot fit` (the card path), the synthetic diagnostics and any fit made inside a quarter. The weekly replays were rerun and their numbers are identical. A bundle fitted before this rule keeps its stored period table until refit.
An empirical-Bayes period variance (a period deviation weighted by its own estimated variance instead of a row count threshold) is the alternative; it is not built here.

The data end of a fit is its clock. A backtest fit passes its origin; `moot fit` (the card path) passes the fit clock (`fit_command(..., now=)`, default the wall clock; call 223 of the platform log), and only rows usable at the clock enter the fit; `fit_bundle` without an `as_of` (a library call) falls back to the
newest `usable_after` of the rows. What this means: an archive fit with today's clock sees every quarter of a 2015 or 2021 ledger as complete, so the trailing quarter (Upworthy 2015Q2, 321 rows; ASOS 2021Q1, 40 rows) sets its level as it did before the rule, and the released bundles of run 6 take the period
level the old rule gave (they are refit anyway under the forward-chaining default). A live fit with the clock at now has an incomplete trailing quarter and drops it from the level, which is what the rule is for. Called without a clock, `fit_bundle` on the archives drops 2015Q2 (321 rows) and 2021Q1 (40 rows) from the level and takes 2015Q1's (1,135 rows) and 2020Q4's;
those rows enter the global and cell fits either way (13,453 of 13,453 and 381 of 381 rows). The rule is calendar-level: a quarter is kept when its last day is on or before the data end's day, so a data end on 30 June keeps the second quarter and 29 June drops it.
The empirical-Bayes period variance would weight a
thin or noisy period instead of dropping it; it is future work.

### Call 200: Bonferroni-adjusted bounds for the decision-value table (round 01, R5)

The decision-value table reported three bootstrap intervals per row (captured fraction, regret, difference from random order) and no adjusted bounds, although the paper promises adjusted bounds for every table. Each row now
carries `captured_fraction_adjusted_lo/hi`, `regret_adjusted_lo/hi` and `diff_random_adjusted_lo/hi` and the `family_size` used, computed as in call 174: the estimate plus or minus the bootstrap standard error (the sample
standard deviation of the resampled statistic) times the normal quantile of `1 - 0.05 / m`.

The family. The claim this table makes is which rung ranks tests better than random order, and the pooled (`ALL` origin) rows carry it; the per-origin rows are descriptive. The family is therefore the number `m` of rungs
whose pooled `p_win` row has a difference-from-random interval of positive width at the row's budget (six on Upworthy: P0, P1, P2, GBM, local_eb, text_lr; the recalibrated rungs have no `p_win`), and every row at that
budget carries that `m`. The three intervals of a row are views of one comparison and share it. This is narrower than the aggregate table's family (call 174 counts every cell and rung, descriptive rows included): counting
every interval of this table (about 600) would adjust a claim by the multiplicity of its descriptive rows. Both are recorded in `plan-notes.md` with the verdicts under each; the stored rule is the pooled one.

### Call 201: the decision value is read against the arm-count-matched random order (round 01, R1 blocking 1)

A test's value is the largest positive observed lift among its contrasts and its score is the largest `p_win` among them, so both rise with the number of contrasts, a field a launching team knows before the test. On Upworthy
the mean value runs 0.096 for tests with one contrast, 0.226 with two and 0.390 with three, and a policy that ranks tests by their number of contrasts alone captures 0.3026 of the positive lift at a quarter of the tests,
0.0524 (0.040 to 0.064) over random order and more than the text classifier's 0.3005. Random order is therefore the wrong baseline for the question "does a rung rank tests by something beyond how many arms they have".

The table now carries two more policies and one more difference. `arm_count` ranks tests by their number of contrasts (distinct scored rows of the test at the origin) and reads no forecast; a tie at the cut is resolved by its
expected value, as for the rungs. `random_matched` (one row per rung) is a random order matched to the arm-count composition of the set that rung chooses: within each arm-count stratum a random choice of the same number of tests has
the stratum's mean value per test, so the baseline is the sum over the chosen tests of the stratum mean (a tied test enters with the weight of its chance of being chosen), exact, no draws. Each `p_win` row carries `matched_fraction`,
`diff_matched` (the captured fraction minus the matched fraction) with `diff_matched_lo/hi` from the same by-test resamples within origin as the other intervals, and `diff_matched_adjusted_lo/hi` under the family of call 200.

Reading. The baseline every rung must beat is the arm-count-matched random order, and H5 (a rung with a probability that varies within a cell captures more than chance) is read against `diff_matched`, not `diff_random`. The check
against the review's own recomputation (500 resamples, a different seed, ties resolved by arbitrary order in theirs and by expectation here): arm_count captures 0.3026 (the same), 0.0524 over random order (0.040 to 0.064, theirs 0.041 to 0.064);
text_lr plus 0.0395 (0.0217 to 0.0541; theirs 0.0395, 0.0215 to 0.0534); local_eb plus 0.0150 (-0.0014 to 0.0312; theirs 0.0150); GBM plus 0.0276 (0.0154 to 0.0397; theirs 0.0289); P2 plus 0.0085 (-0.0030 to 0.0201; theirs 0.0092); P1 minus 0.0043
(theirs minus 0.0045). At the 25 percent budget only the text classifier and the boosted model clear zero, adjusted as well; the precedent rung and the local comparison set do not, adjusted or not.

### Call 202: call 66 re-applied to the run5 numbers (round 01, R3 major 1)

Call 66 chose leave-one-test-out (`loto`) as the default before the guard of call 71 existed and said the choice would be revisited with an interval after the guard. Its rule: the better rule's advantage on the log score must clear zero in its
90 percent interval (resampling tests). Re-applied as written to the run5 reports, P2 rung, the same 13,247 scored rows at the same nine origins, by-test bootstrap with 2,000 resamples, seed 0, forward chaining minus leave-one-test-out:

| setting | pooled | headline_only | image_only | both |
|---|---|---|---|---|
| guard 2.0 (the default) | +0.0044 (0.0030, 0.0057) | +0.0083 (0.0061, 0.0104) | -0.0006 (-0.0019, 0.0007) | 0.0000 |
| guard off | +0.0024 (0.0007, 0.0041) | +0.0043 (0.0017, 0.0069) | +0.0001 | +0.0001 |

The pooled advantage of forward chaining clears zero in both settings (call 66 measured +0.0051 with an interval from -0.0014 to +0.0111 before the guard and could not tell the rules apart). Per origin the difference is -0.0228 at October 2013 (the earliest origin
with enough validation blocks), -0.0007 at January 2014 and +0.0090, +0.0148, +0.0083, +0.0025, +0.0023 from April 2014 on: forward chaining is worse where its validation blocks are small and better afterwards, as call 66 observed. P2 scores -0.8562 under forward chaining
and -0.8606 under leave-one-test-out against P1's -0.8566. The pooled P2 minus P1 is +0.0004 (-0.0003, 0.0012) under forward chaining and -0.0040 (-0.0052, -0.0027) under leave-one-test-out, in the headline cell +0.0008 (-0.0006, 0.0022) against -0.0075 (-0.0095, -0.0055).

Outcome. The rule of call 66, applied as written, selects forward chaining as the default: its advantage clears zero in its 90 percent interval with the guard on and with it off. Forward chaining is also the selection that matches a deployment in which a new test has
only older tests as precedents. `config.P2_SELECTION_DEFAULT` is not changed in this call; changing it moves the main backtests, the card path, the replays and every number downstream and is a decision about the rerun. The headline "the precedent rung loses 0.004 nats" is a property of the
leave-one-test-out default; under forward chaining the precedent rung is level with P1 (+0.0004).

### Call 203: discrimination within strata (round 01, R3 major 3)

The pooled AUC and Murphy resolution of call 189 credit every rung with the movement of the base rate between cells and between origins, which P0 has by construction (its pooled AUC on Upworthy is 0.5475 and its pooled resolution 0.00050 above P1's 0.00027). The aggregate
rows now also carry, for the event and the direction, `auc_*_within` and `resolution_*_within` with their `_lo` and `_hi`. A stratum is an (origin, cell) pair; inside a group of cell ALL the strata are the origin and cell pairs, inside a single cell the strata are its origins. Each stratum
is scored on its own: the AUC (ties one half) when it has both classes, and the Murphy resolution over ten equal-mass bins of the forecast in that stratum (a constant forecast has one bin, so resolution zero and AUC one half). The group's figure is the mean over strata weighted by the
rows of the stratum. The interval resamples tests (the same draws as the other statistics of the group), with the stratum weights recomputed in each draw. The within-stratum resolution keeps the upward bias of call 189 in every stratum, so read it as a ranking of rungs on the same rows.

Check against the review's recomputation on the Upworthy main report, within (origin, cell), AUC for the event: P0 0.500, P1 0.5301 (0.5121, 0.5474), P2 0.5468, GBM 0.5477, local_eb 0.538, text_lr 0.5645 (0.5465, 0.5820), against the review's 0.500, 0.530, 0.547 and 0.5645. Within the origins of the
headline-only cell: P1 0.5018 (0.4774, 0.5254), P2 0.5313, GBM 0.5293, local_eb 0.5633, text_lr 0.5768 (0.5548, 0.5974). The prior's pooled 0.553 is the planned standard error plus the movement of the base rate; inside the largest cell it ranks at chance and the text models at 0.56 to 0.58.

### Call 204: the learning curve is scored against the full-history base rate (round 01, R1 blocking 2, R3)

The learning curve of call 65 measured the Brier skill against the base rate re-estimated from each subsample, so the baseline got worse as the history got thinner (implied base Brier 0.0595 at 123 rows against 0.0555 on the full history) and the curve read backwards. Each point is now scored against the P0 Brier score of the
FULL history at the final origin on the same held-out rows (the reference the main table uses), the same for every point: `skill` with `skill_lo`, `skill_hi` and `skill_seed_sd`. The subsample-P0 version is kept as `skill_own_base` (with `_lo`, `_hi`, `_seed_sd`), and `base_brier_full` and `base_brier_own` give the two
baselines. The report also gives, per point, `n_history_tests` (tests in the fitted history) and `n_scored_tests` (the held-out tests, 318 at every point on Upworthy and 9 on ASOS): the gate sizes count scored tests, so every Upworthy point is above both gates (175 and 250) whatever its history, and the gates cannot be read against the history size.
The reports were rerun (the held-out rows' full-history P0 is not stored per subsample), with 500 bootstrap resamples (they used 200); the `skill_own_base` column reproduces the earlier file's `skill` to the last digit.

Result, Upworthy P1 against the full-history base rate at 123, 244, 605, 1,204, 2,991, 6,005 and 11,997 history rows: 0.0007, 0.0191, 0.0229, 0.0273, 0.0286, 0.0288, 0.0295 (rising with the history, 0.0679 to 0.0295 against its own base); P2 0.0006, 0.0188, 0.0228, 0.0275, 0.0280, 0.0284, 0.0311; the
local comparison set -0.0575, -0.0014, 0.0152, 0.0119, 0.0188, 0.0251, 0.0366 (above P1 only at the full history); the boosted model -0.2017 to -0.0685; the text classifier -0.0243 to 0.0104; P0 against the full-history P0 -0.0851 at 123 rows to 0 at the full history. Challengers do not keep a pooled order along the curve.

### Call 205: report columns from the round 01 response (T-074)

Year table (`tables.score_by_year`) and aggregate rows gain `event_rate`: the share of scored rows whose estimate was significant and positive (`y > z s`) in the group (with the group's row count `n` beside it). On Upworthy it falls from 0.1175 (2013, 3,150 rows) to 0.0871 (2014, 8,684) and 0.0566 (2015, 1,413).

The aggregate table gains the all-rows paired log score difference of every rung from P1 on the same rows: `logscore_vs_p1` (nats per row; negative means the rung scores below P1) with a 90 percent by-test interval (`_lo`, `_hi`), Bonferroni-adjusted bounds under the family of call 186 (`logscore_vs_p1_adjusted_lo/hi`) and the number of paired rows
(`n_paired`). P1 against itself is zero; a rung without a density log score (the challengers) has none. On Upworthy P2 minus P1 is -0.0040 (-0.0054, -0.0026) pooled and P0 minus P1 is -0.1493. This is the honest headline comparison between two rungs because it uses the same rows, unlike the difference of two group means.

The gate read per group records the group's own dependence. The nearest simulated gate assumes a rows per test and a within-test correlation (`gate_assumed_rows_per_test`, `gate_assumed_icc`, read from the gate entry); the group has its own, measured on its rows (`gate_cell_rows_per_test`, and `gate_cell_icc`, the design effect with the group's base rate as the
forecast, as `simulate.ledger_dependence` measures them). `gate_cell_n_200` and `gate_cell_n_400` scale the nearest sizes to first order by the information a test carries, `r / (1 + (r - 1) icc)` for `r` rows per test, relative to the assumed values, and `decidable_by_tests_cell` is the verdict at those sizes. A simulation per cell is too slow for the backtest path, so this is an approximation, exact
when the assumed and the group's dependence agree; `decidable_by_tests` stays the verdict at the nearest simulated row. On Upworthy the smallest cell has 2.09 rows per test and a correlation of 0.40, against the 3.5 and 0.13 assumed at base rate 0.09.

### Call 206: forward chaining is the default selection (call 66 applied, run 6)

Call 66 set the rule for the default selection: the better rule's advantage on the log score must clear zero in its 90 percent interval. Re-applied to the run 5 numbers after the guard (call 202) it selects forward chaining: pooled P2, forward minus leave-one-test-out +0.0044 (0.0030, 0.0057) with the guard and +0.0024 (0.0007, 0.0041) without, +0.0083 in the headline cell.
The rule was stated before the data, so the default changes: `config.P2_SELECTION_DEFAULT` is `forward`. Per origin the picture is not uniform and the paper shows it: forward chaining is worse at October 2013 (-0.0228, its validation blocks are smallest), level in January 2014 (-0.0007) and better from April 2014 (+0.0090, +0.0148, +0.0083, +0.0025, +0.0023). Under it P2 is level with P1 (+0.0004, -0.0003 to 0.0012 pooled),
where under leave-one-test-out it was 0.0040 below. Leave-one-test-out remains available (`--p2-selection loto`) and becomes the ablation counterfactual `p2selection_loto` (the ablation set runs it, with the guard on and off, in place of the forward variant). The card path (`moot fit`), the replays and the bundles follow the default with no special casing, so run 6 repeats every number downstream of P2.

## Round 01 calls of the platform and positive-control builders (merged by the lead)

Calls 207 to 210 and 220 to 229 are the platform fixes of round 01 (reviewer R2's findings and reviewer R6's command-line items); calls 230 to 247 are the positive control, the admitted pairs by row, the small items of the round 01 response, the packaging items of reviewer R4 and the release packaging (arXiv source, citation file, release notes). Calls 211 to 219 are unassigned.

### Call 207: gate-power says what it assumes, measures it from the ledger on request, and reports progress (R6, minor)

`moot simulate gate-power --base-rate 0.203` took 751 s in silence and sized the gates with a public archive's rows per test (5.0) and
within-test correlation (0.67), the measured values of the archive nearest the rate, which the page did not say. The command now prints,
before it runs, the assumptions it uses at every base rate and where they come from: "given on the command line", "measured on the <source>
ledger" (`--source NAME` reads the ledger and measures the mean admitted rows per test, the event rate, which becomes the base rate unless
one is given, and the within-test correlation of the event by the design-effect rule of the harness, `simulate.ledger_dependence`), or
"the public archive nearest this base rate" with the hint to pass `--source`; the gates file records the source (`dependence_source`).
Progress: a heartbeat line on standard error after `--progress-after` seconds (default 10) and every ten seconds while the simulation runs,
naming the stage, and one line per sized point once past the delay. `moot init` (the quick gates) and `moot backtest` (origins) take the
same `--progress-after` and print the same heartbeat; the backtest's timing line now also gives the whole run. `--no-table` skips the power
table, which is the slow part and is not needed for the sizes. Tests: `test_ledger_dependence_measures_rows_per_test_base_rate_and_icc`,
`test_gate_power_prints_its_assumptions_their_source_and_progress`, `test_the_heartbeat_prints_a_progress_line_after_the_delay`,
`test_init_and_backtest_take_a_progress_delay`.

### Call 208: `moot reliability` (R6, minor, question 1)

Tutorial 4 needed a Python snippet to read the weekly report. `moot reliability --source NAME [--reports-dir] [--json]` prints the
report's date and one line per cell (as of, rows, tests, Brier skill with its interval, rolling log score, the base rate's, consecutive
joins below, drifted), the same fields the snippet printed, or the JSON; a missing report says which commands write one. Test:
`test_moot_reliability_prints_the_weekly_report`.

### Call 209: a value that rounds to zero prints without a sign (builder-m item a)

`Point estimate: -0.00` read as a defect. The three number formatters (`card._num`, `benchmark._num`, `report._fmt`) strip the sign from
a formatted value that is zero at the printed precision; a value that rounds away from zero keeps it. Test: `test_a_value_that_rounds_to_zero_prints_without_a_sign`.

### Call 210: the report document gives the decidable verdict in the unit of its gates (builder-m item c)

The backtest report's `decidable` and `decidable_research` columns read "not computed: the gates count tests" on every row, because
`harness_stats.aggregate_scores` refuses to compare a row count with gates sized in tests (review N pins that contract, and it stands).
`report.build_document` now fills the two columns of every aggregate table (the pooled one and each metric's) with the verdict in the gates'
own unit: by tests when the gates count tests (the same as `decidable_by_tests`), by rows otherwise, and `notes.decidable_unit` says which
and why; with no gates the columns say so and name `moot simulate gate-power`. The rendered table therefore never shows "not computed", and
the README sentence that tells the reader to ignore two columns can go. Test: `test_the_report_document_gives_the_decidable_verdict_in_the_unit_of_the_gates`.

### Call 220: a card is pre-launch evidence only when it stood at or before the test's start (round 01, R2, blocking)

The weekly join joined a frozen card to its row whenever the row's horizon had passed at the join clock, and never compared the card's
origin or issue time with the row's `started_at` or `usable_after`. R2 reproduced the hole on the sample ledger: after a refresh the champion
had been fit on exp-120's result (usable 2025-12-29), a card for exp-120 issued at 2025-12-30 was accepted, and the join at 2025-12-31 wrote
an outcome typed hit that became the cell's window (n 1, Brier skill 0.177) with no trace in the file. `loop.card_timing` now classifies every
card against its row before anything is scored: `pre_launch` when the later of the card's origin and issue time is at or before the row's
`started_at`, `in_flight` when it is after the start and before `usable_after`, `after_result` when it is at or after `usable_after`. Only a
pre-launch card is scored. A card that is in flight or after the result is recorded (`cards/outcomes/<card_id>.json` with `post_hoc: true`,
`timing`, `post_hoc_reason`, the card's issue time and origin and the row's start) with every score null: no log score, no Brier, no miss
type, no coverage, and `y`, `s` and the event are not written on it either, so nothing of the result is credited to it. `loop.reliability_row`
returns None for it, so it never reaches the reliability report, the drift rule or the card's skill line; `join_new_rows` counts it apart
(`JoinResult.n_post_hoc`, `post_hoc` with the reasons, printed by `moot join`), and `moot doctor` reports the count per source as a warning
(`cards <source>`). The horizon guard of call 42 still comes first: before `usable_after` there is no record of any kind.

Why the start instant and not `usable_after`: the information a card must not have is the test's own data, which begins at `started_at`;
a card issued during the test has not seen the ledger row (visibility is on `usable_after`) but may have seen interim reads, and the paper
offers the record as pre-launch evidence, so in flight is not pre-launch. Why at or before, inclusive: at the start instant the test has
produced nothing, and the replay issues every card at the start of its row's week, which on the ASOS archive is the start instant of 44 of
its 337 rows (midnight-aligned starts; on Upworthy none of 13,247). A strict rule would have turned those 44 replay cards into in-flight
records and moved the replay table; the inclusive rule leaves every replay card pre-launch and every paper number unchanged. The tutorial's
exp-101 card (issued 2025-07-03 for a test that started 2025-06-27) is in flight under this rule and must be replaced by exp-103 in the page.
Tests: `test_a_card_is_pre_launch_only_when_issued_at_or_before_its_test_started_and_is_never_scored_otherwise` (the four timings, the
backdated origin, the horizon guard first), `test_the_join_records_a_post_hoc_card_apart_and_keeps_it_out_of_the_reliability_report` and
`test_r2_exp_120_a_card_issued_the_day_after_its_result_is_recorded_post_hoc_by_the_join_and_counted_by_the_doctor` (R2's case through
`moot card`, `moot join` and the doctor), in `tests/test_round01_r2.py`.

### Call 221: the origin of a card is never after its issue time (round 01, R2, major)

`moot card --now 2025-12-01 --origin 2025-12-30` froze a card whose issue time preceded the test's launch while its origin, the time whose
rows it saw, followed the result; no interface checked the two. `build_card` now refuses an origin after the issue time with one message, on
the command, the service (422) and the tool alike, so the frozen `origin` is always at or before `issued_at`. The rule is a refusal and not a
clamp: a caller who asks for an origin after the issue time has made a mistake the card should not silently correct. The registered times
stay the team's statements (every interface takes `--now` and the service clock is the caller's); what enforces them is the join's guard of
call 220, which reads the later of the two times, so a frozen file from before this rule with a late origin is post-hoc there. A wall-clock
stamp inside the content id, which R2 also suggested, is not added: it is the caller's clock too, so it is not evidence, and a stamp that
changes on every call would defeat the idempotent freeze (`freeze_or_load`) and manufacture the duplicates of call 222. Test:
`test_an_origin_after_the_issue_time_is_refused_on_every_interface`.

### Call 222: one scored card per row, the earliest pre-launch one (round 01, R2, major)

Every frozen card with a row id was scored, so two cards for one row (a retry of `POST /card`, a refreshed screen, an edited headline) gave
two outcomes and the row counted twice in the rolling scores; R2's cards for exp-103 at 2025-07-10 and 2025-07-11 both received the outcome
and the cell's entry read n 2 from one test. `attach_outcomes` now takes the candidate cards of a row in issue order (issue time, then card
id to break a tie) and scores the first pre-launch one; every other pre-launch card for the row is recorded as a reissue (`reissue: true`,
`superseded_by` the scored card's id, no score), and a row that an earlier join already scored keeps its card, so a card frozen later with an
earlier stated issue time is a reissue too. A card that is not pre-launch is recorded post-hoc whatever its place in the order (call 220).
The earliest is the natural choice because it is the first opinion the team recorded, the one with the least information, and a choice that
cannot be made after the fact: scoring the latest would let a team reissue until the forecast looked right. `moot join` prints the reissue
count, `moot doctor` counts reissues beside the post-hoc cards, and the replay, which issues exactly one card per row, is unchanged. Tests:
`test_two_pre_launch_cards_for_one_row_score_once_the_earliest_and_the_later_one_is_a_reissue` (R2's n 2 case, now n 1, and the late card
with an earlier stated time) and `test_only_pre_launch_cards_compete_for_the_scored_slot`.

### Call 223: the nightly fit sees only the rows usable at the fit clock (round 01, R2, major)

`fit_command` called `fit_bundle` with `as_of` unset, so `moot fit` took every admitted row of the snapshot, not the rows usable at the fit
time; with the sample ingested at a 600-day usable delay it fit 360 rows of which 261 were usable, recorded a `fit_cutoff` in 2027 and
refused every card at the wall clock. `fit_command` now takes the fit clock (`moot fit --now`, default the wall clock) and fits on
`ledger.visible_rows(df, clock)`, the one visibility rule the backtest harness uses (status admitted and `usable_after` at or before the
instant), records the clock in the manifest (`fit_as_of`) and registers `data_through` as the latest `usable_after` the fit saw, which is at
or before the clock, so `check_origin` accepts a card at the clock. A fit at a clock where no row is usable fails with the clock in the
message. P1's data end is the clock too (call 199), so on a static archive fit long after its end the trailing quarter counts as complete
and sets the period level; this changes the parameters and the id of a bundle refit by `moot fit` on the archives (it does not change any
backtest or replay, whose fits stand at their origins), and is the honest reading: at that clock the quarter has ended. Tests:
`test_the_fit_command_takes_only_the_rows_usable_at_the_fit_clock` and `test_moot_fit_takes_a_clock_and_records_it`.

### Call 224: promotion is paired, and the interval decides (round 01, R2, major)

`moot promote` compared two unpaired backtest summaries (different snapshots and row sets, no interval on the difference) against a fixed
margin of 0.02 Brier skill that no rung reaches on either archive, while Section 8 called the comparison paired. `registry.paired_comparison`
now scores the two methods on the same rows: the two per-row score tables are joined by row id at their rungs, the statistic is the paired
Brier skill difference, challenger over champion (the mean per-row Brier difference divided by the mean base-rate Brier of the common rows,
so it is on the skill scale and its sign is that of a skill difference), with a 90 percent bootstrap interval that resamples whole tests, as
the guard comparison of call 191 does. `Registry.promote` promotes only when the lower bound of that interval clears the margin and the
common tests reach the gate for the challenger's own skill (`n_200` at a skill of 0.20 or above, else `n_400`, tests not rows). The default
margin is zero: the gates size a skill, not a difference, so no margin above zero follows from them, and the fixed 0.02 was reached by nothing
on these archives; `--margin` remains for a team with a reason of its own. Second-opinion earning keeps its own constant
(`config.EARN_WEIGHT_MARGIN`, 0.02), unchanged. Two models scored by one backtest table and rung have no paired evidence between them, and
`promote_command` refuses with the file name and what to run: back-test the challenger's method and pass `--challenger-scores` (and
`--challenger-rung`), since the registry cannot know which backtest variant implements a different method. The backtest summary now names its
score table (`scores`). The promotion event in the registry history carries the paired block (difference, interval, common rows and tests,
the two tables). Tests: `test_paired_comparison_uses_common_rows_and_bootstraps_the_skill_difference_by_test`,
`test_promotion_needs_the_paired_interval_to_clear_the_margin_at_the_gate`, `test_promote_command_pairs_the_two_score_tables_by_row_and_refuses_a_shared_table`,
`test_the_promotion_margin_is_zero_by_default_and_the_earn_weight_margin_keeps_its_own_constant`, and the rewritten promotion tests of
`tests/test_registry.py` and `tests/test_registry_extra.py`.

### Call 225: the card's backtest line is the card's own cell (round 01, R2, major)

The "Latest gated backtest" line printed the pooled ALL figure on a card issued per cell: on the released headline-only card 0.002 (minus
0.002 to 0.005) over 3,797 tests, while the same report's row for that cell is minus 0.0048 (minus 0.0085 to minus 0.0016) over 2,280 tests,
decidable at both skills and below zero. `registry.backtest_summary` now stores, beside the pooled figure, every cell of the card rung with
its skill, interval, rows, tests and gate verdict (`cells`, written into the manifest and the registry by `moot fit` and `moot backtest`), and
`card.backtest_view` picks the line: the cell's own figure, with its interval, its gate verdict and which side of zero the interval lies, when
the backtest finds that cell decidable; otherwise the pooled figure, said to be pooled and why (the cell is undecidable at this n, the backtest
has no row for the cell, or the summary predates per-cell figures). The window line above it is unchanged and keeps its interval, test count
and verdict. The card JSON's `skill.backtest` carries `scope`, `cell`, `decidable` and `reason`, so the id of a card with a backtest summary
changes; the golden card fixture has no backtest summary and is unchanged. Tests:
`test_the_backtest_summary_carries_every_cell_of_the_card_rung_with_its_decidability` and
`test_the_card_prints_its_own_cell_figure_when_decidable_and_the_pooled_one_labelled_otherwise`; the pooled wording is pinned in
`tests/test_review_l.py::test_the_skill_line_prints_the_interval_the_test_count_and_the_gate_verdict_never_a_bare_number`.

# Design calls of chunk P (T-068): round 01, reviewer R6, code-side fixes, and the three items of builder-m's pass

### Call 226: the doctor looks for sidecar files, and the backtest names them instead of a traceback (R6, major 1)

An environment on an exFAT volume carries a `._` sidecar beside every file macOS wrote, and the plotting library globs its style
directory at import, so `moot backtest` died with a UnicodeDecodeError on `.__classic_test_patch.mplstyle` while `moot doctor` said OK.
`onboarding.check_environment` now lists the `._` files at the top of the active interpreter's site-packages and under the plotting
library's style directory (the two places that fail first; the top level holds one sidecar per package, so the count is a fair measure)
and fails with the count, the consequence and the cure (an environment on the internal disk, reinstalled, or the `find ... -delete` of the
troubleshooting page); an environment whose prefix lies under `/Volumes` with no sidecar yet is a warning that says the same. The check
runs before the storage check so that it is the first line a newcomer reads. `report._pyplot` imports the plotting library and turns that
UnicodeDecodeError into `storage.SidecarEnvironmentError`, one of the user error types the command line prints as one line with exit code 2;
the message names the file, the cause and the cure and points at `moot doctor`. Tests: `test_the_doctor_detects_sidecar_files_in_the_environment_and_names_the_cure`,
`test_the_doctor_runs_the_environment_check`, `test_a_sidecar_in_the_plotting_library_fails_the_backtest_with_one_line_not_a_traceback`.

### Call 227: the gate line names the nearest simulated base rate and the cell's own (R6, minor)

The card's gate line read "at base rate 0.30" beside an evidence line giving the cell's own rate as 0.117, and a reader could not tell that
0.30 was the simulated rate of the gates file nearest the cell's. The gates are still read at the nearest simulated rate (interpolating
between simulated rates would invent a size no simulation produced, so the nearest row is kept and named): the line now says "at the
nearest simulated base rate, 0.30 (this cell's own rate is 0.117)". Test: `test_the_gate_line_names_the_nearest_simulated_base_rate_and_the_cell_own_rate`.

### Call 228: a card without text shows no text fields, and an empty headline is not a changed headline (R6, minor; builder-m item b)

A card for a ledger without text printed `headline "", image changed: no` and stored `headline_changed: true` with an empty headline.
`build_card` now stores `headline_changed` false when the headline is empty (the derived cell follows: an empty headline with the image
changed is `image_only`), and the Request line prints the headline, the reference headline and the image flag only when the request has a
headline or a reference headline. The exposure is called what the exchange format calls it: "planned units per arm" (or "planned units:
N reference, M variant" when the arms differ) on the card and in `moot card --help`; `--impressions` keeps its name. The golden card
fixture changes by that one line (regenerated with `MOOT_UPDATE_GOLDEN=1`); its card id does not, since the request block is unchanged for a
text request. Tests: `test_a_card_without_text_skips_the_text_fields_and_stores_headline_changed_false`, `test_the_card_help_and_module_note_say_planned_units`.

### Call 229: "Tests needed" where the gates count tests (R6, minor)

The one-page report card's Gates heading said "Rows needed" while its Ladder section and the backtest header count tests. The report card
records the unit of its gates (`gates_unit`, from `gates["interval"]["by"]`) and the heading follows it; a card from before the field reads
tests, as every gates file written by this version does. Tests: `test_the_report_card_says_tests_needed_when_the_gates_count_tests`,
`test_the_report_card_records_the_unit_of_its_gates`.

### Call 230: the positive control reports what the rung gains, beside what the guard admits (round 01, R3 major 4 and R1 minor)

The admission curve (`positive_control_sensitivity`, table `positive-control-sensitivity.tex`) said how often the guard admits a weight when a
text lift is planted; it did not say what the precedent rung gains from it, and the one realized number in the paper (the positive-control run,
about 1,200 scored rows per cell) put P2 0.0010 nats above P1 against a ceiling of about 0.011. Every row of the sensitivity now carries, beside
`share_admitted` (unchanged: P2 fit on the whole ledger, the published numbers to the last digit), the gain measured out of sample:

* The split. A random 15 percent of the TESTS of each ledger is held out (never rows; `split_tests`, the same split as `guard_held_out_gain`);
  P1, the feature space, P2 (guard 2) and P0 are fit on the other 85 percent, and every held-out row is scored at an origin one day after the
  ledger's last `usable_after`. `share_admitted_fit_split` records the guard's admissions on that fit.
* `realized_gain`: the mean held-out log score of P2 minus P1 per row, in nats, with a 90 percent percentile interval and a clustered standard
  error, both by test, pooled over the 12 seeds and the three cells (`by_cell` repeats every column per cell).
* The oracle (`oracle_gain`). The forecaster that knows the planted effect and nothing else: P1 refit on the fit rows with the planted term
  `strength * (signal - 0.5)` removed from every outcome (the term the generator adds to theta when the headline carries a signal word), and its
  location moved back by the row's own term at prediction. It is P1's family, P1's estimation and P1's period rule, so its gain over P1 is the
  value of the planted information alone, the ceiling a rung that learns the text can reach while it stays in P1's family; it also carries the
  tighter spread (the planted variance, strength squared over four, leaves the prior). At strength zero it is P1 to the last digit, so its gain
  is exactly zero and the recovered fraction is undefined (None). The closed-form ceiling the reviewers used, one half of the log of
  `(V + strength^2 / 4) / V` with `V = tau^2 + s^2` and the generator's own parameters, is the Normal, known-parameter version of the same
  quantity; the refit oracle is preferred because it is measured on the same held-out rows as the realized gain, with the same estimation
  noise in both.
* `recovered_fraction`: realized over oracle, with an interval from the ratio of the paired by-test draws (one set of multinomial test counts
  serves both means).
* `brier_skill_p1`, `brier_skill_p2`, `brier_skill_oracle`: one minus the mean Brier of `p_sig` over P0's on the held-out rows, P0 fit on the fit
  rows (its `p_sig` is the cell's visible event rate), the event `y > 1.96 s`.

Numbers (12 seeds, 36 cells per point; `paper-extras-synthetic-20261103-bf4fd286e2b2.json`, `positive_control_sensitivity.rows`, keys
`share_admitted`, `realized_gain` with `_lo`, `_hi` and `_se`, `oracle_gain` with `_lo` and `_hi`, `recovered_fraction` with `_lo` and `_hi`,
`brier_skill_p1`, `brier_skill_p2`, `brier_skill_oracle`, `held_out_rows`, `held_out_tests`, `by_cell`). At a planted lift of 1 percent: 300 tests
(200 rows per cell; 1,080 held-out rows over 540 tests) admit 0.056 of cells, realized gain 0.00004 nats (minus 0.00079 to 0.00098), oracle
0.0192 (0.0105 to 0.0284), recovered 0.002 (minus 0.048 to 0.060), Brier skill P1 0.0009, P2 0.0020, oracle 0.0149; 1,000 tests (667 rows per
cell; 3,600 rows over 1,800 tests) admit 0.250, realized minus 0.00010 (minus 0.00100 to 0.00091), oracle 0.0194 (0.0144 to 0.0244), recovered
minus 0.005 (minus 0.055 to 0.044), skills 0.0228, 0.0225, 0.0299; 11,100 tests (7,400 rows per cell; 39,960 rows over 19,980 tests) admit 0.889,
realized 0.00402 (0.00362 to 0.00441), oracle 0.0204 (0.0189 to 0.0221), recovered 0.197 (0.180 to 0.215), skills 0.0174, 0.0204, 0.0338. At
11,100 tests the recovered fraction is 0.047 (0.027 to 0.066) at half a percent, 0.273 (0.263 to 0.282) at 2 percent and 0.254 (0.249 to 0.258)
at 4 percent; at 1,000 tests 0.105 (0.065 to 0.142) at 2 percent and 0.186 (0.167 to 0.205) at 4; at 300 tests 0.094 (0.061 to 0.126) at 4
percent and indistinguishable from zero below. At lift zero the realized gain is 0.00033, 0.00003 and minus 0.00001 nats at the three sizes,
every interval spanning zero, and the oracle gain is exactly zero. By cell at 11,100 tests and 1 percent (`by_cell`): headline_only (a third of
a prior standard deviation) realized 0.0014 against an oracle of 0.0116, recovered 0.123, admitted in 0.667 of cells; both (half) 0.0047 against
0.0218, 0.217; image_only (two thirds) 0.0060 against 0.0281, 0.213. The oracle's gains agree with the closed form at the second digit
(headline_only 0.0107, both 0.0187, image_only 0.0254 at 1 percent). The admission share on the 85 percent fit (`share_admitted_fit_split`) is
within one or two cells of the whole-ledger share everywhere (0.944 against 0.889 at 11,100 tests and 1 percent).

Reading. The guard's admission curve and the rung's gain are different curves. At the size of the headline-only cell the guard admits a
one-percent lift in 89 percent of cells, and the rung then recovers a fifth of the information the lift carries (0.004 of 0.020 nats per row;
0.12 in the headline-only cell itself, where the lift is a third of a prior standard deviation), and a quarter of it at 2 and 4 percent, where
it admits everywhere; at 300 and 1,000 tests it recovers nothing measurable below 2 percent whatever it admits (the admitted weights are
small and the held-out gain of a small weight on a weak signal is zero within noise). In Brier skill the same point reads P1 0.0174, P2 0.0204,
oracle 0.0338. The rung never recovers more than about a quarter of the planted information at any size or strength in this generator: the
kernel weights precedents by the whole feature vector, and one signal word among random fillers is a small part of it.

The oracle's gain in nats is the ceiling for the log score; it says nothing about whether a one-percent text lift matters to a decision, and the
paper should keep the two apart. The table is `positive-control-gain.tex` (`positive_control_gain_table`); rows of an older extras file without
the gain columns are left out of it, so an old run folder builds the old tables unchanged.

### Call 231: the text classifier and the boosted model on the planted ledger (round 01, R3 major 4)

The positive-control run named gbm and local_eb only; the text classifier, the one challenger designed around a text signal, never saw the planted
ledger, and no realized gain existed at the size of the headline-only cell. Two backtests of the planted ledger (`moot simulate ledger --seed 7
--text-effect 1.0`, then `moot backtest --source synthetic --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr --seed
0`) now exist: 2,000 tests, the positive-control run's own ledger (the snapshot id is the same, so P0, P1, P2 and the boosted model reproduce the
published control to the digit and the text classifier is added beside them), and 11,100 tests (about 7,400 rows per cell, the size of the
headline-only cell). `positive_control_rungs` (synthetic paper extras; `scripts/paper_extras.py --positive-control-runs DIR,DIR`) reads each
folder and reports, per cell and pooled, for every rung in the score table:

* the report's log score and Brier skill against P0 with its interval, and the AUC for the event;
* the paired per-row difference from P1 on the rows both scored, in log score (nats; None for a rung without a density: the text classifier,
  raw or recalibrated, and the recalibrated rungs issue `p_sig` only) and in Brier score (negative is better), each with a 90 percent interval
  by test from one set of resamples per cell;
* the oracle of call 230 refit at every origin on the rows visible then (data end the origin, as the harness fits P1), scored on the rows of that
  origin with the location moved back by the row's term: its difference from P1 is the ceiling at that origin set, and
  `recovered_fraction_logscore` (`_brier`) is a rung's difference over the oracle's.

Numbers (`positive_control_rungs.runs[].by_cell[cell].rungs[]`, keys `logscore`, `brier_skill` with `_lo` and `_hi`, `auc_event`,
`diff_logscore_vs_p1` and `diff_brier_vs_p1` with `_lo` and `_hi`, `recovered_fraction_logscore`, `recovered_fraction_brier`; the oracle under
`by_cell[cell].oracle`, keys `gain_logscore_vs_p1`, `gain_brier_vs_p1` with intervals and `brier_skill`). 2,000 tests (the published control's
ledger, snapshot 20261104-8cc34d3af720; 3,576 scored rows, 1,192 per cell; the guard admitted 7 of 24 origin and cell pairs): pooled, the oracle
gains 0.0155 nats (0.0099 to 0.0206) and minus 0.0020 in Brier; P2 plus 0.0003 nats (minus 0.0006 to 0.0013) and minus 0.0001 Brier, recovered
0.02 in log score and 0.06 in Brier; the boosted model minus 0.0251 nats (its Normal spread is not P1's) and plus 0.0003 Brier (recalibrated
minus 0.0003, recovered 0.15), Brier skill 0.0217 raw and 0.0260 recalibrated against P1's 0.0239; the text classifier plus 0.0053 Brier (0.0029
to 0.0077), Brier skill minus 0.0137 (minus 0.0273 to 0.0009), recalibrated plus 0.0045 and minus 0.0079: below the base rate. In the
headline-only cell: oracle 0.0071 (minus 0.0001 to 0.0143); P2 plus 0.0010 (minus 0.0016 to 0.0041), recovered 0.14; the boosted model minus
0.0199 nats but minus 0.0044 Brier (minus 0.0078 to minus 0.0005), 1.7 times the oracle's Brier gain on intervals that overlap, Brier skill
0.0435; the text classifier plus 0.0104 Brier, skill minus 0.0185. 11,100 tests (snapshot 20261104-c7ca82ca15a6; 19,766 scored rows, 6,589 per
cell; 18 of 24 pairs admitted): pooled oracle 0.0197 (0.0177 to 0.0219) and minus 0.0024 Brier; P2 plus 0.0027 nats (0.0022 to 0.0033) and
minus 0.0002 Brier (minus 0.0003 to minus 0.0001), recovered 0.14 and 0.08, Brier skill 0.0227 against P1's 0.0215; the boosted model minus
0.0243 nats and plus 0.0005 Brier, skill 0.0177 raw and recalibrated; local_eb minus 0.0119 nats and plus 0.0005 Brier; the text classifier plus
0.0054 Brier (0.0045 to 0.0063), skill minus 0.0168 (minus 0.0222 to minus 0.0114), recalibrated plus 0.0049 and minus 0.0134. Headline-only
cell at 11,100: oracle 0.0118 (0.0090 to 0.0148); P2 plus 0.0009 (0.0004 to 0.0015), recovered 0.08 in log score and 0.06 in Brier; the boosted
model minus 0.0472 nats and plus 0.0010 Brier, skill 0.0206; the text classifier plus 0.0115 Brier, skill minus 0.0234. The P0, P1, P2, GBM and
local_eb rows of the 2,000-test run equal the published control in every compared value (36 cell and rung rows: n, log score, Brier, skill
and its bounds, AUC, abstention rate).

Reading. The text classifier does not recover the planted signal at either size: raw or recalibrated it scores below the base rate on the
planted ledger (Brier skill minus 0.013 to minus 0.017 pooled, minus 0.018 to minus 0.023 in the headline-only cell), so the one rung whose
skill interval clears zero on the real archive is the one that fails the control; its design (a winner classifier on TF-IDF that ignores the
planned precision) does not see a one-percent location shift under this noise. The boosted model recovers the oracle's Brier gain in the
headline-only cell at 2,000 tests (1.7 times, on a wide interval; the number R3 quoted) and falls below P1 in that cell and pooled at 11,100
tests; its log score is below P1 everywhere. The precedent rung is the only rung above P1 on both scores at both sizes, by a tenth to a
seventh of the ceiling pooled and by a tenth or less in the headline-only cell; it recovers less in the rolling-origin backtest (0.14 pooled at
11,100) than in the end-of-ledger split of call 230 (0.20), because the early origins fit on small histories.

The reports and their Markdown twins are in `paper/data/run5-period-rule/positive-control/rungs/n2000` and `n11100` (a subfolder, so the
`positive-control/backtest-synthetic-*.json` glob of `positive_control_table` still reads the published control); the score tables, ledgers and
models stay on the data root under `experiments/builder-q/positive-control-rungs/`. The table is `positive-control-rungs.tex`
(`positive_control_rungs_table`, cells ALL and headline_only).

### Call 232: the positive-control keys are merged alone, and the points run in processes

`scripts/paper_extras.py --positive-control-only` recomputes `positive_control_sensitivity` and, when `--positive-control-runs` names folders,
`positive_control_rungs`, and merges them into the existing synthetic extras file; every other key is left as it is (the pattern of
`--period-control-only` and `--gain-diagnostic-only`). `--sensitivity-seeds 0` keeps the stored sensitivity and merges the rung comparison alone.
`--jobs N` computes the (size, strength, seed) points of the sensitivity in N processes; each point is a pure function of its arguments and the
bootstrap runs in the parent with a fixed seed, so the file does not depend on N. The full path (`build_extras`) carries the same arguments, so a
complete rerun of the extras produces both keys. Verified after the merge: every key other than the two positive-control keys is byte-identical
to the file before it (`diff` of the sorted JSON with the two keys removed), and the recomputed `share_admitted` values equal the published
ones in all 15 rows. Wall time: the sensitivity (180 points, 12 seeds at every size) 1,826 s with four processes on a machine whose load average
was 40 to 66 from other jobs, about 70 s of processor time per 11,100-test point (two P1 fits of 22 s, the oracle refit, two P2 fits and the
scoring) and under 5 s per smaller point; the two backtests 157 s (2,000 tests) and 2,641 s (11,100 tests, under the same load); the rung merge
121 s. No seeds were reduced.

## Calls of T-067 (round 01, R3 major 2): where the realized loss of the admitted pairs sits

### Call 233: the admitted pairs row by row, and the location and scale parts of the realized difference (round 01, R3 major 2)

Table 24 (`guard_pairs`) gives one realized number per admitted pair, the mean P2 minus P1 log score over its rows. R3 read the per-row score
file and found the loss on the typical row (P2 better on about a fifth to a quarter of the rows of the two largest pairs) and a gain on the
decisive rows, and asked for the difference to be split into a location part and a scale part so the paper can say which term the negative
result is about. `guard_pairs_rows` (paper extras of every source; Upworthy has the nine admitted pairs, ASOS none) reports, per admitted pair
and pooled over them, with 90 percent intervals by test from one set of resamples per pair:

* `rows`, `tests`, `share_p2_better` (rows where P2's log score exceeds P1's), `median_diff` (interval by the weighted median of each draw) and
  `mean_diff`;
* the same for the `decisive` rows and the `non_decisive` rest, where decisive is the harness's own definition, the row's realized |y| above
  1.96 times its realized standard error (R3's split), and for the `event` rows (realized y above 1.96 s, the significant-positive event the
  scores are built on) and the `non_event` rest, so both readings of "decisive" are in the file;
* `location_part` and `scale_part`, whose means sum to `mean_diff` row by row. Both predictives are Student-t with the cell's degrees of freedom
  (P2 is moment matched in P1's family, call 160 and review L), so a row's log score is a function f(location, scale) of two parameters and the
  split is well defined up to the order in which the two parameters are moved: the location part is the average of f(loc2, sc1) minus
  f(loc1, sc1) and f(loc2, sc2) minus f(loc1, sc2), the scale part the average of f(loc1, sc2) minus f(loc1, sc1) and f(loc2, sc2) minus
  f(loc2, sc1) (the two one-parameter-at-a-time paths averaged, the Shapley split of two players). The locations and scales are the backtest's
  own: P1 and P2 are refit at each admitted origin with `harness.default_rungs` on `ledger.visible_rows` (the report's guard setting), each row's
  predictive is rebuilt, and both stored log scores are recomputed from the rebuilt parameters (`recomputation_max_abs_error`, and
  `decomposition.defined` is False if any row misses by more than 1e-6 or the two predictives differ in their degrees of freedom);
* `mean_scale_ratio_p2_over_p1`, `share_scale_wider` (rows where P2's scale exceeds P1's) and `mean_abs_location_shift_over_p1_scale`, the
  plain readings of how P2's predictive differs from P1's on those rows; and the pair's `lambda`, `tau_res2`, `bandwidth_mult` and in-selection
  gain from `tables.p2_selection`.

Numbers (Upworthy, `paper-extras-upworthy-20261103-4bfb354b87e3.json`, `guard_pairs_rows.rows[]` and `.pooled`; nine admitted pairs, 7,773 rows
over 2,221 tests; `decomposition.defined` true, `max_abs_recomputation_error` 0.0, the same degrees of freedom in every row; 500 resamples).
The two largest pairs, headline_only at 2014-07-01 (1,550 rows) and 2014-10-01 (1,544): P2 better on 0.195 (0.170 to 0.219) and 0.278 (0.258 to
0.304) of the rows, median difference minus 0.0504 (minus 0.0528 to minus 0.0480) and minus 0.0666 (minus 0.0697 to minus 0.0614), mean minus
0.0267 (minus 0.0307 to minus 0.0226) and minus 0.0153 (minus 0.0227 to minus 0.0072); decisive rows 402 and 415, mean plus 0.0446 (0.0349 to
0.0555) and plus 0.1327 (0.1151 to 0.1508), P2 better on 0.632 and 0.812 of them; the rest minus 0.0517 and minus 0.0698. R3's four numbers
(0.195 and 0.278; minus 0.0504 and minus 0.0666; plus 0.0446 and plus 0.1327 on 402 and 415 rows) reproduce to the digit. Location part plus
0.0032 (0.0015 to 0.0047) and plus 0.0026 (0.0008 to 0.0045), scale part minus 0.0299 (minus 0.0334 to minus 0.0263) and minus 0.0179 (minus
0.0251 to minus 0.0098); P2's scale is above P1's on every row of both pairs, by 1.104 and 1.205 on average (`tau_res2` 0.5159 and 0.4002,
bandwidth multiplier 0.25). Pooled over the nine pairs: P2 better on 0.332 (0.320 to 0.343) of the rows, median minus 0.0120 (minus 0.0136 to
minus 0.0107), mean minus 0.0067 (minus 0.0088 to minus 0.0045; the Table 24 number); location part plus 0.0023 (0.0016 to 0.0030), scale part
minus 0.0090 (minus 0.0109 to minus 0.0071); the 2,076 decisive rows: P2 better on 0.749, mean plus 0.0608 (0.0554 to 0.0670), location plus
0.0111 and scale plus 0.0497; the 5,697 other rows: mean minus 0.0313, location minus 0.0009 and scale minus 0.0304; the 697 significant-positive
rows: mean plus 0.0678. P2's scale exceeds P1's on 0.917 of the admitted rows (mean ratio 1.089, mean location shift 0.033 P1 scales). The
location part is positive in all nine pairs (plus 0.0006 to plus 0.0036; its interval clears zero in six) and the scale part is negative in
five, the two largest included; the one pair with a clear realized gain (2013-10-01, plus 0.0109, P2 better on 0.750 of its rows) is the one
pair where P2 is narrower than P1 (ratio 0.971; scale part plus 0.0076, location plus 0.0033). ASOS: 0 of 28 pairs admitted, empty rows.

Reading. The realized loss of the admitted pairs is the scale term, not the precedent mean. Pooled, the location part is plus 0.002 nats per row
with an interval clear of zero and positive in every pair, the scale part minus 0.009, and their sum is the minus 0.007 of Table 24. P2's
predictive is wider than P1's on 92 percent of the admitted rows (10 and 20 percent wider in the two largest pairs), which costs on the bulk
(a scale part of minus 0.030 on the 5,697 non-decisive rows) and pays on the tails (plus 0.050 of scale on the 2,076 decisive rows, where P2
also gains plus 0.011 of location). So the sentence R3 asked for is the honest one: the precedent mean carries a little (a location gain of
0.002 nats per row, the decisive rows, the within-cell discrimination of the AUC table), and the moment estimate of the residual variance,
`tau_res2` (0.52 and 0.40 in the two largest pairs), widens the predictive enough to lose it on the typical row; where P2 came out narrower
than P1 it gained. "In-selection gains do not transfer" should be rewritten as "the admitted weights move the location a little in the right
direction and the scale in the wrong one". What this does not say: whether a better variance estimate would turn the pooled difference
positive. A forecaster with P2's location and P1's scale is not the rung that was selected (the selection scored the candidates with the same
scale term), and the location part is the average over two paths, not the gain of that forecaster alone.

The table is `guard-pairs-rows.tex` (`guard_pairs_rows_table`, the Upworthy extras).

### Call 234: the key is merged alone, and a run folder is read as a data root

`scripts/paper_extras.py --source S --guard-pairs-rows-only` adds `guard_pairs_rows` to the existing extras file of the source and leaves every
other key as it is (the pattern of the other add-only flags); the full path computes it for every source. Verified after the merge on Upworthy
and ASOS: every other key byte-identical to the file before it. A correction to T-066 from the storage policy (`tests/test_storage.py`): the
rung comparison read each backtest folder's ledger at a literal `data/ledger.parquet` path; it now reads the folder as a data root,
`storage_paths(run).ledger_path` (the standard layout), the two folders on the data root were moved to that layout, and the recomputed
`positive_control_rungs` key is identical to the published one (only its `inputs.ledger` note changed, and the published file carries the new note).
Wall time: Upworthy 130 s (seven origins refit), ASOS 2 s.

## Calls of T-075 (round 01, five small items from the response letter)

### Call 235: every caption number traces to a source, and a test holds it (R1 major 4, R3 major 6, R5 major 1)

`tests/test_paper_sources.py` parses every float (`table`, `table*`, `figure`, `figure*`) of `paper/sections/*.tex` and `paper/main.tex`. A
float whose caption contains a digit must carry a source: a `% src:` line inside the float or in the contiguous comment block right above it
(the paper's convention), a `% table:` reference, a generated table (`\input{tables/...}`, whose first line names the report JSON and path it was
built from) or a generated figure (a comment naming `figures.json`, the index of every plotted value, which `tests/test_paper_figures.py`
checks against the reports). A comment separated from the float by prose does not count. The check is a regex pass over nine files and runs
in well under a second; a second test feeds it a caption with a digit and no source and expects the report (red), then each source form in
turn (green). On the current tree 57 floats carry a caption, 30 of them a digit; one had no source, the tooling landscape table of Appendix
B, whose only digits are the year of the three cited 2026 systems: it now carries a `% src:` line naming the survey page. Everything else
already traced.

### Call 236: the precedent rung's docstring says what the rung is (R3 nit 2)

The module docstring of `src/mootcourt/predictors/p2.py` opens with what the rung is: P1's Student-t predictive with the cell's degrees of
freedom, its location moved toward the kernel-weighted precedent mean and its scale set from the precedents' variance plus a residual term,
both through the per-cell weight; the lambda-zero identity (weight zero returns P1's predictive object to the last bit); the selection mode
(`"loto"`, leave one test out, the default, or `"forward"`, chaining at inner time cuts) and the admission guard (the best candidate's gain
over weight zero must clear a tie tolerance and `guard` cluster-robust standard errors). The sentence R3 flagged, "a rung is used only when
it beats the rung below out of sample by more than noise", now reads that a candidate is admitted when it beats weight zero on the
validation rows of the fit, and that whether an admitted weight transfers out of time is what the backtest measures and the paper reports
apart (calls 191 and 233). A test pins the phrases and the absence of the old sentence.

### Call 237: the sample ledger's base rate is the headline archive's, and the quick gates are simulated at it (R6 minor 6, question 5)

`mootcourt.importers.sample.sample_exchange(seed=7, n_experiments=120, base_rate=SAMPLE_BASE_RATE)` takes the expected significant-positive
rate per row, default `SAMPLE_BASE_RATE = 0.09`, the headline archive's. Each metric's mean relative effect is the value at which a result
at the metric's typical standard error (the median planned units, 34,000) is significant and positive with that probability given the
metric's spread (`metric_mean`): with the spreads of `METRICS` the means are minus 0.019 (checkout conversion), minus 0.012 (pages per
session) and minus 0.014 (revenue per user), slightly negative, as the average product change is. The random draws are the same as before,
so `base_rate=None` reproduces the earlier sample (fixed means 0.010, 0.000 and 0.005; realized rate 0.197) exactly, and the dates and
experiment ids never move. The realized rate of the default draw is 0.061 (0.042, 0.083 and 0.058 by metric) against the 0.09
expectation: one draw of 360 rows, whose standard deviation is 0.015. `examples/ledgers/sample.csv` is regenerated from the default and
the test that keeps the two equal holds. `moot init` now simulates its quick gates at the sample's base rate (`onboarding.QUICK_GATE_BASE
= SAMPLE_BASE_RATE`, with the archive's dependence at that rate, 3.5 rows per test and a within-test correlation of 0.13): 175 and 250
tests at the decision target, the sizes the paper argues from, in 26 s against 20 s at base rate 0.30 before. The sample stays 120
experiments and 360 rows. What changes downstream: every tutorial and command-guide output that prints a number from the sample ledger
(effects, event rates, p_sig, intervals, card ids, model ids, snapshot ids, the backtest tables, the quick gate sizes and the gate
verdicts) is stale until regenerated, which is builder-m's phase B1; the golden card test is unaffected, because its fixture is the
synthetic generator and not the sample.

### Call 238: the card says when the reference headline was defaulted (R2 question 2)

`RequestEcho.reference_defaulted` (frozen in the card JSON under `request`) is true when the bundle's feature space is pairwise (it reads
a reference headline) and the request gave none: the pair features were then the fit-set mean reference vector (call 187) and the request
sat at the center of the pairwise space rather than at a real pair, which is why such requests see fewer novelty abstentions. The Markdown
card prints, under the Request line, "Reference headline: not supplied; the pair features use the fit-set mean reference vector (the center
of the pairwise space), not a real pair". A space without references (a ledger without text, the synthetic source) and a request that gave
a reference record false and print nothing. The field is additive in schema version 2; every new card's digest changes with it, and the
golden card test masks the three content digests, so its fixture stands. The frozen-card format note in `card.py` carries the field; the
reference page `docs/reference/card.md` (builder-m's) needs the field added to its `request` row.

### Call 239: a per-platform score report from the continuous-integration job (R5 minor 8)

`scripts/ci_score_report.py` runs the backtest `moot init` leads a newcomer to, on the bundled sample ledger (deterministic, seed 7),
imported through the generic exchange format and scored by the harness at its quarterly origins with the ladder only, and writes
`score-report-<python>.json`: for P0, P1 and P2 the mean log score and the Brier skill against P0 over every scored row, to six decimals,
with the rows and tests, the Python, platform and machine, the numpy, scipy, pandas and scikit-learn versions, and the generator string.
The `test` job of `.github/workflows/ci.yml` runs it after the test suite on each Python version (3.11, 3.12, 3.13) and uploads the file as
the artifact `score-report-<python>` (`actions/upload-artifact`, pinned); no data root is read or written and nothing is downloaded. The
paper cites the artifact name; a test runs the report twice and requires identical numbers, the three rungs, six-decimal values, a zero
skill for P0, and the workflow steps. Numbers on this machine (macOS arm64, Python 3.11.14, numpy 2.4.6, scipy 1.17.1, pandas 3.1.0,
scikit-learn 1.9.1; 330 scored rows over 110 tests and 11 origins; 5.7 s): P0 log score 2.001428 and skill 0 by construction, P1 and
P2 log score 2.007951 and Brier skill 0.019860, P2 equal to P1 because the guard admits no weight on a ledger without text (the log
scores are positive because relative effects are small numbers, as on the deployment-shaped archive). The artifact, not these numbers,
is what the paper cites; the continuous-integration runners write their own.

### Call 240: table headers name their source relative to the run folder, and `make tables` rebuilds them (R4 minor, Makefile and tables)

Every committed table named the launching team's absolute data-root path as its source. `paper/build_tables.py` now remembers the run
folder it is given (`set_reports_root`, called by its main block from `--reports`) and `write` passes each header comment through
`relative_to_run`, which strips every spelling of that folder (as given, normalized, absolute, real, with either separator), so a header reads
`% generated by paper/build_tables.py from backtest-upworthy-20261103-4bfb354b87e3.json (...)` or `from ablations/backtest-upworthy-*.json
(...)`, a path inside the run folder, whichever folder and machine built it. A test builds a table from a temporary run folder and checks the
header, and another checks that no committed table names an absolute path. The Makefile gains `tables` (`build_tables.py --reports $(RUN)
--out paper/tables`, `RUN` defaulting to `paper/data/run5-period-rule`) and `paper` now depends on `paper-figures` and `tables`; none of the
three reads the data root. The tables were rebuilt from run5 in place: 63 of 63 generated headers changed and 57 bodies are byte-identical;
the six bodies that changed (`main-upworthy`, `main-asos`, `main-synthetic`, `drift-upworthy`, `drift-asos`, `drift-synthetic`) carry the
extra column of builder-l's uncommitted edits to `main_table` and `drift_table` and the rewritten run5 Upworthy report, which had not been
rebuilt into `paper/tables` yet; the rebuild materialized them and run 6 rebuilds them again. For the paper writer: Table tab:commands
(`appendix.tex`, the `build_tables.py --reports $ROOT/reports` line) should read `make tables`.

### Call 241: the sdist holds the package, its examples and its tests (R4 nit, 8.5 MB sdist)

`[tool.hatch.build.targets.sdist] only-include = ["src", "tests", "examples", "README.md", "LICENSE", "pyproject.toml"]`. The sdist falls from
10,208,715 bytes (316 files of `paper/`, the documentation, the scripts, the reports folder, the lock file) to 516,974 bytes (52 source files,
96 test files, 7 examples, the three metadata files and PKG-INFO). The wheel is untouched: built from one scratch copy of the package with
and without the block, the two wheels have the same 57 members with identical digests. The test suite inside the sdist cannot run the
tests that read `docs/`, `scripts/` or `paper/` (they never could without the repository); the package, its examples and its tests are
what a reader installs from. A test builds the sdist into a temporary folder and lists the archive.

### Call 242: pytest is quieted once (R4 nit, `-q` twice)

`pyproject.toml` sets `addopts = "-q"`; the workflow's two pytest steps and the Makefile's `test` target passed `-q` again, which made
pytest fully quiet and hid the count line (R4 counted 1,184 passes from the dots). The three invocations now pass no `-q`, so the
summary line "N passed in S s" is in every job log and in `make test`. A test reads the workflow and the Makefile.

### Call 243: two documentation corrections handed to the documentation builder (R4 nits on the troubleshooting page and the run5 README)

Not edited here (the documentation pages and the run README belong to other builders). (a) `docs/troubleshooting.md` lines 55 to 65
already quote the RECORD mismatch; the verbatim text from R4's log (`round01-r4-uvsync-attempt1.log`) for the page is:
`error: Failed to install: ruff-0.17.3-py3-none-macosx_11_0_arm64.whl (ruff==0.17.3)` / `Caused by: RECORD file doesn't match wheel
contents: Could not find entry for ruff-0.17.3.data/scripts/._ruff (<clone>/.venv/lib/python3.13/site-packages/ruff-0.17.3.data/scripts/._ruff)`,
preceded by uv's warning `If this is intentional, set export UV_LINK_MODE=copy or use --link-mode=copy to suppress this warning.`; the
older form `failed to copy ... ._ttx.1` stays as the second message, and R4's remaining ask is one sync command across the pages (the
page says `uv sync --extra dev`, the README `uv sync`, the reviewers used `uv sync --all-extras`). (b) `paper/data/run5-period-rule/README.md`
line 7, the clause "The ablations themselves were not rerun: they fit at quarterly origins and the period rule changes nothing there", is
contradicted by R4's major finding (the shipped ASOS `p2-guard-off` ablation was written by the run-4 bundle `a6a5a1c77334` and does not
reproduce: the unguarded P2 at origin 2020-07-01 scores 4.9161 against the shipped 4.9143, 554 entries move, two printed digits change);
the run 6 README carries the true statement.

### Call 244: the arXiv source package is built from the paper folder and holds nothing else

`make arxiv` builds the paper with tectonic keeping its intermediates (so `main.bbl` and the figures are current) and
`scripts/arxiv_package.py` writes `paper/dist/arxiv-<date>.tar.gz` with `main.tex` at the root and the paper's own layout: `main.tex`,
`main.bbl`, `references.bib` (for the record; arXiv uses the `.bbl`, which must carry the main file's name), `sections/*.tex`,
`tables/*.tex`, `figures/*.pdf`, and any `.sty`, `.cls` or `.bst` at the top of the paper folder (none now: `acmart` is in TeX Live). Every
`\input` and `\includegraphics` target must be a member or the build fails; no data, review, PDF, provenance index or auxiliary file goes
in. The archive is reproducible (members sorted, user and group ids zeroed, a fixed timestamp, gzip without a date), so the same sources give the
same bytes, which the test checks. The tarball is not committed (`.gitignore`: `paper/dist/*.tar.gz`); the two notes under `paper/dist`
are, which needed an exception to the repository's `dist/` rule.

### Call 245: the engine is pdfLaTeX on TeX Live 2025, and the compile check is a TeX-only build over the precompiled bibliography

`main.tex` loads `acmart` (`sigconf`, `nonacm`) with `booktabs`, `graphicx`, `amsmath` and `xcolor`, no `fontspec` and no Unicode font, so
pdfLaTeX, arXiv's default processor on its TeX Live 2025, compiles it; the processor is selected in arXiv's submission interface, no
`00README` directive is needed. XeLaTeX (added by arXiv in November 2025, and what tectonic runs inside) would also work; pdfLaTeX is the
safer default and `README-arxiv.md` says to select it. `make arxiv-check` unpacks the tarball into a fresh folder, deletes `references.bib`
there so only the `.bbl` can resolve a citation, compiles three passes with pdflatex where installed and otherwise with tectonic in
TeX-only passes (`--pass tex`), reads the page count from the log and lists every undefined reference or citation, and exits 1 on a
mismatch with the ordinary build's log. Why TeX-only passes: tectonic's default pass runs its own BibTeX, which without the `.bib`
rewrote `main.bbl` and left every citation undefined in the first attempt; with `--pass tex` the `.bbl` is untouched and three passes give
the ordinary build's 25 pages with no undefined reference. pdflatex is not installed on the packaging machine, so the pdflatex path was not
run here; `tests/test_arxiv_package.py` runs it wherever pdflatex is present (and skips otherwise) and runs the tectonic check wherever
tectonic is present. The page count is read from the log's "Output written on" line (pdflatex names the PDF, tectonic the XDV).

### Call 246: the arXiv metadata and the paper's license

`paper/dist/metadata.md` holds the title, an author line left to the user, the abstract of `main.tex` as plain text (it uses no macro),
the categories (stat.ML primary: a benchmark and scoring protocol for probabilistic forecasts with empirical-Bayes and kernel baselines;
cs.LG cross-list: the benchmark, the challengers, the leakage audit and the packaging; stat.ME cross-list: the rolling-origin design,
admission as a status, the planned standard error, decision value and gates in tests), the comments line (25 pages, 6 figures, 51
tables, the repository, the plan registration URL), the license (CC BY 4.0: both archives are CC BY 4.0, the code is MIT, the benchmark
is meant to be reused with attribution, and the license does not restrict a journal version) and the ancillary note (none; `figures.json`
if one is wanted). The abstract and the page count are to be reread against the final sources at upload.

### Call 247: the software citation, the changelog convention and the release checklist

`CITATION.cff` (1.2.0) names the software, version 1.0.0, the repository, the MIT license, keywords, a placeholder author line and a
placeholder release date, with commented slots for the Zenodo DOI and the arXiv identifier. The CHANGELOG gains an `[Unreleased]`
section on top (Keep a Changelog's convention) holding the 1.0.0 release notes drafted from the two review rounds in neutral words; the
heading becomes `[1.0.0] - <date>` at the bump, and `scripts/release_check.py` now reads the newest version entry past an Unreleased
heading, so the release check and `tests/test_release.py` keep passing. `.claude/fleet/release-checklist.md` lists the week's steps in
order with the ones that need the user marked: the version bump, the final build and clone test, the docs site, the arXiv check, the
visibility flip, the tag and GitHub release, the Zenodo DOI, the arXiv upload, and the citation updates after the identifiers exist.

### Call 248: the seed is dated at the fit clock when the ledger's last result is within the staleness limit of it (round 01, R2, minor)

`moot backtest` seeds `reliability-<source>.json` with every date set to the last result of the scored rows, and the staleness rule reads
that date against the wall clock, so on a ledger whose last result is a few days older than the first card the cell is a few days closer to
the 14 day limit than the clock of the fit says. Call 223 gave the fit a clock; the seed now uses it. `report.write_reliability` marks the
file it writes with `seed.last_result`, a mark the weekly join's rewrite drops, so a report a join has written is never touched.
`registry.date_reliability_seed` moves the report's `as_of` and every entry's `as_of` to the fit clock when the mark's date is at or before
the clock and no more than `RELIABILITY_MAX_AGE_DAYS` before it, and leaves the file alone otherwise; the mark keeps the date of the last
result, so a later fit judges the limit again. `fit_command` calls it, and `moot backtest` calls it through `date_seed_at_champion_fit`
with the champion's `fit_as_of`, because the quickstart fits first and seeds second. A ledger whose last result is older than the limit at
the fit clock keeps its seed and its one horizon of abstention; nothing is invented for it. No score, interval or table changes; only
the dates of an unjoined seed. Tests: `test_the_fit_dates_the_seed_at_the_fit_clock_when_the_last_result_is_within_the_staleness_limit`,
`test_the_fit_leaves_a_seed_alone_when_the_last_result_is_older_than_the_staleness_limit`,
`test_the_fit_never_redates_a_report_a_join_has_written`, `test_the_fit_without_a_reliability_file_writes_none`,
`test_a_seed_written_after_the_fit_is_dated_at_the_champions_fit_clock` and
`test_the_reliability_seed_records_the_last_result_it_is_dated_at`.

### Call 249: the outcome names the ledger snapshot that holds its row; the two run-length fields stay where they are (round 01, R2, nit)

The outcome record carried the card's snapshot id and not the ledger snapshot that holds the outcome row. `attach_outcomes` now takes the
snapshot as a function that is called once and only when a record is written, and each record carries `ledger_snapshot_id`: the snapshot
the join wrote when it appended rows, or the existing snapshot of the unchanged source rows (`ensure_snapshot` reuses one whose digest
matches, so a join that adds nothing writes nothing and a repeated join stays byte identical). Records the replay builds carry null. The
second half of the nit asked for `n_checkpoints` and `final_offset_days` to move into the `post_launch` block of the ASOS features. They are
left at the top level, as a decision: the move rewrites `features_json`, which changes every ASOS snapshot id and content digest the run
folders cite, and `scripts/paper_extras.py` reads `final_offset_days` there; that is a change of the ledger format and belongs to the tier
that moves numbers. The reading side is already closed, since the pre-launch view is an allow-list and drops both fields; a test holds it.
Tests: `test_the_outcome_names_the_ledger_snapshot_that_holds_its_row`,
`test_an_outcome_attached_by_a_join_that_added_no_rows_names_the_snapshot_of_the_ledger_it_read` and
`test_the_two_run_length_fields_of_the_asos_rows_reach_no_pre_launch_view`.

### Call 250: a join that brings outcomes older than the trailing window says so (round 01, R2, nit)

An outcome dated at or before the join clock minus the trailing eight weeks is scored and kept, but it is not in the window, so it dates no
reliability entry and a cell with nothing else in the window keeps its old date and ages. A team that missed joins for two months found
this out from the doctor. `JoinResult.n_outside_window` counts the scored outcomes of the join that fall at or before the window's edge,
and `moot join` prints one extra line when the count is not zero, naming the count, the attached total and the consequence. A join with
no such outcome prints what it printed before. Tests: `test_a_join_counts_the_outcomes_that_fall_before_the_trailing_window`,
`test_a_join_inside_the_window_counts_none_outside_it` and `test_moot_join_prints_one_line_when_outcomes_predate_the_window`.

### Call 251: a window of one test says so, and the entry is dated at the first outcome in the window (round 01, R2, minor)

The card printed "no interval is recorded in this reliability report" when the window held one test, although the interval was not
computable, not unrecorded. A window with `n_tests` below two now reads "fewer than two tests in the window, so no interval can be computed
and this number cannot be judged"; a report from before test ids were stored (`n_tests` null) keeps the old sentence, which is true of it.
The dating sentence is corrected where it was written (call 163 and the operations manual): an entry is dated at the join that finds its
first outcome inside the trailing window, which is what recovers a stale cell; ten outcomes are the minimum for drift evidence, so they gate
the clearing of a drift mark and nothing else. The operations manual sentence is the documentation builder's to change. Tests:
`test_a_window_of_one_test_says_fewer_than_two_tests_and_not_that_no_interval_is_recorded`,
`test_a_report_without_test_ids_still_says_no_interval_is_recorded` and `test_a_window_with_an_interval_prints_it`.

### Call 252: the doctor counts the cards no join will score (round 01, R2, minor)

Call 220 and call 222 gave the doctor the post-hoc and reissue counts. The other cards a join never scores are now counted per source on
the `cards <source>` line: no row id, a row id absent from the ledger, a row id of a test that is not admitted, and a horizon that has
passed at the doctor's clock with no outcome file yet. Each nonzero count is a warning and is named on the line; a source with none of them
and no outcome record is not listed, and a card whose row has not concluded is not a finding. The count reads the card files and the
ledger and writes nothing. The unadmitted count is the live record's conditioning on admission made visible; the admission rule itself is
call 254. Tests: `test_the_doctor_counts_cards_with_no_row_id_an_unknown_row_a_passed_horizon_and_an_unadmitted_test` and
`test_the_doctor_adds_no_card_counts_when_every_card_can_be_scored`.

### Call 253: the verification script names what is missing in one line (round 01, R6, minor)

`scripts/verify_readme_numbers.py` ended in a raw traceback when the data root held no report the page cites, or when the page was absent.
A missing data root or an empty reports folder already ended in one line. Now a report or glob the page needs that is not under the reports
folder ends the run with one line naming the file, the section that needs it and the `--reports` flag, with the folder of the published
reports of the paper, and an unreadable page ends with one line naming the page. The numbers it checks and the exit codes of a normal run
are unchanged. Tests: `test_the_verification_script_names_the_missing_report_in_one_line`,
`test_the_verification_script_names_a_missing_data_root_in_one_line` and `test_the_verification_script_names_a_missing_page_in_one_line`.

### Call 254: an admission rule that depends on realized counts is a policy, and the ledger's provenance carries it as one (round 01, R2, minor)

Not built. R2 asked for an admission rule that depends on realized counts to be written into the ledger's provenance. The rule is a
parameter of the source's loader (for Upworthy, a minimum of impressions and clicks per arm); the ledger records its outcome as a status
on each row and the backtest header counts the admitted and scored rows, so the rule's effect is visible and countable. Whether a launching
team should register such a rule before launch is a decision about its analysis plan, which the package cannot make for it: a rule that
conditions on realized counts is what the headline archive has, the paper states the conditioning and measures it in the admission
ablation . Writing the loader's rule
into provenance is a documentation line and not a change to a number or to a guard, so it is left to the operations manual.

### Call 255: the calibration percentile mid-ranks its ties within a tolerance, so it is the same on every platform (continuous integration, 5 November 2026)

Fixed. The percentile of the observed calibration error within the perfect-calibration null (`ece_percentile`, `ece_percentile_independent` and
`ece_equal_mass_percentile`) compared the observed value with each draw strictly and counted exact equality as half. The error of a draw
depends only on the number of events in each bin, so a draw that reproduces the observed counts is a mathematical tie, and such draws are
common: in the sample report 23 of 36 percentile calls have some, and one has 26 of 500. Whether floating point puts such a draw just below,
equal to or just above the observed value depends on the order in which the bin sums are added, and that order differs between builds of
numpy. The same seed therefore gave percentiles that differed by up to 1.1 points between macOS and ubuntu in the continuous integration run
(14 fields, the scores and every other value identical), and the worst case over the sample is 5.2 points (26 draws of 0.2 points each). The
draws themselves are the same on both platforms; nothing in the null is a Cholesky factor or a matrix product.

The rule is now a mid-rank: with `tol = 1e-9 * max(1, |observed|)`, the percentile is 100 times the number of draws below `observed - tol`,
plus half the number of draws within `tol` of the observed value, over the number of draws. Rounding noise cannot move a draw across the
tolerance, so the percentile no longer depends on the order of the additions. With no ties it equals the old value; on the sample ledger
32 percentile fields of the reference report move, by 0.5 to 2.6 points, because the old rule had counted the near-ties on one side. Every percentile in the
paper is regenerated by run 7 under this rule; the paper's tables and the claims register take their values from that folder. Tests:
`test_draws_that_tie_with_the_observed_error_count_half`, `test_rounding_noise_in_the_draws_or_in_the_observed_value_leaves_the_percentile_unchanged`
and `test_without_ties_the_percentile_is_the_share_of_draws_below`.

### Call 256: a card whose cell is not the cell of its ledger row is recorded unscored, and refused at issue (round 02, R2, minor)

Fixed. The join matched a card to its ledger row by row id alone. On a metric-keyed ledger the variant id carries the metric, so a typo or a
copied command line was enough to issue a card for one cell against the row of another: the reviewer's card for `checkout_conversion` on the
`revenue_per_user` row was accepted, joined, scored against the revenue result and fed to the checkout cell's window and drift rule. Three
changes. `attach_outcomes` compares the card's cell with the row's cell before it looks at timing or at the order of the candidates, and a card
that differs gets a record with `scored` false, `cell_mismatch` true and a reason naming both cells, with no score of any kind, so
`reliability_row` skips it and the row stays free for a card of its own cell. `moot join` counts these records on its summary line
(`JoinResult.n_cell_mismatch`) and `moot doctor` lists them beside the other cards no join scores. `moot card`, `POST /card` and the tool read the
ledger row of the card's row id with one filtered read of two columns and refuse a card whose cell differs (exit 1 on the command, 422 on the
service); no ledger, no such row or an unreadable ledger refuses nothing, because a card for a test that has not concluded is the normal case.
Not taken: refusing a card for a row the ledger already holds at issue (R2 suggestion 1), which is a rubric item proposed for round 03.
Tests: `tests/test_round02_b.py`, five tests whose names begin `test_r2_`.

### Call 257: the card's cell verdict is the cell's own-dependence verdict, and its backtest line comes first (round 02, R2, minor)

Fixed, and decision 10 of the launching team. `backtest_summary` copied `decidable_by_tests`, the verdict at the pooled archive's dependence, so a
card for the both cell of the headline archive printed "decidable at skill 0.20 only" where Section 6.2 reports the cell's own verdict, undecidable
at both skills (318 and 454 tests needed at the cell's own rows per test and correlation, 225 available). The summary now also stores
`decidable_by_tests_cell`, `gate_cell_n_200` and `gate_cell_n_400` for every cell, `backtest_view` reads the cell's own verdict first and falls
back to the pooled-dependence one only for a summary stored before the field existed, and a cell that is undecidable at its own dependence gets
the pooled figure, labelled, with the two gate sizes in the reason. The card prints the cell's latest gated backtest line first and the trailing
window line after it, and the window line ends "descriptive, one window of many", so the window reads as one draw and the gated figure as the
evidence a decision can lean on. The golden card text gains that clause. Tests: `test_r2_the_backtest_summary_copies_the_cells_own_verdict_and_its_two_gate_sizes`,
`test_r2_a_both_cell_card_prints_the_cells_own_undecidable_verdict_not_the_pooled_dependence_one` and
`test_r2_the_backtest_line_comes_before_the_window_line_and_the_window_line_says_it_is_descriptive`.

### Call 258: the backtest's fallback gates are the quick simulation `moot init` runs (round 02, R6, minor)

Fixed. With no gates file `moot backtest` ran a different simulation from the one `moot init` runs: per row at base rate 0.30 and interval level
0.95, against by test at 0.09 and level 0.90. A reader of tutorial 3 therefore saw a first card whose gate line counted rows, and adjusted bounds
that differed from the published ones in the fourth decimal because the Bonferroni family reads the gates' level. Both now call
`onboarding.write_quick_gates`: by test, at the simulated base rate nearest the ledger's own (the rates of `simulate.SOURCE_DEPENDENCE`, with that
rate's measured rows per test and correlation), at the release gates' interval level, with the quick replicate counts and no power table. `moot init`
passes the sample's rate and writes the same file as before, so the sample fixture does not move. The backtest names the ledger's rate and says that
the adjusted bounds read the gates file until `moot simulate gate-power` has run. Tests: `test_r6_the_quick_gates_are_by_test_at_the_simulated_rate_nearest_the_ledgers_and_level_090`
and `test_r6_moot_backtest_without_a_gates_file_runs_the_same_quick_simulation_as_init`.

**Correction, 5 November 2026 (round 03, R6).** The diagnosis above is wrong in one clause. The adjusted bounds of a fresh ladder-only run differ from the published ones because of the family of intervals, not because of the gates file: `family_size` is 20 for the ladder alone (P1 and P2 skill intervals plus P0, P1 and P2 log-score intervals over four cells) and 52 in the published report, which includes the challengers, and a fresh run on the unified quick gates gave the same adjusted bounds as before the change. The change itself stands and is what made every decidability key equal the published one. The note line of `moot backtest` now says that the adjusted bounds do not read the gates and depend on the family (20 intervals for the ladder alone, 52 with the challengers).

### Call 259: the report card's Gates section names the simulated base rate and reads the sizes at the rate nearest the ledger's (round 02, R6, minor)

Fixed. The card gave the gate sizes with no base rate while its Ledger section printed the ledger's own (0.067 on the sample), so a reader could not
tell the gates were simulated at 0.09. The Gates paragraph now ends "Simulated at base rate 0.09, the nearest simulated rate to this ledger's 0.067."
(on the heading line, so the card keeps its length), and the sizes in the table are those of `select_gates` at the ledger's rate, the reading the
backtest report's own tables already used; for a gates file with one base rate or none recorded nothing changes, and for a file at several rates the
card used to print the first rate's sizes whatever the ledger's rate. The card's JSON gains `gates_base_rate`. Test: `test_r6_the_report_card_names_the_simulated_base_rate_and_the_ledgers_own`.

### Call 260: the backtest report's first table drops the columns that repeat the by-test verdicts when the gates count tests (round 02, R6, minor)

Fixed. Against gates that count tests, `decidable` and `decidable_research` hold the same words as `decidable_by_tests` and
`decidable_research_by_tests`, and `decidable_by_tests_base_0.3` is empty on every row, while the heading said the by-row columns were beside the
by-test ones. The renderer now drops those three columns and words the heading "the gates count tests, so decidability is read by tests"; a per-row
gates file keeps them and the old heading. The JSON is unchanged, so the sample fixture of `make quick-check` does not move. Tests:
`test_r6_the_first_table_drops_the_repeated_and_the_fixed_rate_columns_when_the_gates_count_tests` and
`test_r6_the_first_table_keeps_the_by_row_columns_for_a_per_row_gates_file`.

### Call 261: a join with a missing input names the file and the step that makes it (round 02, R6, minor)

Fixed. `moot join --new-rows FILE` with a file that does not exist printed `error: <path>` and nothing else. It now prints
`error: new rows file not found: <path>; stage the week's results with moot ingest --ledger incoming/ledger.parquet first`, and a join with no
ledger prints `error: ledger not found: <path>; build it with moot ingest first`. The exit code stays 2, the convention of the join; one code for
every input error is R6 suggestion 1 and is not taken in this round. The same pass reworded the `--impressions-variant` help to "planned units",
like its sibling option, and dropped the design-call number from the `moot reliability` help. Tests: `test_r6_join_with_a_missing_new_rows_file_names_the_file_and_the_ingest_step`,
`test_r6_join_without_a_ledger_names_the_ledger_and_the_ingest_step`, `test_r6_the_impressions_variant_help_says_planned_units_like_its_sibling`
and `test_r6_the_reliability_help_names_no_design_call`; `tests/test_docs_run.py` gains a case that runs the README's `uv run --project` form of
`moot --version` from a folder outside the clone, as a guard on behaviour that already worked.

### Call 262: four table changes that print what the report files already hold (round 02, R1 and R5, no number moves)

Fixed in `paper/build_tables.py`, with no rerun. The learning-curve detail table prints P1's raw Brier score, the base Brier score of the full
history and of each subsample's own base rate, and P1's seed spread of the skill, because the earlier columns were skills only while the text spoke
of base rates (R1, major). The ablation table prints the paired P2 minus P1 log score with its by-test interval for the guard on and off, so the two
settings whose interval clears zero (admission on exposure alone, 0.0009; one contrast per test, 0.0005) are visible where "no setting moves the
score" is read (R1, minor). The positive-control gain table prints the oracle's interval beside its value (R1, minor). The three decision-interval
tables drop the "minus random" column and its Bonferroni-adjusted column, because the arm-count-matched columns beside them are the ones the
hypothesis reads and ten columns of intervals did not render legibly; the difference from plain random order stays in the JSON and is the captured
fraction minus the random row of the same table (R5, nit). Tests: `tests/test_round02_tables.py`, four tests.

### Call 263: the guard-pairs interval rests on 500 resamples, and the extras print the skill of the issued rows (round 02, R1, decision 2 and decision 9)

Fixed, and the one Tier C rerun of the round. `guard_pairs` resampled 1,000 times where every other interval of the paper uses 500, so its default
is now `SENSITIVITY_BOOTSTRAP` (500) and the pooled interval of the eight admitted pairs reads minus 0.00073 to 0.00245 where it read minus 0.00071
to 0.00253. The extras gain `issued_row_brier_skill`: for P1 and P2, the Brier skill with its by-test interval, the Brier score, the base Brier score
and the event rate of the issued rows, of the abstained rows scored on the forecast the rule withheld, and of all rows, by the aggregation and the
resample count of the main report (the all-rows entry equals the main table's pooled row). Pooled over origins and cells, so the composition of the
two row sets, the burn-in origin and the event rate, is part of the difference; decision 2 reads hypothesis 4 on this pooled skill with the
composition named. Stage `extras-upworthy` was rerun on a copy of run 7's ledger, models and reports (125 s) and replaced one file of
`paper/data/run7-tie-rank` through `assemble_run_folder.py --update`; every other file of the folder is byte-identical. The new key is
a number-neutral addition for every existing key. Tests: `test_the_extras_hold_the_issued_and_abstained_row_brier_skill_with_the_issued_base` and
`test_the_guard_pairs_bootstrap_defaults_to_the_count_every_other_interval_uses`.

### Call 264: the released headline bundle's stored backtest summary is regenerated from its own report (round 02, R2, decision 10)

Done on the headline data root. The summary a bundle carries is a pure function of the backtest report of its snapshot (`backtest_summary`), and
`attach_backtest` is the step `moot backtest` ends with, so it was applied to the existing report of the headline snapshot instead of running the
seven-minute backtest again: it rewrote the manifest of the champion `dd73c75e92bd` and its entry in the registry, and nothing else (the report
files are not touched, so no report number can move). The stored cells now carry the cell's own verdict and its gate sizes, and a card for the
both cell reads "undecidable at this n". A bundle fitted from now on reads the field from its report at `moot fit`. Test:
`test_r2_attaching_a_report_with_the_cell_verdict_refreshes_the_stored_summary_and_the_card_reads_it`.

### Call 265: the table formatter prints no signed zero (round 02, R4, nit)

Fixed. `f3` formatted a value that rounds to zero from below as "-0.0000", the one way a table from a fresh run was not byte-identical to the shipped one. A value that rounds to zero at the printed precision now prints as an unsigned zero, in `f3` and in `fr`, and every table was regenerated. Test: `test_r4_the_formatter_prints_no_signed_zero`.

### Call 266: the backtest header records the P2 selection rule (round 02, R3, minor)

Fixed. The header of a backtest report gains `p2_selection`, the rule P2 chose its weight and bandwidth by (`forward` by default, `loto` under `--p2-selection loto`), read from the recorded selections like `p2_guard`, and the Markdown header prints it. It is a number-neutral addition, so the committed sample fixture of `make quick-check` was regenerated and differs from the old one in that one header key. The run 7 reports keep their headers and carry no such key; the paper cites call 206 for their rule. Test: `test_r3_the_backtest_header_records_the_p2_selection_rule_in_force`.

### Call 267: the paired comparison behind the selection default is a shipped extras key (round 02, R3, minor)

Fixed. The comparison that changed the default, P2 under forward chaining minus P2 under leave-one-test-out, was computed for call 202 on run 5 files and not shipped. `p2_selection_comparison` in `scripts/paper_extras.py` reads the per-row score files of the main backtest and of the `p2-selection-loto` ablation, and with the guard off of `p2-guard-off` and `p2-selection-loto+p2-guard-off`, and holds the paired by-test difference pooled and at each origin with the 500-resample interval. On run 7, guard on: 0.0044 (0.0031 to 0.0057); guard off: 0.0024 (0.0006 to 0.0039); the reviewer's recomputation with more resamples gave 0.0030 to 0.0058 for the first. Stage `extras-upworthy` was rerun and one file of the run 7 folder replaced. Test: `test_the_extras_hold_the_paired_forward_minus_loto_comparison_pooled_and_by_origin`.

### Call 268: a card for a row whose result the ledger already holds is refused, and every refusal at issue exits 2 (round 03, R2.15)

Fixed. A card requested with `--now` before a test's start, for a row the ledger already held with its result, was accepted on the command and the service and scored as pre-launch evidence by the next join: the record could not tell that the result was known when the card was requested. `check_row_cell` now refuses, on `moot card`, `POST /card` and the tool (through `ServingState.issue`), any row id the ledger holds: with another cell it is the call 256 refusal, with the card's own cell it is "row id X is in the ledger with its result; a card for it would not be pre-launch evidence". A card for a test that has not concluded is unaffected. The refusal of call 256 and this one are ValueErrors and leave the command through the same wrapper as the other refusals at issue (an origin before the fit cutoff, an origin after the issue time, a foreign source id): one line and exit 2, where call 256 had exit 1. The service answers 422. On the headline archive the timing rule reads the start of the contrast, which `sources/upworthy.py` sets to the later of the two arms' creation times, so a card for a variant added to a running test is pre-launch evidence for that contrast. Tests: `test_r3_moot_card_refuses_a_row_whose_result_the_ledger_holds_even_at_a_backdated_now`, `test_r3_post_card_refuses_a_row_whose_result_the_ledger_holds`, `test_r3_the_tool_refuses_a_row_whose_result_the_ledger_holds` and `test_r3_the_cell_mismatch_refusal_exits_2_like_its_siblings`.

### Call 269: Figures 1 and 2 are drawn at the width they are included at (round 03, R7)

Fixed. The coverage figure and the decision-value figure were drawn at a full column and included at 0.62 of it, so their type printed at about 4 pt. `scripts/paper_figures.py` now draws both at 0.62 of the column width (`INCLUDE_FRACTION`) with an 8 pt body type size (`BODY_RC`): the two coverage panels are stacked, the decision-value legend sits under the axes in two columns, and the label "random order (K over n)" is shortened to "random order" (the caption keeps the definition). The plotted values and `figures.json` are unchanged. Test: `test_figures_one_and_two_are_drawn_at_the_width_they_are_included_at_with_the_body_type_size`.

### Call 270: a report column that is null on every row is left out of the Markdown and named below the table (round 03, R6)

Fixed. The "P2 selection by cell" table printed `half_life_days_median` as n/a on every row of the sample and archive reports, the "not computed" column of round 02 under another name. The Markdown renderer now leaves out any column of a table that is null on every row and ends the table with one line: "Columns not computed (null on every row) and left out: a, b." The JSON is unchanged, so no report moves and the sample fixture of `make quick-check` is untouched. Tests: `test_r3_the_report_tables_omit_a_column_that_is_null_on_every_row_and_say_so` and `test_r3_the_p2_selection_table_of_the_sample_report_drops_its_all_null_half_life_column`.

### Call 271: the per-origin keys of the first and third hypotheses are shipped extras keys (round 03, R1.15)

Fixed. `p1_minus_p0_by_origin` holds the paired log-score difference of P1 over P0 pooled and at each origin with a by-test interval at 500 resamples (pooled 0.1493; the interval excludes zero at all nine origins, narrowest January 2015, 0.0681, 0.0384 to 0.0972). `issued_ece_by_origin` holds the ECE of the issued P1 cards and its percentile in the clustered null drawn at each origin's own design effect (500 draws): pooled 0.01508 at percentile 100.0, inside the central 90 percent at 4 of the 8 origins that issue cards (92.2, 100.0, 27.4, 92.9, 100.0, 95.8, 99.6, 79.3 from July 2013 to April 2015), and 4 of 9 on all rows. Both reproduce the reviewer's recomputation exactly. Every existing key is unchanged; stage `extras-upworthy` was rerun and one file of the run 7 folder replaced. Tests: `test_the_extras_hold_the_paired_p1_minus_p0_difference_by_origin` and `test_the_extras_hold_the_ece_percentile_of_the_issued_cards_by_origin`.

### Call 272: one interval per quantity in the guard-pairs tables, and two table rows (round 03, R3 and R1)

Fixed in `paper/build_tables.py`. The pooled realized P2 minus P1 difference of the eight admitted pairs printed two different 500-resample intervals, minus 0.0007 to 0.0025 in Table guard-pairs and minus 0.0007 to 0.0027 in Table guard-pairs-rows. The rows table now reads the interval of the pooled mean from `guard_pairs.summary`, the key Table guard-pairs prints, so both show 0.0010 (minus 0.0007, 0.0025); its location and scale parts keep their own intervals, and its header comment says so. The rows table also prints the median with its interval, which the file held and the table dropped. The paired ablation column prints five decimals, so a bound of minus 0.00002 no longer reads 0.0000. Tests: `test_r3_the_rows_table_prints_the_median_interval_and_the_one_pooled_interval_of_the_guard_pairs_table` and `test_r3_the_paired_ablation_column_prints_five_decimals`.

### Call 273: the number audit matches the report leaf first (round 03, R4 and decision 30)

Fixed. `scripts/paper_audit.py` matched a printed number to the digits of its `% src:` comment before the report's leaf, so a comment that carried rounded digits (0.05385 for a leaf of 0.053846) let a double-rounded number (0.0539) pass. The order is now the report leaves, the tables, then the comment, and a number that matches only a comment number which is itself a rounding of a leaf of the named reports is listed as unmatched. A derived number that no leaf carries still passes on its comment. On the paper as it stands the audit finds 773 numbers (753 by leaf, 20 by comment) and none unmatched. Tests in `tests/test_round03_audit.py`.

### Call 274: why the matched decision value is zero on the deployment-shaped archive (format pass, 5 November 2026)

A reading, not a code change. The features of the deployment-shaped archive are the metric and the number of variants, so a test's score is a function of its number of arms. Ties within an arm stratum are chosen with equal probability, and `_matched_value` in `src/mootcourt/decision_value.py` then returns the chosen set's own expected value. The difference from the arm-count-matched order is therefore zero at every origin by construction, while the difference from random order is not.
