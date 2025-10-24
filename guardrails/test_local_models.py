#!/usr/bin/env python3
"""
Test script for Local Models Configuration

This script tests the local model configuration for LLM Guard scanners.
It validates that models can be loaded and used properly when local models are enabled.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path to import guard_manager
sys.path.insert(0, str(Path(__file__).parent))

from guard_manager import LLMGuardManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_local_models_disabled():
    """Test guard manager with local models disabled (default behavior)."""
    logger.info("Testing LLM Guard Manager with local models disabled...")
    
    # Ensure local models are disabled
    os.environ.pop('LLM_GUARD_USE_LOCAL_MODELS', None)
    
    try:
        manager = LLMGuardManager()
        logger.info(f"✓ Manager initialized successfully")
        logger.info(f"  - Use local models: {manager.use_local_models}")
        logger.info(f"  - Input scanners: {len(manager.input_scanners)}")
        logger.info(f"  - Output scanners: {len(manager.output_scanners)}")
        
        # Test a simple scan
        test_prompt = "Hello, this is a test prompt."
        result = manager.scan_input(test_prompt)
        logger.info(f"✓ Input scan completed: {result['allowed']}")
        
        test_output = "This is a test output response."
        result = manager.scan_output(test_output)
        logger.info(f"✓ Output scan completed: {result['allowed']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing disabled local models: {e}")
        return False


def test_local_models_enabled():
    """Test guard manager with local models enabled."""
    logger.info("Testing LLM Guard Manager with local models enabled...")
    
    # Enable local models
    os.environ['LLM_GUARD_USE_LOCAL_MODELS'] = 'true'
    models_path = os.environ.get('LLM_GUARD_MODELS_PATH', './models')
    os.environ['LLM_GUARD_MODELS_PATH'] = models_path
    
    logger.info(f"Local models path: {models_path}")
    
    try:
        manager = LLMGuardManager()
        logger.info(f"✓ Manager initialized successfully")
        logger.info(f"  - Use local models: {manager.use_local_models}")
        logger.info(f"  - Input scanners: {len(manager.input_scanners)}")
        logger.info(f"  - Output scanners: {len(manager.output_scanners)}")
        
        # Check if models directory exists
        if not os.path.exists(models_path):
            logger.warning(f"⚠ Models directory does not exist: {models_path}")
            logger.info("  This is expected if models haven't been downloaded yet.")
            logger.info("  The scanners should still initialize but may download models on first use.")
        
        # Test a simple scan
        test_prompt = "Hello, this is a test prompt."
        result = manager.scan_input(test_prompt)
        logger.info(f"✓ Input scan completed: {result['allowed']}")
        
        test_output = "This is a test output response."
        result = manager.scan_output(test_output)
        logger.info(f"✓ Output scan completed: {result['allowed']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing enabled local models: {e}")
        return False


def check_model_files():
    """Check if model files exist in the expected locations."""
    logger.info("Checking for model files...")
    
    models_path = os.environ.get('LLM_GUARD_MODELS_PATH', './models')
    
    expected_models = [
        "deberta-v3-base-prompt-injection-v2",
        "unbiased-toxic-roberta", 
        "programming-language-identification",
        "deberta-v3-base_finetuned_ai4privacy_v2"
    ]
    
    models_found = 0
    for model_name in expected_models:
        model_path = os.path.join(models_path, model_name)
        if os.path.exists(model_path):
            logger.info(f"✓ Found model: {model_name}")
            models_found += 1
        else:
            logger.warning(f"✗ Missing model: {model_name} at {model_path}")
    
    logger.info(f"Models found: {models_found}/{len(expected_models)}")
    
    if models_found == 0:
        logger.info("\nTo download models, run:")
        logger.info("  mkdir -p models")
        logger.info("  cd models")
        logger.info("  git lfs install")
        logger.info("  git clone https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2")
        logger.info("  git clone https://huggingface.co/unitary/unbiased-toxic-roberta")
        logger.info("  git clone https://huggingface.co/philomath-1209/programming-language-identification")
        logger.info("  git clone https://huggingface.co/Isotonic/deberta-v3-base_finetuned_ai4privacy_v2")
    
    return models_found


def test_scanner_configurations():
    """Test individual scanner configurations."""
    logger.info("Testing scanner configurations...")
    
    try:
        # Test with local models enabled
        os.environ['LLM_GUARD_USE_LOCAL_MODELS'] = 'true'
        manager = LLMGuardManager()
        
        # Check input scanners
        logger.info("Input scanners:")
        for scanner_info in manager.input_scanners:
            scanner_name = scanner_info['name']
            enabled = scanner_info['enabled']
            logger.info(f"  - {scanner_name}: {'enabled' if enabled else 'disabled'}")
        
        # Check output scanners
        logger.info("Output scanners:")
        for scanner_info in manager.output_scanners:
            scanner_name = scanner_info['name']
            enabled = scanner_info['enabled']
            logger.info(f"  - {scanner_name}: {'enabled' if enabled else 'disabled'}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing scanner configurations: {e}")
        return False


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("LLM Guard Local Models Configuration Test")
    logger.info("=" * 60)
    
    # Check model files
    check_model_files()
    
    logger.info("-" * 60)
    
    # Test disabled local models
    success1 = test_local_models_disabled()
    
    logger.info("-" * 60)
    
    # Test enabled local models
    success2 = test_local_models_enabled()
    
    logger.info("-" * 60)
    
    # Test scanner configurations
    success3 = test_scanner_configurations()
    
    logger.info("-" * 60)
    
    # Summary
    logger.info("Test Results:")
    logger.info(f"  - Local models disabled: {'✓ PASS' if success1 else '✗ FAIL'}")
    logger.info(f"  - Local models enabled: {'✓ PASS' if success2 else '✗ FAIL'}")
    logger.info(f"  - Scanner configurations: {'✓ PASS' if success3 else '✗ FAIL'}")
    
    if all([success1, success2, success3]):
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.error("\n❌ Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())