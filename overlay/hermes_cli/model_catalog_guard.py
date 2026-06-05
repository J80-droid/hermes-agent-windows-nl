"""Fork model-catalog guard helpers (overlay; Tier A hermes_cli/models.py unchanged)."""
from __future__ import annotations

from typing import Iterable, Optional

from hermes_cli.models import (
    normalize_provider,
    provider_model_ids,
    validate_requested_model,
)

_MODEL_VARIANT_SUFFIXES: tuple[str, ...] = (":free", ":extended", ":fast")


def _catalog_match_keys(model_id: str) -> set[str]:
    low = (model_id or "").strip().lower()
    if not low:
        return set()
    keys: set[str] = {low}
    for suffix in _MODEL_VARIANT_SUFFIXES:
        if low.endswith(suffix):
            stripped = low[: -len(suffix)]
            if stripped:
                keys.add(stripped)
    return keys


def _union_catalog_match_keys(catalog: Iterable[str]) -> set[str]:
    merged: set[str] = set()
    for mid in catalog:
        merged |= _catalog_match_keys(mid)
    return merged


def model_matches_provider_catalog(model_id: str, catalog: Iterable[str]) -> bool:
    wanted = _catalog_match_keys(model_id)
    if not wanted:
        return False
    catalog_keys = _union_catalog_match_keys(catalog)
    return bool(wanted & catalog_keys)


def model_default_passes_startup_catalog_guard(
    provider: Optional[str],
    default_model: str,
    *,
    force_refresh: bool = False,
) -> bool:
    normalized = normalize_provider(provider)
    requested = (default_model or "").strip()
    if not normalized or not requested:
        return True
    if normalized in {"custom", "auto"}:
        return True

    catalog: list[str] = []
    try:
        catalog = list(provider_model_ids(normalized, force_refresh=force_refresh) or [])
    except Exception:
        catalog = []

    if catalog and model_matches_provider_catalog(requested, catalog):
        return True

    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        model_cfg = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
        base_url = str(model_cfg.get("base_url") or "").strip() or None
        api_key: Optional[str] = None
        if normalized == "nous":
            try:
                from hermes_cli.auth import resolve_nous_runtime_credentials

                creds = resolve_nous_runtime_credentials()
                if creds:
                    api_key = str(creds.get("api_key") or "").strip() or None
                    if not base_url:
                        base_url = str(creds.get("base_url") or "").strip() or None
            except Exception:
                pass
        validation = validate_requested_model(
            requested,
            normalized,
            api_key=api_key,
            base_url=base_url,
        )
        return bool(validation.get("accepted"))
    except Exception:
        return not catalog
