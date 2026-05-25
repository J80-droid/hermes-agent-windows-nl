"""Strict filesystem sandbox for Hermes agent file tools.

All agent file operations (read_file, write_file, patch, search_files) must
stay within a single workspace root.  The root is resolved once per process:

  1. ``HERMES_WORKSPACE_ROOT`` environment variable
  2. ``workspace.root`` in config.yaml
  3. ``TERMINAL_CWD`` (project-specific workspace when the agent is launched
     from a checkout)
  4. Hardcoded default:
       - Windows: ``%LOCALAPPDATA%\\hermes\\workspace``
       - Other:   ``~/.hermes/workspace``

Defense-in-depth only — the terminal tool runs as the same OS user and can
bypass this boundary.  See ``agent/file_safety.py`` for the same caveat.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SANDBOX_ROOT_CACHE: Path | None = None
_ENFORCE_CACHE: bool | None = None

# Windows extended-length and device paths — reject before resolve().
_WINDOWS_DEVICE_PREFIXES = (
    "\\\\.\\",
    "\\\\?\\",
    "//./",
    "//?/",
)


class FilesystemSandboxViolation(Exception):
    """Raised when a path escapes the configured workspace root."""


def default_workspace_root() -> Path:
    """Return the built-in workspace root (created on first use)."""
    if sys.platform == "win32":
        local_app = (os.environ.get("LOCALAPPDATA") or "").strip()
        if local_app:
            root = Path(local_app) / "hermes" / "workspace"
        else:
            root = Path.home() / "AppData" / "Local" / "hermes" / "workspace"
    else:
        root = Path.home() / ".hermes" / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def is_sandbox_enforced() -> bool:
    """Return True when file-tool sandbox checks are active."""
    global _ENFORCE_CACHE
    if _ENFORCE_CACHE is not None:
        return _ENFORCE_CACHE

    env_flag = os.environ.get("HERMES_ENFORCE_FILE_SANDBOX", "").strip().lower()
    if env_flag in {"0", "false", "no", "off"}:
        _ENFORCE_CACHE = False
        return _ENFORCE_CACHE
    if env_flag in {"1", "true", "yes", "on"}:
        _ENFORCE_CACHE = True
        return _ENFORCE_CACHE

    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        workspace_cfg = cfg.get("workspace") or {}
        if isinstance(workspace_cfg, dict):
            enforce = workspace_cfg.get("enforce_sandbox")
            if enforce is not None:
                _ENFORCE_CACHE = bool(enforce)
                return _ENFORCE_CACHE
    except Exception:
        pass

    _ENFORCE_CACHE = True
    return _ENFORCE_CACHE


def _expand_workspace_path(raw: str) -> Path:
    """Expand user/env vars and resolve to an absolute path."""
    expanded = Path(os.path.expandvars(os.path.expanduser(raw.strip())))
    try:
        if not expanded.is_absolute():
            return (Path.cwd() / expanded).resolve()
        return expanded.resolve()
    except OSError as exc:
        raise OSError(f"Cannot resolve workspace path {raw!r}: {exc}") from exc


def get_workspace_root() -> Path:
    """Resolve and cache the active workspace root."""
    global _SANDBOX_ROOT_CACHE
    if _SANDBOX_ROOT_CACHE is not None:
        return _SANDBOX_ROOT_CACHE

    candidates: list[str] = []

    env_root = os.environ.get("HERMES_WORKSPACE_ROOT", "").strip()
    if env_root:
        candidates.append(env_root)

    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        workspace_cfg = cfg.get("workspace") or {}
        if isinstance(workspace_cfg, dict):
            cfg_root = str(workspace_cfg.get("root") or "").strip()
            if cfg_root:
                candidates.append(cfg_root)
    except Exception:
        pass

    terminal_cwd = os.environ.get("TERMINAL_CWD", "").strip()
    if terminal_cwd:
        candidates.append(terminal_cwd)

    root: Path | None = None
    for raw in candidates:
        try:
            root = _expand_workspace_path(raw)
            break
        except OSError:
            continue

    if root is None:
        root = default_workspace_root()

    root.mkdir(parents=True, exist_ok=True)
    _SANDBOX_ROOT_CACHE = root.resolve()
    logger.debug("Filesystem sandbox root: %s", _SANDBOX_ROOT_CACHE)
    return _SANDBOX_ROOT_CACHE


def reset_workspace_cache() -> None:
    """Clear cached sandbox settings (for tests)."""
    global _SANDBOX_ROOT_CACHE, _ENFORCE_CACHE
    _SANDBOX_ROOT_CACHE = None
    _ENFORCE_CACHE = None


def has_forbidden_path_content(path_str: str) -> str | None:
    """Return an error message for obviously malicious path strings.

    Expands ``%ENV%`` and ``~`` before checking traversal components so
    obfuscated ``..`` via environment variables is caught.
    """
    if not path_str or not str(path_str).strip():
        return "Empty path is not allowed."

    if "\x00" in path_str:
        return "Path contains null bytes."

    expanded = os.path.expandvars(os.path.expanduser(str(path_str)))
    normalized = expanded.replace("/", os.sep)
    if sys.platform == "win32":
        normalized_lower = normalized.lower()
        for prefix in _WINDOWS_DEVICE_PREFIXES:
            if normalized_lower.startswith(prefix.lower()):
                return f"Device or extended path prefix is not allowed: {prefix!r}"
    else:
        for prefix in _WINDOWS_DEVICE_PREFIXES:
            if normalized.startswith(prefix):
                return f"Device or extended path prefix is not allowed: {prefix!r}"

    parts = Path(expanded).parts
    if ".." in parts:
        return "Path traversal ('..') is not allowed."

    return None


def _path_is_under_root(resolved: Path, root: Path) -> bool:
    """Return True when *resolved* is the root or a descendant of *root*."""
    try:
        root_resolved = root.resolve()
    except OSError:
        root_resolved = Path(os.path.normpath(str(root)))

    try:
        candidate = resolved.resolve()
    except OSError:
        candidate = Path(os.path.normpath(str(resolved)))

    try:
        candidate.relative_to(root_resolved)
        return True
    except ValueError:
        pass

    if sys.platform == "win32":
        candidate_norm = os.path.normcase(str(candidate))
        root_norm = os.path.normcase(str(root_resolved))
        if candidate_norm == root_norm:
            return True
        return candidate_norm.startswith(root_norm + os.sep)

    return False


def resolve_path_within_sandbox(
    raw_path: str,
    *,
    resolution_base: str | Path | None = None,
    sandbox_root: Path | None = None,
) -> Path:
    """Resolve *raw_path* and ensure it stays inside the workspace root."""
    forbidden = has_forbidden_path_content(raw_path)
    if forbidden:
        raise FilesystemSandboxViolation(forbidden)

    root = sandbox_root or get_workspace_root()
    p = Path(raw_path).expanduser()

    if not p.is_absolute():
        base = resolution_base or os.environ.get("TERMINAL_CWD") or str(root)
        p = Path(base) / p

    try:
        resolved = p.resolve()
    except OSError as exc:
        raise FilesystemSandboxViolation(f"Cannot resolve path: {exc}") from exc

    if not _path_is_under_root(resolved, root):
        raise FilesystemSandboxViolation(
            f"Path escapes workspace sandbox: {raw_path!r} resolves to {resolved} "
            f"which is outside {root}"
        )
    return resolved


def check_filesystem_sandbox(
    raw_path: str,
    *,
    resolution_base: str | Path | None = None,
    sandbox_root: Path | None = None,
) -> str | None:
    """Return an error message when *raw_path* violates the sandbox, else None."""
    if not is_sandbox_enforced():
        return None
    try:
        resolve_path_within_sandbox(
            raw_path,
            resolution_base=resolution_base,
            sandbox_root=sandbox_root,
        )
    except FilesystemSandboxViolation as exc:
        return str(exc)
    return None


def validate_agent_path_for_task(
    raw_path: str,
    *,
    resolution_base: str | Path | None,
    sandbox_root: Path | None = None,
) -> tuple[Path | None, str | None]:
    """Validate and resolve an agent path; returns (resolved, error_message)."""
    if not is_sandbox_enforced():
        try:
            p = Path(raw_path).expanduser()
            if not p.is_absolute():
                base = resolution_base or os.environ.get("TERMINAL_CWD", os.getcwd())
                p = Path(base) / p
            return p.resolve(), None
        except (OSError, ValueError) as exc:
            return None, f"Cannot resolve path: {exc}"

    try:
        resolved = resolve_path_within_sandbox(
            raw_path,
            resolution_base=resolution_base,
            sandbox_root=sandbox_root,
        )
        return resolved, None
    except FilesystemSandboxViolation as exc:
        return None, str(exc)
