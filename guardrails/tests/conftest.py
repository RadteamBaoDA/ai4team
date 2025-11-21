"""
Pytest configuration and fixtures for Ollama Guardrails tests.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "ollama_url": "http://localhost:11434",
        "proxy_host": "0.0.0.0", 
        "proxy_port": 8080,
        "enable_input_guard": True,
        "enable_output_guard": True,
    }


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "model": "llama2",
        "created_at": "2023-12-12T14:13:43.416799Z",
        "response": "Hello! How can I assist you today?",
        "done": True
    }