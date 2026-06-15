"""System Configuration page."""
import os
for _v in ("ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","OPENROUTER_API_KEY"):
    os.environ.pop(_v, None)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from app.style import inject
from config.model_config import ModelConfig

st.set_page_config(page_title="ARIA · Config", page_icon="⚙️", layout="wide")
inject()

st.title("System Configuration")
st.caption("View and override ARIA model assignments and system settings.")

cfg = ModelConfig.from_env()

# ── Model config ───────────────────────────────────────────────────────────────
st.subheader("Model Assignments", divider="blue")
st.info("Changes here apply to the current session only. Edit `.env` to persist.", icon="ℹ️")

CLAUDE_MODELS = ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"]
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
ALL_MODELS = CLAUDE_MODELS + OPENAI_MODELS

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Agent → Model**")
    orch = st.selectbox("Orchestrator (ARIA)", ALL_MODELS, index=ALL_MODELS.index(cfg.orchestrator_model) if cfg.orchestrator_model in ALL_MODELS else 0)
    spec = st.selectbox("Specialist Agents", ALL_MODELS, index=ALL_MODELS.index(cfg.specialist_model) if cfg.specialist_model in ALL_MODELS else 1)
    critic = st.selectbox("Grounding Critic", ALL_MODELS, index=ALL_MODELS.index(cfg.critic_model) if cfg.critic_model in ALL_MODELS else 3)

with col2:
    st.markdown("**Utility → Model**")
    light = st.selectbox("Lightweight (guardrails, resolver)", ALL_MODELS, index=ALL_MODELS.index(cfg.lightweight_model) if cfg.lightweight_model in ALL_MODELS else 4)
    fallback = st.selectbox("Fallback Provider", ALL_MODELS, index=ALL_MODELS.index(cfg.fallback_model) if cfg.fallback_model in ALL_MODELS else 3)
    provider = st.radio("LLM Provider layer", ["litellm", "openai"], horizontal=True, index=0 if cfg.provider == "litellm" else 1)

if st.button("Apply to Session", type="primary"):
    st.session_state["model_override"] = ModelConfig(
        orchestrator_model=orch, specialist_model=spec, critic_model=critic,
        lightweight_model=light, fallback_model=fallback, provider=provider,
    )
    st.success("Model config updated for this session.", icon="✅")
    st.toast("Model config applied.", icon="⚙️")

# ── TTL settings ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("Freshness TTLs", divider="blue")
wcol, ncol = st.columns(2)
with wcol:
    weather_ttl = st.slider("Weather cache TTL (seconds)", 600, 14400, cfg.weather_ttl_seconds, step=600)
    st.caption(f"= {weather_ttl // 3600}h {(weather_ttl % 3600) // 60}m")
with ncol:
    news_ttl = st.slider("News cache TTL (seconds)", 3600, 172800, cfg.news_ttl_seconds, step=3600)
    st.caption(f"= {news_ttl // 3600} hours")

# ── Tracing settings ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Tracing & Privacy", divider="blue")
sensitive = st.toggle("Include sensitive data in traces", value=False, help="Must be OFF in production (PII protection).")
if sensitive:
    st.error("WARNING: Enabling this in production violates PII policy. For local dev only.", icon="🔴")

# ── Current config display ─────────────────────────────────────────────────────
st.divider()
with st.expander("Active Configuration (JSON)", expanded=False):
    import json, dataclasses
    active = st.session_state.get("model_override", cfg)
    st.json(dataclasses.asdict(active))
