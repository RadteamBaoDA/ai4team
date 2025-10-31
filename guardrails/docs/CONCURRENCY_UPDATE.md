# Ollama Guard Proxy - Concurrent Request Handling Update

## Overview

The Ollama Guard Proxy has been enhanced with **Ollama-style concurrent request handling**, implementing proper queue management and parallelism control to efficiently handle high-load scenarios.

## New Features

### 🔄 Concurrent Request Processing
- **Per-Model Queuing**: Each model has its own request queue with independent parallelism limits
- **Automatic Memory Detection**: Intelligently sets parallel limits based on available RAM
- **Queue Management**: Configurable queue size with graceful rejection when full
- **Request Timeout**: Configurable timeout for queued requests

### 📊 Queue Monitoring
- **Real-time Statistics**: Track active, queued, processed, and rejected requests per model
- **Performance Metrics**: Average wait time and processing time tracking
- **Memory Monitoring**: Current memory usage and recommended parallel limits

### ⚙️ Dynamic Configuration
- **Runtime Updates**: Adjust parallelism and queue limits without restart
- **Per-Model Tuning**: Different limits for different models
- **Admin API**: RESTful endpoints for queue management

## Quick Start

### 1. Update Dependencies

```bash
pip install -r requirements.txt
# Adds: psutil>=5.9.0
```

### 2. Configure Concurrency

**Option A: Auto-Detection (Recommended)**

```yaml
# config.yaml
ollama_num_parallel: "auto"  # Detects based on RAM
ollama_max_queue: 512
request_timeout: 300
```

**Option B: Manual Configuration**

```yaml
# config.yaml
ollama_num_parallel: 4  # Fixed value
ollama_max_queue: 512
request_timeout: 300
```

**Option C: Environment Variables**

```bash
export OLLAMA_NUM_PARALLEL=auto
export OLLAMA_MAX_QUEUE=512
export REQUEST_TIMEOUT=300
```

### 3. Start the Proxy

```bash
# Standard start
python ollama_guard_proxy.py

# Or with script
./run_proxy.sh start
```

### 4. Monitor Queue Status

```bash
# Check overall stats
curl http://localhost:8080/queue/stats

# Check specific model
curl http://localhost:8080/queue/stats?model=llama2

# Check memory info
curl http://localhost:8080/queue/memory

# Health check (includes concurrency info)
curl http://localhost:8080/health
```

## Configuration Details

### Auto-Detection Logic

The system automatically detects optimal parallelism based on available memory:

| Available RAM | Parallel Limit |
|---------------|----------------|
| ≥ 16GB        | 4 parallel requests |
| ≥ 8GB         | 2 parallel requests |
| < 8GB         | 1 parallel request (sequential) |

### Configuration Options

```yaml
# Concurrency Configuration
ollama_num_parallel: "auto"  # Options: "auto", 1, 2, 4, 8, etc.
ollama_max_queue: 512         # Maximum queued requests
request_timeout: 300          # Request timeout in seconds
enable_queue_stats: true      # Enable statistics tracking
```

## API Endpoints

### Queue Statistics

**GET `/queue/stats`**
- Get statistics for all models

**GET `/queue/stats?model=<name>`**
- Get statistics for a specific model

Response:
```json
{
  "default_parallel": 4,
  "default_queue_limit": 512,
  "total_models": 2,
  "models": {
    "llama2": {
      "model": "llama2",
      "parallel_limit": 4,
      "queue_limit": 512,
      "active_requests": 2,
      "queued_requests": 3,
      "available_slots": 2,
      "queue_available": 509,
      "total_processed": 1234,
      "total_rejected": 5,
      "avg_wait_time_ms": 45.2,
      "avg_processing_time_ms": 2340.5,
      "uptime_seconds": 3600
    }
  }
}
```

### Memory Information

**GET `/queue/memory`**

Response:
```json
{
  "total_gb": 32.0,
  "available_gb": 18.5,
  "used_gb": 13.5,
  "percent": 42.2,
  "recommended_parallel": 4
}
```

### Admin Endpoints

**POST `/admin/queue/reset`**
- Reset statistics for all models or a specific model

**POST `/admin/queue/update`**
- Update parallelism and queue limits for a model

```bash
curl -X POST http://localhost:8080/admin/queue/update \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "parallel_limit": 8,
    "queue_limit": 1024
  }'
```

## Error Handling

### Queue Full (503)

When the queue is full, clients receive:

```json
{
  "error": "queue_full",
  "message": "Server is currently busy processing other requests. Please try again later.",
  "model": "llama2"
}
```

**Client should**: Wait and retry with exponential backoff

### Request Timeout (504)

When a request exceeds the timeout:

```json
{
  "error": "timeout",
  "message": "Request timed out. Please try again with a shorter prompt or later.",
  "model": "llama2"
}
```

**Client should**: Reduce prompt size or retry later

## Monitoring

### Health Check

The `/health` endpoint now includes concurrency information:

```json
{
  "status": "healthy",
  "timestamp": "2025-10-31T12:00:00",
  "concurrency": {
    "default_parallel": 4,
    "default_queue_limit": 512,
    "total_models": 2,
    "memory": {
      "total_gb": 32.0,
      "available_gb": 18.5,
      "used_gb": 13.5,
      "percent": 42.2,
      "recommended_parallel": 4
    }
  },
  "guards": { ... },
  "cache": { ... }
}
```

### Real-time Monitoring

```bash
# Watch queue stats every 2 seconds
watch -n 2 'curl -s http://localhost:8080/queue/stats | jq .models'

# Monitor specific model
watch -n 1 'curl -s "http://localhost:8080/queue/stats?model=llama2" | jq'

# Monitor memory
watch -n 5 'curl -s http://localhost:8080/queue/memory | jq'
```

## Performance Tuning

### Recommended Settings by Workload

#### High Throughput (32GB+ RAM)
```yaml
ollama_num_parallel: 8
ollama_max_queue: 1024
request_timeout: 300
```

#### Balanced (16-32GB RAM)
```yaml
ollama_num_parallel: 4
ollama_max_queue: 512
request_timeout: 300
```

#### Low Resource (8-16GB RAM)
```yaml
ollama_num_parallel: 2
ollama_max_queue: 256
request_timeout: 300
```

### Per-Model Optimization

Different models may need different limits:

```bash
# Fast, small model - high parallelism
curl -X POST http://localhost:8080/admin/queue/update \
  -d '{"model": "phi3", "parallel_limit": 8}'

# Large model - low parallelism
curl -X POST http://localhost:8080/admin/queue/update \
  -d '{"model": "llama3-70b", "parallel_limit": 1}'
```

## Client Integration

### Python with Retry Logic

```python
import requests
import time

def call_ollama_with_retry(prompt, model="llama2", max_retries=3):
    url = "http://localhost:8080/api/generate"
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }, timeout=300)
            
            if response.status_code == 503:
                # Queue full, exponential backoff
                wait_time = 2 ** attempt
                print(f"Queue full, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print("Timeout, retrying...")
                continue
            raise
    
    raise Exception("Max retries exceeded")

# Usage
result = call_ollama_with_retry("What is AI?")
print(result['response'])
```

## Load Testing

### Apache Bench

```bash
# Create test payload
echo '{"model":"llama2","prompt":"Test","stream":false}' > prompt.json

# Run load test
ab -n 1000 -c 50 -p prompt.json -T application/json \
  http://localhost:8080/api/generate

# Monitor during test
watch -n 1 'curl -s http://localhost:8080/queue/stats | jq .models'
```

### Async Load Test (Python)

```python
import asyncio
import aiohttp

async def send_request(session, i):
    url = "http://localhost:8080/api/generate"
    payload = {"model": "llama2", "prompt": f"Test {i}", "stream": False}
    
    async with session.post(url, json=payload) as response:
        return await response.json()

async def load_test(num_requests=100):
    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session, i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = sum(1 for r in results if not isinstance(r, Exception))
        print(f"Success rate: {successes}/{num_requests}")

asyncio.run(load_test(100))
```

## Comparison with Ollama

| Feature | Ollama | Guard Proxy |
|---------|--------|-------------|
| Parallel Requests | 4 or 1 (fixed) | Auto-detect: 4/2/1 |
| Queue Size | 512 (fixed) | Configurable |
| Per-Model Queues | Yes | Yes |
| Dynamic Limits | No | Yes |
| Queue Statistics | No | Detailed metrics |
| Memory Detection | Basic | Advanced |
| Admin API | No | Full REST API |

## Troubleshooting

### High Rejection Rate
- **Symptom**: Many 503 errors
- **Solution**: Increase `ollama_max_queue` or `ollama_num_parallel`

### High Wait Times
- **Symptom**: High `avg_wait_time_ms`
- **Solution**: Increase `ollama_num_parallel` or optimize backend

### Memory Issues
- **Symptom**: System OOM errors
- **Solution**: Reduce `ollama_num_parallel` or add more RAM

## Documentation

- **[Detailed Guide](docs/CONCURRENCY_GUIDE.md)**: Complete documentation
- **[Quick Reference](docs/CONCURRENCY_QUICKREF.md)**: Command reference
- **[Configuration](config.yaml)**: Sample configuration

## Migration from Previous Version

No breaking changes! The system works with existing configurations:

1. **Auto-upgrade**: Set `ollama_num_parallel: "auto"` in `config.yaml`
2. **Manual**: Set specific value like `ollama_num_parallel: 4`
3. **Default**: If not configured, uses auto-detection

Existing installations will continue to work without changes.

## Files Changed

- `guardrails/concurrency.py` - New concurrency manager
- `guardrails/ollama_guard_proxy.py` - Integrated concurrency control
- `guardrails/config.yaml` - Added concurrency settings
- `guardrails/language.py` - Added new error messages
- `guardrails/requirements.txt` - Already includes psutil
- `guardrails/docs/CONCURRENCY_GUIDE.md` - Complete guide
- `guardrails/docs/CONCURRENCY_QUICKREF.md` - Quick reference

## Next Steps

1. Review configuration in `config.yaml`
2. Start proxy and check `/health` endpoint
3. Monitor queue stats during load testing
4. Tune parallelism based on your workload
5. Set up alerts for high rejection rates

---

**Questions or Issues?** Check the [Concurrency Guide](docs/CONCURRENCY_GUIDE.md) or open an issue.
