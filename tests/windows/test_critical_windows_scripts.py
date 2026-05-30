"""Kritieke Windows-backup/RAG-scripts moeten in de repo staan (regressie a4ed15405+)."""

from pathlib import Path

import pytest

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
    "windows/requirements-windows.txt",
    "windows/WINDOWS_REQUIREMENTS.md",
    "windows/INSTALL_WINDOWS_TERMINAL.bat",
    "windows/scripts/install_windows_terminal.ps1",
    "windows/hermes_wt_entry.cmd",
    "windows/scripts/launch_in_windows_terminal.ps1",
    "windows/scripts/hermes_disable_quickedit.ps1",
    "windows/scripts/hermes_prepare_console_for_chat.ps1",
    "windows/scripts/launch_hermes.ps1",
    "windows/HermesLaunchUi.ps1",
    "windows/HermesShellCommon.ps1",
    "windows/LANCEDB_MAINTENANCE.bat",
    "scripts/rag_pipeline/lancedb_maintenance.py",
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
    """Regressie: Trim() vóór Substring(3) maakte 'ssets/...' — pad-parse in HermesShellCommon."""
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert "TrimEnd()" in common
    assert "Substring(3)" in common
    sync = (REPO / "windows/upstream_sync.ps1").read_text(encoding="utf-8")
    assert "Test-HermesGitDirtyAllowedForPreflight" in sync


def test_update_hermes_uses_upstream_sync():
    bat = (REPO / "windows/UPDATE_HERMES.bat").read_text(encoding="utf-8")
    assert "upstream_sync.ps1" in bat
    assert "-Phase Update" in bat
    assert "gestopt met code" in bat.lower()
    assert "goto :team_display" in bat.lower()
    assert "-Yes" in bat
    assert "fix_hermes_taskbar_pins.ps1" in bat
    assert "PostUpdateGuidance" in bat
    assert "taakbalk" in bat.lower()
    yes_bat = REPO / "windows/UPDATE_HERMES_YES.bat"
    assert yes_bat.is_file()
    assert "UPDATE_HERMES.bat" in yes_bat.read_text(encoding="utf-8")
    assert "HERMES_UPSTREAM_AUTO_CONFIRM=1" in yes_bat.read_text(encoding="utf-8")


def test_taskbar_pin_repair_covers_start_hermes_and_in_place_refresh():
    """Taakbalk-pins (ook Start Hermes*.lnk) worden na update in-place vernieuwd."""
    ps1 = (REPO / "windows/scripts/HermesPersistentShortcuts.ps1").read_text(encoding="utf-8")
    icon_ps1 = (REPO / "windows/HermesIconGeneratorInvoke.ps1").read_text(encoding="utf-8")
    post_merge = (REPO / "windows/scripts/Invoke-UpstreamPostMerge.ps1").read_text(encoding="utf-8")
    assert "function Test-HermesManagedPinLeaf" in ps1
    assert "function Get-HermesTaskbarPinShortcutCandidates" in ps1
    assert "Remove-HermesUnlaunchableTaskbarPins" in ps1
    assert "RefreshAllTaskbarPins" in ps1
    assert "InstallLocation" in icon_ps1
    assert "fix_hermes_taskbar_pins.ps1" in post_merge
    assert "Filter 'Hermes*.lnk'" not in ps1
    assert "Remove-Item -LiteralPath $ShortcutPath" not in icon_ps1
    assert "function Set-HermesTaskbarPinShortcut" in icon_ps1
    assert "TargetPath = $batFull" in icon_ps1
    assert "ForTaskbarPin" in ps1
    assert "zonder .lnk te verwijderen" in ps1 or "windows\\ eerst" in ps1


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
    launch_ps1 = (REPO / "windows/scripts/launch_hermes.ps1").read_text(encoding="utf-8")
    assert "launch_hermes.ps1" in bat
    assert "launch_pre_chat_orchestrator.ps1" in launch_ps1
    assert (REPO / "tests/cli/test_institutional_profile_chat_ux.py").is_file()
    assert (REPO / "hermes_cli/institutional_render.py").is_file()
    assert (REPO / "tests/cli/test_institutional_rich_render.py").is_file()
    assert (REPO / "docs/templates/SOUL_CORE_ORCHESTRATOR.md").is_file()
    assert (REPO / "docs/LEGAL_TAXONOMY.md").is_file()
    assert (REPO / "docs/LEGAL_DOMAIN_ARCHITECTURE.md").is_file()
    assert (REPO / "docs/CODEBASE_AUDIT_EVIDENCE.md").is_file()
    assert (REPO / "windows/audits/RUN_CODEBASE_SMOKE_AUDIT.ps1").is_file()
    assert (REPO / "scripts/emit_codebase_smoke_report.py").is_file()
    prepare_text = (REPO / "windows/run_hermes_prepare.ps1").read_text(encoding="utf-8")
    launch_bat = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    launch_ps1 = (REPO / "windows/scripts/launch_hermes.ps1").read_text(encoding="utf-8")
    orch_ps1 = (REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1").read_text(encoding="utf-8")
    assert "ensure_hermes_launch_env.ps1" in prepare_text
    assert "launch_hermes.ps1" in launch_bat
    assert "launch_pre_chat_orchestrator.ps1" in launch_ps1
    assert "hermes_chat.cmd" in launch_bat
    assert "launch_pending_trust_runtime.ps1" in orch_ps1


def test_landkaart_skill_exists():
    assert (REPO / "skills/productivity/landkaart/SKILL.md").is_file()
    assert (REPO / "skills/productivity/landkaart/scripts/inventory_landkaart.py").is_file()


def test_upstream_sync_verify_uses_ps1_not_interactive_bat():
    """Regressie: VERIFY_WINDOWS_CHAIN.bat pause blokkeerde post-merge keten."""
    post = (REPO / "windows/scripts/Invoke-UpstreamPostMerge.ps1").read_text(encoding="utf-8")
    assert "verify_windows_script_chain.ps1" in post
    assert "VERIFY_WINDOWS_CHAIN.bat" not in post
    sync = (REPO / "windows/upstream_sync.ps1").read_text(encoding="utf-8")
    assert "Invoke-UpstreamPostMerge.ps1" in sync


def test_critical_windows_files_exist():
    missing = [rel for rel in CRITICAL if not (REPO / rel).is_file()]
    assert not missing, f"Ontbrekend in repo: {', '.join(missing)}"


def test_open_setup_is_single_canonical_implementation():
    canonical = (REPO / "scripts/windows/OPEN_SETUP.bat").read_text(encoding="utf-8")
    wrapper = (REPO / "windows/OPEN_SETUP.bat").read_text(encoding="utf-8")
    assert "python -m hermes_cli.main setup" in canonical
    assert "Wrapper-only" in wrapper
    assert "..\\scripts\\windows\\OPEN_SETUP.bat" in wrapper
    assert "python -m hermes_cli.main setup" not in wrapper


def test_setup_launchers_reference_canonical_open_setup():
    setup_bat = (REPO / "windows/setup_hermes_windows.bat").read_text(encoding="utf-8")
    setup_hermes = (REPO / "windows/SETUP_HERMES.bat").read_text(encoding="utf-8")
    setup_ps1 = (REPO / "scripts/windows/setup_hermes_windows.ps1").read_text(encoding="utf-8")
    assert "..\\scripts\\windows\\OPEN_SETUP.bat" in setup_bat
    assert "..\\scripts\\windows\\OPEN_SETUP.bat" in setup_hermes
    assert "Wrapper-only: canonieke implementatie leeft in scripts\\windows\\OPEN_SETUP.bat" in setup_ps1


def test_launch_hermes_uses_relaunch_maximize_baseline():
    launch = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    assert 'start "" /max "%ComSpec%"' in launch or "HERMES_MAX_FLAG=1" in launch
    assert "ShowWindow" not in launch


def test_start_hermes_sets_max_flag_to_skip_double_relaunch():
    bat = (REPO / "start_hermes.bat").read_text(encoding="utf-8")
    profiles = (REPO / "windows/launch_profiles.ps1").read_text(encoding="utf-8")
    assert "Invoke-HermesLaunchProfileEnv" in bat
    assert "HERMES_MAX_FLAG" in profiles and "'1'" in profiles
    assert "HERMES_SKIP_DOCKER_ON_START" in profiles
    assert "HERMES_SKIP_HARDWARE_PROBE" in profiles
    assert "HERMES_NO_WAKE_LOCAL_LLM" in profiles
    assert "HERMES_CONSOLE_LAYOUT" in profiles
    assert "'maximized'" in profiles
    assert "HERMES_AUTO_WINDOWS_TERMINAL" in profiles


def test_windows_requirements_lists_windows_terminal():
    req = (REPO / "windows/requirements-windows.txt").read_text(encoding="utf-8")
    assert "Microsoft.WindowsTerminal" in req
    install_ps1 = (REPO / "windows/scripts/install_windows_terminal.ps1").read_text(encoding="utf-8")
    assert "Microsoft.WindowsTerminal" in install_ps1


def test_launch_hermes_skips_docker_when_env_set():
    orch = (REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1").read_text(encoding="utf-8")
    profiles = (REPO / "windows/launch_profiles.ps1").read_text(encoding="utf-8")
    launch_ui = (REPO / "windows/HermesLaunchUi.ps1").read_text(encoding="utf-8")
    assert "HERMES_SKIP_DOCKER_ON_START" in orch
    assert "Invoke-HermesDockerPreflight" in launch_ui
    assert "HERMES_SKIP_DOCKER_ON_START" in profiles


def test_launch_ui_sink_wiring():
    bat = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    ps1 = (REPO / "windows/scripts/launch_hermes.ps1").read_text(encoding="utf-8")
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert (REPO / "windows/HermesLaunchUi.ps1").is_file()
    assert (REPO / "windows/scripts/launch_hermes.ps1").is_file()
    assert "launch_hermes.ps1" in bat
    assert "launch_pre_chat_orchestrator.ps1" in ps1
    assert "-SkipBootstrap" not in ps1
    assert "launch_bootstrap.ps1" not in bat
    assert "HermesLaunchUi.ps1" in common
    assert "Write-HermesLaunchUi" in common
    assert "Invoke-HermesLaunchPhase" in common


LAUNCH_UI_ALLOWLIST = [
    "windows/scripts/launch_hermes.ps1",
    "windows/scripts/launch_pre_chat_orchestrator.ps1",
    "windows/scripts/launch_bootstrap.ps1",
    "windows/scripts/launch_soul_anatomy_deploy.ps1",
    "windows/scripts/launch_trust_runtime_sync.ps1",
    "windows/scripts/launch_institutional_runtime.ps1",
    "windows/scripts/launch_pending_trust_runtime.ps1",
    "windows/scripts/launch_dashboard_on_start.ps1",
    "windows/scripts/HermesSessionMaintenance.ps1",
    "windows/apply_institutional_runtime.ps1",
    "windows/scripts/Invoke-TrustRuntimeLight.ps1",
    "windows/scripts/sync_all_domain_souls_from_templates.ps1",
    "windows/scripts/install_rag_extras.ps1",
]


@pytest.mark.parametrize("rel_path", LAUNCH_UI_ALLOWLIST)
def test_launch_path_scripts_use_launch_ui_not_write_host(rel_path: str):
    path = REPO / rel_path
    assert path.is_file(), f"{rel_path} ontbreekt"
    text = path.read_text(encoding="utf-8")
    assert "Write-Host" not in text, f"{rel_path} mag geen Write-Host gebruiken (Launch UI Sink)"
    assert "-NoNewline" not in text, f"{rel_path} mag geen -NoNewline gebruiken"


def test_launch_pre_chat_orchestrator_and_maximize():
    launch = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    launch_ps1 = (REPO / "windows/scripts/launch_hermes.ps1").read_text(encoding="utf-8")
    common = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert (REPO / "windows/scripts/launch_pre_chat_orchestrator.ps1").is_file()
    assert (REPO / "windows/scripts/maximize_console.ps1").is_file()
    assert "hermes_wt_entry.cmd" in launch
    assert "System32\\cmd.exe" in launch
    assert "Invoke-HermesDisableConsoleQuickEdit" in launch
    assert (REPO / "windows/scripts/hermes_disable_quickedit.ps1").is_file()
    assert "launch_hermes.ps1" in launch
    assert "launch_pre_chat_orchestrator.ps1" in launch_ps1
    assert "Invoke-HermesExpandConsoleWindow" in launch or "Invoke-HermesExpandConsoleWindow" in common
    assert "auto-expand werkgebied" in launch or "Invoke-HermesExpandConsoleWindow" in launch
    assert "Invoke-HermesLaunchPhase" in common
    assert "Invoke-HermesMaximizeConsoleWindow" in common
    assert "Start-HermesNoWindowProcess" in common
    assert "Stop-HermesGhostInputBlockers" in common
    assert "Invoke-HermesDismissGhostConsoleWindows" in common
    assert "Reset-HermesConsoleInputModes" in common
    profiles_ps1 = (REPO / "windows/launch_profiles.ps1").read_text(encoding="utf-8")
    assert "HERMES_SKIP_DASHBOARD_ON_START" in profiles_ps1
    launch_bat = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    assert "run_hermes_prepare.ps1" in launch_bat
    assert "Invoke-HermesDisableConsoleQuickEdit" in launch_bat
    assert "ExpandConsoleToWorkArea" in common
    assert "ExpandConsoleComfortably" in common
    assert "maximized" in common
    assert "EnsureConsoleScrollbackBuffer" in common
    assert "ConfigureConsoleInputForScroll" in common
    assert "Invoke-HermesExpandConsoleWindow" in common
    assert "Invoke-HermesPostConsoleLayoutFix" in common
    assert "Invoke-HermesFocusConsoleWindow" in common
    assert "HERMES_DISMISS_GHOST_CONSOLES" in common
    assert "FocusConsoleWindow" in common
    home = (REPO / "windows/scripts/HermesHomeCommon.ps1").read_text(encoding="utf-8")
    assert "Write-HermesRuntimeModelBanner" in home
    assert "Get-HermesModelFieldsFromConfigYaml" in home
    assert "(?ms)^model:" not in home


def test_run_hermes_no_duplicate_catalog_guard():
    run_ps1 = (REPO / "windows/run_hermes.ps1").read_text(encoding="utf-8")
    assert "Test-HermesModelCatalogAvailability" not in run_ps1


def test_run_hermes_uses_direct_python_not_conda_run():
    """conda run ontkoppelt Win32 console → prompt_toolkit NoConsoleScreenBufferError."""
    run_ps1 = (REPO / "windows/run_hermes.ps1").read_text(encoding="utf-8")
    prepare_ps1 = (REPO / "windows/run_hermes_prepare.ps1").read_text(encoding="utf-8")
    common_ps1 = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    launch = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    chat_cmd = REPO / "windows/hermes_chat.cmd"
    assert chat_cmd.is_file()
    assert "run_hermes_prepare.ps1" in launch
    assert "hermes_chat.cmd" in launch
    assert "TERM=xterm-256color" not in launch
    assert "TERM=xterm-256color" not in prepare_ps1
    assert "run -n hermes-env" not in prepare_ps1
    assert "Get-HermesAuditPython" in prepare_ps1
    assert "Write-HermesLaunchState" in prepare_ps1
    assert "HermesShellCommon.ps1" in run_ps1
    assert "Invoke-HermesCliInCmdConsole" in common_ps1
    assert "function Clear-HermesUnixTerminalEnv" in common_ps1
    assert "function Set-HermesWin32ChatEnv" in common_ps1
    assert "function Invoke-HermesCliInCmdConsole" in common_ps1
    assert "function Test-HermesWin32Console" in common_ps1
    chat_text = (REPO / "windows/hermes_chat.cmd").read_text(encoding="utf-8")
    assert 'set "TERM="' in chat_text or "set TERM=" in chat_text
    assert "HERMES_PYTHON" in chat_text
    assert "powershell -noprofile" not in chat_text.lower()
    assert "invoke-hermesrepairconsoleforchat" not in chat_text.lower()
    assert "start /B" not in chat_text.lower()
    assert "Clear-Host" not in prepare_ps1
    assert "Start-HermesDashboardAfterChatDetached" in prepare_ps1
    launch_ui = (REPO / "windows/HermesLaunchUi.ps1").read_text(encoding="utf-8")
    assert "Write-HermesLaunchPinnedHeader" in launch_ui
