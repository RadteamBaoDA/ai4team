#!/bin/bash
# LLM Guard API Entrypoint Script

set -e

CONFIG_FILE="${CONFIG_FILE:-./config/scanners.yml}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-1}"

echo "Starting LLM Guard API..."
echo "Config file: ${CONFIG_FILE}"
echo "Port: ${APP_PORT}"
echo "Workers: ${APP_WORKERS}"

# Check if config file exists
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Error: Config file not found: ${CONFIG_FILE}"
    exit 1
fi

# Start the LLM Guard API
exec llm_guard_api "${CONFIG_FILE}"
