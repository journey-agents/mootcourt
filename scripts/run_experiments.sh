#!/bin/bash
# Run every experiment behind the README results block and the paper tables, from the current tree, several at a time.
# Usage: scripts/run_experiments.sh LOGS_DIR [JOBS]    (needs MOOTCOURT_DATA_ROOT, or the repo-local folders, to hold the ledger)
# Stages (round 00 layout):
#   gates        moot simulate gate-power: gates by test at the base rates of the archives (0.09, 0.14, 0.30)
#   main         fit and the main backtest of upworthy, asos and synthetic, each WITH the challengers and their recalibrated rungs;
#                the positive control (a synthetic archive with a planted text signal) runs beside them in reports/positive-control
#   pool         a pool of JOBS processes over: the ablations (guard on and off, pairwise off, admission prelaunch, kappa, prior, triggers), the
#                learning curves, the cautionary run, the weekly replays, the paper extras, the leakage audits and the card latency
# Each step appends "<name> <exit code> <seconds>" to LOGS_DIR/stages.txt; the exit code is read on the line right after the command.
# The script stops at the first failed main step. Threads per process are limited so several runs share the machine.
set -u
LOGS="${1:?usage: run_experiments.sh LOGS_DIR [JOBS]}"
JOBS="${2:-4}"
PY="${PY:-.venv/bin/python}"
MOOT="$PY -m mootcourt.cli"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"
mkdir -p "$LOGS"
STAGES="$LOGS/stages.txt"
ROOT="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().reports)')"
LEDGER="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().ledger_path)')"
step() {
  local name=$1; shift
  local t0=$SECONDS
  "$@" > "$LOGS/$name.log" 2>&1
  local rc=$?
  echo "$name $rc $((SECONDS - t0))" >> "$STAGES"
  return $rc
}
pool() {      # pool NAME COMMAND...: start in the background once fewer than JOBS are running
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 2; done
  step "$@" &
}
if [ "${REUSE_GATES:-0}" = 1 ] && grep -q by_base_rate "$ROOT/gates.json" 2>/dev/null; then
  echo "gates 0 0 (reused: $ROOT/gates.json already holds the by-test gates at several base rates, written by the same command and seed)" >> "$STAGES"
else
  step gates $MOOT simulate gate-power || exit 1
fi
main_source() {
  local src=$1; shift
  step "fit-$src" $MOOT fit --source "$src" || return 1
  step "main-$src" $MOOT backtest --source "$src" --origins quarterly "$@" || return 1
}
main_source upworthy --challenger gbm --challenger local_eb --challenger text_lr &
main_source asos --challenger gbm --challenger local_eb &
main_source synthetic --challenger gbm --challenger local_eb --challenger text_lr &
PC="$ROOT/positive-control"
mkdir -p "$PC"
(
  step pc-ledger $MOOT simulate ledger --out "$PC/data/ledger.parquet" --n-tests 2000 --seed 7 --text-effect "${PC_TEXT_EFFECT:-1.0}" && \
  cp "$ROOT/gates.json" "$PC/gates.json" && \
  step pc-backtest $MOOT backtest --source synthetic --origins quarterly --ledger "$PC/data/ledger.parquet" --reports-dir "$PC" --models-dir "$PC/models" \
    --challenger gbm --challenger local_eb
) &
wait
if grep -E "^(fit|main)-" "$STAGES" | grep -vq " 0 "; then echo "a main step failed" >&2; exit 1; fi
LOGS="$LOGS" PY="$PY" bash scripts/run_ablations.sh upworthy "$JOBS" --list > "$LOGS/ablation-settings-upworthy.txt"
LOGS="$LOGS" PY="$PY" bash scripts/run_ablations.sh asos "$JOBS" --list > "$LOGS/ablation-settings-asos.txt"
pool lc-upworthy $MOOT backtest --source upworthy --learning-curve 0.01,0.02,0.05,0.1,0.25,0.5,1 --seeds 20 --challenger gbm --challenger local_eb --challenger text_lr --no-recalibrate
pool lc-asos $MOOT backtest --source asos --learning-curve 0.05,0.1,0.25,0.5,1 --seeds 20 --challenger gbm --challenger local_eb --no-recalibrate
pool replay-upworthy $PY scripts/replay_weekly.py --source upworthy --verbose
pool replay-asos $PY scripts/replay_weekly.py --source asos --verbose
pool cautionary $MOOT backtest --source upworthy --origins quarterly --effect-scale relative --s-star realized --bootstrap 200
for src in upworthy asos; do
  while IFS= read -r flags; do
    name=$(echo "$flags" | tr ' ' '_' | tr -d '-')
    # shellcheck disable=SC2086
    pool "ablation-$src-$name" $MOOT backtest --source "$src" --bootstrap "${BOOT:-500}" $flags
  done < "$LOGS/ablation-settings-$src.txt"
done
for src in upworthy asos synthetic; do pool "extras-$src" $PY scripts/paper_extras.py --source "$src" --verbose; done
for src in upworthy asos; do pool "guard-compare-$src" $PY scripts/compare_guard.py --source "$src"; done
wait
for src in upworthy asos synthetic; do
  for f in "$ROOT"/scores-$src-*.parquet; do step "audit-$src" $PY scripts/leakage_audit.py --ledger "$LEDGER" --scores "$f" --out "$ROOT/leakage-audit-$src.txt"; done
done
step latency $PY scripts/card_latency.py --source upworthy --json-out "$ROOT/card-latency.json"
echo "experiments-done" >> "$STAGES"
