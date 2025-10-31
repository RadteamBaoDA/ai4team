# Concurrency Testing Guide

## Quick Test Commands

### 1. Basic Functionality Test

```bash
# Start the proxy
./run_proxy.sh start

# Check health (should show concurrency info)
curl http://localhost:8080/health | jq .concurrency

# Expected output:
# {
#   "default_parallel": 4,
#   "default_queue_limit": 512,
#   "total_models": 0,
#   "memory": {...}
# }
```

### 2. Memory Detection Test

```bash
# Check memory info
curl http://localhost:8080/queue/memory | jq

# Expected output:
# {
#   "total_gb": 32.0,
#   "available_gb": 18.5,
#   "used_gb": 13.5,
#   "percent": 42.2,
#   "recommended_parallel": 4
# }
```

### 3. Single Request Test

```bash
# Send a test request
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "What is AI?",
    "stream": false
  }'

# Check queue stats after request
curl http://localhost:8080/queue/stats | jq
```

### 4. Concurrent Requests Test

```bash
# Send 10 requests concurrently
for i in {1..10}; do
  curl -X POST http://localhost:8080/api/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"llama2\",\"prompt\":\"Test $i\",\"stream\":false}" &
done

# Wait for completion
wait

# Check statistics
curl http://localhost:8080/queue/stats?model=llama2 | jq
```

### 5. Queue Full Test

```bash
# Configure small limits for testing
curl -X POST http://localhost:8080/admin/queue/update \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "parallel_limit": 1, "queue_limit": 2}'

# Send many requests to trigger queue full
for i in {1..10}; do
  curl -X POST http://localhost:8080/api/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"test\",\"prompt\":\"Test $i\",\"stream\":false}" &
done

# You should see some 503 errors
```

## Load Testing

### Apache Bench

```bash
# Create test payload
cat > prompt.json << EOF
{
  "model": "llama2",
  "prompt": "What is machine learning?",
  "stream": false
}
EOF

# Run load test
ab -n 100 -c 10 -p prompt.json -T application/json \
  http://localhost:8080/api/generate

# Monitor during test
watch -n 1 'curl -s http://localhost:8080/queue/stats | jq .models'
```

### wrk (Advanced)

```bash
# Create Lua script
cat > post.lua << 'EOF'
wrk.method = "POST"
wrk.body   = '{"model":"llama2","prompt":"Test","stream":false}'
wrk.headers["Content-Type"] = "application/json"
EOF

# Run test
wrk -t4 -c20 -d30s -s post.lua http://localhost:8080/api/generate

# Results will show:
# - Requests/sec
# - Latency distribution
# - Error rate
```

### Python Load Test

```python
import asyncio
import aiohttp
import time

async def send_request(session, i):
    url = "http://localhost:8080/api/generate"
    payload = {
        "model": "llama2",
        "prompt": f"Test request {i}",
        "stream": False
    }
    
    start = time.time()
    try:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            elapsed = time.time() - start
            return {"status": response.status, "time": elapsed, "error": None}
    except Exception as e:
        elapsed = time.time() - start
        return {"status": 0, "time": elapsed, "error": str(e)}

async def load_test(num_requests=100, concurrency=10):
    async with aiohttp.ClientSession() as session:
        # Send requests in batches
        all_results = []
        for batch_start in range(0, num_requests, concurrency):
            batch_end = min(batch_start + concurrency, num_requests)
            tasks = [
                send_request(session, i)
                for i in range(batch_start, batch_end)
            ]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Analyze results
        success = sum(1 for r in all_results if r["status"] == 200)
        queue_full = sum(1 for r in all_results if r["status"] == 503)
        errors = sum(1 for r in all_results if r["status"] not in [200, 503])
        
        times = [r["time"] for r in all_results if r["status"] == 200]
        avg_time = sum(times) / len(times) if times else 0
        
        print(f"\nLoad Test Results:")
        print(f"  Total requests: {num_requests}")
        print(f"  Successful: {success} ({success/num_requests*100:.1f}%)")
        print(f"  Queue full (503): {queue_full}")
        print(f"  Errors: {errors}")
        print(f"  Average response time: {avg_time:.2f}s")
        
        return all_results

# Run test
if __name__ == "__main__":
    asyncio.run(load_test(num_requests=100, concurrency=20))
```

## Monitoring During Tests

### Real-time Queue Stats

```bash
# Terminal 1: Run load test
ab -n 1000 -c 50 -p prompt.json -T application/json \
  http://localhost:8080/api/generate

# Terminal 2: Monitor queue stats
watch -n 0.5 'curl -s http://localhost:8080/queue/stats | jq -r ".models.llama2 | \
  \"Active: \(.active_requests)/\(.parallel_limit) | \
  Queued: \(.queued_requests)/\(.queue_limit) | \
  Processed: \(.total_processed) | \
  Rejected: \(.total_rejected) | \
  Avg Wait: \(.avg_wait_time_ms)ms\""'
```

### Memory Monitoring

```bash
# Monitor memory usage
watch -n 2 'curl -s http://localhost:8080/queue/memory | jq'
```

### Combined Dashboard

```bash
#!/bin/bash
# dashboard.sh - Real-time monitoring dashboard

while true; do
    clear
    echo "======================================"
    echo " Ollama Guard Proxy - Queue Dashboard"
    echo "======================================"
    echo
    
    # Queue stats
    echo "Queue Statistics:"
    curl -s http://localhost:8080/queue/stats | jq -r '.models | to_entries[] | 
        "\(.key):
          Active: \(.value.active_requests)/\(.value.parallel_limit)
          Queued: \(.value.queued_requests)/\(.value.queue_limit)
          Processed: \(.value.total_processed)
          Rejected: \(.value.total_rejected)
          Avg Wait: \(.value.avg_wait_time_ms)ms
          Avg Process: \(.value.avg_processing_time_ms)ms"'
    
    echo
    echo "Memory:"
    curl -s http://localhost:8080/queue/memory | jq -r '
        "Available: \(.available_gb)GB / \(.total_gb)GB (\(100 - .percent | floor)% free)
         Recommended Parallel: \(.recommended_parallel)"'
    
    sleep 1
done
```

## Test Scenarios

### Scenario 1: Gradual Load Increase

```python
import asyncio
import aiohttp

async def gradual_load_test():
    """Start with low load and gradually increase"""
    session = aiohttp.ClientSession()
    
    for concurrency in [1, 5, 10, 20, 50]:
        print(f"\nTesting with {concurrency} concurrent requests...")
        
        start = asyncio.get_event_loop().time()
        tasks = [send_request(session, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = asyncio.get_event_loop().time() - start
        
        success = sum(1 for r in results if not isinstance(r, Exception))
        print(f"  Completed in {elapsed:.2f}s")
        print(f"  Success rate: {success}/{concurrency}")
        
        await asyncio.sleep(2)  # Cool down between tests
    
    await session.close()

asyncio.run(gradual_load_test())
```

### Scenario 2: Sustained Load

```bash
# Run constant load for 5 minutes
duration=300  # 5 minutes
rate=10       # 10 req/sec

echo "Running sustained load test for ${duration}s at ${rate} req/sec"

end_time=$(($(date +%s) + duration))
while [ $(date +%s) -lt $end_time ]; do
    for i in $(seq 1 $rate); do
        curl -X POST http://localhost:8080/api/generate \
          -H "Content-Type: application/json" \
          -d '{"model":"llama2","prompt":"Test","stream":false}' \
          > /dev/null 2>&1 &
    done
    sleep 1
done

echo "Test complete. Check stats:"
curl http://localhost:8080/queue/stats?model=llama2 | jq
```

### Scenario 3: Burst Traffic

```bash
# Send bursts of requests with pauses
for burst in {1..10}; do
    echo "Burst $burst..."
    for i in {1..50}; do
        curl -X POST http://localhost:8080/api/generate \
          -H "Content-Type: application/json" \
          -d '{"model":"llama2","prompt":"Burst test","stream":false}' \
          > /dev/null 2>&1 &
    done
    sleep 10  # 10 second pause between bursts
done
```

## Expected Results

### Healthy System
- ✅ Active requests ≤ parallel limit
- ✅ Queued requests < queue limit
- ✅ Zero or very few rejections
- ✅ Consistent average wait times
- ✅ Stable memory usage

### Overloaded System
- ⚠️ Queue consistently near limit
- ⚠️ Increasing rejection rate
- ⚠️ Growing wait times
- ⚠️ High memory usage

### Action Required
- 🔴 Rejection rate > 5%: Increase queue or parallel limits
- 🔴 Avg wait time > 10s: Increase parallel limits
- 🔴 Memory > 90%: Reduce parallel limits

## Automated Test Suite

```python
#!/usr/bin/env python3
"""Automated test suite for concurrency features"""

import asyncio
import aiohttp
import sys

class ConcurrencyTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.session = None
    
    async def setup(self):
        self.session = aiohttp.ClientSession()
    
    async def teardown(self):
        if self.session:
            await self.session.close()
    
    async def test_health_check(self):
        """Test health endpoint includes concurrency info"""
        async with self.session.get(f"{self.base_url}/health") as resp:
            data = await resp.json()
            assert "concurrency" in data
            assert "default_parallel" in data["concurrency"]
            print("✓ Health check test passed")
    
    async def test_memory_endpoint(self):
        """Test memory info endpoint"""
        async with self.session.get(f"{self.base_url}/queue/memory") as resp:
            data = await resp.json()
            assert "total_gb" in data
            assert "recommended_parallel" in data
            print("✓ Memory endpoint test passed")
    
    async def test_single_request(self):
        """Test single request processing"""
        payload = {"model": "test", "prompt": "Hello", "stream": False}
        async with self.session.post(
            f"{self.base_url}/api/generate",
            json=payload
        ) as resp:
            # May fail if Ollama not running, but shouldn't crash
            print(f"✓ Single request test: status {resp.status}")
    
    async def test_concurrent_requests(self):
        """Test multiple concurrent requests"""
        tasks = []
        for i in range(10):
            payload = {"model": "test", "prompt": f"Test {i}", "stream": False}
            task = self.session.post(f"{self.base_url}/api/generate", json=payload)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in responses if not isinstance(r, Exception))
        print(f"✓ Concurrent requests test: {success}/10 completed")
    
    async def test_queue_stats(self):
        """Test queue statistics endpoint"""
        async with self.session.get(f"{self.base_url}/queue/stats") as resp:
            data = await resp.json()
            assert "default_parallel" in data
            assert "models" in data
            print("✓ Queue stats test passed")
    
    async def run_all(self):
        """Run all tests"""
        await self.setup()
        try:
            await self.test_health_check()
            await self.test_memory_endpoint()
            await self.test_single_request()
            await self.test_concurrent_requests()
            await self.test_queue_stats()
            print("\n✓ All tests passed!")
            return 0
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            return 1
        finally:
            await self.teardown()

if __name__ == "__main__":
    tester = ConcurrencyTester()
    exit_code = asyncio.run(tester.run_all())
    sys.exit(exit_code)
```

## Troubleshooting Tests

### Test Fails: Connection Refused
- **Cause**: Proxy not running
- **Fix**: Start proxy with `./run_proxy.sh start`

### Test Fails: 502 Bad Gateway
- **Cause**: Ollama not running or unreachable
- **Fix**: Check Ollama configuration and start Ollama

### High Rejection Rate in Tests
- **Cause**: Limits too low for test load
- **Fix**: Increase limits or reduce test concurrency

### Memory Warnings During Tests
- **Cause**: Parallel limit too high for available memory
- **Fix**: Reduce parallel limit or add more RAM

## Continuous Monitoring

```bash
# Add to crontab for continuous monitoring
*/5 * * * * curl -s http://localhost:8080/queue/stats | \
  jq -r '.models | to_entries[] | 
  select(.value.total_rejected > 100) | 
  "Alert: \(.key) has \(.value.total_rejected) rejected requests"' | \
  mail -s "Queue Alert" admin@example.com
```
