"""Gateway model persistence via persist_model_runtime (root + auth sync)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_APPLIED = False


def apply_gateway_model_switch_fork_patch() -> None:
    global _APPLIED
    if _APPLIED:
        return

    try:
        import tui_gateway.server as srv
    except ImportError:
        return

    if getattr(srv, "_fork_model_switch_patch_applied", False):
        _APPLIED = True
        return

    _orig = srv._persist_model_switch

    def _persist_model_switch(result: Any) -> None:
        from overlay.hermes_cli.model_switch_persist_fork_patch import (
            persist_global_model_switch,
        )

        try:
            persist_global_model_switch(
                provider=str(getattr(result, "target_provider", "") or ""),
                default_model=str(getattr(result, "new_model", "") or ""),
                base_url=str(getattr(result, "base_url", "") or ""),
                api_mode=getattr(result, "api_mode", None),
            )
        except Exception:
            logger.exception("gateway persist_model_runtime failed; falling back")
            _orig(result)

    srv._persist_model_switch = _persist_model_switch  # type: ignore[assignment]
    srv._fork_model_switch_patch_applied = True
    _APPLIED = True
