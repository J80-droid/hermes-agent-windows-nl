"""Overlay: dashboard toolset env + post-setup routes."""

from __future__ import annotations

from overlay.bootstrap import install


def test_web_server_fork_routes_after_bootstrap() -> None:
    install()
    from hermes_cli import web_server as ws

    paths = {getattr(r, "path", "") for r in ws.app.routes}
    assert "/api/tools/toolsets/{name}/env" in paths
    assert "/api/tools/toolsets/{name}/post-setup" in paths
    assert ws._ACTION_LOG_FILES.get("tools-post-setup") == "action-tools-post-setup.log"
