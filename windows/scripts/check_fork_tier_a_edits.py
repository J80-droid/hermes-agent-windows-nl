#!/usr/bin/env python3
"""Warn/block staged edits in tier-A paths outside fork policy.

SSOT: docs/NOUS_OVERLAY_ARCHITECTURE.md · HermesNousTierPaths.ps1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TIER_A_ROOTS = (
    "agent/",
    "gateway/",
    "tools/",
    "hermes_cli/",
    "web/",
    "ui-tui/",
    "tui_gateway/",
    "run_agent.py",
    "cli.py",
    "pyproject.toml",
    "uv.lock",
    "website/",
    "docker/",
)

EXCLUDE_PREFIXES = (
    "scripts/rag_pipeline/",
    "scripts/windows/",
    "overlay/",
    "windows/",
    "memory-bank/",
    "skills/legal/",
    "skills/productivity/landkaart/",
    "plugins/j80-windows-nl/",
    "tests/",
)

FORK_INTENTIONAL = frozenset(
    {
        "hermes_cli/gateway_windows.py",
    }
)


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./")


def _under_tier_a(path: str) -> bool:
    for root in TIER_A_ROOTS:
        if root.endswith("/"):
            if path.startswith(root):
                return True
        elif path == root:
            return True
    return False


def _excluded(path: str) -> bool:
    for pfx in EXCLUDE_PREFIXES:
        if path.startswith(pfx):
            return True
    if path.startswith("scripts/") and not path.startswith("scripts/rag_pipeline/"):
        if path.split("/")[1].startswith(
            (
                "install",
                "run_tests",
                "score_institutional",
                "verify_institutional",
                "diagnose_renderer",
                "deduplicate",
                "emit_codebase",
                "bench_normalize",
                "check-windows",
            )
        ):
            return True
    return False


def _staged_paths(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    return [_norm(p) for p in proc.stdout.splitlines() if p.strip()]


def check_staged(repo: Path) -> list[str]:
    violations: list[str] = []
    for path in _staged_paths(repo):
        if not _under_tier_a(path):
            continue
        if _excluded(path):
            continue
        if path in FORK_INTENTIONAL:
            continue
        violations.append(path)
    return sorted(violations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--warn", action="store_true", help="Print warnings but exit 0")
    args = parser.parse_args()
    if not args.staged:
        parser.error("--staged required")

    repo = _repo_root(args.repo)
    violations = check_staged(repo)
    if not violations:
        return 0

    print(
        "[WARN] Tier-A staged edits buiten overlay/windows — gebruik overlay/*_fork_patch.py:",
        file=sys.stderr,
    )
    for p in violations:
        print(f"  {p}", file=sys.stderr)
    print("  Zie docs/NOUS_OVERLAY_ARCHITECTURE.md", file=sys.stderr)
    return 0 if args.warn else 1


if __name__ == "__main__":
    raise SystemExit(main())
