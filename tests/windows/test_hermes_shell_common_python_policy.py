"""Verify HermesShellCommon loads HermesPythonPolicy from windows/ (not caller scripts/)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COMMON = REPO / "windows" / "HermesShellCommon.ps1"
LAUNCH_PS1 = REPO / "windows" / "scripts" / "launch_dashboard_on_start.ps1"


def _ps1_quote(path: Path) -> str:
    return str(path).replace("'", "''")


@pytest.mark.parametrize(
    "script_rel,extra_env",
    [
        ("windows/scripts/launch_institutional_runtime.ps1", {"HERMES_SKIP_INSTITUTIONAL_RUNTIME": "1"}),
        ("windows/scripts/launch_dashboard_on_start.ps1", {"HERMES_SKIP_DASHBOARD_ON_START": "1"}),
    ],
)
def test_dot_source_exposes_resolve_hermes_python(script_rel: str, extra_env: dict[str, str]) -> None:
    script = REPO / script_rel
    assert script.is_file()
    ps = rf"""
$ErrorActionPreference = 'Stop'
. '{_ps1_quote(COMMON)}'
if (-not (Get-Command Resolve-HermesPythonExe -ErrorAction SilentlyContinue)) {{ exit 2 }}
. '{_ps1_quote(script)}' -RepoRoot '{_ps1_quote(REPO)}'
exit $LASTEXITCODE
"""
    env = {**extra_env, "HERMES_REPO_ROOT": str(REPO)}
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=90,
        env={**__import__("os").environ, **env},
    )
    assert proc.returncode != 2, proc.stderr or proc.stdout
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_common_only_sets_hermes_windows_root() -> None:
    text = COMMON.read_text(encoding="utf-8")
    assert "script:HermesWindowsRoot" in text
    assert "MyInvocation.MyCommand.Path" in text
    assert "Join-Path $PSScriptRoot 'HermesPythonPolicy.ps1'" not in text


def test_launch_dashboard_uses_get_dashboard_python_in_stop() -> None:
    text = LAUNCH_PS1.read_text(encoding="utf-8")
    assert "Get-DashboardPythonExe -RepoRoot $RepoRoot" in text
    assert "Stop-HermesDashboardProcess" in text
