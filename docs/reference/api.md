# Python API

The command line is the supported interface. The modules below are importable and documented from their docstrings. A
function not listed here is internal and may change in any release.

## Ledger

::: mootcourt.ledger
    options:
      show_root_heading: true
      members:
        - read_ledger
        - write_ledger
        - validate_ledger
        - visible_rows
        - snapshot_id
        - ensure_snapshot
        - append_rows

## Predictors

::: mootcourt.predictors.p0
::: mootcourt.predictors.p1
::: mootcourt.predictors.p2

## Bundle and registry

::: mootcourt.bundle
    options:
      members:
        - ModelBundle
        - fit_bundle
        - save_bundle
        - load_bundle

::: mootcourt.registry
    options:
      members:
        - Registry
        - find_scores

## Card

::: mootcourt.card
    options:
      members:
        - CardRequest
        - Card
        - build_card
        - to_json
        - to_markdown

## Backtest

::: mootcourt.harness
    options:
      members:
        - rolling_origin
        - default_rungs
        - quarterly_origins

## Simulators

::: mootcourt.simulators.base
    options:
      members:
        - SimulationRequest
        - SimulationResult
        - SimulatorInfo
        - ResponseSimulator

::: mootcourt.simulators.stdio.StdioSimulator
::: mootcourt.simulators.http.HttpSimulator

## Benchmarks

::: mootcourt.benchmark
    options:
      members:
        - run_scale
        - run_report_card
