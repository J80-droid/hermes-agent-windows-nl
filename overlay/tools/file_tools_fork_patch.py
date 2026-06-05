"""Fork patch: wire Tier-A file_tools path resolution to overlay filesystem_sandbox."""
from __future__ import annotations

from pathlib import Path


def apply_file_tools_fork_patch() -> None:
    """Monkey-patch ``tools.file_tools._resolve_path_for_task`` when sandbox is enforced."""
    import tools.file_tools as ft
    from hermes_cli import filesystem_sandbox as fs

    if getattr(ft, "_fork_file_tools_patch_applied", False):
        return

    _orig_resolve = ft._resolve_path_for_task
    _orig_check_sensitive = ft._check_sensitive_path

    def _resolve_path_for_task(filepath: str, task_id: str = "default") -> Path:
        if not fs.is_sandbox_enforced():
            return _orig_resolve(filepath, task_id)
        base = ft._resolve_base_dir(task_id)
        resolved, err = fs.validate_agent_path_for_task(
            filepath,
            resolution_base=base,
        )
        if err:
            raise fs.FilesystemSandboxViolation(err)
        if resolved is None:
            raise fs.FilesystemSandboxViolation(f"Cannot resolve path: {filepath!r}")
        return resolved

    def _check_sensitive_path(filepath: str, task_id: str = "default") -> str | None:
        try:
            return _orig_check_sensitive(filepath, task_id)
        except fs.FilesystemSandboxViolation as exc:
            return str(exc)

    ft._resolve_path_for_task = _resolve_path_for_task  # type: ignore[assignment]
    ft._check_sensitive_path = _check_sensitive_path  # type: ignore[assignment]
    ft._fork_file_tools_patch_applied = True  # type: ignore[attr-defined]
