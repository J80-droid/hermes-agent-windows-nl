"""Unit tests voor Invoke-HermesPostChangeMaintenance.ps1 en HERMES_ONDERHOUD.bat."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PS1 = REPO / "windows" / "scripts" / "Invoke-HermesPostChangeMaintenance.ps1"
BAT_WIN = REPO / "windows" / "HERMES_ONDERHOUD.bat"
BAT_ROOT = REPO / "hermes_onderhoud.bat"


@pytest.fixture(scope="module")
def ps1_text() -> str:
    assert PS1.is_file()
    return PS1.read_text(encoding="utf-8")


def test_ps1_exists_and_wires_phases(ps1_text: str) -> None:
    assert "create_taskbar_shortcuts.ps1" in ps1_text
    assert "create_shortcut.ps1" in ps1_text
    assert "fix_hermes_taskbar_pins.ps1" in ps1_text
    assert "launch_dashboard_on_start.ps1" in ps1_text
    assert "verify_windows_script_chain.ps1" in ps1_text
    assert "ShortcutsOnly" in ps1_text
    assert "DashboardOnly" in ps1_text


def test_bat_wrappers_exist() -> None:
    bat_root = BAT_ROOT.read_text(encoding="utf-8")
    bat_win = BAT_WIN.read_text(encoding="utf-8")
    assert "HERMES_ONDERHOUD.bat" in bat_root
    assert "Invoke-HermesPostChangeMaintenance.ps1" in bat_win

    refresh = (REPO / "windows" / "REFRESH_TASKBAR_SHORTCUTS.bat").read_text(encoding="utf-8")
    assert "HERMES_ONDERHOUD.bat" in refresh
    assert "-ShortcutsOnly" in refresh

    restart = (REPO / "audits" / "RESTART_CODEBASE_VIZ_DASHBOARD.bat").read_text(encoding="utf-8")
    assert "HERMES_ONDERHOUD.bat" in restart
    assert "-DashboardOnly" in restart
