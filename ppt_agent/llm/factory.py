"""Builds the configured LangChain chat model without hard-importing every provider.

Each provider's integration package (``langchain-openai``,
``langchain-anthropic``) is only imported when that provider is actually
selected, so a user running purely against a local OpenAI-compatible
server never needs ``langchain-anthropic`` installed, and vice versa.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from ppt_agent.config import AgentConfig
from ppt_agent.exceptions import PptAgentError


def build_chat_model(config: AgentConfig) -> BaseChatModel:
    """Instantiate the chat model named by ``config.llm_provider``.

    "openai_compatible" covers OpenAI itself as well as the many local
    servers that expose the same API surface, e.g. Ollama
    (``http://localhost:11434/v1``) and LM Studio
    (``http://localhost:1234/v1``) -- only ``base_url``/``api_key``/
    ``model`` change between them.
    """
    if config.llm_provider == "openai_compatible":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    if config.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        # AgentConfig defaults api_key to a placeholder meant for local
        # servers that don't check it; for Anthropic, fall back to the
        # ANTHROPIC_API_KEY env var (ChatAnthropic's own default) instead
        # of sending that placeholder as a real credential.
        default_api_key = AgentConfig().api_key
        api_key = config.api_key if config.api_key != default_api_key else None

        return ChatAnthropic(
            model=config.model,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens_to_sample=config.max_tokens,
        )

    raise PptAgentError(
        f"Unknown llm_provider '{config.llm_provider}'. "
        "Supported values: 'openai_compatible', 'anthropic'."
    )
