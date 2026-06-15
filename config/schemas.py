"""Pydantic output models for all ARIA agents."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class EmployeeRecord(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    department: str
    job_title: str
    office_location: str
    hire_date: str
    salary_band: str
    manager_id: int | None = None


class EmployeeResult(BaseModel):
    """Structured output from the Employee Intelligence Agent."""
    employees: list[EmployeeRecord] = Field(default_factory=list)
    total_count: int = 0
    query_description: str = ""
    data_source: str = "employees table (SQLite)"
    answer_text: str = ""
    requires_hitl: bool = False
    hitl_reason: str | None = None


class GuardrailDecision(BaseModel):
    """Output from the input guardrail agent."""
    is_safe: bool
    reason: str
    category: str = "safe"  # "safe" | "off_topic" | "harmful" | "pii_risk"


# ── Phase 2: Location & Weather ────────────────────────────────────────────────

class LocationMatch(BaseModel):
    """Output from the Semantic Location Resolver."""
    original: str
    normalized: str
    confidence: float = Field(ge=0.0, le=1.0)
    country: str = ""
    search_query: str = ""  # optimised string to pass to Tavily


class WeatherResult(BaseModel):
    """A single weather result from Tavily."""
    location: str
    query_used: str
    summary: str
    temperature_c: float | None = None
    condition: str = ""          # "rainy", "sunny", "cloudy", "stormy", etc.
    retrieved_at: str = ""       # ISO timestamp
    is_fresh: bool = True
    source_url: str | None = None
    raw_content: str = ""


class NewsItem(BaseModel):
    """A single news article from Tavily."""
    title: str
    summary: str
    url: str
    published_at: str | None = None
    relevance_score: float = 1.0
    source: str = ""


class WeatherNewsBundle(BaseModel):
    """Combined output from the Weather & News Agent."""
    weather: list[WeatherResult] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    locations_queried: list[str] = Field(default_factory=list)
    retrieval_timestamp: str = ""


# ── Phase 3: RAG ──────────────────────────────────────────────────────────────

class RAGDocument(BaseModel):
    """A single document retrieved from the vector store."""
    id: str
    content: str
    metadata: dict = Field(default_factory=dict)
    distance: float | None = None   # cosine distance from query (lower = more similar)
    collection: str = ""


class RAGResult(BaseModel):
    """Output from the RAG Retrieval Agent."""
    documents: list[RAGDocument] = Field(default_factory=list)
    collection: str = ""
    query: str = ""
    total_found: int = 0
    search_type: str = "semantic"   # "semantic" | "keyword" | "hybrid"
    from_cache: bool = False


# ── Phase 4: Grounding Critic ─────────────────────────────────────────────────

class CitationRef(BaseModel):
    """A single evidence citation from the critic."""
    text: str                        # excerpt from evidence that supports the answer
    source: str = ""                 # collection / tool / URL
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)


class CriticVerdict(BaseModel):
    """Output from the Grounding Critic Agent."""
    verdict: str = "GROUNDED"        # "GROUNDED" | "PARTIAL" | "UNGROUNDED"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    citations: list[CitationRef] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)  # list of grounding problems
    critique_summary: str = ""       # one-line explanation


class OrchestratorResponse(BaseModel):
    """Final structured response from the ARIA Orchestrator."""
    answer: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    agents_involved: list[str] = Field(default_factory=list)
    employee_data: EmployeeResult | None = None
    weather_data: WeatherNewsBundle | None = None
    rag_data: RAGResult | None = None
    rag_cache_hit: bool = False
    requires_followup: bool = False
    followup_suggestion: str | None = None
    critic_verdict: CriticVerdict | None = None
