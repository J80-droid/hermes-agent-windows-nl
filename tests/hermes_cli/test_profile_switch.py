"""Tests for hermes_cli.profile_switch institutional orchestration."""

from __future__ import annotations

import os
import subprocess
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
        monkeypatch.setattr(
            ps,
            "_set_user_hermes_home_windows",
            lambda home: os.environ.__setitem__("HERMES_HOME", home),
        )

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

        monkeypatch.setattr(ps, "sync_profile_env_windows", lambda **_: (False, None))
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

        def _sync(**_kwargs):
            called.append(True)
            return True, None

        monkeypatch.setattr(ps, "sync_profile_env_windows", _sync)
        monkeypatch.setattr(ps, "_gateway_running_for_profile", lambda _n: False)

        result = ps.execute_profile_switch("legal", restart_gateway=False)
        assert result.env_synced is True
        assert called

    def test_kanban_workers_stopped_on_switch(self, monkeypatch, tmp_path):
        from hermes_cli import profile_switch as ps

        hermes_root = tmp_path / ".hermes"
        (hermes_root / "profiles" / "legal").mkdir(parents=True)
        (hermes_root / "profiles" / "core").mkdir(parents=True, exist_ok=True)
        _patch_hermes_root(monkeypatch, hermes_root)

        monkeypatch.setattr(ps, "sync_profile_env_windows", lambda **_: (False, None))
        monkeypatch.setattr(ps, "_gateway_running_for_profile", lambda _n: False)
        monkeypatch.setattr(ps, "restart_gateway_for_profile", lambda *_a: False)
        monkeypatch.setattr(ps, "stop_kanban_workers_for_assignee", lambda a: 2 if a == "core" else 0)

        result = ps.execute_profile_switch(
            "legal", old_profile="core", sync_env=False, restart_gateway=False
        )
        assert result.kanban_workers_stopped == 2


class TestSyncProfileEnvWindows:
    def test_sync_timeout_returns_error_message(self, monkeypatch):
        from hermes_cli import profile_switch as ps

        script = ps._repo_windows_dir() / "sync_hermes_api_env.ps1"
        if not script.is_file():
            pytest.skip("sync script missing")
        monkeypatch.setattr(ps.sys, "platform", "win32")

        def _timeout(*_a, **_k):
            raise subprocess.TimeoutExpired(cmd="powershell", timeout=1)

        monkeypatch.setattr(ps.subprocess, "run", _timeout)
        ok, err = ps.sync_profile_env_windows(timeout_sec=1)
        assert ok is False
        assert err and "timeout" in err.lower()


class TestExecuteProfileSwitchBounded:
    def test_bounded_raises_on_timeout(self, monkeypatch, tmp_path):
        from hermes_cli import profile_switch as ps

        hermes_root = tmp_path / ".hermes"
        (hermes_root / "profiles" / "legal").mkdir(parents=True)
        _patch_hermes_root(monkeypatch, hermes_root)

        def _slow(*_a, **_k):
            import time

            time.sleep(5)
            return ps.ProfileSwitchResult(profile="legal", old_profile="default")

        monkeypatch.setattr(ps, "execute_profile_switch", _slow)
        with pytest.raises(ps.ProfileSwitchError, match="timeout"):
            ps.execute_profile_switch_bounded("legal", timeout_sec=1, sync_env=False)
