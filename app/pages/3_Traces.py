"""Run Trace Explorer + Vector Store Explorer."""
import os
for _v in ("ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","OPENROUTER_API_KEY"):
    os.environ.pop(_v, None)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from app.style import inject
from app.components.agent_trace import render_trace_timeline, TraceEvent

st.set_page_config(page_title="ARIA · Traces", page_icon="🔍", layout="wide")
inject()

st.title("Trace & Memory Explorer")
st.caption("Agent execution traces and the sqlite-vec RAG vector store.")

main_tab1, main_tab2, main_tab3 = st.tabs([
    "Agent Traces",
    "Vector Store Explorer",
    "Audit Log",
])

# ── Tab 1: Agent Traces ────────────────────────────────────────────────────────
with main_tab1:
    events_raw = st.session_state.get("trace_events", [])

    if not events_raw:
        st.info("No trace events recorded yet. Start a conversation on the Chat page.", icon="ℹ️")
    else:
        tl_tab, json_tab = st.tabs(["Timeline", "Raw JSON"])
        with tl_tab:
            render_trace_timeline([TraceEvent(**e) for e in events_raw])
        with json_tab:
            st.json(events_raw)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download Trace (JSON)",
                data=json.dumps(events_raw, indent=2),
                file_name="aria_trace.json",
                mime="application/json",
                use_container_width=True,
            )
        with c2:
            if st.button("Clear Traces", use_container_width=True):
                st.session_state.trace_events = []
                st.rerun()

# ── Tab 2: Vector Store Explorer ──────────────────────────────────────────────
with main_tab2:
    st.subheader("sqlite-vec RAG Vector Store")
    st.caption("Documents auto-stored from Tavily weather/news retrievals.")

    try:
        from db.vector_store import list_collections, get_all_documents, upsert, search

        # KPIs
        cols_info = list_collections()
        kpi_cols = st.columns(len(cols_info))
        for i, col_info in enumerate(cols_info):
            kpi_cols[i].metric(
                col_info["collection"].replace("_", " ").title(),
                col_info["document_count"],
                help=f"Documents in {col_info['collection']}"
            )

        st.divider()

        # Collection browser
        selected_coll = st.selectbox(
            "Browse collection",
            [c["collection"] for c in cols_info],
            index=0,
        )

        docs = get_all_documents(selected_coll, limit=50)
        if not docs:
            st.info(f"No documents in **{selected_coll}** yet. Make a weather or news query in the Chat page.", icon="ℹ️")
        else:
            st.caption(f"{len(docs)} most recent documents")
            for doc in docs:
                with st.expander(f"[{doc['created_at'][:19]}] {doc['content'][:80]}...", expanded=False):
                    st.markdown(f"**Content:**\n{doc['content']}")
                    st.markdown("**Metadata:**")
                    clean_meta = {k: v for k, v in doc["metadata"].items() if k != "_rowid"}
                    st.json(clean_meta)
                    st.caption(f"Doc ID: `{doc['id']}`")

        st.divider()

        # Semantic search UI
        st.subheader("Semantic Search")
        search_col1, search_col2 = st.columns([0.7, 0.3])
        with search_col1:
            search_query = st.text_input("Search query", placeholder="e.g. rainy weather London")
        with search_col2:
            search_coll = st.selectbox("Collection", [c["collection"] for c in cols_info], key="search_coll")
            n_res = st.slider("Results", 1, 10, 3)

        if st.button("Search Vector Store", type="primary", disabled=not search_query):
            with st.spinner("Running semantic search..."):
                results = search(search_coll, search_query, n_results=n_res)
            if not results:
                st.warning("No results found.", icon="⚠️")
            else:
                for r in results:
                    dist_color = "#3fb950" if (r["distance"] or 1) < 0.3 else "#d29922" if (r["distance"] or 1) < 0.6 else "#f85149"
                    st.html(
                        f"<span style='color:{dist_color};font-weight:700'>Distance: {r['distance']:.4f}</span>"
                    )
                    with st.container(border=True):
                        st.markdown(r["content"])
                        clean_meta = {k: v for k, v in r["metadata"].items() if k != "_rowid"}
                        st.json(clean_meta)

        st.divider()

        # Manual embed UI — HITL protected
        st.subheader("Embed Custom Document")
        st.caption("Manually add text to the vector store. Requires confirmation.")

        with st.form("embed_form"):
            embed_content = st.text_area("Document content", placeholder="Paste text to embed...")
            embed_coll = st.selectbox("Collection", [c["collection"] for c in cols_info], key="embed_coll")
            embed_meta = st.text_input("Metadata (JSON)", value='{"source": "manual", "type": "custom"}')
            submitted = st.form_submit_button("Preview & Confirm Embed")

        if submitted and embed_content.strip():
            st.session_state["pending_embed"] = {
                "content": embed_content,
                "collection": embed_coll,
                "metadata": embed_meta,
            }
            st.rerun()

        if st.session_state.get("pending_embed"):
            pe = st.session_state["pending_embed"]
            with st.container(border=True):
                st.warning("**HITL: Confirm document embed**", icon="⚠️")
                st.markdown(f"**Collection:** `{pe['collection']}`")
                st.markdown(f"**Content:** {pe['content'][:200]}")
                st.json(pe["metadata"])
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("Confirm Embed", type="primary", use_container_width=True):
                        try:
                            meta = json.loads(pe["metadata"])
                        except Exception:
                            meta = {"source": "manual"}
                        doc_id = upsert(pe["collection"], pe["content"], meta)
                        st.success(f"Embedded: `{doc_id}`", icon="✅")
                        st.session_state.pop("pending_embed", None)
                        st.toast("Document embedded.", icon="✅")
                        st.rerun()
                with c_no:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.pop("pending_embed", None)
                        st.rerun()

    except Exception as exc:
        st.error(f"Vector store error: {exc}", icon="⚠️")

# ── Tab 3: Audit Log ──────────────────────────────────────────────────────────
with main_tab3:
    st.subheader("Tool-Call Audit Log")
    audit_path = os.path.join(os.path.dirname(__file__), "..", "..", ".claude", "logs", "audit.jsonl")
    if os.path.exists(audit_path):
        with open(audit_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        if lines:
            st.caption(f"{len(lines)} audit entries")
            st.dataframe(pd.DataFrame(lines[:200]), use_container_width=True, hide_index=True)
        else:
            st.caption("Audit log is empty.")
    else:
        st.caption("Audit log not found — hooks will create it on first tool use.")
