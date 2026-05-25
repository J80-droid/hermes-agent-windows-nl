#!/usr/bin/env python3
"""Selectief providers/Venice/skills merge van legacy config naar runtime root.

Runtime-pad: ``root_config_path()`` (``get_default_hermes_root()``), niet profiel-``HERMES_HOME``.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[WARN] Could not read {path}: {exc}", file=sys.stderr)
        return {}


def _save(path: Path, cfg: dict) -> None:
    from utils import atomic_yaml_write

    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_yaml_write(path, cfg, sort_keys=False)


def _merge_providers(legacy: dict, runtime: dict) -> list[str]:
    merged_keys: list[str] = []
    lg = legacy.get("providers") if isinstance(legacy.get("providers"), dict) else {}
    rt = runtime.setdefault("providers", {})
    if not isinstance(rt, dict):
        rt = {}
        runtime["providers"] = rt
    for key, value in lg.items():
        if key not in rt and isinstance(value, dict):
            rt[key] = copy.deepcopy(value)
            merged_keys.append(f"providers.{key}")
    return merged_keys


def _merge_external_dirs(legacy: dict, runtime: dict) -> list[str]:
    changes: list[str] = []
    lg_skills = legacy.get("skills") if isinstance(legacy.get("skills"), dict) else {}
    rt_skills = runtime.setdefault("skills", {})
    if not isinstance(rt_skills, dict):
        rt_skills = {}
        runtime["skills"] = rt_skills
    lg_dirs = lg_skills.get("external_dirs")
    if not isinstance(lg_dirs, list):
        return changes
    rt_dirs = rt_skills.get("external_dirs")
    if not isinstance(rt_dirs, list):
        rt_dirs = []
        rt_skills["external_dirs"] = rt_dirs
    for entry in lg_dirs:
        if not entry or entry in rt_dirs:
            continue
        expanded = Path(str(entry).replace("~", str(Path.home()))).expanduser()
        if expanded.is_dir():
            rt_dirs.append(entry)
            changes.append(f"skills.external_dirs: {entry}")
    return changes


def _merge_chat_favorites(legacy: dict, runtime: dict) -> list[str]:
    if "chat.favorites" in runtime or "chat" in runtime:
        return []
    fav = legacy.get("chat.favorites")
    if fav is None:
        return []
    runtime["chat.favorites"] = copy.deepcopy(fav)
    return ["chat.favorites"]


def _merge_docker_forward_env(legacy: dict, runtime: dict) -> list[str]:
    lg_term = legacy.get("terminal") if isinstance(legacy.get("terminal"), dict) else {}
    rt_term = runtime.setdefault("terminal", {})
    if not isinstance(rt_term, dict):
        rt_term = {}
        runtime["terminal"] = rt_term
    lg_fwd = lg_term.get("docker_forward_env")
    if not isinstance(lg_fwd, list):
        return []
    rt_fwd = rt_term.get("docker_forward_env")
    if not isinstance(rt_fwd, list):
        rt_fwd = []
        rt_term["docker_forward_env"] = rt_fwd
    added: list[str] = []
    for key in lg_fwd:
        if key and key not in rt_fwd:
            rt_fwd.append(key)
            added.append(key)
    return [f"terminal.docker_forward_env: {k}" for k in added]


def merge_legacy_into_runtime(*, legacy: dict, runtime: dict) -> tuple[dict, list[str]]:
    runtime = copy.deepcopy(runtime)
    changes: list[str] = []
    changes.extend(_merge_providers(legacy, runtime))
    changes.extend(_merge_external_dirs(legacy, runtime))
    changes.extend(_merge_chat_favorites(legacy, runtime))
    changes.extend(_merge_docker_forward_env(legacy, runtime))
    return runtime, changes


def find_best_legacy_config(legacy_root: Path) -> Path | None:
    candidates: list[Path] = []
    for pattern in (
        "config.yaml.bak.*",
        "config.yaml.deprecated-*",
        "config.yaml.backup.*",
    ):
        candidates.extend(legacy_root.glob(pattern))
    if (legacy_root / "config.yaml").is_file():
        candidates.append(legacy_root / "config.yaml")
    best: Path | None = None
    best_size = -1
    for path in candidates:
        try:
            size = path.stat().st_size
            if size > best_size:
                best_size = size
                best = path
        except OSError:
            continue
    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, help="Legacy config.yaml path")
    parser.add_argument("--runtime", type=Path, help="Runtime root config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import os

    from hermes_cli.profile_model_inheritance import root_config_path

    runtime_path = args.runtime
    if runtime_path is None:
        runtime_path = root_config_path()

    legacy_path = args.legacy
    if legacy_path is None:
        legacy_root = Path.home() / ".hermes"
        legacy_path = find_best_legacy_config(legacy_root)

    if legacy_path is None or not legacy_path.is_file():
        print("[SKIP] No legacy config found for provider merge")
        return 0
    if not runtime_path.is_file():
        print(f"[FAIL] Runtime config missing: {runtime_path}", file=sys.stderr)
        return 1

    legacy_cfg = _load(legacy_path)
    runtime_cfg = _load(runtime_path)
    merged, changes = merge_legacy_into_runtime(legacy=legacy_cfg, runtime=runtime_cfg)

    if not changes:
        print(f"[OK] No provider merge needed (legacy: {legacy_path.name})")
        return 0

    if args.dry_run:
        print(yaml.safe_dump(merged, sort_keys=False, allow_unicode=True))
        print("Changes:", ", ".join(changes))
        return 0

    _save(runtime_path, merged)
    try:
        from hermes_cli.profile_model_inheritance import bust_config_caches

        bust_config_caches(root_config_path())
    except Exception:
        pass
    print(f"[OK] Merged from {legacy_path.name}: {', '.join(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
