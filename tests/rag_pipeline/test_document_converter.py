"""Unit tests for scripts/rag_pipeline/document_converter.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import document_converter as dc  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_converter():
    dc.set_document_converter(None)
    yield
    dc.set_document_converter(None)


class TestMarkItDownDocumentConverter:
    def test_delegates_to_ingest_handlers(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF")
        with patch.object(dc, "_convert_document_impl", return_value=("text", None, "markitdown")) as conv:
            out = dc.MarkItDownDocumentConverter().convert(f)
        conv.assert_called_once_with(f)
        assert out == ("text", None, "markitdown")

    def test_propagates_error_from_impl(self, tmp_path):
        f = tmp_path / "bad.docx"
        f.write_bytes(b"x")
        with patch.object(dc, "_convert_document_impl", return_value=("", "parse failed", "")):
            text, err, method = dc.MarkItDownDocumentConverter().convert(f)
        assert text == "" and err == "parse failed" and method == ""


class TestConverterRegistry:
    def test_get_returns_singleton_default(self):
        a = dc.get_document_converter()
        b = dc.get_document_converter()
        assert a is b
        assert isinstance(a, dc.MarkItDownDocumentConverter)

    def test_set_injects_custom_converter(self):
        mock = MagicMock()
        mock.convert.return_value = ("injected", None, "test")
        dc.set_document_converter(mock)
        assert dc.get_document_converter() is mock
        assert dc.convert_document(Path("x.md")) == ("injected", None, "test")

    def test_set_none_resets_to_default(self):
        dc.set_document_converter(MagicMock())
        dc.set_document_converter(None)
        assert isinstance(dc.get_document_converter(), dc.MarkItDownDocumentConverter)
