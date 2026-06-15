"""ARIA Streamlit application entry point."""
import os
# Must run before ANY other import — system env vars override .env and redirect
# Anthropic API calls to OpenRouter with an invalid token.
for _v in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "OPENROUTER_API_KEY"):
    os.environ.pop(_v, None)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from app.style import inject

st.set_page_config(
    page_title="ARIA — Agentic RAG",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "ARIA — Agentic Retrieval & Intelligence Architecture v0.1",
    },
)
inject()

# ── Navigation ─────────────────────────────────────────────────────────────────
pages = {
    "ARIA": [
        st.Page(os.path.join(os.path.dirname(__file__), "pages", "1_Chat.py"),       title="Chat",          icon="💬", default=True),
        st.Page(os.path.join(os.path.dirname(__file__), "pages", "2_Employees.py"), title="Employees",     icon="👥"),
        st.Page(os.path.join(os.path.dirname(__file__), "pages", "3_Traces.py"),    title="Trace Explorer",icon="🔍"),
        st.Page(os.path.join(os.path.dirname(__file__), "pages", "4_HITL_Queue.py"),title="HITL Queue",    icon="👤"),
        st.Page(os.path.join(os.path.dirname(__file__), "pages", "5_Config.py"),    title="Configuration", icon="⚙️"),
    ]
}

pg = st.navigation(pages)

# ── Global sidebar header ──────────────────────────────────────────────────────
with st.sidebar:
    st.html("""
    <div style="padding: 8px 0 16px 0;">
      <span style="font-size:1.5rem;font-weight:700;color:#58a6ff;">ARIA</span>
      <span style="font-size:0.75rem;color:#8b949e;display:block;margin-top:2px;">
        Agentic Retrieval &amp; Intelligence Architecture
      </span>
    </div>
    """)

pg.run()
