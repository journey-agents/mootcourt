#!/bin/bash
# The registered confirmatory procedure in one command (docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md, sections "Part C" and
# "Registration of the confirmatory reading"). It starts from a ledger that scripts/confirmatory_ledger.py has already built; it fetches
# nothing, builds no ledger and reads no packages file. The analysis runs once.
# Usage: scripts/run_confirmatory.sh --root DIR                  run every stage in order; stop at the first stage that fails
#        scripts/run_confirmatory.sh --root DIR --dry-run        print every command and run nothing (nothing is written)
#        scripts/run_confirmatory.sh --root DIR --from STAGE     after a crash: start at STAGE (see the note on the last lines of this header)
#        scripts/run_confirmatory.sh --list                      print the stage names in order
# DIR is the data directory of the confirmatory ledger. It must hold data/ledger/ledger.parquet and data/ledger/confirmatory-record.json,
# and DIR/reports must hold no backtest report. MOOTCOURT_DATA_ROOT is set to DIR for every child, so reports go to DIR/reports and models to
# DIR/models. The commit is written to DIR/run-commit.txt and the driver refuses to start while src/ or scripts/ differ from it. The driver
# logs to DIR/run-log.txt, each stage logs under DIR/logs, and everything runs under nice -n 19.
# Stages, in order (SID is the snapshot id in the record):
#   gates            moot simulate gate-power, through scripts/run_experiments.sh --only gates: run 9's gates, the same command and seed.
#                    Without reports/gates.json the backtest would size its gates with the quick simulation, which run 9 did not use.
#   fit              moot fit --source upworthy (run_experiments.sh --only fit-upworthy), as in run 9
#   main             the one backtest with the main run's settings and the three challengers, quarterly origins, seed 0, 500 resamples
#                    (run_experiments.sh --only main-upworthy). Its report also holds the calibration percentiles on both binnings, the
#                    coverage of the 80 and 90 percent intervals and P2 against P1
#   by-origin        scripts/by_origin_difference.py: P1 minus P0 on the log score by origin and with the quarters as units
#   by-origin-skill  scripts/by_origin_skill.py: the Brier skill of P1 and P2 by origin, against the unsmoothed base rate
#   extras           scripts/paper_extras.py --source upworthy --verbose (run_experiments.sh --only extras-upworthy): it holds ranking_paired,
#                    the paired ranking against the arm-count rule, and calibration_within_period. Keys that read run 9's ablations are null
#   null-size        scripts/calibration_null_size.py with run 9's arguments: the simulated critical value the calibration verdicts are read
#                    against
#   smoothed-base    scripts/smoothed_base_skill.py: the Brier skill against the registered smoothed base rate (the second primary reading)
#   one-contrast     the secondary backtest with one contrast per test: the main command line with --contrasts one, so the text classifier is
#                    scored (the ablation stage of run_experiments.sh runs this setting without challengers). It writes to reports/ablations
# Left out, on purpose: the secondary run with the date rule off. The ledger with the rule off is rebuilt from a packages file, and the one
# script that does so (scripts/rebuild_upworthy_ledger.py --window off) reads the exploratory file only, while scripts/confirmatory_ledger.py
# has no option for the rule. No existing script can build that ledger for this split, so this driver has no stage for it.
# Side effects of run_experiments.sh --only, which this driver does not undo: empty folders reports/positive-control and
# reports/include-randomization-window, and a copy of gates.json under reports/positive-control. They hold no result.
# --from: the procedure allows a crash to be fixed only if the fix cannot change a number. --from STAGE skips the stages before STAGE and is
# written to the log. From a stage after main it needs the main report to exist; from main or earlier the refusal on an existing backtest
# report still holds.
set -u
STAGE_NAMES="gates fit main by-origin by-origin-skill extras null-size smoothed-base one-contrast"
USAGE="usage: run_confirmatory.sh --root DIR [--dry-run] [--from STAGE]  |  --list"
MODE=run DIR="" FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --list) MODE=list; shift ;;
    --dry-run) MODE=dry; shift ;;
    --root) DIR="${2:?$USAGE}"; shift 2 ;;
    --from) FROM="${2:?$USAGE}"; shift 2 ;;
    *) echo "$USAGE" >&2; exit 2 ;;
  esac
done
if [ "$MODE" = list ]; then
  # shellcheck disable=SC2086
  printf '%s\n' $STAGE_NAMES
  exit 0
fi
[ -n "$DIR" ] || { echo "$USAGE" >&2; exit 2; }
if [ -n "$FROM" ]; then
  case " $STAGE_NAMES " in *" $FROM "*) ;; *) echo "no stage is named $FROM (see --list)" >&2; exit 2 ;; esac
fi
cd "$(dirname "$0")/.." || exit 1
DIR="${DIR%/}"
case "$DIR" in /*) ;; *) DIR="$PWD/$DIR" ;; esac
PY="${PY:-.venv/bin/python}"
LEDGER="$DIR/data/ledger/ledger.parquet"
RECORD="$DIR/data/ledger/confirmatory-record.json"
ROOT="$DIR/reports"
LOGS="$DIR/logs"
LOG="$DIR/run-log.txt"

# refusal 1: the ledger and its record
for f in "$LEDGER" "$RECORD"; do
  [ -f "$f" ] || { echo "missing input: $f (scripts/confirmatory_ledger.py writes it); nothing was run" >&2; exit 1; }
done
SID="$(sed -n 's/.*"snapshot": *"\([^"]*\)".*/\1/p' "$RECORD" | head -n 1)"
if ! [[ "$SID" =~ ^[0-9]{8}-[0-9a-f]{12}$ ]]; then
  echo "no snapshot id in $RECORD; nothing was run" >&2
  exit 1
fi
REPORT="$ROOT/backtest-upworthy-$SID.json"
SCORES="$ROOT/scores-upworthy-$SID.parquet"

skipped() {      # skipped NAME: true when --from names a later stage
  [ -z "$FROM" ] && return 1
  local s
  for s in $STAGE_NAMES; do
    [ "$s" = "$FROM" ] && return 1
    [ "$s" = "$1" ] && return 0
  done
  return 1
}

# refusal 2: the analysis runs once
if skipped main; then
  [ -f "$REPORT" ] || { echo "--from $FROM needs the main report $REPORT, which does not exist; nothing was run" >&2; exit 1; }
else
  for f in "$ROOT"/backtest-*.json; do
    [ -e "$f" ] || continue
    echo "$ROOT already holds a backtest report ($(basename "$f")); the analysis runs once, and nothing was run" >&2
    exit 1
  done
fi

# refusal 3: one committed code state
DIRTY="$(git status --porcelain src scripts)" || exit 1
if [ -n "$DIRTY" ]; then
  if [ "$MODE" = run ]; then
    echo "src/ or scripts/ differ from the commit: commit first, then run; nothing was run" >&2
    exit 1
  fi
  echo "note: src/ or scripts/ differ from the commit; a run would be refused" >&2
fi
COMMIT="$(git rev-parse HEAD)" || exit 1

# every child sees the confirmatory root and none of the switches that change a stage of run_experiments.sh
CHILD=(env -u REUSE_GATES -u RUN7_REPORT -u RUN7_SCORES -u RUN7_UPWORTHY_DIGEST -u PC_TEXT_EFFECT -u BOOT -u SKIP_SIZING
       "MOOTCOURT_DATA_ROOT=$DIR" "PY=$PY" nice -n 19)

say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG"; }
show() {      # show NAME COMMAND...: the line of a dry run, each word quoted as a shell would need it
  local name=$1 word line=""
  shift
  for word in "$@"; do line+=" $(printf '%q' "$word")"; done
  echo "$name:$line"
}
stage() {      # stage NAME COMMAND...: run one command; the driver stops when it fails
  local name=$1; shift
  skipped "$name" && return 0
  if [ "$MODE" = dry ]; then show "$name" "$@"; return 0; fi
  say "start $name: $*"
  local t0=$SECONDS
  "$@" > "$LOGS/$name.log" 2>&1
  local rc=$?
  say "end $name: exit code $rc, $((SECONDS - t0)) s"
  if [ "$rc" != 0 ]; then
    echo "stage $name failed (exit code $rc); see $LOGS/$name.log. Stopped" >&2
    exit 1
  fi
}
driver_stage() {      # driver_stage NAME STAGE: one stage of run_experiments.sh, whose exit code is read from its stages.txt
  local name=$1 theirs=$2 before=0
  skipped "$name" && return 0
  [ -f "$LOGS/stages.txt" ] && before=$(wc -l < "$LOGS/stages.txt")
  stage "$name" "${CHILD[@]}" bash scripts/run_experiments.sh --only "$theirs" "$LOGS"
  [ "$MODE" = dry ] && return 0
  if ! tail -n +"$((before + 1))" "$LOGS/stages.txt" 2>/dev/null | grep -q "^$theirs 0 "; then
    say "end $name: $theirs did not finish with exit code 0 in $LOGS/stages.txt"
    echo "stage $name failed: $theirs has no line with exit code 0 in $LOGS/stages.txt; see $LOGS/$theirs.log. Stopped" >&2
    exit 1
  fi
}

if [ "$MODE" = run ]; then
  mkdir -p "$LOGS" || exit 1
  echo "$COMMIT" > "$DIR/run-commit.txt"
  say "run_confirmatory.sh at commit $COMMIT, root $DIR, snapshot $SID${FROM:+, started at stage $FROM after a crash}"
else
  echo "# dry run: nothing is run and nothing is written. Commit $COMMIT, root $DIR, snapshot $SID"
  echo "# gates, fit, main and extras are stages of scripts/run_experiments.sh; it runs, in that order:"
  echo "#   $PY -m mootcourt.cli simulate gate-power"
  echo "#   $PY -m mootcourt.cli fit --source upworthy"
  echo "#   $PY -m mootcourt.cli backtest --source upworthy --origins quarterly --challenger gbm --challenger local_eb --challenger text_lr"
  echo "#   $PY scripts/paper_extras.py --source upworthy --verbose"
fi

driver_stage gates gates
driver_stage fit fit-upworthy
driver_stage main main-upworthy
if [ "$MODE" = run ]; then      # one main report, and it is the record's snapshot
  COUNT=0
  for f in "$ROOT"/backtest-upworthy-*.json; do [ -e "$f" ] && COUNT=$((COUNT + 1)); done
  if [ "$COUNT" != 1 ] || [ ! -f "$REPORT" ] || [ ! -f "$SCORES" ]; then
    say "stopped: expected one main report, $REPORT, with its score table"
    echo "expected one main report, $REPORT, with its score table $SCORES; found $COUNT report(s). Stopped" >&2
    exit 1
  fi
fi
stage by-origin "${CHILD[@]}" "$PY" scripts/by_origin_difference.py --scores "$SCORES" --report "$REPORT" --out "$ROOT/by-origin-upworthy-$SID.json"
stage by-origin-skill "${CHILD[@]}" "$PY" scripts/by_origin_skill.py --scores "$SCORES" --report "$REPORT" \
  --out "$ROOT/by-origin-skill-upworthy-$SID.json"
driver_stage extras extras-upworthy
stage null-size "${CHILD[@]}" "$PY" scripts/calibration_null_size.py --scores "$SCORES" --out "$ROOT/calibration-null-size-upworthy-$SID.json" \
  --reps 400 --seed 20261113 --jobs 2
stage smoothed-base "${CHILD[@]}" "$PY" scripts/smoothed_base_skill.py --scores "$SCORES" --report "$REPORT" \
  --out "$ROOT/smoothed-base-skill-upworthy-$SID.json"
stage one-contrast "${CHILD[@]}" "$PY" -m mootcourt.cli backtest --source upworthy --origins quarterly --challenger gbm --challenger local_eb \
  --challenger text_lr --contrasts one --seed 0 --bootstrap 500
if [ "$MODE" = run ]; then
  say "confirmatory-done"
  echo "done; reports in $ROOT, log in $LOG"
fi
exit 0
