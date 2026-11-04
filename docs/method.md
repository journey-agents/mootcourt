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
nothing to score and is the only kind left out. Recovery needs outcomes, so a cell that abstains for staleness recovers after the first
ten outcomes of its abstained cards arrive and one join that is not below threshold.

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

On the archives the card-path default (the data end is the newest `usable_after`) drops the trailing quarter of each ledger from the level: on Upworthy 2015Q2 (321 rows, the newest result is 6 May 2015), whose
level is replaced by that of 2015Q1 (1,135 rows), and on ASOS 2021Q1 (40 rows, newest result 26 February 2021). Those rows still enter the global and the cell fits (13,453 of 13,453 and 381 of 381 rows). The rule
is calendar-level: a quarter is kept when its last day is on or before the data end's day, so a data end on 30 June keeps the second quarter and 29 June drops it. The empirical-Bayes period variance would weight a
thin or noisy period instead of dropping it; it is future work.
