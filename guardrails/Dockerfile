# Multi-architecture support for x86_64 and ARM64 (Apple Silicon)
FROM --platform=$BUILDPLATFORM python:3.12-slim AS base

WORKDIR /app

# Build arguments for multi-platform support
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG VERSION=1.0.0

# Install system dependencies with platform-specific optimizations
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    make \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python project configuration first for better layer caching
COPY pyproject.toml setup.py MANIFEST.in ./
COPY requirements.txt ./

# Install Python dependencies with platform-specific optimizations
# For Apple Silicon (ARM64), use pre-built wheels when available
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "Building for ARM64 (Apple Silicon compatible)"; \
        # Install PyTorch with CPU support for ARM64
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    else \
        echo "Building for x86_64"; \
    fi && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code in proper package structure
COPY main.py ./
COPY src/ ./src/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p /app/logs /app/models

# Install the package in editable mode for development
# This ensures proper Python package structure and importability
RUN pip install --no-cache-dir -e .

# Set environment variables for optimal performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # PyTorch optimizations
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4 \
    # Guardrails configuration
    LLM_GUARD_DEVICE=cpu \
    LLM_GUARD_USE_LOCAL_MODELS=false \
    # Default configuration
    PROXY_HOST=0.0.0.0 \
    PROXY_PORT=8080 \
    CONFIG_FILE=/app/config/config.yaml \
    # Security hardening
    PYTHONHTTPSVERIFY=1

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/models /app/cache && \
    chmod 755 /app/logs /app/models /app/cache

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8080

# Health check with improved parameters
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Use the proper entry point - can use main.py or the CLI
# Multiple options for flexibility:
# Option 1: Direct module execution (recommended)
CMD ["python", "-m", "ollama_guardrails", "server"]
# Option 2: Via main.py (fallback)
# CMD ["python", "main.py"]
# Option 3: Via uvicorn directly (advanced)
# CMD ["uvicorn", "ollama_guardrails.app:app", "--host", "0.0.0.0", "--port", "8080"]
