"""Concrete PowerPoint operations exposed to the LLM as LangChain tools.

Each ``*_tools.py`` module owns one area of functionality (slides, text,
shapes, images, charts, tables, context) and exposes a ``build_tools(...)``
function that returns a list of ``StructuredTool`` instances closed over
the shared state they operate on (``PresentationManager``/``ContextStore``).
``build_default_tools`` below wires every module together for the agent.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from ppt_agent.context.store import ContextStore
from ppt_agent.presentation.manager import PresentationManager


def build_default_tools(
    presentation_manager: PresentationManager,
    context_store: ContextStore,
) -> list[StructuredTool]:
    """Build every built-in tool, bound to the given shared state."""
    from ppt_agent.tools import (
        chart_tools,
        context_tools,
        image_tools,
        presentation_tools,
        shape_tools,
        table_tools,
        text_tools,
    )

    return [
        *presentation_tools.build_tools(presentation_manager),
        *text_tools.build_tools(presentation_manager),
        *shape_tools.build_tools(presentation_manager),
        *image_tools.build_tools(presentation_manager),
        *chart_tools.build_tools(presentation_manager),
        *table_tools.build_tools(presentation_manager),
        *context_tools.build_tools(context_store),
    ]
