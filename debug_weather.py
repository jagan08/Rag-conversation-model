#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug script to test Tavily weather API integration."""

import os
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project to path
sys.path.insert(0, os.getcwd())

# Load environment manually
print("=" * 70)
print("ARIA WEATHER API DIAGNOSTIC")
print("=" * 70)

print("\n1. Loading environment variables...")
with open('.env') as f:
    for line in f:
        if line.strip() and line.startswith('TAVILY_API_KEY'):
            key, val = line.strip().split('=', 1)
            os.environ[key] = val
            print(f"   [OK] Set {key}: {val[:40]}...")

tavily_key = os.getenv('TAVILY_API_KEY', '')

if not tavily_key:
    print("   [ERROR] ERROR: TAVILY_API_KEY not found!")
    sys.exit(1)

if tavily_key.endswith("..."):
    print("   [ERROR] ERROR: TAVILY_API_KEY appears to be a placeholder!")
    sys.exit(1)

print(f"   [OK] OK: Key is set (length: {len(tavily_key)})")

# Test 1: Direct Tavily API call
print("\n2. Testing Tavily API directly...")
try:
    from tavily import TavilyClient

    client = TavilyClient(api_key=tavily_key)

    response = client.search(
        query="current weather in London today temperature conditions",
        search_depth="basic",
        topic="general",
        max_results=3,
        include_answer=True,
        include_raw_content=False,
    )

    print("   [OK] API call successful!")
    print(f"   - Answer: {response.get('answer', '')[:100]}...")
    print(f"   - Results count: {len(response.get('results', []))}")

    if response.get('results'):
        print(f"   - First result: {response['results'][0].get('title', '')}")

except Exception as e:
    print(f"   [ERROR] ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Full orchestrator test
print("\n3. Testing through ARIA Orchestrator...")
try:
    print("   Loading orchestrator...")
    from aria_agents.orchestrator import get_orchestrator
    from agents import Runner, RunConfig

    orchestrator = get_orchestrator()
    print("   [OK] Orchestrator loaded")

    print("   Running query: 'What is the weather in London?'")
    result = Runner.run(
        orchestrator,
        input="What is the weather in London?",
        run_config=RunConfig(tracing_disabled=True),
    )

    print(f"   [OK] Orchestrator executed!")
    print(f"   Final output:\n{result.final_output}")

except Exception as e:
    print(f"   [ERROR] ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
