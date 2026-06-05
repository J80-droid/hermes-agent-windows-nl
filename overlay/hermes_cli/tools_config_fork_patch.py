"""Fork toolset resolution: explicit empty ``cli: []`` disables auto MCP/plugins."""
from __future__ import annotations

from typing import Set

_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY = "_user_customized"


def _platform_toolsets_user_customized(config: dict, platform: str) -> bool:
    pt = config.get("platform_toolsets")
    if not isinstance(pt, dict):
        return False
    meta = pt.get(_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY)
    if isinstance(meta, dict):
        return bool(meta.get(platform))
    return bool(meta)


def _mark_platform_toolsets_user_customized(config: dict, platform: str) -> None:
    config.setdefault("platform_toolsets", {})
    pt = config["platform_toolsets"]
    meta = pt.get(_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY)
    if not isinstance(meta, dict):
        meta = {}
        pt[_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY] = meta
    meta[platform] = True


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
    tc._platform_toolsets_user_customized = _platform_toolsets_user_customized  # type: ignore[attr-defined]
    tc._mark_platform_toolsets_user_customized = _mark_platform_toolsets_user_customized  # type: ignore[attr-defined]
    tc._PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY = _PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY  # type: ignore[attr-defined]
    tc._fork_tools_config_patch_applied = True  # type: ignore[attr-defined]
