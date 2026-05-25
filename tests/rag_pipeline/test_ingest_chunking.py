"""Unit tests for scripts/rag_pipeline/ingest_chunking.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from ingest_chunking import (  # noqa: E402
    DEFAULT_MAX_WORDS,
    chunk_row_id,
    semantic_chunk_document,
)


class TestChunkRowId:
    def test_deterministic_for_same_input(self):
        a = chunk_row_id("folder/doc.md", 0)
        b = chunk_row_id("folder/doc.md", 0)
        assert a == b
        assert len(a) == 64

    def test_different_index_different_id(self):
        assert chunk_row_id("doc.md", 0) != chunk_row_id("doc.md", 1)

    def test_normalizes_windows_path_to_posix(self):
        assert chunk_row_id(r"folder\doc.md", 0) == chunk_row_id("folder/doc.md", 0)


class TestSemanticChunkDocument:
    def test_empty_string_returns_empty(self):
        assert semantic_chunk_document("") == []
        assert semantic_chunk_document("   \n  ") == []

    def test_single_paragraph_under_limit(self):
        text = "Eén korte alinea zonder kop."
        chunks = semantic_chunk_document(text, max_words=50)
        assert len(chunks) == 1
        assert "korte alinea" in chunks[0]

    def test_markdown_heading_splits_sections(self):
        text = "## Eerste\n\n" + ("woord " * 80) + "\n\n## Tweede\n\n" + ("zin " * 80)
        chunks = semantic_chunk_document(text, max_words=50)
        assert len(chunks) >= 2
        assert any("## Eerste" in c or "## Tweede" in c for c in chunks)

    def test_fenced_code_preserved_as_unit_when_small(self):
        text = "Intro.\n\n```python\nprint('ok')\n```\n\nOutro."
        chunks = semantic_chunk_document(text, max_words=100)
        code_chunks = [c for c in chunks if "```" in c]
        assert len(code_chunks) >= 1

    def test_oversized_prose_splits_by_sentences(self):
        words = "woord " * 500
        chunks = semantic_chunk_document(words.strip(), max_words=100)
        assert len(chunks) > 1
        assert all(len(c.split()) <= 100 for c in chunks)

    def test_crlf_normalized(self):
        text = "Regel één.\r\n\r\nRegel twee."
        chunks = semantic_chunk_document(text, max_words=50)
        assert chunks and "\r" not in chunks[0]

    def test_invalid_max_words_still_chunks(self):
        chunks = semantic_chunk_document("a b c d e", max_words=2)
        assert len(chunks) >= 2
