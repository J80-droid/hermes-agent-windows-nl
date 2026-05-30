"""Unit tests voor ``audits/LegalProactiveSparringE2E.harness.py`` (mocks, geen live PS1-keten)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "LegalProactiveSparringE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "legal_proactive_sparring_e2e_harness", HARNESS_PATH
    )
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


def _valid_template_reads() -> dict[str, str]:
    """Minimale inhoud die alle template-contractstappen in main() laat slagen."""
    return {
        "docs/templates/SOUL_LEGAL_DOMAIN.md": (
            "Parallelle invalshoeken\nProactief meedenken\nPushback\n"
            "parallelle invalshoeken\nmandaat\ndisciplinair\n"
            "USER.md (trust EN + legal triggers NL)\nSOUL prevaleert\n"
        ),
        "docs/templates/LEGAL_ACTIVE_MATTERS.example.md": (
            "GCR 2024-00145\nAdjacent checks\n"
        ),
        "docs/templates/MEMORY_CANONICAL_SEED.md": (
            "## legal USER.md entries\nLegal proactief\nLegal triggers\n"
            "voorbeeldvragen\ndisciplinaire maatregel\nLegal taallaag\n"
            "SOUL prevaleert\nTaal- en triggerlagen\nGeen i18n\n"
        ),
        "docs/LEGAL_DOMAIN_ARCHITECTURE.md": (
            "Taal- en triggerlagen\nSOUL prevaleert\n"
        ),
        "docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md": (
            "Parallelle invalshoeken\nSOUL_LEGAL_DOMAIN\n"
        ),
        "windows/scripts/SyncSoulSnippet.psm1": (
            "Repair-SoulDuplicateConfigGovernanceBlocks\n"
            "Export-ModuleMember\n"
            "verwacht 1 Config governance-blok\n"
        ),
        "windows/scripts/sync_profile_memories.ps1": (
            "Test-IsLegalProfileMemoryUserPath\nlegal USER.md\n"
        ),
        "windows/scripts/HermesMemoryMergeCommon.ps1": (
            "[switch]$Optional\nTest-IsLegalProfileMemoryUserPath\n"
        ),
    }


def _patch_reads(harness: ModuleType, overrides: dict[str, str] | None = None) -> MagicMock:
    base = _valid_template_reads()
    if overrides:
        base.update(overrides)

    def fake_read(rel: str) -> str:
        if rel in base:
            return base[rel]
        return (REPO / rel).read_text(encoding="utf-8")

    return patch.object(harness, "_read", side_effect=fake_read)


class TestStep:
    def test_ok_increments_step_only(self, harness: ModuleType) -> None:
        harness._step("ok", True, "detail")
        assert harness.STEP == 1
        assert harness.FAILURES == 0

    def test_fail_increments_failures_and_step(self, harness: ModuleType) -> None:
        harness._step("bad", False, "x")
        assert harness.STEP == 1
        assert harness.FAILURES == 1

    def test_multiple_failures_accumulate(self, harness: ModuleType) -> None:
        harness._step("a", False)
        harness._step("b", False)
        harness._step("c", True)
        assert harness.STEP == 3
        assert harness.FAILURES == 2

    def test_empty_detail_omits_suffix(self, harness: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
        harness._step("no-detail", True)
        out = capsys.readouterr().out
        assert "[OK]" in out
        assert " -- " not in out.split("no-detail")[1].split("\n")[0]


class TestAuditPython:
    def test_prefers_hermes_audit_python_env(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        py = tmp_path / "custom-python.exe"
        py.write_text("", encoding="utf-8")
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(py))
        assert harness._audit_python() == str(py)

    def test_missing_env_file_falls_back(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", str(REPO / "__missing_audit_python__.exe"))
        monkeypatch.setenv("USERPROFILE", str(REPO / "__no_conda_home__"))
        assert harness._audit_python() == sys.executable

    def test_empty_env_ignored(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HERMES_AUDIT_PYTHON", "")
        monkeypatch.setenv("USERPROFILE", str(REPO / "__no_conda_home__"))
        assert harness._audit_python() == sys.executable


class TestRunPySafe:
    def test_run_py_safe_timeout_returns_fail_proc(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("py", 10)):
            proc = harness._run_py_safe(["-c", "pass"], timeout=10)
        assert proc.returncode == 1
        assert "timeout" in (proc.stderr or "").lower()

    def test_run_ps1_safe_missing_script_returns_fail(self, harness: ModuleType) -> None:
        proc = harness._run_ps1_safe("__missing_script__.ps1")
        assert proc.returncode == 1
        assert "ontbreekt" in (proc.stderr or "")


class TestRunPy:
    def test_run_py_uses_repo_cwd_and_audit_interpreter(self, harness: ModuleType) -> None:
        with (
            patch.object(harness, "_audit_python", return_value="C:\\fake\\python.exe"),
            patch("subprocess.run", return_value=_ok_proc()) as run,
        ):
            harness._run_py(["-m", "pytest", "-q"], timeout=99)
        cmd, kwargs = run.call_args[0][0], run.call_args.kwargs
        assert cmd[0] == "C:\\fake\\python.exe"
        assert kwargs["cwd"] == str(REPO)
        assert kwargs["timeout"] == 99
        assert kwargs["text"] is True

    def test_run_py_timeout_propagates(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("py", 10)):
            with pytest.raises(subprocess.TimeoutExpired):
                harness._run_py(["-c", "pass"], timeout=10)

    def test_run_py_subprocess_error_propagates(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=OSError("spawn failed")):
            with pytest.raises(OSError, match="spawn failed"):
                harness._run_py(["-c", "pass"])


class TestRunPs1:
    def test_run_ps1_builds_powershell_command_with_repo_script(self, harness: ModuleType) -> None:
        script = REPO / "audits" / "LegalProactiveSparringE2E.core.ps1"
        with patch("subprocess.run", return_value=_ok_proc()) as run:
            harness._run_ps1(
                "audits/LegalProactiveSparringE2E.core.ps1",
                "-RepoRoot",
                str(REPO),
                timeout=120,
            )
        cmd = run.call_args[0][0]
        kwargs = run.call_args.kwargs
        assert cmd[0].lower() == "powershell"
        assert "-ExecutionPolicy" in cmd
        assert "Bypass" in cmd
        assert str(script) in cmd
        assert "-RepoRoot" in cmd
        assert str(REPO) in cmd
        assert kwargs["cwd"] == str(REPO)
        assert kwargs["timeout"] == 120
        assert kwargs["env"] is not None

    def test_run_ps1_normalizes_forward_slashes(self, harness: ModuleType) -> None:
        rel = "audits/Invoke-LegalProactiveSparringPester.ps1"
        expected = REPO / rel.replace("/", "\\") if "\\" in str(REPO) else REPO / rel
        with patch("subprocess.run", return_value=_ok_proc()) as run:
            harness._run_ps1(rel)
        assert str(expected) in run.call_args[0][0]


class TestRead:
    def test_read_existing_repo_file(self, harness: ModuleType) -> None:
        text = harness._read("docs/templates/SOUL_LEGAL_DOMAIN.md")
        assert text is not None
        assert "Parallelle invalshoeken" in text

    def test_read_missing_file_returns_none(self, harness: ModuleType) -> None:
        assert harness._read("__unit_test_missing_template__.md") is None


class TestMainHappyPath:
    def test_main_success_all_external_mocked(self, harness: ModuleType) -> None:
        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc("12 passed\n")),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc("ALL PASS")),
        ):
            assert harness.main() == 0
        assert harness.FAILURES == 0
        assert harness.STEP == 19

    def test_main_prints_banner_and_success_line(
        self, harness: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 0
        out = capsys.readouterr().out
        assert "Legal Proactive Sparring E2E" in out
        assert "ALL PASS" in out


class TestMainNegativeScenarios:
    def test_repo_artifacts_fail_when_required_path_missing(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            harness,
            "REQUIRED_PATHS",
            ("__definitely_missing_proactive_sparring__.md",),
        )
        with (
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1
        assert harness.FAILURES >= 1

    def test_soul_template_missing_parallelle_section(
        self, harness: ModuleType,
    ) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "docs/templates/SOUL_LEGAL_DOMAIN.md": "Pushback only\nmandaat\ndisciplinair\n",
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            code = harness.main()
        assert code == 1
        assert harness.FAILURES >= 1

    def test_matters_example_missing_adjacent_checks(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {"docs/templates/LEGAL_ACTIVE_MATTERS.example.md": "GCR 2024-00145 only\n"},
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_memory_seed_missing_legal_user_section(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {"docs/templates/MEMORY_CANONICAL_SEED.md": "## USER.md entries\n"},
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_sync_profile_memories_still_uses_extraexisting_fails(
        self, harness: ModuleType,
    ) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "windows/scripts/sync_profile_memories.ps1": (
                        "Test-IsLegalProfileMemoryUserPath\n"
                        "legal USER.md\nExtraExisting\n"
                    ),
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_pytest_contract_failure(self, harness: ModuleType) -> None:
        def fake_run_py(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            if "pytest" in " ".join(args):
                return _fail_proc("FAILED tests/windows/test_legal_meta_contract.py")
            return _ok_proc()

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", side_effect=fake_run_py),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_pester_runner_failure(self, harness: ModuleType) -> None:
        def fake_run_ps1(script_rel: str, *ps_args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
            if "Invoke-LegalProactiveSparringPester" in script_rel:
                return _fail_proc("Pester FailedCount=2")
            return _ok_proc("ALL PASS")

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc("12 passed")),
            patch.object(harness, "_run_ps1_safe", side_effect=fake_run_ps1),
        ):
            assert harness.main() == 1

    def test_core_ps1_failure(self, harness: ModuleType) -> None:
        def fake_run_ps1(script_rel: str, *ps_args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
            if "LegalProactiveSparringE2E.core.ps1" in script_rel:
                return _fail_proc("runtime legal SOUL single config governance -- count=2")
            return _ok_proc()

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", side_effect=fake_run_ps1),
        ):
            assert harness.main() == 1

    def test_multiple_template_and_external_failures_increase_failure_count(
        self, harness: ModuleType,
    ) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "docs/templates/SOUL_LEGAL_DOMAIN.md": "",
                    "docs/templates/MEMORY_CANONICAL_SEED.md": "",
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_fail_proc("pytest fail")),
            patch.object(harness, "_run_ps1_safe", return_value=_fail_proc("core fail")),
        ):
            code = harness.main()
        assert code == 1
        assert harness.FAILURES >= 4

    def test_read_raises_after_artifacts_pass_propagates(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harness, "REQUIRED_PATHS", ())
        with (
            patch.object(harness, "_read", side_effect=FileNotFoundError("gone")),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            with pytest.raises(FileNotFoundError, match="gone"):
                harness.main()


class TestMainExternalInvocation:
    def test_main_calls_pytest_with_expected_target(self, harness: ModuleType) -> None:
        captured: list[list[str]] = []

        def fake_run_py(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured.append(args)
            return _ok_proc("12 passed")

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", side_effect=fake_run_py),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            harness.main()

        pytest_calls = [a for a in captured if "pytest" in " ".join(a)]
        assert len(pytest_calls) == 1
        assert "tests/windows/test_legal_meta_contract.py" in " ".join(pytest_calls[0])

    def test_main_invokes_pester_then_core_in_order(self, harness: ModuleType) -> None:
        order: list[str] = []

        def fake_run_ps1(script_rel: str, *ps_args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
            order.append(script_rel.replace("\\", "/"))
            return _ok_proc()

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", side_effect=fake_run_ps1),
        ):
            harness.main()

        assert order == [
            "audits/Invoke-LegalProactiveSparringPester.ps1",
            "audits/LegalProactiveSparringE2E.core.ps1",
        ]

    def test_core_ps1_receives_repo_root_argument(self, harness: ModuleType) -> None:
        captured_args: list[str] = []

        def fake_run_ps1(script_rel: str, *ps_args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
            if "core.ps1" in script_rel:
                captured_args.extend(ps_args)
            return _ok_proc()

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", side_effect=fake_run_ps1),
        ):
            harness.main()

        assert "-RepoRoot" in captured_args
        assert str(REPO) in captured_args


class TestRequiredPaths:
    def test_all_required_paths_exist_in_repo(self, harness: ModuleType) -> None:
        missing = [p for p in harness.REQUIRED_PATHS if not (REPO / p).is_file()]
        assert not missing, f"Ontbrekend in repo: {missing}"

    def test_required_paths_include_core_and_pester_runner(self, harness: ModuleType) -> None:
        paths = set(harness.REQUIRED_PATHS)
        assert "audits/LegalProactiveSparringE2E.core.ps1" in paths
        assert "docs/templates/SOUL_LEGAL_DOMAIN.md" in paths
        assert "windows/tests/SoulSnippetRepair.Unit.Tests.ps1" in paths

    def test_required_paths_count_stable(self, harness: ModuleType) -> None:
        assert len(harness.REQUIRED_PATHS) == 12


class TestModuleEntrypoint:
    def test_harness_has_main_guard(self) -> None:
        source = HARNESS_PATH.read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in source
        assert "SystemExit(main())" in source

    def test_repo_root_points_at_hermes_agent(self, harness: ModuleType) -> None:
        assert harness.REPO.name == "hermes-agent"
        assert (harness.REPO / "audits" / "LegalProactiveSparringE2E.harness.py").is_file()
