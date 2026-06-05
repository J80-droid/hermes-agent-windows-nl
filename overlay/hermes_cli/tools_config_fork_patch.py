"""Fork toolset resolution: explicit empty ``cli: []`` disables auto MCP/plugins."""
from __future__ import annotations

from typing import Set


def apply_tools_config_fork_patch() -> None:
    import hermes_cli.tools_config as tc

    if getattr(tc, "_fork_tools_config_patch_applied", False):
        return

    _orig = tc._get_platform_tools

    def _get_platform_tools(
        config: dict,
        platform: str,
        *,
        include_default_mcp_servers: bool = True,
    ) -> Set[str]:
        platform_toolsets = config.get("platform_toolsets") or {}
        if (
            platform in platform_toolsets
            and isinstance(platform_toolsets.get(platform), list)
            and not platform_toolsets.get(platform)
        ):
            return set()
        return _orig(
            config,
            platform,
            include_default_mcp_servers=include_default_mcp_servers,
        )

    tc._get_platform_tools = _get_platform_tools  # type: ignore[assignment]
    tc._fork_tools_config_patch_applied = True  # type: ignore[attr-defined]
