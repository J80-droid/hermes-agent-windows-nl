"""Fork toolset resolution + dashboard post-setup CLI (Tier B; no Tier A edits)."""
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


def valid_post_setup_keys() -> Set[str]:
    """Allowlist of declared post-setup hook keys (CLI + dashboard)."""
    import hermes_cli.tools_config as tc

    keys: Set[str] = set()
    for cat in tc.TOOL_CATEGORIES.values():
        for prov in cat.get("providers", []):
            ps = prov.get("post_setup")
            if ps:
                keys.add(ps)
    for builder in (
        tc._plugin_web_search_providers,
        tc._plugin_image_gen_providers,
        tc._plugin_video_gen_providers,
        tc._plugin_browser_providers,
    ):
        try:
            for prov in builder():
                ps = prov.get("post_setup")
                if ps:
                    keys.add(ps)
        except Exception:  # pragma: no cover — plugins optional
            continue
    return keys


def run_post_setup_command(args) -> int:
    """``hermes tools post-setup <key>`` — non-interactive install hook runner."""
    import hermes_cli.tools_config as tc

    key = getattr(args, "post_setup_key", None)
    if not key:
        tc._print_error("Usage: hermes tools post-setup <key>")
        return 2
    valid = valid_post_setup_keys()
    if key not in valid:
        tc._print_error(
            f"Unknown post-setup key: {key!r}. "
            f"Valid keys: {', '.join(sorted(valid)) or '(none)'}"
        )
        return 2
    tc._print_info(f"Running post-setup hook: {key}")
    try:
        tc._run_post_setup(key)
    except Exception as exc:  # pragma: no cover — defensive
        tc._print_error(f"Post-setup failed: {exc}")
        return 1
    tc._print_success(f"Post-setup '{key}' complete")
    return 0


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
    if not hasattr(tc, "valid_post_setup_keys"):
        tc.valid_post_setup_keys = valid_post_setup_keys  # type: ignore[attr-defined]
    if not hasattr(tc, "run_post_setup_command"):
        tc.run_post_setup_command = run_post_setup_command  # type: ignore[attr-defined]
    tc._fork_tools_config_patch_applied = True  # type: ignore[attr-defined]
