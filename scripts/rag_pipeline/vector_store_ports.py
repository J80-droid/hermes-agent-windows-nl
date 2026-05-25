"""Vector store abstraction for dependency injection and test doubles."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator, Protocol, runtime_checkable


@runtime_checkable
class VectorStoreConnection(Protocol):
    """Minimal connection surface used by ingest, MCP, and maintenance."""

    def close(self) -> None: ...


class VectorStoreBackend(Protocol):
    """Backend contract between agent/RAG callers and concrete storage engines."""

    def connect(self, uri: str | None = None, *, domain: str | None = None) -> Any: ...

    @contextmanager
    def session(self, uri: str | None = None, *, domain: str | None = None) -> Iterator[Any]: ...

    def close(self, connection: Any | None) -> None: ...

    def register_shutdown_hooks(
        self, extra_cleanup: Callable[[], None] | None = None
    ) -> None: ...


_default_backend: VectorStoreBackend | None = None


def set_vector_store_backend(backend: VectorStoreBackend | None) -> None:
    """Inject a backend (tests, alternate engines). Pass ``None`` to reset default."""
    global _default_backend
    _default_backend = backend


def get_vector_store_backend() -> VectorStoreBackend:
    """Return the configured backend, lazily defaulting to LanceDB."""
    global _default_backend
    if _default_backend is None:
        from lancedb_backend import LanceDBVectorStoreBackend

        _default_backend = LanceDBVectorStoreBackend()
    return _default_backend
