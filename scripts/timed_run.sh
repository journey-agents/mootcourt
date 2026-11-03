#!/bin/bash
# Timed run of the whole pipeline from a clean copy of the files git would commit (tracked plus untracked and not ignored).
# Usage: scripts/timed_run.sh [work_dir]   (default: a new folder under the system temp directory)
# Writes <work_dir>/clone/reports/run-log.json and run-log.md; every stage's log is in <work_dir>/logs.
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${1:-$(mktemp -d)}"
CLONE="$WORK/clone"; LOGS="$WORK/logs"
if [ -e "$CLONE" ] && [ -n "$(ls -A "$CLONE" 2>/dev/null)" ]; then
  echo "refusing a work_dir whose clone folder is not empty ($CLONE): a reused folder is not a clean copy" >&2
  exit 1
fi
mkdir -p "$CLONE" "$LOGS"
cd "$SRC" && git ls-files -co --exclude-standard > "$WORK/filelist.txt"
rsync -a --files-from="$WORK/filelist.txt" "$SRC"/ "$CLONE"/
cd "$CLONE" || exit 1
HEAD_SHA=$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || true)
if [ -z "$HEAD_SHA" ]; then COMMIT_NOTE="none yet (the tree has no commit; the digest above identifies the files)"
elif [ -n "$(git -C "$SRC" status --porcelain 2>/dev/null)" ]; then COMMIT_NOTE="$HEAD_SHA plus uncommitted changes (the digest above identifies the files that ran)"
else COMMIT_NOTE="$HEAD_SHA"; fi
TREE=$(sort "$WORK/filelist.txt" | while read -r f; do shasum -a 256 "$f"; done | shasum -a 256 | cut -c1-16)
STAGES="$WORK/stages.txt"; : > "$STAGES"
stage() {
  local name=$1; shift
  local t0; t0=$(date +%s.%N)
  "$@" > "$LOGS/$name.log" 2>&1; local rc=$?
  local t1; t1=$(date +%s.%N)
  printf "%s %s %.1f\n" "$name" "$rc" "$(echo "$t1 - $t0" | bc)" >> "$STAGES"
  return $rc
}
stage setup make setup || exit 1
stage data make data || exit 1
stage power make power || exit 1
for src in upworthy asos synthetic; do
  stage "fit-$src" make fit SOURCE="$src" || exit 1
  stage "backtest-$src" make backtest SOURCE="$src" || exit 1
done
stage challenger-gbm make challenger SOURCE=upworthy || exit 1
for src in upworthy asos synthetic; do stage "audit-$src" make audit SOURCE="$src" || exit 1; done
stage inventory uv run python scripts/data_inventory.py || exit 1
stage data-verify make data || exit 1
stage latency uv run python scripts/card_latency.py --source upworthy --json-out reports/card-latency.json || exit 1
PYV=$(uv run python --version 2>&1)
# The word "downloaded" is the run log's to write: scripts/run_log.py reads the download script's own summary line from the data log.
if [ -z "${MOOTCOURT_DATA_ROOT:-}" ]; then ROOT_NOTE="empty data root inside the copy"; else ROOT_NOTE="data root $MOOTCOURT_DATA_ROOT"; fi
uv run python scripts/run_log.py --stages "$STAGES" --data-log "$LOGS/data.log" --out-dir reports \
  --meta "run=clean copy of the files git would commit, $ROOT_NOTE; the data line below says whether anything was downloaded; the Python environment came from the uv cache, so the setup stage is not a cold install" \
  --meta "tree_sha256_16=$TREE" --meta "files=$(wc -l < "$WORK/filelist.txt" | tr -d ' ')" --meta "python=$PYV" \
  --meta "machine=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m), $(sysctl -n hw.ncpu 2>/dev/null || nproc) cores" \
  --meta "commit=$COMMIT_NOTE" \
  --meta "seed=0 for fit and backtest; 20261102 for the power run" --meta "uv=$(uv --version)"
echo "done: $CLONE/reports/run-log.md"
