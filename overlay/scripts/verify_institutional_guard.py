#!/usr/bin/env python3
"""Run institutional tests when renderer-related files changed (pre-commit guard).

Usage:
    python scripts/verify_institutional_guard.py           # staged + unstaged vs HEAD
    python scripts/verify_institutional_guard.py --ci    # only staged (for hooks)
    python scripts/verify_institutional_guard.py --force # always run tests
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

# Mirror windows/merge_upstream_fork.ps1 $keepOurs (institutional subset).
TIER_A_FORK_ONLY_CLI_PATTERNS = (
    "_append_status_bar_cost_fragments",
    'canonical == "cost"',
    "_handle_cost_command",
    'canonical == "tps"',
    "_handle_tps_command",
    "_record_stream_tps_delta",
    "_freeze_stream_tps_segment",
)

GUARD_GLOBS = (
    "overlay/hermes_cli/institutional_render.py",
    "overlay/hermes_cli/markdown_output_normalize.py",
    "overlay/hermes_cli/display_markdown.py",
    "web/src/components/Markdown.tsx",
    "web/src/lib/institutionalMarkdown.ts",
    "ui-tui/src/lib/institutionalMarkdownNormalize.ts",
    "web/src/lib/institutionalWebPalette.ts",
    "web/src/lib/assistantDisplayEvents.ts",
    "web/src/contexts/AssistantDisplayProvider.tsx",
    "config/palettes.yaml",
    "scripts/diagnose_renderer.py",
    "scripts/score_institutional_render.py",
    "windows/team_display.defaults",
    "windows/apply_team_display.ps1",
    "windows/scripts/apply_team_display_profiles.py",
    "docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md",
    "docs/INSTITUTIONAL_PRESENTATION.md",
    "docs/INSTITUTIONAL_PORTING_GUIDE.md",
    ".cursor/rules/institutional-presentatie.mdc",
    "tests/cli/test_institutional_rich_render.py",
    "tests/hermes_cli/test_normalizer_ts_parity.py",
    "tests/hermes_cli/test_markdown_output_normalize.py",
)


def _glob_match(path: str, pattern: str) -> bool:
    norm = path.replace("\\", "/").lstrip("./")
    if "**" in pattern:
        prefix = pattern.split("**", 1)[0].rstrip("/")
        if prefix and not norm.startswith(prefix):
            return False
        rest = pattern.split("**", 1)[1].lstrip("/")
        if not rest:
            return True
        return fnmatch.fnmatch(norm, f"*{rest}") or fnmatch.fnmatch(norm, rest)
    return fnmatch.fnmatch(norm, pattern)


def _changed_paths(*, staged_only: bool) -> list[str]:
    repo = Path(__file__).resolve().parents[2]
    diff_cmd = ["git", "diff", "--name-only"]
    if staged_only:
        diff_cmd.append("--cached")
    else:
        diff_cmd.extend(["HEAD"])
    out = subprocess.run(
        diff_cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    paths = [p.strip() for p in out.stdout.splitlines() if p.strip()]
    if staged_only:
        return paths
    unstaged = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    for p in unstaged.stdout.splitlines():
        p = p.strip()
        if p and p not in paths:
            paths.append(p)
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    for p in untracked.stdout.splitlines():
        p = p.strip()
        if p and p not in paths:
            paths.append(p)
    return paths


def _touches_guard(paths: list[str]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        norm = path.replace("\\", "/")
        for pattern in GUARD_GLOBS:
            if _glob_match(norm, pattern):
                hits.append(norm)
                break
    return hits


def _verify_tier_a_cli_no_fork_hooks(repo: Path) -> int:
    cli_path = repo / "cli.py"
    if not cli_path.is_file():
        print("[FAIL] cli.py ontbreekt")
        return 1
    text = cli_path.read_text(encoding="utf-8")
    hits = [p for p in TIER_A_FORK_ONLY_CLI_PATTERNS if p in text]
    if hits:
        print("[FAIL] Tier A cli.py bevat fork-only hooks (horen in overlay/):")
        for h in hits:
            print(f"  - {h}")
        return 1
    print("[OK] Tier A cli.py — geen fork-only cost/tps hooks")
    return 0


def _run_guard_tests(repo: Path) -> int:
    steps = [
        (
            "pytest institutional subset",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/cli/test_institutional_rich_render.py",
                "tests/hermes_cli/test_markdown_output_normalize.py",
                "tests/hermes_cli/test_normalizer_ts_parity.py",
                "-q",
            ],
        ),
        (
            "diagnose_renderer --verify",
            [sys.executable, "scripts/diagnose_renderer.py", "--verify"],
        ),
        (
            "verify_pseudo_table_normalizer --verify",
            [sys.executable, "scripts/verify_pseudo_table_normalizer.py", "--verify"],
        ),
        (
            "score_institutional_render --verify",
            [sys.executable, "scripts/score_institutional_render.py", "--verify"],
        ),
    ]
    for label, cmd in steps:
        print(f"\n--- {label} ---")
        r = subprocess.run(cmd, cwd=repo)
        if r.returncode != 0:
            print(f"[FAIL] {label}")
            return r.returncode
        print(f"[OK] {label}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Institutional guard: tests on renderer file changes")
    parser.add_argument("--ci", action="store_true", help="Only consider staged files (pre-commit)")
    parser.add_argument("--force", action="store_true", help="Always run tests regardless of diff")
    parser.add_argument(
        "--check-tier-a-cli",
        action="store_true",
        help="Verify Tier A cli.py has no fork-only cost/tps hooks",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    if args.check_tier_a_cli:
        return _verify_tier_a_cli_no_fork_hooks(repo)

    if args.force:
        print("[INFO] --force: institutional guard tests draaien")
        tier = _verify_tier_a_cli_no_fork_hooks(repo)
        if tier != 0:
            return tier
        return _run_guard_tests(repo)

    changed = _changed_paths(staged_only=args.ci)
    hits = _touches_guard(changed)
    if not hits:
        print("[OK] Geen institutionele renderer-wijzigingen — guard overgeslagen")
        return 0

    print("[INFO] Institutionele bestanden gewijzigd:")
    for h in hits:
        print(f"  - {h}")
    return _run_guard_tests(repo)


if __name__ == "__main__":
    sys.exit(main())
