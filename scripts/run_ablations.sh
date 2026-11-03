#!/bin/bash
# Run the ablation backtests of one source, several at a time. Every run writes its own report under reports/ablations.
# Usage: scripts/run_ablations.sh SOURCE [JOBS]
#   upworthy  P2 selection rule, recency, feature sets, bandwidth, lambda, kappa, prior, P2 admission guard (off, 1.0)
#   asos      kappa, prior and the P2 admission guard (the other switches change only P2, which equals P1 on a cell-only space)
# Needs MOOTCOURT_DATA_ROOT or the repo-local folders to hold the ledger and gates.json. Logs go to $LOGS (default: a temp folder).
set -u
SOURCE="${1:-upworthy}"
JOBS="${2:-3}"
PY="${PY:-.venv/bin/python}"
LOGS="${LOGS:-$(mktemp -d)}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"
case "$SOURCE" in
  upworthy)
    SETTINGS=(
      "--p2-selection forward"
      "--recency select"
      "--p2-selection forward --recency select"
      "--features text" "--features structured"
      "--bandwidth-mult 1" "--bandwidth-mult 0.5" "--bandwidth-mult 0.25" "--bandwidth-mult 0.125"
      "--lambda 0" "--lambda 0.2" "--lambda 0.5" "--lambda 1"
      "--kappa 0" "--kappa 5" "--kappa 80"
      "--prior normal"
      "--p2-guard off" "--p2-guard 1.0"
    ) ;;
  asos)
    SETTINGS=("--kappa 0" "--kappa 5" "--kappa 80" "--prior normal" "--p2-guard off" "--p2-guard 1.0") ;;
  *) echo "unknown source $SOURCE" >&2; exit 2 ;;
esac
mkdir -p "$LOGS"
echo "logs in $LOGS"
run_one() {
  local flags="$1" name
  name=$(echo "$flags" | tr ' ' '_' | tr -d '-')
  # shellcheck disable=SC2086
  "$PY" -m mootcourt.cli backtest --source "$SOURCE" --bootstrap 200 $flags > "$LOGS/ablation-$SOURCE-$name.log" 2>&1
  echo "$flags -> exit $?"
}
for s in "${SETTINGS[@]}"; do
  run_one "$s" &
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 2; done
done
wait
