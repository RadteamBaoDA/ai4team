#!/usr/bin/env bash
# Helper script with convenience commands for the reranker service.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_SCRIPT="${SCRIPT_DIR}/start_reranker.sh"
PID_FILE="${SCRIPT_DIR}/reranker.pid"
LOG_FILE="${SCRIPT_DIR}/reranker.log"

usage() {
    cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  sample-dev       Show sample command to run in development mode.
  sample-daemon    Show sample command to run in daemon mode.
  sample-fg        Show sample command to run in foreground mode.
  start            Start the service in daemon mode.
  stop             Stop the daemon-mode service.
  restart          Restart the daemon-mode service.
  status           Show service status and PID if running.
  tail             Tail the daemon log output.
EOF
}

start_daemon() {
    if [ -f "${PID_FILE}" ] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        echo "Service already running with PID $(cat "${PID_FILE}")"
        exit 0
    fi
        "${START_SCRIPT}" daemon "$@"
}

stop_daemon() {
    if [ ! -f "${PID_FILE}" ]; then
        echo "No PID file found. Service may not be running."
        return
    fi
    PID="$(cat "${PID_FILE}")"
    if kill -0 "${PID}" 2>/dev/null; then
        echo "Stopping service with PID ${PID}"
        kill "${PID}"
        # Give it a moment to shutdown gracefully
        sleep 2
        if kill -0 "${PID}" 2>/dev/null; then
            echo "Force killing PID ${PID}"
            kill -9 "${PID}"
        fi
    else
        echo "Process ${PID} not running"
    fi
    rm -f "${PID_FILE}"
}

status_daemon() {
    if [ -f "${PID_FILE}" ]; then
        PID="$(cat "${PID_FILE}")"
        if kill -0 "${PID}" 2>/dev/null; then
            echo "Service running with PID ${PID}"
            return
        fi
        echo "PID file exists but process ${PID} not running"
    else
        echo "Service not running"
    fi
}

case "${1:-help}" in
    sample-dev)
        cat <<EOF
Example (development with reload):
  LOG_LEVEL=DEBUG RERANKER_MAX_PARALLEL=2 ./start_reranker.sh dev
EOF
        ;;
    sample-daemon)
        cat <<EOF
Example (daemon with custom ports and local model):
  RERANKER_PORT=9000 RERANKER_MODEL_LOCAL_PATH=/models/reranker ./start_reranker.sh daemon
EOF
        ;;
    sample-fg)
        cat <<EOF
Example (foreground production):
  RERANKER_DEVICE=cuda RERANKER_MAX_PARALLEL=8 ./start_reranker.sh fg
EOF
        ;;
    start)
        shift || true
        start_daemon "$@"
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        shift || true
        stop_daemon
        start_daemon "$@"
        ;;
    status)
        status_daemon
        ;;
    tail)
        tail -f "${LOG_FILE}"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Unknown command '$1'" >&2
        usage
        exit 1
        ;;
 esac
