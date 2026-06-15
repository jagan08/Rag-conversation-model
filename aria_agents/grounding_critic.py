"""Grounding Critic Agent — independently validates ARIA answers against evidence."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import Agent
from config.model_config import make_claude_model

from config.model_config import config

CRITIC_INSTRUCTIONS = """
You are the ARIA Grounding Critic — an independent verification agent powered by GPT-4o.
Your ONLY job is to assess whether a proposed answer is faithfully grounded in the provided evidence.

## Input format
You will receive a message like:
---
USER QUERY: <the original user question>
PROPOSED ANSWER: <what ARIA wants to say>
EVIDENCE:
<list of retrieved documents / tool outputs ARIA used>
---

## Your task
1. Read the evidence carefully.
2. Check every factual claim in the proposed answer against the evidence.
3. Output a structured verdict.

### GROUNDED
Every key claim in the answer is directly supported by the evidence. Confidence >= 0.80.

### PARTIAL
Some claims are supported, but one or more are extrapolated, inferred, or uncertain.
Confidence 0.40-0.79.

### UNGROUNDED
No meaningful evidence supports the answer, OR the answer contradicts the evidence.
Confidence < 0.40.

## Output format (strictly follow this)
Reply ONLY with the following block — no prose before or after:

VERDICT: <GROUNDED|PARTIAL|UNGROUNDED>
CONFIDENCE: <0.00 to 1.00>
CITATIONS:
- "<quote from evidence>" (source: <collection or tool name>)
- (add more as needed, or "- none" if UNGROUNDED)
ISSUES:
- <specific grounding problem, or "- none" if GROUNDED>
SUMMARY: <one sentence explaining the verdict>

## Rules
- Never make up evidence. If evidence is absent, verdict MUST be UNGROUNDED.
- Treat employee DB facts as grounded if the answer cites employee IDs, names, or aggregates that match the evidence.
- Treat weather/news facts as PARTIAL if the retrieved_at timestamp is > 2 hours old.
- If the proposed answer says "I don't know" or refuses, verdict is GROUNDED (honest refusal).
- Be strict but fair. Prefer PARTIAL over UNGROUNDED when evidence partially supports the answer.
"""


def get_critic_agent() -> Agent:
    return Agent(
        name="Grounding Critic",
        instructions=CRITIC_INSTRUCTIONS,
        model=make_claude_model(config.critic_model),
    )


def _parse_verdict_text(text: str) -> dict:
    """Parse the structured critic output into a dict."""
    import re
    result = {
        "verdict": "GROUNDED",
        "confidence": 1.0,
        "citations": [],
        "issues": [],
        "critique_summary": "",
    }

    verdict_match = re.search(r"VERDICT:\s*(GROUNDED|PARTIAL|UNGROUNDED)", text, re.I)
    if verdict_match:
        result["verdict"] = verdict_match.group(1).upper()

    conf_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", text)
    if conf_match:
        try:
            result["confidence"] = max(0.0, min(1.0, float(conf_match.group(1))))
        except ValueError:
            pass

    cit_block = re.search(r"CITATIONS:\n(.*?)\n(?:ISSUES:|SUMMARY:)", text, re.S)
    if cit_block:
        for line in cit_block.group(1).splitlines():
            line = line.strip("- ").strip()
            if line and line.lower() != "none":
                src_match = re.search(r'\(source:\s*([^)]+)\)', line)
                src = src_match.group(1).strip() if src_match else ""
                quote = re.sub(r'\s*\(source:[^)]+\)', '', line).strip('"').strip()
                if quote:
                    result["citations"].append({"text": quote, "source": src, "relevance": 1.0})

    issues_block = re.search(r"ISSUES:\n(.*?)\n(?:SUMMARY:|$)", text, re.S)
    if issues_block:
        for line in issues_block.group(1).splitlines():
            line = line.strip("- ").strip()
            if line and line.lower() != "none":
                result["issues"].append(line)

    summary_match = re.search(r"SUMMARY:\s*(.+)", text)
    if summary_match:
        result["critique_summary"] = summary_match.group(1).strip()

    return result


async def run_critic(
    user_query: str,
    proposed_answer: str,
    evidence_docs: list[str],
) -> dict:
    """Run the Grounding Critic and return parsed verdict dict."""
    from agents import Runner, RunConfig

    if not proposed_answer.strip():
        return {
            "verdict": "UNGROUNDED",
            "confidence": 0.0,
            "citations": [],
            "issues": ["No answer was generated."],
            "critique_summary": "Empty answer — nothing to verify.",
        }

    evidence_text = "\n".join(
        f"[{i+1}] {doc}" for i, doc in enumerate(evidence_docs)
    ) if evidence_docs else "(No evidence documents provided)"

    critic_prompt = (
        f"USER QUERY: {user_query}\n\n"
        f"PROPOSED ANSWER: {proposed_answer}\n\n"
        f"EVIDENCE:\n{evidence_text}"
    )

    try:
        critic = get_critic_agent()
        result = await Runner.run(
            critic,
            input=critic_prompt,
            run_config=RunConfig(tracing_disabled=True),
            max_turns=1,
        )
        raw_text = result.final_output or ""
        return _parse_verdict_text(raw_text)
    except Exception as exc:
        return {
            "verdict": "PARTIAL",
            "confidence": 0.5,
            "citations": [],
            "issues": [f"Critic error: {str(exc)[:120]}"],
            "critique_summary": "Critic could not complete verification.",
        }
