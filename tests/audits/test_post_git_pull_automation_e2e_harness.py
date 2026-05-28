"""Unit tests voor ``audits/PostGitPullAutomationE2E.harness.py``.

Piramide:
  - Unit (hier): helpers + scenario's met mocks (geen live PowerShell/WMI/subprocess-keten)
  - Integratie: ``test_post_git_pull_automation_e2e_harness_runs`` (volledige harness via subprocess)

Conventie: importlib-laden zoals ``tests/audits/test_institutional_pipeline_e2e_harness.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "PostGitPullAutomationE2E.harness.py"


@contextmanager
def _fake_temp_directory(root: Path) -> Iterator[str]:
    root.mkdir(parents=True, exist_ok=True)
    yield str(root)


def _patch_harness_tempdir(harness: ModuleType, monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(
        harness.tempfile,
        "TemporaryDirectory",
        lambda: _fake_temp_directory(root),
    )


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("post_git_pull_automation_e2e_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    assert HARNESS_PATH.is_file(), "PostGitPullAutomationE2E.harness.py ontbreekt"
    return _load_harness()


@pytest.fixture(autouse=True)
def _reset_harness_counters(harness: ModuleType) -> None:
    harness.FAILURES = 0
    harness.STEP = 0
    yield
    harness.FAILURES = 0
    harness.STEP = 0


# ---------------------------------------------------------------------------
# _step
# ---------------------------------------------------------------------------


class TestStep:
    def test_ok_increments_step_only(self, harness: ModuleType) -> None:
        harness._step("naam", True, "detail")
        assert harness.STEP == 1
        assert harness.FAILURES == 0

    def test_fail_increments_failures(self, harness: ModuleType) -> None:
        harness._step("naam", False, "fout")
        assert harness.STEP == 1
        assert harness.FAILURES == 1

    def test_empty_detail(self, harness: ModuleType) -> None:
        harness._step("zonder-detail", True)
        assert harness.STEP == 1


# ---------------------------------------------------------------------------
# _read
# ---------------------------------------------------------------------------


class TestRead:
    def test_reads_existing_file(self, harness: ModuleType) -> None:
        text = harness._read("PULL_HERMES.bat")
        assert "POST_GIT_PULL" in text

    def test_missing_file_raises(self, harness: ModuleType) -> None:
        with pytest.raises(FileNotFoundError):
            harness._read("__definitely_missing_post_pull_e2e__.bat")


# ---------------------------------------------------------------------------
# _audit_python
# ---------------------------------------------------------------------------


class TestAuditPython:
    def test_hermes_audit_python_env_when_file_exists(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        py = tmp_path / "custom-python.exe"
        py.write_text("", encoding="utf-8")
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(py))
        assert harness._audit_python() == str(py)

    def test_ignores_invalid_hermes_audit_python_env(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(REPO / "__no_such_python__.exe"))
        result = harness._audit_python()
        assert result  # fallback naar sys.executable of miniconda

    def test_prefers_miniconda_when_present(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("HERMES_AUDIT_PYTHON", raising=False)
        fake_miniconda = tmp_path / "miniconda3" / "envs" / "hermes-env" / "python.exe"
        fake_miniconda.parent.mkdir(parents=True)
        fake_miniconda.write_text("", encoding="utf-8")
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        assert harness._audit_python() == str(fake_miniconda)

    def test_falls_back_to_sys_executable(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("HERMES_AUDIT_PYTHON", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "no_conda"))
        assert harness._audit_python() == sys.executable


# ---------------------------------------------------------------------------
# _powershell_file / _parse_ps1
# ---------------------------------------------------------------------------


class TestPowerShellHelpers:
    def test_powershell_file_invokes_subprocess(self, harness: ModuleType) -> None:
        script = REPO / "windows/scripts/Invoke-PostGitPullTrustOutcome.ps1"
        proc = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=proc) as run:
            result = harness._powershell_file(script, "-TrustExitCode", "0")
        assert result.returncode == 0
        args, kwargs = run.call_args
        assert args[0][0] == "powershell"
        assert "-File" in args[0]
        assert str(script) in args[0]
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"

    def test_powershell_file_merges_env(self, harness: ModuleType) -> None:
        script = REPO / "windows/scripts/Get-RagSourceReadiness.ps1"
        with patch("subprocess.run", return_value=MagicMock(returncode=2)) as run:
            harness._powershell_file(script, env={"USERPROFILE": "/tmp/e2e"})
        env_passed = run.call_args.kwargs["env"]
        assert env_passed["USERPROFILE"] == "/tmp/e2e"

    def test_powershell_file_timeout_propagates(self, harness: ModuleType) -> None:
        script = REPO / "windows/scripts/Get-RagSourceReadiness.ps1"
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("powershell", 60)):
            with pytest.raises(subprocess.TimeoutExpired):
                harness._powershell_file(script, timeout=60)

    def test_parse_ps1_true_on_exit_zero(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            assert harness._parse_ps1(REPO / "windows/stop_other_hermes_processes.ps1") is True

    def test_parse_ps1_false_on_exit_nonzero(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="parse error")):
            assert harness._parse_ps1(REPO / "windows/stop_other_hermes_processes.ps1") is False

    def test_parse_ps1_escapes_single_quotes_in_path(self, harness: ModuleType) -> None:
        fake = REPO / "windows" / "test'script.ps1"
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as run:
            harness._parse_ps1(fake)
        cmd = run.call_args.args[0][-1]
        assert "test''script.ps1" in cmd


# ---------------------------------------------------------------------------
# P1 repo artifacts
# ---------------------------------------------------------------------------


class TestP1RepoArtifacts:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p1_repo_artifacts()
        assert harness.FAILURES == 0
        assert harness.STEP == 1

    def test_missing_artifact_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_repo = REPO / "_nonexistent_post_pull_repo_for_unit_test"
        monkeypatch.setattr(harness, "REPO", fake_repo)
        harness.test_p1_repo_artifacts()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# P2 POST_GIT_PULL wiring
# ---------------------------------------------------------------------------


class TestP2PostGitPullWiring:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p2_post_git_pull_wiring()
        assert harness.FAILURES == 0

    def test_missing_skip_relaunch_flag_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        bat = harness._read("windows/POST_GIT_PULL.bat").replace("-SkipRelaunch", "")
        monkeypatch.setattr(harness, "_read", lambda rel: bat if "POST_GIT_PULL" in rel else harness._read(rel))
        harness.test_p2_post_git_pull_wiring()
        assert harness.FAILURES == 1

    def test_missing_merge_head_guard_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        bat = harness._read("windows/POST_GIT_PULL.bat").replace("MERGE_HEAD", "")
        monkeypatch.setattr(harness, "_read", lambda rel: bat)
        harness.test_p2_post_git_pull_wiring()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# P3 PULL_HERMES chain
# ---------------------------------------------------------------------------


class TestP3PullHermesChain:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p3_pull_hermes_chain()
        assert harness.FAILURES == 0

    def test_missing_post_git_pull_call_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        pull = harness._read("PULL_HERMES.bat").replace("POST_GIT_PULL.bat", "")
        monkeypatch.setattr(harness, "_read", lambda rel: pull)
        harness.test_p3_pull_hermes_chain()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# P4–P6 contract (static wiring)
# ---------------------------------------------------------------------------


class TestP4RelaunchContract:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p4_relaunch_script_contract()
        assert harness.FAILURES == 0

    def test_missing_pip_exit_check_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        ps1 = harness._read("windows/scripts/Invoke-HermesPostPullRelaunch.ps1").replace(
            "LASTEXITCODE -ne 0", ""
        )
        monkeypatch.setattr(harness, "_read", lambda rel: ps1)
        harness.test_p4_relaunch_script_contract()
        assert harness.FAILURES == 1


class TestP5StopScriptContract:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p5_stop_script_contract()
        assert harness.FAILURES == 0

    def test_missing_wmi_filter_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        stop = harness._read("windows/stop_other_hermes_processes.ps1").replace("python.exe", "")
        monkeypatch.setattr(harness, "_read", lambda rel: stop)
        harness.test_p5_stop_script_contract()
        assert harness.FAILURES == 1


class TestP6UpstreamPostMerge:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p6_upstream_post_merge_relaunch()
        assert harness.FAILURES == 0

    def test_missing_keep_pid_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        merge = harness._read("windows/scripts/Invoke-UpstreamPostMerge.ps1").replace("-KeepPid $PID", "")
        monkeypatch.setattr(harness, "_read", lambda rel: merge)
        harness.test_p6_upstream_post_merge_relaunch()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# P7 PowerShell parse
# ---------------------------------------------------------------------------


class TestP7PowerShellParse:
    def test_all_scripts_parse(self, harness: ModuleType) -> None:
        harness.test_p7_powershell_parse()
        assert harness.FAILURES == 0

    def test_one_bad_script_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _parse(path: Path) -> bool:
            return "TrustOutcome" not in path.name

        monkeypatch.setattr(harness, "_parse_ps1", _parse)
        harness.test_p7_powershell_parse()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# P8 skip relaunch
# ---------------------------------------------------------------------------


class TestP8SkipRelaunch:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="Relaunch overgeslagen", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p8_skip_relaunch_env()
        assert harness.FAILURES == 0

    def test_nonzero_exit_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="Relaunch overgeslagen", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p8_skip_relaunch_env()
        assert harness.FAILURES == 1

    def test_missing_overgeslagen_text_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="skipped", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p8_skip_relaunch_env()
        assert harness.FAILURES == 1

    def test_passes_skip_env_to_powershell(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="overgeslagen", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc) as ps:
            harness.test_p8_skip_relaunch_env()
        _, kwargs = ps.call_args
        assert kwargs["env"]["HERMES_SKIP_RELAUNCH_AFTER_PULL"] == "1"


# ---------------------------------------------------------------------------
# P9 invalid RepoRoot
# ---------------------------------------------------------------------------


class TestP9InvalidRepoRoot:
    def test_nonzero_exit_passes(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="FAIL Ongeldig RepoRoot")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p9_invalid_repo_root()
        assert harness.FAILURES == 0

    def test_zero_exit_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p9_invalid_repo_root()
        assert harness.FAILURES == 1

    def test_clears_skip_env_for_probe(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc) as ps:
            harness.test_p9_invalid_repo_root()
        env = ps.call_args.kwargs["env"]
        assert env.get("HERMES_SKIP_RELAUNCH_AFTER_PULL") == "0"

    def test_uses_nonexistent_nested_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc) as ps:
            harness.test_p9_invalid_repo_root()
        repo_arg = ps.call_args.args[2]
        assert "_e2e_post_pull_bogus_nested" in repo_arg


# ---------------------------------------------------------------------------
# P10 / P11 trust outcome
# ---------------------------------------------------------------------------


class TestP10TrustOutcomeSuccess:
    def test_happy_path(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "trust_ok"
        pending = root / "LocalAppData" / "hermes" / "pending_trust_runtime.json"
        _patch_harness_tempdir(harness, monkeypatch, root)

        def _fake_ps(*_args: object, **_kwargs: object) -> MagicMock:
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text(json.dumps({"status": "required"}), encoding="utf-8")
            pending.unlink(missing_ok=True)
            return MagicMock(returncode=0, stdout="Trust runtime gesynchroniseerd", stderr="")

        with patch.object(harness, "_powershell_file", side_effect=_fake_ps):
            harness.test_p10_trust_outcome_success()
        assert harness.FAILURES == 0
        assert not pending.exists()

    def test_nonzero_exit_fails(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_harness_tempdir(harness, monkeypatch, tmp_path / "trust_fail")
        proc = MagicMock(returncode=5, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p10_trust_outcome_success()
        assert harness.FAILURES == 1

    def test_trust_exit_code_zero_argument(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "trust_args"
        _patch_harness_tempdir(harness, monkeypatch, root)
        proc = MagicMock(returncode=0, stdout="", stderr="")

        with patch.object(harness, "_powershell_file", return_value=proc) as ps:
            harness.test_p10_trust_outcome_success()
        assert "-TrustExitCode" in ps.call_args.args
        assert "0" in ps.call_args.args


class TestP11TrustOutcomeFailure:
    def test_happy_path(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "trust_pending"
        pending = root / "LocalAppData" / "hermes" / "pending_trust_runtime.json"
        _patch_harness_tempdir(harness, monkeypatch, root)

        def _fake_ps(*_args: object, **_kwargs: object) -> MagicMock:
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text(
                json.dumps({"status": "required", "source": "POST_GIT_PULL"}),
                encoding="utf-8",
            )
            return MagicMock(returncode=5, stdout="pending trust", stderr="")

        with patch.object(harness, "_powershell_file", side_effect=_fake_ps):
            harness.test_p11_trust_outcome_failure()
        assert harness.FAILURES == 0

    def test_wrong_exit_code_fails(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_harness_tempdir(harness, monkeypatch, tmp_path / "trust_wrong_exit")
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p11_trust_outcome_failure()
        assert harness.FAILURES == 1

    def test_missing_pending_file_fails(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Trust FAIL zonder geschreven pending JSON moet falen."""
        _patch_harness_tempdir(harness, monkeypatch, tmp_path / "trust_no_file")
        proc = MagicMock(returncode=5, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p11_trust_outcome_failure()
        assert harness.FAILURES == 1

    def test_wrong_pending_source_fails(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "trust_bad_source"
        pending = root / "LocalAppData" / "hermes" / "pending_trust_runtime.json"
        _patch_harness_tempdir(harness, monkeypatch, root)

        def _fake_ps(*_args: object, **_kwargs: object) -> MagicMock:
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text(
                json.dumps({"status": "required", "source": "UPDATE_HERMES"}),
                encoding="utf-8",
            )
            return MagicMock(returncode=5, stdout="", stderr="")

        with patch.object(harness, "_powershell_file", side_effect=_fake_ps):
            harness.test_p11_trust_outcome_failure()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# P12 RAG readiness
# ---------------------------------------------------------------------------


class TestP12RagReadiness:
    def test_exit_two_passes(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=2, stdout="Geen bronbestanden", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p12_rag_readiness_empty()
        assert harness.FAILURES == 0

    def test_exit_zero_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc):
            harness.test_p12_rag_readiness_empty()
        assert harness.FAILURES == 1

    def test_isolates_userprofile(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=2, stdout="", stderr="")
        with patch.object(harness, "_powershell_file", return_value=proc) as ps:
            harness.test_p12_rag_readiness_empty()
        assert "USERPROFILE" in ps.call_args.kwargs["env"]


# ---------------------------------------------------------------------------
# P13 pytest subset
# ---------------------------------------------------------------------------


class TestP13PytestSubset:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="9 passed", stderr="")
        with patch("subprocess.run", return_value=proc):
            with patch.object(harness, "_audit_python", return_value=sys.executable):
                harness.test_p13_pytest_subset()
        assert harness.FAILURES == 0

    def test_pytest_failure_fails_step(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="FAILED")
        with patch("subprocess.run", return_value=proc):
            with patch.object(harness, "_audit_python", return_value=sys.executable):
                harness.test_p13_pytest_subset()
        assert harness.FAILURES == 1

    def test_invokes_expected_test_paths(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=proc) as run:
            with patch.object(harness, "_audit_python", return_value="/fake/python"):
                harness.test_p13_pytest_subset()
        cmd = run.call_args.args[0]
        assert cmd[0] == "/fake/python"
        assert "-m" in cmd and "pytest" in cmd
        joined = " ".join(cmd)
        assert "test_post_git_pull_args.py" in joined
        assert "test_cli_post_sync_new_chat.py" in joined


# ---------------------------------------------------------------------------
# P14 CLI hook
# ---------------------------------------------------------------------------


class TestP14CliInitHook:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_p14_cli_init_hook()
        assert harness.FAILURES == 0

    def test_missing_hook_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        cli = harness._read("cli.py").replace("_apply_post_sync_new_chat_notice", "")
        monkeypatch.setattr(harness, "_read", lambda rel: cli if rel == "cli.py" else harness._read(rel))
        harness.test_p14_cli_init_hook()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# PS1_SCRIPTS constant
# ---------------------------------------------------------------------------


class TestPs1ScriptsConstant:
    def test_lists_four_post_pull_scripts(self, harness: ModuleType) -> None:
        assert len(harness.PS1_SCRIPTS) == 4
        assert any("PostPullRelaunch" in s for s in harness.PS1_SCRIPTS)
        assert any("stop_other_hermes" in s for s in harness.PS1_SCRIPTS)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_returns_zero_when_all_pass(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in (
            "test_p1_repo_artifacts",
            "test_p2_post_git_pull_wiring",
            "test_p3_pull_hermes_chain",
            "test_p4_relaunch_script_contract",
            "test_p5_stop_script_contract",
            "test_p6_upstream_post_merge_relaunch",
            "test_p7_powershell_parse",
            "test_p8_skip_relaunch_env",
            "test_p9_invalid_repo_root",
            "test_p10_trust_outcome_success",
            "test_p11_trust_outcome_failure",
            "test_p12_rag_readiness_empty",
            "test_p13_pytest_subset",
            "test_p14_cli_init_hook",
        ):
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 0

    def test_returns_one_on_failure(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fail() -> None:
            harness._step("forced", False)

        monkeypatch.setattr(harness, "test_p1_repo_artifacts", _fail)
        for name in (
            "test_p2_post_git_pull_wiring",
            "test_p3_pull_hermes_chain",
            "test_p4_relaunch_script_contract",
            "test_p5_stop_script_contract",
            "test_p6_upstream_post_merge_relaunch",
            "test_p7_powershell_parse",
            "test_p8_skip_relaunch_env",
            "test_p9_invalid_repo_root",
            "test_p10_trust_outcome_success",
            "test_p11_trust_outcome_failure",
            "test_p12_rag_readiness_empty",
            "test_p13_pytest_subset",
            "test_p14_cli_init_hook",
        ):
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 1
        assert harness.FAILURES >= 1


# ---------------------------------------------------------------------------
# Integratie (subprocess) — gemarkeerd e2e
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_post_git_pull_automation_e2e_harness_runs() -> None:
    """Volledige audits/PostGitPullAutomationE2E.harness.py."""
    proc = subprocess.run(
        [sys.executable, str(HARNESS_PATH)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]
    assert "ALL PASS" in (proc.stdout or "")
