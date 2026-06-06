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


def _display_drift_messages(root: Path, defaults: dict[str, object]) -> list[str]:
    """Return human-readable drift lines when live YAML != team_display.defaults."""
    messages: list[str] = []

    def check_block(label: str, cfg_path: Path) -> None:
        if not cfg_path.is_file():
            messages.append(f"{label}: geen config.yaml")
            return
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        display = data.get("display")
        block = display if isinstance(display, dict) else {}
        for key, expected in defaults.items():
            actual = block.get(key)
            if actual != expected:
                messages.append(
                    f"{label}: display.{key}={actual!r} (verwacht {expected!r})"
                )

    check_block("root", root / "config.yaml")
    profiles_dir = root / "profiles"
    if profiles_dir.is_dir():
        for prof_dir in sorted(profiles_dir.iterdir()):
            if prof_dir.is_dir():
                check_block(prof_dir.name, prof_dir / "config.yaml")
    else:
        messages.append("profiles: map ontbreekt")
    return messages


def check_display_drift() -> int:
    repo = Path(__file__).resolve().parents[2]
    defaults_path = repo / "windows" / "team_display.defaults"
    if not defaults_path.is_file():
        print(f"[ERROR] Ontbrekend: {defaults_path}", file=sys.stderr)
        return 1
    defaults = _parse_defaults(defaults_path)
    messages = _display_drift_messages(_hermes_root(), defaults)
    if not messages:
        print("[OK] geen team display drift")
        return 0
    for line in messages:
        print(f"[DRIFT] {line}", file=sys.stderr)
    return 1


def main() -> int:
    if "--check-drift" in sys.argv:
        return check_display_drift()

    profile_only = None
    if "--profile" in sys.argv:
        idx = sys.argv.index("--profile")
        if idx + 1 >= len(sys.argv):
            print("[ERROR] --profile vereist een naam", file=sys.stderr)
            return 1
        profile_only = sys.argv[idx + 1].strip()

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
    # Repo root on sys.path — script lives under windows/scripts/, not package root.
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from utils import atomic_yaml_write

    root_cfg = root / "config.yaml"
    if root_cfg.is_file():
        with root_cfg.open(encoding="utf-8") as f:
            root_data = yaml.safe_load(f) or {}
        root_block = root_data.get("display")
        if not isinstance(root_block, dict):
            root_block = {}
        root_block.update(display)
        root_data["display"] = root_block
        atomic_yaml_write(root_cfg, root_data, sort_keys=False)
        print(f"  [OK] root -> {root_cfg}")

    names: list[str] = []
    prof_dirs = sorted(profiles_dir.iterdir())
    if profile_only:
        prof_dirs = [profiles_dir / profile_only]
        if not prof_dirs[0].is_dir():
            print(f"[ERROR] Onbekend profiel: {profile_only}", file=sys.stderr)
            return 1
    for prof_dir in prof_dirs:
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
        try:
            atomic_yaml_write(cfg_path, cfg, sort_keys=False)
        except PermissionError:
            import time

            time.sleep(0.5)
            try:
                atomic_yaml_write(cfg_path, cfg, sort_keys=False)
            except PermissionError as exc:
                print(
                    f"  [WARN] {prof_dir.name}: config.yaml locked ({exc}); "
                    "sluit Hermes/gateway en draai opnieuw.",
                    file=sys.stderr,
                )
                continue
        names.append(prof_dir.name)
        print(f"  [OK] {prof_dir.name} -> {cfg_path}")

    print(f"[OK] display defaults op {len(names)} profiel(en): {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
