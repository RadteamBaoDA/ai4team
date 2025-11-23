#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${1:-$SCRIPT_DIR/config.yaml}"
PYTHON_EXE="${PYTHON_EXE:-python}"
exec "$PYTHON_EXE" -m structure_understand.cli --config "$CONFIG_PATH"
