"""Unit tests voor ``audits/LegalMemoryLanguageLayersE2E.harness.py`` (mocks, geen live PS1-keten)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "LegalMemoryLanguageLayersE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "legal_memory_language_layers_e2e_harness", HARNESS_PATH
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


def _valid_reads() -> dict[str, str]:
    return {
        "docs/templates/MEMORY_CANONICAL_SEED.md": (
            "Taal- en triggerlagen\nGeen i18n\n| Trust |\n| Legal triggers |\n"
            "## legal USER.md entries\n"
            "```\nLegal proactief (NL):\n```\n"
            "```\nLegal triggers — voorbeeldvragen J. (NL):\n```\n"
            "```\nLegal taallaag (NL):\n```\n"
            "## USER.md entries\n"
            "J. demands absolute trust, zero babysitting\n"
        ),
        "docs/templates/SOUL_LEGAL_DOMAIN.md": (
            "USER.md (trust EN + legal triggers NL)\nSOUL prevaleert\n"
        ),
        "docs/LEGAL_DOMAIN_ARCHITECTURE.md": (
            "## Taal- en triggerlagen\nSOUL prevaleert\nUSER.nl.md\n"
        ),
    }


def _patch_reads(harness: ModuleType, overrides: dict[str, str] | None = None) -> MagicMock:
    base = _valid_reads()
    if overrides:
        base.update(overrides)

    def reader(rel: str) -> str | None:
        if rel in base:
            return base[rel]
        return (REPO / rel).read_text(encoding="utf-8") if (REPO / rel).is_file() else None

    return patch.object(harness, "_read", side_effect=reader)


class TestRepoRoot:
    def test_repo_root_prefers_hermes_repo_root_env(
        self, harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        other = tmp_path / "alt-repo"
        other.mkdir()
        (other / "marker.txt").write_text("x", encoding="utf-8")
        monkeypatch.setenv("HERMES_REPO_ROOT", f'"{other}"')
        assert harness._repo_root() == other.resolve()

    def test_repo_root_strips_whitespace_env(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HERMES_REPO_ROOT", f"  {REPO}  ")
        assert harness._repo_root() == REPO.resolve()

    def test_repo_root_empty_env_falls_back_to_harness_parent(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HERMES_REPO_ROOT", raising=False)
        root = harness._repo_root()
        assert root == HARNESS_PATH.resolve().parents[1]
        assert (root / "audits" / "LegalMemoryLanguageLayersE2E.harness.py").is_file()


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

    def test_empty_detail_omits_suffix(
        self, harness: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        harness._step("no-detail", True)
        out = capsys.readouterr().out
        assert "[OK]" in out
        assert " -- " not in out.split("no-detail")[1].split("\n")[0]

    def test_fail_writes_stderr(
        self, harness: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        harness._step("broken", False, "reason")
        err = capsys.readouterr().err
        assert "[FAIL]" in err
        assert "broken" in err
        assert "reason" in err


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


class TestRunPy:
    def test_run_py_uses_repo_cwd_and_audit_interpreter(self, harness: ModuleType) -> None:
        with (
            patch.object(harness, "_audit_python", return_value="C:\\fake\\python.exe"),
            patch("subprocess.run", return_value=_ok_proc()) as run,
        ):
            harness._run_py(["-m", "pytest", "-q"], timeout=99)
        cmd, kwargs = run.call_args[0][0], run.call_args.kwargs
        assert cmd[0] == "C:\\fake\\python.exe"
        assert kwargs["cwd"] == str(harness.REPO)
        assert kwargs["timeout"] == 99
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"

    def test_run_py_timeout_propagates(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("py", 10)):
            with pytest.raises(subprocess.TimeoutExpired):
                harness._run_py(["-c", "pass"], timeout=10)

    def test_run_py_oserror_propagates(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=OSError("spawn failed")):
            with pytest.raises(OSError, match="spawn failed"):
                harness._run_py(["-c", "pass"])


class TestRunPySafe:
    def test_timeout_returns_fail_proc(self, harness: ModuleType) -> None:
        with patch.object(harness, "_run_py", side_effect=subprocess.TimeoutExpired("py", 10)):
            proc = harness._run_py_safe(["-c", "pass"], timeout=10)
        assert proc.returncode == 1
        assert "timeout" in (proc.stderr or "").lower()

    def test_oserror_returns_fail_proc(self, harness: ModuleType) -> None:
        with patch.object(harness, "_run_py", side_effect=OSError("no python")):
            proc = harness._run_py_safe(["-c", "pass"])
        assert proc.returncode == 1
        assert "no python" in (proc.stderr or "")


class TestRunPs1Safe:
    def test_missing_script_returns_fail_without_subprocess(self, harness: ModuleType) -> None:
        proc = harness._run_ps1_safe("__unit_missing_layers_core__.ps1")
        assert proc.returncode == 1
        assert "ontbreekt" in (proc.stderr or "")

    def test_builds_powershell_command(self, harness: ModuleType) -> None:
        script = REPO / "audits" / "LegalMemoryLanguageLayersE2E.core.ps1"
        with patch("subprocess.run", return_value=_ok_proc()) as run:
            harness._run_ps1_safe(
                "audits/LegalMemoryLanguageLayersE2E.core.ps1",
                "-RepoRoot",
                str(REPO),
                timeout=90,
            )
        cmd = run.call_args[0][0]
        kwargs = run.call_args.kwargs
        assert cmd[0].lower() == "powershell"
        assert "-ExecutionPolicy" in cmd
        assert "Bypass" in cmd
        assert str(script) in cmd
        assert kwargs["cwd"] == str(harness.REPO)
        assert kwargs["timeout"] == 90

    def test_timeout_returns_fail_proc(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["pwsh"], timeout=5)):
            proc = harness._run_ps1_safe(
                "audits/LegalMemoryLanguageLayersE2E.core.ps1",
                timeout=5,
            )
        assert proc.returncode == 1
        assert "timeout" in (proc.stderr or "").lower()

    def test_oserror_returns_fail_proc(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=OSError("powershell blocked")):
            proc = harness._run_ps1_safe("audits/LegalMemoryLanguageLayersE2E.core.ps1")
        assert proc.returncode == 1
        assert "powershell blocked" in (proc.stderr or "")


class TestRead:
    def test_read_existing_repo_file(self, harness: ModuleType) -> None:
        text = harness._read("docs/templates/MEMORY_CANONICAL_SEED.md")
        assert text is not None
        assert "legal USER.md entries" in text

    def test_read_missing_file_returns_none(self, harness: ModuleType) -> None:
        assert harness._read("__unit_test_missing_layers__.md") is None


class TestMainHappyPath:
    def test_main_success_all_external_mocked(self, harness: ModuleType) -> None:
        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc("[OK] Parity\n")),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc("ALL PASS")),
        ):
            assert harness.main() == 0
        assert harness.FAILURES == 0
        assert harness.STEP == 9

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
        assert "Legal Memory Language Layers E2E" in out
        assert "ALL PASS" in out


class TestMainNegativeScenarios:
    def test_repo_artifacts_fail_when_required_path_missing(
        self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            harness,
            "REQUIRED_PATHS",
            ("__definitely_missing_language_layers__.md",),
        )
        with (
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1
        assert harness.FAILURES >= 1

    def test_seed_missing_taal_lagen_table(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "docs/templates/MEMORY_CANONICAL_SEED.md": (
                        "Geen i18n\n## legal USER.md entries\n```\nLegal proactief (NL):\n```\n"
                        "```\nLegal triggers\n```\n```\nLegal taallaag\n```\n"
                        "## USER.md entries\nJ. demands absolute trust\n"
                    ),
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1
        assert harness.FAILURES >= 1

    def test_seed_insufficient_legal_fences(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "docs/templates/MEMORY_CANONICAL_SEED.md": (
                        "Taal- en triggerlagen\nGeen i18n\n| Trust |\n| Legal triggers |\n"
                        "## legal USER.md entries\n```\nLegal proactief (NL):\n```\n"
                        "## USER.md entries\nJ. demands absolute trust\n"
                    ),
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_seed_missing_en_trust_section(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "docs/templates/MEMORY_CANONICAL_SEED.md": (
                        "Taal- en triggerlagen\nGeen i18n\n| Trust |\n| Legal triggers |\n"
                        "## legal USER.md entries\n```\nx\n```\n```\ny\n```\n```\nz\n```\n"
                    ),
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_seed_read_none_fails_multiple_steps(self, harness: ModuleType) -> None:
        with (
            patch.object(harness, "_read", return_value=None),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            code = harness.main()
        assert code == 1
        assert harness.FAILURES >= 4

    def test_soul_missing_user_section(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {"docs/templates/SOUL_LEGAL_DOMAIN.md": "SOUL prevaleert only\n"},
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_architecture_missing_i18n_note(self, harness: ModuleType) -> None:
        with (
            _patch_reads(
                harness,
                {
                    "docs/LEGAL_DOMAIN_ARCHITECTURE.md": (
                        "## Taal- en triggerlagen\nSOUL prevaleert\n"
                    ),
                },
            ),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_lens_parity_failure(self, harness: ModuleType) -> None:
        with (
            _patch_reads(harness),
            patch.object(
                harness,
                "_run_py_safe",
                return_value=_fail_proc("Parity mismatch: 5 vs 0"),
            ),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_pytest_contract_failure(self, harness: ModuleType) -> None:
        call_count = 0

        def fake_run_py(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ok_proc("[OK] Parity")
            return _fail_proc("1 failed")

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", side_effect=fake_run_py),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_core_ps1_failure(self, harness: ModuleType) -> None:
        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc("[OK] Parity")),
            patch.object(harness, "_run_ps1_safe", return_value=_fail_proc("core FAIL")),
        ):
            assert harness.main() == 1

    def test_parity_timeout_still_fails_harness(self, harness: ModuleType) -> None:
        with (
            _patch_reads(harness),
            patch.object(
                harness,
                "_run_py_safe",
                return_value=_fail_proc("timeout after 60s"),
            ),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            assert harness.main() == 1

    def test_run_py_safe_called_for_parity_and_pytest(self, harness: ModuleType) -> None:
        calls: list[list[str]] = []

        def capture_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(list(args))
            return _ok_proc()

        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", side_effect=capture_run),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()),
        ):
            harness.main()

        assert len(calls) == 2
        assert "verify_legal_lens_parity.py" in calls[0][0]
        assert calls[0][-1] == "docs/templates/SOUL_LEGAL_DOMAIN.md"
        assert calls[1][:3] == ["-m", "pytest", "tests/windows/test_legal_memory_language_layers.py"]

    def test_run_ps1_safe_passes_repo_root(self, harness: ModuleType) -> None:
        with (
            _patch_reads(harness),
            patch.object(harness, "_run_py_safe", return_value=_ok_proc()),
            patch.object(harness, "_run_ps1_safe", return_value=_ok_proc()) as run_ps1,
        ):
            harness.main()
        assert run_ps1.called
        assert "-RepoRoot" in run_ps1.call_args[0]
        assert str(harness.REPO) in run_ps1.call_args[0]


class TestRequiredPathsContract:
    def test_required_paths_include_language_layers_artifacts(self, harness: ModuleType) -> None:
        paths = set(harness.REQUIRED_PATHS)
        assert "docs/templates/MEMORY_CANONICAL_SEED.md" in paths
        assert "audits/LegalMemoryLanguageLayersE2E.core.ps1" in paths
        assert "tests/windows/test_legal_memory_language_layers.py" in paths
        assert all((harness.REPO / p).is_file() for p in harness.REQUIRED_PATHS)
