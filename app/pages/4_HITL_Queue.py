"""HITL Approval Queue page."""
import os
for _v in ("ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","OPENROUTER_API_KEY"):
    os.environ.pop(_v, None)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from app.style import inject
from app.components.hitl_modal import hitl_approval_dialog

st.set_page_config(page_title="ARIA · HITL Queue", page_icon="👤", layout="wide")
inject()

st.title("Human-in-the-Loop Approval Queue")
st.caption("Review and approve or reject agent actions that require human oversight.")

# ── Queue state init ───────────────────────────────────────────────────────────
if "hitl_queue" not in st.session_state:
    st.session_state.hitl_queue = []
if "hitl_history" not in st.session_state:
    st.session_state.hitl_history = []

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Pending Approvals", len(st.session_state.hitl_queue))
approved = sum(1 for h in st.session_state.hitl_history if h.get("decision") == "approved")
rejected = sum(1 for h in st.session_state.hitl_history if h.get("decision") == "rejected")
k2.metric("Approved (session)", approved)
k3.metric("Rejected (session)", rejected)

st.divider()

# ── Pending queue ──────────────────────────────────────────────────────────────
st.subheader("Pending")
if not st.session_state.hitl_queue:
    st.success("No pending approvals.", icon="✅")
else:
    for i, item in enumerate(st.session_state.hitl_queue):
        with st.container(border=True):
            cols = st.columns([0.7, 0.15, 0.15])
            with cols[0]:
                st.markdown(f"**{item['title']}**")
                st.caption(item.get("description", ""))
                if item.get("details"):
                    with st.expander("Details"):
                        st.json(item["details"])
            with cols[1]:
                if st.button("Approve", key=f"approve_{i}", type="primary", use_container_width=True):
                    item["decision"] = "approved"
                    st.session_state.hitl_history.append(item)
                    st.session_state.hitl_queue.pop(i)
                    st.toast("Approved!", icon="✅")
                    st.rerun()
            with cols[2]:
                if st.button("Reject", key=f"reject_{i}", type="secondary", use_container_width=True):
                    item["decision"] = "rejected"
                    st.session_state.hitl_history.append(item)
                    st.session_state.hitl_queue.pop(i)
                    st.toast("Rejected.", icon="🚫")
                    st.rerun()

# ── Demo trigger ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("Demo: Trigger a HITL approval")
st.caption("In production, agents trigger these automatically. Click below to simulate one.")
if st.button("Simulate: DB Write Approval", type="secondary"):
    st.session_state.hitl_queue.append({
        "title": "Database Write: Update Employee Record",
        "description": "Employee Intelligence Agent wants to update employee #42's office_location from 'London, UK' to 'Berlin, Germany'.",
        "operation_type": "db_write",
        "details": {
            "employee_id": 42,
            "field": "office_location",
            "old_value": "London, UK",
            "new_value": "Berlin, Germany",
            "requested_by": "Employee Intelligence Agent",
        },
    })
    st.session_state.hitl_pending = True
    st.rerun()

# ── History ────────────────────────────────────────────────────────────────────
if st.session_state.hitl_history:
    st.divider()
    st.subheader("Decision History")
    import pandas as pd
    hist_df = pd.DataFrame(st.session_state.hitl_history)[["title", "operation_type", "decision"]]
    st.dataframe(hist_df, use_container_width=True, hide_index=True)
