"""Kritieke Windows-backup/RAG-scripts moeten in de repo staan (regressie a4ed15405+)."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CRITICAL = [
    "windows/backup_hermes.ps1",
    "windows/restore_from_backup.ps1",
    "windows/MANAGE_BACKUPS.bat",
    "windows/RESTORE_FROM_BACKUP.bat",
    "windows/UPDATE_HERMES.bat",
    "windows/upstream_sync.ps1",
    "windows/UPSTREAM_SYNC.md",
    "windows/FIX_TASKBAR_ICONS.bat",
    "windows/fix_hermes_taskbar_pins.ps1",
    "windows/sync_local_assets_to_backup.ps1",
    "windows/WindowsLocalAssetsManifest.ps1",
    "windows/verify_windows_script_chain.ps1",
    "windows/scripts/rag_ingest_perf_defaults.ps1",
    "pyproject.toml",
]


def test_taskbar_white_icon_from_png_pipeline():
    """Update-icoon moet PNG-pipeline zijn (~270KB), geen legacy 2KB H-stub."""
    white = REPO / "windows/hermes_taskbar_white.ico"
    gen = REPO / "windows/tools/generate_colored_hermes_icons.py"
    assert "hermes_taskbar_white.ico" in gen.read_text(encoding="utf-8")
    if white.exists():
        assert white.stat().st_size >= 12_000


def test_update_hermes_uses_upstream_sync():
    bat = (REPO / "windows/UPDATE_HERMES.bat").read_text(encoding="utf-8")
    assert "upstream_sync.ps1" in bat
    assert "-Phase Update" in bat
    assert "gestopt met code" in bat.lower()
    assert "goto :team_display" in bat.lower()


def test_critical_windows_files_exist():
    missing = [rel for rel in CRITICAL if not (REPO / rel).is_file()]
    assert not missing, f"Ontbrekend in repo: {', '.join(missing)}"
