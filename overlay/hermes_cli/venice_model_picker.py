"""Venice-specific helpers for model pickers and ``/model`` switches.

Used by:
- ``hermes model`` / setup wizard (interactive CLI)
- Telegram gateway ``/model`` inline picker (``vf:*`` callbacks)
- ``model_switch.switch_model`` (OpenAI name → Venice id via compatibility_mapping)
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

_TELEGRAM_CALLBACK_DATA_MAX = 64
from agent.venice_usage import (
    fetch_venice_compatibility_mapping,
    fetch_venice_model_traits,
    filter_models_by_venice_trait,
    resolve_venice_openai_model,
)


def run_venice_model_picker_preflight(
    *,
    api_key: str,
    base_url: str,
    models: list[str],
    timeout: float = 8.0,
) -> tuple[list[str], Optional[str]]:
    """Optional Venice filters before the standard model list UI.

    Returns ``(models_to_show, preset_model_id)``. When ``preset_model_id`` is set,
    the caller may skip the radiolist and persist that model directly.
    """
    traits, traits_err = fetch_venice_model_traits(
        base_url=base_url, api_key=api_key, timeout=timeout
    )
    mapping, mapping_err = fetch_venice_compatibility_mapping(
        base_url=base_url, api_key=api_key, timeout=timeout
    )
    if not traits and not mapping:
        if traits_err or mapping_err:
            print("  Venice model metadata unavailable (continuing with full model list).")
            if traits_err:
                print(f"    traits: {traits_err}")
            if mapping_err:
                print(f"    mapping: {mapping_err}")
        return list(models), None

    print()
    print("  Venice model helpers (GET /models/traits, /models/compatibility_mapping):")
    if mapping:
        for openai_name, venice_id in list(mapping.items())[:8]:
            print(f"    {openai_name} → {venice_id}")
        if len(mapping) > 8:
            print(f"    … {len(mapping) - 8} more mappings")
    options: list[tuple[str, str]] = [("all", "Browse all models")]
    if traits:
        options.append(("trait", "Filter by trait"))
    if mapping:
        options.append(("openai", "Resolve OpenAI model name (e.g. gpt-4o)"))
    options.append(("skip", "Skip helpers"))

    for idx, (_key, label) in enumerate(options, 1):
        print(f"  {idx}. {label}")

    try:
        raw = input(f"  Choice [1-{len(options)}] (default 1): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return list(models), None

    if not raw:
        choice_idx = 0
    else:
        try:
            choice_idx = int(raw) - 1
        except ValueError:
            print("  Invalid choice — showing all models.")
            return list(models), None
    if choice_idx < 0 or choice_idx >= len(options):
        print("  Invalid choice — showing all models.")
        return list(models), None

    choice_key = options[choice_idx][0]
    if choice_key in {"all", "skip"}:
        return list(models), None
    if choice_key == "trait":
        return _prompt_trait_filter(models, traits)
    if choice_key == "openai":
        return _prompt_openai_mapping(models, mapping)
    return list(models), None


def _prompt_trait_filter(
    models: list[str],
    traits: dict[str, str],
) -> tuple[list[str], Optional[str]]:
    if not traits:
        print("  No traits returned.")
        return list(models), None
    trait_names = sorted(traits.keys())
    print()
    print("  Traits (text):")
    for idx, trait in enumerate(trait_names, 1):
        print(f"    {idx}. {trait} → {traits[trait]}")
    print("    0. Back (all models)")
    try:
        raw = input(f"  Trait [1-{len(trait_names)}, 0=all]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return list(models), None
    if not raw or raw == "0":
        return list(models), None
    try:
        trait_idx = int(raw) - 1
    except ValueError:
        print("  Invalid choice — showing all models.")
        return list(models), None
    if trait_idx < 0 or trait_idx >= len(trait_names):
        print("  Invalid choice — showing all models.")
        return list(models), None
    trait_name = trait_names[trait_idx]
    trait_model = traits[trait_name]
    filtered = filter_models_by_venice_trait(models, trait_model)
    print(f"  Trait '{trait_name}' → {trait_model} ({len(filtered)} model(s))")
    if not filtered:
        print("  No matching models in /v1/models — using trait model id.")
        return [trait_model], trait_model
    if len(filtered) == 1:
        only = filtered[0]
        try:
            confirm = input(f"  Use {only}? [Y/n]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return list(models), None
        if confirm in {"", "y", "yes"}:
            return filtered, only
    return filtered, None


def _prompt_openai_mapping(
    models: list[str],
    mapping: dict[str, str],
) -> tuple[list[str], Optional[str]]:
    try:
        openai_name = input("  OpenAI model name (e.g. gpt-4o): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return list(models), None
    if not openai_name:
        return list(models), None
    venice_id = resolve_venice_openai_model(openai_name, mapping)
    if not venice_id:
        print(f"  No Venice mapping for '{openai_name}'.")
        return list(models), None
    print(f"  Mapped: {openai_name} → {venice_id}")
    try:
        confirm = input(f"  Use {venice_id}? [Y/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return list(models), None
    if confirm not in {"", "y", "yes"}:
        return list(models), None
    if venice_id in models:
        return models, venice_id
    print("  Model not in live /v1/models list — selecting mapped id anyway.")
    return [venice_id] + [m for m in models if m != venice_id], venice_id


def resolve_venice_api_key(*, provider_slug: str = "") -> str:
    """Resolve Venice API key from env (``VENICE_API_KEY`` / ``key_env`` in root config)."""
    key = str(os.environ.get("VENICE_API_KEY", "") or "").strip()
    if key:
        return key
    try:
        from hermes_cli.config import get_env_value

        key = str(get_env_value("VENICE_API_KEY") or "").strip()
        if key:
            return key
    except Exception:
        pass
    slug = str(provider_slug or "").strip().lower()
    if not slug:
        slug = "venice"
    try:
        from hermes_cli.config import load_config_readonly

        cfg = load_config_readonly() or {}
        providers = cfg.get("providers")
        if isinstance(providers, dict):
            entry = providers.get(slug) or providers.get("venice")
            if isinstance(entry, dict):
                key_env = str(
                    entry.get("key_env") or entry.get("api_key_env") or ""
                ).strip()
                if key_env:
                    return str(os.environ.get(key_env, "") or "").strip()
    except Exception:
        pass
    return ""


def load_venice_picker_metadata(
    *,
    api_key: str,
    base_url: str,
    timeout: float = 8.0,
) -> tuple[dict[str, str], dict[str, str], Optional[str], Optional[str]]:
    """Fetch traits + OpenAI compatibility mapping for gateway/CLI pickers (parallel)."""
    if not api_key:
        return {}, {}, "VENICE_API_KEY not set", None

    def _traits() -> tuple[dict[str, str], Optional[str]]:
        data, err = fetch_venice_model_traits(
            base_url=base_url, api_key=api_key, timeout=timeout
        )
        return data or {}, err

    def _mapping() -> tuple[dict[str, str], Optional[str]]:
        data, err = fetch_venice_compatibility_mapping(
            base_url=base_url, api_key=api_key, timeout=timeout
        )
        return data or {}, err

    with ThreadPoolExecutor(max_workers=2) as pool:
        traits_future = pool.submit(_traits)
        mapping_future = pool.submit(_mapping)
        traits, traits_err = traits_future.result()
        mapping, mapping_err = mapping_future.result()
    return traits, mapping, traits_err, mapping_err


def venice_trait_names_sorted(traits: dict[str, str]) -> list[str]:
    return sorted(traits.keys())


def venice_openai_names_sorted(mapping: dict[str, str]) -> list[str]:
    return sorted(mapping.keys())


def build_venice_helper_button_rows(
    traits: dict[str, str],
    mapping: dict[str, str],
    *,
    max_traits: int = 6,
    max_openai: int = 6,
) -> list[list[tuple[str, str]]]:
    """Rows of ``(callback_data, label)`` for Telegram inline keyboards."""
    rows: list[list[tuple[str, str]]] = [[("vf:all", "All models")]]
    for i, name in enumerate(venice_trait_names_sorted(traits)[:max_traits]):
        label = name if len(name) <= 24 else f"{name[:21]}..."
        cb = f"vf:t:{i}"
        if len(cb) <= _TELEGRAM_CALLBACK_DATA_MAX:
            rows.append([(cb, f"Trait: {label}")])
    for i, name in enumerate(venice_openai_names_sorted(mapping)[:max_openai]):
        label = name if len(name) <= 24 else f"{name[:21]}..."
        cb = f"vf:o:{i}"
        if len(cb) <= _TELEGRAM_CALLBACK_DATA_MAX:
            rows.append([(cb, f"OpenAI: {label}")])
    rows.append([("mb", "◀ Back"), ("mx", "✗ Cancel")])
    return rows


def apply_venice_helper_callback(
    callback: str,
    models: list[str],
    traits: dict[str, str],
    mapping: dict[str, str],
) -> tuple[list[str], Optional[str]]:
    """Apply a Venice helper choice (callback body after ``vf:``)."""
    if callback == "all":
        return list(models), None
    if callback.startswith("t:"):
        try:
            idx = int(callback[2:])
        except ValueError:
            return list(models), None
        names = venice_trait_names_sorted(traits)
        if idx < 0 or idx >= len(names):
            return list(models), None
        return _apply_trait_choice(models, traits, names[idx])
    if callback.startswith("o:"):
        try:
            idx = int(callback[2:])
        except ValueError:
            return list(models), None
        openai_names = venice_openai_names_sorted(mapping)
        if idx < 0 or idx >= len(openai_names):
            return list(models), None
        openai_name = openai_names[idx]
        venice_id = resolve_venice_openai_model(openai_name, mapping)
        if not venice_id:
            return list(models), None
        if venice_id in models:
            return models, venice_id
        return [venice_id] + [m for m in models if m != venice_id], venice_id
    return list(models), None


def _apply_trait_choice(
    models: list[str],
    traits: dict[str, str],
    trait_name: str,
) -> tuple[list[str], Optional[str]]:
    trait_model = traits.get(trait_name, "")
    if not trait_model:
        return list(models), None
    filtered = filter_models_by_venice_trait(models, trait_model)
    if not filtered:
        return [trait_model], trait_model
    if len(filtered) == 1:
        return filtered, filtered[0]
    return filtered, None


def resolve_venice_model_for_switch(
    raw_model: str,
    *,
    api_key: str,
    base_url: str,
    timeout: float = 8.0,
) -> str:
    """Map OpenAI-style model ids to Venice ids when compatibility data exists."""
    name = str(raw_model or "").strip()
    if not name or not api_key:
        return name
    mapping, _mapping_err = fetch_venice_compatibility_mapping(
        base_url=base_url, api_key=api_key, timeout=timeout
    )
    if not mapping:
        return name
    mapped = resolve_venice_openai_model(name, mapping)
    return mapped or name
