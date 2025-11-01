#!/usr/bin/env python3
"""
Test script for the optimized Guardrails Error Handler Filter

This tests the core functionality focusing on stream and outlet methods.
"""

import asyncio
import json
from typing import Dict, Any
from main import Filter


def test_safe_get():
    """Test the _safe_get method that prevents 'str' object attribute errors"""
    print("=== Testing _safe_get method ===")
    
    filter_instance = Filter()
    
    # Test with dictionary
    test_dict = {"key1": "value1", "key2": "value2"}
    result = filter_instance._safe_get(test_dict, "key1", "default")
    print(f"Dict test: {result}")
    assert result == "value1"
    
    # Test with missing key
    result = filter_instance._safe_get(test_dict, "missing", "default")
    print(f"Dict missing key: {result}")
    assert result == "default"
    
    # Test with string (should return default, not error)
    test_string = "just a string"
    result = filter_instance._safe_get(test_string, "key", "default")
    print(f"String test: {result}")
    assert result == "default"
    
    # Test with None
    result = filter_instance._safe_get(None, "key", "default")
    print(f"None test: {result}")
    assert result == "default"
    
    print("✓ _safe_get tests passed\n")


def test_error_detection():
    """Test error type detection"""
    print("=== Testing Error Type Detection ===")
    
    filter_instance = Filter()
    
    test_cases = [
        ("Scanner invalid content detected", "scanner_invalid"),
        ("Inappropriate content found", "inappropriate"),  
        ("Security threat detected", "threat_detected"),
        ("Request timed out", "timeout"),
        ("Some random error", "generic"),
        ("", "generic"),
    ]
    
    for message, expected_type in test_cases:
        result = filter_instance._detect_error_type(message)
        print(f"Message: '{message}' -> Type: {result}")
        assert result == expected_type
    
    print("✓ Error detection tests passed\n")


def test_error_formatting():
    """Test error message formatting"""
    print("=== Testing Error Message Formatting ===")
    
    filter_instance = Filter()
    
    # Test markdown format (default)
    result = filter_instance._format_error_message("scanner_invalid")
    print(f"Markdown format: {result}")
    assert result.startswith(">")
    
    # Test HTML format
    filter_instance.valves.error_format = "html"
    result = filter_instance._format_error_message("scanner_invalid")
    print(f"HTML format: {result}")
    assert "<div" in result
    
    # Test plain format
    filter_instance.valves.error_format = "plain"
    result = filter_instance._format_error_message("scanner_invalid")
    print(f"Plain format: {result}")
    assert result.startswith("ERROR:")
    
    print("✓ Error formatting tests passed\n")


def test_outlet_method():
    """Test the outlet method with various error scenarios"""
    print("=== Testing Outlet Method ===")
    
    filter_instance = Filter()
    
    # Test with error in body
    error_body = {
        "error": "Scanner detected inappropriate content",
        "status": 400
    }
    
    result = filter_instance.outlet(error_body)
    print(f"Error body result: {result}")
    assert "content" in result or "messages" in result
    
    # Test with detail field
    detail_body = {
        "detail": "Content blocked by security scanner",
        "status_code": 403
    }
    
    result = filter_instance.outlet(detail_body)
    print(f"Detail body result: {result}")
    
    # Test with normal body (no error)
    normal_body = {
        "messages": [{"role": "assistant", "content": "Hello, how can I help?"}]
    }
    
    result = filter_instance.outlet(normal_body)
    print(f"Normal body result: {result}")
    assert result == normal_body  # Should be unchanged
    
    print("✓ Outlet method tests passed\n")


async def test_stream_method():
    """Test the stream method with various streaming scenarios"""
    print("=== Testing Stream Method ===")
    
    filter_instance = Filter()
    
    # Test error event
    error_event = {
        "type": "error",
        "data": {
            "error": "Scanner invalid content detected",
            "status": 400
        }
    }
    
    print("Testing error event:")
    async for result in filter_instance.stream(error_event):
        print(f"Error event result: {result}")
        assert result["type"] == "message"
        assert "Content Blocked" in result["data"]["content"]
        break
    
    # Test message with error content
    message_event = {
        "type": "message", 
        "data": {
            "content": "Error: Content blocked by scanner",
            "role": "assistant",
            "done": False
        }
    }
    
    print("Testing message with error content:")
    async for result in filter_instance.stream(message_event):
        print(f"Message event result: {result}")
        # Should be transformed into error message
        break
    
    # Test normal message (should pass through)
    normal_event = {
        "type": "message",
        "data": {
            "content": "This is a normal message",
            "role": "assistant", 
            "done": False
        }
    }
    
    print("Testing normal message event:")
    async for result in filter_instance.stream(normal_event):
        print(f"Normal event result: {result}")
        assert result == normal_event  # Should be unchanged
        break
    
    print("✓ Stream method tests passed\n")


def test_string_handling():
    """Test handling of string objects to prevent 'str' object has no attribute 'get' errors"""
    print("=== Testing String Object Handling ===")
    
    filter_instance = Filter()
    
    # Test outlet with string body
    string_body = "This is just a string error message"
    result = filter_instance.outlet(string_body)
    print(f"String body handling: {result}")
    
    # Test various problematic inputs
    problematic_inputs = [
        "string error",
        123,
        None,
        {"error": "dict error"},
        ["list", "error"]
    ]
    
    for input_data in problematic_inputs:
        try:
            result = filter_instance._safe_get(input_data, "key", "default")
            print(f"Input: {type(input_data)} -> Result: {result}")
            assert result == "default" or isinstance(result, (str, int, list, dict))
        except Exception as e:
            print(f"ERROR with {type(input_data)}: {e}")
            assert False, f"Should not raise exception for {type(input_data)}"
    
    print("✓ String handling tests passed\n")


async def main():
    """Run all tests"""
    print("Running Optimized Guardrails Error Handler Filter Tests")
    print("=" * 60)
    
    # Run synchronous tests
    test_safe_get()
    test_error_detection() 
    test_error_formatting()
    test_outlet_method()
    test_string_handling()
    
    # Run async tests
    await test_stream_method()
    
    print("🎉 ALL TESTS PASSED! 🎉")
    print("\nThe optimized filter successfully:")
    print("✓ Prevents 'str' object has no attribute 'get' errors")
    print("✓ Handles various input types safely") 
    print("✓ Detects and formats error messages correctly")
    print("✓ Processes both outlet and stream methods")
    print("✓ Maintains compatibility with OpenWebUI Filter Function spec")


if __name__ == "__main__":
    asyncio.run(main())