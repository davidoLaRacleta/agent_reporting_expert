"""Tools for creating, opening, saving, and navigating a presentation."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ppt_agent.presentation.manager import LAYOUT_NAME_TO_INDEX, PresentationManager


class CreatePresentationInput(BaseModel):
    template_path: str | None = Field(
        default=None, description="Path to a .pptx file to use as a starting template."
    )


class OpenPresentationInput(BaseModel):
    path: str = Field(description="Path to the .pptx file to open.")


class SavePresentationInput(BaseModel):
    path: str | None = Field(
        default=None, description="Destination .pptx path. Optional if the presentation already has one."
    )


class AddSlideInput(BaseModel):
    layout: str = Field(
        default="title_and_content",
        description=f"Slide layout to use. Supported: {sorted(LAYOUT_NAME_TO_INDEX)}.",
    )
    title: str | None = Field(default=None, description="Optional title text for the new slide.")


class DeleteSlideInput(BaseModel):
    slide_index: int = Field(description="0-based index of the slide to remove.")


class SetActiveSlideInput(BaseModel):
    slide_index: int = Field(description="0-based index of the slide to activate.")


def build_tools(manager: PresentationManager) -> list[StructuredTool]:
    """Build presentation-lifecycle tools bound to ``manager``."""

    def create_presentation(template_path: str | None = None) -> str:
        manager.new(template_path)
        base = f" from template '{template_path}'" if template_path else ""
        return f"Created a new, empty presentation{base}."

    def open_presentation(path: str) -> str:
        manager.open(path)
        slide_count = len(manager.list_slides())
        return f"Opened '{path}' ({slide_count} slide(s))."

    def save_presentation(path: str | None = None) -> str:
        saved_path = manager.save(path)
        return f"Saved presentation to '{saved_path}'."

    def add_slide(layout: str = "title_and_content", title: str | None = None) -> str:
        index = manager.add_slide(layout=layout, title=title)
        return f"Added slide {index} using layout '{layout}'" + (f" with title '{title}'." if title else ".")

    def delete_slide(slide_index: int) -> str:
        manager.delete_slide(slide_index)
        return f"Deleted slide {slide_index}."

    def set_active_slide(slide_index: int) -> str:
        resolved_index = manager.resolve_slide_index(slide_index)
        return f"Slide {resolved_index} is now active."

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

    return [
        StructuredTool.from_function(
            func=create_presentation,
            name="create_presentation",
            description=(
                "Start a brand new, empty presentation, discarding any presentation "
                "currently open in memory (does not delete files on disk). Optionally "
                "base it on a .pptx template file to inherit its theme and layouts."
            ),
            args_schema=CreatePresentationInput,
        ),
        StructuredTool.from_function(
            func=open_presentation,
            name="open_presentation",
            description="Open an existing .pptx file for viewing and editing.",
            args_schema=OpenPresentationInput,
        ),
        StructuredTool.from_function(
            func=save_presentation,
            name="save_presentation",
            description=(
                "Save the current presentation to disk. If no path is given, saves to "
                "the path it was last opened from or saved to."
            ),
            args_schema=SavePresentationInput,
        ),
        StructuredTool.from_function(
            func=add_slide,
            name="add_slide",
            description=(
                "Append a new slide to the presentation and make it the active slide. "
                f"Available layouts: {sorted(LAYOUT_NAME_TO_INDEX)}."
            ),
            args_schema=AddSlideInput,
        ),
        StructuredTool.from_function(
            func=delete_slide,
            name="delete_slide",
            description="Remove a slide from the presentation by its 0-based index.",
            args_schema=DeleteSlideInput,
        ),
        StructuredTool.from_function(
            func=set_active_slide,
            name="set_active_slide",
            description="Change which slide subsequent tool calls act on by default when they omit slide_index.",
            args_schema=SetActiveSlideInput,
        ),
        StructuredTool.from_function(
            func=list_slides,
            name="list_slides",
            description="List every slide with its index, title, shape count, and whether it is active.",
        ),
    ]
