"""Tests for ReportingAgent, using a scripted fake chat model.

No network/model server is involved: ``FakeToolCallingChatModel`` is a
minimal ``BaseChatModel`` that replays a fixed sequence of ``AIMessage``
replies (including ones with ``tool_calls``), which is enough to exercise
the full LangGraph tool-calling loop deterministically.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from pydantic import Field

from ppt_agent.agent.core import ReportingAgent


class FakeToolCallingChatModel(BaseChatModel):
    """Replays scripted ``AIMessage`` replies instead of calling a real model."""

    responses: list[AIMessage] = Field(default_factory=list)
    call_count: int = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        message = self.responses[self.call_count]
        self.call_count += 1
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling-chat-model"


@tool
def echo(text: str) -> str:
    """Echo back the given text."""
    return f"echoed: {text}"


@tool
def boom() -> str:
    """A tool that always raises, to exercise error handling."""
    raise ValueError("kaboom")


def _tool_call(name: str, args: dict, call_id: str) -> dict:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def test_agent_returns_plain_text_when_no_tool_calls_requested():
    model = FakeToolCallingChatModel(responses=[AIMessage(content="Hello there!")])
    agent = ReportingAgent(model, [echo])

    reply = agent.send_user_message("hi")

    assert reply == "Hello there!"


def test_agent_executes_tool_call_then_returns_final_reply():
    model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("echo", {"text": "hi"}, "call_1")]),
            AIMessage(content="Done."),
        ]
    )
    tool_calls_seen = []
    tool_results_seen = []
    agent = ReportingAgent(
        model,
        [echo],
        on_tool_call=lambda name, args: tool_calls_seen.append((name, args)),
        on_tool_result=lambda name, result: tool_results_seen.append((name, result)),
    )

    reply = agent.send_user_message("please echo hi")

    assert reply == "Done."
    assert tool_calls_seen == [("echo", {"text": "hi"})]
    assert tool_results_seen == [("echo", "echoed: hi")]


def test_tool_exception_is_reported_and_fed_back_to_the_model():
    model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("boom", {}, "call_1")]),
            AIMessage(content="Handled the error."),
        ]
    )
    tool_results_seen = []
    agent = ReportingAgent(model, [boom], on_tool_result=lambda name, result: tool_results_seen.append(result))

    reply = agent.send_user_message("please break")

    assert reply == "Handled the error."
    assert len(tool_results_seen) == 1
    assert "kaboom" in tool_results_seen[0]


def test_agent_reports_safety_limit_instead_of_looping_forever():
    infinite_tool_calls = [
        AIMessage(content="", tool_calls=[_tool_call("echo", {"text": "loop"}, f"call_{i}")]) for i in range(10)
    ]
    model = FakeToolCallingChatModel(responses=infinite_tool_calls)
    agent = ReportingAgent(model, [echo], max_tool_iterations=2)

    reply = agent.send_user_message("loop forever")

    assert "iteration safety limit" in reply


def test_reset_starts_a_new_conversation_thread():
    model = FakeToolCallingChatModel(responses=[AIMessage(content="first"), AIMessage(content="second")])
    agent = ReportingAgent(model, [echo])
    first_thread_id = agent._thread_id

    agent.send_user_message("hi")
    agent.reset()

    assert agent._thread_id != first_thread_id
