"""Kritieke Windows-backup/RAG-scripts moeten in de repo staan (regressie a4ed15405+)."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CRITICAL = [
    "windows/backup_hermes.ps1",
    "windows/restore_from_backup.ps1",
    "windows/MANAGE_BACKUPS.bat",
    "windows/RESTORE_FROM_BACKUP.bat",
    "windows/sync_local_assets_to_backup.ps1",
    "windows/WindowsLocalAssetsManifest.ps1",
    "windows/verify_windows_script_chain.ps1",
    "windows/scripts/rag_ingest_perf_defaults.ps1",
    "pyproject.toml",
]


def test_critical_windows_files_exist():
    missing = [rel for rel in CRITICAL if not (REPO / rel).is_file()]
    assert not missing, f"Ontbrekend in repo: {', '.join(missing)}"
