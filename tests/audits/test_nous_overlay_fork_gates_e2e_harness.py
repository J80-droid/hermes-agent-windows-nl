"""Unit tests voor ``audits/NousOverlayForkGatesE2E.harness.py``.

Piramide:
  - Unit (hier): helpers + scenario's met mocks (geen live subprocess/PowerShell in E3–E8)
  - Integratie: ``test_nous_overlay_fork_gates_e2e_harness_runs`` (volledige harness)

Conventie: importlib-laden zoals ``tests/audits/test_institutional_pipeline_e2e_harness.py``.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "NousOverlayForkGatesE2E.harness.py"
SYNC_SCRIPT = REPO / "windows" / "scripts" / "sync_profile_toolsets_from_manifest.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("nous_overlay_fork_gates_e2e_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_sync_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_profile_toolsets_ut", SYNC_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    assert HARNESS_PATH.is_file(), "NousOverlayForkGatesE2E.harness.py ontbreekt"
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
# E1 repo artifacts
# ---------------------------------------------------------------------------


class TestE1RepoArtifacts:
    def test_happy_path_all_present(self, harness: ModuleType) -> None:
        harness.test_e1_repo_artefacts()
        assert harness.FAILURES == 0
        assert harness.STEP == 1

    def test_missing_file_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_root = REPO / "nonexistent_fork_gates_repo"
        monkeypatch.setattr(harness, "REPO_ROOT", fake_root)
        harness.test_e1_repo_artefacts()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E2 argv sanitizer (via sync module)
# ---------------------------------------------------------------------------


class TestE2ArgvSanitizer:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_e2_argv_sanitizer_forms()
        assert harness.FAILURES == 0

    def test_load_sync_module_failure_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom() -> None:
            raise ImportError("sync ontbreekt")

        monkeypatch.setattr(harness, "_load_sync_module", _boom)
        with pytest.raises(ImportError):
            harness.test_e2_argv_sanitizer_forms()

    def test_argv_edge_cases_direct(self) -> None:
        mod = _load_sync_module()
        assert mod._argv_without_hermes_profile_flag(["x.py"]) == ["x.py"]
        assert mod._argv_without_hermes_profile_flag(["x.py", "--other", "v"]) == [
            "x.py",
            "--other",
            "v",
        ]
        # --profile als laatste arg zonder waarde
        assert mod._argv_without_hermes_profile_flag(["x.py", "--check", "--profile"]) == [
            "x.py",
            "--check",
        ]


# ---------------------------------------------------------------------------
# E3 provision subprocess (mock)
# ---------------------------------------------------------------------------


class TestE3ProvisionSubprocess:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="[OK] ict", stderr="")
        with patch("subprocess.run", return_value=proc):
            with patch.object(Path, "is_file", return_value=True):
                harness.test_e3_provision_subprocess_with_profile_flag()
        assert harness.FAILURES == 0

    def test_nonzero_exit_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Profile 'ict' does not exist",
        )
        with patch("subprocess.run", return_value=proc):
            harness.test_e3_provision_subprocess_with_profile_flag()
        assert harness.FAILURES == 1

    def test_missing_config_after_success_exit_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=proc):
            with patch.object(Path, "is_file", return_value=False):
                harness.test_e3_provision_subprocess_with_profile_flag()
        assert harness.FAILURES == 1

    def test_subprocess_timeout_propagates(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)):
            with pytest.raises(subprocess.TimeoutExpired):
                harness.test_e3_provision_subprocess_with_profile_flag()


# ---------------------------------------------------------------------------
# E4 config get overlay CLI (mock)
# ---------------------------------------------------------------------------


class TestE4ConfigGetOverlay:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="gemini\n", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e4_config_get_overlay_entrypoint()
        assert harness.FAILURES == 0

    def test_invalid_choice_in_stderr_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(
            returncode=2,
            stdout="",
            stderr="invalid choice: 'get' (choose from 'show', 'edit')",
        )
        with patch("subprocess.run", return_value=proc):
            harness.test_e4_config_get_overlay_entrypoint()
        assert harness.FAILURES == 1

    def test_empty_output_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e4_config_get_overlay_entrypoint()
        assert harness.FAILURES == 1

    def test_usage_line_filtered_value_get_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="get\n", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e4_config_get_overlay_entrypoint()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E5 toolset check skip user customized
# ---------------------------------------------------------------------------


class TestE5ToolsetCheckSkip:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_e5_toolset_check_skips_user_customized()
        assert harness.FAILURES == 0

    def test_sync_profile_returns_false_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_mod = MagicMock()
        fake_mod._load_manifest.return_value = {"profiles": {"legal": {}}}
        fake_mod._sync_profile.return_value = False
        monkeypatch.setattr(harness, "_load_sync_module", lambda: fake_mod)
        harness.test_e5_toolset_check_skips_user_customized()
        assert harness.FAILURES == 1

    def test_force_manifest_still_checks_drift(self) -> None:
        mod = _load_sync_module()
        with tempfile.TemporaryDirectory() as tmp:
            hermes = Path(tmp) / "hermes"
            prof = hermes / "profiles" / "legal"
            prof.mkdir(parents=True)
            cfg = {
                "platform_toolsets": {
                    "cli": ["mcp"],
                    "_user_customized": {"cli": True},
                }
            }
            (prof / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
            manifest = mod._load_manifest(REPO)
            spec = manifest["profiles"]["legal"]
            assert mod._sync_profile(
                hermes, "legal", spec, dry_run=False, check=True, force_manifest=True
            ) is False


# ---------------------------------------------------------------------------
# E6 argparse pytest subprocess (mock)
# ---------------------------------------------------------------------------


class TestE6ArgparsePytest:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="2 passed", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e6_argparse_config_get_no_duplicate()
        assert harness.FAILURES == 0

    def test_pytest_failure(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="1 failed")
        with patch("subprocess.run", return_value=proc):
            harness.test_e6_argparse_config_get_no_duplicate()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E7 legal USER stale domain (mock subprocess + real temp file)
# ---------------------------------------------------------------------------


class TestE7LegalUserStale:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="OK", stderr="")

        def _fake_run(*_a: object, **_k: object) -> MagicMock:
            hermes_root = _k.get("env", {}).get("HERMES_HOME")
            if hermes_root:
                user = Path(hermes_root) / "profiles" / "legal" / "memories" / "USER.md"
                user.parent.mkdir(parents=True, exist_ok=True)
                user.write_text(
                    "trust\n§\nLegal proactief (NL): x\n§\nLegal triggers — y\n",
                    encoding="utf-8",
                )
            return proc

        with patch("subprocess.run", side_effect=_fake_run):
            harness.test_e7_legal_user_stale_domain_replaced()
        assert harness.FAILURES == 0

    def test_stale_block_remains_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")

        def _fake_run(*_a: object, **_k: object) -> MagicMock:
            hermes_root = _k.get("env", {}).get("HERMES_HOME")
            if hermes_root:
                user = Path(hermes_root) / "profiles" / "legal" / "memories" / "USER.md"
                user.parent.mkdir(parents=True, exist_ok=True)
                user.write_text(
                    "Parallelle invalshoeken. Oud blok zonder Legal proactief triggers.\n",
                    encoding="utf-8",
                )
            return proc

        with patch("subprocess.run", side_effect=_fake_run):
            harness.test_e7_legal_user_stale_domain_replaced()
        assert harness.FAILURES == 1

    def test_powershell_nonzero_exit_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="dedup failed")
        with patch("subprocess.run", return_value=proc):
            harness.test_e7_legal_user_stale_domain_replaced()
        assert harness.FAILURES == 1

    def test_missing_legal_triggers_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")

        def _fake_run(*_a: object, **_k: object) -> MagicMock:
            hermes_root = _k.get("env", {}).get("HERMES_HOME")
            if hermes_root:
                user = Path(hermes_root) / "profiles" / "legal" / "memories" / "USER.md"
                user.parent.mkdir(parents=True, exist_ok=True)
                user.write_text("Legal proactief only\n", encoding="utf-8")
            return proc

        with patch("subprocess.run", side_effect=_fake_run):
            harness.test_e7_legal_user_stale_domain_replaced()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E8 toolset runtime env guard (mock)
# ---------------------------------------------------------------------------


class TestE8ToolsetRuntimeEnvGuard:
    def test_happy_path_missing_env(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="[FAIL] ontbrekende env: HERMES_TOOLSET_E2E_REPO", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e8_toolset_runtime_env_guard()
        assert harness.FAILURES == 0

    def test_wrong_exit_code_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="[OK] runtime", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e8_toolset_runtime_env_guard()
        assert harness.FAILURES == 1

    def test_missing_message_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="other error", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e8_toolset_runtime_env_guard()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_returns_zero_when_all_pass(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in (
            "test_e1_repo_artefacts",
            "test_e2_argv_sanitizer_forms",
            "test_e3_provision_subprocess_with_profile_flag",
            "test_e4_config_get_overlay_entrypoint",
            "test_e5_toolset_check_skips_user_customized",
            "test_e6_argparse_config_get_no_duplicate",
            "test_e7_legal_user_stale_domain_replaced",
            "test_e8_toolset_runtime_env_guard",
        ):
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 0

    def test_returns_one_on_failure(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fail() -> None:
            harness._step("forced", False)

        monkeypatch.setattr(harness, "test_e1_repo_artefacts", _fail)
        for name in (
            "test_e2_argv_sanitizer_forms",
            "test_e3_provision_subprocess_with_profile_flag",
            "test_e4_config_get_overlay_entrypoint",
            "test_e5_toolset_check_skips_user_customized",
            "test_e6_argparse_config_get_no_duplicate",
            "test_e7_legal_user_stale_domain_replaced",
            "test_e8_toolset_runtime_env_guard",
        ):
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 1
        assert harness.FAILURES >= 1


# ---------------------------------------------------------------------------
# Integratie (subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_nous_overlay_fork_gates_e2e_harness_runs() -> None:
    """Volledige audits/NousOverlayForkGatesE2E.harness.py."""
    proc = subprocess.run(
        [sys.executable, str(HARNESS_PATH)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]
    assert "PASS" in (proc.stdout or "")
