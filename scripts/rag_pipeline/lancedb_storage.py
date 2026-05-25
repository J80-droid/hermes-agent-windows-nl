"""Backward-compatible facade for VectorStore paths, lifecycle, and LanceDB access.

New code should prefer:
  - ``vector_store_paths`` — path resolution
  - ``vector_store_lifecycle`` — preflight + shutdown
  - ``vector_store_ports`` / ``lancedb_backend`` — DI-friendly backend
"""

from __future__ import annotations

import atexit
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from vector_store_lifecycle import (
    _STALE_MIN_AGE_SEC,
    _artifact_is_safe_to_remove,
    _is_stale_artifact,
    _run_shutdown_hooks,
    close_lancedb_connection,
    preflight_vector_store,
    register_lancedb_connection,
    register_lancedb_shutdown_hooks,
    reset_lancedb_storage_state,
    shutdown_all_lancedb_connections,
)
from vector_store_paths import (
    AGENT_NAME,
    DEFAULT_DOMAIN_SUBDIR,
    VECTOR_STORE_DIRNAME,
    _abs_path,
    default_vector_store_root,
    lancedb_table_dir,
    resolve_lancedb_path,
)
from vector_store_ports import get_vector_store_backend, set_vector_store_backend

__all__ = [
    "AGENT_NAME",
    "DEFAULT_DOMAIN_SUBDIR",
    "VECTOR_STORE_DIRNAME",
    "_STALE_MIN_AGE_SEC",
    "_abs_path",
    "_artifact_is_safe_to_remove",
    "_is_stale_artifact",
    "_run_shutdown_hooks",
    "close_lancedb_connection",
    "connect_lancedb",
    "default_vector_store_root",
    "get_vector_store_backend",
    "lancedb_session",
    "lancedb_table_dir",
    "preflight_vector_store",
    "register_lancedb_connection",
    "register_lancedb_shutdown_hooks",
    "reset_lancedb_storage_state",
    "resolve_lancedb_path",
    "set_vector_store_backend",
    "shutdown_all_lancedb_connections",
]


def connect_lancedb(uri: str | None = None, *, domain: str | None = None) -> Any:
    """Preflight storage, connect, and register for shutdown."""
    return get_vector_store_backend().connect(uri, domain=domain)


@contextmanager
def lancedb_session(uri: str | None = None, *, domain: str | None = None) -> Iterator[Any]:
    """Context manager: preflight + connect + guaranteed close."""
    db = connect_lancedb(uri, domain=domain)
    try:
        yield db
    finally:
        close_lancedb_connection(db)
