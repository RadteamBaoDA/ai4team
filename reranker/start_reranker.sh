#!/usr/bin/env bash
# Bootstrap script for the reranker FastAPI service.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv"

# Environment defaults – override by exporting before invoking this script
export RERANKER_MODEL="${RERANKER_MODEL:-cross-encoder/ms-marco-MiniLM-L-6-v2}"
export RERANKER_MAX_LENGTH="${RERANKER_MAX_LENGTH:-512}"
export RERANKER_MAX_PARALLEL="${RERANKER_MAX_PARALLEL:-4}"
export RERANKER_MAX_QUEUE="${RERANKER_MAX_QUEUE:-}"  # leave empty for unlimited
export RERANKER_QUEUE_TIMEOUT="${RERANKER_QUEUE_TIMEOUT:-30.0}"
export RERANKER_DEVICE="${RERANKER_DEVICE:-auto}"
export RERANKER_MODEL_LOCAL_PATH="${RERANKER_MODEL_LOCAL_PATH:-}"  # optional local model cache
export RERANKER_HOST="${RERANKER_HOST:-0.0.0.0}"
export RERANKER_PORT="${RERANKER_PORT:-8000}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Ensure the virtual environment is used if present
if [ -d "${VENV_PATH}" ]; then
    # shellcheck disable=SC1091
    source "${VENV_PATH}/Scripts/activate" 2>/dev/null || source "${VENV_PATH}/bin/activate"
fi

MODE="${1:-dev}"
shift || true

APP_PATH="reranker.index:app"
COMMON_ARGS=("--host" "${RERANKER_HOST}" "--port" "${RERANKER_PORT}" "--log-level" "${LOG_LEVEL,,}")

case "${MODE}" in
    dev)
        echo "Starting reranker in development mode (reload, debug)."
        exec uvicorn "${APP_PATH}" "${COMMON_ARGS[@]}" "--reload" "--log-level" "debug"
        ;;
    daemon)
    LOG_FILE="${SCRIPT_DIR}/reranker.log"
    PID_FILE="${SCRIPT_DIR}/reranker.pid"
    echo "Starting reranker in daemon mode (nohup, background). Logs -> ${LOG_FILE}"
    nohup uvicorn "${APP_PATH}" "${COMMON_ARGS[@]}" "$@" >>"${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}"
    echo "Reranker started with PID $(cat "${PID_FILE}")"
    echo "Use './manage_reranker.sh tail' to follow logs."
        ;;
    fg)
        echo "Starting reranker in foreground production mode."
        exec uvicorn "${APP_PATH}" "${COMMON_ARGS[@]}" "$@"
        ;;
    *)
        echo "Unknown mode '${MODE}'. Use 'dev', 'daemon', or 'fg'." >&2
        exit 1
        ;;
 esac
