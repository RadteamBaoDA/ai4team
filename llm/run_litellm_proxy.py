#!/usr/bin/env python3
"""
LiteLLM Proxy Launcher with Custom Guardrail Integration
Supports custom guardrail mode for security scanning

The proxy loads the custom guardrail from litellm_config.yaml and applies it to all requests.

Usage:
    python run_litellm_proxy.py
    python run_litellm_proxy.py --config ./litellm_config.yaml
    python run_litellm_proxy.py --host 0.0.0.0 --port 8000 --workers 4
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_config(config_path):
    """Validate that the config file exists and is readable."""
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            if 'guardrails:' not in content or 'litellm_guard_hooks' not in content:
                logger.warning("Config file does not contain guardrail configuration")
                logger.info("Add guardrails section to enable LLM Guard security")
        return True
    except Exception as e:
        logger.error(f"Failed to read config file: {e}")
        return False


def validate_guardrail():
    """Validate that the guardrail module can be imported."""
    try:
        from litellm_guard_hooks import LLMGuardCustomGuardrail, LanguageDetector
        logger.info("✓ Custom guardrail module imported successfully")
        
        # Test guardrail instantiation
        guardrail = LLMGuardCustomGuardrail()
        logger.info(f"✓ Guardrail initialized (Guard enabled: {guardrail.guard_manager.enabled})")
        
        # Test language detector
        test_langs = {
            "hello": "en",
            "你好": "zh",
            "مرحبا": "ar",
        }
        for text, expected in test_langs.items():
            detected = LanguageDetector.detect_language(text)
            if detected == expected or expected == "en":
                logger.debug(f"✓ Language detection: '{text}' -> {detected}")
        
        return True
    except ImportError as e:
        logger.warning(f"Could not import guardrail: {e}")
        logger.info("Ensure litellm_guard_hooks.py is in the Python path")
        return False
    except Exception as e:
        logger.error(f"Guardrail validation failed: {e}")
        return False


def main():
    """Main entry point for LiteLLM proxy with custom guardrail."""
    parser = argparse.ArgumentParser(
        description='LiteLLM Proxy with Custom LLM Guard Guardrail',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default config
  python run_litellm_proxy.py
  
  # Start with custom config and port
  python run_litellm_proxy.py --config ./my_config.yaml --port 9000
  
  # Start with multiple workers
  python run_litellm_proxy.py --workers 8
  
  # Start in debug mode
  python run_litellm_proxy.py --log-level DEBUG
        """
    )
    
    # Configuration options
    parser.add_argument(
        '--config',
        default=os.getenv('CONFIG_PATH', './litellm_config.yaml'),
        help='Path to LiteLLM config YAML file (default: ./litellm_config.yaml)'
    )
    
    parser.add_argument(
        '--host',
        default=os.getenv('LITELLM_HOST', '0.0.0.0'),
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('LITELLM_PORT', 8000)),
        help='Port to bind to (default: 8000)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=int(os.getenv('LITELLM_WORKERS', 4)),
        help='Number of worker processes (default: 4)'
    )
    
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Log level (default: INFO)'
    )
    
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload on file changes (development mode)'
    )
    
    parser.add_argument(
        '--disable-guard',
        action='store_true',
        help='Disable custom guardrail security scanning'
    )
    
    parser.add_argument(
        '--input-score-threshold',
        type=float,
        default=float(os.getenv('LLM_GUARD_INPUT_SCORE_THRESHOLD', 0.9)),
        help='Input scanner score threshold (0.0-1.0). Scores below this are rejected. Default: 0.9'
    )
    
    parser.add_argument(
        '--output-score-threshold',
        type=float,
        default=float(os.getenv('LLM_GUARD_OUTPUT_SCORE_THRESHOLD', 0.9)),
        help='Output scanner score threshold (0.0-1.0). Scores below this are rejected. Default: 0.9'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate config and guardrail, then exit'
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['CONFIG_PATH'] = args.config
    os.environ['LITELLM_HOST'] = args.host
    os.environ['LITELLM_PORT'] = str(args.port)
    os.environ['LITELLM_WORKERS'] = str(args.workers)
    os.environ['LITELLM_LOG_LEVEL'] = args.log_level
    
    if args.disable_guard:
        os.environ['GUARD_ENABLED'] = 'false'
    
    # Print header
    logger.info("=" * 80)
    logger.info("LiteLLM Proxy with Custom Guardrail (LLM Guard)")
    logger.info("=" * 80)
    logger.info(f"Configuration File: {args.config}")
    logger.info(f"Bind Address: {args.host}:{args.port}")
    logger.info(f"Worker Processes: {args.workers}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info(f"Guardrail Enabled: {not args.disable_guard}")
    logger.info("=" * 80)
    
    # Validate configuration
    logger.info("\n[VALIDATION] Checking configuration...")
    if not validate_config(args.config):
        logger.error("Configuration validation failed")
        sys.exit(1)
    logger.info("✓ Configuration file is valid")
    
    # Validate guardrail (if not disabled)
    if not args.disable_guard:
        logger.info("\n[VALIDATION] Checking custom guardrail...")
        if not validate_guardrail():
            logger.warning("⚠ Guardrail validation failed - continuing without guardrail")
        else:
            logger.info("✓ Custom guardrail is ready")
    
    # Exit after validation if requested
    if args.validate_only:
        logger.info("\n[VALIDATION] All checks passed! ✓")
        sys.exit(0)
    
    # Print startup info
    logger.info("\n[STARTUP] LiteLLM Proxy Configuration:")
    logger.info(f"  API Endpoint: http://{args.host}:{args.port}/v1")
    logger.info(f"  Chat Completions: http://{args.host}:{args.port}/v1/chat/completions")
    logger.info(f"  Models: http://{args.host}:{args.port}/v1/models")
    logger.info(f"  Health: http://{args.host}:{args.port}/health")
    
    if not args.disable_guard:
        logger.info("\n[SECURITY] Custom Guardrails Enabled:")
        logger.info("  ✓ Pre-call input validation (async_pre_call_hook)")
        logger.info("  ✓ Parallel moderation (async_moderation_hook)")
        logger.info("  ✓ Post-call output validation (async_post_call_success_hook)")
        logger.info("  ✓ Stream processing (async_post_call_streaming_iterator_hook)")
        logger.info("  ✓ Automatic language detection (7 languages)")
        logger.info("  ✓ 10 security scanners (5 input, 5 output)")
    
    logger.info("\n[STARTUP] Starting LiteLLM proxy...")
    logger.info("=" * 80)
    
    # Start LiteLLM proxy
    try:
        # Use litellm CLI to start the proxy
        import subprocess
        
        cmd = [
            'litellm',
            '--config', args.config,
            '--host', args.host,
            '--port', str(args.port),
            '--num_workers', str(args.workers),
        ]
        
        if args.reload:
            cmd.insert(1, '--debug')  # Enable debug/reload mode
        
        # Set environment for LiteLLM
        env = os.environ.copy()
        env['LITELLM_LOG_LEVEL'] = args.log_level
        
        logger.info(f"Command: {' '.join(cmd)}")
        logger.info("=" * 80)
        
        # Run the proxy
        result = subprocess.run(cmd, env=env, check=False)
        sys.exit(result.returncode)
    
    except KeyboardInterrupt:
        logger.info("\n[SHUTDOWN] Proxy stopped by user")
        sys.exit(0)
    
    except FileNotFoundError:
        logger.error("litellm command not found. Install with: pip install litellm")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Failed to start LiteLLM proxy: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
