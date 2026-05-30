"""Unit tests voor ``audits/LegalProductionE2E.harness.py`` (mocks, geen live PS1-keten)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "LegalProductionE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("legal_production_e2e_harness", HARNESS_PATH)
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


def _ok_proc(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail_proc(stderr: str = "error") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class TestStep:
    def test_ok_increments_step_only(self, harness: ModuleType) -> None:
        harness._step("ok", True, "detail")
        assert harness.STEP == 1 and harness.FAILURES == 0

    def test_fail_increments_failures(self, harness: ModuleType) -> None:
        harness._step("bad", False, "x")
        assert harness.FAILURES == 1


class TestAuditPython:
    def test_prefers_hermes_audit_python_env(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        py = tmp_path / "custom-python.exe"
        py.write_text("", encoding="utf-8")
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(py))
        assert harness._audit_python() == str(py)

    def test_invalid_env_falls_back_to_executable(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(REPO / "__missing__.exe"))
        monkeypatch.setenv("USERPROFILE", str(REPO / "__no_conda__"))
        assert harness._audit_python() == sys.executable


class TestRunPy:
    def test_run_py_uses_repo_cwd(self, harness: ModuleType) -> None:
        with patch("subprocess.run", return_value=_ok_proc()) as run:
            harness._run_py(["-c", "print(1)"])
        assert run.call_args.kwargs["cwd"] == str(REPO)

    def test_run_py_timeout_propagates(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("py", 10)):
            with pytest.raises(subprocess.TimeoutExpired):
                harness._run_py(["-c", "pass"], timeout=10)


class TestRunPs1:
    def test_run_ps1_builds_powershell_command(self, harness: ModuleType) -> None:
        script = REPO / "windows/scripts/ensure_legal_active_matters.ps1"
        with patch("subprocess.run", return_value=_ok_proc()) as run:
            harness._run_ps1("windows/scripts/ensure_legal_active_matters.ps1", "-Quiet")
        cmd = run.call_args[0][0]
        assert "powershell" in cmd[0].lower()
        assert str(script) in cmd


class TestMainHappyPath:
    def test_main_success_all_external_mocked(self, harness: ModuleType) -> None:
        with (
            patch.object(harness, "_run_py", return_value=_ok_proc("[OK]\n")),
            patch.object(harness, "_run_ps1", return_value=_ok_proc()),
        ):
            assert harness.main() == 0
        assert harness.FAILURES == 0

    def test_main_repo_artifacts_fail_when_paths_missing(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harness, "REQUIRED_PATHS", ("__definitely_missing__.md",))
        with patch.object(harness, "_run_py", return_value=_ok_proc()):
            with patch.object(harness, "_run_ps1", return_value=_ok_proc()):
                assert harness.main() == 1


class TestMainNegativeScenarios:
    def test_parity_failure_without_fix_still_counts(
        self, harness: ModuleType,
    ) -> None:
        calls = {"n": 0}

        def fake_run_py(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls["n"] += 1
            if "verify_legal_lens_parity" in " ".join(args):
                return _fail_proc("mismatch")
            if "sync_legal_lens" in " ".join(args):
                return _ok_proc()
            if "pytest" in " ".join(args):
                return _ok_proc("28 passed")
            return _ok_proc()

        with (
            patch.object(harness, "_run_py", side_effect=fake_run_py),
            patch.object(harness, "_run_ps1", return_value=_ok_proc()),
        ):
            code = harness.main()
        assert code == 1

    def test_pytest_bundle_failure(self, harness: ModuleType) -> None:
        def fake_run_py(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            if "pytest" in " ".join(args):
                return _fail_proc("FAILED")
            return _ok_proc()

        with (
            patch.object(harness, "_run_py", side_effect=fake_run_py),
            patch.object(harness, "_run_ps1", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_verify_runtime_strict_failure(self, harness: ModuleType) -> None:
        with (
            patch.object(harness, "_run_py", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1", return_value=_fail_proc("strict fail")),
        ):
            assert harness.main() == 1

    def test_slash_import_failure_recorded(self, harness: ModuleType) -> None:
        with (
            patch.object(harness, "_run_py", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1", return_value=_ok_proc()),
            patch(
                "hermes_cli.commands.resolve_command",
                side_effect=ImportError("broken"),
            ),
        ):
            assert harness.main() == 1


class TestParityRepairPath:
    def test_parity_all_triggers_sync_on_first_fail(self, harness: ModuleType) -> None:
        parity_calls = {"n": 0}

        def fake_run_py(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            arg_s = " ".join(args)
            if "verify_legal_lens_parity" in arg_s and "--all" in arg_s:
                parity_calls["n"] += 1
                return _fail_proc() if parity_calls["n"] == 1 else _ok_proc("[OK]")
            if "sync_legal_lens_table" in arg_s and "--all" in arg_s:
                return _ok_proc()
            if "pytest" in arg_s:
                return _ok_proc("passed")
            return _ok_proc()

        with (
            patch.object(harness, "_run_py", side_effect=fake_run_py),
            patch.object(harness, "_run_ps1", return_value=_ok_proc()),
        ):
            assert harness.main() == 0
        assert parity_calls["n"] >= 2


class TestRequiredPaths:
    def test_all_required_paths_exist_in_repo(self, harness: ModuleType) -> None:
        missing = [p for p in harness.REQUIRED_PATHS if not (REPO / p).is_file()]
        assert not missing, f"Ontbrekend in repo: {missing}"
