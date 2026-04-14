#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
STATUS_FILE="$LOG_DIR/last-run.status"
OUTPUT_FILE="$LOG_DIR/last-run.out"
ERROR_FILE="$LOG_DIR/last-run.err"
PID_FILE="$LOG_DIR/last-run.pid"

mkdir -p "$LOG_DIR"

PYTHON_BIN="${CHISATO_PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python}"

# 已在執行中 → 不重複啟動
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "already running (PID $OLD_PID), skip"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

echo "starting at $(date '+%Y-%m-%d %H:%M:%S')" > "$STATUS_FILE"
echo "running" >> "$STATUS_FILE"

# 真正在背景執行，不等結果
nohup "$PYTHON_BIN" "$SCRIPT_DIR/generate_diary.py" \
    > "$OUTPUT_FILE" \
    2> "$ERROR_FILE" &
echo $! > "$PID_FILE"

echo "launched as background job, PID=$(cat $PID_FILE)"
exit 0
