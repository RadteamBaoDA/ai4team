"""API routes for the reranker service."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from .normalization import normalize_documents
from .schemas import RerankRequest, RerankResponse
from .service import (
    QueueFullError,
    QueueTimeoutError,
    config,
    controller,
    rerank_with_queue,
)

router = APIRouter()


@router.post("/rerank", response_model=RerankResponse)
async def rerank_endpoint(request: RerankRequest) -> RerankResponse:
    try:
        ranked, took_ms = await rerank_with_queue(
            request.query,
            request.documents,
            request.top_k,
        )
    except QueueFullError:
        raise HTTPException(status_code=503, detail="Queue is full") from None
    except QueueTimeoutError:
        raise HTTPException(status_code=504, detail="Timed out waiting for available worker") from None

    if not request.return_documents:
        for item in ranked:
            item.pop("document", None)

    return RerankResponse(model=config.model_name, took_ms=took_ms, results=ranked)


@router.post("/v1/rerank")
async def rerank_v1(request: Request) -> Dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(status_code=400, detail="Field 'query' must be a non-empty string")

    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        raise HTTPException(status_code=400, detail="Field 'documents' must be a non-empty list")

    try:
        normalized_docs, metadata = normalize_documents(documents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    requested_top = payload.get("top_n")
    if requested_top is None:
        requested_top = payload.get("top_k")
    if requested_top is None:
        requested_top = payload.get("rank_count")

    if requested_top is None:
        top_k: Optional[int] = None
    else:
        try:
            top_k = int(requested_top)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="top_n/top_k must be an integer") from exc
        if top_k <= 0:
            top_k = None

    return_documents = payload.get("return_documents")
    if return_documents is None:
        return_documents = True
    elif isinstance(return_documents, str):
        return_documents = return_documents.strip().lower() not in {"false", "0", "no"}
    else:
        return_documents = bool(return_documents)

    try:
        ranked, took_ms = await rerank_with_queue(query, normalized_docs, top_k)
    except QueueFullError:
        raise HTTPException(status_code=503, detail="Queue is full") from None
    except QueueTimeoutError:
        raise HTTPException(status_code=504, detail="Timed out waiting for available worker") from None

    results: List[Dict[str, Any]] = []
    for position, item in enumerate(ranked, start=1):
        idx = item.get("index")
        if idx is None or not (0 <= idx < len(metadata)):
            continue
        meta = metadata[idx]
        relevance = float(item.get("score", 0.0))
        result_entry: Dict[str, Any] = {
            "index": idx,
            "rank": position,
            "relevance_score": relevance,
            "score": relevance,
        }
        if "id" in meta:
            result_entry["id"] = meta["id"]

        if return_documents:
            original = documents[idx]
            if isinstance(original, dict):
                doc_payload = copy.deepcopy(original)
                doc_payload.setdefault("text", meta.get("text", ""))
            else:
                doc_payload = {"text": meta.get("text", "")}
                if "id" in meta:
                    doc_payload.setdefault("id", meta["id"])
            result_entry["document"] = doc_payload
            result_entry["text"] = meta.get("text", "")

        results.append(result_entry)

    response = {
        "id": f"rerank-{uuid.uuid4().hex}",
        "model": payload.get("model") or config.model_name,
        "results": results,
        "data": results,
        "usage": {"total_tokens": 0},
        "took_ms": took_ms,
        "meta": {
            "api_version": {"version": datetime.utcnow().date().isoformat()},
            "warnings": [],
            "compatibility": ["cohere", "jina"],
        },
    }

    return response
