"""Employee Database Browser page — with live weather lookup."""
import os
for _v in ("ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","OPENROUTER_API_KEY"):
    os.environ.pop(_v, None)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from app.style import inject
from app.components.weather_card import render_weather_card
from db.models import Employee, get_session

st.set_page_config(page_title="ARIA · Employees", page_icon="👥", layout="wide")
inject()

st.title("Employee Database")
st.caption("500 mock employees · click **Check Weather** on any location to see live conditions.")

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_employees() -> pd.DataFrame:
    with get_session() as session:
        rows = session.query(Employee).all()
        return pd.DataFrame([{
            "ID": e.id, "First": e.first_name, "Last": e.last_name,
            "Email": e.email, "Department": e.department, "Title": e.job_title,
            "Location": e.office_location, "Hired": e.hire_date,
            "Band": e.salary_band, "Manager ID": e.manager_id,
        } for e in rows])


@st.cache_data(ttl=7200, show_spinner=False)
def fetch_weather(location: str) -> dict:
    """Fetch weather via the Tavily tool — cached 2h."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.endswith("..."):
        return {"error": "TAVILY_API_KEY not configured", "location": location, "is_fresh": False}
    try:
        from tools.location_matcher import normalize_location
        import asyncio
        # Call the underlying function directly
        norm_result = asyncio.run(_run_normalize(location))
        query = norm_result.get("search_query", f"{location} weather")

        from tools.tavily_weather import get_weather as _get_weather_tool
        weather_result = asyncio.run(_run_weather(query, location))
        return weather_result
    except Exception as exc:
        return {"error": str(exc), "location": location, "is_fresh": False}


async def _run_normalize(location: str) -> dict:
    from tools.location_matcher import normalize_location
    from agents import RunContextWrapper
    result = await normalize_location(None, f'{{"office_location": "{location}"}}')
    if isinstance(result, dict):
        return result
    import json
    try:
        return json.loads(str(result))
    except Exception:
        return {"search_query": f"{location} weather", "confidence": 0.5}


async def _run_weather(query: str, location: str) -> dict:
    from tools.tavily_weather import get_weather as _tool
    result = await _tool(None, f'{{"location": "{query}", "force_refresh": false}}')
    if isinstance(result, dict):
        return result
    import json
    try:
        return json.loads(str(result))
    except Exception:
        return {"error": "Parse error", "location": location}


df = load_employees()

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Employees", len(df))
k2.metric("Departments", df["Department"].nunique())
k3.metric("Locations", df["Location"].nunique())
k4.metric("Salary Bands", df["Band"].nunique())

st.divider()

# ── Weather by Location panel ──────────────────────────────────────────────────
st.subheader("Live Weather by Office Location")

if not os.getenv("TAVILY_API_KEY", "").replace("tvly-...", ""):
    st.info("Add `TAVILY_API_KEY` to `.env` to enable live weather lookups.", icon="ℹ️")
else:
    unique_locs = sorted(df["Location"].unique())
    selected_loc = st.selectbox(
        "Select a location to check weather",
        ["— select —"] + unique_locs,
        index=0,
    )

    if selected_loc and selected_loc != "— select —":
        emp_count = len(df[df["Location"] == selected_loc])
        st.caption(f"{emp_count} employee(s) at this location")

        if st.button(f"Check Weather: {selected_loc}", type="primary"):
            with st.spinner(f"Fetching weather for {selected_loc}..."):
                weather = fetch_weather(selected_loc)
            render_weather_card(weather)

st.divider()

# ── Filters ────────────────────────────────────────────────────────────────────
st.subheader("Employee Directory")
fcol1, fcol2, fcol3 = st.columns(3)

with fcol1:
    dept_filter = st.multiselect("Department", sorted(df["Department"].unique()), placeholder="All departments")
with fcol2:
    loc_filter = st.multiselect("Location", sorted(df["Location"].unique()), placeholder="All locations")
with fcol3:
    band_filter = st.multiselect("Salary Band", sorted(df["Band"].unique()), placeholder="All bands")

search = st.text_input("Search by name or email", placeholder="e.g. John or @example.com")

filtered = df.copy()
if dept_filter:
    filtered = filtered[filtered["Department"].isin(dept_filter)]
if loc_filter:
    filtered = filtered[filtered["Location"].isin(loc_filter)]
if band_filter:
    filtered = filtered[filtered["Band"].isin(band_filter)]
if search:
    mask = (
        filtered["First"].str.contains(search, case=False, na=False) |
        filtered["Last"].str.contains(search, case=False, na=False) |
        filtered["Email"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

st.caption(f"Showing {len(filtered)} of {len(df)} employees")
st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Email": st.column_config.TextColumn("Email"),
        "Location": st.column_config.TextColumn("Office Location"),
    },
)

# ── Charts ─────────────────────────────────────────────────────────────────────
st.divider()
chart_tab1, chart_tab2, chart_tab3 = st.tabs(["By Department", "By Location", "By Band"])

with chart_tab1:
    dept_counts = filtered["Department"].value_counts().reset_index()
    dept_counts.columns = ["Department", "Count"]
    st.bar_chart(dept_counts.set_index("Department"))

with chart_tab2:
    loc_counts = filtered["Location"].value_counts().reset_index()
    loc_counts.columns = ["Location", "Count"]
    st.bar_chart(loc_counts.set_index("Location"))

with chart_tab3:
    band_counts = filtered["Band"].value_counts().reset_index()
    band_counts.columns = ["Band", "Count"]
    st.bar_chart(band_counts.set_index("Band"))
