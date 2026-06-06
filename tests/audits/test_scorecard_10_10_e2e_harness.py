"""Unit tests voor audits/Scorecard1010E2E.harness.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "Scorecard1010E2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scorecard_10_10_e2e_harness", HARNESS_PATH)
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


class TestStepHelper:
    def test_ok_increments_step(self, harness: ModuleType) -> None:
        harness._step("x", True)
        assert harness.STEP == 1
        assert harness.FAILURES == 0

    def test_fail_increments_failures(self, harness: ModuleType) -> None:
        harness._step("x", False, "detail")
        assert harness.STEP == 1
        assert harness.FAILURES == 1


class TestE1TierAPolicy:
    def test_passes_with_valid_repo(self, harness: ModuleType) -> None:
        harness.test_e1_tier_a_pyproject_and_helpers()
        assert harness.FAILURES == 0

    def test_fails_when_helper_missing(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        pyproject_text = (REPO / "pyproject.toml").read_text(encoding="utf-8")

        def fake_read(rel: str) -> str:
            if rel == "windows/HermesShellCommon.ps1":
                return "# stripped"
            if rel == "pyproject.toml":
                return pyproject_text
            raise FileNotFoundError(rel)

        monkeypatch.setattr(harness, "_read", fake_read)
        harness.test_e1_tier_a_pyproject_and_helpers()
        assert harness.FAILURES == 1


class TestE5CondaCollect:
    def test_skips_when_no_conda(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness, "CONDA", Path("/nonexistent/conda.exe"))
        harness.test_e5_conda_audit_pytest_collect()
        assert harness.FAILURES == 0
        assert harness.STEP == 1

    @patch("subprocess.run")
    def test_fails_on_conda_value_error(
        self, mock_run: MagicMock, harness: ModuleType, tmp_path: Path
    ) -> None:
        conda_shim = tmp_path / "conda.exe"
        conda_shim.write_text("", encoding="utf-8")
        harness.CONDA = conda_shim  # type: ignore[misc]
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="CondaValueError: bad env",
        )
        harness.test_e5_conda_audit_pytest_collect()
        assert harness.FAILURES == 1
