"""Tests for scripts/repair_cursor_mcp_json.py."""

from __future__ import annotations

import json
from pathlib import Path


def test_load_rejects_case_insensitive_duplicate_servers(tmp_path: Path):
    """playwright + Playwright breaks PowerShell ConvertFrom-Json."""
    from scripts.repair_cursor_mcp_json import _load_mcp_config

    bad = tmp_path / "mcp.json"
    bad.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "playwright": {"command": "npx"},
                    "Playwright": {"command": "npx"},
                }
            }
        ),
        encoding="utf-8",
    )
    try:
        _load_mcp_config(bad, strict=True)
        raised = False
    except ValueError as exc:
        raised = True
        assert "Case-insensitive duplicate" in str(exc)
    assert raised


def test_repair_merges_playwright_and_disables_placeholders(tmp_path: Path):
    from scripts.repair_cursor_mcp_json import repair_file

    path = tmp_path / "mcp.json"
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "playwright": {"command": "npx", "args": ["-y", "old"], "enabled": True},
                    "Playwright": {"command": "npx @playwright/mcp@latest"},
                    "dbt Labs": {
                        "command": "uvx dbt-mcp",
                        "env": {"DBT_TOKEN": "your-service-token"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    changes = repair_file(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data["mcpServers"]
    assert "Playwright" not in servers
    assert servers["playwright"]["args"] == ["-y", "@playwright/mcp@latest", "--vision"]
    assert servers["dbt Labs"]["enabled"] is False
    assert any("playwright" in c for c in changes)
