# Changelog

This project follows [semantic versioning](https://semver.org). Before 1.0.0 a minor version may change the ledger
schema, the card schema or a command line option; the change is listed here and the schema versions are bumped.
The format follows [Keep a Changelog](https://keepachangelog.com).

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
- Card schema version 2: the card stores its predictive (family, degrees of freedom, location, scale, grid and the planned standard error), the interval for the true effect and the interval for the observed estimate, a sealed
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
