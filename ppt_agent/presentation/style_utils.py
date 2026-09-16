"""Small formatting helpers shared by the shape/text/chart tool modules."""

from __future__ import annotations

import re

from pptx.dml.color import RGBColor

_HEX_COLOR_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def hex_to_rgb_color(hex_color: str) -> RGBColor:
    """Convert a "#RRGGBB" or "RRGGBB" string into an ``RGBColor``.

    Raises:
        ValueError: If ``hex_color`` is not a 6-digit hex color.
    """
    if not _HEX_COLOR_RE.match(hex_color):
        raise ValueError(
            f"Invalid color '{hex_color}'. Expected a 6-digit hex value, e.g. '1F4E79' or '#1F4E79'."
        )
    return RGBColor.from_string(hex_color.lstrip("#").upper())
