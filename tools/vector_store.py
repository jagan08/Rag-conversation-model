"""@function_tool wrappers around the sqlite-vec vector store."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any
from agents import function_tool


@function_tool
def embed_and_store(
    content: str,
    collection: str,
    metadata_json: str = "{}",
) -> dict[str, Any]:
    """
    Embed a text document and store it in the vector store.

    Args:
        content: The text to embed and store (weather summary, news article, etc.)
        collection: Target collection — must be one of:
                    'weather_history', 'news_history', 'employee_context'
        metadata_json: JSON string of metadata, e.g. '{"location":"London","condition":"rainy"}'

    Returns doc_id on success.
    """
    import json
    from db.vector_store import upsert
    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
        doc_id = upsert(collection=collection, content=content, metadata=metadata)
        return {
            "success": True,
            "doc_id": doc_id,
            "collection": collection,
            "content_preview": content[:80],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@function_tool
def vector_search(
    query: str,
    collection: str,
    n_results: int = 5,
) -> dict[str, Any]:
    """
    Semantic search over a vector store collection.

    Args:
        query: The natural language search query
        collection: Collection to search — 'weather_history', 'news_history',
                    or 'employee_context'
        n_results: Number of results to return (max 10)

    Returns relevant documents with content, metadata, and similarity distance.
    Lower distance = more similar.
    """
    from db.vector_store import search
    try:
        results = search(collection=collection, query=query, n_results=min(n_results, 10))
        return {
            "query": query,
            "collection": collection,
            "total_found": len(results),
            "documents": results,
        }
    except Exception as exc:
        return {"query": query, "collection": collection, "total_found": 0, "error": str(exc)}


@function_tool
def list_vector_collections() -> dict[str, Any]:
    """
    List all vector store collections and their document counts.
    Use this to check what's available in the RAG cache before deciding
    whether to run a live Tavily search.
    """
    from db.vector_store import list_collections
    try:
        cols = list_collections()
        return {"collections": cols, "total_documents": sum(c["document_count"] for c in cols)}
    except Exception as exc:
        return {"error": str(exc), "collections": []}
