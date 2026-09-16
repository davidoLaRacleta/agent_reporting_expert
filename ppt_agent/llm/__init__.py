"""Pluggable connectors to a chat-completion LLM backend.

The rest of the codebase only depends on the small interface defined in
``llm.base`` (``LLMClient``, ``ChatMessage``, ``ToolCall``). Concrete
backends translate that generic representation to/from a specific wire
format, so swapping a local model for a hosted one is a one-line config
change in ``llm.factory``.
"""

from ppt_agent.llm.base import ChatMessage, LLMClient, ToolCall

__all__ = ["ChatMessage", "LLMClient", "ToolCall"]
