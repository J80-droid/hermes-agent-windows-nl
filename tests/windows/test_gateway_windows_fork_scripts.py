"""Unit tests for fork Windows gateway install helpers (windows/scripts/*.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "windows" / "scripts"


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / rel)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestGatewayPidsProbe:
    def test_main_prints_pids_one_per_line(self, capsys):
        mod = _load_module("gateway_pids_probe", "gateway_pids_probe.py")
        with patch.object(mod, "find_gateway_pids", return_value=[111, 222]) as mock_find:
            assert mod.main() == 0
            mock_find.assert_called_once_with(all_profiles=True)
        out = capsys.readouterr().out.strip().splitlines()
        assert out == ["111", "222"]

    def test_main_empty_when_no_gateway(self, capsys):
        mod = _load_module("gateway_pids_probe", "gateway_pids_probe.py")
        with patch.object(mod, "find_gateway_pids", return_value=[]):
            assert mod.main() == 0
        assert capsys.readouterr().out.strip() == ""

    def test_main_rejects_invalid_pid_types_gracefully(self, capsys):
        mod = _load_module("gateway_pids_probe", "gateway_pids_probe.py")
        with patch.object(mod, "find_gateway_pids", return_value=[0, -1, 42]):
            assert mod.main() == 0
        assert capsys.readouterr().out.strip().splitlines() == ["0", "-1", "42"]


class TestGatewayRefreshTaskScript:
    def test_main_returns_1_when_script_missing(self, tmp_path, monkeypatch):
        mod = _load_module("gateway_refresh_task_script", "gateway_refresh_task_script.py")
        missing = tmp_path / "nope.cmd"
        monkeypatch.setattr(mod, "_write_task_script", lambda: missing)
        monkeypatch.setattr(mod, "is_task_registered", lambda: False)
        assert mod.main() == 1

    def test_main_success(self, tmp_path, monkeypatch, capsys):
        mod = _load_module("gateway_refresh_task_script", "gateway_refresh_task_script.py")
        script = tmp_path / "Hermes_Gateway_core.cmd"
        script.write_text("@echo off\r\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_write_task_script", lambda: script)
        monkeypatch.setattr(mod, "is_task_registered", lambda: True)
        assert mod.main() == 0
        out = capsys.readouterr().out
        assert "Task script:" in out
        assert "Scheduled Task registered: True" in out

    def test_main_when_task_not_registered_still_writes_script(self, tmp_path, monkeypatch, capsys):
        mod = _load_module("gateway_refresh_task_script", "gateway_refresh_task_script.py")
        script = tmp_path / "Hermes_Gateway.cmd"
        script.write_text("@echo off\r\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_write_task_script", lambda: script)
        monkeypatch.setattr(mod, "is_task_registered", lambda: False)
        assert mod.main() == 0
        assert "Scheduled Task registered: False" in capsys.readouterr().out


class TestGatewayInstallLoginElevated:
    def test_main_success(self, monkeypatch, capsys):
        mod = _load_module("gateway_install_login_elevated", "gateway_install_login_elevated.py")
        monkeypatch.setattr(
            mod,
            "_launch_elevated_install",
            lambda start_now=True, start_on_login=True: True,
        )
        assert mod.main() == 0
        assert "UAC gestart" in capsys.readouterr().out

    def test_main_failure(self, monkeypatch, capsys):
        mod = _load_module("gateway_install_login_elevated", "gateway_install_login_elevated.py")
        monkeypatch.setattr(
            mod,
            "_launch_elevated_install",
            lambda start_now=True, start_on_login=True: False,
        )
        assert mod.main() == 1
        assert "ShellExecuteW" in capsys.readouterr().out

    def test_passes_start_flags(self, monkeypatch):
        mod = _load_module("gateway_install_login_elevated", "gateway_install_login_elevated.py")
        seen = {}

        def capture(**kwargs):
            seen.update(kwargs)
            return True

        monkeypatch.setattr(mod, "_launch_elevated_install", capture)
        mod.main()
        assert seen == {"start_now": True, "start_on_login": True}


class TestGatewayWindowsPs1Wiring:
    def test_ensure_running_uses_dynamic_task_variable(self):
        text = (REPO / "windows" / "GATEWAY_ENSURE_RUNNING.ps1").read_text(encoding="utf-8")
        assert "schtasks /Run /TN $taskName" in text
        assert "schtasks /Run /TN Hermes_Gateway_core" not in text

    def test_common_resolves_multiple_task_names(self):
        text = (REPO / "windows" / "scripts" / "GatewayWindowsCommon.ps1").read_text(encoding="utf-8")
        assert "Hermes_Gateway_core" in text
        assert "Hermes_Gateway_legal" in text
        assert "Resolve-HermesGatewayScheduledTaskName" in text

    def test_install_login_dot_sources_common(self):
        text = (REPO / "windows" / "GATEWAY_INSTALL_LOGIN.ps1").read_text(encoding="utf-8")
        assert "GatewayWindowsCommon.ps1" in text
        assert "Test-HermesGatewayRunning" in text
