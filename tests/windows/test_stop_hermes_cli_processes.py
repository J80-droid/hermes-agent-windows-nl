"""stop_other_hermes_processes.ps1 kills python hermes_cli.main."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parents[2]
STOP_PS1 = REPO / "windows" / "stop_other_hermes_processes.ps1"


def test_stop_script_matches_hermes_cli_main_in_commandline() -> None:
    text = STOP_PS1.read_text(encoding="utf-8")
    assert "hermes_cli\\.main" in text
    assert "Win32_Process" in text
    assert "KeepPid" in text
    assert "Name = 'python.exe' OR Name = 'pythonw.exe'" in text


def test_stop_script_ps1_parses() -> None:
    import subprocess

    path = str(STOP_PS1).replace("'", "''")
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"$e=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile('{path}', [ref]$null, [ref]$e); if ($e) {{ $e; exit 1 }}",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
