"""Kritieke Windows-backup/RAG-scripts moeten in de repo staan (regressie a4ed15405+)."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CRITICAL = [
    "windows/backup_hermes.ps1",
    "windows/backup_soul_profiles.ps1",
    "windows/scripts/HermesBackupCommon.ps1",
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
    "windows/HermesSetupScriptPolicy.ps1",
    "windows/scripts/rag_ingest_perf_defaults.ps1",
    "pyproject.toml",
]


def test_hermes_logo_ico_readable_by_pillow():
    """Regressie: multi-size ICO gaf corrupt BMP — Explorer toonde lege pagina-iconen."""
    main = REPO / "windows/hermes_logo.ico"
    if not main.is_file():
        pytest.skip("hermes_logo.ico ontbreekt (genereer via generate_colored_hermes_icons.py)")
    from PIL import Image

    with Image.open(main) as im:
        assert im.size == (256, 256)


def test_taskbar_white_icon_from_png_pipeline():
    """Update-icoon moet PNG-pipeline zijn (~270KB), geen legacy 2KB H-stub."""
    white = REPO / "windows/hermes_taskbar_white.ico"
    gen = REPO / "windows/tools/generate_colored_hermes_icons.py"
    assert "hermes_taskbar_white.ico" in gen.read_text(encoding="utf-8")
    if white.exists():
        assert white.stat().st_size >= 12_000


def test_upstream_sync_branding_dirty_parses_porcelain_path():
    """Regressie: Trim() vóór Substring(3) maakte 'ssets/...' — update blokkeerde ten onrechte."""
    text = (REPO / "windows/upstream_sync.ps1").read_text(encoding="utf-8")
    assert "TrimEnd()" in text
    assert "niet $line.Trim() vóór Substring(3)" in text


def test_update_hermes_uses_upstream_sync():
    bat = (REPO / "windows/UPDATE_HERMES.bat").read_text(encoding="utf-8")
    assert "upstream_sync.ps1" in bat
    assert "-Phase Update" in bat
    assert "gestopt met code" in bat.lower()
    assert "goto :team_display" in bat.lower()


def test_orchestrator_routing_doc_exists():
    assert (REPO / "docs/ORCHESTRATOR_ROUTING.md").is_file()
    assert (REPO / "docs/templates/SOUL_SHARED_INTERACTION.md").is_file()
    assert (REPO / "docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md").is_file()
    assert (REPO / "docs/INSTITUTIONAL_PRESENTATION.md").is_file()
    assert (REPO / "windows/scripts/sync_soul_output_format_snippet.ps1").is_file()
    assert (REPO / "windows/apply_institutional_runtime.ps1").is_file()
    assert (REPO / "windows/APPLY_INSTITUTIONAL_RUNTIME.bat").is_file()
    assert (REPO / "windows/scripts/launch_institutional_runtime.ps1").is_file()
    bat = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    assert "launch_institutional_runtime.ps1" in bat
    assert (REPO / "tests/cli/test_institutional_profile_chat_ux.py").is_file()
    assert (REPO / "hermes_cli/institutional_render.py").is_file()
    assert (REPO / "tests/cli/test_institutional_rich_render.py").is_file()
    assert (REPO / "docs/templates/SOUL_CORE_ORCHESTRATOR.md").is_file()
    assert (REPO / "docs/LEGAL_TAXONOMY.md").is_file()
    assert (REPO / "docs/LEGAL_DOMAIN_ARCHITECTURE.md").is_file()


def test_landkaart_skill_exists():
    assert (REPO / "skills/productivity/landkaart/SKILL.md").is_file()
    assert (REPO / "skills/productivity/landkaart/scripts/inventory_landkaart.py").is_file()


def test_upstream_sync_verify_uses_ps1_not_interactive_bat():
    """Regressie: VERIFY_WINDOWS_CHAIN.bat pause blokkeerde post-merge keten."""
    text = (REPO / "windows/upstream_sync.ps1").read_text(encoding="utf-8")
    assert "verify_windows_script_chain.ps1" in text
    assert "VERIFY_WINDOWS_CHAIN.bat heeft pause" in text


def test_critical_windows_files_exist():
    missing = [rel for rel in CRITICAL if not (REPO / rel).is_file()]
    assert not missing, f"Ontbrekend in repo: {', '.join(missing)}"
