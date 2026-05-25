"""Unit tests for scripts/rag_pipeline/orphan_cleanup.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from orphan_cleanup import (  # noqa: E402
    _orphan_predicate,
    _sql_escape,
    delete_all_chunks_for_source,
    delete_orphan_chunks_for_source,
)


class TestSqlEscape:
    def test_escapes_single_quote(self):
        assert _sql_escape("it's") == "it''s"


class TestOrphanPredicate:
    def test_empty_active_ids_deletes_all_for_source(self):
        pred = _orphan_predicate("docs/a.md", [])
        assert pred == "source = 'docs/a.md'"

    def test_single_batch_not_in(self):
        pred = _orphan_predicate("doc.md", ["id1", "id2"])
        assert "source = 'doc.md'" in pred
        assert "id NOT IN ('id1', 'id2')" in pred
        assert pred.count("id NOT IN") == 1

    def test_dedup_duplicate_ids(self):
        pred = _orphan_predicate("doc.md", ["id1", "id1", "id2"])
        assert pred.count("'id1'") == 1

    def test_multi_batch_uses_and_joined_not_in(self):
        ids = [f"id{i:03d}" for i in range(150)]
        pred = _orphan_predicate("src/x.md", ids)
        assert pred.count("id NOT IN") >= 2
        assert " AND " in pred

    def test_sql_injection_in_source_escaped(self):
        pred = _orphan_predicate("bad' OR 1=1 --", ["x"])
        assert "bad'' OR 1=1 --" in pred

    def test_escapes_quotes_in_active_ids(self):
        pred = _orphan_predicate("doc.md", ["id'42"])
        assert "id''42" in pred
        assert "id NOT IN ('id''42')" in pred

    def test_empty_source_still_valid_predicate(self):
        pred = _orphan_predicate("", ["a"])
        assert pred.startswith("source = ''")
        assert "id NOT IN ('a')" in pred

    def test_backslash_in_source_literal_is_sql_escaped_only(self):
        pred = _orphan_predicate(r"folder\doc.md", ["keep"])
        assert "source = 'folder\\doc.md'" in pred
        assert "id NOT IN ('keep')" in pred


class TestDeleteOrphanChunks:
    def test_happy_path_returns_count(self):
        table = MagicMock()
        table.delete.return_value = 3
        n = delete_orphan_chunks_for_source(table, "doc.md", ["keep"])
        table.delete.assert_called_once()
        assert n == 3

    def test_delete_failure_returns_zero(self):
        table = MagicMock()
        table.delete.side_effect = RuntimeError("lance error")
        assert delete_orphan_chunks_for_source(table, "doc.md", ["a"]) == 0

    def test_none_result_returns_zero(self):
        table = MagicMock()
        table.delete.return_value = None
        assert delete_orphan_chunks_for_source(table, "doc.md", ["a"]) == 0

    def test_object_with_count_attr(self):
        table = MagicMock()
        result = MagicMock()
        result.count = 7
        table.delete.return_value = result
        assert delete_orphan_chunks_for_source(table, "doc.md", ["a"]) == 7

    def test_delete_all_delegates_with_empty_ids(self):
        table = MagicMock()
        table.delete.return_value = 5
        n = delete_all_chunks_for_source(table, "gone.md")
        assert n == 5
        assert "NOT IN" not in table.delete.call_args[0][0]
