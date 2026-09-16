"""Builds the LangChain chat model that powers the agent.

The rest of the codebase depends only on LangChain's ``BaseChatModel``
interface (via ``langchain_core``), not on any specific provider. Swapping
a local model for a hosted one is a config change handled in
``llm.factory``.
"""

from ppt_agent.llm.factory import build_chat_model

__all__ = ["build_chat_model"]
