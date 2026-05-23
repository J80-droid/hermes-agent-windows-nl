"""Dedupliceer MEMORY.md / USER.md per profiel op §-secties (runtime %LOCALAPPDATA%\\hermes).

Gebruik na sync-duplicaten of [OVER] door herhaalde trust-blokken. Daarna:
audit_profile_memories.ps1 en RUN_MEMORY_PRODUCTION_GATE.bat.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SECTION_RE = re.compile(r"\s*§\s*")
_MOJIBAKE_LINE_RE = re.compile(r"^\s*Â\s*$", re.MULTILINE)


def _normalize_section(text: str) -> str:
    cleaned = _MOJIBAKE_LINE_RE.sub("", text)
    return " ".join(cleaned.split()).lower()


def deduplicate_content(content: str) -> str:
    """Return §-deduplicated body (strips mojibake lines, drops duplicate preamble/sections)."""
    sections = SECTION_RE.split(content)
    seen_norms: set[str] = set()
    unique_sections: list[str] = []

    for sec in sections:
        sec_clean = _MOJIBAKE_LINE_RE.sub("", sec).strip()
        if not sec_clean:
            continue
        norm = _normalize_section(sec_clean)
        if norm not in seen_norms:
            seen_norms.add(norm)
            unique_sections.append(sec_clean)

    new_content = "\n§\n".join(unique_sections)
    return new_content.strip() + "\n"


def deduplicate_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding='utf-8-sig')
        sections = SECTION_RE.split(content)
        new_content = deduplicate_content(content)
        path.write_text(new_content, encoding='utf-8')
        print(
            f"[OK] Deduplicated {path}: {len(sections)} -> {len(unique_sections)} sections. "
            f"New size: {len(new_content)} chars"
        )
        return True
    except OSError as e:
        print(f"[ERROR] Failed to deduplicate {path}: {e}", file=sys.stderr)
        return False


def main() -> int:
    hermes_root = Path(os.environ.get('LOCALAPPDATA', '')) / 'hermes'
    if not (hermes_root / 'config.yaml').is_file():
        hermes_root = Path(os.environ.get('USERPROFILE', '')) / '.hermes'
        
    profiles_dir = hermes_root / 'profiles'
    if not profiles_dir.is_dir():
        print(f"[ERROR] Profiles directory not found: {profiles_dir}", file=sys.stderr)
        return 1

    print(f"Scanning profiles under: {profiles_dir}")
    failed = 0
    for profile_dir in sorted(profiles_dir.iterdir()):
        if not profile_dir.is_dir():
            continue
        memories_dir = profile_dir / "memories"
        if not memories_dir.is_dir():
            continue
        print(f"\n--- Profile: {profile_dir.name} ---")
        for filename in ("MEMORY.md", "USER.md"):
            filepath = memories_dir / filename
            if filepath.is_file() and not deduplicate_file(filepath):
                failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
