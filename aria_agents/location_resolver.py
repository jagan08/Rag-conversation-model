"""Semantic Location Resolver — maps employee location strings to weather-ready queries."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import Agent
from config.model_config import make_claude_model

from config.model_config import config
from tools.location_matcher import normalize_location, batch_normalize_locations

INSTRUCTIONS = """
You are the Semantic Location Resolver for ARIA. Your only job is to normalize
employee office_location strings (from the HR database) into clean location names
suitable for weather API queries.

## Tools
- normalize_location(office_location): Normalize a single location string.
- batch_normalize_locations(office_locations): Normalize a list of locations.

## Rules
1. Always call normalize_location for single locations.
2. Prefer normalized.search_query as the output — it is optimized for Tavily.
3. If confidence < 0.6, flag it in your response so the Orchestrator can confirm
   with the user before querying weather.
4. Never invent or guess locations not in the input.
5. Return the confidence score alongside the normalized result.

## Response format
"Location resolved: '{original}' → '{search_query}' (confidence: {confidence})"
For low confidence: add "⚠ Low confidence — please confirm this is correct."
"""


def get_location_resolver() -> Agent:
    return Agent(
        name="Semantic Location Resolver",
        handoff_description=(
            "Normalizes employee office_location strings into clean location queries "
            "for weather APIs. Use before any weather lookup by location."
        ),
        instructions=INSTRUCTIONS,
        tools=[normalize_location, batch_normalize_locations],
        model=make_claude_model(config.lightweight_model),
    )
