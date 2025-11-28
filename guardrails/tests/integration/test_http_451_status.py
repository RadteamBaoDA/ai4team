#!/usr/bin/env python3
"""
Test script to verify HTTP status code 451 is returned for guardrail violations
"""

import json
import asyncio
from pathlib import Path
import sys

# Add src directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ollama_guardrails.api.endpoints_ollama import create_ollama_endpoints
from ollama_guardrails.core.config import Config


class MockGuardManager:
    """Mock guard manager that always returns blocked results for testing"""
    
    async def scan_input(self, text, block_on_error=False):
        return {
            'allowed': False,
            'scanners': {
                'test_scanner': {
                    'passed': False,
                    'reason': 'Content blocked for testing',
                    'score': 0.9
                }
            }
        }
    
    async def scan_output(self, text, prompt=None, block_on_error=False):
        return {
            'allowed': False,
            'scanners': {
                'test_output_scanner': {
                    'passed': False,
                    'reason': 'Output blocked for testing',
                    'score': 0.8
                }
            }
        }


class MockRequest:
    """Mock FastAPI request object"""
    
    def __init__(self, json_data):
        self._json_data = json_data
    
    async def json(self):
        return self._json_data


class MockConfig(dict):
    """Mock configuration object"""
    
    def __init__(self):
        super().__init__()
        self.update({
            'enable_input_guard': True,
            'enable_output_guard': True,
            'block_on_guard_error': False,
            'ollama_url': 'http://localhost:11434',
            'ollama_path': '/api/generate',
            'request_timeout': 300
        })
    
    def get(self, key, default=None):
        return super().get(key, default)
    
    def get_int(self, key, default=None):
        value = self.get(key, default)
        return int(value) if value is not None else default


async def test_http_451_status_codes():
    """Test that guardrail violations return HTTP 451 status code"""
    
    print("Testing HTTP 451 status codes for guardrail violations...")
    print("=" * 60)
    
    # Setup mock objects
    config = MockConfig()
    guard_manager = MockGuardManager()
    # Create router with endpoints
    router = create_ollama_endpoints(config, guard_manager)
    
    # Test data
    test_payload = {
        "model": "test-model",
        "prompt": "This is a test prompt that will be blocked",
        "stream": False
    }
    
    chat_payload = {
        "model": "test-model", 
        "messages": [
            {"role": "user", "content": "This is a test message that will be blocked"}
        ],
        "stream": False
    }
    
    # Test cases
    test_cases = [
        ("proxy_generate", MockRequest(test_payload)),
        ("proxy_chat", MockRequest(chat_payload))
    ]
    
    results = []
    
    for endpoint_name, mock_request in test_cases:
        print(f"\nTesting {endpoint_name} endpoint...")
        
        try:
            # Get the endpoint function
            for route in router.routes:
                if hasattr(route, 'endpoint') and route.endpoint.__name__ == endpoint_name:
                    endpoint_func = route.endpoint
                    break
            else:
                print(f"❌ Endpoint {endpoint_name} not found")
                continue
            
            # Call the endpoint (should raise HTTPException with status 451)
            try:
                await endpoint_func(mock_request)
                print(f"❌ Expected HTTPException but endpoint returned normally")
                results.append(f"{endpoint_name}: FAILED - No exception raised")
                
            except Exception as e:
                # Check if it's HTTPException with status 451
                if hasattr(e, 'status_code'):
                    if e.status_code == 451:
                        print(f"✅ {endpoint_name}: HTTP 451 returned correctly")
                        print(f"   Detail: {e.detail}")
                        print(f"   Headers: {getattr(e, 'headers', {})}")
                        results.append(f"{endpoint_name}: PASSED - HTTP 451")
                    else:
                        print(f"❌ {endpoint_name}: Wrong status code {e.status_code} (expected 451)")
                        results.append(f"{endpoint_name}: FAILED - HTTP {e.status_code}")
                else:
                    print(f"❌ {endpoint_name}: Non-HTTP exception: {type(e).__name__}: {e}")
                    results.append(f"{endpoint_name}: FAILED - {type(e).__name__}")
                    
        except Exception as e:
            print(f"❌ {endpoint_name}: Test setup error: {e}")
            results.append(f"{endpoint_name}: ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    passed = 0
    for result in results:
        print(result)
        if "PASSED" in result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED! HTTP 451 is correctly returned for guardrail violations.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_http_451_status_codes())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test framework error: {e}")
        sys.exit(1)