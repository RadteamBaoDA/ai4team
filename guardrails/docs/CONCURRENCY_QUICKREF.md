# Concurrency Quick Reference

## Configuration

```yaml
# Auto-detect based on memory
ollama_num_parallel: "auto"

# Or set manually
ollama_num_parallel: 4

# Queue size
ollama_max_queue: 512

# Timeout
request_timeout: 300
```

## Environment Variables

```bash
export OLLAMA_NUM_PARALLEL=auto  # or 1, 2, 4, 8
export OLLAMA_MAX_QUEUE=512
export REQUEST_TIMEOUT=300
```

## Quick Commands

```bash
# Check queue stats
curl http://localhost:8080/queue/stats

# Check specific model
curl http://localhost:8080/queue/stats?model=llama2

# Check memory
curl http://localhost:8080/queue/memory

# Reset stats
curl -X POST http://localhost:8080/admin/queue/reset

# Update limits
curl -X POST http://localhost:8080/admin/queue/update \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2", "parallel_limit": 8, "queue_limit": 1024}'
```

## Auto-Detection Logic

| Available RAM | Parallel Limit |
|---------------|----------------|
| ≥ 16GB        | 4              |
| ≥ 8GB         | 2              |
| < 8GB         | 1              |

## Error Codes

| Code | Error | Meaning |
|------|-------|---------|
| 503  | queue_full | Queue is full, retry later |
| 504  | timeout | Request timeout, reduce prompt size |

## Metrics to Monitor

- `active_requests`: Currently processing
- `queued_requests`: Waiting in queue
- `total_rejected`: Rejected due to full queue
- `avg_wait_time_ms`: Average wait time
- `avg_processing_time_ms`: Average processing time

## Recommended Settings

### High Load (32GB+ RAM)
```yaml
ollama_num_parallel: 8
ollama_max_queue: 1024
```

### Medium Load (16GB RAM)
```yaml
ollama_num_parallel: 4
ollama_max_queue: 512
```

### Low Load (8GB RAM)
```yaml
ollama_num_parallel: 2
ollama_max_queue: 256
```

## Python Client with Retry

```python
import requests
import time

def call_with_retry(prompt, max_retries=3):
    url = "http://localhost:8080/api/generate"
    
    for attempt in range(max_retries):
        response = requests.post(url, json={
            "model": "llama2",
            "prompt": prompt
        }, timeout=300)
        
        if response.status_code == 503:
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        
        response.raise_for_status()
        return response.json()
    
    raise Exception("Max retries exceeded")
```

## Load Testing

```bash
# Apache Bench
ab -n 1000 -c 50 -p prompt.json -T application/json \
  http://localhost:8080/api/generate

# Watch stats during test
watch -n 1 'curl -s http://localhost:8080/queue/stats | jq .models'
```
