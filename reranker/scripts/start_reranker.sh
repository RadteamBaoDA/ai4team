#!/usr/bin/env bash
# Bootstrap script for the reranker FastAPI service.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv"

# Environment defaults – override by exporting before invoking this script
# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
export RERANKER_MODEL="${RERANKER_MODEL:-cross-encoder/ms-marco-MiniLM-L-6-v2}"
export RERANKER_MODEL_LOCAL_PATH="${RERANKER_MODEL_LOCAL_PATH:-}"  # optional local model cache
export RERANKER_USE_MLX="${RERANKER_USE_MLX:-false}"  # use MLX backend on Apple Silicon

# ============================================================================
# PERFORMANCE & CONCURRENCY (critical for high-load scenarios)
# ============================================================================
export RERANKER_MAX_PARALLEL="${RERANKER_MAX_PARALLEL:-4}"  # number of concurrent inference jobs
export RERANKER_MAX_QUEUE="${RERANKER_MAX_QUEUE:-}"  # max waiting requests (empty = unlimited)
export RERANKER_QUEUE_TIMEOUT="${RERANKER_QUEUE_TIMEOUT:-30.0}"  # wait time for slot acquisition
export RERANKER_WORKER_TIMEOUT="${RERANKER_WORKER_TIMEOUT:-300.0}"  # worker timeout
export RERANKER_MAX_RETRIES="${RERANKER_MAX_RETRIES:-2}"  # max retries for failed requests

# ============================================================================
# MODEL PERFORMANCE & OPTIMIZATION
# ============================================================================
export RERANKER_MAX_LENGTH="${RERANKER_MAX_LENGTH:-512}"  # max input sequence length
export RERANKER_DEVICE="${RERANKER_DEVICE:-auto}"  # auto, cpu, cuda, mps, mlx
export RERANKER_BATCH_SIZE="${RERANKER_BATCH_SIZE:-8}"  # inference batch size
export ENABLE_TORCH_COMPILE="${ENABLE_TORCH_COMPILE:-false}"  # torch.compile() optimization
export ENABLE_MIXED_PRECISION="${ENABLE_MIXED_PRECISION:-false}"  # mixed precision (float16) for CUDA
export WARMUP_ON_START="${WARMUP_ON_START:-true}"  # warm up model on startup

# ============================================================================
# QUANTIZATION (memory optimization)
# ============================================================================
export QUANTIZATION="${QUANTIZATION:-none}"  # none, bf16, int8
# bf16: 50% memory reduction, minimal accuracy impact (CUDA only)
# int8: 75% memory reduction, requires bitsandbytes (CUDA only)

# ============================================================================
# CACHING & MEMORY
# ============================================================================
export ENABLE_PREDICTION_CACHE="${ENABLE_PREDICTION_CACHE:-true}"  # enable local response caching
export CACHE_TTL_SECONDS="${CACHE_TTL_SECONDS:-300}"  # local cache TTL in seconds
export CLEAR_CACHE_INTERVAL="${CLEAR_CACHE_INTERVAL:-3600}"  # cache cleanup interval

# ============================================================================
# REDIS DISTRIBUTED CACHE (multi-server coordination)
# ============================================================================
export REDIS_ENABLED="${REDIS_ENABLED:-false}"  # enable Redis distributed cache
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"  # Redis connection URL
export REDIS_TTL_SECONDS="${REDIS_TTL_SECONDS:-600}"  # Redis cache TTL (10 min default)
# Use Redis for: multi-server deployments, request deduplication, shared caching

# ============================================================================
# MICRO-BATCHING (GPU efficiency for bursty traffic)
# ============================================================================
export MICRO_BATCH_ENABLED="${MICRO_BATCH_ENABLED:-false}"  # enable micro-batching
export MICRO_BATCH_WINDOW_MS="${MICRO_BATCH_WINDOW_MS:-10.0}"  # collection window in milliseconds
export MICRO_BATCH_MAX_SIZE="${MICRO_BATCH_MAX_SIZE:-32}"  # max batch size
# Micro-batching adds ~10ms latency but improves throughput by 30-50%

# ============================================================================
# DISTRIBUTED MODE (experimental)
# ============================================================================
export RERANKER_DISTRIBUTED="${RERANKER_DISTRIBUTED:-false}"  # enable distributed processing

# SERVER CONFIGURATION
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
        echo "Use './manage_reranker.sh tail' to follow logs."
        nohup uvicorn "${APP_PATH}" "${COMMON_ARGS[@]}" "$@" >>"${LOG_FILE}" 2>&1 &
        echo $! > "${PID_FILE}"
        echo "Reranker started with PID $(cat "${PID_FILE}")"
        ;;
    fg)
        echo "Starting reranker in foreground production mode."
        exec uvicorn "${APP_PATH}" "${COMMON_ARGS[@]}" "$@"
        ;;
    *)
        echo "Unknown mode '${MODE}'. Use 'dev', 'daemon', or 'fg'." >&2
        echo ""
        echo "Environment variables (customize before running):"
        echo ""
        echo "  Core Settings:"
        echo "    RERANKER_MODEL           # Model name or path"
        echo "    RERANKER_DEVICE          # Device: auto/cpu/cuda/mps/mlx (default: auto)"
        echo "    RERANKER_MAX_PARALLEL    # Concurrent inference jobs (default: 4)"
        echo "    RERANKER_BATCH_SIZE      # Inference batch size (default: 8)"
        echo ""
        echo "  Performance Optimization:"
        echo "    QUANTIZATION             # none/bf16/int8 (default: none)"
        echo "    ENABLE_TORCH_COMPILE     # PyTorch 2.0 optimization (default: false)"
        echo "    ENABLE_MIXED_PRECISION   # Float16 for CUDA (default: false)"
        echo ""
        echo "  Advanced Features:"
        echo "    REDIS_ENABLED            # Distributed cache (default: false)"
        echo "    REDIS_URL                # Redis URL (default: redis://localhost:6379/0)"
        echo "    MICRO_BATCH_ENABLED      # Micro-batching (default: false)"
        echo "    MICRO_BATCH_WINDOW_MS    # Batch window ms (default: 10.0)"
        echo ""
        echo "  Caching:"
        echo "    ENABLE_PREDICTION_CACHE  # Local cache (default: true)"
        echo "    CACHE_TTL_SECONDS        # Local TTL (default: 300)"
        echo ""
        echo "Examples:"
        echo ""
        echo "  # Basic production setup"
        echo "  RERANKER_DEVICE=cuda QUANTIZATION=bf16 ./start_reranker.sh fg"
        echo ""
        echo "  # High-performance setup with all features"
        echo "  REDIS_ENABLED=true MICRO_BATCH_ENABLED=true QUANTIZATION=bf16 \\"
        echo "  ENABLE_MIXED_PRECISION=true ./start_reranker.sh daemon"
        echo ""
        echo "  # Multi-server setup"
        echo "  REDIS_ENABLED=true REDIS_URL=redis://redis-server:6379/0 \\"
        echo "  RERANKER_MAX_PARALLEL=8 ./start_reranker.sh daemon"
        echo ""
        echo "For detailed documentation, see:"
        echo "  - docs/ADVANCED_QUICKSTART.md  (quick reference)"
        echo "  - docs/ADVANCED_FEATURES.md    (comprehensive guide)"
        echo "  - docs/ENV_VARS_QUICK_REF.md   (all environment variables)"
        exit 1
        ;;
 esac