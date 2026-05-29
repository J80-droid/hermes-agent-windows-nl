#!/usr/bin/env python3
"""E2E: dashboard start-optimalisaties (pip-manifest, pygount-cache repair, test-isolatie).

Scenario's:
  - Wiring launch_dashboard_on_start.ps1 + HermesPythonPolicy functies
  - FIX_CODEBASE_VIZ_CACHE.bat + Repair-CodebaseVizPygountCache.ps1
  - Pygount mismatch-detectie (pytest-pad)
  - Web-dashboard-deps manifest fast-path (structuur + PowerShell smoke)
  - pytest plugins/conftest productie-cache guard

Draai: audits/RUN_DASHBOARD_LAUNCH_OPTIMIZATIONS_E2E.bat
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

POLICY_PS1 = REPO / "windows" / "HermesPythonPolicy.ps1"
LAUNCH_PS1 = REPO / "windows" / "scripts" / "launch_dashboard_on_start.ps1"
REPAIR_PS1 = REPO / "windows" / "scripts" / "Repair-CodebaseVizPygountCache.ps1"
FIX_BAT = REPO / "windows" / "FIX_CODEBASE_VIZ_CACHE.bat"
PLUGIN_CONFTEST = REPO / "tests" / "plugins" / "conftest.py"
UNIT_PS1 = REPO / "windows" / "tests" / "HermesWebDashboardLaunch.Unit.Tests.ps1"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] W{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] W{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _powershell(cmd: str, *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_w1_policy_and_launch_wiring() -> None:
    policy = POLICY_PS1.read_text(encoding="utf-8")
    launch = LAUNCH_PS1.read_text(encoding="utf-8")
    checks = [
        "Get-HermesWebDashboardDepsManifestPath" in policy,
        "Test-HermesNeedsWebDashboardPipInstall" in policy,
        "Test-HermesCodebaseVizPygountCacheMismatch" in policy,
        "Repair-HermesCodebaseVizPygountCache" in policy,
        "web-dashboard-deps.json" in policy,
        "Test-HermesNeedsWebDashboardPipInstall" in launch,
        "canSkipRestart" in launch or "Dashboard al actief" in launch,
        "Test-HermesCodebaseVizPygountCacheMismatch" in launch,
        "Dashboard-deps up-to-date" in launch,
    ]
    _step("policy + launch PS1 wiring", all(checks), f"{sum(checks)}/{len(checks)}")


def test_w2_fix_bat_and_repair_script() -> None:
    bat = FIX_BAT.read_text(encoding="utf-8") if FIX_BAT.is_file() else ""
    ok = (
        FIX_BAT.is_file()
        and REPAIR_PS1.is_file()
        and "Repair-CodebaseVizPygountCache.ps1" in bat
        and "Repair-HermesCodebaseVizPygountCache" in REPAIR_PS1.read_text(encoding="utf-8")
    )
    _step("FIX_CODEBASE_VIZ_CACHE + repair script", ok)


def test_w3_pygount_mismatch_detects_pytest_path() -> None:
    policy = str(POLICY_PS1).replace("'", "''")
    repo = str(REPO).replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
. '{policy}'
$td = New-TemporaryFile | ForEach-Object {{ Remove-Item $_; New-Item -ItemType Directory -Path ($_.FullName + '_m') }}
$repo = (Resolve-Path '{repo}').Path
$cache = Join-Path $td.FullName 'cache.json'
@{{ version = 1; repo_path = 'C:\Temp\pytest-of-user\test_0'; repo_revision = 'x'; bundle = @{{ file_rows = @(@{{}}) }} }} |
  ConvertTo-Json | Set-Content -LiteralPath $cache -Encoding UTF8
$m = Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $repo -CachePath $cache
if ($m) {{ exit 0 }} else {{ exit 1 }}
"""
    proc = _powershell(ps)
    _step("pygount mismatch pytest path", proc.returncode == 0, (proc.stderr or proc.stdout or "")[:160])


def test_w4_web_deps_manifest_fast_path() -> None:
    policy = str(POLICY_PS1).replace("'", "''")
    repo = str(REPO).replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
. '{policy}'
$repo = (Resolve-Path '{repo}').Path
$tempLocal = Join-Path $env:TEMP ('hermes_web_e2e_' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $tempLocal -Force | Out-Null
$prevLocal = $env:LOCALAPPDATA
$env:LOCALAPPDATA = $tempLocal
try {{
  $manifest = Get-HermesWebDashboardDepsManifestPath
  New-Item -ItemType Directory -Path (Split-Path -Parent $manifest) -Force | Out-Null
  Remove-Item Function:Resolve-HermesPythonExe -ErrorAction SilentlyContinue
  Remove-Item Function:Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue
  function Resolve-HermesPythonExe {{ param([string]$RepoRoot, [switch]$RequirePip) return 'C:\\fake\\python.exe' }}
  function Test-HermesWebDashboardExtrasInstalled {{ param([string]$PythonExe, [switch]$RequirePygount) return $true }}
  @{{ installed_at = (Get-Date).ToUniversalTime().ToString('o'); python_exe = 'C:\\fake\\python.exe'; deps_fingerprint = (Get-HermesWebDashboardDepsFingerprint -RepoRoot $repo); web_deps_verified = $true; require_pygount = $false }} |
    ConvertTo-Json | Set-Content -LiteralPath $manifest -Encoding UTF8
  $need = Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repo
  if (-not $need) {{ exit 0 }} else {{ exit 1 }}
}} finally {{
  Remove-Item Function:Resolve-HermesPythonExe -ErrorAction SilentlyContinue
  Remove-Item Function:Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue
  if ($null -eq $prevLocal) {{ Remove-Item Env:LOCALAPPDATA -ErrorAction SilentlyContinue }} else {{ $env:LOCALAPPDATA = $prevLocal }}
  Remove-Item -LiteralPath $tempLocal -Recurse -Force -ErrorAction SilentlyContinue
}}
"""
    proc = _powershell(ps)
    _step("web-deps manifest fast-path (mocked)", proc.returncode == 0, (proc.stderr or "")[:120])


def test_w5_force_dashboard_pip_env() -> None:
    policy = str(POLICY_PS1).replace("'", "''")
    repo = str(REPO).replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
. '{policy}'
$env:HERMES_FORCE_DASHBOARD_PIP = '1'
$repo = (Resolve-Path '{repo}').Path
if (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repo) {{ exit 0 }} else {{ exit 1 }}
"""
    proc = _powershell(ps)
    _step("HERMES_FORCE_DASHBOARD_PIP=1", proc.returncode == 0)


def test_w6_plugins_conftest_isolation() -> None:
    text = PLUGIN_CONFTEST.read_text(encoding="utf-8")
    ok = (
        PLUGIN_CONFTEST.is_file()
        and "PRODUCTION_PYGOUNT_CACHE" in text
        and "CODEBASE_VIZ_PYGOUNT_CACHE_PATH" in text
        and "apply_isolated_pygount_cache_to_module" in text
        and "prod_snapshot" in text
    )
    _step("plugins/conftest production cache guard", ok)


def test_w7_unit_tests_ps1_gate() -> None:
    if not UNIT_PS1.is_file():
        _step("HermesWebDashboardLaunch unit gate", False, "unit file ontbreekt")
        return
    proc = _powershell(f"& '{UNIT_PS1}'", timeout=90)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("HermesWebDashboardLaunch.Unit.Tests.ps1", proc.returncode == 0, detail)


def test_w8_pytest_cache_isolation_gate() -> None:
    py = Path.home() / "miniconda3/envs/hermes-env/python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    proc = subprocess.run(
        [str(py), "-m", "pytest", "tests/plugins/test_codebase_viz_cache_isolation.py", "-q", "--tb=line"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("pytest cache isolation", proc.returncode == 0, detail)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Dashboard launch optimizations E2E", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_w1_policy_and_launch_wiring()
    test_w2_fix_bat_and_repair_script()
    test_w3_pygount_mismatch_detects_pytest_path()
    test_w4_web_deps_manifest_fast_path()
    test_w5_force_dashboard_pip_env()
    test_w6_plugins_conftest_isolation()
    test_w7_unit_tests_ps1_gate()
    test_w8_pytest_cache_isolation_gate()

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
