"""Shared config snapshot (mtime-keyed) for CLI, gateway, and sandbox."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

_snapshot: ConfigSnapshot | None = None


@dataclass(frozen=True)
class ConfigSnapshot:
    """Raw + expanded config for a single on-disk mtime."""

    path: Path
    mtime_ns: int
    raw: dict[str, Any]
    expanded: dict[str, Any]


def config_path_mtime_ns() -> int:
    """Return mtime_ns of the active Hermes config file (0 if missing)."""
    try:
        from hermes_cli.config import get_config_path

        path = get_config_path()
        if path.is_file():
            return path.stat().st_mtime_ns
    except OSError:
        pass
    return 0


def bust_config_snapshot() -> None:
    """Clear the in-process config snapshot."""
    global _snapshot
    _snapshot = None


def get_config_snapshot(*, force_reload: bool = False) -> ConfigSnapshot:
    """Load or return cached raw + expanded config."""
    global _snapshot
    from hermes_cli.config import get_config_path, load_config_readonly, read_raw_config

    path = get_config_path()
    try:
        mtime_ns = path.stat().st_mtime_ns if path.is_file() else 0
    except OSError:
        mtime_ns = 0
    if (
        not force_reload
        and _snapshot is not None
        and _snapshot.path == path
        and _snapshot.mtime_ns == mtime_ns
    ):
        return _snapshot
    raw = read_raw_config()
    expanded = load_config_readonly() or {}
    _snapshot = ConfigSnapshot(path=path, mtime_ns=mtime_ns, raw=raw, expanded=expanded)
    return _snapshot
