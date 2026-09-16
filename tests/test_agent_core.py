from ppt_agent.agent.core import ReportingAgent
from ppt_agent.llm.base import ChatMessage, LLMClient, ToolCall
from ppt_agent.tools.registry import ToolRegistry


class ScriptedLLMClient(LLMClient):
    """Replays a fixed sequence of assistant replies, for testing the agent
    loop without a real model. Each call to chat() returns the next reply."""

    def __init__(self, replies):
        self._replies = list(replies)

    def chat(self, messages, tools):
        return self._replies.pop(0)


def build_registry_with_echo_tool():
    registry = ToolRegistry()
    registry.add(
        name="echo",
        description="Echo back the given text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=lambda text: f"echoed: {text}",
    )
    return registry


def test_agent_returns_plain_text_when_no_tool_calls_requested():
    llm_client = ScriptedLLMClient(
        [ChatMessage(role="assistant", content="Hello there!")]
    )
    agent = ReportingAgent(llm_client, ToolRegistry())

    reply = agent.send_user_message("hi")

    assert reply == "Hello there!"


def test_agent_executes_tool_call_then_returns_final_reply():
    tool_call = ToolCall(id="call_1", name="echo", arguments={"text": "hi"})
    llm_client = ScriptedLLMClient(
        [
            ChatMessage(role="assistant", content="", tool_calls=[tool_call]),
            ChatMessage(role="assistant", content="Done."),
        ]
    )
    agent = ReportingAgent(llm_client, build_registry_with_echo_tool())

    reply = agent.send_user_message("please echo hi")

    assert reply == "Done."
    tool_result_messages = [m for m in agent.history if m.role == "tool"]
    assert tool_result_messages[0].content == "echoed: hi"
    assert tool_result_messages[0].tool_call_id == "call_1"


def test_agent_stops_after_max_tool_iterations():
    tool_call = ToolCall(id="call_1", name="echo", arguments={"text": "loop"})
    infinite_tool_calls = ChatMessage(
        role="assistant", content="", tool_calls=[tool_call]
    )
    llm_client = ScriptedLLMClient([infinite_tool_calls] * 3)
    agent = ReportingAgent(
        llm_client, build_registry_with_echo_tool(), max_tool_iterations=3
    )

    reply = agent.send_user_message("loop forever")

    assert "iteration safety limit" in reply


def test_reset_clears_history_but_keeps_system_prompt():
    llm_client = ScriptedLLMClient([ChatMessage(role="assistant", content="ok")])
    agent = ReportingAgent(llm_client, ToolRegistry(), system_prompt="SYSTEM")
    agent.send_user_message("hi")

    agent.reset()

    assert len(agent.history) == 1
    assert agent.history[0].role == "system"
    assert agent.history[0].content == "SYSTEM"


def test_tool_registry_dispatch_reports_unknown_tool():
    registry = ToolRegistry()
    result = registry.dispatch("does_not_exist", {})
    assert "unknown tool" in result


def test_tool_registry_dispatch_catches_handler_exceptions():
    registry = ToolRegistry()
    registry.add(
        name="boom",
        description="Always fails.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: (_ for _ in ()).throw(RuntimeError("kaboom")),
    )
    result = registry.dispatch("boom", {})
    assert "failed unexpectedly" in result
