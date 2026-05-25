"""Unit tests for scripts/rag_pipeline/knowledge_repository.py.

Covers happy paths, edge cases, invalid input, and negative scenarios.
External dependencies (VectorStoreBackend, kb_schema, LanceDB table API) are mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest

RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import knowledge_repository as repo_mod  # noqa: E402
from knowledge_repository import KnowledgeRepository, schema_has_id  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_vector_store_backend():
    """Prevent injected backends from leaking across tests."""
    import vector_store_ports as ports

    ports.set_vector_store_backend(None)
    yield
    ports.set_vector_store_backend(None)


def _mock_db_with_table(mock_table: MagicMock, *, table_names: list[str] | None = None) -> MagicMock:
    mock_db = MagicMock()
    page = MagicMock()
    page.tables = table_names if table_names is not None else ["knowledge_base"]
    page.page_token = None
    mock_db.list_tables.return_value = page
    mock_db.open_table.return_value = mock_table
    return mock_db


def _table_with_schema(*field_names: str) -> MagicMock:
    mock_table = MagicMock()
    mock_table.schema = pa.schema([(name, pa.string()) for name in field_names])
    return mock_table


def _row(row_id: str) -> dict:
    return {"id": row_id, "text": "chunk", "source": "doc.md"}


# ---------------------------------------------------------------------------
# schema_has_id
# ---------------------------------------------------------------------------


class TestSchemaHasId:
    def test_true_when_id_column_present(self):
        schema = pa.schema([("id", pa.string()), ("text", pa.string())])
        assert schema_has_id(schema) is True

    def test_false_when_id_missing(self):
        schema = pa.schema([("text", pa.string()), ("source", pa.string())])
        assert schema_has_id(schema) is False

    def test_false_when_schema_has_no_names(self):
        assert schema_has_id(object()) is False

    def test_false_when_names_is_none(self):
        schema = MagicMock()
        schema.names = None
        assert schema_has_id(schema) is False


# ---------------------------------------------------------------------------
# Construction & backend wiring — happy path
# ---------------------------------------------------------------------------


class TestKnowledgeRepositoryInit:
    def test_uses_injected_backend(self):
        backend = MagicMock()
        repo = KnowledgeRepository(db_path="/data/kb", backend=backend)
        assert repo.backend is backend

    def test_defaults_to_get_vector_store_backend(self):
        backend = MagicMock()
        with patch.object(repo_mod, "get_vector_store_backend", return_value=backend):
            repo = KnowledgeRepository()
        assert repo.backend is backend

    def test_db_path_stored_for_session(self):
        backend = MagicMock()
        backend.connect.return_value = MagicMock()
        repo = KnowledgeRepository(db_path="/custom/path", backend=backend)
        with repo.session():
            pass
        backend.connect.assert_called_once_with("/custom/path")


# ---------------------------------------------------------------------------
# session() — happy path & lifecycle edge cases
# ---------------------------------------------------------------------------


class TestKnowledgeRepositorySession:
    def test_yields_connected_db(self):
        backend = MagicMock()
        mock_db = MagicMock()
        backend.connect.return_value = mock_db
        repo = KnowledgeRepository(backend=backend)

        with repo.session() as db:
            assert db is mock_db

        backend.close.assert_called_once_with(mock_db)

    def test_closes_on_exception_in_with_block(self):
        backend = MagicMock()
        mock_db = MagicMock()
        backend.connect.return_value = mock_db
        repo = KnowledgeRepository(backend=backend)

        with pytest.raises(RuntimeError, match="boom"):
            with repo.session():
                raise RuntimeError("boom")

        backend.close.assert_called_once_with(mock_db)

    def test_connect_failure_propagates_without_close(self):
        backend = MagicMock()
        backend.connect.side_effect = OSError("connection refused")
        repo = KnowledgeRepository(backend=backend)

        with pytest.raises(OSError, match="connection refused"):
            with repo.session():
                pass

        backend.close.assert_not_called()

    def test_none_db_path_passed_to_backend(self):
        backend = MagicMock()
        backend.connect.return_value = MagicMock()
        repo = KnowledgeRepository(db_path=None, backend=backend)
        with repo.session():
            pass
        backend.connect.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# list_table_names & ensure_table
# ---------------------------------------------------------------------------


class TestKnowledgeRepositoryEnsureTable:
    def test_opens_existing_table_with_id_column(self):
        mock_table = _table_with_schema("id", "text", "source")
        mock_db = _mock_db_with_table(mock_table)
        repo = KnowledgeRepository(backend=MagicMock())

        table = repo.ensure_table(mock_db)

        assert table is mock_table
        mock_db.open_table.assert_called_once_with("knowledge_base")
        mock_db.create_table.assert_not_called()

    def test_creates_table_when_missing(self, monkeypatch):
        mock_db = MagicMock()
        page = MagicMock()
        page.tables = []
        page.page_token = None
        mock_db.list_tables.return_value = page
        created = MagicMock()
        mock_db.create_table.return_value = created
        schema_cls = object()
        monkeypatch.setattr(repo_mod, "get_knowledge_schema", lambda: schema_cls)

        repo = KnowledgeRepository(backend=MagicMock())
        table = repo.ensure_table(mock_db)

        assert table is created
        mock_db.create_table.assert_called_once_with("knowledge_base", schema=schema_cls)

    def test_rejects_legacy_schema_without_id(self):
        mock_table = _table_with_schema("text", "source")
        mock_db = _mock_db_with_table(mock_table)
        repo = KnowledgeRepository(backend=MagicMock())

        with pytest.raises(RuntimeError, match="missing required column 'id'"):
            repo.ensure_table(mock_db)

    def test_rejects_schema_without_names_attribute(self):
        mock_table = MagicMock()
        mock_table.schema = MagicMock(spec=[])  # no .names
        mock_db = _mock_db_with_table(mock_table)
        repo = KnowledgeRepository(backend=MagicMock())

        with pytest.raises(RuntimeError, match="missing required column 'id'"):
            repo.ensure_table(mock_db)

    def test_list_table_names_delegates_to_kb_schema(self, monkeypatch):
        mock_db = MagicMock()
        monkeypatch.setattr(repo_mod, "list_all_table_names", lambda db: ["a", "b"])
        repo = KnowledgeRepository(backend=MagicMock())
        assert repo.list_table_names(mock_db) == ["a", "b"]


# ---------------------------------------------------------------------------
# search() — happy path
# ---------------------------------------------------------------------------


class TestKnowledgeRepositorySearchHappyPath:
    def test_delegates_to_table_search_chain(self):
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_list.return_value = [
            {"text": "hit", "source": "doc.md"}
        ]
        repo = KnowledgeRepository()

        hits = repo.search("contract clause", limit=3, table=mock_table)

        assert hits == [{"text": "hit", "source": "doc.md"}]
        mock_table.search.assert_called_once_with("contract clause")
        mock_table.search.return_value.limit.assert_called_once_with(3)

    def test_default_limit_is_five(self):
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_list.return_value = []
        KnowledgeRepository().search("term", table=mock_table)
        mock_table.search.return_value.limit.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# search() — edge cases & invalid input
# ---------------------------------------------------------------------------


class TestKnowledgeRepositorySearchEdgeCases:
    @pytest.mark.parametrize("query", ["", "   ", "\n\t", "\r\n"])
    def test_empty_or_whitespace_query_returns_empty_without_search(self, query: str):
        mock_table = MagicMock()
        repo = KnowledgeRepository()
        assert repo.search(query, table=mock_table) == []
        mock_table.search.assert_not_called()

    def test_requires_open_table(self):
        repo = KnowledgeRepository()
        with pytest.raises(ValueError, match="requires an open table"):
            repo.search("query", table=None)

    @pytest.mark.parametrize(
        ("limit", "expected"),
        [
            (0, 1),
            (-10, 1),
            (1, 1),
            (50, 50),
            (100, 50),
            (999, 50),
        ],
    )
    def test_limit_clamped_between_1_and_50(self, limit: int, expected: int):
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_list.return_value = []
        KnowledgeRepository().search("q", limit=limit, table=mock_table)
        mock_table.search.return_value.limit.assert_called_once_with(expected)

    @pytest.mark.parametrize("bad_limit", ["not-a-number", None, object()])
    def test_invalid_limit_falls_back_to_five(self, bad_limit):
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_list.return_value = []
        KnowledgeRepository().search("q", limit=bad_limit, table=mock_table)  # type: ignore[arg-type]
        mock_table.search.return_value.limit.assert_called_once_with(5)

    def test_search_propagates_table_api_errors(self):
        mock_table = MagicMock()
        mock_table.search.side_effect = RuntimeError("vector index missing")
        with pytest.raises(RuntimeError, match="vector index missing"):
            KnowledgeRepository().search("q", table=mock_table)


# ---------------------------------------------------------------------------
# upsert_chunks() — happy path
# ---------------------------------------------------------------------------


class TestKnowledgeRepositoryUpsertHappyPath:
    def test_empty_rows_is_no_op(self):
        mock_table = MagicMock()
        KnowledgeRepository().upsert_chunks(mock_table, [])
        mock_table.merge_insert.assert_not_called()

    def test_single_batch_merge_insert_chain(self):
        mock_table = MagicMock()
        chain = mock_table.merge_insert.return_value
        chain.when_matched_update_all.return_value = chain
        chain.when_not_matched_insert_all.return_value = chain

        rows = [_row("1"), _row("2")]
        KnowledgeRepository().upsert_chunks(mock_table, rows)

        mock_table.merge_insert.assert_called_once_with("id")
        chain.when_matched_update_all.assert_called_once()
        chain.when_not_matched_insert_all.assert_called_once()
        chain.execute.assert_called_once_with(rows)

    def test_batches_when_rows_exceed_batch_size(self):
        mock_table = MagicMock()
        rows = [_row(str(i)) for i in range(5)]
        KnowledgeRepository().upsert_chunks(mock_table, rows, batch_size=2)
        assert mock_table.merge_insert.call_count == 3

    def test_batch_size_one_processes_each_row_separately(self):
        mock_table = MagicMock()
        rows = [_row("a"), _row("b"), _row("c")]
        KnowledgeRepository().upsert_chunks(mock_table, rows, batch_size=1)
        assert mock_table.merge_insert.call_count == 3


# ---------------------------------------------------------------------------
# upsert_chunks() — edge cases & negative scenarios
# ---------------------------------------------------------------------------


class TestKnowledgeRepositoryUpsertEdgeCases:
    def test_batch_size_zero_treated_as_one(self):
        mock_table = MagicMock()
        rows = [_row("1"), _row("2")]
        KnowledgeRepository().upsert_chunks(mock_table, rows, batch_size=0)
        assert mock_table.merge_insert.call_count == 2

    def test_batch_size_negative_treated_as_one(self):
        mock_table = MagicMock()
        rows = [_row("1"), _row("2")]
        KnowledgeRepository().upsert_chunks(mock_table, rows, batch_size=-5)
        assert mock_table.merge_insert.call_count == 2

    def test_invalid_batch_size_raises_value_error(self):
        mock_table = MagicMock()
        with pytest.raises(ValueError):
            KnowledgeRepository().upsert_chunks(mock_table, [_row("1")], batch_size="bad")  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "rows",
        [
            [{"text": "no id"}],
            [{"id": "ok"}, {"text": "second row missing id"}],
            [{"id": "ok"}, {}],
        ],
    )
    def test_rejects_rows_missing_id_key(self, rows: list[dict]):
        mock_table = MagicMock()
        with pytest.raises(ValueError, match="'id'"):
            KnowledgeRepository().upsert_chunks(mock_table, rows)
        mock_table.merge_insert.assert_not_called()


class TestKnowledgeRepositoryMergeRows:
    def test_wraps_underlying_exception_with_context(self):
        mock_table = MagicMock()
        chain = mock_table.merge_insert.return_value
        chain.when_matched_update_all.return_value = chain
        chain.when_not_matched_insert_all.return_value = chain
        chain.execute.side_effect = OSError("disk full")

        with pytest.raises(RuntimeError, match="merge_insert failed for 2 row") as exc_info:
            KnowledgeRepository._merge_rows(mock_table, [_row("1"), _row("2")])

        assert isinstance(exc_info.value.__cause__, OSError)
        assert "disk full" in str(exc_info.value.__cause__)


# ---------------------------------------------------------------------------
# register_shutdown_hooks
# ---------------------------------------------------------------------------


class TestKnowledgeRepositoryShutdownHooks:
    def test_delegates_to_backend(self):
        backend = MagicMock()
        cleanup = MagicMock()
        repo = KnowledgeRepository(backend=backend)

        repo.register_shutdown_hooks(extra_cleanup=cleanup)

        backend.register_shutdown_hooks.assert_called_once_with(extra_cleanup=cleanup)

    def test_accepts_none_cleanup(self):
        backend = MagicMock()
        KnowledgeRepository(backend=backend).register_shutdown_hooks(extra_cleanup=None)
        backend.register_shutdown_hooks.assert_called_once_with(extra_cleanup=None)


# ---------------------------------------------------------------------------
# Integration-style flow (all mocked)
# ---------------------------------------------------------------------------


class TestKnowledgeRepositoryEndToEndMocked:
    def test_session_ensure_search_upsert_flow(self):
        mock_table = _table_with_schema("id", "text", "source")
        mock_table.search.return_value.limit.return_value.to_list.return_value = [{"text": "hit"}]
        mock_db = _mock_db_with_table(mock_table)

        backend = MagicMock()
        backend.connect.return_value = mock_db
        repo = KnowledgeRepository(db_path="/tmp/kb", backend=backend)

        with repo.session() as db:
            table = repo.ensure_table(db)
            hits = repo.search("query", limit=2, table=table)
            repo.upsert_chunks(table, [_row("chunk-1")])

        assert hits == [{"text": "hit"}]
        backend.close.assert_called_once_with(mock_db)
        mock_table.merge_insert.assert_called_once()
