"""``ReportingAgent``: a thin wrapper around a LangGraph ReAct agent.

LangGraph's ``create_react_agent`` implements the tool-calling loop (call
the model, run any requested tools, feed results back, repeat until the
model replies with plain text) and, via a checkpointer, the conversation
memory -- both used to be hand-rolled here. This module now only owns:
wiring the model/tools/prompt together, bridging LangChain's tool-run
callbacks to the CLI's transcript display, and translating LangGraph's
failure modes into a single friendly outcome for the caller.
"""

from __future__ import annotations

import uuid
import warnings
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.warnings import LangGraphDeprecatedSinceV10

from ppt_agent.agent.prompts import SYSTEM_PROMPT
from ppt_agent.exceptions import PptAgentError

# create_react_agent moved to langchain.agents in LangGraph 1.0 and will be
# removed from langgraph in 2.0; it still works identically today. We stay
# on the langgraph-native import rather than adding the full `langchain`
# meta-package as a dependency for this one call, so we silence just this
# warning instead of letting it leak into the CLI's output.
warnings.filterwarnings("ignore", category=LangGraphDeprecatedSinceV10)

ToolCallObserver = Callable[[str, dict], None]
ToolResultObserver = Callable[[str, str], None]

_SAFETY_LIMIT_MESSAGE_TEMPLATE = (
    "I made a lot of tool calls without reaching a final answer "
    "(hit the {max_tool_iterations}-iteration safety limit). "
    "Please check the presentation state and try rephrasing your request."
)


class _TranscriptCallbackHandler(BaseCallbackHandler):
    """Bridges LangChain's tool-run callbacks to the CLI's transcript hooks."""

    def __init__(
        self,
        on_tool_call: ToolCallObserver | None,
        on_tool_result: ToolResultObserver | None,
    ) -> None:
        self._on_tool_call = on_tool_call
        self._on_tool_result = on_tool_result
        self._tool_names_by_run_id: dict[UUID, str] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name", "tool")
        self._tool_names_by_run_id[run_id] = name
        if self._on_tool_call:
            self._on_tool_call(name, inputs or {})

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        name = self._tool_names_by_run_id.pop(run_id, getattr(output, "name", "tool"))
        if self._on_tool_result:
            self._on_tool_result(name, _stringify_tool_output(output))

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        name = self._tool_names_by_run_id.pop(run_id, "tool")
        if self._on_tool_result:
            self._on_tool_result(name, f"Error: {error}")


def _stringify_tool_output(output: Any) -> str:
    content = getattr(output, "content", output)
    return content if isinstance(content, str) else str(content)


class ReportingAgent:
    """Ties a chat model and a list of tools into a conversational agent."""

    def __init__(
        self,
        chat_model: BaseChatModel,
        tools: list[BaseTool],
        system_prompt: str = SYSTEM_PROMPT,
        max_tool_iterations: int = 8,
        on_tool_call: ToolCallObserver | None = None,
        on_tool_result: ToolResultObserver | None = None,
    ) -> None:
        self._max_tool_iterations = max_tool_iterations
        self._callback_handler = _TranscriptCallbackHandler(on_tool_call, on_tool_result)
        self._checkpointer = MemorySaver()
        self._thread_id = str(uuid.uuid4())

        # handle_tool_errors=True catches every exception a tool raises
        # (including our ToolExecutionError) and feeds it back to the model
        # as the tool's result, instead of crashing the run.
        tool_node = ToolNode(tools, handle_tool_errors=True)
        self._graph = create_react_agent(
            model=chat_model,
            tools=tool_node,
            prompt=system_prompt,
            checkpointer=self._checkpointer,
        )

    def send_user_message(self, text: str) -> str:
        """Send one user message and return the agent's final text reply."""
        config = {
            "configurable": {"thread_id": self._thread_id},
            "recursion_limit": self._max_tool_iterations * 2 + 1,
            "callbacks": [self._callback_handler],
        }
        safety_limit_message = _SAFETY_LIMIT_MESSAGE_TEMPLATE.format(
            max_tool_iterations=self._max_tool_iterations
        )

        try:
            result = self._graph.invoke({"messages": [HumanMessage(text)]}, config=config)
        except GraphRecursionError:
            return safety_limit_message
        except Exception as exc:
            raise PptAgentError(f"Agent run failed: {exc}") from exc

        final_message = result["messages"][-1]
        # A "clean" finish is a plain-text AIMessage with no pending tool
        # calls. Anything else (e.g. the run was cut off mid tool-call by
        # the recursion limit without LangGraph raising) is treated the
        # same as hitting the safety limit, rather than surfacing internal
        # state (an empty message or a raw tool result) as the reply.
        if isinstance(final_message, AIMessage) and not final_message.tool_calls:
            content = final_message.content
            return content if isinstance(content, str) else str(content)
        return safety_limit_message

    def reset(self) -> None:
        """Start a fresh conversation thread (presentation state is untouched)."""
        self._thread_id = str(uuid.uuid4())
