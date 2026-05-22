#!/usr/bin/env python3
"""Sync platform_toolsets.cli from docs/domain_toolsets.yaml to Hermes profiles + root."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hermes_cli.profile_mcp_format import _read_yaml, _split_header, _write_yaml  # noqa: E402


def _hermes_root() -> Path:
    override = (os.environ.get("HERMES_HOME") or "").strip()
    if override:
        return Path(override)
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    if (local_root / "config.yaml").is_file():
        return local_root
    home_root = Path.home() / ".hermes"
    if (home_root / "config.yaml").is_file():
        return home_root
    return local_root


def _load_manifest(repo: Path) -> dict[str, Any]:
    path = repo / "docs" / "domain_toolsets.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    data = _read_yaml(path)
    if not isinstance(data.get("profiles"), dict):
        raise ValueError("domain_toolsets.yaml mist profiles")
    return data


def _apply_toolsets_to_config(
    raw: dict[str, Any],
    cli_toolsets: list[str],
) -> tuple[dict[str, Any], bool]:
    out = dict(raw)
    changed = False
    pt = out.get("platform_toolsets")
    if not isinstance(pt, dict):
        pt = {}
        out["platform_toolsets"] = pt
        changed = True
    old_cli = list(pt.get("cli") or []) if "cli" in pt else None
    new_cli = list(cli_toolsets)
    if old_cli != new_cli or "cli" not in pt:
        pt["cli"] = new_cli
        changed = True
    if "enabled_toolsets" in out:
        out.pop("enabled_toolsets", None)
        changed = True
    if out.get("toolsets"):
        out.pop("toolsets", None)
        changed = True
    return out, changed


def _merge_skills_disabled(root_cfg: dict[str, Any], manifest: dict[str, Any]) -> bool:
    suggestions = manifest.get("skills_disabled_suggestions") or []
    if not suggestions:
        return False
    skills = root_cfg.setdefault("skills", {})
    if not isinstance(skills, dict):
        skills = {}
        root_cfg["skills"] = skills
    existing = set(skills.get("disabled") or [])
    add = {str(s) for s in suggestions}
    merged = sorted(existing | add)
    if list(skills.get("disabled") or []) != merged:
        skills["disabled"] = merged
        return True
    return False


def _sync_root(repo: Path, hermes: Path, manifest: dict[str, Any], *, dry_run: bool) -> bool:
    root_spec = manifest.get("root") or {}
    cli = list((root_spec.get("platform_toolsets") or {}).get("cli") or [])
    cfg_path = hermes / "config.yaml"
    if not cfg_path.is_file():
        print(f"[WARN] Root config ontbreekt: {cfg_path}")
        return True
    raw = _read_yaml(cfg_path)
    if raw.get("toolsets"):
        raw = dict(raw)
        raw.pop("toolsets", None)
    merged, changed = _apply_toolsets_to_config(raw, cli)
    # Override DEFAULT_CONFIG merge (toolsets: [hermes-cli]) on root.
    if merged.get("toolsets") != []:
        merged["toolsets"] = []
        changed = True
    if _merge_skills_disabled(merged, manifest):
        changed = True
    if not changed:
        print("[OK] root config.yaml — platform_toolsets.cli al actueel")
        return True
    if dry_run:
        print(f"[DRY] root -> platform_toolsets.cli={cli}")
        return True
    header, _ = _split_header(cfg_path.read_text(encoding="utf-8"))
    if not header:
        header = (
            "# Hermes root config — model/provider hier; toolsets per profiel "
            "(docs/domain_toolsets.yaml).\n"
        )
    _write_yaml(cfg_path, merged, header=header)
    print(f"[OK] root config.yaml — platform_toolsets.cli={cli}")
    return True


def _sync_profile(
    hermes: Path,
    name: str,
    spec: dict[str, Any],
    *,
    dry_run: bool,
    check: bool,
) -> bool:
    cli = list((spec.get("platform_toolsets") or {}).get("cli") or [])
    cfg_path = hermes / "profiles" / name / "config.yaml"
    if not cfg_path.is_file():
        print(f"[FAIL] {name}: config.yaml ontbreekt ({cfg_path})")
        return False
    raw = _read_yaml(cfg_path)
    merged, changed = _apply_toolsets_to_config(raw, cli)
    if check:
        current = list((raw.get("platform_toolsets") or {}).get("cli") or [])
        if current != cli:
            print(f"[FAIL] {name}: platform_toolsets.cli drift: {current!r} != {cli!r}")
            return False
        print(f"[OK] {name}: platform_toolsets.cli matcht manifest")
        return True
    if not changed:
        print(f"[OK] {name}: geen wijziging")
        return True
    if dry_run:
        print(f"[DRY] {name} -> platform_toolsets.cli={cli}")
        return True
    text = cfg_path.read_text(encoding="utf-8")
    header, _ = _split_header(text)
    if not header:
        header = (
            f"# Profiel {name} — toolsets via docs/domain_toolsets.yaml "
            f"(sync_profile_toolsets_from_manifest).\n"
            f"# Gebruik platform_toolsets.cli — enabled_toolsets is verouderd.\n"
        )
    _write_yaml(cfg_path, merged, header=header)
    print(f"[OK] {name}: platform_toolsets.cli={cli}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(_REPO))
    parser.add_argument("--hermes-root", default="")
    parser.add_argument("--profile", default="", help="Alleen dit profiel")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    hermes = Path(args.hermes_root).resolve() if args.hermes_root else _hermes_root()
    manifest = _load_manifest(repo)
    profiles: dict[str, Any] = manifest["profiles"]

    ok = True
    if not args.profile:
        ok = _sync_root(repo, hermes, manifest, dry_run=args.dry_run) and ok
    names = [args.profile] if args.profile else sorted(profiles.keys())
    for name in names:
        if name not in profiles:
            print(f"[FAIL] Onbekend profiel in manifest: {name}")
            ok = False
            continue
        if not _sync_profile(hermes, name, profiles[name], dry_run=args.dry_run, check=args.check):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
