# Configuration files directory
# This directory contains environment-specific configuration files

## Files in this directory:

- `production.env` - Production environment variables
- `development.env` - Development environment variables  
- `docker.env` - Docker container environment variables
- `apple_silicon.env` - Optimized settings for Apple Silicon Macs

## Usage:

Load environment files before starting the service:

```bash
# Development
source config/development.env
python main.py

# Production  
source config/production.env
python main.py

# Docker
docker run --env-file config/docker.env reranker-service
```