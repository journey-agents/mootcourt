#!/bin/bash
# Run every experiment behind the README results block, in order, from the current tree.
# Usage: scripts/run_experiments.sh LOGS_DIR     (needs MOOTCOURT_DATA_ROOT or the repo-local folders to hold the raw data)
# Stages: ledger, fit and main backtest of the three sources, challengers, ablations (includes the P2 admission guard off and 1.0),
# the guarded-versus-unguarded comparison, learning curves, the cautionary run, leakage audits and card latency.
# Each stage appends "<name> <exit code> <seconds>" to LOGS_DIR/stages.txt. The script stops at the first main-stage failure.
set -u
LOGS="${1:?usage: run_experiments.sh LOGS_DIR}"
PY="${PY:-.venv/bin/python}"
MOOT="$PY -m mootcourt.cli"
mkdir -p "$LOGS"
STAGES="$LOGS/stages.txt"
stage() {
  local name=$1; shift
  local t0; t0=$(date +%s)
  "$@" > "$LOGS/$name.log" 2>&1; local rc=$?
  echo "$name $rc $(( $(date +%s) - t0 ))" >> "$STAGES"
  return $rc
}
stage ingest $MOOT ingest --source all || exit 1
for src in upworthy asos synthetic; do
  stage "fit-$src" $MOOT fit --source "$src" || exit 1
  stage "main-$src" $MOOT backtest --source "$src" --origins quarterly || exit 1
done
# Challengers run in their own folder so they never replace the main report.
ROOT="$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().reports)')"
mkdir -p "$ROOT/challengers"; cp "$ROOT/gates.json" "$ROOT/challengers/gates.json"
stage challengers-upworthy $MOOT backtest --source upworthy --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr \
  --reports-dir "$ROOT/challengers" --models-dir "$ROOT/challengers/models" &
stage challengers-asos $MOOT backtest --source asos --origins quarterly --challenger gbm --challenger local_eb \
  --reports-dir "$ROOT/challengers" --models-dir "$ROOT/challengers/models" &
wait
LOGS="$LOGS" PY="$PY" stage ablations-asos scripts/run_ablations.sh asos 3
LOGS="$LOGS" PY="$PY" stage ablations-upworthy scripts/run_ablations.sh upworthy 3
stage cautionary $MOOT backtest --source upworthy --origins quarterly --effect-scale relative --s-star realized --bootstrap 200
for src in upworthy asos; do stage "guard-compare-$src" $PY scripts/compare_guard.py --source "$src"; done
stage lc-asos $MOOT backtest --source asos --learning-curve 0.05,0.1,0.25,0.5,1 --seeds 3 --challenger gbm --challenger local_eb
stage lc-upworthy $MOOT backtest --source upworthy --learning-curve 0.05,0.1,0.25,0.5,1 --seeds 3 --challenger gbm --challenger local_eb --challenger text_lr
for src in upworthy asos synthetic; do
  for f in "$ROOT"/scores-$src-*.parquet; do stage "audit-$src" $PY scripts/leakage_audit.py --ledger "$($PY -c 'from mootcourt.storage import storage_paths; print(storage_paths().ledger_path)')" --scores "$f" --out "$ROOT/leakage-audit-$src.txt"; done
done
stage latency $PY scripts/card_latency.py --source upworthy --json-out "$ROOT/card-latency.json"
echo "experiments-done" >> "$STAGES"
