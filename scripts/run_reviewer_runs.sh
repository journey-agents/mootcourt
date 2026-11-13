#!/bin/bash
# The reviewer runs of 13 November 2026 (docs/superpowers/plans/2026-11-13-reviewer-runs.md): six additions to run 8, all from one commit.
# Usage: scripts/run_reviewer_runs.sh [--only STAGE[,STAGE...]] [--dry-run] [JOBS]      (needs MOOTCOURT_DATA_ROOT)
# It refuses to start while src/ or scripts/ differ from the commit, and writes the commit to LOGS/reviewer-runs-commit.txt first.
# Stages, each logged under LOGS with "<name> <exit code> <seconds>" in LOGS/stages.txt:
#   A  null-size                   scripts/calibration_null_size.py on the main run's score table
#   B  pc-seed-8 .. pc-seed-11     the planted ledger of 11,100 tests at four more seeds, each with the rolling backtest of the main control
#      pc-seeds                    scripts/positive_control_seeds.py over seeds 7 (the existing run) to 11
#   C  ablation-upworthy-recalibrateladder_on                             (scripts/run_experiments.sh --only)
#   E  ablation-upworthy-baserecency_quarter_exposure_cellmedianvisible   (scripts/run_experiments.sh --only)
#      extras-exposure-visible     the key exposure_fixed_visible merged into the Upworthy extras report; no other key is recomputed
#   D  lc-origin-YYYY-MM-DD        the learning curve at each scored origin but the one the existing curve holds
#      lc-origins                  scripts/learning_curve_origins.py over the seven curves
#   F  split-half                  scripts/split_half_spread.py on the synthetic rows of the ledger
# Nothing here reruns a main backtest, and no existing report key is recomputed.
set -u
MODE=run ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry; shift ;;
    --only) ONLY="${2:?usage: run_reviewer_runs.sh --only STAGE[,STAGE...]}"; shift 2 ;;
    *) break ;;
  esac
done
JOBS="${1:-4}"
D="${MOOTCOURT_DATA_ROOT:?export MOOTCOURT_DATA_ROOT}"
PY="${PY:-.venv/bin/python}"
MOOT="$PY -m mootcourt.cli"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"
LOGS="$D/experiments/reviewer-runs/logs"
STAGES="$LOGS/stages.txt"
ROOT="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().reports)')"
LEDGER="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().ledger_path)')"
SID_UP=20261106-2dc461f52ea4
SID_SYN=20261103-bf4fd286e2b2
LC_ORIGINS="2013-04-01 2014-01-01 2014-04-01 2014-07-01 2014-10-01 2015-04-01"      # the scored origins; the existing curve is at 2015-01-01
PC="$ROOT/positive-control"
PC11="$PC/rungs/n11100"
selected() {
  local pat
  [ -z "$ONLY" ] && return 0
  local IFS=,
  for pat in $ONLY; do
    # shellcheck disable=SC2053
    [[ "$1" == $pat ]] && return 0
  done
  return 1
}
step() {
  local name=$1; shift
  selected "$name" || return 0
  if [ "$MODE" != run ]; then echo "$name: $*"; return 0; fi
  local t0=$SECONDS
  "$@" > "$LOGS/$name.log" 2>&1
  local rc=$?
  echo "$name $rc $((SECONDS - t0))" >> "$STAGES"
  return $rc
}
pool() {
  if [ "$MODE" != run ]; then step "$@"; return 0; fi
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 2; done
  step "$@" &
}
if [ "$MODE" = run ]; then
  if [ -n "$(git status --porcelain src scripts)" ]; then echo "src/ or scripts/ differ from the commit: commit first, then run" >&2; exit 1; fi
  for f in "$ROOT/backtest-upworthy-$SID_UP.json" "$ROOT/scores-upworthy-$SID_UP.parquet" "$ROOT/backtest-synthetic-$SID_SYN.json" \
           "$ROOT/learning-curve-upworthy-$SID_UP.json" "$ROOT/paper-extras-upworthy-$SID_UP.json" "$ROOT/gates.json" "$LEDGER"; do
    [ -e "$f" ] || { echo "missing input: $f" >&2; exit 1; }
  done
  ls "$PC11"/backtest-synthetic-*.json > /dev/null 2>&1 || { echo "missing input: the seed 7 control under $PC11" >&2; exit 1; }
  mkdir -p "$LOGS"
  git rev-parse HEAD > "$LOGS/reviewer-runs-commit.txt"
fi

# B: four more seeds of the planted ledger, the commands of the main control (run_experiments.sh, stage pc11-backtest) with the seed changed
for s in 8 9 10 11; do
  P="$PC/seeds/seed-$s"
  pool "pc-seed-$s" bash -c "mkdir -p '$P/data/ledger' && $MOOT simulate ledger --out '$P/data/ledger/ledger.parquet' --n-tests 11100 --seed $s --text-effect 1.0 && \
    cp '$ROOT/gates.json' '$P/gates.json' && $MOOT backtest --source synthetic --origins quarterly --ledger '$P/data/ledger/ledger.parquet' \
    --reports-dir '$P' --models-dir '$P/models' --challenger gbm --challenger local_eb --challenger text_lr --seed 0"
done
# D: the existing curve's fractions, seeds and flags (run_experiments.sh, stage lc-upworthy) at each other scored origin
for o in $LC_ORIGINS; do
  pool "lc-origin-$o" $MOOT backtest --source upworthy --learning-curve 0.01,0.02,0.05,0.1,0.25,0.5,1 --seeds 20 --challenger gbm --challenger local_eb \
    --challenger text_lr --no-recalibrate --bootstrap 500 --learning-curve-origin "$o"
done
# A
pool null-size $PY scripts/calibration_null_size.py --scores "$ROOT/scores-upworthy-$SID_UP.parquet" \
  --out "$ROOT/calibration-null-size-upworthy-$SID_UP.json" --reps 400 --seed 20261113 --jobs 2
# F
pool split-half $PY scripts/split_half_spread.py --ledger "$LEDGER" --source synthetic --report "$ROOT/backtest-synthetic-$SID_SYN.json" \
  --out "$ROOT/split-half-synthetic-$SID_SYN.json"
[ "$MODE" = run ] && wait
# C and E: the two ablations through the main driver, which names and logs them as every other ablation
ABL="ablation-upworthy-recalibrateladder_on,ablation-upworthy-baserecency_quarter_exposure_cellmedianvisible"
if selected "ablations"; then
  if [ "$MODE" = run ]; then
    t0=$SECONDS
    bash scripts/run_experiments.sh --only "$ABL" "$LOGS" 2 > "$LOGS/ablations.log" 2>&1
    echo "ablations $? $((SECONDS - t0))" >> "$STAGES"
  else
    echo "ablations: bash scripts/run_experiments.sh --only $ABL $LOGS 2"
  fi
fi
step extras-exposure-visible $PY scripts/paper_extras.py --source upworthy --exposure-fixed-visible-only
RUNS=("7=$PC11")
for s in 8 9 10 11; do RUNS+=("$s=$PC/seeds/seed-$s"); done
step pc-seeds $PY scripts/positive_control_seeds.py --runs "${RUNS[@]}" \
  --main-report "$ROOT/backtest-upworthy-$SID_UP.json" --out "$ROOT/positive-control-seeds.json"
CURVES=("$ROOT/learning-curve-upworthy-$SID_UP.json")
for o in $LC_ORIGINS; do CURVES+=("$ROOT/learning-curve-upworthy-$SID_UP--origin-$o.json"); done
step lc-origins $PY scripts/learning_curve_origins.py --curves "${CURVES[@]}" --out "$ROOT/learning-curve-origins-upworthy-$SID_UP.json"
[ "$MODE" = run ] && [ -z "$ONLY" ] && echo "reviewer-runs-done" >> "$STAGES"
exit 0
