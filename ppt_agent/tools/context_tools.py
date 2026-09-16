"""Tools that let the LLM pull in content from documents loaded into context.

These wrap ``ContextStore`` so the agent can decide, mid-conversation, to
load a reference document, list what's loaded, and search or read it
before drafting slide content grounded in the source material.
"""

from __future__ import annotations

from ppt_agent.context.store import ContextStore
from ppt_agent.tools.registry import ToolRegistry

_DEFAULT_MAX_CHARS = 4000


def register(registry: ToolRegistry, context_store: ContextStore) -> None:
    """Register document-context tools onto ``registry``."""

    def load_document(path: str) -> str:
        document = context_store.add_document(path)
        preview = document.text[:200].replace("\n", " ")
        return (
            f"Loaded '{document.path.name}' as {document.doc_id} "
            f"({len(document.text)} characters). Preview: {preview!r}"
        )

    registry.add(
        name="load_document",
        description="Load a .txt, .md, .docx, or .pdf file into context so its content can be reused in slides.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the document to load.",
                }
            },
            "required": ["path"],
        },
        handler=load_document,
    )

    def list_documents() -> str:
        documents = context_store.list_documents()
        if not documents:
            return "No documents are loaded into context yet."
        return "\n".join(
            f"{doc.doc_id}: {doc.path} ({len(doc.text)} characters)"
            for doc in documents
        )

    registry.add(
        name="list_documents",
        description="List every document currently loaded into context.",
        parameters={"type": "object", "properties": {}},
        handler=list_documents,
    )

    def get_document_text(doc_id: str, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
        try:
            document = context_store.get(doc_id)
        except KeyError as exc:
            return f"Error: {exc}"
        text = document.text
        if len(text) > max_chars:
            return (
                text[:max_chars]
                + f"\n...[truncated, {len(text) - max_chars} more characters]"
            )
        return text

    registry.add(
        name="get_document_text",
        description="Read (a prefix of) the full extracted text of a loaded document.",
        parameters={
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "doc_id returned by load_document or list_documents.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return.",
                },
            },
            "required": ["doc_id"],
        },
        handler=get_document_text,
    )

    def search_context(query: str, max_results: int = 5) -> str:
        matches = context_store.search(query, max_results=max_results)
        if not matches:
            return f"No matches for '{query}' in the loaded documents."
        return "\n".join(f"[{doc_id}] {paragraph}" for doc_id, paragraph in matches)

    registry.add(
        name="search_context",
        description="Keyword-search all loaded documents and return the most relevant paragraphs.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of paragraphs to return.",
                },
            },
            "required": ["query"],
        },
        handler=search_context,
    )
