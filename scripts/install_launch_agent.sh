#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$BASE_DIR/scripts"
LOG_DIR="$BASE_DIR/logs"
LAUNCHD_DIR="$BASE_DIR/launchd"
mkdir -p "$LOG_DIR" "$LAUNCHD_DIR" "$HOME/Library/LaunchAgents"

LABEL="${CHISATO_DIARY_LABEL:-ai.chisato.diary}"
HOUR="${CHISATO_DIARY_HOUR:-22}"
MINUTE="${CHISATO_DIARY_MINUTE:-0}"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
RUN_SCRIPT="$SCRIPTS_DIR/run_diary.sh"
PYTHON_BIN="${CHISATO_PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python}"
ENV_FILE="${CHISATO_ENV_FILE:-$HOME/.hermes/.env}"
NODE_BIN=""

if command -v node >/dev/null 2>&1; then
  NODE_BIN="$(dirname "$(command -v node)")"
fi

PATH_VALUE="$HOME/.hermes/hermes-agent/venv/bin"
if [ -n "$NODE_BIN" ]; then
  PATH_VALUE="$PATH_VALUE:$NODE_BIN"
fi
PATH_VALUE="$PATH_VALUE:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cat >"$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUN_SCRIPT</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$BASE_DIR</string>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$HOUR</integer>
    <key>Minute</key>
    <integer>$MINUTE</integer>
  </dict>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$PATH_VALUE</string>
    <key>CHISATO_PYTHON_BIN</key>
    <string>$PYTHON_BIN</string>
    <key>CHISATO_ENV_FILE</key>
    <string>$ENV_FILE</string>
    <key>HOME</key>
    <string>$HOME</string>
  </dict>

  <key>RunAtLoad</key>
  <false/>

  <key>StandardOutPath</key>
  <string>$LOG_DIR/launchd.out.log</string>

  <key>StandardErrorPath</key>
  <string>$LOG_DIR/launchd.err.log</string>
</dict>
</plist>
PLIST

cp "$PLIST_PATH" "$LAUNCHD_DIR/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed LaunchAgent: $PLIST_PATH"
echo "Schedule: ${HOUR}:${MINUTE}"
echo "Run once manually:"
echo "  launchctl kickstart -k gui/$(id -u)/$LABEL"
