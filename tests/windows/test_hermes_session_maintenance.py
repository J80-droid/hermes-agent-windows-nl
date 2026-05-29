"""Hermes sessie-onderhoud (stamps, module, orchestrator wiring)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_hermes_session_maintenance_module_exists() -> None:
    path = REPO / "windows/scripts/HermesSessionMaintenance.ps1"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    for name in (
        "Invoke-HermesStartMaintenance",
        "Invoke-HermesPostPullMaintenance",
        "Invoke-HermesShortcutMaintenance",
        "Invoke-HermesConditionalWindowsChainVerify",
        "Invoke-HermesBrandingOnlyAutoCommit",
    ):
        assert name in text


def test_invoke_post_pull_maintenance_wrapper() -> None:
    path = REPO / "windows/scripts/Invoke-HermesPostPullMaintenance.ps1"
    assert path.is_file()
    assert "HermesSessionMaintenance.ps1" in path.read_text(encoding="utf-8")


def test_post_git_pull_uses_post_pull_maintenance() -> None:
    bat = (REPO / "windows/POST_GIT_PULL.bat").read_text(encoding="utf-8")
    assert "Invoke-HermesPostPullMaintenance.ps1" in bat
    assert "PostPullTail" in bat


def test_launch_hermes_uses_orchestrator() -> None:
    bat = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    assert "launch_pre_chat_orchestrator.ps1" in bat
    assert "-SkipBootstrap" in bat


def test_shell_common_session_stamps() -> None:
    text = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert "Get-HermesSessionStampPath" in text
    assert "Test-HermesShouldSkipPostPullMaintenanceOnStart" in text
    assert "Clear-HermesUpdateCheckCache" in text


def test_launch_profiles_full_autorepair() -> None:
    text = (REPO / "windows/launch_profiles.ps1").read_text(encoding="utf-8")
    assert "HERMES_AUTOREPAIR_MODEL_ON_DRIFT" in text
    assert "HERMES_SKIP_SHORTCUT_MAINT_ON_START" in text


def test_launch_profiles_minimal_skips_start_maint() -> None:
    text = (REPO / "windows/launch_profiles.ps1").read_text(encoding="utf-8")
    assert "HERMES_SKIP_SHORTCUT_MAINT_ON_START     = '1'" in text


def test_model_catalog_auto_repair_exists() -> None:
    text = (REPO / "windows/scripts/HermesHomeCommon.ps1").read_text(encoding="utf-8")
    assert "function Invoke-HermesModelCatalogAutoRepair" in text


def test_branding_only_paths_in_shell_common() -> None:
    text = (REPO / "windows/HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert "Test-HermesGitDirtyOnlyBranding" in text
    assert "hermes[^/]*\\.ico" in text or "hermes[^/]*.ico" in text


def test_model_config_maintenance_allowfailure_param() -> None:
    text = (REPO / "windows/scripts/HermesSessionMaintenance.ps1").read_text(encoding="utf-8")
    assert "function Invoke-HermesModelConfigMaintenance" in text
    assert "param([switch]$AllowFailure)" in text
    assert "$script:DotAllowFailure" in text
    assert "Invoke-HermesModelConfigMaintenance -AllowFailure:$AllowFailure" in text


def test_domains_fingerprint_helper() -> None:
    text = (REPO / "windows/scripts/HermesSessionMaintenance.ps1").read_text(encoding="utf-8")
    assert "function Test-HermesDomainsFingerprintChanged" in text
    assert "if (-not $CurrentFp)" in text


def test_post_pull_rag_uses_start_process() -> None:
    text = (REPO / "windows/scripts/HermesSessionMaintenance.ps1").read_text(encoding="utf-8")
    assert "Start-Process -FilePath 'cmd.exe'" in text
    assert "$ragProc.ExitCode" in text
