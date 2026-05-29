"""Unit tests voor ``audits/SessionMaintenanceE2E.harness.py``.

Piramide:
  - Unit (hier): helpers + scenario's met mocks (geen live PowerShell-keten)
  - Integratie: ``test_session_maintenance_e2e_harness_runs`` (volledige harness via subprocess, -m e2e)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "SessionMaintenanceE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("session_maintenance_e2e_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    assert HARNESS_PATH.is_file()
    return _load_harness()


@pytest.fixture(autouse=True)
def _reset_counters(harness: ModuleType) -> None:
    harness.FAILURES = 0
    harness.STEP = 0
    yield
    harness.FAILURES = 0
    harness.STEP = 0


class TestStep:
    def test_ok(self, harness: ModuleType) -> None:
        harness._step("ok", True, "detail")
        assert harness.STEP == 1 and harness.FAILURES == 0

    def test_fail(self, harness: ModuleType) -> None:
        harness._step("fail", False)
        assert harness.FAILURES == 1


class TestAuditPython:
    def test_prefers_hermes_audit_python_env(self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        py = tmp_path / "audit-python.exe"
        py.write_text("", encoding="utf-8")
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(py))
        assert harness._audit_python() == str(py)

    def test_invalid_env_falls_back(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(REPO / "__nope__.exe"))
        monkeypatch.setenv("USERPROFILE", str(REPO / "__no_conda__"))
        assert harness._audit_python() == sys.executable


class TestPowerShellHelpers:
    def test_powershell_file_merges_env(self, harness: ModuleType) -> None:
        script = REPO / "windows/scripts/HermesSessionMaintenance.ps1"
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as run:
            harness._powershell_file(script, env={"LOCALAPPDATA": "/tmp/unit"})
        assert run.call_args.kwargs["env"]["LOCALAPPDATA"] == "/tmp/unit"

    def test_powershell_command_timeout(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("powershell", 90)):
            with pytest.raises(subprocess.TimeoutExpired):
                harness._powershell_command("exit 0", timeout=90)

    def test_parse_ps1_false_on_error(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert harness._parse_ps1(REPO / "windows/HermesShellCommon.ps1") is False


class TestS1RepoArtifacts:
    def test_happy(self, harness: ModuleType) -> None:
        harness.test_s1_repo_artifacts()
        assert harness.FAILURES == 0

    def test_missing_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness, "REPO", REPO / "__missing_repo__")
        harness.test_s1_repo_artifacts()
        assert harness.FAILURES == 1


class TestS3PostGitPullWiring:
    def test_order_verify_before_trust(self, harness: ModuleType) -> None:
        harness.test_s3_post_git_pull_wiring()
        assert harness.FAILURES == 0

    def test_fails_when_post_pull_missing(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        text = (REPO / "windows/POST_GIT_PULL.bat").read_text(encoding="utf-8")
        monkeypatch.setattr(harness, "_read", lambda rel: text.replace("Invoke-HermesPostPullMaintenance.ps1", ""))
        harness.test_s3_post_git_pull_wiring()
        assert harness.FAILURES == 1


class TestS4Orchestrator:
    def test_allowfailure_dot_source(self, harness: ModuleType) -> None:
        harness.test_s4_orchestrator_wiring()
        assert harness.FAILURES == 0


class TestS8StampRoundtrip:
    def test_isolated_stamps(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")):
            harness.test_s8_stamp_roundtrip_isolated()
        assert harness.FAILURES == 0

    def test_nonzero_exit_fails(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="err", stderr="")):
            harness.test_s8_stamp_roundtrip_isolated()
        assert harness.FAILURES == 1


class TestS10DomainsFingerprint:
    def test_helper_via_powershell(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")):
            harness.test_s10_domains_fingerprint_helper()
        assert harness.FAILURES == 0


class TestS11PostPullTail:
    def test_skips_env_passed(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="[OK]", stderr="")) as run:
            harness.test_s11_post_pull_tail_skips()
        env = run.call_args.kwargs.get("env") or run.call_args[1].get("env")
        assert env is not None
        assert env.get("HERMES_SKIP_DOMAIN_TOOLSETS_ON_POST_PULL") == "1"
        assert harness.FAILURES == 0

    def test_failure_exit(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=3, stdout="", stderr="fail")):
            harness.test_s11_post_pull_tail_skips()
        assert harness.FAILURES == 1


class TestS13PytestSubset:
    def test_mocked_pytest(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="9 passed", stderr="")):
            harness.test_s13_pytest_subset()
        assert harness.FAILURES == 0


class TestMain:
    _ALL_STEPS = (
        "test_s1_repo_artifacts",
        "test_s2_stamp_api_contract",
        "test_s3_post_git_pull_wiring",
        "test_s4_orchestrator_wiring",
        "test_s5_start_hermes_sync_cache",
        "test_s6_launch_profiles",
        "test_s7_powershell_parse",
        "test_s8_stamp_roundtrip_isolated",
        "test_s9_skip_post_pull_on_start",
        "test_s10_domains_fingerprint_helper",
        "test_s11_post_pull_tail_skips",
        "test_s12_start_maintenance_minimal",
        "test_s13_pytest_subset",
        "test_s14_pester_unit",
    )

    def test_returns_zero_when_all_pass(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in self._ALL_STEPS:
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 0

    def test_returns_one_on_failure(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness, "test_s1_repo_artifacts", lambda: harness._step("x", False))
        for name in self._ALL_STEPS[1:]:
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 1


@pytest.mark.e2e
def test_session_maintenance_e2e_harness_runs() -> None:
    proc = subprocess.run(
        [sys.executable, str(HARNESS_PATH)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]
    assert "ALL PASS" in (proc.stdout or "")
