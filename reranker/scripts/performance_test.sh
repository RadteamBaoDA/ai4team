#!/usr/bin/env bash
# Performance testing script for the reranker service.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_URL="http://localhost:${RERANKER_PORT:-8000}"

usage() {
    cat <<EOF
Performance testing script for reranker service.

Usage: $0 <test-type> [options]

Test types:
  load              Basic load test with concurrent requests
  latency           Latency test with detailed timing
  throughput        Sustained throughput test
  stress            Stress test with increasing load
  metrics           Show current service metrics

Examples:
  $0 load --requests=50 --concurrency=5
  $0 latency --warmup=5 --requests=100
  $0 throughput --duration=30s --rate=10
  $0 stress --max-concurrency=16
  $0 metrics

Requirements:
  - Service must be running on $SERVICE_URL
  - curl and jq installed
  - Python 3.8+ for advanced tests
EOF
}

install_requirements() {
    if ! command -v jq >/dev/null 2>&1; then
        echo "Installing jq for JSON processing..."
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y jq
        elif command -v brew >/dev/null 2>&1; then
            brew install jq
        else
            echo "Please install jq manually"
            exit 1
        fi
    fi
}

check_service() {
    if ! curl -s -f "${SERVICE_URL}/health" >/dev/null; then
        echo "ERROR: Service not responding at ${SERVICE_URL}"
        echo "Start the service first with: ./start_reranker.sh fg"
        exit 1
    fi
}

basic_load_test() {
    local requests=${1:-20}
    local concurrency=${2:-4}
    
    echo "Load test: ${requests} requests with concurrency ${concurrency}"
    echo "=========================================="
    
    start_time=$(date +%s.%N)
    
    for i in $(seq 1 $concurrency); do
        (
            local thread_requests=$((requests / concurrency))
            local thread_time=0
            
            for j in $(seq 1 $thread_requests); do
                req_start=$(date +%s.%N)
                curl -s -X POST "${SERVICE_URL}/rerank" \
                    -H "Content-Type: application/json" \
                    -d "{
                        \"query\": \"Test query ${i}\",
                        \"documents\": [\"Document ${j} content here\", \"Another document ${j}\", \"Third document ${j}\"],
                        \"top_k\": 2
                    }" >/dev/null
                req_end=$(date +%s.%N)
                thread_time=$(echo "$thread_time + $req_end - $req_start" | bc -l)
            done
        ) &
    done
    
    wait
    
    end_time=$(date +%s.%N)
    total_time=$(echo "$end_time - $start_time" | bc -l)
    rps=$(echo "scale=2; $requests / $total_time" | bc -l)
    
    echo "Results:"
    echo "  Total time: ${total_time}s"
    echo "  Requests/sec: ${rps}"
    echo "  Avg time/req: $(echo "scale=3; $total_time / $requests" | bc -l)s"
    
    # Get detailed metrics
    echo ""
    echo "Service Metrics:"
    curl -s "${SERVICE_URL}/metrics" | jq '.metrics'
}

latency_test() {
    local warmup=${1:-5}
    local requests=${2:-100}
    
    echo "Latency test: ${requests} requests (warmup: ${warmup})"
    echo "================================================"
    
    # Warmup
    echo "Warming up with ${warmup} requests..."
    for i in $(seq 1 $warmup); do
        curl -s -X POST "${SERVICE_URL}/rerank" \
            -H "Content-Type: application/json" \
            -d '{"query":"Warmup","documents":["Test doc"]}' >/dev/null &
    done
    wait
    
    # Actual test
    local times=()
    echo "Running ${requests} latency measurements..."
    
    for i in $(seq 1 $requests); do
        req_start=$(date +%s.%N)
        response=$(curl -s -X POST "${SERVICE_URL}/rerank" \
            -H "Content-Type: application/json" \
            -d '{"query":"Latency test","documents":["Document A","Document B","Document C"]}')
        req_end=$(date +%s.%N)
        
        elapsed=$(echo "$req_end - $req_start" | bc -l)
        times+=($elapsed)
        
        if [ $((i % 20)) -eq 0 ]; then
            echo "  Completed ${i}/${requests} requests"
        fi
    done
    
    # Calculate statistics
    local sum=0
    local min=${times[0]}
    local max=${times[0]}
    
    for time in "${times[@]}"; do
        sum=$(echo "$sum + $time" | bc -l)
        if (( $(echo "$time < $min" | bc -l) )); then
            min=$time
        fi
        if (( $(echo "$time > $max" | bc -l) )); then
            max=$time
        fi
    done
    
    local avg=$(echo "scale=4; $sum / $requests" | bc -l)
    local p50=$(echo "scale=4; $(echo "${times[@]}" | tr ' ' '\n' | sort -n | awk -v count=$requests 'NR==int(count*0.5) {print $1}')" | bc -l)
    local p95=$(echo "scale=4; $(echo "${times[@]}" | tr ' ' '\n' | sort -n | awk -v count=$requests 'NR==int(count*0.95) {print $1}')" | bc -l)
    local p99=$(echo "scale=4; $(echo "${times[@]}" | tr ' ' '\n' | sort -n | awk -v count=$requests 'NR==int(count*0.99) {print $1}')" | bc -l)
    
    echo "Results:"
    echo "  Min:    ${min}s"
    echo "  P50:    ${p50}s"
    echo "  P95:    ${p95}s"
    echo "  P99:    ${p99}s"
    echo "  Max:    ${max}s"
    echo "  Mean:   ${avg}s"
}

throughput_test() {
    local duration=${1:-30s}
    local rate=${2:-5}
    
    echo "Throughput test: ${rate} req/s for ${duration}"
    echo "============================================="
    
    local interval=$(echo "scale=3; 1 / $rate" | bc -l)
    local end_time=$(($(date +%s) + $(echo $duration | sed 's/s$//')))
    
    local count=0
    local errors=0
    
    echo "Running for ${duration} at ${rate} requests/second..."
    
    while [ $(date +%s) -lt $end_time ]; do
        (
            curl -s -X POST "${SERVICE_URL}/rerank" \
                -H "Content-Type: application/json" \
                -d '{"query":"Throughput test","documents":["Doc A","Doc B"]}' >/dev/null
        ) &
        
        count=$((count + 1))
        sleep $interval
    done
    
    wait
    
    local duration_sec=$(echo $duration | sed 's/s$//')
    local actual_rps=$(echo "scale=2; $count / $duration_sec" | bc -l)
    
    echo "Results:"
    echo "  Target rate:   ${rate} req/s"
    echo "  Actual rate:   ${actual_rps} req/s"
    echo "  Total requests: $count"
}

stress_test() {
    local max_concurrency=${1:-16}
    
    echo "Stress test: escalating concurrency from 1 to ${max_concurrency}"
    echo "==========================================================="
    
    for conc in $(seq 1 $max_concurrency); do
        echo ""
        echo "Testing concurrency level: $conc"
        
        local start_time=$(date +%s.%N)
        local count=0
        local errors=0
        
        for i in $(seq 1 $conc); do
            (
                local local_errors=0
                for j in $(seq 1 10); do
                    if ! curl -s -X POST "${SERVICE_URL}/rerank" \
                        -H "Content-Type: application/json" \
                        -d '{"query":"Stress test","documents":["Doc '$j'"]}' >/dev/null; then
                        local_errors=$((local_errors + 1))
                    fi
                    sleep 0.1
                done
                echo $local_errors
            ) &
        done
        
        wait
        
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)
        
        # Check service health
        if curl -s -f "${SERVICE_URL}/health" >/dev/null; then
            echo "  ✓ Concurrency $conc: ${duration}s"
        else
            echo "  ✗ Concurrency $conc: Service failed"
            break
        fi
    done
}

show_metrics() {
    echo "Current Service Metrics:"
    echo "========================"
    curl -s "${SERVICE_URL}/metrics" | jq '.' || curl -s "${SERVICE_URL}/metrics"
    echo ""
    echo "Health Status:"
    curl -s "${SERVICE_URL}/health" | jq '.' || curl -s "${SERVICE_URL}/health"
}

main() {
    install_requirements
    check_service
    
    case "${1:-help}" in
        load)
            basic_load_test "${2:-20}" "${3:-4}"
            ;;
        latency)
            latency_test "${2:-5}" "${3:-100}"
            ;;
        throughput)
            throughput_test "${2:-30s}" "${3:-5}"
            ;;
        stress)
            stress_test "${2:-16}"
            ;;
        metrics)
            show_metrics
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo "Unknown test type '$1'"
            usage
            exit 1
            ;;
    esac
}

main "$@"
