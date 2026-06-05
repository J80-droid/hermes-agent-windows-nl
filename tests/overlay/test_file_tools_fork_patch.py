"""Unit tests for overlay/tools/file_tools_fork_patch.py."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from overlay.bootstrap import install
from overlay.tools.file_tools_fork_patch import apply_file_tools_fork_patch


@pytest.fixture(autouse=True)
def _reset_sandbox_and_bootstrap(monkeypatch):
    monkeypatch.delenv("HERMES_ENFORCE_FILE_SANDBOX", raising=False)
    monkeypatch.delenv("HERMES_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("TERMINAL_CWD", raising=False)
    from hermes_cli import filesystem_sandbox as fs

    fs.reset_workspace_cache()
    install()
    yield
    fs.reset_workspace_cache()


def test_apply_file_tools_fork_patch_idempotent():
    apply_file_tools_fork_patch()
    import tools.file_tools as ft

    assert getattr(ft, "_fork_file_tools_patch_applied", False) is True
    apply_file_tools_fork_patch()
    assert getattr(ft, "_fork_file_tools_patch_applied", False) is True


def test_resolve_path_unchanged_when_sandbox_off(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "0")
    from hermes_cli import filesystem_sandbox as fs

    fs.reset_workspace_cache()

    workspace = tmp_path / "ws"
    workspace.mkdir()
    target = workspace / "hello.txt"
    target.write_text("ok\n", encoding="utf-8")
    monkeypatch.setenv("TERMINAL_CWD", str(workspace))

    import tools.file_tools as ft

    resolved = ft._resolve_path_for_task("hello.txt")
    assert resolved == target.resolve()


def test_patch_tool_blocks_escape_when_sandbox_on(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("HERMES_WORKSPACE_ROOT", str(workspace))
        monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "1")
        monkeypatch.setenv("TERMINAL_CWD", str(workspace))

        from hermes_cli import filesystem_sandbox as fs

        fs.reset_workspace_cache()
        apply_file_tools_fork_patch()

        from tools.file_tools import patch_tool

        result = json.loads(
            patch_tool(
                mode="replace",
                path="../outside.txt",
                old_string="a",
                new_string="b",
            )
        )
        assert "error" in result
        assert "traversal" in result["error"].lower() or "sandbox" in result["error"].lower()


def test_read_file_tool_blocks_escape_when_sandbox_on(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("HERMES_WORKSPACE_ROOT", str(workspace))
        monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "1")
        monkeypatch.setenv("TERMINAL_CWD", str(workspace))

        from hermes_cli import filesystem_sandbox as fs

        fs.reset_workspace_cache()
        apply_file_tools_fork_patch()

        from tools.file_tools import read_file_tool

        result = json.loads(read_file_tool("../outside.txt"))
        assert "error" in result
