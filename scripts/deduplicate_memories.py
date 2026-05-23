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


def deduplicate_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        # Read file with UTF-8, handling BOM if present
        content = path.read_text(encoding='utf-8-sig')
        
        # Split by § character
        sections = SECTION_RE.split(content)
        
        seen_norms = set()
        unique_sections = []
        
        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue
            # Normalize whitespace for duplicate detection
            norm = " ".join(sec_clean.split()).lower()
            if norm not in seen_norms:
                seen_norms.add(norm)
                unique_sections.append(sec_clean)
        
        # Join back with standard separator
        # Keep UTF-8 BOM if it was there or write normal UTF-8
        new_content = "\n§\n".join(unique_sections)
        # Ensure a trailing newline is not adding empty sections
        new_content = new_content.strip() + "\n"
        
        # Write back to file as UTF-8
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
