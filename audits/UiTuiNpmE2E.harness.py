#!/usr/bin/env python3
"""E2E: HermesUiTuiNpm workspace vitest/npm helpers (wiring + live readiness).

Scenario's:
  - W1–W6: module wiring, workspace detectie, CI-volgorde, E2E-integratie
  - W7: live Test-HermesVitestPackageReady op echte repo (skip zonder vitest)
  - W8: live Invoke-HermesUiTuiVitest deps-only (geen test-run) exit 0/2

Draai: audits/RUN_UI_TUI_NPM_E2E.bat
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

UI_NPM_PS1 = REPO / "windows" / "HermesUiTuiNpm.ps1"
SHELL_COMMON = REPO / "windows" / "HermesShellCommon.ps1"
CLEAN_PS1 = REPO / "windows" / "scripts" / "clean_audit_reports.ps1"
CI_YML = REPO / ".github" / "workflows" / "fork-windows-institutional.yml"
NOUS_OVERLAY_CORE = REPO / "audits" / "NousOverlayInstitutionalE2E.core.ps1"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] W{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] W{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _powershell(script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_w1_module_wiring() -> None:
    text = _read("windows/HermesUiTuiNpm.ps1")
    common = _read("windows/HermesShellCommon.ps1")
    ok = (
        UI_NPM_PS1.is_file()
        and "function Test-HermesVitestPackageReady" in text
        and "function Test-HermesNpmWorkspaceRoot" in text
        and "function Invoke-HermesUiTuiNpmEnsure" in text
        and "function Invoke-HermesUiTuiVitest" in text
        and "HermesUiTuiNpm.ps1" in common
        and "$vitestArgs" in text
        and "$args = @('vitest'" not in text
    )
    _step("HermesUiTuiNpm.ps1 wiring + ShellCommon dot-source", ok)


def test_w2_workspace_vitest_paths() -> None:
    text = _read("windows/HermesUiTuiNpm.ps1")
    ok = (
        "node_modules/vitest/package.json" in text
        and "ui-tui" in text
        and "Test-HermesNpmWorkspaceRoot" in text
        and "npm ci" in text
    )
    _step("workspace vitest path + npm ci", ok)


def test_w3_return_codes_documented() -> None:
    text = _read("windows/HermesUiTuiNpm.ps1")
    lower = text.lower()
    ok = (
        "return 0" in text
        and "return 1" in text
        and "return 2" in text
        and ("niet op path" in lower or "overgeslagen" in lower)
    )
    _step("exit codes 0/1/2 + skip zonder npm", ok)


def test_w4_nous_overlay_integration() -> None:
    text = _read("audits/NousOverlayInstitutionalE2E.core.ps1")
    ok = "Invoke-HermesUiTuiVitest" in text and "CopyOverlay" in text
    _step("NousOverlayInstitutionalE2E uses Invoke-HermesUiTuiVitest", ok)


def test_w5_ci_npm_after_drift() -> None:
    yml = _read(".github/workflows/fork-windows-institutional.yml")
    drift_idx = yml.find("Nous Tier A drift gate")
    npm_idx = yml.find("npm ci workspace")
    node_idx = yml.find("Set up Node.js")
    ok = drift_idx >= 0 and npm_idx > drift_idx and node_idx > drift_idx
    _step("CI: drift gate vóór npm ci workspace", ok)


def test_w6_clean_audit_reports() -> None:
    text = _read("windows/scripts/clean_audit_reports.ps1")
    ok = (
        CLEAN_PS1.is_file()
        and "check-ignore" in text
        and "git niet op PATH" in text
        and "WhatIf" in text
    )
    _step("clean_audit_reports.ps1 safe gitignore cleanup", ok)


def test_w7_live_vitest_ready() -> None:
    repo = str(REPO).replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
. '{REPO / "windows" / "HermesShellCommon.ps1"}'
$ready = Test-HermesVitestPackageReady -RepoRoot '{repo}'
if ($ready) {{ exit 0 }}
$ws = Test-HermesNpmWorkspaceRoot -RepoRoot '{repo}'
if (-not $ws) {{ exit 3 }}
exit 2
"""
    proc = _powershell(ps, timeout=60)
    if proc.returncode == 0:
        _step("live Test-HermesVitestPackageReady", True, "vitest aanwezig")
    elif proc.returncode == 2:
        _step("live Test-HermesVitestPackageReady", True, "SKIP geen vitest (npm/deps)")
    else:
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        _step("live Test-HermesVitestPackageReady", False, detail or f"exit {proc.returncode}")


def test_w8_live_deps_only_no_tests() -> None:
    repo = str(REPO).replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
. '{REPO / "windows" / "HermesShellCommon.ps1"}'
$rc = Invoke-HermesUiTuiVitest -RepoRoot '{repo}' -Quiet -TestPaths @()
exit $rc
"""
    proc = _powershell(ps, timeout=180)
    ok = proc.returncode in (0, 2)
    detail = "deps OK" if proc.returncode == 0 else "SKIP geen npm/vitest"
    if not ok:
        detail = (proc.stderr or proc.stdout or "").strip()[:200] or f"exit {proc.returncode}"
    _step("live Invoke-HermesUiTuiVitest deps-only (empty TestPaths)", ok, detail)


def test_w9_root_package_workspaces() -> None:
    pkg = REPO / "package.json"
    ok = False
    if pkg.is_file():
        data = json.loads(pkg.read_text(encoding="utf-8"))
        workspaces = data.get("workspaces") or []
        ok = "ui-tui" in workspaces
    _step("root package.json workspaces bevat ui-tui", ok)


def main() -> int:
    print("=== UI/TUI NPM E2E harness ===", flush=True)
    test_w1_module_wiring()
    test_w2_workspace_vitest_paths()
    test_w3_return_codes_documented()
    test_w4_nous_overlay_integration()
    test_w5_ci_npm_after_drift()
    test_w6_clean_audit_reports()
    test_w7_live_vitest_ready()
    test_w8_live_deps_only_no_tests()
    test_w9_root_package_workspaces()
    status = "PASS" if FAILURES == 0 else f"FAIL ({FAILURES})"
    print(f"\n=== UI TUI NPM E2E: {status} ===", flush=True)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
