"""Fork-only tui_gateway config.get/set handlers (cost, cost_bar_mode, tps) — no Tier A edits."""
from __future__ import annotations

from typing import Any, Callable


def _display_dict(load_cfg: Callable[[], dict]) -> dict:
    display = load_cfg().get("display")
    return display if isinstance(display, dict) else {}


def handle_config_set_display_fork_key(
    *,
    rid: Any,
    key: str,
    value: Any,
    load_cfg: Callable[[], dict],
    write_config_key: Callable[[str, Any], None],
    ok: Callable[[Any, dict], dict],
    err: Callable[[Any, int, str], dict],
) -> dict | None:
    """Return a JSON-RPC response when *key* is fork-owned; else ``None``."""
    if key == "cost":
        raw = str(value or "").strip().lower()
        current = bool(_display_dict(load_cfg).get("show_cost", True))
        if raw == "status":
            return ok(rid, {"key": key, "value": "on" if current else "off"})
        if raw in {"", "toggle"}:
            nv_b = not current
        elif raw in {"on", "true", "yes", "1"}:
            nv_b = True
        elif raw in {"off", "false", "no", "0"}:
            nv_b = False
        else:
            return err(rid, 4002, f"unknown cost value: {value}")
        write_config_key("display.show_cost", nv_b)
        return ok(rid, {"key": key, "value": "on" if nv_b else "off"})

    if key == "cost_bar_mode":
        raw = str(value or "").strip().lower()
        current = str(_display_dict(load_cfg).get("cost_bar_mode", "rich") or "rich").strip().lower()
        if current not in {"rich", "minimal"}:
            current = "rich"
        if raw in {"", "status"}:
            return ok(rid, {"key": key, "value": current})
        if raw in {"rich", "minimal"}:
            nv = raw
        elif raw == "toggle":
            nv = "minimal" if current == "rich" else "rich"
        else:
            return err(rid, 4002, f"unknown cost_bar_mode value: {value}")
        write_config_key("display.cost_bar_mode", nv)
        return ok(rid, {"key": key, "value": nv})

    if key in {"status_bar_tps", "tps"}:
        raw = str(value or "").strip().lower()
        current = bool(_display_dict(load_cfg).get("show_status_bar_tps", True))
        if raw == "status":
            return ok(rid, {"key": key, "value": "on" if current else "off"})
        if raw in {"", "toggle"}:
            nv_b = not current
        elif raw in {"on", "true", "yes", "1"}:
            nv_b = True
        elif raw in {"off", "false", "no", "0"}:
            nv_b = False
        else:
            return err(rid, 4002, f"unknown status_bar_tps value: {value}")
        write_config_key("display.show_status_bar_tps", nv_b)
        return ok(rid, {"key": key, "value": "on" if nv_b else "off"})

    return None


def handle_config_get_display_fork_key(
    *,
    rid: Any,
    key: str,
    load_cfg: Callable[[], dict],
    ok: Callable[[Any, dict], dict],
) -> dict | None:
    if key == "cost":
        display = load_cfg().get("display")
        if isinstance(display, dict):
            on = bool(display.get("show_cost", True))
        else:
            on = False
        return ok(rid, {"value": "on" if on else "off"})

    if key in {"status_bar_tps", "tps"}:
        display = load_cfg().get("display")
        if isinstance(display, dict):
            on = bool(display.get("show_status_bar_tps", True))
        else:
            on = False
        return ok(rid, {"value": "on" if on else "off"})

    if key == "cost_bar_mode":
        display = load_cfg().get("display")
        raw = (
            str((display or {}).get("cost_bar_mode", "rich") or "rich").strip().lower()
            if isinstance(display, dict)
            else "rich"
        )
        return ok(rid, {"value": raw if raw in {"rich", "minimal"} else "rich"})

    return None


def _patch_get_usage(srv: Any) -> None:
    if getattr(srv, "_fork_usage_snapshot_patch_applied", False):
        return
    orig_get_usage = srv._get_usage

    def _get_usage_fork(agent: Any) -> dict:
        try:
            from hermes_cli.usage_snapshot import build_session_usage_snapshot

            return build_session_usage_snapshot(agent)
        except ImportError:
            return orig_get_usage(agent)

    srv._get_usage = _get_usage_fork
    srv._fork_usage_snapshot_patch_applied = True


def apply_gateway_config_fork_patch() -> None:
    import tui_gateway.server as srv

    if getattr(srv, "_fork_gateway_config_patch_applied", False):
        return

    _patch_get_usage(srv)

    orig_set = srv._methods["config.set"]
    orig_get = srv._methods["config.get"]

    def config_set_patched(rid, params: dict) -> dict:
        key = params.get("key", "")
        fork_resp = handle_config_set_display_fork_key(
            rid=rid,
            key=key,
            value=params.get("value", ""),
            load_cfg=srv._load_cfg,
            write_config_key=srv._write_config_key,
            ok=srv._ok,
            err=srv._err,
        )
        if fork_resp is not None:
            return fork_resp
        return orig_set(rid, params)

    def config_get_patched(rid, params: dict) -> dict:
        key = params.get("key", "")
        fork_resp = handle_config_get_display_fork_key(
            rid=rid,
            key=key,
            load_cfg=srv._load_cfg,
            ok=srv._ok,
        )
        if fork_resp is not None:
            return fork_resp
        return orig_get(rid, params)

    srv._methods["config.set"] = config_set_patched
    srv._methods["config.get"] = config_get_patched
    srv._fork_gateway_config_patch_applied = True
