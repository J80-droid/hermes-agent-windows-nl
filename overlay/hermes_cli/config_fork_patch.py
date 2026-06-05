"""``config get`` and dotted config helpers (Tier B overlay)."""
from __future__ import annotations

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


def apply_config_fork_patch() -> None:
    import hermes_cli.config as config_mod

    if getattr(config_mod, "_fork_config_patch_applied", False):
        return

    config_mod.get_config_value = get_config_value  # type: ignore[attr-defined]

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
