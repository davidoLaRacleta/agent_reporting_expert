"""LLM backend for the hosted Anthropic Claude API.

Anthropic's Messages API differs from the OpenAI-style protocol in two
ways that matter here: the system prompt is a separate top-level
parameter (not a message in the list), and tool results are sent back as
``tool_result`` content blocks inside a *user* message rather than as
their own "tool" role. This module absorbs both differences so the rest
of the codebase never has to know about them.
"""

from __future__ import annotations

from ppt_agent.exceptions import LlmConnectionError
from ppt_agent.llm.base import ChatMessage, LLMClient, ToolCall


class AnthropicClient(LLMClient):
    """Talks to the Anthropic Messages API via the ``anthropic`` SDK."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only when dep missing
            raise LlmConnectionError(
                "The 'anthropic' package is required for the anthropic backend. "
                "Install it with `pip install anthropic`."
            ) from exc

        # api_key=None lets the SDK fall back to the ANTHROPIC_API_KEY env var.
        self._client = anthropic.Anthropic(api_key=api_key or None)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def chat(self, messages: list[ChatMessage], tools: list[dict]) -> ChatMessage:
        system_prompt, conversation = _split_system_prompt(messages)
        anthropic_messages = _to_anthropic_messages(conversation)
        anthropic_tools = [_to_anthropic_tool(tool) for tool in tools]

        try:
            response = self._client.messages.create(
                model=self._model,
                system=system_prompt,
                messages=anthropic_messages,
                tools=anthropic_tools or None,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/network failure uniformly
            raise LlmConnectionError(
                f"Anthropic backend request failed: {exc}"
            ) from exc

        return _from_anthropic_response(response)


def _split_system_prompt(messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
    """Pull the leading system message out, as Anthropic wants it separately."""
    system_parts = [m.content for m in messages if m.role == "system"]
    conversation = [m for m in messages if m.role != "system"]
    return "\n\n".join(system_parts), conversation


def _to_anthropic_tool(tool: dict) -> dict:
    """Convert an OpenAI-style function schema to Anthropic's tool shape."""
    function = tool["function"]
    return {
        "name": function["name"],
        "description": function.get("description", ""),
        "input_schema": function.get(
            "parameters", {"type": "object", "properties": {}}
        ),
    }


def _to_anthropic_messages(conversation: list[ChatMessage]) -> list[dict]:
    """Convert generic messages into Anthropic's message list.

    Consecutive "tool" messages are merged into a single user message
    containing multiple ``tool_result`` blocks, because Anthropic expects
    all results for one assistant turn's tool calls to arrive together.
    """
    anthropic_messages: list[dict] = []
    pending_tool_results: list[dict] = []

    def flush_tool_results() -> None:
        if pending_tool_results:
            anthropic_messages.append(
                {"role": "user", "content": list(pending_tool_results)}
            )
            pending_tool_results.clear()

    for message in conversation:
        if message.role == "tool":
            pending_tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": message.tool_call_id,
                    "content": message.content,
                }
            )
            continue

        flush_tool_results()

        if message.role == "assistant" and message.tool_calls:
            content = []
            if message.content:
                content.append({"type": "text", "text": message.content})
            for tool_call in message.tool_calls:
                content.append(
                    {
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.arguments,
                    }
                )
            anthropic_messages.append({"role": "assistant", "content": content})
        else:
            anthropic_messages.append(
                {"role": message.role, "content": message.content}
            )

    flush_tool_results()
    return anthropic_messages


def _from_anthropic_response(response) -> ChatMessage:
    """Convert an Anthropic Messages API response into a generic ``ChatMessage``."""
    text_parts = []
    tool_calls = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(id=block.id, name=block.name, arguments=block.input)
            )

    return ChatMessage(
        role="assistant", content="".join(text_parts), tool_calls=tool_calls
    )
