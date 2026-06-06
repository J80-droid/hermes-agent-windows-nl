"""Overlay: fork platform_toolsets guards + MCP sentinel expansion."""

from __future__ import annotations

from overlay.bootstrap import install
from overlay.hermes_cli.tools_config_fork_patch import (
    apply_tools_config_fork_patch,
    expand_cli_toolset_arg,
)


def test_expand_cli_toolset_arg_mcp_sentinel() -> None:
    apply_tools_config_fork_patch()
    cfg = {
        "mcp_servers": {
            "lancedb-legal": {"enabled": True},
            "lancedb-core": {"enabled": False},
        }
    }
    out = expand_cli_toolset_arg(["mcp", "file"], cfg)
    assert out == ["lancedb-legal", "file"]


def test_get_platform_tools_empty_list_guard() -> None:
    apply_tools_config_fork_patch()
    import hermes_cli.tools_config as tc

    cfg = {"platform_toolsets": {"cli": []}}
    assert tc._get_platform_tools(cfg, "cli") == set()


def test_bootstrap_exposes_expand_cli_on_tools_config() -> None:
    install()
    import hermes_cli.tools_config as tc

    assert callable(tc.expand_cli_toolset_arg)
    assert hasattr(tc, "_platform_toolsets_user_customized")
