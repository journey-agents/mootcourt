#!/bin/bash
# Run every experiment behind the README results block and the paper tables, from the current tree, several at a time.
# Usage: scripts/run_experiments.sh [--only STAGE[,STAGE...]] LOGS_DIR [JOBS]    (needs MOOTCOURT_DATA_ROOT, or the repo-local folders, to hold the ledger)
#        scripts/run_experiments.sh --list                          print every stage name in order and run nothing
#        scripts/run_experiments.sh [--only ...] --dry-run          print the names of the stages that would run and run nothing
# --only runs just the named stages (a name may end in * to match a family, such as "fit-*" or "ablation-upworthy-*"); every other stage is skipped
# and logs nothing, a name that matches no stage is refused (exit 2), and the "experiments-done" marker is not written. The stage names are the
# ones in stages.txt; the stage list below shows the order. --list and --dry-run touch neither the data root nor the logs folder.
# Stages (round 00 layout):
#   gates        moot simulate gate-power: gates by test at the base rates of the archives (0.09, 0.14, 0.30)
#   main         fit and the main backtest of upworthy, asos and synthetic, each WITH the challengers and their recalibrated rungs;
#                the positive control (a synthetic archive with a planted text signal) runs beside them in reports/positive-control
#   pool         a pool of JOBS processes over: the ablations (guard on and off, pairwise off, admission prelaunch, kappa, prior, triggers), the
#                learning curves, the cautionary run, the weekly replays, the paper extras, the leakage audits and the card latency
# Each step appends "<name> <exit code> <seconds>" to LOGS_DIR/stages.txt; the exit code is read on the line right after the command.
# The script stops at the first failed main step. Threads per process are limited so several runs share the machine.
set -u
MODE=run ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --list) MODE=list; shift ;;
    --dry-run) MODE=dry; shift ;;
    --only) ONLY="${2:?usage: run_experiments.sh --only STAGE[,STAGE...] LOGS_DIR [JOBS]}"; shift 2 ;;
    *) break ;;
  esac
done
if [ "$MODE" = run ]; then
  LOGS="${1:?usage: run_experiments.sh [--only STAGE[,STAGE...]] LOGS_DIR [JOBS]  |  --list  |  [--only ...] --dry-run}"
else
  LOGS="$(mktemp -d)"        # only the ablation settings are written there (a file the listing reads back); removed on exit
  trap 'rm -rf "$LOGS"' EXIT
fi
JOBS="${2:-4}"
PY="${PY:-.venv/bin/python}"
MOOT="$PY -m mootcourt.cli"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"
[ "$MODE" = run ] && mkdir -p "$LOGS"
STAGES="$LOGS/stages.txt"
ROOT="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().reports)')"
LEDGER="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().ledger_path)')"
SEEN=" "
selected() {      # selected NAME: true when --only is absent or one of its comma-separated names (or globs) matches
  local pat
  [ -z "$ONLY" ] && return 0
  local IFS=,
  for pat in $ONLY; do
    # shellcheck disable=SC2053
    [[ "$1" == $pat ]] && return 0
  done
  return 1
}
act() { [ "$MODE" = run ] && "$@"; return 0; }      # act COMMAND...: a side effect between stages, skipped by --list and --dry-run
bg() { if [ "$MODE" = run ]; then "$@" & else "$@"; fi; }      # bg COMMAND...: in the background for a run, in order for a listing
step() {
  local name=$1; shift
  if [ "$MODE" != run ]; then
    case "$SEEN" in *" $name "*) return 0 ;; esac
    SEEN="$SEEN$name "
    { [ "$MODE" = list ] || selected "$name"; } && echo "$name"
    return 0
  fi
  selected "$name" || return 0
  local t0=$SECONDS
  "$@" > "$LOGS/$name.log" 2>&1
  local rc=$?
  echo "$name $rc $((SECONDS - t0))" >> "$STAGES"
  return $rc
}
pool() {      # pool NAME COMMAND...: start in the background once fewer than JOBS are running
  if [ "$MODE" != run ]; then step "$@"; return 0; fi
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 2; done
  step "$@" &
}
if [ -n "$ONLY" ] && [ "$MODE" != list ]; then      # refuse a name that matches no stage before anything runs
  ALL="$(bash "$0" --list)" || exit 1
  IFS=, read -r -a WANT <<< "$ONLY"
  for pat in "${WANT[@]}"; do
    found=0
    for st in $ALL; do
      # shellcheck disable=SC2053
      [[ "$st" == $pat ]] && found=1
    done
    [ "$found" = 1 ] || { echo "no stage matches --only $pat (see --list)" >&2; exit 2; }
  done
fi
FIRST_LINE=1
[ -f "$STAGES" ] && FIRST_LINE=$(( $(wc -l < "$STAGES") + 1 ))      # this run's lines of stages.txt start here
if [ "$MODE" = run ] && [ "${REUSE_GATES:-0}" = 1 ] && selected gates && grep -q by_base_rate "$ROOT/gates.json" 2>/dev/null; then
  echo "gates 0 0 (reused: $ROOT/gates.json already holds the by-test gates at several base rates, written by the same command and seed)" >> "$STAGES"
else
  step gates $MOOT simulate gate-power || exit 1
fi
main_source() {
  local src=$1; shift
  step "fit-$src" $MOOT fit --source "$src" || return 1
  step "main-$src" $MOOT backtest --source "$src" --origins quarterly "$@" || return 1
}
bg main_source upworthy --challenger gbm --challenger local_eb --challenger text_lr
bg main_source asos --challenger gbm --challenger local_eb
bg main_source synthetic --challenger gbm --challenger local_eb --challenger text_lr
PC="$ROOT/positive-control"
act mkdir -p "$PC"
pc_control() {
  step pc-ledger $MOOT simulate ledger --out "$PC/data/ledger.parquet" --n-tests 2000 --seed 7 --text-effect "${PC_TEXT_EFFECT:-1.0}" && \
  act cp "$ROOT/gates.json" "$PC/gates.json" && \
  step pc-backtest $MOOT backtest --source synthetic --origins quarterly --ledger "$PC/data/ledger.parquet" --reports-dir "$PC" --models-dir "$PC/models" \
    --challenger gbm --challenger local_eb --challenger text_lr --seed 0
}
bg pc_control
wait
if tail -n +"$FIRST_LINE" "$STAGES" 2>/dev/null | grep -E "^(fit|main)-" | grep -vq " 0 "; then echo "a main step failed" >&2; exit 1; fi
LOGS="$LOGS" PY="$PY" bash scripts/run_ablations.sh upworthy "$JOBS" --list > "$LOGS/ablation-settings-upworthy.txt"
LOGS="$LOGS" PY="$PY" bash scripts/run_ablations.sh asos "$JOBS" --list > "$LOGS/ablation-settings-asos.txt"
# the planted ledger at the size of the Upworthy headline-only cell per cell (11,100 tests, about 7,400 rows in each cell): every rung of that
# backtest is read against the oracle in paper_extras (positive_control_rungs, round 01 R3 major 4); it is long, so it starts first in the pool
PC11="$PC/rungs/n11100"
act mkdir -p "$PC11/data/ledger"
pool pc11-backtest bash -c "$MOOT simulate ledger --out '$PC11/data/ledger/ledger.parquet' --n-tests 11100 --seed 7 --text-effect '${PC_TEXT_EFFECT:-1.0}' && \
  cp '$ROOT/gates.json' '$PC11/gates.json' && $MOOT backtest --source synthetic --origins quarterly --ledger '$PC11/data/ledger/ledger.parquet' \
  --reports-dir '$PC11' --models-dir '$PC11/models' --challenger gbm --challenger local_eb --challenger text_lr --seed 0"
pool lc-upworthy $MOOT backtest --source upworthy --learning-curve 0.01,0.02,0.05,0.1,0.25,0.5,1 --seeds 20 --challenger gbm --challenger local_eb --challenger text_lr --no-recalibrate --bootstrap 500
pool lc-asos $MOOT backtest --source asos --learning-curve 0.05,0.1,0.25,0.5,1 --seeds 20 --challenger gbm --challenger local_eb --no-recalibrate --bootstrap 500
pool replay-upworthy $PY scripts/replay_weekly.py --source upworthy --verbose
pool replay-asos $PY scripts/replay_weekly.py --source asos --verbose
pool cautionary $MOOT backtest --source upworthy --origins quarterly --effect-scale relative --s-star realized --bootstrap 500
# X1 of the paper v2 plan (D1): the ablation that includes the randomization window, run 7's configuration. Its own ledger (the Upworthy rows rebuilt from the
# downloaded file with the date rule off; RUN7_UPWORTHY_DIGEST, when set, makes the stage fail unless that ledger is run 7's), fitted and back-tested with the
# main run's challengers and seed; it sits in reports/include-randomization-window like the planted ledgers sit in positive-control.
WIN="$ROOT/include-randomization-window"
act mkdir -p "$WIN/data/ledger"
pool window-ablation bash -c "$PY scripts/rebuild_upworthy_ledger.py --window off --ledger '$LEDGER' --out '$WIN/data/ledger/ledger.parquet' \
  ${RUN7_UPWORTHY_DIGEST:+--expect-digest $RUN7_UPWORTHY_DIGEST} && cp '$ROOT/gates.json' '$WIN/gates.json' && \
  $MOOT fit --source upworthy --ledger '$WIN/data/ledger/ledger.parquet' --models-dir '$WIN/models' --reports-dir '$WIN' && \
  $MOOT backtest --source upworthy --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr --ledger '$WIN/data/ledger/ledger.parquet' \
  --reports-dir '$WIN' --models-dir '$WIN/models' --seed 0"
# X7: the gates simulated at each stratum's own dependence, from the main run's score table
for src in upworthy asos; do pool "gates-strata-$src" $PY scripts/gates_by_stratum.py --source "$src"; done
for src in upworthy asos; do
  while IFS= read -r flags; do
    name=$(echo "$flags" | tr ' ' '_' | tr -d '-')
    # shellcheck disable=SC2086
    pool "ablation-$src-$name" $MOOT backtest --source "$src" --bootstrap "${BOOT:-500}" $flags
  done < "$LOGS/ablation-settings-$src.txt"
done
for src in upworthy asos; do pool "guard-compare-$src" $PY scripts/compare_guard.py --source "$src"; done
wait
# the paper extras read the finished main reports, the ablations and the positive-control backtests, so they run after everything above; the
# pc2000 folder is the published control (top level of $PC), copied to rungs/n2000 beside n11100
act mkdir -p "$PC/rungs/n2000/data/ledger"
act cp "$PC/data/ledger.parquet" "$PC/rungs/n2000/data/ledger/ledger.parquet"          # the run folder is read as a data root: data/ledger/ledger.parquet
act cp "$PC"/backtest-synthetic-*.json "$PC"/backtest-synthetic-*.md "$PC"/scores-synthetic-*.parquet "$PC/rungs/n2000/"
EXTRAS_UP=()          # X1 reads run 7's main report and score table to check that the ablation regenerates them
[ -n "${RUN7_REPORT:-}" ] && EXTRAS_UP+=(--run7-report "$RUN7_REPORT")
[ -n "${RUN7_SCORES:-}" ] && EXTRAS_UP+=(--run7-scores "$RUN7_SCORES")
pool extras-upworthy $PY scripts/paper_extras.py --source upworthy --verbose ${EXTRAS_UP[@]+"${EXTRAS_UP[@]}"}
pool extras-asos $PY scripts/paper_extras.py --source asos --verbose
wait
# X10 (paper v2 plan, docs/superpowers/plans/2026-11-06-x10-sizing-design.md): the sizing evaluation merges into the Upworthy extras report, so it starts once that
# report exists and runs beside the synthetic extras; SKIP_SIZING=1 leaves it out (the stage then logs "skipped"),
pool sizing-upworthy bash -c "if [ '${SKIP_SIZING:-0}' = 1 ]; then echo skipped; else $PY scripts/paper_extras.py --source upworthy --sizing-only; fi"
pool extras-synthetic $PY scripts/paper_extras.py --source synthetic --verbose --jobs 4 --positive-control-runs "$PC/rungs/n2000,$PC11"
wait
for src in upworthy asos synthetic; do
  for f in "$ROOT"/scores-$src-*.parquet; do step "audit-$src" $PY scripts/leakage_audit.py --ledger "$LEDGER" --scores "$f" --out "$ROOT/leakage-audit-$src.txt" --json-out "$ROOT/leakage-audit-$src.json"; done
done
step latency $PY scripts/card_latency.py --source upworthy --json-out "$ROOT/card-latency.json"
step refresh-check $PY scripts/refresh_discrimination.py "$ROOT" --check
[ "$MODE" = run ] && [ -z "$ONLY" ] && echo "experiments-done" >> "$STAGES"
exit 0
