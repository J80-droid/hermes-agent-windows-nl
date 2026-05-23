#!/usr/bin/env python3
"""Migrate legacy [COLOR_*] tokens from SOUL.md files to plain markdown.

Replaces:
    [COLOR_BLUE] ... [RESET]
    [COLOR_TEAL] ... [RESET]
    [COLOR_GREEN] ... [RESET]

With: nothing (tokens are stripped).  Markdown headings and bold markers are preserved.

Usage:
    python scripts/migrate_soul_tokens.py SOUL.md
    python scripts/migrate_soul_tokens.py --in-place SOUL.md
    python scripts/migrate_soul_tokens.py --all-profiles
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_LEGACY_TOKEN_RE = re.compile(
    r"\[(COLOR_BLUE|COLOR_TEAL|COLOR_GREEN|RESET)\]",
    re.IGNORECASE,
)


def migrate_text(text: str) -> str:
    """Strip legacy colour tokens while preserving markdown structure."""
    cleaned = _LEGACY_TOKEN_RE.sub("", text)
    # Collapse any accidental double spaces left by token removal
    cleaned = re.sub(r"  +", " ", cleaned)
    # Clean up empty lines that may have been left
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def migrate_file(path: Path, in_place: bool = False) -> str:
    text = path.read_text(encoding="utf-8")
    cleaned = migrate_text(text)
    if in_place:
        backup = path.with_suffix(path.suffix + ".backup-legacy-tokens")
        backup.write_text(text, encoding="utf-8")
        path.write_text(cleaned, encoding="utf-8")
        print(f"[OK] Migrated (backup: {backup}): {path}")
    return cleaned


def find_all_profile_souls() -> list[Path]:
    import os

    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    souls: list[Path] = []
    # Root SOUL.md
    root_soul = hermes_home / "SOUL.md"
    if root_soul.exists():
        souls.append(root_soul)
    # Profile SOULs
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.exists():
        for profile_dir in profiles_dir.iterdir():
            soul = profile_dir / "SOUL.md"
            if soul.exists():
                souls.append(soul)
    return souls


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy [COLOR_*] tokens from SOUL.md")
    parser.add_argument("path", nargs="?", help="Single SOUL.md file to migrate")
    parser.add_argument("--in-place", action="store_true", help="Overwrite file (keeps .backup-legacy-tokens)")
    parser.add_argument("--all-profiles", action="store_true", help="Migrate all profile SOUL.md files")
    parser.add_argument("--dry-run", action="store_true", help="Print result without writing")
    args = parser.parse_args()

    if args.all_profiles:
        souls = find_all_profile_souls()
        if not souls:
            print("[INFO] No SOUL.md files found under HERMES_HOME.")
            return 0
        for soul in souls:
            if args.dry_run:
                print(f"\n--- {soul} ---")
                print(migrate_file(soul, in_place=False)[:800])
            else:
                migrate_file(soul, in_place=True)
        return 0

    if not args.path:
        parser.error("Provide a SOUL.md path or use --all-profiles")

    soul_path = Path(args.path)
    if not soul_path.exists():
        print(f"[ERROR] File not found: {soul_path}", file=sys.stderr)
        return 1

    cleaned = migrate_file(soul_path, in_place=args.in_place)
    print(cleaned)
    return 0


if __name__ == "__main__":
    sys.exit(main())
