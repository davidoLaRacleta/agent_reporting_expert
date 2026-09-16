"""Plain-text extraction for the document formats the agent can ingest.

Each format's parsing library is imported lazily inside its extractor
function, so a user who never loads a .pdf never needs ``pypdf``
installed, and likewise for .docx and ``python-docx``.
"""

from __future__ import annotations

from pathlib import Path

_SUPPORTED_SUFFIXES = {".txt", ".md", ".docx", ".pdf"}


def extract_text(path: Path) -> str:
    """Extract plain text from a .txt, .md, .docx, or .pdf file.

    Raises:
        ValueError: If the file extension is not one of the supported types.
    """
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        return _extract_docx_text(path)
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    raise ValueError(
        f"Unsupported document type '{suffix}'. Supported types: {sorted(_SUPPORTED_SUFFIXES)}."
    )


def _extract_docx_text(path: Path) -> str:
    from docx import Document as WordDocument

    document = WordDocument(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
