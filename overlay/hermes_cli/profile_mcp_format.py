"""
Migreer verouderd ``mcp.servers`` naar ``mcp_servers`` in domein-profiel-configs.

Hermes CLI/chat leest alleen ``mcp_servers`` op root-niveau (zie cli-config.yaml.example).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(r"D:\A.I\APPS\Hermes_agent_WS\hermes-agent")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_yaml(path: Path, data: dict[str, Any], *, header: str = "") -> None:
    import yaml

    body = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    path.write_text(header + body, encoding="utf-8")


def _split_header(text: str) -> tuple[str, str]:
    if not text.startswith("#"):
        return "", text
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].startswith("#") or lines[i].strip() == ""):
        i += 1
    return "".join(lines[:i]), "".join(lines[i:])


def has_legacy_mcp_block(raw: dict[str, Any]) -> bool:
    mcp = raw.get("mcp")
    return isinstance(mcp, dict) and isinstance(mcp.get("servers"), dict)


def enrich_mcp_server_env(
    servers: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> None:
    root = str(repo_root or REPO_ROOT_DEFAULT)
    for entry in servers.values():
        if not isinstance(entry, dict):
            continue
        env = entry.setdefault("env", {})
        if not isinstance(env, dict):
            continue
        env.setdefault("HERMES_REPO_ROOT", root)
        env.setdefault("PYTHONIOENCODING", "utf-8")


def migrate_profile_mcp_config(
    raw: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> tuple[dict[str, Any], bool]:
    """Return (config, changed)."""
    out = dict(raw)
    changed = False

    if has_legacy_mcp_block(out):
        nested = out["mcp"]["servers"]
        if not isinstance(out.get("mcp_servers"), dict):
            out["mcp_servers"] = dict(nested)
            changed = True
        out.pop("mcp", None)
        changed = True

    servers = out.get("mcp_servers")
    if isinstance(servers, dict) and servers:
        before = {k: dict(v) if isinstance(v, dict) else v for k, v in servers.items()}
        enrich_mcp_server_env(servers, repo_root=repo_root)
        if servers != before:
            changed = True

    return out, changed


def profiles_with_legacy_mcp(profiles_root: Path | None = None) -> list[str]:
    from hermes_constants import get_default_hermes_root

    root = profiles_root or (get_default_hermes_root() / "profiles")
    names: list[str] = []
    if not root.is_dir():
        return names
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        raw = _read_yaml(entry / "config.yaml")
        if has_legacy_mcp_block(raw):
            names.append(entry.name)
    return names


def migrate_profile_config_file(
    config_path: Path,
    *,
    repo_root: str | Path | None = None,
) -> bool:
    if not config_path.is_file():
        return False
    text = config_path.read_text(encoding="utf-8")
    header, body = _split_header(text)
    raw = _read_yaml_from_text(body)
    migrated, changed = migrate_profile_mcp_config(raw, repo_root=repo_root)
    if not changed:
        return False
    _write_yaml(config_path, migrated, header=header)
    return True


def _read_yaml_from_text(body: str) -> dict[str, Any]:
    if not body.strip():
        return {}
    try:
        import yaml

        data = yaml.safe_load(body) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def migrate_all_profile_mcp_configs(
    profiles_root: Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> list[str]:
    from hermes_constants import get_default_hermes_root

    root = profiles_root or (get_default_hermes_root() / "profiles")
    fixed: list[str] = []
    if not root.is_dir():
        return fixed
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        path = entry / "config.yaml"
        if migrate_profile_config_file(path, repo_root=repo_root):
            fixed.append(entry.name)
    return fixed
