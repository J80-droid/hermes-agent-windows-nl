"""Legal profile runtime path hints (Tier B overlay)."""
from __future__ import annotations

import os
from pathlib import Path


def build_legal_runtime_paths_block() -> str:
    """Ephemeral path hints for legal profile (file tools; not cached in SOUL)."""
    try:
        from agent.file_safety import _resolve_active_profile_name
    except Exception:
        return ""
    if _resolve_active_profile_name() != "legal":
        return ""
    try:
        from hermes_constants import get_default_hermes_root

        root = get_default_hermes_root()
    except Exception:
        return ""
    matters = (root / "profiles" / "legal" / "LEGAL_ACTIVE_MATTERS.md").resolve()
    userprofile = os.environ.get("USERPROFILE", str(Path.home()))
    raw_legal = Path(userprofile) / "data" / "raw_source_files" / "04_Legal_Corporate"
    lance_legal = Path(userprofile) / "data" / "lancedb" / "legal"
    return (
        "## Runtime paths (legal profile — file tools)\n"
        f"- LEGAL_ACTIVE_MATTERS: {matters}\n"
        f"- Legal bronnen: {raw_legal.resolve()}\n"
        f"- LanceDB legal: {lance_legal.resolve()}\n"
        "Gebruik deze absolute paden; open geen letterlijke `%LOCALAPPDATA%`-placeholders."
    )


def augment_ephemeral_for_legal_profile(ephemeral: str | None) -> str | None:
    """Append legal runtime path block when profile is legal."""
    block = build_legal_runtime_paths_block()
    if not block:
        return ephemeral
    base = (ephemeral or "").strip()
    if base:
        return f"{base}\n\n{block}"
    return block
