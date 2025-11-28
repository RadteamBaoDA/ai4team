# LLM Guard API Makefile
# Convenience commands for building and running the API

.PHONY: help build run stop logs clean test litellm

# Default target
help:
	@echo "LLM Guard API - Available commands:"
	@echo ""
	@echo "  Docker Commands:"
	@echo "    make build       - Build Docker image"
	@echo "    make build-gpu   - Build Docker image with GPU support"
	@echo "    make build-macos - Build Docker image for macOS (Apple Silicon)"
	@echo "    make run         - Start the API container"
	@echo "    make run-gpu     - Start the API container with GPU support"
	@echo "    make run-macos   - Start the API container for macOS"
	@echo "    make stop        - Stop the API container"
	@echo "    make logs        - View container logs"
	@echo "    make clean       - Remove containers and images"
	@echo ""
	@echo "  Local Commands:"
	@echo "    make install     - Install dependencies locally"
	@echo "    make run-local   - Run API locally (without Docker)"
	@echo "    make test        - Run health check"
	@echo ""
	@echo "  LiteLLM Commands:"
	@echo "    make litellm           - Start LiteLLM proxy with LLM Guard"
	@echo "    make litellm-advanced  - Start LiteLLM with advanced config"
	@echo "    make litellm-install   - Install LiteLLM proxy"
	@echo ""

# Build Docker image
build:
	docker-compose build

build-gpu:
	docker-compose -f docker-compose.gpu.yml build

build-macos:
	docker-compose -f docker-compose.macos.yml build

# Run the API
run:
	docker-compose up -d

run-gpu:
	docker-compose -f docker-compose.gpu.yml up -d

run-macos:
	docker-compose -f docker-compose.macos.yml up -d

# Stop the API
stop:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Clean up
clean:
	docker-compose down -v --rmi local
	docker-compose -f docker-compose.gpu.yml down -v --rmi local 2>/dev/null || true
	docker-compose -f docker-compose.macos.yml down -v --rmi local 2>/dev/null || true

# Health check
test:
	@echo "Checking API health..."
	@curl -sf http://localhost:8000/healthz && echo "API is healthy" || echo "API is not responding"

# Install dependencies locally
install:
	pip install -r requirements.txt

# Run locally without Docker
run-local:
	llm_guard_api ./config/scanners.yml

# ===== LiteLLM Commands =====

# Install LiteLLM proxy
litellm-install:
	pip install 'litellm[proxy]'

# Start LiteLLM proxy with LLM Guard integration
litellm:
	@echo "Starting LiteLLM with LLM Guard..."
	@echo "LLM Guard API: $${LLM_GUARD_API_BASE:-http://localhost:8000}"
	LLM_GUARD_API_BASE=$${LLM_GUARD_API_BASE:-http://localhost:8000} \
	OLLAMA_API_BASE=$${OLLAMA_API_BASE:-http://192.168.1.2:11434} \
	litellm --config litellm_llmguard_config.yaml --port 4000

# Start LiteLLM with advanced configuration
litellm-advanced:
	@echo "Starting LiteLLM with advanced config..."
	LLM_GUARD_API_BASE=$${LLM_GUARD_API_BASE:-http://localhost:8000} \
	OLLAMA_API_BASE=$${OLLAMA_API_BASE:-http://192.168.1.2:11434} \
	LITELLM_MASTER_KEY=$${LITELLM_MASTER_KEY:-sk-litellm-master-key} \
	litellm --config litellm_advanced_config.yaml --port 4000

# Test LiteLLM endpoint
litellm-test:
	@echo "Testing LiteLLM endpoint..."
	@curl -sf http://localhost:4000/health && echo "LiteLLM is healthy" || echo "LiteLLM is not responding"
