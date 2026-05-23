"""
Synchroniseer ``mcp_servers`` in Hermes-profielen vanuit ``domains.yaml``.

Enige bron van waarheid voor MCP-paden per domein. Voorkomt verouderd ``mcp.servers``
en handmatige drift tussen profielen.

Gebruik:
  python sync_profile_mcp_from_domains.py           # alle domeinen
  python sync_profile_mcp_from_domains.py --check # alleen controleren
  python sync_profile_mcp_from_domains.py --domain legal
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from domains_config import DomainSpec, default_domains_yaml, load_domains, resolve_domain_paths  # noqa: E402
from hermes_cli.profile_mcp_format import (  # noqa: E402
    _read_yaml,
    _split_header,
    _write_yaml,
    has_legacy_mcp_block,
    migrate_profile_mcp_config,
)


def _resolve_python() -> Path:
    override = (os.environ.get("HERMES_PYTHON") or "").strip()
    if override:
        p = Path(override)
        if p.is_file():
            return p
    default = Path(os.environ.get("USERPROFILE", "")) / "miniconda3/envs/hermes-env/python.exe"
    if default.is_file():
        return default
    return Path(sys.executable)


def _resolve_repo_root() -> Path:
    override = (os.environ.get("HERMES_REPO") or os.environ.get("HERMES_REPO_ROOT") or "").strip()
    if override:
        return Path(override).resolve()
    marker = Path(os.environ.get("USERPROFILE", "")) / "data/hermes_agent_repo.txt"
    if marker.is_file():
        line = marker.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if line:
            return Path(line).resolve()
    return _REPO


def build_mcp_server_entry(
    spec: DomainSpec,
    *,
    python_exe: Path,
    repo_root: Path,
) -> dict[str, Any]:
    ldb, _, _ = resolve_domain_paths(spec)
    mcp_script = repo_root / "scripts" / "rag_pipeline" / "mcp_server.py"
    return {
        "command": str(python_exe),
        "args": [str(mcp_script)],
        "env": {
            "HERMES_LANCEDB_PATH": str(ldb),
            "HERMES_REPO_ROOT": str(repo_root),
            "PYTHONIOENCODING": "utf-8",
        },
    }


def expected_mcp_block(
    spec: DomainSpec,
    *,
    python_exe: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    py = python_exe or _resolve_python()
    repo = repo_root or _resolve_repo_root()
    name = spec.resolved_mcp_name()
    return {name: build_mcp_server_entry(spec, python_exe=py, repo_root=repo)}


def _norm_path(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(Path(str(value)).resolve()).lower()
    except OSError:
        return str(value).replace("\\", "/").lower()


def _mcp_entry_matches(expected: dict[str, Any], current: dict[str, Any]) -> bool:
    if not isinstance(current, dict):
        return False
    exp_cmd = _norm_path(expected.get("command"))
    cur_cmd = _norm_path(current.get("command"))
    if exp_cmd != cur_cmd:
        return False
    exp_args = [str(a) for a in (expected.get("args") or [])]
    cur_args = [str(a) for a in (current.get("args") or [])]
    if exp_args != cur_args:
        return False
    exp_env = expected.get("env") if isinstance(expected.get("env"), dict) else {}
    cur_env = current.get("env") if isinstance(current.get("env"), dict) else {}
    for key in ("HERMES_LANCEDB_PATH", "HERMES_REPO_ROOT", "PYTHONIOENCODING"):
        if _norm_path(exp_env.get(key)) != _norm_path(cur_env.get(key)):
            return False
    return True


def sync_profile_config(
    spec: DomainSpec,
    *,
    python_exe: Path | None = None,
    repo_root: Path | None = None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Return (changed, message)."""
    _, _, profile = resolve_domain_paths(spec)
    cfg_path = profile / "config.yaml"
    if not cfg_path.is_file():
        return False, f"{spec.name}: profiel-config ontbreekt ({cfg_path})"

    text = cfg_path.read_text(encoding="utf-8")
    header, body = _split_header(text)
    raw = _read_yaml_from_body(body)
    expected = expected_mcp_block(spec, python_exe=python_exe, repo_root=repo_root)

    out = dict(raw)
    out.pop("mcp", None)
    current = out.get("mcp_servers")
    if not isinstance(current, dict):
        current = {}
    merged = dict(current)
    for key, entry in expected.items():
        merged[key] = entry
    out["mcp_servers"] = merged

    name = spec.resolved_mcp_name()
    current_entry = current.get(name) if isinstance(current, dict) else None
    expected_entry = expected.get(name) or {}
    needs_path_refresh = not _mcp_entry_matches(expected_entry, current_entry or {})

    good, _ = validate_profile_mcp(spec)
    if good and not has_legacy_mcp_block(raw) and not needs_path_refresh:
        return False, f"{spec.name}: OK (geen wijziging)"

    migrated, _ = migrate_profile_mcp_config(out, repo_root=repo_root or _resolve_repo_root())

    if dry_run:
        return True, f"{spec.name}: zou bijwerken ({cfg_path})"

    _write_yaml(cfg_path, migrated, header=header)
    return True, f"{spec.name}: gesynchroniseerd → mcp_servers.{spec.resolved_mcp_name()}"


def _read_yaml_from_body(body: str) -> dict[str, Any]:
    if not body.strip():
        return {}
    try:
        import yaml

        data = yaml.safe_load(body) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def validate_profile_mcp(spec: DomainSpec) -> tuple[bool, str]:
    _, _, profile = resolve_domain_paths(spec)
    cfg_path = profile / "config.yaml"
    raw = _read_yaml(cfg_path)
    if has_legacy_mcp_block(raw):
        return False, f"{spec.name}: legacy mcp.servers in {cfg_path}"
    servers = raw.get("mcp_servers")
    if not isinstance(servers, dict):
        return False, f"{spec.name}: mcp_servers ontbreekt"
    name = spec.resolved_mcp_name()
    if name not in servers:
        return False, f"{spec.name}: {name} niet in mcp_servers"
    entry = servers[name]
    if not isinstance(entry, dict) or not entry.get("command"):
        return False, f"{spec.name}: ongeldige serverconfig voor {name}"
    env = entry.get("env") or {}
    if not isinstance(env, dict) or not env.get("HERMES_LANCEDB_PATH"):
        return False, f"{spec.name}: HERMES_LANCEDB_PATH ontbreekt in env"
    return True, f"{spec.name}: OK"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync mcp_servers in Hermes-profielen vanuit domains.yaml"
    )
    parser.add_argument("--domains-yaml", type=Path, default=None)
    parser.add_argument("--domain", action="append", default=[])
    parser.add_argument("--check", action="store_true", help="Alleen valideren, niet schrijven")
    parser.add_argument("--python", type=Path, default=None)
    parser.add_argument("--repo", type=Path, default=None)
    args = parser.parse_args(argv)

    yaml_path = args.domains_yaml or default_domains_yaml()
    if not yaml_path.is_file():
        print(f"[ERROR] domains.yaml ontbreekt: {yaml_path}", file=sys.stderr)
        return 1

    py = args.python or _resolve_python()
    repo = args.repo or _resolve_repo_root()
    if not py.is_file():
        print(f"[ERROR] Python niet gevonden: {py}", file=sys.stderr)
        return 1

    specs = load_domains(yaml_path)
    if args.domain:
        wanted = {d.strip().lower() for d in args.domain}
        specs = [s for s in specs if s.name in wanted]
        if not specs:
            print(f"[ERROR] Geen domeinen gevonden voor: {', '.join(args.domain)}", file=sys.stderr)
            return 1

    print(f"[INFO] domains.yaml: {yaml_path}")
    print(f"[INFO] python: {py}")
    print(f"[INFO] repo:   {repo}")

    ok = True
    changed_any = False
    for spec in specs:
        if args.check:
            good, msg = validate_profile_mcp(spec)
            print(f"[{'OK' if good else 'ERROR'}] {msg}")
            if not good:
                ok = False
            continue
        chg, msg = sync_profile_config(spec, python_exe=py, repo_root=repo, dry_run=False)
        tag = "OK" if chg or "OK" in msg else "INFO"
        print(f"[{tag}] {msg}")
        if chg:
            changed_any = True

    if args.check:
        return 0 if ok else 1
    if changed_any:
        print("[INFO] Start een nieuwe Hermes-chat-sessie of /reload-mcp na MCP-wijzigingen.")
    else:
        print("[OK] Alle profiel-MCP-configs zijn al gesynchroniseerd.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
