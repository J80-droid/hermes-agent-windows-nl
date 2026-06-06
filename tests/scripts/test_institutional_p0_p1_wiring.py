"""Unit tests for scripts/institutional_p0_p1_wiring.py."""

from __future__ import annotations

import os
from pathlib import Path

from scripts.institutional_p0_p1_wiring import (
    REPO_ROOT,
    check_institutional_p0_p1_wiring,
    resolve_hermes_repo_from_env,
)


def test_check_wiring_all_pass_on_repo():
    report = check_institutional_p0_p1_wiring(REPO_ROOT)
    assert report["ok"] is True
    assert all(c["ok"] for c in report["checks"])


def test_check_wiring_fails_missing_rooktest(tmp_path):
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "pyproject.toml").write_text("name: x\n", encoding="utf-8")
    report = check_institutional_p0_p1_wiring(fake)
    assert report["ok"] is False
    names = {c["name"] for c in report["checks"] if not c["ok"]}
    assert "rooktest_search_script" in names or "resolve_hermes_repo" in names


def test_resolve_hermes_repo_from_env_prefers_env(monkeypatch, tmp_path):
    root = tmp_path / "hermes"
    root.mkdir()
    (root / "pyproject.toml").write_text("x", encoding="utf-8")
    monkeypatch.setenv("HERMES_REPO", str(root))
    assert resolve_hermes_repo_from_env() == root.resolve()


def test_resolve_hermes_repo_strips_pointer_line(monkeypatch, tmp_path):
    root = tmp_path / "hermes"
    root.mkdir()
    (root / "pyproject.toml").write_text("x", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pointer = data_dir / "hermes_agent_repo.txt"
    pointer.write_text(f"{root}\r\n", encoding="utf-8")
    monkeypatch.delenv("HERMES_REPO", raising=False)
    monkeypatch.setattr(
        "scripts.institutional_p0_p1_wiring.WINDOWS_SCRIPTS",
        tmp_path / "nope" / "scripts",
    )
    monkeypatch.setattr(
        "scripts.institutional_p0_p1_wiring.Path.home",
        lambda: tmp_path,
    )
    resolved = resolve_hermes_repo_from_env()
    assert resolved == root.resolve()


def test_institutional_bat_passes_hermes_repo():
    inst = REPO_ROOT / "windows" / "scripts" / "institutional_p0_p1.bat"
    text = inst.read_text(encoding="utf-8")
    assert 'set "HERMES_REPO=%HERMES_REPO%"' in text
    assert "ROOKTEST_BAT=%INST_SCRIPT_DIR%user_data" in text


def test_resolve_bat_uses_for_f_not_set_p():
    bat = REPO_ROOT / "windows" / "scripts" / "rag" / "_resolve_hermes_repo.bat"
    text = bat.read_text(encoding="utf-8")
    assert "for /f" in text
    assert "set /p HERMES_REPO" not in text
