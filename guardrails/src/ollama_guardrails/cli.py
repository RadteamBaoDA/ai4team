"""
Command Line Interface for Ollama Guardrails.

This module provides CLI commands for running the server and managing the application.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Initialize tiktoken offline mode BEFORE any other imports that depend on it
from .utils.tiktoken_cache import setup_tiktoken_offline_mode
setup_tiktoken_offline_mode()

from .app import run_server
from .core.config import Config


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def cmd_server(args: argparse.Namespace) -> None:
    """Run the guardrails server."""
    setup_logging(args.verbose)
    
    if args.config:
        os.environ["CONFIG_FILE"] = args.config
    
    run_server()


def cmd_validate_config(args: argparse.Namespace) -> None:
    """Validate configuration file."""
    setup_logging(args.verbose)
    
    config_path = args.config
    if not config_path or not Path(config_path).exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        config = Config(config_path)
        print(f"Configuration file '{config_path}' is valid")
        
        # Print some key settings
        print("\nKey Settings:")
        print(f"  Ollama URL: {config.get('ollama_url', 'http://127.0.0.1:11434')}")
        print(f"  Proxy Host: {config.get('proxy_host', '0.0.0.0')}")
        print(f"  Proxy Port: {config.get('proxy_port', 8080)}")
        print(f"  Input Guard: {config.get_bool('enable_input_guard', True)}")
        print(f"  Output Guard: {config.get_bool('enable_output_guard', True)}")
        print(f"  Cache Enabled: {config.get_bool('cache_enabled', True)}")
        
    except Exception as e:
        print(f"Error validating configuration: {e}")
        sys.exit(1)


def cmd_version(args: argparse.Namespace) -> None:
    """Show version information."""
    print("Ollama Guardrails v1.0.0")


def cmd_tiktoken_info(args: argparse.Namespace) -> None:
    """Show tiktoken cache information."""
    setup_logging(args.verbose)
    
    from .utils.tiktoken_cache import get_tiktoken_cache_info
    
    info = get_tiktoken_cache_info()
    
    print("\nTiktoken Offline Cache Configuration:")
    print(f"  Cache Directory: {info['cache_dir']}")
    print(f"  Directory Exists: {info['cache_dir_exists']}")
    print(f"  Offline Mode: {info['offline_mode']}")
    print(f"  Fallback Local: {info['fallback_local']}")
    print(f"  Cache Size: {info['cache_size_mb']:.2f} MB")
    
    if info['cached_files']:
        print(f"  Cached Files ({len(info['cached_files'])}):")
        for filename in info['cached_files']:
            print(f"    - {filename}")
    else:
        print("  No cached files found")


def cmd_tiktoken_download(args: argparse.Namespace) -> None:
    """Download tiktoken encodings for offline use."""
    setup_logging(args.verbose)
    
    from .utils.tiktoken_cache import download_tiktoken_encoding, get_tiktoken_cache_info
    
    encodings = args.encodings or ['cl100k_base', 'p50k_base', 'p50k_edit', 'r50k_base']
    cache_dir = args.cache_dir or os.environ.get('TIKTOKEN_CACHE_DIR', './models/tiktoken')
    
    print(f"\nDownloading tiktoken encodings to: {os.path.abspath(cache_dir)}")
    
    success_count = 0
    for encoding in encodings:
        print(f"  Downloading {encoding}...", end=" ")
        if download_tiktoken_encoding(encoding, cache_dir):
            print("✓")
            success_count += 1
        else:
            print("✗")
    
    print(f"\nSuccessfully downloaded {success_count}/{len(encodings)} encodings")
    
    # Show updated cache info
    info = get_tiktoken_cache_info()
    print(f"\nCache Statistics:")
    print(f"  Total Size: {info['cache_size_mb']:.2f} MB")
    print(f"  Files Cached: {len(info['cached_files'])}")


def cmd_huggingface_info(args: argparse.Namespace) -> None:
    """Show Hugging Face cache information."""
    setup_logging(args.verbose)
    
    from .utils.huggingface_cache import get_huggingface_cache_info
    
    info = get_huggingface_cache_info()
    
    print("\nHugging Face Offline Cache Configuration:")
    print(f"  HF_HOME: {info['hf_home']}")
    print(f"  HF_HOME Exists: {info['hf_home_exists']}")
    print(f"  TRANSFORMERS_CACHE: {info['transformers_cache']}")
    print(f"  TRANSFORMERS Exists: {info['transformers_exists']}")
    print(f"  HF_DATASETS_CACHE: {info['datasets_cache']}")
    print(f"  DATASETS Exists: {info['datasets_exists']}")
    print(f"  Offline Mode: {info['offline_mode']}")
    print(f"  Total Size: {info['hf_home_size_mb']:.2f} MB")
    print(f"  Transformers Models: {info['transformers_files']} files")
    print(f"  Datasets: {info['datasets_files']} files")


def cmd_huggingface_download(args: argparse.Namespace) -> None:
    """Download Hugging Face models for offline use."""
    setup_logging(args.verbose)
    
    from .utils.huggingface_cache import download_huggingface_model, get_huggingface_cache_info
    
    models = args.models or []
    cache_dir = args.cache_dir or os.environ.get('HF_HOME', './models/huggingface')
    
    if not models:
        print("\nNo models specified. Use -m/--models to specify models to download.")
        print("Example: ollama-guardrails hf-download -m bert-base-uncased sentence-transformers/all-mpnet-base-v2")
        return
    
    print(f"\nDownloading Hugging Face models to: {os.path.abspath(cache_dir)}")
    
    success_count = 0
    for model_id in models:
        print(f"  Downloading {model_id}...", end=" ")
        if download_huggingface_model(model_id, cache_dir):
            print("✓")
            success_count += 1
        else:
            print("✗")
    
    print(f"\nSuccessfully downloaded {success_count}/{len(models)} models")
    
    # Show updated cache info
    info = get_huggingface_cache_info()
    print(f"\nCache Statistics:")
    print(f"  Total Size: {info['hf_home_size_mb']:.2f} MB")
    print(f"  Transformers Files: {info['transformers_files']}")
    print(f"  Datasets Files: {info['datasets_files']}")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ollama-guardrails",
        description="Advanced LLM Guard Proxy for Ollama",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands"
    )
    
    # Server command
    server_parser = subparsers.add_parser(
        "server",
        help="Run the guardrails server",
        aliases=["serve", "run"]
    )
    server_parser.add_argument(
        "-c", "--config",
        help="Path to configuration file"
    )
    server_parser.set_defaults(func=cmd_server)
    
    # Validate config command  
    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate configuration file",
        aliases=["validate"]
    )
    validate_parser.add_argument(
        "-c", "--config",
        required=True,
        help="Path to configuration file"
    )
    validate_parser.set_defaults(func=cmd_validate_config)
    
    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information"
    )
    version_parser.set_defaults(func=cmd_version)
    
    # Tiktoken info command
    tiktoken_info_parser = subparsers.add_parser(
        "tiktoken-info",
        help="Show tiktoken cache information"
    )
    tiktoken_info_parser.set_defaults(func=cmd_tiktoken_info)
    
    # Tiktoken download command
    tiktoken_download_parser = subparsers.add_parser(
        "tiktoken-download",
        help="Download tiktoken encodings for offline use"
    )
    tiktoken_download_parser.add_argument(
        "-e", "--encodings",
        nargs="+",
        default=None,
        help="Encodings to download (default: cl100k_base p50k_base p50k_edit r50k_base)"
    )
    tiktoken_download_parser.add_argument(
        "-d", "--cache-dir",
        help="Cache directory for tiktoken files"
    )
    tiktoken_download_parser.set_defaults(func=cmd_tiktoken_download)
    
    # Hugging Face info command
    hf_info_parser = subparsers.add_parser(
        "hf-info",
        help="Show Hugging Face cache information"
    )
    hf_info_parser.set_defaults(func=cmd_huggingface_info)
    
    # Hugging Face download command
    hf_download_parser = subparsers.add_parser(
        "hf-download",
        help="Download Hugging Face models for offline use"
    )
    hf_download_parser.add_argument(
        "-m", "--models",
        nargs="+",
        default=None,
        help="Models to download (e.g., bert-base-uncased sentence-transformers/all-mpnet-base-v2)"
    )
    hf_download_parser.add_argument(
        "-d", "--cache-dir",
        help="Cache directory for Hugging Face models"
    )
    hf_download_parser.set_defaults(func=cmd_huggingface_download)
    
    return parser


def main(args: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Default to server command if no command specified
    if not hasattr(parsed_args, "func"):
        parsed_args.func = cmd_server
    
    try:
        parsed_args.func(parsed_args)
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()