#!/usr/bin/env python3
"""Repair Cursor ``~/.cursor/mcp.json`` for duplicate keys and process hygiene.

JSON objects cannot contain duplicate keys; many parsers keep the last value
silently (Python ``json.loads``), while PowerShell ``ConvertFrom-Json`` fails.
This script reads the file with duplicate-key detection, merges case-insensitive
server names, disables placeholder servers, and writes valid JSON.

Usage:
    python scripts/repair_cursor_mcp_json.py
    python scripts/repair_cursor_mcp_json.py --path "%USERPROFILE%\\.cursor\\mcp.json"
    python scripts/repair_cursor_mcp_json.py --dry-run
    python scripts/repair_cursor_mcp_json.py --verify
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


_PLACEHOLDER_PATTERNS = (
    re.compile(r"your-service-token", re.I),
    re.compile(r"\{INSERT_YOUR", re.I),
    re.compile(r"^/path/to/", re.I),
)

_CANONICAL_PLAYWRIGHT_ARGS = ["-y", "@playwright/mcp@latest", "--vision"]

_DEFAULT_HERMES_PYTHON = os.environ.get(
    "HERMES_PYTHON",
    os.path.join(
        os.environ.get("USERPROFILE", ""),
        "miniconda3",
        "envs",
        "hermes-env",
        "python.exe",
    ),
)


def _default_mcp_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def _find_case_insensitive_duplicate_keys(
    servers: dict[str, Any],
) -> list[tuple[str, str]]:
    """Keys that collide under case-insensitive comparison (breaks PowerShell)."""
    seen: dict[str, str] = {}
    collisions: list[tuple[str, str]] = []
    for name in servers:
        lower = _canonical_server_key(name)
        if lower in seen and seen[lower] != name:
            collisions.append((seen[lower], name))
        else:
            seen[lower] = name
    return collisions


def _load_mcp_config(path: Path, *, strict: bool = False) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("mcp.json root must be a JSON object")
    if strict:
        servers = data.get("mcpServers")
        if isinstance(servers, dict):
            collisions = _find_case_insensitive_duplicate_keys(servers)
            if collisions:
                names = ", ".join(f"{a!r}/{b!r}" for a, b in collisions)
                raise ValueError(
                    f"Case-insensitive duplicate MCP server names: {names}. "
                    "Run this repair script to merge them."
                )
    return data


def _canonical_server_key(name: str) -> str:
    return name.strip().lower()


def _is_placeholder_server(cfg: dict[str, Any]) -> bool:
    blob = json.dumps(cfg, ensure_ascii=False)
    if any(pat.search(blob) for pat in _PLACEHOLDER_PATTERNS):
        return True
    env = cfg.get("env") or {}
    if isinstance(env, dict):
        for key, val in env.items():
            if key.endswith("_API_KEY") or key.endswith("_TOKEN"):
                if val in ("", None):
                    return True
    return False


def _dedupe_servers_by_name(servers: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Merge servers that differ only by case; last definition wins."""
    changes: list[str] = []
    by_lower: dict[str, tuple[str, dict[str, Any]]] = {}
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            changes.append(f"Skipped non-object server entry: {name!r}")
            continue
        lower = _canonical_server_key(name)
        if lower in by_lower and by_lower[lower][0] != name:
            changes.append(f"Merged duplicate server {by_lower[lower][0]!r} + {name!r}")
        by_lower[lower] = (name, dict(cfg))

    result: dict[str, dict[str, Any]] = {}
    for lower, (orig_name, cfg) in by_lower.items():
        out_name = "playwright" if lower == "playwright" else orig_name
        result[out_name] = cfg
    return result, changes


def _merge_playwright_entries(servers: dict[str, dict[str, Any]], changes: list[str]) -> None:
    playwright_keys = [k for k in list(servers) if _canonical_server_key(k) == "playwright"]
    if not playwright_keys:
        return

    merged: dict[str, Any] = {}
    for key in playwright_keys:
        merged.update(servers.pop(key))
    if len(playwright_keys) > 1 or playwright_keys[0] != "playwright":
        changes.append("Merged duplicate playwright/Playwright into single 'playwright' entry")
    merged["command"] = "npx"
    merged["args"] = list(_CANONICAL_PLAYWRIGHT_ARGS)
    merged["enabled"] = merged.get("enabled", True)
    servers["playwright"] = merged


def _fix_coin_api_python(servers: dict[str, dict[str, Any]], changes: list[str]) -> None:
    entry = servers.get("coin_api")
    if not isinstance(entry, dict):
        return
    py = _DEFAULT_HERMES_PYTHON
    if not py or not Path(py).exists():
        changes.append("coin_api: HERMES_PYTHON not found — left command unchanged")
        return
    entry["command"] = py
    entry["args"] = ["-m", "coin_api_mcp"]
    changes.append(f"coin_api: pinned Python to {py}")


def repair_mcp_servers(servers: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    result, changes = _dedupe_servers_by_name(servers)
    _merge_playwright_entries(result, changes)
    _fix_coin_api_python(result, changes)

    for name, cfg in list(result.items()):
        if _is_placeholder_server(cfg):
            if cfg.get("enabled", True) is not False:
                cfg["enabled"] = False
                changes.append(
                    f"Disabled placeholder server {name!r} "
                    "(set enabled:true after configuring credentials)"
                )

    return result, changes


def repair_file(path: Path, *, dry_run: bool = False) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"mcp.json not found: {path}")

    original_text = path.read_text(encoding="utf-8-sig")
    data = json.loads(original_text)
    if not isinstance(data, dict):
        raise ValueError("mcp.json root must be a JSON object")
    servers = data.get("mcpServers")
    if servers is None:
        raise ValueError("mcp.json missing top-level 'mcpServers' key")
    if not isinstance(servers, dict):
        raise ValueError("'mcpServers' must be a JSON object")

    repaired, changes = repair_mcp_servers(servers)
    data["mcpServers"] = repaired

    out_text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        changes.insert(0, f"[dry-run] Would write {path}")
        return changes

    backup = path.with_suffix(".json.bak")
    backup.write_text(original_text, encoding="utf-8")
    path.write_text(out_text, encoding="utf-8")
    changes.insert(0, f"Wrote {path} (backup: {backup})")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=_default_mcp_path(),
        help="Path to mcp.json (default: ~/.cursor/mcp.json)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Validate only (exit 1 if case-insensitive duplicate server names)",
    )
    args = parser.parse_args(argv)

    if args.verify:
        try:
            _load_mcp_config(args.path, strict=True)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"INVALID: {exc}", file=sys.stderr)
            return 1
        print(f"OK: {args.path}")
        return 0

    try:
        changes = repair_file(args.path, dry_run=args.dry_run)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for line in changes:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
