#!/usr/bin/env python3
"""Bouw de persistente Codebase Viz pygount-schijfcache zonder draaiend dashboard.

Gebruik:
  python scripts/warm_codebase_viz_pygount_cache.py           # scan indien nodig
  python scripts/warm_codebase_viz_pygount_cache.py --check-only  # exit 0 = cache ok
  python scripts/warm_codebase_viz_pygount_cache.py --force     # altijd opnieuw scannen

Exitcodes: 0 geslaagd, 1 fout, 2 (--check-only) geen geldige cache.

Na `--force` wordt de cache gevalideerd (leesbaar + repo-revisie klopt) vóór exit 0.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_API = REPO_ROOT / "plugins" / "codebase-viz" / "dashboard" / "plugin_api.py"
BUNDLED_SEED = (
    REPO_ROOT / "plugins" / "codebase-viz" / "dashboard" / "seed" / "codebase_viz_pygount_cache.json"
)


def _load_plugin_module():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if not os.environ.get("CODEBASE_VIZ_REPO", "").strip():
        os.environ.setdefault("CODEBASE_VIZ_REPO", str(REPO_ROOT))
    module_name = f"codebase_viz_warm_pygount_{os.getpid()}_{id(os.environ)}"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, PLUGIN_API)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"kan plugin_api niet laden: {PLUGIN_API}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _try_install_bundled_seed(mod) -> bool:
    """Kopieer optionele meegeleverde seed-cache als repo-handtekening klopt."""
    if not BUNDLED_SEED.is_file() or mod.REPO_PATH is None:
        return False
    try:
        import json

        data = json.loads(BUNDLED_SEED.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    try:
        cached_repo = Path(str(data.get("repo_path", ""))).resolve()
        if cached_repo != mod.REPO_PATH.resolve():
            return False
    except (OSError, ValueError):
        return False
    signature = data.get("repo_revision") or data.get("repo_signature") or ""
    if signature != mod._repo_cache_revision(mod.REPO_PATH):
        if signature != mod._compute_repo_signature(mod.REPO_PATH):
            return False
    bundle = data.get("bundle")
    if not isinstance(bundle, dict) or bundle.get("error") or not bundle.get("file_rows"):
        return False
    dest = mod._pygount_disk_cache_file()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUNDLED_SEED, dest)
    return mod._read_pygount_disk_cache(allow_stale=False) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="controleer cache; exit 0 indien geldig, anders 2",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="negeer bestaande cache en voer pygount opnieuw uit",
    )
    args = parser.parse_args(argv)

    try:
        mod = _load_plugin_module()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if mod.REPO_PATH is None:
        print("Geen repo gevonden (zet CODEBASE_VIZ_REPO).", file=sys.stderr)
        return 1

    repo = mod.REPO_PATH
    timeout = mod.PYGOUNT_TIMEOUT

    if not args.force:
        if mod._read_pygount_disk_cache(allow_stale=False) is not None:
            if args.check_only:
                return 0
            print(f"Pygount-cache al actueel voor {repo}")
            return 0
        if _try_install_bundled_seed(mod):
            if args.check_only:
                return 0
            print(f"Pygount-cache geïnstalleerd vanuit bundled seed voor {repo}")
            return 0

    if args.check_only:
        return 2

    print(f"Pygount-scan starten voor {repo} (timeout {timeout}s)...", flush=True)
    bundle = mod._sync_pygount_bundle(str(repo))
    if bundle.get("error"):
        print(f"Scan mislukt: {bundle['error']}", file=sys.stderr)
        stale = mod._read_pygount_disk_cache(allow_stale=True)
        if stale is not None:
            print("Waarschuwing: verouderde cache blijft beschikbaar.", file=sys.stderr)
            return 1
        return 1

    mod._write_pygount_disk_cache(bundle)
    if mod._read_pygount_disk_cache(allow_stale=False) is None:
        print("Cache geschreven maar validatie mislukt.", file=sys.stderr)
        return 1
    rows = len(bundle.get("file_rows") or [])
    print(f"Klaar: {rows} bestanden gecachet -> {mod._pygount_disk_cache_file()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
