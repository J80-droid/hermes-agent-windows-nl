"""Architecture tests for vector store ports and dependency injection."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import lancedb_storage as storage  # noqa: E402
import vector_store_ports as ports  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_backend():
    storage.reset_lancedb_storage_state()
    yield
    storage.reset_lancedb_storage_state()


class TestVectorStorePorts:
    def test_injected_backend_is_used_for_connect(self):
        mock_db = MagicMock()
        backend = MagicMock()
        backend.connect.return_value = mock_db

        ports.set_vector_store_backend(backend)
        result = storage.connect_lancedb("/tmp/injected")

        assert result is mock_db
        backend.connect.assert_called_once_with("/tmp/injected", domain=None)

    def test_reset_clears_injected_backend(self, monkeypatch):
        fake_lancedb = MagicMock()
        fake_lancedb.connect.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "lancedb", fake_lancedb)

        ports.set_vector_store_backend(MagicMock())
        storage.reset_lancedb_storage_state()
        storage.connect_lancedb("/tmp/default")

        fake_lancedb.connect.assert_called_once_with("/tmp/default")
