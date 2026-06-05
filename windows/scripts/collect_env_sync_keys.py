#!/usr/bin/env python3
"""Collect env var names to sync from runtime root config (providers, auxiliary).

Leest altijd ``root_config_path()`` — ook wanneer ``HERMES_HOME`` een profielsubmap is.

Gebruikt door ``sync_hermes_api_env.ps1``; E2E valideert syntax via ``py_compile`` (stap 4/10).
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(0)


def _collect_from_obj(obj, keys: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("api_key_env", "key_env") and isinstance(v, str) and v.strip():
                keys.add(v.strip())
            else:
                _collect_from_obj(v, keys)
    elif isinstance(obj, list):
        for item in obj:
            _collect_from_obj(item, keys)


def _ensure_overlay() -> None:
    repo = Path(__file__).resolve().parents[2]
    repo_s = str(repo)
    if repo_s not in sys.path:
        sys.path.insert(0, repo_s)
    try:
        from overlay.bootstrap import install
    except ImportError as exc:
        print(f"[ERROR] overlay bootstrap unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    install()


def main() -> int:
    _ensure_overlay()
    from hermes_cli.profile_model_inheritance import root_config_path

    cfg_path = root_config_path()
    keys: set[str] = set()
    if cfg_path.is_file():
        try:
            with cfg_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return 0
        if isinstance(data, dict):
            _collect_from_obj(data.get("providers"), keys)
            _collect_from_obj(data.get("custom_providers"), keys)
            _collect_from_obj(data.get("auxiliary"), keys)
    for key in sorted(keys):
        print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
