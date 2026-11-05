# Changelog

This project follows [semantic versioning](https://semver.org). Before 1.0.0 a minor version may change the ledger
schema, the card schema or a command line option; the change is listed here and the schema versions are bumped.
The format follows [Keep a Changelog](https://keepachangelog.com).

## [1.0.0] - 2026-11-05

Release notes for 1.0.0, from the four review rounds of the paper (rounds 00 to 03).

### Changed

- P0 is the empirical base-rate forecaster: its significant-positive probability is the visible event rate, so its Brier skill is zero by
  construction and every other rung's skill is read against it.
- P2 issues P1's own Student-t predictive with the location and the scale moved by the admitted precedents; weight zero returns P1's
  predictive exactly, and a two-standard-error admission guard on the validation gain keeps the weight at zero when nothing transfers.
- P1 takes its period level from the last complete calendar quarter; a partial trailing quarter sets no level.
- The feature space is pairwise where the rows carry a reference headline (variant, reference, difference and pair features), and a card
  issued without a reference headline says so.
- Every score is the analytic Student-t marginal; the calibration null is clustered by test; coverage is reported within deciles of the
  ratio of realized to planned standard error; the gates are counted in tests at the archive's base rate with within-test dependence.
- Decision value is measured against an exact random order with by-test intervals and Bonferroni-adjusted bounds, at three budgets.
- An abstained card keeps the forecast it withheld in its frozen file, the weekly join scores it and it feeds the reliability report; a card issued at or after its
  test's start is recorded as post-hoc and never scored; one card per row is scored, the earliest pre-launch one.
- The card's skill line prints the cell's own gated figure when the cell is decidable, and the pooled one otherwise, saying so.
- The sample ledger of `moot init` has a significant-positive rate near the headline archive's (0.09) and the quick gates are simulated at
  that rate; the Request line of a card without text prints no headline fields.
- The source distribution holds the package, its examples and its tests; the paper's run folders stay in the repository.
- The precedent rung selects its settings by forward chaining, from the origins before the one it forecasts (call 206); leave-one-test-out stays as the ablation `p2selection_loto`, and the paired forward minus leave-one-test-out difference of the rung's log score is a shipped report key (`p2_selection_comparison`).
- The calibration null's percentile uses a mid-rank tie rule within a relative 1e-9 (call 255), so it is the same on every platform; under the previous strict comparison floating-point ties moved it by up to 1.1 points between macOS and ubuntu on the same seed.
- A card whose cell differs from its ledger row's cell is recorded unscored at the join, counted by `moot doctor`, and refused at issue by `moot card`, the service and the tool (call 256).
- The card prints the cell's own-dependence gate verdict, with the backtest line before the window line.
- The seed is dated at the fit clock when the ledger's last result is within the staleness limit; the outcome record carries the ledger snapshot id that holds the outcome row; a join that attaches outcomes older than the trailing window says so (calls 248 to 250).
- Backtest report headers record the selection rule in force (`p2_selection`).
- Table output prints an unsigned zero, so a table built from a fresh run is byte-identical.

### Added

- The challengers (a precision-weighted tuned boosted model, a local empirical-Bayes comparison set, a pairwise TF-IDF classifier), each
  raw and Platt-recalibrated on visible rows, scored on identical rows and tests as the ladder.
- The positive control: a planted text lift on the synthetic archive, with the guard's admission by size and lift and the realized
  held-out gain of the precedent rung against the oracle that knows the lift; the text classifier and the boosted model on the same ledger.
- The admitted guard pairs row by row, with the realized difference split into a location part and a scale part.
- The learning curve, the weekly replay of each archive, the leakage audit, the guard comparison, the trigger-removal ablations and the
  paper extras, each written as a report JSON that the paper's tables trace to.
- Response simulators attached over stdio or HTTP, recorded and replayed, with a stacking weight that is earned out of time.
- `make tables`, `make paper` and `make arxiv`: the tables, the figures, the PDF and the arXiv source package from the run folder, with
  provenance lines relative to it; a per-platform score report from the continuous-integration job; a test that every caption number
  traces to a source.
- `moot doctor` counts, per source, cards with no row id, with a row id absent from the ledger, with a passed horizon and no outcome, and cards on an unadmitted test (call 252).
- `make quick-check` (the sample ledger's backtest regenerated and diffed against a committed reference, percentile fields within two points), `make selfcheck` (the release gate: markers, number audit, source resolution, writing rules, the paper build, table byte-identity, docs currency, the claims audit, the release check), `scripts/run_experiments.sh --list`, `--only` and `--dry-run` for stage-only reruns, and `scripts/assemble_run_folder.py --update`.
- The claims register (`paper/reviews/claims.md`) and `scripts/claims_audit.py`, which checks every printed claim value against its report key.
- The learning-curve detail tables print the raw Brier score, the base scores and the seed spread; the ablation table prints the paired difference column; the positive-control table prints the oracle interval.
- The README verification script prints one line instead of a traceback when a report or the page is missing.

### Fixed

- A first run that scored relative lift at the realized standard error let post-launch information into a pre-launch forecast; the
  protocol scores the absolute effect at the planned standard error, and the first run is kept as the cautionary table.
- A ledger ending inside a quarter gave P1 a period level from a few days of data, which the guard then read as a precedent gain.
- The log score on the grid dropped the Student-t mass beyond the grid edge; the analytic marginal replaces it.
- Storage: every heavy read goes through the data root; a run folder is read as a data root with the standard layout.
- The table builder ordered the oracle and arm-count rows by hash seed; policy name is now the tiebreaker, with a determinism test.
- The first-card tutorial printed the interpreter version, the environment path and the free space; the documentation runner masks them.
- `aggregate_scores` no longer requires a row id column.

## [0.1.0] - unreleased

First release.

### Added

- The ledger: one row per contrast, with a schema, admission status, immutable snapshots and a content digest.
- The predictor ladder: P0 (cell base rate), P1 (pooled shrinkage by cell), P2 (weighted precedents shrunk toward P1,
  with an admission guard on the weight), and the challengers GBM, local empirical Bayes and a text-only classifier.
- The rolling-origin harness: scores, bootstrap intervals by test, gates for decidability, calibration by precision,
  abstention and decision value.
- The card: issued or abstained, with the reasons, the precedents that carry the forecast, a robustness note and
  frozen, content-addressed JSON.
- Reliability: a weekly join of cards with outcomes, drift detection and a reliability report that gates the next card.
- Sources: a synthetic generator, the Upworthy Research Archive and the ASOS digital experiments dataset, each ingested
  from a pinned, checksummed download.
- Importers for vendor exports and a generic exchange format, with mapping files.
- Response simulators: attach an outside agent over stdio or HTTP, backtest it once, replay it for free, and give it a
  stacking weight only after it earns one out of time. Failures are recorded and never cached.
- A service (`moot serve`), a read-only MCP server and a model registry with champion and challenger promotion.
- `moot init` and `moot doctor` for onboarding and health checks.
- Several metrics per contrast and guardrail cards.
- The scale benchmark (`moot benchmark --scale N`) and the organization report card (`moot benchmark --ledger FILE`).
- A documentation site built with mkdocs, a CPU Dockerfile and a continuous integration workflow.

### Changed before release

- The Upworthy final read and `usable_after` are test level: seven days after the creation of the latest arm of the test. The status
  counts are unchanged and the headline scores moved in the fifth decimal at most.
- The earn-weight gate and the promotion gate count tests, not rows. `backtest_summary` stores `n_tests`.
- The report card states the interval level it computes and the power targets it reads from the gates file, writes quick gates to
  `reports/benchmark/gates-quick.json`, and has report card schema version 2.
- `effect_unit` is checked against `absolute`, `relative`, `standardized` and `as_exported`, and rows pooled in one cell must share a unit.
- The MCP tool `get_card` takes `source` and `impressions` first, because optional arguments must follow required ones, so the order of its
  arguments changed. A client that calls the tool by argument name is unaffected.
- Ledger rebuild: a ledger file written before these changes is rebuilt from its source files with `moot ingest`, not edited. An Upworthy ledger
  written before the test-level final read must be rebuilt, because `append_rows` treats a changed `usable_after` as a conflict. `moot ledger check`
  on a ledger Parquet file now reads each row's unit and vendor and reports a cell that pools two units, a unit outside the documented set, and an
  `as_exported` cell that holds rows from two vendors. An import names a row id that two different experiment, variant and metric ids would share.
  A count above 2**53 is rejected exactly, and a Parquet null in a nullable integer count is a one-line error.
- The docker job of the continuous integration workflow runs `moot --version` as its own step and fails when `moot doctor` crashes, not only
  when it exits above 1. Dependabot uses the `uv` ecosystem so that its pull requests update `uv.lock`.
- `moot simulators list` prints the weights that a newer version of a provider displaced. The credential scrub keeps `PIP_CERT` and `NO_PROXY`.
- Bad inputs end in one line and exit code 2; `MOOTCOURT_DEBUG=1` restores the traceback.
- Every read of a folder under the data root skips dot files, so the AppleDouble sidecars of exFAT volumes cannot break a command.

### Changed after the round 00 red-team review

- P0 is the empirical base-rate forecaster of the visible ledger (its `p_sig` is the visible event rate, so its Brier skill is zero by construction); the statement that each rung is a strict generalization of the one
  below is replaced by what each rung adds. The P2 predictive is a Student-t of P1's family at every lambda (moment matched), and the selection scores every candidate, the lambda 0 baseline included, with that predictive.
- Card schema version 2: the card stores its predictive (family, degrees of freedom, location, scale, grid and the planned standard error), the interval for the true effect and the interval for the observed estimate, a frozen
  `withheld` forecast on an abstained card, and a skill line with the interval, the test count and the gate verdict. The weekly join and the replay score outcomes with the stored predictive, and an abstained card is scored on the forecast it withheld (flagged,
  not dropped), so a stale or drifted cell recovers; the two paths share one code path.
- `moot card`, `POST /card` and the MCP tool `get_card` accept a row id (or the ledger row key), the planned exposures of the two arms and the reference headline. Champion refresh: a refit of the same method on a newer fit replaces the
  champion without the challenger margin (`method_id` in the manifest and the registry); a different method still needs the margin.
- `moot simulate gate-power` sizes the gates by test at one or several base rates (default 0.09, 0.14 and 0.30) with a 90 percent interval; `gates.json` gains `by_base_rate` and `interval`, and the harness reads each group's gate at the nearest base rate and keeps the
  0.30 gate as the column `decidable_by_tests_base_0.3`.
- Report tables: `coverage_by_se_ratio`; a perfect-calibration null clustered by test with the design effect, the independent percentile and an equal-mass ECE; decision value with exact random order, a bootstrap interval for every fraction, regret and difference from random
  order, budgets of 10, 25 and 50 percent, every challenger and a note; Bonferroni-adjusted bounds (`adjusted_lo`, `adjusted_hi`) on the aggregate and year tables; the counts of tests in the ledger, admitted and scored; the P2 guard setting in the header; the direction accuracy on decisive rows.
- The feature space reads the reference headline where the ledger has one (variant, reference and difference blocks, and three pair features), so the feature hash and every model id changed; `--pairwise off` restores the single-headline space. The GBM is precision weighted
  and tuned on the latest visible rows; every challenger gets a recalibrated rung (Platt map fit on out-of-fold predictions of visible rows only; `--no-recalibrate`, `--recalibration isotonic`).
- Ablations: the feature, bandwidth, selection, recency and pairwise ablations also run with `--p2-guard off`; `--admission prelaunch` admits on exposure only (ablation); `moot simulate ledger --text-effect` plants a text signal for the positive control.
- The learning curve drops the direction baselines. The decision-value rows of a benchmark card read the 25 percent budget.

### Changed after the review of chunk L (chunk N)

- The log score of y for every predictive built from a location-scale family (P1, P2, the card, the weekly join, the replay, the drift flag) is the analytic marginal of the stored Student-t (or Normal),
  the quantity the lambda selection and the P1 likelihood already used; the grid serves intervals, probabilities and the CRPS. Every log score of run3 moved (P1 by 0.025 nats on Upworthy, 0.099 on ASOS).
- The weekly join and the reliability report tolerate outcome files without a test id (`n_tests` None, "no interval is recorded"). The by-row `decidable` column reads "not computed: the gates count tests"
  when the gates file counts tests. The clustered calibration null solves its latent correlation to reproduce the observed design effect (`latent_rho`). The gate simulation draws dependent rows within a test with the
  measured correlation of each source (`SOURCE_DEPENDENCE`, `--icc`), so the gates are larger. The Bonferroni family counts the intervals reported.
- The leakage audit wraps the construction of `GBMChallenger`, `LocalEB` and `TextLR`. Champion refresh needs strictly newer data (`data_through`), holds a same-method fit without a backtest as pending until the summary is attached, and writes the reason of every challenger in the history.
- Smaller: exposure bound, MCP refusals as messages, the variant exposure to the simulator, neutral pair features without a reference, the learning curve on the recorded admission, row id checks, P0 variance floor, P1's predictive for a far query,
  `method_id` covering the feature space, GBM calibration subsample, relative robustness threshold, finite guardrail margins, the join's baseline from the card's own P0 (the card stores P0's variance).
- Learning curve: every point is scored against the full-history P0 (`skill`), the subsample base rate is kept as `skill_own_base`, the rows carry `n_history_tests` and `n_scored_tests`, and the bootstrap uses the `--bootstrap` setting (500) instead of 200 (docs/method.md call 204). Aggregate rows: `auc_*_within` and `resolution_*_within`, discrimination within (origin, cell) strata (call 203).
- Decision-value table: the policies `arm_count` and `random_matched` and, for every `p_win` rung, `diff_matched` (difference from random order matched on the number of contrasts) with unadjusted and adjusted bounds; a test of H5 reads against it (docs/method.md call 201).
- Decision-value table: Bonferroni-adjusted bounds for the captured fraction, the regret and the difference from random order, with `family_size` (the rungs compared with random order in the pooled rows; docs/method.md call 200).
- After the review of chunk N2: P1's period level comes from the last complete quarter (a quarter whose end is after the fit's data end sets no level; `P1Predictor.fit(rows, data_end=None)`); fits at other dates change (the bundles of `moot fit`, hence the card path), the quarterly backtests do not. The synthetic guard diagnostics are rerun: with no planted signal the guard admits at 0.00 to 0.06 of cells at every size (it was 0.67 at 3,700 tests and 0.39 at 11,100), and `guard_period_control` records the mechanism. `guard_held_out_gain` scores the best candidate's own held-out gain with clustered standard errors. `scripts/refresh_discrimination.py` counts skipped reports and handles the multi-metric blocks. `make paper-figures` defaults to `paper/data/run5-period-rule`.
- After the review of chunk N: the `resolution_*` columns are the Murphy resolution over equal-mass forecast bins (they were forecast spread); the positive-control sensitivity point is 11,100 tests (about 7,400 rows per cell); a champion
  without `data_through` gets it derived from its bundle; `moot fit` says a refresh is pending and that `moot backtest` decides it; the P2 search returns P1's predictive below the float32 kernel range; a missing exposure is filled with the exposure
  column's mean and `list_precedents` takes an `exposure`; `moot init` writes quick gates by test at 0.90; `gate_verdict` compares rows with a per-row gates file.
- Reports: AUC and the Murphy resolution term per rung (`auc_event`, `auc_direction`, `resolution_event`, `resolution_direction`, with intervals); a sensitivity of the event defined on the planned standard
  error (score columns `event_planned`, `brier_planned`, `p_base_planned`, `brier_base_planned`; aggregate columns `event_rate_planned`, `p_sig_mean`, `brier_planned`, `brier_base_planned`, `brier_skill_planned`
  with `_lo` and `_hi`); `guard_pairs` in the paper extras; the positive-control sensitivity gains a ledger of 3,700 tests.

### Security

- The HTTP simulator adapter ignores proxy settings and refuses redirects and non-loopback hosts unless allowed.
- The stdio simulator adapter runs without a shell in its own process group, strips credential-like environment
  variables, bounds its output and refuses to run a command from the data root. The group is killed on every exit path, and the
  data-root refusal covers the working directory, `-m` modules, `--opt=path` arguments and letter case.
- The HTTP simulator adapter enforces its time cap as a wall clock for the whole exchange. A config table can no longer grant `allow_remote`.
- `moot serve` on a loopback address accepts only loopback names in the Host header, and its own bind address.
- The download script contacts OSF hosts only, over https, and refuses an ambiguous or a missing approved file name.
- The HTTP simulator adapter shuts down its socket when the time cap is reached, so a server that sends its status line or headers slowly cannot keep a connection open.
- The data-root refusal reads `-mmodule`, the words of a `sh -c` string and `:` separated lists.
