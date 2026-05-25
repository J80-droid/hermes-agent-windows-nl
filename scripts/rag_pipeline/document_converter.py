"""Document conversion port for RAG ingest (MarkItDown / pandoc / OCR chain).

Default: ``MarkItDownDocumentConverter`` delegates to ``ingest_handlers.convert_document``.
Tests inject a custom converter via ``set_document_converter()``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ingest_handlers import convert_document as _convert_document_impl


@runtime_checkable
class DocumentConverter(Protocol):
    """Convert a source file to plain text for chunking."""

    def convert(self, path: Path) -> tuple[str, str | None, str]:
        """Returns (text, error, ocr_method)."""
        ...


class MarkItDownDocumentConverter:
    """Default converter: MarkItDown → pandoc → PyMuPDF/Tesseract."""

    def convert(self, path: Path) -> tuple[str, str | None, str]:
        return _convert_document_impl(path)


_default_converter: DocumentConverter | None = None


def get_document_converter() -> DocumentConverter:
    global _default_converter
    if _default_converter is None:
        _default_converter = MarkItDownDocumentConverter()
    return _default_converter


def set_document_converter(converter: DocumentConverter | None) -> None:
    """Inject converter (tests) or reset to default."""
    global _default_converter
    _default_converter = converter


def convert_document(path: Path) -> tuple[str, str | None, str]:
    """Backward-compatible entrypoint used by ingest."""
    return get_document_converter().convert(path)
