"""Backend-agnostic chat/tool-calling primitives.

Every LLM backend (a hosted API, a local Ollama/LM Studio server, ...)
speaks its own wire format for messages and tool/function calling. To keep
the agent loop and tool registry independent of any single provider, all
backends convert to and from the small set of types defined here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A single tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict


@dataclass
class ChatMessage:
    """One turn in the conversation, in a provider-neutral shape.

    Attributes:
        role: One of "system", "user", "assistant", or "tool".
        content: Plain-text content. Empty string for assistant turns that
            only carry tool calls.
        tool_calls: Populated on assistant messages that request one or
            more tool invocations.
        tool_call_id: Populated on "tool" messages to link the result back
            to the ``ToolCall.id`` it answers.
        name: Populated on "tool" messages with the tool's name (some
            backends require it alongside ``tool_call_id``).
    """

    role: str
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class LLMClient(ABC):
    """Interface every LLM backend must implement.

    A backend receives the full conversation history plus the JSON-schema
    tool definitions the agent currently exposes, and must return exactly
    one new assistant ``ChatMessage`` (which may contain tool calls, plain
    text, or both).
    """

    @abstractmethod
    def chat(self, messages: list[ChatMessage], tools: list[dict]) -> ChatMessage:
        """Send the conversation so far and return the assistant's reply.

        Args:
            messages: Full conversation history, oldest first, including
                the leading system message.
            tools: Tool definitions in OpenAI function-calling format:
                ``{"type": "function", "function": {"name", "description",
                "parameters"}}``. Backends adapt this shape as needed.

        Returns:
            A new ``ChatMessage`` with role "assistant".
        """
        raise NotImplementedError
