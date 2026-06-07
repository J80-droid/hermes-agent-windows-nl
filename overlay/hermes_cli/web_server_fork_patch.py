"""Fork web_server routes (assistant display settings)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def _get_assistant_display_settings_handler():
    """Live assistant render settings (same source as CLI/gateway Rich pipeline)."""
    try:
        from hermes_cli.display_markdown import get_assistant_render_settings

        return get_assistant_render_settings()
    except Exception:
        logger.exception("GET /api/display/assistant failed")
        return {
            "assistant_render_style": "institutional_rich",
            "assistant_palette": "demo",
            "assistant_label_columns": True,
        }


def apply_web_server_fork_patch() -> None:
    import hermes_cli.web_server as ws

    if getattr(ws, "_fork_web_server_patch_applied", False):
        return

    if "/api/display/assistant" not in ws._PUBLIC_API_PATHS:
        ws._PUBLIC_API_PATHS = frozenset(  # type: ignore[misc]
            set(ws._PUBLIC_API_PATHS) | {"/api/display/assistant"}
        )

    paths = {
        getattr(route, "path", None)
        for route in ws.app.routes
    }
    if "/api/display/assistant" not in paths:
        ws.app.add_api_route(
            "/api/display/assistant",
            _get_assistant_display_settings_handler,
            methods=["GET"],
        )
        # Ensure the route wins over the SPA catch-all when mounted mid-process.
        for idx, route in enumerate(ws.app.routes):
            if getattr(route, "path", None) == "/api/display/assistant":
                ws.app.routes.insert(0, ws.app.routes.pop(idx))
                break

    ws._fork_web_server_patch_applied = True  # type: ignore[attr-defined]
