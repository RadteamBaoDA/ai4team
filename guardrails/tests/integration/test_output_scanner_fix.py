#!/usr/bin/env python3
"""
Test script to verify output scanner fix works correctly.

This verifies that output scanners are called with the correct signature:
scanner.scan(prompt, output) instead of scanner.scan(output)
"""

import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_output_scanners():
    """Test that output scanners work with the fixed signature."""
    print("\n" + "="*80)
    print("OUTPUT SCANNER FIX - TEST")
    print("="*80)
    
    try:
        from guard_manager import LLMGuardManager
        
        # Initialize manager
        print("\n1. Initializing LLM Guard Manager...")
        manager = LLMGuardManager(
            enable_input=False,  # Only test output
            enable_output=True,
            lazy_init=False
        )
        print("   ✓ Manager initialized")
        
        # Test 1: Scan output with prompt (recommended)
        print("\n2. Testing output scan WITH prompt context...")
        result = await manager.scan_output(
            text="This is a safe test output message.",
            prompt="Please write a test message",
            block_on_error=False
        )
        
        print(f"   Allowed: {result['allowed']}")
        print(f"   Scanners run: {result.get('scanner_count', 0)}")
        print(f"   Scanner results:")
        for scanner_name, scanner_result in result.get('scanners', {}).items():
            passed = scanner_result.get('passed', False)
            status = "✓" if passed else "✗"
            print(f"     {status} {scanner_name}: {scanner_result}")
        
        if result['allowed']:
            print("   ✓ Output scan with prompt PASSED")
        else:
            print("   ✗ Output scan with prompt FAILED (expected to pass)")
            return False
        
        # Test 2: Scan output without prompt (backwards compatibility)
        print("\n3. Testing output scan WITHOUT prompt (backwards compat)...")
        result = await manager.scan_output(
            text="This is another safe test output.",
            block_on_error=False
        )
        
        print(f"   Allowed: {result['allowed']}")
        print(f"   Scanners run: {result.get('scanner_count', 0)}")
        
        if result['allowed']:
            print("   ✓ Output scan without prompt PASSED")
        else:
            print("   ✗ Output scan without prompt FAILED (expected to pass)")
            return False
        
        # Test 3: Scan potentially toxic output
        print("\n4. Testing output scan with toxic content...")
        result = await manager.scan_output(
            text="I hate you and everyone like you. You are all terrible people.",
            prompt="Tell me what you think",
            block_on_error=False
        )
        
        print(f"   Allowed: {result['allowed']}")
        print(f"   Failed scanners:")
        for scanner_name, scanner_result in result.get('scanners', {}).items():
            if not scanner_result.get('passed', True):
                print(f"     ✗ {scanner_name}: risk_score={scanner_result.get('risk_score', 0)}")
        
        if not result['allowed']:
            print("   ✓ Toxic output correctly BLOCKED")
        else:
            print("   ⚠ Toxic output was NOT blocked (may need scanner tuning)")
        
        # Test 4: Check for errors
        print("\n5. Checking for scanner errors...")
        has_errors = False
        for scanner_name, scanner_result in result.get('scanners', {}).items():
            if 'error' in scanner_result:
                print(f"   ✗ {scanner_name} error: {scanner_result['error']}")
                has_errors = True
        
        if not has_errors:
            print("   ✓ No scanner errors detected")
        else:
            print("   ✗ Some scanners have errors")
            return False
        
        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED")
        print("="*80)
        print("\nOutput scanners are working correctly with the fixed signature.")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    success = asyncio.run(test_output_scanners())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
