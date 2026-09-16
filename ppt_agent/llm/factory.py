"""Builds the configured ``LLMClient`` without hard-importing every backend.

Each backend's third-party dependency (``openai``, ``anthropic``) is only
imported when that backend is actually selected, so a user running purely
against a local OpenAI-compatible server never needs the ``anthropic``
package installed, and vice versa.
"""

from __future__ import annotations

from ppt_agent.config import AgentConfig
from ppt_agent.exceptions import PptAgentError
from ppt_agent.llm.base import LLMClient


def build_llm_client(config: AgentConfig) -> LLMClient:
    """Instantiate the LLM backend named by ``config.llm_provider``."""
    if config.llm_provider == "openai_compatible":
        from ppt_agent.llm.openai_compatible import OpenAICompatibleClient

        return OpenAICompatibleClient(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    if config.llm_provider == "anthropic":
        from ppt_agent.llm.anthropic_client import AnthropicClient

        return AnthropicClient(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    raise PptAgentError(
        f"Unknown llm_provider '{config.llm_provider}'. "
        "Supported values: 'openai_compatible', 'anthropic'."
    )
