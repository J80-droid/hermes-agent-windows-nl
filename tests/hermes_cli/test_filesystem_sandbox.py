"""Unit tests for hermes_cli.filesystem_sandbox — Windows path traversal focus."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from hermes_cli import filesystem_sandbox as fs


@pytest.fixture(autouse=True)
def _reset_sandbox_cache():
    fs.reset_workspace_cache()
    yield
    fs.reset_workspace_cache()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_WORKSPACE_ROOT", str(root))
    monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "1")
    monkeypatch.delenv("TERMINAL_CWD", raising=False)
    return root


def _can_symlink() -> bool:
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.txt"
            src.write_text("x", encoding="utf-8")
            link = Path(d) / "link.txt"
            link.symlink_to(src)
            return True
    except OSError:
        return False


class TestForbiddenPathContent:
    @pytest.mark.parametrize(
        "bad_path",
        [
            "",
            "   ",
            "src\x00main.py",
            "../secret.txt",
            "..\\secret.txt",
            "src/../../outside.txt",
            "src\\..\\..\\outside.txt",
        ],
    )
    def test_blocks_traversal_components(self, bad_path):
        err = fs.has_forbidden_path_content(bad_path)
        assert err is not None
        assert ".." in err or "Empty" in err or "null" in err.lower()

    @pytest.mark.parametrize(
        "device_path",
        [
            r"\\.\C:\Windows",
            r"\\?\C:\Windows\System32",
            "//?/C:/Windows",
        ],
    )
    def test_blocks_windows_device_prefixes(self, device_path):
        err = fs.has_forbidden_path_content(device_path)
        assert err is not None
        assert "Device" in err or "extended" in err


class TestWindowsPathTraversal:
    @pytest.mark.parametrize(
        "raw_path",
        [
            "../outside.txt",
            "..\\outside.txt",
            "src/../../outside.txt",
            "src\\..\\..\\outside.txt",
            "/etc/passwd",
        ],
    )
    def test_blocks_relative_escape(self, workspace, raw_path):
        err = fs.check_filesystem_sandbox(raw_path, sandbox_root=workspace)
        assert err is not None

    @pytest.mark.parametrize(
        "raw_path",
        [
            "C:\\Windows\\System32\\config\\SAM",
            "C:/Windows/System32/drivers/etc/hosts",
            "D:\\outside\\file.txt",
        ],
    )
    def test_blocks_absolute_outside_workspace(self, workspace, raw_path):
        if sys.platform != "win32":
            pytest.skip("Drive-letter cases are Windows-specific")
        err = fs.check_filesystem_sandbox(raw_path, sandbox_root=workspace)
        assert err is not None
        assert "outside" in err.lower() or "escapes" in err.lower()

    def test_allows_in_workspace_relative(self, workspace):
        resolved, err = fs.validate_agent_path_for_task(
            "src/main.py",
            resolution_base=workspace,
            sandbox_root=workspace,
        )
        assert err is None
        assert resolved == (workspace / "src" / "main.py").resolve()

    def test_allows_in_workspace_absolute(self, workspace):
        target = workspace / "README.md"
        resolved, err = fs.validate_agent_path_for_task(
            str(target),
            resolution_base=workspace,
            sandbox_root=workspace,
        )
        assert err is None
        assert resolved == target.resolve()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows case-insensitivity")
    def test_windows_case_insensitive_root(self, workspace):
        upper = str(workspace).upper()
        child = upper + "\\SRC\\MAIN.PY"
        resolved, err = fs.validate_agent_path_for_task(
            child,
            resolution_base=workspace,
            sandbox_root=workspace,
        )
        assert err is None
        assert resolved.name.lower() == "main.py"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows drive-letter paths")
    def test_blocks_sibling_directory_prefix_confusion(self, workspace, tmp_path):
        sibling = tmp_path / "workspace-backdoor"
        sibling.mkdir()
        secret = sibling / "secret.txt"
        secret.write_text("leak", encoding="utf-8")
        err = fs.check_filesystem_sandbox(str(secret), sandbox_root=workspace)
        assert err is not None


@pytest.mark.skipif(not _can_symlink(), reason="Symlinks require elevated/dev mode on Windows")
class TestSymlinkSandboxEscape:
    def test_blocks_symlink_outside_workspace(self, workspace):
        outside = workspace.parent / "outside-secret.txt"
        outside.write_text("secret", encoding="utf-8")
        link = workspace / "link.txt"
        link.symlink_to(outside)
        err = fs.check_filesystem_sandbox("link.txt", sandbox_root=workspace, resolution_base=workspace)
        assert err is not None

    def test_allows_symlink_inside_workspace(self, workspace):
        real = workspace / "src" / "real.txt"
        real.write_text("ok", encoding="utf-8")
        link = workspace / "src" / "alias.txt"
        link.symlink_to(real)
        resolved, err = fs.validate_agent_path_for_task(
            "src/alias.txt",
            resolution_base=workspace,
            sandbox_root=workspace,
        )
        assert err is None
        assert resolved == link.resolve()


class TestSandboxEnforcementToggle:
    def test_disabled_allows_outside_path(self, workspace, monkeypatch):
        monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "0")
        fs.reset_workspace_cache()
        outside = workspace.parent / "outside.txt"
        outside.write_text("x", encoding="utf-8")
        err = fs.check_filesystem_sandbox(str(outside), sandbox_root=workspace)
        assert err is None

    def test_default_workspace_root_windows_layout(self, monkeypatch, tmp_path):
        monkeypatch.delenv("HERMES_WORKSPACE_ROOT", raising=False)
        monkeypatch.delenv("TERMINAL_CWD", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        fs.reset_workspace_cache()
        root = fs.default_workspace_root()
        assert "hermes" in str(root).lower()
        assert "workspace" in str(root).lower()
        assert root.exists()


class TestFileToolsIntegration:
    def test_read_file_tool_blocks_escape(self, workspace, monkeypatch):
        monkeypatch.setenv("HERMES_WORKSPACE_ROOT", str(workspace))
        monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "1")
        monkeypatch.setenv("TERMINAL_CWD", str(workspace))
        fs.reset_workspace_cache()

        from tools.file_tools import read_file_tool
        import json

        result = json.loads(read_file_tool("../outside.txt"))
        assert "error" in result
        assert ".." in result["error"] or "sandbox" in result["error"].lower()

    def test_read_file_tool_allows_internal_file(self, workspace, monkeypatch):
        monkeypatch.setenv("HERMES_WORKSPACE_ROOT", str(workspace))
        monkeypatch.setenv("HERMES_ENFORCE_FILE_SANDBOX", "1")
        monkeypatch.setenv("TERMINAL_CWD", str(workspace))
        fs.reset_workspace_cache()

        err = fs.check_filesystem_sandbox(
            "README.md",
            sandbox_root=workspace,
            resolution_base=workspace,
        )
        assert err is None
        resolved, resolve_err = fs.validate_agent_path_for_task(
            "README.md",
            resolution_base=workspace,
            sandbox_root=workspace,
        )
        assert resolve_err is None
        assert resolved == (workspace / "README.md").resolve()
