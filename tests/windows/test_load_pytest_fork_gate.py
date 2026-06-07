"""Unit tests for windows/scripts/load_pytest_fork_gate.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
LOADER_PATH = REPO / "windows" / "scripts" / "load_pytest_fork_gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("load_pytest_fork_gate", LOADER_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def loader():
    return _load_module()


def _write_manifest(root: Path, content: str) -> Path:
    path = root / "windows" / "tests" / "pytest_fork_gate.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def _copy_loader_script(root: Path) -> None:
    dest = root / "windows" / "scripts" / "load_pytest_fork_gate.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(LOADER_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def test_build_config_gate_happy_path(loader, tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "sample.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_x(): pass\n", encoding="utf-8")
    _write_manifest(
        tmp_path,
        """
        version: 1
        markers: "not e2e"
        paths:
          - tests/sample.py
          - tests/sample.py::TestClass
        ignores:
          - tests/integration
        upstream:
          paths: [tests/]
          maxfail_default: 25
        """,
    )
    cfg = loader.build_config(tmp_path, "gate")
    assert cfg["mode"] == "gate"
    assert cfg["paths"] == ["tests/sample.py", "tests/sample.py::TestClass"]
    assert cfg["ignores"] == ["tests/integration"]
    assert cfg["markers"] == "not e2e"


def test_build_config_upstream_merges_ignores(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        markers: "not integration and not e2e"
        paths:
          - tests/sample.py
        ignores:
          - tests/e2e
        upstream:
          paths: [tests/]
          ignores: [tests/docker]
          maxfail_default: 10
          junit: windows/tests/custom_junit.xml
        """,
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "sample.py").write_text("pass\n", encoding="utf-8")
    cfg = loader.build_config(tmp_path, "upstream")
    assert cfg["mode"] == "upstream"
    assert cfg["maxfail"] == 10
    assert cfg["junit"] == "windows/tests/custom_junit.xml"
    assert cfg["ignores"] == ["tests/e2e", "tests/docker"]


def test_build_config_gate_empty_paths_raises(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths: []
        ignores: []
        """,
    )
    with pytest.raises(ValueError, match="paths must not be empty"):
        loader.build_config(tmp_path, "gate")


def test_build_config_invalid_paths_type(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths: not-a-list
        ignores: []
        """,
    )
    with pytest.raises(ValueError, match="paths"):
        loader.build_config(tmp_path, "gate")


def test_build_config_invalid_maxfail(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths: [tests/sample.py]
        ignores: []
        upstream:
          maxfail_default: zero
        """,
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "sample.py").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="maxfail_default"):
        loader.build_config(tmp_path, "upstream")


def test_build_config_missing_gate_file(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths:
          - tests/missing.py
        ignores: []
        """,
    )
    with pytest.raises(FileNotFoundError, match="missing"):
        loader.build_config(tmp_path, "gate")


def test_build_config_missing_manifest(loader, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="manifest missing"):
        loader.build_config(tmp_path, "gate")


def test_build_config_empty_yaml(loader, tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "")
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        loader.build_config(tmp_path, "gate")


def test_main_cli_gate_mode(loader, tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "ok.py").write_text("x", encoding="utf-8")
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths: [tests/ok.py]
        ignores: []
        """,
    )
    monkeypatch.setattr(sys, "argv", ["load_pytest_fork_gate.py", "--mode", "gate", "--repo-root", str(tmp_path)])
    assert loader.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "gate"


def test_main_cli_invalid_repo_exit_one(loader, monkeypatch, capsys) -> None:
    missing = Path("Z:/no_such_repo_root_for_pytest")
    monkeypatch.setattr(
        sys,
        "argv",
        ["load_pytest_fork_gate.py", "--mode", "gate", "--repo-root", str(missing)],
    )
    assert loader.main() == 1
    assert "manifest missing" in capsys.readouterr().err


def test_build_config_invalid_upstream_type(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths: [tests/sample.py]
        ignores: []
        upstream: not-a-dict
        """,
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "sample.py").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="upstream"):
        loader.build_config(tmp_path, "upstream")


def test_build_config_unsupported_mode(loader, tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths: [tests/sample.py]
        ignores: []
        """,
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "sample.py").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported mode"):
        loader.build_config(tmp_path, "invalid-mode")


def test_build_config_gate_directory_path(loader, tmp_path: Path) -> None:
    overlay = tmp_path / "tests" / "overlay"
    overlay.mkdir(parents=True)
    _write_manifest(
        tmp_path,
        """
        version: 1
        paths:
          - tests/overlay/
        ignores: []
        """,
    )
    cfg = loader.build_config(tmp_path, "gate")
    assert cfg["paths"] == ["tests/overlay/"]


def test_real_repo_manifest_parses(loader) -> None:
    cfg = loader.build_config(REPO, "gate")
    assert cfg["mode"] == "gate"
    data = yaml.safe_load((REPO / "windows/tests/pytest_fork_gate.yaml").read_text(encoding="utf-8"))
    assert cfg["paths"] == data["paths"]
