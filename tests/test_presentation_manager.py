import pytest

from ppt_agent.exceptions import ToolExecutionError
from ppt_agent.presentation.manager import PresentationManager


def test_requires_a_presentation_before_adding_slides():
    manager = PresentationManager()
    with pytest.raises(ToolExecutionError):
        manager.add_slide()


def test_add_slide_sets_title_and_becomes_active():
    manager = PresentationManager()
    manager.new()

    index = manager.add_slide(layout="title_and_content", title="Hello")

    assert index == 0
    slides = manager.list_slides()
    # "title_and_content" contributes two placeholders: title + body.
    assert slides == [
        {"index": 0, "title": "Hello", "shape_count": 2, "is_active": True}
    ]


def test_unknown_layout_raises_tool_execution_error():
    manager = PresentationManager()
    manager.new()
    with pytest.raises(ToolExecutionError, match="Unknown layout"):
        manager.add_slide(layout="not_a_real_layout")


def test_resolve_slide_index_out_of_range():
    manager = PresentationManager()
    manager.new()
    manager.add_slide()
    with pytest.raises(ToolExecutionError, match="out of range"):
        manager.resolve_slide_index(5)


def test_get_slide_defaults_to_active_slide():
    manager = PresentationManager()
    manager.new()
    manager.add_slide(title="First")
    manager.add_slide(title="Second")

    active_slide = manager.get_slide(None)

    assert active_slide.shapes.title.text == "Second"


def test_delete_slide_updates_active_index():
    manager = PresentationManager()
    manager.new()
    manager.add_slide(title="First")
    manager.add_slide(title="Second")

    manager.delete_slide(1)

    slides = manager.list_slides()
    assert len(slides) == 1
    assert slides[0]["title"] == "First"


def test_save_without_known_path_raises():
    manager = PresentationManager()
    manager.new()
    with pytest.raises(ToolExecutionError, match="No file path"):
        manager.save()


def test_save_and_reopen_round_trip(tmp_path):
    manager = PresentationManager()
    manager.new()
    manager.add_slide(title="Round trip")
    output_path = tmp_path / "deck.pptx"

    manager.save(str(output_path))

    reopened = PresentationManager()
    reopened.open(str(output_path))
    assert reopened.list_slides()[0]["title"] == "Round trip"
