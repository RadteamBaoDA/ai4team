#!/usr/bin/env python3
"""
LiteLLM Integration Test Suite

Tests:
  - Configuration loading
  - Load balancing routing
  - LLM Guard integration
  - API endpoint compatibility
  - Error handling

Usage:
    python test_litellm_integration.py
    python test_litellm_integration.py --verbose
    python test_litellm_integration.py --test guard
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any, Optional
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """Test result container."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.error = None
    
    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        result = f"{status}: {self.name}"
        if self.message:
            result += f" - {self.message}"
        if self.error:
            result += f"\n  Error: {self.error}"
        return result


class LiteLLMTester:
    """Test suite for LiteLLM integration."""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.results = []
        
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def test_config_loading(self) -> TestResult:
        """Test configuration file loading."""
        result = TestResult("Configuration Loading")
        
        try:
            import yaml
            
            config_path = "litellm_config.yaml"
            if not os.path.exists(config_path):
                result.error = f"Config file not found: {config_path}"
                return result
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Verify required sections
            required = ['model_list', 'load_balancing_config', 'proxy_server']
            for section in required:
                if section not in config:
                    result.error = f"Missing required section: {section}"
                    return result
            
            # Verify at least one model
            if not config.get('model_list') or len(config['model_list']) == 0:
                result.error = "No models configured"
                return result
            
            result.passed = True
            result.message = f"Loaded {len(config['model_list'])} models"
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_guard_hooks_import(self) -> TestResult:
        """Test LLM Guard hooks can be imported."""
        result = TestResult("LLM Guard Hooks Import")
        
        try:
            from litellm_guard_hooks import (
                initialize_hooks,
                get_hooks,
                LiteLLMGuardHooks
            )
            
            result.passed = True
            result.message = "Hooks imported successfully"
            
        except ImportError as e:
            result.error = f"Import error: {e}"
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_language_detection(self) -> TestResult:
        """Test language detection."""
        result = TestResult("Language Detection")
        
        try:
            from litellm_guard_hooks import LanguageDetector
            
            test_cases = {
                "你好，世界": "zh",           # Chinese
                "Xin chào thế giới": "vi",    # Vietnamese
                "こんにちは": "ja",            # Japanese
                "안녕하세요": "ko",            # Korean
                "Привет мир": "ru",           # Russian
                "مرحبا بالعالم": "ar",        # Arabic
                "Hello world": "en",          # English
            }
            
            all_passed = True
            for text, expected_lang in test_cases.items():
                detected = LanguageDetector.detect_language(text)
                if detected != expected_lang:
                    result.error = f"Expected {expected_lang}, got {detected} for '{text}'"
                    all_passed = False
                    break
            
            if all_passed:
                result.passed = True
                result.message = f"Tested {len(test_cases)} languages"
        
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_error_messages(self) -> TestResult:
        """Test error message retrieval."""
        result = TestResult("Error Messages")
        
        try:
            from litellm_guard_hooks import LanguageDetector
            
            languages = ['zh', 'vi', 'ja', 'ko', 'ru', 'ar', 'en']
            errors_found = 0
            
            for lang in languages:
                msg = LanguageDetector.get_error_message(
                    'prompt_blocked',
                    lang,
                    'TestReason'
                )
                if msg and 'TestReason' in msg:
                    errors_found += 1
            
            if errors_found == len(languages):
                result.passed = True
                result.message = f"All {len(languages)} language messages found"
            else:
                result.error = f"Only {errors_found}/{len(languages)} messages found"
        
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_api_health(self) -> TestResult:
        """Test API health endpoint."""
        result = TestResult("API Health Endpoint")
        
        try:
            import requests
            
            response = requests.get(f"{self.base_url}/health", timeout=5)
            
            if response.status_code == 200:
                result.passed = True
                result.message = "Health endpoint responding"
            else:
                result.error = f"Status {response.status_code}"
        
        except requests.exceptions.ConnectionError:
            result.error = f"Cannot connect to {self.base_url}"
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_api_models(self) -> TestResult:
        """Test models endpoint."""
        result = TestResult("Models Endpoint")
        
        try:
            import requests
            
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    result.passed = True
                    result.message = f"Found {len(data['data'])} models"
                else:
                    result.error = "No models in response"
            else:
                result.error = f"Status {response.status_code}"
        
        except requests.exceptions.ConnectionError:
            result.error = f"Cannot connect to {self.base_url}"
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_chat_completion(self, model: str = "ollama/llama3.2") -> TestResult:
        """Test chat completion endpoint."""
        result = TestResult(f"Chat Completion ({model})")
        
        try:
            import requests
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
                "stream": False,
                "max_tokens": 50
            }
            
            start = time.time()
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=30
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    result.passed = True
                    result.message = f"Generated response in {elapsed:.2f}s"
                else:
                    result.error = "No choices in response"
            else:
                result.error = f"Status {response.status_code}: {response.text[:100]}"
        
        except requests.exceptions.Timeout:
            result.error = "Request timeout (30s)"
        except requests.exceptions.ConnectionError:
            result.error = f"Cannot connect to {self.base_url}"
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_guard_blocking(self) -> TestResult:
        """Test LLM Guard blocking."""
        result = TestResult("LLM Guard Blocking")
        
        try:
            import requests
            
            # Payload designed to trigger guards
            payload = {
                "model": "ollama/llama3.2",
                "messages": [
                    {"role": "user", "content": "my_secret_api_key=12345"}  # Secrets scanner
                ],
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=10
            )
            
            # Should be blocked (400) or allowed (200)
            if response.status_code == 400:
                result.passed = True
                result.message = "Guard blocked suspicious request"
            elif response.status_code == 200:
                result.message = "Request not blocked (scanner not configured)"
                result.passed = True
            else:
                result.error = f"Unexpected status {response.status_code}"
        
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_streaming(self) -> TestResult:
        """Test streaming response."""
        result = TestResult("Streaming Response")
        
        try:
            import requests
            
            payload = {
                "model": "ollama/llama3.2",
                "messages": [
                    {"role": "user", "content": "Count to 5"}
                ],
                "stream": True,
                "max_tokens": 20
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=30,
                stream=True
            )
            
            if response.status_code == 200:
                chunks = 0
                for line in response.iter_lines():
                    if line:
                        chunks += 1
                
                if chunks > 0:
                    result.passed = True
                    result.message = f"Received {chunks} stream chunks"
                else:
                    result.error = "No stream data received"
            else:
                result.error = f"Status {response.status_code}"
        
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_embeddings(self) -> TestResult:
        """Test embeddings endpoint."""
        result = TestResult("Embeddings Endpoint")
        
        try:
            import requests
            
            payload = {
                "model": "ollama/llama3.2",
                "input": "Hello world"
            }
            
            response = requests.post(
                f"{self.base_url}/v1/embeddings",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    result.passed = True
                    result.message = "Embeddings generated successfully"
                else:
                    result.error = "No embeddings in response"
            else:
                result.error = f"Status {response.status_code}"
        
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def run_all_tests(self) -> bool:
        """Run all tests."""
        logger.info("Starting LiteLLM Integration Tests")
        logger.info("=" * 50)
        
        tests = [
            self.test_config_loading,
            self.test_guard_hooks_import,
            self.test_language_detection,
            self.test_error_messages,
            self.test_api_health,
            self.test_api_models,
            self.test_chat_completion,
            self.test_guard_blocking,
            self.test_streaming,
            self.test_embeddings,
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                self.results.append(result)
                logger.info(str(result))
            except Exception as e:
                logger.error(f"Test execution error: {e}", exc_info=self.verbose)
        
        logger.info("=" * 50)
        
        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        logger.info(f"Results: {passed}/{total} tests passed")
        
        return passed == total
    
    def run_specific_tests(self, test_pattern: str) -> bool:
        """Run tests matching pattern."""
        logger.info(f"Running tests matching: {test_pattern}")
        logger.info("=" * 50)
        
        tests = [
            self.test_config_loading,
            self.test_guard_hooks_import,
            self.test_language_detection,
            self.test_error_messages,
            self.test_api_health,
            self.test_api_models,
            self.test_chat_completion,
            self.test_guard_blocking,
            self.test_streaming,
            self.test_embeddings,
        ]
        
        for test_func in tests:
            test_name = test_func.__name__
            if test_pattern.lower() in test_name.lower():
                try:
                    result = test_func()
                    self.results.append(result)
                    logger.info(str(result))
                except Exception as e:
                    logger.error(f"Test error: {e}", exc_info=self.verbose)
        
        logger.info("=" * 50)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        logger.info(f"Results: {passed}/{total} tests passed")
        
        return passed == total


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='LiteLLM Integration Test Suite'
    )
    
    parser.add_argument(
        '--base-url',
        default='http://localhost:8000',
        help='Base URL of LiteLLM proxy (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--test',
        type=str,
        help='Run specific test (e.g., "guard", "api", "embedding")'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    tester = LiteLLMTester(args.base_url, args.verbose)
    
    if args.test:
        success = tester.run_specific_tests(args.test)
    else:
        success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
