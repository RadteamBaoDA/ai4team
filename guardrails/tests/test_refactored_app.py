"""
Test script to verify the refactored application starts correctly.
"""

import sys
import asyncio
import importlib.util

def test_import_modules():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    modules = [
        'http_client',
        'utils',
        'streaming_handlers',
        'endpoints_ollama',
        'endpoints_openai',
        'endpoints_admin',
        'ollama_guard_proxy'
    ]
    
    for module_name in modules:
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                print(f"  ❌ {module_name}: Module not found")
                return False
            else:
                # Try to import it
                module = importlib.import_module(module_name)
                print(f"  ✅ {module_name}: OK")
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            return False
    
    return True


def test_app_creation():
    """Test that the FastAPI app is created correctly."""
    print("\nTesting FastAPI app creation...")
    
    try:
        from ollama_guard_proxy import app
        print(f"  ✅ App created: {app.title}")
        
        # Check routers
        routes = [route.path for route in app.routes]
        print(f"  ✅ Total routes: {len(routes)}")
        
        # Check for key endpoints
        expected_endpoints = [
            '/api/generate',
            '/api/chat',
            '/v1/chat/completions',
            '/health',
        ]
        
        for endpoint in expected_endpoints:
            if endpoint in routes:
                print(f"  ✅ Endpoint registered: {endpoint}")
            else:
                print(f"  ❌ Missing endpoint: {endpoint}")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_functions():
    """Test that factory functions work correctly."""
    print("\nTesting factory functions...")
    
    try:
        from config import Config
        from guard_manager import LLMGuardManager
        from concurrency import ConcurrencyManager
        from ip_whitelist import IPWhitelist
        
        # Create mock dependencies
        import os
        config = Config(os.environ.get('CONFIG_FILE'))
        guard_manager = LLMGuardManager(
            enable_input=True,
            enable_output=True,
            lazy_init=True
        )
        concurrency_manager = ConcurrencyManager(
            default_parallel=2,
            default_queue_limit=10
        )
        ip_whitelist = IPWhitelist([])
        
        # Test Ollama endpoints
        from endpoints_ollama import create_ollama_endpoints
        ollama_router = create_ollama_endpoints(
            config=config,
            guard_manager=guard_manager,
            concurrency_manager=concurrency_manager,
            guard_cache=None,
            HAS_CACHE=False
        )
        print(f"  ✅ Ollama router created: {len(ollama_router.routes)} routes")
        
        # Test OpenAI endpoints
        from endpoints_openai import create_openai_endpoints
        openai_router = create_openai_endpoints(
            config=config,
            guard_manager=guard_manager,
            concurrency_manager=concurrency_manager,
            guard_cache=None,
            HAS_CACHE=False
        )
        print(f"  ✅ OpenAI router created: {len(openai_router.routes)} routes")
        
        # Test Admin endpoints
        from endpoints_admin import create_admin_endpoints
        admin_router = create_admin_endpoints(
            config=config,
            guard_manager=guard_manager,
            ip_whitelist=ip_whitelist,
            concurrency_manager=concurrency_manager,
            guard_cache=None,
            HAS_CACHE=False
        )
        print(f"  ✅ Admin router created: {len(admin_router.routes)} routes")
        
        return True
    except Exception as e:
        print(f"  ❌ Factory function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Refactored Application Test Suite")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_import_modules),
        ("App Creation", test_app_creation),
        ("Factory Functions", test_factory_functions),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! The refactored application is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
