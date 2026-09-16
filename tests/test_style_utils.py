import pytest
from pptx.dml.color import RGBColor

from ppt_agent.presentation.style_utils import hex_to_rgb_color


def test_hex_to_rgb_color_accepts_hash_prefix():
    assert hex_to_rgb_color("#1F4E79") == RGBColor(0x1F, 0x4E, 0x79)


def test_hex_to_rgb_color_accepts_bare_hex_lowercase():
    assert hex_to_rgb_color("1f4e79") == RGBColor(0x1F, 0x4E, 0x79)


@pytest.mark.parametrize("bad_value", ["red", "#12345", "#1234567", ""])
def test_hex_to_rgb_color_rejects_invalid_input(bad_value):
    with pytest.raises(ValueError):
        hex_to_rgb_color(bad_value)
