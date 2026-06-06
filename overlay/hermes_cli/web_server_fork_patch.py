"""Dashboard toolset env + post-setup routes (Tier B overlay)."""
from __future__ import annotations

from typing import Any, Dict, List


def apply_web_server_fork_patch() -> None:
    import hermes_cli.web_server as ws

    if getattr(ws, "_fork_web_server_toolset_routes_applied", False):
        return

    existing_paths = {getattr(r, "path", "") for r in ws.app.routes}
    if "/api/tools/toolsets/{name}/env" in existing_paths:
        ws._fork_web_server_toolset_routes_applied = True  # type: ignore[attr-defined]
        return

    from fastapi import HTTPException
    from pydantic import BaseModel

    ws._ACTION_LOG_FILES.setdefault("tools-post-setup", "action-tools-post-setup.log")

    class ToolsetEnvUpdate(BaseModel):
        env: Dict[str, str]

    class ToolsetPostSetup(BaseModel):
        key: str

    async def save_toolset_env(name: str, body: ToolsetEnvUpdate) -> Dict[str, Any]:
        from hermes_cli.config import get_env_value, save_env_value
        from hermes_cli.tools_config import (
            TOOL_CATEGORIES,
            _get_effective_configurable_toolsets,
            _visible_providers,
        )

        valid_ts = {ts_key for ts_key, _, _ in _get_effective_configurable_toolsets()}
        if name not in valid_ts:
            raise HTTPException(status_code=400, detail=f"Unknown toolset: {name}")

        config = ws.load_config()
        cat = TOOL_CATEGORIES.get(name)
        allowed: set[str] = set()
        if cat:
            for prov in _visible_providers(cat, config, force_fresh=True):
                for e in prov.get("env_vars", []):
                    allowed.add(e["key"])

        unknown = [k for k in body.env if k not in allowed]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown env var(s) for toolset {name}: {', '.join(sorted(unknown))}",
            )

        saved: List[str] = []
        skipped: List[str] = []
        for key, value in body.env.items():
            if value and value.strip():
                try:
                    save_env_value(key, value.strip())
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
                saved.append(key)
            else:
                skipped.append(key)

        status = {k: bool(get_env_value(k)) for k in allowed}
        return {
            "ok": True,
            "name": name,
            "saved": saved,
            "skipped": skipped,
            "is_set": status,
        }

    async def run_toolset_post_setup(name: str, body: ToolsetPostSetup) -> Dict[str, Any]:
        from hermes_cli.tools_config import (
            _get_effective_configurable_toolsets,
            valid_post_setup_keys,
        )

        valid_ts = {ts_key for ts_key, _, _ in _get_effective_configurable_toolsets()}
        if name not in valid_ts:
            raise HTTPException(status_code=400, detail=f"Unknown toolset: {name}")

        if body.key not in valid_post_setup_keys():
            raise HTTPException(
                status_code=400, detail=f"Unknown post-setup key: {body.key}"
            )

        try:
            proc = ws._spawn_hermes_action(
                ["tools", "post-setup", body.key], "tools-post-setup"
            )
        except Exception as exc:
            ws._log.exception("Failed to spawn tools post-setup")
            raise HTTPException(
                status_code=500, detail=f"Failed to run post-setup: {exc}"
            ) from exc
        return {
            "ok": True,
            "pid": proc.pid,
            "name": "tools-post-setup",
            "key": body.key,
        }

    ws.app.add_api_route(
        "/api/tools/toolsets/{name}/env",
        save_toolset_env,
        methods=["PUT"],
        tags=["tools"],
    )
    ws.app.add_api_route(
        "/api/tools/toolsets/{name}/post-setup",
        run_toolset_post_setup,
        methods=["POST"],
        tags=["tools"],
    )
    ws._fork_web_server_toolset_routes_applied = True  # type: ignore[attr-defined]
