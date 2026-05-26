#!/usr/bin/env python3
"""E2E wiring: UPDATE_HERMES -QuickFix, guard log, health_check, upstream preflight."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] U{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] U{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    update_bat = _read("windows/UPDATE_HERMES.bat")
    _step("UPDATE_HERMES.bat roept upstream_sync aan", "upstream_sync.ps1" in update_bat)
    _step("UPDATE_HERMES.bat heeft -QuickFix", "-QuickFix" in update_bat)
    _step("quick_fix_repo_hygiene.ps1 bestaat", (REPO / "windows/scripts/quick_fix_repo_hygiene.ps1").is_file())
    _step("health_check_repo.ps1 bestaat", (REPO / "windows/scripts/health_check_repo.ps1").is_file())

    sync = _read("windows/upstream_sync.ps1")
    _step("upstream_sync logt guard", "Write-RepoHygieneGuardLog" in sync)
    _step("upstream_sync QuickFix hint", "QuickFix" in sync)

    gi = _read("windows/.gitignore")
    _step("guard log gitignored", "_upstream_sync_guard.log" in gi)

    ws = _read("docs/WORKSPACE_CONVENTIONS.md")
    _step("WORKSPACE_CONVENTIONS output/research", "output/research/scripts" in ws)

    proc = subprocess.run(
        [
            "powershell", "-NoProfile",
            "-File", str(REPO / "windows/scripts/health_check_repo.ps1"),
            "-RepoRoot", str(REPO),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    _step("health_check_repo exit 0 op schone repo", proc.returncode == 0, f"exit={proc.returncode}")

  # QuickFix dry: geen untracked rommel, moet exit 0
    qf = subprocess.run(
        [
            "powershell", "-NoProfile",
            "-File", str(REPO / "windows/scripts/quick_fix_repo_hygiene.ps1"),
            "-RepoRoot", str(REPO),
            "-NonInteractive",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    _step("quick_fix op schone repo exit 0", qf.returncode == 0, f"exit={qf.returncode}")

    if FAILURES:
        print(f"\n{FAILURES} failure(s)", file=sys.stderr)
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
