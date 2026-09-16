"""Tools for adding data tables to a slide."""

from __future__ import annotations

from pptx.util import Inches

from ppt_agent.exceptions import ToolExecutionError
from ppt_agent.presentation.manager import PresentationManager
from ppt_agent.tools.registry import ToolRegistry


def register(registry: ToolRegistry, manager: PresentationManager) -> None:
    """Register table-related tools onto ``registry``."""

    def add_table(
        rows: list[list[str]],
        slide_index: int | None = None,
        left: float = 1.0,
        top: float = 1.5,
        width: float = 8.0,
        height: float = 4.0,
        header_row: bool = True,
    ) -> str:
        if not rows or not rows[0]:
            raise ToolExecutionError(
                "rows must be a non-empty 2D list, e.g. [['A', 'B'], ['1', '2']]."
            )

        column_count = len(rows[0])
        for row_index, row in enumerate(rows):
            if len(row) != column_count:
                raise ToolExecutionError(
                    f"Row {row_index} has {len(row)} cell(s) but row 0 has {column_count}; "
                    "every row must have the same number of columns."
                )

        slide = manager.get_slide(slide_index)
        graphic_frame = slide.shapes.add_table(
            len(rows),
            column_count,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
        )
        table = graphic_frame.table
        for row_index, row_values in enumerate(rows):
            for column_index, cell_value in enumerate(row_values):
                cell = table.cell(row_index, column_index)
                cell.text = str(cell_value)
                if header_row and row_index == 0:
                    cell.text_frame.paragraphs[0].font.bold = True

        return (
            f"Added a {len(rows)}x{column_count} table to slide "
            f"{manager.resolve_slide_index(slide_index)}."
        )

    registry.add(
        name="add_table",
        description="Add a table to a slide from a 2D list of cell text, with an optional bold header row.",
        parameters={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                    "description": "Row-major 2D list of cell text. Every row must have the same length.",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "Defaults to the active slide.",
                },
                "left": {"type": "number", "description": "Left position in inches."},
                "top": {"type": "number", "description": "Top position in inches."},
                "width": {"type": "number", "description": "Width in inches."},
                "height": {"type": "number", "description": "Height in inches."},
                "header_row": {
                    "type": "boolean",
                    "description": "Bold the first row as a header.",
                },
            },
            "required": ["rows"],
        },
        handler=add_table,
    )
