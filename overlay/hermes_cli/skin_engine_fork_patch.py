"""Fork status-bar style tokens for prompt_toolkit (cost + throughput)."""
from __future__ import annotations


def apply_skin_engine_fork_patch() -> None:
    import hermes_cli.skin_engine as skin_mod

    if getattr(skin_mod, "_fork_skin_engine_patch_applied", False):
        return

    _orig = skin_mod.get_prompt_toolkit_style_overrides

    def get_prompt_toolkit_style_overrides():
        overrides = dict(_orig())
        try:
            skin = skin_mod.get_active_skin()
            status_bg = skin.get_color("status_bar_bg", "#1a1a2e")
            cost_color = skin.get_color("status_cost", "#6B9BD1")
            tps_color = skin.get_color("status_tps", "#A8A8A8")
        except Exception:
            status_bg = "#1a1a2e"
            cost_color = "#6B9BD1"
            tps_color = "#A8A8A8"
        overrides.setdefault("status-bar-cost", f"bg:{status_bg} {cost_color}")
        overrides.setdefault("status-bar-tps", f"bg:{status_bg} {tps_color}")
        return overrides

    skin_mod.get_prompt_toolkit_style_overrides = get_prompt_toolkit_style_overrides  # type: ignore[assignment]
    skin_mod._fork_skin_engine_patch_applied = True  # type: ignore[attr-defined]
