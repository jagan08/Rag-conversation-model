# ARIA — Agentic Retrieval & Intelligence Architecture

A sophisticated multi-agent AI system that orchestrates specialized AI agents to retrieve information, analyze employee data, fetch real-time news and weather, and provide intelligent insights through a user-friendly web interface.

## Overview

ARIA is built on the **OpenAI Agents SDK** with **Claude models** (via LiteLLM) as the primary intelligence layer. The system features a **Streamlit-based dashboard** with multi-page support, SQLite employee database, ChromaDB vector retrieval, and human-in-the-loop approval workflows for sensitive operations.

## Architecture

### Multi-Agent System

- **Orchestrator** (Claude Opus) — Main decision-maker with guardrails and agent handoff logic
- **Employee Intelligence Agent** (Claude Sonnet) — SQL-based employee data retrieval and analysis
- **Weather & News Agent** (Claude Sonnet) — Real-time weather and news data via Tavily API
- **Location Resolver** (GPT-4o-mini) — Location normalization and batch processing

### Tech Stack

- **Framework:** Streamlit (multi-page UI)
- **LLM:** Claude (Opus/Sonnet via LiteLLM), OpenAI models
- **Database:** SQLite + SQLAlchemy ORM
- **Vector Store:** ChromaDB
- **APIs:** Tavily (weather, news)
- **Agent SDK:** OpenAI Agents v0.17.4

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
│   ├── orchestrator.py
│   ├── employee_intelligence.py
│   ├── weather_news.py
│   ├── location_resolver.py
│   ├── rag_retrieval.py
│   └── grounding_critic.py
├── tools/                      # Agent tools
│   ├── sql_query.py            # Employee search/update
│   ├── tavily_weather.py       # Weather retrieval (2h cache)
│   ├── tavily_news.py          # News retrieval (24h cache)
│   └── location_matcher.py     # Location normalization
├── config/                     # Configuration
│   ├── model_config.py         # Model settings
│   └── schemas.py              # Pydantic models
├── db/                         # Database layer
│   ├── models.py               # SQLAlchemy ORM
│   ├── session_store.py        # SQLite session persistence
│   └── aria.db                 # Employee database (500 records)
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

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
ruff check .
mypy .
```

### Database Queries
- Employee search uses SQL + semantic matching
- Sensitive updates require human approval
- All queries logged for audit purposes

## Dependencies

See `pyproject.toml` for full list. Key packages:
- `streamlit` — Web UI
- `sqlalchemy` — Database ORM
- `chromadb` — Vector storage
- `openai-agents` — Agent SDK
- `litellm` — Multi-model LLM gateway
- `tavily-python` — Web search & weather
- `anthropic` — Claude API
- `pydantic` — Data validation

## Contributing

1. Create a feature branch
2. Make changes and run tests
3. Submit a pull request

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.

---

Built with ❤️ using Claude, OpenAI, and the OpenAI Agents SDK.
