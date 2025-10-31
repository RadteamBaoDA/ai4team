#!/usr/bin/env python3
"""
Test script for HTTP 451 specific error handling in the Guardrails Error Handler Filter

This tests that the filter ONLY processes HTTP 451 errors and ignores other errors.
"""

import asyncio
import json
from main import Filter


def test_http_451_detection():
    """Test the _is_http_451_error method"""
    print("=== Testing HTTP 451 Error Detection ===")
    
    filter_instance = Filter()
    
    test_cases = [
        # Should return True (HTTP 451 errors)
        ({"status_code": 451, "detail": "Content blocked"}, True, "Direct status_code 451"),
        ({"status": 451, "error": "Content policy violation"}, True, "Status field 451"),
        ({"X-Error-Type": "content_policy_violation", "detail": "Blocked"}, True, "Content policy header"),
        ("HTTP 451 Unavailable for Legal Reasons - content blocked", True, "String with 451 and keywords"),
        ({"error": "451: Content blocked by guardrails"}, True, "Error field with 451"),
        
        # Should return False (other errors)
        ({"status_code": 400, "detail": "Bad request"}, False, "HTTP 400 error"),
        ({"status_code": 500, "error": "Internal server error"}, False, "HTTP 500 error"),
        ({"error": "Connection timeout"}, False, "Generic error without 451"),
        ("This is a normal message", False, "Normal text"),
        (None, False, "None input"),
        ({"status_code": 403, "detail": "Forbidden"}, False, "HTTP 403 error"),
    ]
    
    passed = 0
    for test_input, expected, description in test_cases:
        result = filter_instance._is_http_451_error(test_input)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: {description} -> {result}")
        if result == expected:
            passed += 1
    
    print(f"\nHTTP 451 Detection: {passed}/{len(test_cases)} tests passed\n")
    return passed == len(test_cases)


def test_outlet_451_only():
    """Test that outlet only processes HTTP 451 errors"""
    print("=== Testing Outlet Method - HTTP 451 Only ===")
    
    filter_instance = Filter()
    
    test_cases = [
        # Should be processed (HTTP 451)
        {
            "input": {"status_code": 451, "detail": "Content blocked by scanner"},
            "should_modify": True,
            "description": "HTTP 451 error"
        },
        # Should NOT be processed (other errors)
        {
            "input": {"status_code": 400, "error": "Bad request"},
            "should_modify": False,
            "description": "HTTP 400 error"
        },
        {
            "input": {"error": "Connection failed"},
            "should_modify": False,
            "description": "Generic connection error"
        },
        {
            "input": {"messages": [{"role": "assistant", "content": "Hello"}]},
            "should_modify": False,
            "description": "Normal response"
        },
    ]
    
    passed = 0
    for i, case in enumerate(test_cases):
        original_input = json.loads(json.dumps(case["input"]))  # Deep copy
        result = filter_instance.outlet(case["input"])
        
        was_modified = result != original_input
        expected_modification = case["should_modify"]
        
        status = "✅ PASS" if was_modified == expected_modification else "❌ FAIL"
        print(f"{status}: {case['description']}")
        print(f"   Modified: {was_modified}, Expected: {expected_modification}")
        
        if was_modified == expected_modification:
            passed += 1
    
    print(f"\nOutlet HTTP 451 Only: {passed}/{len(test_cases)} tests passed\n")
    return passed == len(test_cases)


async def test_stream_451_only():
    """Test that stream only processes HTTP 451 errors"""
    print("=== Testing Stream Method - HTTP 451 Only ===")
    
    filter_instance = Filter()
    
    test_cases = [
        # Should be processed (HTTP 451)
        {
            "input": {"type": "error", "data": {"status_code": 451, "error": "Content blocked"}},
            "should_modify": True,
            "description": "HTTP 451 error event"
        },
        {
            "input": {"type": "message", "data": {"content": "HTTP 451 Unavailable - content blocked by policy"}},
            "should_modify": True,
            "description": "Message with HTTP 451 content"
        },
        # Should NOT be processed (other errors)
        {
            "input": {"type": "error", "data": {"status_code": 500, "error": "Server error"}},
            "should_modify": False,
            "description": "HTTP 500 error event"
        },
        {
            "input": {"type": "message", "data": {"content": "This is a normal message"}},
            "should_modify": False,
            "description": "Normal message"
        },
        {
            "input": {"type": "message", "data": {"content": "Error: Connection timeout"}},
            "should_modify": False,
            "description": "Generic error message"
        },
    ]
    
    passed = 0
    for case in test_cases:
        results = []
        async for event in filter_instance.stream(case["input"]):
            results.append(event)
        
        # Check if the output is different from input
        was_modified = len(results) != 1 or results[0] != case["input"]
        expected_modification = case["should_modify"]
        
        status = "✅ PASS" if was_modified == expected_modification else "❌ FAIL"
        print(f"{status}: {case['description']}")
        print(f"   Modified: {was_modified}, Expected: {expected_modification}")
        
        if was_modified == expected_modification:
            passed += 1
    
    print(f"\nStream HTTP 451 Only: {passed}/{len(test_cases)} tests passed\n")
    return passed == len(test_cases)


def test_error_message_formatting():
    """Test that formatted messages are user-friendly"""
    print("=== Testing Error Message Formatting ===")
    
    filter_instance = Filter()
    
    # Test HTTP 451 error processing
    test_body = {
        "status_code": 451,
        "detail": "Content blocked by scanner - inappropriate content detected"
    }
    
    result = filter_instance.outlet(test_body)
    
    # Check if a user-friendly message was created
    has_formatted_message = False
    if 'messages' in result and result['messages']:
        content = result['messages'][0].get('content', '')
        has_formatted_message = any(emoji in content for emoji in ['🛡️', '⚠️', '🚨']) and '**' in content
    
    status = "✅ PASS" if has_formatted_message else "❌ FAIL"
    print(f"{status}: HTTP 451 error formatted to user-friendly message")
    if has_formatted_message:
        print(f"   Formatted message: {result['messages'][0]['content']}")
    
    print(f"\nError Message Formatting: {'1/1' if has_formatted_message else '0/1'} tests passed\n")
    return has_formatted_message


async def main():
    """Run all HTTP 451 specific tests"""
    print("Testing HTTP 451 Specific Guardrails Error Handler Filter")
    print("=" * 60)
    
    # Run all tests
    test1 = test_http_451_detection()
    test2 = test_outlet_451_only()
    test3 = await test_stream_451_only()
    test4 = test_error_message_formatting()
    
    # Summary
    total_passed = sum([test1, test2, test3, test4])
    total_tests = 4
    
    print("=" * 60)
    print("FINAL RESULTS:")
    print(f"Tests Passed: {total_passed}/{total_tests}")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe filter successfully:")
        print("✅ Only processes HTTP 451 content policy violations")
        print("✅ Ignores other HTTP status codes and generic errors")
        print("✅ Formats user-friendly messages for blocked content")
        print("✅ Works correctly in both stream and outlet modes")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)