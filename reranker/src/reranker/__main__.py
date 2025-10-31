"""Main module for package execution (python -m reranker)."""

import sys
import os
from pathlib import Path

# Ensure proper import path
if __package__ is None:
    # Running directly as script
    src_path = Path(__file__).parent.parent.parent / "src"
    sys.path.insert(0, str(src_path))
    from reranker.api.app import app
else:
    # Running as module
    from .api.app import app


def main():
    """Main entry point when run as module."""
    import uvicorn
    
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()