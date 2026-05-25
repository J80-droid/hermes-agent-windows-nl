"""Tests for lazy kb_schema loading."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))


def test_kb_schema_constants_import_without_lancedb(monkeypatch):
    """Importing constants must not pull in lancedb."""
    monkeypatch.delitem(sys.modules, "kb_schema_constants", raising=False)
    monkeypatch.delitem(sys.modules, "kb_schema", raising=False)
    monkeypatch.delitem(sys.modules, "lancedb", raising=False)

    import kb_schema_constants

    assert kb_schema_constants.TABLE_NAME == "knowledge_base"
    assert "lancedb" not in sys.modules


def test_db_path_resolves_via_vector_store_paths(monkeypatch, tmp_path):
    monkeypatch.delitem(sys.modules, "kb_schema", raising=False)
    monkeypatch.setenv("HERMES_LANCEDB_PATH", str(tmp_path / "schema-db"))

    import kb_schema

    assert kb_schema.get_db_path() == str((tmp_path / "schema-db").resolve())
    assert kb_schema.DB_PATH == str((tmp_path / "schema-db").resolve())
