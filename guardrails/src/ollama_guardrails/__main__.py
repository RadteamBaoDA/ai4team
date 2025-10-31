"""
Main module for running Ollama Guardrails as a module.

Usage:
    python -m ollama_guardrails server
    python -m ollama_guardrails --help
"""

from .cli import main

if __name__ == "__main__":
    main()