"""Tools for placing images on a slide."""

from __future__ import annotations

from pathlib import Path

from pptx.util import Inches

from ppt_agent.exceptions import ToolExecutionError
from ppt_agent.presentation.manager import PresentationManager
from ppt_agent.tools.registry import ToolRegistry


def register(registry: ToolRegistry, manager: PresentationManager) -> None:
    """Register image-related tools onto ``registry``."""

    def add_image(
        image_path: str,
        slide_index: int | None = None,
        left: float = 1.0,
        top: float = 1.0,
        width: float | None = None,
        height: float | None = None,
    ) -> str:
        resolved_path = Path(image_path).expanduser().resolve()
        if not resolved_path.exists():
            raise ToolExecutionError(f"Image file not found: {resolved_path}")

        slide = manager.get_slide(slide_index)
        size_kwargs = {}
        if width is not None:
            size_kwargs["width"] = Inches(width)
        if height is not None:
            size_kwargs["height"] = Inches(height)

        # Omitting a dimension keeps python-pptx's native aspect-ratio scaling.
        slide.shapes.add_picture(
            str(resolved_path), Inches(left), Inches(top), **size_kwargs
        )
        return f"Added image '{resolved_path.name}' to slide {manager.resolve_slide_index(slide_index)}."

    registry.add(
        name="add_image",
        description=(
            "Insert an image file onto a slide. Omit width/height to keep the "
            "image's original aspect ratio while scaling by whichever dimension is given."
        ),
        parameters={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to a local image file (png, jpg, etc.).",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "Defaults to the active slide.",
                },
                "left": {"type": "number", "description": "Left position in inches."},
                "top": {"type": "number", "description": "Top position in inches."},
                "width": {
                    "type": "number",
                    "description": "Width in inches. Optional.",
                },
                "height": {
                    "type": "number",
                    "description": "Height in inches. Optional.",
                },
            },
            "required": ["image_path"],
        },
        handler=add_image,
    )
