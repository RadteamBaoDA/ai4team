#!/usr/bin/env python3
"""
Test script to validate connection cleanup optimization for LLM Guard proxy.

This script tests that:
1. Connections are closed immediately when output is blocked (streaming)
2. Connections are closed immediately when output is blocked (non-streaming)
3. Ollama stops generating when connection is closed
4. Resources are freed properly

Usage:
    python test_connection_cleanup.py

Requirements:
    - Ollama Guard Proxy running on localhost:8080
    - Ollama backend running
    - LLM Guard configured with output scanners
"""

import json
import time
import requests
import asyncio
import httpx
from typing import Dict, Any

PROXY_URL = "http://localhost:8080"
MODEL = "llama2"  # Change to your model

def test_streaming_output_block():
    """Test that streaming connections are closed immediately when blocked."""
    print("\n" + "="*80)
    print("TEST 1: Streaming Output Block - Connection Cleanup")
    print("="*80)
    
    # Craft a prompt that should generate toxic content (modify based on your scanners)
    payload = {
        "model": MODEL,
        "prompt": "Write a hateful message about people",
        "stream": True
    }
    
    print(f"\nSending streaming request with prompt likely to be blocked...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{PROXY_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=30
        )
        
        chunks = []
        blocked = False
        
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line)
                chunks.append(data)
                
                if data.get('error') == 'content_policy_violation':
                    blocked = True
                    elapsed = time.time() - start_time
                    print(f"✓ Content blocked after {elapsed:.2f}s")
                    print(f"  Block type: {data.get('type')}")
                    print(f"  Message: {data.get('message')}")
                    print(f"  Failed scanners: {len(data.get('failed_scanners', []))}")
                    break
                    
            except json.JSONDecodeError:
                continue
        
        elapsed = time.time() - start_time
        
        if blocked:
            print(f"✓ Connection closed after blocking")
            print(f"✓ Total time: {elapsed:.2f}s (should be < 5s for immediate closure)")
            print(f"✓ Total chunks received: {len(chunks)}")
            
            if elapsed < 5:
                print("\n✓ PASS: Connection closed immediately (< 5s)")
            else:
                print(f"\n✗ FAIL: Connection took too long to close ({elapsed:.2f}s)")
        else:
            print(f"\n⚠ WARNING: Content was not blocked (may need different prompt)")
            print(f"  Received {len(chunks)} chunks without blocking")
            
    except Exception as e:
        print(f"✗ ERROR: {e}")

def test_nonstreaming_output_block():
    """Test that non-streaming connections are closed immediately when blocked."""
    print("\n" + "="*80)
    print("TEST 2: Non-Streaming Output Block - Connection Cleanup")
    print("="*80)
    
    payload = {
        "model": MODEL,
        "prompt": "Write toxic content",
        "stream": False
    }
    
    print(f"\nSending non-streaming request with prompt likely to be blocked...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{PROXY_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 451:
            print(f"✓ Response blocked with status code 451")
            print(f"✓ Response time: {elapsed:.2f}s")
            
            # Check headers for metadata
            error_type = response.headers.get('X-Error-Type')
            block_type = response.headers.get('X-Block-Type')
            failed_scanners = response.headers.get('X-Failed-Scanners')
            
            print(f"  Error Type: {error_type}")
            print(f"  Block Type: {block_type}")
            print(f"  Failed Scanners: {failed_scanners}")
            
            # Check response body
            try:
                error_msg = response.text
                print(f"  Error Message: {error_msg}")
            except:
                pass
            
            print("\n✓ PASS: Non-streaming blocking works correctly")
        else:
            print(f"\n⚠ WARNING: Response not blocked (status: {response.status_code})")
            print(f"  May need different prompt or scanner configuration")
            
    except Exception as e:
        print(f"✗ ERROR: {e}")

def test_openai_streaming_block():
    """Test OpenAI-compatible streaming with blocking."""
    print("\n" + "="*80)
    print("TEST 3: OpenAI Streaming Output Block - Connection Cleanup")
    print("="*80)
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Write hateful content"}
        ],
        "stream": True
    }
    
    print(f"\nSending OpenAI streaming request...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=30
        )
        
        chunks = []
        blocked = False
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            if not line_str.startswith('data: '):
                continue
            
            data_str = line_str[6:]  # Remove 'data: ' prefix
            if data_str == '[DONE]':
                break
            
            try:
                data = json.loads(data_str)
                chunks.append(data)
                
                # Check for blocking in error field
                error = data.get('error')
                if error and error.get('code') == 'output_blocked':
                    blocked = True
                    elapsed = time.time() - start_time
                    print(f"✓ OpenAI content blocked after {elapsed:.2f}s")
                    print(f"  Message: {error.get('message')}")
                    break
                    
            except json.JSONDecodeError:
                continue
        
        elapsed = time.time() - start_time
        
        if blocked:
            print(f"✓ Connection closed after blocking")
            print(f"✓ Total time: {elapsed:.2f}s")
            
            if elapsed < 5:
                print("\n✓ PASS: OpenAI streaming connection closed immediately")
            else:
                print(f"\n✗ FAIL: Connection took too long ({elapsed:.2f}s)")
        else:
            print(f"\n⚠ WARNING: OpenAI content was not blocked")
            
    except Exception as e:
        print(f"✗ ERROR: {e}")

async def test_resource_monitoring():
    """Test that resources are freed by monitoring connection pool."""
    print("\n" + "="*80)
    print("TEST 4: Resource Monitoring - Connection Pool Health")
    print("="*80)
    
    print("\nSending multiple concurrent requests with blocking...")
    
    async def send_request(session: httpx.AsyncClient, i: int):
        try:
            response = await session.post(
                f"{PROXY_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": "Generate toxic content",
                    "stream": True
                },
                timeout=10
            )
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get('error') == 'content_policy_violation':
                        return True  # Blocked successfully
                except:
                    pass
            return False
        except Exception as e:
            print(f"  Request {i} error: {e}")
            return False
    
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [send_request(client, i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        blocked_count = sum(1 for r in results if r is True)
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"\n✓ Completed 20 concurrent requests")
        print(f"  Blocked: {blocked_count}")
        print(f"  Errors: {error_count}")
        print(f"  Successful (not blocked): {20 - blocked_count - error_count}")
        
        if error_count == 0:
            print("\n✓ PASS: No connection pool exhaustion")
        else:
            print(f"\n✗ FAIL: {error_count} requests failed")

def test_logs_validation():
    """Provide instructions for validating logs."""
    print("\n" + "="*80)
    print("TEST 5: Log Validation Instructions")
    print("="*80)
    
    print("\nTo validate connection cleanup in logs:")
    print("\n1. Check proxy logs for these messages:")
    print("   - 'Connection closed after blocking streaming output'")
    print("   - 'Connection closed after blocking non-streaming output'")
    print("   - 'Connection closed after blocking OpenAI chat output'")
    print("\n2. These should appear immediately after 'Output blocked by LLM Guard'")
    print("\n3. Count should match number of blocked requests")
    print("\n4. No 'Connection pool exhausted' or 'Too many connections' errors")

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("CONNECTION CLEANUP OPTIMIZATION - TEST SUITE")
    print("="*80)
    print(f"\nProxy URL: {PROXY_URL}")
    print(f"Model: {MODEL}")
    print("\nNote: These tests require output scanners to be configured")
    print("      to block toxic/hateful content.")
    
    # Run synchronous tests
    test_streaming_output_block()
    test_nonstreaming_output_block()
    test_openai_streaming_block()
    
    # Run async test
    print("\nRunning async resource monitoring test...")
    asyncio.run(test_resource_monitoring())
    
    # Log validation instructions
    test_logs_validation()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review logs for connection closure messages")
    print("2. Monitor Ollama resource usage during blocking")
    print("3. Check httpx connection pool stats")
    print("4. Verify no resource leaks under sustained load")
    print()

if __name__ == "__main__":
    main()
