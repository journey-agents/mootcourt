#!/usr/bin/env bash
# Usage: check_doctor_output.sh EXIT_CODE OUTPUT_FILE
# Judges a `moot doctor` run from its exit code and its output. The doctor exits 0 (healthy) or 1 (warnings, as on an empty data
# root), but Python also exits 1 on an uncaught exception, so the code alone cannot tell a warning from a crash. The run passes only
# when the code is 0 or 1, the output holds no traceback, and it ends in the doctor's own `status: ok` or `status: warn` line.
set -u
code="${1:?exit code}"
file="${2:?output file}"
if [ "$code" != 0 ] && [ "$code" != 1 ]; then
  echo "moot doctor exited with $code" >&2
  exit 1
fi
if grep -q "Traceback (most recent call last)" "$file"; then
  echo "moot doctor crashed: the output holds a Traceback" >&2
  exit 1
fi
if ! grep -Eq "^status: (ok|warn)$" "$file"; then
  echo "moot doctor printed no parseable status line" >&2
  exit 1
fi
echo "moot doctor exited with $code and reported a healthy or warning status"
