"""Live agent trace display component."""
from __future__ import annotations

import streamlit as st
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TraceEvent:
    agent: str
    event_type: str  # "tool_call" | "handoff" | "llm_call" | "guardrail" | "hitl"
    detail: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    duration_ms: int | None = None
    status: str = "ok"  # "ok" | "error" | "pending"


ICONS = {
    "tool_call": "🔧",
    "handoff": "🔀",
    "llm_call": "🤖",
    "guardrail": "🛡️",
    "hitl": "👤",
    "critic": "🔬",
}

STATUS_COLOR = {
    "ok": "#3fb950",
    "error": "#f85149",
    "pending": "#d29922",
    "warning": "#d29922",
}


def render_trace_timeline(events: list[TraceEvent]) -> None:
    """Render a vertical trace timeline."""
    if not events:
        st.caption("No trace events yet.")
        return

    for ev in events:
        icon = ICONS.get(ev.event_type, "•")
        color = STATUS_COLOR.get(ev.status, "#8b949e")
        dur = f" · {ev.duration_ms}ms" if ev.duration_ms else ""
        st.html(
            f"<div style='display:flex;align-items:flex-start;margin-bottom:6px;'>"
            f"  <span style='font-size:1.1rem;margin-right:8px'>{icon}</span>"
            f"  <div>"
            f"    <span style='color:{color};font-weight:600'>{ev.agent}</span>"
            f"    <span style='color:#8b949e;font-size:0.8rem'> {ev.timestamp}{dur}</span><br>"
            f"    <span style='color:#e6edf3;font-size:0.9rem'>{ev.detail}</span>"
            f"  </div>"
            f"</div>"
        )
