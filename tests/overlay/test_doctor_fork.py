"""Fork tests migrated from tests/hermes_cli/test_doctor.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from hermes_cli import doctor
from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestWindowsSplitHomeCheck:
    def test_skips_off_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        issues: list = []
        doctor._check_windows_split_home_config(issues)
        assert issues == []

    def test_warns_when_both_configs_exist(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sys, "platform", "win32")
        local = tmp_path / "AppData" / "Local" / "hermes"
        local.mkdir(parents=True)
        (local / "config.yaml").write_text("model: {}\n", encoding="utf-8")
        legacy = tmp_path / ".hermes"
        legacy.mkdir()
        (legacy / "config.yaml").write_text("model: {}\n", encoding="utf-8")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        issues: list = []
        doctor._check_windows_split_home_config(issues)
        assert any("APPLY_HERMES_HOME_MIGRATION" in item for item in issues)
        captured = capsys.readouterr()
        assert "split-home" in captured.out.lower() or "Split-home" in captured.out
