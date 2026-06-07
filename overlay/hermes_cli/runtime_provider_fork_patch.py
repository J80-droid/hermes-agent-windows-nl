"""Fork runtime_provider: profile .env via get_env_value + api_key_env alias."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _resolve_provider_api_key(entry: dict, rp_mod) -> str:
    get_env_value = getattr(rp_mod, "get_env_value", None)
    for hint in ("key_env", "api_key_env"):
        key_env = str(entry.get(hint) or "").strip()
        if key_env and callable(get_env_value):
            val = get_env_value(key_env) or ""
            if str(val).strip():
                return str(val).strip()
    return str(entry.get("api_key", "") or "").strip()


def apply_runtime_provider_fork_patch() -> None:
    import hermes_cli.runtime_provider as rp

    if getattr(rp, "_fork_runtime_provider_patch_applied", False):
        return

    from hermes_cli.config import get_env_value

    rp.get_env_value = get_env_value  # type: ignore[attr-defined]

    _orig_named = rp._get_named_custom_provider

    def _get_named_custom_provider(requested_provider: str) -> Optional[Dict[str, Any]]:
        result = _orig_named(requested_provider)
        requested_norm = rp._normalize_custom_provider_name(requested_provider or "")
        config = rp.load_config()
        providers = config.get("providers")
        if not isinstance(providers, dict):
            return result

        for ep_name, entry in providers.items():
            if not isinstance(entry, dict):
                continue
            name_norm = rp._normalize_custom_provider_name(str(ep_name))
            display_name = str(entry.get("name", "") or "")
            display_norm = (
                rp._normalize_custom_provider_name(display_name) if display_name else ""
            )
            aliases = {ep_name, name_norm, f"custom:{name_norm}"}
            if display_name:
                aliases |= {display_name, display_norm, f"custom:{display_norm}"}
            if requested_norm not in aliases:
                continue
            base_url = (
                entry.get("api")
                or entry.get("url")
                or entry.get("base_url")
                or (result or {}).get("base_url")
                or ""
            )
            if not str(base_url).strip():
                continue
            api_key = _resolve_provider_api_key(entry, rp)
            out: Dict[str, Any] = dict(result or {})
            out.update(
                {
                    "name": entry.get("name", ep_name),
                    "base_url": str(base_url).strip(),
                    "api_key": api_key or out.get("api_key", ""),
                    "model": entry.get("default_model", out.get("model", "")),
                }
            )
            api_mode = rp._parse_api_mode(entry.get("api_mode") or entry.get("transport"))
            if api_mode:
                out["api_mode"] = api_mode
            return out
        return result

    rp._get_named_custom_provider = _get_named_custom_provider  # type: ignore[assignment]
    rp._fork_runtime_provider_patch_applied = True  # type: ignore[attr-defined]
