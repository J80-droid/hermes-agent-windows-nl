"""Unit tests for create_profile model-strip + s6 register (upstream merge path)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


@pytest.fixture
def profile_env(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    default_home = tmp_path / ".hermes"
    default_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(default_home))
    return default_home


class TestCreateProfileModelStrip:
    """Happy path + edge cases for strip_model_block_from_profile_config in create_profile."""

    def test_create_without_clone_has_no_config_yaml_until_user_writes_one(self, profile_env):
        from hermes_cli.profiles import create_profile

        prof = create_profile("fresh_no_clone", no_alias=True)
        assert prof.is_dir()
        assert not (prof / "config.yaml").exists()

    def test_clone_strips_model_and_preserves_agent_block(self, profile_env):
        from hermes_cli.profiles import create_profile

        (profile_env / "config.yaml").write_text(
            "model:\n  default: openrouter/x\n"
            "agent:\n  terminal:\n    cwd: /tmp\n",
            encoding="utf-8",
        )
        prof = create_profile("child_agent", clone_config=True, no_alias=True)
        data = yaml.safe_load((prof / "config.yaml").read_text(encoding="utf-8")) or {}
        assert "model" not in data
        assert data.get("agent", {}).get("terminal", {}).get("cwd") == "/tmp"

    def test_register_hook_called_after_create(self, profile_env, monkeypatch):
        from hermes_cli.profiles import create_profile

        registered: list[str] = []

        def _capture(name: str) -> None:
            registered.append(name)

        monkeypatch.setattr(
            "hermes_cli.profiles._maybe_register_gateway_service",
            _capture,
        )
        create_profile("hook_order", no_alias=True)
        assert registered == ["hook_order"]

    def test_create_propagates_unhandled_strip_errors(self, profile_env):
        """strip wordt in create_profile niet afgevangen — alleen ImportError op import."""
        from hermes_cli.profiles import create_profile

        with patch(
            "hermes_cli.profile_model_inheritance.strip_model_block_from_profile_config",
            side_effect=RuntimeError("strip exploded"),
        ):
            with pytest.raises(RuntimeError, match="strip exploded"):
                create_profile("strip_raises", clone_config=True, no_alias=True)

    def test_invalid_profile_name_rejected(self, profile_env):
        from hermes_cli.profiles import create_profile

        with pytest.raises((ValueError, Exception)):
            create_profile("INVALID NAME!", no_alias=True)


class TestCreateProfileNegativeInput:
    """Invalid / edge inputs must not corrupt HERMES_HOME."""

    def test_duplicate_profile_raises(self, profile_env):
        from hermes_cli.profiles import create_profile

        create_profile("dupe", no_alias=True)
        with pytest.raises(Exception):
            create_profile("dupe", no_alias=True)

    def test_reserved_default_name_rejected(self, profile_env):
        from hermes_cli.profiles import create_profile

        with pytest.raises(Exception):
            create_profile("default", no_alias=True)
