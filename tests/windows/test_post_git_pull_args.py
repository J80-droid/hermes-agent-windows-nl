"""POST_GIT_PULL.bat flags and relaunch wiring."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_post_git_pull_has_relaunch_and_full_flags() -> None:
    text = (REPO / "windows/POST_GIT_PULL.bat").read_text(encoding="utf-8")
    assert "-RelaunchHermes" in text
    assert "-SkipRelaunch" in text
    assert "-IncludeInstitutionalVerify" in text
    assert "-IncludeRagPipeline" in text
    assert "-Full" in text
    assert "Invoke-HermesPostPullRelaunch.ps1" in text
    assert "Invoke-HermesPostPullMaintenance.ps1" in text
    assert "-Phase PostPullTail" in text
    assert "Invoke-PostGitPullTrustOutcome.ps1" in text
    assert "apply_institutional_runtime.ps1" in text
    assert "MERGE_HEAD" in text
    assert "HermesSessionMaintenance.ps1" in text


def test_pull_hermes_bat_chains_git_pull_and_post() -> None:
    text = (REPO / "PULL_HERMES.bat").read_text(encoding="utf-8")
    assert "git pull" in text
    assert "POST_GIT_PULL.bat" in text
    assert "which_hermes_repo.ps1" in text


def test_invoke_upstream_post_merge_calls_relaunch() -> None:
    text = (REPO / "windows/scripts/Invoke-UpstreamPostMerge.ps1").read_text(encoding="utf-8")
    assert "Invoke-HermesPostPullRelaunch.ps1" in text
