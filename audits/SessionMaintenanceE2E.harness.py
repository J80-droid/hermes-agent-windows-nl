#!/usr/bin/env python3
"""E2E: sessie-onderhoud (stamps, start maintenance, post-pull tail, orchestrator wiring).

Geen live git pull, geen WT-relaunch, geen volledige RAG-ingest.
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

PS1_PARSE = (
    "windows/scripts/HermesSessionMaintenance.ps1",
    "windows/scripts/launch_pre_chat_orchestrator.ps1",
    "windows/scripts/Invoke-HermesPostPullMaintenance.ps1",
    "windows/HermesShellCommon.ps1",
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] S{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] S{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def _audit_python() -> str:
    if os.environ.get("HERMES_AUDIT_PYTHON") and Path(os.environ["HERMES_AUDIT_PYTHON"]).is_file():
        return os.environ["HERMES_AUDIT_PYTHON"]
    for c in (
        Path(os.environ.get("USERPROFILE", "")) / "miniconda3/envs/hermes-env/python.exe",
        Path(sys.executable),
    ):
        if c.is_file():
            return str(c)
    return sys.executable


def _powershell_file(script: Path, *args: str, env: dict[str, str] | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args]
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=run_env,
    )


def _powershell_command(command: str, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=run_env,
    )


def _parse_ps1(path: Path) -> bool:
    esc = str(path).replace("'", "''")
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                f"$e=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile('{esc}', "
                "[ref]$null, [ref]$e); if ($e) {{ $e | Out-String; exit 1 }} else {{ exit 0 }}"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO),
    )
    return proc.returncode == 0


def test_s1_repo_artifacts() -> None:
    required = [
        "windows/scripts/HermesSessionMaintenance.ps1",
        "windows/scripts/Invoke-HermesPostPullMaintenance.ps1",
        "windows/HermesShellCommon.ps1",
        "windows/scripts/launch_pre_chat_orchestrator.ps1",
        "windows/scripts/launch_hermes.ps1",
        "windows/HermesLaunchUi.ps1",
        "windows/launch_hermes.bat",
        "windows/POST_GIT_PULL.bat",
        "windows/launch_profiles.ps1",
        "windows/scripts/HermesHomeCommon.ps1",
        "tests/windows/test_hermes_session_maintenance.py",
        "windows/tests/HermesSessionMaintenance.Unit.Tests.ps1",
        "audits/SessionMaintenanceE2E.harness.py",
        "audits/RUN_SESSION_MAINTENANCE_E2E.bat",
        "audits/SESSION_MAINTENANCE_E2E_README.md",
    ]
    missing = [r for r in required if not (REPO / r).is_file()]
    _step("repo-artefacten sessie-onderhoud", not missing, ", ".join(missing) or "OK")


def test_s2_stamp_api_contract() -> None:
    common = _read("windows/HermesShellCommon.ps1")
    needles = [
        "function Get-HermesSessionStampPath",
        "function Read-HermesSessionStamp",
        "function Write-HermesSessionStamp",
        "function Get-HermesGitHead",
        "function Get-HermesDomainsYamlFingerprint",
        "function Test-HermesPathNewerThanStamp",
        "function Test-HermesShouldSkipPostPullMaintenanceOnStart",
        "function Clear-HermesUpdateCheckCache",
        "function Test-HermesGitDirtyOnlyBranding",
        "git -C $RepoRoot",
    ]
    _step("HermesShellCommon stamp-API", all(n in common for n in needles))


def test_s3_post_git_pull_wiring() -> None:
    bat = _read("windows/POST_GIT_PULL.bat")
    maint = _read("windows/scripts/HermesSessionMaintenance.ps1")
    order_verify = bat.find("ConditionalWindowsChainVerify")
    order_trust = bat.find("SYNC_TRUST_RUNTIME.bat")
    checks = [
        "Invoke-HermesPostPullMaintenance.ps1" in bat,
        "PostPullTail" in bat,
        "POST_PULL_ERR" in bat,
        order_verify >= 0 and order_trust >= 0 and order_verify < order_trust,
        "Invoke-HermesPostPullMaintenance" in maint,
        "Write-HermesSessionStamp -Name 'post_pull_maintenance'" in maint,
        "Test-HermesDomainsFingerprintChanged" in maint,
    ]
    _step("POST_GIT_PULL volgorde + PostPullTail", all(checks))


def test_s4_orchestrator_wiring() -> None:
    launch = _read("windows/launch_hermes.bat")
    launch_ps1 = _read("windows/scripts/launch_hermes.ps1")
    orch = _read("windows/scripts/launch_pre_chat_orchestrator.ps1")
    checks = [
        "launch_hermes.ps1" in launch,
        "launch_pre_chat_orchestrator.ps1" in launch_ps1,
        "-SkipBootstrap" not in launch,
        "HERMES_LAUNCH_LOG" in launch,
        ":launch_chat" in launch,
        "HermesSessionMaintenance.ps1" in orch,
        "HERMES_REPO_ROOT" in launch,
        "launch_bootstrap.ps1" in orch,
        ". $maintenancePath -RepoRoot $RepoRoot -AllowFailure" in orch,
        "Invoke-HermesStartMaintenance" in orch,
        "SkipConfigDrift = $true" in orch,
    ]
    _step("launch_hermes orchestrator + AllowFailure", all(checks))


def test_s5_start_hermes_sync_cache() -> None:
    bat = _read("start_hermes.bat")
    ok = "Clear-HermesUpdateCheckCache" in bat and ":after_sync_no_relaunch" in bat
    _step("start_hermes --sync Clear-HermesUpdateCheckCache", ok)


def test_s6_launch_profiles() -> None:
    prof = _read("windows/launch_profiles.ps1")
    checks = [
        "HERMES_AUTOREPAIR_MODEL_ON_DRIFT" in prof,
        "HERMES_AUTOREPAIR_MODEL_CATALOG" in prof,
        "HERMES_SKIP_SHORTCUT_MAINT_ON_START     = '1'" in prof,
        "HERMES_SKIP_TUI_MAINT_ON_START" in prof,
    ]
    _step("launch_profiles full/minimal env", all(checks))


def test_s7_powershell_parse() -> None:
    bad = [rel for rel in PS1_PARSE if not _parse_ps1(REPO / rel)]
    _step("PowerShell parse maintenance-keten", not bad, ", ".join(bad) or "OK")


def test_s8_stamp_roundtrip_isolated() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        la = str(Path(tmp) / "LocalAppData")
        repo_esc = str(REPO).replace("'", "''")
        cmd = f"""
$ErrorActionPreference = 'Stop'
$env:LOCALAPPDATA = '{la.replace("'", "''")}'
. '{repo_esc}\\windows\\HermesShellCommon.ps1'
Write-HermesSessionStamp -Name 'e2e_roundtrip' -Data @{{ tag = 'e2e' }} -RepoRoot '{repo_esc}'
$r = Read-HermesSessionStamp -Name 'e2e_roundtrip'
if (-not $r -or $r.tag -ne 'e2e') {{ throw 'stamp read mismatch' }}
$watch = Join-Path $env:TEMP 'hermes_e2e_watch.txt'
Set-Content -LiteralPath $watch -Value 'v1'
Write-HermesSessionStamp -Name 'e2e_watch' -Data @{{}}
Start-Sleep -Milliseconds 30
if (Test-HermesPathNewerThanStamp -WatchPaths @($watch) -StampName 'e2e_watch') {{ throw 'should not be newer yet' }}
Set-Content -LiteralPath $watch -Value 'v2'
if (-not (Test-HermesPathNewerThanStamp -WatchPaths @($watch) -StampName 'e2e_watch')) {{ throw 'should be newer' }}
exit 0
"""
        proc = _powershell_command(cmd, timeout=90)
        out = (proc.stdout or "") + (proc.stderr or "")
        _step("stamp round-trip + path-newer (isolated)", proc.returncode == 0, out.strip()[:200] or f"exit={proc.returncode}")


def test_s9_skip_post_pull_on_start() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        la = str(Path(tmp) / "LocalAppData")
        repo_esc = str(REPO).replace("'", "''")
        cmd = f"""
$ErrorActionPreference = 'Stop'
$env:LOCALAPPDATA = '{la.replace("'", "''")}'
. '{repo_esc}\\windows\\HermesShellCommon.ps1'
$head = Get-HermesGitHead -RepoRoot '{repo_esc}'
if (-not $head) {{ exit 2 }}
Write-HermesSessionStamp -Name 'post_pull_maintenance' -Data @{{}} -RepoRoot '{repo_esc}'
if (-not (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot '{repo_esc}')) {{ throw 'expected skip true' }}
exit 0
"""
        proc = _powershell_command(cmd, timeout=60)
        ok = proc.returncode == 0
        if proc.returncode == 2:
            ok = True
            detail = "SKIP geen git head"
        else:
            detail = (proc.stderr or proc.stdout or "")[:200] or f"exit={proc.returncode}"
        _step("Test-HermesShouldSkipPostPullMaintenanceOnStart", ok, detail)


def test_s10_domains_fingerprint_helper() -> None:
    repo_esc = str(REPO).replace("'", "''")
    cmd = f"""
$ErrorActionPreference = 'Stop'
. '{repo_esc}\\windows\\scripts\\HermesSessionMaintenance.ps1' -RepoRoot '{repo_esc}'
if (-not (Test-HermesDomainsFingerprintChanged -Stamp $null -CurrentFp $null)) {{ throw 'null fp' }}
if (-not (Test-HermesDomainsFingerprintChanged -Stamp $null -CurrentFp 'abc')) {{ throw 'new fp' }}
$stamp = [pscustomobject]@{{ domainsHash = 'abc' }}
if (Test-HermesDomainsFingerprintChanged -Stamp $stamp -CurrentFp 'abc') {{ throw 'same fp' }}
if (-not (Test-HermesDomainsFingerprintChanged -Stamp $stamp -CurrentFp 'def')) {{ throw 'changed fp' }}
exit 0
"""
    proc = _powershell_command(cmd, timeout=90)
    out = (proc.stdout or "") + (proc.stderr or "")
    _step("Test-HermesDomainsFingerprintChanged", proc.returncode == 0, out.strip()[:200] or f"exit={proc.returncode}")


def test_s11_post_pull_tail_skips() -> None:
    maint = REPO / "windows/scripts/HermesSessionMaintenance.ps1"
    env = {
        "HERMES_SKIP_DOMAIN_TOOLSETS_ON_POST_PULL": "1",
        "HERMES_SKIP_LANCEDB_INIT_ON_POST_PULL": "1",
        "HERMES_RAG_ON_POST_PULL": "0",
        "HERMES_INCLUDE_RAG_PIPELINE": "0",
    }
    proc = _powershell_file(
        maint,
        "-Phase",
        "PostPullTail",
        "-RepoRoot",
        str(REPO),
        "-Quiet",
        env=env,
        timeout=600,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    _step("PostPullTail met domain/lance/rag skips", proc.returncode == 0, out.strip()[:240] or f"exit={proc.returncode}")


def test_s12_start_maintenance_minimal() -> None:
    maint = REPO / "windows/scripts/HermesSessionMaintenance.ps1"
    proc = _powershell_file(
        maint,
        "-Phase",
        "StartMaintenance",
        "-RepoRoot",
        str(REPO),
        "-Quiet",
        env={"HERMES_MINIMAL_LAUNCH": "1"},
        timeout=120,
    )
    _step("StartMaintenance HERMES_MINIMAL_LAUNCH", proc.returncode == 0, f"exit={proc.returncode}")


def test_s13_pytest_subset() -> None:
    py = _audit_python()
    proc = subprocess.run(
        [py, "-m", "pytest", "tests/windows/test_hermes_session_maintenance.py", "-q", "--tb=line"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    _step("pytest test_hermes_session_maintenance", proc.returncode == 0, f"exit={proc.returncode}")


def test_s14_pester_unit() -> None:
    unit = REPO / "windows/tests/HermesSessionMaintenance.Unit.Tests.ps1"
    proc = _powershell_file(unit, timeout=120)
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "passed" in out.lower()
    _step("Pester HermesSessionMaintenance.Unit.Tests", ok, out.strip()[:200] or f"exit={proc.returncode}")


def main() -> int:
    print("=== Sessie-onderhoud (stamps) E2E ===", flush=True)
    test_s1_repo_artifacts()
    test_s2_stamp_api_contract()
    test_s3_post_git_pull_wiring()
    test_s4_orchestrator_wiring()
    test_s5_start_hermes_sync_cache()
    test_s6_launch_profiles()
    test_s7_powershell_parse()
    test_s8_stamp_roundtrip_isolated()
    test_s9_skip_post_pull_on_start()
    test_s10_domains_fingerprint_helper()
    test_s11_post_pull_tail_skips()
    test_s12_start_maintenance_minimal()
    test_s13_pytest_subset()
    test_s14_pester_unit()

    if FAILURES:
        print(f"\n{FAILURES} failure(s)", file=sys.stderr, flush=True)
        return 1
    print("\nALL PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
