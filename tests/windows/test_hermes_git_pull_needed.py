"""Test-HermesGitPullNeeded.ps1 contract and wiring."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PS1 = REPO / "windows" / "scripts" / "Test-HermesGitPullNeeded.ps1"
START_BAT = REPO / "start_hermes.bat"


def test_pull_needed_script_exists_and_documents_exit_codes() -> None:
    text = PS1.read_text(encoding="utf-8")
    assert "exit 0" in text
    assert "exit 1" in text
    assert "exit 2" in text
    assert "MERGE_HEAD" in text
    assert "HERMES_SKIP_AUTO_PULL_ON_START" in text


def test_start_hermes_auto_pull_wiring() -> None:
    bat = START_BAT.read_text(encoding="utf-8")
    assert "Test-HermesGitPullNeeded.ps1" in bat
    assert "maybe_auto_pull_before_start" in bat
    assert "--no-pull" in bat


def test_start_hermes_ps1_parses() -> None:
    import subprocess

    path = str(PS1).replace("'", "''")
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
