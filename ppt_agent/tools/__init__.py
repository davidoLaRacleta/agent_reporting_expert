"""Concrete PowerPoint operations exposed to the LLM as callable tools.

Each ``*_tools.py`` module owns one area of functionality (slides, text,
shapes, images, charts, tables, context) and registers its tools -- schema
plus handler -- onto a shared ``ToolRegistry`` via a ``register(...)``
function. See ``tools.registry`` for the registry itself and
``build_default_registry`` in this module for how everything is wired
together.
"""

from __future__ import annotations

from ppt_agent.context.store import ContextStore
from ppt_agent.presentation.manager import PresentationManager
from ppt_agent.tools.registry import ToolRegistry


def build_default_registry(
    presentation_manager: PresentationManager,
    context_store: ContextStore,
) -> ToolRegistry:
    """Create a ``ToolRegistry`` with every built-in tool module registered."""
    from ppt_agent.tools import (
        chart_tools,
        context_tools,
        image_tools,
        presentation_tools,
        shape_tools,
        table_tools,
        text_tools,
    )

    registry = ToolRegistry()
    presentation_tools.register(registry, presentation_manager)
    text_tools.register(registry, presentation_manager)
    shape_tools.register(registry, presentation_manager)
    image_tools.register(registry, presentation_manager)
    chart_tools.register(registry, presentation_manager)
    table_tools.register(registry, presentation_manager)
    context_tools.register(registry, context_store)
    return registry
