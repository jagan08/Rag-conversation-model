# Multi-Agent RAG System — Implementation Plan
## Batch 1: Executive Summary · Assumptions · SDK Matrix · Architecture Overview

> **Grounding note:** Every SDK capability cited below is sourced from the OpenAI Agents SDK
> documentation and search results gathered on 2026-06-10. Where a capability requires a
> custom wrapper or is inferred rather than explicitly documented, it is marked accordingly.

---

## 1. Executive Summary

### System Name: **ARIA** — *Agentic Retrieval & Intelligence Architecture*

ARIA is a production-ready, multi-agent conversational system that answers natural-language
questions by fusing two live data sources: real-time weather and news retrieved via the
**Tavily API**, and structured enterprise HR data stored in a **SQLAlchemy-backed relational
database** containing 500 mock employee records.

The orchestration layer is built on the **OpenAI Agents SDK (Python)**, which provides
first-class primitives for agent definitions, handoffs, function tools, guardrails,
human-in-the-loop (HITL) approvals, tracing, and session-based memory. Claude (Anthropic)
is the **primary LLM provider** for all reasoning-heavy agents, accessed via the SDK's
`LitellmModel` extension. OpenAI GPT-4o is the **fallback provider** and is used for
lightweight guardrail/critic agents where cost efficiency matters. Model-provider selection
is abstracted behind a configuration layer, making it trivially swappable.

### What the System Does

A user asks questions such as:

- *"What is the weather where Raghav lives?"*
- *"Which employees are in rainy locations today?"*
- *"Which departments are impacted by heat alerts?"*

ARIA:
1. Interprets intent and routes to the appropriate specialist agent.
2. Queries the employee database to resolve identity → office_location.
3. Retrieves fresh weather/news from Tavily (and/or from a vector store for recent
   historical context).
4. Semantically maps employee locations to weather data locations.
5. Validates the answer against retrieved evidence through a dedicated Grounding Critic.
6. Returns a conversational response with **provenance metadata** (source URLs, query
   timestamps, confidence scores).
7. Pauses execution and requests human approval for any sensitive or ambiguous operation.

### Primary Design Goals

| Goal | Approach |
|---|---|
| Factual groundedness | Critic agent + retrieval citations + structured outputs |
| No hallucination | Zero evidence → refusal response, not a guess |
| Production resilience | Retry policies, fallback providers, error guardrails |
| Human oversight | SDK-native `needs_approval` HITL on all destructive/ambiguous actions |
| Maintainability | Thin agents, clear tool boundaries, no over-agentization |
| Observability | SDK-native tracing + optional OpenTelemetry export |

---

## 2. Assumptions and Constraints

### 2.1 Explicit Assumptions

| # | Assumption | Impact if Wrong |
|---|---|---|
| A1 | OpenAI Agents SDK version ≥ 0.14.0 (confirms `needs_approval` on `Agent.as_tool`, `RunState`, `EncryptedSession`) | HITL and session patterns must be re-scoped |
| A2 | Claude (Anthropic) accessed via `LitellmModel(model="claude-opus-4-5")` or equivalent through LiteLLM; API key set via `ANTHROPIC_API_KEY` env var | Change model string in config if naming differs |
| A3 | Tavily API has distinct endpoints for weather and news search, returning JSON with a `location` or `query` echo field | Normalization layer must be adjusted to actual response schema |
| A4 | SQLAlchemy 2.x ORM is used; database is SQLite for development, PostgreSQL for production | Migration scripts and connection strings differ |
| A5 | Vector store is ChromaDB (local, serverless) for MVP; can be swapped to Pinecone/Weaviate in Phase 2 | Embedding client and collection management code changes |
| A6 | Embeddings use OpenAI `text-embedding-3-small` for MVP (cost-efficient); can be switched to Voyage AI or Cohere | Embedding dimension must match across store operations |
| A7 | "Office location" in the employee DB is a plain English city/country string, not a geocode | Semantic matching layer is mandatory |
| A8 | Human approvers interact via a CLI prompt or thin web UI; no production UI is in scope | HITL surface must be extended for production |
| A9 | The `SQLAlchemySession` backend available in the SDK is used for conversational memory | If session IDs are not namespaced, multi-user isolation requires custom wrapper |
| A10 | Tavily weather results should be considered fresh for **≤ 2 hours**; news for **≤ 24 hours** | Freshness TTLs are configurable constants |

### 2.2 Hard Constraints

- **No hallucination tolerance.** If no grounded evidence exists, the system must refuse and explain.
- **Separation of read vs. destructive operations.** All DB writes, re-indexing, and schema changes require HITL approval.
- **Model switching must not require agent code changes.** Model identity is injected via a `ModelConfig` dataclass.
- **All LLM calls must be traced.** `RunConfig.tracing_disabled` must never be `True` in production.
- **PII in employee records must never be logged to traces.** `RunConfig.trace_include_sensitive_data = False` is mandatory.

### 2.3 Out of Scope (MVP)

- Multi-tenant authentication and row-level security
- Real employee data (mock data only)
- Voice interface
- Fine-tuning or distillation pipelines
- Production UI (CLI or notebook interface assumed)

---

## 3. SDK-Native vs. Custom Implementation Matrix

This is the single most important grounding artifact in the plan. Every capability is
classified as: **Native** (SDK provides it out of the box), **Partial** (SDK provides
scaffolding; integration code required), or **Custom** (must be built on top of SDK).

| Capability | SDK Support Level | SDK Primitive / Method | Notes |
|---|---|---|---|
| Agent definition with instructions + tools | **Native** | `Agent(name, instructions, tools)` | |
| Structured output from agent | **Native** | `Agent(output_type=PydanticModel)` | |
| Dynamic instructions (runtime context injection) | **Native** | `instructions=callable(ctx, agent)` | Function receives `RunContextWrapper` |
| Runner (sync / async / streamed) | **Native** | `Runner.run()`, `Runner.run_sync()`, `Runner.run_streamed()` | |
| Function tools with auto-schema | **Native** | `@function_tool` decorator | |
| Tool-level HITL approval | **Native** | `function_tool(..., needs_approval=True/callable)` | |
| Agent-as-tool | **Native** | `Agent.as_tool(tool_name, description)` | Returns a function tool wrapping a full agent run |
| HITL on `Agent.as_tool` | **Native** | `Agent.as_tool(..., needs_approval=...)` | Interruption surfaces on outer `RunResult` |
| Pause / resume run flow | **Native** | `result.to_state()` → `state.approve/reject()` → `Runner.run(agent, state)` | |
| Handoffs between agents | **Native** | `handoff(agent, ...)` or `Agent(handoffs=[...])` | Represented as LLM tools |
| Handoff input filter | **Native** | `handoff(agent, input_filter=callable)` | Allows message history transformation before handoff |
| Handoff callback | **Native** | `handoff(agent, on_handoff=callable)` | Side effects on handoff trigger |
| Input guardrails | **Native** | `Agent(input_guardrails=[...])` | Runs on first agent only |
| Output guardrails | **Native** | `Agent(output_guardrails=[...])` | Runs on final output agent only |
| Tool-level guardrails | **Native** | Guardrail attached to `function_tool` | Does not apply to handoff calls |
| Guardrail parallel vs. blocking mode | **Native** | `run_in_parallel=True/False` | |
| Session / conversational memory | **Native** | `SQLiteSession`, `SQLAlchemySession`, `RedisSession`, `OpenAIConversationsSession`, `EncryptedSession` | Pass `session=` to `Runner.run()` |
| Session serialization / persistence | **Native** | `state.to_json()` / `RunState.from_json()` | |
| Run-level tracing | **Native** | Auto-wrapped in `trace()` for every `Runner.run()` | |
| Trace grouping across turns | **Native** | `RunConfig(trace_group_id=session_id)` | Links all turns of a conversation |
| Sensitive data exclusion from traces | **Native** | `RunConfig(trace_include_sensitive_data=False)` | **Mandatory for employee PII** |
| External trace export | **Partial** | `BackendSpanExporter` to OpenAI dashboard natively; custom `SpanExporter` for OTEL | Custom OTEL exporter requires wrapper |
| Claude as primary LLM | **Native (via extension)** | `LitellmModel(model="claude-opus-4-5")` via `openai-agents[litellm]` | SDK auto-handles Claude message ordering |
| Provider-level abstraction / hot-swap | **Partial** | `RunConfig(model_provider=LitellmProvider())` | Config wrapper to switch providers without changing agent code is custom |
| Vector store (ChromaDB) integration | **Custom** | No native ChromaDB binding | Custom `VectorStoreClient` tool required |
| RAG pipeline (embed → chunk → retrieve) | **Custom** | No native RAG primitives | Must build chunking, embedding, retrieval tools |
| Tavily API integration | **Custom** | No native Tavily binding | Custom `function_tool` wrapping `tavily-python` |
| SQLAlchemy query tools | **Custom** | No native ORM agent binding | Custom `function_tool` wrapping safe ORM queries |
| Semantic location matching | **Custom** | No native geo/NLP matching | Custom matcher using embeddings + fuzzy string |
| Retrieval provenance / citation tracking | **Custom** | No native citation primitive | Custom `ProvenanceMetadata` Pydantic model injected into agent outputs |
| Confidence scoring | **Custom** | No native confidence primitive | Computed in Grounding Critic agent output |
| Long-term memory (beyond session) | **Custom** | `AdvancedSQLiteSession` provides branching/analytics; persistent user preferences require custom layer | |
| Freshness TTL enforcement for Tavily results | **Custom** | No native TTL primitive | Enforced in retrieval tool logic |
| Conflict resolution (SQL vs. retrieved data) | **Custom** | No native conflict resolution | Grounding Critic agent responsibility |
| Audit trail for HITL decisions | **Custom** | `RunState` stores sticky decisions; persistent audit log requires custom DB insert | |

**Summary counts:**

- **Native:** 19 capabilities
- **Partial (SDK scaffolding + integration code):** 3 capabilities
- **Custom (built on top of SDK):** 13 capabilities

---

## 4. Proposed Multi-Agent Architecture

### 4.1 Agent Count Justification

After applying the **anti-over-agentization principle** (only create an agent when it
requires its own LLM reasoning loop, stateful behavior, or exclusive tool access), ARIA
uses **6 agents**:

| # | Agent Name | Role Category | Justification for Existence |
|---|---|---|---|
| 1 | **ARIA Orchestrator** | Orchestrator | Single entry point; routes all user intents; owns session and HITL flow |
| 2 | **Employee Intelligence Agent** | Specialist | Owns exclusive ORM access; translates NL → safe SQL; isolates DB concerns |
| 3 | **Weather & News Agent** | Specialist | Owns Tavily API calls and live retrieval; manages freshness policy |
| 4 | **RAG Retrieval Agent** | Specialist | Owns vector store; serves historical/cached knowledge; manages embedding ops |
| 5 | **Semantic Location Resolver** | Utility / as_tool | Bridges employee locations to weather data locations; contains geo-NLP logic |
| 6 | **Grounding Critic** | Validator | Validates final answer against retrieved evidence; issues confidence score; triggers refusals |

**Why not more agents?**
- A separate "News Agent" and "Weather Agent" would be redundant — both call Tavily and apply the same freshness policy. One agent with two tools suffices.
- A "Query Planning Agent" was considered but rejected — the Orchestrator's dynamic instructions handle query decomposition adequately without a dedicated LLM loop.
- A "PII Scrubbing Agent" was considered but rejected — a guardrail (not an agent) is the correct primitive for input/output filtering.

**Why not fewer agents?**
- Merging Employee Intelligence Agent with the Orchestrator would couple ORM access to the routing layer — violating separation of concerns and making DB-side HITL impossible to scope cleanly.
- Merging the Grounding Critic into the Orchestrator would mean the same LLM call both produces and validates the answer — defeating the purpose of independent review.

### 4.2 Orchestrator Name

> **ARIA Orchestrator** — contextually named after the system itself.
> Full name: *Agentic Retrieval & Intelligence Architecture Orchestrator*

### 4.3 High-Level Architecture Diagram (Text)

```
User
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ARIA ORCHESTRATOR                           │
│  • Claude claude-opus-4-5 (primary)  • GPT-4o (fallback)       │
│  • Dynamic instructions (session context injected)              │
│  • Input guardrail: scope/safety check (GPT-4o-mini, blocking)  │
│  • Session: SQLAlchemySession (per user, encrypted)             │
│  • HITL manager: pauses run, routes approvals                   │
│  • RunConfig: trace_group_id=session_id, sensitive_data=False   │
└──────────┬──────────────────────────────────────┬───────────────┘
           │ handoff (with input_filter)           │ Agent.as_tool()
           │                                       │
    ┌──────▼──────────┐              ┌─────────────▼──────────────┐
    │  EMPLOYEE        │              │  WEATHER & NEWS AGENT       │
    │  INTELLIGENCE    │              │  • Claude claude-sonnet-4-5 │
    │  AGENT           │              │  • tools: tavily_weather,   │
    │  • Claude        │              │    tavily_news              │
    │    claude-       │              │  • freshness TTL enforced   │
    │    sonnet-4-5    │              │  • output: WeatherResult[]  │
    │  • tools: sql_   │              └─────────────┬──────────────┘
    │    query_tool    │                            │ Agent.as_tool()
    │  • needs_        │              ┌─────────────▼──────────────┐
    │    approval on   │              │  RAG RETRIEVAL AGENT        │
    │    writes        │              │  • GPT-4o-mini              │
    └──────┬───────────┘              │  • tools: embed_and_store,  │
           │ result returned          │    vector_search            │
           │ to Orchestrator          │  • hybrid retrieval logic   │
           │                          └─────────────┬──────────────┘
           │                                        │ results returned
           └──────────────────┬─────────────────────┘
                              │
              ┌───────────────▼───────────────────┐
              │  SEMANTIC LOCATION RESOLVER        │
              │  (Agent.as_tool on Orchestrator)   │
              │  • GPT-4o-mini                     │
              │  • tools: fuzzy_match, geo_norm    │
              │  • output: LocationMatch (typed)   │
              └───────────────┬───────────────────┘
                              │ LocationMatch returned
                              ▼
              ┌───────────────────────────────────┐
              │  GROUNDING CRITIC                  │
              │  (Agent.as_tool on Orchestrator)   │
              │  • GPT-4o (independent reviewer)   │
              │  • receives: draft answer +        │
              │    retrieved evidence bundle       │
              │  • output: CriticReport (typed)    │
              │    { verdict, confidence, issues,  │
              │      citations, refusal_required } │
              └───────────────┬───────────────────┘
                              │
                              ▼
                         Final Answer
                    (with provenance metadata)
                         returned to User
```

### 4.4 Collaboration Pattern Summary

| Agent Pair | Pattern | Justification |
|---|---|---|
| Orchestrator → Employee Intelligence Agent | **Handoff** | Stateful multi-turn DB conversation; owns its own tool loop; needs full agent autonomy |
| Orchestrator → Weather & News Agent | **Agent.as_tool()** | Returns a bounded, typed result; no need to transfer session context; Orchestrator assembles final answer |
| Orchestrator → RAG Retrieval Agent | **Agent.as_tool()** | Same reasoning; retrieval is a bounded function from the Orchestrator's perspective |
| Orchestrator → Semantic Location Resolver | **Agent.as_tool()** | Pure transformation function (location string → LocationMatch); bounded, typed, no side effects |
| Orchestrator → Grounding Critic | **Agent.as_tool()** | Validation is a bounded review function; result informs Orchestrator's final output decision |
| Employee Intelligence Agent → Orchestrator | **Return via handoff** | Returns control after resolving employee data; Orchestrator continues assembly |

### 4.5 Provider Configuration Strategy

All model assignments are centralized in a `ModelConfig` dataclass in `config/model_config.py`.
Agents consume `ModelConfig.get_model(role)` to obtain their `LitellmModel` or `OpenAI` model
instance. Switching Claude to GPT-4o for any agent requires changing **one line in config**, not
agent code. This satisfies the "provider-switching is abstracted" constraint.

```python
# config/model_config.py  (interface sketch — not final code)
@dataclass
class ModelConfig:
    orchestrator_model:    str = "claude-opus-4-5"          # primary
    specialist_model:      str = "claude-sonnet-4-5"        # worker agents
    critic_model:          str = "gpt-4o"                   # independent reviewer
    lightweight_model:     str = "gpt-4o-mini"              # guardrails, resolvers
    fallback_model:        str = "gpt-4o"                   # orchestrator fallback
    provider:              str = "litellm"                  # "litellm" | "openai"
```

---

*End of Batch 1*

---

**Sources consulted:**
- [OpenAI Agents SDK — Main Docs](https://openai.github.io/openai-agents-python/)
- [Agents](https://openai.github.io/openai-agents-python/agents/)
- [Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [Tools](https://openai.github.io/openai-agents-python/tools/)
- [Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)
- [Sessions](https://openai.github.io/openai-agents-python/sessions/)
- [Tracing](https://openai.github.io/openai-agents-python/tracing/)
- [Models / LiteLLM](https://openai.github.io/openai-agents-python/models/litellm/)
