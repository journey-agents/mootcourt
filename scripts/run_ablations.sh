#!/bin/bash
# Run the ablation backtests of one source, several at a time. Every run writes its own report under reports/ablations.
# Usage: scripts/run_ablations.sh SOURCE [JOBS]      (or: scripts/run_ablations.sh SOURCE JOBS --list, which prints the settings and runs nothing)
#   upworthy  P2 selection rule (leave-one-test-out, the counterfactual of the forward-chaining default), recency, feature sets, bandwidth, lambda, kappa, prior, the base rate's density (--base-density t), P2 admission guard (off, 1.0), the single-headline
#             feature space (--pairwise off), admission on exposure only (--admission prelaunch), one contrast per test (--contrasts one); the two single changes of the
#             cautionary run (--effect-scale relative, at planned precision; --s-star realized, on the absolute effect) and the exposure fixed at the cell median
#             (--exposure cell-median), paper v2 plan X2 and X3; the feature, bandwidth, selection, recency and
#             pairwise ablations are run twice, with the guard on and with --p2-guard off, because behind the guard the ablated setting rarely
#             reaches a forecast (round 00, R3); the off runs are named like `features-text+p2-guard-off`
#   asos      kappa, prior and the P2 admission guard (the other switches change only P2, which equals P1 on a cell-only space)
#   both      also the trigger-removal runs: each abstention trigger switched off on its own (--drop-trigger support, novelty, reliability, instability)
# Needs MOOTCOURT_DATA_ROOT or the repo-local folders to hold the ledger and gates.json. Logs go to $LOGS (default: a temp folder).
set -u
SOURCE="${1:-upworthy}"
JOBS="${2:-3}"
PY="${PY:-.venv/bin/python}"
BOOT="${BOOT:-500}"       # the main run's resample count, so an interval differs from the main table's only by the setting (round 00 R3 minor)
LOGS="${LOGS:-$(mktemp -d)}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-2}"
case "$SOURCE" in
  upworthy)
    GUARDED=(
      "--p2-selection loto"
      "--recency select"
      "--p2-selection loto --recency select"
      "--features text" "--features structured"
      "--bandwidth-mult 1" "--bandwidth-mult 0.5" "--bandwidth-mult 0.25" "--bandwidth-mult 0.125"
      "--pairwise off"
    )
    SETTINGS=("${GUARDED[@]}")
    for g in "${GUARDED[@]}"; do SETTINGS+=("$g --p2-guard off"); done
    SETTINGS+=(
      "--lambda 0" "--lambda 0.2" "--lambda 0.5" "--lambda 1"
      "--kappa 0" "--kappa 5" "--kappa 80"
      "--prior normal" "--base-density t"
      "--p2-guard off" "--p2-guard 1.0"
      "--admission prelaunch"
      "--contrasts one"
      "--effect-scale relative" "--s-star realized" "--exposure cell-median"
      "--base-density t --exposure cell-median"
      "--base-recency quarter" "--base-recency quarter --exposure cell-median" "--base-recency cell-quarter"
      "--exposure cell-median-visible" "--base-density t --exposure cell-median-visible"
      "--recalibrate-ladder on"
      "--drop-trigger support" "--drop-trigger novelty" "--drop-trigger reliability" "--drop-trigger instability"
    ) ;;
  asos)
    SETTINGS=("--kappa 0" "--kappa 5" "--kappa 80" "--prior normal" "--p2-guard off" "--p2-guard 1.0"
              "--drop-trigger support" "--drop-trigger novelty" "--drop-trigger reliability" "--drop-trigger instability") ;;
  *) echo "unknown source $SOURCE" >&2; exit 2 ;;
esac
if [ "${3:-}" = "--list" ]; then printf '%s\n' "${SETTINGS[@]}"; exit 0; fi      # one setting per line, for a driver that runs them in its own pool
mkdir -p "$LOGS"
echo "logs in $LOGS"
run_one() {
  local flags="$1" name
  name=$(echo "$flags" | tr ' ' '_' | tr -d '-')
  # shellcheck disable=SC2086
  "$PY" -m mootcourt.cli backtest --source "$SOURCE" --bootstrap "$BOOT" $flags > "$LOGS/ablation-$SOURCE-$name.log" 2>&1
  echo "$flags -> exit $?"
}
for s in "${SETTINGS[@]}"; do
  run_one "$s" &
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 2; done
done
wait
