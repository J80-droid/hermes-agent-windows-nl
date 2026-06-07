"""Fork update-check helpers (upstream-aware compare ref)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def _resolve_update_compare_ref(repo_dir: Path) -> tuple[str, str, str]:
    """Return (remote, ref, label) for behind-count.

    Forks with an ``upstream`` remote compare against Nous ``upstream/main``;
    otherwise ``origin/main``.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "upstream"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0 and (result.stdout or "").strip():
            return "upstream", "upstream/main", "upstream"
    except Exception:
        pass
    return "origin", "origin/main", "origin"


def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    """Count commits behind origin/main (or upstream/main on forks)."""
    import hermes_cli.banner as banner_mod

    remote, compare_ref, _label = _resolve_update_compare_ref(repo_dir)
    try:
        subprocess.run(
            ["git", "fetch", remote, "--quiet"],
            capture_output=True,
            timeout=10,
            cwd=str(repo_dir),
        )
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD..{compare_ref}"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def apply_banner_fork_patch() -> None:
    import hermes_cli.banner as banner_mod

    if getattr(banner_mod, "_fork_banner_patch_applied", False):
        return

    _orig_check = banner_mod._check_via_local_git

    def _check_via_local_git_patched(repo_dir: Path) -> Optional[int]:
        return _check_via_local_git(repo_dir)

    banner_mod._resolve_update_compare_ref = _resolve_update_compare_ref  # type: ignore[attr-defined]
    banner_mod._check_via_local_git = _check_via_local_git_patched  # type: ignore[assignment]
    banner_mod._fork_banner_patch_applied = True  # type: ignore[attr-defined]
