"""ARIA Chat Interface — real agent execution with streaming."""
import os
for _v in ("ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","OPENROUTER_API_KEY"):
    os.environ.pop(_v, None)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import asyncio
import uuid
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from app.style import inject
from app.components.hitl_modal import hitl_status_badge
from app.components.provenance_card import render_provenance, Citation
from app.components.agent_trace import render_trace_timeline, TraceEvent
from app.components.grounding_badge import render_grounding_badge, render_grounding_detail

st.set_page_config(
    page_title="ARIA · Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject()

# ── Session state init ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "trace_events" not in st.session_state:
    st.session_state.trace_events = []
if "hitl_pending" not in st.session_state:
    st.session_state.hitl_pending = False
if "hitl_queue" not in st.session_state:
    st.session_state.hitl_queue = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"aria-{uuid.uuid4().hex[:8]}"
if "agents_ready" not in st.session_state:
    st.session_state.agents_ready = False


# ── API key check ──────────────────────────────────────────────────────────────
def _has_anthropic_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key and not key.endswith("...") and len(key) > 10)

def _has_openai_key() -> bool:
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key and not key.endswith("...") and len(key) > 10)


# ── Run agent (async helper) ───────────────────────────────────────────────────
async def _run_agent(prompt: str, session_id: str) -> dict:
    """Run the ARIA orchestrator and return result dict."""
    import traceback
    from agents import Runner, RunConfig
    from agents.stream_events import RawResponsesStreamEvent, RunItemStreamEvent, AgentUpdatedStreamEvent
    from agents.items import MessageOutputItem, ToolCallItem, ToolCallOutputItem, HandoffCallItem, HandoffOutputItem
    from db.session_store import get_session as get_sdk_session
    from aria_agents.orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    sdk_session = get_sdk_session(session_id)

    run_config = RunConfig(
        workflow_name="ARIA Chat",
        group_id=session_id,
        trace_include_sensitive_data=False,
    )

    events_accumulated = []
    final_text = ""
    agents_involved = []
    error_msg = None

    try:
        result = Runner.run_streamed(
            orchestrator,
            input=prompt,
            session=sdk_session,
            run_config=run_config,
            max_turns=10,
        )

        async for event in result.stream_events():
            ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"

            if isinstance(event, AgentUpdatedStreamEvent):
                agent_name = event.new_agent.name
                if agent_name not in agents_involved:
                    agents_involved.append(agent_name)
                events_accumulated.append({
                    "agent": agent_name,
                    "event_type": "handoff",
                    "detail": f"Agent activated: {agent_name}",
                    "timestamp": ts,
                    "status": "ok",
                })

            elif isinstance(event, RunItemStreamEvent):
                item = event.item
                if hasattr(item, "raw_item"):
                    raw = item.raw_item
                    # Tool call
                    if hasattr(raw, "name") and hasattr(raw, "arguments"):
                        events_accumulated.append({
                            "agent": agents_involved[-1] if agents_involved else "ARIA",
                            "event_type": "tool_call",
                            "detail": f"Tool: {raw.name}",
                            "timestamp": ts,
                            "status": "ok",
                        })
                    # Tool output / text
                    elif hasattr(raw, "content") and isinstance(raw.content, list):
                        for block in raw.content:
                            if hasattr(block, "text") and block.text:
                                final_text = block.text

            elif isinstance(event, RawResponsesStreamEvent):
                # Capture streaming text deltas
                e = event.data
                if hasattr(e, "type"):
                    if e.type == "response.output_text.delta":
                        final_text += getattr(e, "delta", "")
                    elif e.type == "response.completed":
                        pass

        # Fallback: use final_output from result if streaming didn't build text
        if not final_text.strip():
            final_text = getattr(result, "final_output", "") or ""
            if not final_text:
                # Try accessing via last response
                try:
                    final_text = str(result.final_output) if result.final_output else "(No response generated)"
                except Exception:
                    final_text = "(No response generated)"

    except Exception as exc:
        tb = traceback.format_exc()
        error_msg = str(exc)
        events_accumulated.append({
            "agent": "ARIA Orchestrator",
            "event_type": "guardrail",
            "detail": f"Error: {error_msg[:120]}",
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "status": "error",
        })

    # ── Phase 4: Grounding Critic ─────────────────────────────────────────────
    critic_verdict = None
    if final_text.strip() and not error_msg:
        try:
            from aria_agents.grounding_critic import run_critic
            # Build evidence list from trace tool outputs captured during the run
            evidence_docs = [
                ev["detail"] for ev in events_accumulated
                if ev.get("event_type") == "tool_call"
            ]
            critic_verdict = await run_critic(
                user_query=prompt,
                proposed_answer=final_text,
                evidence_docs=evidence_docs,
            )
            events_accumulated.append({
                "agent": "Grounding Critic",
                "event_type": "critic",
                "detail": (
                    f"Verdict: {critic_verdict['verdict']} "
                    f"(confidence {critic_verdict['confidence']:.0%}) — "
                    f"{critic_verdict.get('critique_summary', '')}"
                ),
                "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "status": (
                    "ok" if critic_verdict["verdict"] == "GROUNDED"
                    else "warning" if critic_verdict["verdict"] == "PARTIAL"
                    else "error"
                ),
            })
        except Exception:
            pass  # Critic failure must never block the answer

    return {
        "final_text": final_text,
        "trace_events": events_accumulated,
        "agents_involved": agents_involved,
        "error": error_msg,
        "critic_verdict": critic_verdict,
    }


def run_agent_sync(prompt: str, session_id: str) -> dict:
    """Run async agent in the sync Streamlit context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
        return loop.run_until_complete(_run_agent(prompt, session_id))
    except RuntimeError:
        return asyncio.run(_run_agent(prompt, session_id))


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html("""
    <div style="font-size:1.3rem;font-weight:700;color:#58a6ff;padding-bottom:4px;">ARIA</div>
    <div style="font-size:0.72rem;color:#8b949e;">Agentic Retrieval & Intelligence Architecture</div>
    """)
    st.divider()

    st.markdown("#### API Status")
    tavily_ok = bool(os.getenv("TAVILY_API_KEY", "").replace("tvly-...", ""))
    for name, ok in [
        ("Anthropic (Claude)", _has_anthropic_key()),
        ("OpenAI (guardrail/RAG)", _has_openai_key()),
        ("Tavily (weather/news)", tavily_ok),
    ]:
        color = "#3fb950" if ok else "#f85149"
        label = "Connected" if ok else "Key missing"
        st.html(f"<span style='color:#8b949e'>{name}:</span> <span style='color:{color};font-weight:600'>{label}</span><br>")

    # RAG cache summary
    st.divider()
    st.markdown("#### RAG Memory")
    try:
        from db.vector_store import list_collections
        for c in list_collections():
            st.html(
                f"<span style='color:#8b949e'>{c['collection'].replace('_',' ')}:</span> "
                f"<span style='color:#58a6ff;font-weight:600'>{c['document_count']} docs</span><br>"
            )
    except Exception:
        st.caption("Vector store not initialised")

    st.divider()
    hitl_status_badge()
    st.divider()

    st.markdown("#### Session")
    st.code(st.session_state.session_id, language=None)
    st.metric("Messages", len(st.session_state.messages))
    st.metric("Trace Events", len(st.session_state.trace_events))

    if st.button("New Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.trace_events = []
        st.session_state.session_id = f"aria-{uuid.uuid4().hex[:8]}"
        st.rerun()

    st.divider()

    with st.expander("Example queries"):
        examples = [
            "How many employees are in Engineering?",
            "Find employees in London",
            "Who has the job title 'Data Scientist'?",
            "Show headcount by department",
            "Find employee with ID 42",
            "What's the weather in Tokyo?",
            "Latest tech news from Berlin",
            "What's the weather where employee ID 1 works?",
            "Which departments have employees in rainy cities?",
            "What weather data do you have in memory?",
            "Search your memory for London weather",
        ]
        for ex in examples:
            if st.button(ex, use_container_width=True, key=f"ex_{ex[:20]}"):
                st.session_state["prefill_prompt"] = ex
                st.rerun()

    st.caption("ARIA v0.1 · Phase 3")

# ── Main layout ────────────────────────────────────────────────────────────────
chat_col, trace_col = st.columns([0.65, 0.35])

with chat_col:
    st.title("ARIA Chat")
    st.caption("*Agentic Retrieval & Intelligence Architecture* · Phase 3: Employee + Weather/News + RAG Memory")

    # HITL banner
    if st.session_state.get("hitl_pending"):
        st.warning("An agent action requires your approval. Go to the **HITL Queue** page.", icon="⚠️")

    # API key warning
    if not _has_anthropic_key():
        st.error(
            "**Anthropic API key not configured.** Add `ANTHROPIC_API_KEY=sk-ant-...` to your `.env` file and restart.",
            icon="🔑",
        )

    # Message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("rag_cache_hit"):
                st.html("<span style='background:#58a6ff22;color:#58a6ff;border:1px solid #58a6ff;border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:600'>From ARIA memory cache</span>")
            if msg.get("critic_verdict"):
                render_grounding_badge(msg["critic_verdict"])
            if msg.get("agents_involved"):
                st.caption(f"Agents: {' → '.join(msg['agents_involved'])}")
            if msg.get("critic_verdict"):
                render_grounding_detail(msg["critic_verdict"])
            if msg.get("citations"):
                render_provenance(
                    [Citation(**c) for c in msg["citations"]],
                    confidence=msg.get("confidence"),
                )

    # Pre-filled prompt from sidebar examples
    prefill = st.session_state.pop("prefill_prompt", None)

    # Chat input
    prompt = st.chat_input("Ask ARIA about employees…") or prefill

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if not _has_anthropic_key():
                response_text = "Cannot run: Anthropic API key is not configured. Please add it to `.env`."
                st.markdown(response_text)
                result = {"final_text": response_text, "trace_events": [], "agents_involved": [], "error": "No API key"}
            else:
                with st.status("ARIA is thinking…", expanded=True) as status_box:
                    st.write(f"Session: `{st.session_state.session_id}`")
                    st.write("Routing to specialist agents…")

                    result = run_agent_sync(prompt, st.session_state.session_id)

                    if result["error"]:
                        status_box.update(label="Error during execution", state="error")
                        st.write(f"Error: {result['error']}")
                    else:
                        agents_str = " → ".join(result["agents_involved"]) if result["agents_involved"] else "ARIA Orchestrator"
                        status_box.update(label=f"Done · {agents_str}", state="complete")

                response_text = result["final_text"] or "*(No response — check API keys and model configuration.)*"
                st.markdown(response_text)

                # Show RAG cache badge
                if "rag cache" in response_text.lower() or "from memory" in response_text.lower() or "aria memory" in response_text.lower():
                    st.html("<span style='background:#58a6ff22;color:#58a6ff;border:1px solid #58a6ff;border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:600'>From ARIA memory cache</span>")

                # Show grounding verdict inline
                if result.get("critic_verdict"):
                    render_grounding_badge(result["critic_verdict"])

                if result["agents_involved"]:
                    st.caption(f"Agents: {' → '.join(result['agents_involved'])}")

                # Show grounding detail
                if result.get("critic_verdict"):
                    render_grounding_detail(result["critic_verdict"])

            # Accumulate trace events
            for ev in result.get("trace_events", []):
                st.session_state.trace_events.append(ev)

        rag_hit = "rag cache" in response_text.lower() or "from memory" in response_text.lower() or "aria memory" in response_text.lower()
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "agents_involved": result.get("agents_involved", []),
            "rag_cache_hit": rag_hit,
            "critic_verdict": result.get("critic_verdict"),
            "citations": [],
            "confidence": None,
        })

with trace_col:
    st.subheader("Live Trace", divider="blue")
    st.caption("Agent execution events from this session.")

    events = [TraceEvent(**e) for e in st.session_state.trace_events]
    render_trace_timeline(events)

    if st.session_state.trace_events:
        if st.button("Clear Trace", use_container_width=True):
            st.session_state.trace_events = []
            st.rerun()
