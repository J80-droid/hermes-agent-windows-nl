"""Patch upstream usage_pricing with fork Google Gemini catalog (Tier B)."""
from __future__ import annotations

from typing import Any


def apply_pricing_fork_patch() -> None:
    import agent.usage_pricing as up

    if getattr(up, "_fork_google_pricing_patch_applied", False):
        return
    from overlay.agent.google_gemini_pricing import try_google_pricing_entry

    _orig = up.get_pricing_entry

    def get_pricing_entry(model_name: str, *args: Any, **kwargs: Any) -> Any:
        entry = try_google_pricing_entry(model_name, *args, **kwargs)
        if entry is not None:
            return entry
        return _orig(model_name, *args, **kwargs)

    get_pricing_entry.__name__ = getattr(_orig, "__name__", "get_pricing_entry")
    up.get_pricing_entry = get_pricing_entry  # type: ignore[method-assign]
    up._fork_google_pricing_patch_applied = True
