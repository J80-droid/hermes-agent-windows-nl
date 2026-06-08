"""Launcher fork routes legacy spawns and gateway detection to ``hermes_cli_entry``."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock

import gateway.status as gateway_status
import hermes_cli.kanban_db as kanban_db
import hermes_cli.web_server as web_server
import tui_gateway.server as tgs
from overlay.hermes_cli.launcher import CLI_MODULE, rewrite_legacy_cli_module_argv


def test_rewrite_legacy_cli_module_argv():
    argv = [sys.executable, "-m", "hermes_cli.main", "setup"]
    assert rewrite_legacy_cli_module_argv(argv) == [
        sys.executable,
        "-m",
        CLI_MODULE,
        "setup",
    ]


def test_module_hermes_argv_uses_entry_module():
    argv = kanban_db._module_hermes_argv()
    assert argv == [sys.executable, "-m", CLI_MODULE]


def test_gateway_run_resolve_hermes_bin_uses_entry_module(monkeypatch):
    import gateway.run as gateway_run

    monkeypatch.setattr("shutil.which", lambda _name: None)
    argv = gateway_run._resolve_hermes_bin()
    assert argv == [sys.executable, "-m", CLI_MODULE]


def test_gateway_status_recognizes_entry_module_cmdline(monkeypatch):
    monkeypatch.setattr(
        gateway_status,
        "_read_process_cmdline",
        lambda _pid: f"{sys.executable} -m {CLI_MODULE} gateway run",
    )
    assert gateway_status._looks_like_gateway_process(4242) is True


def test_tui_cli_exec_uses_entry_module(monkeypatch):
    captured: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)
    monkeypatch.setattr(tgs, "_cli_exec_blocked", lambda _argv: None)
    result = tgs._methods["cli.exec"](1, {"argv": ["doctor", "--help"]})
    assert result["result"]["code"] == 0
    assert captured[0][1:3] == ["-m", CLI_MODULE]


def test_web_spawn_hermes_action_uses_entry_module(monkeypatch, tmp_path):
    captured: list[list[str]] = []

    monkeypatch.setattr(web_server, "_ACTION_LOG_DIR", tmp_path)
    monkeypatch.setattr(web_server, "_ACTION_LOG_FILES", {"update": "update.log"})
    monkeypatch.setattr(web_server, "_ACTION_RESULTS", {})
    monkeypatch.setattr(web_server, "_ACTION_PROCS", {})
    monkeypatch.setattr(web_server, "PROJECT_ROOT", tmp_path)

    def _fake_popen(cmd, **kwargs):
        captured.append(list(cmd))
        return MagicMock()

    monkeypatch.setattr("subprocess.Popen", _fake_popen)
    web_server._spawn_hermes_action(["update", "--yes"], "update")
    assert captured[0][1:3] == ["-m", CLI_MODULE]
