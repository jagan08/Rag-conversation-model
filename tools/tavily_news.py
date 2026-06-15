"""Tavily news search function tool with freshness TTL enforcement."""
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

_NEWS_CACHE: dict[str, tuple[dict, float]] = {}


def _is_fresh(fetched_at: float) -> bool:
    age = datetime.now(timezone.utc).timestamp() - fetched_at
    return age < aria_config.news_ttl_seconds


@function_tool
def get_news(topic: str, location: str = "", max_results: int = 5) -> dict[str, Any]:
    """
    Search for recent news on a topic, optionally filtered by location.
    Results are cached for up to 24 hours (configurable TTL).

    Args:
        topic: News topic, e.g. "technology layoffs", "weather alerts", "local events"
        location: Optional location context, e.g. "London" or "Singapore"
        max_results: Number of articles to return (max 10)
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.endswith("..."):
        return {
            "error": "TAVILY_API_KEY not configured",
            "topic": topic,
            "articles": [],
            "is_fresh": False,
        }

    cache_key = f"{topic.lower().strip()}|{location.lower().strip()}"
    now = datetime.now(timezone.utc).timestamp()
    max_results = min(max_results, 10)

    if cache_key in _NEWS_CACHE:
        cached, fetched_at = _NEWS_CACHE[cache_key]
        if _is_fresh(fetched_at):
            cached["is_fresh"] = True
            cached["from_cache"] = True
            return cached

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        query = f"{topic} {location}".strip() if location else topic
        response = client.search(
            query=query,
            search_depth="basic",
            topic="news",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            days=1,
        )

        results = response.get("results", [])
        articles = [
            {
                "title": r.get("title", ""),
                "summary": r.get("content", "")[:250],
                "url": r.get("url", ""),
                "published_at": r.get("published_date"),
                "relevance_score": r.get("score", 1.0),
                "source": r.get("url", "").split("/")[2] if r.get("url") else "",
            }
            for r in results
        ]

        result = {
            "topic": topic,
            "location": location,
            "query_used": query,
            "articles": articles,
            "total_found": len(articles),
            "answer": response.get("answer", ""),
            "retrieved_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "is_fresh": True,
            "from_cache": False,
        }

        _NEWS_CACHE[cache_key] = (result.copy(), now)

        # Auto-store each article into RAG news_history (best-effort)
        try:
            from db.vector_store import upsert
            for art in articles[:5]:
                doc_content = (
                    f"Title: {art['title']}. "
                    f"Summary: {art['summary']}. "
                    f"Topic: {topic}. Location: {location}. "
                    f"Retrieved: {result['retrieved_at']}."
                )
                upsert(
                    collection="news_history",
                    content=doc_content,
                    metadata={
                        "title": art["title"],
                        "url": art["url"],
                        "topic": topic,
                        "location": location,
                        "retrieved_at": result["retrieved_at"],
                        "published_at": art.get("published_at", ""),
                    },
                )
        except Exception:
            pass  # RAG store failure must never break news retrieval

        return result

    except Exception as exc:
        return {
            "error": str(exc),
            "topic": topic,
            "articles": [],
            "is_fresh": False,
        }
