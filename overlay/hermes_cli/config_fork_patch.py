"""``config get``, dotted config helpers, and profile root inheritance (Tier B overlay)."""
from __future__ import annotations

import copy
from typing import Any

import yaml


def get_config_value(key: str) -> None:
    """Print a dotted config key (e.g. auxiliary.vision.provider)."""
    from hermes_cli.config import load_config

    cfg = load_config()
    parts = [p for p in key.split(".") if p]
    if not parts:
        print("", end="")
        return
    cur: object = cfg
    for part in parts:
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                print("", end="")
                return
        elif isinstance(cur, dict):
            if part not in cur:
                print("", end="")
                return
            cur = cur[part]
        else:
            print("", end="")
            return
    if isinstance(cur, (dict, list)):
        print(yaml.safe_dump(cur, sort_keys=False, allow_unicode=True).rstrip())
    else:
        print(cur)


def _read_profile_user_config() -> dict[str, Any]:
    from hermes_cli.config import get_config_path

    path = get_config_path()
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _apply_profile_inheritance(cfg: dict[str, Any]) -> dict[str, Any]:
    from hermes_cli.profile_model_inheritance import (
        apply_profile_root_config_inheritance,
        is_profile_hermes_home,
    )

    if not is_profile_hermes_home():
        return cfg
    profile_user = _read_profile_user_config()
    return apply_profile_root_config_inheritance(cfg, profile_user)


def apply_config_fork_patch() -> None:
    import hermes_cli.config as config_mod

    if getattr(config_mod, "_fork_config_patch_applied", False):
        return

    config_mod.get_config_value = get_config_value  # type: ignore[attr-defined]

    _orig_load_config = config_mod.load_config
    _orig_load_config_readonly = config_mod.load_config_readonly

    def load_config():
        cfg = _orig_load_config()
        return _apply_profile_inheritance(cfg)

    def load_config_readonly():
        cfg = _orig_load_config_readonly()
        if not cfg:
            return cfg
        from hermes_cli.profile_model_inheritance import is_profile_hermes_home

        if not is_profile_hermes_home():
            return cfg
        return _apply_profile_inheritance(copy.deepcopy(cfg))

    config_mod.load_config = load_config  # type: ignore[assignment]
    config_mod.load_config_readonly = load_config_readonly  # type: ignore[assignment]

    _orig_config_command = config_mod.config_command

    def config_command(args):
        subcmd = getattr(args, "config_command", None)
        if subcmd == "get":
            key = getattr(args, "config_key", "") or ""
            get_config_value(key)
            return
        return _orig_config_command(args)

    config_mod.config_command = config_command  # type: ignore[assignment]
    config_mod._fork_config_patch_applied = True  # type: ignore[attr-defined]
