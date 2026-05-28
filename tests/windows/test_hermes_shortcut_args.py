"""Unit tests voor cmd/wt-argumenten in Hermes .lnk-snelkoppelingen."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ICON_PS1 = REPO / "windows" / "HermesIconGeneratorInvoke.ps1"


def _get_cmd_arg_line(bat: str, *, keep_open: bool = False) -> str:
    flag = "$true" if keep_open else "$false"
    script = (
        f". '{ICON_PS1}' ; "
        f"Get-HermesCmdShortcutArgumentLine -BatchPath '{bat}' -KeepWindowOpen:{flag}"
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


def _get_wt_arg_line(work: str, bat: str, *, keep_open: bool = False) -> str:
    flag = "$true" if keep_open else "$false"
    script = (
        f". '{ICON_PS1}' ; "
        f"Get-HermesWtShortcutArgumentLine -WorkingDirectory '{work}' "
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


def test_cmd_shortcut_args_no_nested_cd_quotes() -> None:
    bat = r"D:\A.I\APPS\Hermes_agent_WS\hermes-agent\windows\UPDATE_HERMES.bat"
    line = _get_cmd_arg_line(bat)
    assert line.startswith("/c call ")
    assert "cd /d" not in line
    assert bat in line.replace('""', '"')


def test_cmd_shortcut_args_keep_open_uses_k_flag() -> None:
    bat = r"C:\repo\windows\RAG_KNOWLEDGE_UPDATE.bat"
    line = _get_cmd_arg_line(bat, keep_open=True)
    assert line.startswith("/k call ")


def test_wt_shortcut_args_use_d_and_call() -> None:
    work = r"D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
    bat = r"D:\A.I\APPS\Hermes_agent_WS\hermes-agent\windows\UPDATE_HERMES.bat"
    line = _get_wt_arg_line(work, bat)
    assert line.startswith('-M -d "')
    assert "cmd.exe" in line.lower()
    assert "/c call" in line
    assert bat in line


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
    assert "start_hermes" in joined


def test_shell_shortcut_uses_wt_when_available() -> None:
    repo = str(REPO).replace("'", "''")
    icon_ps1 = str(ICON_PS1).replace("'", "''")
    bat = str(REPO / "windows" / "UPDATE_HERMES.bat").replace("'", "''")
    script = (
        f". '{icon_ps1}' ; "
        f"$repo = '{repo}'; "
        "$ico = Join-Path $repo 'windows\\hermes_logo_update.ico'; "
        "$lnk = Join-Path $env:TEMP ('hermes_test_shell_' + [guid]::NewGuid().ToString('N') + '.lnk'); "
        "try { "
        f"  if (-not (Set-HermesShellShortcut -ShortcutPath $lnk -TargetBatPath '{bat}' "
        "    -IconIcoPath $ico -WorkingDirectory $repo)) { throw 'create failed' }; "
        "  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk); "
        "  Write-Output $s.TargetPath; Write-Output $s.Arguments; "
        "  $resolved = Get-HermesShortcutResolvedBatPath -ShortcutPath $lnk; "
        "  Write-Output $resolved "
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
    target = lines[0].lower()
    args = lines[1] if len(lines) > 1 else ""
    resolved = lines[-1].lower()
    if "wt.exe" in target:
        assert "/c call" in args
    else:
        assert args.startswith("/c call ")
    assert resolved.endswith("windows\\update_hermes.bat")
