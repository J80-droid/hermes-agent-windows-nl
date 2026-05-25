"""Unit tests for scripts/check-windows-footguns.py.

Focus: PS1 path convention footgun, should_scan_file scope, scan_file matching,
suppression markers, and main() exit codes. External git/subprocess calls mocked.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
FOOTGUNS_PATH = REPO / "scripts" / "check-windows-footguns.py"

spec = importlib.util.spec_from_file_location("check_windows_footguns", FOOTGUNS_PATH)
assert spec and spec.loader
fg = importlib.util.module_from_spec(spec)
sys.modules["check_windows_footguns"] = fg
spec.loader.exec_module(fg)


@pytest.fixture
def tmp_repo_file(tmp_path: Path):
    """Create a file under a fake repo tree and return absolute path."""

    def _make(relative: str, content: str, *, encoding: str = "utf-8") -> Path:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return target

    return _make


# ---------------------------------------------------------------------------
# should_scan_file — scope / edge cases
# ---------------------------------------------------------------------------


class TestShouldScanFile:
    def test_scans_python_under_repo(self, tmp_path: Path):
        py = tmp_path / "tools" / "foo.py"
        py.parent.mkdir(parents=True)
        py.write_text("x = 1\n", encoding="utf-8")
        assert fg.should_scan_file(py) is True

    def test_scans_ps1_under_windows(self, tmp_path: Path):
        ps1 = tmp_path / "windows" / "audits" / "Demo.ps1"
        ps1.parent.mkdir(parents=True)
        ps1.write_text("Write-Host 'ok'\n", encoding="utf-8")
        assert fg.should_scan_file(ps1) is True

    def test_skips_ps1_outside_windows(self, tmp_path: Path):
        ps1 = tmp_path / "scripts" / "other.ps1"
        ps1.parent.mkdir(parents=True)
        ps1.write_text("Write-Host 'ok'\n", encoding="utf-8")
        assert fg.should_scan_file(ps1) is False

    def test_skips_excluded_suffixes(self, tmp_path: Path):
        lock = tmp_path / "tools" / "uv.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("dummy\n", encoding="utf-8")
        assert fg.should_scan_file(lock) is False

    def test_skips_excluded_dirs(self, tmp_path: Path):
        py = tmp_path / "node_modules" / "pkg" / "mod.py"
        py.parent.mkdir(parents=True)
        py.write_text("open('x')\n", encoding="utf-8")
        assert fg.should_scan_file(py) is False

    def test_skips_self_module_path(self, tmp_path: Path):
        rel = fg.REPO_ROOT / "scripts" / "check-windows-footguns.py"
        if rel.exists():
            assert fg.should_scan_file(rel) is False


# ---------------------------------------------------------------------------
# PS1 legacy path footgun
# ---------------------------------------------------------------------------


class TestPs1LegacyPathFootgun:
    _PS1_FG = next(f for f in fg.FOOTGUNS if "PS1: legacy" in f.name)

    def test_detects_legacy_join_path_replace(self, tmp_path: Path):
        bad = tmp_path / "windows" / "audits" / "BadAudit.ps1"
        bad.parent.mkdir(parents=True)
        bad.write_text(
            "if (-not (Test-Path (Join-Path $RepoRoot ($rel -replace '/', '\\'))) { exit 1 }\n",
            encoding="utf-8",
        )
        matches = fg.scan_file(bad, [self._PS1_FG])
        assert len(matches) == 1
        assert "Join-Path" in matches[0][1]

    def test_allows_join_hermes_repo_path(self, tmp_path: Path):
        good = tmp_path / "windows" / "audits" / "GoodAudit.ps1"
        good.parent.mkdir(parents=True)
        good.write_text(
            "Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/foo.md'\n",
            encoding="utf-8",
        )
        matches = fg.scan_file(good, [self._PS1_FG])
        assert matches == []

    def test_allowlist_hermes_shell_common_internal_replace(self, tmp_path: Path):
        common = tmp_path / "windows" / "HermesShellCommon.ps1"
        common.parent.mkdir(parents=True)
        common.write_text(
            "$normalized = $RelativePath -replace '/', [IO.Path]::DirectorySeparatorChar\n",
            encoding="utf-8",
        )
        matches = fg.scan_file(common, [self._PS1_FG])
        assert matches == []

    def test_allowlist_hermes_home_common(self, tmp_path: Path):
        home = tmp_path / "windows" / "scripts" / "HermesHomeCommon.ps1"
        home.parent.mkdir(parents=True)
        home.write_text(
            "Join-Path $RepoRoot ($rel -replace '/', '\\')\n",
            encoding="utf-8",
        )
        matches = fg.scan_file(home, [self._PS1_FG])
        assert matches == []

    @pytest.mark.parametrize(
        "line",
        [
            "Join-Path $repoRoot 'windows/scripts/foo.ps1'",
            "# Join-Path $RepoRoot ($rel -replace '/', '\\')  # windows-footgun: ok",
        ],
    )
    def test_no_false_positive_on_safe_lines(self, tmp_path: Path, line: str):
        ps1 = tmp_path / "windows" / "audits" / "Safe.ps1"
        ps1.parent.mkdir(parents=True)
        ps1.write_text(line + "\n", encoding="utf-8")
        matches = fg.scan_file(ps1, [self._PS1_FG])
        assert matches == []


# ---------------------------------------------------------------------------
# Python open() footgun — happy / negative / suppression
# ---------------------------------------------------------------------------


class TestOpenEncodingFootgun:
    _OPEN_FG = next(f for f in fg.FOOTGUNS if "open() without encoding" in f.name)

    def test_flags_text_open_without_encoding(self, tmp_path: Path):
        py = tmp_path / "tools" / "bad.py"
        py.parent.mkdir(parents=True)
        py.write_text("data = open('file.txt', 'r').read()\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._OPEN_FG])
        assert len(matches) == 1

    def test_allows_open_with_encoding(self, tmp_path: Path):
        py = tmp_path / "tools" / "good.py"
        py.parent.mkdir(parents=True)
        py.write_text("data = open('file.txt', encoding='utf-8').read()\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._OPEN_FG])
        assert matches == []

    def test_allows_binary_mode(self, tmp_path: Path):
        py = tmp_path / "tools" / "binary.py"
        py.parent.mkdir(parents=True)
        py.write_text("data = open('file.bin', 'rb').read()\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._OPEN_FG])
        assert matches == []

    def test_suppression_marker_on_same_line(self, tmp_path: Path):
        py = tmp_path / "tools" / "suppressed.py"
        py.parent.mkdir(parents=True)
        py.write_text("open('legacy.txt')  # windows-footgun: ok\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._OPEN_FG])
        assert matches == []

    def test_skips_path_open_method(self, tmp_path: Path):
        py = tmp_path / "tools" / "path_open.py"
        py.parent.mkdir(parents=True)
        py.write_text("Path('x').open('r').read()\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._OPEN_FG])
        assert matches == []


# ---------------------------------------------------------------------------
# os.kill(pid, 0) footgun
# ---------------------------------------------------------------------------


class TestOsKillFootgun:
    _KILL_FG = next(f for f in fg.FOOTGUNS if "os.kill(pid, 0)" in f.name)

    def test_detects_bare_os_kill_zero(self, tmp_path: Path):
        py = tmp_path / "agent" / "probe.py"
        py.parent.mkdir(parents=True)
        py.write_text("import os\nos.kill(pid, 0)\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._KILL_FG])
        assert len(matches) == 1

    def test_skips_guarded_hasattr_line(self, tmp_path: Path):
        py = tmp_path / "agent" / "safe.py"
        py.parent.mkdir(parents=True)
        py.write_text("if hasattr(os, 'kill'):\n    pass\n", encoding="utf-8")
        matches = fg.scan_file(py, [self._KILL_FG])
        assert matches == []


# ---------------------------------------------------------------------------
# iter_files + main() — integration with mocks
# ---------------------------------------------------------------------------


class TestMainAndIterFiles:
    def test_main_clean_file_returns_zero(self, tmp_path: Path, monkeypatch):
        good = tmp_path / "windows" / "audits" / "Clean.ps1"
        good.parent.mkdir(parents=True)
        good.write_text(
            "Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'cli.py'\n",
            encoding="utf-8",
        )
        assert fg.main([str(good)]) == 0

    def test_main_legacy_ps1_returns_one(self, tmp_path: Path):
        bad = tmp_path / "windows" / "audits" / "Legacy.ps1"
        bad.parent.mkdir(parents=True)
        bad.write_text(
            "Join-Path $RepoRoot ($rel -replace '/', '\\')\n",
            encoding="utf-8",
        )
        assert fg.main([str(bad)]) == 1

    def test_main_no_staged_files_returns_zero(self, monkeypatch):
        monkeypatch.setattr(fg, "get_staged_files", lambda: [])
        assert fg.main([]) == 0

    def test_main_list_returns_zero(self, capsys):
        assert fg.main(["--list"]) == 0
        out = capsys.readouterr().out
        assert "PS1: legacy Join-Path" in out

    def test_iter_files_yields_scanable_only(self, tmp_path: Path):
        py = tmp_path / "tools" / "a.py"
        ps1_win = tmp_path / "windows" / "b.ps1"
        ps1_out = tmp_path / "other" / "c.ps1"
        lock = tmp_path / "tools" / "d.lock"
        for p, content in [
            (py, "x=1\n"),
            (ps1_win, "1\n"),
            (ps1_out, "2\n"),
            (lock, "3\n"),
        ]:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

        scanned = list(fg.iter_files([tmp_path]))
        paths = {p.name for p in scanned}
        assert paths == {"a.py", "b.ps1"}

    @patch.object(fg, "get_diff_files", return_value=[])
    def test_main_diff_empty_returns_zero(self, _mock_diff):
        assert fg.main(["--diff", "main"]) == 0


class TestStripCodeHelpers:
    def test_strip_code_removes_trailing_comment(self):
        assert fg._strip_code("open('x')  # comment") == "open('x')  "

    def test_strip_code_full_line_comment_empty(self):
        assert fg._strip_code("# only a comment") == ""

    def test_find_unquoted_hash_inside_string(self):
        line = "msg = 'hash # not comment'"
        assert fg._find_unquoted_hash(line) is None
