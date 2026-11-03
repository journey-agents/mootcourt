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
