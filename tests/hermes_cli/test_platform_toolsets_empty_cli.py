"""platform_toolsets.cli: [] must not expand to hermes-cli."""
from hermes_cli.tools_config import _get_platform_tools


def test_empty_cli_list_is_explicit_not_hermes_cli():
    cfg = {"platform_toolsets": {"cli": []}, "mcp_servers": {}}
    enabled = _get_platform_tools(cfg, "cli", include_default_mcp_servers=False)
    assert "hermes-cli" not in enabled
    assert "web" not in enabled
    assert "file" not in enabled
    assert "browser" not in enabled


def test_missing_cli_key_falls_back_to_hermes_cli():
    cfg = {"platform_toolsets": {}}
    enabled = _get_platform_tools(cfg, "cli")
    assert "web" in enabled or "file" in enabled or len(enabled) > 5
