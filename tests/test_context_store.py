import pytest

from ppt_agent.context.store import ContextStore


def test_add_document_reads_text_and_assigns_incrementing_ids(tmp_path):
    first_path = tmp_path / "first.txt"
    first_path.write_text("Revenue grew 12% this quarter.")
    second_path = tmp_path / "second.md"
    second_path.write_text("# Notes\nChurn stayed flat.")

    store = ContextStore()
    first_doc = store.add_document(str(first_path))
    second_doc = store.add_document(str(second_path))

    assert first_doc.doc_id == "doc1"
    assert second_doc.doc_id == "doc2"
    assert "Revenue grew" in first_doc.text


def test_add_document_missing_file_raises(tmp_path):
    store = ContextStore()
    with pytest.raises(FileNotFoundError):
        store.add_document(str(tmp_path / "missing.txt"))


def test_get_unknown_doc_id_raises_with_helpful_message(tmp_path):
    store = ContextStore()
    with pytest.raises(KeyError, match="Unknown doc_id"):
        store.get("doc99")


def test_search_ranks_paragraphs_by_term_frequency(tmp_path):
    path = tmp_path / "report.txt"
    path.write_text(
        "Revenue revenue revenue was strong.\n"
        "Headcount grew modestly.\n"
        "Revenue was the main driver.\n"
    )
    store = ContextStore()
    store.add_document(str(path))

    results = store.search("revenue", max_results=2)

    assert len(results) == 2
    assert "Revenue revenue revenue" in results[0][1]


def test_search_with_no_matches_returns_empty_list(tmp_path):
    path = tmp_path / "report.txt"
    path.write_text("Nothing relevant here.")
    store = ContextStore()
    store.add_document(str(path))

    assert store.search("nonexistent_term") == []
