"""Guards voor Win32-chat env (geen TERM=xterm op native launcher)."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_launch_hermes_no_unix_term_for_wt_session() -> None:
    bat = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    assert "TERM=xterm-256color" not in bat
    assert "hermes_chat.cmd" in bat


def test_prepare_and_chat_clear_term() -> None:
    prepare = (REPO / "windows/run_hermes_prepare.ps1").read_text(encoding="utf-8")
    chat = (REPO / "windows/hermes_chat.cmd").read_text(encoding="utf-8")
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert "Set-HermesWin32ChatEnv" in prepare
    assert 'set "TERM="' in chat or "set TERM=" in chat
    assert "Clear-HermesUnixTerminalEnv" in common
    assert "set TERM=" in common  # Invoke-HermesCliInCmdConsole bat vangnet
