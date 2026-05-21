"""
Profiel-model overerven van root ``~/.hermes/config.yaml``.

Domein-profielen (legal, core, …) bevatten **geen** vast model — wijzig het model
eenmalig in de root-config (``hermes model`` / ``~/.hermes/config.yaml``).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

PROFILE_MODEL_INHERIT_KEY = "inherit"


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
        return True
    except Exception:
        return False


def is_global_model_config_key(key: str) -> bool:
    """Config-keys die bij profielen naar root ``config.yaml`` horen."""
    k = (key or "").strip()
    return k == "model" or k.startswith("model.")


def profile_uses_local_model_override(home: Path | None = None) -> bool:
    """True wanneer dit profiel ``model.inherit: false`` heeft."""
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    return profile_has_explicit_model_override(_read_yaml(path / "config.yaml").get("model"))


def config_path_for_user_key(key: str, *, home: Path | None = None) -> Path:
    """Doelpad voor ``hermes config set`` / ``save_config_value``."""
    from hermes_constants import get_hermes_home

    path = home or get_hermes_home()
    if is_profile_hermes_home(path) and is_global_model_config_key(key):
        if not profile_uses_local_model_override(path):
            return root_config_path()
    return path / "config.yaml"


def should_redirect_model_save_to_root(home: Path | None = None) -> bool:
    """Of ``save_config`` het model-blok naar root moet schrijven (niet naar profiel)."""
    return is_profile_hermes_home(home) and not profile_uses_local_model_override(home)


def save_model_section_to_root(model_section: Any) -> None:
    """Persisteer ``model:`` in root config (voor ``hermes -p <profiel> model``)."""
    if model_section is None:
        return
    root_path = root_config_path()
    root_path.parent.mkdir(parents=True, exist_ok=True)
    root_cfg = _read_yaml(root_path)
    if isinstance(model_section, dict):
        existing = root_cfg.get("model")
        if isinstance(existing, dict):
            root_cfg["model"] = _deep_merge_dict(existing, model_section)
        else:
            root_cfg["model"] = copy.deepcopy(model_section)
    else:
        root_cfg["model"] = model_section
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


def bust_config_caches(*paths: Path) -> None:
    """Invalideer load/read caches na root-model wijziging."""
    try:
        from hermes_cli import config as cfg_mod

        for path in paths:
            key = str(path)
            cfg_mod._LOAD_CONFIG_CACHE.pop(key, None)
            cfg_mod._RAW_CONFIG_CACHE.pop(key, None)
        # Profiel-configs hangen af van root model — leeg cache breedte.
        if not paths:
            cfg_mod._LOAD_CONFIG_CACHE.clear()
            cfg_mod._RAW_CONFIG_CACHE.clear()
    except Exception:
        pass


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
