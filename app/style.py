"""ARIA brand CSS injected into every page."""

ARIA_CSS = """
<style>
/* ── ARIA global theme ─────────────────────────────────────────── */
:root {
    --aria-bg:      #0d1117;
    --aria-surface: #161b22;
    --aria-border:  #30363d;
    --aria-accent:  #58a6ff;
    --aria-accent2: #3fb950;
    --aria-warn:    #d29922;
    --aria-error:   #f85149;
    --aria-text:    #e6edf3;
    --aria-muted:   #8b949e;
}

/* Main background */
.stApp { background: var(--aria-bg); color: var(--aria-text); }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--aria-surface);
    border-right: 1px solid var(--aria-border);
}
[data-testid="stSidebar"] * { color: var(--aria-text) !important; }

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--aria-surface);
    border: 1px solid var(--aria-border);
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricValue"] { color: var(--aria-accent) !important; font-size: 1.8rem !important; }

/* Chat bubbles */
.stChatMessage { background: var(--aria-surface); border: 1px solid var(--aria-border); border-radius: 8px; }

/* Primary buttons */
.stButton > button {
    background: var(--aria-accent);
    color: #0d1117;
    border: none;
    border-radius: 6px;
    font-weight: 600;
}
.stButton > button:hover { background: #79c0ff; color: #0d1117; }

/* Tabs */
.stTabs [data-baseweb="tab"] { color: var(--aria-muted); }
.stTabs [aria-selected="true"] { color: var(--aria-accent) !important; border-bottom: 2px solid var(--aria-accent); }

/* Divider */
hr { border-color: var(--aria-border); }

/* Badge overrides */
.stBadge { font-size: 0.72rem !important; }

/* HITL dialog */
.hitl-dialog { background: var(--aria-surface); border: 1px solid var(--aria-warn); border-radius: 10px; padding: 20px; }
</style>
"""


def inject() -> None:
    import streamlit as st
    st.html(ARIA_CSS)
