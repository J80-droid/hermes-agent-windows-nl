"""Vector store preflight cleanup and connection lifecycle (no LanceDB import)."""

from __future__ import annotations

import atexit
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from vector_store_paths import _abs_path

logger = logging.getLogger(__name__)

# Only remove lock/tmp artifacts older than this (avoids racing active writes).
_STALE_MIN_AGE_SEC = 30.0

_STALE_SUFFIXES = (".lance-lock", ".tmp")
_STALE_EXACT_NAMES = {".lance-lock", ".tmp"}
# Lance version/data dirs hold thousands of segment files; locks live at dataset roots.
_SKIP_WALK_DIRS = frozenset({"_versions", "_transactions", "data", "_indices"})

_open_connections: list[Any] = []
_connections_lock = threading.Lock()
_shutdown_lock = threading.Lock()
_shutdown_registered = False
_shutdown_ran = False
_extra_shutdown: Callable[[], None] | None = None
_preflight_done: set[str] = set()
_preflight_lock = threading.Lock()


def _is_stale_artifact(path: Path) -> bool:
    name = path.name
    if name in _STALE_EXACT_NAMES:
        return True
    lower = name.lower()
    return any(lower.endswith(suffix) for suffix in _STALE_SUFFIXES)


def _artifact_is_safe_to_remove(path: Path, *, now: float | None = None) -> bool:
    """Return True when a stale artifact is old enough to delete safely."""
    try:
        age = max(0.0, (now if now is not None else time.time()) - path.stat().st_mtime)
    except OSError:
        return False
    return age >= _STALE_MIN_AGE_SEC


def _scan_lance_dataset_shallow(lance_dir: Path) -> Iterator[Path]:
    """Scan only the dataset root for lock/tmp files (not version blobs)."""
    try:
        with os.scandir(lance_dir) as entries:
            for entry in entries:
                if not entry.is_file(follow_symlinks=False):
                    continue
                path = Path(entry.path)
                if _is_stale_artifact(path):
                    yield path
    except OSError:
        return


def _scan_storage_subdir(dir_path: Path) -> Iterator[Path]:
    """Walk storage layout without descending into Lance segment trees."""
    try:
        with os.scandir(dir_path) as entries:
            for entry in entries:
                path = Path(entry.path)
                if entry.is_file(follow_symlinks=False):
                    if _is_stale_artifact(path):
                        yield path
                elif entry.is_dir(follow_symlinks=False):
                    if entry.name in _SKIP_WALK_DIRS:
                        continue
                    if entry.name.endswith(".lance"):
                        yield from _scan_lance_dataset_shallow(path)
                    else:
                        yield from _scan_storage_subdir(path)
    except OSError:
        return


def _iter_stale_artifact_paths(storage_dir: Path) -> Iterator[Path]:
    """Yield stale lock/tmp candidates without scanning Lance version blobs."""
    try:
        with os.scandir(storage_dir) as entries:
            for entry in entries:
                path = Path(entry.path)
                if entry.is_file(follow_symlinks=False):
                    if _is_stale_artifact(path):
                        yield path
                elif entry.is_dir(follow_symlinks=False):
                    if entry.name in _SKIP_WALK_DIRS:
                        continue
                    if entry.name.endswith(".lance"):
                        yield from _scan_lance_dataset_shallow(path)
                    else:
                        yield from _scan_storage_subdir(path)
    except OSError:
        return


def _iter_stale_artifact_paths_deep(storage_dir: Path) -> Iterator[Path]:
    """Full-tree scan used only when ``force=True`` (legacy / nested lock layouts)."""
    for root, dirs, files in os.walk(storage_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in _SKIP_WALK_DIRS and not d.startswith(".")]
        root_path = Path(root)
        for filename in files:
            candidate = root_path / filename
            if _is_stale_artifact(candidate):
                yield candidate


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
    now = time.time()
    candidates = (
        _iter_stale_artifact_paths_deep(storage_dir)
        if force
        else _iter_stale_artifact_paths(storage_dir)
    )
    for candidate in candidates:
        if not _artifact_is_safe_to_remove(candidate, now=now):
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
        if getattr(connection, "is_open", True) is not False:
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
    with _connections_lock:
        if connection not in _open_connections:
            _open_connections.append(connection)
    _ensure_shutdown_registered()


def shutdown_all_lancedb_connections() -> None:
    """Close all tracked LanceDB connections (CLI/MCP/ingest graceful shutdown)."""
    with _connections_lock:
        pending = list(_open_connections)
        _open_connections.clear()
    for conn in reversed(pending):
        close_lancedb_connection(conn)


def _run_shutdown_hooks() -> None:
    """Single shutdown entry: optional MCP cleanup, then close all connections."""
    global _shutdown_ran
    with _shutdown_lock:
        if _shutdown_ran:
            return
        _shutdown_ran = True
    if _extra_shutdown is not None:
        try:
            _extra_shutdown()
        except Exception as exc:
            logger.warning("LanceDB extra cleanup failed: %s", exc)
    shutdown_all_lancedb_connections()


def _ensure_shutdown_registered() -> None:
    global _shutdown_registered
    with _shutdown_lock:
        if not _shutdown_registered:
            atexit.register(_run_shutdown_hooks)
            _shutdown_registered = True


def reset_lancedb_storage_state() -> None:
    """Test helper: clear tracked connections and shutdown flag."""
    global _shutdown_registered, _shutdown_ran, _extra_shutdown
    with _connections_lock:
        _open_connections.clear()
    with _preflight_lock:
        _preflight_done.clear()
    with _shutdown_lock:
        _shutdown_registered = False
        _shutdown_ran = False
        _extra_shutdown = None
    from vector_store_ports import set_vector_store_backend
    from vector_store_paths import reset_vector_store_root_cache

    set_vector_store_backend(None)
    reset_vector_store_root_cache()


def register_lancedb_shutdown_hooks(
    extra_cleanup: Callable[[], None] | None = None,
) -> None:
    """Register SIG/atexit hooks for MCP servers and long-lived agent processes."""
    global _extra_shutdown
    if extra_cleanup is not None:
        _extra_shutdown = extra_cleanup
    _ensure_shutdown_registered()

    import signal

    def _signal_handler(signum, frame):  # noqa: ARG001
        logger.info("LanceDB shutdown hook received signal %s", signum)
        _run_shutdown_hooks()

    for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _signal_handler)
        except (OSError, ValueError):
            pass
