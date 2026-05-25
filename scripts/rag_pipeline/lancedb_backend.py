"""Default LanceDB implementation of ``VectorStoreBackend``."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from vector_store_lifecycle import (
    close_lancedb_connection,
    preflight_vector_store,
    register_lancedb_connection,
    register_lancedb_shutdown_hooks,
)
from vector_store_paths import resolve_lancedb_path


class LanceDBVectorStoreBackend:
    """LanceDB-backed vector store with lazy ``lancedb`` import."""

    def connect(self, uri: str | None = None, *, domain: str | None = None) -> Any:
        import lancedb

        path = uri or resolve_lancedb_path(domain=domain)
        preflight_vector_store(Path(path))
        try:
            db = lancedb.connect(path)
        except Exception as exc:
            raise RuntimeError(f"LanceDB connect failed for {path!r}: {exc}") from exc
        register_lancedb_connection(db)
        return db

    @contextmanager
    def session(self, uri: str | None = None, *, domain: str | None = None) -> Iterator[Any]:
        db = self.connect(uri, domain=domain)
        try:
            yield db
        finally:
            self.close(db)

    def close(self, connection: Any | None) -> None:
        close_lancedb_connection(connection)

    def register_shutdown_hooks(
        self, extra_cleanup: Callable[[], None] | None = None
    ) -> None:
        register_lancedb_shutdown_hooks(extra_cleanup=extra_cleanup)
