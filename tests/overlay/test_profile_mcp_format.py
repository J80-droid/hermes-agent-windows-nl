"""Tests for profile MCP config migration (mcp.servers → mcp_servers)."""

from hermes_cli.profile_mcp_format import (
    has_legacy_mcp_block,
    migrate_profile_mcp_config,
)


def test_has_legacy_mcp_block():
    assert has_legacy_mcp_block({"mcp": {"servers": {"lancedb-legal": {}}}})
    assert not has_legacy_mcp_block({"mcp_servers": {"lancedb-legal": {}}})


def test_migrate_profile_mcp_config():
    raw = {
        "mcp": {
            "servers": {
                "lancedb-legal": {
                    "command": "python",
                    "args": ["mcp_server.py"],
                    "env": {"HERMES_LANCEDB_PATH": "/data/legal"},
                }
            }
        },
        "enabled_toolsets": ["mcp"],
    }
    migrated, changed = migrate_profile_mcp_config(raw, repo_root="/repo")
    assert changed
    assert "mcp" not in migrated
    assert "lancedb-legal" in migrated["mcp_servers"]
    env = migrated["mcp_servers"]["lancedb-legal"]["env"]
    assert env["HERMES_LANCEDB_PATH"] == "/data/legal"
    assert env["HERMES_REPO_ROOT"] == "/repo"
    assert env["PYTHONIOENCODING"] == "utf-8"
