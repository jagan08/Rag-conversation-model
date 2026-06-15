"""Location normalization tools for the Semantic Location Resolver."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any
from agents import function_tool

# Known location normalizations — maps DB strings to clean Tavily queries
_LOCATION_MAP: dict[str, dict[str, str]] = {
    "san francisco, ca, usa": {"normalized": "San Francisco, California", "country": "United States", "query": "San Francisco CA weather"},
    "new york, ny, usa": {"normalized": "New York City", "country": "United States", "query": "New York City weather"},
    "austin, tx, usa": {"normalized": "Austin, Texas", "country": "United States", "query": "Austin TX weather"},
    "seattle, wa, usa": {"normalized": "Seattle, Washington", "country": "United States", "query": "Seattle WA weather"},
    "boston, ma, usa": {"normalized": "Boston, Massachusetts", "country": "United States", "query": "Boston MA weather"},
    "chicago, il, usa": {"normalized": "Chicago, Illinois", "country": "United States", "query": "Chicago IL weather"},
    "london, uk": {"normalized": "London, England", "country": "United Kingdom", "query": "London UK weather"},
    "berlin, germany": {"normalized": "Berlin", "country": "Germany", "query": "Berlin Germany weather"},
    "amsterdam, netherlands": {"normalized": "Amsterdam", "country": "Netherlands", "query": "Amsterdam Netherlands weather"},
    "paris, france": {"normalized": "Paris", "country": "France", "query": "Paris France weather"},
    "toronto, canada": {"normalized": "Toronto, Ontario", "country": "Canada", "query": "Toronto Canada weather"},
    "singapore": {"normalized": "Singapore", "country": "Singapore", "query": "Singapore weather"},
    "sydney, australia": {"normalized": "Sydney, New South Wales", "country": "Australia", "query": "Sydney Australia weather"},
    "tokyo, japan": {"normalized": "Tokyo", "country": "Japan", "query": "Tokyo Japan weather"},
    "bangalore, india": {"normalized": "Bangalore, Karnataka", "country": "India", "query": "Bangalore India weather"},
    "dublin, ireland": {"normalized": "Dublin", "country": "Ireland", "query": "Dublin Ireland weather"},
    "stockholm, sweden": {"normalized": "Stockholm", "country": "Sweden", "query": "Stockholm Sweden weather"},
    "zurich, switzerland": {"normalized": "Zurich", "country": "Switzerland", "query": "Zurich Switzerland weather"},
}


@function_tool
def normalize_location(office_location: str) -> dict[str, Any]:
    """
    Normalize an employee's office_location string into a clean location
    suitable for weather queries. Returns normalized name, country, and
    an optimized search query string.

    Args:
        office_location: Raw location from the employee DB, e.g. "San Francisco, CA, USA"
    """
    key = office_location.lower().strip()

    # Exact match
    if key in _LOCATION_MAP:
        mapping = _LOCATION_MAP[key]
        return {
            "original": office_location,
            "normalized": mapping["normalized"],
            "country": mapping["country"],
            "search_query": mapping["query"],
            "confidence": 1.0,
            "match_type": "exact",
        }

    # Fuzzy: check if any known key is a substring or vice versa
    best_key = None
    best_score = 0.0
    for known_key in _LOCATION_MAP:
        # Simple token overlap score
        known_tokens = set(known_key.replace(",", " ").split())
        input_tokens = set(key.replace(",", " ").split())
        overlap = len(known_tokens & input_tokens)
        score = overlap / max(len(known_tokens), len(input_tokens), 1)
        if score > best_score:
            best_score = score
            best_key = known_key

    if best_key and best_score >= 0.4:
        mapping = _LOCATION_MAP[best_key]
        return {
            "original": office_location,
            "normalized": mapping["normalized"],
            "country": mapping["country"],
            "search_query": mapping["query"],
            "confidence": round(best_score, 2),
            "match_type": "fuzzy",
        }

    # Fallback: use the location as-is
    clean = office_location.replace(", USA", "").replace(", UK", ", United Kingdom")
    return {
        "original": office_location,
        "normalized": clean,
        "country": "",
        "search_query": f"{clean} weather",
        "confidence": 0.5,
        "match_type": "fallback",
    }


@function_tool
def batch_normalize_locations(office_locations: list[str]) -> dict[str, Any]:
    """
    Normalize multiple employee office_location strings at once.
    Returns a mapping from original → normalized location info.

    Args:
        office_locations: List of raw location strings from employee DB
    """
    import asyncio

    results = {}
    for loc in office_locations[:20]:  # cap at 20 to avoid runaway
        key = loc.lower().strip()
        if key in _LOCATION_MAP:
            m = _LOCATION_MAP[key]
            results[loc] = {"normalized": m["normalized"], "search_query": m["query"], "confidence": 1.0}
        else:
            results[loc] = {"normalized": loc, "search_query": f"{loc} weather", "confidence": 0.5}

    return {"locations": results, "total": len(results)}
