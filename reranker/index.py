"""Entrypoint module that exposes the FastAPI app instance."""

from .app import app  # noqa: F401


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "reranker.index:app",
        host=os.environ.get("RERANKER_HOST", "0.0.0.0"),
        port=int(os.environ.get("RERANKER_PORT", "8000")),
        reload=False,
    )
