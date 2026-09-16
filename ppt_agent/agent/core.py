"""``ReportingAgent``: drives the LLM <-> tool-call loop for one conversation.

The agent keeps the full message history, sends it to the configured
``LLMClient`` on every user turn, executes any tool calls the model
requests via the ``ToolRegistry``, feeds the results back, and repeats
until the model responds with plain text (or a safety cap is hit).
"""

from __future__ import annotations

from collections.abc import Callable

from ppt_agent.agent.prompts import SYSTEM_PROMPT
from ppt_agent.llm.base import ChatMessage, LLMClient
from ppt_agent.tools.registry import ToolRegistry

# Called with (tool_name, arguments) before a tool runs, and (tool_name, result)
# after -- lets the CLI print progress without the agent depending on any UI.
ToolCallObserver = Callable[[str, dict], None]
ToolResultObserver = Callable[[str, str], None]


class ReportingAgent:
    """Ties an ``LLMClient`` and a ``ToolRegistry`` into a conversational agent."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        system_prompt: str = SYSTEM_PROMPT,
        max_tool_iterations: int = 8,
        on_tool_call: ToolCallObserver | None = None,
        on_tool_result: ToolResultObserver | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._max_tool_iterations = max_tool_iterations
        self._on_tool_call = on_tool_call
        self._on_tool_result = on_tool_result
        self.history: list[ChatMessage] = [
            ChatMessage(role="system", content=system_prompt)
        ]

    def send_user_message(self, text: str) -> str:
        """Send one user message and return the agent's final text reply.

        Internally this may loop several times, executing tool calls and
        feeding their results back to the model, before a final plain-text
        reply is produced.
        """
        self.history.append(ChatMessage(role="user", content=text))

        for _ in range(self._max_tool_iterations):
            assistant_message = self._llm_client.chat(
                self.history, self._tool_registry.schemas()
            )
            self.history.append(assistant_message)

            if not assistant_message.tool_calls:
                return assistant_message.content

            for tool_call in assistant_message.tool_calls:
                if self._on_tool_call:
                    self._on_tool_call(tool_call.name, tool_call.arguments)

                result_text = self._tool_registry.dispatch(
                    tool_call.name, tool_call.arguments
                )

                if self._on_tool_result:
                    self._on_tool_result(tool_call.name, result_text)

                self.history.append(
                    ChatMessage(
                        role="tool",
                        content=result_text,
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                )

        return (
            "I made a lot of tool calls without reaching a final answer "
            f"(hit the {self._max_tool_iterations}-iteration safety limit). "
            "Please check the presentation state and try rephrasing your request."
        )

    def reset(self) -> None:
        """Clear conversation history, keeping only the system prompt.

        Note this does not touch the presentation itself -- slides already
        created remain, since they live in the shared ``PresentationManager``.
        """
        system_message = self.history[0]
        self.history = [system_message]
