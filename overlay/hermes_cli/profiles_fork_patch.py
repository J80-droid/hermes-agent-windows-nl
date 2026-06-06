"""Orphan profile wrapper discovery (Tier B)."""
from __future__ import annotations

import re
from pathlib import Path


_ORPHAN_WRAPPER_RE = re.compile(r"hermes -p (\S+)", re.IGNORECASE)


def iter_orphan_profile_wrappers(
    wrapper_dir: Path | None = None,
) -> list[tuple[str, str]]:
    from hermes_cli.profiles import _get_wrapper_dir, profile_exists

    root = wrapper_dir or _get_wrapper_dir()
    orphans: list[tuple[str, str]] = []
    if not root.is_dir():
        return orphans
    for wrapper in root.iterdir():
        if not wrapper.is_file():
            continue
        try:
            content = wrapper.read_text(encoding="utf-8")
        except OSError:
            continue
        if "hermes -p" not in content:
            continue
        match = _ORPHAN_WRAPPER_RE.search(content)
        if not match:
            continue
        profile_name = match.group(1)
        if not profile_exists(profile_name):
            orphans.append((wrapper.name, profile_name))
    return orphans


def remove_orphan_profile_wrappers(
    wrapper_dir: Path | None = None,
) -> list[str]:
    from hermes_cli.profiles import remove_wrapper_script

    removed: list[str] = []
    for wrapper_name, _profile in iter_orphan_profile_wrappers(wrapper_dir):
        if remove_wrapper_script(wrapper_name):
            removed.append(wrapper_name)
    return removed


def apply_profiles_fork_patch() -> None:
    import hermes_cli.profiles as profiles

    if getattr(profiles, "_fork_profiles_orphan_patch_applied", False):
        return
    if not hasattr(profiles, "iter_orphan_profile_wrappers"):
        profiles.iter_orphan_profile_wrappers = iter_orphan_profile_wrappers  # type: ignore[attr-defined]
    if not hasattr(profiles, "remove_orphan_profile_wrappers"):
        profiles.remove_orphan_profile_wrappers = remove_orphan_profile_wrappers  # type: ignore[attr-defined]
    profiles._fork_profiles_orphan_patch_applied = True  # type: ignore[attr-defined]
