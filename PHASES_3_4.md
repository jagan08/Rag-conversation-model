# ARIA Phases 3 & 4: RAG Retrieval & Grounding Critic

## Overview

Phases 3 and 4 complete the ARIA multi-agent system with intelligent caching and answer verification:

- **Phase 3 (RAG Retrieval)**: Semantic search over a persistent vector store to avoid redundant API calls
- **Phase 4 (Grounding Critic)**: Independent agent that validates answers against evidence before returning to users

## Phase 3: RAG Retrieval (Vector Store)

### Architecture

ARIA uses **sqlite-vec** instead of ChromaDB (which has compatibility issues on Python 3.14+). The vector store is built on:

- **Backend**: SQLite 3.16+ with sqlite-vec extension
- **Embeddings**: OpenAI `text-embedding-3-small` (1536-dimensional)
- **Database**: `aria_vectors.db` (persistent, auto-created)

### Collections

Three collections track different data types:

1. **weather_history** - Past weather lookups
   - Documents: "Location: {loc}. Condition: {cond}. Summary: {info}. Retrieved: {ts}."
   - Metadata: location, condition, retrieved_at, source_url, query
   - TTL: 2 hours (queries older than this are marked stale)

2. **news_history** - Past news articles
   - Documents: "Title: {title}. Summary: {summary}. Topic: {topic}. Location: {loc}. Retrieved: {ts}."
   - Metadata: title, url, topic, location, retrieved_at, published_at
   - TTL: 24 hours

3. **employee_context** - Cached employee query results
   - Documents: Aggregated employee data (count by dept, headcount, etc.)
   - Metadata: query_type, timestamp, filters_applied

### Vector Store API

#### `upsert(collection, content, metadata)`
Store a new document with embeddings.

```python
from db.vector_store import upsert

doc_id = upsert(
    collection="weather_history",
    content="Location: London. Condition: rainy. Summary: ...",
    metadata={"location": "London", "retrieved_at": "2024-01-15T10:00:00Z"}
)
```

#### `search(collection, query, n_results=5)`
Semantic search across a collection.

```python
from db.vector_store import search

results = search(
    collection="weather_history",
    query="Is it raining in London?",
    n_results=5
)
# Returns: [
#   {
#     "id": "weat_20240115100000_abc123",
#     "content": "...",
#     "metadata": {...},
#     "distance": 0.12  # Lower = more similar
#   },
#   ...
# ]
```

#### `list_collections()`
Get document counts per collection.

```python
from db.vector_store import list_collections

cols = list_collections()
# Returns: [
#   {"collection": "weather_history", "document_count": 42},
#   {"collection": "news_history", "document_count": 18},
#   {"collection": "employee_context", "document_count": 5}
# ]
```

#### `get_all_documents(collection, limit=100)`
Retrieve raw documents from a collection (for UI exploration).

```python
from db.vector_store import get_all_documents

docs = get_all_documents("weather_history", limit=20)
```

### Agent Integration

**RAG Retrieval Agent** (`aria_agents/rag_retrieval.py`):
- Always called FIRST before live Tavily searches
- Searches relevant collection based on query type
- Returns cache hits with timestamps and similarity distance
- Auto-stores new results for future reuse

**Workflow**:
1. Orchestrator receives weather/news query
2. Calls `rag_agent.as_tool(search_rag_cache)`
3. RAG agent searches weather_history or news_history
4. If distance < 0.3 (strong hit) AND fresh (within TTL): return cached result
5. If distance 0.3-0.6 (partial) or stale: recommend live search
6. If distance > 0.6 or empty: "Cache miss"

### Storage Behavior

- **Auto-storage**: Weather and news tools automatically store results to RAG on retrieval
- **Non-blocking**: Failures in storage don't break the main flow
- **TTL-aware**: Timestamps in metadata enable stale detection

### Distance Interpretation

Semantic similarity in sqlite-vec uses cosine distance (0 to 2, where 0 = identical):

- `distance < 0.3`: Strong cache hit (same location/topic)
- `0.3 ≤ distance ≤ 0.6`: Partial hit (related but not exact)
- `distance > 0.6`: Weak match (consider cache miss)

---

## Phase 4: Grounding Critic

### Purpose

The **Grounding Critic** is an independent verification agent that:
- Validates every factual claim in ARIA's proposed answer against evidence
- Rates answers on a 3-level severity scale
- Extracts supporting citations with relevance scores
- Flags common grounding problems (extrapolation, stale data, missing sources)

### Verdict Levels

#### GROUNDED (Confidence ≥ 0.80)
- Every key claim is directly supported by evidence
- No extrapolation, inference, or assumptions
- Proper citations included
- Example: "Employee ID 123 works in Engineering" (answer cites employee ID from DB)

#### PARTIAL (Confidence 0.40-0.79)
- Some claims supported, others extrapolated or inferred
- Weather/news older than TTL marked as PARTIAL even if cached
- Reasonable inference but not directly stated
- Example: "London will likely have similar weather tomorrow" (today's data extrapolated)

#### UNGROUNDED (Confidence < 0.40)
- No meaningful evidence supports the claim
- Answer contradicts evidence
- Critical gaps in evidence chain
- Example: "There are 500 employees in the Marketing department" (no such data provided)

### Critic Output Format

```
VERDICT: GROUNDED|PARTIAL|UNGROUNDED
CONFIDENCE: 0.00 to 1.00
CITATIONS:
- "<exact quote from evidence>" (source: tool_name or collection_name)
- (add more as needed, or "- none" if UNGROUNDED)
ISSUES:
- <specific grounding problem, or "- none" if GROUNDED>
SUMMARY: <one sentence explaining the verdict>
```

### Example Verdict

```
VERDICT: PARTIAL
CONFIDENCE: 0.65
CITATIONS:
- "Currently sunny with a high of 72°F" (source: weather_api)
- "London office" (source: employees table)
ISSUES:
- Weather data is 2.5 hours old (exceeds 2h TTL)
- No forecast data for tomorrow provided
SUMMARY: Current conditions grounded but forecast extrapolated.
```

### API: run_critic()

```python
from aria_agents.grounding_critic import run_critic
import asyncio

async def main():
    verdict = await run_critic(
        user_query="How many engineers are in London?",
        proposed_answer="We have 5 engineers in the London office based on recent records.",
        evidence_docs=[
            "[1] Employee ID 101: London, Engineering",
            "[2] Employee ID 102: London, Engineering",
            "[3] Employee ID 103: London, Engineering",
            "[4] Employee ID 104: London, Engineering",
            "[5] Employee ID 105: London, Engineering",
        ]
    )
    
    print(f"Verdict: {verdict['verdict']}")
    print(f"Confidence: {verdict['confidence']}")
    for citation in verdict['citations']:
        print(f"  - {citation['text']} (source: {citation['source']})")

asyncio.run(main())
```

### Internal Parsing

The critic output is parsed into a structured dict by `_parse_verdict_text()`:

```python
{
    "verdict": "GROUNDED",
    "confidence": 0.85,
    "citations": [
        {"text": "quote", "source": "tool_name", "relevance": 1.0},
        ...
    ],
    "issues": ["issue1", "issue2"],
    "critique_summary": "One sentence explanation"
}
```

### Grounding Rules

1. **Employee Data**: Grounded if answer cites specific IDs/counts from query results
2. **Weather/News**: Grounded if fresh; PARTIAL if stale (> TTL); UNGROUNDED if no evidence
3. **Honest Refusals**: GROUNDED if answer says "I don't know" or refuses to answer
4. **Extrapolation**: PARTIAL if answer infers beyond evidence (e.g., forecast from current data)
5. **Contradictions**: UNGROUNDED if answer contradicts provided evidence

---

## Integration with Orchestrator

### Example Flow

```
User: "What's the weather in San Francisco and how many employees are there?"

Orchestrator:
  1. Call search_rag_cache("weather in San Francisco")
     → Cache hit! Distance 0.15, retrieved 1 hour ago → FRESH
  2. Return: "From memory: Sunny, 72°F (Retrieved 2024-01-15T09:00:00Z)"
  3. Call get_employee_by_id(search for SF location)
     → Found 3 employees
  4. Return: "3 employees in our San Francisco office"

Proposed Answer:
  "San Francisco has sunny weather at 72°F with favorable conditions.
   We have 3 employees based in our San Francisco office."

Run Critic:
  → GROUNDED (0.92 confidence)
  - Weather from cached source (1h old, within TTL)
  - Employee count directly from DB query
  - No extrapolation, no contradictions
```

### When Critic Runs

The orchestrator calls the critic in these scenarios:

1. **Multi-source answers** (mixing employee + weather + news)
2. **High-stakes queries** (location changes, sensitive data)
3. **Cached data** (verify age/staleness before returning)
4. **User-requested verification** ("Is this accurate?")

---

## Storage Schema

### Documents Table (sqlite)

```sql
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,           -- "weat_20240115100000_abc123"
    collection  TEXT NOT NULL,              -- "weather_history"
    content     TEXT NOT NULL,              -- Full document text
    metadata    TEXT NOT NULL DEFAULT '{}', -- JSON metadata
    created_at  TEXT NOT NULL               -- ISO timestamp
);
```

### Vector Tables (sqlite-vec virtual)

```sql
CREATE VIRTUAL TABLE vec_weather_history
USING vec0(embedding float[1536]);

CREATE VIRTUAL TABLE vec_news_history
USING vec0(embedding float[1536]);

CREATE VIRTUAL TABLE vec_employee_context
USING vec0(embedding float[1536]);
```

---

## Performance Characteristics

### Vector Search Speed

- **First query** (~2s): Embedding API calls + search
- **Subsequent queries** (~0.3s): Cached embeddings + search
- **Large collections** (1000+ docs): Still <0.5s with proper indexing

### Memory Usage

- `aria_vectors.db` grows ~2KB per stored document (with metadata)
- 500 documents ≈ 1MB database file
- Embeddings stored as binary (6KB each)

### TTL Impact

- **Weather**: Queries older than 2h autochecked by critic
- **News**: Queries older than 24h autochecked by critic
- **Stale data**: Marked PARTIAL, recommendation: run fresh query

---

## Troubleshooting

### Vector Search Returns Empty

1. Check collection name is valid: `weather_history`, `news_history`, `employee_context`
2. Verify embeddings API key: `OPENAI_API_KEY` must be set
3. Check document count: `list_collections()` should show > 0 docs
4. Test embedding: Try `_embed(["test"])` directly

### Critic Never Runs

Verify critic is called in orchestrator logic. By default, it runs on multi-source answers.

### Stale Data Not Marked PARTIAL

Ensure metadata includes `retrieved_at` field with ISO timestamp. Critic regex parses this to check TTL.

### sqlite-vec Extension Missing

```bash
pip install sqlite-vec
# Or if using older sqlite3:
sqlite3 :memory: "SELECT load_extension('sqlite_vec')"
```

---

## Future Enhancements

1. **Batch Embedding**: Process multiple documents concurrently
2. **Hybrid Search**: Combine semantic + keyword search
3. **Collection Pruning**: Auto-delete docs older than 30 days
4. **UI Explorer**: Dashboard to browse vector store
5. **Critic Feedback Loop**: User marks verdicts right/wrong for training

---

## Files

| File | Purpose |
|------|---------|
| `db/vector_store.py` | Core vector store API (upsert, search, list) |
| `tools/vector_store.py` | @function_tool wrappers for agents |
| `aria_agents/rag_retrieval.py` | RAG Retrieval Agent (searches before live APIs) |
| `aria_agents/grounding_critic.py` | Grounding Critic Agent + verdict parsing |
| `aria_vectors.db` | Persistent vector database (auto-created) |

---

## Summary

**Phase 3 + 4 enable ARIA to**:
- 🚀 Avoid redundant API calls (cache hits save 95%+ latency)
- 🔍 Search historical context semantically (find related queries automatically)
- ✅ Verify answers with independent critic before surfacing to users
- 📊 Track answer confidence and grounding with structured verdicts
- 💾 Persist knowledge across sessions for continuous improvement
