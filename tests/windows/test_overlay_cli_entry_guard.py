"""Windows launchers must not invoke bare ``python -m hermes_cli.main``."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SCAN_ROOTS = (
    REPO / "windows",
    REPO / "scripts" / "windows",
)

ALLOWLIST = {
    REPO / "windows" / "TERMINAL_WINDOWS.md",
    REPO / "windows" / "START.md",
    REPO / "windows" / "LAUNCH_PROFILES.md",
    REPO / "windows" / "launch_profiles.ps1",
    REPO / "windows" / "stop_other_hermes_processes.ps1",
    REPO / "windows" / "scripts" / "user_data" / "hermes_with_env.bat",
}

LEGACY_INVOKE = re.compile(r"-m\s+hermes_cli\.main\b")


def _iter_guarded_files():
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".bat", ".cmd", ".ps1"}:
                continue
            if path in ALLOWLIST:
                continue
            yield path


def test_repair_console_entry_uses_cli_entry():
    bat = (REPO / "windows/REPAIR_CONSOLE_ENTRY.bat").read_text(encoding="utf-8")
    ps1 = (REPO / "windows/scripts/repair_console_entry.ps1").read_text(encoding="utf-8")
    assert "repair_console_entry.ps1" in bat
    assert "hermes_cli_entry" in ps1
    assert "pip install -e" in ps1
    assert "repair_terminal_cwd.ps1" in ps1


def test_repair_terminal_cwd_script_exists():
    ps1 = (REPO / "windows/scripts/repair_terminal_cwd.ps1").read_text(encoding="utf-8")
    py = (REPO / "scripts/repair_terminal_cwd.py").read_text(encoding="utf-8")
    assert "repair_terminal_cwd.py" in ps1
    assert "migrate_terminal_cwd" in py
    assert "MESSAGING_CWD" in py


def test_windows_launchers_avoid_legacy_cli_module():
    offenders: list[str] = []
    for path in _iter_guarded_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if LEGACY_INVOKE.search(text):
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, (
        "Gebruik '-m hermes_cli_entry' (overlay bootstrap). Offenders: "
        + ", ".join(offenders)
    )
