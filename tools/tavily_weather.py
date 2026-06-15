"""Tavily weather search function tool with freshness TTL enforcement."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from typing import Any

from agents import function_tool
from dotenv import load_dotenv
load_dotenv()

from config.model_config import config as aria_config

# In-memory cache: location → (result_dict, fetched_at_epoch)
_WEATHER_CACHE: dict[str, tuple[dict, float]] = {}


def _is_fresh(fetched_at: float) -> bool:
    age = datetime.now(timezone.utc).timestamp() - fetched_at
    return age < aria_config.weather_ttl_seconds


@function_tool
def get_weather(location: str, force_refresh: bool = False) -> dict[str, Any]:
    """
    Retrieve current weather for a given location using Tavily.
    Returns temperature, condition, summary, and source URL.
    Results are cached for up to 2 hours (configurable TTL).

    Args:
        location: City/country string, e.g. "London, UK" or "Singapore"
        force_refresh: If True, bypass the cache and fetch fresh data
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.endswith("..."):
        return {
            "error": "TAVILY_API_KEY not configured",
            "location": location,
            "is_fresh": False,
        }

    cache_key = location.lower().strip()
    now = datetime.now(timezone.utc).timestamp()

    if not force_refresh and cache_key in _WEATHER_CACHE:
        cached_result, fetched_at = _WEATHER_CACHE[cache_key]
        if _is_fresh(fetched_at):
            cached_result["is_fresh"] = True
            cached_result["from_cache"] = True
            return cached_result

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        query = f"current weather in {location} today temperature conditions"
        response = client.search(
            query=query,
            search_depth="basic",
            topic="general",
            max_results=3,
            include_answer=True,
            include_raw_content=False,
        )

        answer = response.get("answer") or ""
        results = response.get("results", [])
        source_url = results[0].get("url") if results else None
        snippet = results[0].get("content", "")[:300] if results else ""

        # Parse condition keywords from answer
        condition = "unknown"
        for cond in ["rain", "sunny", "cloud", "storm", "snow", "fog", "wind", "clear", "hot", "cold", "humid"]:
            if cond in (answer + snippet).lower():
                condition = cond
                break

        result = {
            "location": location,
            "query_used": query,
            "summary": answer or snippet or f"Weather data retrieved for {location}.",
            "condition": condition,
            "temperature_c": None,
            "retrieved_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "is_fresh": True,
            "from_cache": False,
            "source_url": source_url,
            "raw_snippet": snippet,
        }

        _WEATHER_CACHE[cache_key] = (result.copy(), now)

        # Auto-store into RAG vector store (non-blocking, best-effort)
        try:
            import json
            from db.vector_store import upsert
            doc_content = (
                f"Location: {location}. Condition: {condition}. "
                f"Summary: {result['summary']}. Retrieved: {result['retrieved_at']}."
            )
            upsert(
                collection="weather_history",
                content=doc_content,
                metadata={
                    "location": location,
                    "condition": condition,
                    "retrieved_at": result["retrieved_at"],
                    "source_url": source_url or "",
                    "query": query,
                },
            )
        except Exception:
            pass  # RAG store failure must never break weather retrieval

        return result

    except Exception as exc:
        return {
            "error": str(exc),
            "location": location,
            "is_fresh": False,
        }
