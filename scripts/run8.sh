#!/bin/bash
# Run 8 (paper version 2 plan, docs/superpowers/plans/2026-11-06-paper-v2-plan.md): the pipeline of run 7 on a ledger that applies the date rule of the archive's
# June 2024 randomization notice (decision D1: a test that started from 2013-06-25 to 2014-01-10 gets the status imbalance_flag), plus the new experiments.
# Usage: scripts/run8.sh [JOBS]      (needs MOOTCOURT_DATA_ROOT; run only on the lead's go)
# Steps, each logged under $X/logs with its exit code in stages.txt:
#   0. check that the ablation setting regenerates run 7's ledger: the Upworthy rows rebuilt with the rule off must have run 7's content digest (4bfb354b87e3)
#   1. a staging root $X/root (data copied; the Upworthy rows of its ledger rebuilt with the rule ON; gates.json is simulated again) and the full driver
#      scripts/run_experiments.sh: gate-power, fits and main backtests, the positive control, ablations (now also the ablation that includes the randomization window,
#      relative lift at planned precision, absolute effect at realized precision, exposure fixed at the cell median), learning curves (now with the paired
#      differences from P1), replays, guard comparison, the gates simulated at each stratum's own dependence, paper extras (now with the keys of X1 and X4 to X9),
#      leakage audits, card latency, refresh_discrimination --check
#   2. refresh_discrimination on the staging reports (the data root's reports, models and cards are NOT swapped: run 7 stays where it is)
#   3. paper/data/run8-randomization-window from run 7 (scripts/assemble_run_folder.py); the paper tables are checked to build from it into $X/tables-check
#      (paper/tables is not touched: the text pass regenerates it)
# The seeds are those of run 7 (backtest seed 0, bootstrap 500, power seed 20261102). The timed run is not repeated: run-log.json and run-log.md stay run 7's.
# DRY_RUN=1 scripts/run8.sh : run step 0 (the ledger check, a few seconds), print the stages the driver would run, and stop.
set -u
JOBS="${1:-4}"
D="${MOOTCOURT_DATA_ROOT:?export MOOTCOURT_DATA_ROOT}"
X="$D/experiments/run8"
PY="${PY:-.venv/bin/python}"
RUN7=paper/data/run7-tie-rank
export RUN7_UPWORTHY_DIGEST=4bfb354b87e3
# X10 (sizing) runs (design note approved 6 November 2026); SKIP_SIZING=1 skips it
export SKIP_SIZING="${SKIP_SIZING:-0}"
mkdir -p "$X/root/reports" "$X/logs" "$X/check"
RUN7_REPORT="$(ls "$RUN7"/backtest-upworthy-*.json | head -n 1)"
export RUN7_REPORT
RUN7_SCORES="$D/reports/scores-upworthy-${RUN7_REPORT##*backtest-upworthy-}"
RUN7_SCORES="${RUN7_SCORES%.json}.parquet"
export RUN7_SCORES
if [ "${SKIP_DRIVER:-0}" != 1 ]; then
  "$PY" scripts/rebuild_upworthy_ledger.py --window off --ledger "$D/data/ledger/ledger.parquet" --out "$X/check/ledger.parquet" --expect-digest "$RUN7_UPWORTHY_DIGEST" \
    > "$X/logs/run8-check-ablation-ledger.log" 2>&1 || { echo "the ablation does not regenerate run 7's ledger: see $X/logs/run8-check-ablation-ledger.log" >&2; exit 1; }
  cat "$X/logs/run8-check-ablation-ledger.log"
  if [ "${DRY_RUN:-0}" = 1 ]; then
    echo "stages the driver would run:"
    bash scripts/run_experiments.sh --dry-run | tr '\n' ' '
    echo
    exit 0
  fi
  [ -d "$X/root/data" ] || cp -R "$D/data" "$X/root/data"
  MOOTCOURT_DATA_ROOT="$X/root" "$PY" scripts/rebuild_upworthy_ledger.py --window on > "$X/logs/run8-rebuild-ledger.log" 2>&1 || { echo "the ledger rebuild failed" >&2; exit 1; }
  MOOTCOURT_DATA_ROOT="$X/root" OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" bash scripts/run_experiments.sh "$X/logs" "$JOBS" || { echo "the driver failed" >&2; exit 1; }
fi
if grep -v "^experiments-done" "$X/logs/stages.txt" | grep -vE " 0( |$)" | grep -v "^gates 0" | grep -v "failed-layout" | grep -q .; then echo "a stage failed: see $X/logs/stages.txt" >&2; exit 1; fi
"$PY" scripts/refresh_discrimination.py "$X/root/reports" > "$X/logs/run8-refresh.log" 2>&1 || exit 1
"$PY" scripts/assemble_run_folder.py "$X/root/reports" "$RUN7" paper/data/run8-randomization-window --keep run-log.json run-log.md > "$X/logs/run8-assemble.log" 2>&1 || exit 1
"$PY" paper/build_tables.py --reports paper/data/run8-randomization-window --out "$X/tables-check" > "$X/logs/run8-tables-check.log" 2>&1
echo "tables-check $?" >> "$X/logs/stages.txt"
echo "run8-done" >> "$X/logs/stages.txt"
