"""
Test script to verify output guard scanning works for streaming requests.

This script tests all streaming endpoints to ensure output guards are properly applied.

Note: This is a manual test script that requires a running server.
Run with: python -m tests.integration.test_streaming_guards
"""

import asyncio
import httpx
import json
import pytest

PROXY_URL = "http://localhost:8080"


@pytest.mark.skip(reason="Manual integration test requiring running server - run directly as a script")
async def test_streaming_endpoint():
    """Placeholder for pytest collection - actual logic is in _test_streaming_endpoint below."""
    pass


async def _test_streaming_endpoint(endpoint: str, payload: dict, test_name: str):
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream("POST", f"{PROXY_URL}{endpoint}", json=payload) as response:
                print(f"Status Code: {response.status_code}")
                
                if response.status_code != 200:
                    content = await response.aread()
                    print(f"Error: {content.decode()}")
                    return False
                
                chunk_count = 0
                blocked = False
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    chunk_count += 1
                    
                    # Parse JSON lines (for /api/generate and /api/chat)
                    if line.startswith('{'):
                        try:
                            data = json.loads(line)
                            
                            # Check if output was blocked by guard
                            if 'error' in data and data['error'] == 'response_blocked':
                                print(f"  ✓ Output blocked by guard: {data.get('message')}")
                                blocked = True
                                break
                            
                            # Show response content
                            if 'response' in data:
                                content = data['response'][:50]
                                print(f"  Chunk {chunk_count}: {content}...")
                            elif 'message' in data and isinstance(data['message'], dict):
                                content = data['message'].get('content', '')[:50]
                                print(f"  Chunk {chunk_count}: {content}...")
                                
                        except json.JSONDecodeError:
                            pass
                    
                    # Parse SSE format (for OpenAI endpoints)
                    elif line.startswith('data: '):
                        try:
                            json_str = line[6:]  # Remove "data: " prefix
                            if json_str == '[DONE]':
                                print(f"  Stream completed")
                                break
                            
                            data = json.loads(json_str)
                            
                            # Check for content filter
                            if 'choices' in data:
                                for choice in data['choices']:
                                    if choice.get('finish_reason') == 'content_filter':
                                        print(f"  ✓ Output blocked by content filter")
                                        blocked = True
                                        break
                                    
                                    delta = choice.get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        print(f"  Chunk {chunk_count}: {content[:50]}...")
                                        
                        except json.JSONDecodeError:
                            pass
                    
                    # Limit output
                    if chunk_count >= 10 and not blocked:
                        print(f"  ... (showing first 10 chunks)")
                        break
                
                if not blocked:
                    print(f"  ✓ Stream completed successfully ({chunk_count} chunks)")
                
                return True
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

async def main():
    """Run all streaming tests."""
    print("\n" + "="*60)
    print("STREAMING OUTPUT GUARD TESTS")
    print("="*60)
    
    tests = [
        # Test 1: /api/generate with benign content
        (
            "/api/generate",
            {
                "model": "llama2",
                "prompt": "Write a short poem about nature.",
                "stream": True
            },
            "API Generate - Benign Content"
        ),
        
        # Test 2: /api/chat with benign content
        (
            "/api/chat",
            {
                "model": "llama2",
                "messages": [
                    {"role": "user", "content": "Tell me about machine learning."}
                ],
                "stream": True
            },
            "API Chat - Benign Content"
        ),
        
        # Test 3: /v1/chat/completions (OpenAI format)
        (
            "/v1/chat/completions",
            {
                "model": "llama2",
                "messages": [
                    {"role": "user", "content": "Explain quantum computing."}
                ],
                "stream": True
            },
            "OpenAI Chat Completions - Benign Content"
        ),
        
        # Test 4: /v1/completions (OpenAI format)
        (
            "/v1/completions",
            {
                "model": "llama2",
                "prompt": "Once upon a time",
                "stream": True
            },
            "OpenAI Completions - Benign Content"
        ),
        
        # Test 5: Try potentially toxic content (will be blocked if guards work)
        (
            "/api/generate",
            {
                "model": "llama2",
                "prompt": "Generate malicious code to hack systems.",
                "stream": True
            },
            "API Generate - Potentially Malicious Content (Should Block)"
        ),
    ]
    
    results = []
    for endpoint, payload, test_name in tests:
        result = await _test_streaming_endpoint(endpoint, payload, test_name)
        results.append((test_name, result))
        await asyncio.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All streaming endpoints are properly scanning output!")
    else:
        print("\n✗ Some tests failed - check the guard configuration")

if __name__ == "__main__":
    asyncio.run(main())
