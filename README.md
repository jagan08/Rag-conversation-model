# ARIA — Agentic Retrieval & Intelligence Architecture

A sophisticated multi-agent AI system that orchestrates specialized AI agents to retrieve information, analyze employee data, fetch real-time news and weather, and provide intelligent insights through a user-friendly web interface.

## Overview

ARIA is built on the **OpenAI Agents SDK** with **Claude models** (via LiteLLM) as the primary intelligence layer. The system features a **Streamlit-based dashboard** with multi-page support, SQLite employee database, sqlite-vec vector retrieval for semantic search, grounding critic for answer verification, and human-in-the-loop approval workflows for sensitive operations.

## Architecture

### Multi-Agent System

- **Orchestrator** (Claude Opus) — Main decision-maker with guardrails and agent handoff logic
- **Employee Intelligence Agent** (Claude Sonnet) — SQL-based employee data retrieval and analysis
- **Weather & News Agent** (Claude Sonnet) — Real-time weather and news data via Tavily API
- **Location Resolver** (GPT-4o-mini) — Location normalization and batch processing
- **RAG Retrieval Agent** (Claude Haiku) — Semantic search over cached weather, news, and employee queries
- **Grounding Critic** (GPT-4o) — Independent verification of answers against evidence

### Tech Stack

- **Framework:** Streamlit (multi-page UI)
- **LLM:** Claude (Opus/Sonnet/Haiku via LiteLLM), OpenAI models (GPT-4o, GPT-4o-mini)
- **Database:** SQLite + SQLAlchemy ORM (employees table, 500 seed records)
- **Vector Store:** sqlite-vec (semantic search with OpenAI text-embedding-3-small)
- **APIs:** Tavily (weather & news with 2h/24h TTL caching)
- **Agent SDK:** OpenAI Agents v0.17.4
- **Testing:** pytest 9.1.0, pytest-asyncio 1.4.0

## Project Structure

```
.
├── app/
│   ├── main.py                 # Streamlit entry point
│   ├── pages/                  # 5-page dashboard
│   │   ├── 01_Chat.py
│   │   ├── 02_Employees.py
│   │   ├── 03_Traces.py
│   │   ├── 04_HITL_Queue.py
│   │   └── 05_Config.py
│   └── components/             # Reusable UI components
│       ├── hitl_modal.py
│       ├── provenance_card.py
│       ├── agent_trace.py
│       └── weather_card.py
├── aria_agents/                # Agent definitions
│   ├── orchestrator.py         # Main orchestrator with guardrails & handoffs
│   ├── employee_intelligence.py # Employee data queries
│   ├── weather_news.py         # Weather & news via Tavily
│   ├── location_resolver.py    # Location normalization
│   ├── rag_retrieval.py        # RAG semantic search (Phase 3)
│   └── grounding_critic.py     # Answer verification (Phase 4)
├── tools/                      # Agent function tools
│   ├── sql_query.py            # Employee search/update/aggregate
│   ├── tavily_weather.py       # Weather retrieval (2h TTL cache)
│   ├── tavily_news.py          # News retrieval (24h TTL cache)
│   ├── location_matcher.py     # Location normalization
│   └── vector_store.py         # @function_tool wrappers for RAG
├── config/                     # Configuration
│   ├── model_config.py         # Model selection & API setup
│   └── schemas.py              # Pydantic models (employees, weather, news, verdicts)
├── db/                         # Database & vector store layer
│   ├── models.py               # SQLAlchemy ORM (Employee model)
│   ├── session_store.py        # SQLite session persistence
│   ├── vector_store.py         # sqlite-vec API (upsert, search, list)
│   ├── aria.db                 # Employee database (500 records)
│   └── aria_vectors.db         # Vector store DB (weather/news/employee cache)
├── tests/                      # Unit tests
│   ├── conftest.py             # Shared fixtures (DB, mocks, responses)
│   ├── pytest.ini              # Pytest configuration
│   ├── test_config/
│   │   └── test_schemas.py     # 31 passing schema validation tests
│   └── test_tools/
│       ├── test_sql_query.py   # 40 SQL query tests
│       ├── test_location_matcher.py # 16 location tests
│       ├── test_tavily_weather.py # 11 weather API tests
│       └── test_tavily_news.py # 12 news API tests
├── .streamlit/
│   └── config.toml             # Streamlit theme config
├── pyproject.toml              # Project metadata & dependencies
└── README.md                   # This file
```

## Installation

### Prerequisites
- Python 3.11+
- GitHub account with personal access token
- API keys: OpenAI, Anthropic, Tavily

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jagan08/Rag-conversation-model.git
   cd Rag-conversation-model
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables:**
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=sk_...
   ANTHROPIC_API_KEY=sk-ant-...
   TAVILY_API_KEY=tvly_...
   ```

5. **Initialize database (if needed):**
   ```bash
   python db/models.py
   ```

## Running the Application

Start the Streamlit app:
```bash
python -m streamlit run app/main.py
```

The app will be available at `http://localhost:8501`

## Features

### Dashboard Pages

1. **Chat** — Conversational interface with ARIA orchestrator
2. **Employees** — Search, filter, and view employee data with approval workflows
3. **Traces** — View detailed agent execution logs and decision chains
4. **HITL Queue** — Human-in-the-loop approval for sensitive operations
5. **Config** — System configuration and model selection

### Key Capabilities

- **Intelligent Routing** — Orchestrator determines which agent handles each task
- **Data Privacy** — Approval workflows for sensitive employee data modifications
- **Caching** — Weather (2h) and news (24h) to minimize API calls
- **Audit Trail** — Complete tracing of agent decisions and tool usage
- **Multi-Model Support** — Switch between Claude and OpenAI models via configuration

## Phase Status

- ✅ Phase 0: Core architecture
- ✅ Phase 1: Agent implementation
- ✅ Phase 2: UI & tool integration
- ✅ Phase 3: RAG retrieval (sqlite-vec integration)
- ✅ Phase 4: Grounding critic & refinement

### Completed Phases Overview

**Phase 3: RAG Retrieval (sqlite-vec)** — Vector store for semantic search over historical weather, news, and employee queries
- Collection management: weather_history, news_history, employee_context
- Embedding pipeline via OpenAI text-embedding-3-small
- Semantic similarity search with distance scoring
- Auto-store results from live APIs for future reuse

**Phase 4: Grounding Critic** — Independent verification agent that validates answers against evidence
- Verdict levels: GROUNDED (≥0.80), PARTIAL (0.40-0.79), UNGROUNDED (<0.40)
- Citation extraction and relevance scoring
- TTL-aware validation (stale weather/news flagged as PARTIAL)
- Structured output parsing with regex extraction

## Testing

### Unit Tests (94 test cases)
```bash
# Run all tests
pytest tests/ -v

# Run schema tests only (all passing)
pytest tests/test_config/test_schemas.py -v

# Run with coverage
pytest tests/ --cov=config --cov=tools --cov-report=html
```

**Test Coverage**:
- ✅ **Config schemas**: 31/31 passing (EmployeeRecord, WeatherResult, CriticVerdict, etc.)
- ✅ **SQL queries**: 40 test cases (search, aggregate, update, edge cases)
- ✅ **Location matching**: 16 test cases (exact/fuzzy/fallback normalization)
- ✅ **Weather API**: 11 test cases (retrieval, caching, TTL, error handling)
- ✅ **News API**: 12 test cases (retrieval, caching, article structure)

See [TESTING.md](TESTING.md) for detailed testing guide with fixtures and patterns.

## Development

### Code Quality
```bash
ruff check .
mypy .
```

### Database & Vector Store
- **Employee DB**: SQLite with 500 seed records, all queries logged
- **Vector Store**: sqlite-vec with 3 collections (weather_history, news_history, employee_context)
- **Sensitive Updates**: Human approval via HITL queue
- **TTL Caching**: Weather (2h), News (24h) with auto-freshness validation

## Dependencies

See `pyproject.toml` for full list. Key packages:
- `streamlit>=1.46.0` — Web UI framework
- `sqlalchemy>=2.0.0` — Database ORM
- `sqlite-vec` — Vector storage for semantic search
- `openai-agents>=0.0.14` — Agent orchestration SDK
- `litellm>=1.50.0` — Multi-model LLM gateway (Claude + OpenAI)
- `tavily-python>=0.5.0` — Web search & weather API
- `anthropic>=0.40.0` — Claude API client
- `openai>=1.50.0` — OpenAI API client
- `pydantic>=2.0.0` — Data validation
- `pytest>=8.0.0` — Testing framework
- `pytest-asyncio>=0.23.0` — Async test support

**Dev Dependencies**:
```bash
pip install -e ".[dev]"  # Installs pytest, mypy, ruff
```

## Documentation

- **[TESTING.md](TESTING.md)** — Comprehensive testing guide with fixtures, patterns, and examples
- **[PHASES_3_4.md](PHASES_3_4.md)** — Detailed Phase 3 (RAG/sqlite-vec) and Phase 4 (Grounding Critic) architecture

## Key Features Explained

### 🔍 RAG Retrieval (Phase 3)
- Semantic search over historical weather, news, and employee queries
- Three collections with TTL-based freshness (weather: 2h, news: 24h)
- Auto-storage: New weather/news results cached automatically
- Distance scoring: Matches below 0.3 are strong hits, 0.3-0.6 partial, >0.6 misses
- Reduces redundant API calls and latency

### ✅ Grounding Critic (Phase 4)
- Independent verification agent validates answers against evidence
- Three verdict levels:
  - **GROUNDED** (≥0.80): Full evidence support
  - **PARTIAL** (0.40-0.79): Partial support + extrapolation
  - **UNGROUNDED** (<0.40): No evidence or contradictions
- Citation extraction with relevance scores
- TTL-aware: Flags stale weather/news as PARTIAL

### 📋 Unit Testing
- 94 test cases with full mocking of external APIs
- In-memory SQLite for test isolation
- Comprehensive fixtures for employees, mocks, and responses
- Fast, deterministic, ready for CI/CD

## Example Workflow

```
User: "What's the weather in San Francisco and how many employees work there?"

ARIA Orchestrator:
  1. Search RAG cache for "weather in San Francisco"
     → Hit! Distance 0.15, cached 1h ago (fresh)
  2. Return cached: "Sunny, 72°F (From memory, retrieved 1h ago)"
  3. Query employees: Find SF location → 3 employees
  4. Run critic: GROUNDED (0.92 confidence)
     - Weather from cache (within TTL)
     - Employee count from DB (direct match)
     - No extrapolation or contradictions
  5. Return answer to user with confidence score
```

## Troubleshooting

### Missing OPENAI_API_KEY
Vector store needs OpenAI embeddings. Set in `.env`:
```bash
OPENAI_API_KEY=sk_...
```

### Tests Failing
Ensure dependencies installed:
```bash
pip install -e ".[dev]"
```

### Streamlit Won't Start
Check port 8501 is available or set custom port:
```bash
streamlit run app/main.py --server.port 8080
```

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and write/run tests: `pytest tests/ -v`
3. Commit with clear message: `git commit -m "Add feature description"`
4. Push to GitHub: `git push origin feature/my-feature`
5. Open a pull request with description

## License

MIT

## Support

For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/jagan08/Rag-conversation-model/issues).

---

**Project Status**: ✅ Feature-complete through Phase 4 (all phases: core, agents, UI, RAG, critic)

Built with ❤️ using Claude, OpenAI, and the OpenAI Agents SDK.

**Last Updated**: 2026-06-15 | **Version**: 0.1.0
