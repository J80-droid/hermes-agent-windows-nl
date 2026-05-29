#!/usr/bin/env python3
"""E2E: Launch UI Sink (overlap-fix, capture contract, wiring, allowlist).

Geen live Windows Terminal, geen chat, geen zware bootstrap/RAG.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

LAUNCH_ALLOWLIST = [
    "windows/scripts/launch_hermes.ps1",
    "windows/scripts/launch_pre_chat_orchestrator.ps1",
    "windows/scripts/launch_bootstrap.ps1",
    "windows/scripts/launch_soul_anatomy_deploy.ps1",
    "windows/scripts/launch_trust_runtime_sync.ps1",
    "windows/scripts/launch_institutional_runtime.ps1",
    "windows/scripts/launch_pending_trust_runtime.ps1",
    "windows/scripts/launch_dashboard_on_start.ps1",
    "windows/scripts/HermesSessionMaintenance.ps1",
    "windows/apply_institutional_runtime.ps1",
    "windows/scripts/Invoke-TrustRuntimeLight.ps1",
    "windows/scripts/sync_all_domain_souls_from_templates.ps1",
    "windows/scripts/install_rag_extras.ps1",
]


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] L{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] L{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


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


def test_l1_repo_artifacts() -> None:
    required = [
        "windows/HermesLaunchUi.ps1",
        "windows/scripts/launch_hermes.ps1",
        "windows/scripts/launch_pre_chat_orchestrator.ps1",
        "windows/launch_hermes.bat",
        "windows/HermesShellCommon.ps1",
        "audits/LaunchUiSinkE2E.harness.py",
        "audits/RUN_LAUNCH_UI_SINK_E2E.bat",
    ]
    missing = [r for r in required if not (REPO / r).is_file()]
    _step("repo-artefacten Launch UI Sink", not missing, ", ".join(missing) or "OK")


def test_l2_shell_common_contract() -> None:
    common = _read("windows/HermesShellCommon.ps1")
    launch_ui = _read("windows/HermesLaunchUi.ps1")
    checks = [
        "HermesLaunchUi.ps1" in common,
        "Write-HermesLaunchUi" in launch_ui,
        "Write-HermesLaunchConsoleLine" in launch_ui,
        "Test-HermesConsoleCapability" in launch_ui,
        "Invoke-HermesLaunchPhase" in common,
        "Test-HermesLaunchConsoleCapture" in common,
    ]
    _step("HermesShellCommon + LaunchUi contract", all(checks))


def test_l3_bat_ps1_orchestrator_wiring() -> None:
    bat = _read("windows/launch_hermes.bat")
    ps1 = _read("windows/scripts/launch_hermes.ps1")
    orch = _read("windows/scripts/launch_pre_chat_orchestrator.ps1")
    checks = [
        "launch_hermes.ps1" in bat,
        "launch_pre_chat_orchestrator.ps1" in ps1,
        "-SkipBootstrap" not in bat,
        "launch_bootstrap.ps1" not in bat,
        "launch_bootstrap.ps1" in orch,
        "Pre-chat orchestrator start" in orch or "Add-HermesLaunchLogLine" in orch,
    ]
    _step("bat -> ps1 -> orchestrator -> bootstrap", all(checks))


def test_l4_overlap_el_clear() -> None:
    repo_esc = str(REPO).replace("'", "''")
    cmd = (
        f". '{repo_esc}/windows/HermesShellCommon.ps1'; "
        "$pad = '=' * 52; "
        "[Console]::Out.WriteLine($pad); "
        "Write-HermesLaunchConsoleLine -Message 'OK short line' -ForegroundColor Green"
    )
    proc = _powershell_command(cmd, timeout=60)
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    ok = proc.returncode == 0 and bool(lines)
    if ok:
        last = lines[-1]
        ok = "OK short line" in last and not last.rstrip().endswith("=" * 10)
        ok = ok and last.count("=") < 20
    detail = f"exit={proc.returncode}"
    if not ok and lines:
        detail += f" last={lines[-1][:80]!r}"
    _step("EL [2K] overlap-simulatie", ok, detail)


def test_l5_orchestrator_quiet_capture() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as fh:
        log_path = fh.name
    try:
        env = {
            "HERMES_LAUNCH_UI": "quiet",
            "HERMES_SKIP_DOCKER_ON_START": "1",
            "HERMES_SKIP_SOUL_DEPLOY_ON_START": "1",
            "HERMES_SKIP_TRUST_RUNTIME_ON_START": "1",
            "HERMES_SKIP_INSTITUTIONAL_RUNTIME": "1",
            "HERMES_SKIP_PENDING_TRUST_ON_START": "1",
            "HERMES_SKIP_DASHBOARD_ON_START": "1",
            "HERMES_DASHBOARD_ON_START": "0",
            "HERMES_LAUNCH_LOG": log_path,
        }
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1"),
                "-RepoRoot",
                str(REPO),
                "-SkipBootstrap",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            env={**os.environ, **env},
        )
        log_text = Path(log_path).read_text(encoding="utf-8", errors="replace") if Path(log_path).is_file() else ""
        ok = proc.returncode == 0 and "Pre-chat orchestrator start" in log_text
        _step("orchestrator quiet + log contract", ok, f"exit={proc.returncode}")
    finally:
        Path(log_path).unlink(missing_ok=True)


def test_l6_launch_allowlist_no_write_host() -> None:
    bad: list[str] = []
    for rel in LAUNCH_ALLOWLIST:
        text = _read(rel)
        if "Write-Host" in text or "-NoNewline" in text:
            bad.append(rel)
    _step("launch-pad geen Write-Host/-NoNewline", not bad, ", ".join(bad) or "OK")


def test_l7_visual_disable_env() -> None:
    repo_esc = str(REPO).replace("'", "''")
    cmd = (
        f". '{repo_esc}/windows/HermesShellCommon.ps1'; "
        "$env:HERMES_LAUNCH_VISUAL='0'; "
        "if (Test-HermesLaunchVisualEnabled) { exit 2 } else { exit 0 }"
    )
    proc = _powershell_command(cmd, timeout=60)
    _step("HERMES_LAUNCH_VISUAL=0", proc.returncode == 0, f"exit={proc.returncode}")


def test_l8_unit_tests_gate() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "windows/tests/HermesShellCommon.Unit.Tests.ps1"),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    ok = proc.returncode == 0 and "PASS" in (proc.stdout or "")
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("HermesShellCommon unit gate", ok, detail)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Launch UI Sink E2E - Audit", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_l1_repo_artifacts()
    test_l2_shell_common_contract()
    test_l3_bat_ps1_orchestrator_wiring()
    test_l4_overlap_el_clear()
    test_l5_orchestrator_quiet_capture()
    test_l6_launch_allowlist_no_write_host()
    test_l7_visual_disable_env()
    test_l8_unit_tests_gate()

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
