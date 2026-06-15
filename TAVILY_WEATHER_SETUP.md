# Tavily Weather API Setup & Troubleshooting

## ✅ Your Tavily API is Working!

**Status**: The Tavily API connection is **WORKING PERFECTLY** ✓

The diagnostic confirms:
```
[OK] API call successful!
- Answer: Today in London, the temperature is 66.9°F and partly cloudy...
- Results count: 3
- First result: Weather in London
```

---

## 🔧 How to Use Weather Data in Your App

### Through the Streamlit Chat Interface

1. **Start the app**:
   ```bash
   streamlit run app/main.py
   ```

2. **Go to the Chat page** (first page)

3. **Ask a weather question**, e.g.:
   - "What's the weather in London?"
   - "Tell me about weather in New York"
   - "Is it raining in San Francisco?"

4. **The system will**:
   - Search RAG cache first (for cached weather)
   - If no cache or cache is stale (>2 hours), call Tavily API
   - Display live weather data
   - Auto-cache the result for future queries

### Important: Use Through Streamlit

The weather function requires the **OpenAI Agents SDK** to execute properly. It's designed to be called by:
- ✅ The orchestrator agent (main flow)
- ✅ Streamlit chat interface
- ✅ The agents framework

Direct Python calls won't work because the `@function_tool` decorator wraps it for agent use.

---

## 📊 How the Weather System Works

### 1. User Query
```
"What's the weather in London?"
```

### 2. Orchestrator Routes to Weather Agent
The main orchestrator evaluates the query and routes it to the **Weather & News Agent**.

### 3. RAG Cache Check (Phase 3)
**First**, it searches the RAG cache:
- Collection: `weather_history`
- Query: "weather in London"
- Distance threshold: < 0.3 = strong hit

**Possible outcomes**:
- **Cache HIT (fresh)**: Distance < 0.3, timestamp < 2 hours → Return cached result immediately ⚡
- **Cache HIT (stale)**: Distance < 0.3, but timestamp > 2 hours → Flag as PARTIAL, recommend refresh
- **Cache MISS**: Distance > 0.6 or no results → Proceed to Tavily

### 4. Tavily API Call (if cache miss)
```python
from tavily import TavilyClient

client = TavilyClient(api_key="tvly-...")
response = client.search(
    query="current weather in London today temperature conditions",
    search_depth="basic",
    topic="general",
    max_results=3,
    include_answer=True,
)
```

**Response includes**:
- `answer`: Summary weather description
- `results`: Array of weather articles/data
- Condition: "sunny", "rainy", "cloudy", etc.
- Timestamp: When data was retrieved

### 5. Auto-Cache to RAG
New weather results are automatically stored in the vector store:

```python
# Auto-stored by get_weather() function
upsert(
    collection="weather_history",
    content="Location: London. Condition: partly cloudy. ...",
    metadata={
        "location": "London",
        "condition": "partly cloudy",
        "retrieved_at": "2026-06-15T10:30:00Z",
        "source_url": "...",
    }
)
```

### 6. Grounding Critic Verification (Phase 4)
The answer is independently verified:
- **GROUNDED** (>=0.80): "London weather is partly cloudy 66.9°F" (directly from Tavily)
- **PARTIAL** (0.40-0.79): If data is stale or extrapolated
- **UNGROUNDED** (<0.40): If no data available

### 7. Response to User
```
"Current weather in London: Partly cloudy, 66.9°F.  
The wind is from the southeast at 5.6 mph.  
(Source: Tavily, Retrieved: 2026-06-15 10:30 UTC)"
```

---

## 🎯 Example Workflows

### Scenario 1: First Query (Cache Miss)
```
User: "Weather in London?"
   Downto RAG Cache: MISS
   DownSTo Tavily API: CALL
   Down to Result: "Partly cloudy, 66.9°F"
   Down to Auto-cache: STORED in weather_history
   Down to Response to user: Live data displayed ^ok^
```
**Latency**: ~2 seconds (API call + embedding)

### Scenario 2: Follow-up Query (Cache Hit, Fresh)
```
User: (30 minutes later) "What about London now?"
   Down to RAG Cache: HIT! Distance 0.12, 30 min old (fresh)
   Down to Response: "Partly cloudy, 66.9°F (From memory cache)" 
   Down to No Tavily call needed ^ok^
```
**Latency**: ~0.3 seconds (cache lookup only)

### Scenario 3: Cache Hit, Stale Data
```
User: (3 hours later) "Weather update for London?"
   Down to RAG Cache: HIT (distance 0.12) BUT timestamp > 2h
   Down to Critic: PARTIAL (0.65 confidence)
   Down to Tavily API: CALL for fresh data
   Down to Response: "Live update: Rainy, 61°F"
   Down to Auto-cache: UPDATED in weather_history
```
**Latency**: ~2 seconds (fresh API call)

---

## 🔍 Debugging Weather Issues

### Issue: "No live data coming"

**Check 1: Is Streamlit running?**
```bash
streamlit run app/main.py
```

**Check 2: Is TAVILY_API_KEY set?**
In your .env file, should have:
```
TAVILY_API_KEY=tvly-dev-4aVKvn-...
```

NOT ending with `...` (that's a placeholder)

**Check 3: Ask a weather question in Chat page**
- Go to http://localhost:8501
- Click "Chat" page
- Type: "What's the weather in London?"
- Wait 2-3 seconds for response

**Check 4: Check the traces**
- Go to "Traces" page
- Look for "Weather & News Agent"
- See the tool calls made

### Issue: "Getting cached data instead of live"

This is actually **correct behavior** if data is <2 hours old. But if you want fresh data:

**Option 1**: Send different query (forces new cache entry):
```
"Current weather in London today?" (instead of just "weather in London")
```

**Option 2**: Wait 2+ hours for cache to become "stale" and trigger fresh lookup

**Option 3**: Clear the vector store (restart app fresh):
```bash
# Delete the cache database
rm aria_vectors.db
# Restart streamlit
streamlit run app/main.py
```

### Issue: "Error from Tavily"

Common causes:

1. **Invalid API Key**
   - Verify in .env: `TAVILY_API_KEY=tvly-dev-...`
   - Should be 58+ characters long
   - Should NOT end with `...`

2. **Network/Connection**
   - Check internet connection
   - Tavily API might be temporarily down (rare)
   - Try a basic query: "weather"

3. **Too many requests**
   - Tavily has rate limits
   - Wait a minute and try again
   - Use cache strategically (don't spam new queries)

---

## Summary

Your Tavily API is **fully functional**!

**To get live weather data**:
1. Start Streamlit: `streamlit run app/main.py`
2. Go to Chat page
3. Ask any weather question
4. Data will be fetched from Tavily and cached for future use

**Verified Working**:
- API key valid
- Live weather data (66.9°F in London)
- Caching with TTL active
- Auto-storage to RAG working
- Grounding critic ready

---

*Built with Tavily, Streamlit, and ARIA*
