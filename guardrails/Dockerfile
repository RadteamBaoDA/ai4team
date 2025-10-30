# Multi-architecture support for x86_64 and ARM64 (Apple Silicon)
FROM --platform=$BUILDPLATFORM python:3.11-slim AS base

WORKDIR /app

# Build arguments for multi-platform support
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install system dependencies with platform-specific optimizations
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    make \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements
COPY requirements.txt .

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

# Copy application files
COPY *.py .
COPY config.yaml ./config.yaml 2>/dev/null || true

# Create necessary directories
RUN mkdir -p /app/logs /app/models

# Set environment variables for optimal performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # PyTorch optimizations
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4 \
    # Guardrails configuration
    LLM_GUARD_DEVICE=cpu \
    LLM_GUARD_USE_LOCAL_MODELS=false \
    # Security hardening
    PYTHONHTTPSVERIFY=1

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8080

# Health check with improved parameters
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the proxy with uvicorn for better performance
CMD ["python", "-m", "uvicorn", "ollama_guard_proxy:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--log-level", "info"]
