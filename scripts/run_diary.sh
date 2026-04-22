#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${CHISATO_PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python}"
LOG_DIR="$SCRIPT_DIR/logs"
RUN_OUT="$LOG_DIR/last-run.out"
RUN_ERR="$LOG_DIR/last-run.err"
RUN_PID="$LOG_DIR/last-run.pid"
RUN_STATUS="$LOG_DIR/last-run.status"

mkdir -p "$LOG_DIR"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

write_status() {
  local status="$1"
  {
    printf 'status=%s\n' "$status"
    printf 'pid=%s\n' "$$"
    printf 'updated_at=%s\n' "$(timestamp)"
  } > "$RUN_STATUS"
}

: > "$RUN_OUT"
: > "$RUN_ERR"
write_status "starting"

{
  printf '[%s] run_diary.sh starting\n' "$(timestamp)"
  printf '[%s] python=%s\n' "$(timestamp)" "$PYTHON_BIN"
} | tee -a "$RUN_OUT"

set +e
"$PYTHON_BIN" "$SCRIPT_DIR/generate_diary.py" "$@" \
  > >(tee -a "$RUN_OUT") \
  2> >(tee -a "$RUN_ERR" >&2) &
child_pid=$!
set -e

printf '%s\n' "$child_pid" > "$RUN_PID"
write_status "running"

while kill -0 "$child_pid" 2>/dev/null; do
  printf '[%s] heartbeat: diary pid=%s still running\n' "$(timestamp)" "$child_pid" | tee -a "$RUN_OUT"
  sleep 15
done

set +e
wait "$child_pid"
exit_code=$?
set -e

if [[ "$exit_code" -eq 0 ]]; then
  write_status "completed"
  printf '[%s] run_diary.sh completed successfully\n' "$(timestamp)" | tee -a "$RUN_OUT"
else
  write_status "failed"
  printf '[%s] run_diary.sh failed with exit code %s\n' "$(timestamp)" "$exit_code" | tee -a "$RUN_ERR" >&2
fi

exit "$exit_code"
