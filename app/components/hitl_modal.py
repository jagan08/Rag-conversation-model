"""Reusable HITL approval dialog component using @st.dialog."""
from __future__ import annotations

import streamlit as st


def hitl_approval_dialog(
    title: str,
    description: str,
    details: dict | None = None,
    operation_type: str = "operation",
) -> None:
    """
    Render a Human-in-the-Loop approval modal.

    Sets st.session_state.hitl_decision to 'approved' | 'rejected' | None.
    Call this function; Streamlit will show the dialog overlay.
    """
    @st.dialog(f"HITL Approval Required: {title}", width="large")
    def _dialog():
        col_icon, col_title = st.columns([0.08, 0.92])
        with col_icon:
            st.html("<span style='font-size:2rem;'>&#x26A0;</span>")
        with col_title:
            st.subheader(title, divider="orange")

        st.info(description, icon="ℹ️")

        if details:
            with st.expander("Operation Details", expanded=True):
                st.json(details)

        st.markdown(f"**Operation type:** `{operation_type}`")
        st.caption("This action requires explicit human approval before ARIA proceeds.")

        col_approve, col_reject, _ = st.columns([1, 1, 2])
        with col_approve:
            if st.button("Approve", type="primary", use_container_width=True):
                st.session_state.hitl_decision = "approved"
                st.session_state.hitl_pending = False
                st.toast("Action approved.", icon="✅")
                st.rerun()
        with col_reject:
            if st.button("Reject", type="secondary", use_container_width=True):
                st.session_state.hitl_decision = "rejected"
                st.session_state.hitl_pending = False
                st.toast("Action rejected.", icon="🚫")
                st.rerun()

    _dialog()


def hitl_status_badge() -> None:
    """Show a sidebar badge for pending HITL approvals."""
    pending = st.session_state.get("hitl_pending", False)
    if pending:
        st.sidebar.warning("1 approval pending", icon="⏳")
    else:
        st.sidebar.success("No pending approvals", icon="✅")
