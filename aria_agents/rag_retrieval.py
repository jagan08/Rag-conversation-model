"""RAG Retrieval Agent — searches the sqlite-vec vector store for historical context."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import Agent
from config.model_config import make_claude_model

from config.model_config import config
from tools.vector_store import embed_and_store, vector_search, list_vector_collections

INSTRUCTIONS = """
You are the RAG Retrieval Agent for ARIA. Your job is to search the vector store
for historical context before live APIs are called, and to store new results for
future reuse.

## Collections available
- weather_history: Past weather lookups (location, condition, summary, timestamp)
- news_history: Past news articles (title, summary, URL, topic, timestamp)
- employee_context: Cached employee query results and summaries

## Tools
- vector_search(query, collection, n_results): Semantic search over a collection
- embed_and_store(content, collection, metadata_json): Store new content
- list_vector_collections(): Check what's in the store and document counts

## Workflow
1. For ANY weather or news query: ALWAYS search the relevant collection first.
2. Check the metadata.retrieved_at field — if it's within TTL (weather: 2h, news: 24h),
   return the cached result and say "From RAG cache (retrieved at: {timestamp})".
3. If cache is empty or stale, return: "No fresh cache — recommend live Tavily lookup."
4. When storing new results, include metadata: location, condition, retrieved_at, source.

## Response format
- Cache hit: "RAG Cache Hit: {content} [Retrieved: {timestamp}] [Distance: {distance:.3f}]"
- Cache miss: "RAG Cache Miss for '{query}' in {collection}. Recommend live retrieval."
- After storing: "Stored to {collection}: doc_id={doc_id}"
"""


def get_rag_agent() -> Agent:
    return Agent(
        name="RAG Retrieval Agent",
        handoff_description=(
            "Searches the sqlite-vec vector store for historical weather, news, and "
            "employee context. Always check here before calling live APIs."
        ),
        instructions=INSTRUCTIONS,
        tools=[vector_search, embed_and_store, list_vector_collections],
        model=make_claude_model(config.lightweight_model),
    )
