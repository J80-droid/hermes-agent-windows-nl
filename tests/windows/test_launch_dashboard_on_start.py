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
    assert "hermes_cli.main', 'dashboard'" in ps1_text or "hermes_cli.main dashboard" in ps1_text


def test_ps1_skip_env_flags(ps1_text: str) -> None:
    assert "HERMES_SKIP_DASHBOARD_ON_START" in ps1_text
    assert "HERMES_DASHBOARD_ON_START" in ps1_text


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


def test_launch_hermes_bat_wires_script() -> None:
    bat = BAT.read_text(encoding="utf-8")
    assert "launch_dashboard_on_start.ps1" in bat
    assert "HERMES_SKIP_DASHBOARD_ON_START" in bat
    assert "HERMES_LAUNCH_LOG" in bat


def test_skip_env_exits_zero_quickly() -> None:
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
        env={**os.environ, "HERMES_SKIP_DASHBOARD_ON_START": "1"},
    )
    assert proc.returncode == 0
    assert "overgeslagen" in (proc.stdout or "").lower()


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


def test_docs_institutional_operations_mention() -> None:
    ops = (REPO / "docs/INSTITUTIONAL_OPERATIONS.md").read_text(encoding="utf-8")
    assert "HERMES_SKIP_DASHBOARD_ON_START" in ops
    assert "9119" in ops


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
