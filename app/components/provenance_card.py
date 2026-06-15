"""Provenance / citation display component."""
from __future__ import annotations

import streamlit as st
from dataclasses import dataclass, field


@dataclass
class Citation:
    source: str
    url: str | None = None
    timestamp: str | None = None
    confidence: float | None = None
    snippet: str | None = None


def render_provenance(citations: list[Citation], confidence: float | None = None) -> None:
    """Render a provenance card below an agent response."""
    if not citations:
        return

    with st.expander("Sources & Provenance", expanded=False):
        if confidence is not None:
            conf_pct = int(confidence * 100)
            color = "#3fb950" if conf_pct >= 80 else "#d29922" if conf_pct >= 60 else "#f85149"
            st.html(
                f"<div style='margin-bottom:8px'>"
                f"<span style='font-size:0.85rem;color:#8b949e'>Confidence: </span>"
                f"<span style='color:{color};font-weight:700;font-size:1rem'>{conf_pct}%</span>"
                f"</div>"
            )
            st.progress(confidence)

        for i, c in enumerate(citations):
            cols = st.columns([0.05, 0.95])
            with cols[0]:
                st.html(f"<span style='color:#58a6ff;font-weight:700'>[{i+1}]</span>")
            with cols[1]:
                if c.url:
                    st.markdown(f"**[{c.source}]({c.url})**")
                else:
                    st.markdown(f"**{c.source}**")
                if c.timestamp:
                    st.caption(f"Retrieved: {c.timestamp}")
                if c.snippet:
                    st.markdown(f"> {c.snippet[:200]}...")
