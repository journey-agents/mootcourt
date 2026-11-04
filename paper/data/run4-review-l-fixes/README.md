Run 4 (review of chunk L fixes, 3 Nov 2026): every report of the full rerun after the fixes of task T-056 (chunk N), from `scripts/run_experiments.sh` into a staging root, then copied to the data root. The method changed again (analytic scoring of the predictive, clustered calibration null with a solved latent correlation, gates with within-test dependence, champion refresh by newer data), so this is a new folder beside `run3-round00-fixes`.

- The layout is the same as run 3: three main backtests with challengers and `+cal` rungs, `ablations/`, `positive-control/`, `gates.json`, `card-latency.json`, learning curves, replays and paper extras.
- `gates.json` now holds gates by test with the source dependence stated per base rate (rows per test and intraclass correlation).
- `run-log.json` is from the timed run on pre-placed archives (no download), data root `timed-run-n`.
- The cautionary run's per-row scores stay on the data root; `paper/build_tables.py` reads them from there.
