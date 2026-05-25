"""Unit tests for scripts/rag_pipeline/bootstrap_ingest_state.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert((0, str(RAG_DIR)))

import bootstrap_ingest_state as boot  # noqa: E402


class TestResolveSourceFile:
    def test_happy_path_relative_file(self, tmp_path):
        (tmp_path / "docs").mkdir()
        f = tmp_path / "docs" / "note.md"
        f.write_text("x", encoding="utf-8")
        got = boot._resolve_source_file(tmp_path, "docs/note.md")
        assert got == f.resolve()

    def test_rejects_parent_traversal(self, tmp_path):
        (tmp_path / "ok.md").write_text("x", encoding="utf-8")
        assert boot._resolve_source_file(tmp_path, "../outside.md") is None

    def test_rejects_absolute_key(self, tmp_path):
        assert boot._resolve_source_file(tmp_path, "/etc/passwd") is None

    def test_missing_file_returns_none(self, tmp_path):
        assert boot._resolve_source_file(tmp_path, "missing.md") is None

    def test_normalizes_backslashes(self, tmp_path):
        (tmp_path / "a.md").write_text("x", encoding="utf-8")
        got = boot._resolve_source_file(tmp_path, "a.md")
        assert got is not None and got.name == "a.md"


class TestUniqueSourcesFromTable:
    def _batch(self, values: list):
        batch = MagicMock()
        batch.num_rows = len(values)
        col = MagicMock()
        col.__getitem__ = lambda _self, i: MagicMock(as_py=lambda v=values[i]: v)
        batch.column.return_value = col
        return batch

    def test_scan_columns_happy_path(self):
        table = MagicMock()
        dataset = MagicMock()
        dataset.scan.return_value.to_batches.return_value = [
            self._batch(["a.md", None, "b\\c.md"])
        ]
        table.to_lance.return_value = dataset
        assert boot._unique_sources_from_table(table) == ["a.md", "b/c.md"]

    def test_fallback_to_arrow_when_scan_fails(self):
        table = MagicMock()
        table.to_lance.side_effect = RuntimeError("no lance")
        arrow = MagicMock()
        arrow.column_names = ["source"]
        uniq = MagicMock()
        uniq.__iter__ = lambda self: iter([MagicMock(as_py=lambda: "x.md")])
        table.to_arrow.return_value = arrow
        with patch.object(boot.pc, "unique", return_value=uniq):
            assert boot._unique_sources_from_table(table) == ["x.md"]

    def test_fallback_returns_empty_when_no_source_column(self):
        table = MagicMock()
        table.to_lance.side_effect = RuntimeError("scan fail")
        arrow = MagicMock()
        arrow.column_names = ["text"]
        table.to_arrow.return_value = arrow
        assert boot._unique_sources_from_table(table) == []

    def test_fallback_returns_empty_when_to_arrow_fails(self):
        table = MagicMock()
        table.to_lance.side_effect = RuntimeError("a")
        table.to_arrow.side_effect = OSError("b")
        assert boot._unique_sources_from_table(table) == []


class TestBootstrapFromLancedb:
    def test_no_table_returns_zeros(self, tmp_path, monkeypatch):
        mock_repo = MagicMock()
        mock_db = MagicMock()
        mock_repo.session.return_value.__enter__ = lambda self: mock_db
        mock_repo.session.return_value.__exit__ = lambda *a: None
        with patch.object(boot, "KnowledgeRepository", return_value=mock_repo), patch.object(
            boot, "list_all_table_names", return_value=[]
        ):
            assert boot.bootstrap_from_lancedb(tmp_path) == (0, 0, 0)

    def test_dry_run_does_not_save(self, tmp_path, monkeypatch):
        (tmp_path / "doc.md").write_text("hi", encoding="utf-8")
        mock_table = MagicMock()
        mock_table.to_lance.side_effect = RuntimeError("x")
        mock_table.to_arrow.return_value = pa.table({"source": ["doc.md"]})
        mock_db = MagicMock()
        mock_db.open_table.return_value = mock_table
        mock_repo = MagicMock()
        mock_repo.session.return_value.__enter__ = lambda self: mock_db
        mock_repo.session.return_value.__exit__ = lambda *a: None

        mock_state = MagicMock()
        mock_state.bootstrap_entry.return_value = True
        mock_state.entries = {"doc.md": {}}

        with patch.object(boot, "KnowledgeRepository", return_value=mock_repo), patch.object(
            boot, "list_all_table_names", return_value=["knowledge_base"]
        ), patch.object(boot, "IngestState") as IS:
            IS.load.return_value = mock_state
            in_db, matched, entries = boot.bootstrap_from_lancedb(tmp_path, dry_run=True)
        assert in_db == 1 and matched == 1 and entries == 1
        mock_state.save.assert_not_called()

    def test_saves_when_matched(self, tmp_path):
        (tmp_path / "doc.md").write_text("hi", encoding="utf-8")
        mock_table = MagicMock()
        mock_table.to_lance.side_effect = RuntimeError("x")
        mock_table.to_arrow.return_value = pa.table({"source": ["doc.md"]})
        mock_db = MagicMock()
        mock_db.open_table.return_value = mock_table
        mock_repo = MagicMock()
        mock_repo.session.return_value.__enter__ = lambda self: mock_db
        mock_repo.session.return_value.__exit__ = lambda *a: None

        mock_state = MagicMock()
        mock_state.bootstrap_entry.return_value = True
        mock_state.entries = {"doc.md": {}}

        with patch.object(boot, "KnowledgeRepository", return_value=mock_repo), patch.object(
            boot, "list_all_table_names", return_value=["knowledge_base"]
        ), patch.object(boot, "IngestState") as IS:
            IS.load.return_value = mock_state
            boot.bootstrap_from_lancedb(tmp_path, dry_run=False)
        mock_state.save.assert_called_once()

    def test_skips_unmatched_sources_on_disk(self, tmp_path):
        mock_table = MagicMock()
        mock_table.to_lance.side_effect = RuntimeError("x")
        mock_table.to_arrow.return_value = pa.table({"source": ["only-in-db.md"]})
        mock_db = MagicMock()
        mock_db.open_table.return_value = mock_table
        mock_repo = MagicMock()
        mock_repo.session.return_value.__enter__ = lambda self: mock_db
        mock_repo.session.return_value.__exit__ = lambda *a: None
        mock_state = MagicMock()
        mock_state.bootstrap_entry.return_value = True
        with patch.object(boot, "KnowledgeRepository", return_value=mock_repo), patch.object(
            boot, "list_all_table_names", return_value=["knowledge_base"]
        ), patch.object(boot, "IngestState") as IS:
            IS.load.return_value = mock_state
            in_db, matched, _ = boot.bootstrap_from_lancedb(tmp_path)
        assert in_db == 1 and matched == 0
        mock_state.save.assert_not_called()


class TestDefaultRawRoot:
    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_RAG_RAW_SOURCE", str(tmp_path))
        assert boot._default_raw_root() == tmp_path.resolve()
