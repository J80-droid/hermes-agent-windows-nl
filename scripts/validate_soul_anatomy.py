#!/usr/bin/env python3
"""Validate SOUL.md files against SOUL_ANATOMY_SPEC section list."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    r"^# SOUL\.md - ",
    r"^## Identity\s",
    r"^## Values & Principles\s",
    r"^## Communication Style\s",
    r"^### Interaction met J\.\s",
    r"^### Output conventions \(institutional\)\s",
    r"^## Expertise & Knowledge\s",
    r"^## Hard Limits\s",
    r"^## Workflow\s",
    r"^## Tool Usage\s",
    r"^## Memory Policy\s",
    r"^## Example Interaction\s",
]

LEGACY_FORBIDDEN = [
    r"^## Advisory & trust\s",
    r"^## Outputformaat \(institutioneel\)\s",
    r"^## Tool governance \(domein-minimum\)\s",
    r"^## Interaction met J\.\s",
    r"^# SOUL: ",
]

LEGACY_ALLOWED_WITH_WARNING = [
    r"^## Tone\s",
    r"^## Mission\s",
]


def hermes_home() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    if (local / "config.yaml").exists():
        return local
    home = Path.home() / ".hermes"
    if (home / "config.yaml").exists():
        return home
    return local


def find_souls(home: Path, *, profiles_only: bool = False) -> list[Path]:
    souls: list[Path] = []
    if not profiles_only:
        root_soul = home / "SOUL.md"
        if root_soul.exists():
            souls.append(root_soul)
    profiles = home / "profiles"
    if profiles.is_dir():
        for d in sorted(profiles.iterdir()):
            p = d / "SOUL.md"
            if p.is_file():
                souls.append(p)
    return souls


def _section_order_issues(text: str) -> list[str]:
    issues: list[str] = []
    comm = re.search(r"^## Communication Style\s", text, re.MULTILINE)
    out = re.search(r"^### Output conventions \(institutional\)\s", text, re.MULTILINE)
    exp = re.search(r"^## Expertise & Knowledge\s", text, re.MULTILINE)
    if comm and out and exp and not (comm.start() < out.start() < exp.start()):
        issues.append("Output conventions not between Communication Style and Expertise")
    out_count = len(re.findall(r"^### Output conventions \(institutional\)\s", text, re.MULTILINE))
    if out_count != 1:
        issues.append(f"expected 1 Output conventions block, found {out_count}")
    if not re.search(r"^### Trust & verification", text, re.MULTILINE):
        issues.append("missing ### Trust & verification")
    return issues


def validate_file(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8-sig")
    missing = [pat for pat in REQUIRED_SECTIONS if not re.search(pat, text, re.MULTILINE)]
    legacy = [pat for pat in LEGACY_FORBIDDEN if re.search(pat, text, re.MULTILINE)]
    warnings = [pat for pat in LEGACY_ALLOWED_WITH_WARNING if re.search(pat, text, re.MULTILINE)]
    order_issues = _section_order_issues(text)
    return missing, legacy + order_issues + [f"warn:{w}" for w in warnings]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SOUL.md anatomy sections")
    parser.add_argument("path", nargs="?", help="Single SOUL.md file")
    parser.add_argument("--all-profiles", action="store_true", help="Validate all runtime SOUL files")
    parser.add_argument("--repo-templates", action="store_true", help="Validate docs/templates/SOUL_*")
    args = parser.parse_args()

    paths: list[Path] = []
    if args.path:
        paths.append(Path(args.path))
    elif args.all_profiles:
        paths = find_souls(hermes_home(), profiles_only=True)
    elif args.repo_templates:
        repo = Path(__file__).resolve().parents[1]
        templates = repo / "docs" / "templates"
        paths = sorted(templates.glob("SOUL_*_DOMAIN.md")) + [templates / "SOUL_CORE_ORCHESTRATOR.md"]
    else:
        parser.print_help()
        return 2

    if not paths:
        print("[WARN] Geen SOUL.md bestanden gevonden.", file=sys.stderr)
        return 0

    failed = 0
    for p in paths:
        if not p.exists():
            print(f"[SKIP] {p} (ontbreekt)")
            continue
        missing, issues = validate_file(p)
        if missing or [i for i in issues if not i.startswith("warn:")]:
            failed += 1
            print(f"[FAIL] {p}")
            for m in missing:
                print(f"  mist: {m}")
            for i in issues:
                if not i.startswith("warn:"):
                    print(f"  legacy: {i}")
        else:
            print(f"[OK] {p}")
            for w in issues:
                if w.startswith("warn:"):
                    print(f"  {w} (draai migrate + SYNC_SOUL_SNIPPETS)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
