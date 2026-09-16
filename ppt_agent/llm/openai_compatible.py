"""LLM backend for any OpenAI-compatible chat-completions endpoint.

This covers OpenAI itself as well as the many local servers that expose
the same API surface, e.g. Ollama (``http://localhost:11434/v1``) and
LM Studio (``http://localhost:1234/v1``). Because they all speak the same
protocol, one client implementation serves them all -- only ``base_url``,
``api_key`` and ``model`` change.
"""

from __future__ import annotations

import json

from ppt_agent.exceptions import LlmConnectionError
from ppt_agent.llm.base import ChatMessage, LLMClient, ToolCall


class OpenAICompatibleClient(LLMClient):
    """Talks to a chat-completions endpoint via the ``openai`` SDK."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> None:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - exercised only when dep missing
            raise LlmConnectionError(
                "The 'openai' package is required for the openai_compatible "
                "backend. Install it with `pip install openai`."
            ) from exc

        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def chat(self, messages: list[ChatMessage], tools: list[dict]) -> ChatMessage:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[_to_openai_message(message) for message in messages],
                tools=tools or None,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/network failure uniformly
            raise LlmConnectionError(
                f"OpenAI-compatible backend request failed: {exc}"
            ) from exc

        choice_message = response.choices[0].message
        return _from_openai_message(choice_message)


def _to_openai_message(message: ChatMessage) -> dict:
    """Convert a generic ``ChatMessage`` into an OpenAI wire-format dict."""
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content,
        }

    if message.role == "assistant" and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.arguments),
                    },
                }
                for tool_call in message.tool_calls
            ],
        }

    return {"role": message.role, "content": message.content}


def _from_openai_message(choice_message) -> ChatMessage:
    """Convert an OpenAI SDK response message into a generic ``ChatMessage``."""
    tool_calls = []
    for raw_call in choice_message.tool_calls or []:
        try:
            arguments = json.loads(raw_call.function.arguments or "{}")
        except json.JSONDecodeError:
            arguments = {}
        tool_calls.append(
            ToolCall(id=raw_call.id, name=raw_call.function.name, arguments=arguments)
        )

    return ChatMessage(
        role="assistant",
        content=choice_message.content or "",
        tool_calls=tool_calls,
    )
