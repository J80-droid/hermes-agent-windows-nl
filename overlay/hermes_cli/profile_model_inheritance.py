"""
Profiel → root overerving voor globale config-blokken.

Domein-profielen (legal, core, …) bevatten **geen** vast ``model:``, ``auxiliary:``
of ``providers:`` — wijzig die eenmalig in root ``config.yaml`` (``hermes model``,
auxiliary preset, custom providers).

Belangrijk:
- ``root_config_path()`` gebruikt altijd ``get_default_hermes_root()`` (niet profiel-``HERMES_HOME``).
- ``apply_profile_root_config_inheritance()`` leest root YAML één keer per load.
- ``bust_config_caches(root_path)`` leegt alle load/raw caches (profielen hangen af van root).
- ``save_config()`` redirect naar root alleen als de key expliciet in de meegegeven ``config`` dict staat.
- ``profile_has_global_config_blocks`` / ``list_profiles_with_global_config_blocks`` —
  YAML top-level keys (geen comment false-positives); ``strip_all_profile_global_blocks``
  voor doctor ``--fix`` en migratie.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

PROFILE_MODEL_INHERIT_KEY = "inherit"
PROFILE_AUXILIARY_INHERIT_KEY = "inherit"
PROFILE_PROVIDERS_INHERIT_KEY = "inherit"


def is_profile_hermes_home(home: Path | None = None) -> bool:
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    try:
        return path.parent.name == "profiles"
    except (TypeError, ValueError):
        return False


def root_config_path() -> Path:
    from hermes_constants import get_default_hermes_root

    return get_default_hermes_root() / "config.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def profile_has_explicit_model_override(profile_model: Any) -> bool:
    """True alleen bij ``model.inherit: false`` (bewuste uitzondering)."""
    if not isinstance(profile_model, dict):
        return False
    return profile_model.get(PROFILE_MODEL_INHERIT_KEY) is False


def resolve_model_section(
    profile_user_config: dict[str, Any] | None,
    *,
    root_user_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Effectief model-blok voor een profiel (standaard: volledig van root)."""
    root_user = root_user_config if root_user_config is not None else _read_yaml(root_config_path())
    root_model = copy.deepcopy(root_user.get("model") or {})
    if not isinstance(root_model, dict):
        return {}

    profile_user = profile_user_config or {}
    profile_model = profile_user.get("model")

    if profile_has_explicit_model_override(profile_model):
        if isinstance(profile_model, dict):
            overrides = {
                k: v
                for k, v in profile_model.items()
                if k != PROFILE_MODEL_INHERIT_KEY
            }
            return _deep_merge_dict(copy.deepcopy(root_model), overrides)
        return copy.deepcopy(root_model)

    return root_model


def apply_profile_model_inheritance(
    merged_config: dict[str, Any],
    profile_user_config: dict[str, Any] | None,
) -> dict[str, Any]:
    if not is_profile_hermes_home():
        return merged_config
    merged_config["model"] = resolve_model_section(profile_user_config)
    return merged_config


def profile_has_explicit_auxiliary_override(profile_auxiliary: Any) -> bool:
    if not isinstance(profile_auxiliary, dict):
        return False
    return profile_auxiliary.get(PROFILE_AUXILIARY_INHERIT_KEY) is False


def profile_has_explicit_providers_override(profile_providers: Any) -> bool:
    if not isinstance(profile_providers, dict):
        return False
    return profile_providers.get(PROFILE_PROVIDERS_INHERIT_KEY) is False


def resolve_auxiliary_section(
    profile_user_config: dict[str, Any] | None,
    *,
    root_user_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Effectief auxiliary-blok voor een profiel (standaard: volledig van root)."""
    root_user = root_user_config if root_user_config is not None else _read_yaml(root_config_path())
    root_aux = copy.deepcopy(root_user.get("auxiliary") or {})
    if not isinstance(root_aux, dict):
        return {}

    profile_user = profile_user_config or {}
    profile_aux = profile_user.get("auxiliary")

    if profile_has_explicit_auxiliary_override(profile_aux):
        if isinstance(profile_aux, dict):
            overrides = {
                k: v
                for k, v in profile_aux.items()
                if k != PROFILE_AUXILIARY_INHERIT_KEY
            }
            return _deep_merge_dict(copy.deepcopy(root_aux), overrides)
        return copy.deepcopy(root_aux)

    return root_aux


def resolve_providers_sections(
    profile_user_config: dict[str, Any] | None,
    *,
    root_user_config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[Any]]:
    """Effectieve providers + custom_providers (standaard: volledig van root)."""
    root_user = root_user_config if root_user_config is not None else _read_yaml(root_config_path())
    root_providers = copy.deepcopy(root_user.get("providers") or {})
    root_custom = copy.deepcopy(root_user.get("custom_providers") or [])
    if not isinstance(root_providers, dict):
        root_providers = {}
    if not isinstance(root_custom, list):
        root_custom = []

    profile_user = profile_user_config or {}
    profile_providers = profile_user.get("providers")

    if profile_has_explicit_providers_override(profile_providers):
        if isinstance(profile_providers, dict):
            prov_overrides = {
                k: v
                for k, v in profile_providers.items()
                if k != PROFILE_PROVIDERS_INHERIT_KEY
            }
            merged_providers = _deep_merge_dict(copy.deepcopy(root_providers), prov_overrides)
        else:
            merged_providers = copy.deepcopy(root_providers)
        profile_custom = profile_user.get("custom_providers")
        if isinstance(profile_custom, list) and profile_custom:
            merged_custom = copy.deepcopy(profile_custom)
        else:
            merged_custom = copy.deepcopy(root_custom)
        return merged_providers, merged_custom

    return root_providers, root_custom


def apply_profile_root_config_inheritance(
    merged_config: dict[str, Any],
    profile_user_config: dict[str, Any] | None,
) -> dict[str, Any]:
    """Root overerving voor model, auxiliary en providers in profiel-modus."""
    if not is_profile_hermes_home():
        return merged_config
    root_user = _read_yaml(root_config_path())
    merged_config["model"] = resolve_model_section(
        profile_user_config, root_user_config=root_user
    )
    merged_config["auxiliary"] = resolve_auxiliary_section(
        profile_user_config, root_user_config=root_user
    )
    providers, custom_providers = resolve_providers_sections(
        profile_user_config, root_user_config=root_user
    )
    merged_config["providers"] = providers
    if custom_providers:
        merged_config["custom_providers"] = custom_providers
    elif "custom_providers" in merged_config:
        merged_config.pop("custom_providers", None)
    return merged_config


def effective_model_provider(profile_dir: Path) -> tuple[str | None, str | None]:
    """Voor doctor/profile list — zelfde regels als load_config."""
    profile_user = _read_yaml(profile_dir / "config.yaml")
    model_cfg = resolve_model_section(profile_user)
    if isinstance(model_cfg, str):
        return model_cfg, None
    if isinstance(model_cfg, dict):
        return (
            (model_cfg.get("default") or model_cfg.get("model") or "").strip() or None,
            (model_cfg.get("provider") or "").strip() or None,
        )
    return None, None


def strip_model_block_from_profile_config(profile_dir: Path) -> bool:
    """
    Verwijder ``model:`` uit profiel-config (aanbevolen voor domein-profielen).
    Returns True als er iets is verwijderd.
    """
    path = profile_dir / "config.yaml"
    if not path.is_file():
        return False
    cfg = _read_yaml(path)
    if "model" not in cfg:
        return False
    cfg.pop("model", None)
    try:
        import yaml

        body = yaml.safe_dump(
            cfg,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        note = (
            "# model/provider: inherited from root config (~/.hermes/config.yaml).\n"
            "# Change model globally: hermes model  (or edit root config.yaml).\n"
            "# Per-profile override only: model.inherit: false + model.default below.\n"
        )
        path.write_text(note + body, encoding="utf-8")
        bust_config_caches()
        return True
    except Exception:
        return False


def is_global_model_config_key(key: str) -> bool:
    """Config-keys die bij profielen naar root ``config.yaml`` horen."""
    k = (key or "").strip()
    return k == "model" or k.startswith("model.")


def is_global_auxiliary_config_key(key: str) -> bool:
    k = (key or "").strip()
    return k == "auxiliary" or k.startswith("auxiliary.")


def is_global_providers_config_key(key: str) -> bool:
    k = (key or "").strip()
    return (
        k == "providers"
        or k.startswith("providers.")
        or k == "custom_providers"
        or k.startswith("custom_providers.")
    )


def is_global_root_config_key(key: str) -> bool:
    return (
        is_global_model_config_key(key)
        or is_global_auxiliary_config_key(key)
        or is_global_providers_config_key(key)
    )


def profile_uses_local_model_override(home: Path | None = None) -> bool:
    """True wanneer dit profiel ``model.inherit: false`` heeft."""
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    return profile_has_explicit_model_override(_read_yaml(path / "config.yaml").get("model"))


def profile_uses_local_auxiliary_override(home: Path | None = None) -> bool:
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    return profile_has_explicit_auxiliary_override(
        _read_yaml(path / "config.yaml").get("auxiliary")
    )


def profile_uses_local_providers_override(home: Path | None = None) -> bool:
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    return profile_has_explicit_providers_override(
        _read_yaml(path / "config.yaml").get("providers")
    )


def config_path_for_user_key(key: str, *, home: Path | None = None) -> Path:
    """Doelpad voor ``hermes config set`` / ``save_config_value``."""
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    if not is_profile_hermes_home(path):
        return path / "config.yaml"
    if is_global_model_config_key(key) and not profile_uses_local_model_override(path):
        return root_config_path()
    if is_global_auxiliary_config_key(key) and not profile_uses_local_auxiliary_override(path):
        return root_config_path()
    if is_global_providers_config_key(key) and not profile_uses_local_providers_override(path):
        return root_config_path()
    return path / "config.yaml"


def should_redirect_model_save_to_root(home: Path | None = None) -> bool:
    """Of ``save_config`` het model-blok naar root moet schrijven (niet naar profiel)."""
    return is_profile_hermes_home(home) and not profile_uses_local_model_override(home)


def should_redirect_auxiliary_save_to_root(home: Path | None = None) -> bool:
    return is_profile_hermes_home(home) and not profile_uses_local_auxiliary_override(home)


def should_redirect_providers_save_to_root(home: Path | None = None) -> bool:
    return is_profile_hermes_home(home) and not profile_uses_local_providers_override(home)


def _write_root_config_section(section_key: str, section_value: Any, *, merge_dict: bool = True) -> None:
    if section_value is None:
        return
    root_path = root_config_path()
    root_path.parent.mkdir(parents=True, exist_ok=True)
    root_cfg = _read_yaml(root_path)
    if merge_dict and isinstance(section_value, dict):
        existing = root_cfg.get(section_key)
        if isinstance(existing, dict):
            root_cfg[section_key] = _deep_merge_dict(existing, section_value)
        else:
            root_cfg[section_key] = copy.deepcopy(section_value)
    else:
        root_cfg[section_key] = copy.deepcopy(section_value)
    try:
        from utils import atomic_yaml_write

        atomic_yaml_write(root_path, root_cfg, sort_keys=False)
        try:
            import os

            os.chmod(root_path, 0o600)
        except (OSError, NotImplementedError):
            pass
        bust_config_caches(root_path)
    except Exception:
        pass


def save_model_section_to_root(model_section: Any) -> None:
    """Persisteer ``model:`` in root config (voor ``hermes -p <profiel> model``)."""
    _write_root_config_section("model", model_section, merge_dict=True)


def save_auxiliary_section_to_root(auxiliary_section: Any) -> None:
    _write_root_config_section("auxiliary", auxiliary_section, merge_dict=True)


def save_providers_sections_to_root(
    providers_section: Any,
    custom_providers_section: Any = None,
) -> None:
    _write_root_config_section("providers", providers_section, merge_dict=True)
    if custom_providers_section is not None:
        _write_root_config_section("custom_providers", custom_providers_section, merge_dict=False)


def bust_config_caches(*paths: Path) -> None:
    """Invalideer load/read caches na root- of profiel-config wijziging."""
    try:
        from hermes_cli import config as cfg_mod

        root_key = str(root_config_path())
        clear_all = not paths or any(str(p) == root_key for p in paths)
        if clear_all:
            cfg_mod._LOAD_CONFIG_CACHE.clear()
            cfg_mod._RAW_CONFIG_CACHE.clear()
            try:
                from hermes_cli.config_snapshot import bust_config_snapshot

                bust_config_snapshot()
            except Exception:
                pass
            try:
                from gateway.config import bust_gateway_config_cache

                bust_gateway_config_cache()
            except Exception:
                pass
            return
        for path in paths:
            key = str(path)
            cfg_mod._LOAD_CONFIG_CACHE.pop(key, None)
            cfg_mod._RAW_CONFIG_CACHE.pop(key, None)
    except Exception:
        pass


def _strip_keys_from_profile_config(
    profile_dir: Path,
    keys: tuple[str, ...],
    note: str,
) -> bool:
    path = profile_dir / "config.yaml"
    if not path.is_file():
        return False
    cfg = _read_yaml(path)
    removed = [k for k in keys if k in cfg]
    if not removed:
        return False
    for k in removed:
        cfg.pop(k, None)
    try:
        import yaml

        body = yaml.safe_dump(
            cfg,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        path.write_text(note + body, encoding="utf-8")
        bust_config_caches()
        return True
    except Exception:
        return False


def strip_auxiliary_block_from_profile_config(profile_dir: Path) -> bool:
    return _strip_keys_from_profile_config(
        profile_dir,
        ("auxiliary",),
        (
            "# auxiliary: inherited from root config (runtime hermes/config.yaml).\n"
            "# Apply preset: windows\\APPLY_AUXILIARY_HYBRID_PRESET.bat\n"
        ),
    )


def strip_providers_blocks_from_profile_config(profile_dir: Path) -> bool:
    return _strip_keys_from_profile_config(
        profile_dir,
        ("providers", "custom_providers"),
        (
            "# providers/custom_providers: inherited from root config.\n"
            "# Custom endpoints (e.g. Venice): edit root config.yaml only.\n"
        ),
    )


def strip_global_blocks_from_profile_config(profile_dir: Path) -> bool:
    changed = False
    changed |= strip_model_block_from_profile_config(profile_dir)
    changed |= strip_auxiliary_block_from_profile_config(profile_dir)
    changed |= strip_providers_blocks_from_profile_config(profile_dir)
    return changed


_GLOBAL_BLOCK_KEYS = frozenset({"auxiliary", "providers", "custom_providers"})


def profile_has_global_config_blocks(profile_dir: Path) -> bool:
    """True when profile ``config.yaml`` has top-level global blocks (YAML keys).

    Uses parsed YAML only — comment lines like ``# providers:`` do not match.
    Missing or invalid profile config returns ``False``.
    """
    cfg = _read_yaml(profile_dir / "config.yaml")
    return any(key in cfg for key in _GLOBAL_BLOCK_KEYS)


def list_profiles_with_global_config_blocks() -> list[str]:
    """Profile names that still define auxiliary/providers locally."""
    from hermes_constants import get_default_hermes_root

    profiles_root = get_default_hermes_root() / "profiles"
    names: list[str] = []
    if not profiles_root.is_dir():
        return names
    for entry in sorted(profiles_root.iterdir()):
        if entry.is_dir() and profile_has_global_config_blocks(entry):
            names.append(entry.name)
    return names


def strip_all_profile_global_blocks() -> list[str]:
    """Verwijder model/auxiliary/providers uit alle domein-profielen."""
    from hermes_constants import get_default_hermes_root

    profiles_root = get_default_hermes_root() / "profiles"
    stripped: list[str] = []
    if not profiles_root.is_dir():
        return stripped
    for entry in sorted(profiles_root.iterdir()):
        if not entry.is_dir():
            continue
        if strip_global_blocks_from_profile_config(entry):
            stripped.append(entry.name)
    return stripped


def strip_all_profile_model_blocks() -> list[str]:
    """Verwijder ``model:`` uit alle domein-profielen. Returns profielnamen."""
    from hermes_constants import get_default_hermes_root

    profiles_root = get_default_hermes_root() / "profiles"
    stripped: list[str] = []
    if not profiles_root.is_dir():
        return stripped
    for entry in sorted(profiles_root.iterdir()):
        if not entry.is_dir():
            continue
        if strip_model_block_from_profile_config(entry):
            stripped.append(entry.name)
    return stripped


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge_dict(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out
