"""Tools that let the LLM pull in content from documents loaded into context.

These wrap ``ContextStore`` so the agent can decide, mid-conversation, to
load a reference document, list what's loaded, and search or read it
before drafting slide content grounded in the source material.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ppt_agent.context.store import ContextStore

_DEFAULT_MAX_CHARS = 4000


class LoadDocumentInput(BaseModel):
    path: str = Field(description="Path to the document to load.")


class GetDocumentTextInput(BaseModel):
    doc_id: str = Field(description="doc_id returned by load_document or list_documents.")
    max_chars: int = Field(default=_DEFAULT_MAX_CHARS, description="Maximum characters to return.")


class SearchContextInput(BaseModel):
    query: str
    max_results: int = Field(default=5, description="Maximum number of paragraphs to return.")


def build_tools(context_store: ContextStore) -> list[StructuredTool]:
    """Build document-context tools bound to ``context_store``."""

    def load_document(path: str) -> str:
        document = context_store.add_document(path)
        preview = document.text[:200].replace("\n", " ")
        return (
            f"Loaded '{document.path.name}' as {document.doc_id} "
            f"({len(document.text)} characters). Preview: {preview!r}"
        )

    def list_documents() -> str:
        documents = context_store.list_documents()
        if not documents:
            return "No documents are loaded into context yet."
        return "\n".join(f"{doc.doc_id}: {doc.path} ({len(doc.text)} characters)" for doc in documents)

    def get_document_text(doc_id: str, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
        try:
            document = context_store.get(doc_id)
        except KeyError as exc:
            return f"Error: {exc}"
        text = document.text
        if len(text) > max_chars:
            return text[:max_chars] + f"\n...[truncated, {len(text) - max_chars} more characters]"
        return text

    def search_context(query: str, max_results: int = 5) -> str:
        matches = context_store.search(query, max_results=max_results)
        if not matches:
            return f"No matches for '{query}' in the loaded documents."
        return "\n".join(f"[{doc_id}] {paragraph}" for doc_id, paragraph in matches)

    return [
        StructuredTool.from_function(
            func=load_document,
            name="load_document",
            description="Load a .txt, .md, .docx, or .pdf file into context so its content can be reused in slides.",
            args_schema=LoadDocumentInput,
        ),
        StructuredTool.from_function(
            func=list_documents,
            name="list_documents",
            description="List every document currently loaded into context.",
        ),
        StructuredTool.from_function(
            func=get_document_text,
            name="get_document_text",
            description="Read (a prefix of) the full extracted text of a loaded document.",
            args_schema=GetDocumentTextInput,
        ),
        StructuredTool.from_function(
            func=search_context,
            name="search_context",
            description="Keyword-search all loaded documents and return the most relevant paragraphs.",
            args_schema=SearchContextInput,
        ),
    ]
