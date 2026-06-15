"""Weather and news card display components."""
from __future__ import annotations

import streamlit as st
from datetime import datetime, timezone

CONDITION_ICON = {
    "rain": "🌧️", "rainy": "🌧️",
    "sunny": "☀️", "clear": "☀️",
    "cloud": "☁️", "cloudy": "☁️",
    "storm": "⛈️", "stormy": "⛈️",
    "snow": "❄️", "snowy": "❄️",
    "fog": "🌫️", "foggy": "🌫️",
    "wind": "💨", "windy": "💨",
    "hot": "🌡️", "cold": "🌡️",
    "unknown": "🌐",
}


def _freshness_badge(retrieved_at: str, ttl_seconds: int = 7200) -> str:
    """Return HTML badge: green=fresh, amber=aging, red=stale."""
    try:
        if retrieved_at.endswith("Z"):
            retrieved_at = retrieved_at[:-1]
        fetched = datetime.fromisoformat(retrieved_at)
        age = (datetime.utcnow() - fetched).total_seconds()
        if age < ttl_seconds * 0.5:
            color, label = "#3fb950", "Fresh"
        elif age < ttl_seconds:
            color, label = "#d29922", "Aging"
        else:
            color, label = "#f85149", "Stale"
    except Exception:
        color, label = "#8b949e", "Unknown"

    return (
        f"<span style='background:{color}22;color:{color};border:1px solid {color};"
        f"border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:600'>{label}</span>"
    )


def render_weather_card(weather: dict) -> None:
    """Render a weather result card."""
    if not weather or weather.get("error"):
        st.error(f"Weather unavailable: {weather.get('error', 'unknown error')}", icon="⚠️")
        return

    condition = weather.get("condition", "unknown").lower()
    icon = CONDITION_ICON.get(condition, "🌐")
    location = weather.get("location", "")
    summary = weather.get("summary", "")
    temp = weather.get("temperature_c")
    retrieved_at = weather.get("retrieved_at", "")
    source_url = weather.get("source_url")

    with st.container(border=True):
        col_icon, col_info = st.columns([0.1, 0.9])
        with col_icon:
            st.html(f"<div style='font-size:2.5rem;text-align:center'>{icon}</div>")
        with col_info:
            temp_str = f" · {temp:.0f}°C" if temp is not None else ""
            st.html(
                f"<span style='font-size:1.1rem;font-weight:700;color:#e6edf3'>{location}</span>"
                f"<span style='color:#58a6ff'>{temp_str}</span><br>"
                f"<span style='color:#8b949e;font-size:0.85rem;text-transform:capitalize'>{condition}</span> "
                + (f"&nbsp;{_freshness_badge(retrieved_at)}" if retrieved_at else "")
            )

        st.markdown(summary)

        if source_url:
            st.link_button("View Source", source_url, use_container_width=False)
        if retrieved_at:
            st.caption(f"Retrieved: {retrieved_at}")


def render_news_card(article: dict) -> None:
    """Render a single news article card."""
    title = article.get("title", "Untitled")
    summary = article.get("summary", "")
    url = article.get("url", "")
    published = article.get("published_at", "")
    source = article.get("source", "")

    with st.container(border=True):
        st.markdown(f"**{title}**")
        if published:
            st.caption(f"{source} · {published}" if source else published)
        st.markdown(summary)
        if url:
            st.link_button("Read Article", url, use_container_width=False)


def render_weather_news_section(result_text: str) -> None:
    """
    Parse agent response text for weather/news markers and render cards.
    Falls back to plain markdown if no structured data found.
    """
    st.markdown(result_text)
