"""Unit tests: Invoke-HermesTierAPostAuditClean / pytest audit helpers (HermesShellCommon.ps1)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COMMON = REPO / "windows" / "HermesShellCommon.ps1"
RUN_AUDITS = REPO / "windows" / "audits" / "RUN_AUDITS.ps1"
SEED_PS = REPO / "windows" / "scripts" / "seed_rag_minimal_fixtures.ps1"
PARALLEL = REPO / "scripts" / "run_tests_parallel.py"


def _ps1_quote(path: Path | str) -> str:
    return str(path).replace("'", "''")


def _run_ps(command: str, *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def common_text() -> str:
    assert COMMON.is_file(), "HermesShellCommon.ps1 ontbreekt"
    return COMMON.read_text(encoding="utf-8")


class TestHermesShellCommonStructure:
    def test_tier_a_clean_functions_present(self, common_text: str) -> None:
        assert "function Invoke-HermesTierAPostAuditClean" in common_text
        assert "function Invoke-HermesTierASrcClean" in common_text
        assert "ValidateSet('Preflight', 'PreOverlay', 'Postflight')" in common_text

    def test_conda_pytest_param_order_before_env_name(self, common_text: str) -> None:
        idx_args = common_text.index("ValueFromRemainingArguments = $true, Position = 1")
        idx_env = common_text.index("[string]$EnvName = 'hermes-env'", idx_args)
        assert idx_args < idx_env

    def test_conda_run_uses_separator(self, common_text: str) -> None:
        assert "'--'" in common_text
        assert "'run', '-n', $EnvName, '--no-capture-output', '--'" in common_text

    def test_audit_pytest_validates_python_path(self, common_text: str) -> None:
        assert "Test-Path -LiteralPath $Python" in common_text
        assert "python niet gevonden" in common_text

    def test_audit_pytest_validates_conda_path(self, common_text: str) -> None:
        assert "Test-Path -LiteralPath $CondaExe" in common_text
        assert "conda niet gevonden" in common_text

    def test_drift_only_on_postflight(self, common_text: str) -> None:
        assert "$Phase -eq 'Postflight'" in common_text
        assert "Test-NousTreeIdentical.ps1" in common_text


class TestRunAuditsWiring:
    def test_skip_tier_a_post_clean_switch(self) -> None:
        text = RUN_AUDITS.read_text(encoding="utf-8")
        assert "SkipTierAPostClean" in text
        assert "Invoke-HermesTierAPostAuditClean" in text
        assert "tier-a-restore-preflight" in text
        assert "tier-a-drift-postflight" in text


class TestSeedRagMinimalFixtures:
    def test_script_rejects_empty_fixture_tree(self, tmp_path: Path) -> None:
        empty_repo = tmp_path / "repo"
        (empty_repo / "fixtures" / "rag_minimal").mkdir(parents=True)
        ps = (
            f"& '{_ps1_quote(SEED_PS)}' -RepoRoot '{_ps1_quote(empty_repo)}' "
            f"-DestRoot '{_ps1_quote(tmp_path / 'dest')}'"
        )
        proc = _run_ps(ps, timeout=60)
        assert proc.returncode == 1
        assert "geen domein-mappen" in (proc.stdout or proc.stderr or "").lower()

    def test_whatif_does_not_write_files(self, tmp_path: Path) -> None:
        dest = tmp_path / "dest"
        dest.mkdir()
        ps = (
            f"& '{_ps1_quote(SEED_PS)}' -RepoRoot '{_ps1_quote(REPO)}' "
            f"-DestRoot '{_ps1_quote(dest)}' -WhatIf"
        )
        proc = _run_ps(ps, timeout=60)
        assert proc.returncode == 0
        assert not any(dest.rglob("*"))

    def test_happy_path_copies_smoke_md(self, tmp_path: Path) -> None:
        dest = tmp_path / "dest"
        ps = (
            f"& '{_ps1_quote(SEED_PS)}' -RepoRoot '{_ps1_quote(REPO)}' "
            f"-DestRoot '{_ps1_quote(dest)}'"
        )
        proc = _run_ps(ps, timeout=60)
        assert proc.returncode == 0, proc.stderr or proc.stdout
        assert (dest / "01_Academics_Beta" / "smoke.md").is_file()


class TestInvokeHermesAuditPytestNegative:
    def test_missing_python_returns_exit_1(self) -> None:
        ps = (
            f". '{_ps1_quote(COMMON)}'; "
            "Invoke-HermesAuditPytest -Python 'C:\\__hermes_missing_py__.exe' "
            "tests/windows/test_pytest_windows_timeout_policy.py --collect-only -q; "
            "exit $LASTEXITCODE"
        )
        proc = _run_ps(ps, timeout=60)
        assert proc.returncode == 1

    def test_missing_conda_returns_exit_1(self) -> None:
        ps = (
            f". '{_ps1_quote(COMMON)}'; "
            "Invoke-HermesCondaAuditPytest -CondaExe 'C:\\__hermes_missing_conda__.exe' "
            "tests/windows/test_pytest_windows_timeout_policy.py --collect-only -q; "
            "exit $LASTEXITCODE"
        )
        proc = _run_ps(ps, timeout=60)
        assert proc.returncode == 1


class TestRunTestsParallelWindows:
    def test_sets_pytest_addopts_on_win32(self) -> None:
        text = PARALLEL.read_text(encoding="utf-8")
        assert 'sys.platform == "win32"' in text
        assert "PYTEST_ADDOPTS" in text
        assert "timeout-method=thread" in text
