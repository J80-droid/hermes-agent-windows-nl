"""Unit tests voor windows/scripts/launch_dashboard_on_start.ps1 (structuur + skip-run)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PS1 = REPO / "windows" / "scripts" / "launch_dashboard_on_start.ps1"
BAT = REPO / "windows" / "launch_hermes.bat"


@pytest.fixture(scope="module")
def ps1_text() -> str:
    assert PS1.is_file(), "launch_dashboard_on_start.ps1 ontbreekt"
    return PS1.read_text(encoding="utf-8")


def test_ps1_exists_and_has_no_open(ps1_text: str) -> None:
    assert "--no-open" in ps1_text
    assert "hermes_cli.main" in ps1_text
    assert "'dashboard'" in ps1_text or '"dashboard"' in ps1_text


def test_ps1_imports_python_policy(ps1_text: str) -> None:
    assert "Import-HermesPythonPolicy" in ps1_text


def test_ps1_skip_env_flags(ps1_text: str) -> None:
    assert "HERMES_SKIP_DASHBOARD_ON_START" in ps1_text
    assert "HERMES_DASHBOARD_ON_START" in ps1_text
    assert "HERMES_BUNDLED_PLUGINS" in ps1_text
    assert "HERMES_DASHBOARD_OPEN_PATH" in ps1_text
    assert "HERMES_SKIP_DASHBOARD_BROWSER" in ps1_text
    assert "Initialize-WorkspaceDashboardPlugins" in ps1_text
    assert "Install-HermesWebDashboardPackage" in ps1_text
    assert "Test-HermesNeedsWebDashboardPipInstall" in ps1_text
    assert "Write-HermesWebDashboardDepsManifest" in ps1_text
    assert "Test-HermesCodebaseVizPygountCacheMismatch" in ps1_text
    assert "[web]" in ps1_text
    assert "Stop-HermesDashboardProcess" in ps1_text
    assert "CODEBASE_VIZ_PYGOUNT_TIMEOUT" in ps1_text
    assert "HERMES_DASHBOARD_WINDOW_STYLE" in ps1_text
    assert "Start-HermesNoWindowProcess" in ps1_text
    assert "CreateNoWindow" in ps1_text or "conhost" in ps1_text.lower()
    assert "Get-CondaDashboardRunArgs" in ps1_text
    assert "Get-DashboardPythonExe" in ps1_text
    assert "-e', \"HERMES_BUNDLED_PLUGINS" not in ps1_text
    assert "'240'" in ps1_text or '"240"' in ps1_text
    assert "Test-CodebaseVizHealth" in ps1_text
    assert "pygount" in ps1_text
    assert "verify_codebase_viz_health.py" in ps1_text
    assert "Update-CodebaseVizDistIfNeeded" in ps1_text
    assert "Invoke-CodebaseVizWarmupScan" in ps1_text
    assert "HERMES_CODEBASE_VIZ_WARMUP" in ps1_text


def test_ps1_port_validation(ps1_text: str) -> None:
    assert "HERMES_DASHBOARD_PORT" in ps1_text
    assert "65535" in ps1_text
    assert "Test-DashboardPortInUse" in ps1_text


def test_ps1_launch_log_append(ps1_text: str) -> None:
    assert "HERMES_LAUNCH_LOG" in ps1_text
    assert "Write-LaunchLogAppend" in ps1_text


def test_ps1_no_unicode_em_dash_in_strings(ps1_text: str) -> None:
    """PSES/Windows PowerShell 5.1: em-dash in strings kan parse errors geven."""
    for line in ps1_text.splitlines():
        if line.strip().startswith("#"):
            continue
        if "—" in line or "–" in line:
            pytest.fail(f"Unicode dash in PS1 line: {line[:80]}")


def test_mouse_regression_contracts() -> None:
    """TERMINAL_WINDOWS: geen start /B dashboard; prepare zonder Clear-Host; NoWindow default."""
    chat = (REPO / "windows/hermes_chat.cmd").read_text(encoding="utf-8")
    prepare = (REPO / "windows/run_hermes_prepare.ps1").read_text(encoding="utf-8")
    bat = BAT.read_text(encoding="utf-8")
    launch_ui = (REPO / "windows/HermesLaunchUi.ps1").read_text(encoding="utf-8")
    orch = (REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1").read_text(encoding="utf-8")
    assert "start /B" not in chat.lower()
    assert 'start "" powershell' not in chat.lower()
    prepare = (REPO / "windows/run_hermes_prepare.ps1").read_text(encoding="utf-8")
    assert "Start-HermesDashboardAfterChatDetached" in prepare
    assert "Invoke-HermesRepairConsoleForChat" not in chat
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert "Start-HermesDashboardAfterChatDetached" in common
    assert "Start-HermesNoWindowProcess" in common
    assert "CASCADIA_HOSTING_WINDOW_CLASS" not in common
    assert "Test-HermesWindowsTerminalSession" in common
    assert "RestoreConsoleFromWorkAreaOverlay" in common
    assert "Invoke-HermesFixMouseBlocked" in common
    assert "Clear-Host" not in prepare
    assert "HERMES_DASHBOARD_USE_NOWINDOW=1" in bat
    assert "Write-HermesLaunchPinnedHeader" in launch_ui
    assert "[93m" in launch_ui
    assert "Start-HermesDashboardAfterChatDetached" in prepare
    assert "Invoke-HermesRepairConsoleForChat" not in prepare
    assert "WT_SESSION" in bat
    assert "if (-not $env:WT_SESSION)" in bat


def _invoke_hermes_expand_console_window_body(common_ps1: str) -> str:
    m = re.search(
        r"function Invoke-HermesExpandConsoleWindow\s*\{",
        common_ps1,
        re.IGNORECASE,
    )
    if not m:
        pytest.fail("Invoke-HermesExpandConsoleWindow not found in HermesShellCommon.ps1")
    start = m.start()
    depth = 0
    i = m.end() - 1
    while i < len(common_ps1):
        ch = common_ps1[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return common_ps1[start : i + 1]
        i += 1
    pytest.fail("Unbalanced braces in Invoke-HermesExpandConsoleWindow")


def test_expand_console_to_work_area_guarded_in_wt() -> None:
    """ExpandConsoleToWorkArea only when not in Windows Terminal."""
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    body = _invoke_hermes_expand_console_window_body(common)
    assert "Test-HermesWindowsTerminalSession" in body
    assert "$inWt" in body
    idx_wt = body.find("if (-not $inWt)")
    assert idx_wt >= 0, "if (-not $inWt) guard missing"
    idx_after_wt_block = body.find("$scrollMin = 999")
    assert idx_after_wt_block > idx_wt
    for match in re.finditer(r"ExpandConsoleToWorkArea", body):
        pos = match.start()
        assert idx_wt < pos < idx_after_wt_block, (
            "ExpandConsoleToWorkArea must be inside if (-not $inWt) block"
        )
    assert "ExpandConsoleToWorkArea" not in body[:idx_wt]


def test_cli_align_viewport_skipped_in_wt() -> None:
    """cli.py must not align viewport in Windows Terminal."""
    cli = (REPO / "cli.py").read_text(encoding="utf-8")
    assert "align_win32_viewport_to_bottom" in cli
    assert re.search(
        r"if\s+not\s+os\.environ\.get\(\s*[\"']WT_SESSION[\"']\s*\)\s*:\s*\n\s*align_win32_viewport_to_bottom\(\)",
        cli,
    )


def test_launch_hermes_bat_wires_script() -> None:
    bat = BAT.read_text(encoding="utf-8")
    launch_ps1 = (REPO / "windows/scripts/launch_hermes.ps1").read_text(encoding="utf-8")
    orch = (REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1").read_text(encoding="utf-8")
    chat_cmd = (REPO / "windows/hermes_chat.cmd").read_text(encoding="utf-8")
    defer_ps1 = (REPO / "windows/scripts/Start-HermesDashboardAfterChat.ps1").read_text(encoding="utf-8")
    assert "launch_hermes.ps1" in bat
    assert "launch_pre_chat_orchestrator.ps1" in launch_ps1
    assert "HERMES_DASHBOARD_AFTER_CHAT" in bat
    assert "HERMES_DASHBOARD_AFTER_CHAT" in orch
    assert "Start-HermesDashboardAfterChat" in chat_cmd
    assert "launch_dashboard_on_start.ps1" in defer_ps1
    assert "launch_dashboard_on_start.ps1" in orch or "DeferDashboardAfterChat" in orch
    assert "HERMES_SKIP_DASHBOARD_ON_START" in orch
    assert "HERMES_DASHBOARD_ON_START" in orch
    assert "HERMES_AUTO_WINDOWS_TERMINAL" in bat
    assert "hermes_launch.log" in bat
    assert "HERMES_LAUNCH_LOG" in orch
    assert 'if defined NO_COLOR set "NO_COLOR="' in bat
    assert 'if /I "%TERM%"=="dumb" set "TERM="' in bat
    assert 'if /I "%FORCE_COLOR%"=="0" set "FORCE_COLOR=1"' in bat
    assert "launch_institutional_runtime.ps1" in orch
    assert 'set "HERMES_DASHBOARD_OPEN_PATH=/codebase-viz"' not in bat


def test_skip_env_exits_zero_quickly(tmp_path: Path) -> None:
    log_path = tmp_path / "hermes_launch.log"
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
        timeout=90,
        env={
            **os.environ,
            "HERMES_SKIP_DASHBOARD_ON_START": "1",
            "HERMES_LAUNCH_LOG": str(log_path),
        },
    )
    assert proc.returncode == 0
    assert log_path.is_file()
    assert "overgeslagen" in log_path.read_text(encoding="utf-8").lower()


def test_on_start_zero_exits_zero() -> None:
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
        timeout=90,
        env={**os.environ, "HERMES_DASHBOARD_ON_START": "0"},
    )
    assert proc.returncode == 0


def test_quiet_still_writes_launch_log(tmp_path: Path) -> None:
    log_path = tmp_path / "hermes_launch.log"
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
            "-Quiet",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=90,
        env={
            **os.environ,
            "HERMES_SKIP_DASHBOARD_ON_START": "1",
            "HERMES_LAUNCH_LOG": str(log_path),
        },
    )
    assert proc.returncode == 0
    assert log_path.is_file()
    assert "overgeslagen" in log_path.read_text(encoding="utf-8").lower()


def test_fix_codebase_viz_cache_bat_exists() -> None:
    bat = REPO / "windows" / "FIX_CODEBASE_VIZ_CACHE.bat"
    repair = REPO / "windows" / "scripts" / "Repair-CodebaseVizPygountCache.ps1"
    assert bat.is_file()
    assert repair.is_file()
    assert "Repair-CodebaseVizPygountCache.ps1" in bat.read_text(encoding="utf-8")


def test_docs_institutional_operations_mention() -> None:
    ops = (REPO / "docs/INSTITUTIONAL_OPERATIONS.md").read_text(encoding="utf-8")
    assert "HERMES_SKIP_DASHBOARD_ON_START" in ops
    assert "9119" in ops
    assert "Codebase Viz" in ops
    assert "verify_codebase_viz_health" in ops


@pytest.mark.e2e
def test_dashboard_on_start_e2e_harness() -> None:
    harness = REPO / "audits" / "DashboardOnStartE2E.harness.py"
    proc = subprocess.run(
        [sys.executable, str(harness)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-3000:]
    assert "ALL PASS" in (proc.stdout or "")
