"""Fork tools_config tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hermes_cli.tools_config import CONFIGURABLE_TOOLSETS, _get_platform_tools, _save_platform_tools
from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


def test_save_platform_tools_marks_user_customized():
    config = {"platform_toolsets": {"cli": ["web"]}}
    with patch("hermes_cli.tools_config.save_config"):
        _save_platform_tools(config, "cli", {"web", "terminal"})
    assert config["platform_toolsets"]["_user_customized"]["cli"] is True


def test_get_platform_tools_ignores_reserved_meta_key_in_cli_list():
    config = {
        "platform_toolsets": {
            "cli": ["_user_customized", "web", "terminal"],
        }
    }
    enabled = _get_platform_tools(config, "cli", include_default_mcp_servers=False)
    assert "_user_customized" not in enabled
    assert enabled == {"web", "terminal"}


def test_get_platform_tools_user_customized_skips_hermes_cli_expansion():
    config = {
        "platform_toolsets": {
            "_user_customized": {"cli": True},
            "cli": ["hermes-cli", "web", "terminal"],
        }
    }
    enabled = _get_platform_tools(config, "cli", include_default_mcp_servers=False)
    assert enabled == {"web", "terminal"}


def test_mcp_and_kanban_in_configurable_toolsets():
    keys = {ts_key for ts_key, _, _ in CONFIGURABLE_TOOLSETS}
    assert "mcp" in keys
    assert "kanban" in keys
