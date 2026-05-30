"""Unit tests voor windows/launch_profiles.ps1."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROFILE_PS1 = REPO / "windows" / "launch_profiles.ps1"


def _ps(script: str) -> str:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return (proc.stdout or "").strip()


def test_resolve_defaults_to_full() -> None:
    out = _ps(
        f". '{PROFILE_PS1}' ; Resolve-HermesLaunchProfile -Profile '' -ConfigPath 'C:\\nope\\config.yaml'"
    )
    assert out == "full"


def test_resolve_full_from_profile_arg() -> None:
    out = _ps(f". '{PROFILE_PS1}' ; Resolve-HermesLaunchProfile -Profile 'full'")
    assert out == "full"


def test_full_profile_enables_dashboard_and_disables_minimal() -> None:
    out = _ps(
        f". '{PROFILE_PS1}' ; "
        "$m = Get-HermesLaunchProfileEnvMap -Profile full; "
        "Write-Output ($m['HERMES_MINIMAL_LAUNCH']); "
        "Write-Output ($m['HERMES_SKIP_DASHBOARD_ON_START']); "
        "Write-Output ($m['HERMES_SKIP_DASHBOARD_BROWSER']); "
        "Write-Output ([string]::IsNullOrEmpty($m['HERMES_DASHBOARD_OPEN_PATH']))"
    )
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert lines[0] == "0"
    assert lines[1] == "0"
    assert lines[2] == "1"
    assert lines[3].lower() == "true"


def test_cli_args_filter_strips_launch_profile_flags() -> None:
    script = (
        f". '{PROFILE_PS1}' ; "
        f"$env:HERMES_LAUNCH_ARGS='chat --minimal --maximized'; "
        f"$a = Get-HermesLaunchCliArgs; Write-Output ($a -join ' ')"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert proc.stdout.strip() == "chat"


def test_minimal_profile_skips_prechat() -> None:
    out = _ps(
        f". '{PROFILE_PS1}' ; "
        "$m = Get-HermesLaunchProfileEnvMap -Profile minimal; "
        "Write-Output ($m['HERMES_MINIMAL_LAUNCH']); "
        "Write-Output ($m['HERMES_SKIP_SOUL_DEPLOY_ON_START'])"
    )
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert lines[0] == "1"
    assert lines[1] == "1"
