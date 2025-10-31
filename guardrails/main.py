"""
Ollama Guardrails - Entry Point

This is the main entry point for the Ollama Guardrails application.
The application code is now organized as a proper Python package in src/ollama_guardrails/.

Usage:
    python main.py
    
Or with the CLI:
    python -m ollama_guardrails server
    
Or with Uvicorn:
    uvicorn src.ollama_guardrails.app:app --host 0.0.0.0 --port 8080

For installed package:
    ollama-guardrails server
"""

import sys
import os

# Add src directory to Python path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
if __name__ == "__main__":
    from ollama_guardrails import run_server
    run_server()
