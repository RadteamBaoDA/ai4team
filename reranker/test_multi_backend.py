#!/usr/bin/env python3
"""
Test script to validate multi-backend functionality.

Tests:
1. Backend detection and initialization
2. Inference correctness across backends
3. Performance comparison
4. Cache functionality
5. Error handling
"""

import os
import sys
import time
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reranker.config import RerankerConfig
from reranker.unified_reranker import UnifiedReRanker


def test_backend_detection():
    """Test that backend is correctly detected."""
    print("=" * 60)
    print("TEST 1: Backend Detection")
    print("=" * 60)
    
    config = RerankerConfig.from_env()
    reranker = UnifiedReRanker(config)
    
    print(f"✓ Backend: {reranker.backend}")
    print(f"✓ Device: {reranker.device}")
    print(f"✓ Model Source: {reranker.model_source}")
    
    # Validate backend is supported
    assert reranker.backend in ["pytorch", "mlx"], f"Unknown backend: {reranker.backend}"
    print("✓ Backend is valid")
    
    return reranker


def test_basic_inference(reranker: UnifiedReRanker):
    """Test basic reranking functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: Basic Inference")
    print("=" * 60)
    
    query = "What is machine learning?"
    documents = [
        "Machine learning is a subset of artificial intelligence.",
        "Python is a popular programming language.",
        "Deep learning uses neural networks for complex tasks.",
        "The weather today is sunny and warm.",
        "Supervised learning requires labeled data."
    ]
    
    print(f"Query: {query}")
    print(f"Documents: {len(documents)}")
    
    start = time.perf_counter()
    results = reranker.rerank(query, documents, top_k=3)
    elapsed = (time.perf_counter() - start) * 1000
    
    print(f"✓ Processing time: {elapsed:.2f}ms")
    print(f"✓ Results returned: {len(results)}")
    
    # Validate results
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert all("score" in r for r in results), "Missing scores"
    assert all("index" in r for r in results), "Missing indices"
    assert all("document" in r for r in results), "Missing documents"
    
    # Check ordering
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Results not sorted by score"
    
    print("\nTop 3 Results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. [{result['score']:.4f}] {result['document'][:60]}...")
    
    return results, elapsed


def test_cache_functionality(reranker: UnifiedReRanker):
    """Test that caching works correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Cache Functionality")
    print("=" * 60)
    
    query = "What is artificial intelligence?"
    documents = [
        "AI is intelligence demonstrated by machines.",
        "Dogs are loyal pets.",
        "Neural networks process information."
    ]
    
    # First request (cache miss)
    print("First request (cache miss)...")
    start = time.perf_counter()
    results1 = reranker.rerank(query, documents, top_k=2, use_cache=True)
    time1 = (time.perf_counter() - start) * 1000
    print(f"✓ Time: {time1:.2f}ms")
    
    # Second request (cache hit)
    print("Second request (cache hit)...")
    start = time.perf_counter()
    results2 = reranker.rerank(query, documents, top_k=2, use_cache=True)
    time2 = (time.perf_counter() - start) * 1000
    print(f"✓ Time: {time2:.2f}ms")
    
    # Validate results are identical
    assert len(results1) == len(results2), "Cache returned different number of results"
    for r1, r2 in zip(results1, results2):
        assert r1["index"] == r2["index"], "Cache returned different ordering"
        assert abs(r1["score"] - r2["score"]) < 0.0001, "Cache returned different scores"
    
    print(f"✓ Cache speedup: {time1 / time2:.2f}x")
    
    return time1, time2


def test_batch_processing(reranker: UnifiedReRanker):
    """Test batch processing with many documents."""
    print("\n" + "=" * 60)
    print("TEST 4: Batch Processing")
    print("=" * 60)
    
    query = "machine learning algorithms"
    documents = [
        f"Document {i} about {'ML' if i % 3 == 0 else 'random'} topic"
        for i in range(50)
    ]
    
    print(f"Query: {query}")
    print(f"Documents: {len(documents)}")
    print(f"Batch size: {reranker.config.batch_size}")
    
    start = time.perf_counter()
    results = reranker.rerank(query, documents, top_k=10)
    elapsed = (time.perf_counter() - start) * 1000
    
    print(f"✓ Processing time: {elapsed:.2f}ms")
    print(f"✓ Throughput: {len(documents) / (elapsed / 1000):.2f} docs/sec")
    print(f"✓ Results: {len(results)}")
    
    assert len(results) == 10, f"Expected 10 results, got {len(results)}"
    
    return elapsed


def test_error_handling(reranker: UnifiedReRanker):
    """Test error handling."""
    print("\n" + "=" * 60)
    print("TEST 5: Error Handling")
    print("=" * 60)
    
    # Empty documents
    print("Testing empty documents...")
    results = reranker.rerank("query", [], top_k=5)
    assert len(results) == 0, "Expected empty results for empty documents"
    print("✓ Empty documents handled")
    
    # Invalid top_k
    print("Testing invalid top_k...")
    results = reranker.rerank("query", ["doc1", "doc2"], top_k=10)
    assert len(results) == 2, "Expected to return all documents when top_k > len"
    print("✓ Invalid top_k handled")
    
    # Very long documents
    print("Testing long documents...")
    long_doc = "word " * 1000  # Very long document
    results = reranker.rerank("query", [long_doc], top_k=1)
    assert len(results) == 1, "Failed to process long document"
    print("✓ Long documents handled")


def performance_summary(times: Dict[str, float]):
    """Print performance summary."""
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for test_name, time_ms in times.items():
        print(f"{test_name:.<40} {time_ms:>8.2f}ms")
    
    total = sum(times.values())
    print(f"{'Total':.<40} {total:>8.2f}ms")


def main():
    """Run all tests."""
    print("\nReranker Multi-Backend Test Suite")
    print("Python:", sys.version.split()[0])
    
    try:
        # Test 1: Backend detection
        reranker = test_backend_detection()
        
        # Test 2: Basic inference
        _, time_basic = test_basic_inference(reranker)
        
        # Test 3: Cache functionality
        time_nocache, time_cached = test_cache_functionality(reranker)
        
        # Test 4: Batch processing
        time_batch = test_batch_processing(reranker)
        
        # Test 5: Error handling
        test_error_handling(reranker)
        
        # Performance summary
        performance_summary({
            "Basic inference (3 docs)": time_basic,
            "Cache miss": time_nocache,
            "Cache hit": time_cached,
            "Batch processing (50 docs)": time_batch,
        })
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
        return 0
        
    except Exception as exc:
        print(f"\n✗ TEST FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
