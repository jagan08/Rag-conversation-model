from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

# Claude Code injects ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN pointing at OpenRouter.
# Clear them ALL — LiteLLM's native Anthropic handler must not see a custom base URL.
# Then inject the real API key directly via litellm so it's used for all calls.
os.environ.pop("ANTHROPIC_BASE_URL", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
os.environ.pop("OPENROUTER_API_KEY", None)

# Sync the real Anthropic key into litellm at module load time
try:
    import litellm as _litellm
    from dotenv import load_dotenv as _lde
    _lde(override=False)
    _litellm.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    # Enable automatic retries with exponential backoff for rate limits
    _litellm.num_retries = 3
    _litellm.request_timeout = 60
except Exception:
    pass


def make_claude_model(model_name: str):
    """Return a LitellmModel using LiteLLM's native Anthropic handler."""
    from agents.extensions.models.litellm_model import LitellmModel
    # Pass api_key explicitly so it survives env-var overrides
    return LitellmModel(
        model=f"anthropic/{model_name}",
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    )


@dataclass
class ModelConfig:
    orchestrator_model: str = "claude-opus-4-5"
    specialist_model: str = "claude-sonnet-4-5"
    critic_model: str = "gpt-4o"
    lightweight_model: str = "gpt-4o-mini"
    fallback_model: str = "gpt-4o"
    provider: Literal["litellm", "openai"] = "litellm"

    # Freshness TTLs (seconds)
    weather_ttl_seconds: int = 7200    # 2 hours
    news_ttl_seconds: int = 86400      # 24 hours

    # Tracing
    trace_include_sensitive_data: bool = False

    @classmethod
    def from_env(cls) -> "ModelConfig":
        return cls(
            orchestrator_model=os.getenv("ARIA_ORCHESTRATOR_MODEL", "claude-opus-4-5"),
            specialist_model=os.getenv("ARIA_SPECIALIST_MODEL", "claude-sonnet-4-5"),
            critic_model=os.getenv("ARIA_CRITIC_MODEL", "gpt-4o"),
            lightweight_model=os.getenv("ARIA_LIGHTWEIGHT_MODEL", "gpt-4o-mini"),
            fallback_model=os.getenv("ARIA_FALLBACK_MODEL", "gpt-4o"),
            provider=os.getenv("ARIA_PROVIDER", "litellm"),
        )

    def get_model(self, role: Literal["orchestrator", "specialist", "critic", "lightweight", "fallback"]) -> str:
        return {
            "orchestrator": self.orchestrator_model,
            "specialist": self.specialist_model,
            "critic": self.critic_model,
            "lightweight": self.lightweight_model,
            "fallback": self.fallback_model,
        }[role]


# Singleton loaded from env
config = ModelConfig.from_env()
