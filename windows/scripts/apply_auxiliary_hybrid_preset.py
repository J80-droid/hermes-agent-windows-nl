#!/usr/bin/env python3
"""Apply institutional hybrid auxiliary preset to runtime config.yaml."""
from __future__ import annotations

import argparse
import copy
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PRESET_PATH = REPO_ROOT / "docs" / "templates" / "AUXILIARY_HYBRID_OLLAMA.yaml"

TEXT_AUX = (
    "compression",
    "web_extract",
    "mcp",
    "approval",
    "title_generation",
    "skills_hub",
    "triage_specifier",
    "curator",
)


def _ollama_ok(base_url: str) -> bool:
    url = base_url.rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _google_key_in_env(env_path: Path) -> bool:
    if not env_path.is_file():
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if t.startswith("GOOGLE_API_KEY="):
            val = t.split("=", 1)[1].strip().strip('"').strip("'")
            return bool(val) and "your_" not in val
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-ollama-check", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault(
        "HERMES_HOME",
        os.environ.get("HERMES_HOME")
        or str(Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"),
    )

    from hermes_cli.profile_model_inheritance import bust_config_caches, root_config_path
    from utils import atomic_yaml_write

    if not PRESET_PATH.is_file():
        print(f"Preset missing: {PRESET_PATH}", file=sys.stderr)
        return 1

    with PRESET_PATH.open(encoding="utf-8") as f:
        preset = yaml.safe_load(f) or {}
    preset_aux = preset.get("auxiliary") if isinstance(preset.get("auxiliary"), dict) else {}
    if not preset_aux:
        print("Empty auxiliary preset", file=sys.stderr)
        return 1

    vision = preset_aux.get("vision") if isinstance(preset_aux.get("vision"), dict) else {}
    sample = preset_aux.get("compression") if isinstance(preset_aux.get("compression"), dict) else {}
    base_url = str(sample.get("base_url") or "http://localhost:11434/v1")

    if not args.skip_ollama_check and not _ollama_ok(base_url):
        print(f"[WARN] Ollama not reachable at {base_url} — preset still applies; aux tasks may fail until Ollama runs.")

    runtime_root = Path(os.environ["HERMES_HOME"])
    env_path = runtime_root / ".env"
    if not _google_key_in_env(env_path):
        legacy_env = Path.home() / ".hermes" / ".env"
        if not _google_key_in_env(legacy_env):
            print("[WARN] GOOGLE_API_KEY not found in runtime or ~/.hermes/.env — vision may fail.")

    root_path = root_config_path()
    root_path.parent.mkdir(parents=True, exist_ok=True)
    if root_path.is_file():
        try:
            with root_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as exc:
            print(f"[FAIL] Could not read {root_path}: {exc}", file=sys.stderr)
            return 1
    else:
        cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}

    aux = cfg.setdefault("auxiliary", {})
    if not isinstance(aux, dict):
        aux = {}
        cfg["auxiliary"] = aux

    for task in TEXT_AUX:
        slot = preset_aux.get(task)
        if isinstance(slot, dict):
            merged = copy.deepcopy(aux.get(task) if isinstance(aux.get(task), dict) else {})
            for k, v in slot.items():
                merged[k] = copy.deepcopy(v)
            aux[task] = merged

    if isinstance(vision, dict):
        vslot = copy.deepcopy(aux.get("vision") if isinstance(aux.get("vision"), dict) else {})
        for k, val in vision.items():
            vslot[k] = copy.deepcopy(val)
        aux["vision"] = vslot

    if args.dry_run:
        print(yaml.safe_dump({"auxiliary": aux}, sort_keys=False, allow_unicode=True))
        return 0

    atomic_yaml_write(root_path, cfg, sort_keys=False)
    bust_config_caches(root_path)
    print("[OK] Auxiliary hybrid preset applied to", root_path.parent)
    for task in TEXT_AUX + ("vision",):
        slot = aux.get(task, {})
        prov = slot.get("provider") if isinstance(slot, dict) else "?"
        model = slot.get("model") if isinstance(slot, dict) else "?"
        print(f"  {task}: {prov} / {model}")
    print("[VERIFY] hermes config get auxiliary.vision.provider →", end=" ")
    vision = aux.get("vision") or {}
    print(vision.get("provider") if isinstance(vision, dict) else "?")

    try:
        from hermes_cli.profile_model_inheritance import strip_all_profile_global_blocks

        stripped = strip_all_profile_global_blocks()
        if stripped:
            print("[OK] Stripped stale profile global blocks:", ", ".join(stripped))
    except Exception as exc:
        print(f"[WARN] Profile strip skipped: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
