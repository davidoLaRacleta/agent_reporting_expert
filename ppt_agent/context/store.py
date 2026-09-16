"""In-memory store of documents loaded into the agent's context.

The store deliberately does not do anything fancy (no embeddings, no
vector search): it holds raw extracted text and offers a simple keyword
search over paragraphs. That is enough for an LLM tool call to pull a
relevant snippet before writing slide content, while keeping the module
dependency-free and easy to reason about.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ppt_agent.context.loader import extract_text


@dataclass
class ContextDocument:
    """A single document that has been loaded into context."""

    doc_id: str
    path: Path
    text: str


class ContextStore:
    """Holds loaded documents and offers a naive keyword search over them."""

    def __init__(self) -> None:
        self._documents: dict[str, ContextDocument] = {}
        self._next_id = 1

    def add_document(self, path: str) -> ContextDocument:
        """Load a document from disk and register it under a new doc_id."""
        resolved_path = Path(path).expanduser().resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Document not found: {resolved_path}")

        text = extract_text(resolved_path)
        doc_id = f"doc{self._next_id}"
        self._next_id += 1

        document = ContextDocument(doc_id=doc_id, path=resolved_path, text=text)
        self._documents[doc_id] = document
        return document

    def list_documents(self) -> list[ContextDocument]:
        return list(self._documents.values())

    def get(self, doc_id: str) -> ContextDocument:
        try:
            return self._documents[doc_id]
        except KeyError as exc:
            known_ids = sorted(self._documents)
            raise KeyError(
                f"Unknown doc_id '{doc_id}'. Loaded documents: {known_ids}"
            ) from exc

    def search(self, query: str, max_results: int = 5) -> list[tuple[str, str]]:
        """Return the top paragraphs across all documents matching ``query``.

        Scoring is a plain term-frequency count over lowercased whitespace
        tokens -- intentionally simple, since this only needs to surface
        plausibly-relevant snippets for the LLM to read and rephrase, not
        to rank precisely.

        Returns:
            A list of ``(doc_id, paragraph)`` tuples, best matches first.
        """
        query_terms = [term for term in query.lower().split() if term]
        if not query_terms:
            return []

        scored_paragraphs: list[tuple[int, str, str]] = []
        for document in self._documents.values():
            for paragraph in document.text.split("\n"):
                stripped = paragraph.strip()
                if not stripped:
                    continue
                lowered = stripped.lower()
                score = sum(lowered.count(term) for term in query_terms)
                if score > 0:
                    scored_paragraphs.append((score, document.doc_id, stripped))

        scored_paragraphs.sort(key=lambda item: item[0], reverse=True)
        return [
            (doc_id, paragraph)
            for _, doc_id, paragraph in scored_paragraphs[:max_results]
        ]
