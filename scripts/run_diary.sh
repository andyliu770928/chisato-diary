#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${CHISATO_PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python}"

exec "$PYTHON_BIN" "$SCRIPT_DIR/generate_diary.py" "$@"
