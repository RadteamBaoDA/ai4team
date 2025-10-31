# Concurrent Request Handling - Ollama-Style

## Overview

The Ollama Guard Proxy now implements concurrent request handling similar to Ollama's approach, providing robust queue management and parallelism control for high-load scenarios.

## Features

### 1. **Per-Model Parallelism Control**
Each model has its own request queue with configurable parallel execution limits.

### 2. **Automatic Memory Detection**
The system automatically detects available memory and sets appropriate parallelism limits:
- **≥ 16GB RAM**: 4 parallel requests per model (default)
- **≥ 8GB RAM**: 2 parallel requests per model
- **< 8GB RAM**: 1 parallel request per model (sequential)

### 3. **Request Queueing**
When all parallel slots are busy, requests are queued with a configurable maximum queue size (default: 512).

### 4. **Graceful Degradation**
When the queue is full, new requests receive a `503 Service Unavailable` response with a clear error message.

## Configuration

### Environment Variables

```bash
# Maximum parallel requests per model
# Options: 'auto' (memory-based), or a number (1, 2, 4, 8, etc.)
export OLLAMA_NUM_PARALLEL=auto

# Maximum queued requests before rejection
export OLLAMA_MAX_QUEUE=512

# Request timeout in seconds
export REQUEST_TIMEOUT=300
```

### YAML Configuration

```yaml
# config.yaml
concurrency:
  # Maximum parallel requests per model
  ollama_num_parallel: "auto"  # or a number: 1, 2, 4, 8, etc.
  
  # Maximum queue size
  ollama_max_queue: 512
  
  # Request timeout
  request_timeout: 300
  
  # Enable queue statistics
  enable_queue_stats: true
```

## API Endpoints

### Queue Statistics

**GET** `/queue/stats`

Get statistics for all models:

```bash
curl http://localhost:8080/queue/stats
```

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
      "active_requests": 3,
      "queued_requests": 5,
      "available_slots": 1,
      "queue_available": 507,
      "total_processed": 1234,
      "total_rejected": 12,
      "avg_wait_time_ms": 45.23,
      "avg_processing_time_ms": 2345.67,
      "uptime_seconds": 3600.5
    }
  }
}
```

**GET** `/queue/stats?model=llama2`

Get statistics for a specific model.

### Memory Information

**GET** `/queue/memory`

Get current memory status and recommended parallel limit:

```bash
curl http://localhost:8080/queue/memory
```

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

#### Reset Statistics

**POST** `/admin/queue/reset`

Reset statistics for all models:

```bash
curl -X POST http://localhost:8080/admin/queue/reset
```

Reset for a specific model:

```bash
curl -X POST "http://localhost:8080/admin/queue/reset?model=llama2"
```

#### Update Queue Limits

**POST** `/admin/queue/update`

Update limits for a specific model:

```bash
curl -X POST "http://localhost:8080/admin/queue/update" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "parallel_limit": 8,
    "queue_limit": 1024
  }'
```

Response:
```json
{
  "model": "llama2",
  "parallel_limit": 8,
  "queue_limit": 1024,
  "status": "updated"
}
```

## How It Works

### Request Flow

```
1. Request arrives → Extract model name
2. Get or create queue for model
3. Try to enqueue request (check queue limit)
4. Wait for available parallel slot (semaphore)
5. Execute request (scan input → forward to Ollama → scan output)
6. Release parallel slot
7. Return response
```

### Queue States

- **Available Slot**: Request executes immediately
- **Queued**: Request waits for an available slot
- **Queue Full**: Request rejected with 503 error

### Error Responses

#### Queue Full (503)

```json
{
  "error": "queue_full",
  "message": "Server is currently busy processing other requests. Please try again later.",
  "model": "llama2"
}
```

#### Request Timeout (504)

```json
{
  "error": "timeout",
  "message": "Request timed out. Please try again with a shorter prompt or later.",
  "model": "llama2"
}
```

## Monitoring

### Health Check

The `/health` endpoint now includes concurrency information:

```bash
curl http://localhost:8080/health
```

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

### Statistics Monitoring

Monitor queue statistics in real-time:

```bash
# Watch queue stats every 2 seconds
watch -n 2 'curl -s http://localhost:8080/queue/stats | jq'
```

Key metrics to monitor:
- **active_requests**: Currently processing
- **queued_requests**: Waiting in queue
- **total_rejected**: Requests rejected due to full queue
- **avg_wait_time_ms**: Average queue wait time
- **avg_processing_time_ms**: Average processing time

## Performance Tuning

### Optimal Settings

#### High Memory System (≥ 32GB)

```yaml
ollama_num_parallel: 8
ollama_max_queue: 1024
request_timeout: 300
```

#### Medium Memory System (16-32GB)

```yaml
ollama_num_parallel: 4
ollama_max_queue: 512
request_timeout: 300
```

#### Low Memory System (8-16GB)

```yaml
ollama_num_parallel: 2
ollama_max_queue: 256
request_timeout: 300
```

### Considerations

1. **Model Size**: Larger models require more memory per parallel request
2. **Prompt Length**: Longer prompts increase processing time and memory usage
3. **Guard Scanning**: Input/output scanning adds latency (use caching to optimize)
4. **Network Latency**: Consider timeout values based on Ollama response times

## Best Practices

### 1. Start with Auto-Detection

Let the system detect optimal settings:

```yaml
ollama_num_parallel: "auto"
```

### 2. Monitor and Adjust

Watch queue statistics and adjust based on:
- Rejection rate (`total_rejected`)
- Average wait time (`avg_wait_time_ms`)
- Available memory

### 3. Load Testing

Test your configuration under load:

```bash
# Concurrent requests with Apache Bench
ab -n 1000 -c 50 -p prompt.json -T application/json \
  http://localhost:8080/api/generate

# Or with wrk
wrk -t4 -c50 -d30s -s post.lua http://localhost:8080/api/generate
```

### 4. Per-Model Tuning

Different models may need different limits:

```bash
# Set high parallelism for fast model
curl -X POST "http://localhost:8080/admin/queue/update" \
  -d '{"model": "phi3", "parallel_limit": 8}'

# Set low parallelism for large model
curl -X POST "http://localhost:8080/admin/queue/update" \
  -d '{"model": "llama3-70b", "parallel_limit": 1}'
```

## Comparison with Ollama

| Feature | Ollama | Guard Proxy |
|---------|--------|-------------|
| **Parallel Requests** | 4 (default) or 1 | Auto-detect: 4/2/1 based on RAM |
| **Queue Size** | 512 (fixed) | 512 (configurable) |
| **Per-Model Queues** | Yes | Yes |
| **Dynamic Limits** | No | Yes (via API) |
| **Queue Statistics** | No | Yes (detailed metrics) |
| **Memory Detection** | Basic | Advanced with recommendations |

## Troubleshooting

### High Rejection Rate

**Problem**: Many requests rejected with `queue_full` error

**Solution**:
1. Increase queue size: `ollama_max_queue: 1024`
2. Increase parallelism (if memory allows): `ollama_num_parallel: 8`
3. Scale horizontally (add more proxy instances)

### High Wait Times

**Problem**: `avg_wait_time_ms` is high

**Solution**:
1. Increase parallelism: `ollama_num_parallel: 8`
2. Optimize Ollama backend (GPU, faster storage)
3. Enable Redis caching for guard results

### Memory Pressure

**Problem**: System running out of memory

**Solution**:
1. Reduce parallelism: `ollama_num_parallel: 2`
2. Reduce queue size: `ollama_max_queue: 256`
3. Add more RAM or optimize model usage

## Examples

### Python Client

```python
import requests
import time

def call_with_retry(prompt, max_retries=3):
    url = "http://localhost:8080/api/generate"
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json={
                "model": "llama2",
                "prompt": prompt,
                "stream": False
            }, timeout=300)
            
            if response.status_code == 503:
                # Queue full, wait and retry
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Queue full, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            print("Request timed out")
            if attempt < max_retries - 1:
                continue
            raise
    
    raise Exception("Max retries exceeded")

# Usage
result = call_with_retry("What is AI?")
print(result['response'])
```

### Concurrent Load Testing

```python
import asyncio
import aiohttp

async def send_request(session, prompt, model="llama2"):
    url = "http://localhost:8080/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    
    async with session.post(url, json=payload) as response:
        return await response.json()

async def load_test(num_requests=100):
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_request(session, f"Question {i}")
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = num_requests - successes
        
        print(f"Successes: {successes}, Failures: {failures}")
        return results

# Run load test
asyncio.run(load_test(100))
```

## Conclusion

The concurrent request handling system provides Ollama-compatible queue management with enhanced monitoring and control capabilities. It ensures efficient resource utilization while maintaining system stability under high load.

For additional support, see:
- [Configuration Guide](QUICK_START.md)
- [Performance Tuning](OPTIMIZATION_SUMMARY.md)
- [Monitoring Guide](README_OPTIMIZED.md)
