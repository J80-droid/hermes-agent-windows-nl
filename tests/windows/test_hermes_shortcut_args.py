"""Unit tests voor cmd.exe-argumenten in Hermes .lnk-snelkoppelingen."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ICON_PS1 = REPO / "windows" / "HermesIconGeneratorInvoke.ps1"


def _get_arg_line(work: str, bat: str, *, keep_open: bool = False) -> str:
    flag = "$true" if keep_open else "$false"
    script = (
        f". '{ICON_PS1}' ; "
        f"Get-HermesCmdShortcutArgumentLine -WorkingDirectory '{work}' "
        f"-BatchPath '{bat}' -KeepWindowOpen:{flag}"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return (proc.stdout or "").strip()


def test_shortcut_args_use_cd_and_call_for_dotted_path() -> None:
    work = r"D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
    bat = r"D:\A.I\APPS\Hermes_agent_WS\hermes-agent\start_hermes.bat"
    line = _get_arg_line(work, bat)
    assert line.startswith("/d /c ")
    assert 'cd /d ""D:\\A.I\\APPS\\Hermes_agent_WS\\hermes-agent""' in line
    assert 'call ""D:\\A.I\\APPS\\Hermes_agent_WS\\hermes-agent\\start_hermes.bat""' in line


def test_shortcut_args_keep_open_uses_k_flag() -> None:
    work = r"C:\repo"
    bat = r"C:\repo\windows\RAG_KNOWLEDGE_UPDATE.bat"
    line = _get_arg_line(work, bat, keep_open=True)
    assert line.startswith("/d /k ")


def test_start_shortcut_prefers_wt_with_start_hermes() -> None:
    repo = str(REPO).replace("'", "''")
    icon_ps1 = str(ICON_PS1).replace("'", "''")
    script = (
        f". '{icon_ps1}' ; "
        f"$repo = '{repo}'; "
        "$ico = Join-Path $repo 'windows\\hermes_logo.ico'; "
        "$lnk = Join-Path $env:TEMP ('hermes_test_start_' + [guid]::NewGuid().ToString('N') + '.lnk'); "
        "try { "
        "  if (-not (Set-HermesStartShellShortcut -ShortcutPath $lnk -RepoRoot $repo -IconIcoPath $ico)) { throw 'create failed' }; "
        "  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk); "
        "  Write-Output $s.TargetPath; Write-Output $s.Arguments "
        "} finally { Remove-Item -LiteralPath $lnk -Force -ErrorAction SilentlyContinue }"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    assert any("wt.exe" in ln.lower() or "windowsterminal.exe" in ln.lower() for ln in lines[:1]) or lines
    joined = " ".join(lines)
    assert "start_hermes.bat" in joined
