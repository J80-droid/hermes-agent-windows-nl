"""Unit tests for windows/scripts/check_fork_hermes_cli_tests.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO / "windows" / "scripts" / "check_fork_hermes_cli_tests.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_fork_hermes_cli_tests", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def checker():
    return _load_module()


def _write_exceptions(root: Path, content: str) -> Path:
    path = root / "windows" / "tests" / "fork_hermes_cli_test_exceptions.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def test_norm_converts_backslashes(checker) -> None:
    assert checker._norm(r"tests\hermes_cli\test_x.py") == "tests/hermes_cli/test_x.py"


def test_under_hermes_cli_prefix(checker) -> None:
    assert checker._under_hermes_cli("tests/hermes_cli/test_a.py")
    assert not checker._under_hermes_cli("tests/overlay/test_a.py")


def test_classify_splits_legacy_and_unknown(checker) -> None:
    paths = [
        "tests/hermes_cli/test_legacy.py",
        "tests/hermes_cli/test_new.py",
    ]
    exceptions = {"tests/hermes_cli/test_legacy.py"}
    buckets = checker._classify(paths, exceptions)
    assert buckets["legacy"] == ["tests/hermes_cli/test_legacy.py"]
    assert buckets["unknown"] == ["tests/hermes_cli/test_new.py"]


def test_invalid_exception_paths_rejects_overlay(checker) -> None:
    bad = checker._invalid_exception_paths(
        {
            "tests/hermes_cli/test_ok.py",
            "tests/overlay/test_wrong.py",
        }
    )
    assert bad == ["tests/overlay/test_wrong.py"]


def test_load_exceptions_skips_comments_and_blanks(checker, tmp_path: Path) -> None:
    _write_exceptions(
        tmp_path,
        """
        # comment
        tests/hermes_cli/test_one.py

        tests/hermes_cli/test_two.py
        """,
    )
    out = checker._load_exceptions(tmp_path)
    assert out == {
        "tests/hermes_cli/test_one.py",
        "tests/hermes_cli/test_two.py",
    }


def test_load_exceptions_missing_file_raises(checker, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="exceptions list missing"):
        checker._load_exceptions(tmp_path)


def test_run_pre_merge_upstream_parity_clean(checker, tmp_path: Path) -> None:
    _write_exceptions(tmp_path, "# empty\n")
    with patch.object(checker, "_git_lines", side_effect=[[], []]):
        report = checker.run_pre_merge(tmp_path, "upstream/main")
    assert report["upstream_parity_clean"] is True
    assert report["conflict_risk_total"] == 0
    assert report["unknown_paths"] == []


def test_run_pre_merge_flags_unknown_without_exception(checker, tmp_path: Path) -> None:
    _write_exceptions(tmp_path, "# empty\n")
    with patch.object(
        checker,
        "_git_lines",
        side_effect=[
            ["tests/hermes_cli/test_modified.py"],
            ["tests/hermes_cli/test_added.py"],
        ],
    ):
        report = checker.run_pre_merge(tmp_path, "upstream/main")
    assert report["conflict_risk_total"] == 2
    assert report["upstream_parity_clean"] is False
    assert set(report["unknown_paths"]) == {
        "tests/hermes_cli/test_modified.py",
        "tests/hermes_cli/test_added.py",
    }


def test_run_pre_merge_invalid_exceptions_in_report(checker, tmp_path: Path) -> None:
    _write_exceptions(
        tmp_path,
        """
        tests/overlay/test_misplaced.py
        """,
    )
    with patch.object(checker, "_git_lines", return_value=[]):
        report = checker.run_pre_merge(tmp_path, "upstream/main")
    assert report["invalid_exceptions"] == ["tests/overlay/test_misplaced.py"]


def test_run_staged_violation_on_new_file(checker, tmp_path: Path) -> None:
    _write_exceptions(tmp_path, "# empty\n")
    with patch.object(
        checker,
        "_git_lines",
        side_effect=[
            ["tests/hermes_cli/test_new.py"],
            ["tests/hermes_cli/test_new.py"],
        ],
    ):
        report = checker.run_staged(tmp_path)
    assert report["violations"] == ["tests/hermes_cli/test_new.py"]


def test_run_staged_allows_exception_legacy_add(checker, tmp_path: Path) -> None:
    _write_exceptions(
        tmp_path,
        """
        tests/hermes_cli/test_legacy.py
        """,
    )
    with patch.object(
        checker,
        "_git_lines",
        side_effect=[
            ["tests/hermes_cli/test_legacy.py"],
            ["tests/hermes_cli/test_legacy.py"],
        ],
    ):
        report = checker.run_staged(tmp_path)
    assert report["violations"] == []


def test_run_staged_ignores_modified_existing(checker, tmp_path: Path) -> None:
    """Staged guard blocks only --diff-filter=A, not modifications."""
    _write_exceptions(tmp_path, "# empty\n")
    with patch.object(
        checker,
        "_git_lines",
        side_effect=[
            ["tests/hermes_cli/test_existing.py"],
            [],
        ],
    ):
        report = checker.run_staged(tmp_path)
    assert report["staged_hermes_cli"] == ["tests/hermes_cli/test_existing.py"]
    assert report["violations"] == []


def test_git_lines_raises_on_nonzero(checker, tmp_path: Path) -> None:
    with patch.object(
        checker.subprocess,
        "run",
        return_value=type("R", (), {"returncode": 128, "stdout": "", "stderr": "fatal: bad"})(),
    ):
        with pytest.raises(RuntimeError, match="git diff"):
            checker._git_lines(tmp_path, "diff")


def test_main_pre_merge_strict_fails_on_unknown(checker, tmp_path: Path, monkeypatch, capsys) -> None:
    _write_exceptions(tmp_path, "# empty\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_fork_hermes_cli_tests.py",
            "--pre-merge",
            "--strict",
            "--repo",
            str(tmp_path),
        ],
    )
    with patch.object(
        checker,
        "_git_lines",
        side_effect=[
            [],
            ["tests/hermes_cli/test_fork_only.py"],
        ],
    ):
        code = checker.main()
    assert code == 1
    err = capsys.readouterr().err
    assert "test_fork_only.py" in err


def test_main_staged_fails_with_suggest(checker, tmp_path: Path, monkeypatch, capsys) -> None:
    _write_exceptions(tmp_path, "# empty\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_fork_hermes_cli_tests.py",
            "--staged",
            "--suggest",
            "--repo",
            str(tmp_path),
        ],
    )
    with patch.object(
        checker,
        "_git_lines",
        side_effect=[
            ["tests/hermes_cli/test_bad.py"],
            ["tests/hermes_cli/test_bad.py"],
        ],
    ):
        code = checker.main()
    assert code == 1
    err = capsys.readouterr().err
    assert "git restore --staged" in err


def test_main_json_output(checker, tmp_path: Path, monkeypatch, capsys) -> None:
    _write_exceptions(tmp_path, "# empty\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_fork_hermes_cli_tests.py",
            "--pre-merge",
            "--json",
            "--repo",
            str(tmp_path),
        ],
    )
    with patch.object(checker, "_git_lines", return_value=[]):
        assert checker.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["upstream_parity_clean"] is True


def test_main_requires_mode(checker, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["check_fork_hermes_cli_tests.py"])
    with pytest.raises(SystemExit):
        checker.main()


def test_real_repo_pre_merge_clean(checker) -> None:
    """Integration: live repo should have upstream parity after migration."""
    with patch.object(checker, "_repo_root", return_value=REPO):
        report = checker.run_pre_merge(REPO, "upstream/main")
    assert report["invalid_exceptions"] == []
    assert report["upstream_parity_clean"] is True
