"""Test configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        "Machine learning is a subset of artificial intelligence.",
        "Python is a popular programming language.",
        "Deep learning uses neural networks with multiple layers.",
        "Data science combines statistics and programming.",
        "Natural language processing helps computers understand text.",
    ]

@pytest.fixture 
def sample_query():
    """Sample query for testing."""
    return "What is machine learning?"