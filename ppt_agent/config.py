"""Runtime configuration for the ppt_agent CLI.

Configuration can come from (in increasing priority order): built-in
defaults, environment variables, and command-line arguments. Keeping this
in one dataclass makes it trivial to see every knob the agent exposes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Settings needed to talk to an LLM backend and run the agent.

    The defaults target a local, OpenAI-API-compatible server (e.g. Ollama
    at ``http://localhost:11434/v1`` or LM Studio at
    ``http://localhost:1234/v1``), since that is the most common way to run
    a model on a personal machine. Any OpenAI-compatible endpoint, including
    OpenAI itself, works by overriding ``base_url``/``api_key``/``model``.
    """

    llm_provider: str = "openai_compatible"
    """Which LLMClient implementation to use: "openai_compatible" or "anthropic"."""

    model: str = "llama3.1"
    """Model name/tag as understood by the target server."""

    base_url: str = "http://localhost:11434/v1"
    """Base URL of the chat-completions endpoint (ignored by some providers)."""

    api_key: str = "not-needed"
    """API key/token. Local servers usually accept any non-empty placeholder."""

    temperature: float = 0.4
    max_tokens: int = 2048
    max_tool_iterations: int = 8
    """Safety cap on chained tool calls per user turn, to avoid infinite loops."""

    @classmethod
    def from_env(cls) -> AgentConfig:
        """Build a config from ``PPT_AGENT_*`` environment variables.

        Any variable that is unset falls back to the dataclass default.
        """
        defaults = cls()
        return cls(
            llm_provider=os.environ.get(
                "PPT_AGENT_LLM_PROVIDER", defaults.llm_provider
            ),
            model=os.environ.get("PPT_AGENT_MODEL", defaults.model),
            base_url=os.environ.get("PPT_AGENT_BASE_URL", defaults.base_url),
            api_key=os.environ.get("PPT_AGENT_API_KEY", defaults.api_key),
            temperature=float(
                os.environ.get("PPT_AGENT_TEMPERATURE", defaults.temperature)
            ),
            max_tokens=int(os.environ.get("PPT_AGENT_MAX_TOKENS", defaults.max_tokens)),
            max_tool_iterations=int(
                os.environ.get(
                    "PPT_AGENT_MAX_TOOL_ITERATIONS", defaults.max_tool_iterations
                )
            ),
        )
