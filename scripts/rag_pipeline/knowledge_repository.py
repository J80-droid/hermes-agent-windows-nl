"""Agent-facing knowledge base API above VectorStoreBackend + KnowledgeSchema.

Contract (edge cases):
  - ``search``: whitespace-only query → ``[]``; ``limit`` clamped 1–50; invalid limit → 5.
  - ``upsert_chunks``: each row must include ``id``; ``merge_insert`` errors → ``RuntimeError``.
  - ``ensure_table``: rejects legacy tables without an ``id`` column.
  - ``session``: always closes the backend connection in ``finally``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator

from kb_schema import TABLE_NAME, get_knowledge_schema, list_all_table_names
from vector_store_ports import VectorStoreBackend, get_vector_store_backend


def schema_has_id(schema: Any) -> bool:
    """Return True when the Lance table schema includes an ``id`` column."""
    names = getattr(schema, "names", None)
    if names is None:
        return False
    return "id" in names


class KnowledgeRepository:
    """High-level RAG storage: connect, ensure table, search, upsert."""

    def __init__(
        self,
        db_path: str | None = None,
        *,
        backend: VectorStoreBackend | None = None,
    ) -> None:
        self._db_path = db_path
        self._backend = backend or get_vector_store_backend()

    @property
    def backend(self) -> VectorStoreBackend:
        return self._backend

    @contextmanager
    def session(self) -> Iterator[Any]:
        """Open a tracked LanceDB connection and close it on exit."""
        db = self._backend.connect(self._db_path)
        try:
            yield db
        finally:
            self._backend.close(db)

    def list_table_names(self, db: Any) -> list[str]:
        return list_all_table_names(db)

    def ensure_table(self, db: Any) -> Any:
        """Open ``knowledge_base`` or create it with ``KnowledgeSchema``."""
        if TABLE_NAME in self.list_table_names(db):
            table = db.open_table(TABLE_NAME)
            if not schema_has_id(table.schema):
                raise RuntimeError(
                    f"Table '{TABLE_NAME}' is missing required column 'id' (legacy schema)."
                )
            return table
        return db.create_table(TABLE_NAME, schema=get_knowledge_schema())

    def search(self, query: str, *, limit: int = 5, table: Any | None = None) -> list[dict]:
        """Vector search over ``knowledge_base`` (requires an open table or active session)."""
        if table is None:
            raise ValueError("search() requires an open table; use ensure_table(db) first.")
        if not str(query).strip():
            return []
        try:
            safe_limit = max(1, min(int(limit), 50))
        except (TypeError, ValueError):
            safe_limit = 5
        return table.search(query).limit(safe_limit).to_list()

    def upsert_chunks(self, table: Any, rows: list[dict], *, batch_size: int = 64) -> None:
        """Idempotent upsert on ``id`` (merge_insert)."""
        if not rows:
            return
        if any("id" not in row for row in rows):
            raise ValueError("upsert_chunks requires each row to include an 'id' key")
        batch_size = max(1, int(batch_size))
        if len(rows) <= batch_size:
            self._merge_rows(table, rows)
            return
        for i in range(0, len(rows), batch_size):
            self._merge_rows(table, rows[i : i + batch_size])

    @staticmethod
    def _merge_rows(table: Any, rows: list[dict]) -> None:
        try:
            table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(rows)
        except Exception as exc:
            raise RuntimeError(f"LanceDB merge_insert failed for {len(rows)} row(s): {exc}") from exc

    def register_shutdown_hooks(
        self, extra_cleanup: Callable[[], None] | None = None
    ) -> None:
        self._backend.register_shutdown_hooks(extra_cleanup=extra_cleanup)
