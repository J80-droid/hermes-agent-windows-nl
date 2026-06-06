#!/usr/bin/env python3
"""E2E: Tier A post-audit clean (restore + git clean + drift gate)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] {name}{suffix}")
    else:
        print(f"[FAIL] {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def main() -> int:
    print("=" * 60)
    print("  Tier A Working Tree E2E")
    print("=" * 60)

    marker = REPO / "ui-tui" / "src" / "_tier_a_e2e_marker.tmp"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("tier-a-leak", encoding="utf-8")

    ps = (
        f"Set-Location '{REPO}'; "
        ". .\\windows\\HermesShellCommon.ps1; "
        "Invoke-HermesTierAPostAuditClean -RepoRoot . -Phase Postflight; "
        "exit $LASTEXITCODE"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(REPO),
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and not marker.exists() and "Tier A identical" in combined
    _step("Invoke-HermesTierAPostAuditClean Postflight", ok, f"exit={proc.returncode}")

    # Drift gate standalone
    drift = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "windows/scripts/Test-NousTreeIdentical.ps1"),
            "-RepoRoot",
            str(REPO),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
    )
    _step("Test-NousTreeIdentical strict", drift.returncode == 0, f"exit={drift.returncode}")

    print()
    if FAILURES:
        print(f"FAILURES: {FAILURES}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
