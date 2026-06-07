"""Tests for platform toolset sentinel expansion (mcp → MCP server names)."""

from __future__ import annotations

from hermes_cli.tools_config import PLATFORM_TOOLSET_SENTINELS, expand_cli_toolset_arg


def test_expand_mcp_sentinel_to_server_names():
    cfg = {
        "mcp_servers": {
            "lancedb-legal": {"enabled": True},
            "lancedb-core": {"enabled": False},
            "lancedb-trading": {},
        }
    }
    out = expand_cli_toolset_arg(["mcp", "file", "memory"], cfg)
    assert out == ["lancedb-legal", "lancedb-trading", "file", "memory"]
    assert "mcp" not in out


def test_no_mcp_sentinel_drops_mcp_servers():
    cfg = {"mcp_servers": {"lancedb-legal": {}}}
    out = expand_cli_toolset_arg(["no_mcp", "file"], cfg)
    assert out == ["file"]


def test_all_passthrough_unchanged():
    cfg = {"mcp_servers": {"lancedb-legal": {}}}
    assert expand_cli_toolset_arg(["all"], cfg) == ["all"]


def test_platform_sentinels_frozen():
    assert "mcp" in PLATFORM_TOOLSET_SENTINELS
    assert "no_mcp" in PLATFORM_TOOLSET_SENTINELS
