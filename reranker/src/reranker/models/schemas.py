"""Pydantic schemas for the reranker API."""

from typing import List, Optional

from pydantic import BaseModel, Field, validator


class RerankRequest(BaseModel):
    query: str = Field(..., description="User query text")
    documents: List[str] = Field(..., description="Candidate documents to rerank")
    top_k: Optional[int] = Field(None, description="Number of top documents to return")
    return_documents: bool = Field(True, description="Include documents in the response")

    @validator("documents")
    def validate_documents(cls, value: List[str]) -> List[str]:  # noqa: D417
        if not value:
            raise ValueError("documents must contain at least one item")
        return value


class RerankResponse(BaseModel):
    model: str
    took_ms: float
    results: List[dict]
