#!/usr/bin/env python3
"""E2E: dashboard bij launch (hermes dashboard --no-open, geen browser-tab).

Geen live netwerk buiten loopback. Draai: audits/RUN_DASHBOARD_ON_START_E2E.bat
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PS1 = REPO / "windows/scripts/launch_dashboard_on_start.ps1"
BAT = REPO / "windows/launch_hermes.bat"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] D{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] D{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def test_d1_repo_artefacts() -> None:
    ok = PS1.is_file() and BAT.is_file()
    _step("repo-artefacten", ok, "launch_dashboard_on_start.ps1 + launch_hermes.bat")


def test_d2_launch_hermes_wiring() -> None:
    bat = _read("windows/launch_hermes.bat")
    orch = _read("windows/scripts/launch_pre_chat_orchestrator.ps1")
    dash_ps1 = _read("windows/scripts/launch_dashboard_on_start.ps1")
    checks = [
        "launch_pre_chat_orchestrator.ps1" in bat,
        "launch_dashboard_on_start.ps1" in orch or "launch_dashboard_on_start.ps1" in dash_ps1,
        "HERMES_SKIP_DASHBOARD_ON_START" in orch or "HERMES_SKIP_DASHBOARD_ON_START" in dash_ps1,
        "HERMES_LAUNCH_LOG" in bat,
    ]
    ok = all(checks)
    _step("launch_hermes.bat wiring", ok, f"{sum(checks)}/{len(checks)}")


def test_d3_ps1_contract() -> None:
    ps1 = PS1.read_text(encoding="utf-8")
    checks = [
        "--no-open" in ps1,
        "HERMES_SKIP_DASHBOARD_ON_START" in ps1,
        "Test-DashboardPortInUse" in ps1,
        "HERMES_LAUNCH_LOG" in ps1,
        "dashboard --status" in ps1,
        "65535" in ps1,
    ]
    ok = all(checks)
    _step("PS1 contract (--no-open, skip, port check)", ok, f"{sum(checks)}/6")


def test_d4_docs_mention() -> None:
    ops = _read("docs/INSTITUTIONAL_OPERATIONS.md")
    win = _read("windows/README.md")
    ok = (
        "HERMES_SKIP_DASHBOARD_ON_START" in ops
        and "9119" in ops
        and "Codebase Viz" in ops
        and "verify_codebase_viz_health" in ops
        and "launch_hermes.bat" in win
        and ("dashboard --no-open" in win or "9119" in win)
    )
    _step("documentatie cheat sheet", ok)


def test_d5_skip_env_exits_zero() -> None:
    env = {**os.environ, "HERMES_SKIP_DASHBOARD_ON_START": "1"}
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            "-RepoRoot",
            str(REPO),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    ok = proc.returncode == 0 and "overgeslagen" in (proc.stdout or "").lower()
    _step("HERMES_SKIP_DASHBOARD_ON_START=1", ok, f"exit={proc.returncode}")


def test_d6_invalid_port_fallback() -> None:
    ps1 = PS1.read_text(encoding="utf-8")
    ok = "HERMES_DASHBOARD_PORT" in ps1 and "65535" in ps1
    _step("ongeldige poort fallback in PS1", ok)


def test_d7_pytest_unit_gate() -> None:
    py = Path.home() / "miniconda3/envs/hermes-env/python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    proc = subprocess.run(
        [str(py), "-m", "pytest", "tests/windows/test_launch_dashboard_on_start.py", "-q", "--tb=short"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("pytest unit gate", ok, detail)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Dashboard on start E2E - Audit", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_d1_repo_artefacts()
    test_d2_launch_hermes_wiring()
    test_d3_ps1_contract()
    test_d4_docs_mention()
    test_d5_skip_env_exits_zero()
    test_d6_invalid_port_fallback()
    test_d7_pytest_unit_gate()

    print(flush=True)
    print("=" * 60, flush=True)
    if FAILURES == 0:
        print(f"  ALL PASS ({STEP}/{STEP})", flush=True)
    else:
        print(f"  FAILURES: {FAILURES}/{STEP}", file=sys.stderr, flush=True)
    print("=" * 60, flush=True)
    return 1 if FAILURES > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
