"""Grounding Critic verdict badge and detail panel."""
from __future__ import annotations

import streamlit as st

_VERDICT_STYLES = {
    "GROUNDED": {
        "bg": "#0d2818",
        "border": "#3fb950",
        "color": "#3fb950",
        "icon": "✓",
        "label": "GROUNDED",
    },
    "PARTIAL": {
        "bg": "#2d1f00",
        "border": "#d29922",
        "color": "#d29922",
        "icon": "~",
        "label": "PARTIAL",
    },
    "UNGROUNDED": {
        "bg": "#2d0f0f",
        "border": "#f85149",
        "color": "#f85149",
        "icon": "✗",
        "label": "UNGROUNDED",
    },
}


def render_grounding_badge(verdict: dict | None, key: str = "") -> None:
    """Render a compact inline badge showing the critic verdict."""
    if not verdict:
        return

    v = verdict.get("verdict", "GROUNDED")
    style = _VERDICT_STYLES.get(v, _VERDICT_STYLES["PARTIAL"])
    conf = verdict.get("confidence", 1.0)
    conf_pct = f"{conf:.0%}"

    st.html(
        f"<span style='"
        f"background:{style['bg']};"
        f"border:1px solid {style['border']};"
        f"color:{style['color']};"
        f"border-radius:4px;"
        f"padding:2px 8px;"
        f"font-size:0.72rem;"
        f"font-weight:700;"
        f"font-family:monospace;"
        f"'>"
        f"{style['icon']} {style['label']} &nbsp;·&nbsp; {conf_pct}"
        f"</span>"
    )


def render_grounding_detail(verdict: dict | None, key: str = "") -> None:
    """Render an expandable critic verdict detail panel."""
    if not verdict:
        return

    v = verdict.get("verdict", "GROUNDED")
    style = _VERDICT_STYLES.get(v, _VERDICT_STYLES["PARTIAL"])
    conf = verdict.get("confidence", 1.0)
    summary = verdict.get("critique_summary", "")
    citations = verdict.get("citations", [])
    issues = verdict.get("issues", [])

    with st.expander(
        f"{style['icon']} Grounding Critic: **{v}** ({conf:.0%} confidence)",
        expanded=(v == "UNGROUNDED"),
    ):
        # Confidence progress bar
        bar_color = style["border"]
        st.html(
            f"<div style='margin-bottom:8px'>"
            f"<span style='color:#8b949e;font-size:0.75rem'>Confidence</span><br>"
            f"<div style='background:#21262d;border-radius:4px;height:6px;width:100%'>"
            f"<div style='background:{bar_color};border-radius:4px;height:6px;width:{conf*100:.0f}%'></div>"
            f"</div>"
            f"</div>"
        )

        if summary:
            st.markdown(f"**Summary:** {summary}")

        if issues:
            st.markdown("**Issues flagged:**")
            for issue in issues:
                st.html(f"<span style='color:#f85149'>⚠ {issue}</span><br>")

        if citations:
            st.markdown("**Supporting citations:**")
            for cit in citations:
                src = f" *(source: {cit['source']})*" if cit.get("source") else ""
                st.markdown(f"> {cit['text']}{src}")
        elif v != "UNGROUNDED":
            st.caption("No specific citations extracted.")

        st.caption("Verdict by ARIA Grounding Critic (GPT-4o independent reviewer)")
