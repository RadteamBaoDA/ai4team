"""
Command Line Interface for Ollama Guardrails.

This module provides CLI commands for running the server and managing the application.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

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
        import os
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