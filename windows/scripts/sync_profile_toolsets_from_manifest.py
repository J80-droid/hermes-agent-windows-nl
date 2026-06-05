#!/usr/bin/env python3
"""Sync platform_toolsets.cli from docs/domain_toolsets.yaml to Hermes profiles + root.

Profiles with ``platform_toolsets._user_customized.cli: true`` (set by
``hermes tools``) are skipped unless ``--force-manifest`` is passed.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _argv_without_hermes_profile_flag(argv: list[str]) -> list[str]:
    """Drop --profile/-p so overlay bootstrap (imports hermes_cli.main) does not resolve it."""
    out: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg in ("--profile", "-p"):
            skip_next = True
            continue
        if arg.startswith("--profile="):
            continue
        out.append(arg)
    return out


_argv_saved = list(sys.argv)
sys.argv = _argv_without_hermes_profile_flag(sys.argv)
try:
    from overlay.bootstrap import install

    install()
finally:
    sys.argv = _argv_saved

from hermes_cli.profile_mcp_format import _read_yaml, _split_header, _write_yaml  # noqa: E402
from hermes_cli.tools_config import _platform_toolsets_user_customized  # noqa: E402


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


def _sync_root(
    repo: Path,
    hermes: Path,
    manifest: dict[str, Any],
    *,
    dry_run: bool,
    force_manifest: bool = False,
) -> bool:
    root_spec = manifest.get("root") or {}
    cli = list((root_spec.get("platform_toolsets") or {}).get("cli") or [])
    cfg_path = hermes / "config.yaml"
    if not cfg_path.is_file():
        print(f"[WARN] Root config ontbreekt: {cfg_path}")
        return True
    raw = _read_yaml(cfg_path)
    if not force_manifest and _platform_toolsets_user_customized(raw, "cli"):
        print(
            "[OK] root config.yaml — platform_toolsets.cli door gebruiker aangepast; sync overgeslagen"
        )
        return True
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
    force_manifest: bool = False,
) -> bool:
    cli = list((spec.get("platform_toolsets") or {}).get("cli") or [])
    cfg_path = hermes / "profiles" / name / "config.yaml"
    if not cfg_path.is_file():
        print(f"[FAIL] {name}: config.yaml ontbreekt ({cfg_path})")
        return False
    raw = _read_yaml(cfg_path)
    if not force_manifest and _platform_toolsets_user_customized(raw, "cli"):
        if check:
            print(
                f"[OK] {name}: platform_toolsets.cli door gebruiker aangepast "
                f"(hermes tools) — check overgeslagen"
            )
            return True
        print(
            f"[OK] {name}: platform_toolsets.cli door gebruiker aangepast "
            f"(hermes tools) — sync overgeslagen"
        )
        return True
    if check:
        current = list((raw.get("platform_toolsets") or {}).get("cli") or [])
        if sorted(current) != sorted(cli):
            print(f"[FAIL] {name}: platform_toolsets.cli drift: {current!r} != {cli!r}")
            return False
        print(f"[OK] {name}: platform_toolsets.cli matcht manifest")
        return True
    merged, changed = _apply_toolsets_to_config(raw, cli)
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


def _resolve_soul_template(repo: Path, profile_name: str) -> Path | None:
    """Return repo path to SOUL_*_DOMAIN.md or None."""
    upper = profile_name.upper()
    for candidate in (
        repo / "docs" / "templates" / f"SOUL_{upper}_DOMAIN.md",
        repo / "docs" / "templates" / f"SOUL_{profile_name}_DOMAIN.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def _inject_soul_shared_sections(content: str, repo: Path) -> str:
    """Replace stub Interaction/Output sections with shared template bodies (legal-sync pattern)."""
    interaction = (repo / "docs" / "templates" / "SOUL_SHARED_INTERACTION.md").read_text(
        encoding="utf-8"
    )
    output_fmt = (repo / "docs" / "templates" / "SOUL_SHARED_OUTPUT_FORMAT.md").read_text(
        encoding="utf-8"
    )
    tool_gov = (repo / "docs" / "templates" / "SOUL_SHARED_TOOL_GOVERNANCE.md").read_text(
        encoding="utf-8"
    )
    content = re.sub(
        r"(?ms)^## Outputformaat \(institutioneel\)\s*\r?\n.*?(?=^## )",
        output_fmt.rstrip() + "\n\n",
        content,
        count=1,
    )
    content = re.sub(
        r"(?ms)^## Interaction met J\.\s*\r?\n.*?(?=^## )",
        interaction.rstrip() + "\n\n",
        content,
        count=1,
    )
    if "## Tool governance" not in content:
        content = content.rstrip() + "\n\n## Tool governance (domein-minimum)\n\n" + tool_gov.strip() + "\n"
    return content


def _copy_soul_from_profile(hermes: Path, canon: str, clone_from: str) -> bool:
    """Fallback SOUL: kopieer van bestaand profiel (geen template)."""
    src = hermes / "profiles" / clone_from / "SOUL.md"
    dst = hermes / "profiles" / canon / "SOUL.md"
    if not src.is_file():
        return False
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[OK] {canon}: SOUL.md gekopieerd van profiel '{clone_from}'")
    return True


def _apply_trust_memory_limits(repo: Path, *, dry_run: bool = False) -> bool:
    """Idempotent: zet memory 4000/1800 op root + alle profielen."""
    script = repo / "windows" / "scripts" / "apply_trust_memory_limits.ps1"
    if not script.is_file():
        print(f"[WARN] apply_trust_memory_limits ontbreekt: {script}")
        return True
    if dry_run:
        print("[DRY] zou apply_trust_memory_limits.ps1 draaien")
        return True
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=str(repo),
        check=False,
    )
    if r.returncode != 0:
        print(f"[FAIL] apply_trust_memory_limits exit {r.returncode}")
        return False
    print("[OK] trust memory limits toegepast")
    return True


def _provision_profile(
    hermes: Path,
    repo: Path,
    name: str,
    *,
    dry_run: bool = False,
    inject_soul: bool = True,
    clone_from: str = "legal",
) -> bool:
    """Create profile directory structure + minimal config + SOUL from template."""
    try:
        from hermes_cli.profiles import (
            _PROFILE_DIRS,
            normalize_profile_name,
            validate_profile_name,
        )
    except ImportError as e:
        print(f"[FAIL] {name}: kan profiles-module niet laden ({e})")
        return False

    try:
        canon = normalize_profile_name(name)
        validate_profile_name(canon)
    except ValueError as e:
        print(f"[FAIL] {name}: ongeldige profielnaam ({e})")
        return False

    profile_dir = hermes / "profiles" / canon
    if profile_dir.is_dir() and (profile_dir / "config.yaml").is_file():
        print(f"[OK] {name}: profiel bestaat al — overgeslagen")
        return True
    if dry_run:
        print(f"[DRY] zou aanmaken: {profile_dir}")
        return True

    profile_dir.mkdir(parents=True, exist_ok=True)
    for subdir in _PROFILE_DIRS:
        (profile_dir / subdir).mkdir(parents=True, exist_ok=True)

    cfg_path = profile_dir / "config.yaml"
    created_new_config = not cfg_path.is_file()
    if created_new_config:
        _write_yaml(
            cfg_path,
            {"platform_toolsets": {"cli": []}},
            header=(
                f"# Profiel {canon} — aangemaakt via sync_profile_toolsets_from_manifest.py\n"
                f"# Toolsets worden gesynchroniseerd uit docs/domain_toolsets.yaml\n"
            ),
        )

    soul_path = profile_dir / "SOUL.md"
    if inject_soul:
        template = _resolve_soul_template(repo, canon)
        if template is not None:
            body = template.read_text(encoding="utf-8").strip()
            body = _inject_soul_shared_sections(body, repo)
            soul_path.write_text(body + "\n", encoding="utf-8")
            print(f"[OK] {name}: SOUL.md van template {template.name}")
        elif clone_from:
            if not _copy_soul_from_profile(hermes, canon, clone_from):
                print(
                    f"[WARN] {name}: geen SOUL-template en geen SOUL bij '{clone_from}' "
                    f"— draai SYNC_SOUL_SNIPPETS.bat na sync"
                )

    try:
        from hermes_cli.profile_model_inheritance import strip_model_block_from_profile_config

        strip_model_block_from_profile_config(profile_dir)
    except Exception:
        pass

    if created_new_config:
        if not _apply_trust_memory_limits(repo, dry_run=dry_run):
            return False

    print(f"[OK] {name}: profiel aangemaakt ({profile_dir})")
    return True


def _run_soul_snippets_sync(repo: Path, *, dry_run: bool) -> bool:
    bat = repo / "windows" / "SYNC_SOUL_SNIPPETS.bat"
    if not bat.is_file():
        print(f"[WARN] SOUL snippet sync ontbreekt: {bat}")
        return True
    if dry_run:
        print("[DRY] zou SYNC_SOUL_SNIPPETS.bat draaien")
        return True
    env = {**os.environ, "HERMES_SKIP_PAUSE": "1"}
    r = subprocess.run(
        ["cmd", "/c", str(bat)],
        cwd=str(repo),
        env=env,
        check=False,
    )
    if r.returncode != 0:
        print(f"[FAIL] SYNC_SOUL_SNIPPETS.bat exit {r.returncode}")
        return False
    print("[OK] SOUL snippets gesynchroniseerd (alle profielen)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(_REPO))
    parser.add_argument("--hermes-root", default="")
    parser.add_argument("--profile", default="", help="Alleen dit profiel")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--create-missing",
        action="store_true",
        help="Maak ontbrekende profielen aan (map, config, SOUL) vóór sync",
    )
    parser.add_argument(
        "--no-soul-inject",
        action="store_true",
        help="Geen SOUL-template injectie bij provision (alleen structuur)",
    )
    parser.add_argument(
        "--sync-soul-snippets",
        action="store_true",
        help="Na sync: windows/SYNC_SOUL_SNIPPETS.bat (alle runtime SOUL's)",
    )
    parser.add_argument(
        "--clone-from",
        default="legal",
        metavar="NAME",
        help="Fallback SOUL-bron als domein-template ontbreekt (default: legal)",
    )
    parser.add_argument(
        "--provision-only",
        action="store_true",
        help="Alleen ontbrekende profielen aanmaken, geen toolset-sync",
    )
    parser.add_argument(
        "--force-manifest",
        action="store_true",
        help="Overschrijf ook platform_toolsets.cli na handmatige hermes tools-keuze",
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    hermes = Path(args.hermes_root).resolve() if args.hermes_root else _hermes_root()
    manifest = _load_manifest(repo)
    profiles: dict[str, Any] = manifest["profiles"]

    ok = True
    if not args.profile:
        ok = _sync_root(
            repo,
            hermes,
            manifest,
            dry_run=args.dry_run,
            force_manifest=args.force_manifest,
        ) and ok
    names = [args.profile] if args.profile else sorted(profiles.keys())
    inject_soul = not args.no_soul_inject
    clone_from = (args.clone_from or "legal").strip()
    for name in names:
        if name not in profiles:
            print(f"[FAIL] Onbekend profiel in manifest: {name}")
            ok = False
            continue
        if args.create_missing:
            cfg_path = hermes / "profiles" / name / "config.yaml"
            if not cfg_path.is_file():
                if not _provision_profile(
                    hermes,
                    repo,
                    name,
                    dry_run=args.dry_run,
                    inject_soul=inject_soul,
                    clone_from=clone_from,
                ):
                    ok = False
                    continue
        if args.provision_only:
            continue
        if not _sync_profile(
            hermes,
            name,
            profiles[name],
            dry_run=args.dry_run,
            check=args.check,
            force_manifest=args.force_manifest,
        ):
            ok = False
    if ok and args.sync_soul_snippets and not args.check:
        ok = _run_soul_snippets_sync(repo, dry_run=args.dry_run) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
