"""Unit tests for hermes_cli/config_snapshot.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hermes_cli import config_snapshot as cs


@pytest.fixture(autouse=True)
def _clear_snapshot():
    cs.bust_config_snapshot()
    yield
    cs.bust_config_snapshot()


class TestConfigPathMtimeNs:
    def test_returns_mtime_when_file_exists(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("x: 1\n", encoding="utf-8")
        with patch("hermes_cli.config.get_config_path", return_value=cfg):
            mtime = cs.config_path_mtime_ns()
        assert mtime == cfg.stat().st_mtime_ns

    def test_returns_zero_when_missing(self, tmp_path, monkeypatch):
        missing = tmp_path / "nope.yaml"
        with patch("hermes_cli.config.get_config_path", return_value=missing):
            assert cs.config_path_mtime_ns() == 0

    def test_returns_zero_on_stat_error(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("a", encoding="utf-8")
        with patch("hermes_cli.config.get_config_path", return_value=cfg), patch.object(
            Path, "stat", side_effect=OSError("locked")
        ):
            assert cs.config_path_mtime_ns() == 0


class TestGetConfigSnapshot:
    def test_loads_and_caches_by_mtime(self, tmp_path, monkeypatch):
        cfg = tmp_path / "hermes.yaml"
        cfg.write_text("raw: true\n", encoding="utf-8")
        with patch("hermes_cli.config.get_config_path", return_value=cfg), patch(
            "hermes_cli.config.read_raw_config", return_value={"raw": True}
        ), patch("hermes_cli.config.load_config_readonly", return_value={"expanded": 1}):
            first = cs.get_config_snapshot()
            second = cs.get_config_snapshot()
        assert first is second
        assert first.raw == {"raw": True}
        assert first.expanded == {"expanded": 1}
        assert first.path == cfg

    def test_force_reload_bypasses_cache(self, tmp_path):
        cfg = tmp_path / "hermes.yaml"
        cfg.write_text("v1", encoding="utf-8")
        with patch("hermes_cli.config.get_config_path", return_value=cfg), patch(
            "hermes_cli.config.read_raw_config", side_effect=[{"v": 1}, {"v": 2}]
        ), patch("hermes_cli.config.load_config_readonly", return_value={}):
            a = cs.get_config_snapshot()
            b = cs.get_config_snapshot(force_reload=True)
        assert a is not b
        assert a.raw["v"] == 1
        assert b.raw["v"] == 2

    def test_bust_invalidates_cache(self, tmp_path):
        cfg = tmp_path / "hermes.yaml"
        cfg.write_text("x", encoding="utf-8")
        with patch("hermes_cli.config.get_config_path", return_value=cfg), patch(
            "hermes_cli.config.read_raw_config", return_value={}
        ), patch("hermes_cli.config.load_config_readonly", return_value={}):
            a = cs.get_config_snapshot()
            cs.bust_config_snapshot()
            b = cs.get_config_snapshot()
        assert a is not b

    def test_reload_when_mtime_changes(self, tmp_path):
        cfg = tmp_path / "hermes.yaml"
        cfg.write_text("v1", encoding="utf-8")
        mtime_values = iter([1_000_000_000, 2_000_000_000])
        with patch("hermes_cli.config.get_config_path", return_value=cfg), patch(
            "hermes_cli.config.read_raw_config", return_value={"n": 1}
        ), patch("hermes_cli.config.load_config_readonly", return_value={}), patch.object(
            cs, "config_path_mtime_ns", side_effect=lambda: next(mtime_values)
        ):
            first = cs.get_config_snapshot()
            cfg.write_text("v2", encoding="utf-8")
            second = cs.get_config_snapshot()
        assert first is not second
        assert first.mtime_ns == 1_000_000_000
        assert second.mtime_ns == 2_000_000_000
