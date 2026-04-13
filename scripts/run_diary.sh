#!/usr/bin/env bash
set -euo pipefail

exec "${CHISATO_PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python}" \
  /Users/aliu/MEGA/openclaw/diary/scripts/generate_diary.py \
  "$@"
