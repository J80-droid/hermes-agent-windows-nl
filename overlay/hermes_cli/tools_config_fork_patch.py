"""Fork platform_toolsets guards + MCP/kanban checklist + sentinel expansion (Tier B)."""
from __future__ import annotations

from typing import List, Set

_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY = "_user_customized"
PLATFORM_TOOLSET_SENTINELS = frozenset({"mcp", "no_mcp"})

_FORK_TOOLSET_EXTRAS: tuple[tuple[str, str, str], ...] = (
    ("mcp", "🔌 MCP Servers", "search_knowledge, … (per mcp_servers config)"),
    ("kanban", "📌 Kanban Board", "kanban_show, kanban_list, kanban_create, …"),
)


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


def _effective_configurable_keys(tc) -> set[str]:
    return {ts_key for ts_key, _, _ in tc.CONFIGURABLE_TOOLSETS}


def _extend_configurable_toolsets(tc) -> None:
    existing = {ts_key for ts_key, _, _ in tc.CONFIGURABLE_TOOLSETS}
    extras = [entry for entry in _FORK_TOOLSET_EXTRAS if entry[0] not in existing]
    if extras:
        skills_idx = next(
            (i for i, (k, _, _) in enumerate(tc.CONFIGURABLE_TOOLSETS) if k == "skills"),
            len(tc.CONFIGURABLE_TOOLSETS),
        )
        tc.CONFIGURABLE_TOOLSETS[skills_idx + 1 : skills_idx + 1] = extras  # type: ignore[index]


def apply_tools_config_fork_patch() -> None:
    import hermes_cli.tools_config as tc

    if getattr(tc, "_fork_tools_config_patch_applied", False):
        return

    _extend_configurable_toolsets(tc)
    _orig_get = tc._get_platform_tools
    _orig_save = tc._save_platform_tools

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

        names = platform_toolsets.get(platform)
        if isinstance(names, list):
            sanitized = [
                str(ts)
                for ts in names
                if str(ts) not in {_PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY}
            ]
            if sanitized != names:
                config = dict(config)
                config["platform_toolsets"] = dict(platform_toolsets)
                config["platform_toolsets"][platform] = sanitized
                names = sanitized

        user_customized = _platform_toolsets_user_customized(config, platform)
        if user_customized and isinstance(names, list):
            configurable_keys = _effective_configurable_keys(tc)
            return {
                ts
                for ts in names
                if ts in configurable_keys and tc._toolset_allowed_for_platform(ts, platform)
            }

        return _orig_get(
            config,
            platform,
            include_default_mcp_servers=include_default_mcp_servers,
        )

    def _save_platform_tools(config: dict, platform: str, enabled_toolset_keys: Set[str]):
        _orig_save(config, platform, enabled_toolset_keys)
        _mark_platform_toolsets_user_customized(config, platform)

    tc._get_platform_tools = _get_platform_tools  # type: ignore[assignment]
    tc._save_platform_tools = _save_platform_tools  # type: ignore[assignment]
    tc._platform_toolsets_user_customized = _platform_toolsets_user_customized  # type: ignore[attr-defined]
    tc._mark_platform_toolsets_user_customized = _mark_platform_toolsets_user_customized  # type: ignore[attr-defined]
    tc._PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY = _PLATFORM_TOOLSETS_USER_CUSTOMIZED_KEY  # type: ignore[attr-defined]
    if not hasattr(tc, "PLATFORM_TOOLSET_SENTINELS"):
        tc.PLATFORM_TOOLSET_SENTINELS = PLATFORM_TOOLSET_SENTINELS  # type: ignore[attr-defined]
    if not hasattr(tc, "expand_cli_toolset_arg"):
        tc.expand_cli_toolset_arg = expand_cli_toolset_arg  # type: ignore[attr-defined]
    tc._fork_tools_config_patch_applied = True  # type: ignore[attr-defined]
