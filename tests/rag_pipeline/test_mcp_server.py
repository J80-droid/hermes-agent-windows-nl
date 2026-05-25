"""Unit tests for scripts/rag_pipeline/mcp_server.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from rag_display import source_basename  # noqa: E402

import mcp_server as ms  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mcp_connection():
    ms.close_lancedb_mcp_connection()
    yield
    ms.close_lancedb_mcp_connection()


def test_source_basename_matches_mcp_contract():
    assert source_basename(r"04_Legal_Corporate\map\doc.pdf") == "doc.pdf"


class TestEnsureMcpKnowledge:
    def test_returns_cached_repo_and_table(self):
        mock_repo = MagicMock()
        mock_table = MagicMock()
        ms._repo = mock_repo
        ms._db = object()
        ms._table = mock_table
        repo, table = ms._ensure_mcp_knowledge()
        assert repo is mock_repo and table is mock_table

    def test_connect_failure_clears_cache(self):
        with patch.object(ms, "KnowledgeRepository", side_effect=RuntimeError("db down")):
            ms._repo = None
            with pytest.raises(RuntimeError, match="db down"):
                ms._ensure_mcp_knowledge()
        assert ms._repo is None and ms._db is None and ms._table is None

    def test_lazy_init_happy_path(self):
        mock_repo = MagicMock()
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_repo.backend.connect.return_value = mock_db
        mock_repo.ensure_table.return_value = mock_table
        with patch.object(ms, "KnowledgeRepository", return_value=mock_repo), patch.object(
            ms, "get_db_path", return_value="/tmp/kb"
        ):
            repo, table = ms._ensure_mcp_knowledge()
        assert repo is mock_repo and table is mock_table
        mock_repo.backend.connect.assert_called_once()
        mock_repo.ensure_table.assert_called_once_with(mock_db)


class TestSearchKnowledge:
    def test_empty_query_rejected(self):
        assert ms.search_knowledge("   ") == "Geen zoekterm opgegeven."

    def test_happy_path_formats_results(self):
        mock_repo = MagicMock()
        mock_table = MagicMock()
        mock_repo.search.return_value = [
            {"source": "folder/doc.pdf", "text": "Inhoud hier."},
        ]
        with patch.object(ms, "_ensure_mcp_knowledge", return_value=(mock_repo, mock_table)):
            out = ms.search_knowledge("juridisch", limit=3)
        mock_repo.search.assert_called_once_with("juridisch", limit=3, table=mock_table)
        assert "bron_bestand: doc.pdf" in out
        assert "Inhoud: Inhoud hier." in out
        assert "inline_citeer_sjabloon:" in out

    def test_no_results_message(self):
        mock_repo = MagicMock()
        mock_repo.search.return_value = []
        with patch.object(ms, "_ensure_mcp_knowledge", return_value=(mock_repo, MagicMock())):
            assert ms.search_knowledge("xyz") == "Geen resultaten gevonden."

    def test_exception_returns_user_facing_error(self):
        with patch.object(ms, "_ensure_mcp_knowledge", side_effect=OSError("mmap locked")):
            out = ms.search_knowledge("q")
        assert out.startswith("Fout bij doorzoeken database:")
        assert "mmap locked" in out


class TestCloseAndReset:
    def test_close_calls_backend_close(self):
        mock_repo = MagicMock()
        mock_db = MagicMock()
        ms._repo = mock_repo
        ms._db = mock_db
        ms._table = MagicMock()
        ms.close_lancedb_mcp_connection()
        mock_repo.backend.close.assert_called_once_with(mock_db)
        assert ms._repo is None and ms._db is None and ms._table is None

    def test_reset_delegates_to_close(self):
        ms._repo = MagicMock()
        ms._db = object()
        ms._table = object()
        with patch.object(ms, "close_lancedb_mcp_connection") as close:
            ms.reset_knowledge_table_cache()
        close.assert_called_once()
