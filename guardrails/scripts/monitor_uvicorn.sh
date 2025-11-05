#!/bin/bash
# Uvicorn Concurrency Monitor - Real-time Task/Connection Tracking
# Monitors active concurrent connections and tasks in uvicorn proxy
#
# Usage:
#   ./monitor_uvicorn.sh [OPTIONS]
#   ./monitor_uvicorn.sh --pid 12345                    # Monitor specific PID
#   ./monitor_uvicorn.sh --log-file /var/log/proxy.log  # Monitor specific log file
#   ./monitor_uvicorn.sh --watch                         # Watch mode (continuous)
#   ./monitor_uvicorn.sh --json                          # JSON output format
#   ./monitor_uvicorn.sh --help                          # Show help

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/proxy.pid"
LOG_FILE="$LOG_DIR/proxy.log"

# Options
MONITOR_PID=""
MONITOR_LOG="$LOG_FILE"
WATCH_MODE=false
JSON_OUTPUT=false
UPDATE_INTERVAL=2
COLOR_ENABLED=true

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --pid)
      MONITOR_PID="$2"; shift 2
      ;;
    --log-file)
      MONITOR_LOG="$2"; shift 2
      ;;
    --watch)
      WATCH_MODE=true; shift
      ;;
    --json)
      JSON_OUTPUT=true; shift
      ;;
    --interval)
      UPDATE_INTERVAL="$2"; shift 2
      ;;
    --no-color)
      COLOR_ENABLED=false; shift
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# If no PID specified, try to read from PID file
if [ -z "$MONITOR_PID" ] && [ -f "$PID_FILE" ]; then
  MONITOR_PID=$(cat "$PID_FILE")
fi

show_help() {
  cat << 'EOF'
Uvicorn Concurrency Monitor - Real-time Task and Connection Tracking

Usage: ./monitor_uvicorn.sh [OPTIONS]

Options:
  --pid PID                Monitor specific process ID
  --log-file FILE          Log file to monitor (default: logs/proxy.log)
  --watch                  Continuous monitoring mode (press Ctrl+C to stop)
  --json                   Output metrics in JSON format
  --interval SECONDS       Update interval in seconds (default: 2)
  --no-color               Disable colored output
  --help                   Show this help message

Examples:
  # Monitor proxy with auto-detected PID
  ./monitor_uvicorn.sh

  # Monitor with specific PID
  ./monitor_uvicorn.sh --pid 12345

  # Watch mode (continuous updates)
  ./monitor_uvicorn.sh --watch

  # JSON output
  ./monitor_uvicorn.sh --json

  # Custom interval
  ./monitor_uvicorn.sh --watch --interval 1

Output Metrics:
  - Active Concurrent Tasks: Current active tasks across all endpoints
  - Peak Concurrent: Maximum concurrent tasks seen
  - Total Requests: Total requests processed
  - Failed Requests: Total failed requests
  - Queue Depth: Current request queue depth
  - Per-endpoint breakdown: Active and completed tasks per endpoint
  - System metrics: CPU, Memory, Thread count (if psutil available)

Debug Log Levels:
  - DEBUG level logs show per-task tracking
  - INFO level shows summary at shutdown
  - MONITOR_UPDATE_INTERVAL env var can adjust update frequency

EOF
}

# Function to parse log file for metrics
parse_metrics() {
  local log_file="$1"
  
  if [ ! -f "$log_file" ]; then
    echo "Error: Log file not found: $log_file"
    return 1
  fi
  
  # Extract recent concurrency metrics from debug logs
  local recent_lines=50
  local metrics=$(tail -"$recent_lines" "$log_file" 2>/dev/null | grep -E '\[CONCURRENCY\]|\[ENDPOINTS\]|\[SYSTEM\]' | tail -3)
  
  if [ -z "$metrics" ]; then
    echo "No concurrency metrics found in log file. Ensure DEBUG level logging is enabled."
    echo "Set: export DEBUG=true"
    return 1
  fi
  
  echo "$metrics"
}

# Function to extract metrics from debug logs
extract_metrics() {
  local log_file="$1"
  
  # Look for CONCURRENCY line
  local concurrency_line=$(tail -100 "$log_file" 2>/dev/null | grep '\[CONCURRENCY\]' | tail -1)
  local endpoints_line=$(tail -100 "$log_file" 2>/dev/null | grep '\[ENDPOINTS\]' | tail -1)
  local system_line=$(tail -100 "$log_file" 2>/dev/null | grep '\[SYSTEM\]' | tail -1)
  
  if [ -z "$concurrency_line" ]; then
    return 1
  fi
  
  # Parse concurrency metrics
  local active=$(echo "$concurrency_line" | grep -oP 'Active: \K[0-9]+(?=/)')
  local peak=$(echo "$concurrency_line" | grep -oP 'Peak: \K[0-9]+')
  local total=$(echo "$concurrency_line" | grep -oP 'Total: \K[0-9]+')
  local failed=$(echo "$concurrency_line" | grep -oP 'Failed: \K[0-9]+')
  local queue=$(echo "$concurrency_line" | grep -oP 'Queue: \K[0-9]+')
  
  if [ "$JSON_OUTPUT" = true ]; then
    echo "{"
    echo "  \"active_concurrent\": $active,"
    echo "  \"peak_concurrent\": $peak,"
    echo "  \"total_requests\": $total,"
    echo "  \"failed_requests\": $failed,"
    echo "  \"queue_depth\": ${queue:-0}"
    if [ -n "$system_line" ]; then
      local cpu=$(echo "$system_line" | grep -oP 'CPU: \K[0-9.]+')
      local memory=$(echo "$system_line" | grep -oP 'Memory: \K[0-9.]+')
      echo "  \"cpu_percent\": $cpu,"
      echo "  \"memory_mb\": $memory"
    fi
    echo "}"
  else
    # Human readable output
    if [ "$COLOR_ENABLED" = true ]; then
      echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
      echo -e "${CYAN}║${NC}  ${BLUE}Uvicorn Concurrency Monitor${NC}"
      echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
      echo -e "${CYAN}║${NC}  Active Concurrent:  ${GREEN}$active${NC}"
      echo -e "${CYAN}║${NC}  Peak Concurrent:    ${YELLOW}$peak${NC}"
      echo -e "${CYAN}║${NC}  Total Requests:     ${GREEN}$total${NC}"
      echo -e "${CYAN}║${NC}  Failed Requests:    ${RED}$failed${NC}"
      if [ -n "${queue:-}" ] && [ "$queue" -gt 0 ]; then
        echo -e "${CYAN}║${NC}  Queue Depth:        ${YELLOW}$queue${NC}"
      fi
    else
      echo "╔════════════════════════════════════════════════════════╗"
      echo "║  Uvicorn Concurrency Monitor"
      echo "╠════════════════════════════════════════════════════════╣"
      echo "║  Active Concurrent:  $active"
      echo "║  Peak Concurrent:    $peak"
      echo "║  Total Requests:     $total"
      echo "║  Failed Requests:    $failed"
      if [ -n "${queue:-}" ] && [ "$queue" -gt 0 ]; then
        echo "║  Queue Depth:        $queue"
      fi
    fi
    
    # Endpoints breakdown
    if [ -n "$endpoints_line" ]; then
      if [ "$COLOR_ENABLED" = true ]; then
        echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
        echo -e "${CYAN}║${NC}  ${BLUE}Active Endpoints:${NC}"
      else
        echo "╠════════════════════════════════════════════════════════╣"
        echo "║  Active Endpoints:"
      fi
      
      # Extract endpoint data and format
      local endpoint_data=$(echo "$endpoints_line" | sed 's/.*\[ENDPOINTS\] //')
      IFS='|' read -ra endpoints <<< "$endpoint_data"
      for ep in "${endpoints[@]}"; do
        ep=$(echo "$ep" | xargs)  # trim whitespace
        if [ "$COLOR_ENABLED" = true ]; then
          echo -e "${CYAN}║${NC}    • $ep"
        else
          echo "║    • $ep"
        fi
      done
    fi
    
    # System metrics
    if [ -n "$system_line" ]; then
      if [ "$COLOR_ENABLED" = true ]; then
        echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
        echo -e "${CYAN}║${NC}  ${BLUE}System Metrics:${NC}"
        local cpu=$(echo "$system_line" | grep -oP 'CPU: \K[0-9.]+')
        local memory=$(echo "$system_line" | grep -oP 'Memory: \K[0-9.]+')
        local threads=$(echo "$system_line" | grep -oP 'Threads: \K[0-9]+')
        echo -e "${CYAN}║${NC}    CPU: ${YELLOW}$cpu%${NC} | Memory: ${YELLOW}$memory MB${NC} | Threads: ${YELLOW}$threads${NC}"
      else
        echo "╠════════════════════════════════════════════════════════╣"
        echo "║  System Metrics:"
        local cpu=$(echo "$system_line" | grep -oP 'CPU: \K[0-9.]+')
        local memory=$(echo "$system_line" | grep -oP 'Memory: \K[0-9.]+')
        local threads=$(echo "$system_line" | grep -oP 'Threads: \K[0-9]+')
        echo "║    CPU: $cpu% | Memory: $memory MB | Threads: $threads"
      fi
    fi
    
    if [ "$COLOR_ENABLED" = true ]; then
      echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    else
      echo "╚════════════════════════════════════════════════════════╝"
    fi
  fi
}

# Function for watch mode
watch_metrics() {
  local log_file="$1"
  
  while true; do
    clear
    if [ "$COLOR_ENABLED" = true ]; then
      echo -e "${CYAN}Monitoring: $log_file${NC}"
      echo -e "${CYAN}Update interval: ${UPDATE_INTERVAL}s (Press Ctrl+C to stop)${NC}"
      echo ""
    else
      echo "Monitoring: $log_file"
      echo "Update interval: ${UPDATE_INTERVAL}s (Press Ctrl+C to stop)"
      echo ""
    fi
    
    extract_metrics "$log_file" || echo "Waiting for metrics..."
    sleep "$UPDATE_INTERVAL"
  done
}

# Main execution
if [ "$WATCH_MODE" = true ]; then
  watch_metrics "$MONITOR_LOG"
else
  if ! extract_metrics "$MONITOR_LOG"; then
    echo ""
    echo "To enable concurrency monitoring:"
    echo "  1. Set DEBUG logging: export DEBUG=true"
    echo "  2. Restart proxy: ./run_proxy.sh restart"
    echo "  3. Run monitor: ./monitor_uvicorn.sh --watch"
    exit 1
  fi
fi
