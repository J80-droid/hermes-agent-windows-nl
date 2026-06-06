"""Overlay: dashboard toolset env + post-setup routes (happy + edge cases)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from overlay.bootstrap import install
from overlay.hermes_cli.web_server_fork_patch import apply_web_server_fork_patch


@pytest.fixture
def ws_module():
    install()
    from hermes_cli import web_server as ws

    return ws


def test_web_server_fork_routes_after_bootstrap(ws_module) -> None:
    paths = {getattr(r, "path", "") for r in ws_module.app.routes}
    assert "/api/tools/toolsets/{name}/env" in paths
    assert "/api/tools/toolsets/{name}/post-setup" in paths
    assert ws_module._ACTION_LOG_FILES.get("tools-post-setup") == "action-tools-post-setup.log"


def test_apply_idempotent_no_duplicate_routes(ws_module) -> None:
    before = len(ws_module.app.routes)
    apply_web_server_fork_patch()
    apply_web_server_fork_patch()
    assert len(ws_module.app.routes) == before


def _find_route_handler(ws, path: str, method: str):
    for route in ws.app.routes:
        if getattr(route, "path", "") != path:
            continue
        methods = getattr(route, "methods", None) or set()
        if method.upper() in methods:
            return route.endpoint
    raise AssertionError(f"route not found: {method} {path}")


def test_save_toolset_env_unknown_toolset(ws_module) -> None:
    handler = _find_route_handler(ws_module, "/api/tools/toolsets/{name}/env", "PUT")
    body = SimpleNamespace(env={"FOO": "bar"})
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(handler("unknown_ts", body))
    assert exc.value.status_code == 400


def test_save_toolset_env_unknown_env_key(ws_module) -> None:
    handler = _find_route_handler(ws_module, "/api/tools/toolsets/{name}/env", "PUT")
    body = SimpleNamespace(env={"NOT_ALLOWED": "x"})
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ), patch("hermes_cli.tools_config.TOOL_CATEGORIES", {"web": {"providers": []}}), patch(
        "hermes_cli.tools_config._visible_providers", return_value=[]
    ), patch.object(ws_module, "load_config", return_value={}):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(handler("web", body))
    assert exc.value.status_code == 400
    assert "Unknown env var" in exc.value.detail


def test_save_toolset_env_skips_blank_values(ws_module) -> None:
    handler = _find_route_handler(ws_module, "/api/tools/toolsets/{name}/env", "PUT")
    body = SimpleNamespace(env={"API_KEY": "  "})
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ), patch(
        "hermes_cli.tools_config.TOOL_CATEGORIES",
        {"web": {"providers": [{"env_vars": [{"key": "API_KEY"}]}]}},
    ), patch(
        "hermes_cli.tools_config._visible_providers",
        return_value=[{"env_vars": [{"key": "API_KEY"}]}],
    ), patch.object(ws_module, "load_config", return_value={}), patch(
        "hermes_cli.config.get_env_value", return_value=None
    ):
        result = asyncio.run(handler("web", body))
    assert result["skipped"] == ["API_KEY"]
    assert result["saved"] == []


def test_run_toolset_post_setup_empty_key(ws_module) -> None:
    handler = _find_route_handler(
        ws_module, "/api/tools/toolsets/{name}/post-setup", "POST"
    )
    body = SimpleNamespace(key="   ")
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(handler("web", body))
    assert exc.value.status_code == 400


def test_run_toolset_post_setup_unknown_key(ws_module) -> None:
    handler = _find_route_handler(
        ws_module, "/api/tools/toolsets/{name}/post-setup", "POST"
    )
    body = SimpleNamespace(key="not_a_real_hook")
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ), patch("hermes_cli.tools_config.valid_post_setup_keys", return_value={"agent_browser"}):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(handler("web", body))
    assert exc.value.status_code == 400


def test_run_toolset_post_setup_spawn_failure(ws_module) -> None:
    handler = _find_route_handler(
        ws_module, "/api/tools/toolsets/{name}/post-setup", "POST"
    )
    body = SimpleNamespace(key="agent_browser")
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ), patch(
        "hermes_cli.tools_config.valid_post_setup_keys", return_value={"agent_browser"}
    ), patch.object(
        ws_module, "_spawn_hermes_action", side_effect=RuntimeError("spawn fail")
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(handler("web", body))
    assert exc.value.status_code == 500


def test_run_toolset_post_setup_happy_path(ws_module) -> None:
    handler = _find_route_handler(
        ws_module, "/api/tools/toolsets/{name}/post-setup", "POST"
    )
    body = SimpleNamespace(key="agent_browser")
    proc = MagicMock(pid=4242)
    with patch(
        "hermes_cli.tools_config._get_effective_configurable_toolsets",
        return_value=[("web", "Web", "desc")],
    ), patch(
        "hermes_cli.tools_config.valid_post_setup_keys", return_value={"agent_browser"}
    ), patch.object(ws_module, "_spawn_hermes_action", return_value=proc) as spawn:
        result = asyncio.run(handler("web", body))
    spawn.assert_called_once_with(["tools", "post-setup", "agent_browser"], "tools-post-setup")
    assert result["ok"] is True
    assert result["pid"] == 4242


def test_skip_register_when_tier_a_has_routes(ws_module) -> None:
    """Routes already present (Tier A or prior apply) → flag set, no duplicate routes."""
    route_count = len(ws_module.app.routes)
    assert "/api/tools/toolsets/{name}/env" in {
        getattr(r, "path", "") for r in ws_module.app.routes
    }
    ws_module._fork_web_server_toolset_routes_applied = False
    apply_web_server_fork_patch()
    assert ws_module._fork_web_server_toolset_routes_applied is True
    assert len(ws_module.app.routes) == route_count
