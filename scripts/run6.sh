#!/bin/bash
# Run 6: every experiment downstream of P2 under the forward-chaining default (docs/method.md call 206), produced once by the final code.
# Usage: scripts/run6.sh [JOBS]      (needs MOOTCOURT_DATA_ROOT; run only on the lead's "run 6 go")
# Steps, each logged under $X/logs with the prefix run6- and its exit code in stages.txt:
#   1. a staging root $X/root (ledger copied, gates.json copied from run 5: simulations, independent of P2) and the full driver
#      scripts/run_experiments.sh : gate-power, fits and main backtests with all challengers, the positive control and its 11,100 test rung
#      backtest, ablations (leave-one-test-out as the counterfactual), learning curves and the cautionary run at 500 resamples, replays, guard
#      comparison, paper extras (every key), leakage audits, card latency, refresh_discrimination --check
#   2. archive the run 5 reports, models and cards of the data root under archive-pre-run6, swap the staging reports, models and cards in
#   3. refresh_discrimination on the data root (the within-stratum, planned-event and decision-value columns, all from the stored scores)
#   4. paper/data/run6-forward-chaining from run 5 (scripts/assemble_run_folder.py) and paper/tables from it
# The seeds are those of run 5 (backtest seed 0, bootstrap 500, power seed 20261102 in the reused gates).
set -u
JOBS="${1:-4}"
D="${MOOTCOURT_DATA_ROOT:?export MOOTCOURT_DATA_ROOT}"
X="$D/experiments/run6"
PY="${PY:-.venv/bin/python}"
mkdir -p "$X/root/reports" "$X/logs"
[ -d "$X/root/data" ] || cp -R "$D/data" "$X/root/data"
# gates.json is simulated again by the driver (gate-power, about 14 minutes) so the folder is one code state
[ "${SKIP_DRIVER:-0}" = 1 ] || MOOTCOURT_DATA_ROOT="$X/root" OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" bash scripts/run_experiments.sh "$X/logs" "$JOBS" || { echo "the driver failed" >&2; exit 1; }
if grep -v "^experiments-done" "$X/logs/stages.txt" | grep -vE " 0( |$)" | grep -v "^gates 0" | grep -v "failed-layout" | grep -q .; then echo "a stage failed: see $X/logs/stages.txt" >&2; exit 1; fi
A="$D/archive-pre-run6"
mkdir -p "$A"
for k in reports models cards; do [ -d "$A/$k" ] || cp -R "$D/$k" "$A/$k"; done
for k in reports models; do rm -rf "$D/$k.new"; cp -R "$X/root/$k" "$D/$k.new"; mv "$D/$k" "$D/$k.old-run5"; mv "$D/$k.new" "$D/$k"; done
cp "$A/reports/scale-"*.json "$D/reports/" 2>/dev/null       # wall-time measurements of the scale benchmark: not repeated (README says so)
# the timed run on a quiet machine writes run-log.json (and a fresh gates.json from its power stage, which the driver's equals): run it by itself,
# after this script, with MOOTCOURT_DATA_ROOT pointing at a new empty root: scripts/timed_run.sh; then copy its reports/run-log.* to the data root and the run folder
"$PY" scripts/refresh_discrimination.py "$D/reports" > "$X/logs/run6-refresh.log" 2>&1 || exit 1
"$PY" scripts/assemble_run_folder.py "$D/reports" paper/data/run5-period-rule paper/data/run6-forward-chaining > "$X/logs/run6-assemble.log" 2>&1 || exit 1
make tables RUN=paper/data/run6-forward-chaining > "$X/logs/run6-tables.log" 2>&1
echo "run6-done" >> "$X/logs/stages.txt"
