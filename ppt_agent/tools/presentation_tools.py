"""Tools for creating, opening, saving, and navigating a presentation."""

from __future__ import annotations

from ppt_agent.presentation.manager import LAYOUT_NAME_TO_INDEX, PresentationManager
from ppt_agent.tools.registry import ToolRegistry


def register(registry: ToolRegistry, manager: PresentationManager) -> None:
    """Register all presentation-lifecycle tools onto ``registry``."""

    def create_presentation(template_path: str | None = None) -> str:
        manager.new(template_path)
        base = f" from template '{template_path}'" if template_path else ""
        return f"Created a new, empty presentation{base}."

    registry.add(
        name="create_presentation",
        description=(
            "Start a brand new, empty presentation, discarding any presentation "
            "currently open in memory (does not delete files on disk). Optionally "
            "base it on a .pptx template file to inherit its theme and layouts."
        ),
        parameters={
            "type": "object",
            "properties": {
                "template_path": {
                    "type": "string",
                    "description": "Path to a .pptx file to use as a starting template.",
                }
            },
        },
        handler=create_presentation,
    )

    def open_presentation(path: str) -> str:
        manager.open(path)
        slide_count = len(manager.list_slides())
        return f"Opened '{path}' ({slide_count} slide(s))."

    registry.add(
        name="open_presentation",
        description="Open an existing .pptx file for viewing and editing.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the .pptx file to open.",
                }
            },
            "required": ["path"],
        },
        handler=open_presentation,
    )

    def save_presentation(path: str | None = None) -> str:
        saved_path = manager.save(path)
        return f"Saved presentation to '{saved_path}'."

    registry.add(
        name="save_presentation",
        description=(
            "Save the current presentation to disk. If no path is given, saves to "
            "the path it was last opened from or saved to."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Destination .pptx path. Optional if the presentation already has one.",
                }
            },
        },
        handler=save_presentation,
    )

    def add_slide(layout: str = "title_and_content", title: str | None = None) -> str:
        index = manager.add_slide(layout=layout, title=title)
        return f"Added slide {index} using layout '{layout}'" + (
            f" with title '{title}'." if title else "."
        )

    registry.add(
        name="add_slide",
        description=(
            "Append a new slide to the presentation and make it the active slide. "
            f"Available layouts: {sorted(LAYOUT_NAME_TO_INDEX)}."
        ),
        parameters={
            "type": "object",
            "properties": {
                "layout": {
                    "type": "string",
                    "enum": sorted(LAYOUT_NAME_TO_INDEX),
                    "description": "Slide layout to use.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title text for the new slide.",
                },
            },
        },
        handler=add_slide,
    )

    def delete_slide(slide_index: int) -> str:
        manager.delete_slide(slide_index)
        return f"Deleted slide {slide_index}."

    registry.add(
        name="delete_slide",
        description="Remove a slide from the presentation by its 0-based index.",
        parameters={
            "type": "object",
            "properties": {
                "slide_index": {
                    "type": "integer",
                    "description": "0-based index of the slide to remove.",
                }
            },
            "required": ["slide_index"],
        },
        handler=delete_slide,
    )

    def set_active_slide(slide_index: int) -> str:
        resolved_index = manager.resolve_slide_index(slide_index)
        return f"Slide {resolved_index} is now active."

    registry.add(
        name="set_active_slide",
        description=(
            "Change which slide subsequent tool calls act on by default when they "
            "omit slide_index."
        ),
        parameters={
            "type": "object",
            "properties": {
                "slide_index": {
                    "type": "integer",
                    "description": "0-based index of the slide to activate.",
                }
            },
            "required": ["slide_index"],
        },
        handler=set_active_slide,
    )

    def list_slides() -> str:
        slides = manager.list_slides()
        if not slides:
            return "The presentation has no slides yet."
        lines = [
            f"[{s['index']}]{' (active)' if s['is_active'] else ''} "
            f"title='{s['title']}' shapes={s['shape_count']}"
            for s in slides
        ]
        return "\n".join(lines)

    registry.add(
        name="list_slides",
        description="List every slide with its index, title, shape count, and whether it is active.",
        parameters={"type": "object", "properties": {}},
        handler=list_slides,
    )
