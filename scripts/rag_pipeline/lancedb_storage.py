"""Windows-safe LanceDB storage paths, preflight cleanup, and connection lifecycle."""

from __future__ import annotations

import atexit
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

logger = logging.getLogger(__name__)

AGENT_NAME = "Hermes"
VECTOR_STORE_DIRNAME = "VectorStore"
DEFAULT_DOMAIN_SUBDIR = "default"
# Only remove lock/tmp artifacts older than this (avoids racing active writes).
_STALE_MIN_AGE_SEC = 30.0

_STALE_SUFFIXES = (".lance-lock", ".tmp")
_STALE_EXACT_NAMES = {".lance-lock", ".tmp"}

_open_connections: list[Any] = []
_connections_lock = threading.Lock()
_shutdown_registered = False
_preflight_done: set[str] = set()
_preflight_lock = threading.Lock()


def _abs_path(raw: str) -> Path:
    """Expand env/user vars and return a resolved absolute path."""
    expanded = Path(os.path.expandvars(os.path.expanduser(raw.strip())))
    try:
        if not expanded.is_absolute():
            return (Path.cwd() / expanded).resolve()
        return expanded.resolve()
    except OSError as exc:
        raise ValueError(f"Cannot resolve LanceDB path {raw!r}: {exc}") from exc


def default_vector_store_root() -> Path:
    """Built-in absolute VectorStore root (Windows: %LOCALAPPDATA%\\hermes\\VectorStore)."""
    if sys.platform == "win32":
        local_app = (os.environ.get("LOCALAPPDATA") or "").strip()
        if local_app:
            base = Path(local_app)
        else:
            base = Path.home() / "AppData" / "Local"
        root = base / "hermes" / VECTOR_STORE_DIRNAME
    else:
        root = Path.home() / ".hermes" / VECTOR_STORE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_lancedb_path(*, domain: str | None = None) -> str:
    """Resolve the absolute LanceDB directory (never relative).

    Priority:
      1. ``HERMES_LANCEDB_PATH`` environment variable
      2. ``domain`` subfolder under the default VectorStore root
      3. Default VectorStore root + ``default`` subfolder
    """
    explicit = (os.environ.get("HERMES_LANCEDB_PATH") or "").strip()
    if explicit:
        path = _abs_path(explicit)
    else:
        root = default_vector_store_root()
        sub = (domain or DEFAULT_DOMAIN_SUBDIR).strip() or DEFAULT_DOMAIN_SUBDIR
        path = (root / sub).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def lancedb_table_dir(storage_dir: Path, table_name: str = "knowledge_base") -> Path:
    """On-disk Lance dataset directory for a table (``<storage>/<name>.lance``)."""
    return storage_dir / f"{table_name}.lance"


def _is_stale_artifact(path: Path) -> bool:
    name = path.name
    if name in _STALE_EXACT_NAMES:
        return True
    lower = name.lower()
    return any(lower.endswith(suffix) for suffix in _STALE_SUFFIXES)


def _artifact_is_safe_to_remove(path: Path) -> bool:
    """Return True when a stale artifact is old enough to delete safely."""
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    return age >= _STALE_MIN_AGE_SEC


def preflight_vector_store(storage_dir: Path, *, force: bool = False) -> list[str]:
    """Ensure storage exists and remove stale lock/tmp files from crashed runs.

    Returns a list of removed file paths (for logging).
    """
    storage_dir = _abs_path(str(storage_dir))
    cache_key = str(storage_dir)
    if not force:
        with _preflight_lock:
            if cache_key in _preflight_done:
                return []

    storage_dir.mkdir(parents=True, exist_ok=True)

    removed: list[str] = []
    for root, _dirs, files in os.walk(storage_dir):
        root_path = Path(root)
        for filename in files:
            candidate = root_path / filename
            if not _is_stale_artifact(candidate):
                continue
            if not _artifact_is_safe_to_remove(candidate):
                logger.debug("Skipping recent LanceDB artifact (may be active): %s", candidate)
                continue
            try:
                candidate.unlink()
                removed.append(str(candidate))
                logger.info("Removed stale LanceDB artifact: %s", candidate)
            except OSError as exc:
                logger.warning("Could not remove stale LanceDB artifact %s: %s", candidate, exc)

    if removed:
        logger.info(
            "LanceDB preflight cleaned %d stale artifact(s) under %s",
            len(removed),
            storage_dir,
        )

    with _preflight_lock:
        _preflight_done.add(cache_key)
    return removed


def close_lancedb_connection(connection: Any | None) -> None:
    """Close a LanceDB connection and drop mmap handles (Windows-safe)."""
    if connection is None:
        return
    try:
        if getattr(connection, "is_open", True) is False:
            return
    except Exception:
        pass
    try:
        closer = getattr(connection, "close", None)
        if callable(closer):
            closer()
    except Exception as exc:
        logger.warning("LanceDB close failed: %s", exc)
    finally:
        with _connections_lock:
            try:
                _open_connections.remove(connection)
            except ValueError:
                pass


def register_lancedb_connection(connection: Any) -> None:
    """Track an open connection for graceful process shutdown."""
    global _shutdown_registered
    with _connections_lock:
        if connection not in _open_connections:
            _open_connections.append(connection)
        if not _shutdown_registered:
            atexit.register(shutdown_all_lancedb_connections)
            _shutdown_registered = True


def shutdown_all_lancedb_connections() -> None:
    """Close all tracked LanceDB connections (CLI/MCP/ingest graceful shutdown)."""
    with _connections_lock:
        pending = list(_open_connections)
        _open_connections.clear()
    for conn in reversed(pending):
        close_lancedb_connection(conn)


def reset_lancedb_storage_state() -> None:
    """Test helper: clear tracked connections and shutdown flag."""
    global _shutdown_registered
    with _connections_lock:
        _open_connections.clear()
    with _preflight_lock:
        _preflight_done.clear()
    _shutdown_registered = False


def connect_lancedb(uri: str | None = None, *, domain: str | None = None) -> Any:
    """Preflight storage, connect, and register for shutdown."""
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
def lancedb_session(uri: str | None = None, *, domain: str | None = None) -> Iterator[Any]:
    """Context manager: preflight + connect + guaranteed close."""
    db = connect_lancedb(uri, domain=domain)
    try:
        yield db
    finally:
        close_lancedb_connection(db)


def register_lancedb_shutdown_hooks(
    extra_cleanup: Callable[[], None] | None = None,
) -> None:
    """Register SIG/atexit hooks for MCP servers and long-lived agent processes."""
    global _shutdown_registered

    def _cleanup() -> None:
        if extra_cleanup is not None:
            try:
                extra_cleanup()
            except Exception as exc:
                logger.warning("LanceDB extra cleanup failed: %s", exc)
        shutdown_all_lancedb_connections()

    if not _shutdown_registered:
        atexit.register(_cleanup)
        _shutdown_registered = True

    import signal

    def _signal_handler(signum, frame):  # noqa: ARG001
        logger.info("LanceDB shutdown hook received signal %s", signum)
        _cleanup()

    for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _signal_handler)
        except (OSError, ValueError):
            pass
