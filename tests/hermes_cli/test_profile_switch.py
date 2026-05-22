"""Tests for hermes_cli.profile_switch institutional orchestration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


class TestNormalizeUserHermesHome:
    def test_detects_profile_subdir_without_fix(self, monkeypatch, tmp_path):
        from hermes_cli import profile_switch as ps

        root = tmp_path / "hermes"
        root.mkdir()
        (root / "config.yaml").write_text("x: 1\n")
        profile_dir = root / "profiles" / "core"
        profile_dir.mkdir(parents=True)

        monkeypatch.setattr(
            "hermes_constants.get_default_hermes_root", lambda: root
        )
        monkeypatch.setenv("HERMES_HOME", str(profile_dir))

        normalized, msg = ps.normalize_user_hermes_home(fix=False)
        assert normalized is False
        assert msg and "core" in msg

    def test_fix_sets_process_env(self, monkeypatch, tmp_path):
        from hermes_cli import profile_switch as ps

        root = tmp_path / "hermes"
        root.mkdir()
        (root / "config.yaml").write_text("x: 1\n")
        profile_dir = root / "profiles" / "core"
        profile_dir.mkdir(parents=True)

        monkeypatch.setattr(
            "hermes_constants.get_default_hermes_root", lambda: root
        )
        monkeypatch.setenv("HERMES_HOME", str(profile_dir))

        normalized, msg = ps.normalize_user_hermes_home(fix=True)
        assert normalized is True
        assert os.environ["HERMES_HOME"] == str(root)


def _patch_hermes_root(monkeypatch, hermes_root: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: hermes_root.parent)
    monkeypatch.setattr(
        "hermes_constants.get_default_hermes_root", lambda: hermes_root
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_root))


class TestExecuteProfileSwitch:
    def test_switch_writes_active_profile(self, monkeypatch, tmp_path):
        from hermes_cli import profile_switch as ps

        hermes_root = tmp_path / ".hermes"
        (hermes_root / "profiles" / "legal").mkdir(parents=True)
        (hermes_root / "profiles" / "core").mkdir(parents=True, exist_ok=True)
        (hermes_root / "active_profile").write_text("core\n")
        _patch_hermes_root(monkeypatch, hermes_root)

        monkeypatch.setattr(ps, "sync_profile_env_windows", lambda: False)
        monkeypatch.setattr(ps, "_gateway_running_for_profile", lambda _n: False)
        monkeypatch.setattr(ps, "restart_gateway_for_profile", lambda *_a: False)

        result = ps.execute_profile_switch("legal", sync_env=False, restart_gateway=False)
        assert result.profile == "legal"
        assert (hermes_root / "active_profile").read_text(encoding="utf-8").strip() == "legal"

    def test_sync_called_on_windows(self, monkeypatch, tmp_path):
        from hermes_cli import profile_switch as ps

        hermes_root = tmp_path / ".hermes"
        (hermes_root / "profiles" / "legal").mkdir(parents=True)
        _patch_hermes_root(monkeypatch, hermes_root)
        monkeypatch.setattr(ps.sys, "platform", "win32")

        called = []

        def _sync():
            called.append(True)
            return True

        monkeypatch.setattr(ps, "sync_profile_env_windows", _sync)
        monkeypatch.setattr(ps, "_gateway_running_for_profile", lambda _n: False)

        result = ps.execute_profile_switch("legal", restart_gateway=False)
        assert result.env_synced is True
        assert called
