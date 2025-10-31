# Multi-architecture support for x86_64 and ARM64 (Apple Silicon)
FROM --platform=$BUILDPLATFORM python:3.12-slim AS base

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
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with platform-specific optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "Building for ARM64 (Apple Silicon compatible)"; \
        # Install PyTorch with CPU support for ARM64
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    else \
        echo "Building for x86_64"; \
        # Install PyTorch with CUDA support for x86_64
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu118; \
    fi && \
    # Install core dependencies
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY pyproject.toml .
COPY setup.py .
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Install the package in development mode
RUN pip install -e .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/models /app/cache && \
    chmod 755 /app/logs /app/models /app/cache

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
    # Reranker default configuration
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    RERANKER_DEVICE=auto \
    RERANKER_MAX_PARALLEL=4 \
    RERANKER_BATCH_SIZE=16 \
    ENABLE_PREDICTION_CACHE=true \
    # Security hardening
    PYTHONHTTPSVERIFY=1

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash reranker && \
    chown -R reranker:reranker /app

USER reranker

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set the default command
CMD ["python", "main.py"]