"""Fork platform_toolsets guards + MCP sentinel expansion (Tier B)."""
from __future__ import annotations

from typing import List, Set

_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY = "_user_customized"
PLATFORM_TOOLSET_SENTINELS = frozenset({"mcp", "no_mcp"})


def expand_cli_toolset_arg(toolsets: list[str] | set[str], config: dict) -> List[str]:
    """Expand ``mcp`` sentinel to MCP server names for ``hermes chat --toolsets``."""
    import hermes_cli.tools_config as tc

    raw = [str(t).strip() for t in toolsets if str(t).strip()]
    if not raw or "all" in raw or "*" in raw:
        return raw
    mcp_servers = config.get("mcp_servers") if isinstance(config, dict) else None
    enabled_mcp: list[str] = []
    if isinstance(mcp_servers, dict):
        for name, cfg in mcp_servers.items():
            key = str(name).strip()
            if not key:
                continue
            if isinstance(cfg, dict) and not tc._parse_enabled_flag(cfg.get("enabled", True), default=True):
                continue
            enabled_mcp.append(key)
    expanded: list[str] = []
    for entry in raw:
        if entry == "mcp":
            expanded.extend(enabled_mcp)
        elif entry == "no_mcp":
            continue
        else:
            expanded.append(entry)
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in expanded:
        if entry not in seen:
            seen.add(entry)
            ordered.append(entry)
    return ordered


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
    if not hasattr(tc, "PLATFORM_TOOLSET_SENTINELS"):
        tc.PLATFORM_TOOLSET_SENTINELS = PLATFORM_TOOLSET_SENTINELS  # type: ignore[attr-defined]
    if not hasattr(tc, "expand_cli_toolset_arg"):
        tc.expand_cli_toolset_arg = expand_cli_toolset_arg  # type: ignore[attr-defined]
    tc._fork_tools_config_patch_applied = True  # type: ignore[attr-defined]
