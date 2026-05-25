"""Absolute VectorStore path resolution (no LanceDB import)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

AGENT_NAME = "Hermes"
VECTOR_STORE_DIRNAME = "VectorStore"
DEFAULT_DOMAIN_SUBDIR = "default"

_VECTOR_STORE_ROOT_CACHE: Path | None = None
_VECTOR_STORE_ROOT_ENV_KEY: str | None = None


def _vector_store_env_key() -> str:
    if sys.platform == "win32":
        return (os.environ.get("LOCALAPPDATA") or "").strip()
    return str(Path.home())


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
    global _VECTOR_STORE_ROOT_CACHE, _VECTOR_STORE_ROOT_ENV_KEY
    env_key = _vector_store_env_key()
    if _VECTOR_STORE_ROOT_CACHE is not None and _VECTOR_STORE_ROOT_ENV_KEY == env_key:
        return _VECTOR_STORE_ROOT_CACHE

    if sys.platform == "win32":
        local_app = env_key
        if local_app:
            base = Path(local_app)
        else:
            base = Path.home() / "AppData" / "Local"
        root = base / "hermes" / VECTOR_STORE_DIRNAME
    else:
        root = Path.home() / ".hermes" / VECTOR_STORE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve()
    _VECTOR_STORE_ROOT_CACHE = resolved
    _VECTOR_STORE_ROOT_ENV_KEY = env_key
    return resolved


def reset_vector_store_root_cache() -> None:
    """Test helper: clear cached VectorStore root."""
    global _VECTOR_STORE_ROOT_CACHE, _VECTOR_STORE_ROOT_ENV_KEY
    _VECTOR_STORE_ROOT_CACHE = None
    _VECTOR_STORE_ROOT_ENV_KEY = None


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
