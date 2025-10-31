"""Test script to verify the optimized package structure."""

import sys
import importlib.util
from pathlib import Path

def test_package_structure():
    """Test that the new package structure works correctly."""
    
    # Add src to path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    print("🧪 Testing Optimized Package Structure")
    print("=" * 50)
    
    # Test core imports
    print("\n📦 Testing Core Modules:")
    try:
        from reranker.core.config import RerankerConfig
        print("  ✅ reranker.core.config - OK")
    except ImportError as e:
        print(f"  ❌ reranker.core.config - {e}")
    
    try:
        from reranker.core.concurrency import OptimizedConcurrencyController
        print("  ✅ reranker.core.concurrency - OK")
    except ImportError as e:
        print(f"  ❌ reranker.core.concurrency - {e}")
    
    # Test models
    print("\n📋 Testing Model Schemas:")
    try:
        from reranker.models.schemas import RerankRequest, RerankResponse
        print("  ✅ reranker.models.schemas - OK")
    except ImportError as e:
        print(f"  ❌ reranker.models.schemas - {e}")
    
    # Test utils
    print("\n🔧 Testing Utilities:")
    try:
        from reranker.utils.normalization import normalize_documents
        print("  ✅ reranker.utils.normalization - OK")
    except ImportError as e:
        print(f"  ❌ reranker.utils.normalization - {e}")
    
    # Test API
    print("\n🌐 Testing API Layer:")
    try:
        from reranker.api.routes import router
        print("  ✅ reranker.api.routes - OK")
    except ImportError as e:
        print(f"  ❌ reranker.api.routes - {e}")
    
    try:
        from reranker.api.app import app
        print("  ✅ reranker.api.app - OK")
    except ImportError as e:
        print(f"  ❌ reranker.api.app - {e}")
    
    # Test main package
    print("\n📦 Testing Package Entry Points:")
    try:
        import reranker
        print("  ✅ reranker package - OK")
    except ImportError as e:
        print(f"  ❌ reranker package - {e}")
    
    print("\n✨ Structure Test Complete!")
    print("\n📁 New Package Structure Summary:")
    print("""
    reranker/
    ├── src/reranker/           # Main package
    │   ├── api/                # FastAPI layer
    │   ├── core/               # Core logic
    │   ├── models/             # Data models
    │   ├── services/           # Business services
    │   └── utils/              # Utilities
    ├── tests/                  # Test suite
    │   ├── unit/               # Unit tests
    │   └── integration/        # Integration tests
    ├── scripts/                # Shell scripts
    ├── config/                 # Environment configs
    ├── main.py                 # Entry point
    └── pyproject.toml          # Modern packaging
    """)

if __name__ == "__main__":
    test_package_structure()