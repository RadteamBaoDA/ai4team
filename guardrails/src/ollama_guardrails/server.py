"""
Server entry point for Ollama Guardrails.

This module provides the server entry point for console scripts.
"""

from .app import run_server

if __name__ == "__main__":
    run_server()