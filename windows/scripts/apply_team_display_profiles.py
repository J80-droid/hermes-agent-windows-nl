"""Apply windows/team_display.defaults to every profiles/<name>/config.yaml."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml


def _hermes_root() -> Path:
    override = os.environ.get("HERMES_ROOT", "").strip()
    if override:
        return Path(override)
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    if (local / "config.yaml").is_file():
        return local
    home = Path.home() / ".hermes"
    if (home / "config.yaml").is_file():
        return home
    return local if local.is_dir() else home


def _parse_defaults(path: Path) -> dict[str, object]:
    out: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if not key:
            continue
        low = val.lower()
        if low in {"true", "yes", "on"}:
            out[key] = True
        elif low in {"false", "no", "off"}:
            out[key] = False
        else:
            out[key] = val
    if not out:
        raise SystemExit(f"Geen defaults in {path}")
    return out


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    defaults_path = repo / "windows" / "team_display.defaults"
    if not defaults_path.is_file():
        print(f"[ERROR] Ontbrekend: {defaults_path}", file=sys.stderr)
        return 1

    root = _hermes_root()
    profiles_dir = root / "profiles"
    if not profiles_dir.is_dir():
        print(f"[ERROR] Geen profiles-map: {profiles_dir}", file=sys.stderr)
        return 1

    display = _parse_defaults(defaults_path)
    from utils import atomic_yaml_write

    names: list[str] = []
    for prof_dir in sorted(profiles_dir.iterdir()):
        if not prof_dir.is_dir():
            continue
        cfg_path = prof_dir / "config.yaml"
        cfg = {}
        if cfg_path.is_file():
            with cfg_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        block = cfg.get("display")
        if not isinstance(block, dict):
            block = {}
        block.update(display)
        cfg["display"] = block
        atomic_yaml_write(cfg_path, cfg, sort_keys=False)
        names.append(prof_dir.name)
        print(f"  [OK] {prof_dir.name} -> {cfg_path}")

    print(f"[OK] display defaults op {len(names)} profiel(en): {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
