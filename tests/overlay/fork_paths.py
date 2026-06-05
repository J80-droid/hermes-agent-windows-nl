"""Resolve fork module paths (Tier B overlay vs legacy Tier A on disk)."""
from __future__ import annotations

from pathlib import Path


def fork_repo_path(repo: Path, relative: str) -> Path:
    rel = relative.replace("\\", "/").lstrip("./")
    overlay = repo / "overlay" / rel
    tier_a = repo / rel
    if overlay.is_file():
        return overlay
    return tier_a


def fork_repo_paths_exist(repo: Path, *relatives: str) -> bool:
    return all(fork_repo_path(repo, rel).is_file() for rel in relatives)
