"""Unit tests for overlay.hermes_cli.doctor_fork_patch."""

from __future__ import annotations

import re
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from overlay.bootstrap import install
from overlay.hermes_cli import doctor_fork_patch as dfp


@pytest.fixture(autouse=True)
def _bootstrap():
    install()
    yield


@pytest.fixture
def profile_with_global_blocks(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    prof = root / "profiles" / "core"
    prof.mkdir(parents=True)
    (root / "config.yaml").write_text("model:\n  provider: nous\n", encoding="utf-8")
    (prof / "config.yaml").write_text(
        "agent:\n  max_turns: 30\n"
        "auxiliary:\n  profile_describer:\n    provider: auto\n"
        "providers:\n  venice:\n    api_key_env: VENICE_API_KEY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(prof))
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    monkeypatch.setattr("hermes_constants.get_default_hermes_root", lambda: root)
    monkeypatch.setattr(
        "hermes_cli.profile_model_inheritance.root_config_path",
        lambda: root / "config.yaml",
    )
    return root, prof


class TestEnvHasNonEmptyKey:
    def test_missing_file_returns_false(self, tmp_path):
        assert dfp._env_has_non_empty_key(tmp_path / "missing.env", "KEY") is False

    def test_empty_value_returns_false(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("KEY=\n", encoding="utf-8")
        assert dfp._env_has_non_empty_key(env, "KEY") is False

    def test_quoted_value_returns_true(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text('KEY="secret"\n', encoding="utf-8")
        assert dfp._env_has_non_empty_key(env, "KEY") is True

    def test_comment_line_ignored(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("# KEY=ignored\nOTHER=1\n", encoding="utf-8")
        assert dfp._env_has_non_empty_key(env, "KEY") is False

    def test_oserror_returns_false(self, tmp_path, monkeypatch):
        env = tmp_path / ".env"
        env.write_text("KEY=1\n", encoding="utf-8")

        def _boom(_self, *_a, **_k):
            raise OSError("denied")

        monkeypatch.setattr(Path, "read_text", _boom)
        assert dfp._env_has_non_empty_key(env, "KEY") is False


class TestCheckWindowsSplitHome:
    def test_skips_non_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        issues: list = []
        dfp.check_windows_split_home_config(issues)
        assert issues == []

    def test_skips_without_localappdata(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        issues: list = []
        dfp.check_windows_split_home_config(issues)
        assert issues == []


class TestCheckProfileGlobalConfigBlocks:
    def test_warns_when_blocks_present(self, profile_with_global_blocks, monkeypatch):
        issues: list = []
        warns: list[str] = []

        monkeypatch.setattr(
            "hermes_cli.doctor.check_warn",
            lambda title, hint="": warns.append(title),
        )
        dfp.check_profile_global_config_blocks(issues, should_fix=False)
        assert issues
        assert any("core" in w for w in warns)

    def test_fix_strips_and_clears_issues(self, profile_with_global_blocks, monkeypatch):
        _, prof = profile_with_global_blocks
        issues: list = []
        monkeypatch.setattr("hermes_cli.doctor.check_ok", lambda *a, **k: None)
        monkeypatch.setattr("hermes_cli.doctor.check_warn", lambda *a, **k: None)

        dfp.check_profile_global_config_blocks(issues, should_fix=True)

        text = (prof / "config.yaml").read_text(encoding="utf-8")
        assert not re.search(r"(?m)^auxiliary:\s*", text)
        assert not any(i.startswith("Strip global config blocks") for i in issues)

    def test_no_fix_without_should_fix(self, profile_with_global_blocks, monkeypatch):
        _, prof = profile_with_global_blocks
        before = (prof / "config.yaml").read_text(encoding="utf-8")
        monkeypatch.setattr("hermes_cli.doctor.check_warn", lambda *a, **k: None)
        dfp.check_profile_global_config_blocks([], should_fix=False)
        assert (prof / "config.yaml").read_text(encoding="utf-8") == before

    def test_runtime_error_logs_warning(self, monkeypatch):
        mock_logger = MagicMock()
        monkeypatch.setattr(dfp, "logger", mock_logger)
        monkeypatch.setattr(
            "hermes_cli.profile_model_inheritance.list_profiles_with_global_config_blocks",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        dfp.check_profile_global_config_blocks([], should_fix=False)
        mock_logger.warning.assert_called_once()


class TestRunForkDoctorChecks:
    def test_fix_true_strips_blocks(self, profile_with_global_blocks, monkeypatch):
        _, prof = profile_with_global_blocks
        monkeypatch.setattr("hermes_cli.doctor.check_ok", lambda *a, **k: None)
        monkeypatch.setattr("hermes_cli.doctor.check_warn", lambda *a, **k: None)
        dfp._run_fork_doctor_checks(Namespace(fix=True))
        text = (prof / "config.yaml").read_text(encoding="utf-8")
        assert "agent:" in text
        assert "providers:" not in text.splitlines()[0:3]


class TestApplyDoctorForkPatch:
    def test_idempotent_second_call_no_rewrap(self):
        import hermes_cli.doctor as doctor_mod

        dfp.apply_doctor_fork_patch()
        first = doctor_mod.run_doctor
        dfp.apply_doctor_fork_patch()
        assert doctor_mod.run_doctor is first
        assert hasattr(doctor_mod, "_check_profile_global_config_blocks")

    def test_run_fork_checks_invoked_before_orig(self, monkeypatch):
        calls: list[str] = []
        monkeypatch.setattr(
            dfp,
            "_run_fork_doctor_checks",
            lambda args: calls.append("fork"),
        )
        import hermes_cli.doctor as doctor_mod

        sentinel = MagicMock(return_value=None)
        monkeypatch.setattr(doctor_mod, "run_doctor", sentinel, raising=False)
        doctor_mod._fork_doctor_patch_applied = False  # type: ignore[attr-defined]
        dfp.apply_doctor_fork_patch()
        doctor_mod.run_doctor(Namespace(fix=False))
        assert calls == ["fork"]
        sentinel.assert_called_once()
