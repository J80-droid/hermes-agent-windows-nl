"""Fork overlay: kanban worker argv resolves to ``hermes_cli_entry``."""
from __future__ import annotations

import sys

import pytest

from overlay.bootstrap import install
from overlay.hermes_cli.launcher import CLI_MODULE

install()

import hermes_cli.kanban_db as kb


def test_resolve_hermes_argv_avoids_implicit_windows_batch_shim(monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "hermes.CMD").write_text("@echo off\n", encoding="utf-8")
    monkeypatch.delenv("HERMES_BIN", raising=False)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("PATHEXT", ".CMD")
    monkeypatch.setattr(kb, "_IS_WINDOWS", True)

    assert kb._resolve_hermes_argv() == [sys.executable, "-m", CLI_MODULE]


@pytest.mark.parametrize(
    "env_setup",
    [
        {"PATH": "", "HERMES_BIN": "hermes", "_IS_WINDOWS": True},
        {"PATH": "", "HERMES_BIN": "hermes", "_IS_WINDOWS": False},
    ],
)
def test_resolve_hermes_argv_module_fallback_when_shim_unusable(monkeypatch, env_setup):
    for key, val in env_setup.items():
        if key == "_IS_WINDOWS":
            monkeypatch.setattr(kb, key, val)
        else:
            monkeypatch.setenv(key, val)
    assert kb._resolve_hermes_argv() == [sys.executable, "-m", CLI_MODULE]


def test_resolve_hermes_argv_falls_back_to_module_form_when_no_path_shim(monkeypatch):
    monkeypatch.delenv("HERMES_BIN", raising=False)
    monkeypatch.setattr(kb, "_safe_which_no_cwd", lambda _name: None)
    assert kb._resolve_hermes_argv() == [sys.executable, "-m", CLI_MODULE]
