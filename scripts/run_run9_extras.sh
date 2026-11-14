#!/bin/bash
# The additions to run 9 (docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md), all from the commit of the main run. Start it after
# scripts/run_experiments.sh has finished: it reads the main reports.
# Usage: scripts/run_run9_extras.sh [--only STAGE[,STAGE...]] [--dry-run] [JOBS]      (needs MOOTCOURT_DATA_ROOT)
# It refuses to start while src/ or scripts/ differ from the commit, and writes the commit to LOGS/run9-extras-commit.txt first.
# Stages, each logged under LOGS with "<name> <exit code> <seconds>" in LOGS/stages.txt:
#   null-size                   scripts/calibration_null_size.py on the main run's score table
#   pc-seed-8 .. pc-seed-11     the planted ledger of 11,100 tests at four more seeds, each with the rolling backtest of the main control
#   pc-seeds                    scripts/positive_control_seeds.py over seeds 7 (the main control) to 11
#   lc-origin-YYYY-MM-DD        the learning curve at each scored origin but the one the main curve holds
#   lc-origins                  scripts/learning_curve_origins.py over the seven curves; the curves by origin then move to learning-curve-origins/
#   split-half                  scripts/split_half_spread.py on the synthetic rows of the ledger
#   horizon-14, horizon-28      the Upworthy ledger rebuilt with a test's end assumed 14 and 28 days after its last arm, fitted and back-tested
#                               with the ladder only, each in its own folder (Part B)
#   by-origin*, no-history*     the main run's score table and those of the diagnostics read by origin and against the no-effect reference
set -u
MODE=run ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry; shift ;;
    --only) ONLY="${2:?usage: run_run9_extras.sh --only STAGE[,STAGE...]}"; shift 2 ;;
    *) break ;;
  esac
done
JOBS="${1:-4}"
D="${MOOTCOURT_DATA_ROOT:?export MOOTCOURT_DATA_ROOT}"
PY="${PY:-.venv/bin/python}"
MOOT="$PY -m mootcourt.cli"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"
LOGS="$D/experiments/run9-extras/logs"
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
  git rev-parse HEAD > "$LOGS/run9-extras-commit.txt"
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
# Part B: another assumed end of a test; the ladder only, like the window ablation without its challengers
for h in 14 28; do
  H="$ROOT/horizon-$h"
  pool "horizon-$h" bash -c "mkdir -p '$H/data/ledger' && $PY scripts/rebuild_upworthy_ledger.py --window on --horizon-days $h --ledger '$LEDGER' \
    --out '$H/data/ledger/ledger.parquet' && cp '$ROOT/gates.json' '$H/gates.json' && \
    $MOOT fit --source upworthy --ledger '$H/data/ledger/ledger.parquet' --models-dir '$H/models' --reports-dir '$H' && \
    $MOOT backtest --source upworthy --origins quarterly --ledger '$H/data/ledger/ledger.parquet' --reports-dir '$H' --models-dir '$H/models' --seed 0"
done
# the main run and the diagnostics by origin, and against the reference that uses no past effect
pool by-origin $PY scripts/by_origin_difference.py --scores "$ROOT/scores-upworthy-$SID_UP.parquet" --report "$ROOT/backtest-upworthy-$SID_UP.json" \
  --out "$ROOT/by-origin-upworthy-$SID_UP.json"
pool no-history $PY scripts/no_history_reference.py --scores "$ROOT/scores-upworthy-$SID_UP.parquet" --report "$ROOT/backtest-upworthy-$SID_UP.json" \
  --out "$ROOT/no-history-upworthy-$SID_UP.json"
for v in base-density-normal exposure-planned exposure-planned+base-density-normal; do
  pool "by-origin-$v" $PY scripts/by_origin_difference.py --scores "$ROOT/ablations/scores-upworthy-$SID_UP--$v.parquet" \
    --report "$ROOT/ablations/backtest-upworthy-$SID_UP--$v.json" --out "$ROOT/ablations/by-origin-upworthy-$SID_UP--$v.json"
  pool "no-history-$v" $PY scripts/no_history_reference.py --scores "$ROOT/ablations/scores-upworthy-$SID_UP--$v.parquet" \
    --report "$ROOT/ablations/backtest-upworthy-$SID_UP--$v.json" --out "$ROOT/ablations/no-history-upworthy-$SID_UP--$v.json"
done
[ "$MODE" = run ] && wait
RUNS=("7=$PC11")
for s in 8 9 10 11; do RUNS+=("$s=$PC/seeds/seed-$s"); done
step pc-seeds $PY scripts/positive_control_seeds.py --runs "${RUNS[@]}" \
  --main-report "$ROOT/backtest-upworthy-$SID_UP.json" --out "$ROOT/positive-control-seeds.json"
CURVES=("$ROOT/learning-curve-upworthy-$SID_UP.json")
for o in $LC_ORIGINS; do CURVES+=("$ROOT/learning-curve-upworthy-$SID_UP--origin-$o.json"); done
step lc-origins $PY scripts/learning_curve_origins.py --curves "${CURVES[@]}" --out "$ROOT/learning-curve-origins-upworthy-$SID_UP.json"
# The curves by origin and their summary move to a folder of their own: at the top of the reports they match the pattern
# learning-curve-<source>-*.json, which other readers expect to name one curve.
if [ "${MODE:-run}" != dry ]; then
  mkdir -p "$ROOT/learning-curve-origins"
  for f in "$ROOT"/learning-curve-upworthy-"$SID_UP"--origin-*.json "$ROOT"/learning-curve-upworthy-"$SID_UP"--origin-*.md \
           "$ROOT/learning-curve-origins-upworthy-$SID_UP.json"; do
    if [ -f "$f" ]; then mv "$f" "$ROOT/learning-curve-origins/"; fi
  done
fi
[ "$MODE" = run ] && [ -z "$ONLY" ] && echo "run9-extras-done" >> "$STAGES"
exit 0
