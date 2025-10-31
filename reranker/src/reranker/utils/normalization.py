"""Utilities for normalising document inputs."""

from typing import Any, Dict, List, Tuple


def normalize_documents(documents: List[Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Normalise incoming documents into plain text list and metadata mapping."""
    texts: List[str] = []
    metadata: List[Dict[str, Any]] = []
    for idx, doc in enumerate(documents):
        if isinstance(doc, str):
            text_value = doc
            meta: Dict[str, Any] = {"text": doc}
        elif isinstance(doc, dict):
            text_value = (
                doc.get("text")
                or doc.get("document")
                or doc.get("content")
                or doc.get("body")
                or doc.get("value")
                or doc.get("snippet")
            )
            if text_value is None:
                raise ValueError(f"Document at index {idx} is missing a text/content field")
            meta = dict(doc)
            meta.setdefault("text", text_value)
        else:
            text_value = str(doc)
            meta = {"text": text_value}

        if not isinstance(text_value, str):
            text_value = str(text_value)
        texts.append(text_value)
        metadata.append(meta)
    return texts, metadata
