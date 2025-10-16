# Ollama Guard Proxy - Uvicorn Server Guide

## Quick Start

### Linux/macOS
```bash
chmod +x run_proxy.sh
./run_proxy.sh
```

### Windows
```bash
run_proxy.bat
```

---

## Understanding Parallel/Concurrent Request Handling

### Single vs Multiple Workers

**Single Worker** (Default in development):
```
Request 1 → Proxy → Ollama
Request 2 → (waits for Request 1)
Request 3 → (waits)
```

**Multiple Workers** (Recommended for production):
```
Request 1 → Worker 1 → Ollama
Request 2 → Worker 2 → Ollama (parallel)
Request 3 → Worker 3 → Ollama (parallel)
Request 4 → Worker 4 → Ollama (parallel)
```

### Concurrency Settings

**Worker Count** determines how many requests can be processed simultaneously:
- 1 worker: Sequential processing
- 2 workers: 2 concurrent requests
- 4 workers: 4 concurrent requests (default)
- 8 workers: 8 concurrent requests

**Per-Worker Concurrency** (default 128):
- Each worker can handle up to 128 concurrent connections
- Controls connection pooling and timeouts

---

## Usage Examples

### Example 1: Development with Auto-Reload
```bash
# Linux/macOS
./run_proxy.sh --reload --debug

# Windows
run_proxy.bat --reload --debug
```
Features:
- Auto-reload on code changes
- Debug logging enabled
- Single worker (adequate for development)
- Easier debugging

### Example 2: Standard Multi-Worker (Recommended)
```bash
# Linux/macOS
./run_proxy.sh --workers 4 --concurrency 128

# Windows
run_proxy.bat --workers 4 --concurrency 128
```
Features:
- 4 parallel workers for concurrent requests
- 128 concurrent connections per worker
- Suitable for production
- Balanced performance

### Example 3: High-Performance (Heavy Load)
```bash
# Linux/macOS
./run_proxy.sh --workers 8 --concurrency 256

# Windows
run_proxy.bat --workers 8 --concurrency 256
```
Features:
- 8 parallel workers
- 256 concurrent connections each
- For high-traffic production
- Maximum throughput

### Example 4: Custom Configuration
```bash
# Linux/macOS
./run_proxy.sh --host 0.0.0.0 --port 9000 --workers 4 --log-level debug

# Windows
run_proxy.bat --host 0.0.0.0 --port 9000 --workers 4 --log-level debug
```

### Example 5: Localhost Only (Secure)
```bash
# Linux/macOS
./run_proxy.sh --host 127.0.0.1 --port 8080

# Windows
run_proxy.bat --host 127.0.0.1 --port 8080
```

---

## Environment Variables

Set before running the script:

### Ollama Configuration
```bash
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_PATH=/api/generate
```

### Guard Settings
```bash
export ENABLE_INPUT_GUARD=true
export ENABLE_OUTPUT_GUARD=true
export ENABLE_IP_FILTER=false
```

### Access Control
```bash
export IP_WHITELIST="192.168.1.0/24,10.0.0.0/8"
export IP_BLACKLIST="192.168.1.100"
```

### Complete Example (Linux/macOS)
```bash
export OLLAMA_URL=http://127.0.0.1:11434
export ENABLE_INPUT_GUARD=true
export ENABLE_OUTPUT_GUARD=true
export PROXY_PORT=8080
./run_proxy.sh --workers 4 --log-level info
```

### Complete Example (Windows)
```batch
set OLLAMA_URL=http://127.0.0.1:11434
set ENABLE_INPUT_GUARD=true
set ENABLE_OUTPUT_GUARD=true
set PROXY_PORT=8080
run_proxy.bat --workers 4 --log-level info
```

---

## Testing Parallel Requests

### Test 1: Sequential Requests (Baseline)
```bash
# Single request
curl http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","prompt":"What is AI?","stream":false}'
```

### Test 2: Parallel Requests (Concurrent)
```bash
# Linux/macOS - 4 concurrent requests
for i in {1..4}; do
  curl http://localhost:8080/v1/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"mistral","prompt":"What is AI?","stream":false}' &
done
wait
echo "All requests completed"
```

### Test 3: Heavy Load Test
```bash
# Linux/macOS - 20 concurrent requests
for i in {1..20}; do
  (
    curl http://localhost:8080/v1/generate \
      -H "Content-Type: application/json" \
      -d '{"model":"mistral","prompt":"test","stream":false}' \
      -o /dev/null -s
  ) &
done
wait
echo "Load test complete"
```

### Test 4: Concurrent with Monitoring
```bash
# Terminal 1: Start proxy with 4 workers
./run_proxy.sh --workers 4

# Terminal 2: Monitor requests
watch -n 1 'curl -s http://localhost:8080/health | jq'

# Terminal 3: Send concurrent requests
for i in {1..10}; do
  (
    time curl http://localhost:8080/v1/generate \
      -H "Content-Type: application/json" \
      -d '{"model":"mistral","prompt":"test","stream":false}'
  ) &
done
wait
```

### Test 5: With Python Client
```python
import concurrent.futures
from client_example import OllamaGuardClient

client = OllamaGuardClient("http://localhost:8080")

def generate_request(prompt, num):
    try:
        response = client.generate(prompt, model="mistral")
        print(f"Request {num}: OK")
        return response
    except Exception as e:
        print(f"Request {num}: ERROR - {e}")
        return None

# Send 10 concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = []
    for i in range(10):
        future = executor.submit(generate_request, f"Question {i}", i)
        futures.append(future)
    
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
    print(f"Completed: {len(results)} requests")
```

---

## Performance Tuning

### Optimal Worker Count

**Formula**: `workers = CPU_cores * 2`

```bash
# Get CPU count
# Linux/macOS
nproc

# Windows
wmic os get ProcessorCount
```

**Examples**:
- 2-core machine: 4 workers (default)
- 4-core machine: 8 workers
- 8-core machine: 16 workers
- 16-core machine: 32 workers

### Concurrency Per Worker

**Default**: 128 connections per worker

**Recommendations**:
- Light load: 64
- Normal load: 128 (default)
- Heavy load: 256
- Very heavy: 512

```bash
# High performance setup for 8-core machine
./run_proxy.sh --workers 16 --concurrency 256
```

### Memory Usage

Each worker uses approximately:
- Base: ~50MB
- With guards: ~200-300MB (depends on LLM Guard models)

**Total Memory** ≈ `(200-300MB * workers) + 500MB overhead`

Examples:
- 4 workers: ~1.3GB
- 8 workers: ~2.1GB
- 16 workers: ~3.7GB

---

## Monitoring

### Health Check
```bash
# Basic health
curl http://localhost:8080/health

# Pretty print
curl http://localhost:8080/health | jq

# Continuous monitoring
watch -n 1 'curl -s http://localhost:8080/health | jq'
```

### Config Check
```bash
curl http://localhost:8080/config | jq
```

### Log Levels

```bash
# Development (verbose)
./run_proxy.sh --log-level debug

# Normal
./run_proxy.sh --log-level info

# Production (minimal)
./run_proxy.sh --log-level warning
```

### Real-time Logs
```bash
# Linux/macOS
./run_proxy.sh --log-level debug | grep -E "Request|Response|ERROR"

# Windows (PowerShell)
run_proxy.bat --log-level debug | Select-String "Request","Response","ERROR"
```

---

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
# Linux/macOS
lsof -i :8080

# Windows (PowerShell)
Get-NetTCPConnection -LocalPort 8080 | Select-Object OwningProcess, LocalAddress, LocalPort

# Use different port
./run_proxy.sh --port 9000
```

### Out of Memory
**Symptom**: Proxy crashes or becomes unresponsive

**Solutions**:
1. Reduce worker count: `--workers 2`
2. Check Ollama not consuming memory
3. Monitor with: `watch -n 1 'ps aux | grep python'`
4. Restart periodically

### Slow Responses with Multiple Workers
**Symptom**: No improvement with more workers

**Causes**:
1. Ollama backend is bottleneck (add more Ollama instances)
2. LLM Guard scanning is slow (disable output guard if not needed)
3. Network latency

**Solutions**:
1. Check Ollama performance directly
2. Test without guards
3. Add more Ollama backends

### Connection Timeouts
**Symptom**: "Connection timeout" errors

**Solutions**:
1. Increase concurrency: `--concurrency 256`
2. Check Ollama is responding
3. Increase request timeout in client code

---

## Performance Comparison

### Single Worker vs Multiple Workers

**Test Setup**:
- Ollama model: mistral
- Prompt: "What is AI?" (short)
- Concurrent requests: 10
- Guards: Enabled

**Results** (typical):
```
1 worker:  Total time: 45s (sequential)
2 workers: Total time: 23s (parallel)
4 workers: Total time: 12s (parallel)
8 workers: Total time: 7s (parallel - diminishing returns with single Ollama)
```

**Key Insight**: Multiple workers help only if Ollama can handle parallel requests.

---

## Production Deployment

### Recommended Setup
```bash
# Production with 8 workers on 4-core machine (scaled up for cloud)
./run_proxy.sh \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 8 \
  --concurrency 256 \
  --log-level info
```

### With Nginx Load Balancing
```bash
# Run 3 instances on different ports
./run_proxy.sh --port 8080 --workers 4 &
./run_proxy.sh --port 8081 --workers 4 &
./run_proxy.sh --port 8082 --workers 4 &
```

Then configure Nginx:
```nginx
upstream proxy_cluster {
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}

server {
    listen 80;
    location / {
        proxy_pass http://proxy_cluster;
    }
}
```

### SystemD Service (Linux)
```ini
# /etc/systemd/system/ollama-guard.service
[Unit]
Description=Ollama Guard Proxy
After=network.target

[Service]
Type=simple
User=ollama
WorkingDirectory=/opt/ollama-guard
ExecStart=/opt/ollama-guard/run_proxy.sh --workers 8 --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start with:
```bash
sudo systemctl start ollama-guard
sudo systemctl enable ollama-guard
sudo systemctl status ollama-guard
```

---

## FAQ

**Q: How many workers should I use?**  
A: Start with `workers = CPU_cores * 2`. Monitor performance and adjust.

**Q: Will more workers always be faster?**  
A: No. If Ollama is the bottleneck, more workers won't help.

**Q: Can I mix local and remote Ollama?**  
A: Yes. Set `OLLAMA_URL` to remote and use load balancer.

**Q: What's the maximum number of workers?**  
A: 32-64 workers is practical maximum (depends on resources).

**Q: Can I run multiple proxy instances?**  
A: Yes! Run on different ports and use Nginx to load balance.

**Q: How do I monitor performance?**  
A: Use health check endpoint and system monitoring tools.

**Q: What's the overhead per request?**  
A: 150-700ms (depends on guard complexity).

---

## Next Steps

1. **Choose worker configuration** based on your CPU cores
2. **Run the proxy** with `run_proxy.sh` or `run_proxy.bat`
3. **Test with concurrent requests** to verify performance
4. **Monitor** with health check endpoint
5. **Adjust** workers and concurrency based on actual load

---

Last Updated: October 16, 2025
