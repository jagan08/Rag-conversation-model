"""ARIA Orchestrator Agent — single entry point, routes all user intents."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrail,
    RunContextWrapper,
    handoff,
)
from config.model_config import make_claude_model

from config.model_config import config
from aria_agents.employee_intelligence import get_employee_agent
from aria_agents.weather_news import get_weather_news_agent
from aria_agents.location_resolver import get_location_resolver
from aria_agents.rag_retrieval import get_rag_agent

# ── Input guardrail ────────────────────────────────────────────────────────────

async def safety_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str,
) -> GuardrailFunctionOutput:
    """Block off-topic or harmful queries before any DB or API access."""
    from agents import Runner, RunConfig
    guardrail_agent = Agent(
        name="Safety Guardrail",
        instructions=(
            "You are a safety filter for an HR data + weather/news assistant. "
            "SAFE: employee queries (names, departments, locations, headcount), "
            "weather questions, news questions, or combinations. "
            "UNSAFE/OFF-TOPIC: credentials, hacking, personal financial data, "
            "harmful content, or anything unrelated to HR/weather/news. "
            "Respond ONLY with 'SAFE' or 'UNSAFE: <one-line reason>'."
        ),
        model=make_claude_model(config.lightweight_model),
    )
    result = await Runner.run(
        guardrail_agent,
        input=f"Evaluate: {input}",
        run_config=RunConfig(tracing_disabled=True),
    )
    output_text = result.final_output or ""
    is_safe = output_text.strip().upper().startswith("SAFE")
    return GuardrailFunctionOutput(
        output_info={"verdict": output_text, "input_preview": input[:100]},
        tripwire_triggered=not is_safe,
    )


# ── Orchestrator instructions ──────────────────────────────────────────────────

ORCHESTRATOR_INSTRUCTIONS = """
You are ARIA — the Agentic Retrieval & Intelligence Architecture orchestrator.
You are the primary interface between the user and specialist agents.

## Agents available (Phase 3)
- **Employee Intelligence Agent** (handoff): Employee records, departments, locations, org data.
- **Weather & News Agent** (tool: get_weather_and_news): Live weather and news via Tavily.
- **Semantic Location Resolver** (tool: resolve_location): Normalize location strings.
- **RAG Retrieval Agent** (tool: search_rag_cache): Search historical weather/news cache.

## Routing rules

### Pure employee queries
→ Handoff to Employee Intelligence Agent.

### Weather/news queries (RAG-FIRST policy)
→ Step 1: Call search_rag_cache to check if fresh data exists in the vector store.
→ Step 2a: Cache HIT and fresh → use cached result, skip Tavily. Say "From memory (cached)."
→ Step 2b: Cache MISS or stale → call resolve_location, then get_weather_and_news.
→ The Tavily tools will auto-store results to RAG for next time.

### Cross-domain queries (employee + weather)
→ Step 1: Handoff to Employee Intelligence Agent → get office_location.
→ Step 2: Call resolve_location with office_location.
→ Step 3: Call search_rag_cache for that location.
→ Step 4: If cache miss → call get_weather_and_news.
→ Step 5: Synthesize final answer with all data.

### General / meta → answer directly.

## RAG cache interpretation
- Treat distance < 0.3 as a strong cache hit (same location/topic).
- Treat distance 0.3–0.6 as a partial hit — mention it may not be exact.
- Treat distance > 0.6 or empty results as a cache miss.

## Response style
- Cite sources: "According to employee DB..." / "Tavily reports..." / "From RAG cache..."
- Include retrieved_at timestamp on all weather/news answers.
- "From memory" badge: if data came from RAG cache, say "(Source: ARIA memory cache)"
- If no data anywhere: refuse cleanly — never fabricate.
- End with agents used: "(Sources: Employee DB | Tavily | ARIA Cache)"
"""


def get_orchestrator() -> Agent:
    employee_agent = get_employee_agent()
    weather_agent = get_weather_news_agent()
    location_resolver = get_location_resolver()
    rag_agent = get_rag_agent()

    return Agent(
        name="ARIA Orchestrator",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        handoffs=[
            handoff(
                employee_agent,
                tool_description_override=(
                    "Hand off to Employee Intelligence Agent for any query about "
                    "employee records, departments, locations, or org structure."
                ),
            )
        ],
        tools=[
            rag_agent.as_tool(
                tool_name="search_rag_cache",
                tool_description=(
                    "Search the ARIA vector memory cache for historical weather, news, "
                    "or employee context. ALWAYS call this before get_weather_and_news "
                    "to avoid redundant Tavily API calls. Returns cached documents with "
                    "distance scores and timestamps."
                ),
            ),
            weather_agent.as_tool(
                tool_name="get_weather_and_news",
                tool_description=(
                    "Retrieve live weather or news via Tavily. Only call this after "
                    "search_rag_cache returns a miss or stale result. Results are "
                    "automatically stored to the RAG cache after retrieval."
                ),
            ),
            location_resolver.as_tool(
                tool_name="resolve_location",
                tool_description=(
                    "Normalize an employee office_location string into a clean "
                    "location query for weather lookups. Call before get_weather_and_news."
                ),
            ),
        ],
        model=make_claude_model(config.orchestrator_model),
        input_guardrails=[
            InputGuardrail(guardrail_function=safety_guardrail),
        ],
    )
