"""Custom exceptions shared across the ppt_agent package."""


class PptAgentError(Exception):
    """Base class for all errors raised intentionally by ppt_agent."""


class ToolExecutionError(PptAgentError):
    """Raised by a tool handler when it cannot complete the requested action.

    The message is surfaced back to the LLM as the tool's result, so it
    should be phrased as actionable feedback (e.g. what was wrong and what
    the caller could try instead) rather than an internal stack trace.
    """


class LlmConnectionError(PptAgentError):
    """Raised when the configured LLM backend cannot be reached or fails."""
